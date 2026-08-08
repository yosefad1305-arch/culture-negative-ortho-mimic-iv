"""
Main-text Table 1 and the supplementary eTables. Writes tables.json, consumed by 50_build_docx.py.
"""
import json
import os

import numpy as np
import pandas as pd

from paths import OUT, INT

spec = pd.read_parquet(os.path.join(INT, "specimens.parquet"))
org = pd.read_parquet(os.path.join(INT, "organisms.parquet"))
ep = pd.read_parquet(os.path.join(INT, "episodes.parquet"))
with open(os.path.join(OUT, "results_digest.json"), encoding="utf-8") as f:
    D = json.load(f)

T = {}


def med_iqr(s):
    return f"{s.median():.0f} ({s.quantile(.25):.0f}-{s.quantile(.75):.0f})"


def pct(n, d):
    return f"{n} ({100*n/d:.1f})" if d else "0 (0.0)"


def fmt_p(p):
    """Very small P values are reported as a bound, never as 0.000."""
    return "<0.001" if p < 0.001 else f"{p:.3f}"


# ---------------------------------------------------------------- Table 1
def char_col(d):
    n = len(d)
    return [
        f"{n:,}",
        med_iqr(d.anchor_age),
        pct(int((d.gender == "F").sum()), n),
        pct(int(d.race.str.upper().str.startswith("WHITE", na=False).sum()), n),
        pct(int(d.icu_linked.sum()), n),
        med_iqr(d.los_days),
        pct(int(d.hospital_expire_flag.astype(float).fillna(0).sum()), n),
        pct(int(d.has_strict_specimen.sum()), n),
        pct(int(d.has_generic_specimen.sum()), n),
        med_iqr(d.n_culture_specimens),
    ]


rows = ["No. of episodes", "Age, median (IQR), years", "Female, no. (%)",
        "White race, no. (%)", "ICU stay during admission, no. (%)",
        "Length of stay, median (IQR), days", "In-hospital death, no. (%)",
        "At least 1 source-specific deep specimen, no. (%)",
        "At least 1 generic deep specimen, no. (%)",
        "Culture specimens per episode, median (IQR)"]
cols = {"Overall": ep,
        "Prosthetic joint infection": ep[ep.infection_type == "PJI"],
        "Native osteomyelitis": ep[ep.infection_type == "Osteomyelitis"],
        "Other device infection": ep[ep.infection_type == "Device (other)"]}
T["table1"] = dict(
    caption=("Characteristics of code-defined orthopaedic-infection episodes, overall and by "
             "infection type."),
    header=["Characteristic"] + list(cols),
    rows=[[r] + [char_col(d)[i] for d in cols.values()] for i, r in enumerate(rows)])

# ---------------------------------------------------------------- Table 2 organism spectrum
b_strict = D["spectrum"]["strict|first_isolate_episode"]
b_strict_pat = D["spectrum"]["strict|first_isolate_patient"]
b_strict_all = D["spectrum"]["strict|all_isolates"]
b_pool = D["spectrum"]["pooled|first_isolate_episode"]
orgs = list(b_strict["top_frac"])
t2 = []
for o in orgs:
    t2.append([
        o,
        f"{b_strict['top'].get(o,0)} ({100*b_strict['top_frac'].get(o,0):.1f})",
        f"{b_strict_pat['top'].get(o,0)} ({100*b_strict_pat['top_frac'].get(o,0):.1f})",
        f"{b_strict_all['top'].get(o,0)} ({100*b_strict_all['top_frac'].get(o,0):.1f})",
        f"{b_pool['top'].get(o,0)} ({100*b_pool['top_frac'].get(o,0):.1f})",
    ])
T["table2"] = dict(
    caption=("Organism spectrum of deep musculoskeletal isolates, by specimen label tier "
             "and deduplication rule. Values are no. (%) of speciated isolates."),
    header=["Organism group",
            f"Source-specific, first isolate per episode (n = {b_strict['n_isolates']:,})",
            f"Source-specific, first isolate per patient (n = {b_strict_pat['n_isolates']:,})",
            f"Source-specific, all isolates (n = {b_strict_all['n_isolates']:,})",
            f"Pooled, first isolate per episode (n = {b_pool['n_isolates']:,})"],
    rows=t2)


