[![DOI](https://zenodo.org/badge/1294114170.svg)](https://doi.org/10.5281/zenodo.21268251)

# Specimen-label cohorts and culture estimates in orthopedic infection (MIMIC-IV)

Code to reproduce every number, table and figure in:

> Adiniaev Y, Gorenshtein A, Timor TM, Klang E, Geftler A. Specimen-label cohorts and culture
> estimates in code-defined bone and joint infection: a MIMIC-IV measurement study. Under review.

## What this study asks

Culture-based descriptions of bone and joint infection are increasingly drawn from electronic
health record databases. A surgical series knows which specimen came from the infected bone; a
database does not, because microbiology tables record a free-text laboratory workflow label rather
than an anatomical site. We measured how far the resulting estimates depend on which labels are analysed.

Specimen labels are split into two tiers, assigned before any outcome was examined:

- **source-specific** — the label names a musculoskeletal structure or an orthopedic-implant procedure:
  `JOINT FLUID`, `PROSTHETIC JOINT FLUID`, and explicit sonication (from either the specimen label
  or a sonication culture test name);
- **generic** — the label is compatible with, but not specific to, a deep musculoskeletal source:
  `TISSUE`, `BIOPSY`, and `FOREIGN BODY` without a sonication test.

## The central result

Between cohorts, the two label sets give very different numbers: no growth 48.0% (source-specific)
against 34.0% (generic), and a polymicrobial fraction of 10.9% against 42.1%. But the two cohorts
describe different patients, so a between-cohort contrast cannot attribute that to the label.

Within the 487 episodes that contributed **both** kinds of specimen, holding the patient and
admission fixed:

- counting a tier as negative only when **every** one of its evaluable specimens grew nothing, the
  source-specific tier was entirely negative in 198/487 (40.7%) against 154/487 (31.6%) — a paired
  difference of +9.0 points (patient-clustered 95% CI, 4.1–13.8), in the **same** direction as the
  between-cohort comparison;
- that episode-level gap is confounded by specimen count (median 1 source-specific vs 3 generic per
  episode), so an **episode-stratified conditional logistic** model was fitted: OR 0.86 (95% CI,
  0.64–1.15) with patient-clustered uncertainty — no detected per-specimen association;
- a **one-to-one matched subset** (75 episodes contributing exactly one evaluable specimen per
  tier) agreed: 25 vs 14 discordant, P = .11.

So the estimates depend heavily on which labels are analysed, and this design cannot decompose that
dependence into an effect of the specimen versus an effect of who was sampled. The code reports all
three analyses rather than the most favourable one.

Two traps are worth naming, because both produced wrong answers in earlier drafts of this analysis:

- defining an episode-level tier outcome as "contains **any** negative specimen" is not an
  episode-level measure and is biased toward whichever tier contributes more specimens;
- the conditional likelihood discards strata with no within-episode variation, so the retained
  sample (1,227 specimens, 252 informative episodes, 233 patients) is what the estimate rests on,
  not the 2,179 specimens fed in.

## Four definitional choices, made explicit in code

Each one moves the reported numbers, and each is usually left implicit in database studies:

| Choice | Implemented in | Effect in this cohort |
| --- | --- | --- |
| Specimen label tier | `spec_map.py` | No growth 48.0% (source-specific) vs 34.0% (generic); polymicrobial 10.9% vs 42.1% |
| Completed-negative culture | `result_map.py` | Cancelled, incomplete and panel-only negatives excluded from the negative numerator rather than absorbed into it (0.47% of deep specimens here) |
| First-isolate **scope** | `02_build_cohort.py` | Flags are computed *within* each tier. A globally scoped rule would discard 43.2% of source-specific episode-first isolates because the same organism appeared earlier on a blood, urine or swab specimen |
| Low-resolution growth | `02_build_cohort.py` | Counting an explicit report of mixed flora as polymicrobial raises the pooled fraction from 42.1% to 50.8% |

Two classification traps are guarded with explicit tests, runnable via `python code/org_map.py`
and `python code/result_map.py`:

- a laboratory string that names an organism in order to *exclude* it (`NON-FERMENTER, NOT
  PSEUDOMONAS AERUGINOSA`) must not be read as that organism;
- a panel-specific negative (`NO ANAEROBES ISOLATED`) does not establish that the routine culture
  grew nothing, and an incomplete or cancelled readout outranks a negative companion panel.

## Two properties of the source data that bound the results

**There is no explicit bone specimen label anywhere in MIMIC-IV v3.1.** Bone specimens, where they
exist, are submitted under the generic `TISSUE` label and cannot be distinguished from soft tissue.
This is a property of the data, not an analytic choice.

**Chart dates carry no calendar meaning.** MIMIC-IV shifts every patient's dates by a random
per-patient offset into roughly 2100-2200, so calendar-year stratification is impossible. Era is
represented by `anchor_year_group`, which is the only admissible era marker.

The tiers address specimen-category specificity, not infection attribution. A source-specific label identifies
the kind of structure sampled; because the database records no laterality and no link between a
specimen and an operation, it does not establish that the specimen came from the bone, joint, side
or prosthesis named in the diagnosis code.

## Repository structure

```
.
├── README.md
├── LICENSE
├── requirements.txt          pinned dependencies
├── DATA_ACCESS.md            how to obtain MIMIC-IV (credentialed; not included here)
├── run_all.py                runs the whole pipeline in order and stops on the first failure
└── code/
    ├── org_map.py            organism normalization dictionary
    ├── spec_map.py           specimen taxonomy and label tiers
    ├── result_map.py         culture result-status rules
    ├── 00_recon.py           cohort sizing (optional)
    ├── 01_micro_recon.py     microbiology feasibility scan (optional)
    ├── 02_build_cohort.py    episodes, specimens, organisms, susceptibilities
    ├── 10_analysis.py        statistics -> results_digest.json, stats_digest.json
    ├── 20_figures.py         Fig1-Fig3
    ├── 30_verify_refs.py     Crossref DOI verification of the reference list
    ├── 40_supplement_tables.py   Tables 1-4 and eTables 1-13 -> tables.json
    ├── manuscript_text.py    manuscript body text
    ├── paths.py              MIMIC_ROOT and PROJ_ROOT resolution
    ├── 50_build_docx.py      manuscript and Online Resource 1 (Word)
    ├── 55_build_supplement_pdf.py  Online Resource 1 (PDF, the format the journal asks for)
    ├── 60_build_submission.py    title page, cover letter, reporting checklist
    └── 99_audit.py           asserts every number in the prose against the digests
```

`spec_map.py`, `result_map.py` and `org_map.py` each run standalone and print their own
classification self-tests, including the adversarial cases above:

```bash
python code/spec_map.py
```

## Requirements

- Python 3.13 (see `requirements.txt` for exact package versions)
- Approximately 20 GB free disk and 8 GB RAM to run end to end; the large source tables are
  streamed in chunks rather than loaded whole

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Data access

MIMIC-IV is credentialed and is **not** distributed here. See [`DATA_ACCESS.md`](DATA_ACCESS.md)
for how to obtain it from PhysioNet, the required training and data use agreement, and where to
place the files. Set the `MIMIC_ROOT` and `PROJ_ROOT` environment variables, or edit the defaults
in `code/paths.py`.

## Reproducing the results

```bash
python run_all.py
```

This runs every step in order and stops at the first failure. To run the steps individually:

```bash
python code/02_build_cohort.py       # Parquet checkpoints in output/intermediate/
python code/10_analysis.py           # results_digest.json, stats_digest.json, validation sample
python code/20_figures.py            # Fig1-Fig3 to output/figures/ (PDF and PNG, 600 dpi)
python code/40_supplement_tables.py  # tables.json
python code/50_build_docx.py         # manuscript and Online Resource 1 (Word)
python code/55_build_supplement_pdf.py  # Online Resource 1 (PDF)
python code/60_build_submission.py   # title page, cover letter, checklist
python code/99_audit.py              # fails loudly if any reported number has drifted
```

`30_verify_refs.py` checks the reference DOIs against Crossref and needs internet access; it is not
required to reproduce the results. `00_recon.py` and `01_micro_recon.py` only print cohort sizing
used during design.

### Consistency audit

`99_audit.py` restates every quantitative claim made in the manuscript and checks each against
`results_digest.json` and `stats_digest.json`. It also enforces the journal's abstract word limit
and keyword count, and asserts that terminology retired from earlier drafts has not reappeared. It
exits non-zero on any mismatch, so a number cannot drift between the analysis and the prose.

### Determinism

All analyses use a fixed seed. Bootstrap generators are seeded from the data being resampled rather
than drawn from a shared stream, so the same subset of specimens yields the same interval wherever
it is computed; a quantity reported in two places cannot differ in the last decimal between the
text and the tables. A clean run reproduces the published values exactly.

### Caching

`02_build_cohort.py` caches the cohort-filtered microbiology rows to
`output/intermediate/micro_raw_cohort.parquet` and reuses them on later runs, so iterating on the
classification rules does not require re-streaming the source file. Delete that file to force a
re-read.

## Notes on definitions

Cohort, specimen taxonomy, organism dictionary, result-status rules and all measure definitions are
documented in the paper's Methods and Online Resource 1. The dictionaries are code
(`org_map.py`, `spec_map.py`, `result_map.py`) and are the authoritative version of what appears in
the eTables.

## License

Released under the MIT License (see `LICENSE`). Please cite the paper if you use this code.
