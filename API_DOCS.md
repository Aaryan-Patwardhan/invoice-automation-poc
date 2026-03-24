# Invoice Automation API Documentation

The REST API operates on `http://127.0.0.1:8000` by default. 
Interactive Swagger docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) when running the server.

## Authentication
Every request must include the `X-API-Key` header if the `API_KEY` environment variable is set on the server on launch. If `API_KEY` is not set, the endpoints will be open.

## Endpoints

### 1. `GET /health`
Checks the connection to the SQLite database and the local Ollama daemon.

**Example Request:**
```bash
curl -X GET http://127.0.0.1:8000/health
```
**Example Response:**
```json
{
  "status": "ok",
  "ollama": "reachable",
  "db": "ok"
}
```

### 2. `POST /extract`
Uploads a document to automatically extract invoice data using standard and Vision LLM processing. Upload size is limited to 10MB. 

**Params:**
- `file`: The `multipart/form-data` file (supports `.pdf`, `.jpg`, `.png`, `.webp`, `.bmp`, `.tiff`)

**Example Request:**
```bash
curl -X POST http://127.0.0.1:8000/extract \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@samples/test_invoice.pdf"
```

**Example Response:**
```json
{
  "status": "success",
  "path_taken": "OCR",
  "row_id": 12,
  "data": {
    "vendor_name": "Tech Corp",
    "invoice_number": "INV-100",
    "invoice_date": "2023-10-01",
    "total_amount": "500.00",
    "gst_number": null,
    "buyer_name": "Aaryan"
  }
}
```

### 3. `GET /invoices`
Returns a list of all processed invoices from the local SQLite database.

**Params (Query):**
- `limit` (int, default: 50, max: 200)

**Example Request:**
```bash
curl -X GET "http://127.0.0.1:8000/invoices?limit=10" \
  -H "X-API-Key: YOUR_API_KEY"
```

### 4. `GET /invoices/{id}`
Returns a specific invoice row by its database ID.

**Example Request:**
```bash
curl -X GET http://127.0.0.1:8000/invoices/12 \
  -H "X-API-Key: YOUR_API_KEY"
```

**Example Response (404):**
```json
{
  "status": "not_found"
}
```
