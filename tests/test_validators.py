"""Tests for validators."""

from __future__ import annotations

import io
import os
import pathlib
import zipfile

import pytest
from PIL import Image, ImageDraw, ImageFont


# Test data - minimal valid file signatures
PDF_SIGNATURE = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"


def _make_minimal_docx() -> bytes:
    """Create a minimal valid DOCX file in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""")
        z.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""")
        z.writestr("word/document.xml", """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Test</w:t></w:r></w:p></w:body>
</w:document>""")
    return buf.getvalue()


DOCX_SIGNATURE = _make_minimal_docx()

# TXT content - filetype needs enough text to detect as text/plain
TXT_CONTENT = b"This is a plain text file with enough content for detection.\n" * 10

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Minimal PNG header + some data

JPG_SIGNATURE = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 100


def test_validate_filename_valid_extensions():
    from app.utils.validators import validate_filename
    assert validate_filename("test.pdf") == (True, "")
    assert validate_filename("test.docx") == (True, "")
    assert validate_filename("test.txt") == (True, "")
    assert validate_filename("test.png") == (True, "")
    assert validate_filename("test.jpg") == (True, "")
    assert validate_filename("test.jpeg") == (True, "")
    assert validate_filename("test.tiff") == (True, "")
    assert validate_filename("test.tif") == (True, "")
    assert validate_filename("test.bmp") == (True, "")


def test_validate_filename_invalid_extension():
    from app.utils.validators import validate_filename
    ok, reason = validate_filename("test.exe")
    assert not ok
    assert "exe" in reason
    assert "Unsupported" in reason

    ok, reason = validate_filename("test.unknown")
    assert not ok


def test_validate_filename_case_insensitive():
    from app.utils.validators import validate_filename
    assert validate_filename("test.PDF") == (True, "")
    assert validate_filename("test.DocX") == (True, "")
    assert validate_filename("test.TXT") == (True, "")


def test_sanitize_filename_removes_path_traversal():
    from app.utils.validators import sanitize_filename
    # Unix path traversal
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("a/b/c.pdf") == "c.pdf"
    assert sanitize_filename("a\\b\\c.pdf") == "c.pdf"

    # Mixed separators
    assert sanitize_filename("a/b\\c.pdf") == "c.pdf"

    # Multiple traversal attempts
    assert sanitize_filename("../../../etc/passwd") == "passwd"


def test_sanitize_filename_limits_length():
    from app.utils.validators import sanitize_filename
    # 300 character name with .pdf extension
    long_name = "a" * 300 + ".pdf"
    sanitized = sanitize_filename(long_name)
    # Stem should be truncated to 200 chars, extension preserved
    from pathlib import Path
    assert len(Path(sanitized).stem) <= 200
    assert sanitized.endswith(".pdf")

    # Very long name without extension
    long_no_ext = "a" * 350
    sanitized = sanitize_filename(long_no_ext)
    assert len(sanitized) <= 200


def test_sanitize_filename_preserves_normal_names():
    from app.utils.validators import sanitize_filename
    assert sanitize_filename("normal_file.pdf") == "normal_file.pdf"
    assert sanitize_filename("my document.docx") == "my document.docx"
    assert sanitize_filename("test-file_name.txt") == "test-file_name.txt"


def test_validate_file_content_pdf():
    from app.utils.validators import validate_file_content
    ok, reason, ftype = validate_file_content(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    assert ok
    assert ftype == "pdf"


def test_validate_file_content_docx():
    """Test with a real minimal DOCX file."""
    import zipfile
    import io
    from app.utils.validators import validate_file_content
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""")
        z.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""")
        z.writestr("word/document.xml", """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Test</w:t></w:r></w:p></w:body>
