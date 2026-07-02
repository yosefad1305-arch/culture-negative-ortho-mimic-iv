# Culture-negative benchmark in orthopedic infection (MIMIC-IV)

Code to reproduce the analyses in:

> [Author list]. Microbiology and the culture-negative fraction of code-defined orthopedic infections: an open, reproducible benchmark from MIMIC-IV. Under review.

## Overview

We used MIMIC-IV v3.1 to characterize the microbiology of hospital episodes coded as prosthetic joint
infection or native osteomyelitis. We describe the organism spectrum, the polymicrobial fraction, the
antimicrobial-resistance profile, and the culture-negative fraction of deep musculoskeletal specimens,
and we test how well culture-negativity is anticipated by routinely captured structured data. This
repository reproduces every number, table, and figure in the paper from the raw MIMIC-IV files.

## Repository structure

```
.
├── README.md
├── LICENSE
├── requirements.txt          pinned dependencies
├── DATA_ACCESS.md            how to obtain MIMIC-IV (credentialed; not included here)
└── code/                     analysis code, in run order
    ├── org_map.py            organism normalization dictionary
    ├── spec_map.py           specimen source taxonomy
    ├── 00_recon.py           cohort sizing (reconnaissance)
    ├── 01_micro_recon.py     microbiology feasibility scan
    ├── 02_build_cohort.py    build episodes + specimens + organisms + susceptibilities
    ├── 03_extract_labs.py    inflammatory/nutritional markers from labevents
    ├── 10_analysis.py        aims 1-5: descriptive + inferential statistics
    ├── 11_ml_optional.py     anticipatability probe (cross-validated)
    ├── 20_figures.py         figures 1-4
    ├── 30_verify_refs.py     Crossref DOI verification of the reference list
    ├── 40_supplement_tables.py   supplement eTables
    └── 50_build_docx.py      assemble Word documents
```

## Requirements

- Python 3.14 (see `requirements.txt` for exact package versions)
- Approx. 20 GB free disk and 8 GB RAM to run end to end (the large tables are streamed, not loaded whole)

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Data access

MIMIC-IV is credentialed and is **not** distributed in this repository. See
[`DATA_ACCESS.md`](DATA_ACCESS.md) for how to obtain it from PhysioNet, the required training and data
use agreement, and where to place the files locally. Set the dataset path near the top of each script
(the `ROOT` variable).

## Reproducing the results

Run in order, from the repository root:

```bash
python code/02_build_cohort.py       # writes Parquet checkpoints to output/intermediate/
python code/03_extract_labs.py       # inflammatory markers (for the probe)
python code/10_analysis.py           # results_digest.json + stats_digest.json + tables
python code/11_ml_optional.py        # ml_digest.json
python code/20_figures.py            # figures to output/figures/
python code/40_supplement_tables.py  # supplement eTables
python code/30_verify_refs.py        # reference verification (needs internet)
python code/50_build_docx.py         # Word documents
```

The reconnaissance scripts (`00_recon.py`, `01_micro_recon.py`) are optional and only print cohort
sizing used during design; they are not required to reproduce the final numbers.

## Notes on definitions

Cohort, specimen taxonomy, organism dictionary, and all measure definitions are documented in the
paper's Methods and Supplement. The organism and specimen dictionaries are code (`org_map.py`,
`spec_map.py`) and are the authoritative version of what appears in the eTables.

## License

Released under the MIT License (see `LICENSE`). Please cite the paper if you use this code.
