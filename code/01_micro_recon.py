"""
Phase 3 feasibility recon for Paper (1): microbial epidemiology of orthopedic infections.
Restrict microbiologyevents to the PJI + osteomyelitis cohort and characterize:
  - specimen-type vocabulary (to build a musculoskeletal-source taxonomy)
  - organism vocabulary + how culture-negative / 'no growth' is represented
  - antibiotic-susceptibility coverage (ab_name, interpretation S/I/R)
No heavy tables loaded except microbiologyevents (117 MB gz) filtered to cohort hadm.
"""
import os
import pandas as pd
import numpy as np

ROOT = r"C:\Users\Owner\OneDrive\Desktop\researches\mimic-iv-3.1"
PROJ = r"C:\Users\Owner\ortho-mimic-study"
OUT = os.path.join(PROJ, "output", "intermediate")

def p(*a): print(*a, flush=True)

# --- cohort: PJI + native osteomyelitis (any-position dx) ---
DX = {
    "PJI": {9: ["99666", "99667"], 10: ["T845"]},
    "Osteomyelitis": {9: ["730"], 10: ["M86"]},
    "MechImplantComplication": {9: ["9964"], 10: ["T84"]},  # broader device complication (context)
}
p("Loading diagnoses_icd...")
dx = pd.read_csv(os.path.join(ROOT, "hosp", "diagnoses_icd.csv.gz"),
                 usecols=["hadm_id", "icd_code", "icd_version"],
                 dtype={"icd_code": "string", "icd_version": "int8"})

def hadms_for(spec):
    hs = set()
    for ver in (9, 10):
        pre = tuple(spec.get(ver, []))
        if not pre: continue
        m = dx[(dx.icd_version == ver) & (dx.icd_code.str.startswith(pre))]
        hs |= set(m.hadm_id.dropna().unique())
    return hs

pji = hadms_for(DX["PJI"])
osteo = hadms_for(DX["Osteomyelitis"])
cohort = pji | osteo
p(f"PJI hadm: {len(pji):,} | Osteomyelitis hadm: {len(osteo):,} | union: {len(cohort):,}")

# --- micro restricted to cohort ---
p("Loading microbiologyevents (filtered to cohort by chunks)...")
usecols = ["hadm_id", "micro_specimen_id", "spec_type_desc", "test_name",
           "org_name", "isolate_num", "ab_name", "interpretation", "comments"]
chunks = []
reader = pd.read_csv(os.path.join(ROOT, "hosp", "microbiologyevents.csv.gz"),
                     usecols=usecols, dtype="string", chunksize=500_000)
for ch in reader:
    ch = ch[ch.hadm_id.astype("Int64").isin(cohort)]
    if len(ch): chunks.append(ch)
mic = pd.concat(chunks, ignore_index=True)
mic["hadm_id"] = mic.hadm_id.astype("Int64")
p(f"micro rows in cohort: {len(mic):,} | unique specimens: {mic.micro_specimen_id.nunique():,} | unique hadm w/ micro: {mic.hadm_id.nunique():,}")

p("\n=== spec_type_desc vocabulary (top 40, specimen-level) ===")
spec_level = mic.drop_duplicates("micro_specimen_id")
p(spec_level.spec_type_desc.value_counts().head(40).to_string())

p("\n=== test_name vocabulary (top 25) ===")
p(spec_level.test_name.value_counts().head(25).to_string())

p("\n=== org_name vocabulary (top 40, among rows with an organism) ===")
orgrows = mic[mic.org_name.notna() & (mic.org_name.str.strip() != "")]
p(orgrows.org_name.value_counts().head(40).to_string())

p("\n=== how many specimens have >=1 organism vs none (potential culture-negative) ===")
spec_has_org = orgrows.groupby("micro_specimen_id").size().rename("norg")
spec_all = spec_level[["micro_specimen_id", "spec_type_desc", "test_name"]].copy()
spec_all = spec_all.merge(spec_has_org, on="micro_specimen_id", how="left")
spec_all["has_org"] = spec_all.norg.notna()
p(spec_all.has_org.value_counts().to_string())
p("\nby spec_type_desc (top 25) has_org fraction:")
g = spec_all.groupby("spec_type_desc").agg(n=("micro_specimen_id","size"), pos_frac=("has_org","mean")).sort_values("n", ascending=False).head(25)
p(g.to_string())

p("\n=== antibiotic susceptibility coverage ===")
ab = mic[mic.ab_name.notna() & (mic.ab_name.str.strip() != "")]
p(f"rows with ab_name: {len(ab):,} | unique ab: {ab.ab_name.nunique()} | interpretations: {ab.interpretation.value_counts().to_string()}")
p("\ntop antibiotics tested:")
p(ab.ab_name.value_counts().head(20).to_string())

p("\n=== sample 'no growth' comments (specimens with no organism, culture tests) ===")
culture_specs = spec_all[spec_all.test_name.str.contains("CULTURE", case=False, na=False)]
p(f"culture-test specimens: {len(culture_specs):,} | culture-negative (no org): {(~culture_specs.has_org).sum():,} ({(~culture_specs.has_org).mean():.1%})")
noorg_ids = set(culture_specs[~culture_specs.has_org].micro_specimen_id.head(8))
sample = mic[mic.micro_specimen_id.isin(noorg_ids)].drop_duplicates("micro_specimen_id")[["spec_type_desc","test_name","comments"]]
for _, r in sample.iterrows():
    p(f"  [{r.spec_type_desc} | {r.test_name}] -> {str(r.comments)[:140]}")

p("\nDONE micro recon")
