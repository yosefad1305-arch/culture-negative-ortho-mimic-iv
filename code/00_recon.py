"""
Phase 1 reconnaissance: size orthopedic phenotypes in MIMIC-IV v3.1 and check
outcome availability. Memory-smart: only small/medium hosp tables are read, with
usecols + category dtypes. No big icu tables touched here.

Outputs:
  output/intermediate/recon_phenotypes.csv   one row per phenotype (N, outcomes)
  output/intermediate/recon_procedures.csv   one row per procedure group
  prints a human summary to stdout
"""
import os
import gzip
import pandas as pd
import numpy as np

ROOT = r"C:\Users\Owner\OneDrive\Desktop\researches\mimic-iv-3.1"
PROJ = r"C:\Users\Owner\ortho-mimic-study"
OUT = os.path.join(PROJ, "output", "intermediate")
os.makedirs(OUT, exist_ok=True)

def p(*a):
    print(*a, flush=True)

# ----------------------------------------------------------------------------
# ICD code definitions (prefix match). ICD-9 (version 9) and ICD-10 (version 10).
# Diagnoses: fractures & degenerative/ortho conditions.
# ----------------------------------------------------------------------------
DX = {
    "Hip fracture (femoral neck/pertroch/subtroch)": {
        9:  ["820"],
        10: ["S720", "S721", "S722"],
    },
    "Femoral shaft/lower fracture": {
        9:  ["821"],
        10: ["S723", "S724", "S728", "S729"],
    },
    "Pelvic / acetabular fracture": {
        9:  ["808"],
        10: ["S320", "S321", "S322", "S323", "S324", "S325", "S328", "S329"],
    },
    "Vertebral fracture": {
        9:  ["805", "806"],
        10: ["S120", "S121", "S122", "S220", "S221", "S320", "T085"],
    },
    "Tibia/fibula fracture": {
        9:  ["823"],
        10: ["S82"],
    },
    "Humerus/upper-arm fracture": {
        9:  ["812"],
        10: ["S422", "S423", "S424"],
    },
    "Distal radius/wrist fracture": {
        9:  ["813"],
        10: ["S52"],
    },
    "Osteoarthritis (any site)": {
        9:  ["715"],
        10: ["M15", "M16", "M17", "M18", "M19"],
    },
    "Osteoporosis": {
        9:  ["7330"],
        10: ["M80", "M81"],
    },
    "Osteomyelitis": {
        9:  ["730"],
        10: ["M86"],
    },
    "Mechanical complication of orthopedic implant": {
        9:  ["9964", "99640", "99641", "99642", "99643", "99644", "99645", "99646", "99647", "99649"],
        10: ["T84"],
    },
    "Periprosthetic/prosthetic joint infection": {
        9:  ["99666", "99667"],
        10: ["T845"],
    },
}

# Procedures: orthopedic surgical groups.
PROC = {
    "Total hip arthroplasty": {
        9:  ["8151"],
        10: ["0SR9", "0SRA", "0SRB", "0SRE", "0SRR", "0SRS"],
    },
    "Hip hemiarthroplasty / partial": {
        9:  ["8152"],
        10: ["0SRA0", "0SRB0"],  # partial-hip subset (approx; refined later if selected)
    },
    "Total knee arthroplasty": {
        9:  ["8154"],
        10: ["0SRC", "0SRD", "0SRT", "0SRU", "0SRV", "0SRW"],
    },
    "Hip fracture ORIF / internal fixation femur": {
        9:  ["7905", "7915", "7925", "7935", "7845"],
        10: ["0QS6", "0QS7", "0QS8", "0QH6", "0QH7", "0QH8"],
    },
    "Spinal fusion": {
        9:  ["810", "8100", "8101", "8102", "8103", "8104", "8105", "8106", "8107", "8108"],
        10: ["0RG", "0SG"],
    },
    "Lower-limb amputation": {
        9:  ["8410", "8411", "8412", "8413", "8414", "8415", "8416", "8417", "8418", "8419"],
        10: ["0Y6"],
    },
}

def matches(code, prefixes):
    return any(code.startswith(pref) for pref in prefixes)

def build_mask(df, defs):
    """Return dict phenotype -> set of hadm_id matching (any listed dx/proc)."""
    result = {}
    codes9 = df[df.icd_version == 9]
    codes10 = df[df.icd_version == 10]
    for name, spec in defs.items():
        pre9 = tuple(spec.get(9, []))
        pre10 = tuple(spec.get(10, []))
        hs = set()
        if pre9:
            m = codes9[codes9.icd_code.str.startswith(pre9)]
            hs |= set(m.hadm_id.unique())
        if pre10:
            m = codes10[codes10.icd_code.str.startswith(pre10)]
            hs |= set(m.hadm_id.unique())
        result[name] = hs
    return result

# ----------------------------------------------------------------------------
p("Loading admissions...")
adm = pd.read_csv(
    os.path.join(ROOT, "hosp", "admissions.csv.gz"),
    usecols=["subject_id", "hadm_id", "admittime", "dischtime", "deathtime",
             "discharge_location", "insurance", "race", "hospital_expire_flag"],
    parse_dates=["admittime", "dischtime", "deathtime"],
)
adm["los_days"] = (adm.dischtime - adm.admittime).dt.total_seconds() / 86400.0
p(f"  admissions: {len(adm):,} rows, {adm.hadm_id.nunique():,} hadm")

