import logging

from app.ingestion.document_loader import load_pdf
from app.ingestion.ocr import ocr_pdf

logger = logging.getLogger(__name__)


def load_document(file_path: str) -> str:

    text = load_pdf(file_path)

    # If text is too small → likely scanned PDF
    if len(text.strip()) < 50:
        logger.info("Using OCR fallback for PDF")
        text = ocr_pdf(file_path)

    return text