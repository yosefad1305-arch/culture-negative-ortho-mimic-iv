"""
Phase 5 analysis. Reads Parquet checkpoints, produces:
  output/results_digest.json   (descriptive numbers, source of truth)
  output/stats_digest.json     (inferential: tests, effect sizes, CIs, BH-adjusted)
  output/tables/*.csv          (Table 1, organism tables, resistance, intensity, regression)
Every fraction carries an exact (Clopper-Pearson) 95% CI; group tests carry effect sizes.
Descriptive framing only; no causal language.
"""
import os, sys, json
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportion_confint
from statsmodels.stats.multitest import multipletests
import statsmodels.formula.api as smf

PROJ = r"C:\Users\Owner\ortho-mimic-study"
OUT  = os.path.join(PROJ, "output")
INT  = os.path.join(OUT, "intermediate")
TAB  = os.path.join(OUT, "tables")
os.makedirs(TAB, exist_ok=True)
def p(*a): print(*a, flush=True)

ep   = pd.read_parquet(os.path.join(INT,"episodes.parquet"))
spec = pd.read_parquet(os.path.join(INT,"specimens.parquet"))
org  = pd.read_parquet(os.path.join(INT,"organisms.parquet"))
sus  = pd.read_parquet(os.path.join(INT,"susceptibilities.parquet"))

# infection type for main contrast: PJI vs Osteomyelitis (device-other kept as 3rd descriptive group)
spec = spec.merge(ep[["hadm_id","infection_type"]], on="hadm_id", how="left")
org  = org.merge(ep[["hadm_id","infection_type"]], on="hadm_id", how="left")

def ci_prop(k, n):
    if n == 0: return (np.nan, np.nan, np.nan)
    lo, hi = proportion_confint(k, n, alpha=0.05, method="beta")
    return (k/n, lo, hi)

def cramers_v(ct):
    chi2, p_, dof, _ = stats.chi2_contingency(ct)
    n = ct.values.sum()
    r, c = ct.shape
    v = np.sqrt((chi2/n) / (min(r-1, c-1) or 1))
    return chi2, p_, dof, v

def kw_eps(groups):
    groups = [g for g in groups if len(g) > 0]
    H, p_ = stats.kruskal(*groups)
    k = len(groups); n = sum(len(g) for g in groups)
    eps = (H - k + 1) / (n - k) if (n-k) > 0 else np.nan
    return H, p_, eps

results = {}   # descriptive
statsd  = {}   # inferential

# ---- grouping helpers ----
def race_group(r):
    if pd.isna(r): return "Unknown/other"
    r = str(r).upper()
    if r.startswith("WHITE"): return "White"
    if r.startswith("BLACK"): return "Black"
    if "HISPANIC" in r or "LATINO" in r: return "Hispanic/Latino"
    if r.startswith("ASIAN"): return "Asian"
    return "Unknown/other"
def insur_group(i):
    if pd.isna(i): return "Other/unknown"
    i=str(i)
    return i if i in ("Medicare","Medicaid","Private") else "Other/unknown"
def age_band(a):
    if pd.isna(a): return "Unknown"
    a=float(a)
    return "<50" if a<50 else "50-64" if a<65 else "65-74" if a<75 else "75-84" if a<85 else "85+"

ep["race_group"] = ep.race.map(race_group)
ep["insurance_group"] = ep.insurance.map(insur_group)
ep["age_band"] = ep.anchor_age.map(age_band)
ep["female"] = (ep.gender=="F").astype(int)

