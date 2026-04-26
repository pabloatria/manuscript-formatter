"""Generate a small .docx fixture for tests. Run once, commit the .docx."""
from pathlib import Path
from docx import Document

def make_jpd_style_manuscript(out_path: Path):
    doc = Document()
    doc.add_heading("Abstract", level=1)
    doc.add_paragraph(
        "Statement of Problem: Endocrowns are minimally invasive but their "
        "long-term survival in posterior teeth remains underreported. "
        "Purpose: to evaluate 5-year survival of lithium disilicate endocrowns. "
        "Methods: 50 endocrowns followed prospectively. Results: 92% survival. "
        "Conclusions: comparable to crowns."
    )
    doc.add_heading("Background", level=1)  # alias for "Statement of Problem"
    doc.add_paragraph("Endodontically treated teeth are restorative challenges...")
    doc.add_heading("Methods", level=1)  # alias for "Material and Methods"
    doc.add_paragraph("Fifty patients enrolled, ages 35-72...")
    doc.add_heading("Results", level=1)
    doc.add_paragraph("Kaplan-Meier 5-year survival 92%...")
    doc.add_heading("Discussion", level=1)
    doc.add_paragraph("Our findings agree with prior systematic reviews...")
    doc.add_heading("Conclusion", level=1)  # alias for "Conclusions"
    doc.add_paragraph("Endocrowns are a reliable alternative.")
    doc.save(out_path)

if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "minimal_manuscript.docx"
    make_jpd_style_manuscript(out)
    print(f"wrote {out}")
