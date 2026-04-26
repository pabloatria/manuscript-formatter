# tests/test_inline_citations.py
from pathlib import Path
import pytest

from scripts.references import load_references, render_inline_citations

FIXT = Path(__file__).resolve().parent / "fixtures"
CSL = (Path(__file__).resolve().parent.parent / "scripts" / "csl"
       / "journal-of-prosthetic-dentistry.csl")


def test_inline_single_citation_returns_number_only():
    """Vancouver-superscript style: a single in-text cite is the number."""
    refs = load_references(FIXT / "sample_zotero.json")
    out = render_inline_citations([["smith2024"]], refs, CSL)
    assert out == ["1"]


def test_inline_multi_citation_groups_assign_distinct_numbers():
    """Two separate citation points get sequential numbers per the CSL's
    citation-sequence numbering."""
    refs = load_references(FIXT / "sample_zotero.json")
    out = render_inline_citations([["smith2024"], ["lee2023"]], refs, CSL)
    assert out == ["1", "2"]


def test_inline_grouped_citations_render_compactly():
    """Two ids in one citation group render as a single comma-joined
    string."""
    refs = load_references(FIXT / "sample_zotero.json")
    out = render_inline_citations([["smith2024", "lee2023"]], refs, CSL)
    assert out == ["1,2"]


def test_inline_empty_groups_returns_empty():
    refs = load_references(FIXT / "sample_zotero.json")
    assert render_inline_citations([], refs, CSL) == []


def test_inline_unknown_id_renders_without_raising():
    """citeproc-py renders unknown ids as `<cite-key>?` rather than
    raising. Confirm we get a string back (callers should use
    collect_unresolved to detect, not string-match)."""
    refs = load_references(FIXT / "sample_zotero.json")
    out = render_inline_citations([["does-not-exist"]], refs, CSL)
    assert len(out) == 1
    assert isinstance(out[0], str)


def test_inline_collect_unresolved_returns_tuple():
    """When collect_unresolved=True, the function returns a (rendered,
    unresolved) tuple. Unresolved ids must include 'does-not-exist'."""
    refs = load_references(FIXT / "sample_zotero.json")
    rendered, unresolved = render_inline_citations(
        [["smith2024"], ["does-not-exist"]], refs, CSL,
        collect_unresolved=True,
    )
    assert len(rendered) == 2
    assert "does-not-exist" in unresolved


def test_inline_collect_unresolved_is_empty_when_all_resolve():
    refs = load_references(FIXT / "sample_zotero.json")
    rendered, unresolved = render_inline_citations(
        [["smith2024"]], refs, CSL, collect_unresolved=True,
    )
    assert rendered == ["1"]
    assert unresolved == []


def test_inline_registration_order_drives_numbering():
    """Register lee2023 first, then smith2024; assert lee gets '1'."""
    refs = load_references(FIXT / "sample_zotero.json")
    out = render_inline_citations(
        [["lee2023"], ["smith2024"]], refs, CSL,
    )
    assert out == ["1", "2"]