# =====================================================================
# Table 1 — cohort characteristics (overall + by infection type)
# =====================================================================
p("Building Table 1...")
def t1_col(d):
    return dict(
        n=len(d),
        age_median=round(float(d.anchor_age.median()),1),
        age_iqr=[round(float(d.anchor_age.quantile(.25)),1), round(float(d.anchor_age.quantile(.75)),1)],
        female_n=int((d.gender=="F").sum()), female_pct=round(float((d.gender=="F").mean()*100),1),
        white_pct=round(float((d.race_group=="White").mean()*100),1),
        black_pct=round(float((d.race_group=="Black").mean()*100),1),
        hispanic_pct=round(float((d.race_group=="Hispanic/Latino").mean()*100),1),
        medicare_pct=round(float((d.insurance_group=="Medicare").mean()*100),1),
        medicaid_pct=round(float((d.insurance_group=="Medicaid").mean()*100),1),
        private_pct=round(float((d.insurance_group=="Private").mean()*100),1),
        icu_pct=round(float(d.icu_linked.mean()*100),1),
        los_median=round(float(d.los_days.median()),1),
        los_iqr=[round(float(d.los_days.quantile(.25)),1), round(float(d.los_days.quantile(.75)),1)],
        inhosp_mortality_pct=round(float(d.hospital_expire_flag.mean()*100),2),
        deep_specimen_pct=round(float(d.has_deep_specimen.mean()*100),1),
    )
t1 = {"Overall": t1_col(ep)}
for it in ["PJI","Osteomyelitis","Device (other)"]:
    t1[it] = t1_col(ep[ep.infection_type==it])
results["table1"] = t1
pd.DataFrame(t1).to_csv(os.path.join(TAB,"table1_cohort.csv"))

# =====================================================================
# AIM 2 — culture-negative benchmark (specimen-level & episode-level)
# =====================================================================
p("Aim 2: culture-negative benchmark...")
dc = spec[spec.has_culture_test & spec.is_deep_msk].copy()   # deep-msk culture specimens
def cn_block(d):
    k = int(d.culture_negative.sum()); n = len(d)
    r,lo,hi = ci_prop(k,n)
    return dict(neg=k, total=n, frac=round(r,4), ci=[round(lo,4),round(hi,4)])
aim2 = {"specimen_deep_msk_overall": cn_block(dc)}
aim2["by_infection_type"] = {it: cn_block(dc[dc.infection_type==it]) for it in ["PJI","Osteomyelitis","Device (other)"]}
aim2["by_source_category"] = {c: cn_block(dc[dc.source_category==c]) for c in dc.source_category.unique()}
# sensitivity: include abscess/deep fluid
de = spec[spec.has_culture_test & spec.is_deep_ext]
aim2["specimen_deep_ext_overall"] = cn_block(de)
# episode-level culture-negative (episodes w/ deep specimen where all deep specimens negative)
epd = ep[ep.has_deep_specimen]
k=int(epd.deep_culture_negative_episode.sum()); n=len(epd)
r,lo,hi=ci_prop(k,n)
aim2["episode_level"] = dict(neg=k, total=n, frac=round(r,4), ci=[round(lo,4),round(hi,4)])
aim2["episode_by_infection_type"] = {}
for it in ["PJI","Osteomyelitis","Device (other)"]:
    d=epd[epd.infection_type==it]; k=int(d.deep_culture_negative_episode.sum()); n=len(d)
    r,lo,hi=ci_prop(k,n); aim2["episode_by_infection_type"][it]=dict(neg=k,total=n,frac=round(r,4),ci=[round(lo,4),round(hi,4)])
results["aim2_culture_negative"] = aim2

# cluster-robust CI for the headline specimen-level fraction: bootstrap over EPISODES (not specimens),
# because specimens within an episode are correlated (reviewer 1, concern 1). 2000 resamples.
rng = np.random.RandomState(20260702)
ep_ids = dc.hadm_id.unique()
by_ep = {h: g.culture_negative.values for h,g in dc.groupby("hadm_id")}
fracs=[]
for _ in range(2000):
    samp = rng.choice(ep_ids, len(ep_ids), replace=True)
    num=0; den=0
    for h in samp:
        v=by_ep[h]; num+=v.sum(); den+=len(v)
    if den: fracs.append(num/den)
