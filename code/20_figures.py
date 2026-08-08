"""
Figures 1-3. All estimates carry patient-clustered 95% confidence intervals.

Fig 1  No growth: (a) by specimen label tier, (b) by specimen source within the source-specific
       tier, (c) by number of evaluable source-specific specimens per episode, (d) within the
       episodes that contributed both tiers.
Fig 2  Organism spectrum of source-specific deep musculoskeletal isolates, under three
       deduplication rules (all isolates, episode-first, patient-first).
Fig 3  Resistance: (a) S. aureus panel, (b) gram-negative panel, episode-first isolates;
       (c) oxacillin resistance by anchor-year group.

Figure numbers here match the legends in the manuscript. The panels are built in a different
order for layout reasons; the output filenames are what the journal receives.
"""
import json
import os
import sys

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from figure_kit import set_style, save, panel, faint_grid, BLUE, GREY, SALMON, OKABE

from paths import OUT, FIG

with open(os.path.join(OUT, "results_digest.json"), encoding="utf-8") as f:
    D = json.load(f)

set_style()


def err(blk):
    """Asymmetric error bar heights from a patient-clustered interval."""
    lo, hi = blk["clustered_ci"]
    e = blk["est"]
    if any(np.isnan([lo, hi])):
        return [[0.0], [0.0]]
    return [[max(0.0, e - lo)], [max(0.0, hi - e)]]


# Formal agent names for figures and tables. Informal laboratory contractions are not used in
# published output; the expansions are given in the figure legends.
AGENT_NAMES = {
    "OXACILLIN": "Oxacillin", "VANCOMYCIN": "Vancomycin", "ERYTHROMYCIN": "Erythromycin",
    "CLINDAMYCIN": "Clindamycin", "LEVOFLOXACIN": "Levofloxacin", "GENTAMICIN": "Gentamicin",
    "TETRACYCLINE": "Tetracycline", "RIFAMPIN": "Rifampin", "CEFTRIAXONE": "Ceftriaxone",
    "CEFEPIME": "Cefepime", "CIPROFLOXACIN": "Ciprofloxacin", "TOBRAMYCIN": "Tobramycin",
    "MEROPENEM": "Meropenem",
    "TRIMETHOPRIM/SULFA": "TMP–SMX",
    "PIPERACILLIN/TAZO": "Piperacillin–tazobactam",
}


def agent_label(key):
    return AGENT_NAMES.get(key, key.title())


