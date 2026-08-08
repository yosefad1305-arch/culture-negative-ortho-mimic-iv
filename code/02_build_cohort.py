"""
Cohort build. Emits Parquet checkpoints + a validation report.
  episodes.parquet         one row per qualifying admission (episode)
  specimens.parquet        one row per micro_specimen_id in cohort
  organisms.parquet        one row per (specimen, organism) isolate, with first-isolate flags
  susceptibilities.parquet one row per (specimen, organism, antibiotic) S/I/R result

Definitions that differ from a naive build, and why:

  Anatomical-certainty tiers. MIMIC-IV carries no anatomical site for a specimen and no link to
  the operative procedure. Specimen labels are therefore split into a strict tier that names a
  musculoskeletal structure or an orthopaedic-implant procedure, and a generic tier (tissue,
  biopsy, undifferentiated foreign body) that is compatible with a deep musculoskeletal source
  but does not establish one. The strict tier is the primary cohort. See spec_map.py.

  Completed negative cultures. A specimen counts in the no-growth denominator only if the
  laboratory reported a completed bacterial culture. Cancelled, unsuitable and uninterpretable
  tests are classified separately and excluded, rather than being absorbed into the negative
  numerator. See result_map.py.

  First isolates. Organism-spectrum and resistance analyses repeat the same infecting strain
  whenever a patient is sampled intensively. Isolates therefore carry episode-level and
  patient-level first-isolate flags, following CLSI M39 first-isolate principles, and the
  primary analyses use them.
"""
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from org_map import classify as org_classify
from spec_map import classify_spec, is_culture, is_bacterial_culture
from result_map import classify_result, is_admin_org

from paths import ROOT, INT as OUT, hosp, icu, require_source

require_source()
CACHE = os.path.join(OUT, "micro_raw_cohort.parquet")