# ---------------------------------------------------------------- Table 3/4 resistance
def amr_rows(key_prefix, agents_order=None):
    ep_b = D["amr"][f"{key_prefix}|first_isolate_episode|saureus"] if "saureus" in key_prefix \
        else None
    return ep_b


def panel_table(panel_key_ep, panel_key_pat, panel_key_all):
    ep_b = D["amr"][panel_key_ep]
    pat_b = D["amr"][panel_key_pat]
    all_b = D["amr"][panel_key_all]
    out = []
    for ab in ep_b:
        e, p_, a = ep_b[ab], pat_b.get(ab, {}), all_b.get(ab, {})

        def cell(b):
            if not b or b.get("est") is None:
                return f"n = {b.get('n', 0)}, not reported"
            lo, hi = b["clustered_ci"]
            return (f"{b['k']}/{b['n']} ({b['est']*100:.1f}; "
                    f"{lo*100:.1f}-{hi*100:.1f})")
        out.append([ab.title().replace("/Sulfa", "/sulfamethoxazole")
                    .replace("/Tazo", "/tazobactam"), cell(e), cell(p_), cell(a)])
    return out


T["table3"] = dict(
    caption=("Staphylococcus aureus resistance among deep musculoskeletal isolates (pooled tier), "
             "by deduplication rule. Values are resistant/tested (%; patient-clustered 95% CI)."),
    header=["Antimicrobial agent", "First isolate per episode", "First isolate per patient",
            "All isolates"],
    rows=panel_table("pooled|first_isolate_episode|saureus",
                     "pooled|first_isolate_patient|saureus",
                     "pooled|all_isolates|saureus"))

T["table4"] = dict(
    caption=("Gram-negative resistance among deep musculoskeletal isolates (pooled tier), by "
             "deduplication rule. Values are resistant/tested (%; patient-clustered 95% CI)."),
    header=["Antimicrobial agent", "First isolate per episode", "First isolate per patient",
            "All isolates"],
    rows=panel_table("pooled|first_isolate_episode|gramneg",
                     "pooled|first_isolate_patient|gramneg",
                     "pooled|all_isolates|gramneg"))

# ---------------------------------------------------------------- eTables
acct = D["specimen_accounting"]
T["etable_accounting"] = dict(
    caption=("Specimen accounting for the no-growth denominator, by specimen label tier. "
             "Only completed, reported bacterial cultures are evaluable."),
    header=["Tier", "Bacterial cultures", "Positive", "Reported no growth", "Cancelled",
            "Indeterminate", "Evaluable", "Excluded, %"],
    rows=[[{"strict":"Source-specific","generic":"Generic","pooled":"Pooled"}.get(k,k.title()), f"{v['n_bacterial_culture']:,}", f"{v['positive']:,}",
           f"{v['negative']:,}", f"{v['cancelled']:,}", f"{v['indeterminate']:,}",
           f"{v['n_evaluable']:,}", f"{v['excluded_frac']*100:.2f}"]
          for k, v in acct.items()])

sm = spec[spec.has_bacterial_culture].groupby(
    ["tier", "source_category", "spec_type_desc"]).size().rename("n").reset_index()
T["etable_specimen_map"] = dict(
    caption=("Mapping of MIMIC-IV specimen labels to specimen label tiers and source "
             "categories, with specimen counts in the cohort."),
    header=["Tier", "Source category", "MIMIC-IV specimen label", "Specimens"],
    rows=[[{"strict":"Source-specific","generic":"Generic"}.get(str(r.tier),str(r.tier)), r.source_category, r.spec_type_desc, f"{r.n:,}"]
          for r in sm.sort_values(["tier", "source_category", "n"], ascending=[True, True, False])
          .itertuples() if r.tier in ("strict", "generic")])

