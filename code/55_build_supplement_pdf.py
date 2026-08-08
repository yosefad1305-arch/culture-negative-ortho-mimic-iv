"""
Online Resource 1 as PDF. The journal asks for text-based supplementary material in PDF, and the
document is headings plus tables, so it is generated directly rather than converted from the Word
version. Both files are built from the same tables.json, so they cannot diverge.
"""
import json
import os
import platform
import sys

import matplotlib
import numpy as np
import pandas as pd
import scipy
import statsmodels
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

sys.path.insert(0, os.path.dirname(__file__))
import manuscript_text as M
from org_map import classify as org_classify

from paths import OUT, INT, DOCS

with open(os.path.join(OUT, "tables.json"), encoding="utf-8") as f:
    T = json.load(f)

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Times-Bold", fontSize=16,
                    spaceAfter=10, alignment=TA_LEFT)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Times-Bold", fontSize=12,
                    spaceBefore=10, spaceAfter=6)
BODY = ParagraphStyle("BODY", parent=ss["Normal"], fontName="Times-Roman", fontSize=10,
                      leading=13, spaceAfter=4)
SMALL = ParagraphStyle("SMALL", parent=BODY, fontSize=9, leading=11)
CAP = ParagraphStyle("CAP", parent=BODY, fontSize=9, leading=11, spaceBefore=8, spaceAfter=4)
CELL = ParagraphStyle("CELL", parent=BODY, fontSize=7, leading=8.5, spaceAfter=0)
CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Times-Bold")


def _page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 9)
    canvas.drawCentredString(A4[0] / 2.0, 1.2 * cm, f"S{doc.page}")
    canvas.restoreState()


