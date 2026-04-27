# ChatGPT distribution for manuscript-formatter — Design

> **Historical implementation log.** This is the plan that was executed when the feature was built. Useful for understanding the design rationale or for forking the project; **not needed to use or self-host the skill** — see [README](../../README.md) and [`chatgpt/SETUP.md`](../../chatgpt/SETUP.md) for that.

**Date:** 2026-04-26
**Status:** Approved
**Author:** Pablo Atria (with Claude Code, in auto mode)

## Problem

`manuscript-formatter` currently targets Claude only. The user wants the
same skill available as a ChatGPT Custom GPT, mirroring the distribution
pattern established for `pubmed-brief` so audiences on either platform can
use the same tool with the same UX guarantees.

## Goals

- Single source of truth: the Custom GPT runs the **same code** committed
  to `scripts/` — no parallel maintenance fork.
- Public Custom GPT on the GPT Store, discoverable by name.
- Cover all 11 journals already supported by the Claude skill.
- Documented setup that any user can complete in ≤10 minutes.
- Zero ongoing cost to the maintainer (Code Interpreter handles compute).

## Non-goals

- Not implementing bibliography splicing into the output `.docx` (that is
  v1.1 work in the Claude version too — same scope on both platforms).
- Not vendoring `citeproc-py` / `bibtexparser` into the bundle. Code
  Interpreter pre-installs `python-docx`, `pyyaml`, `rapidfuzz`. The two
  exotic deps are lazy-imported and only needed for `.bib` (Mendeley)
  intake — Code Interpreter can `pip install bibtexparser` if the user
  uses Mendeley.
- Not building an OpenAPI Action — `manuscript-formatter` has zero
  network calls at runtime, so the GPT needs no Actions at all.

## Audience

Same as the Claude skill: clinical researchers (faculty, fellows,
residents) submitting peer-reviewed work who use ChatGPT instead of (or
alongside) Claude.

## The structural decision

`pubmed-brief` had 5 Knowledge files (1 Python + 4 TTFs). This skill has
**32 files** (10 Python modules + 11 journal YAMLs + 11 CSL files), well
over ChatGPT's ~20-file Knowledge limit. Three options were considered:

| Option | Files | Pros | Cons |
|---|---|---|---|
| A. Single zip Knowledge upload | 1 | All 11 journals, no code change, 1 extra `unzip` step | Setup needs one extra command |
| B. Top-5 journals only | 20 | Standard Knowledge upload | Loses J Periodontol/J Endod/JERD etc. |
| C. Consolidate configs into one super-YAML | 13 | Standard upload | Requires code change to `journal_config.load_journal` |

**Decision: A (single zip).** All 11 journals, no code drift, one
`unzip` line in the GPT's workflow. The zip is built reproducibly from
`scripts/` by a script committed to the repo — never hand-maintained.

## Design

### Repo additions

```
manuscript-formatter/
├── README.md                                    ← gains "Choose your platform" section
├── chatgpt/                                     ← NEW
│   ├── SETUP.md                                 ← step-by-step Custom GPT setup
│   ├── CUSTOM_GPT_INSTRUCTIONS.md               ← paste into GPT Instructions
│   └── build_zip.sh                             ← reproducible build of the Knowledge zip
└── docs/maintainer-notes.md                     ← NEW (matches pubmed-brief pattern)
```

The zip itself (`manuscript_formatter.zip`) is **not** committed — it's a
build artifact. Users (or the maintainer) regenerate it by running
`chatgpt/build_zip.sh` against the current `scripts/` tree before
uploading to the Custom GPT's Knowledge.

### `build_zip.sh`

One-line reproducible bundle:

```bash
#!/usr/bin/env bash
# Build the Knowledge upload for the ChatGPT Custom GPT.
# Output: manuscript_formatter.zip in the repo root.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/manuscript_formatter.zip"
rm -f "$OUT"

cd "$REPO"
zip -qr "$OUT" \
    scripts/__init__.py \
    scripts/format_manuscript.py \
    scripts/journal_config.py \
    scripts/docx_helpers.py \
    scripts/validators.py \
    scripts/cover_letter.py \
    scripts/report.py \
    scripts/references.py \
    scripts/_bibtex_to_csl.py \
    scripts/_endnote_xml_to_csl.py \
    scripts/_ris_to_csl.py \
    scripts/journals/ \
    scripts/csl/ \
    -x "*.pyc" "*/__pycache__/*"

echo "✓ wrote $OUT ($(du -h "$OUT" | cut -f1))"
```

### `CUSTOM_GPT_INSTRUCTIONS.md`

Tells ChatGPT how to:
1. Find `manuscript_formatter.zip` in `/mnt/data/` (Knowledge files
   appear there in Code Interpreter)