T["etable_era"] = dict(
    caption=("Oxacillin resistance and source-specific-tier no growth by anchor-year group. MIMIC-IV "
             "chartdates are per-patient date-shifted, so anchor_year_group is the only "
             "admissible era marker."),
    header=["Anchor-year group", "Oxacillin-resistant S. aureus, n/N (%)",
            "Source-specific-tier no growth, n/N (%)"],
    rows=[[k,
           (f"{D['era_mrsa'][k]['k']}/{D['era_mrsa'][k]['n']} "
            f"({D['era_mrsa'][k]['est']*100:.1f})") if k in D["era_mrsa"] else "-",
           (f"{D['era_no_growth_strict'][k]['k']}/{D['era_no_growth_strict'][k]['n']} "
            f"({D['era_no_growth_strict'][k]['est']*100:.1f})")
           if k in D["era_no_growth_strict"] else "-"]
          for k in sorted(set(D["era_no_growth_strict"]) | (set(D["era_mrsa"]) - {"trend_test"}))])

poly = D["polymicrobial"]
# Each rule gets its own label; giving several rows the same name makes the sensitivity
# definitions unreadable.
POLY_RULE = {
    "raw": "Speciated growth, distinct raw laboratory strings",
    "norm": "Speciated growth, distinct normalized dictionary identities",
    "incl_mixed": "Speciated raw strings, plus an explicit report of mixed flora counted as "
                  "polymicrobial",
    "mixed_flora": "Episodes with an explicit report of mixed flora (shown for reference; not a "
                   "polymicrobial rule)",
}
T["etable_poly"] = dict(
    caption=("Polymicrobial fraction among culture-positive episodes, under raw and normalized "
             "organism identity, by tier. Values are n/N (%; patient-clustered 95% CI)."),
    header=["Tier", "Organism identity", "Polymicrobial episodes"],
    rows=[[{"strict":"Source-specific","pooled":"Pooled"}.get(k.split("_")[0],k.split("_")[0].title()),
           POLY_RULE[k.split("_", 1)[1]],
           f"{v['k']}/{v['n']} ({v['est']*100:.1f}; "
           f"{v['clustered_ci'][0]*100:.1f}-{v['clustered_ci'][1]*100:.1f})"]
          for k, v in poly.items()])

grad = D["sampling_gradient_strict"]
T["etable_gradient"] = dict(
    caption=("No growth by number of evaluable source-specific specimens per episode. Values are "
             "n/N (%; patient-clustered 95% CI)."),
    header=["Evaluable source-specific specimens per episode", "No growth"],
    rows=[[k, f"{v['k']}/{v['n']} ({v['est']*100:.1f}; "
           + ("not estimable" if np.isnan(v['clustered_ci'][0])
              else f"{v['clustered_ci'][0]*100:.1f}-{v['clustered_ci'][1]*100:.1f}") + ")"]
          for k, v in grad.items()])

# ---------------------------------------------------------------- eTable 11: full model output
with open(os.path.join(OUT, "stats_digest.json"), encoding="utf-8") as f:
    S = json.load(f)

PRETTY = {
    "infection_type_Osteomyelitis": "Infection type: native osteomyelitis",
    "infection_type_Device (other)": "Infection type: other device infection",
    "age_band_50-64": "Age band: 50-64 years", "age_band_65-79": "Age band: 65-79 years",
    "age_band_80+": "Age band: 80 years or more",
    "gender_M": "Sex: male", "race_group_White": "Race group: White",
    "race_group_Other/Unknown": "Race group: other or unknown",
    "insurance_Medicare": "Insurance: Medicare", "insurance_Private": "Insurance: private",
    "insurance_Other": "Insurance: other",
    "log_n_spec": "Log evaluable source-specific specimens per episode",
}
MODEL_TITLES = {
    "no_growth_infection_type_only": "Model 1: infection type only",
    "no_growth_unadjusted_for_sampling": "Model 2: infection type and case mix",
    "no_growth_adjusted_for_sampling": "Model 3: infection type, case mix and sampling intensity",
}
reg_rows = []
for key in ["no_growth_infection_type_only", "no_growth_unadjusted_for_sampling",
            "no_growth_adjusted_for_sampling"]:
    m = S.get(key, {})
    if "coefficients" not in m:
        continue
    refs = ", ".join(f"{k} = {v}" for k, v in m.get("reference_levels", {}).items())
    reg_rows.append([MODEL_TITLES[key],
                     f"n = {m['n']:,} specimens; {m['n_clusters']:,} patients; "
                     f"{m['n_events']:,} no-growth events. Reference categories: {refs or 'none'}",
                     "", "", "", ""])
    for term, v in m["coefficients"].items():
        reg_rows.append([
            "", PRETTY.get(term, term),
            f"{v['n_in_level']:,}", f"{v['events_in_level']:,}",
            f"{v['or_']:.2f} ({v['ci'][0]:.2f}-{v['ci'][1]:.2f})",
            fmt_p(v["p"]) + (f" / {fmt_p(v['p_bh'])}" if "p_bh" in v else " / -")])

