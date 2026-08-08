"""
Primary analysis. Writes results_digest.json and stats_digest.json.

Inference conventions
---------------------
Specimens are clustered within episodes and episodes within patients, so every interval and every
test in this script accounts for that clustering:

  * proportions carry a patient-clustered bootstrap percentile interval (resampling patients, not
    specimens or isolates), alongside the naive exact interval for reference only;
  * group comparisons use a logistic model with patient-clustered robust standard errors rather
    than a specimen-level chi-square test;
  * organism-spectrum and resistance analyses are computed on first isolates, at episode level
    (primary) and patient level (sensitivity), following CLSI M39 first-isolate principles.

The strict anatomical tier is the primary cohort throughout. Generic-tier and pooled results are
reported alongside as prespecified sensitivity analyses, never as the headline.
"""
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))

from paths import OUT, INT

SEED = 20260808
N_BOOT = 2000
rng = np.random.default_rng(SEED)


def p(*a):
    print(*a, flush=True)


spec = pd.read_parquet(os.path.join(INT, "specimens.parquet"))
org = pd.read_parquet(os.path.join(INT, "organisms.parquet"))
sus = pd.read_parquet(os.path.join(INT, "susceptibilities.parquet"))
ep = pd.read_parquet(os.path.join(INT, "episodes.parquet"))

D = {}   # results digest
S = {}   # stats digest


# ------------------------------------------------------------------ helpers
def exact_ci(k, n):
    if n == 0:
        return (float("nan"), float("nan"))
    lo, hi = stats.beta.ppf(0.025, k, n - k + 1), stats.beta.ppf(0.975, k + 1, n - k)
    return (0.0 if k == 0 else float(lo), 1.0 if k == n else float(hi))


def cluster_boot_ci(df, value_col, cluster_col="subject_id", n_boot=N_BOOT, stat=np.mean):
    """
    Percentile bootstrap resampling whole clusters (patients).

    The generator is seeded from the data itself rather than drawn from a shared stream, so the
    same subset of specimens always yields the same interval no matter where in the script it is
    computed. Without this, a quantity reported in two places (for example oxacillin resistance,
    which appears both in the resistance panel and in the methicillin-resistance summary) would
    differ in the last decimal between the text and the tables.
    """
    if len(df) == 0:
        return (float("nan"), float("nan"))
    groups = [g[value_col].to_numpy() for _, g in df.groupby(cluster_col, sort=False)]
    if len(groups) < 2:
        return (float("nan"), float("nan"))
    sizes = tuple(len(g) for g in groups)
    totals = tuple(int(g.sum()) for g in groups)
    # hashlib rather than the built-in hash(), whose string hashing is randomised per process.
    key = repr((SEED, value_col, cluster_col, sizes, totals)).encode()
    local = np.random.default_rng(
        int.from_bytes(hashlib.blake2b(key, digest_size=8).digest(), "big"))
    idx = np.arange(len(groups))
    out = np.empty(n_boot)
    for b in range(n_boot):
        pick = local.choice(idx, size=len(idx), replace=True)
        out[b] = stat(np.concatenate([groups[i] for i in pick]))
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def prop_block(df, col, cluster_col="subject_id", label=""):
    """
    Proportion with naive exact and patient-clustered bootstrap intervals.

    Zero-event denominators are handled separately. A bootstrap that resamples patients from a
    sample containing no events returns [0, 0], which would assert that the population risk is
    zero. For k = 0 the block instead carries a one-sided 97.5% upper bound computed on the number
    of independent patients rather than the number of isolates, which is the conservative unit
    when isolates are clustered within patients.
    """
    n = int(len(df))
    k = int(df[col].sum())
    est = k / n if n else float("nan")
    e_lo, e_hi = exact_ci(k, n)
    n_clusters = int(df[cluster_col].nunique()) if n else 0
    blk = dict(label=label, k=k, n=n, est=est,
               exact_ci=[e_lo, e_hi], n_clusters=n_clusters)
    if n and k == 0:
        # Exact one-sided upper bound on patients: 1 - alpha^(1/m), the clustered analogue of the
        # rule of three. Reported as an upper bound, never as a point estimate of zero risk.
        blk["clustered_ci"] = [0.0, float(1 - 0.025 ** (1 / n_clusters)) if n_clusters else
                               float("nan")]
        blk["zero_event"] = True
        blk["upper_bound_basis"] = (f"exact one-sided 97.5% upper bound on {n_clusters} patients")
    else:
        blk["clustered_ci"] = list(cluster_boot_ci(df, col, cluster_col))
        blk["zero_event"] = False
    return blk


def fmt(b):
    if not b["n"]:
        return f"{b['label']}: no data"
    return (f"{b['label']}: {b['est']:.1%} ({b['k']:,}/{b['n']:,}); "
            f"patient-clustered 95% CI {b['clustered_ci'][0]:.1%}-{b['clustered_ci'][1]:.1%}")


