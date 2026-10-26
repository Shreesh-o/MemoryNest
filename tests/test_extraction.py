"""Tests for text extraction (PDF/DOCX/TXT) and OCR on generated samples."""

from __future__ import annotations

import pytest

from app.services import extraction_service, ocr_service


def test_extract_pdf(sample_pdf):
    text = extraction_service.extract_text(sample_pdf, "pdf")
    assert "Quarterly Sales Report" in text
    assert "$1.2M" in text
    assert "October 15, 2026" in text


def test_extract_docx(sample_docx):
    text = extraction_service.extract_text(sample_docx, "docx")
    assert "Project Notes" in text
    assert "March 3, 2027" in text
    assert "$50,000" in text
    # table content should be present
    assert "Server" in text and "$10,000" in text


def test_extract_txt(sample_txt):
    text = extraction_service.extract_text(sample_txt, "txt")
    assert "Dentist appointment" in text
    assert "passport" in text


def test_extract_unknown_type(tmp_path):
    p = tmp_path / "x.bin"
    p.write_text("hi")
    with pytest.raises(ValueError):
        extraction_service.extract_text(p, "bin")


def test_extract_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        extraction_service.extract_text(str(tmp_path / "nope.txt"), "txt")


def test_extract_empty_txt(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("   \n  ")
    with pytest.raises(RuntimeError):
        extraction_service.extract_text(p, "txt")


def test_tesseract_available():
    assert ocr_service.tesseract_available()


def test_ocr_image(sample_image):
    text = ocr_service.ocr_image(sample_image)
    assert text, "OCR returned no text"
    lowered = text.lower()
    assert "meeting" in lowered
    # The date should be OCR'd; allow loose matching.
    assert "2027" in lowered or "20" in lowered


def test_extract_routes_image_to_ocr(sample_image):
    text = extraction_service.extract_text(sample_image, "image")
    assert "meeting" in text.lower()


def test_extract_pdf_ocr_fallback(tmp_path):
    """Test OCR fallback for image-only PDF (scanned PDF)."""
    from PIL import Image, ImageDraw, ImageFont
    import pymupdf as fitz

    # Create an image with text
    img = Image.new("RGB", (800, 400), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=32)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((50, 50), "Scanned document", fill="black", font=font)
    draw.text((50, 120), "Invoice #INV-2026-001", fill="black", font=font)
    draw.text((50, 190), "Date: 15 October 2026", fill="black", font=font)
    draw.text((50, 260), "Amount: $1,250.00", fill="black", font=font)

    # Save as PNG first
    img_path = tmp_path / "invoice.png"
    img.save(str(img_path))

    # Create PDF with the image (no text layer)
    pdf_path = tmp_path / "scanned_invoice.pdf"
    doc = fitz.open()
    page = doc.new_page(width=800, height=400)
    page.insert_image(page.rect, filename=str(img_path))
    doc.save(str(pdf_path))
    doc.close()

    # Extract text - should use OCR fallback
    text = extraction_service.extract_text(pdf_path, "pdf")
    assert "Scanned document" in text
    assert "INV-2026-001" in text or "2026" in text
    assert "15 October 2026" in text or "October" in text
    assert "1250" in text or "1,250" in text or "1250.00" in text


def test_sanitize_html():
    from app.services.text_cache_service import sanitize_html

    sample_html = """
    <p>Document content with <a href="https://example.com" target="_blank">link</a></p>
    <p><img src="data:image/png;base64,iVBORw0KGgo=" alt="test"></p>
    <script>alert('xss')</script>
    """
    clean = sanitize_html(sample_html)
    assert "<script>" not in clean
    assert "https://example.com" in clean
    assert 'rel="noopener noreferrer"' in clean
    assert "data:image/png" in clean