def hbar(ax, blocks, labels, color=BLUE):
    y = np.arange(len(blocks))[::-1]
    est = [b["est"] * 100 for b in blocks]
    lo = [max(0, (b["est"] - b["clustered_ci"][0]) * 100) for b in blocks]
    hi = [max(0, (b["clustered_ci"][1] - b["est"]) * 100) for b in blocks]
    ax.barh(y, est, color=color, height=0.62, zorder=3)
    ax.errorbar(est, y, xerr=[lo, hi], fmt="none", ecolor="#2B2B2B", elinewidth=0.9,
                capsize=2.5, zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    faint_grid(ax, "x")
    return y


# ---------------------------------------------------------------- Fig 2: spectrum
rules = [("all_isolates", "All isolates"),
         ("first_isolate_episode", "First isolate per episode"),
         ("first_isolate_patient", "First isolate per patient")]
present = [(k, lab) for k, lab in rules if f"strict|{k}" in D["spectrum"]]
# organism order from the episode-first rule, which is the primary
base = D["spectrum"]["strict|first_isolate_episode"]["top_frac"]
orgs = [o for o, _ in sorted(base.items(), key=lambda kv: -kv[1])][:8]

fig, ax = plt.subplots(figsize=(6.85, 4.2))
w = 0.26
x = np.arange(len(orgs))
for i, (k, lab) in enumerate(present):
    b = D["spectrum"][f"strict|{k}"]
    vals = [b["top_frac"].get(o, 0.0) * 100 for o in orgs]
    ax.bar(x + (i - 1) * w, vals, width=w, label=f"{lab} (n = {b['n_isolates']:,})",
           color=[BLUE, SALMON, GREY][i], zorder=3)
ax.set_xticks(x)
ax.set_xticklabels([o.replace(" (Propionibacterium)", "") for o in orgs],
                   rotation=30, ha="right")
ax.set_ylabel("Share of speciated isolates (%)")
ax.legend(frameon=False, loc="upper right")
faint_grid(ax, "y")
save(fig, os.path.join(FIG, "Fig2"))
print("Fig2 (organism spectrum) written")

# ---------------------------------------------------------------- Fig 1: no-growth
# Built as a 2x2 at the journal's full text width (174 mm = 6.85 in) so that no reduction is
# applied in production and the 8-9 pt lettering survives at final size. A 1x4 strip at this
# width would shrink the type to roughly 4 pt.
fig, axg = plt.subplots(2, 2, figsize=(6.85, 6.4))
axes = axg.ravel()

# (a) by tier
tiers = [("strict", "Source-specific\n(joint fluid,\nsonicate)"),
         ("generic", "Generic\n(tissue, biopsy,\nforeign body)"),
         ("pooled", "Pooled")]
blocks = [D["no_growth"][k] for k, _ in tiers]
ax = axes[0]
xs = np.arange(len(blocks))
est = [b["est"] * 100 for b in blocks]
lo = [max(0, (b["est"] - b["clustered_ci"][0]) * 100) for b in blocks]
hi = [max(0, (b["clustered_ci"][1] - b["est"]) * 100) for b in blocks]
ax.bar(xs, est, color=[BLUE, GREY, SALMON], width=0.6, zorder=3)
ax.errorbar(xs, est, yerr=[lo, hi], fmt="none", ecolor="#2B2B2B", elinewidth=0.9,
            capsize=3, zorder=4)
ax.set_xticks(xs)
ax.set_xticklabels([lab for _, lab in tiers], fontsize=8)
ax.set_ylabel("Specimens with no growth (%)")
ax.set_ylim(0, 65)
for xi, b in zip(xs, blocks):
    ax.text(xi, b["est"] * 100 + 6, f"{b['n']:,}", ha="center", fontsize=8, color="#6B7280")
faint_grid(ax, "y")
panel(ax, "a")

# (b) by source within strict
src = D["no_growth"]["strict_by_source"]
names = {"synovial_joint": "Synovial /\njoint fluid", "implant_sonication": "Implant\nsonication"}
axes[1].set_title("")  # titles live in the caption, never in the figure
keys = [k for k in ["synovial_joint", "implant_sonication"] if k in src]
ax = axes[1]
xs = np.arange(len(keys))
blocks = [src[k] for k in keys]
est = [b["est"] * 100 for b in blocks]
lo = [max(0, (b["est"] - b["clustered_ci"][0]) * 100) for b in blocks]
hi = [max(0, (b["clustered_ci"][1] - b["est"]) * 100) for b in blocks]
ax.bar(xs, est, color=BLUE, width=0.55, zorder=3)
ax.errorbar(xs, est, yerr=[lo, hi], fmt="none", ecolor="#2B2B2B", elinewidth=0.9,
            capsize=3, zorder=4)
ax.set_xticks(xs)
ax.set_xticklabels([names[k] for k in keys], fontsize=8)
ax.set_ylabel("Specimens with no growth (%)")
ax.set_ylim(0, 65)
for xi, b in zip(xs, blocks):
    ax.text(xi, b["est"] * 100 + 6, f"{b['n']:,}", ha="center", fontsize=8, color="#6B7280")
faint_grid(ax, "y")
panel(ax, "b")

# (c) sampling gradient
grad = D["sampling_gradient_strict"]
gk = [k for k in ["1", "2", "3", "4-6", "7+"] if k in grad]
ax = axes[2]
xs = np.arange(len(gk))
blocks = [grad[k] for k in gk]
est = [b["est"] * 100 for b in blocks]
# Strata whose clustered interval is not estimable (too few patients to resample) are drawn as
# unconnected open markers without error bars, so the panel cannot be read as a dose-response
# trend running through them.
estimable = [not np.isnan(b["clustered_ci"][0]) and not np.isnan(b["clustered_ci"][1])
             for b in blocks]
lo = [max(0, (b["est"] - b["clustered_ci"][0]) * 100) if ok else 0
      for b, ok in zip(blocks, estimable)]
hi = [max(0, (b["clustered_ci"][1] - b["est"]) * 100) if ok else 0
      for b, ok in zip(blocks, estimable)]

solid = [i for i, ok in enumerate(estimable) if ok]
sparse = [i for i, ok in enumerate(estimable) if not ok]
ax.errorbar([xs[i] for i in solid], [est[i] for i in solid],
            yerr=[[lo[i] for i in solid], [hi[i] for i in solid]],
            fmt="o-", color=BLUE, ecolor="#2B2B2B", elinewidth=0.9, capsize=3, ms=5, zorder=4)
if sparse:
    ax.plot([xs[i] for i in sparse], [est[i] for i in sparse], "o", mfc="white",
            mec=BLUE, mew=1.4, ms=6, ls="none", zorder=4)
    for i in sparse:
        ax.annotate("CI not\nestimable", (xs[i], est[i]), textcoords="offset points",
                    xytext=(0, -30), ha="center", fontsize=8, color="#6B7280")
ax.set_xticks(xs)
ax.set_xticklabels(gk)
ax.set_xlabel("Evaluable source-specific specimens per episode")
ax.set_ylabel("Specimens with no growth (%)")
ax.set_ylim(0, 90)
for xi, b in zip(xs, blocks):
    ax.text(xi, 82, f"{b['n']:,}", ha="center", fontsize=8, color="#6B7280")
faint_grid(ax, "y")
panel(ax, "c")

# (d) within-episode paired comparison, episode level.
# A tier counts as negative for an episode only when every evaluable specimen in it grew nothing.
# The episode-level difference runs in the SAME direction as the between-cohort one in panel a,
# and is confounded by specimen count (median 1 source-specific vs 3 generic per episode); the
# episode-stratified per-specimen model shows no significant difference. The caption says so.
wi = D["within_episode"]
pt = wi["paired_table"]
ptst = wi["paired_test"]
cl = wi.get("conditional_logit", {})
n_ep = pt["n_episodes"]
ax = axes[3]

# Plotting the paired difference with its interval, rather than two independent-looking bars,
# because the comparison is paired and because the raw proportions invite a per-specimen reading
# the data do not support.
d = ptst["diff"] * 100
lo_d, hi_d = ptst["diff_ci"][0] * 100, ptst["diff_ci"][1] * 100
ax.axvline(0, color="#9CA3AF", lw=0.9, ls="--", zorder=2)
ax.errorbar([d], [0], xerr=[[d - lo_d], [hi_d - d]], fmt="o", color=BLUE, ecolor="#2B2B2B",
            elinewidth=1.2, capsize=4, ms=7, zorder=4)
ax.set_yticks([0])
ax.set_yticklabels(["Episode\nentirely\nnegative"], fontsize=8)
ax.set_ylim(-0.75, 0.75)
ax.set_xlim(-6, 20)
ax.set_xlabel("Paired difference, source-specific minus generic\n(percentage points)", fontsize=8)
# Estimate label sits just above the marker, in data coordinates so it tracks the point.
ax.text(d, 0.16, f"{d:+.1f} ({lo_d:+.1f} to {hi_d:+.1f})", ha="center", va="bottom", fontsize=8,
        color="#2B2B2B")
# Sample note is anchored in AXES coordinates and right-aligned inside the frame, so it cannot
# run past the spine however the x-limits change. The discordant split and the conditional odds
# ratio live in the caption; repeating them here overran the panel.
ax.text(0.97, 0.04, f"n = {n_ep:,} episodes", transform=ax.transAxes, ha="right", va="bottom",
        fontsize=8, color="#6B7280")
# Favours-which-side cues, also in axes coordinates.
ax.text(0.02, 0.96, "generic\nmore often\nnegative", transform=ax.transAxes, ha="left", va="top",
        fontsize=7.5, color="#9CA3AF", linespacing=1.2)
ax.text(0.98, 0.96, "source-specific\nmore often\nnegative", transform=ax.transAxes, ha="right",
        va="top", fontsize=7.5, color="#9CA3AF", linespacing=1.2)
faint_grid(ax, "x")
panel(ax, "d")

fig.tight_layout()
save(fig, os.path.join(FIG, "Fig1"))
print("Fig1 (no growth) written")

# ---------------------------------------------------------------- Fig 3: resistance
# Two rows at journal text width: the two agent panels share the top row, and the era panel takes
# a full row of its own. Three panels abreast at 174 mm leaves the era axis too narrow for its
# tick labels.
fig = plt.figure(figsize=(6.85, 6.2))
gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1.0], hspace=0.55, wspace=0.72)

