from pathlib import Path
import pytest
from xml.etree import ElementTree as ET
from scripts.journal_config import load_journal

CSL_DIR = Path(__file__).resolve().parent.parent / "scripts" / "csl"
CFG_DIR = Path(__file__).resolve().parent.parent / "scripts" / "journals"

JOURNAL_SLUGS = [
    "jpd", "jomi", "coir", "jdr", "jada", "j-dent",
    "int-j-prosthodont", "j-periodontol", "j-endod",
    "oper-dent", "jerd",
]


@pytest.mark.parametrize("slug", JOURNAL_SLUGS)
def test_each_journal_csl_file_exists(slug):
    """Every journal config must point at a CSL file that exists in
    scripts/csl/ and is well-formed XML."""
    cfg = load_journal(slug, config_dir=CFG_DIR)
    csl_path = CSL_DIR / cfg["reference_style"]
    assert csl_path.exists(), f"CSL file missing for {slug}: {csl_path}"
    ET.parse(csl_path)  # raises if not well-formed XML


@pytest.mark.parametrize("slug", JOURNAL_SLUGS)
def test_csl_file_is_independent_style(slug):
    """citeproc-py cannot render dependent shims. Verify our bundled file
    is an independent style (declares its own <category citation-format>
    and is NOT just a <link rel='independent-parent'> wrapper)."""
    cfg = load_journal(slug, config_dir=CFG_DIR)
    csl_path = CSL_DIR / cfg["reference_style"]
    text = csl_path.read_text(encoding="utf-8")
    # An independent style has either <citation> or <bibliography> blocks
    assert "<citation" in text or "<bibliography" in text, \
        f"{slug}: bundled CSL appears to be a dependent shim"
