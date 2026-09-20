"""Input validation for uploads and user data."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".tiff": "image",
    ".tif": "image",
    ".bmp": "image",
}

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


def validate_filename(filename: str) -> Tuple[bool, str]:
    """Check extension is supported. Returns (ok, reason)."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return False, f"Unsupported file type '{ext}'. Allowed: {allowed}"
    return True, ""


def validate_size(size_bytes: int) -> Tuple[bool, str]:
    if size_bytes <= 0:
        return False, "File is empty"
    if size_bytes > MAX_FILE_SIZE_BYTES:
        return False, f"File too large ({size_bytes / 1e6:.1f} MB, limit {MAX_FILE_SIZE_BYTES / 1e6:.0f} MB)"
    return True, ""


def file_type_for(filename: str) -> str:
    return ALLOWED_EXTENSIONS[Path(filename).suffix.lower()]
