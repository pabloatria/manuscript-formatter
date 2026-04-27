# manuscript-formatter — Design

> **Historical implementation log.** This is the plan that was executed when the feature was built. Useful for understanding the design rationale or for forking the project; **not needed to use or self-host the skill** — see [README](../../README.md) and [`chatgpt/SETUP.md`](../../chatgpt/SETUP.md) for that.

**Date:** 2026-04-26
**Status:** Approved (brainstorming session with Claude Code)
**Author:** Pablo Atria

## Problem

A working dental researcher writes manuscripts in one journal's house style
(typically JPD), then needs to retarget them for resubmission elsewhere
(JOMI, COIR, JDR, JADA, etc.) when papers are rejected or strategy changes.
Reformatting between journals is mechanical drudgery that nonetheless
takes hours: section headings rename, abstract restructures, word counts
must be re-checked, references must be re-styled (Vancouver vs. AMA vs.
Harvard variants), title pages reformat, cover letters rewrite. Doing it
by hand introduces errors and discourages multi-journal targeting.

## Goals

- Take a finished `.docx` manuscript and emit a journal-ready `.docx` for
  any of 11 targeted dental journals.
- **Never edit the author's prose.** Move text, relabel headings, swap
  reference list, generate cover letter — but body paragraphs are
  byte-identical to the input.
- Report what's wrong (over-limit abstracts, missing required sections)
  rather than silently truncating.
- Same config-driven pattern as `pubmed-brief` and the user's
  DentalPrecios country configs — adding a new journal is one YAML file.

## Non-goals

