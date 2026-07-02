"""
Phase 4 cohort build for Paper (1). Emits Parquet checkpoints + a validation report.
  episodes.parquet         one row per qualifying admission (episode)
  specimens.parquet        one row per micro_specimen_id in cohort
  organisms.parquet        one row per (specimen, organism) positive isolate
  susceptibilities.parquet one row per (specimen, organism, antibiotic) S/I/R result
"""
import os, sys
import pandas as pd
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from org_map import classify as org_classify
from spec_map import classify_spec, is_culture

ROOT = r"C:\Users\Owner\OneDrive\Desktop\researches\mimic-iv-3.1"
PROJ = r"C:\Users\Owner\ortho-mimic-study"
OUT  = os.path.join(PROJ, "output", "intermediate")
os.makedirs(OUT, exist_ok=True)
def p(*a): print(*a, flush=True)

# ---------------------------------------------------------------- cohort (dx)
# PJI = infection of an internal JOINT prosthesis only: ICD-9 996.66, ICD-10 T84.5x.
# ICD-9 996.67 ("other internal orthopedic device") is the ICD-9 analogue of T84.6/T84.7 and belongs
# in the other-device group, NOT PJI (adversarial-audit C2).
PJI9, PJI10   = ("99666",), ("T845",)
DEV9, DEV10   = ("99667",), ("T846", "T847")   # other internal orthopedic device infection
OST9, OST10   = ("730",), ("M86",)

p("Loading diagnoses_icd...")
dx = pd.read_csv(os.path.join(ROOT,"hosp","diagnoses_icd.csv.gz"),
                 usecols=["hadm_id","seq_num","icd_code","icd_version"],
                 dtype={"icd_code":"string","icd_version":"int8","seq_num":"int16"})
dx = dx.dropna(subset=["hadm_id"]); dx["hadm_id"] = dx.hadm_id.astype("int64")

def match(pre9, pre10):
    m = pd.Series(False, index=dx.index)
    if pre9:  m |= (dx.icd_version==9)  & dx.icd_code.str.startswith(tuple(pre9))
    if pre10: m |= (dx.icd_version==10) & dx.icd_code.str.startswith(tuple(pre10))
    return m

is_pji  = match(PJI9, PJI10)
is_dev  = match(DEV9, DEV10)
is_ost  = match(OST9, OST10)

pji_h  = set(dx.loc[is_pji, "hadm_id"].unique())
dev_h  = set(dx.loc[is_dev, "hadm_id"].unique())
ost_h  = set(dx.loc[is_ost, "hadm_id"].unique())
# primary-position (seq_num==1) sets
pji_prim = set(dx.loc[is_pji & (dx.seq_num==1), "hadm_id"].unique())
ost_prim = set(dx.loc[is_ost & (dx.seq_num==1), "hadm_id"].unique())

cohort = pji_h | dev_h | ost_h
p(f"PJI={len(pji_h):,} device-other={len(dev_h):,} osteomyelitis={len(ost_h):,} union={len(cohort):,}")

# primary infection type: PJI > device-other > osteomyelitis
def inf_type(h):
    if h in pji_h: return "PJI"
    if h in dev_h: return "Device (other)"
    return "Osteomyelitis"

# ---------------------------------------------------------------- admissions/patients/icu
p("Loading admissions/patients/icustays...")
adm = pd.read_csv(os.path.join(ROOT,"hosp","admissions.csv.gz"),
                  usecols=["subject_id","hadm_id","admittime","dischtime","deathtime",
                           "discharge_location","insurance","language","marital_status","race",
                           "hospital_expire_flag"],
                  parse_dates=["admittime","dischtime","deathtime"])
adm = adm[adm.hadm_id.isin(cohort)].copy()
adm["los_days"] = (adm.dischtime - adm.admittime).dt.total_seconds()/86400.0
pat = pd.read_csv(os.path.join(ROOT,"hosp","patients.csv.gz"),
                  usecols=["subject_id","gender","anchor_age","dod"], parse_dates=["dod"])