def clustered_logit(df, outcome, terms, cluster_col="subject_id"):
    """Logistic regression with cluster-robust (patient) standard errors."""
    d = df.dropna(subset=[outcome] + terms + [cluster_col]).copy()
    X = pd.get_dummies(d[terms], drop_first=True, dtype=float)
    X = sm.add_constant(X, has_constant="add")
    y = d[outcome].astype(float)
    r = sm.Logit(y, X).fit(disp=0, maxiter=200, cov_type="cluster",
                           cov_kwds={"groups": d[cluster_col].to_numpy()})
    res = {}
    for name, coef, se, pv in zip(X.columns, r.params, r.bse, r.pvalues):
        if name == "const":
            continue
        col = X[name]
        res[name] = dict(or_=float(np.exp(coef)),
                         ci=[float(np.exp(coef - 1.96 * se)), float(np.exp(coef + 1.96 * se))],
                         p=float(pv),
                         n_in_level=int((col > 0).sum()) if set(col.unique()) <= {0.0, 1.0}
                         else int(len(col)),
                         events_in_level=int(y[(col > 0)].sum()) if set(col.unique()) <= {0.0, 1.0}
                         else int(y.sum()))
    # Reference level of every categorical term, so the table is readable without the source data.
    refs = {}
    for t in terms:
        if str(d[t].dtype) in ("object", "category") or d[t].dtype == bool:
            levels = (list(d[t].cat.categories) if str(d[t].dtype) == "category"
                      else sorted(map(str, d[t].dropna().unique())))
            if levels:
                refs[t] = str(levels[0])
    return dict(coefficients=res, reference_levels=refs, n=int(len(d)),
                n_clusters=int(d[cluster_col].nunique()), n_events=int(y.sum())), \
        int(len(d)), int(d[cluster_col].nunique())


def bh(pvals):
    """Benjamini-Hochberg adjusted p-values."""
    pv = np.asarray(pvals, dtype=float)
    n = len(pv)
    if n == 0:
        return pv
    order = np.argsort(pv)
    adj = np.empty(n)
    prev = 1.0
    for rank, i in enumerate(order[::-1]):
        r = n - rank
        prev = min(prev, pv[i] * n / r)
        adj[i] = prev
    return adj


# ------------------------------------------------------------------ cohort
p("=" * 90)
p("COHORT")
p("=" * 90)
D["cohort"] = dict(
    n_episodes=int(len(ep)),
    n_patients=int(ep.subject_id.nunique()),
    by_infection_type=ep.infection_type.value_counts().to_dict(),
    n_with_strict=int(ep.has_strict_specimen.sum()),
    n_with_generic=int(ep.has_generic_specimen.sum()),
    n_with_any_deep=int(ep.has_deep_specimen.sum()),
    icu_linked=int(ep.icu_linked.sum()),
    icu_linked_frac=float(ep.icu_linked.mean()),
    anchor_year_group=ep.anchor_year_group.value_counts().sort_index().to_dict(),
)
strict_eps = ep[ep.has_strict_specimen]
D["cohort"]["strict_cohort"] = dict(
    n_episodes=int(len(strict_eps)),
    n_patients=int(strict_eps.subject_id.nunique()),
    by_infection_type=strict_eps.infection_type.value_counts().to_dict(),
)
p(f"episodes={len(ep):,} patients={ep.subject_id.nunique():,}")
p(f"strict-tier cohort: {len(strict_eps):,} episodes, "
  f"{strict_eps.subject_id.nunique():,} patients")
p(f"ICU-linked: {ep.icu_linked.mean():.1%}")

# ------------------------------------------------------------------ specimen accounting
p("\n" + "=" * 90)
p("SPECIMEN ACCOUNTING (reviewer item 2: what enters the no-growth denominator)")
p("=" * 90)
acct = {}
for name, sel in [("strict", spec.is_deep_strict), ("generic", spec.is_deep_generic),
                  ("pooled", spec.is_deep_msk)]:
    d = spec[sel & spec.has_bacterial_culture]
    acct[name] = dict(
        n_bacterial_culture=int(len(d)),
        positive=int((d.result_status == "positive").sum()),
        negative=int((d.result_status == "negative").sum()),
        cancelled=int((d.result_status == "cancelled").sum()),
        indeterminate=int((d.result_status == "indeterminate").sum()),
        n_evaluable=int(d.evaluable.sum()),
        excluded_frac=float(1 - d.evaluable.mean()) if len(d) else float("nan"),
    )
    p(f"{name:8s} bact-culture={len(d):5,} positive={acct[name]['positive']:5,} "
      f"negative={acct[name]['negative']:5,} cancelled={acct[name]['cancelled']:3,} "
      f"indeterminate={acct[name]['indeterminate']:3,} "
      f"-> excluded {acct[name]['excluded_frac']:.2%}")
D["specimen_accounting"] = acct

# ------------------------------------------------------------------ no-growth
p("\n" + "=" * 90)
p("NO-GROWTH (primary = strict tier)")
p("=" * 90)
ng = {}
for name, sel in [("strict", spec.is_deep_strict), ("generic", spec.is_deep_generic),
                  ("pooled", spec.is_deep_msk)]:
    d = spec[sel & spec.evaluable]
    blk = prop_block(d, "culture_negative", label=f"no-growth ({name})")
    ng[name] = blk
    p("  " + fmt(blk))

# by source category, within strict
ng["strict_by_source"] = {}
for cat, d in spec[spec.is_deep_strict & spec.evaluable].groupby("source_category"):
    blk = prop_block(d, "culture_negative", label=f"no-growth [{cat}]")
    ng["strict_by_source"][cat] = blk
    p("    " + fmt(blk))

