"""Step 2: Read text out of many document formats.

Supported: .pdf, .docx, .doc, .rtf, .odt, .html/.htm, .md, .txt
"""

import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

SUPPORTED_EXTENSIONS = ["pdf", "docx", "doc", "rtf", "odt", "html", "htm", "md", "txt"]


class DocumentError(ValueError):
    """Raised when a document can't be read. The message is safe to show users."""


def extract_text(file_path: str) -> str:
    """Read a file from disk and return its text."""
    path = Path(file_path)
    return extract_text_from_bytes(path.read_bytes(), path.name)


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """Return the text of a document given its raw bytes and file name."""
    ext = Path(filename).suffix.lower().lstrip(".")
    readers = {
        "pdf": _read_pdf,
        "docx": _read_docx,
        "doc": _read_doc,
        "rtf": _read_rtf,
        "odt": _read_odt,
        "html": _read_html,
        "htm": _read_html,
        "md": _read_plain,
        "txt": _read_plain,
    }
    if ext not in readers:
        raise DocumentError(
            f"Unsupported file type '.{ext}'. Supported: "
            + ", ".join("." + e for e in SUPPORTED_EXTENSIONS)
        )
    try:
        text = readers[ext](data)
    except DocumentError:
        raise
    except Exception as exc:  # corrupted or mislabeled file
        raise DocumentError(f"Could not read '{filename}': {exc}") from exc

    text = _clean(text)
    if not text:
        hint = " It may be a scanned image; try a text-based PDF." if ext == "pdf" else ""
        raise DocumentError(f"No text found in '{filename}'.{hint}")
    return text


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


# ---------- individual readers ----------

def _read_plain(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _read_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs]
    # Many resumes put content in tables - read those too.
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(parts)


def _read_rtf(data: bytes) -> str:
    from striprtf.striprtf import rtf_to_text

    return rtf_to_text(data.decode("latin-1"))


def _read_odt(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = ElementTree.fromstring(z.read("content.xml"))
    text_ns = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
    lines = []
    for el in root.iter():
        if el.tag in (f"{text_ns}p", f"{text_ns}h"):
            lines.append("".join(el.itertext()))
    return "\n".join(lines)


def _read_html(data: bytes) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(data, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text("\n")


def _read_doc(data: bytes) -> str:
    """Old Word 97-2003 .doc files.

    Best option: convert with LibreOffice if installed. Otherwise fall back to
    pulling readable text runs out of the binary 'WordDocument' stream.
    """
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "input.doc"
            src.write_bytes(data)
            subprocess.run(
                [soffice, "--headless", "--convert-to", "txt:Text", "--outdir", tmp, str(src)],
                capture_output=True, timeout=60, check=False,
            )
            out = Path(tmp) / "input.txt"
            if out.exists():
                return _read_plain(out.read_bytes())

    import olefile

    if not olefile.isOleFile(io.BytesIO(data)):
        raise DocumentError("This .doc file is not a valid Word 97-2003 document.")
    with olefile.OleFileIO(io.BytesIO(data)) as ole:
        if not ole.exists("WordDocument"):
            raise DocumentError("This .doc file has no Word text stream.")
        stream = ole.openstream("WordDocument").read()
        flags = int.from_bytes(stream[0x0A:0x0C], "little")
        table_name = "1Table" if flags & 0x0200 else "0Table"
        table = ole.openstream(table_name).read() if ole.exists(table_name) else b""

    try:
        return _doc_text_from_piece_table(stream, table)
    except Exception:
        return _doc_text_heuristic(stream)


def _doc_text_from_piece_table(stream: bytes, table: bytes) -> str:
    """Read the main text using the Word 97 'piece table', which lists where
    each chunk of text lives and whether it is 1-byte or 2-byte encoded."""
    ccp_text = int.from_bytes(stream[0x4C:0x50], "little")
    fc_clx = int.from_bytes(stream[0x1A2:0x1A6], "little")
    lcb_clx = int.from_bytes(stream[0x1A6:0x1AA], "little")
    clx = table[fc_clx:fc_clx + lcb_clx]

    pos = 0
    while clx[pos] == 0x01:  # skip formatting entries (Prc)
        pos += 3 + int.from_bytes(clx[pos + 1:pos + 3], "little")
    if clx[pos] != 0x02:
        raise ValueError("piece table not found")
    lcb = int.from_bytes(clx[pos + 1:pos + 5], "little")
    plc = clx[pos + 5:pos + 5 + lcb]
    n = (lcb - 4) // 12
    cps = [int.from_bytes(plc[i * 4:i * 4 + 4], "little") for i in range(n + 1)]

    chunks = []
    for i in range(n):
        pcd = plc[(n + 1) * 4 + i * 8:(n + 1) * 4 + i * 8 + 8]
        fc = int.from_bytes(pcd[2:6], "little")
        count = cps[i + 1] - cps[i]
        if fc & 0x40000000:  # compressed: 1 byte per char
            start = (fc & ~0x40000000) // 2
            chunks.append(stream[start:start + count].decode("cp1252", errors="ignore"))
        else:
            chunks.append(stream[fc:fc + 2 * count].decode("utf-16-le", errors="ignore"))
    text = "".join(chunks)[:ccp_text]

    # Word control characters: cell/row marks, line breaks, field codes.
    text = text.replace("\x07", "\t").replace("\x0b", "\n").replace("\x0c", "\n")
    text = re.sub(r"\x13[^\x14\x15]*\x14?", "", text).replace("\x15", "")
    text = re.sub(r"[\x00-\x08\x0e-\x1f]", "", text)
    if not text.strip():
        raise ValueError("empty text")
    return text


def _doc_text_heuristic(stream: bytes) -> str:
    # Text is stored either as UTF-16 or as single-byte cp1252; try both and
    # keep whichever yields more readable text.
    readable = re.compile(r"[A-Za-z0-9À-ɏ\s.,;:()@+#/&%'\"-]{4,}")
    candidates = []
    for encoding in ("utf-16-le", "cp1252"):
        decoded = stream.decode(encoding, errors="ignore")
        runs = [r.strip() for r in readable.findall(decoded) if sum(c.isalpha() for c in r) >= 3]
        candidates.append("\n".join(runs))
    return max(candidates, key=lambda t: sum(c.isalpha() for c in t))
