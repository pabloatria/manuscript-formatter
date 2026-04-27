# Manuscript Formatter Implementation Plan

> **Historical implementation log.** This is the plan that was executed when the feature was built. Useful for understanding the design rationale or for forking the project; **not needed to use or self-host the skill** — see [README](../../README.md) and [`chatgpt/SETUP.md`](../../chatgpt/SETUP.md) for that.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Claude skill that reformats a finished `.docx` manuscript for any of 11 dental journals — moving sections, renaming headings, regenerating references from a manager export, flagging word-count/structure problems — without altering a single byte of the author's prose.

**Architecture:** Config-driven (one YAML per journal), Python 3.10+. Reading and writing `.docx` via python-docx; reference rendering via citeproc-py + bundled CSL style files; reference manager intake from Zotero CSL JSON, Mendeley BibTeX, or EndNote XML/RIS — all normalized to internal CSL JSON before rendering. CLI tool plus a `SKILL.md` for Claude auto-trigger.

**Tech Stack:** Python 3.10+, python-docx ~1.1, citeproc-py ~0.6, bibtexparser ~1.4, pyyaml ~6.0, rapidfuzz ~3.0, pytest ~8 for tests. No native deps, no API keys, no costs.

**Design reference:** `docs/plans/2026-04-26-manuscript-formatter-design.md`

**Project location:** `<repo>` (already initialized as a git repo with the design doc committed).

---

## Phase ordering rationale

The plan follows a dependency-respecting order: data formats first (YAML schema, reference intake), then read-side `.docx` parsing, then transformations, then CLI assembly, then docs/distribution. Each phase ends with a green test and a commit. Tests use programmatic `.docx` fixtures generated with python-docx so we don't need a real manuscript to develop against.

The text-preservation invariant (body paragraphs byte-identical) is the most important assertion in the test suite — every phase that touches the document keeps it verified.

---

## Task 1: Repo scaffold

**Files:**
- Create: `.gitignore`
- Create: `LICENSE` (MIT, copy verbatim from `<sibling repo>/LICENSE`)
- Create: `pyproject.toml` (minimal, declares python_requires + deps for `pip install -e`)
- Create: `pytest.ini`
- Create: empty placeholders: `scripts/__init__.py`, `tests/__init__.py`

**Step 1:** Copy `LICENSE` from pubmed-brief.

```bash
cp <sibling repo>/LICENSE <repo>/LICENSE
```

**Step 2:** Write `.gitignore`:

```
__pycache__/
*.py[cod]
.Python
build/
dist/
*.egg-info/
.venv/
venv/
.pytest_cache/

.DS_Store
.AppleDouble
.LSOverride

.vscode/
.idea/
*.swp

# Local outputs
*.docx
!examples/**/*.docx
!tests/fixtures/**/*.docx
*.pdf
!examples/**/*.pdf

# Local reference exports — never commit a real library
*.bib
*.ris
*.enl
!tests/fixtures/**/*.bib
!tests/fixtures/**/*.ris
```

**Step 3:** Write `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short
```

**Step 4:** Write minimal `pyproject.toml`:

```toml
[project]
name = "manuscript-formatter"
version = "0.1.0"
description = "Reformat dental research manuscripts for journal submission"
requires-python = ">=3.10"
dependencies = [
    "python-docx>=1.1",
    "citeproc-py>=0.6",
    "bibtexparser>=1.4,<2",
    "pyyaml>=6.0",
    "rapidfuzz>=3.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
```

**Step 5:** Touch the empty package init files:

```bash
mkdir -p scripts tests scripts/journals scripts/csl tests/fixtures
touch scripts/__init__.py tests/__init__.py
```

**Step 6:** Install in editable mode + test deps; verify pytest runs.

```bash
cd <repo>
python3 -m pip install --quiet --break-system-packages -e ".[dev]"
pytest --collect-only 2>&1 | tail -3
```

Expected: `0 tests collected`, no import errors.

**Step 7:** Commit.

```bash
git add .
git commit -m "scaffold: project structure, MIT license, pytest config"
```

---

## Task 2: Journal config schema + first config (JPD)

**Files:**
- Create: `scripts/journal_config.py` — load + validate YAML, return typed dict
- Create: `scripts/journals/jpd.yaml` — full JPD config (the example from the design doc)
- Create: `tests/test_journal_config.py`

**Step 1: Write the failing test**

```python
# tests/test_journal_config.py
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
```

**Step 2: Run** — expect `ModuleNotFoundError` on import.

**Step 3: Write `scripts/journals/jpd.yaml`** — copy the JPD YAML block verbatim from the design doc (`Each journals/<slug>.yaml` section).

**Step 4: Write `scripts/journal_config.py`:**

```python
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
        cfg = yaml.safe_load(f)
    missing = REQUIRED_TOP_KEYS - set(cfg.keys())
    if missing:
        raise JournalConfigError(f"{slug}: missing top-level keys: {sorted(missing)}")
    if not isinstance(cfg["sections"], list) or not cfg["sections"]:
        raise JournalConfigError(f"{slug}: sections must be a non-empty list")
    canonicals = [s.get("canonical") for s in cfg["sections"]]
    if len(canonicals) != len(set(canonicals)):
        raise JournalConfigError(f"{slug}: duplicate canonical section names")
    return cfg
```

**Step 5:** Run tests — expect 3/3 pass.

```bash
pytest tests/test_journal_config.py -v
```

**Step 6: Commit**

```bash
git add scripts/journal_config.py scripts/journals/jpd.yaml tests/test_journal_config.py
git commit -m "config: load + validate journal YAML; ship JPD as first config"
```

---

## Task 3: docx heading detection

**Files:**
- Create: `scripts/docx_helpers.py`
- Create: `tests/test_docx_helpers.py`
- Create: `tests/fixtures/build_fixtures.py` — programmatic `.docx` generator (run once, commit the output)

**Step 1: Write the fixture builder + a test fixture**

```python
# tests/fixtures/build_fixtures.py
"""Generate a small .docx fixture for tests. Run once, commit the .docx."""
from pathlib import Path
from docx import Document

def make_jpd_style_manuscript(out_path: Path):
    doc = Document()
    doc.add_heading("Abstract", level=1)
    doc.add_paragraph(
        "Statement of Problem: Endocrowns are minimally invasive but their "
        "long-term survival in posterior teeth remains underreported. "
        "Purpose: to evaluate 5-year survival of lithium disilicate endocrowns. "
        "Methods: 50 endocrowns followed prospectively. Results: 92% survival. "
        "Conclusions: comparable to crowns."
    )
    doc.add_heading("Background", level=1)  # alias for "Statement of Problem"
    doc.add_paragraph("Endodontically treated teeth are restorative challenges...")
    doc.add_heading("Methods", level=1)  # alias for "Material and Methods"
    doc.add_paragraph("Fifty patients enrolled, ages 35-72...")
    doc.add_heading("Results", level=1)
    doc.add_paragraph("Kaplan-Meier 5-year survival 92%...")
    doc.add_heading("Discussion", level=1)
    doc.add_paragraph("Our findings agree with prior systematic reviews...")
    doc.add_heading("Conclusion", level=1)  # alias for "Conclusions"
    doc.add_paragraph("Endocrowns are a reliable alternative.")
    doc.save(out_path)

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "minimal_manuscript.docx"
    make_jpd_style_manuscript(out)
    print(f"wrote {out}")
```

**Step 2:** Run the fixture builder once.

```bash
python3 tests/fixtures/build_fixtures.py
```

Expected: `wrote tests/fixtures/minimal_manuscript.docx`. The `.docx` is whitelisted in `.gitignore`.

**Step 3: Write the failing test**

