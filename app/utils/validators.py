"""Input validation for uploads and user data."""

from __future__ import annotations

import filetype
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

# Magic bytes signatures for allowed file types
ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
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


def validate_file_content(file_bytes: bytes) -> Tuple[bool, str, str]:
    """Check file content via magic bytes. Returns (ok, reason, detected_type)."""
    kind = filetype.guess(file_bytes)
    if kind is None:
        return False, "Could not determine file type from content", ""
    mime = kind.mime
    if mime not in ALLOWED_MIME_TYPES:
        return False, f"File type '{mime}' not allowed. Allowed: PDF, DOCX, TXT, PNG, JPG, TIFF, BMP", ""
    return True, "", ALLOWED_MIME_TYPES[mime]


def validate_size(size_bytes: int, max_size_bytes: int) -> Tuple[bool, str]:
    if size_bytes <= 0:
        return False, "File is empty"
    if size_bytes > max_size_bytes:
        return False, f"File too large ({size_bytes / 1e6:.1f} MB, limit {max_size_bytes / 1e6:.0f} MB)"
    return True, ""


def file_type_for(filename: str) -> str:
    return ALLOWED_EXTENSIONS[Path(filename).suffix.lower()]