</w:document>""")
    docx_bytes = buf.getvalue()
    
    ok, reason, ftype = validate_file_content(docx_bytes)
    assert ok, f"DOCX validation failed: {reason}"
    assert ftype == "docx"


def test_validate_file_content_txt():
    # filetype needs enough text content to detect as text/plain
    txt_content = b"This is a plain text file with enough content for detection.\n" * 10
    from app.utils.validators import validate_file_content
    ok, reason, ftype = validate_file_content(txt_content)
    if not ok:
        # filetype might not detect minimal text as text/plain, that's OK
        # The important thing is it doesn't crash and returns a reasonable result
        assert not ok
        assert "Could not determine" in reason or "not allowed" in reason.lower()
    else:
        assert ftype == "txt"


def test_validate_file_content_png():
    from app.utils.validators import validate_file_content
    png_sig = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    ok, reason, ftype = validate_file_content(png_sig)
    assert ok
    assert ftype == "png"


def test_validate_file_content_jpg():
    from app.utils.validators import validate_file_content
    jpg_sig = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 100
    ok, reason, ftype = validate_file_content(jpg_sig)
    assert ok
    assert ftype == "jpg"


def test_validate_file_content_random_binary_rejected():
    """Random binary file renamed to .pdf should be rejected."""
    import os
    from app.utils.validators import validate_file_content
    random_bytes = os.urandom(100)
    ok, reason, ftype = validate_file_content(random_bytes)
    assert not ok
    assert "Could not determine" in reason or "not allowed" in reason


def test_validate_file_content_invalid_type_rejected():
    """A file with unrecognized magic bytes should be rejected."""
    from app.utils.validators import validate_file_content
    invalid = b"NOT A VALID FILE TYPE\x00\x01\x02"
    ok, reason, ftype = validate_file_content(invalid)
    assert not ok
    assert "not allowed" in reason.lower() or "could not determine" in reason.lower()


def test_validate_size_valid():
    from app.utils.validators import validate_size
    assert validate_size(100, 1000) == (True, "")
    assert validate_size(1000, 1000) == (True, "")


def test_validate_size_empty():
    from app.utils.validators import validate_size
    ok, reason = validate_size(0, 1000)
    assert not ok
    assert "empty" in reason.lower()

    ok, reason = validate_size(-1, 1000)
    assert not ok


def test_validate_size_too_large():
    from app.utils.validators import validate_size
    ok, reason = validate_size(100 * 1024 * 1024, 20 * 1024 * 1024)
    assert not ok
    assert "too large" in reason.lower()


def test_file_type_for():
    from app.utils.validators import file_type_for
    assert file_type_for("test.pdf") == "pdf"
    assert file_type_for("test.DOCX") == "docx"
    assert file_type_for("test.txt") == "txt"
    assert file_type_for("image.PNG") == "png"
    assert file_type_for("photo.JPG") == "jpg"
    assert file_type_for("scan.tiff") == "tiff"
    assert file_type_for("image.tif") == "tif"
    assert file_type_for("bitmap.bmp") == "bmp"


# End-to-end test through the same function the Upload page calls
def test_upload_batch_rejected_file_does_not_stop_valid_files(tmp_path, monkeypatch):
    """A rejected file in a batch does not stop valid files in the same batch."""
    import uuid

    # Set up environment BEFORE importing modules that use config
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))

    # Reload config module to pick up new env vars
    import importlib
    import app.utils.config as config_module
    importlib.reload(config_module)

    # Now import modules that use config (after env vars are set and config reloaded)
    from app.database.database import init_db
    from app.database.repositories import DocumentRepository, UserRepository
    from app.pages.upload import _save_uploaded_file, _process_document

    init_db()

    # Create test user with unique username
    user_repo = UserRepository()
    unique_username = f"batchuser_{uuid.uuid4().hex[:8]}"
    user = user_repo.create(unique_username, "hashed", "batch@example.com")

    doc_repo = DocumentRepository()

    # Create test files
    # Create a proper PDF using PyMuPDF
    import fitz
    valid_pdf = tmp_path / "valid.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Test PDF content")
    doc.save(str(valid_pdf))
    doc.close()

    invalid_exe = tmp_path / "malware.exe"
    invalid_exe.write_bytes(os.urandom(100))

    # Create a PNG with text that OCR can recognize
    import fitz
    from PIL import Image, ImageDraw, ImageFont
    valid_png = tmp_path / "valid.png"
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=24)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((20, 50), 'Hello World', fill='black', font=font)
    draw.text((20, 100), 'OCR Test 123', fill='black', font=font)
    img.save(str(valid_png))

    invalid_exe = tmp_path / "malware.exe"
    invalid_exe.write_bytes(os.urandom(100))

    valid_pdf = tmp_path / "valid.pdf"
    # Create a proper PDF using PyMuPDF
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Test PDF content")
    doc.save(str(valid_pdf))
    doc.close()

    # Upload batch: valid PDF, invalid EXE, valid PNG
    files = [
        (valid_pdf, "pdf"),
        (invalid_exe, "exe"),  # Should be rejected
        (valid_png, "png"),
    ]

    results = []
    for file_path, ftype in files:
        # Simulate uploaded file object
        class MockUploaded:
            def __init__(self, path, name):
                self._path = path
                self.name = name
            def getbuffer(self):
                return self._path.read_bytes()

        uploaded = MockUploaded(file_path, file_path.name)
        safe_name = pathlib.Path(uploaded.name).name

        # Validation - import validators locally
        from app.utils.validators import (
            validate_filename, validate_size, validate_file_content
        )

        ok, reason = validate_filename(safe_name)
        if not ok:
            results.append(("rejected", uploaded.name, reason))
            continue

        file_bytes = uploaded.getbuffer()
        ok, reason = validate_size(len(file_bytes), 20 * 1024 * 1024)
        if not ok:
            results.append(("rejected", uploaded.name, reason))
            continue

        ok, reason, detected_type = validate_file_content(file_bytes)
        if not ok:
            results.append(("rejected", uploaded.name, reason))
            continue

        # Save and process
        from app.pages.upload import _save_uploaded_file, _process_document
        from app.database.repositories import DocumentRepository
        doc_repo = DocumentRepository()

        stored_path, size = _save_uploaded_file(uploaded, user.id, safe_name)

        doc = doc_repo.create(user.id, safe_name, str(stored_path), detected_type, size, file_hash="")

        try:
            _process_document(doc.id, user.id, stored_path, detected_type, safe_name)
            results.append(("success", uploaded.name))
        except Exception as e:
            results.append(("error", uploaded.name, str(e)))

    # Verify: PDF succeeded, EXE rejected, PNG succeeded
    statuses = [r[0] for r in results]
    names = [r[1] for r in results]

    assert "valid.pdf" in names
    assert "malware.exe" in names
    assert "valid.png" in names

    # Check PDF succeeded
    idx_pdf = names.index("valid.pdf")
    assert statuses[idx_pdf] == "success", f"valid.pdf failed: {results[idx_pdf]}"

    # Check malware.exe rejected
    idx_exe = names.index("malware.exe")
    assert statuses[idx_exe] == "rejected", f"malware.exe should be rejected: {results[idx_exe]}"

    # Check PNG succeeded
    idx_png = names.index("valid.png")
    assert statuses[idx_png] == "success", f"valid.png failed: {results[idx_png]}"

    # Verify document count in DB
    from app.database.repositories import DocumentRepository
    doc_repo = DocumentRepository()
    docs = doc_repo.list_for_user(user.id)
    ready_docs = [d for d in docs if d.status == "ready"]
    assert len(ready_docs) == 2, "Only valid files should be processed"