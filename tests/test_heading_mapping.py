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
