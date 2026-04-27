# Article-Type Support — v1.1 Design

**Date:** 2026-04-26
**Status:** Approved
**Author:** Pablo Atria (with Claude Code, in auto mode)

## Problem

`manuscript-formatter` v1 assumes one structure for every manuscript: IMRAD
original research. In reality dental journals publish at least four
distinct article types per submission portal — each with its own section
order, abstract format, and word/figure limits:

- **Research / Clinical Science Article** (current default)
- **Clinical Report** (case report)
- **Dental Technique**
- **Systematic Review and Meta-Analysis**

A user submitting a clinical report or technique article today gets a
mis-formatted output: the skill fuzzy-matches "Clinical Report" or
"Technique" against IMRAD aliases (Methods/Results) at low confidence,
either renaming heading text incorrectly or leaving the heading alone but
flagging missing required sections that the article type doesn't have.

## Goals

- User declares article type via a new `--article-type` CLI flag.
- Defaults to `research` so every existing v1 invocation keeps working.
- Each journal YAML grows an `article_types:` map; the existing single
  `sections`/`abstract`/`total_word_limit`/`cover_letter_template` block
  moves into the per-type block.
- Five journals fully populated with all 4 types: JPD (verified live),
  JERD, JOMI, COIR, IJP (best-effort with `# TODO verify` markers).
- Other six journals stay research-only; the other 3 type blocks get
  empty placeholders so adding them later is a YAML edit, not a code
  change.

## Non-goals

- No automatic article-type detection (deferred to v2). User declares.
- No automatic PRISMA/PROSPERO scaffolding for systematic reviews. User
  writes those sections; the skill validates structure + word counts.
- No bibliography splicing into the output `.docx` (still v1.1+ work
  separate from this).
- No reader-tip / Tips From Our Readers article type (out of scope per
  user direction).

## Audience

Same as v1: clinician-researchers submitting peer-reviewed work. The
new flag makes the skill correctly handle case reports and techniques,
which v1 silently mis-formatted.

## JPD reference data (verified live)

Source: <https://www.sciencedirect.com/science/journal/00223913/publish/guide-for-authors>
(fetched 2026-04-26).

### Research / Clinical Science Article

```
Body sections (in order):
  Abstract → Clinical Implications → Introduction → Material and Methods →
  Results → Discussion → Conclusions

Abstract: structured, ≤400 words.
  Subsections: Statement of Problem, Purpose, Material and Methods,
               Results, Conclusions
  (Note: Statement of Problem and Purpose are abstract subsections only,
   NOT body section headings — corrects a v1 bug in jpd.yaml that aliased
   body Introduction → Statement of Problem.)

Total word limit: ~3000 (10-12 double-spaced pages).
Figures/tables: max 12 illustrations.
```

### Clinical Report

```
Body sections:
  Abstract → Introduction → Clinical Report → Discussion (optional) → Summary

Abstract: unstructured, single paragraph (~150 words).
Total word limit: ~1250 (4-5 double-spaced pages).
Figures/tables: max 8 illustrations.

The "Clinical Report" section is the case description with H2 subsections
typically covering patient history, examination/findings, treatment, and
outcome. The skill leaves H2 subsection headings unchanged — they are
free-form per author preference.
```

### Dental Technique

```
Body sections:
  Abstract → Introduction → Technique → Discussion (optional) → Summary

Abstract: unstructured, single paragraph (~150 words).
Total word limit: ~1250 (4-5 double-spaced pages).
Figures/tables: max 8 illustrations.

The "Technique" section is often numbered step-by-step instructions; H2
subsections are author-driven and left unchanged.
```

### Systematic Review and Meta-Analysis

```
Body sections (in order):
  Abstract → Introduction → Methods → Results → Discussion → Conclusions
  (Note: "Methods" — singular — not "Material and Methods" as in research
   articles. JPD's guide is internally inconsistent on this; we preserve
   the guide's verbatim wording.)

Abstract: structured, ≤400 words, same subsections as research.
Total word limit: not capped.
Figures/tables: as needed.
```

## Other 4 fully-populated journals (best-effort with TODOs)

For JERD, JOMI, COIR, IJP — values marked `# TODO verify` in the YAMLs
are my best estimates from prior knowledge; the user (or a future
maintainer) can correct them with one-line YAML edits. Schema and
section logic are correct; only word-limit numbers and one or two
journal-specific subsections are uncertain.

| Journal | Research | Case Report | Technique | Systematic Review | Notes |
|---|---|---|---|---|---|
| JERD | 4000w | 2000w | 2000w | not capped | "Clinical Significance" section in research |
| JOMI | 4500w | 2000w | 2000w | not capped | JPD-like taxonomy; tighter limits |
| COIR | 4000w | 1500w (short comm.) | 2000w | 7500w | Case reports rare; called "Short Communication" |
| IJP | 4000w | 1500w | 2000w | not capped | JPD-like; "Clinical Implications" matches JPD |

## The other 6 journals (research-only-with-placeholders)

JDR, JADA, J Dent, J Periodontol, J Endod, Oper Dent: each YAML grows
an `article_types:` map with the existing fields moved under
`research:`, plus three placeholder blocks:

```yaml
case-report:
  # TODO populate from journal's author guidelines
  sections: []
  abstract: { format: unstructured, word_limit: null }
  total_word_limit: null
  cover_letter_template: ""
technique:
  # TODO populate
  sections: []
  ...
systematic-review:
  # TODO populate
  sections: []
  ...
```

