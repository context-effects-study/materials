"""make_synthetic_export.py: a synthetic Qualtrics export for testing analysis/ingest.py.

It builds a wide export in the shape the backbone survey produces (reusing surveys/generate_qsf.py's cell
resolution, so the columns match), plants choices at known effect sizes, adds one row for each exclusion
rule, and then checks that the codebook decodes every structure correctly, that every exclusion fires,
that clean rows survive, and that the recovered effect signs match the planted ones. Fixed seed 4242.

Run: python analysis/make_synthetic_export.py    (also run by python analysis/ingest.py --selftest)
"""
from __future__ import annotations
import csv, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Layout: in the working repository this file lives at
# surveys/ (root two levels up; synth at root/engines/analysis; the survey
# generator in this directory); in the public deposit it lives at analysis/ (root one level up;
# synth in this directory; the generator at root/surveys). working repository behavior is unchanged.
def _find_root(start):
    d = start
    for _ in range(4):
        d = os.path.dirname(d)
        if os.path.isdir(os.path.join(d, "stimuli")):
            return d
    return os.path.abspath(os.path.join(start, "..", ".."))
ROOT = _find_root(HERE)
sys.path.insert(0, HERE)
for _cand in (os.path.join(ROOT, "engines", "analysis"), os.path.join(ROOT, "analysis"),
              os.path.join(ROOT, "surveys")):
    if os.path.isdir(_cand):
        sys.path.insert(0, _cand)
import generate_qsf as G
import ingest as I
from synth import TRUTH, TIER_ATTEN, BASE   # planted human truths


def effect_by_struct_tier(tgt_rows):
    """Per-(structure, tier) effect = the structure's target share minus its matched control's share.
    The matched control is BIN for every effect except the extremity treatment MOT, whose control is the
    EXC single-option-per-tier menu (path a, contract v1.1). Local to this self-test so it does not
    depend on a synth helper name; mirrors analyze.py's human_effect control choice."""
    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0])
    for r in tgt_rows:
        a = agg[(r["structure"], r["tier"])]
        a[0] += int(r["chose_target"]); a[1] += 1
    share = {k: (v[0] / v[1] if v[1] else 0.0) for k, v in agg.items()}
    out = {}
    for (st, tier), sh in share.items():
        if st in ("BIN", "EXC"):
            continue
        control = "EXC" if st == "MOT" else "BIN"
        out[(st, tier)] = sh - share.get((control, tier), BASE)
    return out

N_TRIALS = 7
EXPORT = os.path.join(HERE, "out", "synthetic_export.csv")

def _resolve():
    cats, by_cell, pub, inv, structs = G.load_design()
    cat_map, str_map = G.build_index_map(pub, inv, structs)
    rows = list(csv.DictReader(open(G.SCRIPTSET, encoding="utf-8")))
    scripts = {}
    for r in rows:
        scripts.setdefault(int(r["script_id"]), []).append(
            {"script_id": int(r["script_id"]), "position": int(r["position"]),
             "category": r["category"], "structure": r["structure"], "tier": r["tier"]})
    by_id = {r["id"]: r for r in json.load(open(G.STIMULI, encoding="utf-8"))["stimuli"]}
    _, _, ctf = I.load_stimuli()
    return cats, by_cell, cat_map, str_map, scripts, by_id, ctf