```python
# tests/test_docx_helpers.py
from pathlib import Path
from scripts.docx_helpers import read_headings

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "minimal_manuscript.docx"

def test_read_headings_finds_six_top_level():
    hs = read_headings(FIXTURE)
    levels = [h["level"] for h in hs]
    texts = [h["text"] for h in hs]
    assert all(lv == 1 for lv in levels)
    assert texts == ["Abstract", "Background", "Methods", "Results",
                     "Discussion", "Conclusion"]

def test_each_heading_has_paragraph_index():
    hs = read_headings(FIXTURE)
    indices = [h["paragraph_index"] for h in hs]
    assert indices == sorted(indices)  # strictly ascending
    assert indices[0] >= 0
```

**Step 4: Run** — expect `ModuleNotFoundError`.

**Step 5: Implement `scripts/docx_helpers.py`:**

```python
"""python-docx helpers: heading detection, paragraph manipulation."""
from pathlib import Path
from typing import Iterable
from docx import Document
from docx.text.paragraph import Paragraph

HEADING_STYLE_PREFIX = "Heading "

def _heading_level(p: Paragraph) -> int | None:
    """Return 1..9 if the paragraph uses a Heading N style; else None."""
    style = (p.style.name or "")
    if style.startswith(HEADING_STYLE_PREFIX):
        try:
            return int(style[len(HEADING_STYLE_PREFIX):])
        except ValueError:
            return None
    return None

def read_headings(docx_path: Path) -> list[dict]:
    """Return [{level, text, paragraph_index}, ...] for every heading paragraph."""
    doc = Document(str(docx_path))
    out = []
    for idx, p in enumerate(doc.paragraphs):
        lv = _heading_level(p)
        if lv is not None:
            out.append({"level": lv, "text": p.text.strip(), "paragraph_index": idx})
    return out
```

**Step 6:** Run tests — expect 2/2 pass.

```bash
pytest tests/test_docx_helpers.py -v
```

**Step 7: Commit**

```bash
git add scripts/docx_helpers.py tests/test_docx_helpers.py tests/fixtures/build_fixtures.py tests/fixtures/minimal_manuscript.docx
git commit -m "docx: read_headings detects Heading-styled paragraphs; fixture added"
```

---

## Task 4: Map detected headings to canonical sections (fuzzy)

**Files:**
- Modify: `scripts/docx_helpers.py` — add `map_headings_to_canonical(headings, sections_config)`
- Create: `tests/test_heading_mapping.py`

**Step 1: Write the failing test**

```python
# tests/test_heading_mapping.py
from scripts.docx_helpers import map_headings_to_canonical

JPD_SECTIONS = [
    {"canonical": "abstract", "aliases": ["Abstract", "Summary"]},
    {"canonical": "introduction", "aliases": ["Introduction", "Background", "Statement of Problem"]},
    {"canonical": "methods", "aliases": ["Methods", "Materials and Methods", "Material and Methods"]},
    {"canonical": "results", "aliases": ["Results", "Findings"]},
    {"canonical": "discussion", "aliases": ["Discussion"]},
    {"canonical": "conclusions", "aliases": ["Conclusion", "Conclusions"]},
]

def test_exact_matches():
    detected = [{"text": "Abstract", "level": 1, "paragraph_index": 0}]
    mapped = map_headings_to_canonical(detected, JPD_SECTIONS)
    assert mapped[0]["canonical"] == "abstract"
    assert mapped[0]["confidence"] >= 0.95

def test_alias_matches_background_to_introduction():
    detected = [{"text": "Background", "level": 1, "paragraph_index": 0}]
    mapped = map_headings_to_canonical(detected, JPD_SECTIONS)
    assert mapped[0]["canonical"] == "introduction"

def test_typo_resolves_via_fuzzy():
    detected = [{"text": "Conclussion", "level": 1, "paragraph_index": 0}]
    mapped = map_headings_to_canonical(detected, JPD_SECTIONS)
    assert mapped[0]["canonical"] == "conclusions"
    assert 0.8 <= mapped[0]["confidence"] < 1.0

def test_unmapped_returns_none_with_low_confidence():
    detected = [{"text": "Acknowledgments", "level": 1, "paragraph_index": 0}]
    mapped = map_headings_to_canonical(detected, JPD_SECTIONS)
    assert mapped[0]["canonical"] is None
    assert mapped[0]["original_text"] == "Acknowledgments"
```

**Step 2:** Run — expect ImportError.

**Step 3: Implement** by appending to `scripts/docx_helpers.py`:

```python
from rapidfuzz import fuzz

FUZZY_THRESHOLD = 80  # 0-100; below this we don't map

def map_headings_to_canonical(headings: list[dict],
                               sections_config: list[dict]) -> list[dict]:
    """For each heading, find best canonical match across all aliases.

    Returns enriched heading dicts with: canonical (str|None), confidence (0..1),
    original_text (str). Unmapped headings keep canonical=None.
    """
    out = []
    for h in headings:
        text = h["text"]
        best_canon, best_score = None, 0.0
        for sec in sections_config:
            for alias in sec.get("aliases", []):
                score = fuzz.ratio(text.lower(), alias.lower())
                if score > best_score:
                    best_score = score
                    best_canon = sec["canonical"]
        out.append({
            **h,
            "canonical": best_canon if best_score >= FUZZY_THRESHOLD else None,
            "confidence": best_score / 100,
            "original_text": text,
        })
    return out
```

**Step 4:** Run tests — expect 4/4 pass.

**Step 5: Commit**

```bash
git add scripts/docx_helpers.py tests/test_heading_mapping.py
git commit -m "docx: map detected headings to canonical sections via fuzzy alias match"
```

---

## Task 5: Section reorder + rename — write side, with text-preservation invariant

**Files:**
- Modify: `scripts/docx_helpers.py` — add `reformat_sections(input_path, output_path, journal_cfg)`
- Create: `tests/test_section_reformat.py`

**Step 1: Write the failing test (the most important test in the project)**

```python
# tests/test_section_reformat.py
from pathlib import Path
import shutil
from docx import Document
from scripts.docx_helpers import reformat_sections, read_headings
from scripts.journal_config import load_journal

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "minimal_manuscript.docx"
CFG_DIR = Path(__file__).resolve().parent.parent / "scripts" / "journals"

def _body_paragraph_texts(path: Path) -> list[str]:
    """All non-heading paragraph texts (the author's prose)."""
    doc = Document(str(path))
    out = []
    for p in doc.paragraphs:
        style = p.style.name or ""
        if not style.startswith("Heading "):
            out.append(p.text)
    return out

def test_reformat_renames_headings_to_jpd_canonical(tmp_path):
    out_path = tmp_path / "out.docx"
    cfg = load_journal("jpd", config_dir=CFG_DIR)
    reformat_sections(FIXTURE, out_path, cfg)
    new_headings = [h["text"] for h in read_headings(out_path)]
    # JPD canonicals: Abstract, Statement of Problem, Material and Methods, Results, Discussion, Conclusions
    assert "Statement of Problem" in new_headings  # was "Background"
    assert "Material and Methods" in new_headings  # was "Methods"
    assert "Conclusions" in new_headings  # was "Conclusion"

def test_reformat_preserves_body_paragraphs_byte_identical(tmp_path):
    out_path = tmp_path / "out.docx"
    cfg = load_journal("jpd", config_dir=CFG_DIR)
    reformat_sections(FIXTURE, out_path, cfg)
    assert _body_paragraph_texts(FIXTURE) == _body_paragraph_texts(out_path), \
        "TEXT-PRESERVATION INVARIANT VIOLATED — body prose changed"
```

**Step 2:** Run — expect failure (function not defined).

**Step 3: Implement.** Append to `scripts/docx_helpers.py`:

