"""Text extraction from PDF / DOCX / TXT / images (OCR routing)."""

from __future__ import annotations

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
    with fitz.open(path) as doc:
        for page in doc:
            parts.append(page.get_text("text"))
    text = "\n".join(parts).strip()
    if not text:
        # Scanned PDF without a text layer — flag it clearly.
        raise RuntimeError(
            "PDF contains no extractable text layer. If this is a scanned PDF, "
            "save the pages as images and upload them instead (OCR will apply)."
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
