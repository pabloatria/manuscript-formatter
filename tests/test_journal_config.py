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