```python
import copy

def reformat_sections(input_path: Path, output_path: Path, journal_cfg: dict) -> None:
    """Open `input_path`, rename headings to journal canonical names,
    write to `output_path`. Body paragraphs are NEVER mutated.
    """
    doc = Document(str(input_path))
    headings = read_headings(input_path)
    mapped = map_headings_to_canonical(headings, journal_cfg["sections"])
    canon_to_display = {s["canonical"]: s["display"] for s in journal_cfg["sections"]}
    for h in mapped:
        if h["canonical"] is None:
            continue  # leave unmapped headings alone
        target_text = canon_to_display[h["canonical"]]
        para = doc.paragraphs[h["paragraph_index"]]
        # Replace text without changing the paragraph's style.
        # Clear existing runs, add a single run with the new text.
        for run in list(para.runs):
            run.text = ""
        if para.runs:
            para.runs[0].text = target_text
        else:
            para.add_run(target_text)
    doc.save(str(output_path))
```

**Step 4:** Run — expect 2/2 pass. Pay attention to the byte-identical assertion.

```bash
pytest tests/test_section_reformat.py -v
```

**Step 5: Commit**

```bash
git add scripts/docx_helpers.py tests/test_section_reformat.py
git commit -m "docx: rename headings to journal canonical names; verify body preserved"
```

---

## Task 6: Word-count + structure validators

**Files:**
- Create: `scripts/validators.py`
- Create: `tests/test_validators.py`

**Step 1: Write the failing test**

```python
# tests/test_validators.py
from pathlib import Path
from scripts.validators import validate_manuscript
from scripts.journal_config import load_journal

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "minimal_manuscript.docx"
CFG_DIR = Path(__file__).resolve().parent.parent / "scripts" / "journals"

def test_validator_returns_section_word_counts():
    cfg = load_journal("jpd", config_dir=CFG_DIR)
    report = validate_manuscript(FIXTURE, cfg)
    by_canon = {r["canonical"]: r for r in report["sections"]}
    assert by_canon["abstract"]["word_count"] > 0
    assert by_canon["abstract"]["word_count"] < 250  # fixture is short

def test_validator_flags_missing_required_section():
    """Fixture has no Purpose section, but JPD requires one."""
    cfg = load_journal("jpd", config_dir=CFG_DIR)
    report = validate_manuscript(FIXTURE, cfg)
    missing = [m["canonical"] for m in report["missing_required"]]
    assert "purpose" in missing

def test_validator_flags_overlong_abstract():
    """Synthesize an abstract over the 250-word limit and confirm it flags."""
    from docx import Document
    import tempfile
    doc = Document()
    doc.add_heading("Abstract", level=1)
    long_text = "word " * 300
    doc.add_paragraph(long_text)
    p = Path(tempfile.mkstemp(suffix=".docx")[1])
    doc.save(str(p))
    cfg = load_journal("jpd", config_dir=CFG_DIR)
    report = validate_manuscript(p, cfg)
    abs_row = next(r for r in report["sections"] if r["canonical"] == "abstract")
    assert abs_row["over_limit"] is True
    assert abs_row["limit"] == 250
```

**Step 2:** Run — fail.

**Step 3: Implement `scripts/validators.py`:**

```python
"""Validate a manuscript against a journal config: word counts, structure."""
from pathlib import Path
from docx import Document
from .docx_helpers import read_headings, map_headings_to_canonical

def _count_words(text: str) -> int:
    return len([w for w in text.split() if w.strip()])

def _section_text_blocks(doc, headings_idx: list[int]) -> list[list[str]]:
    """Group non-heading paragraphs into runs between consecutive heading indices."""
    paras = doc.paragraphs
    blocks = []
    bounds = headings_idx + [len(paras)]
    for i in range(len(bounds) - 1):
        start, end = bounds[i] + 1, bounds[i + 1]
        block = [paras[j].text for j in range(start, end)
                 if not (paras[j].style.name or "").startswith("Heading ")]
        blocks.append(block)
    return blocks

def validate_manuscript(docx_path: Path, journal_cfg: dict) -> dict:
    doc = Document(str(docx_path))
    headings = read_headings(docx_path)
    mapped = map_headings_to_canonical(headings, journal_cfg["sections"])
    blocks = _section_text_blocks(doc, [h["paragraph_index"] for h in headings])

    # Per-section word counts
    sections_report = []
    seen_canons = set()
    for h, block in zip(mapped, blocks):
        wc = sum(_count_words(t) for t in block)
        cfg_for_section = next(
            (s for s in journal_cfg["sections"] if s["canonical"] == h["canonical"]),
            None,
        )
        limit = cfg_for_section["word_limit"] if cfg_for_section else None
        # Abstract limit comes from a different config field
        if h["canonical"] == "abstract":
            limit = journal_cfg["abstract"].get("word_limit", limit)
        over = (limit is not None) and (wc > limit)
        sections_report.append({
            "canonical": h["canonical"],
            "original_heading": h["original_text"],
            "word_count": wc,
            "limit": limit,
            "over_limit": over,
        })
        if h["canonical"] is not None:
            seen_canons.add(h["canonical"])

    # Required-section check
    required = [s for s in journal_cfg["sections"] if s.get("required")]
    missing = [s for s in required if s["canonical"] not in seen_canons]

    # Total
    total_wc = sum(r["word_count"] for r in sections_report)
    total_limit = journal_cfg.get("total_word_limit")

    return {
        "sections": sections_report,
        "missing_required": missing,
        "total_word_count": total_wc,
        "total_word_limit": total_limit,
        "total_over_limit": (total_limit is not None) and (total_wc > total_limit),
    }
```

**Step 4:** Run tests — expect 3/3 pass.

**Step 5: Commit**

```bash
git add scripts/validators.py tests/test_validators.py
git commit -m "validators: per-section word counts, structure checks, total limit"
```

---

## Task 7: Reference-manager intake (Zotero CSL JSON pass-through)

**Files:**
- Create: `scripts/references.py`
- Create: `tests/test_references.py`
- Create: `tests/fixtures/sample_zotero.json`

**Step 1: Write a tiny CSL JSON fixture**

```json
[
  {
    "id": "smith2024",
    "type": "article-journal",
    "title": "Endocrowns in posterior teeth",
    "author": [{"family": "Smith", "given": "J"}, {"family": "Doe", "given": "A"}],
    "container-title": "J Prosthet Dent",
    "issued": {"date-parts": [[2024]]},
    "DOI": "10.1016/j.test.2024.001"
  },
  {
    "id": "lee2023",
    "type": "article-journal",
    "title": "5-year survival of lithium disilicate",
    "author": [{"family": "Lee", "given": "M"}],
    "container-title": "Clin Oral Implants Res",
    "issued": {"date-parts": [[2023]]}
  }
]
```

**Step 2: Write the failing test**

```python
# tests/test_references.py
from pathlib import Path
from scripts.references import load_references

FIXT = Path(__file__).resolve().parent / "fixtures"

def test_zotero_csl_json_loads():
    refs = load_references(FIXT / "sample_zotero.json")
    assert len(refs) == 2
    assert refs[0]["id"] == "smith2024"
    assert refs[0]["author"][0]["family"] == "Smith"

def test_unknown_extension_raises():
    import pytest
    from scripts.references import ReferenceFormatError
    with pytest.raises(ReferenceFormatError):
        load_references(FIXT / "nonexistent.xyz")
```

**Step 3: Implement `scripts/references.py`:**

