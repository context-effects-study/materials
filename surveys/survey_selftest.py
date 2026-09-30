"""survey_selftest.py: check that the similarity, format and price-free surveys carry the balanced deals.

For the similarity survey it parses the script setters from the file and re-runs deal.py's balance proofs
on them. For the three surveys that take their scripts from the assignment service, it checks that each
survey file calls the service correctly and that the service's bundled scripts (built by
surveys/assign_worker/build_worker_data.py) carry the same balanced deal and resolve to real stimuli. It
also reads a synthetic export of each survey through analysis/ingest.py.

Run: python surveys/assign_worker/build_worker_data.py
     python surveys/survey_selftest.py
"""
import base64, collections, gzip, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "analysis"))  # ingest.py
import deal
import ingest as I

OUT = os.path.join(HERE, "out")
WORKER_SRC = os.path.abspath(os.path.join(HERE, "assign_worker", "src"))

def parse_setters(qsf_path):
    qsf = json.load(open(qsf_path, encoding="utf-8"))
    flow = next(e for e in qsf["SurveyElements"] if e["Element"] == "FL")["Payload"]["Flow"]
    rnd = next(e for e in flow if e["Type"] == "BlockRandomizer")
    scripts = []
    for s in rnd["Flow"]:
        kv = {d["Field"]: d["Value"] for d in s["EmbeddedData"]}
        k = sum(1 for key in kv if key.startswith("cell") and key.endswith("_category"))
        cells = [{"category": kv[f"cell{t}_category"], "structure": kv[f"cell{t}_structure"],
                  "tier": int(kv[f"cell{t}_tier"]), "sim_placement": kv.get(f"cell{t}_sim_placement", "NA"),
                  "format": kv.get(f"cell{t}_format", "numbers"),
                  "stimulus": kv[f"cell{t}_stimulus"], "order": kv[f"cell{t}_order"],
                  "image": kv.get(f"cell{t}_image", ""),
                  "options": kv[f"cell{t}_options"]} for t in range(1, k + 1)]
        scripts.append(cells)
    return rnd, scripts

def load_worker_arm(arm):
    """Decode one arm's bundled script table from src/scripts_data.js exactly as the Worker does
    (gzip+base64 -> JSON array of flat field-dicts), and reshape each script into the same cell list
    parse_setters returns, so the SAME balance proofs run on the Worker's data."""
    js = open(os.path.join(WORKER_SRC, "scripts_data.js"), encoding="utf-8").read()
    # the bundle is `export const ARMS_GZ_B64 = { "arm": "b64", ... };` - pull this arm's base64 string.
    # Anchor inside the ARMS_GZ_B64 object (the same arm key also appears in MANIFEST earlier in the file),
    # then take the OPENING quote of the value and its matching CLOSING quote (base64 has no quotes inside
    # it, so a simple quote-to-quote scan is safe and exact).
    arms_start = js.index("ARMS_GZ_B64")
    marker = json.dumps(arm) + ":"
    i = js.index(marker, arms_start) + len(marker)
    q0 = js.index('"', i)
    q1 = js.index('"', q0 + 1)
    b64 = js[q0 + 1:q1]
    payloads = json.loads(gzip.decompress(base64.b64decode(b64)).decode("utf-8"))
    scripts = []
    for kv in payloads:
        k = sum(1 for key in kv if key.startswith("cell") and key.endswith("_category"))
        cells = [{"category": kv[f"cell{t}_category"], "structure": kv[f"cell{t}_structure"],
                  "tier": int(kv[f"cell{t}_tier"]), "sim_placement": kv.get(f"cell{t}_sim_placement", "NA"),
                  "format": kv.get(f"cell{t}_format", "numbers"),
                  "stimulus": kv[f"cell{t}_stimulus"], "order": kv[f"cell{t}_order"],
                  "image": kv.get(f"cell{t}_image", ""),
                  "options": kv[f"cell{t}_options"]} for t in range(1, k + 1)]
        scripts.append(cells)
    return scripts

