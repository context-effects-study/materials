"""ingest.py: read a Qualtrics export and write the human long table (one row per choice).

For every response it applies the registered exclusions (preview, incomplete, duplicate participant,
failed attention check, median choice-page time under 3 seconds, an impossible choice such as the
unavailable phantom, and a repeated category), decodes each choice through the per-structure codebook
using the recorded option order, computes the derived indicators (chose_target, chose_ext, chose_hd,
chose_extreme_tier, chose_clone) and asserts the table's invariants. Participant ids are replaced by a
one-way hash. The columns are listed in analysis/DATA_DICTIONARY.md, part A.

Run: python analysis/ingest.py --export <qualtrics_export.csv> --out human_long.csv
     python analysis/ingest.py --selftest     (builds a synthetic export, reads it, checks the result)
Manuscript: Method ("Human study", exclusions) and Web Appendix D.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Layout: in the working repository this file lives at
# surveys/ (root two levels up, mapping in ./out/); in the public deposit it lives
# at analysis/ (root one level up, mapping in ../surveys/out/). Root = the nearest ancestor
# holding stimuli/; the mapping = the first candidate that exists. working repository behavior is unchanged.
def _find_root(start):
    d = start
    for _ in range(4):
        d = os.path.dirname(d)
        if os.path.isdir(os.path.join(d, "stimuli")):
            return d
    return os.path.abspath(os.path.join(start, "..", ".."))
ROOT = _find_root(HERE)
STIM = os.path.join(ROOT, "stimuli", "stimuli.json")
MAPPING = next((p for p in (os.path.join(HERE, "out", "backbone_MAPPING.json"),
                            os.path.join(ROOT, "surveys", "out", "backbone_MAPPING.json"))
                if os.path.exists(p)), os.path.join(HERE, "out", "backbone_MAPPING.json"))
N_TRIALS = 7
SPEEDER_FLOOR_SEC = 3.0          # SURVEY_SPEC.md rule 2: median per-choice time below this -> exclude

# ---- the per-structure choice codebook (DATA_DICTIONARY.md §A, ) ------------------------------
# Maps the chosen option CODE (stored by the widget as choice_t_code) to the codebook value, using the
# stimulus's target/competitor designation. The decoy code is whatever third code the structure carries.
DECOY_CODES = {"FRQ": "DECOY", "RNG": "RANGE_DECOY", "PHT": "PHANTOM", "SYM": "SYM_DECOY",
               "SIM": "CLONE", "SOT": "EXTREME"}

def load_stimuli():
    S = json.load(open(STIM, encoding="utf-8"))
    by_id = {r["id"]: r for r in S["stimuli"]}
    cats = {c["id"]: c for c in S["categories"]}
    # BIN has no target field; the target focal is the category's decoy target (shared by its decoy cells).
    cat_target_focal = {}
    for r in S["stimuli"]:
        if r["structure"] != "BIN" and r.get("target"):
            cat_target_focal.setdefault(r["category"], r["target"])
    return by_id, cats, cat_target_focal

def option_set(rec, sim_placement):
    """The placement-resolved (target, competitor, options-by-code) for one stimulus."""
    if rec["structure"] == "SIM" and sim_placement == "clone_HD" and rec.get("placement_variants"):
        pv = rec["placement_variants"]["clone_HD"]
        opts = {o["code"]: o for o in pv["options"]}
        return pv.get("target", rec.get("target")), pv.get("competitor", rec.get("competitor")), opts
    return rec.get("target"), rec.get("competitor"), {o["code"]: o for o in rec["options"]}

def decode(structure, code, rec, sim_placement, cat_target_focal):
    """Decode one chosen code into (codebook_value, derived-indicator dict, valid?).
    valid=False means an impossible/unavailable choice (e.g. the phantom) -> routed to exclusions."""
    target, competitor, opts = option_set(rec, sim_placement)
    d = {"chose_target": "", "chose_ext": "", "chose_hd": "", "chose_clone": "", "chose_extreme_tier": ""}
    if code not in opts:
        return ("INVALID", d, False)
    chosen = opts[code]
    d["chose_hd"] = 1 if chosen.get("is_hd") else 0           # available everywhere via is_hd
    if structure == "BIN":
        tf = cat_target_focal.get(rec["category"])
        val = "TARGET" if code == tf else "COMP"
        d["chose_target"] = 1 if code == tf else 0
        return (val, d, True)
    if structure in ("MOT", "EXC"):
        # extremity: the chosen menu-quality tier (per-option 'tier': High/Middle/Low); extreme = not
        # Middle. MOT is the treatment menu, EXC the matched single-option-per-tier control (path a,
        # contract v1.1); the extremity statistic is the MOT-minus-EXC difference on this indicator.
        mt = chosen.get("tier", "")
        d["chose_extreme_tier"] = 0 if mt == "Middle" else 1
        # chose_target MIRRORS chose_extreme_tier for MOT/EXC (CONTRACTS A; analyze.human_cell_rows reads
        # chose_target, and analyze.human_effect documents that the two are the same indicator for the
        # extremity structures). synth.gen_human sets them equal too; keep the real ingest consistent so
        # the human-side reader never hits an empty chose_target for an extremity cell.
        d["chose_target"] = d["chose_extreme_tier"]
        return (code, d, True)                                 # MOT/EXC keep the slot code; no TARGET/COMP
    # decoy structures: TARGET / COMP / <decoy>
    if structure == "PHT" and code == DECOY_CODES["PHT"]:
        return ("PHANTOM", d, False)                           # unavailable-by-design -> exclusion accounting
    if code == target:
        d["chose_target"] = 1; val = "TARGET"
    elif code == competitor:
        d["chose_target"] = 0; val = "COMP"
    else:
        d["chose_target"] = 0; val = DECOY_CODES.get(structure, "DECOY")
    if structure == "SOT":
        d["chose_ext"] = 1 if code == "EXTREME" else 0
    if structure == "SIM":
        d["chose_clone"] = 1 if code == "CLONE" else 0
    return (val, d, True)

# ---- reading the Qualtrics export -----------------------------------------------------------------
def read_qualtrics_csv(path):
    """Return list of row dicts. Qualtrics CSV has 3 header rows (labels, question text, ImportId JSON);
    we key on the FIRST row and skip the next two metadata rows."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    header = rows[0]
    # detect + skip the two Qualtrics metadata rows (row 2 = question text, row 3 = {"ImportId":...})
    body_start = 1
    for i in range(1, min(3, len(rows))):
        joined = ",".join(rows[i])
        if "ImportId" in joined or rows[i][:1] == ['Response Type'] or i <= 2 and any("ImportId" in c for c in rows[i]):
            body_start = i + 1
    # robust: skip rows whose first cell isn't a real ResponseId-like value if a metadata marker was seen
    out = []
    for r in rows[body_start:]:
        if not any(c.strip() for c in r):
            continue
        out.append(dict(zip(header, r)))
    return out