# by infection type, within strict
sp_ep = spec.merge(ep[["hadm_id", "infection_type", "anchor_year_group", "icu_linked"]],
                   on="hadm_id", how="left")
ng["strict_by_infection_type"] = {}
for it, d in sp_ep[sp_ep.is_deep_strict & sp_ep.evaluable].groupby("infection_type"):
    blk = prop_block(d, "culture_negative", label=f"no-growth [{it}]")
    ng["strict_by_infection_type"][it] = blk
    p("    " + fmt(blk))

# episode-level all-negative
ng["episode_all_negative_strict"] = prop_block(
    strict_eps[strict_eps.strict_n_evaluable > 0], "strict_all_negative",
    label="episode all-negative (strict)")
p("  " + fmt(ng["episode_all_negative_strict"]))
D["no_growth"] = ng

# ------------------------------------------------------------------ within-episode paired tiers
p("\n" + "=" * 90)
p("WITHIN-EPISODE COMPARISON OF TIERS")
p("=" * 90)
p("Between-cohort differences are confounded by infection type, sampling indication and case "
  "selection, because the two tiers describe different patients. Restricting to episodes that "
  "contributed BOTH tiers holds the patient and admission fixed.")
p("A tier is counted negative for an episode only when EVERY evaluable specimen in that tier grew "
  "nothing. Calling a tier negative whenever it contains any negative specimen is not an "
  "episode-level definition and is mechanically biased by sampling intensity: the tier with more "
  "specimens per episode gets more opportunities to contain at least one negative.")

both = ep[(ep.strict_n_evaluable > 0) & (ep.generic_n_evaluable > 0)].copy()
p(f"episodes contributing both tiers: {len(both):,} "
  f"({both.subject_id.nunique():,} patients)")
p(f"  specimens per episode, median: source-specific {both.strict_n_evaluable.median():.0f}, "
  f"generic {both.generic_n_evaluable.median():.0f}")

wi = dict(n_episodes=int(len(both)), n_patients=int(both.subject_id.nunique()),
          by_infection_type=both.infection_type.value_counts().to_dict(),
          median_specimens=dict(strict=float(both.strict_n_evaluable.median()),
                                generic=float(both.generic_n_evaluable.median())))