def webservice_el(qsf_path):
    """Return the WebService flow element from a QSF (or None), whether a BlockRandomizer is absent, and
    the top-level flow (so the worker-SPOF guard branch + ordering can be checked)."""
    qsf = json.load(open(qsf_path, encoding="utf-8"))
    flow = next(e for e in qsf["SurveyElements"] if e["Element"] == "FL")["Payload"]["Flow"]
    ws = next((e for e in flow if e["Type"] == "WebService"), None)
    no_rnd = not any(e["Type"] == "BlockRandomizer" for e in flow)
    return ws, no_rnd, flow

def cell_resolves(cells, by_id):
    """Every cell's options JSON parses, and its codes match the placement-resolved stimulus record."""
    for c in cells:
        rec = by_id.get(c["stimulus"])
        if rec is None:
            return False
        _, _, opts = I.option_set(rec, c["sim_placement"])
        try:
            oj = json.loads(c["options"])
        except Exception:
            return False
        if {o["code"] for o in oj} != set(opts) or sorted(c["order"].split(",")) != sorted(opts):
            return False
    return True

def main():
    cats, by_cell, pub, inv, pf = deal.load()
    by_id = {r["id"]: r for r in json.load(open(deal.STIM, encoding="utf-8"))["stimuli"]}
    checks = []
    def ck(n, ok, d=""): checks.append((n, bool(ok), d))

    # The fields the choice widget needs the Worker (or randomizer) to provide, per trial.
    WS_FIELDS = ("id", "category", "structure", "tier", "format", "order", "stimulus", "sim_placement",
                 "stem", "options")

    # The one ResponseMap entry whose JSON key differs from the embedded-data field: the worker-SPOF guard
    # maps the Worker's `ok` flag into `assign_ok` (CRIT-WORKER-SPOF). Every OTHER entry stays flat.
    GUARD_MAP = {"key": "ok", "value": "assign_ok"}

    def check_webservice(label, qsf_path, arm, k, picture=False):
        """For a Web-Service arm: assert the QSF has a correct WebService element, no randomizer, and the
        worker-SPOF guard (assign_ok wiring + the screen-out branch before the first choice)."""
        ws, no_rnd, flow = webservice_el(qsf_path)
        ck(f"{label} QSF has WebService element + NO randomizer (importer-cap fix)", bool(ws) and no_rnd,
           "" if ws and no_rnd else "missing WS or stray randomizer")
        if not ws:
            return
        url_ok = ws.get("URL", "").endswith("/assign") and ws.get("Method") == "GET"
        arm_ok = any(p.get("key") == "arm" and p.get("value") == arm for p in ws.get("RequestParams", []))
        ck(f"{label} WebService URL=/assign GET, arm={arm}", url_ok and arm_ok,
           f"url={ws.get('URL')} params={ws.get('RequestParams')}")
        rmap = ws.get("ResponseMap", [])
        mapped = {r["value"] for r in rmap}
        need = {"script_id"} | {f"cell{t}_{s}" for t in range(1, k + 1) for s in WS_FIELDS}
        if picture:
            need |= {f"cell{t}_image" for t in range(1, k + 1)}
        ck(f"{label} ResponseMap covers every field the widget reads", need <= mapped,
           f"missing={sorted(need - mapped)[:4]}" if not need <= mapped else f"{len(mapped)} fields mapped")
        # ResponseMap is flat (key==value) for every entry EXCEPT the one worker-SPOF guard entry (ok->assign_ok).
        non_flat = [r for r in rmap if r["key"] != r["value"]]
        flat_ok = non_flat == [GUARD_MAP]
        ck(f"{label} ResponseMap flat except the ok->assign_ok guard", flat_ok,
           f"non-flat entries: {non_flat}" if not flat_ok else "")

        # ---- worker-SPOF guard (CRIT-WORKER-SPOF) ----
        # (1) the Worker's `ok` flag is wired into the `assign_ok` embedded-data field.
        ck(f"{label} ResponseMap maps ok -> assign_ok (the guard flag)", GUARD_MAP in rmap)
        # (2) a Branch tests assign_ok != "true" and sits AFTER the WebService call and BEFORE the first
        #     choice block, and routes to a screen-out that ends WITHOUT a completion code (a bare EndSurvey,
        #     no Redirect Options), so a failed assignment can never reach an empty-trial choice page.
        types = [e["Type"] for e in flow]
        ws_i = types.index("WebService")
        first_choice_i = next((i for i, e in enumerate(flow) if e["Type"] == "Standard"
                               and i > ws_i), None)
        guard = None
        for i, e in enumerate(flow):
            if e["Type"] != "Branch":
                continue
            lo = e.get("BranchLogic", {}).get("0", {}).get("0", {})
            if lo.get("LeftOperand") == "assign_ok" and lo.get("Operator") == "NotEqualTo" \
                    and lo.get("RightOperand") == "true":
                guard = (i, e)
        guard_after_ws = bool(guard) and guard[0] > ws_i
        guard_before_choice = bool(guard) and first_choice_i is not None and guard[0] < first_choice_i
        ck(f"{label} screen-out branch (assign_ok!=true) AFTER WebService, BEFORE first choice",
           guard_after_ws and guard_before_choice,
           f"ws@{ws_i} guard@{guard[0] if guard else None} firstChoice@{first_choice_i}")
        # the branch's flow ends with a bare EndSurvey (no Redirect/Options) = NO completion code paid.
        ends_no_code = False
        if guard:
            gflow = guard[1].get("Flow", [])
            end = next((e for e in gflow if e["Type"] == "EndSurvey"), None)
            ends_no_code = bool(end) and "Options" not in end
        ck(f"{label} screen-out ends with a bare EndSurvey (NO completion code)", ends_no_code)

    # ---- Survey 4 (price-free) - WEB SERVICE arm ----
    check_webservice("S4", os.path.join(OUT, "survey4_pricefree.qsf"), "price-free", 3)
    s4 = load_worker_arm("price-free")
    ck("S4 worker bundle has 2,800 scripts", len(s4) == 2800, f"{len(s4)} scripts")
    fill4 = collections.Counter((c["category"], c["structure"]) for sc in s4 for c in sc)
    ok4, o4 = deal.verify_pricefree(s4, fill4)
    ck("S4 deal balanced (reconstructed from worker bundle)", ok4,
       "; ".join(f"{n}:{'P' if k else 'F'}" for n, k, _ in o4))
    ck("S4 every cell resolves w/ valid option JSON", cell_resolves([c for sc in s4 for c in sc], by_id))

    # ---- Survey 2 (SIM top-up) ----
    rnd2, s2 = parse_setters(os.path.join(OUT, "survey2_sim.qsf"))
    ck("S2 randomizer SubSet=1 + EvenPresentation", rnd2.get("SubSet") == 1 and rnd2.get("EvenPresentation") is True)
    ck("S2 1,000 setters", len(s2) == 1000, f"{len(s2)} setters")
    ck("S2 every trial is SIM", all(c["structure"] == "SIM" for sc in s2 for c in sc))
    fill2 = collections.Counter((c["category"], c["sim_placement"], c["tier"]) for sc in s2 for c in sc)
    appear2 = collections.Counter(c["category"] for sc in s2 for c in sc)
    ok2, o2 = deal.verify_sim(s2, fill2, appear2, pub)
    ck("S2 deal balanced (reconstructed from .qsf)", ok2, "; ".join(f"{n}:{'P' if k else 'F'}" for n, k, _ in o2))
    ck("S2 both placements present", {"clone_HF", "clone_HD"} <= {c["sim_placement"] for sc in s2 for c in sc})
    ck("S2 every cell resolves w/ valid option JSON (placement-correct)",
       cell_resolves([c for sc in s2 for c in sc], by_id))

    # ---- Survey 3 words (format module) - WEB SERVICE arm ----
    check_webservice("S3w", os.path.join(OUT, "survey3_words.qsf"), "words", 3)
    s3 = load_worker_arm("words")
    ck("S3w worker bundle has 2,800 scripts", len(s3) == 2800, f"{len(s3)} scripts")
    ck("S3w every trial format=words & structure in {BIN,FRQ,SOT}",
       all(c["format"] == "words" and c["structure"] in ("BIN", "FRQ", "SOT") for sc in s3 for c in sc))
    fill3 = collections.Counter((c["category"], c["structure"]) for sc in s3 for c in sc)
    appear3 = collections.Counter(c["category"] for sc in s3 for c in sc)
    ok3, o3 = deal.verify_format(s3, fill3, appear3, "words")
    ck("S3w deal balanced (reconstructed from worker bundle)", ok3, "; ".join(f"{n}:{'P' if k else 'F'}" for n, k, _ in o3))
    ck("S3w every cell resolves w/ valid option JSON", cell_resolves([c for sc in s3 for c in sc], by_id))
    # words cards spell the MAGNITUDE (e.g. "seventy"); the scale anchor "out of 100" is deliberately
    # left as a numeral so only the magnitude representation varies across formats (a controlled contrast:
    # numbers "70/100" vs words "seventy out of 100"). So we check for spelled number-words, not "no digits".
    import re as _re
    SPELLED = (r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thir|for|fif|six|"
               r"seven|eigh|nine|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|"
               r"point|dollars|cents|stars)\b")
    sample = json.loads(s3[0][0]["options"])
    words_spelled = all(_re.search(SPELLED, o["html"], _re.I) for o in sample)
    ck("S3w option cards spell the magnitude (words representation)", words_spelled,
       sample[0]["html"][:55] if sample else "")

    # ---- Survey 3 pictures (format module) - WEB SERVICE arm ----
    check_webservice("S3p", os.path.join(OUT, "survey3_pictures.qsf"), "pictures", 3, picture=True)
    sp = load_worker_arm("pictures")
    ck("S3p worker bundle has 2,100 scripts (the hard-drives pictures cells left at the final calibration lock; 3 cats x 3 structs)",
       len(sp) == 2100, f"{len(sp)} scripts")
    ck("S3p every trial format=pictures & structure in {BIN,FRQ,SOT}",
       all(c["format"] == "pictures" and c["structure"] in ("BIN", "FRQ", "SOT") for sc in sp for c in sc))
    fillp = collections.Counter((c["category"], c["structure"]) for sc in sp for c in sc)
    appearp = collections.Counter(c["category"] for sc in sp for c in sc)
    okp, op = deal.verify_format(sp, fillp, appearp, "pictures")
    ck("S3p deal balanced (reconstructed from worker bundle)", okp, "; ".join(f"{n}:{'P' if k else 'F'}" for n, k, _ in op))
    ck("S3p every cell resolves w/ valid option JSON", cell_resolves([c for sc in sp for c in sc], by_id))
    order_ok = label_ok = img_ok = True
    for sc in sp:
        for c in sc:
            rec = by_id[c["stimulus"]]
            pic_opts = (rec.get("format_variants", {}).get("pictures", {}) or {}).get("options") or rec["options"]
            if c["order"].split(",") != [o["code"] for o in pic_opts]:        # canonical (image) order, fixed
                order_ok = False
            oj = json.loads(c["options"])
            if [o["html"] for o in oj] != [f"Option {ch}" for ch in "ABCDEFG"[:len(oj)]]:
                label_ok = False
            if c["image"].rsplit("/", 1)[-1] != c["stimulus"] + ".png":        # image matches the cell's stimulus
                img_ok = False
    ck("S3p option order is the canonical image order (fixed, not shuffled)", order_ok)
    ck("S3p options labelled Option A/B/C", label_ok)
    ck("S3p each cell_image is <stimulus>.png on the host", img_ok,
       sp[0][0]["image"] if sp else "")

    w = max(len(n) for n, _, _ in checks)
    allok = all(ok for _, ok, _ in checks)
    out = ["# Survey 2 & 4 selftest - deals reconstructed from the emitted .qsf",
           "(survey_selftest.py, 2026-06-13. Parses the setters out of each survey's randomizer and re-runs",
           "deal.py's balance proofs on what the FILE contains.)", "", "## Checks", "| check | result | detail |", "|---|---|---|"]
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n:<{w}}  {d}")
        out.append(f"| {n} | {'PASS' if ok else 'FAIL'} | {d} |")
    out += ["", f"## OVERALL: {'ALL SURVEYS (2, 4, 3-words, 3-pictures) CARRY THE BALANCED DEAL' if allok else 'FAILURE'}"]
    open(os.path.join(HERE, "SURVEY_CHECK.md"), "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("RESULT:", "ALL SURVEYS (2, 4, 3-words, 3-pictures) CARRY THE BALANCED DEAL" if allok else "FAILURE")
    sys.exit(0 if allok else 1)

if __name__ == "__main__":
    main()
