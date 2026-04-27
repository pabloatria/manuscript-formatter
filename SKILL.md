---
name: manuscript-formatter
description: Reformat a finished .docx manuscript to match the formatting requirements of a specific dental journal — without changing your prose. Supports 11 dental journals (JPD, JDR, JADA, J Dent, J Endod, J Periodontol, JERD, JOMI, COIR, Int J Prosthodont, Operative Dentistry). Renders citations from any reference manager (Zotero JSON, Mendeley BibTeX, EndNote XML/RIS) into the target journal's CSL style, validates word/abstract/figure/table limits against the journal's YAML config, and writes a reformatted .docx plus a validation report and an optional cover-letter draft. Use this skill whenever the user asks to reformat, restyle, or convert a manuscript for journal submission — including phrases like "reformat my manuscript", "convert this draft to JPD style", "format for JOMI", "prepare submission to JDR", "change reference style", "submit to J Periodontol", "make this fit the COIR format", "apply the journal style", or names a specific dental journal alongside a .docx file.
---

# Manuscript Formatter

Reformat a finished .docx manuscript to match a target dental journal's submission requirements without touching the author's prose. Output: a reformatted .docx, a Markdown validation report, and (optionally) a cover-letter draft.

## When to use

- The user has a finished or near-finished .docx manuscript and wants to format it for a specific dental journal.
- The user names a journal (JPD, JDR, JADA, J Dent, J Endod, J Periodontol, JERD, JOMI, COIR, Int J Prosthodont, Operative Dentistry) and asks for reformatting, restyling, or "convert to X style."
- The user wants to know which sections of their manuscript are over the journal's word, abstract, figure, or table limits.
- The user wants a cover-letter draft alongside the reformatted manuscript.

