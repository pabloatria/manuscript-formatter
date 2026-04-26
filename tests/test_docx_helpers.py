from pathlib import Path
from scripts.docx_helpers import read_headings

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "minimal_manuscript.docx"

def test_read_headings_finds_six_top_level():
    hs = read_headings(FIXTURE)
    levels = [h["level"] for h in hs]
    texts = [h["text"] for h in hs]
    assert all(lv == 1 for lv in levels)
    assert texts == ["Abstract", "Background", "Methods", "Results",
                     "Discussion", "Conclusion"]

def test_each_heading_has_paragraph_index():
    hs = read_headings(FIXTURE)
    indices = [h["paragraph_index"] for h in hs]
    assert indices == sorted(indices)  # strictly ascending
    assert indices[0] >= 0
