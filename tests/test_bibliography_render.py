# tests/test_bibliography_render.py
from pathlib import Path
import pytest

from scripts.references import load_references, render_bibliography

FIXT = Path(__file__).resolve().parent / "fixtures"
CSL = (Path(__file__).resolve().parent.parent / "scripts" / "csl"
       / "journal-of-prosthetic-dentistry.csl")


def test_render_jpd_bibliography_returns_strings():
    refs = load_references(FIXT / "sample_zotero.json")
    rendered = render_bibliography(refs, CSL)
    assert len(rendered) == 2
    full = "\n".join(rendered)
    # Author and title should appear in the formatted output
    assert "Smith" in full
    assert "Endocrowns" in full
    # Vancouver-style numbering: bibliography entry should start with the
    # citation number (e.g., "1." or "1 " or "[1]")
    assert any(rendered[0].lstrip().startswith(s) for s in ("1.", "1 ", "[1]")), \
        f"unexpected bibliography prefix: {rendered[0]!r}"


def test_render_bibliography_handles_missing_optional_fields():
    """The lee2023 fixture entry has no DOI. Renderer must not crash."""
    refs = load_references(FIXT / "sample_zotero.json")
    rendered = render_bibliography(refs, CSL)
    assert "Lee" in "\n".join(rendered)


def test_render_bibliography_with_zero_items_returns_empty():
    rendered = render_bibliography([], CSL)
    assert rendered == []


def test_render_bibliography_invalid_csl_raises(tmp_path):
    bad = tmp_path / "bad.csl"
    bad.write_text("<not-csl/>", encoding="utf-8")
    refs = [{"id": "x", "type": "article-journal", "title": "Y"}]
    with pytest.raises(Exception):  # citeproc-py raises various types
        render_bibliography(refs, bad)