```python
"""Load reference-manager exports; normalize all to CSL JSON."""
from pathlib import Path
import json

class ReferenceFormatError(ValueError):
    pass

def load_references(path: Path) -> list[dict]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _load_csl_json(path)
    if suffix == ".bib":
        from ._bibtex_to_csl import bibtex_to_csl
        return bibtex_to_csl(path)
    if suffix == ".xml":
        from ._endnote_xml_to_csl import endnote_xml_to_csl
        return endnote_xml_to_csl(path)
    if suffix == ".ris":
        from ._ris_to_csl import ris_to_csl
        return ris_to_csl(path)
    raise ReferenceFormatError(
        f"unsupported reference export format: {suffix} "
        f"(supported: .json/Zotero, .bib/Mendeley, .xml/EndNote, .ris/EndNote)"
    )

def _load_csl_json(path: Path) -> list[dict]:
    if not path.exists():
        raise ReferenceFormatError(f"file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ReferenceFormatError(f"{path}: expected JSON array")
    return data
```

**Step 4:** Run — expect 2/2 pass.

**Step 5: Commit**

```bash
git add scripts/references.py tests/test_references.py tests/fixtures/sample_zotero.json
git commit -m "refs: load Zotero CSL JSON; dispatch by file extension"
```

---

## Task 8: BibTeX → CSL JSON (Mendeley intake)

**Files:**
- Create: `scripts/_bibtex_to_csl.py`
- Modify: `tests/test_references.py`
- Create: `tests/fixtures/sample.bib`

**Step 1: Write the fixture**

```bibtex
@article{smith2024,
  author = {Smith, J. and Doe, A.},
  title = {Endocrowns in posterior teeth},
  journal = {Journal of Prosthetic Dentistry},
  year = 2024,
  doi = {10.1016/j.test.2024.001}
}

@article{lee2023,
  author = {Lee, M.},
  title = {5-year survival of lithium disilicate},
  journal = {Clinical Oral Implants Research},
  year = 2023
}
```

**Step 2: Append a failing test:**

```python
def test_bibtex_loads_via_extension():
    refs = load_references(FIXT / "sample.bib")
    assert len(refs) == 2
    by_id = {r["id"]: r for r in refs}
    assert "smith2024" in by_id
    assert by_id["smith2024"]["title"] == "Endocrowns in posterior teeth"
    # date-parts is the CSL canonical year representation
    assert by_id["smith2024"]["issued"]["date-parts"][0][0] == 2024
```

**Step 3: Implement `scripts/_bibtex_to_csl.py`:**

```python
"""Map BibTeX (bibtexparser 1.x) entries to CSL JSON."""
from pathlib import Path
import bibtexparser

# Minimal BibTeX type → CSL type mapping
TYPE_MAP = {
    "article": "article-journal",
    "book": "book",
    "inproceedings": "paper-conference",
    "incollection": "chapter",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "techreport": "report",
    "misc": "document",
}

def _split_authors(s: str) -> list[dict]:
    out = []
    for full in s.split(" and "):
        full = full.strip()
        if "," in full:
            family, _, given = full.partition(",")
            out.append({"family": family.strip(), "given": given.strip()})
        else:
            parts = full.rsplit(" ", 1)
            if len(parts) == 2:
                out.append({"family": parts[1], "given": parts[0]})
            else:
                out.append({"family": full, "given": ""})
    return out

def bibtex_to_csl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        db = bibtexparser.load(f)
    out = []
    for e in db.entries:
        item = {
            "id": e.get("ID", ""),
            "type": TYPE_MAP.get(e.get("ENTRYTYPE", "misc"), "document"),
            "title": e.get("title", "").strip("{}").strip(),
        }
        if "author" in e:
            item["author"] = _split_authors(e["author"])
        if "journal" in e:
            item["container-title"] = e["journal"]
        if "year" in e:
            try:
                item["issued"] = {"date-parts": [[int(e["year"])]]}
            except ValueError:
                pass
        if "doi" in e:
            item["DOI"] = e["doi"]
        out.append(item)
    return out
```

**Step 4:** Run tests — expect 3/3 pass.

**Step 5: Commit**

```bash
git add scripts/_bibtex_to_csl.py tests/test_references.py tests/fixtures/sample.bib
git commit -m "refs: BibTeX (Mendeley) → CSL JSON via bibtexparser"
```

---

## Task 9: EndNote XML → CSL JSON

**Files:**
- Create: `scripts/_endnote_xml_to_csl.py`
- Create: `tests/fixtures/sample_endnote.xml`
- Modify: `tests/test_references.py`

**Step 1: Write the EndNote XML fixture** (real EndNote export structure):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xml>
<records>
  <record>
    <rec-number>1</rec-number>
    <ref-type name="Journal Article">17</ref-type>
    <contributors>
      <authors>
        <author>Smith, J.</author>
        <author>Doe, A.</author>
      </authors>
    </contributors>
    <titles>
      <title>Endocrowns in posterior teeth</title>
      <secondary-title>Journal of Prosthetic Dentistry</secondary-title>
    </titles>
    <dates><year>2024</year></dates>
    <electronic-resource-num>10.1016/j.test.2024.001</electronic-resource-num>
  </record>
  <record>
    <rec-number>2</rec-number>
    <ref-type name="Journal Article">17</ref-type>
    <contributors>
      <authors>
        <author>Lee, M.</author>
      </authors>
    </contributors>
    <titles>
      <title>5-year survival of lithium disilicate</title>
      <secondary-title>Clinical Oral Implants Research</secondary-title>
    </titles>
    <dates><year>2023</year></dates>
  </record>
</records>
</xml>
```

**Step 2: Add a failing test:**

```python
def test_endnote_xml_loads():
    refs = load_references(FIXT / "sample_endnote.xml")
    assert len(refs) == 2
    by_year = {r["issued"]["date-parts"][0][0]: r for r in refs}
    assert 2024 in by_year and 2023 in by_year
    assert by_year[2024]["author"][0]["family"] == "Smith"
```

**Step 3: Implement `scripts/_endnote_xml_to_csl.py`:**

```python
"""Map EndNote XML library export to CSL JSON."""
from pathlib import Path
from xml.etree import ElementTree as ET

def _parse_author(name: str) -> dict:
    name = name.strip()
    if "," in name:
        family, _, given = name.partition(",")
        return {"family": family.strip(), "given": given.strip()}
    parts = name.rsplit(" ", 1)
    if len(parts) == 2:
        return {"family": parts[1], "given": parts[0]}
    return {"family": name, "given": ""}

def endnote_xml_to_csl(path: Path) -> list[dict]:
    tree = ET.parse(str(path))
    root = tree.getroot()
    out = []
    for record in root.iter("record"):
        rec_number = (record.findtext("rec-number") or "").strip()
        title = record.findtext(".//titles/title") or ""
        journal = record.findtext(".//titles/secondary-title") or ""
        year_text = record.findtext(".//dates/year") or ""
        doi = record.findtext("electronic-resource-num") or ""
        authors = [_parse_author(a.text or "")
                   for a in record.iterfind(".//contributors/authors/author")]
        item = {
            "id": f"endnote_{rec_number}" if rec_number else f"endnote_{len(out)}",
            "type": "article-journal",
            "title": title.strip(),
        }
        if authors:
            item["author"] = authors
        if journal.strip():
            item["container-title"] = journal.strip()
        if year_text.strip():
            try:
                item["issued"] = {"date-parts": [[int(year_text.strip())]]}
            except ValueError:
                pass
        if doi.strip():
            item["DOI"] = doi.strip()
        out.append(item)
    return out