adm = adm.merge(pat, on="subject_id", how="left")
icu = pd.read_csv(os.path.join(ROOT,"icu","icustays.csv.gz"), usecols=["hadm_id","stay_id"])
icu_h = set(icu.hadm_id.unique())

# ---------------------------------------------------------------- micro (filtered)
p("Streaming microbiologyevents (cohort-filtered)...")
usecols = ["hadm_id","micro_specimen_id","charttime","spec_type_desc","test_name",
           "org_name","isolate_num","ab_name","interpretation","comments"]
parts = []
for ch in pd.read_csv(os.path.join(ROOT,"hosp","microbiologyevents.csv.gz"),
                      usecols=usecols, dtype="string", chunksize=500_000):
    ch = ch[ch.hadm_id.astype("Int64").isin(cohort)]
    if len(ch): parts.append(ch)
mic = pd.concat(parts, ignore_index=True)
mic["hadm_id"] = mic.hadm_id.astype("int64")
mic["micro_specimen_id"] = mic.micro_specimen_id.astype("int64")
p(f"micro rows={len(mic):,} specimens={mic.micro_specimen_id.nunique():,} hadm_w_micro={mic.hadm_id.nunique():,}")

# organism classification cache over distinct org_name
orgvals = mic.org_name.dropna().unique().tolist()
orgcache = {v: org_classify(v) for v in orgvals}
def og(v, key):
    return orgcache.get(v, {}).get(key) if pd.notna(v) else None
mic["is_organism"]    = mic.org_name.map(lambda v: bool(og(v,"is_organism")) if pd.notna(v) and str(v).strip()!="" else False)
mic["is_species"]     = mic.org_name.map(lambda v: bool(og(v,"is_species_level")) if pd.notna(v) and str(v).strip()!="" else False)
mic["is_lowres"]      = mic.org_name.map(lambda v: bool(og(v,"is_low_resolution")) if pd.notna(v) and str(v).strip()!="" else False)
mic["broad_group"]    = mic.org_name.map(lambda v: og(v,"broad_group") if pd.notna(v) and str(v).strip()!="" else None)
mic["genus_group"]    = mic.org_name.map(lambda v: og(v,"genus_group") if pd.notna(v) and str(v).strip()!="" else None)
mic["species"]        = mic.org_name.map(lambda v: og(v,"species") if pd.notna(v) and str(v).strip()!="" else None)
mic["is_saureus"]     = mic.org_name.map(lambda v: bool(og(v,"is_staph_aureus")) if pd.notna(v) and str(v).strip()!="" else False)

# specimen classification
specmap = {s: classify_spec(s) for s in mic.spec_type_desc.dropna().unique().tolist()}
mic["source_category"] = mic.spec_type_desc.map(lambda s: specmap.get(s,{}).get("source_category","other") if pd.notna(s) else "other")
mic["is_deep_msk"]     = mic.spec_type_desc.map(lambda s: bool(specmap.get(s,{}).get("is_deep_msk")) if pd.notna(s) else False)
mic["is_deep_ext"]     = mic.spec_type_desc.map(lambda s: bool(specmap.get(s,{}).get("is_deep_ext")) if pd.notna(s) else False)
mic["is_culture_test"] = mic.test_name.map(lambda t: is_culture(t) if pd.notna(t) else False)

