#!/home/ins4ne/.pyenv/versions/3.14.2/bin/python
"""
make_samples.py — Generate synthetic sample PDFs for pipeline testing.
Uses the PyMuPDF 1.24+ TextWriter API (fitz.Font objects required).
Run once to create sample4_service.pdf and sample5_retail.pdf.
"""

from pathlib import Path
import fitz  # PyMuPDF >= 1.24  # type: ignore[import-not-found]

SAMPLES_DIR = Path("samples")
SAMPLES_DIR.mkdir(exist_ok=True)

# Pre-load fonts once (built-in PDF base-14 fonts via fitz.Font)
FONT_REGULAR = fitz.Font("helv")
FONT_BOLD    = fitz.Font("helv", is_bold=True)


def _write(tw: fitz.TextWriter, x: float, y: float, text: str,
           size: float = 11, bold: bool = False) -> None:
    font = FONT_BOLD if bold else FONT_REGULAR
    tw.append((x, y), text, font=font, fontsize=size)


def make_service_invoice() -> None:
    """sample4_service.pdf — IT consultancy invoice with GST."""
    doc  = fitz.open()
    page = doc.new_page(width=595, height=842)   # A4
    tw   = fitz.TextWriter(page.rect)

    _write(tw, 200, 60,  "TAX INVOICE",                          size=18, bold=True)

    # Vendor block
    _write(tw, 50, 110,  "Vendor:  TECHSPARK SOLUTIONS PVT LTD", bold=True)
    _write(tw, 50, 128,  "GSTIN:   27AABCT1234D1ZX")
    _write(tw, 50, 146,  "Address: 501, Cyber Tower, Hinjawadi, Pune - 411057")
    _write(tw, 50, 164,  "Email:   billing@techspark.in   |   Ph: +91 20 4567 8900")

    page.draw_line((50, 180), (545, 180))

    _write(tw, 50, 200,  "Invoice No :  INV-2024-00847",          bold=True)
    _write(tw, 50, 218,  "Invoice Date:  2024-03-15")
    _write(tw, 50, 236,  "Due Date    :  2024-04-14")

    _write(tw, 50, 270,  "Bill To:",                              bold=True)
    _write(tw, 50, 288,  "INFOSYS LIMITED")
    _write(tw, 50, 306,  "GSTIN: 29AABCI1681G1ZP")
    _write(tw, 50, 324,  "Plot 44, Electronics City Phase-II, Bengaluru - 560100")

    page.draw_line((50, 345), (545, 345))

    # Table header
    _write(tw, 50,  365, "Description",    bold=True)
    _write(tw, 320, 365, "Qty",            bold=True)
    _write(tw, 370, 365, "Rate (INR)",     bold=True)
    _write(tw, 460, 365, "Amount (INR)",   bold=True)
    page.draw_line((50, 378), (545, 378))

    rows = [
        ("Cloud Architecture Consulting", "10 hrs", "8,500.00",  "85,000.00"),
        ("DevOps Pipeline Setup",          "5 hrs",  "8,500.00",  "42,500.00"),
        ("Security Audit & Report",        "1 lot",  "25,000.00", "25,000.00"),
    ]
    y = 395
    for desc, qty, rate, amt in rows:
        _write(tw, 50,  y, desc)
        _write(tw, 320, y, qty)
        _write(tw, 370, y, rate)
        _write(tw, 465, y, amt)
        y += 20

    page.draw_line((50, y + 5), (545, y + 5))
    y += 20

    _write(tw, 370, y,      "Subtotal");          _write(tw, 465, y,      "1,52,500.00"); y += 18
    _write(tw, 370, y,      "CGST @ 9%");         _write(tw, 465, y,         "13,725.00"); y += 18
    _write(tw, 370, y,      "SGST @ 9%");         _write(tw, 465, y,         "13,725.00"); y += 18
    page.draw_line((360, y), (545, y)); y += 8
    _write(tw, 370, y,      "TOTAL AMOUNT",       bold=True)
    _write(tw, 445, y,      "INR 1,79,950.00",    bold=True)

    tw.write_text(page)            # flush all text to the page
    out = SAMPLES_DIR / "sample4_service.pdf"
    doc.save(str(out))
    doc.close()
    print(f"Created: {out}")


def make_retail_invoice() -> None:
    """sample5_retail.pdf — retail shop invoice."""
    doc  = fitz.open()
    page = doc.new_page(width=595, height=842)
    tw   = fitz.TextWriter(page.rect)

    _write(tw, 200, 55,  "RETAIL INVOICE",                                size=16, bold=True)

    _write(tw, 50,  100, "Sold By:  SHARMA GENERAL STORE",                bold=True)
    _write(tw, 50,  118, "GSTIN  :  07ABCPS4321F1Z3")
    _write(tw, 50,  136, "Address:  Shop 12, Lajpat Nagar Market, New Delhi - 110024")

    page.draw_line((50, 155), (545, 155))

    _write(tw, 50,  172, "Invoice No :  SGS/2024/1193",                   bold=True)
    _write(tw, 50,  190, "Date       :  2024-03-20")

    _write(tw, 50,  220, "Customer:  RAMESH KUMAR VERMA",                  bold=True)
    _write(tw, 50,  238, "Phone   :  +91 98110 55221")

    page.draw_line((50, 258), (545, 258))

    _write(tw, 50,  275, "Item",  bold=True)
    _write(tw, 310, 275, "Qty",   bold=True)
    _write(tw, 370, 275, "Price", bold=True)
    _write(tw, 470, 275, "Total", bold=True)
    page.draw_line((50, 288), (545, 288))

    items = [
        ("Tata Salt (1 kg)",        "3",  "22.00",  "66.00"),
        ("Amul Butter (500 g)",     "2", "280.00", "560.00"),
        ("Parle-G Biscuit (800 g)", "4",  "45.00", "180.00"),
        ("Surf Excel (1 kg)",       "1", "320.00", "320.00"),
        ("Maggi Noodles x12",       "2", "204.00", "408.00"),
    ]
    y = 305
    for item, qty, price, total in items:
        _write(tw, 50,  y, item)
        _write(tw, 315, y, qty)
        _write(tw, 365, y, price)
        _write(tw, 470, y, total)
        y += 20

    page.draw_line((50, y + 5), (545, y + 5)); y += 20
    _write(tw, 370, y, "Subtotal");      _write(tw, 465, y, "1,534.00"); y += 18
    _write(tw, 370, y, "GST @ 5%");     _write(tw, 465, y,    "76.70"); y += 18
    page.draw_line((360, y), (545, y)); y += 8
    _write(tw, 370, y, "TOTAL",         bold=True)
    _write(tw, 450, y, "INR 1,610.70",  bold=True)

    _write(tw, 170, y + 60, "Thank you for shopping with us!")

    tw.write_text(page)
    out = SAMPLES_DIR / "sample5_retail.pdf"
    doc.save(str(out))
    doc.close()
    print(f"Created: {out}")


if __name__ == "__main__":
    make_service_invoice()
    make_retail_invoice()
    print("Done — both sample PDFs generated successfully.")