2. Extract once on first use into `/mnt/data/skill/`
3. Identify the user's manuscript file and reference-manager export
   (uploaded by the user to the chat)
4. Run `python /mnt/data/skill/scripts/format_manuscript.py
   <manuscript> --references <refs> --journal <slug>
   --out-dir /mnt/data/`
5. Surface the validation report contents back to the user
6. Offer the reformatted `.docx`, the `-report.md`, and (if requested)
   the cover letter as downloadable files

Includes the same edge-case guidance as `SKILL.md`: EndNote users must
unlink citations to plain text first, manuscripts must use Word's
`Heading 1..9` styles, etc.

### `chatgpt/SETUP.md`

Audience-segregated like pubmed-brief's: top-of-file note clarifying
this is for self-hosters / forkers, with a callout pointing
end-users at the published GPT URL in the main README.

Sections:
- Tradeoffs vs. the Claude skill (table)
- What your GPT will do
- Files you need (just two: `manuscript_formatter.zip` from
  `chatgpt/build_zip.sh`, plus `CUSTOM_GPT_INSTRUCTIONS.md` content)
- Setup steps (create GPT, upload zip, paste instructions, no Actions
  needed, save, optional publish)
- Maintenance (rerun `build_zip.sh` when scripts change, re-upload)

The maintainer-only "promote both versions" content lives separately in
`docs/maintainer-notes.md` (matches the pubmed-brief pattern after we
split it there).

### `README.md` "Choose your platform" section

Replace the current single-platform install section with a two-path
section near the top:

```markdown
## Install

Pick your AI:

### Claude (recommended — runs locally)
[existing one-liner clone + install.sh]

### ChatGPT
Use the published Custom GPT directly:
**[chatgpt.com/g/g-XXXXX-manuscript-formatter](https://chatgpt.com/g/g-XXXXX-manuscript-formatter)**

Requires ChatGPT Plus. Same 11 journals. Same prose-preserving guarantee.

Prefer your own copy? Full self-hosting instructions in
[`chatgpt/SETUP.md`](./chatgpt/SETUP.md). ~10 minutes.
```

URL placeholder gets filled in after publication (separate one-line
commit).

## Tradeoffs vs. the Claude skill

| Feature | Claude skill | ChatGPT Custom GPT |
|---|---|---|
| Auto-trigger from any chat | ✅ via SKILL.md | ⚠️ Only when the user is inside the Custom GPT |
| End-to-end on user's local machine | ✅ | ⚠️ Files live in /mnt/data/ during the session |
| All 11 journals | ✅ | ✅ |
| Text-preservation invariant | ✅ (146 tests) | ✅ (same code) |
| Install steps | 1 line | ~10 minutes UI work |
| Mendeley BibTeX support | ✅ | ⚠️ May need `pip install bibtexparser` in Code Interpreter |
| Cost | Free with subscription | Requires ChatGPT Plus |
| Persistence between sessions | Files persist locally | Files in /mnt/data/ disappear with the session |

## Risks

- **Knowledge file count drift.** If a future task adds another supporting
  module, the zip-bundle approach absorbs it without setup changes —
  just re-run `build_zip.sh`. This is exactly why we chose A over B.
- **Code Interpreter dep variance.** `python-docx` / `pyyaml` /
  `rapidfuzz` are well-established and reliably present. `bibtexparser`
  is rarer; if it's missing, the failure surface is clean (a
  `ReferenceFormatError` from the parser's lazy import). Documented in
  `SETUP.md`.
- **Stale Knowledge upload.** Same as pubmed-brief — when the maintainer
  updates `scripts/`, they must re-run `build_zip.sh` and re-upload.
  Documented in `docs/maintainer-notes.md`.
- **Single zip = single point of failure if extraction fails.** Code
  Interpreter's `unzip` is reliable; the GPT instructions include error
  handling for the missing-zip case (clear message: "did you upload
  manuscript_formatter.zip to Knowledge?").

## Implementation order

1. Write `chatgpt/build_zip.sh`, run it, verify zip extracts cleanly and
   `format_manuscript.py` runs from the extracted directory.
2. Write `chatgpt/CUSTOM_GPT_INSTRUCTIONS.md` (rewrite of pubmed-brief's
   pattern, adjusted for the zip-bundle layout).
3. Write `chatgpt/SETUP.md`.
4. Write `docs/maintainer-notes.md`.
5. Update `README.md` "Install" section + repo-structure tree.
6. Commit + push.
7. (User) creates Custom GPT in ChatGPT UI, uploads zip, pastes
   instructions, publishes to public Store, sends URL back, one-liner
   commit fills in the placeholder.

## Out of scope for this work

- Bibliography splicing into output `.docx` (v1.1 on both platforms).
- Spanish ↔ English translation (separate concern).
- Submission-portal automation.