T["etable_regression"] = dict(
    caption=("eTable 10. Complete output of the patient-clustered logistic models for no growth "
             "in the source-specific tier. Odds ratios carry cluster-robust 95% confidence intervals. P "
             "values are given as raw / Benjamini-Hochberg adjusted within each model; a dash "
             "indicates that multiplicity correction was not applied to that model."),
    header=["Model", "Term", "Specimens in level", "Events in level",
            "Odds ratio (95% CI)", "P raw / P adjusted"],
    rows=reg_rows)

# ---------------------------------------------------------------- eTable 12: exact intervals
exact_rows = []
for name, blk in [("No growth, source-specific tier", D["no_growth"]["strict"]),
                  ("No growth, generic tier", D["no_growth"]["generic"]),
                  ("No growth, pooled", D["no_growth"]["pooled"]),
                  ("Polymicrobial, source-specific tier", D["polymicrobial"]["strict_raw"]),
                  ("Polymicrobial, pooled", D["polymicrobial"]["pooled_raw"]),
                  ("Oxacillin resistance, first isolate per episode",
                   D["mrsa"]["pooled|first_isolate_episode"]),
                  ("Oxacillin resistance, first isolate per patient",
                   D["mrsa"]["pooled|first_isolate_patient"])]:
    exact_rows.append([
        name, f"{blk['k']:,}/{blk['n']:,}", f"{blk['est']*100:.1f}",
        f"{blk['exact_ci'][0]*100:.1f}-{blk['exact_ci'][1]*100:.1f}",
        f"{blk['clustered_ci'][0]*100:.1f}-{blk['clustered_ci'][1]*100:.1f}",
        f"{blk['n_clusters']:,}"])
T["etable_exact"] = dict(
    caption=("eTable 11. Naive exact (Clopper-Pearson) intervals alongside the patient-clustered "
             "bootstrap intervals used for inference, showing the cost of ignoring clustering. "
             "Exact intervals are provided for reference only."),
    header=["Estimate", "Events/total", "%", "Exact 95% CI", "Patient-clustered 95% CI",
            "Patients"],
    rows=exact_rows)

# ---------------------------------------------------------------- eTable 12: primary analysis
w = D["within_episode"]
pt13 = w["paired_table"]
ptst = w["paired_test"]
cl = w["conditional_logit"]
m11 = w["matched_1to1"]
n_ep = pt13["n_episodes"]


def _pc(k, n):
    return f"{k}/{n} ({100*k/n:.1f})" if n else "-"


