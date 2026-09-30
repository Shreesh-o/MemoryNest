"""Text extraction from PDF / DOCX / TXT / images (OCR routing)."""

from __future__ import annotations

import io
from pathlib import Path

from app.services import ocr_service


def extract_text(stored_path: str | Path, file_type: str) -> str:
    """Extract text from a stored file.

    file_type is one of: pdf, docx, txt, image.
    Raises ValueError for unknown types and RuntimeError for unreadable files.
    """
    path = Path(stored_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ft = (file_type or "").lower()
    if ft == "pdf":
        return _extract_pdf(path)
    if ft == "docx":
        return _extract_docx(path)
    if ft == "txt":
        return _extract_txt(path)
    if ft == "image":
        return ocr_service.ocr_image(path)
    raise ValueError(f"Unsupported file type: {file_type}")


def _extract_pdf(path: Path) -> str:
    import pymupdf as fitz  # PyMuPDF

    parts = []
    tesseract_available = False
    try:
        import pytesseract
        from PIL import Image
        import shutil
        if shutil.which("tesseract") is not None:
            tesseract_available = True
    except ImportError:
        tesseract_available = False

    with fitz.open(path) as doc:
        for page_num, page in enumerate(doc):
            # Try to extract text from page
            page_text = page.get_text("text").strip()

            # If page has very little text (threshold: < 50 chars), try OCR
            if len(page_text) < 50 and tesseract_available:
                try:
                    # Render page to image at 300 DPI for good OCR quality
                    pix = page.get_pixmap(dpi=300)
                    img_data = pix.tobytes("png")
                    from PIL import Image
                    img = Image.open(io.BytesIO(img_data))
                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                    import pytesseract
                    ocr_text = pytesseract.image_to_string(img)
                    if ocr_text.strip():
                        parts.append(f"[Page {page_num + 1} OCR]\n{ocr_text.strip()}")
                        continue
                except Exception:
                    # OCR failed, fall back to whatever text we got
                    pass

            if page_text:
                parts.append(f"[Page {page_num + 1}]\n{page_text}")

    text = "\n\n".join(parts).strip()
    if not text:
        if not tesseract_available:
            raise RuntimeError(
                "PDF contains no extractable text and Tesseract OCR is not available. "
                "Install Tesseract: pacman -S tesseract tesseract-data-eng"
            )
        raise RuntimeError(
            "PDF contains no extractable text. If this is a scanned PDF, "
            "ensure Tesseract is installed for OCR fallback."
        )
    return text


def _extract_docx(path: Path) -> str:
    import docx

    d = docx.Document(str(path))
    parts = [p.text for p in d.paragraphs if p.text.strip()]
    for table in d.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("DOCX contains no text.")
    return text


def _extract_txt(path: Path) -> str:
    import io
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except (UnicodeError, UnicodeDecodeError):
            continue
    else:
        raise RuntimeError("Could not decode text file in any supported encoding.")
    text = text.strip()
    if not text:
        raise RuntimeError("Text file is empty.")
    return text