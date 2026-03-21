import logging

from ingestion.document_loader import load_pdf
from ingestion.ocr import ocr_pdf

from ingestion.ocr import ocr_pdf

logger = logging.getLogger(__name__)

def load_document(file_path: str) -> str:
    # Check if this is an image
    file_lower = file_path.lower()
    if file_lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
        logger.info(f"Detected image file, running direct OCR on: {file_path}")
        from PIL import Image
        import pytesseract
        
        try:
            return pytesseract.image_to_string(Image.open(file_path))
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            return ""

    text = load_pdf(file_path)

    # If text is too small → likely scanned PDF
    if len(text.strip()) < 50:
        logger.info("Using OCR fallback for PDF")
        text = ocr_pdf(file_path)

    return text