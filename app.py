#!/usr/bin/env python
"""
app.py — Gradio Web UI for Invoice Automation Pipeline
Upload PDFs or images to extract invoice fields via local LLMs.
"""

import json
import shutil
from pathlib import Path

from PIL import Image  # type: ignore[import-not-found]
import gradio as gr    # type: ignore[import-not-found]

from extractor import (
    extract_text,
    is_text_extractable,
    pdf_to_images,
    parse_invoice,
    parse_invoice_vision,
    save_to_db,
    SAMPLES_DIR,
    REQUIRED_FIELDS,
)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


def _get_path(fp) -> str:
    """Robustly extract the file path regardless of Gradio version (dict, str, or NamedString)."""
    if isinstance(fp, str): return fp
    if hasattr(fp, "name"): return fp.name
    if isinstance(fp, dict) and "name" in fp: return fp["name"]
    return str(fp)

def _process_single_file(raw_fp) -> tuple[dict, str]:
    """
    Process a single file (PDF or image) through the pipeline.
    Returns (data_dict, status_string).
    """
    try:
        file_path = _get_path(raw_fp)
        path = Path(file_path)
        ext = path.suffix.lower()
        name = path.name

        # Enforce recording all inputs in samples/
        temp_path = SAMPLES_DIR / f"temp_{name}"
        SAMPLES_DIR.mkdir(exist_ok=True)
        try:
            shutil.copy(file_path, temp_path)
            file_path = str(temp_path)
        except Exception:
            pass  # Fallback to the original temporary file if copy fails

        # ── Image file → direct vision OCR ──
        if ext in IMAGE_EXTENSIONS:
            try:
                image = Image.open(file_path)
                data = parse_invoice_vision(image)
            except Exception as exc:
                return {}, f"❌ [{name}] Image OCR failed: {exc}"
            status = f"🖼️ [IMAGE-OCR] {name} — Parsed via vision LLM"
            
        # ── PDF file → TEXT or OCR path ──
        elif ext == ".pdf":
            try:
                raw_text = extract_text(file_path)
            except Exception as exc:
                return {}, f"❌ [{name}] Text extraction failed: {exc}"

            if is_text_extractable(raw_text):
                data = parse_invoice(raw_text)
                status = f"📄 [TEXT] {name} — Parsed via text LLM"
            else:
                try:
                    images = pdf_to_images(file_path)
                    data = parse_invoice_vision(images[0]) if images else {}
                except Exception as exc:
                    return {}, f"❌ [{name}] OCR fallback failed: {exc}"
                status = f"🔍 [OCR] {name} — Parsed via vision LLM"
        else:
            return {}, f"⚠️ [{name}] Unsupported file type: {ext}"

        # ── Save to DB ──
        if data and any(data.get(f) for f in REQUIRED_FIELDS):
            try:
                row_id = save_to_db(data, file_path)
                status += f" → ✅ DB row={row_id}"
            except Exception as exc:
                status += f" → ⚠️ DB save failed: {exc}"
        else:
            status += " → ⚠️ All fields empty, not saved."

        return data, status

    except Exception as e:
        return {}, f"❌ Critical error parsing file: {e}"


def process_invoices(file_paths) -> tuple[str, str]:
    """
    Process one or more uploaded files (PDFs and/or images).
    Returns (combined_json, combined_status).
    """
    if not file_paths:
        return "", "⚠️ No files uploaded."

    # Force inputs into iterable list
    if not isinstance(file_paths, list):
        file_paths = [file_paths]

    all_results = []
    all_statuses = []

    for fp in file_paths:
        data, status = _process_single_file(fp)
        file_name = Path(_get_path(fp)).name
        all_results.append({"file": file_name, **data})
        all_statuses.append(status)

    # Single file → return plain object; multiple → return array
    if len(all_results) == 1:
        json_str = json.dumps(all_results[0], indent=2, ensure_ascii=False)
    else:
        json_str = json.dumps(all_results, indent=2, ensure_ascii=False)

    status_str = "\n".join(all_statuses)
    return json_str, status_str


# ─── Gradio Interface ─────────────────────────────────────────────────────────

with gr.Blocks(
    title="Invoice Automation",
    theme=gr.themes.Soft(),
) as demo:
    gr.Markdown(
        "# 🧾 Invoice Automation Pipeline\n"
        "Upload PDF invoices or images (JPG/PNG) to extract fields using local LLMs via Ollama.\n\n"
        "*Multiple files supported — select several at once.*"
    )

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(
                label="Upload Invoices (PDFs or Images)",
                file_types=[".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"],
                file_count="multiple",
                type="filepath",
            )
            process_btn = gr.Button("⚡ Process Invoices", variant="primary")

        with gr.Column(scale=2):
            json_output = gr.Textbox(
                label="Extracted Fields (JSON)",
                lines=18,
                interactive=False,
            )
            status_output = gr.Textbox(
                label="Status",
                lines=6,
                interactive=False,
            )

    process_btn.click(
        fn=process_invoices,
        inputs=[file_input],
        outputs=[json_output, status_output],
    )


if __name__ == "__main__":
    demo.launch(share=True, server_port=7860)
