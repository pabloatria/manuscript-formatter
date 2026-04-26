# Manuscript Formatter — ChatGPT Custom GPT Setup

**Audience:** you want to create your own Custom GPT version of `manuscript-formatter` (either for personal use or to share with your own audience).

**Not looking to set anything up?** If you just want to *use* Manuscript Formatter inside ChatGPT, use the published Custom GPT linked in the main [README](../README.md) — no setup required. This file is only for people who want their own copy.

---

This is the ChatGPT-compatible version of the `manuscript-formatter` Claude skill. It runs the same Python code committed under `scripts/` — packaged as one Knowledge zip — inside ChatGPT's Code Interpreter.

**Time to set up:** ~10 minutes.
**Cost:** $0 incremental — requires an existing ChatGPT Plus subscription.

## Tradeoffs vs. the Claude skill

| Feature                                | Claude skill                | ChatGPT Custom GPT                          |
|----------------------------------------|-----------------------------|----------------------------------------------|
| Auto-trigger from any chat             | ✅ via SKILL.md description  | ⚠️ Only when the user is inside the Custom GPT |
| End-to-end on user's local machine     | ✅                          | ⚠️ Files live in `/mnt/data/` during the session |
| All 11 journals                        | ✅                          | ✅ (same scripts/ tree, repackaged)           |
| Text-preservation invariant            | ✅ (146 tests)               | ✅ (same code)                                |
| Install steps                          | 1 line                      | ~10 minutes UI work                           |
| Mendeley `.bib` support                | ✅                          | ⚠️ May require `pip install bibtexparser` once |
| Cost                                   | Free with subscription      | Requires ChatGPT Plus                         |
| Persistence between sessions           | Files persist locally       | Files in `/mnt/data/` disappear at session end |

If you write in Mendeley BibTeX and want zero friction, the Claude version is materially smoother. If your audience is on ChatGPT, the Custom GPT covers them well.

## What your GPT will do

A Custom GPT named **Manuscript Formatter** that:

1. Accepts a `.docx` manuscript and a reference-manager export (Zotero CSL JSON, Mendeley BibTeX, or EndNote XML/RIS).
2. Reformats the manuscript for one of 11 dental journals — moving sections, renaming headings to the journal's house style — without altering the author's prose.
3. Generates a Markdown validation report flagging over-limit sections, missing required sections, and the heading-rename audit trail.
4. Optionally generates a cover-letter draft.
5. Returns all three files for download.

## Files you need

Two things, both produced from the cloned repo:

1. **`manuscript_formatter.zip`** — build it once with:
   ```bash
   git clone https://github.com/pabloatria/manuscript-formatter.git
   cd manuscript-formatter
   ./chatgpt/build_zip.sh
   ```
   The script writes `manuscript_formatter.zip` (~64 KB, 36 files) at the repo root. This is the **Knowledge file** you upload to your Custom GPT.

2. **The contents of [`CUSTOM_GPT_INSTRUCTIONS.md`](./CUSTOM_GPT_INSTRUCTIONS.md)** — paste into the Custom GPT's Instructions field.

You do **not** need an OpenAPI Action. The skill makes zero network calls.

## Setup steps

### Step 1 — Create the Custom GPT

1. Go to <https://chatgpt.com> → click your name (bottom-left) → **My GPTs** → **Create a GPT**.
2. Click the **Configure** tab.
3. Fill in:
   - **Name:** `Manuscript Formatter`
   - **Description:** `Reformat dental research manuscripts for any of 11 journal styles. Same prose, journal-correct structure + references.`
   - **Instructions:** paste the entire contents of [`CUSTOM_GPT_INSTRUCTIONS.md`](./CUSTOM_GPT_INSTRUCTIONS.md).
   - **Conversation starters:**
     - *Reformat my manuscript for JPD*
     - *Convert this draft to JOMI style*
     - *Format for J Periodontol with a cover letter*
     - *Apply COIR style and tell me what's over the word limit*

### Step 2 — Capabilities

In Capabilities:
- ✅ **Code Interpreter & Data Analysis** (REQUIRED — the skill runs Python here)
- Web Browsing: not needed — disable.
- DALL·E: not needed — disable.

### Step 3 — Upload the Knowledge bundle

Scroll to **Knowledge** → **Upload files** → select `manuscript_formatter.zip` (the file you built in step 1 of "Files you need").

That's the **only** Knowledge file. The GPT extracts it on first use into `/mnt/data/skill/` and runs from there.

### Step 4 — Actions: none

Skip the Actions section entirely. `manuscript-formatter` makes no network calls.

### Step 5 — Save and test

1. Click **Update** (top right).
2. Test in the preview pane: attach a small `.docx` manuscript and a `.json` (CSL JSON from Zotero) to the chat. Ask: *"Reformat this for JPD."*
3. Expected: the GPT extracts the bundle, runs the CLI, summarizes the report, and offers three downloadable files (reformatted `.docx`, `-report.md`, optional cover letter).

If anything fails, the most common issues are:
- Forgetting to upload `manuscript_formatter.zip` to Knowledge.
- Pasting the Instructions into the wrong field (e.g., the Description).
- The user's `.docx` lacks Word `Heading 1..9` styles — re-export from Word with proper headings.

### Step 6 — (Optional) Publish to the GPT Store

1. Click **Update** → **Share**.
2. Choose **Everyone**. The GPT lists publicly.
3. Before public publication ChatGPT requires a **verified builder name** on your profile — ChatGPT will prompt you the first time.
4. OpenAI assigns a permanent URL of the form `https://chatgpt.com/g/g-<hash>-manuscript-formatter`.

Public GPTs go through automated review (typically minutes).

## Maintenance — when the upstream repo updates

The canonical source is `scripts/` in this repo. The Custom GPT does **not** auto-update; when upstream changes you must rebuild and re-upload.

```bash
cd manuscript-formatter
git pull
./chatgpt/build_zip.sh
# In the GPT's Configure tab → Knowledge → delete the old zip, upload the new one
```

If `chatgpt/CUSTOM_GPT_INSTRUCTIONS.md` changed upstream, also re-paste it into the Instructions field. The GPT Store URL stays stable across re-uploads.

The fastest way to tell whether you need to re-upload: `git log -- scripts/ chatgpt/CUSTOM_GPT_INSTRUCTIONS.md` since your last sync.
