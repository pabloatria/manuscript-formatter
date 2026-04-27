from pathlib import Path
import pytest
from scripts.journal_config import load_journal, JournalConfigError

CONFIG_DIR = Path(__file__).resolve().parent.parent / "scripts" / "journals"

def test_load_jpd_returns_required_fields():
    cfg = load_journal("jpd", config_dir=CONFIG_DIR)
    assert cfg["name"] == "Journal of Prosthetic Dentistry"
    assert cfg["abbreviation"] == "J Prosthet Dent"
    assert any(s["canonical"] == "abstract" for s in cfg["sections"])
    assert cfg["abstract"]["word_limit"] == 400
    assert cfg["reference_style"].endswith(".csl")

def test_unknown_journal_raises():
    with pytest.raises(JournalConfigError, match="not found"):
        load_journal("zzznope", config_dir=CONFIG_DIR)

def test_canonical_section_names_are_unique():
    cfg = load_journal("jpd", config_dir=CONFIG_DIR)
    names = [s["canonical"] for s in cfg["sections"]]
    assert len(names) == len(set(names)), f"duplicate canonical: {names}"

def test_malformed_yaml_raises(tmp_path):
    bad = tmp_path / "broken.yaml"
    bad.write_text("name: 'unclosed string\nabbrev: x\n", encoding="utf-8")
    with pytest.raises(JournalConfigError, match="invalid YAML"):
        load_journal("broken", config_dir=tmp_path)

def test_top_level_non_dict_raises(tmp_path):
    bad = tmp_path / "list.yaml"
    bad.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(JournalConfigError, match="must be a mapping"):
        load_journal("list", config_dir=tmp_path)

def test_section_missing_canonical_raises(tmp_path):
    """A section dict without a 'canonical' key must be rejected before the
    duplicate-uniqueness check silently lets two None entries collapse."""
    bad = tmp_path / "missing_canon.yaml"
    bad.write_text(
        "name: X\nabbreviation: X\n"
        "reference_style: x.csl\n"
        "title_page: {separate_file: false, required_blocks: []}\n"
        "figures: {embedded: false, legend_format: '', numbering: ''}\n"
        "guidelines: {font: '', font_size: 12, line_spacing: 2.0, margins_cm: 2.5, page_numbers: true}\n"
        "article_types:\n"
        "  research:\n"
        "    sections:\n      - display: Foo\n        aliases: [Foo]\n"
        "    abstract: {format: unstructured, word_limit: 250}\n"
        "    total_word_limit: 1000\n"
        "    cover_letter_template: ''\n",
        encoding="utf-8"
    )
    with pytest.raises(JournalConfigError, match="missing 'canonical'"):
        load_journal("missing_canon", config_dir=tmp_path)


JOURNAL_SLUGS = [
    "jpd", "jomi", "coir", "jdr", "jada", "j-dent",
    "int-j-prosthodont", "j-periodontol", "j-endod",
    "oper-dent", "jerd",
]


@pytest.mark.parametrize("slug", JOURNAL_SLUGS)
def test_each_journal_loads_research(slug):
    cfg = load_journal(slug, config_dir=CONFIG_DIR, article_type="research")
    assert cfg["name"]
    assert cfg["abbreviation"]
    assert cfg["sections"]
    assert cfg["reference_style"].endswith(".csl")
    assert cfg["abstract"]["format"] in ("structured", "unstructured")
    assert isinstance(cfg["abstract"]["word_limit"], int)


def test_load_jpd_research_returns_merged_config():
    """v1.1: load_journal(slug, article_type='research') returns the
    journal-level fields merged with the per-type block."""
    cfg = load_journal("jpd", config_dir=CONFIG_DIR, article_type="research")
    # Journal-level fields
    assert cfg["name"] == "Journal of Prosthetic Dentistry"
    assert cfg["reference_style"] == "journal-of-prosthetic-dentistry.csl"
    # Per-type fields merged in
    assert cfg["abstract"]["word_limit"] == 400
    assert cfg["total_word_limit"] == 3000
    # Section-level changes
    assert any(s["canonical"] == "clinical_implications" for s in cfg["sections"])
    intro = next(s for s in cfg["sections"] if s["canonical"] == "introduction")
    assert intro["display"] == "Introduction"  # NOT "Statement of Problem"