# ---------------------------------------------------------------- specimen-level
p("Aggregating specimen-level...")
def agg_spec(g):
    has_cult = bool(g.is_culture_test.any())
    real = g[g.is_organism]
    species_set = sorted(set(real.loc[real.is_species, "species"].dropna()))     # collapsed genus, for reporting
    # polymicrobial distinctness on RAW org_name (true species), not the collapsed reporting label,
    # so two distinct organisms sharing a coarse label are not scored as monomicrobial (audit C4).
    orgname_set = sorted(set(real.loc[real.is_species, "org_name"].dropna()))
    any_growth = bool(len(real) > 0)
    return pd.Series({
        "hadm_id": g.hadm_id.iloc[0],
        "spec_type_desc": g.spec_type_desc.dropna().iloc[0] if g.spec_type_desc.notna().any() else None,
        "source_category": g.source_category.iloc[0],
        "is_deep_msk": bool(g.is_deep_msk.any()),
        "is_deep_ext": bool(g.is_deep_ext.any()),
        "has_culture_test": has_cult,
        "any_growth": any_growth,
        "n_species": len(orgname_set),
        "species_list": "; ".join(species_set),
        "orgname_list": "; ".join(orgname_set),
        "polymicrobial": len(orgname_set) >= 2,
        "has_saureus": bool(real.is_saureus.any()),
        "has_lowres_only": bool(any_growth and len(species_set)==0),
        "charttime": g.charttime.dropna().iloc[0] if g.charttime.notna().any() else None,
    })
spec = mic.groupby("micro_specimen_id", sort=False).apply(agg_spec, include_groups=False).reset_index()
# culture status
spec["culture_positive"] = spec.has_culture_test & spec.any_growth
spec["culture_negative"] = spec.has_culture_test & (~spec.any_growth)
p(f"specimens={len(spec):,} culture_specimens={int(spec.has_culture_test.sum()):,} "
  f"deep_msk={int(spec.is_deep_msk.sum()):,}")

# ---------------------------------------------------------------- organism isolate table
org_iso = mic[mic.is_organism].drop_duplicates(["micro_specimen_id","org_name"]).copy()
org_iso = org_iso[["hadm_id","micro_specimen_id","org_name","species","genus_group","broad_group",
                   "is_species","is_lowres","is_saureus","source_category","is_deep_msk"]]

# ---------------------------------------------------------------- susceptibilities
sus = mic[mic.ab_name.notna() & (mic.ab_name.str.strip()!="")].copy()
sus = sus[["hadm_id","micro_specimen_id","org_name","species","genus_group","is_saureus",
           "ab_name","interpretation","source_category","is_deep_msk"]]
# MRSA per S.aureus isolate: oxacillin R
sa = sus[sus.is_saureus].copy()
sa["is_oxacillin"] = sa.ab_name.str.upper().str.contains("OXACILLIN")
mrsa_by_spec = (sa[sa.is_oxacillin].assign(R=lambda d: d.interpretation=="R")
                .groupby("micro_specimen_id").R.max())
# also MRSA-by-string
mrsa_string = set(mic.loc[mic.org_name.str.upper().str.contains("METHICILLIN RESISTANT", na=False),
                          "micro_specimen_id"].unique())

# ---------------------------------------------------------------- episode-level
p("Aggregating episode-level...")
spec_c = spec[spec.has_culture_test].copy()          # culture specimens only
deep = spec_c[spec_c.is_deep_msk]
def agg_ep(h):
    sc = spec_c[spec_c.hadm_id==h]
    dd = deep[deep.hadm_id==h]
    # organisms across deep-msk positive specimens: genus set (reporting) + raw org_name set (distinctness)
    sp_all = set(); org_all = set()
    for lst in dd.loc[dd.culture_positive, "species_list"]:
        sp_all |= set(x for x in lst.split("; ") if x)
    for lst in dd.loc[dd.culture_positive, "orgname_list"]:
        org_all |= set(x for x in lst.split("; ") if x)
    n_deep = len(dd)
    n_deep_pos = int(dd.culture_positive.sum())
    return dict(
        hadm_id=h,
        n_culture_specimens=len(sc),
        n_source_categories=sc.source_category.nunique(),
        n_deep_specimens=n_deep,
        has_deep_specimen=n_deep>0,
        n_deep_positive=n_deep_pos,
        deep_culture_negative_episode=(n_deep>0 and n_deep_pos==0),   # all deep specimens negative
        episode_species=sorted(sp_all),
        n_episode_species=len(org_all),
        episode_polymicrobial=len(org_all)>=2,   # distinct raw organisms (audit C4)
        has_saureus=bool(dd.has_saureus.any()),
    )
