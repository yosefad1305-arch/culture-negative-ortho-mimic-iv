"""
Optional AI/ML measurement probe (Phase 5): how anticipatable is deep-specimen culture-negativity
from routinely captured pre/peri-culture STRUCTURED data? This is a MEASUREMENT probe, not a
deployable predictor. Two nested models compared by paired bootstrap of out-of-fold predictions:
  M1 (clinical context only): infection type + specimen source mix + diagnostic intensity + demographics
  M2 (+ inflammatory/nutritional labs): M1 + WBC/CRP/ESR/albumin/neutrophils (with informative-missingness indicators)
Report OOF AUROC (bootstrap 95% CI) + Brier for each, and the paired AUROC difference (95% CI, bootstrap P).
A modest AUROC that labs barely improve REINFORCES the thesis: culture-negativity is not an artifact
readily explained by routine structured data.
"""
import os, json, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import StratifiedKFold, StratifiedGroupKFold
from sklearn.metrics import roc_auc_score, brier_score_loss

PROJ=r"C:\Users\Owner\ortho-mimic-study"; INT=os.path.join(PROJ,"output","intermediate"); OUT=os.path.join(PROJ,"output")
def p(*a): print(*a,flush=True)
rng=np.random.RandomState(20260702)

ep=pd.read_parquet(os.path.join(INT,"episodes.parquet"))
spec=pd.read_parquet(os.path.join(INT,"specimens.parquet"))
labs=pd.read_parquet(os.path.join(INT,"labs.parquet"))

# analytic cohort: episodes with >=1 deep MSK culture specimen
d=ep[ep.has_deep_specimen].copy()
# per-episode deep source-category flags
sp=spec[spec.has_culture_test & spec.is_deep_msk]
cat=sp.groupby("hadm_id").source_category.agg(lambda s:set(s))
d["has_tissue_bone"]=d.hadm_id.map(lambda h: "deep_tissue_bone" in cat.get(h,set())).astype(int)
d["has_synovial"]=d.hadm_id.map(lambda h: "synovial_joint" in cat.get(h,set())).astype(int)
d["has_sonication"]=d.hadm_id.map(lambda h: "implant_sonication" in cat.get(h,set())).astype(int)

def race_group(r):
    r=str(r).upper()
    if r.startswith("WHITE"):return "White"
    if r.startswith("BLACK"):return "Black"
    if "HISPANIC" in r or "LATINO" in r:return "Hispanic"
    if r.startswith("ASIAN"):return "Asian"
    return "Other"
d["race_group"]=d.race.map(race_group)
d["ins_group"]=d.insurance.map(lambda i: i if str(i) in ("Medicare","Medicaid","Private") else "Other")
d["is_pji"]=(d.infection_type=="PJI").astype(int)
d["female"]=(d.gender=="F").astype(int)
d=d.merge(labs, on="hadm_id", how="left")

y=d.deep_culture_negative_episode.astype(int).values
p(f"analytic n={len(d)}, culture-negative episodes={y.sum()} ({y.mean():.1%})")
# marker missingness (reviewer 1, minor concern): report the fraction missing per lab
miss={c: round(float(d[c].isna().mean()),3) for c in ["wbc_peak","crp_peak","esr_peak","albumin_first","neutro_pct_peak"]}
p("marker missing fractions:", miss)

# feature sets
# NOTE: n_deep_specimens is intentionally EXCLUDED. The outcome is "all deep specimens no growth",
# so specimen count is mechanically anti-correlated with the outcome (more draws -> lower chance of
# all-negative) and would inject definitional signal (reviewer 1, major concern 5).
base_num=["anchor_age","female","is_pji","has_tissue_bone","has_synovial","has_sonication"]
race_d=pd.get_dummies(d.race_group,prefix="race",drop_first=True).astype(float)
ins_d=pd.get_dummies(d.ins_group,prefix="ins",drop_first=True).astype(float)
X_base=pd.concat([d[base_num].astype(float).reset_index(drop=True),
                  race_d.reset_index(drop=True), ins_d.reset_index(drop=True)],axis=1)

lab_cols=["wbc_peak","crp_peak","esr_peak","albumin_first","neutro_pct_peak"]
lab_df=d[lab_cols].astype(float).copy()
# informative-missingness indicators for the sparser markers
for c in ["crp_peak","esr_peak","albumin_first"]:
    lab_df[c+"_missing"]=d[c].isna().astype(float).values
# log-transform skewed markers
for c in ["wbc_peak","crp_peak","esr_peak"]:
    lab_df[c]=np.log1p(lab_df[c])
X_full=pd.concat([X_base.reset_index(drop=True), lab_df.reset_index(drop=True)],axis=1)

def oof_probs_y(X, yv, groups=None):
    X=np.asarray(X)
    # StratifiedGroupKFold on subject_id so a patient's episodes never split across folds (audit J1).
    if groups is not None:
        skf=StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=42)
        splits=skf.split(X,yv,groups)
    else:
        skf=StratifiedKFold(n_splits=5,shuffle=True,random_state=42); splits=skf.split(X,yv)
    oof=np.zeros(len(yv))
    for tr,te in splits:
        pipe=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),
                           LogisticRegression(max_iter=2000))
        pipe.fit(X[tr],yv[tr]); oof[te]=pipe.predict_proba(X[te])[:,1]
    return oof

def oof_probs(X):
    return oof_probs_y(X.values, y, groups=d.subject_id.values)

