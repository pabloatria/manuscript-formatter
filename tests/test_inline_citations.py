# tests/test_inline_citations.py
from pathlib import Path
import pytest

from scripts.references import load_references, render_inline_citations

FIXT = Path(__file__).resolve().parent / "fixtures"
CSL = (Path(__file__).resolve().parent.parent / "scripts" / "csl"
       / "journal-of-prosthetic-dentistry.csl")


def test_inline_single_citation_returns_number_only():
    """Vancouver-superscript style: a single in-text cite should render as
    the citation number, not the author family name."""
    refs = load_references(FIXT / "sample_zotero.json")
    out = render_inline_citations([["smith2024"]], refs, CSL)
    assert len(out) == 1
    # Vancouver-superscript output is the number alone (or wrapped in
    # superscript markup the formatter renders as plain text).
    assert "1" in out[0]
    assert "Smith" not in out[0]


def test_inline_multi_citation_groups_produce_separate_outputs():
    refs = load_references(FIXT / "sample_zotero.json")
    out = render_inline_citations([["smith2024"], ["lee2023"]], refs, CSL)
    assert len(out) == 2
    # Each group renders independently
    assert out[0] != out[1]


def test_inline_grouped_citations_render_compactly():
    """Two ids in one citation group should produce one combined inline
    citation (e.g., '1,2' or '1-2'), not two separate strings."""
    refs = load_references(FIXT / "sample_zotero.json")
    out = render_inline_citations([["smith2024", "lee2023"]], refs, CSL)
    assert len(out) == 1
    # Both numbers should appear in the single rendered string
    rendered = out[0]
    assert "1" in rendered and "2" in rendered


def test_inline_empty_groups_returns_empty():
    refs = load_references(FIXT / "sample_zotero.json")
    assert render_inline_citations([], refs, CSL) == []


def test_inline_unknown_id_raises_or_renders_marker():
    """If a citation group references an id not in items, citeproc-py
    will produce a '???' marker. Confirm the function doesn't crash —
    the caller should detect '???' in the report."""
    refs = load_references(FIXT / "sample_zotero.json")
    out = render_inline_citations([["does-not-exist"]], refs, CSL)
    assert len(out) == 1
    # citeproc-py renders unknown citations as "???" or similar marker
    # — we just want to confirm we got a string back, not an exception.
    assert isinstance(out[0], str)