ep_rows = [agg_ep(h) for h in adm.hadm_id.unique()]
ep = pd.DataFrame(ep_rows)
ep["episode_species"] = ep.episode_species.map(lambda x: "; ".join(x))

# MRSA at episode level
sa_spec = set(mrsa_by_spec.index) | mrsa_string
sa_R = set(mrsa_by_spec[mrsa_by_spec==True].index) | mrsa_string
ep["saureus_tested_oxacillin"] = ep.hadm_id.map(lambda h: any(s in sa_spec for s in spec_c[spec_c.hadm_id==h].micro_specimen_id))
ep["any_mrsa"] = ep.hadm_id.map(lambda h: any(s in sa_R for s in spec_c[spec_c.hadm_id==h].micro_specimen_id))

# merge demographics + infection type
ep = ep.merge(adm[["hadm_id","subject_id","insurance","language","marital_status","race","gender",
                   "anchor_age","los_days","hospital_expire_flag","discharge_location","dod","admittime"]],
              on="hadm_id", how="left")
ep["infection_type"] = ep.hadm_id.map(inf_type)
ep["primary_dx"] = ep.hadm_id.map(lambda h: h in pji_prim or h in ost_prim)
ep["cooccur_pji_osteo"] = ep.hadm_id.map(lambda h: (h in pji_h) and (h in ost_h))
ep["icu_linked"] = ep.hadm_id.map(lambda h: h in icu_h)

# ---------------------------------------------------------------- save
spec.to_parquet(os.path.join(OUT,"specimens.parquet"), index=False)
org_iso.to_parquet(os.path.join(OUT,"organisms.parquet"), index=False)
sus.to_parquet(os.path.join(OUT,"susceptibilities.parquet"), index=False)
ep.to_parquet(os.path.join(OUT,"episodes.parquet"), index=False)

# ---------------------------------------------------------------- validation
p("\n================= VALIDATION =================")
p(f"episodes total: {len(ep):,}  (cohort hadm w/ admission row: {adm.hadm_id.nunique():,})")
p(f"  by infection_type:\n{ep.infection_type.value_counts().to_string()}")
p(f"  episodes with >=1 deep MSK culture specimen: {int(ep.has_deep_specimen.sum()):,}")
p(f"  primary-dx episodes: {int(ep.primary_dx.sum()):,}")
p(f"  PJI/osteo co-occur: {int(ep.cooccur_pji_osteo.sum()):,}")
p(f"specimens: {len(spec):,}; culture: {int(spec.has_culture_test.sum()):,}; "
  f"deep-msk culture: {int((spec.has_culture_test & spec.is_deep_msk).sum()):,}")
dc = spec[spec.has_culture_test & spec.is_deep_msk]
p(f"deep-msk culture-negative fraction (specimen-level): {dc.culture_negative.mean():.3f} "
  f"(neg {int(dc.culture_negative.sum()):,}/{len(dc):,})")
p(f"organism isolates: {len(org_iso):,}; distinct species: {org_iso.loc[org_iso.is_species,'species'].nunique()}")
p(f"susceptibility rows: {len(sus):,}; S.aureus w/ oxacillin: {len(sa[sa.is_oxacillin]):,}")
# invariants
assert ep.hadm_id.is_unique, "episode hadm not unique"
assert spec.micro_specimen_id.is_unique, "specimen id not unique"
assert (dc.culture_negative.mean() >= 0) and (dc.culture_negative.mean() <= 1)
p("INVARIANTS OK. checkpoints written to output/intermediate/")
