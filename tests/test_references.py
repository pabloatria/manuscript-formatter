# tests/test_references.py
from pathlib import Path
import pytest

from scripts.references import load_references, ReferenceFormatError

FIXT = Path(__file__).resolve().parent / "fixtures"


def test_zotero_csl_json_loads():
    refs = load_references(FIXT / "sample_zotero.json")
    assert len(refs) == 2
    assert refs[0]["id"] == "smith2024"
    assert refs[0]["author"][0]["family"] == "Smith"
    assert refs[0]["issued"]["date-parts"][0][0] == 2024


def test_unknown_extension_raises():
    with pytest.raises(ReferenceFormatError, match="unsupported"):
        load_references(FIXT / "nonexistent.xyz")


def test_missing_file_raises_clear_error():
    with pytest.raises(ReferenceFormatError, match="not found"):
        load_references(FIXT / "does-not-exist.json")


def test_csl_json_must_be_a_list(tmp_path):
    """A top-level JSON object instead of an array should raise loudly."""
    bad = tmp_path / "bad.json"
    bad.write_text('{"not": "an array"}', encoding="utf-8")
    with pytest.raises(ReferenceFormatError, match="expected JSON array"):
        load_references(bad)


def test_csl_entry_must_be_dict(tmp_path):
    """A CSL array containing a non-object entry is rejected."""
    bad = tmp_path / "bad.json"
    bad.write_text('[{"id": "ok"}, "not-an-object"]', encoding="utf-8")
    with pytest.raises(ReferenceFormatError, match="entry 1 is not"):
        load_references(bad)


def test_csl_entry_must_have_id(tmp_path):
    """citeproc-py registers citations by id; an entry without one would
    fail opaquely deep in the renderer. Catch it at intake."""
    bad = tmp_path / "bad.json"
    bad.write_text('[{"id": "ok"}, {"title": "no id here"}]', encoding="utf-8")
    with pytest.raises(ReferenceFormatError, match="entry 1 missing required 'id'"):
        load_references(bad)


def test_bibtex_loads_via_extension():
    refs = load_references(FIXT / "sample.bib")
    assert len(refs) == 3
    by_id = {r["id"]: r for r in refs}
    assert "smith2024" in by_id
    assert by_id["smith2024"]["title"] == "Endocrowns in posterior teeth"
    # date-parts is the CSL canonical year representation
    assert by_id["smith2024"]["issued"]["date-parts"][0][0] == 2024
    # Authors split correctly
    assert by_id["smith2024"]["author"][0]["family"] == "Smith"
    assert by_id["smith2024"]["author"][1]["family"] == "Doe"
    # Journal mapped to container-title
    assert by_id["smith2024"]["container-title"] == "Journal of Prosthetic Dentistry"
    # DOI passed through
    assert by_id["smith2024"]["DOI"] == "10.1016/j.test.2024.001"
    # Type is article-journal
    assert by_id["smith2024"]["type"] == "article-journal"


def test_bibtex_drops_others_marker():
    """A 'and others' BibTeX coauthor must not render as a literal author."""
    refs = load_references(FIXT / "sample.bib")
    by_id = {r["id"]: r for r in refs}
    kelly = by_id["kelly2020"]
    assert any(a.get("literal") == "et al." for a in kelly["author"])
    assert all(a.get("family") != "others" for a in kelly["author"])


def test_bibtex_strips_internal_braces_from_title():
    """BibTeX case-protection braces inside titles must not survive into CSL."""
    refs = load_references(FIXT / "sample.bib")
    by_id = {r["id"]: r for r in refs}
    assert by_id["kelly2020"]["title"] == "Dental ceramics: A review"


def test_bibtex_year_with_disambiguation_suffix():
    """Mendeley emits years like '2020a' — extract leading 4 digits."""
    refs = load_references(FIXT / "sample.bib")
    by_id = {r["id"]: r for r in refs}
    assert by_id["kelly2020"]["issued"]["date-parts"][0][0] == 2020


def test_bibtex_book_type_maps_correctly():
    refs = load_references(FIXT / "sample.bib")
    by_id = {r["id"]: r for r in refs}
    assert by_id["kelly2020"]["type"] == "book"