if len(both) >= 20:
    paired = spec[spec.hadm_id.isin(set(both.hadm_id)) & spec.evaluable
                  & (spec.is_deep_strict | spec.is_deep_generic)].copy()
    paired["tier_strict"] = paired.is_deep_strict.astype(int)

    # Specimen-level fractions inside the paired episodes. These pool specimens across episodes
    # and so do NOT hold the episode fixed; they are descriptive context for the paired analysis
    # below, not the comparison itself.
    for name, sel in [("strict", paired.is_deep_strict), ("generic", paired.is_deep_generic)]:
        wi[f"specimen_level_{name}"] = prop_block(
            paired[sel], "culture_negative", label=f"specimen-level no growth, {name}")
        p("  " + fmt(wi[f"specimen_level_{name}"]))

    # ---- episode-level paired table, all-negative definition
    both["strict_all_neg"] = (both.strict_n_positive == 0)
    both["generic_all_neg"] = (both.generic_n_positive == 0)
    both_neg = int((both.strict_all_neg & both.generic_all_neg).sum())
    both_pos = int((~both.strict_all_neg & ~both.generic_all_neg).sum())
    strict_only = int((both.strict_all_neg & ~both.generic_all_neg).sum())
    generic_only = int((~both.strict_all_neg & both.generic_all_neg).sum())
    disc = strict_only + generic_only
    wi["paired_table"] = dict(
        both_all_negative=both_neg, both_had_a_positive=both_pos,
        strict_all_negative_only=strict_only, generic_all_negative_only=generic_only,
        n_episodes=int(len(both)),
        strict_all_negative_total=int(both.strict_all_neg.sum()),
        generic_all_negative_total=int(both.generic_all_neg.sum()),
        definition="a tier is negative for an episode only if all its evaluable specimens "
                   "grew nothing")
    p(f"  paired episodes n={len(both):,} (all-negative definition): both all-negative "
      f"{both_neg:,}, both had a positive {both_pos:,}, source-specific-only all-negative "
      f"{strict_only:,}, generic-only all-negative {generic_only:,}")
    p(f"  tier all-negative overall: source-specific {int(both.strict_all_neg.sum()):,}"
      f"/{len(both):,} ({both.strict_all_neg.mean():.1%}), generic "
      f"{int(both.generic_all_neg.sum()):,}/{len(both):,} ({both.generic_all_neg.mean():.1%})")

    if disc > 0:
        # Naive exact McNemar, reported for reference only. It assumes independent pairs, which
        # does not hold here: the episodes come from fewer patients than there are episodes.
        pv_naive = float(stats.binomtest(strict_only, disc, 0.5).pvalue)

        # Patient-clustered paired inference: bootstrap the difference in the two paired
        # proportions by resampling PATIENTS, so episodes from one patient move together.
        d_obs = float(both.strict_all_neg.mean() - both.generic_all_neg.mean())
        groups = [g for _, g in both.groupby("subject_id", sort=False)]
        idx = np.arange(len(groups))
        key = repr((SEED, "paired_tier_diff", len(groups), int(both.strict_all_neg.sum()),
                    int(both.generic_all_neg.sum()))).encode()
        local = np.random.default_rng(
            int.from_bytes(hashlib.blake2b(key, digest_size=8).digest(), "big"))
        boot = np.empty(N_BOOT)
        for b in range(N_BOOT):
            pick = local.choice(idx, size=len(idx), replace=True)
            s = pd.concat([groups[i] for i in pick])
            boot[b] = s.strict_all_neg.mean() - s.generic_all_neg.mean()
        lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
        # Two-sided bootstrap P for H0: difference = 0.
        pv_clust = float(2 * min((boot <= 0).mean(), (boot >= 0).mean()))
        pv_clust = min(1.0, max(pv_clust, 1.0 / N_BOOT))

        wi["paired_test"] = dict(
            discordant=int(disc), strict_only=strict_only, generic_only=generic_only,
            mcnemar_naive_p=pv_naive,
            diff=d_obs, diff_ci=[lo, hi], patient_clustered_p=pv_clust,
            note="naive McNemar assumes independent pairs and is reported for reference only; "
                 "inference uses a patient-clustered bootstrap of the paired difference")
        p(f"  naive exact McNemar on {disc:,} discordant pairs: P = {pv_naive:.4g} "
          f"(reference only, assumes independent pairs)")
        p(f"  paired difference (source-specific minus generic, all-negative): "
          f"{d_obs:+.1%} (patient-clustered 95% CI {lo:+.1%} to {hi:+.1%}); "
          f"bootstrap P = {pv_clust:.4g}")

    # ---- 1:1 matched subset
    # Even the all-negative definition is sensitive to how many specimens each tier contributes
    # (an episode with one specimen is more easily "all negative" than one with three). The
    # cleanest paired comparison restricts to episodes contributing exactly one evaluable
    # specimen in EACH tier, where the two tiers are matched one-to-one by construction.
    m11 = both[(both.strict_n_evaluable == 1) & (both.generic_n_evaluable == 1)]
    wi["matched_1to1"] = dict(n_episodes=int(len(m11)),
                              n_patients=int(m11.subject_id.nunique()) if len(m11) else 0)
    if len(m11) >= 20:
        a = int((m11.strict_all_neg & m11.generic_all_neg).sum())
        b_ = int((m11.strict_all_neg & ~m11.generic_all_neg).sum())
        c_ = int((~m11.strict_all_neg & m11.generic_all_neg).sum())
        d_ = int((~m11.strict_all_neg & ~m11.generic_all_neg).sum())
        dsc = b_ + c_
        wi["matched_1to1"].update(
            both_negative=a, strict_negative_only=b_, generic_negative_only=c_,
            both_positive=d_, discordant=int(dsc),
            strict_negative=int(m11.strict_all_neg.sum()),
            generic_negative=int(m11.generic_all_neg.sum()))
        p(f"  1:1 matched subset n={len(m11):,} episodes ({m11.subject_id.nunique():,} "
          f"patients): both negative {a:,}, source-only {b_:,}, generic-only {c_:,}, "
          f"both positive {d_:,}")
        if dsc > 0:
            pv11 = float(stats.binomtest(b_, dsc, 0.5).pvalue)
            wi["matched_1to1"]["mcnemar_naive_p"] = pv11
            p(f"    naive exact McNemar: P = {pv11:.4g} (reference only)")

    # ---- episode-stratified conditional logistic regression
    # This is the model that actually uses only within-episode variation: episodes are strata, so
    # any episode-level characteristic is conditioned out. Episodes in which every specimen has
    # the same outcome contribute no information and are dropped by the conditional likelihood.
    try:
        from statsmodels.discrete.conditional_models import ConditionalLogit

        def _fit_clogit(df):
            return ConditionalLogit(df.culture_negative.astype(float),
                                    df[["tier_strict"]].astype(float),
                                    groups=df.hadm_id.to_numpy()).fit(disp=0)

        # Only episodes whose specimens differ in outcome AND in tier contribute to the
        # conditional likelihood; the rest are dropped. Report the retained sample, not the
        # input sample, because the retained one is what the estimate is based on.
        gv = paired.groupby("hadm_id").agg(y_var=("culture_negative", "nunique"),
                                           x_var=("tier_strict", "nunique"))
        informative = set(gv.index[(gv.y_var > 1) & (gv.x_var > 1)])
        inf_rows = paired[paired.hadm_id.isin(informative)]
        pats = inf_rows.subject_id.nunique()
        multi = int((inf_rows.groupby("subject_id").hadm_id.nunique() > 1).sum())

        cm = _fit_clogit(paired)
        coef = float(cm.params.iloc[0])
        se_model = float(cm.bse.iloc[0])

        # Patient-clustered uncertainty. The conditional likelihood treats episodes as
        # independent strata, but episodes are nested in patients, so model-based standard
        # errors understate uncertainty. Resample PATIENTS and refit.
        pat_groups = [g for _, g in paired.groupby("subject_id", sort=False)]
        key = repr((SEED, "clogit_cluster", len(pat_groups), int(len(paired)))).encode()
        rng_c = np.random.default_rng(
            int.from_bytes(hashlib.blake2b(key, digest_size=8).digest(), "big"))
        idx = np.arange(len(pat_groups))
        N_CB = 1000
        boots = []
        for b in range(N_CB):
            pick = rng_c.choice(idx, size=len(idx), replace=True)
            # Re-key episodes so the same episode drawn twice forms two distinct strata.
            parts = []
            for j, i in enumerate(pick):
                gg = pat_groups[i].copy()
                gg["hadm_id"] = gg.hadm_id.astype(str) + f"_{j}"
                parts.append(gg)
            samp = pd.concat(parts, ignore_index=True)
            try:
                boots.append(float(_fit_clogit(samp).params.iloc[0]))
            except Exception:                                  # noqa: BLE001, S112
                continue
        boots = np.asarray(boots, dtype=float)
        boots = boots[np.isfinite(boots)]
        lo_c, hi_c = (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
                      if len(boots) > 50 else (float("nan"), float("nan")))
        se_c = float(np.std(boots, ddof=1)) if len(boots) > 50 else float("nan")
        z = coef / se_c if se_c and np.isfinite(se_c) and se_c > 0 else float("nan")
        p_c = float(2 * stats.norm.sf(abs(z))) if np.isfinite(z) else float("nan")

        wi["conditional_logit"] = dict(
            or_=float(np.exp(coef)),
            ci=[float(np.exp(lo_c)), float(np.exp(hi_c))],
            p=p_c,
            ci_model_based=[float(np.exp(coef - 1.96 * se_model)),
                            float(np.exp(coef + 1.96 * se_model))],
            p_model_based=float(cm.pvalues.iloc[0]),
            n_specimens_input=int(len(paired)), n_strata_input=int(paired.hadm_id.nunique()),
            n_specimens_retained=int(len(inf_rows)), n_strata_retained=int(len(informative)),
            n_patients_retained=int(pats), n_patients_multi_episode=multi,
            n_bootstrap=int(len(boots)),
            note="episodes are strata; episode-level characteristics are conditioned out. "
                 "Uncertainty is patient-clustered by resampling patients and refitting, "
                 "because episodes are nested within patients. Model-based (unclustered) "
                 "interval reported alongside for reference.")
        b = wi["conditional_logit"]
        p(f"  episode-stratified conditional logistic (patient-clustered): OR {b['or_']:.2f} "
          f"({b['ci'][0]:.2f}-{b['ci'][1]:.2f}), P = {b['p']:.3g}")
        p(f"    model-based (unclustered) interval for reference: "
          f"{b['ci_model_based'][0]:.2f}-{b['ci_model_based'][1]:.2f}, "
          f"P = {b['p_model_based']:.3g}")
        p(f"    retained sample: {b['n_specimens_retained']:,} specimens in "
          f"{b['n_strata_retained']:,} informative episodes from {b['n_patients_retained']:,} "
          f"patients ({b['n_patients_multi_episode']:,} contributing >1 informative episode); "
          f"input was {b['n_specimens_input']:,} specimens in {b['n_strata_input']:,} episodes")
    except Exception as e:                                     # noqa: BLE001
        wi["conditional_logit"] = dict(error=str(e))
        p(f"  conditional logistic model failed ({e})")

    # Patient-clustered specimen-level model, reported as a sensitivity analysis. It does NOT
    # hold the episode fixed and is not the primary within-episode estimate.
    try:
        res, n, nc = clustered_logit(paired, "culture_negative", ["tier_strict"])
        wi["clustered_logit_sensitivity"] = res
        c = res["coefficients"]["tier_strict"]
        p(f"  patient-clustered specimen-level (sensitivity, episode NOT fixed): "
          f"OR {c['or_']:.2f} ({c['ci'][0]:.2f}-{c['ci'][1]:.2f}), P = {c['p']:.4g}")
    except Exception as e:                                     # noqa: BLE001
        wi["clustered_logit_sensitivity"] = dict(error=str(e))
