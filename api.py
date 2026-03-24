import os
import uuid
import sqlite3
import requests
from pathlib import Path
from fastapi import FastAPI, Depends, UploadFile, File, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from extractor import (
    extract_text,
    is_text_extractable,
    pdf_to_images,
    parse_invoice,
    parse_invoice_vision,
    save_to_db
)

# Initialize FastAPI
app = FastAPI(
    title="Invoice Automation API",
    description="REST API for the fully local invoice automation pipeline.",
    version="1.0.0"
)

# Security Constants
DB_PATH = "invoices.db"
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Expandable for future frontends
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Size constraint middleware
@app.middleware("http")
async def validate_content_length(request: Request, call_next):
    """
    Middleware to ensure payloads over 10MB are rejected immediately with HTTP 413.
    """
    length = request.headers.get("content-length")
    if length and int(length) > MAX_UPLOAD_SIZE:
        return JSONResponse(
            status_code=413,
            content={"status": "error", "message": "Payload Too Large (Limit 10MB)"}
        )
    return await call_next(request)

# Security Dependency
async def verify_api_key(request: Request):
    """
    Checks the 'X-API-Key' header vs environment 'API_KEY'. 
    Rejects the request if unmatched.
    """
    expected_api_key = os.getenv("API_KEY")
    if expected_api_key:
        passed_key = request.headers.get("X-API-Key")
        if not passed_key or passed_key != expected_api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing X-API-Key header"
            )

# Endpoints
@app.post("/extract", dependencies=[Depends(verify_api_key)])
async def api_extract_invoice(file: UploadFile = File(...)):
    """
    Accepts multipart file upload (PDF or image).
    Extracts text natively or uses Vision LLM OCR fallback.
    Saves results to the DB and securely cleans up temp files.
    """
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    temp_filename = f"temp_{uuid.uuid4()}{ext}"
    temp_path = Path("samples") / temp_filename

    # Ensure output samples directory exists
    temp_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Save payload to disk securely
        with temp_path.open("wb") as buffer:
            buffer.write(await file.read())

        path_taken = None
        data = None

        if ext in ALLOWED_IMAGE_EXTS:
            path_taken = "IMAGE-OCR"
            from PIL import Image
            img = Image.open(temp_path)
            data = parse_invoice_vision(img)
            
        elif ext == ".pdf":
            raw_text = extract_text(str(temp_path))
            
            if is_text_extractable(raw_text):
                path_taken = "TEXT"
                data = parse_invoice(raw_text)
            else:
                path_taken = "OCR"
                images = pdf_to_images(str(temp_path))
                if not images:
                    return {"status": "empty", "message": "No fields could be extracted"}
                
                # We simply use the first page of the PDF for OCR fallback
                data = parse_invoice_vision(images[0])
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        if not data:
            return {"status": "empty", "message": "No fields could be extracted"}

        # Write successfully extracted JSON to Database
        row_id = save_to_db(data, file.filename)
        
        return {
            "status": "success",
            "path_taken": path_taken,
            "row_id": row_id,
            "data": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})

    finally:
        # Guaranteed cleanup, immune to errors
        if temp_path.exists():
            temp_path.unlink()

@app.get("/invoices", dependencies=[Depends(verify_api_key)])
async def list_invoices(limit: int = 50):
    """
    Returns an array of processed invoices from the database. Max limit 200.
    """
    limit = min(limit, 200)
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM invoices ORDER BY id DESC LIMIT ?", (limit,))
        rows = [dict(row) for row in cur.fetchall()]
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})
    finally:
        conn.close()

@app.get("/invoices/{id}", dependencies=[Depends(verify_api_key)])
async def get_invoice(id: int):
    """
    Returns a single invoice row matched by explicit ID.
    Returns HTTP 404 if not found.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM invoices WHERE id = ?", (id,))
        row = cur.fetchone()
        if row is None:
            return JSONResponse(status_code=404, content={"status": "not_found"})
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})
    finally:
        conn.close()

@app.get("/health")
async def health_check():
    """
    Checks the status of the local tools (DB, Ollama daemon).
    Omitted the API key required check here to serve as a generic pingable endpoint.
    """
    db_status = "ok"
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        db_status = "error"

    ollama_status = "unreachable"
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            ollama_status = "reachable"
    except Exception:
        pass

    return {
        "status": "ok",
        "ollama": ollama_status,
        "db": db_status
    }

if __name__ == "__main__":
    import uvicorn
    # Change "127.0.0.1" to "0.0.0.0" below to make the API accessible on your network!
    HOST = "127.0.0.1"
    PORT = 8000
    
    print("Starting Invoice Automation API...")
    print(f"API docs: http://{HOST}:{PORT}/docs")
    print(f"Health:   http://{HOST}:{PORT}/health")
    
    uvicorn.run("api:app", host=HOST, port=PORT, reload=True)
