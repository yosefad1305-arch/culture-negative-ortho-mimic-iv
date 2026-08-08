# Data access

This study uses **MIMIC-IV v3.1**, a de-identified critical-care and hospital database. The data are
credentialed and cannot be redistributed. No patient-level data are included in this repository.

## How to obtain MIMIC-IV

1. Create a PhysioNet account: https://physionet.org/
2. Complete the required CITI "Data or Specimens Only Research" training and upload the completion report.
3. Sign the PhysioNet Credentialed Health Data Use Agreement for MIMIC-IV.
4. Once approved, download MIMIC-IV v3.1 from the project page:
   https://physionet.org/content/mimiciv/3.1/

## Local layout expected by the code

Place the decompressed module folders so the paths resolve as below:

```
<MIMIC_ROOT>/
├── hosp/
│   ├── admissions.csv.gz
│   ├── patients.csv.gz
│   ├── diagnoses_icd.csv.gz
│   ├── microbiologyevents.csv.gz
│   └── d_icd_diagnoses.csv.gz
└── icu/
    └── icustays.csv.gz
```

## Telling the code where the data is

Paths are resolved once, in `code/paths.py`. No analysis script hard-codes a location. Set two
environment variables:

```bash
export MIMIC_ROOT=/path/to/mimic-iv-3.1     # the folder containing hosp/ and icu/
export PROJ_ROOT=/path/to/outputs           # where output/ will be created
```

On Windows PowerShell:

```powershell
$env:MIMIC_ROOT = "C:\path\to\mimic-iv-3.1"
$env:PROJ_ROOT  = "C:\path\to\outputs"
```

Alternatively, edit `DEFAULT_MIMIC_ROOT` and `DEFAULT_PROJ_ROOT` in `code/paths.py`. To check that
the code can see the data before running anything:

```bash
python code/paths.py
```

`microbiologyevents` is streamed in chunks and filtered to the cohort, so the database can be
processed on a workstation without loading whole tables into memory. The cohort-filtered subset is
cached to `output/intermediate/micro_raw_cohort.parquet` on the first run and reused afterwards;
delete it to force a re-read.

## What is safe to commit

Only code and derived, non-identifiable summary outputs (aggregate counts, figures) may be shared. Never
commit the MIMIC-IV files, any `*.csv.gz`, or any Parquet checkpoints derived from patient records. The
provided `.gitignore` enforces this.
