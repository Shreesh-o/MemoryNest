"""Input validation for uploads and user data."""

from __future__ import annotations

import os
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

# Threshold: if more than this fraction of bytes are control characters
# (0x00-0x1F, 0x7F except tab 0x09, newline 0x0A, carriage return 0x0D),
# the file is considered binary.
_BINARY_RATIO_THRESHOLD = 0.3


def _is_likely_binary(file_bytes: bytes) -> bool:
    """Heuristically determine if bytes are binary (not plain text)."""
    if not file_bytes:
        return True
    # Count bytes that are control characters (except tab, newline, CR)
    control = 0
    for b in file_bytes:
        if b in (0x09, 0x0A, 0x0D):
            continue  # tab, newline, carriage return are valid in text
        if b <= 0x1F or b == 0x7F:
            control += 1
    ratio = control / len(file_bytes)
    return ratio > _BINARY_RATIO_THRESHOLD


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
    """Try to decode file_bytes as text. Returns decoded text or None."""
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            text = file_bytes.decode(encoding)
            # For utf-16, strip the BOM if present
            if encoding in ("utf-16", "utf-16-le", "utf-16-be") and text.startswith("\ufeff"):
                text = text[1:]
            return text
        except (UnicodeError, UnicodeDecodeError):
            continue
    return None


def validate_file_content(file_bytes: bytes, filename: str = "") -> Tuple[bool, str, str]:
    """Check file content. Returns (ok, reason, detected_type).

    Policy:
    1. Always check magic bytes first (handles PDF, PNG, JPEG, DOCX etc.).
    2. If magic bytes identify a known type, return it.
    3. If magic bytes are None (e.g. plain text without distinctive headers):
       - If the file has a .txt extension, try to decode as text.
       - If decoding succeeds and the content is not clearly binary, accept as txt.
       - Otherwise reject.
    4. If magic bytes are None and extension is not .txt, reject.
    """
    ext = Path(filename).suffix.lower() if filename else ""

    # --- Step 1: Magic-byte detection for known binary types ---
    kind = __import__("filetype").guess(file_bytes)
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
    # If the file has a .txt extension, try text decoding
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
            # Empty text after stripping BOM
            return False, "File is empty", ""
        # Text decoding failed
        return False, "Could not decode file as text.", ""

    # --- Step 3: No magic bytes and not .txt ---
    return False, "Could not determine file type from content", ""


def validate_size(size_bytes: int, max_size_bytes: int) -> Tuple[bool, str]:
    if size_bytes <= 0:
        return False, "File is empty"
    if size_bytes > max_size_bytes:
        return False, f"File too large ({size_bytes / 1e6:.1f} MB, limit {max_size_bytes / 1e6:.0f} MB)"
    return True, ""


def file_type_for(filename: str) -> str:
    return ALLOWED_EXTENSIONS[Path(filename).suffix.lower()]