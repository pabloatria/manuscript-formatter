"""The bedrock invariant: reformat_sections never mutates body prose.

For every supported journal, run the full CLI on the standard fixture and
assert that body paragraphs (anything not Heading 1..9 styled) are
byte-identical between input and output — both at the .text level (the
visible prose the author wrote) and at the raw XML level (catches
run-level formatting changes that wouldn't show up in text comparison).

If this test ever fails, the skill's central trust contract is broken
and we must NOT ship the skill until the regression is fixed.
"""
import subprocess
import sys
from pathlib import Path

import pytest
from docx import Document
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parent.parent
FIXT = REPO / "tests" / "fixtures"
CLI = REPO / "scripts" / "format_manuscript.py"

JOURNAL_SLUGS = [
    "jpd", "jomi", "coir", "jdr", "jada", "j-dent",
    "int-j-prosthodont", "j-periodontol", "j-endod",
    "oper-dent", "jerd",
]


def _run_cli(in_path: Path, slug: str, out_dir: Path) -> Path:
    """Run the CLI for one journal and return the output .docx path."""
    cmd = [
        sys.executable, str(CLI), str(in_path),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", slug,
        "--out-dir", str(out_dir),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, (
        f"CLI failed for {slug}:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    )
    return out_dir / f"{in_path.stem}-{slug}.docx"


def _body_paragraph_texts(p: Path) -> list[str]:
    """Visible prose text of every non-heading paragraph, in order."""
    doc = Document(str(p))
    return [
        par.text for par in doc.paragraphs
        if not (par.style.name or "").startswith("Heading ")
    ]


def _body_paragraph_xml(p: Path) -> list[bytes]:
    """Raw <w:p> XML of every non-heading paragraph, in order. Catches
    run-level formatting changes (italic/bold flips, color shifts) that
    text comparison would miss."""
    doc = Document(str(p))
    return [
        ET.tostring(par._element, encoding="utf-8")
        for par in doc.paragraphs
        if not (par.style.name or "").startswith("Heading ")
    ]


@pytest.mark.parametrize("slug", JOURNAL_SLUGS)
def test_body_text_byte_identical_for_every_journal(slug, tmp_path):
    in_path = FIXT / "minimal_manuscript.docx"
    out_path = _run_cli(in_path, slug, tmp_path)
    in_texts = _body_paragraph_texts(in_path)
    out_texts = _body_paragraph_texts(out_path)
    assert in_texts == out_texts, (
        f"{slug}: BODY-TEXT INVARIANT VIOLATED\n"
        f"  diff:\n  - {set(in_texts) - set(out_texts)!r}\n  + {set(out_texts) - set(in_texts)!r}"
    )


@pytest.mark.parametrize("slug", JOURNAL_SLUGS)
def test_body_paragraph_xml_byte_identical_for_every_journal(slug, tmp_path):
    in_path = FIXT / "minimal_manuscript.docx"
    out_path = _run_cli(in_path, slug, tmp_path)
    in_xml = _body_paragraph_xml(in_path)
    out_xml = _body_paragraph_xml(out_path)
    assert in_xml == out_xml, (
        f"{slug}: BODY-XML INVARIANT VIOLATED — "
        "a body paragraph's XML changed (could be run-level formatting, "
        "comments, or other invisible-to-text changes)"
    )