p("Loading patients...")
pat = pd.read_csv(
    os.path.join(ROOT, "hosp", "patients.csv.gz"),
    usecols=["subject_id", "gender", "anchor_age", "dod"],
    parse_dates=["dod"],
)
adm = adm.merge(pat[["subject_id", "gender", "anchor_age", "dod"]], on="subject_id", how="left")

p("Loading icustays (for ICU-linkage flag)...")
icu = pd.read_csv(os.path.join(ROOT, "icu", "icustays.csv.gz"), usecols=["hadm_id", "stay_id", "los"])
icu_hadm = set(icu.hadm_id.unique())
p(f"  icustays: {len(icu):,} stays, {len(icu_hadm):,} hadm with ICU")

p("Loading diagnoses_icd (usecols, category)...")
dx = pd.read_csv(
    os.path.join(ROOT, "hosp", "diagnoses_icd.csv.gz"),
    usecols=["hadm_id", "seq_num", "icd_code", "icd_version"],
    dtype={"icd_code": "string", "icd_version": "int8", "seq_num": "int16"},
)
p(f"  diagnoses_icd: {len(dx):,} rows")

p("Loading procedures_icd...")
pr = pd.read_csv(
    os.path.join(ROOT, "hosp", "procedures_icd.csv.gz"),
    usecols=["hadm_id", "seq_num", "icd_code", "icd_version"],
    dtype={"icd_code": "string", "icd_version": "int8", "seq_num": "int16"},
)
p(f"  procedures_icd: {len(pr):,} rows")

# primary-diagnosis subset (seq_num == 1)
dx_primary = dx[dx.seq_num == 1]

p("\nBuilding phenotype masks (diagnoses: any-position)...")
dx_any = build_mask(dx, DX)
p("Building phenotype masks (diagnoses: primary only)...")
dx_prim = build_mask(dx_primary, DX)
p("Building procedure masks...")
proc_any = build_mask(pr, PROC)

adm_idx = adm.set_index("hadm_id")

def summarize(name, hadms):
    sub = adm_idx.reindex([h for h in hadms if h in adm_idx.index])
    n = len(sub)
    if n == 0:
        return dict(phenotype=name, n_hadm=0)
    n_subj = sub.subject_id.nunique()
    mort = sub.hospital_expire_flag.mean()
    icu_frac = np.mean([h in icu_hadm for h in sub.index])
    dod_linked = sub.dod.notna().mean()
    los_med = sub.los_days.median()
    age_med = sub.anchor_age.median()
    female = (sub.gender == "F").mean()
    disp = sub.discharge_location.fillna("MISSING").value_counts(normalize=True)
    rehab_snf = disp.get("REHAB", 0) + disp.get("SKILLED NURSING FACILITY", 0) + disp.get("CHRONIC/LONG TERM ACUTE CARE", 0)
    home = disp.get("HOME", 0) + disp.get("HOME HEALTH CARE", 0)
    return dict(
        phenotype=name, n_hadm=n, n_subj=n_subj,
        inhosp_mortality=round(float(mort), 4),
        icu_linked_frac=round(float(icu_frac), 4),
        dod_linked_frac=round(float(dod_linked), 4),
        los_days_median=round(float(los_med), 2),
        age_median=round(float(age_med), 1),
        female_frac=round(float(female), 4),
        disp_home_frac=round(float(home), 4),
        disp_rehab_snf_frac=round(float(rehab_snf), 4),
    )

p("\n================= DIAGNOSIS PHENOTYPES =================")
rows = []
for name in DX:
    r_any = summarize(name, dx_any[name])
    r_any["definition"] = "any-position dx"
    r_prim = summarize(name + " [PRIMARY dx]", dx_prim[name])
    r_prim["definition"] = "primary dx"
    rows.append(r_any)
    rows.append(r_prim)
dx_df = pd.DataFrame(rows)
pd.set_option("display.width", 200, "display.max_columns", 30)
p(dx_df[["phenotype", "n_hadm", "n_subj", "inhosp_mortality", "icu_linked_frac",
         "los_days_median", "age_median", "female_frac", "disp_rehab_snf_frac"]].to_string(index=False))

p("\n================= PROCEDURE GROUPS =================")
prows = []
for name in PROC:
    r = summarize(name, proc_any[name])
    prows.append(r)
proc_df = pd.DataFrame(prows)
p(proc_df[["phenotype", "n_hadm", "n_subj", "inhosp_mortality", "icu_linked_frac",
           "los_days_median", "age_median", "female_frac", "disp_rehab_snf_frac"]].to_string(index=False))

dx_df.to_csv(os.path.join(OUT, "recon_phenotypes.csv"), index=False)
proc_df.to_csv(os.path.join(OUT, "recon_procedures.csv"), index=False)

# Discharge-location vocabulary (for outcome-proxy design)
p("\n================= discharge_location vocabulary =================")
p(adm.discharge_location.fillna("MISSING").value_counts().to_string())

# Insurance & race vocab (equity framing feasibility)
p("\n================= insurance vocabulary =================")
p(adm.insurance.fillna("MISSING").value_counts().to_string())
p("\n================= race vocabulary (top 15) =================")
p(adm.race.fillna("MISSING").value_counts().head(15).to_string())

p("\nDONE. Wrote recon_phenotypes.csv and recon_procedures.csv")
