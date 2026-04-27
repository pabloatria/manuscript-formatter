# tests/test_report.py
from scripts.report import render_report


SAMPLE_PAYLOAD = {
    "manuscript_filename": "splints-study.docx",
    "journal": {"abbreviation": "J Prosthet Dent"},
    "validation": {
        "sections": [
            {"canonical": "abstract", "original_heading": "Abstract",
             "word_count": 287, "limit": 250, "over_limit": True},
            {"canonical": "introduction", "original_heading": "Background",
             "word_count": 612, "limit": None, "over_limit": False},
        ],
        "missing_required": [{"canonical": "purpose", "display": "Purpose"}],
        "total_word_count": 5121,
        "total_word_limit": 5000,
        "total_over_limit": True,
    },
    "heading_renames": [
        {"from": "Background", "to": "Statement of Problem"},
    ],
    "cover_letter_path": "/tmp/x-cover.docx",
}


def test_render_report_includes_section_word_counts():
    md = render_report(SAMPLE_PAYLOAD)
    assert "287" in md
    assert "limit 250" in md or "limit: 250" in md
    assert "Abstract" in md or "abstract" in md


def test_render_report_flags_over_limit():
    md = render_report(SAMPLE_PAYLOAD)
    # Use the warning marker (the implementation uses "⚠️")
    assert "⚠️" in md or "WARNING" in md.upper()


def test_render_report_lists_missing_required():
    md = render_report(SAMPLE_PAYLOAD)
    assert "purpose" in md.lower()
    assert "missing" in md.lower()


def test_render_report_includes_total_word_count():
    md = render_report(SAMPLE_PAYLOAD)
    # Either "5121" or formatted "5,121" is fine
    assert "5121" in md or "5,121" in md


def test_render_report_includes_heading_rename_audit():
    md = render_report(SAMPLE_PAYLOAD)
    assert "## Heading changes" in md
    assert "Background" in md
    assert "Statement of Problem" in md


def test_render_report_includes_cover_letter_section():
    md = render_report(SAMPLE_PAYLOAD)
    assert "/tmp/x-cover.docx" in md
    assert "[NOVELTY" in md or "NOVELTY" in md


def test_render_report_omits_cover_letter_section_when_path_is_none():
    payload = {**SAMPLE_PAYLOAD, "cover_letter_path": None}
    md = render_report(payload)
    assert "Cover letter" not in md


def test_render_report_handles_no_missing_required():
    payload = {**SAMPLE_PAYLOAD, "validation": {**SAMPLE_PAYLOAD["validation"],
                                                  "missing_required": []}}
    md = render_report(payload)
    assert "All required sections present" in md


def test_render_report_handles_no_heading_renames():
    payload = {**SAMPLE_PAYLOAD, "heading_renames": []}
    md = render_report(payload)
    # Should not emit the "## Heading changes" section when empty
    assert "## Heading changes" not in md


def test_render_report_has_exactly_one_h1():
    """Markdown convention: one H1 per document. The report's title is
    the only H1; cover-letter and heading-changes are H2."""
    md = render_report(SAMPLE_PAYLOAD)
    h1_lines = [ln for ln in md.splitlines() if ln.startswith("# ") and not ln.startswith("## ")]
    assert len(h1_lines) == 1, f"expected exactly one H1, got: {h1_lines}"


def test_render_report_escapes_markdown_injection_in_headings():
    """User-controlled heading text must not render as live Markdown
    in the report — protects the ChatGPT path where the GPT quotes
    report contents into chat."""
    payload = {
        "manuscript_filename": "draft.docx",
        "journal": {"abbreviation": "J Prosthet Dent"},
        "validation": {
            "sections": [
                {"canonical": None,
                 "original_heading": "![pixel](https://attacker.example/leak.png)",
                 "word_count": 50, "limit": None, "over_limit": False},
            ],
            "missing_required": [],
            "total_word_count": 50,
            "total_word_limit": None,
            "total_over_limit": False,
        },
        "heading_renames": [
            {"from": "[click](https://attacker.example)",
             "to": "Statement of Problem"},
        ],
        "cover_letter_path": None,
    }
    md = render_report(payload)
    # The injected URL must appear inside backticks (rendered as monospace,
    # not as a live link/image).
    assert "`![pixel](https://attacker.example/leak.png)`" in md
    assert "`[click](https://attacker.example)`" in md
    # Bare unwrapped form must NOT appear (which would render the link).
    assert "(https://attacker.example/leak.png)`" not in md.replace(
        "`![pixel](https://attacker.example/leak.png)`", ""
    )


def test_render_report_escapes_markdown_injection_in_filename():
    payload = {
        "manuscript_filename": "[click](https://attacker.example).docx",
        "journal": {"abbreviation": "J Prosthet Dent"},
        "validation": {
            "sections": [], "missing_required": [],
            "total_word_count": 0, "total_word_limit": None,
            "total_over_limit": False,
        },
        "heading_renames": [],
        "cover_letter_path": None,
    }
    md = render_report(payload)
    assert "`[click](https://attacker.example).docx`" in md
