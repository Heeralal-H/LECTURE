import fitz
from pathlib import Path

def extract_pdf_text(path: str) -> str:
    doc = fitz.open(path)
    pages = []
    for page_no, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages.append(f"[Page {page_no}]\n{text}")
    doc.close()
    return "\n\n".join(pages)
