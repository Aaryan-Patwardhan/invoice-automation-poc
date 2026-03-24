#!/home/ins4ne/.pyenv/versions/3.14.2/bin/python
"""
extractor.py — Invoice Automation Pipeline
Extracts text from PDFs, parses invoice fields via Ollama/Qwen2.5:1.5b, stores in SQLite.
"""

import os
import re
import io
import json
import base64
import sqlite3
import datetime
from pathlib import Path

from PIL import Image           # type: ignore[import-not-found]
from pdf2image import convert_from_path  # type: ignore[import-not-found]

import fitz          # PyMuPDF  # type: ignore[import-not-found]
import requests      # used to call Ollama REST API  # type: ignore[import-not-found]

# ─── Configuration ────────────────────────────────────────────────────────────

SAMPLES_DIR   = Path("samples")
DB_PATH       = Path("invoices.db")
OLLAMA_URL    = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL  = "qwen2.5:1.5b"
VISION_MODEL  = "qwen2.5vl:3b"

REQUIRED_FIELDS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "total_amount",
    "gst_number",
    "buyer_name",
]

SYSTEM_PROMPT = """\
You are an invoice data extraction assistant.
Given the raw text of an invoice, extract the following fields and return ONLY valid JSON:
{
  "vendor_name":     "<string>",
  "invoice_number":  "<string>",
  "invoice_date":    "<string, ISO 8601 preferred>",
  "total_amount":    "<string, numeric value with currency if present>",
  "gst_number":      "<string or null>",
  "buyer_name":      "<string or null>"
}
Do NOT include any explanation, markdown fences, or extra text — only the JSON object.
"""

# ─── Step 1: Extract Text ─────────────────────────────────────────────────────

def extract_text(pdf_path: str | Path) -> str:
    """Extract all text from a PDF file using PyMuPDF."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


# ─── Step 1b: OCR Fallback ────────────────────────────────────────────────────

def is_text_extractable(text: str) -> bool:
    """Return False if extracted text is too short to be useful (< 100 chars)."""
    return len(text.strip()) >= 100


def pdf_to_images(pdf_path: str) -> list:
    """Convert PDF pages to PIL Image objects using pdf2image at 200 DPI."""
    return convert_from_path(str(pdf_path), dpi=200)


def parse_invoice_vision(image: Image.Image) -> dict:
    """
    Send a PIL Image to qwen2.5vl:3b via Ollama's vision API.
    Returns parsed invoice fields as a dict, or empty dict on failure.
    """
    try:
        # Convert PIL Image to base64-encoded PNG
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        payload = {
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Extract the following fields from this invoice image "
                        "and return ONLY valid JSON, no explanation, no markdown fences:\n"
                        '{\n'
                        '  "vendor_name": "<string>",\n'
                        '  "invoice_number": "<string>",\n'
                        '  "invoice_date": "<string>",\n'
                        '  "total_amount": "<string>",\n'
                        '  "gst_number": "<string or null>",\n'
                        '  "buyer_name": "<string or null>"\n'
                        '}'
                    ),
                    "images": [img_b64],
                }
            ],
            "stream": False,
            "options": {"temperature": 0.0},
        }

        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=180)
        response.raise_for_status()
        llm_output = response.json().get("message", {}).get("content", "").strip()

        # Strip markdown fences if present
        llm_output = _strip_markdown_fences(llm_output)

        data = json.loads(llm_output)
        for field in REQUIRED_FIELDS:
            data.setdefault(field, None)
        return data

    except Exception as exc:
        print(f"  [ERROR] Vision OCR failed: {exc}")
        return {}


# ─── Step 2: Parse Invoice via Ollama ─────────────────────────────────────────

def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences if present."""
    # Remove opening fence (with optional language tag) and closing fence
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


def _regex_fallback(text: str) -> dict:
    """
    Last-resort: pull individual fields with regex from raw LLM output.
    Returns a dict with whatever could be matched (missing fields → None).
    """
    patterns = {
        "vendor_name":    r'"vendor_name"\s*:\s*"([^"]*)"',
        "invoice_number": r'"invoice_number"\s*:\s*"([^"]*)"',
        "invoice_date":   r'"invoice_date"\s*:\s*"([^"]*)"',
        "total_amount":   r'"total_amount"\s*:\s*"([^"]*)"',
        "gst_number":     r'"gst_number"\s*:\s*"([^"]*)"',
        "buyer_name":     r'"buyer_name"\s*:\s*"([^"]*)"',
    }
    result = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        result[field] = match.group(1) if match else None
    return result