def p(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- cohort (dx)
# PJI = infection of an internal JOINT prosthesis only: ICD-9 996.66, ICD-10 T84.5x.
# ICD-9 996.67 ("other internal orthopedic device") is the ICD-9 analogue of T84.6/T84.7 and
# belongs in the other-device group, NOT PJI.
PJI9, PJI10 = ("99666",), ("T845",)
DEV9, DEV10 = ("99667",), ("T846", "T847")
OST9, OST10 = ("730",), ("M86",)

p("Loading diagnoses_icd...")
dx = pd.read_csv(os.path.join(ROOT, "hosp", "diagnoses_icd.csv.gz"),
                 usecols=["hadm_id", "seq_num", "icd_code", "icd_version"],
                 dtype={"icd_code": "string", "icd_version": "int8", "seq_num": "int16"})
dx = dx.dropna(subset=["hadm_id"])
dx["hadm_id"] = dx.hadm_id.astype("int64")


def match(pre9, pre10):
    m = pd.Series(False, index=dx.index)
    if pre9:
        m |= (dx.icd_version == 9) & dx.icd_code.str.startswith(tuple(pre9))
    if pre10:
        m |= (dx.icd_version == 10) & dx.icd_code.str.startswith(tuple(pre10))
    return m


is_pji, is_dev, is_ost = match(PJI9, PJI10), match(DEV9, DEV10), match(OST9, OST10)
pji_h = set(dx.loc[is_pji, "hadm_id"].unique())
dev_h = set(dx.loc[is_dev, "hadm_id"].unique())
ost_h = set(dx.loc[is_ost, "hadm_id"].unique())
pji_prim = set(dx.loc[is_pji & (dx.seq_num == 1), "hadm_id"].unique())
ost_prim = set(dx.loc[is_ost & (dx.seq_num == 1), "hadm_id"].unique())
cohort = pji_h | dev_h | ost_h
p(f"PJI={len(pji_h):,} device-other={len(dev_h):,} osteomyelitis={len(ost_h):,} "
  f"union={len(cohort):,}")


def inf_type(h):
    if h in pji_h:
        return "PJI"
    if h in dev_h:
        return "Device (other)"
    return "Osteomyelitis"


# ---------------------------------------------------------------- admissions/patients/icu
p("Loading admissions/patients/icustays...")
adm = pd.read_csv(os.path.join(ROOT, "hosp", "admissions.csv.gz"),
                  usecols=["subject_id", "hadm_id", "admittime", "dischtime", "deathtime",
                           "discharge_location", "insurance", "language", "marital_status",
                           "race", "hospital_expire_flag"],
                  parse_dates=["admittime", "dischtime", "deathtime"])
adm = adm[adm.hadm_id.isin(cohort)].copy()
adm["los_days"] = (adm.dischtime - adm.admittime).dt.total_seconds() / 86400.0

# anchor_year_group is the only era marker that survives MIMIC-IV date shifting. Individual
# chartdates are shifted per patient into 2100-2200 and carry no calendar meaning.
pat = pd.read_csv(os.path.join(ROOT, "hosp", "patients.csv.gz"),
                  usecols=["subject_id", "gender", "anchor_age", "anchor_year_group", "dod"],
                  parse_dates=["dod"])
adm = adm.merge(pat, on="subject_id", how="left")
icu = pd.read_csv(os.path.join(ROOT, "icu", "icustays.csv.gz"), usecols=["hadm_id", "stay_id"])
icu_h = set(icu.hadm_id.unique())

# ---------------------------------------------------------------- micro (filtered)
usecols = ["subject_id", "hadm_id", "micro_specimen_id", "charttime", "spec_type_desc",
           "test_name", "org_name", "isolate_num", "ab_name", "interpretation", "comments"]
_fresh = not os.path.exists(CACHE)
if _fresh:
    p("Streaming microbiologyevents (cohort-filtered)...")
    parts = []
    for ch in pd.read_csv(os.path.join(ROOT, "hosp", "microbiologyevents.csv.gz"),
                          usecols=usecols, dtype="string", chunksize=500_000):
        ch = ch[ch.hadm_id.astype("Int64").isin(cohort)]
        if len(ch):
            parts.append(ch)
    mic = pd.concat(parts, ignore_index=True)
else:
    p("Reading cached cohort-filtered microbiologyevents...")
    mic = pd.read_parquet(CACHE, columns=usecols)

# Identifier columns are cast before anything else, and before the cache is written, so that the
# cached file is canonical: a run that reads the cache sees exactly the dtypes a run that streams
# the source sees. Later steps join on micro_specimen_id and would fail on a string/int mismatch.
mic["hadm_id"] = mic.hadm_id.astype("int64")
mic["subject_id"] = mic.subject_id.astype("int64")
mic["micro_specimen_id"] = mic.micro_specimen_id.astype("int64")

if _fresh:
    # Later steps read this file for the laboratory comment text, and re-streaming the source on
    # every run is wasteful, so it is written on the first pass rather than left as an optional
    # side artefact.
    mic.to_parquet(CACHE, index=False)
    p(f"cached cohort-filtered microbiology rows to {CACHE}")
p(f"micro rows={len(mic):,} specimens={mic.micro_specimen_id.nunique():,} "
  f"hadm_w_micro={mic.hadm_id.nunique():,}")

# ---------------------------------------------------------------- organism classification
orgvals = mic.org_name.dropna().unique().tolist()
orgcache = {v: org_classify(v) for v in orgvals}
admin_org = {v for v in orgvals if is_admin_org(v)}
p(f"distinct org_name values={len(orgvals):,}; administrative (non-growth) values="
  f"{sorted(admin_org)}")


def og(v, key):
    return orgcache.get(v, {}).get(key) if pd.notna(v) else None


def _has(v):
    return pd.notna(v) and str(v).strip() != ""


mic["is_admin_org"] = mic.org_name.map(lambda v: is_admin_org(v) if _has(v) else False)
mic["is_organism"] = mic.org_name.map(
    lambda v: bool(og(v, "is_organism")) if _has(v) else False) & (~mic.is_admin_org)
mic["is_species"] = mic.org_name.map(lambda v: bool(og(v, "is_species_level")) if _has(v) else False)
mic["is_lowres"] = mic.org_name.map(lambda v: bool(og(v, "is_low_resolution")) if _has(v) else False)
mic["broad_group"] = mic.org_name.map(lambda v: og(v, "broad_group") if _has(v) else None)
mic["genus_group"] = mic.org_name.map(lambda v: og(v, "genus_group") if _has(v) else None)
mic["species"] = mic.org_name.map(lambda v: og(v, "species") if _has(v) else None)
mic["is_saureus"] = mic.org_name.map(lambda v: bool(og(v, "is_staph_aureus")) if _has(v) else False)

# ---------------------------------------------------------------- specimen classification
# The tier depends on the set of test names attached to the specimen, so classification is done
# per specimen rather than per distinct specimen label.
tests_by_spec = (mic.dropna(subset=["test_name"])
                 .groupby("micro_specimen_id").test_name.apply(lambda s: tuple(sorted(set(s)))))
label_by_spec = (mic.groupby("micro_specimen_id").spec_type_desc
                 .apply(lambda s: s.dropna().iloc[0] if s.notna().any() else None))

p("Classifying specimens into anatomical-certainty tiers...")
cls = {}
for sid, lab in label_by_spec.items():
    cls[sid] = classify_spec(lab, tests_by_spec.get(sid, ()))

mic["is_culture_test"] = mic.test_name.map(lambda t: is_culture(t) if pd.notna(t) else False)
mic["is_bact_culture"] = mic.test_name.map(
    lambda t: is_bacterial_culture(t) if pd.notna(t) else False)

# ---------------------------------------------------------------- specimen-level
p("Aggregating specimen-level...")
bact = mic[mic.is_bact_culture]
bact_org = bact[bact.is_organism]

# result status from bacterial-culture rows only
has_org_by_spec = bact_org.groupby("micro_specimen_id").size()
comments_by_spec = bact.groupby("micro_specimen_id").comments.apply(list)

spec_ids = sorted(set(mic.micro_specimen_id))
rows = []
sp_hadm = mic.groupby("micro_specimen_id").hadm_id.first()
sp_subj = mic.groupby("micro_specimen_id").subject_id.first()
sp_time = mic.groupby("micro_specimen_id").charttime.apply(
    lambda s: s.dropna().iloc[0] if s.notna().any() else None)
has_bact_by_spec = mic.groupby("micro_specimen_id").is_bact_culture.any()
has_cult_by_spec = mic.groupby("micro_specimen_id").is_culture_test.any()

# species / raw-organism sets for polymicrobial counting, from bacterial-culture rows
sp_species = (bact_org[bact_org.is_species].groupby("micro_specimen_id").species
              .apply(lambda s: sorted(set(s.dropna()))))
sp_orgname = (bact_org[bact_org.is_species].groupby("micro_specimen_id").org_name
              .apply(lambda s: sorted(set(s.dropna()))))
sp_saureus = bact_org.groupby("micro_specimen_id").is_saureus.any()

# Low-resolution growth (morphotype-only results and explicit mixed flora) is real growth that
# was never speciated. Excluding it from the organism sets, as a species-level-only rule does,
# means a specimen reported as "mixed bacterial flora" contributes zero organisms and is scored
# monomicrobial. That is a reporting artefact, not a microbiological finding, so mixed flora is
# tracked separately and reported under an explicit prespecified rule.
_MIXED_TOKENS = ("MIXED BACTERIAL FLORA", "MIXED FLORA")
sp_mixed = (bact_org.assign(
    _m=bact_org.org_name.str.upper().str.contains("|".join(_MIXED_TOKENS), na=False))
    .groupby("micro_specimen_id")._m.any())
sp_lowres_n = (bact_org[bact_org.is_lowres].groupby("micro_specimen_id").org_name
               .apply(lambda s: len(set(s.dropna()))))

for sid in spec_ids:
    c = cls[sid]
    has_bact = bool(has_bact_by_spec.get(sid, False))
    n_org = int(has_org_by_spec.get(sid, 0))
    status = classify_result(n_org > 0, comments_by_spec.get(sid, [])) if has_bact else "no_test"
    species_set = sp_species.get(sid, [])
    orgname_set = sp_orgname.get(sid, [])
    rows.append(dict(
        micro_specimen_id=sid,
        hadm_id=sp_hadm[sid],
        subject_id=sp_subj[sid],
        spec_type_desc=label_by_spec.get(sid),
        source_category=c["source_category"],
        tier=c["tier"],
        is_deep_strict=c["is_deep_strict"],
        is_deep_generic=c["is_deep_generic"],
        is_deep_msk=c["is_deep_msk"],
        is_deep_ext=c["is_deep_ext"],
        has_culture_test=bool(has_cult_by_spec.get(sid, False)),
        has_bacterial_culture=has_bact,
        result_status=status,
        any_growth=n_org > 0,
        n_species_raw=len(orgname_set),
        n_species_norm=len(species_set),
        species_list="; ".join(species_set),
        orgname_list="; ".join(orgname_set),
        polymicrobial_raw=len(orgname_set) >= 2,
        polymicrobial_norm=len(species_set) >= 2,
        has_mixed_flora=bool(sp_mixed.get(sid, False)),
        n_lowres=int(sp_lowres_n.get(sid, 0)),
        has_saureus=bool(sp_saureus.get(sid, False)),
        has_lowres_only=bool(n_org > 0 and len(species_set) == 0),
        charttime=sp_time.get(sid),
    ))
spec = pd.DataFrame(rows)
spec["culture_positive"] = spec.result_status == "positive"
spec["culture_negative"] = spec.result_status == "negative"
spec["evaluable"] = spec.result_status.isin(["positive", "negative"])

p(f"specimens={len(spec):,} bacterial-culture={int(spec.has_bacterial_culture.sum()):,}")
p("  result_status:\n" + spec.result_status.value_counts().to_string())
p(f"  deep strict={int(spec.is_deep_strict.sum()):,} generic={int(spec.is_deep_generic.sum()):,}")

# ---------------------------------------------------------------- organism isolate table
org_iso = bact_org.drop_duplicates(["micro_specimen_id", "org_name"]).copy()
org_iso = org_iso[["subject_id", "hadm_id", "micro_specimen_id", "charttime", "org_name",
                   "species", "genus_group", "broad_group", "is_species", "is_lowres",
                   "is_saureus"]]
org_iso = org_iso.merge(
    spec[["micro_specimen_id", "source_category", "tier", "is_deep_strict", "is_deep_generic",
          "is_deep_msk"]], on="micro_specimen_id", how="left")

# First-isolate flags (CLSI M39 principle): the first recovery of a given organism identity,
# ordered by collection time, within an episode and within a patient. Ties broken by specimen id
# so the selection is deterministic.
#
# The flags are computed SEPARATELY WITHIN EACH ANALYTIC UNIVERSE (strict, generic, pooled deep,
# and all cultures). Computing them once across every culture in the admission would let an
# earlier blood, urine, swab or generic-tissue isolate suppress a later strict joint-fluid or
# sonicate isolate of the same organism, so "first isolate among strict specimens" would silently
# mean "first strict isolate not preceded by that organism anywhere else". The estimand a reader
# assumes is the within-universe one, so that is what each analysis uses.
org_iso["_t"] = pd.to_datetime(org_iso.charttime, errors="coerce")
org_iso = org_iso.sort_values(["_t", "micro_specimen_id"], kind="mergesort")

UNIVERSES = {
    "strict": org_iso.is_deep_strict,
    "generic": org_iso.is_deep_generic,
    "pooled": org_iso.is_deep_msk,
    "all": pd.Series(True, index=org_iso.index),
}
for _u, _sel in UNIVERSES.items():
    for _scope, _key in [("episode", "hadm_id"), ("patient", "subject_id")]:
        col = f"first_isolate_{_scope}_{_u}"
        org_iso[col] = False
        sub = org_iso[_sel]
        org_iso.loc[sub.index[~sub.duplicated([_key, "species"])], col] = True

# Backwards-compatible aliases: the pooled universe is the default reporting universe.
org_iso["first_isolate_episode"] = org_iso.first_isolate_episode_pooled
org_iso["first_isolate_patient"] = org_iso.first_isolate_patient_pooled
org_iso = org_iso.drop(columns=["_t"])

p(f"organism isolates: {len(org_iso):,}")
for _u in UNIVERSES:
    n = int(org_iso[UNIVERSES[_u]].shape[0])
    e = int(org_iso[f"first_isolate_episode_{_u}"].sum())
    q = int(org_iso[f"first_isolate_patient_{_u}"].sum())
    p(f"  {_u:8s} isolates={n:6,}  episode-first={e:6,}  patient-first={q:6,}")

# Quantify what a globally-scoped rule discards. `first_isolate_*_all` IS the global rule (first
# recovery anywhere in the admission or patient, across every culture). A strict isolate that is
# first within the strict universe but not first globally is one the global rule would have
# dropped because the same organism had already been recovered from blood, urine, a swab or a
# generic tissue specimen.
_lost_ep = int((org_iso.is_deep_strict & org_iso.first_isolate_episode_strict
                & ~org_iso.first_isolate_episode_all).sum())
_lost_pt = int((org_iso.is_deep_strict & org_iso.first_isolate_patient_strict
                & ~org_iso.first_isolate_patient_all).sum())
_n_ep = int(org_iso.loc[org_iso.is_deep_strict, "first_isolate_episode_strict"].sum())
_n_pt = int(org_iso.loc[org_iso.is_deep_strict, "first_isolate_patient_strict"].sum())
p(f"  strict isolates a globally-scoped rule would discard: "
  f"{_lost_ep:,}/{_n_ep:,} ({_lost_ep / max(_n_ep, 1):.1%}) episode-first, "
  f"{_lost_pt:,}/{_n_pt:,} ({_lost_pt / max(_n_pt, 1):.1%}) patient-first")

# ---------------------------------------------------------------- susceptibilities
sus = mic[mic.ab_name.notna() & (mic.ab_name.str.strip() != "") & mic.is_organism].copy()
sus = sus[["subject_id", "hadm_id", "micro_specimen_id", "org_name", "species", "genus_group",
           "broad_group", "is_saureus", "ab_name", "interpretation"]]
sus = sus.drop_duplicates(["micro_specimen_id", "org_name", "ab_name"])
_flag_cols = [c for c in org_iso.columns if c.startswith("first_isolate_")]
sus = sus.merge(org_iso[["micro_specimen_id", "org_name"] + _flag_cols],
                on=["micro_specimen_id", "org_name"], how="left")
sus = sus.merge(
    spec[["micro_specimen_id", "source_category", "tier", "is_deep_strict", "is_deep_generic",
          "is_deep_msk"]], on="micro_specimen_id", how="left")
p(f"susceptibility rows: {len(sus):,}")

# ---------------------------------------------------------------- episode-level
p("Aggregating episode-level...")
sc = spec[spec.has_bacterial_culture]


def _ep_frame(sel, prefix):
    """Per-episode specimen counts and outcomes for a given deep-tier selection."""
    d = sc[sel]
    g = d.groupby("hadm_id")
    out = pd.DataFrame({
        f"{prefix}_n": g.size(),
        f"{prefix}_n_evaluable": g.evaluable.sum(),
        f"{prefix}_n_positive": g.culture_positive.sum(),
        f"{prefix}_n_negative": g.culture_negative.sum(),
    })
    out[f"{prefix}_all_negative"] = (
        (out[f"{prefix}_n_evaluable"] > 0) & (out[f"{prefix}_n_positive"] == 0))
    return out


ep = pd.DataFrame({"hadm_id": sorted(adm.hadm_id.unique())}).set_index("hadm_id")
ep = ep.join(_ep_frame(sc.is_deep_strict, "strict"))
ep = ep.join(_ep_frame(sc.is_deep_generic, "generic"))
ep = ep.join(_ep_frame(sc.is_deep_msk, "pooled"))
count_cols = [c for c in ep.columns if c.endswith(("_n", "_n_evaluable", "_n_positive",
                                                   "_n_negative"))]
ep[count_cols] = ep[count_cols].fillna(0).astype(int)
for c in [c for c in ep.columns if c.endswith("_all_negative")]:
    ep[c] = ep[c].fillna(False).astype(bool)

allc = sc.groupby("hadm_id")
ep["n_culture_specimens"] = allc.size().reindex(ep.index).fillna(0).astype(int)
ep["n_source_categories"] = (allc.source_category.nunique().reindex(ep.index)
                             .fillna(0).astype(int))
ep["has_strict_specimen"] = ep.strict_n > 0
ep["has_generic_specimen"] = ep.generic_n > 0
ep["has_deep_specimen"] = ep.pooled_n > 0

# episode organism sets, restricted to strict-tier positives
sdeep = spec[spec.is_deep_strict & spec.culture_positive]


def _sets(df, col):
    return (df.groupby("hadm_id")[col]
            .apply(lambda s: sorted({x for lst in s for x in str(lst).split("; ") if x})))


ep["strict_species"] = _sets(sdeep, "species_list").reindex(ep.index).apply(
    lambda v: v if isinstance(v, list) else [])
ep["strict_orgnames"] = _sets(sdeep, "orgname_list").reindex(ep.index).apply(
    lambda v: v if isinstance(v, list) else [])
ep["n_strict_species_norm"] = ep.strict_species.map(len)
ep["n_strict_species_raw"] = ep.strict_orgnames.map(len)
ep["strict_polymicrobial_norm"] = ep.n_strict_species_norm >= 2
ep["strict_polymicrobial_raw"] = ep.n_strict_species_raw >= 2
# Prespecified handling of low-resolution growth: an explicit report of mixed bacterial flora is
# counted as polymicrobial, because that is what the laboratory reported, even though the
# constituent organisms were never speciated.
_mixed_strict = (spec[spec.is_deep_strict & spec.culture_positive]
                 .groupby("hadm_id").has_mixed_flora.any())
ep["strict_mixed_flora"] = ep.index.map(_mixed_strict).fillna(False).astype(bool)
ep["strict_polymicrobial_incl_mixed"] = ep.strict_polymicrobial_raw | ep.strict_mixed_flora
ep["strict_species"] = ep.strict_species.map("; ".join)
ep["strict_orgnames"] = ep.strict_orgnames.map("; ".join)

# same for the pooled tier, for the sensitivity comparison
pdeep = spec[spec.is_deep_msk & spec.culture_positive]
ep["pooled_species"] = _sets(pdeep, "species_list").reindex(ep.index).apply(
    lambda v: v if isinstance(v, list) else [])
ep["pooled_orgnames"] = _sets(pdeep, "orgname_list").reindex(ep.index).apply(
    lambda v: v if isinstance(v, list) else [])
ep["n_pooled_species_norm"] = ep.pooled_species.map(len)
ep["n_pooled_species_raw"] = ep.pooled_orgnames.map(len)
ep["pooled_polymicrobial_norm"] = ep.n_pooled_species_norm >= 2
ep["pooled_polymicrobial_raw"] = ep.n_pooled_species_raw >= 2
_mixed_pooled = (spec[spec.is_deep_msk & spec.culture_positive]
                 .groupby("hadm_id").has_mixed_flora.any())
ep["pooled_mixed_flora"] = ep.index.map(_mixed_pooled).fillna(False).astype(bool)
ep["pooled_polymicrobial_incl_mixed"] = ep.pooled_polymicrobial_raw | ep.pooled_mixed_flora
ep["pooled_species"] = ep.pooled_species.map("; ".join)
ep["pooled_orgnames"] = ep.pooled_orgnames.map("; ".join)

ep = ep.reset_index()
ep = ep.merge(adm[["hadm_id", "subject_id", "insurance", "language", "marital_status", "race",
                   "gender", "anchor_age", "anchor_year_group", "los_days",
                   "hospital_expire_flag", "discharge_location", "dod", "admittime"]],
              on="hadm_id", how="left")
ep["infection_type"] = ep.hadm_id.map(inf_type)
ep["primary_dx"] = ep.hadm_id.map(lambda h: h in pji_prim or h in ost_prim)
ep["cooccur_pji_osteo"] = ep.hadm_id.map(lambda h: (h in pji_h) and (h in ost_h))
ep["icu_linked"] = ep.hadm_id.map(lambda h: h in icu_h)

# ---------------------------------------------------------------- save
spec.to_parquet(os.path.join(OUT, "specimens.parquet"), index=False)
org_iso.to_parquet(os.path.join(OUT, "organisms.parquet"), index=False)
sus.to_parquet(os.path.join(OUT, "susceptibilities.parquet"), index=False)
ep.to_parquet(os.path.join(OUT, "episodes.parquet"), index=False)

# ---------------------------------------------------------------- validation
p("\n================= VALIDATION =================")
p(f"episodes total: {len(ep):,}")
p("  by infection_type:\n" + ep.infection_type.value_counts().to_string())
p(f"  episodes with >=1 strict deep specimen : {int(ep.has_strict_specimen.sum()):,}")
p(f"  episodes with >=1 generic deep specimen: {int(ep.has_generic_specimen.sum()):,}")
p(f"  primary-dx episodes: {int(ep.primary_dx.sum()):,}")
p(f"  PJI/osteo co-occur : {int(ep.cooccur_pji_osteo.sum()):,}")
p(f"  ICU-linked         : {int(ep.icu_linked.sum()):,} ({ep.icu_linked.mean():.1%})")

for name, sel in [("STRICT", spec.is_deep_strict), ("GENERIC", spec.is_deep_generic),
                  ("POOLED", spec.is_deep_msk)]:
    d = spec[sel & spec.has_bacterial_culture]
    ev = d[d.evaluable]
    p(f"\n{name}: bacterial-culture specimens={len(d):,}")
    p("  " + d.result_status.value_counts().to_string().replace("\n", "\n  "))
    if len(ev):
        p(f"  evaluable={len(ev):,}  no-growth={ev.culture_negative.mean():.4f} "
          f"({int(ev.culture_negative.sum()):,}/{len(ev):,})")

# invariants
assert ep.hadm_id.is_unique, "episode hadm not unique"
assert spec.micro_specimen_id.is_unique, "specimen id not unique"
assert not (spec.is_deep_strict & spec.is_deep_generic).any(), "tiers must be disjoint"
assert spec.loc[spec.result_status == "positive", "any_growth"].all()
assert not spec.loc[spec.result_status == "negative", "any_growth"].any()
assert org_iso.first_isolate_episode.sum() <= len(org_iso)
p("\nINVARIANTS OK. checkpoints written to output/intermediate/")
