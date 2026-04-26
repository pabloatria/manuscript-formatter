# manuscript-formatter ChatGPT Distribution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish a public ChatGPT Custom GPT for `manuscript-formatter` that runs the same code as the Claude skill, so users on either platform get identical 11-journal coverage with the same prose-preserving guarantee.

**Architecture:** Bundle `scripts/` into a single Knowledge zip (built reproducibly via `chatgpt/build_zip.sh`); the Custom GPT extracts the zip on first use into `/mnt/data/skill/` and runs `format_manuscript.py` from there. No OpenAPI Action — the skill has zero network calls at runtime.

**Tech Stack:** Bash (zip build), Markdown (setup docs + GPT instructions), no new Python deps.

**Design reference:** `docs/plans/2026-04-26-chatgpt-distribution-design.md`

**Project location:** `/Users/pabloatria/Downloads/manuscript-formatter`. Current head: latest commit on `main` (after Task 20 published the Claude skill).

---

## Phase ordering

1. Build script + verify the zip extracts and runs cleanly (Task 1).
2. ChatGPT-specific docs (Tasks 2–4).
3. README integration + maintainer notes (Tasks 5–6).
4. Push (Task 7).
5. Publish + URL fill-in (Task 8 — deferred to user).

Each task ends with a clean commit. No new pytest tests are added — this work is docs + a bash script. Verification is live: extract the zip into a temp dir, run `format_manuscript.py` against the existing test fixture, confirm the same outputs as the Claude path.

---

## Task 1: `chatgpt/build_zip.sh` reproducible bundle

**Files:**
- Create: `chatgpt/build_zip.sh`
- Modify: `.gitignore` — add `manuscript_formatter.zip` so the artifact never gets committed

**Step 1:** Create the script.

```bash
mkdir -p /Users/pabloatria/Downloads/manuscript-formatter/chatgpt
cat > /Users/pabloatria/Downloads/manuscript-formatter/chatgpt/build_zip.sh <<'EOF'
#!/usr/bin/env bash
# Build the Knowledge upload for the manuscript-formatter Custom GPT.
# Reproducible from the current scripts/ tree — no parallel maintenance.
#
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

SIZE=$(du -h "$OUT" | cut -f1)
COUNT=$(unzip -l "$OUT" | tail -1 | awk '{print $2}')
echo "✓ wrote $OUT (${SIZE}, ${COUNT} files)"
EOF
chmod +x /Users/pabloatria/Downloads/manuscript-formatter/chatgpt/build_zip.sh
```

**Step 2:** Run it.

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
./chatgpt/build_zip.sh
```

Expected: `✓ wrote .../manuscript_formatter.zip (~150K, ~30 files)`.

**Step 3:** Verify the zip extracts and the CLI runs from the extracted directory.

```bash
TMP=$(mktemp -d)
unzip -q manuscript_formatter.zip -d "$TMP/skill"
ls "$TMP/skill/scripts/"
# Run the CLI from the extracted location against the existing fixture
/opt/homebrew/bin/python3.13 "$TMP/skill/scripts/format_manuscript.py" \
    tests/fixtures/minimal_manuscript.docx \
    --references tests/fixtures/sample_zotero.json \
    --journal jpd \
    --out-dir "$TMP/out"
ls "$TMP/out"
```

Expected: a `minimal_manuscript-jpd.docx` and `minimal_manuscript-jpd-report.md` in `$TMP/out`. If anything is missing, surface it — likely a missing module in the zip's file list above.

**Step 4:** Add the zip to `.gitignore` so the artifact never gets committed.

In `.gitignore`, add a new line near the end:

```
# Build artifact for the ChatGPT Custom GPT (regenerate with chatgpt/build_zip.sh)
manuscript_formatter.zip
```

**Step 5:** Commit.

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
git add chatgpt/build_zip.sh .gitignore
git commit -m "chatgpt: reproducible Knowledge bundle build script

Single-source-of-truth: the Custom GPT runs the same code committed to
scripts/ — never a parallel fork. chatgpt/build_zip.sh assembles the
required modules + 11 journal YAMLs + 11 CSL files into
manuscript_formatter.zip (~150K), suitable for upload to the Custom
GPT's Knowledge as one file.

Verified end-to-end: extracted zip into a temp dir, ran
format_manuscript.py against the standard fixture, confirmed identical
.docx + report.md outputs to the Claude path."
```

---

## Task 2: `chatgpt/CUSTOM_GPT_INSTRUCTIONS.md`

**Files:**
- Create: `chatgpt/CUSTOM_GPT_INSTRUCTIONS.md`

**Step 1:** Create the file with content adapted from pubmed-brief's pattern. Required sections (mirroring the existing pubmed-brief instructions for tonal consistency):

