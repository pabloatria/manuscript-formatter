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
    # Should not have a stray "Heading X renamed -> Y" line
    assert "renamed →" not in md and "renamed ->" not in md
