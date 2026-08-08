"""
Filesystem locations, resolved once so that no analysis script hard-codes a path.

Resolution order for each location:
  1. the corresponding environment variable, if set;
  2. the default below, which you can edit for a local checkout.

  MIMIC_ROOT   the decompressed MIMIC-IV v3.1 root, containing hosp/ and icu/
  PROJ_ROOT    where outputs are written; output/ is created underneath it

Nothing here reads or writes patient data; the credentialed files stay wherever MIMIC_ROOT points.
"""
import os

# Edit these two defaults for a local checkout, or set the environment variables instead.
DEFAULT_MIMIC_ROOT = os.path.join(os.path.expanduser("~"), "mimic-iv-3.1")
DEFAULT_PROJ_ROOT = os.path.join(os.path.expanduser("~"), "ortho-mimic-study")

ROOT = os.environ.get("MIMIC_ROOT", DEFAULT_MIMIC_ROOT)
PROJ = os.environ.get("PROJ_ROOT", DEFAULT_PROJ_ROOT)

OUT = os.path.join(PROJ, "output")
INT = os.path.join(OUT, "intermediate")
FIG = os.path.join(OUT, "figures")
DOCS = os.path.join(OUT, "submission")

for _d in (OUT, INT, FIG, DOCS):
    os.makedirs(_d, exist_ok=True)


def hosp(name):
    return os.path.join(ROOT, "hosp", name)


def icu(name):
    return os.path.join(ROOT, "icu", name)


def require_source():
    """Fail early and clearly if the credentialed data is not where we expect it."""
    probe = hosp("microbiologyevents.csv.gz")
    if not os.path.exists(probe):
        raise SystemExit(
            f"MIMIC-IV not found at {ROOT!r} (looked for {probe!r}).\n"
            "Set the MIMIC_ROOT environment variable to the decompressed dataset root, or edit\n"
            "DEFAULT_MIMIC_ROOT in code/paths.py. See DATA_ACCESS.md.")


if __name__ == "__main__":
    print(f"MIMIC_ROOT = {ROOT}")
    print(f"PROJ_ROOT  = {PROJ}")
    print(f"outputs    = {OUT}")
    print("source data present" if os.path.exists(hosp("microbiologyevents.csv.gz"))
          else "source data NOT found at MIMIC_ROOT")
