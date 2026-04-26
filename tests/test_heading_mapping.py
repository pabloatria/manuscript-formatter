# tests/test_heading_mapping.py
from scripts.docx_helpers import (
    Heading, MappedHeading, map_headings_to_canonical,
)

JPD_SECTIONS = [
    {"canonical": "abstract", "aliases": ["Abstract", "Summary"]},
    {"canonical": "introduction", "aliases": ["Introduction", "Background", "Statement of Problem"]},
    {"canonical": "methods", "aliases": ["Methods", "Materials and Methods", "Material and Methods"]},
    {"canonical": "results", "aliases": ["Results", "Findings"]},
    {"canonical": "discussion", "aliases": ["Discussion"]},
    {"canonical": "conclusions", "aliases": ["Conclusion", "Conclusions"]},
]


def test_exact_match_resolves_to_canonical():
    detected = [Heading(level=1, text="Abstract", paragraph_index=0)]
    mapped = map_headings_to_canonical(detected, JPD_SECTIONS)
    assert isinstance(mapped[0], MappedHeading)
    assert mapped[0].canonical == "abstract"
    assert mapped[0].confidence >= 0.95


def test_alias_match_background_to_introduction():
    detected = [Heading(level=1, text="Background", paragraph_index=0)]
    mapped = map_headings_to_canonical(detected, JPD_SECTIONS)
    assert mapped[0].canonical == "introduction"


def test_typo_resolves_via_fuzzy():
    detected = [Heading(level=1, text="Conclussion", paragraph_index=0)]
    mapped = map_headings_to_canonical(detected, JPD_SECTIONS)
    assert mapped[0].canonical == "conclusions"
    assert 0.8 <= mapped[0].confidence < 1.0


def test_unmapped_returns_none_with_low_confidence():
    detected = [Heading(level=1, text="Acknowledgments", paragraph_index=0)]
    mapped = map_headings_to_canonical(detected, JPD_SECTIONS)
    assert mapped[0].canonical is None
    assert mapped[0].original_text == "Acknowledgments"


def test_mapped_heading_preserves_level_and_index():
    detected = [Heading(level=2, text="Background", paragraph_index=42)]
    mapped = map_headings_to_canonical(detected, JPD_SECTIONS)
    assert mapped[0].level == 2
    assert mapped[0].paragraph_index == 42
    assert mapped[0].text == "Background"


def test_empty_headings_returns_empty_list():
    assert map_headings_to_canonical([], JPD_SECTIONS) == []


def test_empty_sections_config_marks_all_unmapped():
    detected = [Heading(level=1, text="Abstract", paragraph_index=0)]
    mapped = map_headings_to_canonical(detected, [])
    assert mapped[0].canonical is None
    assert mapped[0].confidence == 0.0


def test_section_without_aliases_key_is_skipped_gracefully():
    """A malformed section entry missing 'aliases' should not crash the loop;
    it just contributes nothing to the score."""
    sections = [
        {"canonical": "broken"},  # no 'aliases' key
        {"canonical": "abstract", "aliases": ["Abstract"]},
    ]
    detected = [Heading(level=1, text="Abstract", paragraph_index=0)]
    mapped = map_headings_to_canonical(detected, sections)
    assert mapped[0].canonical == "abstract"


def test_duplicate_alias_first_section_wins():
    """If the same alias appears under two canonicals (a config bug), the
    first-listed canonical wins. Pin this so future >= vs > tweaks are
    caught explicitly."""
    sections = [
        {"canonical": "first", "aliases": ["Methods"]},
        {"canonical": "second", "aliases": ["Methods"]},
    ]
    detected = [Heading(level=1, text="Methods", paragraph_index=0)]
    mapped = map_headings_to_canonical(detected, sections)
    assert mapped[0].canonical == "first"


def test_funding_is_not_mapped_to_findings():
    """Regression test: with FUZZY_THRESHOLD=82, 'Funding' must not slip past
    threshold and silently rename to a Findings/Results alias. fuzz.ratio
    scores Funding/Findings at exactly 80 — the threshold bump from 80 to
    82 fixed this."""
    sections = [{"canonical": "results", "aliases": ["Results", "Findings"]}]
    detected = [Heading(level=1, text="Funding", paragraph_index=0)]
    mapped = map_headings_to_canonical(detected, sections)
    assert mapped[0].canonical is None
