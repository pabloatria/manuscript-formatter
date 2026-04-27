# Article-Type Support v1.1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `--article-type` flag to `manuscript-formatter` so it correctly handles research, case-report, technique, and systematic-review article types — without silently mis-formatting non-IMRAD manuscripts as v1 currently does.

**Architecture:** Each journal YAML migrates from a flat `sections`/`abstract`/`total_word_limit`/`cover_letter_template` block to an `article_types:` map keyed by type. `journal_config.load_journal()` accepts an `article_type="research"` param (backward-compat default) and returns the merged journal-level + per-type config — downstream modules (validators, docx_helpers, cover_letter, report) see the same shape they see today, no internal changes. JPD's article-type structures are verified live; JERD/JOMI/COIR/IJP are populated from prior knowledge with `# TODO verify` markers; the other 6 journals stay research-only with placeholder blocks.

**Tech Stack:** Python 3.10+, pyyaml (existing), python-docx (existing), pytest. No new dependencies.

**Design reference:** `docs/plans/2026-04-26-article-types-v1.1-design.md`

**Project location:** `/Users/pabloatria/Downloads/manuscript-formatter`. Current head: latest on `main` after the ChatGPT distribution work. Test count: 146.

---

## Task 1: Migrate `jpd.yaml` to `article_types:` map (research only first)

Bootstrap the new schema by migrating one journal first, with one type, and verify the loader still works on the legacy YAML format. This unblocks Task 2 (loader changes) where we add the multi-type logic.

**Files:**
- Modify: `scripts/journals/jpd.yaml`

**Step 1:** Read the current `scripts/journals/jpd.yaml` and confirm its current shape (flat `sections:` / `abstract:` / etc. at top level).

**Step 2:** Rewrite `scripts/journals/jpd.yaml` to the new shape with **only the `research:` block populated**, using the verified live JPD data:

```yaml
name: Journal of Prosthetic Dentistry
abbreviation: J Prosthet Dent
reference_style: journal-of-prosthetic-dentistry.csl

title_page:
  separate_file: true
  required_blocks: [authors, affiliations, corresponding_author, conflicts, funding, irb]

figures:
  embedded: false
  legend_format: "Figure {n}. {caption}"
  numbering: "Figure {n}"

guidelines:
  font: "Times New Roman"
  font_size: 12
  line_spacing: 2.0
  margins_cm: 2.54
  page_numbers: true

article_types:

  research:
    sections:
      - canonical: abstract
        display: Abstract
        aliases: [Abstract, Summary]
        word_limit: 400
        required: true
      - canonical: clinical_implications
        display: Clinical Implications
        aliases: [Clinical Implications, Clinical Significance]
        word_limit: null
        required: true
      - canonical: introduction
        display: Introduction
        aliases: [Introduction, Background]
        word_limit: null
        required: true
      - canonical: methods
        display: Material and Methods
        aliases: [Methods, Materials and Methods, Material and Methods]
        word_limit: null
        required: true
      - canonical: results
        display: Results
        aliases: [Results, Findings]
        word_limit: null
        required: true
      - canonical: discussion
        display: Discussion
        aliases: [Discussion]
        word_limit: null
        required: true
      - canonical: conclusions
        display: Conclusions
        aliases: [Conclusion, Conclusions]
        word_limit: null
        required: true
    abstract:
      format: structured
      subsections:
        - Statement of Problem
        - Purpose
        - Material and Methods
        - Results
        - Conclusions
      word_limit: 400
    total_word_limit: 3000
    cover_letter_template: |
      Dear {editor},

      We submit for your consideration our manuscript titled "{title}", an
      original research study reporting {methods_summary}. Our findings —
      {results_summary} — represent [NOVELTY: 1-2 sentences explaining
      what's new and why this journal is the right home].

      {authors_summary}. The manuscript has not been published or submitted
      elsewhere; all authors have approved the submission. Conflicts of
      interest and funding sources are disclosed on the title page.

      Sincerely,
      {corresponding_author}
```

