#!/usr/bin/env python3
"""qsf_selftest.py: rebuild the backbone design from the survey file alone and check it.

Using only surveys/out/backbone.qsf and its mapping, it parses the 180 script setters and checks that
every cell resolves to the right stimulus, no script repeats a category or a structure, even presentation
gives each cell its planned number of choices (the 350/350 tier split, 100 first choices per cell), every
option block is valid and matches its stimulus, and the choice widget reads and writes the declared
fields. Exit 1 if any check fails.

Run: python surveys/qsf_selftest.py      (after surveys/generate_qsf.py)
"""
import json, os, csv, collections, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Layout: root = the nearest ancestor holding stimuli/
# (working repository: two levels up from surveys/; public deposit: one level up from surveys/).
def _find_root(start):
    d = start
    for _ in range(4):
        d = os.path.dirname(d)
        if os.path.isdir(os.path.join(d, "stimuli")):
            return d
    return os.path.abspath(os.path.join(start, "..", ".."))
ROOT = _find_root(HERE)
QSF = os.path.join(HERE, "out", "backbone.qsf")
MAP = os.path.join(HERE, "out", "backbone_MAPPING.json")
SCRIPTSET = os.path.join(HERE, "scriptset_180.csv")
STIMULI = os.path.join(ROOT, "stimuli", "stimuli.json")
N_PUBLISHED = 7
N_CAT = 10
N_SCRIPTS = 180
N_STRUCT = 9

