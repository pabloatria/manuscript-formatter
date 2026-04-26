"""Load reference-manager exports; normalize all formats to CSL JSON.

Supported inputs (dispatch by file extension):
- .json  Zotero CSL JSON (passes through after a list-shape check)
- .bib   Mendeley/BibTeX             (Task 8 will add bibtexparser pipeline)
- .xml   EndNote library XML export  (Task 9 will add xml.etree pipeline)
- .ris   EndNote RIS export          (Task 10 will add line parser)

The internal representation throughout the rest of the skill is CSL JSON —
a list[dict] with the standard CSL fields (id, type, title, author, issued,
container-title, DOI, ...). citeproc-py consumes this directly.
"""
from pathlib import Path
import json


class ReferenceFormatError(ValueError):
    """Raised on unrecognized file extensions, missing files, malformed
    contents, or any failure during normalization to CSL JSON."""


def load_references(path: Path) -> list[dict]:
    """Dispatch to the right intake parser based on file extension."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".json":
        return _load_csl_json(path)
    if suffix == ".bib":
        from ._bibtex_to_csl import bibtex_to_csl
        return bibtex_to_csl(path)
    if suffix == ".xml":
        raise ReferenceFormatError(
            f"EndNote XML (.xml) intake not yet implemented: {path}"
        )
    if suffix == ".ris":
        raise ReferenceFormatError(
            f"RIS (.ris) intake not yet implemented: {path}"
        )
    raise ReferenceFormatError(
        f"unsupported reference export format: {suffix or '(no extension)'} "
        f"(supported: .json/Zotero, .bib/Mendeley, .xml/EndNote, .ris/EndNote)"
    )


def _load_csl_json(path: Path) -> list[dict]:
    if not path.exists():
        raise ReferenceFormatError(f"file not found: {path}")
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ReferenceFormatError(f"{path}: invalid JSON: {e}") from e
    if not isinstance(data, list):
        raise ReferenceFormatError(f"{path}: expected JSON array of CSL items")
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ReferenceFormatError(
                f"{path}: entry {i} is not a JSON object"
            )
        if "id" not in entry:
            raise ReferenceFormatError(
                f"{path}: entry {i} missing required 'id' field"
            )
    return data
