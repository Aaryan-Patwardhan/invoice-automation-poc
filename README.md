# Invoice Automation POC

Extracts vendor, amount, date, and GST number from any Indian invoice PDF using a local LLM. Zero API costs. Runs fully offline.

## Demo
```json
{
  "vendor_name": "ZOMATO LIMITED",
  "invoice_number": "225WH74O00024196",
  "invoice_date": "2022-11-12",
  "total_amount": "567.00",
  "gst_number": null,
  "buyer_name": "AASHEESH"
}
```

## Stack
- PyMuPDF — PDF text extraction
- Qwen2.5-1.5B via Ollama — structured JSON extraction
- SQLite — storage

## How to run
```bash
git clone https://github.com/that-ins4ne/invoice-automation-poc
cd invoice-automation-poc
python -m venv venv
source venv/bin/activate.fish
pip install pymupdf requests ollama
ollama pull qwen2.5:1.5b
python extractor.py
```
