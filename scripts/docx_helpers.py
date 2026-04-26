"""python-docx helpers: heading detection, paragraph manipulation."""
from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph

HEADING_STYLE_PREFIX = "Heading "

def _heading_level(p: Paragraph) -> int | None:
    """Return 1..9 if the paragraph uses a Heading N style; else None."""
    style = (p.style.name or "")
    if style.startswith(HEADING_STYLE_PREFIX):
        try:
            return int(style[len(HEADING_STYLE_PREFIX):])
        except ValueError:
            return None
    return None

def read_headings(docx_path: Path) -> list[dict]:
    """Return [{level, text, paragraph_index}, ...] for every heading paragraph."""
    doc = Document(str(docx_path))
    out = []
    for idx, p in enumerate(doc.paragraphs):
        lv = _heading_level(p)
        if lv is not None:
            out.append({"level": lv, "text": p.text.strip(), "paragraph_index": idx})
    return out