cl_lo, cl_hi = np.percentile(fracs, [2.5, 97.5])
aim2["specimen_deep_msk_overall"]["cluster_ci"] = [round(float(cl_lo),4), round(float(cl_hi),4)]
aim2["specimen_deep_msk_overall"]["n_episodes"] = int(len(ep_ids))

# specimen-count-stratified CN fraction: if CN rises with more specimens sampled, that is direct
# evidence of a sampling-threshold (ascertainment) mechanism (reviewer 1/2, differential sampling).
nspec = dc.groupby("hadm_id").size().rename("nspec")
dc2 = dc.merge(nspec, on="hadm_id")
def band(n): return "1" if n==1 else ("2-3" if n<=3 else ("4-6" if n<=6 else "7+"))
dc2["nspec_band"]=dc2.nspec.map(band)
cn_by_count={}
for b in ["1","2-3","4-6","7+"]:
    d=dc2[dc2.nspec_band==b]; k=int(d.culture_negative.sum()); n=len(d); r,lo,hi=ci_prop(k,n)
    cn_by_count[b]=dict(neg=k,total=n,frac=round(r,4),ci=[round(lo,4),round(hi,4)])
aim2["cn_by_specimen_count"]=cn_by_count
results["aim2_culture_negative"]=aim2

# test: culture-negative vs infection type (PJI vs Osteo), specimen-level deep-msk
sub = dc[dc.infection_type.isin(["PJI","Osteomyelitis"])]
ct = pd.crosstab(sub.infection_type, sub.culture_negative)
chi2,pp,dof,v = cramers_v(ct)
statsd["cn_by_inftype_specimen"] = dict(test="chi2", chi2=round(chi2,3), dof=int(dof), p=pp, cramers_v=round(v,4), table=ct.to_dict())
# test: culture-negative vs source category
ct2 = pd.crosstab(dc.source_category, dc.culture_negative)
chi2,pp,dof,v = cramers_v(ct2)
statsd["cn_by_source_specimen"] = dict(test="chi2", chi2=round(chi2,3), dof=int(dof), p=pp, cramers_v=round(v,4))

# =====================================================================
# AIM 1 — organism spectrum + polymicrobial
# =====================================================================
p("Aim 1: organism spectrum...")
# organisms from deep-msk positive specimens
odm = org[org.is_deep_msk & org.is_species].copy()
def dist(d, col):
    vc = d[col].value_counts()
    tot = len(d)
    return {k:{"n":int(v),"pct":round(v/tot*100,1)} for k,v in vc.items()}, tot
gd, tot = dist(odm, "genus_group")
bd, _   = dist(odm, "broad_group")
results["aim1_organism"] = {
    "n_isolates_deep_msk_species": tot,
    "by_genus_group": gd,
    "by_broad_group": bd,
}
# by infection type
org_by_it = {}
for it in ["PJI","Osteomyelitis"]:
    d = odm[odm.infection_type==it]; gg,tt = dist(d,"genus_group")
    org_by_it[it] = {"n":tt, "by_genus_group":gg}
results["aim1_organism"]["by_infection_type"] = org_by_it
# test genus group (top few) vs infection type: use broad_group for a clean contingency
sub = odm[odm.infection_type.isin(["PJI","Osteomyelitis"])]
ctg = pd.crosstab(sub.infection_type, sub.broad_group)
chi2,pp,dof,v = cramers_v(ctg)
statsd["organism_broadgroup_by_inftype"] = dict(test="chi2", chi2=round(chi2,3), dof=int(dof), p=pp, cramers_v=round(v,4), table=ctg.to_dict())
# polymicrobial (episode-level, deep specimen episodes)
def poly_block(d):
    k=int(d.episode_polymicrobial.sum()); n=len(d); r,lo,hi=ci_prop(k,n)
    return dict(poly=k, total=n, frac=round(r,4), ci=[round(lo,4),round(hi,4)])
