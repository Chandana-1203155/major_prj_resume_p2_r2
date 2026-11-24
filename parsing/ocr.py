"""Optional OCR support for scanned PDFs."""

# OCR is optional: only used as a fallback for scanned/image-only PDFs where
# normal text extraction returns nothing. If these libraries (and their
# system dependencies — tesseract-ocr, poppler-utils) aren't installed, the
# app still works normally; it just can't OCR scanned resumes and will say
# so instead of silently failing.
try:
    import pytesseract
    from pdf2image import convert_from_bytes
    OCR_AVAILABLE = True
except ImportError:
    pytesseract = None
    convert_from_bytes = None
    OCR_AVAILABLE = False
