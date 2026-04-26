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


def test_endnote_xml_loads():
    refs = load_references(FIXT / "sample_endnote.xml")
    assert len(refs) == 3
    by_year = {r["issued"]["date-parts"][0][0]: r for r in refs}
    assert 2024 in by_year and 2023 in by_year
    assert by_year[2024]["author"][0]["family"] == "Smith"
    assert by_year[2024]["author"][1]["family"] == "Doe"
    assert by_year[2024]["container-title"] == "Journal of Prosthetic Dentistry"
    assert by_year[2024]["DOI"] == "10.1016/j.test.2024.001"
    assert by_year[2024]["type"] == "article-journal"


def test_endnote_xml_assigns_id_when_rec_number_present():
    """EndNote uses <rec-number> as the natural id; the parser should
    derive an entry id from it so citeproc-py can register the citation."""
    refs = load_references(FIXT / "sample_endnote.xml")
    ids = [r["id"] for r in refs]
    assert all(rid for rid in ids)
    # Two distinct ids
    assert len(set(ids)) == len(ids)


def test_endnote_handles_style_wrapped_fields():
    """Real EndNote 20 wraps every leaf field in <style>...</style>. The
    parser must walk descendants, not rely on direct text content."""
    refs = load_references(FIXT / "sample_endnote.xml")
    by_id = {r["id"]: r for r in refs}
    # The third fixture record uses style-wrapping
    muller = next(r for r in refs if r["author"] and r["author"][0].get("family") == "Müller")
    assert muller["title"].startswith("Survival of")
    # Italic species name should still appear in the title
    assert "Streptococcus mutans" in muller["title"]
    assert muller["container-title"] == "J Dent Res"


def test_endnote_uses_pub_dates_path_when_year_missing():
    """The third fixture record stores year in <pub-dates>/<date>, not
    <dates>/<year>. The parser must find it."""
    refs = load_references(FIXT / "sample_endnote.xml")
    muller = next(r for r in refs if r["author"] and r["author"][0].get("family") == "Müller")
    assert muller["issued"]["date-parts"][0][0] == 2022


def test_endnote_corporate_author_renders_as_literal():
    """A name ending in ',' is EndNote's corporate-author signal — must
    render as CSL literal, not split into 'family Organization, given World Health'."""
    from scripts._endnote_xml_to_csl import _parse_author
    parsed = _parse_author("World Health Organization,")
    assert parsed == {"literal": "World Health Organization"}


def test_endnote_malformed_xml_raises_clear_error(tmp_path):
    bad = tmp_path / "broken.xml"
    bad.write_text("<xml><records><record>oops not closed", encoding="utf-8")
    with pytest.raises(ReferenceFormatError, match="malformed EndNote XML"):
        load_references(bad)