epp = ep[ep.has_deep_specimen & (ep.n_deep_positive>0)]  # culture-positive episodes
results["aim1_polymicrobial"] = {
    "overall": poly_block(epp),
    "by_infection_type": {it: poly_block(epp[epp.infection_type==it]) for it in ["PJI","Osteomyelitis","Device (other)"]}
}
sub = epp[epp.infection_type.isin(["PJI","Osteomyelitis"])]
ct = pd.crosstab(sub.infection_type, sub.episode_polymicrobial)
chi2,pp,dof,v = cramers_v(ct)
statsd["poly_by_inftype"] = dict(test="chi2", chi2=round(chi2,3), dof=int(dof), p=pp, cramers_v=round(v,4), table=ct.to_dict())

# =====================================================================
# AIM 3 — resistance. Restricted to DEEP-MSK isolates for scope consistency with Aims 1-2
# (reviewer 1, major concern 2). Agent-level %R is reported ORGANISM-STRATIFIED, not pooled
# across all organisms (reviewer 1, major concern 1), for clinically meaningful organism-drug pairs.
# =====================================================================
p("Aim 3: resistance (deep-MSK, organism-stratified)...")
sus_deep = sus[sus.is_deep_msk].copy()   # scope-consistent with organism spectrum
sa = sus_deep[sus_deep.is_saureus].copy()
def oxa_R_frac(df):
    oxa = df[df.ab_name.str.upper().str.contains("OXACILLIN")]
    # collapse to one interpretation per S. aureus isolate (specimen); resistant if any R
    g = oxa.groupby("micro_specimen_id").interpretation.agg(lambda s: "R" if (s=="R").any() else ("I" if (s=="I").any() else "S"))
    k=int((g=="R").sum()); n=len(g); r,lo,hi=ci_prop(k,n)
    return dict(mrsa=k, tested=n, frac=round(r,4), ci=[round(lo,4),round(hi,4)])
results["aim3_resistance"] = {"mrsa_among_saureus": oxa_R_frac(sa)}
sa2 = sa.merge(ep[["hadm_id","infection_type"]].drop_duplicates(), on="hadm_id", how="left")
results["aim3_resistance"]["mrsa_by_infection_type"] = {it: oxa_R_frac(sa2[sa2.infection_type==it]) for it in ["PJI","Osteomyelitis"]}

# organism-stratified panels: each drug reported only among organisms for which it is clinically relevant
def org_panel(org_filter, agents, label):
    d0 = sus_deep[org_filter(sus_deep)]
    panel={}
    for ab in agents:
        d = d0[(d0.ab_name.str.upper()==ab) & (d0.interpretation.isin(["R","S","I"]))]
        if len(d)==0: continue
        # collapse to ONE result per isolate (specimen x organism) so denominators match the
        # per-isolate MRSA computation and no isolate is double-counted (reviewer 1, concern 4).
        g = d.groupby(["micro_specimen_id","org_name"]).interpretation.agg(
            lambda s: "R" if (s=="R").any() else ("I" if (s=="I").any() else "S"))
        k=int((g=="R").sum()); n=len(g); r,lo,hi=ci_prop(k,n)
        panel[ab]=dict(R=k,tested=n,pctR=round(r*100,1),ci=[round(lo*100,1),round(hi*100,1)])
    return panel
GNB = lambda df: df.genus_group.isin(["Escherichia coli","Pseudomonas aeruginosa","Other gram-negative"])
SA  = lambda df: df.is_saureus
ENT = lambda df: df.genus_group=="Enterococcus"
results["aim3_resistance"]["saureus_panel"] = org_panel(
    SA, ["OXACILLIN","CEFAZOLIN","CLINDAMYCIN","ERYTHROMYCIN","LEVOFLOXACIN","TRIMETHOPRIM/SULFA","TETRACYCLINE","GENTAMICIN","RIFAMPIN","VANCOMYCIN"], "S. aureus")
results["aim3_resistance"]["gramneg_panel"] = org_panel(
    GNB, ["CEFTRIAXONE","CEFEPIME","CIPROFLOXACIN","LEVOFLOXACIN","GENTAMICIN","TOBRAMYCIN","MEROPENEM","PIPERACILLIN/TAZO","TRIMETHOPRIM/SULFA"], "Gram-negative")