else:
    p("  too few episodes contribute both tiers for a paired analysis")
D["within_episode"] = wi

# ------------------------------------------------------------------ sampling-intensity gradient
p("\n" + "=" * 90)
p("SAMPLING INTENSITY GRADIENT (descriptive; strict tier)")
p("=" * 90)
sd = sp_ep[sp_ep.is_deep_strict & sp_ep.evaluable].merge(
    ep[["hadm_id", "strict_n_evaluable"]], on="hadm_id", how="left")
bins = [(1, 1), (2, 2), (3, 3), (4, 6), (7, 999)]
grad = {}
for lo, hi in bins:
    d = sd[(sd.strict_n_evaluable >= lo) & (sd.strict_n_evaluable <= hi)]
    lab = f"{lo}" if lo == hi else (f"{lo}-{hi}" if hi < 999 else f"{lo}+")
    if len(d):
        grad[lab] = prop_block(d, "culture_negative", label=f"no-growth [{lab} specimens]")
        p("  " + fmt(grad[lab]))
D["sampling_gradient_strict"] = grad

# ------------------------------------------------------------------ organism spectrum
p("\n" + "=" * 90)
p("ORGANISM SPECTRUM (first isolates)")
p("=" * 90)
# Deduplication flags are scoped to the tier being analysed, so "first isolate per episode within
# the strict tier" means first among strict specimens, not first anywhere in the admission.
spectrum = {}
for tier_name, tier_sel in [("strict", org.is_deep_strict), ("pooled", org.is_deep_msk)]:
    for rule, rule_sel in [("all_isolates", pd.Series(True, index=org.index)),
                           ("first_isolate_episode", org[f"first_isolate_episode_{tier_name}"]),
                           ("first_isolate_patient", org[f"first_isolate_patient_{tier_name}"])]:
        d = org[tier_sel & rule_sel & org.is_species]
        if not len(d):
            continue
        vc = d.genus_group.value_counts()
        spectrum[f"{tier_name}|{rule}"] = dict(
            n_isolates=int(len(d)),
            top=vc.head(15).to_dict(),
            top_frac={k: float(v / len(d)) for k, v in vc.head(15).items()},
        )