```

**Step 4:** Run tests — expect 4/4 pass.

**Step 5: Commit**

```bash
git add scripts/_endnote_xml_to_csl.py tests/fixtures/sample_endnote.xml tests/test_references.py
git commit -m "refs: EndNote XML library export → CSL JSON"
```

---

## Task 10: RIS → CSL JSON (EndNote alternative)

**Files:**
- Create: `scripts/_ris_to_csl.py`
- Create: `tests/fixtures/sample.ris`
- Modify: `tests/test_references.py`

**Step 1: RIS fixture**

```
TY  - JOUR
ID  - smith2024
TI  - Endocrowns in posterior teeth
AU  - Smith, J.
AU  - Doe, A.
JO  - Journal of Prosthetic Dentistry
PY  - 2024
DO  - 10.1016/j.test.2024.001
ER  -

TY  - JOUR
ID  - lee2023
TI  - 5-year survival of lithium disilicate
AU  - Lee, M.
JO  - Clinical Oral Implants Research
PY  - 2023
ER  -
```

**Step 2: Failing test**

```python
def test_ris_loads():
    refs = load_references(FIXT / "sample.ris")
    assert len(refs) == 2
    titles = sorted(r["title"] for r in refs)
    assert "Endocrowns in posterior teeth" in titles
```

**Step 3: Implement `scripts/_ris_to_csl.py`:**

```python
"""Minimal RIS parser that emits CSL JSON. Handles the common tags only —
TY (type), TI (title), AU (author, repeatable), JO (journal),
PY (year), DO (DOI), ID (id), ER (record terminator)."""
from pathlib import Path
import re

TYPE_MAP = {"JOUR": "article-journal", "BOOK": "book", "CHAP": "chapter",
            "THES": "thesis", "RPRT": "report"}

def ris_to_csl(path: Path) -> list[dict]:
    out = []
    cur = None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            m = re.match(r"^([A-Z][A-Z0-9])\s*-\s*(.*)$", line)
            if not m:
                continue
            tag, val = m.group(1), m.group(2).strip()
            if tag == "TY":
                cur = {"id": "", "type": TYPE_MAP.get(val, "document"),
                       "author": []}
            elif cur is None:
                continue
            elif tag == "ID":
                cur["id"] = val
            elif tag == "TI" or tag == "T1":
                cur["title"] = val
            elif tag == "AU":
                family, _, given = val.partition(",")
                cur["author"].append({"family": family.strip(),
                                       "given": given.strip()})
            elif tag == "JO" or tag == "T2":
                cur["container-title"] = val
            elif tag == "PY" or tag == "Y1":
                year = re.match(r"(\d{4})", val)
                if year:
                    cur["issued"] = {"date-parts": [[int(year.group(1))]]}
            elif tag == "DO":
                cur["DOI"] = val
            elif tag == "ER":
                if not cur.get("id"):
                    cur["id"] = f"ris_{len(out)}"
                if not cur["author"]:
                    cur.pop("author")
                out.append(cur)
                cur = None
    return out
```

**Step 4:** Run tests — expect 5/5 pass.

**Step 5: Commit**

```bash
git add scripts/_ris_to_csl.py tests/fixtures/sample.ris tests/test_references.py
git commit -m "refs: RIS parser → CSL JSON (EndNote alt-export path)"
```

---

## Task 11: Bibliography rendering with citeproc-py + bundled CSL

**Files:**
- Create: `scripts/csl/journal-of-prosthetic-dentistry.csl` (download from citationstyles.org/styles)
- Modify: `scripts/references.py` — add `render_bibliography(items, csl_path)`
- Create: `tests/test_bibliography_render.py`

**Step 1: Download the JPD CSL style**

```bash
cd <repo>
curl -sL -o scripts/csl/journal-of-prosthetic-dentistry.csl \
  "https://raw.githubusercontent.com/citation-style-language/styles/master/journal-of-prosthetic-dentistry.csl"
head -3 scripts/csl/journal-of-prosthetic-dentistry.csl
```

Expected: starts with `<?xml version="1.0"...`

If that exact filename doesn't exist on the CSL repo, fall back to a Vancouver-family style like `vancouver.csl`. Document the fallback in the YAML.

**Step 2: Failing test**

```python
# tests/test_bibliography_render.py
from pathlib import Path
from scripts.references import load_references, render_bibliography

FIXT = Path(__file__).resolve().parent / "fixtures"
CSL = Path(__file__).resolve().parent.parent / "scripts" / "csl" / "journal-of-prosthetic-dentistry.csl"

def test_render_jpd_bibliography_returns_strings():
    refs = load_references(FIXT / "sample_zotero.json")
    rendered = render_bibliography(refs, CSL)
    assert len(rendered) == 2
    # Expect numbered Vancouver-style: starts with "1." or "1 " etc.
    assert rendered[0].lstrip().startswith(("1", "1."))
    # Authors and title appear in the formatted output
    full = "\n".join(rendered)
    assert "Smith" in full
    assert "Endocrowns" in full
```

**Step 3: Implement** (append to `scripts/references.py`):

```python
def render_bibliography(items: list[dict], csl_path: Path) -> list[str]:
    """Render CSL JSON items as bibliography lines using the given CSL style.

    Returns one string per entry, in the order produced by the style
    (Vancouver-family styles preserve input order; author-year styles sort).
    """
    from citeproc import (CitationStylesStyle, CitationStylesBibliography,
                          formatter, Citation, CitationItem)
    from citeproc.source.json import CiteProcJSON

    bib_source = CiteProcJSON(items)
    style = CitationStylesStyle(str(csl_path), validate=False)
    bib = CitationStylesBibliography(style, bib_source, formatter.plain)
    # Cite each item once so it's included in the bibliography
    for item in items:
        bib.register(Citation([CitationItem(item["id"])]))
    return [str(entry) for entry in bib.bibliography()]
```

**Step 4:** Run — expect pass.

```bash
pytest tests/test_bibliography_render.py -v
```

**Step 5: Commit**

```bash
git add scripts/references.py scripts/csl/journal-of-prosthetic-dentistry.csl tests/test_bibliography_render.py
git commit -m "refs: render bibliography via citeproc-py + bundled JPD CSL"
```

---

## Task 12: Inline citation rendering (Vancouver numbered)

**Files:**
- Modify: `scripts/references.py` — add `render_inline_citations(citation_keys, items, csl_path)`
- Create: `tests/test_inline_citations.py`

**Step 1: Failing test**

```python
# tests/test_inline_citations.py
from pathlib import Path
from scripts.references import load_references, render_inline_citations

FIXT = Path(__file__).resolve().parent / "fixtures"
CSL = Path(__file__).resolve().parent.parent / "scripts" / "csl" / "journal-of-prosthetic-dentistry.csl"

def test_inline_single_citation_returns_number():
    refs = load_references(FIXT / "sample_zotero.json")
    out = render_inline_citations([["smith2024"]], refs, CSL)
    # Vancouver: "1" or "[1]" or similar — exact format depends on CSL,
    # so just assert it contains the digit "1" and not the family name.
    assert "1" in out[0]
    assert "Smith" not in out[0]

def test_inline_multi_citation_groups_renders_each():
    refs = load_references(FIXT / "sample_zotero.json")
    out = render_inline_citations([["smith2024"], ["lee2023"]], refs, CSL)
    assert len(out) == 2
```

**Step 2: Implement:**

```python
def render_inline_citations(citation_groups: list[list[str]],
                            items: list[dict],
                            csl_path: Path) -> list[str]:
    """Render each in-text citation group (a list of CSL ids) using the style.

    A citation 'group' is what appears at one citation point — e.g. [1, 2-4]
    is one group with three ids. Returns parallel list of rendered strings.
    """
    from citeproc import (CitationStylesStyle, CitationStylesBibliography,
                          formatter, Citation, CitationItem)
    from citeproc.source.json import CiteProcJSON

    bib_source = CiteProcJSON(items)
    style = CitationStylesStyle(str(csl_path), validate=False)
    bib = CitationStylesBibliography(style, bib_source, formatter.plain)
    citations = []
    for group in citation_groups:
        cit = Citation([CitationItem(cid) for cid in group])
        bib.register(cit)
        citations.append(cit)
    rendered = [str(bib.cite(c, lambda *a, **k: None)) for c in citations]
    return rendered
