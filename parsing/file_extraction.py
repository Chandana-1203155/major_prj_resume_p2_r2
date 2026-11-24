"""Text extraction from uploaded PDF/DOCX/TXT/ZIP files."""

import io
import os
import zipfile

import docx
import streamlit as st
from PyPDF2 import PdfReader

from config import MAX_FILE_SIZE_BYTES, MAX_ZIP_ENTRIES, MAX_ZIP_TOTAL_UNCOMPRESSED, OCR_MAX_PAGES, OCR_MIN_TEXT_CHARS
from parsing.ocr import OCR_AVAILABLE, convert_from_bytes, pytesseract
from utils.hashing import compute_content_hash


# -------------------------------------------------
# FILE EXTRACTION
# -------------------------------------------------

def extract_pdf(file_bytes):
    try:
        pdf = PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        st.error(f"PDF extraction error: {e}")
        return ""

    if len(text.strip()) >= OCR_MIN_TEXT_CHARS:
        return text

    # Normal extraction found little/no text — likely a scanned or
    # image-only PDF. Fall back to OCR if the optional OCR libraries
    # (pytesseract + pdf2image, plus their system deps tesseract-ocr and
    # poppler-utils) are installed; otherwise return what little text we
    # have and let the caller's "empty resume" message explain why.
    if not OCR_AVAILABLE:
        return text

    try:
        images = convert_from_bytes(file_bytes, dpi=200)
        ocr_text_parts = []
        for page_image in images[:OCR_MAX_PAGES]:
            ocr_text_parts.append(pytesseract.image_to_string(page_image))
        ocr_text = "\n".join(ocr_text_parts).strip()
        if ocr_text:
            return ocr_text
        return text
    except Exception as e:
        st.warning(f"OCR fallback failed for a scanned PDF: {e}")
        return text


def extract_docx(file_bytes):
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([para.text for para in doc.paragraphs if para.text])
    except Exception as e:
        st.error(f"DOCX extraction error: {e}")
        return ""


def extract_txt(file_bytes):
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"TXT extraction error: {e}")
        return ""

def extract_text_from_file(uploaded_file):
    name = uploaded_file.name.lower()
    content = uploaded_file.read()
    uploaded_file.seek(0)
    if len(content) > MAX_FILE_SIZE_BYTES:
        st.error(f"{uploaded_file.name} exceeds the {MAX_FILE_SIZE_BYTES // (1024*1024)}MB size limit and was skipped.")
        return ""
    if name.endswith(".pdf"):
        return extract_pdf(content)
    if name.endswith(".docx"):
        return extract_docx(content)
    if name.endswith(".txt"):
        return extract_txt(content)
    return ""


def extract_zip_files(zip_file):
    """
    Extract resumes from a ZIP entirely in memory (never written to disk, so
    classic path-traversal write attacks don't apply), while guarding against
    zip-bomb style abuse: caps on entry count and total uncompressed size, and
    per-entry size checked against the declared file_size before reading.
    Entry names are reduced to their basename only, so any '../' components
    in a malicious archive are discarded rather than used.
    """
    extracted_files = []
    total_uncompressed = 0
    try:
        with zipfile.ZipFile(io.BytesIO(zip_file.read())) as z:
            infolist = z.infolist()
            if len(infolist) > MAX_ZIP_ENTRIES:
                st.error(f"ZIP contains more than {MAX_ZIP_ENTRIES} entries; only the first {MAX_ZIP_ENTRIES} will be processed.")
                infolist = infolist[:MAX_ZIP_ENTRIES]
            for info in infolist:
                if info.is_dir():
                    continue
                safe_name = os.path.basename(info.filename)
                if not safe_name:
                    continue
                name = safe_name.lower()
                if not any(name.endswith(ext) for ext in [".pdf", ".docx", ".txt"]):
                    continue
                if info.file_size > MAX_FILE_SIZE_BYTES:
                    st.warning(f"Skipped {safe_name}: exceeds per-file size limit.")
                    continue
                total_uncompressed += info.file_size
                if total_uncompressed > MAX_ZIP_TOTAL_UNCOMPRESSED:
                    st.error("ZIP extraction stopped: total uncompressed size limit reached (possible zip bomb).")
                    break
                data = z.read(info.filename)
                text = ""
                if name.endswith(".pdf"):
                    text = extract_pdf(data)
                elif name.endswith(".docx"):
                    text = extract_docx(data)
                elif name.endswith(".txt"):
                    text = extract_txt(data)
                if text:
                    extracted_files.append({
                        "name": safe_name,
                        "text": text,
                        "content": data,
                        "content_hash": compute_content_hash(data),
                        "type": name.split('.')[-1]
                    })
    except Exception as e:
        st.error(f"ZIP extraction error: {e}")
    return extracted_files
