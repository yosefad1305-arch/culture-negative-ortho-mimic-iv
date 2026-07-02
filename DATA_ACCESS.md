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

Place the decompressed module folders so the paths resolve as below, then set the `ROOT` variable at the
top of each script to the dataset root:

```
<ROOT>/
├── hosp/
│   ├── admissions.csv.gz
│   ├── patients.csv.gz
│   ├── diagnoses_icd.csv.gz
│   ├── procedures_icd.csv.gz
│   ├── microbiologyevents.csv.gz
│   ├── labevents.csv.gz
│   ├── d_icd_diagnoses.csv.gz
│   └── d_labitems.csv.gz
└── icu/
    └── icustays.csv.gz
```

The large tables (`microbiologyevents`, `labevents`) are streamed in chunks and filtered to the cohort,
so the full database can be processed on a workstation without loading whole tables into memory.

## What is safe to commit

Only code and derived, non-identifiable summary outputs (aggregate counts, figures) may be shared. Never
commit the MIMIC-IV files, any `*.csv.gz`, or any Parquet checkpoints derived from patient records. The
provided `.gitignore` enforces this.