rows13 = [
    ["Paired cohort", "Episodes contributing an evaluable specimen in both tiers",
     f"{n_ep:,} episodes in {w['n_patients']:,} patients"],
    ["", "Evaluable specimens per episode, median (source-specific; generic)",
     f"{w['median_specimens']['strict']:.0f}; {w['median_specimens']['generic']:.0f}"],
    ["", "Infection type of paired episodes",
     "; ".join(f"{k} {v}" for k, v in w["by_infection_type"].items())],

    ["Episode-level outcome", "Definition", pt13["definition"]],
    ["", "Both tiers entirely negative", f"{pt13['both_all_negative']:,}"],
    ["", "Both tiers had at least one positive specimen", f"{pt13['both_had_a_positive']:,}"],
    ["", "Source-specific tier entirely negative only",
     f"{pt13['strict_all_negative_only']:,}"],
    ["", "Generic tier entirely negative only", f"{pt13['generic_all_negative_only']:,}"],
    ["", "Source-specific tier entirely negative, total",
     _pc(pt13["strict_all_negative_total"], n_ep)],
    ["", "Generic tier entirely negative, total",
     _pc(pt13["generic_all_negative_total"], n_ep)],

    ["Paired inference", "Discordant episodes", f"{ptst['discordant']:,}"],
    ["", "Paired difference, source-specific minus generic (percentage points)",
     f"{ptst['diff']*100:+.1f} (patient-clustered 95% CI "
     f"{ptst['diff_ci'][0]*100:+.1f} to {ptst['diff_ci'][1]*100:+.1f}); "
     f"bootstrap P = {ptst['patient_clustered_p']:.4f}"],
    ["", "Exact McNemar, unclustered (reference only; assumes independent pairs)",
     f"P = {ptst['mcnemar_naive_p']:.5f}"],

    ["Episode-stratified conditional logistic regression",
     "Input sample",
     f"{cl['n_specimens_input']:,} specimens in {cl['n_strata_input']:,} episodes"],
    ["", "Retained sample (episodes varying in both outcome and tier)",
     f"{cl['n_specimens_retained']:,} specimens in {cl['n_strata_retained']:,} informative "
     f"episodes from {cl['n_patients_retained']:,} patients"],
    ["", "Patients contributing more than one informative episode",
     f"{cl['n_patients_multi_episode']:,}"],
    ["", "Odds ratio for no growth, source-specific vs generic (patient-clustered)",
     f"{cl['or_']:.2f} (95% CI, {cl['ci'][0]:.2f}-{cl['ci'][1]:.2f}); "
     f"P = {fmt_p(cl['p'])}"],
    ["", "Same model, unclustered model-based interval (reference only)",
     f"{cl['or_']:.2f} (95% CI, {cl['ci_model_based'][0]:.2f}-"
     f"{cl['ci_model_based'][1]:.2f}); P = {fmt_p(cl['p_model_based'])}"],
    ["", "Bootstrap replicates used for the clustered interval", f"{cl['n_bootstrap']:,}"],

    ["One-to-one matched subset",
     "Episodes contributing exactly one evaluable specimen in each tier",
     f"{m11['n_episodes']:,} episodes in {m11['n_patients']:,} patients"],
    ["", "Both negative", f"{m11['both_negative']:,}"],
    ["", "Source-specific negative only", f"{m11['strict_negative_only']:,}"],
    ["", "Generic negative only", f"{m11['generic_negative_only']:,}"],
    ["", "Both positive", f"{m11['both_positive']:,}"],
    ["", "Exact McNemar (reference only)", f"P = {m11['mcnemar_naive_p']:.4f}"],

    ["Specimen-level sensitivity (episode NOT held fixed)",
     "Specimen-level no growth, source-specific tier",
     f"{w['specimen_level_strict']['k']:,}/{w['specimen_level_strict']['n']:,} "
     f"({w['specimen_level_strict']['est']*100:.1f}; "
     f"{w['specimen_level_strict']['clustered_ci'][0]*100:.1f}-"
     f"{w['specimen_level_strict']['clustered_ci'][1]*100:.1f})"],
    ["", "Specimen-level no growth, generic tier",
     f"{w['specimen_level_generic']['k']:,}/{w['specimen_level_generic']['n']:,} "
     f"({w['specimen_level_generic']['est']*100:.1f}; "
     f"{w['specimen_level_generic']['clustered_ci'][0]*100:.1f}-"
     f"{w['specimen_level_generic']['clustered_ci'][1]*100:.1f})"],
]
_sens = w.get("clustered_logit_sensitivity", {}).get("coefficients", {}).get("tier_strict")
if _sens:
    rows13.append(
        ["", "Patient-clustered specimen-level odds ratio (pools specimens across episodes; "
         "does not hold the episode fixed)",
         f"{_sens['or_']:.2f} (95% CI, {_sens['ci'][0]:.2f}-{_sens['ci'][1]:.2f}); "
         f"P = {fmt_p(_sens['p'])}"])

T["etable_within"] = dict(
    caption=("eTable 12. Within-episode comparison of specimen label tiers, the study's primary "
             "comparison, reported in full. A tier counts as negative for an episode only when "
             "every one of its evaluable specimens grew nothing. Percentages are of the paired "
             "cohort unless stated otherwise."),
    header=["Analysis", "Quantity", "Value"],
    rows=rows13)

with open(os.path.join(OUT, "tables.json"), "w", encoding="utf-8") as f:
    json.dump(T, f, indent=2)
print("wrote tables.json with:", ", ".join(T))
