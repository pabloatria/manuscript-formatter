"""Load and validate per-journal YAML configs."""
from pathlib import Path
import yaml


class JournalConfigError(ValueError):
    pass


JOURNAL_LEVEL_KEYS = {"name", "abbreviation", "reference_style",
                       "title_page", "figures", "guidelines"}
PER_TYPE_KEYS = {"sections", "abstract", "total_word_limit",
                  "cover_letter_template"}
SUPPORTED_ARTICLE_TYPES = {"research", "case-report", "technique",
                            "systematic-review"}


def load_journal(slug: str, config_dir: Path,
                  article_type: str = "research") -> dict:
    """Load journals/<slug>.yaml and return a merged config for the given
    article_type.

    The returned dict has the journal-level fields (name, abbreviation,
    reference_style, title_page, figures, guidelines) PLUS the per-type
    fields (sections, abstract, total_word_limit, cover_letter_template)
    flattened to the top level. Downstream modules consume the same
    shape v1 used.
    """
    if "/" in slug or "\\" in slug or slug.startswith(".") or not slug:
        raise JournalConfigError(f"invalid journal slug: {slug!r}")
    if article_type not in SUPPORTED_ARTICLE_TYPES:
        raise JournalConfigError(
            f"unknown article type {article_type!r}; supported: "
            f"{sorted(SUPPORTED_ARTICLE_TYPES)}"
        )

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

    # Validate journal-level keys
    missing_jl = JOURNAL_LEVEL_KEYS - set(cfg.keys())
    if missing_jl:
        raise JournalConfigError(
            f"{slug}: missing journal-level keys: {sorted(missing_jl)}"
        )

    # Validate article_types: map exists
    if "article_types" not in cfg:
        raise JournalConfigError(
            f"{slug}: missing 'article_types' map (v1.1 schema)"
        )
    if not isinstance(cfg["article_types"], dict):
        raise JournalConfigError(
            f"{slug}: 'article_types' must be a mapping, got "
            f"{type(cfg['article_types']).__name__}"
        )

    if article_type not in cfg["article_types"]:
        raise JournalConfigError(
            f"{slug}: article type {article_type!r} not declared in this "
            f"journal's article_types map"
        )

    type_block = cfg["article_types"][article_type]
    if not isinstance(type_block, dict):
        raise JournalConfigError(
            f"{slug}: article_types[{article_type!r}] must be a mapping"
        )

    # Detect placeholder (sections: [] is the convention for "not yet
    # supported — populate later").
    if not type_block.get("sections"):
        raise JournalConfigError(
            f"{slug}: article type {article_type!r} is a placeholder in "
            f"this journal's config (sections: [] — not yet populated). "
            f"Pick a different journal/type or add the missing block."
        )

    # Validate per-type required keys
    missing_pt = PER_TYPE_KEYS - set(type_block.keys())
    if missing_pt:
        raise JournalConfigError(
            f"{slug}: article_types[{article_type!r}] missing keys: "
            f"{sorted(missing_pt)}"
        )

    # Validate sections shape (carry over from v1)
    if not isinstance(type_block["sections"], list):
        raise JournalConfigError(
            f"{slug}: article_types[{article_type!r}].sections must be a list"
        )
    canonicals = []
    for i, s in enumerate(type_block["sections"]):
        if not isinstance(s, dict) or not s.get("canonical"):
            raise JournalConfigError(
                f"{slug}: article_types[{article_type!r}].sections[{i}] "
                f"missing 'canonical'"
            )
        canonicals.append(s["canonical"])
    if len(canonicals) != len(set(canonicals)):
        raise JournalConfigError(
            f"{slug}: article_types[{article_type!r}] has duplicate "
            f"canonical section names"
        )

    # Merge journal-level + per-type into a flat dict
    merged = {k: cfg[k] for k in JOURNAL_LEVEL_KEYS}
    merged.update({k: type_block[k] for k in PER_TYPE_KEYS})
    return merged