def test_load_jpd_default_article_type_is_research():
    """Backward compat: load_journal(slug) with no article_type kwarg
    must still work and default to research."""
    cfg = load_journal("jpd", config_dir=CONFIG_DIR)
    assert cfg["abstract"]["word_limit"] == 400
    assert cfg["total_word_limit"] == 3000


def test_load_jpd_unknown_article_type_raises():
    with pytest.raises(JournalConfigError, match="article type"):
        load_journal("jpd", config_dir=CONFIG_DIR, article_type="zzz")


def test_load_jpd_placeholder_type_raises_clear_error(tmp_path):
    """A YAML with article_types[X].sections == [] must raise a clear
    'placeholder, not yet supported' error."""
    yaml_text = """\
name: X
abbreviation: X
reference_style: x.csl
title_page: {separate_file: false, required_blocks: []}
figures: {embedded: false, legend_format: "", numbering: ""}
guidelines: {font: "", font_size: 12, line_spacing: 2.0, margins_cm: 2.5, page_numbers: true}
article_types:
  research:
    sections:
      - canonical: abstract
        display: Abstract
        aliases: [Abstract]
        word_limit: 250
        required: true
    abstract: {format: unstructured, word_limit: 250}
    total_word_limit: 1000
    cover_letter_template: ""
  case-report:
    sections: []
    abstract: {format: unstructured, word_limit: null}
    total_word_limit: null
    cover_letter_template: ""
"""
    p = tmp_path / "x.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    with pytest.raises(JournalConfigError, match="placeholder|not yet"):
        load_journal("x", config_dir=tmp_path, article_type="case-report")


def test_loader_rejects_stray_per_type_keys_at_journal_level(tmp_path):
    """Catch the v1-muscle-memory authoring mistake of leaving sections:
    or other per-type keys at the journal level."""
    yaml_text = """\
name: X
abbreviation: X
reference_style: x.csl
title_page: {separate_file: false, required_blocks: []}
figures: {embedded: false, legend_format: "", numbering: ""}
guidelines: {font: "", font_size: 12, line_spacing: 2.0, margins_cm: 2.5, page_numbers: true}
sections: [stray-from-v1-muscle-memory]   # MUST be rejected
article_types:
  research:
    sections:
      - canonical: abstract
        display: Abstract
        aliases: [Abstract]
        word_limit: 250
        required: true
    abstract: {format: unstructured, word_limit: 250}
    total_word_limit: 1000
    cover_letter_template: ""
"""
    p = tmp_path / "stray.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    with pytest.raises(JournalConfigError, match="per-type keys.*at journal level"):
        load_journal("stray", config_dir=tmp_path, article_type="research")


@pytest.mark.parametrize("article_type",
                         ["research", "case-report", "technique", "systematic-review"])
def test_jpd_loads_all_four_article_types(article_type):
    cfg = load_journal("jpd", config_dir=CONFIG_DIR, article_type=article_type)
    assert cfg["sections"]
    assert cfg["abstract"]["word_limit"] is not None or article_type == "tip"


# v1.1: research-only journals reject placeholder types with a clear
# 'not yet supported' error rather than silently mis-formatting.
RESEARCH_ONLY_JOURNALS = ["jdr", "jada", "j-dent", "j-periodontol",
                          "j-endod", "oper-dent"]


@pytest.mark.parametrize("slug", RESEARCH_ONLY_JOURNALS)
@pytest.mark.parametrize("article_type",
                          ["case-report", "technique", "systematic-review"])
def test_research_only_journals_reject_placeholder_types(slug, article_type):
    with pytest.raises(JournalConfigError, match="not yet supported"):
        load_journal(slug, config_dir=CONFIG_DIR, article_type=article_type)
