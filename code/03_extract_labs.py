"""
Extract inflammatory/nutritional markers for the infection cohort from labevents (2.6 GB gz),
memory-smart: stream in chunks, filter by target itemid then by cohort hadm. Emit first + peak
value per (hadm_id, marker) to output/intermediate/labs.parquet.
"""
import os, pandas as pd, numpy as np
ROOT=r"C:\Users\Owner\OneDrive\Desktop\researches\mimic-iv-3.1"
PROJ=r"C:\Users\Owner\ortho-mimic-study"; INT=os.path.join(PROJ,"output","intermediate")
def p(*a): print(*a,flush=True)

ep=pd.read_parquet(os.path.join(INT,"episodes.parquet"))
cohort=set(ep.hadm_id.unique())
ITEMS={51301:"wbc",51300:"wbc",50889:"crp",51288:"esr",50862:"albumin",51256:"neutro_pct"}
targets=set(ITEMS)

p("Streaming labevents (filter itemid then cohort)...")
parts=[]
n=0
for ch in pd.read_csv(os.path.join(ROOT,"hosp","labevents.csv.gz"),
                      usecols=["hadm_id","itemid","charttime","valuenum"],
                      dtype={"hadm_id":"Int64","itemid":"int32","valuenum":"float32"},
                      parse_dates=["charttime"], chunksize=1_000_000):
    ch=ch[ch.itemid.isin(targets)]
    ch=ch[ch.hadm_id.isin(cohort)]
    ch=ch.dropna(subset=["valuenum"])
    if len(ch): parts.append(ch)
    n+=1
    if n%50==0: p(f"  ...{n}M rows scanned")
lab=pd.concat(parts,ignore_index=True)
lab["marker"]=lab.itemid.map(ITEMS)
p(f"lab rows in cohort: {len(lab):,}")

# first + peak per (hadm, marker)
lab=lab.sort_values("charttime")
first=lab.groupby(["hadm_id","marker"]).valuenum.first().unstack()
peak =lab.groupby(["hadm_id","marker"]).valuenum.max().unstack()
first.columns=[f"{c}_first" for c in first.columns]
peak.columns=[f"{c}_peak" for c in peak.columns]
out=first.join(peak, how="outer").reset_index()
out.to_parquet(os.path.join(INT,"labs.parquet"), index=False)
p(f"labs.parquet: {out.shape}, hadm with any lab: {out.hadm_id.nunique():,}")
p("coverage per marker (episodes with a value):")
for c in out.columns:
    if c=="hadm_id": continue
    p(f"  {c:16s} {out[c].notna().sum():,}")