def parse_invoice(raw_text: str) -> dict:
    """
    Send raw invoice text to Ollama (Qwen2.5:1.5b) and return a strict JSON dict
    with the required invoice fields.  Handles markdown fences and regex fallback.
    """
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"--- INVOICE TEXT START ---\n{raw_text}\n--- INVOICE TEXT END ---\n\n"
        f"Return only the JSON object:"
    )

    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,   # deterministic output
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        llm_output = response.json().get("response", "").strip()
    except requests.RequestException as exc:
        print(f"  [ERROR] Ollama request failed: {exc}")
        return {field: None for field in REQUIRED_FIELDS}

    # ── Attempt 1: direct JSON parse ──
    try:
        data = json.loads(llm_output)
        # Ensure all required fields exist
        for field in REQUIRED_FIELDS:
            data.setdefault(field, None)
        return data
    except json.JSONDecodeError:
        pass

    # ── Attempt 2: strip markdown fences, re-parse ──
    cleaned = _strip_markdown_fences(llm_output)
    try:
        data = json.loads(cleaned)
        for field in REQUIRED_FIELDS:
            data.setdefault(field, None)
        print("  [WARN] JSON parsed after stripping markdown fences.")
        return data
    except json.JSONDecodeError:
        pass

    # ── Attempt 3: extract first JSON object via regex ──
    json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            for field in REQUIRED_FIELDS:
                data.setdefault(field, None)
            print("  [WARN] JSON extracted via brace-matching regex.")
            return data
        except json.JSONDecodeError:
            pass

    # ── Attempt 4: field-level regex fallback ──
    print("  [WARN] All JSON parse attempts failed — using regex field fallback.")
    return _regex_fallback(llm_output)


# ─── Step 3: Save to SQLite ───────────────────────────────────────────────────

def _init_db(conn: sqlite3.Connection) -> None:
    """Create the invoices table if it does not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file     TEXT    NOT NULL,
            vendor_name     TEXT,
            invoice_number  TEXT,
            invoice_date    TEXT,
            total_amount    TEXT,
            gst_number      TEXT,
            buyer_name      TEXT,
            extracted_at    TEXT    NOT NULL
        )
    """)
    conn.commit()


def save_to_db(data: dict, source_file: str | Path) -> int:
    """
    Persist parsed invoice data to SQLite.
    Skips the insert and returns the existing row id if source_file is already present.
    Returns the row id of the inserted (or existing) record.
    """
    with sqlite3.connect(str(DB_PATH)) as conn:
        _init_db(conn)

        # ── Dedup check ──────────────────────────────────────────────────────
        existing = conn.execute(
            "SELECT id FROM invoices WHERE source_file = ? LIMIT 1",
            (str(source_file),),
        ).fetchone()
        if existing:
            print(f"  [SKIP] Already in DB (row id={existing[0]}), skipping insert.")
            return existing[0]

        cursor = conn.execute(
            """
            INSERT INTO invoices
                (source_file, vendor_name, invoice_number, invoice_date,
                 total_amount, gst_number, buyer_name, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(source_file),
                data.get("vendor_name"),
                data.get("invoice_number"),
                data.get("invoice_date"),
                data.get("total_amount"),
                data.get("gst_number"),
                data.get("buyer_name"),
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid
        assert row_id is not None, "INSERT did not return a row id"
        return row_id


# ─── Main Loop ────────────────────────────────────────────────────────────────

def main() -> None:
    if not SAMPLES_DIR.exists():
        print(f"[ERROR] Samples directory '{SAMPLES_DIR}' not found.")
        return

    pdf_files = sorted(SAMPLES_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"[WARN] No PDF files found in '{SAMPLES_DIR}'.")
        return

    print(f"Found {len(pdf_files)} PDF(s) in '{SAMPLES_DIR}'. Starting pipeline...\n")

    for pdf_path in pdf_files:
        print(f"── Processing: {pdf_path.name}")

        # 1. Extract text
        try:
            raw_text = extract_text(pdf_path)
            print(f"  Extracted {len(raw_text)} characters.")
        except Exception as exc:
            print(f"  [ERROR] Text extraction failed: {exc}")
            continue

        # 2. Parse invoice fields — TEXT or OCR path
        if is_text_extractable(raw_text):
            data = parse_invoice(raw_text)
            print(f"  [TEXT] {pdf_path.name}")
        else:
            print(f"  Text too short, falling back to vision OCR...")
            try:
                images = pdf_to_images(str(pdf_path))
                data = parse_invoice_vision(images[0])
            except Exception as exc:
                print(f"  [ERROR] OCR fallback failed: {exc}")
                data = {}
            print(f"  [OCR] {pdf_path.name}")

        print(f"  Parsed data: {json.dumps(data, ensure_ascii=False)}")

        # 3. Guard: skip save if every field is empty / None
        if all(not data.get(f) for f in REQUIRED_FIELDS):
            print("  [SKIP] All fields empty — not saving to DB.")
            print()
            continue

        # 4. Save to DB
        try:
            row_id = save_to_db(data, pdf_path)
            print(f"  Saved to DB with row id={row_id}.")
        except Exception as exc:
            print(f"  [ERROR] DB save failed: {exc}")

        print()

    print(f"Pipeline complete. Results stored in '{DB_PATH}'.")


if __name__ == "__main__":
    main()