```

**Step 3:** Run — expect pass.

**Step 4: Commit**

```bash
git add scripts/references.py tests/test_inline_citations.py
git commit -m "refs: render inline citation groups (Vancouver/AMA/etc per CSL)"
```

---

## Task 13: Cover-letter generator

**Files:**
- Create: `scripts/cover_letter.py`
- Create: `tests/test_cover_letter.py`

**Step 1: Failing test**

```python
# tests/test_cover_letter.py
from pathlib import Path
from docx import Document
from scripts.cover_letter import generate_cover_letter
from scripts.journal_config import load_journal

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "minimal_manuscript.docx"
CFG_DIR = Path(__file__).resolve().parent.parent / "scripts" / "journals"

def test_cover_letter_writes_docx_with_placeholders(tmp_path):
    out = tmp_path / "cover.docx"
    cfg = load_journal("jpd", config_dir=CFG_DIR)
    generate_cover_letter(
        FIXTURE, out, journal_cfg=cfg,
        editor="Dr. Test Editor",
        manuscript_title="Endocrown Survival Study",
        corresponding_author="Pablo Atria, DDS, PhD",
    )
    txt = "\n".join(p.text for p in Document(str(out)).paragraphs)
    assert "Dr. Test Editor" in txt
    assert "Endocrown Survival Study" in txt
    assert "[NOVELTY" in txt
    assert "Pablo Atria" in txt
```

**Step 2: Implement `scripts/cover_letter.py`:**

```python
"""Generate a cover-letter .docx from the journal config template."""
from pathlib import Path
from docx import Document
from .docx_helpers import read_headings, map_headings_to_canonical

def _summarize_methods(input_docx: Path) -> str:
    """One-line methods summary: first sentence of the Methods section.
    If we cannot locate one, return a placeholder the user must fill in."""
    doc = Document(str(input_docx))
    headings = read_headings(input_docx)
    # Locate methods heading by alias
    aliases = {"methods", "material and methods", "materials and methods"}
    target_idx = None
    for h in headings:
        if h["text"].strip().lower() in aliases:
            target_idx = h["paragraph_index"]
            break
    if target_idx is None:
        return "[METHODS_SUMMARY: one-sentence description of the study design]"
    # First non-heading paragraph after the heading
    paras = doc.paragraphs
    for j in range(target_idx + 1, len(paras)):
        if not (paras[j].style.name or "").startswith("Heading "):
            text = paras[j].text.strip()
            if text:
                # First sentence
                return text.split(". ")[0].rstrip(".") + "."
    return "[METHODS_SUMMARY: one-sentence description of the study design]"

def generate_cover_letter(
    input_docx: Path,
    output_docx: Path,
    journal_cfg: dict,
    editor: str | None = None,
    manuscript_title: str | None = None,
    corresponding_author: str | None = None,
) -> None:
    template = journal_cfg["cover_letter_template"]
    body = template.format(
        editor=editor or "[EDITOR]",
        title=manuscript_title or "[MANUSCRIPT_TITLE]",
        methods_summary=_summarize_methods(input_docx),
        results_summary="[RESULTS_SUMMARY: one sentence on the headline finding]",
        authors_summary="The authors have all contributed substantially to this work",
        corresponding_author=corresponding_author or "[CORRESPONDING_AUTHOR]",
    )
    doc = Document()
    for para in body.strip().split("\n\n"):
        doc.add_paragraph(para.strip())
    doc.save(str(output_docx))
```

**Step 3:** Run — expect pass.

**Step 4: Commit**

```bash
git add scripts/cover_letter.py tests/test_cover_letter.py
git commit -m "cover-letter: generate .docx from journal template + manuscript"
```

---

## Task 14: Validation report writer (Markdown)

**Files:**
- Create: `scripts/report.py`
- Create: `tests/test_report.py`

**Step 1: Failing test**

```python
# tests/test_report.py
from scripts.report import render_report

def test_render_report_shows_section_status_and_overlimit():
    payload = {
        "manuscript_filename": "splints-study.docx",
        "journal": {"abbreviation": "J Prosthet Dent"},
        "validation": {
            "sections": [
                {"canonical": "abstract", "original_heading": "Abstract",
                 "word_count": 287, "limit": 250, "over_limit": True},
                {"canonical": "introduction", "original_heading": "Background",
                 "word_count": 612, "limit": None, "over_limit": False},
            ],
            "missing_required": [{"canonical": "purpose", "display": "Purpose"}],
            "total_word_count": 5121,
            "total_word_limit": 5000,
            "total_over_limit": True,
        },
        "heading_renames": [
            {"from": "Background", "to": "Statement of Problem"},
        ],
        "cover_letter_path": "/tmp/x-cover.docx",
    }
    md = render_report(payload)
    assert "287" in md and "limit 250" in md
    assert "Heading \"Background\"" in md or "Background" in md
    assert "Missing" in md or "purpose" in md.lower()
    assert "5121" in md or "5,121" in md
```

**Step 2: Implement `scripts/report.py`:**

```python
"""Render the Markdown validation report."""

def _ok(b: bool) -> str:
    return "✅" if b else "⚠️"

def render_report(payload: dict) -> str:
    j = payload["journal"]
    v = payload["validation"]
    lines = [
        f"# {j['abbreviation']} Submission Report — {payload['manuscript_filename']}",
        "",
    ]
    if v["missing_required"]:
        names = ", ".join(m["canonical"] for m in v["missing_required"])
        lines.append(f"⚠️ Missing required sections: {names}")
    else:
        lines.append("✅ All required sections present")
    lines.append("")
    for s in v["sections"]:
        wc = s["word_count"]
        limit = s["limit"]
        if limit is None:
            lines.append(f"✅ {s['canonical'] or s['original_heading']}: {wc} words")
        else:
            mark = "⚠️" if s["over_limit"] else "✅"
            over = f" — {wc - limit} over" if s["over_limit"] else ""
            lines.append(f"{mark} {s['canonical'] or s['original_heading']}: {wc} words (limit {limit}){over}")
    if v["total_word_limit"] is not None:
        mark = "⚠️" if v["total_over_limit"] else "✅"
        lines.append(f"{mark} Total: {v['total_word_count']:,} words (limit {v['total_word_limit']:,})")
    if payload.get("heading_renames"):
        lines.append("")
        for r in payload["heading_renames"]:
            lines.append(f"ℹ️ Heading \"{r['from']}\" renamed → \"{r['to']}\"")
    if payload.get("cover_letter_path"):
        lines.append("")
        lines.append("# Cover letter")
        lines.append(f"- Generated: yes ({payload['cover_letter_path']})")
        lines.append("- ⚠️ Fill the [NOVELTY] placeholder before sending")
    return "\n".join(lines) + "\n"
```

**Step 3:** Run — expect pass.

**Step 4: Commit**

```bash
git add scripts/report.py tests/test_report.py
git commit -m "report: render Markdown validation report from validator output"
```

---

## Task 15: Main CLI — `scripts/format_manuscript.py`

**Files:**
- Create: `scripts/format_manuscript.py`
- Create: `tests/test_cli.py`

**Step 1: Failing test (end-to-end smoke)**

```python
# tests/test_cli.py
import subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXT = REPO / "tests" / "fixtures"
CLI = REPO / "scripts" / "format_manuscript.py"