sa = D["amr"]["pooled|first_isolate_episode|saureus"]
sa_keys = [k for k, v in sa.items() if v.get("est") is not None]
sa_keys = sorted(sa_keys, key=lambda k: sa[k]["est"])
ax = fig.add_subplot(gs[0, 0])
hbar(ax, [sa[k] for k in sa_keys], [agent_label(k) for k in sa_keys], color=BLUE)
ax.set_xlabel("Isolates reported resistant (%)", fontsize=8)
ax.set_xlim(0, 96)
ax.tick_params(labelsize=8)
for yi, k in zip(np.arange(len(sa_keys))[::-1], sa_keys):
    ax.text(95, yi, f"{sa[k]['n']:,}", va="center", ha="right", fontsize=8, color="#6B7280")
panel(ax, "a")

gn = D["amr"]["pooled|first_isolate_episode|gramneg"]
gn_keys = [k for k, v in gn.items() if v.get("est") is not None]
gn_keys = sorted(gn_keys, key=lambda k: gn[k]["est"])
ax = fig.add_subplot(gs[0, 1])
hbar(ax, [gn[k] for k in gn_keys], [agent_label(k) for k in gn_keys], color=SALMON)
ax.set_xlabel("Isolates reported resistant (%)", fontsize=8)
ax.set_xlim(0, 96)
ax.tick_params(labelsize=8)
for yi, k in zip(np.arange(len(gn_keys))[::-1], gn_keys):
    ax.text(95, yi, f"{gn[k]['n']:,}", va="center", ha="right", fontsize=8, color="#6B7280")