- Top-of-file warning: "Paste this entire file into the Custom GPT's **Instructions** field."
- "When to use you" — auto-trigger phrases.
- "Your tools" — Code Interpreter (no Actions, no web browsing required).
- "Workflow" — five phases:
  1. **Locate the bundle.** On first use of the session, check for
     `/mnt/data/manuscript_formatter.zip`. If it's missing, tell the
     user to upload it via Knowledge or attach it to the chat.
     Otherwise extract once: `unzip -q -o /mnt/data/manuscript_formatter.zip -d /mnt/data/skill`.
  2. **Identify inputs.** The user uploads (a) a `.docx` manuscript and
     (b) a reference-manager export (`.json` Zotero / `.bib` Mendeley /
     `.xml` or `.ris` EndNote). Both land in `/mnt/data/`.
  3. **Pick the journal slug.** Match the user's request against the 11
     supported slugs: `jpd`, `jomi`, `coir`, `jdr`, `jada`, `j-dent`,
     `int-j-prosthodont`, `j-periodontol`, `j-endod`, `oper-dent`,
     `jerd`. Confirm if ambiguous.
  4. **Run the CLI.** Execute:
     ```bash
     python /mnt/data/skill/scripts/format_manuscript.py \
       /mnt/data/<manuscript>.docx \
       --references /mnt/data/<refs>.<ext> \
       --journal <slug> \
       --out-dir /mnt/data/ \
       [--cover-letter --editor "Dr. ..."]
     ```
     If the user mentions a cover letter / editor, pass the flags;
     otherwise omit.
  5. **Surface the report.** Read `/mnt/data/<base>-<slug>-report.md`,
     summarize warnings (over-limit sections, missing required
     sections, heading renames) in 1–2 short paragraphs in chat. Then
     offer the `.docx` and the `-report.md` (and cover letter if
     generated) as downloadable files.
- "Edge cases" — copy from the Claude SKILL.md:
  - EndNote users must run "Convert Citations and Bibliography → Convert
    to Plain Text" in Word before using the GPT.
  - Manuscripts must use Word's `Heading 1..9` styles (not just bolded
    paragraph text).
  - Three journals (jomi, int-j-prosthodont, jerd) currently use
    `vancouver.csl` as a CSL fallback because their journal-specific
    style isn't yet in the upstream CSL repo. This is documented and
    the rendered output is still numeric/Vancouver — just not
    journal-customized.
  - If the user uploads `.bib` and the run fails with `ModuleNotFoundError:
    bibtexparser`, run `pip install bibtexparser` once (Code Interpreter
    allows it) and retry.
- "Common requests": "reformat for JOMI", "convert to JPD style", "format
  with cover letter for J Periodontol", etc.

**Step 2:** Verify the file is well-formed Markdown (`grep -c "^##"` shows section count).

**Step 3:** Commit (deferred — bundled with Task 3 below).

---

## Task 3: `chatgpt/SETUP.md`

**Files:**
- Create: `chatgpt/SETUP.md`

**Step 1:** Create the file with audience-segregated header (matching the polished pubmed-brief SETUP.md). Required sections:

- **Audience header:** "This file is for anyone who wants to create their
  own Custom GPT version of `manuscript-formatter`. If you just want to
  *use* the GPT, click the link in the main [README](../README.md). No
  setup required."
- **Tradeoffs vs. the Claude skill** (table from the design doc).
- **What your GPT will do** — 1-paragraph elevator summary.
- **Files you need** — two:
  - `manuscript_formatter.zip` (build via `./chatgpt/build_zip.sh` from
    the cloned repo)
  - The text of `chatgpt/CUSTOM_GPT_INSTRUCTIONS.md`
