# Security Policy

## What this skill does (so you can decide if it's safe for your environment)

`manuscript-formatter` is a filesystem-only tool. It makes **zero network calls at runtime**. It does not:

- Open any inbound or outbound network sockets
- Require or store credentials, API keys, or passwords
- Send telemetry, analytics, or usage data anywhere
- Execute shell commands, evaluate user input as code, or use unsafe deserialization (no `eval`, no `exec`, no `subprocess` on user content, no unsafe object serializers)
- Modify any system files or settings outside its working directory
- Request elevated privileges (no `sudo`)

It reads four file types from disk:

- The input `.docx` manuscript (path you pass as the positional argument)
- The references export (`.json` Zotero / `.bib` Mendeley / `.xml` or `.ris` EndNote)
- The journal YAML config bundled in `scripts/journals/<slug>.yaml`
- The CSL style file bundled in `scripts/csl/<slug>.csl`

It writes up to three files into `--out-dir` (default `~/Downloads/`):

- `<basename>-<journal>.docx` — reformatted manuscript
- `<basename>-<journal>-report.md` — validation report
- `<basename>-<journal>-cover-letter.docx` — only if `--cover-letter` is passed

That is the complete I/O surface.

## Threat model and mitigations

The skill processes user-supplied `.docx` manuscripts and reference-manager exports, plus bundled YAML and CSL config. The following defenses are in place:

| Risk | Mitigation |
|---|---|
| Malformed `.docx` | python-docx parses with its built-in XML safety; corrupt files surface as a clear ValueError rather than crashing the host |
| Malformed reference file (BibTeX with broken braces, malformed XML, non-UTF-8 RIS) | Wrapped in `ReferenceFormatError` with a message naming the file and the parser stage that failed |
| Malformed YAML config (missing required keys, bad types) | Wrapped in `JournalConfigError` with a message naming the offending key |
| Path traversal via `--out-dir` | Resolved with `pathlib.Path.expanduser().resolve()` and validated as an existing directory before any write |
| Empty or whitespace-only `--editor` | Guarded — falls back to the `[EDITOR]` placeholder rather than emitting `Dear ,` |
| Unknown journal slug | Hard-fails with a list of valid slugs; no silent fallback |
| Citation-key injection in prose attempting to traverse references | Citation matching is by author + year + title fuzzy match (rapidfuzz), not by raw key lookup; no path or attribute access is derived from manuscript text |
| XML external-entity attacks via EndNote `.xml` | Parsed with `defusedxml.ElementTree` to prevent entity-expansion DoS attacks (billion laughs); external entities and DTD network retrieval are also blocked. |

## Dependencies

The skill depends on six well-maintained Python packages:

- **python-docx** — Word `.docx` reader/writer. Mature, MIT-licensed, used in many production systems.
- **citeproc-py** — CSL renderer, used to convert reference data into a journal's bibliography style. BSD-licensed.
- **bibtexparser** — BibTeX (`.bib`) parser for Mendeley exports. MIT-licensed.
- **pyyaml** — YAML parser, used only on bundled journal configs (never on user input). Loaded with `yaml.safe_load` to disable arbitrary code execution. MIT-licensed.
- **rapidfuzz** — Fast fuzzy-string matching for citation reconciliation. MIT-licensed.
- **defusedxml** — Hardened XML parser used for EndNote `.xml` exports; rejects entity-expansion bombs and external-entity references. PSF-licensed.

All six are MIT, BSD, or PSF licensed and have no known CVEs as of this skill's last release (verified with `pip-audit`). You can re-verify at any time:

```bash
pip install pip-audit
pip-audit -r <(echo -e "python-docx\nciteproc-py\nbibtexparser\npyyaml\nrapidfuzz\ndefusedxml")
```

These are installed via `pip install` in `install.sh`.

## Reporting a vulnerability

If you discover a security issue in this skill, please report it privately by:

1. Opening a [GitHub Security Advisory](https://github.com/pabloatria/manuscript-formatter/security/advisories/new) (preferred), or
2. Emailing the repository owner (see GitHub profile)

Please do not open a public issue for security-sensitive matters. Expected response time: within 7 days for acknowledgment.

## What you should still do as a user

This is open-source software, MIT licensed, with no warranty. Before using on a sensitive system:

1. **Read the code.** It is small and single-purpose. You should be able to audit `scripts/format_manuscript.py` and the helper modules in 30 minutes.
2. **Run it in a venv** if you don't trust your global Python environment:
   ```bash
   python3 -m venv ~/.manuscript-formatter-venv
   source ~/.manuscript-formatter-venv/bin/activate
   pip install python-docx citeproc-py bibtexparser pyyaml rapidfuzz
   ```
3. **Verify the output before submitting.** This skill performs structural reformatting and validation. The output `.docx` and the rendered citations should still be checked against the journal's current author guidelines before you click "submit." Journal requirements drift; this skill's bundled YAML reflects requirements as of release.
4. **Treat the references export as input you trust.** The skill parses BibTeX, EndNote XML, RIS, and Zotero JSON with safe parsers, but a malformed export from an untrusted source could still produce confusing output. Use exports from your own reference manager.

## Out of scope

This skill is a manuscript formatting aid, not a clinical decision support tool, not a regulated medical device, and not a journal submission portal. It does not meet FDA SaMD criteria. Its output is a draft `.docx` ready for human review and journal submission — verifying compliance with the journal's current requirements is the author's responsibility.