def main():
    qsf = json.load(open(QSF, encoding="utf-8"))
    mapping = json.load(open(MAP, encoding="utf-8"))
    cat_map = {int(k): v for k, v in mapping["category_index_to_name"].items()}
    str_map = {int(k): v for k, v in mapping["structure_index_to_code"].items()}
    S = json.load(open(STIMULI, encoding="utf-8"))
    by_cell = {(r["category"], r["structure"], r["memorization_tier"]): r for r in S["stimuli"]}
    cats = {c["id"]: c for c in S["categories"]}

    els = qsf["SurveyElements"]
    flow = next(e for e in els if e["Element"] == "FL")["Payload"]["Flow"]
    rnd = next(e for e in flow if e["Type"] == "BlockRandomizer")
    setters = rnd["Flow"]
    sqs = [e for e in els if e["Element"] == "SQ"]
    bl_blocks = list(next(e for e in els if e["Element"] == "BL")["Payload"].values())

    checks = []
    def ck(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    # 0. randomizer shape
    ck("randomizer is SubSet=1 + EvenPresentation", rnd.get("SubSet") == 1 and rnd.get("EvenPresentation") is True)
    ck("180 script setters present", len(setters) == N_SCRIPTS, f"{len(setters)} setters")

    # 1. parse each setter into {script_id, cells{t}->fields}
    parsed = {}
    for s in setters:
        kv = {d["Field"]: d["Value"] for d in s["EmbeddedData"]}
        sid = int(kv["script_id"])
        cells = {}
        for t in range(1, 8):
            cells[t] = {k[len(f"cell{t}_"):]: kv[k] for k in kv if k.startswith(f"cell{t}_")}
        parsed[sid] = cells
    ck("script_ids are exactly 1..180", sorted(parsed) == list(range(1, N_SCRIPTS + 1)))

    # 2. cross-check every cell against scriptset_180.csv via the seeded map
    rows = list(csv.DictReader(open(SCRIPTSET, encoding="utf-8")))
    src = collections.defaultdict(dict)
    for r in rows:
        src[int(r["script_id"])][int(r["position"])] = (int(r["category"]), int(r["structure"]), int(r["tier"]))
    mismatch = 0
    bad_resolve = 0
    bad_optjson = 0
    order_bad = 0
    norepeat_bad = 0
    for sid, cells in parsed.items():
        seen_cat, seen_str = set(), set()
        for t in range(1, 8):
            ci, si, tier = src[sid][t]
            want_cat, want_str = cat_map[ci], str_map[si]
            c = cells[t]
            if c["category"] != want_cat or c["structure"] != want_str or int(c["tier"]) != tier:
                mismatch += 1
            seen_cat.add(c["category"]); seen_str.add(c["structure"])
            rec = by_cell.get((want_cat, want_str, tier))
            if rec is None or c["stimulus"] != rec["id"]:
                bad_resolve += 1; continue
            # option JSON valid; codes match the record (as a set); count matches; order is a permutation
            try:
                opts = json.loads(c["options"])
            except Exception:
                bad_optjson += 1; continue
            rec_codes = [o["code"] for o in rec["options"]]
            if len(opts) != len(rec_codes) or {o["code"] for o in opts} != set(rec_codes):
                bad_optjson += 1
            order_codes = c["order"].split(",")
            if sorted(order_codes) != sorted(rec_codes) or [o["code"] for o in opts] != order_codes:
                order_bad += 1
        if len(seen_cat) != 7 or len(seen_str) != 7:
            norepeat_bad += 1
    ck("every cell matches scriptset (cat/struct/tier)", mismatch == 0, f"{mismatch} mismatches")
    ck("every cell resolves to the right stimulus id", bad_resolve == 0, f"{bad_resolve} bad")
    ck("every option block is valid JSON w/ matching codes & count", bad_optjson == 0, f"{bad_optjson} bad")
    ck("shown order is a permutation of the option codes", order_bad == 0, f"{order_bad} bad")
    ck("no repeated category/structure within any script", norepeat_bad == 0, f"{norepeat_bad} scripts violate")

    # 3. even dispensing reproduces the proven balance (the QSF carries the proven design)
    appear = collections.Counter()
    tiered = collections.Counter()
    firsts = collections.Counter()
    pub_idx = {cat_map[i] for i in range(N_PUBLISHED)}
    for sid, cells in parsed.items():
        for t in range(1, 8):
            key = (cells[t]["category"], cells[t]["structure"])
            appear[key] += 1
            tiered[(key, int(cells[t]["tier"]))] += 1
            if t == 1:
                firsts[key] += 1
    ck("every (cat,struct) cell in exactly 14 script-slots", set(appear.values()) == {14},
       f"min {min(appear.values())}/max {max(appear.values())}")
    pub_split_ok = all(tiered[(k, 1)] == 7 and tiered[(k, 2)] == 7
                       for k in appear if k[0] in pub_idx)
    inv_split_ok = all(tiered[(k, 3)] == 14 for k in appear if k[0] not in pub_idx)
    ck("published cells split 7 tier-1 + 7 tier-2 slots (=350/350)", pub_split_ok)
    ck("invented cells 14 tier-3 slots (=700)", inv_split_ok)
    ck("every cell first in exactly 2 scripts (=100 first-trials at even dealing)",
       set(firsts.values()) == {2}, f"distinct={sorted(set(firsts.values()))}")
    ck("90 distinct backbone cells covered (10 cat x 9 struct, incl. EXC)", len(appear) == N_CAT * N_STRUCT,
       f"{len(appear)} cells")
    # EXC (the extremity control, path a) is actually DEALT and reaches the registered per-cell N. It sits
    # in the same 10 backbone categories as MOT, so it should cover 10 cells at 14 slots each (=700/cell).
    exc_cells = {k for k in appear if k[1] == "EXC"}
    exc_slots_ok = bool(exc_cells) and all(appear[k] == 14 for k in exc_cells)
    ck("EXC dealt: 10 EXC cells, each in 14 script-slots (=700)", len(exc_cells) == N_CAT and exc_slots_ok,
       f"{len(exc_cells)} EXC cells")

    # 4. the choice widget round-trips the declared fields
    decl = {d["Field"] for d in flow[0]["EmbeddedData"]}
    widget_writes_ok = True
    for t in range(1, 8):
        q = next((x for x in sqs if x["Payload"].get("DataExportTag") == f"choice_{t}_q"), None)
        js = q["Payload"].get("QuestionJS", "") if q else ""
        if (f"cell{t}_options" not in (q["Payload"]["QuestionText"] if q else "")
                or "'choice_'+T" not in js):
            widget_writes_ok = False
    ck("choice widgets read cellT_options & write choice_T", widget_writes_ok)
    ck("choice_1..7 + choice_1..7_code declared", all(f"choice_{t}" in decl and f"choice_{t}_code" in decl
                                                      for t in range(1, 8)))

    # 5. seeded map respects the published(0-6)/invented(7-9) split the tier logic needs
    ck("map: indices 0-6 published, 7-9 invented",
       all(cats[cat_map[i]]["published"] for i in range(7)) and
       all(not cats[cat_map[i]]["published"] for i in range(7, 10)))

    # 6. SIM two-placement: each SIM cell split 7 clone_HF + 7 clone_HD (Survey 1) - the
    #    gap judge B found. (This check compares emitted placements, NOT the generator default.)
    sim_pl = collections.Counter()
    for sid, cells in parsed.items():
        for t in range(1, 8):
            if cells[t]["structure"] == "SIM":
                sim_pl[(cells[t]["category"], cells[t].get("sim_placement"))] += 1
    sim_cats = {k[0] for k in sim_pl}
    sim_ok = bool(sim_cats) and all(sim_pl[(c, "clone_HF")] == 7 and sim_pl[(c, "clone_HD")] == 7
                                    for c in sim_cats)
    ck("SIM cells split 7 clone_HF + 7 clone_HD per category", sim_ok,
       f"{len(sim_cats)} SIM categories")

    # 7. phantom (PHT) carries an unavailable option in its rendered option JSON (judge C: else the
    #    phantom renders selectable and the manipulation breaks)
    pht_total = pht_unavail = 0
    for sid, cells in parsed.items():
        for t in range(1, 8):
            if cells[t]["structure"] == "PHT":
                pht_total += 1
                if any(o.get("available") is False for o in json.loads(cells[t]["options"])):
                    pht_unavail += 1
    ck("every PHT cell carries an unavailable (phantom) option", pht_total > 0 and pht_unavail == pht_total,
       f"{pht_unavail}/{pht_total}")

    # 8. attention check present, forced, pass key recorded & matches (judges B/C: RR fidelity)
    attn = next((q for q in sqs if q["Payload"].get("DataExportTag") == "attention_1"), None)
    attn_force = bool(attn) and attn["Payload"]["Validation"]["Settings"].get("ForceResponse") == "ON"
    key = mapping.get("attention_1_correct")
    attn_key_ok = bool(attn) and key and len(attn["Payload"]["Choices"]) == key and \
        attn["Payload"]["Choices"][str(key)]["Display"] == mapping.get("attention_1_correct_label")
    ck("attention check present, forced, pass key recorded & matches", bool(attn and attn_force and attn_key_ok),
       f"force={attn_force} key={key}={mapping.get('attention_1_correct_label')}")

    # 9. a PageTimer in every one of the 7 choice blocks (the 3s speeder floor is export-computable)
    qtype = {q["PrimaryAttribute"]: q["Payload"].get("QuestionType") for q in sqs}
    choice_blocks = [b for b in bl_blocks if str(b.get("Description", "")).startswith("Choice ")]
    timers_ok = len(choice_blocks) == 7 and all(
        any(qtype.get(el.get("QuestionID")) == "Timing" for el in b.get("BlockElements", []))
        for b in choice_blocks)
    ck("PageTimer in every choice block (speeder floor computable)", timers_ok, f"{len(choice_blocks)} choice blocks")

    # 10. consent widget actually SETS the embedded `consent` field the decline branch keys on
    consent_q = next((q for q in sqs if q["Payload"].get("DataExportTag") == "consent_q"), None)
    consent_sets = bool(consent_q) and "ed('consent'" in consent_q["Payload"].get("QuestionJS", "")
    ck("consent widget sets embedded `consent` (decline branch works)", consent_sets)

    # ---- report ----
    w = max(len(n) for n, _, _ in checks)
    print("== qsf_selftest.py : reconstruct the design from the emitted .qsf ==")
    allok = True
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n:<{w}}  {d}")
        allok &= ok
    print(f"-- {sum(1 for _, ok, _ in checks if ok)}/{len(checks)} checks pass --")
    print("RESULT:", ("DESIGN COMBINATORICS + EXCLUSIONS + WIDGET WIRING VERIFIED OFFLINE "
                      "(a live Qualtrics import and click-through is still required)."
                      if allok else "DESIGN CORRUPTION - fix the generator."))
    sys.exit(0 if allok else 1)

if __name__ == "__main__":
    main()