results["aim3_resistance"]["enterococcus_vancomycin"] = org_panel(
    ENT, ["VANCOMYCIN","AMPICILLIN"], "Enterococcus")

# =====================================================================
# AIM 4 — diagnostic intensity
# =====================================================================
p("Aim 4: diagnostic intensity...")
def intensity_block(d):
    return dict(
        n=len(d),
        specimens_median=float(d.n_culture_specimens.median()),
        specimens_iqr=[float(d.n_culture_specimens.quantile(.25)),float(d.n_culture_specimens.quantile(.75))],
        categories_median=float(d.n_source_categories.median()),
        categories_iqr=[float(d.n_source_categories.quantile(.25)),float(d.n_source_categories.quantile(.75))],
        deep_specimens_median=float(d.n_deep_specimens.median()),
    )
epc = ep[ep.n_culture_specimens>0]
results["aim4_intensity"]={"overall":intensity_block(epc),
    "by_infection_type":{it:intensity_block(epc[epc.infection_type==it]) for it in ["PJI","Osteomyelitis","Device (other)"]}}
# KW: n_culture_specimens by infection type
groups=[epc[epc.infection_type==it].n_culture_specimens.values for it in ["PJI","Osteomyelitis","Device (other)"]]
H,pp,eps=kw_eps(groups)
statsd["intensity_by_inftype"]=dict(test="kruskal", H=round(H,3), p=pp, epsilon_sq=round(eps,4))
# yield by source category (specimen-level)
yld={}
for c in spec[spec.has_culture_test].source_category.unique():
    d=spec[(spec.has_culture_test)&(spec.source_category==c)]
    k=int(d.culture_positive.sum()); n=len(d); r,lo,hi=ci_prop(k,n)
    yld[c]=dict(pos=k,total=n,frac=round(r,4),ci=[round(lo,4),round(hi,4)])
results["aim4_intensity"]["yield_by_source_category"]=yld

# =====================================================================
# AIM 5 — variation (logistic regressions, adjusted ORs, BH correction)
# =====================================================================
p("Aim 5: variation (logistic)...")
def run_logit(df, outcome, name):
    d = df.copy()
    d = d[d.age_band!="Unknown"]
    d["age_band"] = pd.Categorical(d.age_band, categories=["<50","50-64","65-74","75-84","85+"])
    d["race_group"] = pd.Categorical(d.race_group, categories=["White","Black","Hispanic/Latino","Asian","Unknown/other"])
    d["insurance_group"] = pd.Categorical(d.insurance_group, categories=["Private","Medicare","Medicaid","Other/unknown"])
    d["inftype2"] = pd.Categorical(np.where(d.infection_type=="PJI","PJI","Osteomyelitis/other"),
                                   categories=["Osteomyelitis/other","PJI"])
    d["y"]=d[outcome].astype(int)
    f = f"y ~ C(age_band) + female + C(race_group) + C(insurance_group) + C(inftype2)"
    m = smf.logit(f, data=d).fit(disp=0)
    out=[]
    conf=m.conf_int();
    for term in m.params.index:
        if term=="Intercept": continue
        out.append(dict(term=term, OR=round(float(np.exp(m.params[term])),3),
                        ci=[round(float(np.exp(conf.loc[term,0])),3), round(float(np.exp(conf.loc[term,1])),3)],
                        p=float(m.pvalues[term])))
    return dict(name=name, n=int(m.nobs), outcome=outcome, terms=out, pseudo_r2=round(float(m.prsquared),4))

reg_cn = run_logit(ep[ep.has_deep_specimen], "deep_culture_negative_episode", "culture_negative_episode")
reg_poly = run_logit(ep[ep.has_deep_specimen & (ep.n_deep_positive>0)], "episode_polymicrobial", "polymicrobial_episode")
statsd["aim5_logit_culture_negative"]=reg_cn
statsd["aim5_logit_polymicrobial"]=reg_poly

