# Maintainer notes

This file is for the repo owner (currently Pablo Atria). It documents
the workflow for keeping the two distribution paths (Claude skill +
ChatGPT Custom GPT) in sync. A user installing either version does
**not** need to read this — they should read the top-level
[README](../README.md) and, if they're self-hosting their own GPT,
[`chatgpt/SETUP.md`](../chatgpt/SETUP.md).

## After publishing the ChatGPT Custom GPT

1. Publish per [`chatgpt/SETUP.md` Step 6](../chatgpt/SETUP.md#step-6--optional-publish-to-the-gpt-store).
2. Copy the assigned `https://chatgpt.com/g/g-<hash>-manuscript-formatter` URL.
3. Edit the main [README.md](../README.md) — replace the URL in the
   "Try in ChatGPT" badge / 👉 callout / Install → ChatGPT section.
4. Commit as `docs: link to published Manuscript Formatter Custom GPT URL`.

**Current live URL:** _(pending publication)_

## After a change to anything under `scripts/`

The Claude path auto-updates via `git pull`. The Custom GPT does not —
the maintainer must rebuild and re-upload.

```bash
cd manuscript-formatter
git pull
./chatgpt/build_zip.sh
```

Then in ChatGPT:

1. **My GPTs** → Manuscript Formatter → **Configure**.
2. **Knowledge** → delete the old zip → upload the new `manuscript_formatter.zip`.
3. If [`chatgpt/CUSTOM_GPT_INSTRUCTIONS.md`](../chatgpt/CUSTOM_GPT_INSTRUCTIONS.md) changed upstream, re-paste its contents into the **Instructions** field.
4. Save. The GPT Store URL stays stable.

## Promoting both versions

Match the audience to the platform:

- **Claude users** → `https://github.com/pabloatria/manuscript-formatter`. The README has the Claude install path at the top.
- **ChatGPT users** → the published GPT Store URL. Zero install for them.

Same prose-preservation guarantee. Same 11-journal coverage. Same `scripts/` tree under the hood. Audience on Claude gets local execution and tracked-changes friendliness; audience on ChatGPT gets zero install.

## Things that don't change per platform

- `scripts/` is the **single source of truth**. Never copy modules into `chatgpt/`. The setup tells users to upload the zipped result of `chatgpt/build_zip.sh`, not a fork.
- The 11 journal YAMLs and 11 CSL files in `scripts/journals/` and `scripts/csl/` are also bundled into the same zip. New journals get added once and ship to both platforms after the next zip rebuild.
- Bibliography splicing into the output `.docx` is a v1.1 item on **both** platforms. The CLI loads references for validation but does not yet rewrite the reference list.
- The text-preservation invariant (146 tests across 11 journals) holds on both — the GPT runs the same code.

## Cross-skill notes

The sibling skill [`pubmed-brief`](https://github.com/pabloatria/pubmed-brief) follows the same dual-distribution pattern, with two differences worth remembering:

- `pubmed-brief` ships 5 individual Knowledge files (1 Python + 4 TTF fonts). `manuscript-formatter` ships **one zip** because we'd otherwise exceed the ~20-file Knowledge limit.
- `pubmed-brief` requires an OpenAPI Action (NCBI eutils). `manuscript-formatter` requires **no Action** because every CSL is bundled and there are no network calls.

If a future skill follows this pattern again, copy the structure that fits: pubmed-brief for skills that need network access and have few files, manuscript-formatter for skills with many local files and no network needs.