**Notable changes from v1 jpd.yaml** to call out in the commit message:
- Body's first non-abstract section is now `Introduction` (display = `Introduction`), not `Statement of Problem`. Statement of Problem is an abstract-subsection name only. (Fixes a v1 bug.)
- New `clinical_implications` canonical with display `Clinical Implications`. Required per JPD's live guide.
- Abstract word_limit raised from 250 → 400.
- `total_word_limit` lowered from 5000 → 3000 (10-12 double-spaced pages ≈ 3000 words; v1's 5000 was too generous).
- Top-level `sections`/`abstract`/`total_word_limit`/`cover_letter_template` moved under `article_types.research`.

**Step 3:** Don't run the test suite yet — the loader still expects the flat shape. The next task updates the loader to accept the new shape with backward-compat for any legacy flat YAML.

**Step 4:** Stage but don't commit yet — we'll commit Tasks 1+2 together once the loader supports the new shape and tests pass.

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
git add scripts/journals/jpd.yaml
git status --short  # confirm staged
```

---

## Task 2: Update `journal_config.py` to accept `article_type` and merge configs

**Files:**
- Modify: `scripts/journal_config.py`
- Modify: `tests/test_journal_config.py`

**Step 1: Write the failing tests** (append to `tests/test_journal_config.py`):

```python
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
```

Also UPDATE the existing parametrized journal-load test to pass `article_type="research"` explicitly so it works with the new schema:

```python
# REPLACE the existing test_each_journal_loads_and_validates with:
@pytest.mark.parametrize("slug", JOURNAL_SLUGS)
def test_each_journal_loads_research(slug):
    cfg = load_journal(slug, config_dir=CONFIG_DIR, article_type="research")
    assert cfg["name"]
    assert cfg["abbreviation"]
    assert cfg["sections"]
    assert cfg["reference_style"].endswith(".csl")
    assert cfg["abstract"]["format"] in ("structured", "unstructured")
    assert isinstance(cfg["abstract"]["word_limit"], int)
```

**Step 2:** Run the tests — expect failures (loader doesn't accept `article_type` yet, and Tasks 3+ haven't migrated other journals so they'll fail to load).

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
/opt/homebrew/bin/python3.13 -m pytest tests/test_journal_config.py -v
```

Most failures will be "missing top-level key 'article_types'" for the 10 journals not yet migrated — that's expected; we'll migrate them in Tasks 5-9.

**Step 3:** Modify `scripts/journal_config.py` to accept `article_type` and merge:

Replace the existing `load_journal` function with:

```python
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
```

**Step 4:** Run the journal-config tests. The new tests for JPD-specific shape should pass, plus the existing ones. The parametrized test on the 10 unmigrated journals will fail — that's expected; we'll fix in Tasks 5-9.

```bash
/opt/homebrew/bin/python3.13 -m pytest tests/test_journal_config.py -v 2>&1 | tail -30
```

Expected: JPD tests pass; other 10 fail with "missing 'article_types' map (v1.1 schema)".

**Step 5:** Commit Tasks 1+2 together.

```bash
git add scripts/journals/jpd.yaml scripts/journal_config.py tests/test_journal_config.py
git commit -m "config: v1.1 schema — article_types map; migrate JPD with verified live values

journal_config.load_journal() gains article_type='research' kwarg
(default preserves v1 invocations). Returns the journal-level fields
(name, abbreviation, reference_style, title_page, figures, guidelines)
merged with the per-type fields (sections, abstract, total_word_limit,
cover_letter_template) — downstream modules see the same shape v1 used.

JPD migration uses verified live data from
sciencedirect.com/science/journal/00223913/publish/guide-for-authors:
- Body section order corrected: Introduction (not Statement of Problem,
  which is an abstract subsection only — fixes a v1 bug that mis-aliased
  body Introduction → Statement of Problem).
- New required body section: Clinical Implications (between Abstract
  and Introduction).
- Abstract word limit raised 250 → 400 per JPD's actual guide.
- Total word limit lowered 5000 → 3000 (10-12 double-spaced pages).

Loader rejects placeholder types (sections: []) with a clear message —
the convention for journals that haven't been populated for a given
type yet. Other 10 journals will migrate in subsequent tasks; until
then they fail to load with a clear 'missing article_types' error
rather than silently mis-formatting."
```

---

## Task 3: Add `--article-type` CLI flag

**Files:**
- Modify: `scripts/format_manuscript.py`
- Modify: `tests/test_cli.py`

**Step 1: Append failing tests to `tests/test_cli.py`:**

```python
def test_cli_accepts_article_type_research(tmp_path):
    cmd = [
        PYTHON, str(CLI),
        str(FIXT / "minimal_manuscript.docx"),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", "jpd",
        "--article-type", "research",
        "--out-dir", str(tmp_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"CLI failed: {r.stderr}"


def test_cli_default_article_type_is_research(tmp_path):
    """v1 invocations (no --article-type) must keep working."""
    cmd = [
        PYTHON, str(CLI),
        str(FIXT / "minimal_manuscript.docx"),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", "jpd",
        "--out-dir", str(tmp_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"CLI failed: {r.stderr}"


def test_cli_invalid_article_type_rejected(tmp_path):
    cmd = [
        PYTHON, str(CLI),
        str(FIXT / "minimal_manuscript.docx"),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", "jpd",
        "--article-type", "not-a-type",
        "--out-dir", str(tmp_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode != 0
    assert "article" in (r.stderr + r.stdout).lower()
```

**Step 2:** Run — expect failures (flag doesn't exist yet).

```bash
/opt/homebrew/bin/python3.13 -m pytest tests/test_cli.py -v
```

**Step 3: Modify `scripts/format_manuscript.py`** — add the flag to the argparse block, thread it through to `load_journal()`:

In the `main()` function, after the existing `--editor` argument, add:

```python
    ap.add_argument(
        "--article-type",
        default="research",
        choices=["research", "case-report", "technique", "systematic-review"],
        help="Article type for this manuscript (default: research). The "
             "selected type determines which section structure, word "
             "limits, and abstract format the journal expects.",
    )
```

Update the `load_journal` call:

```python
    try:
        cfg = load_journal(args.journal, config_dir=JOURNALS_DIR,
                           article_type=args.article_type)
    except JournalConfigError as e:
        sys.exit(str(e))
```

**Step 4:** Run the CLI tests — expect 3/3 new tests pass.

```bash
/opt/homebrew/bin/python3.13 -m pytest tests/test_cli.py -v
```

**Step 5: Commit**

```bash
git add scripts/format_manuscript.py tests/test_cli.py
git commit -m "cli: add --article-type flag (default research, backward-compat)

argparse choices restrict to the four supported types so an invalid
value gets a clean argparse error rather than reaching the config
loader. Threading is one line into load_journal(). Three tests pin:
explicit --article-type research works; omitting the flag works (v1
invocations); invalid value is rejected before any work."
```

---

## Task 4: Add the other three JPD article-type blocks (case-report, technique, systematic-review)

**Files:**
- Modify: `scripts/journals/jpd.yaml` — append three blocks under `article_types:`

**Step 1:** Append these three blocks to `scripts/journals/jpd.yaml` under `article_types:` (after the existing `research:` block):

```yaml
  case-report:
    sections:
      - canonical: abstract
        display: Abstract
        aliases: [Abstract, Summary]
        word_limit: 150
        required: true
      - canonical: introduction
        display: Introduction
        aliases: [Introduction, Background]
        word_limit: null
        required: true
      - canonical: clinical_report
        display: Clinical Report
        aliases: [Clinical Report, Case Report, Case Description, Patient History, Case Presentation]
        word_limit: null
        required: true
      - canonical: discussion
        display: Discussion
        aliases: [Discussion]
        word_limit: null
        required: false  # JPD lists Discussion as optional for clinical reports
      - canonical: summary
        display: Summary
        aliases: [Summary, Conclusion, Conclusions]
        word_limit: null
        required: true
    abstract:
      format: unstructured
      subsections: []
      word_limit: 150
    total_word_limit: 1250  # 4-5 double-spaced pages
    cover_letter_template: |
      Dear {editor},

      We submit for your consideration a clinical report titled "{title}",
      which describes {methods_summary}. [NOVELTY: 1-2 sentences explaining
      what this case adds to the literature].

      {authors_summary}. The manuscript has not been published or submitted
      elsewhere; all authors have approved the submission.

      Sincerely,
      {corresponding_author}

  technique:
    sections:
      - canonical: abstract
        display: Abstract
        aliases: [Abstract, Summary]
        word_limit: 150
        required: true
      - canonical: introduction
        display: Introduction
        aliases: [Introduction, Background]
        word_limit: null
        required: true
      - canonical: technique
        display: Technique
        aliases: [Technique, Procedure, Method, Step-by-Step]
        word_limit: null
        required: true
      - canonical: discussion
        display: Discussion
        aliases: [Discussion, Clinical Considerations]
        word_limit: null
        required: false  # optional per JPD's guide
      - canonical: summary
        display: Summary
        aliases: [Summary, Conclusion, Conclusions]
        word_limit: null
        required: true
    abstract:
      format: unstructured
      subsections: []
      word_limit: 150
    total_word_limit: 1250  # 4-5 double-spaced pages
    cover_letter_template: |
      Dear {editor},

      We submit for your consideration a dental technique titled "{title}",
      which describes {methods_summary}. [NOVELTY: 1-2 sentences explaining
      the clinical advantage of this technique].

      {authors_summary}. The manuscript has not been published or submitted
      elsewhere; all authors have approved the submission.

      Sincerely,
      {corresponding_author}

  systematic-review:
    sections:
      - canonical: abstract
        display: Abstract
        aliases: [Abstract, Summary]
        word_limit: 400
        required: true
      - canonical: introduction
        display: Introduction
        aliases: [Introduction, Background]
        word_limit: null
        required: true
      - canonical: methods
        display: Methods   # JPD systematic reviews use "Methods" not "Material and Methods"
        aliases: [Methods, Material and Methods, Materials and Methods, Search Strategy]
        word_limit: null
        required: true
      - canonical: results
        display: Results
        aliases: [Results, Findings]
        word_limit: null
        required: true
      - canonical: discussion
        display: Discussion
        aliases: [Discussion]
        word_limit: null
        required: true
      - canonical: conclusions
        display: Conclusions
        aliases: [Conclusion, Conclusions]
        word_limit: null
        required: true
    abstract:
      format: structured
      subsections:
        - Statement of Problem
        - Purpose
        - Material and Methods
        - Results
        - Conclusions
      word_limit: 400
    total_word_limit: null  # JPD does not cap systematic-review length
    cover_letter_template: |
      Dear {editor},

      We submit for your consideration a systematic review titled "{title}",
      which {methods_summary}. Our findings — {results_summary} — represent
      [NOVELTY: 1-2 sentences explaining the gap this review fills].

      The protocol was registered with PROSPERO before data extraction
      began [INSERT PROSPERO ID]. {authors_summary}. The manuscript has
      not been published or submitted elsewhere; all authors have approved
      the submission.

      Sincerely,
      {corresponding_author}
```

**Step 2:** Add a parametrized test in `tests/test_journal_config.py` asserting all 4 JPD types load:

```python
@pytest.mark.parametrize("article_type",
                         ["research", "case-report", "technique", "systematic-review"])
def test_jpd_loads_all_four_article_types(article_type):
    cfg = load_journal("jpd", config_dir=CONFIG_DIR, article_type=article_type)
    assert cfg["sections"]
    assert cfg["abstract"]["word_limit"] is not None or article_type == "tip"
```

**Step 3:** Run.

```bash
/opt/homebrew/bin/python3.13 -m pytest tests/test_journal_config.py -v
```

Expected: 4 new parametrized cases pass; existing JPD tests still pass; the 10 unmigrated journals' tests still fail.

**Step 4: Commit**

```bash
git add scripts/journals/jpd.yaml tests/test_journal_config.py
git commit -m "config: JPD case-report + technique + systematic-review blocks

Three more article-type blocks under jpd.yaml's article_types map,
populated from JPD's verified live guide:
- case-report: 150w abstract (unstructured), Clinical Report block
  with 5 alias variants for the case-description heading, optional
  Discussion, 1250-word total (4-5 dbl-spaced pages).
- technique: 150w abstract, Technique block (numbered steps), optional
  Discussion / 'Clinical Considerations' alias, 1250-word total.
- systematic-review: 400w structured abstract (same subsections as
  research), 'Methods' singular per JPD's guide quirk, no total word
  limit, cover letter mentions PROSPERO registration."
```

---

## Task 5: Add clinical-report fixture + reformat-preserves-Clinical-Report test

**Files:**
- Modify: `tests/fixtures/build_fixtures.py` — add a clinical-report builder
- Run: regenerate the new fixture
- Modify: `tests/test_section_reformat.py` — add a new test

**Step 1:** Append to `tests/fixtures/build_fixtures.py`:

```python
def make_jpd_clinical_report(out_path: Path):
    """A short clinical report following JPD's required structure:
    Abstract → Introduction → Clinical Report → Discussion → Summary."""
    doc = Document()
    doc.add_heading("Abstract", level=1)
    doc.add_paragraph(
        "A 62-year-old patient with a failing implant-supported prosthesis "
        "was treated with a digital workflow combining intraoral scanning, "
        "guided implant placement, and a milled zirconia crown. Six-month "
        "follow-up showed stable peri-implant health and patient satisfaction."
    )
    doc.add_heading("Introduction", level=1)
    doc.add_paragraph(
        "Failures of implant-supported prostheses in the maxillary anterior "
        "are challenging because of esthetic demands and bone quality."
    )
    doc.add_heading("Clinical Report", level=1)
    doc.add_paragraph(
        "Patient history: A 62-year-old female presented with an exposed "
        "abutment screw on tooth 11. Examination revealed peri-implantitis "
        "with 4 mm probing depth and bleeding on probing."
    )
    doc.add_paragraph(
        "Treatment: After non-surgical debridement and a 6-week healing "
        "period, the implant was explanted using a guided technique."
    )
    doc.add_paragraph(
        "Outcome: At 6-month follow-up, the new implant showed full "
        "osseointegration with stable peri-implant health."
    )
    doc.add_heading("Discussion", level=1)
    doc.add_paragraph(
        "Digital workflows for implant explantation and replacement reduce "
        "surgical time and improve esthetic predictability."
    )
    doc.add_heading("Summary", level=1)
    doc.add_paragraph(
        "This clinical report demonstrates a digital workflow for the "
        "predictable replacement of a failing maxillary anterior implant."
    )
    doc.save(out_path)
    _normalize_docx(out_path)
```

Update the `if __name__ == "__main__":` block to also build the new fixture:

```python
if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "minimal_manuscript.docx"
    make_jpd_style_manuscript(out)
    print(f"wrote {out}")

    out = Path(__file__).resolve().parent / "clinical_report_manuscript.docx"
    make_jpd_clinical_report(out)
    print(f"wrote {out}")
```

**Step 2:** Run the builder.

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
/opt/homebrew/bin/python3.13 tests/fixtures/build_fixtures.py
```

Expected: both fixtures regenerate. The existing `minimal_manuscript.docx` should be byte-identical to before (deterministic builder); the new `clinical_report_manuscript.docx` is added.

**Step 3:** Append a new test to `tests/test_section_reformat.py`:

```python
CLINICAL_REPORT_FIXTURE = (Path(__file__).resolve().parent
                            / "fixtures" / "clinical_report_manuscript.docx")


def test_reformat_clinical_report_preserves_clinical_report_heading(tmp_path):
    """For --article-type case-report, the 'Clinical Report' heading must
    survive intact (canonical name === display name) instead of being
    fuzzy-mapped to a research-IMRAD section like Methods or Results."""
    out_path = tmp_path / "out.docx"
    cfg = load_journal("jpd", config_dir=CFG_DIR, article_type="case-report")
    reformat_sections(CLINICAL_REPORT_FIXTURE, out_path, cfg)
    new_headings = [h.text for h in read_headings(out_path)]
    assert "Clinical Report" in new_headings
    # IMRAD sections must NOT appear (they don't apply to case reports)
    assert "Material and Methods" not in new_headings
    assert "Results" not in new_headings
    # Body prose unchanged (the bedrock invariant)
    in_doc = Document(str(CLINICAL_REPORT_FIXTURE))
    out_doc = Document(str(out_path))
    in_body = [p.text for p in in_doc.paragraphs
               if not (p.style.name or "").startswith("Heading ")]
    out_body = [p.text for p in out_doc.paragraphs
                if not (p.style.name or "").startswith("Heading ")]
    assert in_body == out_body
```

**Step 4:** Run.

```bash
/opt/homebrew/bin/python3.13 -m pytest tests/test_section_reformat.py -v
```

Expected: new test passes. Existing tests still pass.

**Step 5: Commit**

```bash
git add tests/fixtures/build_fixtures.py tests/fixtures/clinical_report_manuscript.docx tests/test_section_reformat.py
git commit -m "test: clinical-report fixture; reformat preserves Clinical Report heading

Programmatic fixture for a JPD-style case report (Abstract → Introduction
→ Clinical Report → Discussion → Summary). Normalized for byte-stability
the same way minimal_manuscript.docx is. Test pins the case-report
behavior we care about: 'Clinical Report' heading survives reformat
unchanged (its canonical and display are both 'Clinical Report'), and
IMRAD sections do not appear in the output. Body prose is byte-identical."
```

---

## Task 6: Migrate JERD to all 4 article types (best-effort with TODOs)

**Files:**
- Modify: `scripts/journals/jerd.yaml`

**Step 1:** Rewrite `scripts/journals/jerd.yaml` to the new shape. Use the JPD structure as a starting point and adjust for JERD-specific quirks:

- Research: add a `Clinical Significance` body section at the end (JERD's distinguishing feature). Word limit ~4000 (`# TODO verify`).
- Case-report: same shape as JPD. ~2000 words.
- Technique: same as JPD. ~2000 words.
- Systematic-review: same as JPD. No cap.

Mark journal-specific values that I'm guessing with `# TODO verify <field> against current JERD author guidelines`.

The full content for jerd.yaml is too long to inline here; structure it analogously to the JPD migration, with the differences listed above. Concretely: copy the entire migrated `jpd.yaml`, change `name`/`abbreviation`/`reference_style`, append a `clinical_significance` section to research's section list, adjust `total_word_limit` per type, mark TODOs.

**Step 2:** Run journal-config tests for jerd.

```bash
/opt/homebrew/bin/python3.13 -m pytest tests/test_journal_config.py -v -k jerd
```

Expected: jerd-specific cases pass.

**Step 3: Commit**

```bash
git add scripts/journals/jerd.yaml
git commit -m "config: JERD article_types — research/case-report/technique/systematic-review

Best-effort population (Wiley page 403s on automated fetch, so values
are from prior knowledge). 'Clinical Significance' added as a required
body section for research articles per JERD's submission template. Word
limits and a few abstract-subsection names marked # TODO verify until
the user can pass authoritative values."
```

---

## Task 7: Migrate JOMI

**Files:**
- Modify: `scripts/journals/jomi.yaml`

Same pattern as Task 6: JPD-like taxonomy, slightly tighter limits per JOMI's known style. Mark TODOs for word limits and any uncertain subsection names.

Commit: `config: JOMI article_types — research/case-report/technique/systematic-review`.

---

## Task 8: Migrate COIR

**Files:**
- Modify: `scripts/journals/coir.yaml`

Same pattern. COIR-specific quirk: case reports are rare and called "Short Communication" — use that as the `display` for case-report's body section (or adjust aliases accordingly).

Commit: `config: COIR article_types — research/case-report/technique/systematic-review`.

---

## Task 9: Migrate IJP

**Files:**
- Modify: `scripts/journals/int-j-prosthodont.yaml`

Same pattern. JPD-like structure throughout.

Commit: `config: Int J Prosthodont article_types — research/case-report/technique/systematic-review`.

---

## Task 10: Migrate the other 6 journals to research-only-with-placeholders

**Files:**
- Modify: `scripts/journals/jdr.yaml`
- Modify: `scripts/journals/jada.yaml`
- Modify: `scripts/journals/j-dent.yaml`
- Modify: `scripts/journals/j-periodontol.yaml`
- Modify: `scripts/journals/j-endod.yaml`
- Modify: `scripts/journals/oper-dent.yaml`

For each: move the existing flat `sections`/`abstract`/`total_word_limit`/`cover_letter_template` block under `article_types.research:`, then add three placeholder blocks for `case-report`, `technique`, `systematic-review`. Each placeholder has:

```yaml
  case-report:
    # TODO populate from journal's author guidelines
    sections: []
    abstract:
      format: unstructured
      subsections: []
      word_limit: null
    total_word_limit: null
    cover_letter_template: ""
```

Identical for `technique:` and `systematic-review:`.

**Step 1:** Migrate all 6 in one batch (the change is mechanical and identical per journal except for the per-journal research content which is preserved).

**Step 2:** Run the parametrized journal-config test.

```bash
/opt/homebrew/bin/python3.13 -m pytest tests/test_journal_config.py -v
```

Expected: 11/11 journals load with `article_type="research"`. Attempting the placeholder types raises the clear "placeholder, not yet populated" error from Task 2.

**Step 3:** Add a parametrized test asserting placeholder types raise the right error:

```python
RESEARCH_ONLY_JOURNALS = ["jdr", "jada", "j-dent", "j-periodontol",
                          "j-endod", "oper-dent"]

@pytest.mark.parametrize("slug", RESEARCH_ONLY_JOURNALS)
@pytest.mark.parametrize("article_type",
                         ["case-report", "technique", "systematic-review"])
def test_research_only_journals_reject_placeholder_types(slug, article_type):
    with pytest.raises(JournalConfigError, match="placeholder|not yet"):
        load_journal(slug, config_dir=CONFIG_DIR, article_type=article_type)
```

**Step 4: Commit**

```bash
git add scripts/journals/jdr.yaml scripts/journals/jada.yaml scripts/journals/j-dent.yaml \
        scripts/journals/j-periodontol.yaml scripts/journals/j-endod.yaml \
        scripts/journals/oper-dent.yaml \
        tests/test_journal_config.py
git commit -m "config: 6 research-only journals migrated to v1.1 schema with placeholders

JDR, JADA, J Dent, J Periodontol, J Endod, Oper Dent each grow an
article_types: map. The existing flat fields move under research:
unchanged (no behavior change for v1 invocations). The other three
types (case-report, technique, systematic-review) get placeholder
blocks with sections: [] and TODO-populate comments — the loader
rejects them with a clear 'not yet populated' message until a
maintainer fills them in.

Parametrized test asserts: 6 journals × 3 placeholder types × correct
error message = 18 cases."
```

---

## Task 11: Expand cross-journal text-preservation invariant test

**Files:**
- Modify: `tests/test_text_preservation_invariant.py`

**Step 1:** Replace the existing parametrization to include `article_type`. The test currently runs (slug × invariant_kind) = 22. After: (slug × populated_article_type × invariant_kind).

```python
import subprocess
import sys
from pathlib import Path

import pytest
from docx import Document
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parent.parent
FIXT = REPO / "tests" / "fixtures"
CLI = REPO / "scripts" / "format_manuscript.py"


# (slug, article_type, fixture_filename) — only populated combinations
PARAMETER_GRID: list[tuple[str, str, str]] = []
for slug in ["jpd", "jerd", "jomi", "coir", "int-j-prosthodont"]:
    for at in ["research", "case-report", "technique", "systematic-review"]:
        fixture = ("clinical_report_manuscript.docx" if at == "case-report"
                   else "minimal_manuscript.docx")
        PARAMETER_GRID.append((slug, at, fixture))
# research-only journals
for slug in ["jdr", "jada", "j-dent", "j-periodontol", "j-endod", "oper-dent"]:
    PARAMETER_GRID.append((slug, "research", "minimal_manuscript.docx"))


def _run_cli(in_path: Path, slug: str, article_type: str, out_dir: Path) -> Path:
    cmd = [
        sys.executable, str(CLI), str(in_path),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", slug,
        "--article-type", article_type,
        "--out-dir", str(out_dir),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, (
        f"CLI failed for {slug}/{article_type}:\n{r.stderr}"
    )
    return out_dir / f"{in_path.stem}-{slug}.docx"


def _body_paragraph_texts(p: Path) -> list[str]:
    doc = Document(str(p))
    return [par.text for par in doc.paragraphs
            if not (par.style.name or "").startswith("Heading ")]


def _body_paragraph_xml(p: Path) -> list[bytes]:
    doc = Document(str(p))
    return [ET.tostring(par._element, encoding="utf-8")
            for par in doc.paragraphs
            if not (par.style.name or "").startswith("Heading ")]


@pytest.mark.parametrize("slug,article_type,fixture", PARAMETER_GRID)
def test_body_text_byte_identical(slug, article_type, fixture, tmp_path):
    in_path = FIXT / fixture
    out_path = _run_cli(in_path, slug, article_type, tmp_path)
    assert _body_paragraph_texts(in_path) == _body_paragraph_texts(out_path), \
        f"{slug}/{article_type}: BODY-TEXT INVARIANT VIOLATED"


@pytest.mark.parametrize("slug,article_type,fixture", PARAMETER_GRID)
def test_body_paragraph_xml_byte_identical(slug, article_type, fixture, tmp_path):
    in_path = FIXT / fixture
    out_path = _run_cli(in_path, slug, article_type, tmp_path)
    assert _body_paragraph_xml(in_path) == _body_paragraph_xml(out_path), \
        f"{slug}/{article_type}: BODY-XML INVARIANT VIOLATED"
```

Parameter grid: 5 fully-populated journals × 4 types + 6 research-only × 1 = 26 cases × 2 invariants = **52 parametrized tests**.

**Step 2:** Run.

```bash
/opt/homebrew/bin/python3.13 -m pytest tests/test_text_preservation_invariant.py -v 2>&1 | tail -30
```

Expected: all 52 pass. If any fail (e.g., a TODO-marked alias collides with the fixture's heading and produces an unexpected rename), surface the slug/type/diff and we iterate.

**Step 3: Commit**

```bash
git add tests/test_text_preservation_invariant.py
git commit -m "test: parametrize bedrock invariant over (journal × article_type)

The text-preservation invariant must hold for every populated
combination, not just JPD-research. Parameter grid: 5 fully-populated
journals × 4 types + 6 research-only journals × research only = 26
cases × 2 invariants (text + XML) = 52 parametrized tests. Uses
clinical_report_manuscript.docx as the fixture for case-report, the
existing minimal_manuscript.docx for the rest."
```

---

## Task 12: Update docs (README, SKILL.md, CUSTOM_GPT_INSTRUCTIONS.md)

**Files:**
- Modify: `README.md`
- Modify: `SKILL.md`
- Modify: `chatgpt/CUSTOM_GPT_INSTRUCTIONS.md`

### README.md changes

In the "Use it (Claude)" section, add new natural-language examples that include article type:

```
"Reformat my case report for JPD"
"Convert this systematic review to JOMI style"
"Format this technique article for JERD with cover letter"
```

In the "Manual usage (CLI)" code block, add the new flag:

```bash
python3 scripts/format_manuscript.py \
  ~/Downloads/draft.docx \
  --references ~/Downloads/library.json \
  --journal jpd \
  --article-type case-report \
  --out-dir ~/Downloads/ \
  --cover-letter \
  --editor "Dr. Last Name"
```

Add to the supported-journals table or right after it: a "Supported article types" callout listing the 4 types and noting that not every journal has every type populated yet.

### SKILL.md changes

In the workflow phase 1 (validate inputs), add a new substep: "Identify the article type from the user's request. Default to `research` if unstated. Pass via `--article-type`."

In edge cases: "If the manuscript has a 'Clinical Report' heading, the user is submitting a case report — use `--article-type case-report`."

### CUSTOM_GPT_INSTRUCTIONS.md changes

In the Workflow Phase 3 (pick the journal slug), add a new substep:

```
**Pick the article type.** Match against:

- `research` (default) — original research, cohort studies, in vitro studies, RCTs
- `case-report` — single-patient or small-series clinical descriptions
- `technique` — step-by-step procedure or technique articles
- `systematic-review` — systematic reviews and meta-analyses

If the user's request doesn't make the type obvious, ask. If the
manuscript already has a "Clinical Report" or "Technique" heading,
that's a strong signal.
```

In Phase 4, update the example invocation:

```bash
python /mnt/data/skill/scripts/format_manuscript.py \
  /mnt/data/<manuscript>.docx \
  --references /mnt/data/<refs>.<ext> \
  --journal <slug> \
  --article-type <research|case-report|technique|systematic-review> \
  --out-dir /mnt/data/ \
  [--cover-letter --editor "Dr. ..."]
```

Add to edge cases: "Five journals (JPD, JERD, JOMI, COIR, IJP) support all 4 article types. The other six (JDR, JADA, J Dent, J Periodontol, J Endod, Oper Dent) only support `research` in this version — passing a different type returns a clear 'not yet populated' error and the user should pick a journal that supports their type, or ask Pablo to populate it."

**Step 1:** Make all three doc edits.

**Step 2:** Verify the docs render and run pytest one last time.

```bash
/opt/homebrew/bin/python3.13 -m pytest 2>&1 | tail -3
```

Expected: ~210 passed (146 v1 + ~60 new v1.1 tests).

**Step 3: Commit**

```bash
git add README.md SKILL.md chatgpt/CUSTOM_GPT_INSTRUCTIONS.md
git commit -m "docs: document --article-type flag and 4 supported types

README adds article-type to the natural-language examples and the manual
CLI block, plus a 'Supported article types' callout noting which
journals are fully populated vs research-only.

SKILL.md adds a Phase-1 substep: identify article type from the user's
request, default to research, pass via --article-type.

CUSTOM_GPT_INSTRUCTIONS.md adds a 'pick the article type' substep to
Phase 3, updates the Phase-4 example invocation, and notes which 5 of
the 11 journals are fully populated (JPD/JERD/JOMI/COIR/IJP) vs the 6
research-only journals."
```

---

## Task 13: Re-build ChatGPT zip; push everything

**Files:** none modified.

**Step 1:** Re-run `chatgpt/build_zip.sh`.

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
./chatgpt/build_zip.sh
```

Expected: zip rebuilds with the new YAMLs and `format_manuscript.py`. Size grows slightly (more YAML content).

**Step 2:** Spot-check by extracting and running against the case-report fixture from outside the repo:

```bash
TMP=$(mktemp -d)
unzip -q manuscript_formatter.zip -d "$TMP/skill"
mkdir "$TMP/out"
/opt/homebrew/bin/python3.13 "$TMP/skill/scripts/format_manuscript.py" \
    tests/fixtures/clinical_report_manuscript.docx \
    --references tests/fixtures/sample_zotero.json \
    --journal jpd \
    --article-type case-report \
    --out-dir "$TMP/out"
cat "$TMP/out/clinical_report_manuscript-jpd-report.md"
```

Expected: clean run, report mentions Clinical Report (not over-limit warnings for IMRAD sections).

**Step 3:** Final pytest run.

```bash
/opt/homebrew/bin/python3.13 -m pytest 2>&1 | tail -3
```

Expected: all green.

**Step 4:** Push.

```bash
git status --short    # expect clean
git log --oneline | head -15
git push
```

**Step 5:** Remind in the final commit message (or session summary) that the Custom GPT owner needs to:

1. Re-run `./chatgpt/build_zip.sh` (already done in step 1; the new zip is ready).
2. Upload the new `manuscript_formatter.zip` to the Custom GPT's Knowledge (replacing the old).
3. Re-paste the updated `CUSTOM_GPT_INSTRUCTIONS.md` into the Instructions field.

That's documented in `docs/maintainer-notes.md` already — no doc change needed, just a heads-up in chat.

---

## Verification before declaring complete

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
pytest 2>&1 | tail -3            # ~210 passed expected
git status --short                # nothing
git log --oneline | head -15      # ~12 v1.1 commits since the design doc
./chatgpt/build_zip.sh            # builds cleanly
```

Then user re-uploads the rebuilt zip + re-pastes instructions into the
published Custom GPT.

## Risks summary (from design)

- **Schema migration churn**: 11 YAMLs change. Mitigated by making the
  loader hard-fail on legacy flat YAMLs (with a clear error) so we
  catch any miss immediately.
- **Existing tests**: most need a `article_type="research"` kwarg
  passed. Done in Task 2.
- **TODO markers in JERD/JOMI/COIR/IJP**: word-limit guesses.
  Failure mode is benign (validator over-limit warning where the user
  expected no warning); user fixes a single YAML field.
- **Custom GPT users will need to re-upload the zip**. Documented in
  `docs/maintainer-notes.md` and surfaced in chat after Task 13.
