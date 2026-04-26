# tests/test_cli.py
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXT = REPO / "tests" / "fixtures"
CLI = REPO / "scripts" / "format_manuscript.py"
PYTHON = sys.executable


def test_cli_full_run_produces_three_outputs(tmp_path):
    """End-to-end: input docx + Zotero CSL JSON + jpd journal slug ->
    reformatted docx + report.md + cover-letter docx in out_dir."""
    cmd = [
        PYTHON, str(CLI),
        str(FIXT / "minimal_manuscript.docx"),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", "jpd",
        "--out-dir", str(tmp_path),
        "--cover-letter", "--editor", "Dr. Test Editor",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"CLI failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    out_files = sorted(p.name for p in tmp_path.iterdir())
    # Expect at least: a reformatted .docx, a -report.md, and a -cover-letter.docx
    docx_files = [f for f in out_files if f.endswith(".docx")]
    md_files = [f for f in out_files if f.endswith(".md")]
    assert len(docx_files) >= 2, f"expected reformatted + cover-letter docx, got: {out_files}"
    assert len(md_files) >= 1, f"expected a report.md, got: {out_files}"
    assert any("cover-letter" in f for f in out_files), \
        f"expected a cover-letter file, got: {out_files}"


def test_cli_without_cover_letter_omits_cover_file(tmp_path):
    cmd = [
        PYTHON, str(CLI),
        str(FIXT / "minimal_manuscript.docx"),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", "jpd",
        "--out-dir", str(tmp_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    files = list(tmp_path.iterdir())
    assert not any("cover-letter" in f.name for f in files), \
        f"cover-letter file should not exist without --cover-letter flag: {files}"


def test_cli_missing_manuscript_exits_with_clear_error(tmp_path):
    cmd = [
        PYTHON, str(CLI),
        str(tmp_path / "nonexistent.docx"),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", "jpd",
        "--out-dir", str(tmp_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode != 0
    assert "not found" in r.stderr.lower() or "not found" in r.stdout.lower()


def test_cli_unknown_journal_exits_clearly(tmp_path):
    cmd = [
        PYTHON, str(CLI),
        str(FIXT / "minimal_manuscript.docx"),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", "zzznope",
        "--out-dir", str(tmp_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode != 0
    err = (r.stderr + r.stdout).lower()
    assert "zzznope" in err and "not found" in err


def test_cli_report_includes_renames_and_word_counts(tmp_path):
    """Run end-to-end and read the report file; confirm it contains the
    audit trail and word-count info the validator+report writer produce."""
    cmd = [
        PYTHON, str(CLI),
        str(FIXT / "minimal_manuscript.docx"),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", "jpd",
        "--out-dir", str(tmp_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    md = next(p for p in tmp_path.iterdir() if p.suffix == ".md")
    content = md.read_text(encoding="utf-8")
    # Title from journal abbreviation
    assert "J Prosthet Dent" in content
    # Heading rename audit (Background -> Statement of Problem)
    assert "Background" in content
    assert "Statement of Problem" in content
    # Total word count line
    assert "Total" in content


def test_cli_empty_editor_is_rejected(tmp_path):
    cmd = [
        PYTHON, str(CLI),
        str(FIXT / "minimal_manuscript.docx"),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", "jpd",
        "--out-dir", str(tmp_path),
        "--cover-letter", "--editor", "   ",  # whitespace-only
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode != 0
    assert "editor" in (r.stderr + r.stdout).lower()


def test_cli_out_dir_pointing_at_file_is_rejected(tmp_path):
    out_dir_as_file = tmp_path / "iam-a-file.txt"
    out_dir_as_file.write_text("not a directory", encoding="utf-8")
    cmd = [
        PYTHON, str(CLI),
        str(FIXT / "minimal_manuscript.docx"),
        "--references", str(FIXT / "sample_zotero.json"),
        "--journal", "jpd",
        "--out-dir", str(out_dir_as_file),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode != 0
    err = (r.stderr + r.stdout).lower()
    assert "not a directory" in err