def test_cli_full_run_produces_three_outputs(tmp_path):
    cmd = [sys.executable, str(CLI),
           str(FIXT / "minimal_manuscript.docx"),
           "--references", str(FIXT / "sample_zotero.json"),
           "--journal", "jpd",
           "--out-dir", str(tmp_path),
           "--cover-letter", "--editor", "Dr. Test Editor"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"CLI failed:\n{r.stderr}"
    out_files = list(tmp_path.glob("*"))
    suffixes = {p.suffix for p in out_files}
    assert ".docx" in suffixes
    assert ".md" in suffixes
    assert any("cover" in p.name.lower() for p in out_files)
```

**Step 2: Implement `scripts/format_manuscript.py`:**

```python
"""Reformat a .docx manuscript for a target dental journal.

Usage:
  python format_manuscript.py draft.docx \\
    --references library.json --journal jpd --out-dir ~/Downloads/ \\
    [--cover-letter --editor "Dr. Last Name"]
"""
import argparse
from pathlib import Path
import sys

# Allow running from anywhere via `python /path/to/format_manuscript.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.journal_config import load_journal
from scripts.docx_helpers import reformat_sections, read_headings, map_headings_to_canonical
from scripts.validators import validate_manuscript
from scripts.cover_letter import generate_cover_letter
from scripts.report import render_report

REPO_ROOT = Path(__file__).resolve().parent.parent
JOURNALS_DIR = REPO_ROOT / "scripts" / "journals"

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manuscript", help="Input .docx manuscript")
    ap.add_argument("--references", required=True, help="CSL JSON / .bib / .xml / .ris")
    ap.add_argument("--journal", required=True, help="Journal slug (e.g. jpd, jomi)")
    ap.add_argument("--out-dir", default=str(Path.home() / "Downloads"))
    ap.add_argument("--cover-letter", action="store_true")
    ap.add_argument("--editor", default=None)
    args = ap.parse_args()

    in_path = Path(args.manuscript).expanduser().resolve()
    if not in_path.exists():
        sys.exit(f"manuscript not found: {in_path}")
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_journal(args.journal, config_dir=JOURNALS_DIR)

    # 1) Reformat the .docx
    base = in_path.stem
    out_docx = out_dir / f"{base}-{args.journal}.docx"
    reformat_sections(in_path, out_docx, cfg)

    # 2) Build the validation report payload
    headings_in = read_headings(in_path)
    mapped_in = map_headings_to_canonical(headings_in, cfg["sections"])
    canon_to_display = {s["canonical"]: s["display"] for s in cfg["sections"]}
    renames = [
        {"from": h["original_text"], "to": canon_to_display[h["canonical"]]}
        for h in mapped_in
        if h["canonical"] is not None
        and h["original_text"] != canon_to_display[h["canonical"]]
    ]
    validation = validate_manuscript(out_docx, cfg)

    # 3) Cover letter (optional)
    cover_path = None
    if args.cover_letter:
        cover_path = out_dir / f"{base}-{args.journal}-cover-letter.docx"
        generate_cover_letter(
            in_path, cover_path, journal_cfg=cfg,
            editor=args.editor,
            manuscript_title=base.replace("-", " ").title(),
            corresponding_author=None,
        )

    # 4) Markdown report
    report_md = out_dir / f"{base}-{args.journal}-report.md"
    payload = {
        "manuscript_filename": in_path.name,
        "journal": cfg,
        "validation": validation,
        "heading_renames": renames,
        "cover_letter_path": str(cover_path) if cover_path else None,
    }
    report_md.write_text(render_report(payload), encoding="utf-8")

    print(f"✓ wrote {out_docx}")
    print(f"✓ wrote {report_md}")
    if cover_path:
        print(f"✓ wrote {cover_path}")

if __name__ == "__main__":
    main()
```

**Step 3:** Run — expect pass.

```bash
pytest tests/test_cli.py -v
```

**Step 4: Commit**

```bash
git add scripts/format_manuscript.py tests/test_cli.py
git commit -m "cli: format_manuscript orchestrates reformat + validate + cover + report"
```

---

## Task 16: Bundle the remaining 10 journal YAMLs

**Files:**
- Create: `scripts/journals/jomi.yaml`, `coir.yaml`, `jdr.yaml`, `jada.yaml`, `j-dent.yaml`, `int-j-prosthodont.yaml`, `j-periodontol.yaml`, `j-endod.yaml`, `oper-dent.yaml`, `jerd.yaml`

**Step 1:** For each journal, write a YAML modeled on `jpd.yaml` with:
- Correct `name`, `abbreviation`, `reference_style` filename.
- Section list reflecting that journal's house style (read from each journal's "Information for Authors" page on its publisher site if you have it; otherwise use generic IMRaD with the journal's known quirks: e.g. JOMI uses "Materials and Methods" not "Material and Methods"; JDR has shorter abstracts; JADA accepts unstructured abstracts).
- Per-section word limits where the journal publishes them; otherwise `null`.
- Total word limit where applicable.
- `cover_letter_template` similar to JPD's.

Source values from each journal's official Author Guidelines URL. If a value is unknown, set to `null` and add a YAML comment `# TODO verify`.

**Step 2:** For each new YAML, add a parametrized smoke test in `tests/test_journal_config.py`:

```python
import pytest

JOURNAL_SLUGS = ["jpd", "jomi", "coir", "jdr", "jada", "j-dent",
                 "int-j-prosthodont", "j-periodontol", "j-endod",
                 "oper-dent", "jerd"]

@pytest.mark.parametrize("slug", JOURNAL_SLUGS)
def test_each_journal_loads_and_validates(slug):
    cfg = load_journal(slug, config_dir=CONFIG_DIR)
    assert cfg["name"]
    assert cfg["abbreviation"]
    assert cfg["sections"]
    assert cfg["reference_style"].endswith(".csl")
```

**Step 3:** Run — expect 11/11 pass.

**Step 4: Commit**

```bash
git add scripts/journals/ tests/test_journal_config.py
git commit -m "journals: ship 11 journal configs (JPD, JOMI, COIR, JDR, JADA, J Dent, IJP, J Periodontol, J Endod, Oper Dent, JERD)"
```

---

## Task 17: Bundle the remaining 10 CSL style files

**Files:**
- Create: 10 `.csl` files in `scripts/csl/`

**Step 1:** Pull each style from the official CSL repo. The filenames in
the CSL repo are slug-cased; verify each:

```bash
cd <repo>/scripts/csl
BASE="https://raw.githubusercontent.com/citation-style-language/styles/master"
for slug in \
    "international-journal-of-oral-and-maxillofacial-implants" \
    "clinical-oral-implants-research" \
    "journal-of-dental-research" \
    "the-journal-of-the-american-dental-association" \
    "journal-of-dentistry" \
    "the-international-journal-of-prosthodontics" \
    "journal-of-periodontology" \
    "journal-of-endodontics" \
    "operative-dentistry" \
    "journal-of-esthetic-and-restorative-dentistry"; do
    curl -sL -f -o "${slug}.csl" "$BASE/${slug}.csl" \
      && echo "  ok ${slug}.csl" \
      || echo "  MISSING ${slug}.csl — fall back to vancouver.csl in YAML"
done
```

For any CSL file the official repo doesn't have under that exact name, fall back to a Vancouver-family style in the YAML config (note: `vancouver.csl` is a safe fallback for most dental/medical journals).

**Step 2:** Update each YAML's `reference_style` to match the actual filename pulled.

**Step 3:** Add a smoke test `tests/test_csl_files.py`:

```python
from pathlib import Path
import pytest
from scripts.journal_config import load_journal

CSL_DIR = Path(__file__).resolve().parent.parent / "scripts" / "csl"
CFG_DIR = Path(__file__).resolve().parent.parent / "scripts" / "journals"

@pytest.mark.parametrize("slug", [
    "jpd", "jomi", "coir", "jdr", "jada", "j-dent",
    "int-j-prosthodont", "j-periodontol", "j-endod", "oper-dent", "jerd",
])
def test_each_journal_csl_file_exists(slug):
    cfg = load_journal(slug, config_dir=CFG_DIR)
    csl = CSL_DIR / cfg["reference_style"]
    assert csl.exists(), f"CSL file missing: {csl}"
    head = csl.read_text(encoding="utf-8")[:200]
    assert "<?xml" in head
```

**Step 4:** Run — expect 11/11 pass.

**Step 5: Commit**

```bash
git add scripts/csl/ scripts/journals/ tests/test_csl_files.py
git commit -m "csl: bundle 11 CSL style files (citationstyles.org repo, MIT-licensed)"
```

---

## Task 18: Text-preservation invariant — global integration test

**Files:**
- Create: `tests/test_text_preservation_invariant.py`

This is the bedrock test — for every journal config, running the CLI on the fixture must keep body paragraphs byte-identical.

**Step 1: Failing test**

```python
# tests/test_text_preservation_invariant.py
import subprocess, sys
from pathlib import Path
from docx import Document
import pytest

REPO = Path(__file__).resolve().parent.parent
FIXT = REPO / "tests" / "fixtures"
CLI = REPO / "scripts" / "format_manuscript.py"
JOURNALS = ["jpd", "jomi", "coir", "jdr", "jada", "j-dent",
            "int-j-prosthodont", "j-periodontol", "j-endod",
            "oper-dent", "jerd"]

def _body_paragraph_texts(p: Path) -> list[str]:
    doc = Document(str(p))
    return [par.text for par in doc.paragraphs
            if not (par.style.name or "").startswith("Heading ")]

@pytest.mark.parametrize("slug", JOURNALS)
def test_body_prose_byte_identical_for_every_journal(slug, tmp_path):
    in_path = FIXT / "minimal_manuscript.docx"
    cmd = [sys.executable, str(CLI), str(in_path),
           "--references", str(FIXT / "sample_zotero.json"),
           "--journal", slug, "--out-dir", str(tmp_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"{slug}: CLI failed\n{r.stderr}"
    out = tmp_path / f"minimal_manuscript-{slug}.docx"
    assert _body_paragraph_texts(in_path) == _body_paragraph_texts(out), \
        f"{slug}: TEXT-PRESERVATION INVARIANT VIOLATED"
```

**Step 2:** Run — expect 11/11 pass.

**Step 3: Commit**

```bash
git add tests/test_text_preservation_invariant.py
git commit -m "test: invariant — body prose byte-identical for all 11 journals"
```

---

## Task 19: SKILL.md + README.md + SECURITY.md + install.sh

**Files:**
- Create: `SKILL.md`
- Create: `README.md`
- Create: `SECURITY.md`
- Create: `install.sh` (modeled on pubmed-brief)

**Step 1:** Copy the install.sh skeleton from pubmed-brief and adapt:

```bash
cp <sibling repo>/install.sh <repo>/install.sh
```

Replace the skill name and the dep list (manuscripts deps not pubmed deps):

```bash
# In install.sh, replace this block's deps:
# python-docx citeproc-py bibtexparser pyyaml rapidfuzz
```

**Step 2:** Write `SKILL.md` mirroring pubmed-brief's structure but for this skill:
- "When to use" — user asks "reformat my manuscript for X journal"
- Phase 1: validate inputs (manuscript path, references path, journal slug)
- Phase 2: run `format_manuscript.py`
- Phase 3: open outputs and surface the validation report contents to the user
- Edge cases: EndNote requires plain-text conversion; missing CSL fallback; unmapped headings

**Step 3:** Write `README.md` (model on pubmed-brief structure) with:
- Title + tagline
- Badges
- "What you get" section listing the 11 journals
- Install (Claude path)
- Use it (natural-language examples)
- Manual usage (CLI)
- Customize (point at YAML for new journals)
- Security
- Limitations (esp. EndNote caveat)
- License

**Step 4:** Write `SECURITY.md` mirroring pubmed-brief but updated for: no network access required, only filesystem reads/writes; deps audit list; URL whitelist not applicable (no URLs rendered).

**Step 5:** Verify — `cat` each file, sanity-check.

```bash
ls -la <repo>/
```

Expected: SKILL.md, README.md, SECURITY.md, LICENSE, install.sh, scripts/, tests/, docs/.

**Step 6: Commit**

```bash
git add SKILL.md README.md SECURITY.md install.sh
git commit -m "docs: SKILL.md, README, SECURITY, install.sh — public-package skeleton"
```

---

## Task 20: Set up GitHub remote + push + topics

**Files:**
- None modified — pure infra.

**Step 1:** Confirm `gh auth status` shows logged-in.

```bash
gh auth status 2>&1 | head -3
```

**Step 2:** Create the public repo + push.

```bash
cd <repo>
gh repo create manuscript-formatter --public --source=. --remote=origin \
  --description "Reformat dental research manuscripts for journal submission. Same prose, journal-correct structure + references." \
  --push
```

**Step 3:** Add topics.

```bash
gh repo edit pabloatria/manuscript-formatter \
  --add-topic claude-skill --add-topic dentistry --add-topic manuscript \
  --add-topic citeproc --add-topic publishing --add-topic research-tool
```

**Step 4:** Verify the live URL works.

```bash
curl -sI https://github.com/pabloatria/manuscript-formatter | head -1
```

Expected: `HTTP/2 200`.

**Step 5:** No commit — `gh` already pushed; verify clean tree.

```bash
git status --short
```

Expected: nothing.

---

## Task 21: Self-test on a real manuscript (manual, deferred to user)

**Goal:** Pablo runs the CLI against a real splints-study draft + Zotero export. Skill produces all three outputs cleanly. Report flags real issues. Cover letter draft is presentable.

**Steps the user runs:**

```bash
cd ~/.claude/skills
git clone https://github.com/pabloatria/manuscript-formatter.git
cd manuscript-formatter && ./install.sh

# Real test
python3 scripts/format_manuscript.py ~/Downloads/splints-draft.docx \
  --references ~/Downloads/splints-library.json \
  --journal jpd \
  --out-dir ~/Downloads/ \
  --cover-letter --editor "Dr. Avishai Sadan"
```

**Expected outputs:** three files in `~/Downloads/` — reformatted `.docx`, `-report.md`, `-cover-letter.docx`. Pablo opens the report, scans for warnings, opens the reformatted manuscript, spot-checks that headings and reference list look right and prose is unchanged.

**If anything is off**, the issue gets filed back in this repo and we iterate.

---

## Risks summary (from design doc, restated)

- **Citation field-code parsing** is the most likely place for v1 surprises. Zotero CSL JSON is well-documented; EndNote XML works for the library export but the in-text citation matching for EndNote requires the user to run "Convert to Plain Text" first — documented in SKILL.md.
- **CSL coverage:** if any of the 11 named journals doesn't have a CSL file in the official repo, fall back to `vancouver.csl` in the YAML. Note this in the journal's YAML comment.
- **Word styles:** the parser only sees `Heading 1..N`-styled paragraphs. A draft using bold-text-as-pseudo-heading won't be recognized; the report flags this and tells the user to apply heading styles.

---

## Verification before declaring v1 done

Per superpowers:verification-before-completion:

```bash
cd <repo>
pytest -v 2>&1 | tail -5     # expect all green
git status --short            # expect nothing
git log --oneline | head -25  # ~20 commits
```

Then run Task 21 against a real manuscript and confirm the three outputs.
