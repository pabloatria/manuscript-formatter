"""python-docx helpers: heading detection, paragraph manipulation."""
from dataclasses import dataclass
from pathlib import Path
import re

from docx import Document
from docx.text.paragraph import Paragraph

# Match exactly "Heading 1" through "Heading 9" — refuses "Heading 1 Char"
# (Word's auto-generated linked character style), "Heading 12", localized
# names like "Encabezado 1", and any non-Latin variants. We deliberately
# do NOT silently downgrade or guess at level — unrecognized headings
# return None and the caller sees them as body paragraphs.
_HEADING_RE = re.compile(r"^Heading ([1-9])$")


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    paragraph_index: int


def _heading_level(p: Paragraph) -> int | None:
    """Return 1..9 if the paragraph uses a Heading 1..9 style; else None.

    Tightens the previous startswith() check: rejects "Heading 1 Char" and
    "Heading 12" rather than relying on a bare-except to silently drop
    them.
    """
    style_name = getattr(p.style, "name", "") or ""
    m = _HEADING_RE.match(style_name)
    return int(m.group(1)) if m else None


def read_headings(docx_path: Path) -> list[Heading]:
    """Return the document's heading paragraphs in order.

    Each entry is a Heading dataclass with level (1..9), stripped text, and
    the absolute paragraph_index in `Document(docx_path).paragraphs`.
    """
    doc = Document(docx_path)
    out = []
    for idx, p in enumerate(doc.paragraphs):
        lv = _heading_level(p)
        if lv is not None:
            out.append(Heading(level=lv, text=p.text.strip(), paragraph_index=idx))
    return out
