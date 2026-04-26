"""Map BibTeX entries (bibtexparser 1.x) to CSL JSON.

Imported lazily by scripts/references.py only when a .bib file is being
loaded, so users without bibtexparser installed don't pay the import cost
unless they need it.
"""
from pathlib import Path

import bibtexparser

# BibTeX entry type -> CSL type. Conservative mapping; unknown types fall
# back to 'document' which citeproc-py renders generically.
TYPE_MAP = {
    "article": "article-journal",
    "book": "book",
    "inbook": "chapter",
    "incollection": "chapter",
    "inproceedings": "paper-conference",
    "conference": "paper-conference",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "techreport": "report",
    "manual": "report",
    "misc": "document",
    "unpublished": "manuscript",
    "online": "webpage",
    "electronic": "webpage",
}


def _split_authors(s: str) -> list[dict]:
    """Parse a BibTeX author field ('Last1, First1 and Last2, First2 ...')
    into CSL author dicts. Falls back to a 'family' single-name when the
    entry has no comma."""
    out = []
    for full in s.split(" and "):
        full = full.strip()
        if not full:
            continue
        if "," in full:
            family, _, given = full.partition(",")
            out.append({"family": family.strip(), "given": given.strip()})
        else:
            # No comma: treat the last whitespace-separated token as family.
            parts = full.rsplit(" ", 1)
            if len(parts) == 2:
                out.append({"family": parts[1], "given": parts[0]})
            else:
                out.append({"family": full, "given": ""})
    return out


def bibtex_to_csl(path: Path) -> list[dict]:
    """Load a .bib file and return the entries as CSL JSON."""
    with open(path, encoding="utf-8") as f:
        db = bibtexparser.load(f)
    out = []
    for e in db.entries:
        item = {
            "id": e.get("ID", ""),
            "type": TYPE_MAP.get((e.get("ENTRYTYPE") or "misc").lower(), "document"),
            "title": (e.get("title") or "").strip("{}").strip(),
        }
        if "author" in e:
            authors = _split_authors(e["author"])
            if authors:
                item["author"] = authors
        if "journal" in e:
            item["container-title"] = e["journal"]
        if "year" in e:
            try:
                item["issued"] = {"date-parts": [[int(e["year"])]]}
            except (TypeError, ValueError):
                pass
        if "doi" in e:
            item["DOI"] = e["doi"]
        if "url" in e:
            item["URL"] = e["url"]
        if "volume" in e:
            item["volume"] = e["volume"]
        if "number" in e:
            item["issue"] = e["number"]
        if "pages" in e:
            item["page"] = e["pages"]
        if "publisher" in e:
            item["publisher"] = e["publisher"]
        out.append(item)
    return out