- **Setup steps:**
  1. Create the Custom GPT (Configure tab, name `Manuscript Formatter`,
     description, conversation starters: *"Reformat my manuscript for
     JPD"*, *"Convert this draft to JOMI style"*, *"Format for J
     Periodontol with a cover letter"*, *"Apply COIR style and tell me
     what's over the word limit"*).
  2. Capabilities — enable **Code Interpreter & Data Analysis**
     (REQUIRED). Web Browsing not needed. DALL·E off.
  3. **Knowledge upload:** upload `manuscript_formatter.zip` (one
     file). No need to upload individual scripts.
  4. **Instructions field:** paste the entire content of
     `CUSTOM_GPT_INSTRUCTIONS.md`.
  5. **Actions: none** — the skill makes zero network calls. Skip.
  6. Save → test with the fixture: ask the GPT *"reformat this for
     JPD"* with a small `.docx` + a CSL JSON file attached.
  7. (Optional) Publish to the GPT Store.
- **Maintenance** — re-run `./chatgpt/build_zip.sh` and re-upload the
  zip when `scripts/` changes upstream.

**Step 2:** Verify section count: `grep -E "^(##|###) " /Users/pabloatria/Downloads/manuscript-formatter/chatgpt/SETUP.md`.

**Step 3:** Commit (along with Task 2's file).

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
git add chatgpt/CUSTOM_GPT_INSTRUCTIONS.md chatgpt/SETUP.md
git commit -m "chatgpt: setup walkthrough + Custom GPT instructions

Audience-segregated SETUP.md: top-of-file note clarifies this is for
self-hosters, end-users go through the published GPT URL in the main
README. Lists the two files needed (manuscript_formatter.zip from
build_zip.sh + the instructions text), six setup steps including
explicit 'Actions: none' since the skill makes zero network calls,
and a Maintenance section covering re-upload after scripts/ changes.

CUSTOM_GPT_INSTRUCTIONS.md mirrors the Claude SKILL.md's workflow but
adapts to the ChatGPT environment: locate-the-bundle phase up front
(check /mnt/data/manuscript_formatter.zip, extract once on first use),
inputs come from /mnt/data/ (user attachments), outputs go back there
for download. Edge cases match the Claude version (EndNote
convert-to-plain-text, Word heading styles required, three journals
currently using vancouver.csl fallback)."
```

---

## Task 4: `docs/maintainer-notes.md`

**Files:**
- Create: `docs/maintainer-notes.md`

**Step 1:** Create the file with the same structure as the equivalent in `pubmed-brief` (which already split owner-only content out of SETUP.md):

```markdown
# Maintainer notes

This file is for the repo owner (currently Pablo Atria). It documents
the workflow for keeping the two distribution paths (Claude skill +
ChatGPT Custom GPT) in sync. A user installing either version does
**not** need to read this — they should read the top-level
[README](../README.md) and, if they're self-hosting their own GPT,
[`chatgpt/SETUP.md`](../chatgpt/SETUP.md).

## After publishing the ChatGPT Custom GPT

1. Publish per [`chatgpt/SETUP.md` Step 7](../chatgpt/SETUP.md).
2. Copy the assigned `https://chatgpt.com/g/g-<hash>-manuscript-formatter` URL.
3. Edit the main [README.md](../README.md) — replace the URL in the
   "Try in ChatGPT" badge, the 👉 callout, and the Install → ChatGPT
   section.
4. Commit as `docs: link to published Manuscript Formatter Custom GPT URL`.

**Current live URL:** _(pending publication)_

## After a change to anything under `scripts/`

The Claude path auto-updates via `git pull`. The Custom GPT does not —
the maintainer must rebuild and re-upload.

1. `./chatgpt/build_zip.sh` to rebuild `manuscript_formatter.zip`.
2. ChatGPT → My GPTs → Manuscript Formatter → Configure.
3. Knowledge → delete the old zip, upload the new one.
4. If `chatgpt/CUSTOM_GPT_INSTRUCTIONS.md` changed, re-paste into the
   GPT's Instructions field.
5. Save. URL stays stable.

## Promoting both versions

Match the audience to the platform:

- **Claude users** → `https://github.com/pabloatria/manuscript-formatter`
  (README has the Claude install path at the top).
- **ChatGPT users** → the published GPT Store URL.

Same prose-preservation guarantee, same 11-journal coverage. Audience on
Claude gets local execution and tracked-changes friendliness; audience
on ChatGPT gets zero-install.

## Things that don't change per platform

- `scripts/` is the single source of truth. Never copy modules into
  `chatgpt/`. The setup tells users to upload the zipped result of
  `build_zip.sh`, not a fork.
- Bibliography splicing into the output `.docx` is a v1.1 item on both
  platforms. The CLI loads references for validation but does not yet
  rewrite the reference list.
```

**Step 2:** Commit.

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
git add docs/maintainer-notes.md
git commit -m "docs: maintainer-only workflow notes for dual distribution

Splits owner-specific content (post-publish URL update, re-upload after
scripts/ changes, audience-matching when promoting) out of SETUP.md so
self-hosters reading SETUP.md don't see workflow steps that don't
apply to their fork."
```

---

## Task 5: README "Choose your platform" Install section

**Files:**
- Modify: `README.md`

**Step 1:** Read the current Install section.

```bash
grep -n "^## Install" /Users/pabloatria/Downloads/manuscript-formatter/README.md
```

**Step 2:** Replace the existing Install block (whatever single-platform form it currently takes) with the two-path version:

```markdown
## Install

Pick your AI:

### Claude (recommended — runs locally)

**Requirements:** Python 3.10+ and Claude Code or Claude Desktop with
skill support enabled.

\`\`\`bash
git clone https://github.com/pabloatria/manuscript-formatter.git ~/.claude/skills/manuscript-formatter
cd ~/.claude/skills/manuscript-formatter
./install.sh
\`\`\`

### ChatGPT (zero-install for end users)

Use the published Custom GPT directly:
**[chatgpt.com/g/g-XXXXX-manuscript-formatter](https://chatgpt.com/g/g-XXXXX-manuscript-formatter)** *(URL filled in once the GPT is published to the store)*

Requires ChatGPT Plus. No download, no setup — click the link, attach
your manuscript and reference-manager export, name a journal.

Prefer your own copy (branded differently, or as a backup)? Full
self-hosting instructions in [`chatgpt/SETUP.md`](./chatgpt/SETUP.md) —
~10 minutes. Tradeoffs vs. the Claude skill (Mendeley BibTeX caveat,
session-bound `/mnt/data/`) are documented there.
```

Place this section immediately after the badges block / elevator pitch,
replacing whatever current single-platform install instructions exist.

**Step 3:** Update the repo-structure tree (also in README.md) to include
`chatgpt/` and `docs/` if not already shown.

**Step 4:** Verify rendered Markdown looks right.

```bash
sed -n '/^## Install/,/^## /p' /Users/pabloatria/Downloads/manuscript-formatter/README.md | head -40
```

Confirm: Install section near top, Claude + ChatGPT sub-sections, both
with sensible content, ChatGPT URL is the placeholder.

**Step 5:** Commit.

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
git add README.md
git commit -m "README: add ChatGPT install path (placeholder URL)

Two-path Install section with Claude + ChatGPT side-by-side. The
ChatGPT URL is g-XXXXX placeholder until publication; a follow-up
one-liner commit will swap in the assigned chatgpt.com/g/... URL after
the GPT lands in the public store."
```

---

## Task 6: Verify nothing regressed; final push

**Files:** none modified.

**Step 1:** Re-run the full test suite to confirm the docs/build-script work didn't accidentally break anything.

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
/opt/homebrew/bin/python3.13 -m pytest 2>&1 | tail -3
```

Expected: **146 passed**.

**Step 2:** Re-run `chatgpt/build_zip.sh` and confirm it still produces a working zip.

```bash
./chatgpt/build_zip.sh
ls -lh manuscript_formatter.zip
```

Expected: `~150K` zip exists.

**Step 3:** Confirm the zip is `.gitignore`d.

```bash
git status --short
```

Expected: clean tree (no untracked `manuscript_formatter.zip`).

**Step 4:** Push.

```bash
git push
```

Expected: a small number of commits land on `origin/main`.

---

## Task 7 (deferred — user action): Publish the Custom GPT

**User does:**

1. In ChatGPT → My GPTs → Create a GPT → Configure.
2. Name: `Manuscript Formatter`. Description: *"Reformat dental research
   manuscripts for any of 11 journal styles. Same prose, journal-correct
   structure + references."*
3. Paste the contents of `chatgpt/CUSTOM_GPT_INSTRUCTIONS.md` into
   Instructions.
4. Conversation starters from `chatgpt/SETUP.md` Step 1.
5. Capabilities → enable Code Interpreter, disable Web Browsing & DALL·E.
6. Knowledge → upload `manuscript_formatter.zip` (build it first via
   `./chatgpt/build_zip.sh`).
7. Actions → none.
8. Save → test with a small `.docx` + a CSL JSON.
9. Update → Share → **Everyone** (publishes to the GPT Store).
10. Copy the assigned `https://chatgpt.com/g/g-XXXXXXXX-manuscript-formatter`
    URL.
11. Send the URL back.

## Task 8 (after URL received): Fill in the README placeholder

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
sed -i '' 's|https://chatgpt.com/g/g-XXXXX-manuscript-formatter|<REAL_URL>|g' README.md
git add README.md
git commit -m "docs: link to published Manuscript Formatter Custom GPT"
git push
```

---

## Risks summary (from design)

- **Knowledge file count:** addressed by single-zip strategy.
- **Code Interpreter dep variance** (`bibtexparser`): documented in
  `CUSTOM_GPT_INSTRUCTIONS.md` edge-cases — if the user uses Mendeley
  BibTeX, the GPT runs `pip install bibtexparser` once.
- **Stale Knowledge upload:** documented in
  `docs/maintainer-notes.md` — re-run `build_zip.sh` and re-upload after
  any `scripts/` change.

## Verification before declaring complete

```bash
cd /Users/pabloatria/Downloads/manuscript-formatter
pytest 2>&1 | tail -3            # expect 146 passed
git status --short               # expect nothing
git log --oneline | head -10     # ~5 new commits since the design doc
./chatgpt/build_zip.sh           # expect a fresh zip
```

Then user runs Task 7. Then user sends URL. Then Task 8 fills in.