def plant_code(rec, simpl, tier, ctf, rng):
    """Pick a chosen option code at the planted target/extreme share for this structure."""
    st = rec["structure"]
    target, comp, opts = I.option_set(rec, simpl)
    if st == "BIN":
        tf = ctf.get(rec["category"]); other = next(c for c in opts if c != tf)
        return tf if rng.random() < BASE else other
    if st in ("MOT", "EXC"):
        # Extremity: pick an extreme-tier (High/Low) vs Middle option at the planted extreme share.
        # MOT is the treatment menu (carries the planted extremity pull); EXC is the matched
        # single-option-per-tier control (path a, contract v1.1), so it plants at the BASE rate only
        # (no planted effect) - the registered extremity statistic is the MOT-minus-EXC difference.
        p = BASE + (TRUTH["MOT"] * TIER_ATTEN[tier] if st == "MOT" else 0.0)
        ext = [c for c, o in opts.items() if o.get("tier") in ("High", "Low")]
        mid = [c for c, o in opts.items() if o.get("tier") == "Middle"]
        return rng.choice(ext) if (rng.random() < p and ext) else rng.choice(mid or ext)
    p = BASE + TRUTH.get(st, 0.0) * TIER_ATTEN[tier]
    decoy = [c for c in opts if c not in (target, comp)]
    if rng.random() < p:
        return target
    if st == "PHT":
        return comp                                   # phantom is unavailable; clean rows never pick it
    return comp if rng.random() < 0.85 else (decoy[0] if decoy else comp)

def clean_row(rid, pid, sid, script_rows, cat_map, str_map, by_cell, cats, by_id, ctf, rng, k=None):
    kk = k or N_TRIALS   # k lets a fixture build a shorter (e.g. 3-trial) participant; default = the 7-trial backbone
    pairs = dict(G.script_cells(script_rows, cat_map, str_map, by_cell, cats))
    row = {"ResponseId": rid, "PROLIFIC_PID": pid, "DistributionChannel": "anonymous",
           "Finished": "1", "script_id": str(sid), "attention_1": "5",
           "consent": "yes", "age": str(rng.randint(20, 65)),
           "gender": rng.choice(["Woman", "Man", "Non-binary"]), "device": "desktop"}
    for t in range(1, kk + 1):
        for suf in ("id", "category", "structure", "tier", "format", "order", "stimulus", "sim_placement"):
            row[f"cell{t}_{suf}"] = pairs[f"cell{t}_{suf}"]
        rec = by_id[pairs[f"cell{t}_stimulus"]]
        tier = int(pairs[f"cell{t}_tier"])
        code = plant_code(rec, pairs[f"cell{t}_sim_placement"], tier, ctf, rng)
        order = pairs[f"cell{t}_order"].split(",")
        row[f"choice_{t}"] = str(order.index(code) + 1)
        row[f"choice_{t}_code"] = code
        for sub, val in (("First Click", round(rng.uniform(1, 3), 1)),
                         ("Last Click", round(rng.uniform(4, 9), 1)),
                         ("Page Submit", round(rng.uniform(5, 14), 1)),
                         ("Click Count", rng.randint(1, 4))):
            row[f"timer_{t}_{sub}"] = str(val)
    return row

def build_export(path, n_clean=3000, seed=4242):
    rng = random.Random(seed)
    cats, by_cell, cat_map, str_map, scripts, by_id, ctf = _resolve()
    sids = sorted(scripts)
    clean = []
    for i in range(n_clean):
        sid = sids[i % len(sids)]
        clean.append(clean_row(f"R{i:05d}", f"PID{i:05d}", sid, scripts[sid],
                               cat_map, str_map, by_cell, cats, by_id, ctf, rng))
    # one row per exclusion rule (each violates exactly one), based on fresh clean templates
    bad = []
    def tmpl(tag): return clean_row(f"X{tag}", f"BAD{tag}", sids[0], scripts[sids[0]],
                                    cat_map, str_map, by_cell, cats, by_id, ctf, rng)
    a = tmpl("ATT"); a["attention_1"] = "2"; bad.append(("attention", a))
    s = tmpl("SPD")
    for t in range(1, N_TRIALS + 1):
        s[f"timer_{t}_Page Submit"] = "1.0"
    bad.append(("speeder", s))
    p = tmpl("PRV"); p["DistributionChannel"] = "preview"; bad.append(("preview", p))
    inc = tmpl("INC"); inc["Finished"] = "0"; bad.append(("incomplete", inc))
    dup = dict(clean[0]); dup["ResponseId"] = "XDUP"; bad.append(("duplicate", dup))   # same PID as clean[0]
    ph = None                                          # pick a script that actually CONTAINS a PHT trial
    for sid in sids:                                    # (each script carries only 7 of the 9 structures)
        cand = clean_row("XPHN", "BADPHN", sid, scripts[sid], cat_map, str_map, by_cell, cats, by_id, ctf, rng)
        pht_t = next((t for t in range(1, N_TRIALS + 1) if cand[f"cell{t}_structure"] == "PHT"), None)
        if pht_t:
            cand[f"choice_{pht_t}_code"] = "PHANTOM"   # an unavailable-by-design selection
            ph = cand; break
    bad.append(("invalid_choice_phantom", ph))

    all_rows = clean + [r for _, r in bad]
    cols = list(clean[0].keys())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerow([f"{c} - question text" for c in cols])                 # Qualtrics metadata row 2
        w.writerow(["{\"ImportId\":\"%s\"}" % c for c in cols])            # Qualtrics metadata row 3 (ImportId)
        for r in all_rows:
            w.writerow([r.get(c, "") for c in cols])
    return n_clean, [tag for tag, _ in bad]