The loader treats an empty `sections: []` as "not yet supported" — the
CLI exits with a clear message: *"<journal> does not yet declare a
section structure for article type <type>. Either pick a different
journal/type or add the missing block to the YAML config."*

## Schema migration

### Before (v1)

```yaml
# scripts/journals/jpd.yaml
name: ...
abbreviation: ...
sections: [...]              # IMRAD
abstract: {...}
total_word_limit: 5000
cover_letter_template: |...
reference_style: ...
title_page: {...}
figures: {...}
guidelines: {...}
```

### After (v1.1)

```yaml
# scripts/journals/jpd.yaml
name: ...
abbreviation: ...
reference_style: ...         # journal-level (same across types)
title_page: {...}
figures: {...}
guidelines: {...}
article_types:
  research:
    sections: [...]
    abstract: {...}
    total_word_limit: 3000
    cover_letter_template: |...
  case-report:
    sections: [...]
    abstract: {...}
    total_word_limit: 1250
    cover_letter_template: |...
  technique:
    sections: [...]
    ...
  systematic-review:
    sections: [...]
    ...
```

## Code touchpoints

1. **`scripts/journal_config.py`** — `load_journal()` adds `article_type:
   str = "research"` parameter; returns a merged dict (journal-level +
   per-type block flattened). New `JournalConfigError` cases:
   - "article type '<x>' not in journal '<j>'" (typo / not declared)
   - "article type '<x>' for journal '<j>' has no sections — placeholder
     for future support; pick a different type or add the YAML block"
2. **`scripts/format_manuscript.py`** — adds `--article-type
   {research,case-report,technique,systematic-review}` flag with default
   `research`. Threads through to `load_journal()`.
3. **`scripts/validators.py`, `cover_letter.py`, `docx_helpers.py`,
   `report.py`** — receive merged config; **no internal changes** since
   the per-type fields look identical to v1's flat fields after merging.
4. **All 11 journal YAMLs** — migrate to `article_types:` map. JPD +
   JERD/JOMI/COIR/IJP get all 4 types populated; the other 6 get
   research-only + 3 placeholders.
5. **`tests/test_journal_config.py`** — parametrize over
   (journal × article_type) combinations that are populated. Expect
   `JournalConfigError` for placeholder combinations.
6. **`tests/test_text_preservation_invariant.py`** — parametrize over
   article types too. v1 has 22 cases (11 journals × 2 invariants);
   v1.1 grows to ~40 (11 journals × 4 article types × 2 invariants,
   skipping placeholder combinations).
7. **New `tests/fixtures/clinical_report_manuscript.docx`** —
   programmatic fixture with "Clinical Report" heading, Introduction,
   short discussion, Summary. Confirms reformat keeps "Clinical
   Report" heading unchanged for `--article-type case-report` and
   produces a sensible result for JPD/JERD/JOMI/IJP.
8. **README + SKILL.md + chatgpt/CUSTOM_GPT_INSTRUCTIONS.md** —
   document the new flag and the 4 supported types. Custom GPT
   instructions add a Phase-3.5 step: ask the user the article type if
   ambiguous from their request.
9. **Maintainer note** in `docs/maintainer-notes.md` — re-run
   `chatgpt/build_zip.sh` and re-upload after this v1.1 lands.

## Risks

- **Schema migration churn.** All 11 YAMLs change structure. The fix
  is mechanical but visible in git diffs. Mitigated by writing a
  one-shot migration script (or just doing it by hand carefully — 11
  files is small).
- **Existing tests assume the v1 flat structure.** They need to update
  to call `load_journal(slug, article_type="research")` explicitly.
  Most tests should pass after this single-line update.
- **Heading aliases collide across types.** Example: "Discussion"
  appears in research, case-report, and technique. The fuzzy-match
  loop is per-type, so this isn't an issue — the matcher only sees the
  selected type's `sections` list.
- **Placeholder UX.** A user passing `--journal jdr --article-type
  technique` today would get a clear "not yet declared" error. Better
  than silent mis-formatting.
- **`# TODO verify` values.** The 4 best-effort journals' word limits
  are guesses. Failure mode is benign — the validator flags
  over-limit when a real submission is over the guess limit, the user
  notices the limit is wrong, and updates one YAML field. Unlike the
  v1 SoP-in-body bug, this can't silently mis-format prose.

## Implementation order

1. Migrate `jpd.yaml` to `article_types:` shape with all 4 types using
   verified values; preserve the journal-level fields.
2. Update `scripts/journal_config.py` to accept `article_type` and
   return merged config; raise on placeholder combos.
3. Update existing tests to pass `article_type="research"` explicitly.
4. Add the `--article-type` CLI flag.
5. Add tests for non-research types (clinical-report fixture, expect
   "Clinical Report" heading preserved by reformat for `case-report`).
6. Migrate the other 4 fully-covered journals (JERD, JOMI, COIR, IJP)
   with TODO markers.
7. Migrate the 6 research-only journals with placeholder blocks.
8. Update the cross-journal invariant test to parametrize over types.
9. Update README + SKILL.md + CUSTOM_GPT_INSTRUCTIONS.md.
10. Re-run `chatgpt/build_zip.sh`.
11. Push.

Estimated: 10-12 commits, slightly bigger than the original Tasks
16–18 because the schema migration touches every YAML and updates
every test in the loader area.

## Out of scope (still)

- Auto-detection of article type from manuscript content.
- PRISMA flowchart / PROSPERO validation for systematic reviews.
- Reader-tip article type.
- Bibliography splicing into output `.docx`.
- Spanish ↔ English translation.
