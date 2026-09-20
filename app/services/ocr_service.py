"""OCR for images via Tesseract (pytesseract)."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

_tesseract_warned = False


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def ocr_image(image_path: str | Path) -> str:
    """Run OCR on an image file and return the extracted text (may be empty)."""
    global _tesseract_warned
    if not tesseract_available():
        if not _tesseract_warned:
            _tesseract_warned = True
        raise RuntimeError(
            "tesseract binary not found. Install with: pacman -S tesseract tesseract-data-eng"
        )

    import pytesseract

    path = Path(image_path)
    with Image.open(path) as img:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        text = pytesseract.image_to_string(img)
    return text or ""