panel(ax, "b")

era = {k: v for k, v in D["era_mrsa"].items() if k != "trend_test"}
ek = sorted(era)
ax = fig.add_subplot(gs[1, :])
xs = np.arange(len(ek))
blocks = [era[k] for k in ek]
est = [b["est"] * 100 for b in blocks]
lo = [max(0, (b["est"] - b["clustered_ci"][0]) * 100) for b in blocks]
hi = [max(0, (b["clustered_ci"][1] - b["est"]) * 100) for b in blocks]
ax.errorbar(xs, est, yerr=[lo, hi], fmt="o-", color=BLUE, ecolor="#2B2B2B", elinewidth=0.9,
            capsize=3, ms=5, zorder=4)
ax.set_xticks(xs)
ax.set_xticklabels([k.replace(" - ", "-") for k in ek], fontsize=8)
ax.set_xlim(-0.4, len(ek) - 0.6)
ax.set_xlabel("Anchor-year group", fontsize=8)
ax.set_ylabel("Oxacillin-resistant\nS. aureus (%)", fontsize=8)
ax.set_ylim(0, 78)
ax.tick_params(labelsize=8)
for xi, b in zip(xs, blocks):
    ax.text(xi, 72, f"{b['n']:,}", ha="center", fontsize=8, color="#6B7280")
faint_grid(ax, "y")
panel(ax, "c")
save(fig, os.path.join(FIG, "Fig3"))
print("Fig3 (resistance) written")
