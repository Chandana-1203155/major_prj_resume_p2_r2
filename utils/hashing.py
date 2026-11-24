"""Content/resume hashing helpers."""

import hashlib


def get_resume_hash(text):
    return hashlib.md5(text.encode()).hexdigest()


def compute_content_hash(content_bytes):
    """Hash of the raw file bytes. Used instead of filename to detect
    duplicate resumes — so 'John_Doe.pdf' and 'John_Doe_copy.pdf' with the
    exact same bytes are recognized as the same resume, and two totally
    different resumes that happen to share a filename are not merged."""
    return hashlib.sha256(content_bytes).hexdigest()