p("strict tier, by deduplication rule (top 8):")
for rule in ["all_isolates", "first_isolate_episode", "first_isolate_patient"]:
    key = f"strict|{rule}"
    if key in spectrum:
        b = spectrum[key]
        top = list(b["top_frac"].items())[:8]
        p(f"  {rule:24s} n={b['n_isolates']:5,}  " +
          ", ".join(f"{k} {v:.1%}" for k, v in top))
D["spectrum"] = spectrum

# S. aureus share with clustered CI, strict tier, episode-first isolates
sa_d = org[org.is_deep_strict & org.first_isolate_episode_strict & org.is_species].copy()
sa_d["is_sa"] = sa_d.is_saureus
D["saureus_share_strict_epfirst"] = prop_block(sa_d, "is_sa", label="S. aureus share (strict, episode-first)")
p("  " + fmt(D["saureus_share_strict_epfirst"]))

# ------------------------------------------------------------------ polymicrobial (both rules)
p("\n" + "=" * 90)
p("POLYMICROBIAL (reviewer item 4: raw vs normalized organism identity)")
p("=" * 90)
p("Speciated-only rules exclude low-resolution growth, so a specimen reported as mixed bacterial "
  "flora contributes no organisms and is scored monomicrobial. Three prespecified rules are "
  "reported: speciated distinct laboratory strings, speciated normalized identities, and "
  "speciated strings with an explicit report of mixed flora also counted as polymicrobial.")
poly = {}
for tier, pos_col in [("strict", "strict_n_positive"), ("pooled", "pooled_n_positive")]:
    d = ep[ep[pos_col] > 0]
    for rule, col in [("raw", f"{tier}_polymicrobial_raw"),
                      ("norm", f"{tier}_polymicrobial_norm"),
                      ("incl_mixed", f"{tier}_polymicrobial_incl_mixed")]:
        poly[f"{tier}_{rule}"] = prop_block(d, col, label=f"polymicrobial ({tier}, {rule})")
        p("  " + fmt(poly[f"{tier}_{rule}"]))
    poly[f"{tier}_mixed_flora"] = prop_block(d, f"{tier}_mixed_flora",
                                             label=f"mixed flora reported ({tier})")
    p("  " + fmt(poly[f"{tier}_mixed_flora"]))
D["polymicrobial"] = poly

# ------------------------------------------------------------------ resistance
p("\n" + "=" * 90)
p("ANTIMICROBIAL RESISTANCE (first isolates, patient-clustered intervals)")
p("=" * 90)
sus = sus[sus.interpretation.isin(["S", "I", "R"])].copy()
sus["resistant"] = (sus.interpretation == "R").astype(int)

SA_PANEL = ["OXACILLIN", "VANCOMYCIN", "ERYTHROMYCIN", "CLINDAMYCIN", "LEVOFLOXACIN",
            "GENTAMICIN", "TETRACYCLINE", "TRIMETHOPRIM/SULFA", "RIFAMPIN"]
GN_PANEL = ["CEFTRIAXONE", "CEFEPIME", "CIPROFLOXACIN", "GENTAMICIN", "TOBRAMYCIN",
            "MEROPENEM", "PIPERACILLIN/TAZO", "TRIMETHOPRIM/SULFA"]


def amr_panel(df, agents, label):
    out = {}
    for ab in agents:
        d = df[df.ab_name.str.upper().str.contains(ab.split("/")[0], na=False)]
        if len(d) < 10:
            out[ab] = dict(label=ab, n=int(len(d)), est=None,
                           note="denominator below reporting threshold (n<10)")
            continue
        blk = prop_block(d, "resistant", label=f"{label} {ab}")
        out[ab] = blk
    return out


amr = {}
for tier_name, tier_sel in [("strict", sus.is_deep_strict), ("pooled", sus.is_deep_msk)]:
    for rule, rule_sel in [("all_isolates", pd.Series(True, index=sus.index)),
                           ("first_isolate_episode", sus[f"first_isolate_episode_{tier_name}"].fillna(False)),
                           ("first_isolate_patient", sus[f"first_isolate_patient_{tier_name}"].fillna(False))]:
        base = sus[tier_sel & rule_sel]
        amr[f"{tier_name}|{rule}|saureus"] = amr_panel(
            base[base.is_saureus], SA_PANEL, f"[{tier_name}/{rule}] S. aureus")
        gn = base[base.broad_group == "Gram-negative"]
        amr[f"{tier_name}|{rule}|gramneg"] = amr_panel(
            gn, GN_PANEL, f"[{tier_name}/{rule}] gram-negative")