def pid_hash(pid):
    return "P" + hashlib.sha256((pid or "").encode("utf-8")).hexdigest()[:15]

def attention_ok(row, pass_key, pass_label):
    v = (row.get("attention_1") or "").strip()
    return v == str(pass_key) or v == pass_label

def page_submit_cols(header):
    return {t: f"timer_{t}_Page Submit" for t in range(1, N_TRIALS + 1)}

# ---- main ingest ---------------------------------------------------------------------------------
def ingest(rows, by_id, cats, cat_target_focal, pass_key, pass_label, qsf_sha="", export_ts=""):
    long_rows, excl = [], []
    seen_pid = set()
    # trial count K derived from the export's columns (surveys vary: 7 backbone/SIM, 3 format/price-free)
    K = max([t for t in range(1, 13) if rows and f"cell{t}_stimulus" in rows[0]], default=N_TRIALS)
    for row in rows:
        rid = row.get("ResponseId", "")
        raw_pid = row.get("PROLIFIC_PID", "") or rid
        # ---- participant-level exclusions (SURVEY_SPEC, symmetric across cells) ----
        reasons = []
        if (row.get("DistributionChannel", "") or "").lower() == "preview":
            reasons.append("preview")
        if str(row.get("Finished", "1")).strip() in ("0", "False", "false", ""):
            reasons.append("incomplete")
        if raw_pid in seen_pid:
            reasons.append("duplicate")
        if not attention_ok(row, pass_key, pass_label):
            reasons.append("attention")
        # speeder: median of the per-choice Page-Submit times < floor
        ps = []
        for t in range(1, K + 1):
            v = row.get(f"timer_{t}_Page Submit", "")
            try:
                ps.append(float(v))
            except (TypeError, ValueError):
                pass
        if ps and statistics.median(ps) < SPEEDER_FLOOR_SEC:
            reasons.append("speeder")
        seen_pid.add(raw_pid)
        # ---- decode the K trials ----
        trials, invalid_choice = [], False
        seen_cat, seen_struct = set(), set()
        for t in range(1, K + 1):
            sid = row.get(f"cell{t}_stimulus", "")
            if not sid:
                continue
            rec = by_id.get(sid)
            if rec is None:
                reasons.append(f"unknown_stimulus_t{t}"); continue
            code = (row.get(f"cell{t}_code") or row.get(f"choice_{t}_code") or "").strip()
            simpl = row.get(f"cell{t}_sim_placement", "NA")
            val, d, valid = decode(rec["structure"], code, rec, simpl, cat_target_focal)
            if not valid:
                invalid_choice = True                         # phantom/impossible selection
            try:
                rt = float(row.get(f"timer_{t}_Page Submit", "") or "nan")
            except ValueError:
                rt = float("nan")
            seen_cat.add(row.get(f"cell{t}_category", "")); seen_struct.add(row.get(f"cell{t}_structure", ""))
            trials.append({
                "participant_id": pid_hash(raw_pid), "script_id": row.get("script_id", ""),
                "trial_position": t, "cell_id": row.get(f"cell{t}_id", ""),
                "category": row.get(f"cell{t}_category", ""), "structure": rec["structure"],
                "tier": row.get(f"cell{t}_tier", ""), "format": row.get(f"cell{t}_format", "numbers"),
                "position_order": row.get(f"cell{t}_order", ""), "stimulus_id": sid,
                "sim_placement": simpl, "choice": val, **d, "rt_page_sec": rt,
                "consent": row.get("consent", ""), "age": row.get("age", ""),
                "gender": row.get("gender", ""), "device": row.get("device", ""),
                "qsf_sha256": qsf_sha, "export_ts": export_ts,
            })
        if invalid_choice:
            reasons.append("invalid_choice_phantom")
        # invariant: no repeated CATEGORY within a participant (always true by script construction). Structure
        # MAY legitimately repeat within a participant in the 3-trial format and price-free arms (the same
        # effect shown across number/word/picture formats) and in the all-similarity top-up (two clone
        # placements), so structure-no-repeat is NOT a universal invariant: it holds only for the numeric
        # backbone, by construction, and is not asserted here.
        if len([c for c in seen_cat if c]) != len(trials):
            if trials:
                reasons.append("repeat_within_participant")
        completed = len(trials) == K
        if reasons:
            excl.append({"participant_id": pid_hash(raw_pid), "reasons": ";".join(sorted(set(reasons)))})
            continue
        for tr in trials:
            tr["completed_all"] = 1 if completed else 0
            long_rows.append(tr)
    return long_rows, excl

