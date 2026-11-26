import io
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ats_analyzer.parser import DocumentError, extract_text_from_bytes  # noqa: E402

TEXT = "Python developer skilled in Django"


def make_pdf() -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text=TEXT)
    return bytes(pdf.output())


def make_docx() -> bytes:
    from docx import Document

    doc = Document()
    doc.add_paragraph(TEXT)
    doc.add_table(rows=1, cols=1).cell(0, 0).text = "Table skill: Docker"
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_odt() -> bytes:
    content = (
        '<?xml version="1.0"?><office:document-content '
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
        f"<office:body><office:text><text:p>{TEXT}</text:p></office:text></office:body>"
        "</office:document-content>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("content.xml", content)
    return buf.getvalue()


@pytest.mark.parametrize(
    "filename,data",
    [
        ("resume.txt", TEXT.encode()),
        ("resume.md", f"# Resume\n{TEXT}".encode()),
        ("resume.html", f"<html><script>x()</script><p>{TEXT}</p></html>".encode()),
        ("resume.rtf", ("{\\rtf1\\ansi " + TEXT + "}").encode()),
        ("resume.odt", make_odt()),
        ("resume.docx", make_docx()),
        ("resume.pdf", make_pdf()),
    ],
)
def test_reads_format(filename, data):
    text = extract_text_from_bytes(data, filename)
    assert "Python developer" in text
    assert "x()" not in text  # scripts removed from HTML


def test_docx_tables_are_read():
    assert "Docker" in extract_text_from_bytes(make_docx(), "r.docx")


def test_unsupported_extension():
    with pytest.raises(DocumentError, match="Unsupported"):
        extract_text_from_bytes(b"abc", "resume.xyz")


def test_corrupt_file_gives_friendly_error():
    with pytest.raises(DocumentError):
        extract_text_from_bytes(b"not a real pdf", "resume.pdf")


def test_legacy_word_doc():
    data = (Path(__file__).parent / "fixtures" / "legacy_resume.doc").read_bytes()
    text = extract_text_from_bytes(data, "legacy_resume.doc")
    assert "Skills: Python, Django, PostgreSQL, Docker" in text
    assert "bjbj" not in text  # no binary junk
