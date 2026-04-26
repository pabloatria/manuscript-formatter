# Bundled CSL Style Files

This directory holds Citation Style Language (CSL) files used by
`scripts/references.py` to render bibliographies and inline citations
for each supported journal. All files here are licensed under
[Creative Commons Attribution-ShareAlike 3.0 Unported][1] per the
official [citation-style-language/styles][2] repository.

[1]: https://creativecommons.org/licenses/by-sa/3.0/
[2]: https://github.com/citation-style-language/styles

## Why some filenames don't match their content

Several supported journals — notably JPD (Journal of Prosthetic
Dentistry) — are published in the upstream CSL repo as **dependent
styles**: short XML shims that declare an `independent-parent` and
contain no formatting logic of their own.

For example, JPD's official CSL is at
[`dependent/the-journal-of-prosthetic-dentistry.csl`][3] and reads
roughly: "this journal uses `nlm-citation-sequence-superscript`."

[3]: https://github.com/citation-style-language/styles/blob/master/dependent/the-journal-of-prosthetic-dentistry.csl

`citeproc-py` cannot render from a dependent shim — it needs the
independent parent. So when we bundle a CSL file under a journal
filename here (e.g., `journal-of-prosthetic-dentistry.csl`), the file
contents are the **resolved parent style** (`nlm-citation-sequence-
superscript` for JPD), not the JPD shim.

This is functionally correct for rendering — the parent is what the
journal's Author Instructions actually point to — but maintainers
should not be surprised to open the file and see a different `<title>`
inside.

## How to refresh a style from upstream

```bash
# 1. Fetch the dependent shim and read its <link rel="independent-parent" href="...">
curl -sL "https://raw.githubusercontent.com/citation-style-language/styles/master/dependent/<journal-slug>.csl"

# 2. Use that href to fetch the resolved parent
curl -sL -o "scripts/csl/<journal-slug>.csl" \
  "https://raw.githubusercontent.com/citation-style-language/styles/master/<parent-slug>.csl"
```

If a journal already has an *independent* CSL upstream (no dependent
shim), just fetch it directly under its own filename.