# ---------------------------------- the dress rehearsal -------------------------------------------
def run_selftest():
    by_id, cats, ctf = I.load_stimuli()
    checks = []
    def ck(name, ok, detail=""): checks.append((name, bool(ok), detail))

    # (1) EXACT decoder checks across all 9 structures (backpacks t1; target focal = HD)
    cat = "backpacks"
    rec = lambda st: next(r for r in [by_id[k] for k in by_id]
                          if r["category"] == cat and r["structure"] == st and r["memorization_tier"] == 1)
    def dec(st, code, simpl="NA"): return I.decode(st, code, rec(st), simpl, ctf)
    cases = [
        ("BIN HD->TARGET", dec("BIN", "HD"), "TARGET", {"chose_target": 1, "chose_hd": 1}, True),
        ("BIN HF->COMP", dec("BIN", "HF"), "COMP", {"chose_target": 0, "chose_hd": 0}, True),
        ("FRQ HD->TARGET", dec("FRQ", "HD"), "TARGET", {"chose_target": 1}, True),
        ("FRQ DECOY->DECOY", dec("FRQ", "DECOY"), "DECOY", {"chose_target": 0}, True),
        ("RNG decoy", dec("RNG", "RANGE_DECOY"), "RANGE_DECOY", {"chose_target": 0}, True),
        ("PHT PHANTOM->invalid", dec("PHT", "PHANTOM"), "PHANTOM", {}, False),
        ("PHT HD->TARGET", dec("PHT", "HD"), "TARGET", {"chose_target": 1}, True),
        ("SYM decoy", dec("SYM", "SYM_DECOY"), "SYM_DECOY", {"chose_target": 0}, True),
        ("SYM HD hd-flag", dec("SYM", "HD"), "TARGET", {"chose_hd": 1}, True),
        ("SOT EXTREME->ext", dec("SOT", "EXTREME"), "EXTREME", {"chose_ext": 1, "chose_target": 0}, True),
        ("SOT HD->TARGET", dec("SOT", "HD"), "TARGET", {"chose_target": 1}, True),
        ("SIM CLONE->clone", dec("SIM", "CLONE"), "CLONE", {"chose_clone": 1, "chose_target": 0}, True),
        ("SIM HD->TARGET", dec("SIM", "HD"), "TARGET", {"chose_target": 1}, True),
    ]
    # MOT extreme vs middle (pick a High and a Middle code from the record)
    motr = rec("MOT")
    hi = next(o["code"] for o in motr["options"] if o.get("tier") == "High")
    mid = next(o["code"] for o in motr["options"] if o.get("tier") == "Middle")
    cases.append((f"MOT {hi}(High)->extreme", I.decode("MOT", hi, motr, "NA", ctf), hi, {"chose_extreme_tier": 1}, True))
    cases.append((f"MOT {mid}(Middle)->not extreme", I.decode("MOT", mid, motr, "NA", ctf), mid, {"chose_extreme_tier": 0}, True))
    # EXC, the single-option-per-tier extremity control (path a): same chose_extreme_tier indicator as MOT.
    excr = rec("EXC")
    eh = next(o["code"] for o in excr["options"] if o.get("tier") == "High")
    em = next(o["code"] for o in excr["options"] if o.get("tier") == "Middle")
    cases.append((f"EXC {eh}(High)->extreme", I.decode("EXC", eh, excr, "NA", ctf), eh, {"chose_extreme_tier": 1}, True))
    cases.append((f"EXC {em}(Middle)->not extreme", I.decode("EXC", em, excr, "NA", ctf), em, {"chose_extreme_tier": 0}, True))
    dec_ok = True
    for name, (val, d, valid), exp_val, exp_d, exp_valid in cases:
        ok = (val == exp_val) and (valid == exp_valid) and all(d.get(k) == v for k, v in exp_d.items())
        dec_ok &= ok
        if not ok:
            print(f"  DECODER MISS {name}: got val={val} valid={valid} d={d}")
    ck("codebook decoder exact across all 9 structures (incl. EXC)", dec_ok, f"{len(cases)} cases")

    # (2) build + ingest the synthetic export; exclusions fire, clean rows survive
    n_clean, bad_tags = build_export(EXPORT)
    rows = I.read_qualtrics_csv(EXPORT)
    pk, pl = I.load_pass_key()
    long_rows, excl = I.ingest(rows, by_id, cats, ctf, pk, pl, qsf_sha="selftest", export_ts="2026-06-13")
    I.write_long(os.path.join(HERE, "out", "human_long_selftest.csv"), long_rows)
    ck("rows read = clean + 6 bad", len(rows) == n_clean + 6, f"{len(rows)} read")
    ck("exactly 6 participants excluded", len(excl) == 6, f"{len(excl)} excluded")
    got_reasons = {r["reasons"].split(";")[0] for r in excl}
    want = {"attention", "speeder", "preview", "incomplete", "duplicate", "invalid_choice_phantom"}
    # each bad row trips at least its intended rule (reasons may stack, so check coverage by substring)
    all_reasons = ";".join(r["reasons"] for r in excl)
    cover = all(any(tag in r["reasons"] for r in excl) for tag in want)
    ck("every exclusion rule fired (attention/speeder/preview/incomplete/duplicate/phantom)", cover,
       sorted({x for r in excl for x in r["reasons"].split(";")}))
    ck("kept rows = clean x 7 trials", len(long_rows) == n_clean * N_TRIALS, f"{len(long_rows)} rows")

    # (3) recovery: planted effect SIGNS recovered from the ingested long table (ties ingest->analysis)
    tgt_rows = [{"structure": r["structure"], "tier": int(r["tier"]), "chose_target": int(r["chose_target"])}
                for r in long_rows if r["chose_target"] != "" and r["structure"] != "MOT"]
    eff = effect_by_struct_tier(tgt_rows)
    big = {st: eff.get((st, 1), 0.0) for st in ("FRQ", "RNG", "SOT", "SYM")}
    signs_ok = all(v > 0.02 for v in big.values())
    pht = eff.get(("PHT", 1), 0.0)
    ck("planted effect signs recovered from ingested data (FRQ/RNG/SOT/SYM > 0; PHT ~ 0)",
       signs_ok and abs(pht) < 0.05, f"tier1 { {k: round(v,3) for k,v in big.items()} } PHT={pht:.3f}")
    # derived columns present + sane
    sot = [r for r in long_rows if r["structure"] == "SOT"]
    sim = [r for r in long_rows if r["structure"] == "SIM"]
    mot = [r for r in long_rows if r["structure"] == "MOT"]
    ck("derived cols populated (SOT chose_ext, SIM chose_clone, MOT chose_extreme_tier, HD via is_hd)",
       all(r["chose_ext"] != "" for r in sot) and all(r["chose_clone"] != "" for r in sim)
       and all(r["chose_extreme_tier"] != "" for r in mot)
       and all(r["chose_hd"] in (0, 1) for r in long_rows))
    # SIM both placements present in the kept data
    placements = {r["sim_placement"] for r in sim}
    ck("SIM both placements present in ingested data", {"clone_HF", "clone_HD"} <= placements, sorted(placements))

    # (4) regression guard for the no-repeat-structure fix: a 3-trial
    # participant whose trials REPEAT a structure but use DISTINCT categories must be KEPT, not excluded. This is
    # the real format / price-free / similarity case the OLD "no repeated structure" invariant silently dropped;
    # exercised end to end through the actual ingest(), not just the logic.
    from collections import defaultdict as _dd
    cats4, by_cell4, cat_map4, str_map4, scripts4, by_id4, ctf4 = _resolve()
    bycode = _dd(dict)   # structure-code -> {category: trial}, from the REAL backbone scriptset (codes, not names)
    for sid4 in sorted(scripts4):
        for tr in scripts4[sid4]:
            bycode[tr["structure"]].setdefault(tr["category"], tr)
    pcode, picks = next(((code, list(bycat.values())[:3]) for code, bycat in bycode.items() if len(bycat) >= 3),
                        (None, []))
    rng4 = random.Random(31337)
    s3 = [{"script_id": 99001, "position": i + 1, "category": tr["category"], "structure": pcode, "tier": tr["tier"]}
          for i, tr in enumerate(picks)]
    if len(s3) == 3:
        row3 = clean_row("RFX3", "PIDFX3", 99001, s3, cat_map4, str_map4, by_cell4, cats4, by_id4, ctf4, rng4, k=3)
        lr3, ex3 = I.ingest([row3], by_id, cats, ctf, pk, pl, qsf_sha="fx3", export_ts="2026-06-14")
        structs3 = {r["structure"] for r in lr3}
        ck("3-trial repeated-structure + distinct-category participant KEPT (no false repeat-within exclusion)",
           len(lr3) == 3 and len(ex3) == 0 and len(structs3) == 1,
           f"kept={len(lr3)} excl={len(ex3)} struct={sorted(structs3)} cats={[t['category'] for t in picks]}")
    else:
        ck("3-trial repeated-structure fixture buildable", False, f"only {len(s3)} same-structure distinct-category trials")

    allok = all(ok for _, ok, _ in checks)
    w = max(len(n) for n, _, _ in checks)
    out = ["# ingest.py dress rehearsal (make_synthetic_export.py)",
           "(A synthetic Qualtrics export built from the REAL backbone design, with",
           "planted choices + one row per exclusion rule. Validates the codebook decoder exactly, the",
           "SURVEY_SPEC exclusions end to end, and that the ingested long table feeds the same analysis the",
           "dress rehearsal already proved. NO real data.)", "",
           "## Checks", "| check | result | detail |", "|---|---|---|"]
    lines = []
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n:<{w}}  {d}")
        out.append(f"| {n} | {'PASS' if ok else 'FAIL'} | {d} |")
    out += ["", f"## OVERALL: {'INGEST PIPELINE GREEN' if allok else 'INGEST FAILURE'}",
            f"Synthetic export: {n_clean} clean + 6 excludable; kept {len(long_rows)//N_TRIALS} participants "
            f"({len(long_rows)} choice rows). The same analysis/analyze.py consumes this long table "
            "at Stage 2."]
    open(os.path.join(HERE, "INGEST_CHECK.md"), "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("\n".join(["", f"OVERALL: {'INGEST PIPELINE GREEN' if allok else 'INGEST FAILURE'}"]))
    return allok

if __name__ == "__main__":
    sys.exit(0 if run_selftest() else 1)