def table_flow(spec, col_widths=None):
    """A caption plus a gridded table, sized to the printable width."""
    avail = A4[0] - 4 * cm
    ncol = len(spec["header"])
    if col_widths is None:
        col_widths = [avail / ncol] * ncol
    else:
        s = sum(col_widths)
        col_widths = [w / s * avail for w in col_widths]
    data = [[Paragraph(str(h), CELLB) for h in spec["header"]]]
    for row in spec["rows"]:
        data.append([Paragraph(str(v).replace("&", "&amp;").replace("<", "&lt;"), CELL)
                     for v in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9CA3AF")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return [Paragraph(spec["caption"], CAP), t, Spacer(1, 8)]


story = []
story.append(Paragraph("Online Resource 1", H1))
story.append(Paragraph("Supplementary material for:", BODY))
story.append(Paragraph(f"<i>{M.TITLE}</i>", BODY))
story.append(Paragraph("European Journal of Clinical Microbiology &amp; Infectious Diseases",
                       BODY))
story.append(Spacer(1, 10))
story.append(Paragraph("Yosef Adiniaev, Alon Gorenshtein, Tohar M Timor, Eyal Klang, "
                       "Alexander Geftler", BODY))
story.append(Paragraph("Corresponding author: Yosef Adiniaev, BRIDGE GenAI Lab, Beth Israel "
                       "Deaconess Medical Center, Boston, MA, USA; and Faculty of Medicine, "
                       "University of Debrecen, Debrecen, Hungary.", BODY))
story.append(Paragraph("Correspondence: yosefad1305@gmail.com", BODY))
story.append(PageBreak())

ETABLES = [
    ("etable_specimen_map", "eTable 1", "Specimen label to tier assignment", [1, 1.3, 2.2, 0.8]),
    ("etable_accounting", "eTable 2", "Specimen accounting for the no-growth denominator", None),
    ("etable_poly", "eTable 3", "Polymicrobial fraction under each prespecified rule",
     [1, 3, 1.6]),
    ("etable_gradient", "eTable 4",
     "No growth by number of source-specific specimens per episode", [1.4, 2.6]),
    ("etable_era", "eTable 5", "Resistance and no growth by anchor-year group", None),
]

story.append(Paragraph("Contents", H2))
CONTENTS = [(tag, title) for _, tag, title, _ in ETABLES] + [
    ("eTable 6", "Diagnosis codes defining the cohort"),
    ("eTable 7", "Rules assigning a culture result status"),
    ("eTable 8", "Organism normalisation dictionary"),
    ("eTable 9", "Software environment"),
    ("eTable 10", "Complete patient-clustered logistic model output"),
    ("eTable 11", "Exact versus patient-clustered confidence intervals"),
    ("eTable 12", "Within-episode comparison of specimen label tiers (primary comparison)"),
]
for tag, title in CONTENTS:
    story.append(Paragraph(f"{tag}. {title}", BODY))
story.append(PageBreak())

for key, tag, _, widths in ETABLES:
    spec = dict(T[key])
    if not spec["caption"].startswith("eTable"):
        spec["caption"] = f"{tag}. {spec['caption']}"
    story += table_flow(spec, widths)

# eTable 6: diagnosis codes
story.append(PageBreak())
story += table_flow(dict(
    caption=("eTable 6. Diagnosis codes defining the cohort. Codes are matched as prefixes in any "
             "diagnosis position."),
    header=["Group", "ICD-9-CM", "ICD-10-CM"],
    rows=[["Prosthetic joint infection", "996.66", "T84.5x"],
          ["Other internal orthopaedic device infection", "996.67", "T84.6x, T84.7x"],
          ["Native osteomyelitis", "730.xx", "M86.xx"]]), [2, 1, 1])

# eTable 7: result-status rules
story += table_flow(dict(
    caption=("eTable 7. Rules assigning a culture result status, applied in the order shown. Only "
             "positive and reported no-growth specimens are evaluable."),
    header=["Status", "Rule", "Disposition"],
    rows=[["Positive", "At least one recognised organism on a bacterial-culture row",
           "Evaluable; culture-positive"],
          ["Cancelled",
           "Comment indicates cancellation, patient crediting, an unsuitable or rejected "
           "specimen, or a test not performed; or the organism field carries an administrative "
           "string", "Excluded"],
          ["Indeterminate (incomplete)",
           "Comment indicates mixed growth or overgrowth, an abbreviated workup, or an inability "
           "to exclude pathogens. Takes precedence over any negative language on the same "
           "specimen", "Excluded"],
          ["Reported no growth",
           "No organism, and a bacterial-culture comment states an explicit completed no-growth "
           "result for the routine culture (no growth; no significant growth)",
           "Evaluable; no growth"],
          ["Indeterminate (other)",
           "No organism and no interpretable comment: empty, the de-identification placeholder, "
           "or a panel-specific negative only (no anaerobes, fungi or mycobacteria isolated), "
           "which does not establish that the routine culture grew nothing", "Excluded"]]),
    [1.1, 3.2, 1.1])

# eTable 8: organism dictionary
story.append(PageBreak())
odict = sorted({(v, org_classify(v).get("genus_group"), org_classify(v).get("broad_group"))
                for v in pd.read_parquet(
                    os.path.join(INT, "organisms.parquet")).org_name.unique()})
story += table_flow(dict(
    caption=("eTable 8. Organism normalisation dictionary: every laboratory organism string "
             "observed in the cohort, with its assigned reporting group."),
    header=["Laboratory organism string", "Reporting group", "Broad group"],
    rows=[[a, str(b), str(c)] for a, b, c in odict]), [2.2, 1.6, 1.0])


# eTable 10: software
story.append(PageBreak())
story += table_flow(dict(
    caption="eTable 9. Software environment. Analyses used fixed random seeds throughout.",
    header=["Component", "Version"],
    rows=[["Python", platform.python_version()],
          ["pandas", pd.__version__], ["numpy", np.__version__],
          ["scipy", scipy.__version__], ["statsmodels", statsmodels.__version__],
          ["matplotlib", matplotlib.__version__],
          ["Random seed", "20260808"],
          ["Bootstrap resamples", "2000 (clusters = patients)"]]), [1.5, 1.5])

# eTables 11-13
story.append(PageBreak())
story += table_flow(T["etable_regression"], [1.5, 2.0, 0.8, 0.8, 1.3, 1.1])
story.append(PageBreak())
story += table_flow(T["etable_exact"], [2.0, 0.9, 0.5, 1.0, 1.2, 0.6])
story.append(PageBreak())
story += table_flow(T["etable_within"], [1.7, 2.6, 2.2])

path = os.path.join(DOCS, "Online_Resource_1.pdf")
doc = SimpleDocTemplate(path, pagesize=A4,
                        leftMargin=2 * cm, rightMargin=2 * cm,
                        topMargin=2 * cm, bottomMargin=2 * cm,
                        title="Online Resource 1", author="Adiniaev et al")
doc.build(story, onFirstPage=_page, onLaterPages=_page)
print("wrote", path)
