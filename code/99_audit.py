"""
Consistency audit: every quantitative claim asserted in the manuscript is restated here as an
expected value and checked against results_digest.json / stats_digest.json. Point estimates and
confidence-interval bounds are both checked, because an interval can drift while the estimate is
unchanged. Journal formatting limits are enforced too. Exits non-zero on any mismatch, so a number
cannot drift between the analysis and the prose.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import manuscript_text as M

from paths import OUT

D = json.load(open(os.path.join(OUT, "results_digest.json"), encoding="utf-8"))
S = json.load(open(os.path.join(OUT, "stats_digest.json"), encoding="utf-8"))

RESULTS_TEXT = " ".join(t for _, ps in M.RESULTS for t in ps)

FULL = " ".join(
    [M.TITLE] + [b for _, b in M.ABSTRACT] + M.INTRODUCTION + M.DISCUSSION
    + [t for _, ps in M.METHODS for t in ps] + [t for _, ps in M.RESULTS for t in ps]
    + [b for _, b in M.FIGURE_LEGENDS])

fails, checks = [], 0


def claim(text, present=True):
    global checks
    checks += 1
    if (text in FULL) != present:
        fails.append(f"{'MISSING' if present else 'PRESENT'}: {text!r}")


def node(path):
    n = D
    for k in path.split("::"):
        n = n[k]
    return n


def est(path, expected, tol=0.055):
    """Check a percentage point estimate."""
    global checks
    checks += 1
    got = node(path)["est"] * 100
    if abs(got - expected) > tol:
        fails.append(f"{path}: digest {got:.2f}% vs text {expected}%")


def ci(path, dec=1):
    """Check that the patient-clustered interval appears verbatim in the prose."""
    global checks
    checks += 1
    lo, hi = node(path)["clustered_ci"]
    text = f"{lo*100:.{dec}f}-{hi*100:.{dec}f}"
    if text not in FULL:
        fails.append(f"CI for {path}: digest says {text}, not found in manuscript")


def count(path, key, expected):
    global checks
    checks += 1
    got = node(path)[key]
    if got != expected:
        fails.append(f"{path}.{key}: digest {got} vs text {expected}")


# ---- cohort
count("cohort", "n_episodes", 7697)
count("cohort", "n_patients", 4358)
count("cohort", "n_with_strict", 653)
count("cohort", "n_with_generic", 3397)
claim("7697 orthopaedic-infection episodes in 4358 patients")
claim("653 episodes (8.5%; 552 patients)")
claim("3397 (44.1%)")
claim("439 of 653, 67.2%")

# ---- accounting
acc = D["specimen_accounting"]
checks += 1
if (acc["strict"]["n_bacterial_culture"], acc["strict"]["n_evaluable"]) != (887, 885):
    fails.append(f"strict accounting {acc['strict']}")
checks += 1
if (acc["generic"]["n_bacterial_culture"], acc["generic"]["n_evaluable"]) != (6811, 6777):
    fails.append(f"generic accounting {acc['generic']}")
claim("of 887 "
      "source-specific and 6811 generic bacterial cultures, 885 and 6777 respectively were "
      "evaluable")
checks += 1
if abs(acc["pooled"]["excluded_frac"] * 100 - 0.47) > 0.006:
    fails.append(f"pooled exclusion {acc['pooled']['excluded_frac']*100:.3f}% vs text 0.47%")
claim("an exclusion of 0.47% across all deep specimens")

# ---- between-cohort no growth
est("no_growth::strict", 48.0)
est("no_growth::generic", 34.0)
est("no_growth::pooled", 35.6)
est("no_growth::strict_by_source::synovial_joint", 55.1)
est("no_growth::strict_by_source::implant_sonication", 24.5)
for pth in ["no_growth::strict", "no_growth::generic", "no_growth::pooled",
            "no_growth::strict_by_source::synovial_joint",
            "no_growth::strict_by_source::implant_sonication"]:
    ci(pth)
claim("48.0% of evaluable source-specific specimens (425 of 885")
claim("34.0% of generic specimens (2304 of 6777")
claim("35.6% (2729 of 7662")

# ---- within-episode (the primary comparison)
w = D["within_episode"]
checks += 1
if (w["n_episodes"], w["n_patients"]) != (487, 421):
    fails.append(f"within-episode cohort {w['n_episodes']}/{w['n_patients']} vs text 487/421")
claim("487 episodes (421 "
      "patients)")
checks += 1
if (w["median_specimens"]["strict"], w["median_specimens"]["generic"]) != (1.0, 3.0):
    fails.append(f"median specimens per episode {w['median_specimens']}")
claim("median episode supplied 1 evaluable source-specific specimen and 3 "
      "generic ones")

# The episode-level outcome must be the all-negative definition, never any-negative.
pt = w["paired_table"]
checks += 1
if "all its evaluable specimens" not in pt.get("definition", ""):
    fails.append("paired table does not record the all-evaluable-negative definition")
checks += 1
if (pt["both_all_negative"], pt["both_had_a_positive"], pt["strict_all_negative_only"],
        pt["generic_all_negative_only"]) != (102, 237, 96, 52):
    fails.append(f"paired table {pt}")
claim("102 "
      "were entirely negative on both tiers and 237 had at least one positive specimen in each")
claim("96 were entirely negative only on the source-specific tier "
      "and 52 only on the generic tier")
checks += 1
if (pt["strict_all_negative_total"], pt["generic_all_negative_total"]) != (198, 154):
    fails.append(f"tier all-negative totals {pt['strict_all_negative_total']}/"
                 f"{pt['generic_all_negative_total']} vs text 198/154")
claim("entirely negative in 198 of 487 episodes "
      "(40.7%) and the generic tier in 154 of 487 (31.6%)")

ptst = w["paired_test"]
checks += 1
if ptst["discordant"] != 148:
    fails.append(f"discordant {ptst['discordant']} vs text 148")
claim("148 discordant episodes")
checks += 1
if abs(ptst["diff"] * 100 - 9.0) > 0.06:
    fails.append(f"paired difference {ptst['diff']*100:.2f} vs text 9.0")
checks += 1
lo, hi = ptst["diff_ci"]
if f"{lo*100:.1f}-{hi*100:.1f}" not in FULL:
    fails.append(f"paired difference CI {lo*100:.1f}-{hi*100:.1f} not in manuscript")
claim("bootstrap P = .0005")
# The naive McNemar must be labelled as reference only, never used for inference.
checks += 1
if "reference only" not in ptst.get("note", ""):
    fails.append("naive McNemar is not marked reference-only in the digest")
claim("the exact "
      "McNemar test is reported alongside for reference only, as it assumes independent pairs")

# The episode-stratified model is the one the Methods describe; it must actually be fitted.
cl = w["conditional_logit"]
checks += 1
if "error" in cl:
    fails.append(f"conditional logistic model did not fit: {cl['error']}")
elif (abs(cl["or_"] - 0.86) > 0.006 or abs(cl["ci"][0] - 0.64) > 0.006
      or abs(cl["ci"][1] - 1.15) > 0.006 or abs(cl["p"] - 0.33) > 0.007):
    fails.append(f"conditional logit OR {cl['or_']:.2f} ({cl['ci'][0]:.2f}-{cl['ci'][1]:.2f}) "
                 f"P {cl['p']:.3f} vs text 0.86 (0.64-1.15) P .33")
# The unclustered interval must also be reported, and must be the narrower one.
checks += 1
if not (cl["ci_model_based"][1] - cl["ci_model_based"][0] < cl["ci"][1] - cl["ci"][0]):
    fails.append("model-based interval is not narrower than the patient-clustered one")
claim("odds ratio, 0.86; 0.64-1.15")
claim("0.86 (95% CI, 0.64-1.15; P = .33)")
claim("the unclustered model-based interval was "
      "narrower (0.67-1.10)")
claim("1227 specimens in 252 informative episodes from 233 "
      "patients, of whom 16 contributed more than one informative episode")

m11 = w["matched_1to1"]
checks += 1
if (m11["n_episodes"], m11["strict_negative_only"], m11["generic_negative_only"]) != (75, 25, 14):
    fails.append(f"1:1 matched subset {m11}")
claim("75 episodes (74 patients) that contributed exactly one evaluable specimen in each "
      "tier")
claim("25 were negative only on "
      "the source-specific specimen and 14 only on the generic one (exact McNemar P = .11)")

# Direction: both the between-cohort and the episode-level within comparison must show the
# source-specific tier HIGHER. A reversal claim would be an artefact of an any-negative rule.
checks += 1
if not (node("no_growth::strict")["est"] > node("no_growth::generic")["est"]):
    fails.append("between-cohort ordering does not show source-specific ABOVE generic")
checks += 1
if not (pt["strict_all_negative_total"] > pt["generic_all_negative_total"]):
    fails.append("episode-level ordering does not show source-specific ABOVE generic")
checks += 1
if ptst["diff"] <= 0:
    fails.append("paired difference is not positive; the manuscript states +9.0 points")

# ---- polymicrobial and low-resolution growth
est("polymicrobial::strict_raw", 10.9)
est("polymicrobial::pooled_raw", 42.1)
est("polymicrobial::strict_norm", 10.3)
est("polymicrobial::pooled_norm", 41.1)
est("polymicrobial::pooled_incl_mixed", 50.8)
est("polymicrobial::pooled_mixed_flora", 23.3)
est("polymicrobial::strict_mixed_flora", 0.3)
for pth in ["polymicrobial::strict_raw", "polymicrobial::pooled_raw",
            "polymicrobial::pooled_incl_mixed", "polymicrobial::pooled_mixed_flora"]:
    ci(pth)
claim("10.9% were polymicrobial (38 of 348")
claim("42.1% pooled (1174 of "
      "2789")
claim("source-specific 10.3%; pooled 41.1%")
claim("from 42.1% to 50.8% (1417 of 2789")
claim("23.3% "
      "of pooled culture-positive episodes (651 of 2789")
claim("only 0.3% of "
      "source-specific ones")

# ---- deduplication scope
sp = D["spectrum"]
checks += 1
for key, n in [("strict|all_isolates", 510), ("strict|first_isolate_episode", 395),
               ("strict|first_isolate_patient", 367),
               ("pooled|first_isolate_episode", 4547)]:
    if sp[key]["n_isolates"] != n:
        fails.append(f"spectrum {key} n={sp[key]['n_isolates']} vs text {n}")
for key, exp in [("strict|all_isolates", 48.2), ("strict|first_isolate_episode", 45.3),
                 ("strict|first_isolate_patient", 43.3), ("pooled|first_isolate_episode", 29.0)]:
    checks += 1
    got = sp[key]["top_frac"]["Staphylococcus aureus"] * 100
    if abs(got - exp) > 0.06:
        fails.append(f"S. aureus {key}: digest {got:.2f}% vs text {exp}%")
claim("48.2% of 510 unduplicated isolates, 45.3% of 395 first isolates per episode")
claim("43.3% of 367 first isolates per patient")
claim("S. aureus at 29.0% of 4547 episode-first")
est("saureus_share_strict_epfirst", 45.3)
ci("saureus_share_strict_epfirst")
claim("175 of 395 episode-first source-specific "
      "isolates (43.2%)")

# ---- resistance
est("mrsa::pooled|all_isolates", 43.2)
est("mrsa::pooled|first_isolate_episode", 43.0)
est("mrsa::pooled|first_isolate_patient", 40.5)
ci("mrsa::pooled|first_isolate_episode")
ci("mrsa::pooled|first_isolate_patient")
claim("43.2% of 1143 S. aureus isolates")
claim("43.0% per episode (353 "
      "of 820")
claim("40.5% per patient (274 of 676")
sa = D["amr"]["pooled|first_isolate_episode|saureus"]
gn = D["amr"]["pooled|first_isolate_episode|gramneg"]
for panel, ab, exp in [(sa, "ERYTHROMYCIN", 60.5), (sa, "LEVOFLOXACIN", 40.2),
                       (sa, "CLINDAMYCIN", 39.7), (sa, "TETRACYCLINE", 9.4),
                       (sa, "TRIMETHOPRIM/SULFA", 3.2), (sa, "RIFAMPIN", 3.2),
                       (sa, "GENTAMICIN", 2.2),
                       (gn, "CIPROFLOXACIN", 23.7), (gn, "TRIMETHOPRIM/SULFA", 23.5),
                       (gn, "MEROPENEM", 3.9), (gn, "TOBRAMYCIN", 6.1)]:
    checks += 1
    got = panel[ab]["est"] * 100
    if abs(got - exp) > 0.06:
        fails.append(f"AMR {ab}: digest {got:.2f}% vs text {exp}%")
ci("amr::pooled|first_isolate_episode|saureus::ERYTHROMYCIN")
ci("amr::pooled|first_isolate_episode|gramneg::CIPROFLOXACIN")
ci("amr::pooled|first_isolate_episode|gramneg::MEROPENEM")
# zero-event handling
checks += 1
v = sa["VANCOMYCIN"]
if v["k"] != 0 or v["n"] != 364 or not v.get("zero_event") or v["clustered_ci"][1] <= 0:
    fails.append(f"vancomycin block {v}")
claim("0 of 364, upper 97.5% bound 1.1% on the contributing patients")

# ---- ICU and era
est("icu_mrsa::icu", 44.5)
est("icu_mrsa::non_icu", 42.8)
checks += 1
icu = D["icu_mrsa"]["clustered_logit"]["coefficients"]["icu"]
if abs(icu["or_"] - 1.07) > 0.006 or abs(icu["p"] - 0.70) > 0.006:
    fails.append(f"ICU logit OR {icu['or_']:.3f} P {icu['p']:.3f} vs text 1.07 / .70")
claim("odds ratio, 1.07; 0.74-1.56; P = .70")
claim("Only 15.8% of episodes involved an intensive care stay")
est("era_mrsa::2008 - 2010", 46.0)
est("era_mrsa::2020 - 2022", 35.4)
claim("46.0% (2008-2010) to 35.4% (2020-2022)")
checks += 1
if abs(D["era_mrsa"]["trend_test"]["p"] - 0.48) > 0.006:
    fails.append(f"era omnibus P {D['era_mrsa']['trend_test']['p']:.3f} vs text .48")
claim("omnibus P = .48")

# ---- exploratory infection-type contrast
for key, exp_or, lo, hi in [("no_growth_unadjusted_for_sampling", 2.05, 1.38, 3.05),
                            ("no_growth_adjusted_for_sampling", 1.96, 1.33, 2.90)]:
    checks += 1
    mm = S[key]
    if mm.get("reference_levels", {}).get("infection_type") != "PJI":
        fails.append(f"{key}: infection_type reference is not PJI")
    o = mm["coefficients"]["infection_type_Osteomyelitis"]
    if (abs(o["or_"] - exp_or) > 0.006 or abs(o["ci"][0] - lo) > 0.006
            or abs(o["ci"][1] - hi) > 0.006):
        fails.append(f"{key} osteo OR {o['or_']:.2f} ({o['ci'][0]:.2f}-{o['ci'][1]:.2f})")
claim("odds ratio 2.05 (1.38-3.05) adjusted for age band, sex, race group and insurance category")
claim("Benjamini-Hochberg adjusted P = .004")
claim("1.96 (1.33-2.90) with further adjustment for "
      "the number of specimens obtained (adjusted P = .009)")
est("no_growth::strict_by_infection_type::Osteomyelitis", 61.7)
est("no_growth::strict_by_infection_type::PJI", 43.4)
ci("no_growth::strict_by_infection_type::Osteomyelitis")
ci("no_growth::strict_by_infection_type::PJI")
m = S["no_growth_unadjusted_for_sampling"]["coefficients"]
checks += 1
g = m["gender_M"]
if abs(g["or_"] - 0.80) > 0.006 or abs(g["p"] - 0.193) > 0.006:
    fails.append(f"male OR {g['or_']:.2f} P {g['p']:.3f}")
claim("odds ratio for male "
      "sex, 0.80; 0.58-1.12; P = .19")
checks += 1
socio = [k for k in m if k.startswith(("age_band", "gender", "race_group", "insurance"))]
if any(m[k]["p_bh"] <= 0.05 for k in socio):
    fails.append("a sociodemographic term survives BH correction; the text says none does")
claim("No sociodemographic coefficient "
      "remained statistically significant after correction")
# The infection-type contrast must be labelled exploratory.
claim("contrast is exploratory: only 167 "
      "osteomyelitis episodes contributed a source-specific specimen")
# Results must not carry interpretation; these phrases belong in the Discussion. Checked
# against the Results text only, because several of them legitimately appear there.
for _interp in ["Reporting the pooled value alone", "organism-string handling is not what",
                "should be read as a floor", "does not establish zero population risk",
                "This contrast should be read as exploratory",
                "consistent with the reported advantage", "soft-tissue flora",
                "not explained by intensive-care case mix", "Taken together"]:
    checks += 1
    if _interp in RESULTS_TEXT:
        fails.append(f"interpretation in Results: {_interp!r}")
# Prespecification is not claimed without a dated protocol.
for _pp in ["a priori", "prespecified rule", "because it is prespecified"]:
    claim(_pp, present=False)

# ---- claims that must NOT be present
for banned in ["AUROC", "area under the receiver", "anticipat", "TRIPOD",
               "intensive-care enrichment", "rose monotonically", "interpretive comment",
               "anatomically certain", "reproduces, in routine data, the advantage",
               "ambiguity governs", "Three comparisons reverse",
               "the difference reversed", "the ordering reversed", "difference reverses",
               "Case selection, not label ambiguity", "case selection rather than to the label",
               "attributes that difference to case selection",
               "pairs are independent at the episode level"]:
    claim(banned, present=False)

# ---- journal formatting limits
# A margin is kept below both ceilings, because a submission system may tokenise differently.
abstract_words = sum(len(b.split()) for _, b in M.ABSTRACT)
checks += 1
if not 150 <= abstract_words <= 240:
    fails.append(f"abstract is {abstract_words} words; target 150-240 (journal ceiling 250)")
body_words = sum(len(t.split()) for t in (
    M.INTRODUCTION + [t for _, ps in M.METHODS for t in ps]
    + [t for _, ps in M.RESULTS for t in ps] + M.DISCUSSION))
checks += 1
if body_words > 4400:
    fails.append(f"main text is {body_words} words; target <=4400 (journal ceiling ~4500)")
# The primary analysis must be tabulated in the supplement, not only described in prose.
checks += 1
try:
    import json as _json
    _T = _json.load(open(os.path.join(OUT, "tables.json"), encoding="utf-8"))
    if "etable_within" not in _T:
        fails.append("eTable 12 (within-episode primary analysis) missing from tables.json")
    else:
        _flat = " ".join(" ".join(map(str, r)) for r in _T["etable_within"]["rows"])
        for _need in ["487", "102", "237", "96", "52", "1,227", "252", "233", "0.86"]:
            if _need not in _flat:
                fails.append(f"eTable 12 does not report {_need}")
except FileNotFoundError:
    fails.append("tables.json not found; run 40_supplement_tables.py first")
checks += 1
n_kw = len([k for k in M.KEYWORDS.split(";") if k.strip()])
if not 4 <= n_kw <= 6:
    fails.append(f"{n_kw} keywords; journal requires 4-6")
# Springer figure captions do not end in a full stop.
checks += 1
for tag, body in M.FIGURE_LEGENDS:
    if body.rstrip().endswith("."):
        fails.append(f"{tag} caption ends with a full stop; Springer convention omits it")
# CLSI M39 is invoked in Methods and must be in the bibliography.
checks += 1
if not any("M39" in r for r in M.REFERENCES):
    fails.append("CLSI M39 is cited in Methods but absent from the reference list")
claim("document M39 [16]")


# ---- data governance: no row-level extract of the credentialed source data may be written
checks += 1
_forbidden = [f for f in os.listdir(OUT)
              if f.lower().endswith((".csv", ".parquet", ".dta", ".xlsx"))]
if _forbidden:
    fails.append(f"row-level or tabular data written to the output root: {_forbidden}. "
                 "MIMIC-IV may be redistributed only through PhysioNet.")
checks += 1
for _banned_word in ["validation_sample", "audit sample of classified specimens"]:
    if _banned_word.lower() in FULL.lower():
        fails.append(f"manuscript references a published row-level sample: {_banned_word!r}")

print(f"{checks} checks run")
if fails:
    print(f"\n{len(fails)} FAILURES:")
    for f in fails:
        print("  -", f)
    raise SystemExit(1)
print("ALL CONSISTENT: manuscript numbers match results_digest.json / stats_digest.json")
