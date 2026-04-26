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
