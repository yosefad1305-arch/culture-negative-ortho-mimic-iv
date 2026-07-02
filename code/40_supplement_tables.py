"""Emit supplement eTables (full organism counts, full susceptibility S/I/R, sensitivity analyses)."""
import os, json, pandas as pd, numpy as np
from statsmodels.stats.proportion import proportion_confint
PROJ=r"C:\Users\Owner\ortho-mimic-study"; INT=os.path.join(PROJ,"output","intermediate"); TAB=os.path.join(PROJ,"output","tables")
ep=pd.read_parquet(os.path.join(INT,"episodes.parquet"))
spec=pd.read_parquet(os.path.join(INT,"specimens.parquet"))
org=pd.read_parquet(os.path.join(INT,"organisms.parquet"))
sus=pd.read_parquet(os.path.join(INT,"susceptibilities.parquet"))
spec=spec.merge(ep[["hadm_id","infection_type","primary_dx"]],on="hadm_id",how="left")

def ci(k,n):
    if n==0: return (np.nan,np.nan)
    lo,hi=proportion_confint(k,n,method="beta"); return round(lo*100,1),round(hi*100,1)

# eTable: full species counts among deep-msk speciated isolates
odm=org[org.is_deep_msk & org.is_species]
vc=odm.species.value_counts()
et_org=pd.DataFrame({"species":vc.index,"isolates":vc.values})
et_org["pct"]=(et_org.isolates/et_org.isolates.sum()*100).round(1)
et_org.to_csv(os.path.join(TAB,"eTable_organisms_full.csv"),index=False)

# eTable: full susceptibility by agent (S/I/R counts)
g=sus[sus.interpretation.isin(["S","I","R"])].groupby("ab_name").interpretation.value_counts().unstack(fill_value=0)
for c in ["S","I","R"]:
    if c not in g: g[c]=0
g["tested"]=g[["S","I","R"]].sum(axis=1)
g["pctR"]=(g["R"]/g["tested"]*100).round(1)
g=g.sort_values("tested",ascending=False)
g.to_csv(os.path.join(TAB,"eTable_susceptibility_full.csv"))

# eTable: sensitivity analyses for culture-negative fraction
def cn_frac(d):
    k=int(d.culture_negative.sum()); n=len(d); lo,hi=ci(k,n)
    return dict(neg=k,total=n,pct=round(k/n*100,1) if n else np.nan,ci_lo=lo,ci_hi=hi)
rows=[]
dmsk=spec[spec.has_culture_test & spec.is_deep_msk]
dext=spec[spec.has_culture_test & spec.is_deep_ext]
rows.append(("Primary (deep MSK specimens)",cn_frac(dmsk)))
rows.append(("Sensitivity: + abscess/deep fluid",cn_frac(dext)))
rows.append(("Sensitivity: primary-dx episodes only",cn_frac(dmsk[dmsk.primary_dx])))
rows.append(("PJI only",cn_frac(dmsk[dmsk.infection_type=='PJI'])))
rows.append(("Osteomyelitis only",cn_frac(dmsk[dmsk.infection_type=='Osteomyelitis'])))
sens=pd.DataFrame([{"analysis":a,**v} for a,v in rows])
sens.to_csv(os.path.join(TAB,"eTable_sensitivity_culture_negative.csv"),index=False)
print("eTables written:")
print(sens.to_string(index=False))
print("\nTop 15 species:")
print(et_org.head(15).to_string(index=False))
