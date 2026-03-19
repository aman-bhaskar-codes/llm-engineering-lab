from app.ingestion.document_loader import load_pdf
from app.ingestion.ocr import ocr_pdf


def load_document(file_path: str) -> str:

    text = load_pdf(file_path)

    # If text is too small → likely scanned PDF
    if len(text.strip()) < 50:
        print("Using OCR fallback...")
        text = ocr_pdf(file_path)

    return text