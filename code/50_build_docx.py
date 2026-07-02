"""
Phase 9 output build (no pandoc): markdown -> .docx via python-docx.
Produces manuscript.docx, manuscript_with_figures.docx, supplement.docx, cover_letter.docx and
copies renamed submission figures into output/submission_figures/.
Handles: ATX headings, blank-line paragraphs, **bold**/*italic* inline, pipe tables, --- rules.
"""
import os, re, shutil
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

PROJ=r"C:\Users\Owner\ortho-mimic-study"; MAN=os.path.join(PROJ,"manuscript")
FIG=os.path.join(PROJ,"output","figures"); OUTD=os.path.join(PROJ,"output")
SUBF=os.path.join(OUTD,"submission_figures"); os.makedirs(SUBF,exist_ok=True)

INLINE=re.compile(r"(\*\*.+?\*\*|\*.+?\*|`.+?`)")
def add_runs(par, text):
    for tok in INLINE.split(text):
        if not tok: continue
        if tok.startswith("**") and tok.endswith("**"):
            r=par.add_run(tok[2:-2]); r.bold=True
        elif tok.startswith("*") and tok.endswith("*"):
            r=par.add_run(tok[1:-1]); r.italic=True
        elif tok.startswith("`") and tok.endswith("`"):
            r=par.add_run(tok[1:-1]); r.font.name="Consolas"
        else:
            par.add_run(tok)

def new_doc():
    d=Document()
    st=d.styles["Normal"]; st.font.name="Calibri"; st.font.size=Pt(11)
    return d

def is_table_row(l): return l.strip().startswith("|") and l.strip().endswith("|")
def is_sep_row(l): return bool(re.match(r"^\s*\|[\s:|-]+\|\s*$", l))

def md_to_doc(md, doc):
    lines=md.split("\n"); i=0
    while i < len(lines):
        l=lines[i]
        if is_table_row(l):
            block=[]
            while i<len(lines) and is_table_row(lines[i]):
                block.append(lines[i]); i+=1
            rows=[[c.strip() for c in r.strip().strip("|").split("|")] for r in block if not is_sep_row(r)]
            if rows:
                tbl=doc.add_table(rows=len(rows), cols=len(rows[0])); tbl.style="Light Grid Accent 1"
                for ri,row in enumerate(rows):
                    for ci,cell in enumerate(row):
                        if ci<len(tbl.rows[ri].cells):
                            cpar=tbl.rows[ri].cells[ci].paragraphs[0]; cpar.text=""
                            add_runs(cpar, cell)
                            if ri==0:
                                for rn in cpar.runs: rn.bold=True
            doc.add_paragraph("")
            continue
        m=re.match(r"^(#{1,6})\s+(.*)$", l)
        if m:
            lvl=len(m.group(1)); doc.add_heading(m.group(2).strip(), level=min(lvl,4)); i+=1; continue
        if l.strip()=="---":
            i+=1; continue
        if l.strip()=="":
            i+=1; continue
        par=doc.add_paragraph(); add_runs(par, l)
        i+=1
    return doc

def build(md_path, out_path, figures=None):
    md=open(md_path,encoding="utf-8").read()
    d=new_doc(); md_to_doc(md, d)
    if figures:
        d.add_page_break(); d.add_heading("Figures", level=1)
        for f,cap in figures:
            if os.path.exists(f):
                d.add_picture(f, width=Inches(6.3))
                p=d.add_paragraph(); add_runs(p, cap); p.alignment=WD_ALIGN_PARAGRAPH.LEFT
                d.add_paragraph("")
    d.save(out_path); print("wrote", os.path.basename(out_path))

figs=[(os.path.join(FIG,"Figure1_organism_spectrum.png"),"Figure 1. Organism spectrum of deep musculoskeletal isolates."),
      (os.path.join(FIG,"Figure2_culture_negative.png"),"Figure 2. Culture-negative benchmark by specimen source and infection type."),
      (os.path.join(FIG,"Figure3_resistance.png"),"Figure 3. Antimicrobial resistance."),
      (os.path.join(FIG,"Figure4_yield_and_probe.png"),"Figure 4. Diagnostic yield and anticipatability of culture-negativity.")]

build(os.path.join(MAN,"manuscript.md"), os.path.join(MAN,"manuscript.docx"))
build(os.path.join(MAN,"manuscript.md"), os.path.join(MAN,"manuscript_with_figures.docx"), figures=figs)
build(os.path.join(MAN,"supplement.md"), os.path.join(MAN,"supplement.docx"))
build(os.path.join(MAN,"cover_letter.md"), os.path.join(MAN,"cover_letter.docx"))

# submission figures renamed to final numbers (PDF preferred)
for n,(f,_) in enumerate(figs,1):
    pdf=f.replace(".png",".pdf")
    if os.path.exists(pdf): shutil.copy(pdf, os.path.join(SUBF,f"Figure{n}.pdf"))
    if os.path.exists(f):   shutil.copy(f,   os.path.join(SUBF,f"Figure{n}.png"))
print("submission_figures:", sorted(os.listdir(SUBF)))
