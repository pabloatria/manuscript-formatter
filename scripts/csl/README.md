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

## Vancouver fallback

Some journal-specific CSL files do not exist upstream (neither as an
independent style nor as a dependent shim). In those cases we bundle
the resolved Vancouver style — upstream filename
[`nlm-citation-sequence.csl`][4], which the Author Instructions for
these journals point to as a compatible numbered citation format —
under the journal's intended filename. The journal's
`reference_style` value is left unchanged so future upstream additions
can be picked up just by re-running the fetch script.

[4]: https://github.com/citation-style-language/styles/blob/master/nlm-citation-sequence.csl

Files whose contents are currently the Vancouver style:

- `journal-of-oral-and-maxillofacial-implants.csl` (JOMI)
- `the-international-journal-of-prosthodontics.csl` (Int J Prosthodont)
- `journal-of-esthetic-and-restorative-dentistry.csl` (JERD)
