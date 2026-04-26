"""Reformat a .docx manuscript for a target dental journal.

Outputs three files in --out-dir:
  - <basename>-<journal>.docx        reformatted manuscript
  - <basename>-<journal>-report.md   validation + audit-trail Markdown
  - <basename>-<journal>-cover-letter.docx   (only if --cover-letter)

Usage:
  python format_manuscript.py draft.docx \\
    --references library.json \\
    --journal jpd \\
    --out-dir ~/Downloads/ \\
    [--cover-letter --editor "Dr. Last Name"]

Reference intake supports four formats — pick whichever your manager
exports: Zotero (.json), Mendeley (.bib), EndNote (.xml or .ris).
"""
import argparse
import sys
from pathlib import Path

# Allow running this file directly via `python /path/to/format_manuscript.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.cover_letter import generate_cover_letter
from scripts.docx_helpers import (
    map_headings_to_canonical, read_headings, reformat_sections,
)
from scripts.journal_config import load_journal, JournalConfigError
from scripts.references import load_references, ReferenceFormatError
from scripts.report import render_report
from scripts.validators import validate_manuscript


REPO_ROOT = Path(__file__).resolve().parent.parent
JOURNALS_DIR = REPO_ROOT / "scripts" / "journals"


def _build_heading_renames(input_path: Path, journal_cfg: dict) -> list[dict]:
    """Diff each heading's original text against the canonical display
    name. Used in the report's audit trail."""
    headings = read_headings(input_path)
    mapped = map_headings_to_canonical(headings, journal_cfg["sections"])
    canon_to_display = {s["canonical"]: s["display"] for s in journal_cfg["sections"]}
    renames = []
    for h in mapped:
        if h.canonical is None:
            continue
        target = canon_to_display.get(h.canonical)
        if target and h.original_text != target:
            renames.append({"from": h.original_text, "to": target})
    return renames


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("manuscript", help="Input .docx manuscript")
    ap.add_argument(
        "--references", required=True,
        help="Path to a reference-manager export "
             "(.json/Zotero, .bib/Mendeley, .xml or .ris/EndNote)",
    )
    ap.add_argument("--journal", required=True,
                    help="Journal slug (e.g., jpd, jomi, coir, jdr, jada)")
    ap.add_argument(
        "--out-dir", default=str(Path.home() / "Downloads"),
        help="Where to write outputs (default: ~/Downloads)",
    )
    ap.add_argument("--cover-letter", action="store_true",
                    help="Also generate a cover-letter draft")
    ap.add_argument(
        "--editor", default=None,
        help="Editor name to fill into the cover letter "
             "(uses [EDITOR] placeholder if omitted)",
    )
    args = ap.parse_args()

    if args.editor is not None and not args.editor.strip():
        sys.exit("--editor cannot be empty; omit the flag to use the "
                 "[EDITOR] placeholder")

    in_path = Path(args.manuscript).expanduser().resolve()
    if not in_path.exists():
        sys.exit(f"manuscript not found: {in_path}")

    refs_path = Path(args.references).expanduser().resolve()
    if not refs_path.exists():
        sys.exit(f"references file not found: {refs_path}")

    out_dir = Path(args.out_dir).expanduser().resolve()
    if out_dir.exists() and not out_dir.is_dir():
        sys.exit(f"--out-dir is not a directory: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load and validate inputs early so we fail fast.
    try:
        cfg = load_journal(args.journal, config_dir=JOURNALS_DIR)
    except JournalConfigError as e:
        sys.exit(str(e))

    try:
        references = load_references(refs_path)
    except ReferenceFormatError as e:
        sys.exit(str(e))

    base = in_path.stem
    out_docx = out_dir / f"{base}-{args.journal}.docx"
    report_md = out_dir / f"{base}-{args.journal}-report.md"

    # 1) Build heading-rename audit BEFORE rewriting (we need original text)
    heading_renames = _build_heading_renames(in_path, cfg)

    # 2) Reformat the manuscript (rename headings, body untouched)
    reformat_sections(in_path, out_docx, cfg)

    # 3) Run validators on the reformatted output
    validation = validate_manuscript(out_docx, cfg)

    # 4) Optional cover letter
    cover_path: Path | None = None
    if args.cover_letter:
        cover_path = out_dir / f"{base}-{args.journal}-cover-letter.docx"
        # Try to derive a presentable manuscript title from the basename
        manuscript_title = base.replace("-", " ").replace("_", " ").title()
        generate_cover_letter(
            in_path, cover_path, journal_cfg=cfg,
            editor=args.editor,
            manuscript_title=manuscript_title,
            corresponding_author=None,
        )

    # 5) Markdown validation report
    payload = {
        "manuscript_filename": in_path.name,
        "journal": cfg,
        "validation": validation,
        "heading_renames": heading_renames,
        "cover_letter_path": str(cover_path) if cover_path else None,
    }
    report_md.write_text(render_report(payload), encoding="utf-8")

    # 6) Briefly tell the user where things are
    print(f"\u2713 wrote {out_docx}")
    print(f"\u2713 wrote {report_md}")
    if cover_path:
        print(f"\u2713 wrote {cover_path}")
    # Note: bibliography rendering and inline-citation re-rendering are
    # implemented in scripts/references.py (Tasks 11/12) but are not yet
    # invoked by the CLI — those require parsing the .docx for citation
    # field codes, which is out of scope for v1. The reference list in
    # the output .docx is unchanged from the input; a follow-up release
    # will splice in the rendered bibliography from `references` arg.
    if references:
        # Surface the count so the user knows we read it
        print(f"  (loaded {len(references)} references — bibliography "
              "rendering not yet wired into the .docx)")


if __name__ == "__main__":
    main()