p("Cross-validating M1 (context) and M2 (+labs)...")
oof1=oof_probs(X_base); oof2=oof_probs(X_full)

# M2b: drop the highest-missingness markers (ESR 76%, albumin 57%); keep WBC/CRP/neutrophil.
low_miss=["wbc_peak","crp_peak","neutro_pct_peak"]
lab_lm=d[low_miss].astype(float).copy()
for c in ["wbc_peak","crp_peak"]: lab_lm[c]=np.log1p(lab_lm[c])
lab_lm["crp_peak_missing"]=d["crp_peak"].isna().astype(float).values
X_lm=pd.concat([X_base.reset_index(drop=True), lab_lm.reset_index(drop=True)],axis=1)
oof2b=oof_probs(X_lm)

def boot_auc(oof,y,B=2000):
    aucs=[]
    idx=np.arange(len(y))
    for _ in range(B):
        s=rng.choice(idx,len(idx),replace=True)
        if len(np.unique(y[s]))<2: continue
        aucs.append(roc_auc_score(y[s],oof[s]))
    return np.percentile(aucs,[2.5,97.5])

def paired_boot(oof1,oof2,y,B=2000):
    diffs=[]; idx=np.arange(len(y))
    for _ in range(B):
        s=rng.choice(idx,len(idx),replace=True)
        if len(np.unique(y[s]))<2: continue
        diffs.append(roc_auc_score(y[s],oof2[s])-roc_auc_score(y[s],oof1[s]))
    diffs=np.array(diffs)
    ci=np.percentile(diffs,[2.5,97.5]); pval=2*min((diffs<=0).mean(),(diffs>=0).mean())
    return float(diffs.mean()),[float(ci[0]),float(ci[1])],float(pval)

a1=roc_auc_score(y,oof1); a2=roc_auc_score(y,oof2)
ci1=boot_auc(oof1,y); ci2=boot_auc(oof2,y)
b1=brier_score_loss(y,oof1); b2=brier_score_loss(y,oof2)
dmean,dci,dp=paired_boot(oof1,oof2,y)

# complete-case sensitivity: does the lab increment survive when restricted to episodes with all
# markers measured (i.e., not driven by informative-missingness indicators)? (reviewer 1, concern 3)
cc_mask = d[lab_cols].notna().all(axis=1).values
n_cc=int(cc_mask.sum())
cc={}
if n_cc>200 and len(np.unique(y[cc_mask]))>1:
    Xb_cc=X_base[cc_mask].reset_index(drop=True)
    # values-only labs (no missingness indicators) on complete cases
    labv=d.loc[cc_mask, lab_cols].astype(float).copy()
    for c in ["wbc_peak","crp_peak","esr_peak"]: labv[c]=np.log1p(labv[c])
    Xf_cc=pd.concat([Xb_cc, labv.reset_index(drop=True)],axis=1)
    ycc=y[cc_mask]
    g_cc=d.loc[cc_mask,"subject_id"].values
    o1=oof_probs_y(Xb_cc.values,ycc,groups=g_cc); o2=oof_probs_y(Xf_cc.values,ycc,groups=g_cc)
    cc=dict(n=n_cc, M1_auroc=round(roc_auc_score(ycc,o1),3), M2_auroc=round(roc_auc_score(ycc,o2),3),
            delta=round(roc_auc_score(ycc,o2)-roc_auc_score(ycc,o1),4))

res=dict(
  n=int(len(y)), n_positive=int(y.sum()), prevalence=round(float(y.mean()),4),
  M1_context=dict(auroc=round(a1,3),auroc_ci=[round(ci1[0],3),round(ci1[1],3)],brier=round(b1,4),n_features=X_base.shape[1]),
  M2_with_labs=dict(auroc=round(a2,3),auroc_ci=[round(ci2[0],3),round(ci2[1],3)],brier=round(b2,4),n_features=X_full.shape[1]),
  paired_auroc_gain=dict(delta=round(dmean,4),ci=[round(dci[0],4),round(dci[1],4)],bootstrap_p=round(dp,4)),
  marker_missing_fraction=miss,
  complete_case=cc,
  M2b_low_missingness_only=dict(auroc=round(roc_auc_score(y,oof2b),3),
     auroc_ci=[round(x,3) for x in boot_auc(oof2b,y)],
     note="M1 + WBC/CRP/neutrophil only (ESR 76% and albumin 57% missing dropped)"),
  model_card=dict(library="scikit-learn", estimator="LogisticRegression(max_iter=2000)",
     preprocessing="median imputation + informative-missingness indicators + StandardScaler",
     cv="5-fold stratified, out-of-fold predictions", cv_seed=42, bootstrap_seed=20260702,
     features_excluded="n_deep_specimens (definitionally tied to the outcome)",
     note="Measurement probe only; not externally validated; not a deployable clinical tool."))
json.dump(res,open(os.path.join(OUT,"ml_digest.json"),"w"),indent=2)
p("\n=== ML measurement probe ===")
p(f"M1 (context):   AUROC {a1:.3f} CI[{ci1[0]:.3f},{ci1[1]:.3f}]  Brier {b1:.4f}")
p(f"M2 (+labs):     AUROC {a2:.3f} CI[{ci2[0]:.3f},{ci2[1]:.3f}]  Brier {b2:.4f}")
p(f"paired gain:    {dmean:+.4f} CI[{dci[0]:.4f},{dci[1]:.4f}] bootstrap p={dp:.3f}")
p("ml_digest.json written.")
