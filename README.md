# Invoice Automation POC
Automated invoice data extraction from PDFs and images using a fully local AI stack. Zero cloud dependency, zero data leakage.

## What it does
This tool reads invoices you upload and intelligently extracts the important details like the vendor name, total amount, and dates. It works for both standard digital PDFs and scanned images or photos of invoices. The entire process runs purely on your own computer, meaning your sensitive financial documents are never uploaded to the internet or shared with third-party companies. It's incredibly easy to use: just drop your files into the web application, and it will handle the rest.

## Key Features
- Extracts vendor name, invoice number, date, amount, GST number, buyer name
- Handles digital PDFs (text-based) and scanned/photographed invoices (image-based)
- Fully offline — no OpenAI, no cloud APIs, no data leaves your machine
- Web UI for drag-and-drop invoice processing
- Batch processing — upload multiple invoices at once
- Stores all extracted data in a local SQLite database

## How it works
```text
PDF / Image
     │
     ├── Text extractable? → YES → Qwen2.5:1.5b (text LLM) → JSON
     │
     └── NO (scanned/photo) → Qwen2.5-VL:3b (vision LLM) → JSON
                                        │
                                   SQLite Database
```

## Tech Stack
| Component | Technology |
|---|---|
| PDF text extraction | PyMuPDF |
| OCR / Vision | Qwen2.5-VL:3b via Ollama |
| Text parsing | Qwen2.5:1.5b via Ollama |
| Web UI | Gradio |
| Database | SQLite |
| Runtime | Python 3.14, pyenv |

## Demo
[Screenshot / demo GIF coming soon]

## Setup & Installation
```fish
# 1. Clone the repo
git clone https://github.com/Aaryan-Patwardhan/invoice-automation-poc
cd invoice-automation-poc

# 2. Install system dependency (Arch Linux)
paru -S poppler
# Ubuntu/Debian: sudo apt-get install poppler-utils

# 3. Create venv and install Python dependencies
python -m venv venv
source venv/bin/activate.fish
pip install -r requirements.txt

# 4. Pull Ollama models
ollama pull qwen2.5:1.5b
ollama pull qwen2.5vl:3b
```

## Usage
- **CLI mode**: `python extractor.py` (drops PDFs in `samples/`, runs pipeline)
- **Web UI mode**: `python app.py` → open http://localhost:7860

## Privacy & Security
- All inference runs locally on your hardware via Ollama
- No data is sent to any external server
- No API keys required
- Suitable for confidential financial documents

Built by — "Aaryan Patwardhan — AI Automation Engineer (in progress) | GitHub"
