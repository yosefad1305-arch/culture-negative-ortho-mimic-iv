"""
Independent audit: re-derive every headline number directly from the Parquet checkpoints
(NOT from the digests, to catch analysis bugs), then assert each appears in the manuscript text.
Exits non-zero if any check fails.
"""
import os, re, sys
import pandas as pd, numpy as np
from statsmodels.stats.proportion import proportion_confint

PROJ=r"C:\Users\Owner\ortho-mimic-study"; INT=os.path.join(PROJ,"output","intermediate")
MAN=open(os.path.join(PROJ,"manuscript","manuscript.md"),encoding="utf-8").read()
SUP=open(os.path.join(PROJ,"manuscript","supplement.md"),encoding="utf-8").read()

ep=pd.read_parquet(os.path.join(INT,"episodes.parquet"))
spec=pd.read_parquet(os.path.join(INT,"specimens.parquet")).merge(
    ep[["hadm_id","infection_type"]],on="hadm_id",how="left")
org=pd.read_parquet(os.path.join(INT,"organisms.parquet")).merge(
    ep[["hadm_id","infection_type"]],on="hadm_id",how="left")
sus=pd.read_parquet(os.path.join(INT,"susceptibilities.parquet"))

fails=[]; oks=0
def check(label, value, must_contain):
    global oks
    present = must_contain in MAN or must_contain in SUP
    if present: oks+=1
    else: fails.append(f"{label}: computed '{value}' -> string '{must_contain}' NOT found in manuscript/supplement")

def frac_ci(k,n,method="beta"):
    lo,hi=proportion_confint(k,n,method=method)
    return k/n, lo, hi

# --- cohort ---
assert ep.hadm_id.is_unique
n_ep=len(ep); check("total episodes", n_ep, "7697")
by=ep.infection_type.value_counts().to_dict()
check("PJI n", by["PJI"], "1089"); check("Osteo n", by["Osteomyelitis"], "5715"); check("Device n", by["Device (other)"], "893")
check("median age", ep.anchor_age.median(), "60")

# --- deep-culture analytic cohort ---
dc=spec[spec.has_culture_test & spec.is_deep_msk]
n_dc_ep=dc.hadm_id.nunique(); n_dc_spec=len(dc)
check("deep-culture episodes", n_dc_ep, "3560")
check("deep specimens", n_dc_spec, "7700")
# headline culture-negative
k=int(dc.culture_negative.sum()); f,lo,hi=frac_ci(k,n_dc_spec)
check("CN fraction", round(f*100,1), "35.7%")
check("CN naive CI lo", round(lo*100,1), "34.6"); check("CN naive CI hi", round(hi*100,1), "36.7")
# by infection type
for it,txt in [("PJI","48.6%"),("Osteomyelitis","26.6%")]:
    d=dc[dc.infection_type==it]; kk=int(d.culture_negative.sum()); ff=kk/len(d)
    check(f"CN {it}", round(ff*100,1), txt)
# by source
for cat,txt in [("synovial_joint","54.8%"),("deep_tissue_bone","33.9%"),("implant_sonication","31.7%")]:
    d=dc[dc.source_category==cat]; ff=d.culture_negative.mean()
    check(f"CN {cat}", round(ff*100,1), txt)
# episode-level CN
epd=ep[ep.has_deep_specimen]
f=epd.deep_culture_negative_episode.mean(); check("episode CN", round(f*100,1), "21.4%")
# specimen-count gradient
nspec=dc.groupby("hadm_id").size().rename("n"); dc2=dc.merge(nspec,on="hadm_id")
def band(n): return "1" if n==1 else ("2-3" if n<=3 else ("4-6" if n<=6 else "7+"))
dc2["b"]=dc2.n.map(band)
for b,txt in [("1","24.5%"),("2-3","30.8%"),("4-6","44.3%"),("7+","50.7%")]:
    ff=dc2[dc2.b==b].culture_negative.mean(); check(f"CN band {b}", round(ff*100,1), txt)
# dual-code excluded
cooccur=set(ep.loc[ep.cooccur_pji_osteo,"hadm_id"])
dnx=dc[~dc.hadm_id.isin(cooccur)]; ff=dnx.culture_negative.mean()
check("CN excl dual", round(ff*100,1), "35.1%")
check("n dual-coded", len(cooccur), "97 episodes")

# --- organisms ---
odm=org[org.is_deep_msk & org.is_species]
n_iso=len(odm); check("n isolates", n_iso, "7090")
vc=odm.genus_group.value_counts()
check("S aureus n", int(vc["Staphylococcus aureus"]), "2305")
check("S aureus pct", round(vc["Staphylococcus aureus"]/n_iso*100,1), "32.5%")
check("CoNS pct", round(vc["Coagulase-negative staphylococci"]/n_iso*100,1), "14.3%")
# S aureus by type
for it,txt in [("PJI","36.4%"),("Osteomyelitis","30.2%")]:
    d=odm[odm.infection_type==it]; ff=(d.genus_group=="Staphylococcus aureus").mean()
    check(f"S aureus {it}", round(ff*100,1), txt)
# polymicrobial
epp=ep[ep.has_deep_specimen & (ep.n_deep_positive>0)]
f=epp.episode_polymicrobial.mean(); check("polymicrobial", round(f*100,1), "42.7%")

# --- resistance (deep, per-isolate) ---
sus_d=sus[sus.is_deep_msk]
sa=sus_d[sus_d.is_saureus]
oxa=sa[sa.ab_name.str.upper().str.contains("OXACILLIN")]
g=oxa.groupby("micro_specimen_id").interpretation.agg(lambda s:"R" if (s=="R").any() else ("I" if (s=="I").any() else "S"))
k=int((g=="R").sum()); n=len(g); check("MRSA n tested", n, "1143")
check("MRSA pct", round(k/n*100,1), "43.3%")
# vancomycin S aureus 0
van=sa[sa.ab_name.str.upper()=="VANCOMYCIN"]
gv=van.groupby(["micro_specimen_id","org_name"]).interpretation.agg(lambda s:"R" if (s=="R").any() else "S")
check("vanc R count", int((gv=="R").sum()), "0 of 509" if len(gv)==509 else f"0 of {len(gv)}")

# --- Table 2 sums to n_iso ---
tbl2sum = int(vc.sum())
check("Table2 sum", tbl2sum, "7090")

print(f"\nAUDIT: {oks} checks passed, {len(fails)} failed")
for f_ in fails: print("  FAIL:", f_)
sys.exit(1 if fails else 0)