- Generating prose from raw data (out — clinical writing voice is
  irreplaceable; that's exactly what the author wants to write themselves).
- Translating between languages (separate concern).
- Tracked-changes preservation (the skill operates on clean text; the user
  re-applies tracked changes if needed).
- Submission-portal automation (journals require human attestation).
- Image/figure file processing (figure references and inline images pass
  through untouched, but the skill does not reformat figure files).

## Audience

A clinical researcher (faculty, fellow, resident) submitting peer-reviewed
work. Comfortable with terminal commands, comfortable with reference
managers (EndNote primary, Zotero / Mendeley acceptable), uncomfortable
with mechanical reformatting drudgery.

## Workflow (one-line)

User hands the skill **3 inputs** — manuscript `.docx` + reference-manager
export + target journal slug — and it writes **3 outputs** in
`~/Downloads/`:

1. Reformatted `.docx` (prose byte-identical, structure rearranged,
   references regenerated)
2. Markdown validation report (word counts vs limits, structure warnings,
   audit trail)
3. Cover letter `.docx` (auto-filled fields + a clear `[NOVELTY]`
   placeholder for editorial judgment)

## Inputs (CLI)

```bash
python3 scripts/format_manuscript.py draft.docx \
  --references library.json \      # or library.bib or library.xml or library.ris
  --journal jpd \
  --out-dir ~/Downloads/ \
  [--cover-letter --editor "Dr. Carlos Aparicio"]
```

Reference-manager intake paths:
- **Zotero** → CSL JSON export (`.json`). Citations in the `.docx` are
  Zotero CSL field codes (parseable from the doc XML).
- **Mendeley** → BibTeX (`.bib`). Citations in the `.docx` are CSL field
  codes embedded by Mendeley's CWYW plugin.
- **EndNote** → XML or RIS library export (`.xml` / `.ris`). User must
  first run EndNote's *Convert Citations and Bibliography → Convert to
  Plain Text* in Word; the skill matches plain-text citations against the
  exported library by author+year+title fuzzy match.

All three converge to internal CSL JSON. `citeproc-py` then renders the
bibliography from CSL JSON + the journal's CSL style file.

## Outputs

1. `<basename>-<journal>.docx`
   - Body paragraphs byte-identical to input (asserted by self-test).
   - Headings renamed/reordered to match journal config.
   - Reference list rebuilt from CSL JSON in target style.
   - Inline citations re-rendered (numbered Vancouver vs. author-year vs.
     bracketed AMA, depending on journal style).
2. `<basename>-<journal>-report.md`
   - Per-section word counts vs limits (✅ within / ⚠️ over).
   - Missing required sections flagged.
   - Heading rename audit trail.
   - Citation match warnings (entries that couldn't be confidently mapped).
3. `<basename>-<journal>-cover-letter.docx` (only if `--cover-letter`)
   - Fields auto-populated: title, authors, journal, methods one-liner,
     results one-liner.
   - `[NOVELTY: 1–2 sentences]` placeholder for the author to fill in.
   - Editor name from `--editor` or `[EDITOR]` placeholder.

## Sample validation report

```markdown
# JPD Submission Report — splints-study.docx

✅ Required sections present (all 6)
⚠️ Abstract: 287 words (limit 250) — 37 over
✅ Introduction: 612 words
✅ Material and Methods: 1,103 words
✅ Discussion: 1,248 words
⚠️ Total: 5,121 words (suggested ≤5,000)
✅ References: 42 entries reformatted to JPD Vancouver style
ℹ️ Heading "Background" renamed → "Statement of Problem"
ℹ️ Heading "Conclusion" renamed → "Conclusions"

# Cover letter
- Editor: Dr. Carlos Aparicio
- Generated: yes (~/Downloads/splints-jpd-cover-letter.docx)
- ⚠️ Fill the [NOVELTY] placeholder before sending
```

## Architecture

Same pattern as `pubmed-brief`. Config-driven, one YAML per journal.

```
manuscript-formatter/
├── SKILL.md              # workflow Claude follows when triggered
├── README.md             # public docs, MIT badges, install + use
├── LICENSE               # MIT
├── SECURITY.md           # threat model, dependencies
├── install.sh            # macOS/Linux dependency installer
├── examples/
│   └── splints-jpd-to-jomi/   # real before/after for the user's splints study
├── docs/
│   └── plans/                 # design + implementation plans
└── scripts/
    ├── format_manuscript.py   # main CLI entry
    ├── reference_renderer.py  # citeproc-py + CSL files
    ├── docx_helpers.py        # python-docx utilities
    ├── validators.py          # word counts, structure checks
    ├── cover_letter.py        # cover letter generator
    ├── csl/                   # bundled CSL style files (citationstyles.org, MIT)
    │   ├── journal-of-prosthetic-dentistry.csl
    │   ├── journal-of-oral-implantology.csl
    │   └── ... (11 styles, one per supported journal)
    └── journals/              # per-journal configs
        ├── jpd.yaml
        ├── jomi.yaml
        ├── coir.yaml
        ├── jdr.yaml
        ├── jada.yaml
        ├── j-dent.yaml
        ├── int-j-prosthodont.yaml
        ├── j-periodontol.yaml
        ├── j-endod.yaml
        ├── oper-dent.yaml
        └── jerd.yaml
```

## Each `journals/<slug>.yaml`

```yaml
name: Journal of Prosthetic Dentistry
abbreviation: J Prosthet Dent
sections:
  - canonical: abstract
    display: Abstract
    aliases: [Abstract, Summary]
    word_limit: 250
    required: true
  - canonical: introduction
    display: Statement of Problem
    aliases: [Introduction, Background, Statement of Problem]
    word_limit: null
    required: true
  - canonical: purpose
    display: Purpose
    aliases: [Purpose, Aim, Objective]
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
  format: structured           # or unstructured
  subsections:
    - Statement of Problem
    - Purpose
    - Material and Methods
    - Results
    - Conclusions
  word_limit: 250
total_word_limit: 5000
reference_style: journal-of-prosthetic-dentistry.csl
title_page:
  separate_file: true
  required_blocks: [authors, affiliations, corresponding_author, conflicts, funding, irb]
figures:
  embedded: false              # uploaded separately
  legend_format: "Figure {n}. {caption}"
  numbering: "Figure {n}"
guidelines:
  font: "Times New Roman"
  font_size: 12
  line_spacing: 2.0
  margins_cm: 2.54
  page_numbers: true
cover_letter_template: |
  Dear {editor},

  We submit for your consideration our manuscript titled "{title}", which
  reports {methods_summary}. Our findings — {results_summary} — represent
  [NOVELTY: 1-2 sentences explaining what's new and why this journal is the
  right home].

  {authors_summary}. The manuscript has not been published or submitted
  elsewhere; all authors have approved the submission. Conflicts of interest
  and funding sources are disclosed on the title page.

  Sincerely,
  {corresponding_author}
```

## Text-preservation guarantee

This is the central trust-building feature.

- python-docx represents body content as `Paragraph` objects with `runs`.
- The skill **moves Paragraph objects** (whole, by reference) and
  **rewrites Heading text + style**. It never re-types body text.
- The reference list is **rebuilt from the CSL JSON**, not re-parsed from
  the original reference list. This is safer (canonical source) and
  guarantees the bibliography is fresh.
- A self-test compares the input doc's body paragraphs (excluding headings,
  citations, and bibliography) against the output's body paragraphs and
  asserts byte equality. The test fails CI if any prose changed.

## Risks

- **Citation field-code parsing varies by reference manager.**
  - Zotero/Mendeley CSL fields are well-documented and parseable.
  - EndNote field codes are proprietary; the skill works around this by
    requiring EndNote users to "Convert to Plain Text" before running.
  - This is the most likely place to hit edge cases. Plan: ship v1 with
    Zotero clean, document EndNote/Mendeley caveats, iterate.
- **CSL style coverage.** ~10,000 styles exist in the official repo; we
  bundle 11. Users targeting other journals point the YAML at any CSL file
  from citationstyles.org.
- **Heading detection requires Word styles.** If the draft has bolded
  paragraph text instead of `Heading 1` style, the parser misses it. The
  skill detects this and asks the user to apply heading styles before
  re-running.
- **Fuzzy citation matching.** EndNote plain-text mode requires the skill
  to match `(Smith, 2024)` or `[14]` to a library entry by author+year+
  partial title. Will mis-match occasionally; the report flags every
  uncertain match.

## Tech stack

- Python 3.10+
- `python-docx` — Word `.docx` read/write
- `citeproc-py` — render bibliography from CSL JSON + CSL style file
- `bibtexparser` — parse Mendeley `.bib`
- `pyyaml` — journal configs
- `rapidfuzz` — fuzzy heading matching, fuzzy citation matching for
  EndNote plain-text mode
- Standard library: `xml.etree` for EndNote XML and `.docx` field-code XML

All available via `pip`. No native dependencies, no API keys, no costs.

## Distribution

Same model as `pubmed-brief`:
- Public GitHub repo (`pabloatria/manuscript-formatter`).
- MIT licensed.
- One-line `git clone` install into `~/.claude/skills/manuscript-formatter`.
- `install.sh` handles dependency installation with the macOS PEP 668 fallback.
- ChatGPT distribution path is **not** in scope for v1 — the skill mutates
  Word files, which Code Interpreter can do but with awkward Knowledge
  upload UX. Revisit after v1 lands.

## Out of scope for v1 (potential v2)

- Tracked-changes preservation
- Spanish ↔ English translation
- ChatGPT Custom GPT distribution
- Submission-portal automation
- Image/figure file reformatting
- Auto-pulling references from a Zotero library by collection ID (instead
  of requiring an export)
- Tools for the user to author new YAML configs interactively

## Open questions (resolved during brainstorm)

| Question | Answer |
|---|---|
| Workflow shape | A — reformat existing manuscript |
| Input format | `.docx` only |
| Reference handling | Reference manager (Zotero / Mendeley / EndNote) |
| Transformations | All four core (refs, structure, abstract, word counts) + all four optional (title page, figures, guidelines, cover letter) |
| Text editing | Skill must NOT change any author prose |
| Journal coverage | 10 + JERD = 11 |
| Cover letter | Auto-fill what we can, `[NOVELTY]` placeholder |
