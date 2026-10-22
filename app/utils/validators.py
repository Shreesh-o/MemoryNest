"""Input validation for uploads and user data."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Tuple

ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".png": "png",
    ".jpg": "jpg",
    ".jpeg": "jpg",
    ".tiff": "tiff",
    ".tif": "tif",
    ".bmp": "bmp",
}

# Magic bytes signatures for allowed binary file types
ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/tiff": "tiff",
    "image/bmp": "bmp",
}


def validate_filename(filename: str) -> Tuple[bool, str]:
    """Check extension is supported. Returns (ok, reason)."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return False, f"Unsupported file type '{ext}'. Allowed: {allowed}"
    return True, ""


def sanitize_filename(filename: str) -> str:
    """Sanitize filename: remove path separators, '..', limit length."""
    # Handle both Unix and Windows path separators
    name = filename.replace("\\", "/")
    # Get just the filename part (after last /)
    name = name.split("/")[-1]
    # Remove any remaining path traversal attempts
    name = name.replace("..", "")
    # Limit length (keep extension)
    stem = Path(name).stem
    suffix = Path(name).suffix
    if len(stem) > 200:
        stem = stem[:200]
    return f"{stem}{suffix}"


def _try_decode_text(file_bytes: bytes) -> str | None:
    """Try to decode file_bytes as text using multiple encodings (excluding latin-1).

    Returns decoded text with BOM stripped, or None if all fail.
    Order: utf-8-sig, utf-8, utf-16, cp1252.
    """
    file_bytes = bytes(file_bytes)
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252"):
        try:
            text = file_bytes.decode(encoding)
            # For utf-16, the BOM may be included; strip it
            if encoding in ("utf-16", "utf-16-le", "utf-16-be") and text.startswith("\ufeff"):
                text = text[1:]
            return text
        except (UnicodeError, UnicodeDecodeError):
            continue
    return None


def validate_file_content(file_bytes: bytes, filename: str = "") -> Tuple[bool, str, str]:
    """Check file content. Returns (ok, reason, detected_type).

    Policy:
    1. If filename has a known extension (.pdf, .docx, .txt, .png, .jpg, .tiff, .bmp),
       use filetype module magic-byte detection.
    2. If magic bytes identify a known type:
       - .txt extension + known binary type = disguise -> reject
       - known type + allowed extension -> accept
    3. If magic bytes are None (plain text without distinctive headers):
       - If filename has .txt extension: try text decoding. Accept if decoding succeeds
         and content has real text (not just whitespace). Otherwise reject.
       - If filename has no extension (empty string): always reject with "Could not determine
         file type from content" (this maintains backward compatibility with existing tests).
       - If filename has unknown extension: reject.
    4. Otherwise reject.

    Key fix for the bug: when filename has .txt extension, text decoding is attempted
    and content is accepted if it's valid text, regardless of whether the filename was
    originally correct or empty. The real fix is in the caller (upload.py) which now
    passes the original filename.
    """
    file_bytes = bytes(file_bytes)
    from filetype import guess as _guess_type

    ext = Path(filename).suffix.lower() if filename else ""

    # --- Step 1: Magic-byte detection using filetype module ---
    kind = _guess_type(file_bytes)
    if kind is not None:
        mime = kind.mime
        # If it's a known type AND the file has .txt extension, it's a binary disguise
        if ext == ".txt" and mime in ALLOWED_MIME_TYPES:
            # Binary file disguised as .txt - reject with clear message
            return False, f"File type '{mime}' not allowed. Allowed: PDF, DOCX, TXT, PNG, JPG, TIFF, BMP", ""
        # Known type and not .txt extension (or .txt but unknown mime)
        if mime in ALLOWED_MIME_TYPES:
            return True, "", ALLOWED_MIME_TYPES[mime]
        # Known type but not in allowed list
        return False, f"File type '{mime}' not allowed. Allowed: PDF, DOCX, TXT, PNG, JPG, TIFF, BMP", ""

    # --- Step 2: Magic bytes were None (plain text or unrecognized) ---
    # If filename has .txt extension: try text decoding
    if ext == ".txt":
        # Reject if contains NUL bytes (binary file disguised as .txt)
        if b"\x00" in file_bytes:
            return False, "File type 'txt' not allowed. Binary content detected.", ""
        # Try to decode as text
        text = _try_decode_text(file_bytes)
        if text is not None:
            # Accept if the decoded text has actual content (not just whitespace)
            if text.strip():
                return True, "", "txt"
            # Empty text
            return False, "File is empty", ""
        # Text decoding failed
        return False, "Could not decode file as text.", ""

    # --- Step 3: No magic bytes and not .txt (including empty filename) ---
    # For no filename or unknown extension, reject with standard message
    # This maintains backward compatibility with existing tests
    return False, "Could not determine file type from content", ""


def validate_size(size_bytes: int, max_size_bytes: int) -> Tuple[bool, str]:
    if size_bytes <= 0:
        return False, "File is empty"
    if size_bytes > max_size_bytes:
        return False, f"File too large ({size_bytes / 1e6:.1f} MB, limit {max_size_bytes / 1e6:.0f} MB)"
    return True, ""


def file_type_for(filename: str) -> str:
    return ALLOWED_EXTENSIONS[Path(filename).suffix.lower()]


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format. Returns (ok, reason)."""
    if not email or not isinstance(email, str):
        return False, "Email cannot be empty"
    cleaned = email.strip()
    if len(cleaned) > 254:
        return False, "Email too long (max 254 characters)"
    if " " in cleaned:
        return False, "Email cannot contain spaces"
    if ".." in cleaned:
        return False, "Invalid email address format"
    parts = cleaned.split("@")
    if len(parts) != 2:
        return False, "Invalid email address format"
    local_part, domain = parts
    if not local_part or not domain:
        return False, "Invalid email address format"
    if len(local_part) > 64:
        return False, "Email local part too long"
    if domain.startswith(".") or domain.endswith(".") or domain.startswith("-") or domain.endswith("-"):
        return False, "Invalid email domain"
    domain_parts = domain.split(".")
    if len(domain_parts) < 2:
        return False, "Invalid email domain format"
    for part in domain_parts:
        if not part or part.startswith("-") or part.endswith("-"):
            return False, "Invalid email domain format"
    if not domain_parts[-1].isalpha() or len(domain_parts[-1]) < 2:
        return False, "Invalid email top-level domain"
    if not _EMAIL_RE.match(cleaned):
        return False, "Invalid email address format"
    return True, ""

