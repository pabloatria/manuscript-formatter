from pathlib import Path
import pytest
from scripts.journal_config import load_journal, JournalConfigError

CONFIG_DIR = Path(__file__).resolve().parent.parent / "scripts" / "journals"

def test_load_jpd_returns_required_fields():
    cfg = load_journal("jpd", config_dir=CONFIG_DIR)
    assert cfg["name"] == "Journal of Prosthetic Dentistry"
    assert cfg["abbreviation"] == "J Prosthet Dent"
    assert any(s["canonical"] == "abstract" for s in cfg["sections"])
    assert cfg["abstract"]["word_limit"] == 250
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
        "sections:\n  - display: Foo\n    aliases: [Foo]\n"
        "abstract: {format: unstructured, word_limit: 250}\n"
        "reference_style: x.csl\n"
        "title_page: {separate_file: false, required_blocks: []}\n"
        "figures: {embedded: false, legend_format: '', numbering: ''}\n"
        "guidelines: {font: '', font_size: 12, line_spacing: 2.0, margins_cm: 2.5, page_numbers: true}\n"
        "cover_letter_template: ''\n",
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
def test_each_journal_loads_and_validates(slug):
    cfg = load_journal(slug, config_dir=CONFIG_DIR)
    assert cfg["name"]
    assert cfg["abbreviation"]
    assert cfg["sections"]
    assert cfg["reference_style"].endswith(".csl")
    # Abstract block has the structured/unstructured marker
    assert cfg["abstract"]["format"] in ("structured", "unstructured")
    assert isinstance(cfg["abstract"]["word_limit"], int)