D["amr"] = amr

for key in ["strict|first_isolate_episode|saureus", "pooled|first_isolate_episode|saureus",
            "pooled|all_isolates|saureus"]:
    p(f"\n{key}")
    for ab, b in D["amr"][key].items():
        if b.get("est") is None:
            p(f"  {ab:20s} n={b['n']:<5,} {b.get('note','')}")
        else:
            p(f"  {ab:20s} " + fmt(b).split(": ", 1)[1])

# MRSA fraction, primary reporting unit
p("\nMRSA (oxacillin-resistant S. aureus):")
mrsa = {}
for tier_name, tier_sel in [("strict", sus.is_deep_strict), ("pooled", sus.is_deep_msk)]:
    for rule, rule_sel in [("all_isolates", pd.Series(True, index=sus.index)),
                           ("first_isolate_episode", sus[f"first_isolate_episode_{tier_name}"].fillna(False)),
                           ("first_isolate_patient", sus[f"first_isolate_patient_{tier_name}"].fillna(False))]:
        d = sus[tier_sel & rule_sel & sus.is_saureus
                & sus.ab_name.str.upper().str.contains("OXACILLIN", na=False)]
        if len(d) >= 10:
            blk = prop_block(d, "resistant", label=f"MRSA [{tier_name}/{rule}]")
            mrsa[f"{tier_name}|{rule}"] = blk
            p("  " + fmt(blk))
D["mrsa"] = mrsa

# ------------------------------------------------------------------ era stratification
p("\n" + "=" * 90)
p("ERA STRATIFICATION (anchor_year_group; reviewer item 7)")
p("=" * 90)
p("MIMIC-IV chartdates are per-patient date-shifted and carry no calendar meaning; "
  "anchor_year_group is the only admissible era marker.")
sus_ep = sus.merge(ep[["hadm_id", "anchor_year_group", "icu_linked", "infection_type"]],
                   on="hadm_id", how="left")
era = {}
ox = sus_ep[sus_ep.is_deep_msk & sus_ep.first_isolate_episode_pooled.fillna(False) & sus_ep.is_saureus
            & sus_ep.ab_name.str.upper().str.contains("OXACILLIN", na=False)]
for g, d in ox.groupby("anchor_year_group"):
    if len(d) >= 10:
        era[str(g)] = prop_block(d, "resistant", label=f"MRSA [{g}]")
        p("  " + fmt(era[str(g)]))
if len(era) >= 2:
    tab = [[int(d.resistant.sum()), int(len(d) - d.resistant.sum())]
           for _, d in ox.groupby("anchor_year_group") if len(d) >= 10]
    chi2, pv, dof, _ = stats.chi2_contingency(np.array(tab))
    era["trend_test"] = dict(note="unclustered omnibus, descriptive only",
                             chi2=float(chi2), p=float(pv), dof=int(dof))
    p(f"  omnibus across eras (descriptive): P = {pv:.3f}")
D["era_mrsa"] = era

# no-growth by era
era_ng = {}
for g, d in sp_ep[sp_ep.is_deep_strict & sp_ep.evaluable].groupby("anchor_year_group"):
    if len(d) >= 20:
        era_ng[str(g)] = prop_block(d, "culture_negative", label=f"no-growth [{g}]")
        p("  " + fmt(era_ng[str(g)]))
D["era_no_growth_strict"] = era_ng

# ------------------------------------------------------------------ ICU stratification
p("\n" + "=" * 90)
p("ICU STRATIFICATION (tests the 'intensive-care enrichment' explanation for high MRSA)")
p("=" * 90)
icu_mrsa = {}
for flag, d in ox.groupby("icu_linked"):
    if len(d) >= 10:
        k = "icu" if flag else "non_icu"
        icu_mrsa[k] = prop_block(d, "resistant", label=f"MRSA [{k}]")
        p("  " + fmt(icu_mrsa[k]))
if {"icu", "non_icu"} <= set(icu_mrsa):
    d = ox.dropna(subset=["icu_linked"]).copy()
    d["icu"] = d.icu_linked.astype(int)
    res, n, nc = clustered_logit(d, "resistant", ["icu"])
    icu_mrsa["clustered_logit"] = res
    p(f"  patient-clustered logit, ICU vs not: {res['coefficients']}")
D["icu_mrsa"] = icu_mrsa

# ------------------------------------------------------------------ variation models
p("\n" + "=" * 90)
p("VARIATION IN NO-GROWTH (patient-clustered logistic regression, strict tier)")
p("=" * 90)
mod = sp_ep[sp_ep.is_deep_strict & sp_ep.evaluable].merge(
    ep[["hadm_id", "gender", "anchor_age", "race", "insurance", "strict_n_evaluable"]],
    on="hadm_id", how="left").copy()
mod["age_band"] = pd.cut(mod.anchor_age, [0, 50, 65, 80, 200],
                         labels=["<50", "50-64", "65-79", "80+"])
mod["race_group"] = np.where(mod.race.str.upper().str.startswith("WHITE", na=False), "White",
                             np.where(mod.race.str.upper().str.startswith("BLACK", na=False),
                                      "Black", "Other/Unknown"))
mod["y"] = mod.culture_negative.astype(int)
mod["log_n_spec"] = np.log(mod.strict_n_evaluable.clip(lower=1))

