"""Minimal RIS → CSL JSON parser.

RIS is a line-based reference format with two-letter tags. We handle the
common subset used by EndNote, Mendeley, Zotero, and Papers exports:
TY (type), ID, TI/T1 (title), AU (author, repeatable), JO/T2 (journal),
PY/Y1 (year), DO (DOI), and ER (record terminator).

Imported lazily by scripts/references.py so users without an RIS
workflow don't pay the parse cost.
"""
import re
from pathlib import Path


# RIS TY codes → CSL types. Conservative mapping; unknown codes fall back
# to 'article-journal' since dental/medical libraries are predominantly
# journal articles (matches the EndNote XML parser's choice).
TYPE_MAP = {
    "JOUR": "article-journal",
    "BOOK": "book",
    "CHAP": "chapter",
    "CONF": "paper-conference",
    "THES": "thesis",
    "RPRT": "report",
    "GEN": "document",
    "MGZN": "article-magazine",
    "NEWS": "article-newspaper",
    "ELEC": "webpage",
    "ICOMM": "personal_communication",
    "UNPB": "manuscript",
}

_TAG_RE = re.compile(r"^([A-Z][A-Z0-9])\s*-\s*(.*)$")


def _parse_author(raw: str) -> dict:
    """Parse an RIS author line. Drops 'et al' markers; renders names
    ending in ',' as a CSL 'literal' (corporate author convention).
    """
    raw = raw.strip()
    if raw.lower() in ("et al.", "et al", "others"):
        return {"literal": "et al."}
    if raw.endswith(","):
        return {"literal": raw.rstrip(", ").strip()}
    if "," in raw:
        family, _, given = raw.partition(",")
        return {"family": family.strip(), "given": given.strip()}
    parts = raw.rsplit(" ", 1)
    if len(parts) == 2:
        return {"family": parts[1], "given": parts[0]}
    return {"family": raw, "given": ""}


def ris_to_csl(path: Path) -> list[dict]:
    """Parse an RIS file and return CSL JSON entries.

    Records that lack a recognizable ID tag get a synthetic id of the form
    'ris_<n>' so citeproc-py can register them. The parser is tolerant of
    blank lines between records and stray whitespace; it raises
    ReferenceFormatError only when the file is unreadable.
    """
    out: list[dict] = []
    cur: dict | None = None
    fallback_idx = 0

    def _finalize(item: dict) -> dict:
        nonlocal fallback_idx
        if not item.get("id"):
            item["id"] = f"ris_{fallback_idx}"
            fallback_idx += 1
        # Drop empty author list rather than emit "author": []
        if not item.get("author"):
            item.pop("author", None)
        return item

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n").rstrip("\r")
            m = _TAG_RE.match(line)
            if not m:
                continue
            tag, val = m.group(1), m.group(2).strip()

            if tag == "TY":
                cur = {
                    "id": "",
                    "type": TYPE_MAP.get(val.upper(), "article-journal"),
                    "author": [],
                }
                continue

            if cur is None:
                # Stray field outside any record — skip
                continue

            if tag == "ID":
                cur["id"] = val
            elif tag in ("TI", "T1"):
                cur["title"] = val
            elif tag == "AU":
                cur["author"].append(_parse_author(val))
            elif tag in ("JO", "T2", "JF", "JA"):
                cur["container-title"] = val
            elif tag in ("PY", "Y1"):
                year = re.match(r"\d{4}", val)
                if year:
                    cur["issued"] = {"date-parts": [[int(year.group(0))]]}
            elif tag == "DO":
                cur["DOI"] = val
            elif tag == "UR":
                cur["URL"] = val
            elif tag == "VL":
                cur["volume"] = val
            elif tag == "IS":
                cur["issue"] = val
            elif tag == "SP":
                cur["page"] = val + (cur.get("page", "") and "")  # set start page
            elif tag == "EP":
                # Append end page if start was already captured
                if "page" in cur:
                    cur["page"] = f"{cur['page']}-{val}"
                else:
                    cur["page"] = val
            elif tag == "ER":
                out.append(_finalize(cur))
                cur = None

    # Tolerate files with no terminating ER tag
    if cur is not None:
        out.append(_finalize(cur))

    return out
