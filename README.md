# manuscript-formatter

> Reformat finished .docx manuscripts for any of 11 dental journals — without touching your prose.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Claude Skill](https://img.shields.io/badge/Claude-Skill-D97757)](https://docs.claude.com/en/docs/agents-and-tools/agent-skills)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg)](https://www.python.org/downloads/)
[![Security](https://img.shields.io/badge/security-audited-success.svg)](./SECURITY.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/pulls)

You finished the manuscript. Now the journal asks for 250-word abstracts instead of 300, Vancouver-numeric citations instead of author–year, headings in a specific order, and a cover letter on top. `manuscript-formatter` does the structural reformat — page setup, headings, citation rendering, word/figure/table validation, optional cover letter — and leaves your prose byte-identical to what you wrote.

---

## What you get

For any input `.docx` and a target journal slug, you get three outputs in `~/Downloads/`:

- **`<basename>-<journal>.docx`** — reformatted manuscript with the journal's heading styles, page setup, and citation rendering. Prose is unchanged.
- **`<basename>-<journal>-report.md`** — validation + audit trail. Section-by-section word counts, over-limit flags, unmatched citations, applied transformations.
- **`<basename>-<journal>-cover-letter.docx`** *(optional)* — cover-letter draft populated from the journal's template, with `[NOVELTY]` and `[EDITOR]` placeholders left for you.

### Supported journals (v1)

| Slug | Journal |
|---|---|
| `jpd` | Journal of Prosthetic Dentistry |
| `jdr` | Journal of Dental Research |
| `jada` | Journal of the American Dental Association |
| `j-dent` | Journal of Dentistry |
| `j-endod` | Journal of Endodontics |
| `j-periodontol` | Journal of Periodontology |
| `jerd` | Journal of Esthetic and Restorative Dentistry |
| `jomi` | Journal of Oral and Maxillofacial Implants |
| `coir` | Clinical Oral Implants Research |
| `int-j-prosthodont` | International Journal of Prosthodontics |
| `oper-dent` | Operative Dentistry |

## Install

**Requirements:** Python 3.10+ and Claude Code or Claude Desktop with skill support enabled.

```bash
# 1. Clone into your Claude skills directory
git clone https://github.com/pabloatria/manuscript-formatter.git ~/.claude/skills/manuscript-formatter

# 2. Install Python dependencies
cd ~/.claude/skills/manuscript-formatter
./install.sh
```

The installer handles `python-docx`, `citeproc-py`, `bibtexparser`, `pyyaml`, and `rapidfuzz` (with the `--break-system-packages` workaround for newer macOS Pythons).

## Use it (Claude)

In Claude Desktop or Claude Code, just ask naturally:

```
"Reformat my splints draft for JOMI"
"Convert this manuscript to JDR style"
"Format ~/Downloads/draft.docx for J Periodontol with cover letter"
"Apply COIR style and tell me what's over the word limit"
"Prepare this for submission to JPD using my Zotero export"
```

The skill auto-triggers, runs the formatter, and surfaces the validation report back to you. Takes a few seconds.

## Use it without Claude (manual mode)

```bash
python3 scripts/format_manuscript.py \
  ~/Downloads/draft.docx \
  --references ~/Downloads/library.json \
  --journal jpd \
  --out-dir ~/Downloads/ \
  --cover-letter \
  --editor "Dr. Last Name"
```

Flags:

- `manuscript` *(positional, required)* — the input `.docx`.
- `--references` *(required)* — path to a Zotero `.json`, Mendeley `.bib`, or EndNote `.xml` / `.ris` export.
- `--journal` *(required)* — one of the 11 slugs in the table above.
- `--out-dir` — default `~/Downloads/`.
- `--cover-letter` — also generate the cover-letter draft.
- `--editor` — name to fill into the cover letter's salutation. Leaves the `[EDITOR]` placeholder if omitted.

## What the skill does NOT do

Be honest about scope:

- **Does not change your prose.** The body of your manuscript is byte-identical between input and output. Verified by 22 cross-journal regression tests.
- **Does not splice the rendered bibliography back into the output `.docx`.** v1 limitation. References are loaded for validation and rendered into the report, but the bibliography section in the output `.docx` is unchanged from the input. Plan to re-paste the rendered list yourself, or wait for v2.
- **Does not translate Spanish ↔ English.** Separate concern.
- **Does not submit to the journal.** That requires human attestation.
- **Does not preserve tracked changes or comments.** Operates on clean text. Accept or reject all changes before running, and re-apply comments afterward if needed.
- **Does not copy-edit.** Word-count validation flags overruns; it doesn't shorten your sentences.

## Reference manager support

| Manager | Format | Status |
|---|---|---|
| Zotero | CSL JSON (`.json`) | First-class |
| Mendeley | BibTeX (`.bib`) | First-class |
| EndNote | XML or RIS (`.xml`, `.ris`) | First-class with caveat — see below |
| Papers / generic | RIS (`.ris`) | Best-effort via the RIS parser |

**EndNote caveat:** EndNote embeds proprietary field codes in the `.docx` that aren't parseable without EndNote installed. Before running this skill on an EndNote-authored manuscript, run **Convert Citations and Bibliography → Convert to Plain Text** in Word, then export your library to `.xml` or `.ris`. The skill matches plain-text citations against the export by author + year + title fuzzy match.

## Customize

| Want | Change |
|---|---|
| Add a journal | New `scripts/journals/<slug>.yaml` + new `scripts/csl/<slug>.csl` |
| Change a journal's word/abstract/figure/table limits | Edit the limits block in `scripts/journals/<slug>.yaml` |
| Change a journal's cover-letter template | Edit the `cover_letter_template:` block in `scripts/journals/<slug>.yaml` |
| Different output directory | `--out-dir <path>` |
| Different editor name in the cover letter | `--editor "Dr. Last Name"` |

## Network requirements

**Zero.** This skill makes no network calls at runtime. All 11 CSL files are bundled in `scripts/csl/`. No API keys, no NCBI/Crossref calls, no telemetry. Safe on air-gapped or hospital-restricted networks.

## Limitations

- **v1 does not splice rendered bibliography into output `.docx`** (see above).
- **Three journals fall back to `vancouver.csl`** as the rendering style (`jomi`, `int-j-prosthodont`, `jerd`) because their official CSLs aren't on the Zotero CSL repository. The output is correct Vancouver-numeric — which all three accept — and the journal-specific YAML still drives word/figure/table limits.
- **Heading detection requires Word's built-in `Heading 1..9` paragraph styles.** Manuals with manually-bolded section titles produce a "no headings detected" warning. Apply heading styles in Word and re-run.
- **Tracked changes and comments are not preserved.** Accept/reject before running.

## Security

This skill makes zero network calls and no shell execution. It reads four file types from disk (the input `.docx`, the references export, the journal YAML, the bundled CSL) and writes up to three output files (`.docx`, `.md`, optional cover-letter `.docx`). No credentials, no telemetry, no elevated privileges.

Full threat model and dependency audit: see [`SECURITY.md`](./SECURITY.md). To report a vulnerability privately, use a GitHub Security Advisory rather than a public issue.

If you don't trust the dependencies, install in a venv:
```bash
python3 -m venv ~/.manuscript-formatter-venv && source ~/.manuscript-formatter-venv/bin/activate
pip install python-docx citeproc-py bibtexparser pyyaml rapidfuzz
```

## Repo structure

```
manuscript-formatter/
├── SKILL.md              # The workflow Claude follows when the skill triggers
├── README.md             # This file
├── LICENSE               # MIT
├── SECURITY.md           # Threat model, dependencies, vulnerability disclosure
├── install.sh            # macOS/Linux dependency installer
├── pyproject.toml
├── pytest.ini
├── docs/
│   └── plans/            # Design docs and implementation plans
├── scripts/
│   ├── format_manuscript.py     # CLI entrypoint
│   ├── journal_config.py        # YAML loader + JournalConfigError
│   ├── references.py            # Multi-format reference loader
│   ├── _bibtex_to_csl.py        # Mendeley BibTeX → CSL JSON
│   ├── _endnote_xml_to_csl.py   # EndNote XML → CSL JSON
│   ├── _ris_to_csl.py           # RIS → CSL JSON
│   ├── docx_helpers.py          # python-docx wrappers
│   ├── validators.py            # Word/abstract/figure/table limit checks
│   ├── report.py                # Markdown audit-trail writer
│   ├── cover_letter.py          # Cover-letter template renderer
│   ├── journals/                # 11 YAML configs (one per journal)
│   └── csl/                     # 11 bundled CSL files
└── tests/                # 146 pytest tests
```

## Contributing

PRs welcome. Especially interested in:

- v2 bibliography splicing (render CSL bibliography directly into the output `.docx`)
- Additional journals (any dental journal beyond the current 11)
- Native CSL files for `jomi`, `int-j-prosthodont`, `jerd` (currently fall back to Vancouver)
- Tracked-changes preservation
- A `.pkg`/`.dmg` installer for non-technical users

## License

MIT. Use it, fork it, ship it commercially. Just don't blame me if a journal rejects your formatting — verify the output against the journal's current author guidelines before submitting.

## Author

Built by **Pablo J. Atria** — clinician-researcher, NYU College of Dentistry.

Built for daily use in research and clinical practice. Released publicly because there's no reason every clinician should rebuild this from scratch every submission.

---

*If this saved you a Sunday afternoon, star the repo and tell a colleague.*