# BH correction across the Aim-5 primary family (all covariate p-values from the culture-negative model)
pvals=[t["p"] for t in reg_cn["terms"]]
rej,padj,_,_=multipletests(pvals, alpha=0.05, method="fdr_bh")
for t,pa,rj in zip(reg_cn["terms"],padj,rej):
    t["p_bh"]=float(pa); t["sig_bh"]=bool(rj)
statsd["aim5_bh_family"]="culture_negative_episode covariates"

# =====================================================================
# save
# =====================================================================
def default(o):
    if isinstance(o,(np.integer,)): return int(o)
    if isinstance(o,(np.floating,)): return float(o)
    if isinstance(o,(np.bool_,)): return bool(o)
    return str(o)
with open(os.path.join(OUT,"results_digest.json"),"w") as f: json.dump(results,f,indent=2,default=default)
with open(os.path.join(OUT,"stats_digest.json"),"w") as f: json.dump(statsd,f,indent=2,default=default)

# export a few CSV tables
pd.DataFrame(gd).T.to_csv(os.path.join(TAB,"organism_genus_overall.csv"))
pd.DataFrame(results["aim3_resistance"]["saureus_panel"]).T.to_csv(os.path.join(TAB,"resistance_saureus_panel.csv"))
pd.DataFrame(results["aim3_resistance"]["gramneg_panel"]).T.to_csv(os.path.join(TAB,"resistance_gramneg_panel.csv"))
pd.DataFrame(reg_cn["terms"]).to_csv(os.path.join(TAB,"logit_culture_negative.csv"), index=False)
pd.DataFrame(reg_poly["terms"]).to_csv(os.path.join(TAB,"logit_polymicrobial.csv"), index=False)

# ---- headline print ----
p("\n================= HEADLINES =================")
a2=results["aim2_culture_negative"]
p(f"Deep-MSK culture-negative (specimen): {a2['specimen_deep_msk_overall']['frac']:.1%} "
  f"CI {a2['specimen_deep_msk_overall']['ci']}")
p(f"  PJI: {a2['by_infection_type']['PJI']['frac']:.1%}  Osteo: {a2['by_infection_type']['Osteomyelitis']['frac']:.1%}")
p(f"  Episode-level culture-negative: {a2['episode_level']['frac']:.1%} CI {a2['episode_level']['ci']}")
p(f"CN by infection type chi2 p={statsd['cn_by_inftype_specimen']['p']:.2e} V={statsd['cn_by_inftype_specimen']['cramers_v']}")
p(f"Top organisms (deep-msk):")
for k,v in list(results['aim1_organism']['by_genus_group'].items())[:8]:
    p(f"   {k:38s} {v['pct']:5.1f}% (n={v['n']})")
mr=results['aim3_resistance']['mrsa_among_saureus']
p(f"MRSA among S. aureus (deep-MSK): {mr['frac']:.1%} CI {mr['ci']} (n tested {mr['tested']})")
p("S. aureus panel %R:")
for ab,v in results['aim3_resistance']['saureus_panel'].items(): p(f"   {ab:20s} {v['pctR']:5.1f}% (n={v['tested']})")
p("Gram-negative panel %R:")
for ab,v in results['aim3_resistance']['gramneg_panel'].items(): p(f"   {ab:20s} {v['pctR']:5.1f}% (n={v['tested']})")
poly=results['aim1_polymicrobial']['overall']
p(f"Polymicrobial episodes: {poly['frac']:.1%} CI {poly['ci']}")
p(f"Diagnostic intensity (median specimens/episode): {results['aim4_intensity']['overall']['specimens_median']}")
p("\nAim5 culture-negative logit (selected, BH-adjusted):")
for t in reg_cn["terms"]:
    if t.get("sig_bh"): p(f"   {t['term']:34s} OR={t['OR']} CI{t['ci']} p_bh={t['p_bh']:.3f}")
p("\nDONE. digests + tables written.")
