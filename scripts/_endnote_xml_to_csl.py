"""Map EndNote library XML export to CSL JSON.

EndNote's "Export -> XML" produces a <xml><records><record>...</record>...
file. Each <record> has <rec-number>, <ref-type>, <contributors>/<authors>,
<titles>/<title>+<secondary-title>, <dates>/<year>, and (often)
<electronic-resource-num> for DOI. Unknown or missing ref-type names fall
back to 'article-journal' — empirically the dominant type in dental/medical
EndNote libraries. Misclassifying a chapter as a journal article is less
harmful than defaulting to a generic 'document' type that loses citation
styling.

Imported lazily by scripts/references.py so users without an EndNote
workflow don't pay the parse cost.
"""
import re
from pathlib import Path
from xml.etree import ElementTree as ET


def _itertext(el) -> str:
    """Join all descendant text. Robust against EndNote 20's <style>-wrapped
    fields (e.g., <title><style ...>Endocrowns</style></title>) which would
    otherwise come back empty via findtext()."""
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


# Map common EndNote ref-type ids/names to CSL types. We key on both the
# id (numeric, e.g. 17 = Journal Article) and the name attribute, falling
# back to 'article-journal' for anything we don't recognize. The pairs
# below come from EndNote 20's reference type list.
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
    if name.endswith(","):
        # EndNote signals corporate authors with a trailing comma.
        # Render as a CSL 'literal' so citeproc keeps the name intact.
        return {"literal": name.rstrip(", ").strip()}
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
    try:
        tree = ET.parse(str(path))
    except ET.ParseError as e:
        from .references import ReferenceFormatError
        raise ReferenceFormatError(
            f"{path}: malformed EndNote XML: {e}"
        ) from e
    root = tree.getroot()
    out: list[dict] = []
    seen_ids: set[str] = set()
    fallback_idx = 0

    for record in root.iter("record"):
        rec_number = _itertext(record.find("rec-number"))
        title = _itertext(record.find(".//titles/title"))
        journal = _itertext(record.find(".//titles/secondary-title"))
        doi = _itertext(record.find("electronic-resource-num"))
        ref_type_el = record.find("ref-type")
        ref_type_name = (ref_type_el.get("name") if ref_type_el is not None else "") or ""

        # EndNote stores dates in different paths depending on ref-type.
        # Try each known location in order.
        year_text = ""
        for path_expr in (".//dates/year", ".//dates/pub-dates/date",
                          ".//pub-dates/date", ".//year"):
            val = _itertext(record.find(path_expr))
            if val:
                year_text = val
                break

        authors = []
        for au in record.iterfind(".//contributors/authors/author"):
            text = _itertext(au)
            if text:
                authors.append(_parse_author(text))

        item_type = TYPE_MAP_BY_NAME.get(ref_type_name, "article-journal")

        candidate = f"endnote_{rec_number}" if rec_number else ""
        if not candidate or candidate in seen_ids:
            while True:
                candidate = f"endnote_auto_{fallback_idx}"
                fallback_idx += 1
                if candidate not in seen_ids:
                    break
        seen_ids.add(candidate)
        item_id = candidate

        item = {
            "id": item_id,
            "type": item_type,
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