# Prosthetic joint infection is the reference category for infection type, so that the
# prespecified osteomyelitis-versus-prosthetic-joint-infection contrast is read directly off the
# coefficient rather than being recovered from two coefficients against a third group.
mod["infection_type"] = pd.Categorical(
    mod.infection_type, categories=["PJI", "Osteomyelitis", "Device (other)"], ordered=False)

for name, terms in [
    ("unadjusted_for_sampling", ["infection_type", "age_band", "gender", "race_group", "insurance"]),
    ("adjusted_for_sampling", ["infection_type", "age_band", "gender", "race_group", "insurance",
                               "log_n_spec"]),
]:
    try:
        res, n, nc = clustered_logit(mod, "y", terms)
        coef = res["coefficients"]
        adj = bh([v["p"] for v in coef.values()])
        for (k, v), a in zip(coef.items(), adj):
            v["p_bh"] = float(a)
        res["terms"] = terms
        S[f"no_growth_{name}"] = res
        p(f"\n  {name} (n={n:,} specimens, {nc:,} patients, {res['n_events']:,} events; "
          f"reference levels {res['reference_levels']})")
        for k, v in coef.items():
            p(f"    {k:34s} OR {v['or_']:.2f} ({v['ci'][0]:.2f}-{v['ci'][1]:.2f})  "
              f"P={v['p']:.3f}  P_BH={v['p_bh']:.3f}")
    except Exception as e:                                     # noqa: BLE001
        p(f"  {name}: model failed ({e})")
        S[f"no_growth_{name}"] = dict(error=str(e))

# infection-type contrast on no-growth, clustered, prosthetic joint infection as reference
try:
    res, n, nc = clustered_logit(mod.copy(), "y", ["infection_type"])
    S["no_growth_infection_type_only"] = res
    p("\n  infection_type_only (reference = PJI)")
    for k, v in res["coefficients"].items():
        p(f"    {k:34s} OR {v['or_']:.2f} ({v['ci'][0]:.2f}-{v['ci'][1]:.2f})  P={v['p']:.3f}")
except Exception as e:                                         # noqa: BLE001
    S["no_growth_infection_type_only"] = dict(error=str(e))

# ------------------------------------------------------------------ diagnostic intensity
p("\n" + "=" * 90)
p("DIAGNOSTIC INTENSITY")
p("=" * 90)
di = {}
for it, d in strict_eps.groupby("infection_type"):
    di[it] = dict(n_episodes=int(len(d)),
                  median_strict=float(d.strict_n.median()),
                  iqr_strict=[float(d.strict_n.quantile(.25)), float(d.strict_n.quantile(.75))],
                  median_all_cultures=float(d.n_culture_specimens.median()))
    p(f"  {it:16s} n={len(d):5,} median strict specimens={d.strict_n.median():.0f} "
      f"(IQR {d.strict_n.quantile(.25):.0f}-{d.strict_n.quantile(.75):.0f})")
groups = [g.strict_n.to_numpy() for _, g in strict_eps.groupby("infection_type") if len(g) > 1]
if len(groups) >= 2:
    H, pv = stats.kruskal(*groups)
    n_tot = sum(len(g) for g in groups)
    di["kruskal"] = dict(H=float(H), p=float(pv),
                         epsilon_sq=float((H - len(groups) + 1) / (n_tot - len(groups))))
    p(f"  Kruskal-Wallis P = {pv:.4g}, epsilon-squared = {di['kruskal']['epsilon_sq']:.3f}")
D["diagnostic_intensity"] = di

# ------------------------------------------------------------------ validation sample
p("\n" + "=" * 90)
p("VALIDATION SAMPLE (reviewer item 2: auditable classification sample)")
p("=" * 90)
val = spec[spec.is_deep_msk & spec.has_bacterial_culture].copy()
samp = pd.concat([g.sample(min(len(g), 25), random_state=SEED)
                  for _, g in val.groupby("result_status")], ignore_index=True)
mic_comments = pd.read_parquet(os.path.join(INT, "micro_raw_cohort.parquet"),
                               columns=["micro_specimen_id", "test_name", "comments"])
samp_out = samp[["micro_specimen_id", "spec_type_desc", "tier", "result_status",
                 "orgname_list"]].merge(
    mic_comments.groupby("micro_specimen_id").comments.apply(
        lambda s: " || ".join(sorted({str(x)[:120] for x in s.dropna()}))[:400]),
    on="micro_specimen_id", how="left")
samp_out.to_csv(os.path.join(OUT, "validation_sample.csv"), index=False)
p(f"  wrote {len(samp_out)} sampled specimens to output/validation_sample.csv")
D["validation_sample_n"] = int(len(samp_out))

# ------------------------------------------------------------------ save
D["_meta"] = dict(seed=SEED, n_boot=N_BOOT,
                  pandas=pd.__version__, numpy=np.__version__,
                  statsmodels=sm.__version__, scipy=stats.__name__)
with open(os.path.join(OUT, "results_digest.json"), "w", encoding="utf-8") as f:
    json.dump(D, f, indent=2, default=str)
with open(os.path.join(OUT, "stats_digest.json"), "w", encoding="utf-8") as f:
    json.dump(S, f, indent=2, default=str)
p("\nwrote results_digest.json and stats_digest.json")
