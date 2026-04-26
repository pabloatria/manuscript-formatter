"""Load and validate per-journal YAML configs."""
from pathlib import Path
import yaml

class JournalConfigError(ValueError):
    pass

REQUIRED_TOP_KEYS = {"name", "abbreviation", "sections", "abstract",
                     "reference_style", "title_page", "figures",
                     "guidelines", "cover_letter_template"}

def load_journal(slug: str, config_dir: Path) -> dict:
    """Load journals/<slug>.yaml and validate required keys are present."""
    path = config_dir / f"{slug}.yaml"
    if not path.exists():
        raise JournalConfigError(f"journal config '{slug}' not found at {path}")
    with open(path, encoding="utf-8") as f:
        try:
            cfg = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise JournalConfigError(f"{slug}: invalid YAML — {e}") from e
    if not isinstance(cfg, dict):
        raise JournalConfigError(
            f"{slug}: top-level YAML must be a mapping, got {type(cfg).__name__}"
        )
    missing = REQUIRED_TOP_KEYS - set(cfg.keys())
    if missing:
        raise JournalConfigError(f"{slug}: missing top-level keys: {sorted(missing)}")
    if not isinstance(cfg["sections"], list) or not cfg["sections"]:
        raise JournalConfigError(f"{slug}: sections must be a non-empty list")
    canonicals = []
    for i, s in enumerate(cfg["sections"]):
        if not isinstance(s, dict) or not s.get("canonical"):
            raise JournalConfigError(f"{slug}: sections[{i}] missing 'canonical'")
        canonicals.append(s["canonical"])
    if len(canonicals) != len(set(canonicals)):
        raise JournalConfigError(f"{slug}: duplicate canonical section names")
    return cfg