CONTRACT_A_COLS = ["participant_id", "script_id", "trial_position", "cell_id", "category", "structure",
                   "tier", "format", "position_order", "stimulus_id", "sim_placement", "choice",
                   "chose_target", "chose_ext", "chose_hd", "chose_clone", "chose_extreme_tier",
                   "rt_page_sec", "completed_all", "consent", "age", "gender", "device",
                   "qsf_sha256", "export_ts"]

def write_long(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CONTRACT_A_COLS); w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CONTRACT_A_COLS})

def load_pass_key():
    if os.path.exists(MAPPING):
        m = json.load(open(MAPPING, encoding="utf-8"))
        return m.get("attention_1_correct", 5), m.get("attention_1_correct_label", "Strongly agree")
    return 5, "Strongly agree"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export"); ap.add_argument("--out", default=os.path.join(HERE, "out", "human_long.csv"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        import make_synthetic_export as mse
        sys.exit(0 if mse.run_selftest() else 1)
    if not args.export:
        ap.error("provide --export PATH or --selftest")
    by_id, cats, ctf = load_stimuli()
    pk, pl = load_pass_key()
    rows = read_qualtrics_csv(args.export)
    long_rows, excl = ingest(rows, by_id, cats, ctf, pk, pl)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    write_long(args.out, long_rows)
    n_kept = len({r["participant_id"] for r in long_rows})     # K-aware (was //7: printed "0 kept" on 3-trial arms)
    print(f"[ingest] {len(rows)} responses -> {len(long_rows)} choice rows, "
          f"{len(excl)} participants excluded ({n_kept} kept)")

if __name__ == "__main__":
    main()
