"""Shared fixtures that generate real sample files (PDF/DOCX/TXT/image)."""

from __future__ import annotations

import os
import importlib
import tempfile
import shutil
from pathlib import Path

import pytest

import app.utils.config as config_module


# Configure test environment BEFORE any module imports
def pytest_configure(config):
    """Set up test environment before test collection."""
    # Create temporary directories for testing
    test_base = Path(tempfile.mkdtemp(prefix="memorynest_test_"))
    
    os.environ["DB_PATH"] = str(test_base / "memorynest.db")
    os.environ["CHROMA_DIR"] = str(test_base / "chroma")
    os.environ["UPLOAD_DIR"] = str(test_base / "uploads")
    os.environ["AUDIO_DIR"] = str(test_base / "audio")
    os.environ["MOCK_LLM"] = "1"  # Use mock LLM for tests
    
    # Reload config module to pick up new env vars
    importlib.reload(config_module)


def pytest_sessionfinish(session, exitstatus):
    """Clean up after all tests finish."""
    import app.utils.config as config_module
    if hasattr(config_module, '_cleanup'):
        config_module._cleanup()


# Guard: fail if any test touches the real data/ folder
REAL_DATA_DIR = Path("/home/shreesh/MemoryNest/data").resolve()
REAL_UPLOADS_DIR = REAL_DATA_DIR / "uploads"
REAL_CHROMA_DIR = REAL_DATA_DIR / "chroma"
REAL_DB_PATH = REAL_DATA_DIR / "memorynest.db"


# Pre-test check: fail immediately if test tries to use real data paths
def _check_real_data_access(path: Path):
    try:
        resolved = path.resolve()
        if REAL_DATA_DIR in resolved.parents or resolved == REAL_DATA_DIR:
            pytest.fail(f"Test attempted to access real data directory: {resolved}")
    except (OSError, ValueError):
        pass


# Per-test check: fail immediately if test tries to use real data paths
@pytest.fixture(autouse=True)
def _check_real_data_access_during_test():
    yield
    # Check after test runs if real data was modified
    import app.utils.config as config_module
    for attr in ("DB_PATH", "CHROMA_DIR", "UPLOAD_DIR", "AUDIO_DIR"):
        path = getattr(config_module, attr)
        _check_real_data_access(path)


# Session-scoped fixture: set up test environment BEFORE any module imports
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables and reload config before any tests run."""
    # Create temporary directories for testing
    import tempfile
    test_base = Path(tempfile.mkdtemp(prefix="memorynest_test_"))
    
    os.environ["DB_PATH"] = str(test_base / "memorynest.db")
    os.environ["CHROMA_DIR"] = str(test_base / "chroma")
    os.environ["UPLOAD_DIR"] = str(test_base / "uploads")
    os.environ["AUDIO_DIR"] = str(test_base / "audio")
    os.environ["MOCK_LLM"] = "1"  # Use mock LLM for tests
    
    # Reload config module to pick up new env vars
    import importlib
    import app.utils.config as config_module
    importlib.reload(config_module)
    
    yield
    
    # Cleanup temp directory after all tests
    import shutil
    shutil.rmtree(test_base, ignore_errors=True)


# Guard: fail if any test touches the real data/ folder
REAL_DATA_DIR = Path("/home/shreesh/MemoryNest/data").resolve()
REAL_UPLOADS_DIR = REAL_DATA_DIR / "uploads"
REAL_CHROMA_DIR = REAL_DATA_DIR / "chroma"
REAL_DB_PATH = REAL_DATA_DIR / "memorynest.db"


# Pre-test check: fail immediately if test tries to use real data paths
def _check_real_data_access(path: Path):
    try:
        resolved = path.resolve()
        if REAL_DATA_DIR in resolved.parents or resolved == REAL_DATA_DIR:
            pytest.fail(f"Test attempted to access real data directory: {resolved}")
    except (OSError, ValueError):
        pass


# Per-test check: fail immediately if test tries to use real data paths
@pytest.fixture(autouse=True)
def _check_real_data_access_during_test():
    yield
    # Check after test runs if real data was modified
    import app.utils.config as config_module
    for attr in ("DB_PATH", "CHROMA_DIR", "UPLOAD_DIR", "AUDIO_DIR"):
        path = getattr(config_module, attr)
        _check_real_data_access(path)


@pytest.fixture(scope="session")
def sample_pdf(tmp_path_factory) -> str:
    import fitz

    path = tmp_path_factory.mktemp("files") / "report.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Quarterly Sales Report\n\nTotal revenue was $1.2M, "
                              "up 12% from last quarter. The APAC region grew fastest.")
    page.insert_text((72, 200), "The board meeting is scheduled for October 15, 2026 "
                                "at 9:00 AM in the main conference room.")
    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.fixture(scope="session")
def sample_docx(tmp_path_factory) -> str:
    import docx

    path = tmp_path_factory.mktemp("files") / "notes.docx"
    d = docx.Document()
    d.add_heading("Project Notes", level=1)
    d.add_paragraph("The launch is planned for March 3, 2027.")
    d.add_paragraph("Budget: $50,000 for Q1 marketing.")
    table = d.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Item"
    table.cell(0, 1).text = "Cost"
    table.cell(1, 0).text = "Server"
    table.cell(1, 1).text = "$10,000"
    d.save(str(path))
    return str(path)


@pytest.fixture(scope="session")
def sample_txt(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("files") / "notes.txt"
    path.write_text(
        "Personal notes\n\n"
        "Dentist appointment on 2026-11-01 at noon.\n"
        "Remember to renew the passport before December 31, 2026.\n",
        encoding="utf-8",
    )
    return str(path)


@pytest.fixture(scope="session")
def sample_image(tmp_path_factory) -> str:
    from PIL import Image, ImageDraw, ImageFont

    path = tmp_path_factory.mktemp("files") / "letter.png"
    img = Image.new("RGB", (900, 300), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=36)
    except TypeError:  # older Pillow
        font = ImageFont.load_default()
    draw.text((20, 40), "Team sync meeting", fill="black", font=font)
    draw.text((20, 100), "Date: January 20 2027", fill="black", font=font)
    draw.text((20, 160), "Topic: roadmap review", fill="black", font=font)
    img.save(str(path))
    return str(path)