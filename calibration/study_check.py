"""study_check.py: rebuild one calibration study's reported numbers from its deposited data and compare them with
the report of record. Used by the reproduce.py in each study folder and by run_all.py.

A wave: calibration_analysis.py reads the wave's de-identified export and its survey mapping, applies the
registered exclusions and writes the wave's report to reproduction/; every table row must equal the same row of
the report of record in <wave>/results/. Two wordings are made uniform before the comparison: one column title
that was renamed after July 2, 2026, and the label of the final calibration lock, which the report of record
gives by its working name.

The realism study: anchor_analysis.py rewrites <study>/results/realism_results.json, whose numbers must equal
the deposited file's.
"""
import json
import os
import re
import subprocess
import sys

CAL = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CAL)
REPRO = os.path.join(ROOT, "reproduction")


def _run(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    if p.returncode != 0:
        raise SystemExit(f"{' '.join(args)} exited with {p.returncode}:\n{(p.stdout + p.stderr)[-2500:]}")
    return p.stdout


def table_rows(md):
    rows = []
    for line in open(md, encoding="utf-8").read().splitlines():
        if line.startswith("|"):
            line = line.replace("| verdict |", "| band verdict |")
            line = re.sub(r"values lock at .*? \(with the enrichment content\)",
                          "values lock (with the enrichment content)", line)
            rows.append(line)
    return rows


def reproduce_wave(wave, mapping):
    """Rebuild the report of one wave and compare it row by row. Returns 0 when every row is identical."""
    os.makedirs(REPRO, exist_ok=True)
    out_md = os.path.join(REPRO, f"calibration_report_{wave}.md")
    _run([os.path.join("calibration", "calibration_analysis.py"),
          "--export", os.path.join("calibration", wave, "data", "raw", f"calibration_{wave}_export.csv"),
          "--wave", wave, "--mapping", os.path.join("calibration", wave, "survey", mapping),
          "--label", "real", "--out", out_md])
    record = os.path.join(CAL, wave, "results", f"calibration_report_{wave}.md")
    new, old = table_rows(out_md), table_rows(record)
    if new != old:
        bad = [f"{a} <> {b}" for a, b in zip(new, old) if a != b][:3]
        print(f"{wave}: {len(new)} rows rebuilt against {len(old)} of record; first differences: {bad}")
        return 1
    print(f"{wave}: all {len(new)} table rows identical to the report of record "
          f"(rebuilt report: reproduction/calibration_report_{wave}.md)")
    return 0


def reproduce_realism():
    rec = os.path.join(CAL, "realism_study", "results", "realism_results.json")
    before = json.load(open(rec, encoding="utf-8"))
    _run([os.path.join("calibration", "anchor_analysis.py")])
    after = json.load(open(rec, encoding="utf-8"))
    if after != before:
        print("realism study: the rebuilt results differ from the deposited file")
        return 1
    print("realism study: the rebuilt results equal the deposited results/realism_results.json")
    return 0
