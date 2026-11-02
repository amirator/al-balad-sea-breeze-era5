"""Builds paper.docx from paper.md (figures and CSV tables embedded). Then: libreoffice --headless --convert-to pdf paper.docx"""
import re, pathlib, pandas as pd
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
ROOT = pathlib.Path(__file__).resolve().parents[1]
doc = Document()
st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)
for s in doc.sections: s.left_margin = s.right_margin = Cm(2.3)
TABCOLS = {
 "table2a_trend_tests.csv": (["variable","period","n","tau","p_mk","p_hr","sen_per_decade"],
                             ["Variable","Period","n","Kendall τ","p_MK","p_HR","Sen slope /decade"]),
 "table2b_decades.csv": (["decade","years","afternoon_hours","share_W_N_pct","share_NW_pct(292.5-337.5)","mean_ws","onshore_ws","circular_mean_dir"],
                         ["Decade","Years","Afternoon hours","W–N share %","NW-only share %","Mean speed m/s","Onshore speed m/s","Mean direction °"]),
 "table3_sensitivity.csv": (["sector","early_1940_69_pct","recent_1996_2025_pct","diff_pp","sen_pp_per_decade","p_mk","p_hamed_rao"],
                            ["Sector / window","1940–69 %","1996–2025 %","Diff. pp","Sen pp/decade","p_MK","p_HR"]),
 "table1_data_summary.csv": (["Item","Value"],["Item","Value"])}
def fmt(v, col):
    if isinstance(v, float):
        if col.startswith("p_"): return "<0.001" if v < 0.001 else f"{v:.3f}"
        if col in ("tau","sen_per_decade","sen_pp_per_decade"): return f"{v:.3f}"
        if col == "afternoon_hours": return f"{int(v):,}"
        return f"{v:.2f}" if abs(v) < 100 else f"{v:.1f}"
    return f"{v:,}" if isinstance(v, int) and col=="afternoon_hours" else str(v)
def add_table(path, cap):
    c = doc.add_paragraph(); r = c.add_run(cap); r.bold = True; r.font.size = Pt(9.5)
    df = pd.read_csv(ROOT/path); cols, heads = TABCOLS[pathlib.Path(path).name]
    t = doc.add_table(rows=1, cols=len(cols)); t.style = "Light Grid Accent 1"
    for i, hd in enumerate(heads): t.rows[0].cells[i].text = hd
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for i, col in enumerate(cols): cells[i].text = fmt(row[col], col)
    for row in t.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for r in p.runs: r.font.size = Pt(8)
    doc.add_paragraph()
def add_runs(p, text):
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text):
        if part.startswith("**"): p.add_run(part[2:-2]).bold = True
        elif part.startswith("*") and len(part) > 1: p.add_run(part[1:-1]).italic = True
        elif part.startswith("`"): r = p.add_run(part[1:-1]); r.font.name = "Courier New"; r.font.size = Pt(9.5)
        else: p.add_run(part)
lines = (ROOT/"paper.md").read_text().split("\n"); in_refs = False; titles = []
for ln in lines:
    if ln.startswith("% "): titles.append(ln[2:]); continue
    if titles is not None and titles and not ln.startswith("% "):
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; r = p.add_run(titles[0]); r.bold = True; r.font.size = Pt(16)
        for x in titles[1:]:
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.add_run(x).font.size = Pt(10.5)
        titles = None
    if not ln.strip(): continue
    if ln.startswith("# "):
        doc.add_heading(ln[2:], level=1); in_refs = ln.strip() == "# References"; continue
    if ln.startswith("## "): doc.add_heading(ln[3:], level=2); continue
    m = re.match(r"!\[(.*)\]\((.*)\)", ln)
    if m:
        doc.add_picture(str(ROOT/m.group(2)), width=Cm(15.5 if "map" not in m.group(2) else 12))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        c = doc.add_paragraph(); add_runs(c, m.group(1))
        for r in c.runs: r.font.size = Pt(9)
        continue
    if ln.startswith("TABLE:"):
        path, cap = [x.strip() for x in ln[6:].split("|", 1)]; add_table(path, cap); continue
    if ln.startswith("> "):
        p = doc.add_paragraph(); p.paragraph_format.left_indent = Cm(1); add_runs(p, ln[2:]); continue
    p = doc.add_paragraph(); add_runs(p, ln)
    if in_refs:
        p.paragraph_format.left_indent = Cm(1.27); p.paragraph_format.first_line_indent = Cm(-1.27)
    else: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
doc.save(ROOT/"paper.docx")
