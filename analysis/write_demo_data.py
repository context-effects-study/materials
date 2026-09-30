#!/usr/bin/env python3
"""write_demo_data.py: write the dress rehearsal's synthetic data to files, as demonstration data in the exact
formats the study will produce.

The dress rehearsal (python analysis/analyze.py) builds its synthetic data in memory with synth.py and a fixed
seed (20260613) and analyzes it. This script runs the rehearsal's own data-building code, stops it at the
moment the data are complete (before any analysis), and writes:

    analysis/demo_data/human_long_demo.csv    the rehearsal's main human data set: one row per choice, the
                                              columns of analysis/DATA_DICTIONARY.md part A (the long table
                                              analysis/ingest.py writes from a Qualtrics export)
    analysis/demo_data/model_log_demo.jsonl   the neutral-condition calls of one planted model profile
                                              (FAITHFUL by default): one JSON record per call, the fields
                                              of part B (the log models/run.py writes)
    analysis/demo_data/README.md              what the two files are, with their row counts

The model log of all fifteen profiles holds several hundred thousand calls; --all-models writes it too, to a
folder you name. Standard library only; no network.

Run: python analysis/write_demo_data.py [--model FAITHFUL] [--all-models DIR]
"""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "demo_data")
sys.path.insert(0, HERE)
import analyze   # noqa: E402
import ingest    # noqa: E402  (the column order of the human long table)


class _Captured(Exception):
    pass


def rehearsal_data():
    """The rehearsal's main human rows and model records, exactly as analyze.run_rehearsal builds them."""
    captured = {}
    real_build_pack = analyze.build_pack

    def capture(human_rows, models, *args, **kwargs):
        captured["human"], captured["models"] = human_rows, models
        raise _Captured()

    analyze.build_pack = capture
    try:
        analyze.run_rehearsal()
    except _Captured:
        pass
    finally:
        analyze.build_pack = real_build_pack
    if "human" not in captured:
        raise SystemExit("the rehearsal did not reach its analysis step; no data captured")
    return captured["human"], captured["models"]


def write_human(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=ingest.CONTRACT_A_COLS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in ingest.CONTRACT_A_COLS})


def write_log(path, records):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="FAITHFUL", help="the planted profile whose calls go into model_log_demo.jsonl")
    ap.add_argument("--all-models", metavar="DIR", help="also write every profile's calls, one file each, to DIR")
    a = ap.parse_args()
    human, models = rehearsal_data()
    if a.model not in models:
        raise SystemExit(f"no profile named {a.model}; the rehearsal's profiles are {sorted(models)}")
    os.makedirs(OUT, exist_ok=True)
    write_human(os.path.join(OUT, "human_long_demo.csv"), human)
    neutral = [r for r in models[a.model] if r.get("prompting_mode") == "neutral"]
    write_log(os.path.join(OUT, "model_log_demo.jsonl"), neutral)
    n_participants = len({r["participant_id"] for r in human})
    lines = [
        "# Demonstration data",
        "",
        "Synthetic data in the exact formats the confirmatory study will produce, written by",
        "`analysis/write_demo_data.py` from the dress rehearsal's own synthetic data (`analysis/synth.py`, seed",
        "20260613). They contain no real responses. The effects planted in them are the rehearsal's answer key, not",
        "predictions.",
        "",
        "| File | Format | Rows |",
        "|---|---|---|",
        f"| `human_long_demo.csv` | the human long table, `analysis/DATA_DICTIONARY.md` part A | {len(human):,} choices from "
        f"{n_participants:,} synthetic participants |",
        f"| `model_log_demo.jsonl` | the model call log, part B (the fields the analysis reads) | {len(neutral):,} neutral-condition calls of the "
        f"planted profile {a.model} |",
        "",
        "`python analysis/analyze.py` analyzes these data (with the other fourteen planted profiles, which it",
        "regenerates in memory) and must end with ALL CHECKS PASS. `python analysis/write_demo_data.py` rewrites",
        "both files identically.",
    ]
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {len(human):,} human rows and {len(neutral):,} model records to {OUT}")
    if a.all_models:
        os.makedirs(a.all_models, exist_ok=True)
        for m, recs in sorted(models.items()):
            write_log(os.path.join(a.all_models, f"model_log_{m}.jsonl"), recs)
        print(f"wrote {len(models)} model logs to {a.all_models}")


if __name__ == "__main__":
    main()
