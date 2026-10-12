"""Shared pytest fixtures for MemoryNest.

Every test runs against per-test temp storage (SQLite, Chroma, uploads,
audio) so the suite can never touch the real data/ folder.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Guard: fail if any test touches the real data/ folder
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def _check_real_data_access(path: Path) -> None:
    try:
        resolved = path.resolve()
    except (OSError, ValueError):
        return
    if resolved == DATA_DIR or DATA_DIR in resolved.parents:
        pytest.fail(f"Test attempted to access real data directory: {resolved}")


@pytest.fixture(autouse=True)
def _check_real_data_access_during_test():
    yield
    import app.utils.config as config_module
    for attr in ("DB_PATH", "CHROMA_DIR", "UPLOAD_DIR", "AUDIO_DIR"):
        _check_real_data_access(Path(getattr(config_module, attr)))


@pytest.fixture(autouse=True)
def test_storage(tmp_path, monkeypatch):
    """Redirect DB, Chroma, uploads, and audio to per-test temp dirs.

    Uses the same mechanism as the app: environment variables + config
    reload, so every call-time path resolution (get_connection,
    upload._get_config, config.ensure_dirs, ...) lands in tmp_path.
    Also initializes a fresh database for each test.
    """
    monkeypatch.setenv("DB_PATH", str(tmp_path / "memorynest.db"))
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("AUDIO_DIR", str(tmp_path / "audio"))
    monkeypatch.setenv("MOCK_LLM", "1")

    import importlib
    import app.utils.config as config_module
    importlib.reload(config_module)

    from app.database.database import init_db
    init_db()

    # VectorService captures CHROMA_DIR when its singleton is first created;
    # point it at this test's dir and reset the singleton.
    from app.services import vector_service
    monkeypatch.setattr(vector_service, "CHROMA_DIR", config_module.CHROMA_DIR)
    monkeypatch.setattr(vector_service.VectorService, "_instance", None)

    yield


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