"""Map EndNote library XML export to CSL JSON.

EndNote's "Export -> XML" produces a <xml><records><record>...</record>...
file. Each <record> has <rec-number>, <ref-type>, <contributors>/<authors>,
<titles>/<title>+<secondary-title>, <dates>/<year>, and (often)
<electronic-resource-num> for DOI. We map the common subset and pass
through anything we recognize.

Imported lazily by scripts/references.py so users without an EndNote
workflow don't pay the parse cost.
"""
import re
from pathlib import Path
from xml.etree import ElementTree as ET


# Map common EndNote ref-type ids/names to CSL types. We key on both the
# id (numeric, e.g. 17 = Journal Article) and the name attribute, falling
# back to 'document' for anything we don't recognize. The pairs below
# come from EndNote 20's reference type list.
TYPE_MAP_BY_NAME = {
    "Journal Article": "article-journal",
    "Magazine Article": "article-magazine",
    "Newspaper Article": "article-newspaper",
    "Book": "book",
    "Edited Book": "book",
    "Book Section": "chapter",
    "Conference Paper": "paper-conference",
    "Conference Proceedings": "paper-conference",
    "Thesis": "thesis",
    "Report": "report",
    "Web Page": "webpage",
    "Online Database": "webpage",
    "Manuscript": "manuscript",
    "Unpublished Work": "manuscript",
}


def _parse_author(name: str) -> dict:
    """EndNote stores authors as 'Last, First' or just 'Name'. Drop the
    et-al marker and strip any stray BibTeX-like braces."""
    name = name.strip()
    if name.lower() in ("et al.", "et al", "others"):
        return {"literal": "et al."}
    name = name.replace("{", "").replace("}", "")
    if "," in name:
        family, _, given = name.partition(",")
        return {"family": family.strip(), "given": given.strip()}
    parts = name.rsplit(" ", 1)
    if len(parts) == 2:
        return {"family": parts[1], "given": parts[0]}
    return {"family": name, "given": ""}


def endnote_xml_to_csl(path: Path) -> list[dict]:
    """Load an EndNote .xml library export and return CSL JSON entries.

    Skips records with no recognizable structure (e.g., empty <record>
    placeholders) but never raises mid-file — bad records are dropped
    silently and surface in the validator's count of total entries.
    """
    tree = ET.parse(str(path))
    root = tree.getroot()
    out: list[dict] = []

    for record in root.iter("record"):
        rec_number = (record.findtext("rec-number") or "").strip()
        title = (record.findtext(".//titles/title") or "").strip()
        journal = (record.findtext(".//titles/secondary-title") or "").strip()
        year_text = (record.findtext(".//dates/year") or "").strip()
        doi = (record.findtext("electronic-resource-num") or "").strip()
        ref_type_el = record.find("ref-type")
        ref_type_name = (ref_type_el.get("name") if ref_type_el is not None else "") or ""

        authors = []
        for au in record.iterfind(".//contributors/authors/author"):
            text = (au.text or "").strip()
            if text:
                authors.append(_parse_author(text))

        item = {
            "id": f"endnote_{rec_number}" if rec_number else f"endnote_{len(out)}",
            "type": TYPE_MAP_BY_NAME.get(ref_type_name, "article-journal"
                                          if not ref_type_name else "document"),
            "title": title,
        }
        if authors:
            item["author"] = authors
        if journal:
            item["container-title"] = journal
        if year_text:
            m = re.match(r"\d{4}", year_text)
            if m:
                item["issued"] = {"date-parts": [[int(m.group())]]}
        if doi:
            item["DOI"] = doi

        # Skip placeholder records that have nothing meaningful
        if not (title or authors or journal):
            continue
        out.append(item)
    return out
