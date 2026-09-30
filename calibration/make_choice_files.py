#!/usr/bin/env python3
"""make_choice_files.py: write the analysis-ready files of the calibration pre-test.

For each calibration wave it reads the deposited export (data/raw/) with exactly the reader and the
exclusion rules calibration_analysis.py uses, and writes two files to data/processed/:

  calibration_waveN_participants.csv   one row per export row: whether it was an engineering test row,
                                       whether the respondent was kept, and the exclusion reasons
  calibration_waveN_choices.csv        one row per kept choice: the calibration pair, its block, the
                                       product category, tier and format, the option order shown, the
                                       decoded choice and whether the target option was chosen

For the realism comparison study it writes data/processed/realism_ratings.csv: one row per rating, with
the category, the 7-point rating, the rating page's submit time and whether the respondent was kept under
the study's exclusion rules (anchor_analysis.py).

The raw exports are never modified. The row counts printed here equal the counts in the reports of record
(3,920, 3,090 and 4,131 kept choices; 444 kept realism ratings).

Run: python calibration/make_choice_files.py
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import calibration_analysis as CA     # noqa: E402  (sets up the reader, the pair table and the pre-lock stimuli)
import anchor_analysis as AA          # noqa: E402

I = CA.I                              # analysis/ingest.py

WAVES = {
    "wave1": "calibration_wave1_MAPPING_rng_corrected.json",
    "wave2": "calibration_wave2_MAPPING.json",
    "wave3": "calibration_wave3_MAPPING.json",
}
TEST_PREFIX = "STRESS"


def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def wave_files(wave, mapping_name):
    folder = os.path.join(HERE, wave)
    export = os.path.join(folder, "data", "raw", f"calibration_{wave}_export.csv")
    pairs, by_key, _S, _cats, _by_id = CA.pair_table()
    import json
    mapping = json.load(open(os.path.join(folder, "survey", mapping_name), encoding="utf-8"))
    dealt = {p["arm_id"] for p in mapping.get("calibration_pairs", [])}
    block_of = {p["arm_id"]: p["block"] for p in pairs}
    by_id2, cats2, ctf = I.load_stimuli()
    pk, pl = I.load_pass_key()
    all_rows = I.read_qualtrics_csv(export)
    is_test = lambda r: (r.get("PROLIFIC_PID") or "").startswith(TEST_PREFIX)  # noqa: E731
    rows = [r for r in all_rows if not is_test(r)]
    long_rows, excl = I.ingest(rows, by_id2, cats2, ctf, pk, pl)
    reasons = {e["participant_id"]: e["reasons"] for e in excl}
    pid_of = {}
    for r in all_rows:
        raw = r.get("PROLIFIC_PID", "") or r.get("ResponseId", "")
        pid_of.setdefault(I.pid_hash(raw), raw)

    part_rows = []
    for r in all_rows:
        raw = r.get("PROLIFIC_PID", "") or r.get("ResponseId", "")
        h = I.pid_hash(raw)
        test = is_test(r)
        why = "" if test else reasons.get(h, "")
        kept = 0 if (test or h in reasons) else 1
        part_rows.append([raw, r.get("ResponseId", ""), int(test), 0 if test else 1, kept, why])
    write_csv(os.path.join(folder, "data", "processed", f"calibration_{wave}_participants.csv"),
              ["participant", "response_id", "test_row", "entered_analysis", "kept", "exclusion_reasons"],
              part_rows)

    choice_rows = []
    for r in long_rows:
        if r["structure"] != "BIN":
            continue
        p = by_key.get((r["stimulus_id"], r["format"]))
        if p is None or (dealt and p["arm_id"] not in dealt):
            continue
        choice_rows.append([pid_of.get(r["participant_id"], r["participant_id"]), r["trial_position"],
                            p["arm_id"], block_of.get(p["arm_id"], ""), r["category"], r["tier"], r["format"],
                            r["stimulus_id"], r["position_order"], r["choice"], r["chose_target"],
                            r["rt_page_sec"]])
    write_csv(os.path.join(folder, "data", "processed", f"calibration_{wave}_choices.csv"),
              ["participant", "trial_position", "pair", "block", "category", "tier", "format", "stimulus_id",
               "position_order", "choice", "chose_target", "page_submit_sec"], choice_rows)
    n_kept = sum(1 for x in part_rows if x[4] == 1)
    print(f"[{wave}] {len(all_rows)} export rows; {n_kept} kept respondents; {len(choice_rows)} kept choices")
    return len(choice_rows)


def realism_file():
    rows, _header = AA.load(AA.ANCHOR_CSV)
    timers = lambda row: [f"rea_timer_{c}_Page Submit" for c in AA.PUB_CATS  # noqa: E731
                          if (row.get(f"rea_timer_{c}_Page Submit") or "").strip()]
    kept, _excl = AA.keep_rows(rows, timers)
    kept_ids = {id(r) for r in kept}
    # the reasons, recomputed row by row with the same rules
    out, n_kept_ratings = [], 0
    seen = set()
    for r in rows:
        pid = (r.get("PROLIFIC_PID") or "").strip()
        why = []
        if str(r.get("Finished", "1")).strip() in ("0", "False", "false", ""):
            why.append("incomplete")
        if pid in seen:
            why.append("duplicate")
        if (r.get("attention_1") or "").strip() != AA.ATTN_PASS:
            why.append("attention")
        ps = [float(r[c]) for c in timers(r) if (r.get(c) or "").strip()]
        import statistics
        if ps and statistics.median(ps) < AA.SPEEDER_FLOOR:
            why.append("speeder")
        seen.add(pid)
        k = 1 if id(r) in kept_ids else 0
        for c in AA.PUB_CATS:
            v = AA.rating_value(r.get(f"realism_{c}"))
            if v is None:
                continue
            n_kept_ratings += k
            out.append([pid, r.get("ResponseId", ""), c, v, r.get(f"rea_timer_{c}_Page Submit", ""), k,
                        ";".join(why)])
    write_csv(os.path.join(HERE, "realism_study", "data", "processed", "realism_ratings.csv"),
              ["participant", "response_id", "category", "rating", "page_submit_sec", "kept",
               "exclusion_reasons"], out)
    print(f"[realism_study] {len(rows)} export rows; {len(kept)} kept respondents; {n_kept_ratings} kept ratings")
    return n_kept_ratings


def main():
    counts = {w: wave_files(w, m) for w, m in WAVES.items()}
    counts["realism_study"] = realism_file()
    return counts


if __name__ == "__main__":
    main()
