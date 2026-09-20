"""Shared fixtures that generate real sample files (PDF/DOCX/TXT/image)."""

from __future__ import annotations

import pytest


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
