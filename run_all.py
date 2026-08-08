"""
Run the whole pipeline in order, stopping at the first failure.

    python run_all.py             # analysis, figures, tables, documents, audit
    python run_all.py --no-docs   # skip document assembly
    python run_all.py --refs      # also verify reference DOIs (needs internet)

Set MIMIC_ROOT and PROJ_ROOT first, or edit the defaults in code/paths.py.
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.join(HERE, "code")

CORE = ["02_build_cohort.py", "10_analysis.py", "20_figures.py", "40_supplement_tables.py"]
DOCS = ["50_build_docx.py", "55_build_supplement_pdf.py", "60_build_submission.py"]
AUDIT = ["99_audit.py"]
REFS = ["30_verify_refs.py"]


def run(script):
    path = os.path.join(CODE, script)
    print(f"\n{'=' * 78}\n>>> {script}\n{'=' * 78}", flush=True)
    t0 = time.time()
    r = subprocess.run([sys.executable, path], cwd=HERE)
    if r.returncode != 0:
        print(f"\nFAILED: {script} exited {r.returncode}", flush=True)
        sys.exit(r.returncode)
    print(f"--- {script} completed in {time.time() - t0:.1f}s", flush=True)


def main():
    steps = list(CORE)
    if "--no-docs" not in sys.argv:
        steps += DOCS
    steps += AUDIT
    if "--refs" in sys.argv:
        steps += REFS

    sys.path.insert(0, CODE)
    import paths                                            # noqa: E402
    print(f"MIMIC_ROOT = {paths.ROOT}")
    print(f"PROJ_ROOT  = {paths.PROJ}")
    paths.require_source()

    t0 = time.time()
    for s in steps:
        run(s)
    print(f"\n{'=' * 78}\nAll {len(steps)} steps completed in {time.time() - t0:.1f}s")
    print(f"Outputs in {paths.OUT}")


if __name__ == "__main__":
    main()
