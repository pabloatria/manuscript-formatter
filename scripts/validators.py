"""Validate a manuscript against a journal config: word counts, structure."""
from pathlib import Path
from docx import Document

from .docx_helpers import read_headings, map_headings_to_canonical


def _count_words(text: str) -> int:
    """Whitespace-split word count, dropping empty fragments."""
    return len([w for w in text.split() if w.strip()])


def _section_text_blocks(doc, headings_idx: list[int]) -> list[list[str]]:
    """Group non-heading paragraphs into runs.

    Returns one block per heading, in document order. If the document has
    body text BEFORE the first heading, that prose is captured as a leading
    pseudo-block (returned as the FIRST element). The caller can detect
    this case by comparing returned-list-length to len(headings_idx).
    """
    paras = doc.paragraphs
    blocks: list[list[str]] = []

    # Leading pseudo-block: body paragraphs before the first heading
    if not headings_idx:
        # No headings at all: everything is the pseudo-block
        block = [p.text for p in paras
                 if not (p.style.name or "").startswith("Heading ")]
        if block:
            blocks.append(block)
        return blocks

    if headings_idx[0] > 0:
        block = []
        for j in range(0, headings_idx[0]):
            style = paras[j].style.name or ""
            if not style.startswith("Heading "):
                block.append(paras[j].text)
        if block:
            blocks.append(block)

    bounds = headings_idx + [len(paras)]
    for i in range(len(bounds) - 1):
        start, end = bounds[i] + 1, bounds[i + 1]
        block = []
        for j in range(start, end):
            style = paras[j].style.name or ""
            if not style.startswith("Heading "):
                block.append(paras[j].text)
        blocks.append(block)
    return blocks


def validate_manuscript(docx_path: Path, journal_cfg: dict) -> dict:
    """Return a structured validation report for `docx_path` against the
    given journal config.

    Report shape:
        {
            "sections": [
                {"canonical": str|None, "original_heading": str,
                 "word_count": int, "limit": int|None, "over_limit": bool},
                ...  # one entry per heading in document order
            ],
            "missing_required": [
                {"canonical": str, "display": str},  # required sections not seen
                ...
            ],
            "total_word_count": int,
            "total_word_limit": int|None,
            "total_over_limit": bool,
        }
    """
    doc = Document(docx_path)
    headings = read_headings(docx_path)
    mapped = map_headings_to_canonical(headings, journal_cfg["sections"])
    blocks = _section_text_blocks(doc, [h.paragraph_index for h in headings])

    sections_report: list[dict] = []
    seen_canons: set[str] = set()

    # Handle the leading pseudo-block (prose before the first heading)
    pseudo_blocks: list[list[str]] = []
    if len(blocks) > len(mapped):
        pseudo_blocks = blocks[: len(blocks) - len(mapped)]
        blocks = blocks[len(blocks) - len(mapped):]

    for pb in pseudo_blocks:
        wc = sum(_count_words(t) for t in pb)
        if wc > 0:
            sections_report.append({
                "canonical": None,
                "original_heading": "(before first heading)",
                "word_count": wc,
                "limit": None,
                "over_limit": False,
            })

    for h, block in zip(mapped, blocks):
        wc = sum(_count_words(t) for t in block)
        # Per-section limit
        cfg_for_section = next(
            (s for s in journal_cfg["sections"] if s["canonical"] == h.canonical),
            None,
        )
        limit = cfg_for_section["word_limit"] if cfg_for_section else None
        # Abstract uses its own block in the YAML (with structured/unstructured
        # info). If we landed on the abstract canonical, prefer that limit.
        if h.canonical == "abstract":
            abs_limit = journal_cfg.get("abstract", {}).get("word_limit")
            if abs_limit is not None:
                limit = abs_limit

        over = (limit is not None) and (wc > limit)
        sections_report.append({
            "canonical": h.canonical,
            "original_heading": h.original_text,
            "word_count": wc,
            "limit": limit,
            "over_limit": over,
        })
        if h.canonical is not None:
            seen_canons.add(h.canonical)

    # Required-section check
    # Default to required=True when the YAML omits the key — safer for
    # hand-authored configs (a forgotten `required: true` line should NOT
    # silently make the section optional).
    required = [s for s in journal_cfg["sections"] if s.get("required", True)]
    missing = [
        {"canonical": s["canonical"], "display": s.get("display", s["canonical"])}
        for s in required
        if s["canonical"] not in seen_canons
    ]

    # Total word count
    # Most journals exclude abstract, references, and acknowledgments from
    # the main-text total word limit. Hardcoded for v1; Task 16 may move
    # this into per-journal config (count_in_total: bool) if any journal
    # disagrees.
    EXCLUDED_FROM_TOTAL = {"abstract", "references", "acknowledgments"}
    total_wc = sum(
        r["word_count"] for r in sections_report
        if r["canonical"] not in EXCLUDED_FROM_TOTAL
    )
    total_limit = journal_cfg.get("total_word_limit")
    total_over = (total_limit is not None) and (total_wc > total_limit)

    return {
        "sections": sections_report,
        "missing_required": missing,
        "total_word_count": total_wc,
        "total_word_limit": total_limit,
        "total_over_limit": total_over,
    }