Do not use for: writing the manuscript from scratch, copy-editing prose, translating between languages, or splicing a rendered bibliography into the body of the .docx (that's a v1 limitation — see Edge cases).

## First-time setup (any machine, any OS)

The skill needs six Python packages: `python-docx`, `citeproc-py`, `bibtexparser`, `pyyaml`, `rapidfuzz`, `defusedxml`. On the first run on a new machine, install them silently before anything else:

```bash
python3 -m pip install --quiet python-docx citeproc-py bibtexparser pyyaml rapidfuzz defusedxml 2>/dev/null || \
python3 -m pip install --quiet --break-system-packages python-docx citeproc-py bibtexparser pyyaml rapidfuzz defusedxml
```

This handles both clean Pythons and newer macOS Homebrew/system Pythons that block global installs by default (PEP 668).

Quick import check before running:
```bash
python3 -c "import docx, citeproc, bibtexparser, yaml, rapidfuzz, defusedxml; print('ok')"
```

If this fails, surface the error to the user — don't proceed with reformatting.

## Workflow

The skill runs in four phases. Execute them in order — do not skip validation and do not invent journal config from your training data.

### Phase 1 — Validate inputs

Before invoking the script, confirm:

1. The manuscript path the user gave you exists and ends in `.docx`. If they pointed at a `.doc` (legacy Word), tell them to re-save as `.docx` first.
2. The references file exists. Accepted: `.json` (Zotero CSL JSON), `.bib` (Mendeley BibTeX), `.xml` (EndNote XML), or `.ris` (RIS — EndNote / Papers / generic).
3. The journal slug is one of the 11 supported:
   - `jpd` — Journal of Prosthetic Dentistry
   - `jdr` — Journal of Dental Research
   - `jada` — Journal of the American Dental Association
   - `j-dent` — Journal of Dentistry
   - `j-endod` — Journal of Endodontics
   - `j-periodontol` — Journal of Periodontology
   - `jerd` — Journal of Esthetic and Restorative Dentistry
   - `jomi` — Journal of Oral and Maxillofacial Implants
   - `coir` — Clinical Oral Implants Research
   - `int-j-prosthodont` — International Journal of Prosthodontics
   - `oper-dent` — Operative Dentistry

If the journal isn't on the list, ask the user which of these is closest — do not silently fall back.

4. **Identify the article type.** Pick one of:
   - `research` (default) — original research, in vitro studies, RCTs, cohort studies, materials science
   - `case-report` — single-patient or small-series clinical descriptions ("we report a case of…")
   - `technique` — step-by-step procedure / dental technique articles
   - `systematic-review` — systematic reviews and meta-analyses (PRISMA / PROSPERO)

   If the user's request doesn't make the type obvious, ask. If the manuscript already has a "Clinical Report" or "Technique" or "Search Strategy" heading, those are strong signals. If the user just says "reformat for X journal" without specifying type, default to `research`.

   **Coverage:** JPD, JERD, JOMI, COIR, and Int J Prosthodont support all 4 types. The other 6 journals only support `research` in v1.1 — passing a different `--article-type` returns a clear "not yet supported for this journal" error.

### Phase 2 — Run the formatter

```bash
SKILL_DIR="<absolute path to this skill folder>"

python3 "$SKILL_DIR/scripts/format_manuscript.py" \
  "<absolute path to manuscript.docx>" \
  --references "<absolute path to references file>" \
  --journal "<slug>" \
  --article-type "<research|case-report|technique|systematic-review>" \
  --out-dir "$HOME/Downloads" \
  [--cover-letter --editor "Dr. Last Name"]
```

`--article-type` defaults to `research` if omitted. Pass it explicitly when the user submits anything other than original research.

The script writes three files into `--out-dir`:

- `<basename>-<journal>.docx` — reformatted manuscript
- `<basename>-<journal>-report.md` — validation + audit-trail Markdown
- `<basename>-<journal>-cover-letter.docx` — only if `--cover-letter` was passed

If the script raises `JournalConfigError`, `ReferenceFormatError`, or `FileNotFoundError`, surface the message verbatim — they're already user-friendly.

### Phase 3 — Surface the report

Read the generated `*-report.md` and quote the contents back to the user, especially:

- **Over-limit warnings** — abstract too long, body word count exceeds the journal's limit, too many figures/tables. These are the things the user actually has to act on before submitting.
- **Heading-style warnings** — if the report says "no headings detected," the user's manuscript is missing Word `Heading 1..9` styles. Tell them to apply heading styles in Word and re-run.
- **Reference-match warnings** — citations in the prose that didn't match any entry in the references file. Usually means the citation key in the .docx text differs from the reference manager's title or author.

Do not paraphrase the report — quote the relevant sections. The user wants to see exactly what flagged.

### Phase 4 — Cover-letter follow-up

If the user passed `--cover-letter`, the generated cover-letter .docx contains a `[NOVELTY]` placeholder where the user needs to write the 1–2 sentence novelty pitch (the part only the author can write — what's new about this study). Remind the user to fill this in before sending.

If `--editor` was omitted, the letter contains an `[EDITOR]` placeholder too. Same reminder.

## Edge cases

- **EndNote field codes:** EndNote embeds proprietary field codes in the .docx that aren't parseable without EndNote installed. If the user is on EndNote, tell them to run **Convert Citations and Bibliography → Convert to Plain Text** in Word first, then re-export. The skill matches plain-text citations against the .xml/.ris export by author + year + title fuzzy match. Without the plain-text conversion, the citation matcher will report most citations as unmatched.

- **Heading detection requires Word styles:** The validator detects sections (Abstract, Introduction, Methods, etc.) by Word's built-in `Heading 1..9` paragraph styles — not by bold text or font size. If the report says "no headings detected" or section word counts are missing, the manuscript was authored with manual formatting instead of styles. Tell the user to apply heading styles in Word (Home → Styles → Heading 1) and re-run.

- **Some journals fall back to Vancouver CSL:** The current bundle uses `vancouver.csl` as the rendering style for `jomi`, `int-j-prosthodont`, and `jerd` because the official CSLs aren't on the Zotero CSL repository. This is expected behavior, not a bug. The reference formatting will be correct Vancouver-style numeric output (which all three journals accept); the journal-specific YAML still drives word/figure/table limits and section names.

- **Body prose is byte-identical:** The skill explicitly does not edit the author's prose. The body of the input and output .docx are identical text content (verified by 22 cross-journal tests). The reformatting is structural: heading styles, page setup, line spacing, citation rendering, and validation — never the words.

- **Bibliography not spliced into output:** v1 limitation. The skill loads the references for citation matching and validation, and renders the bibliography for the report.md, but does not currently splice the rendered bibliography list back into the output .docx. The reference list in the output .docx is unchanged from the input. This is documented in the report.

## Customization the user might request

- **Add a new journal:** Drop a YAML config in `scripts/journals/<slug>.yaml` and a CSL in `scripts/csl/<slug>.csl`. Mirror the structure of any existing YAML (e.g., `scripts/journals/jpd.yaml`) — the loader just reads it.
- **Change word-count or figure/table limits for a journal:** Edit the limits block in `scripts/journals/<slug>.yaml`. No code changes needed.
- **Change the cover-letter wording:** Edit the `cover_letter_template:` block inside the journal's YAML. Each journal carries its own template so JPD's letter can sound different from JDR's.
- **Different output directory:** Pass `--out-dir` to the script. Defaults to `~/Downloads/`.
