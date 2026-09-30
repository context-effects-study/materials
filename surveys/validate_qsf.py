#!/usr/bin/env python3
"""validate_qsf.py: check a survey file against the Qualtrics import rules before it is imported.

Rules 1 to 8 are the conditions under which Qualtrics rejects an import; rules 9 to 12 protect the data
(every choice field is recorded, the completion redirect is present, the consent text and completion code
are not placeholders). A placeholder failure on rule 11 is expected for the deposited files: the real
consent text and completion code are added at launch, and this check refuses the file until then.

Run: python surveys/validate_qsf.py                       (checks surveys/out/backbone.qsf)
     python surveys/validate_qsf.py surveys/out/survey2_sim.qsf
Exit 0 when every rule passes.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(HERE, "out", "backbone.qsf")
ID_RE = re.compile(r"^(SV|RS|BL)_[A-Za-z0-9]{15}$")
DEFAULT_TAG_RE = re.compile(r"^Q\d+$")
PLACEHOLDER_MARKERS = ["PLACEHOLDER-CONSENT", "REPLACE_COMPLETION_CODE", "REPLACE-ME",
                       "[CALIB", "PLACEHOLDER_STIMULUS", "TODO", "FIXME"]

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    qsf = json.load(open(path, encoding="utf-8"))
    els = qsf["SurveyElements"]
    results = []                                          # (rule, ok, detail)
    def check(rule, ok, detail=""):
        results.append((rule, bool(ok), detail))

    by_el = lambda name: [e for e in els if e["Element"] == name]
    bl = by_el("BL")[0]["Payload"]
    fl = by_el("FL")[0]["Payload"]
    flow = fl["Flow"]
    sqs = by_el("SQ")
    qc = by_el("QC")[0]

    # Rule 1: BL Payload is a dict keyed by stringified indices
    check("1 BL payload is a dict", isinstance(bl, dict) and all(k.isdigit() for k in bl),
          f"{len(bl)} blocks")

    # Rule 2: flow block entries use Type "Standard"
    def walk(fls):
        for e in fls:
            yield e
            if isinstance(e.get("Flow"), list):
                yield from walk(e["Flow"])
    allflow = list(walk(flow))
    block_runs = [e for e in allflow if "ID" in e and str(e.get("ID", "")).startswith("BL_")]
    check("2 flow block entries Type=Standard", all(e["Type"] == "Standard" for e in block_runs),
          f"{len(block_runs)} block runs")

    # Rule 3: ID formats SV_/RS_/BL_ + 15 alnum
    ids = [qsf["SurveyEntry"]["SurveyID"]]
    ids += [by_el("RS")[0]["PrimaryAttribute"]]
    ids += [b["ID"] for b in bl.values()]
    bad = [i for i in ids if not ID_RE.match(i)]
    check("3 ID formats (SV/RS/BL + 15 alnum)", not bad, f"bad={bad[:3]}" if bad else f"{len(ids)} ids ok")

    # Rule 4: branch logic mirrors UI export (no stray keys at If level; _HiddenExpression present)
    branches = [e for e in allflow if e["Type"] == "Branch"]
    b_ok, b_detail = True, f"{len(branches)} branch(es)"
    for br in branches:
        ifobj = br["BranchLogic"]["0"]["0"]
        if set(ifobj) - {"LogicType", "LeftOperand", "Operator", "RightOperand",
                         "_HiddenExpression", "Type", "Description"}:
            b_ok = False; b_detail = f"stray keys: {set(ifobj)}"
        if "Conjuction" in br["BranchLogic"]["0"] or ifobj.get("_HiddenExpression") is not False:
            b_ok = False; b_detail = "Conjuction present or _HiddenExpression!=false"
    check("4 branch logic mirrors UI export", b_ok, b_detail)

    # Rule 5: default ending bare EndSurvey (no Options); redirect ending carries Options
    ends = [e for e in allflow if e["Type"] == "EndSurvey"]
    bare = [e for e in ends if "Options" not in e]
    redir = [e for e in ends if e.get("EndingType") == "Advanced"]
    check("5 endings: >=1 bare + redirect carries Options", bare and all(
          e["Options"].get("SurveyTermination") == "Redirect" for e in redir),
          f"{len(bare)} bare, {len(redir)} redirect")

    # Rule 6: every flow element unique FlowID; FL_1 reserved for root
    fids = [e["FlowID"] for e in allflow]
    check("6 unique FlowIDs, none is FL_1", len(fids) == len(set(fids)) and "FL_1" not in fids
          and fl["FlowID"] == "FL_1", f"{len(fids)} flow elements")

    # Rule 7: a Trash block exists
    check("7 Trash block present", any(b.get("Type") == "Trash" for b in bl.values()))

    # Rule 8: QC count == real question count
    nq = len(sqs)
    check("8 QC count == #questions", qc["SecondaryAttribute"] == str(nq),
          f"QC={qc['SecondaryAttribute']} actual={nq}")

    # Rule 9: declare every embedded-data field up front; nothing set-only without a declaration
    first = flow[0]
    declared = set()
    if first["Type"] == "EmbeddedData":
        declared = {d["Field"] for d in first["EmbeddedData"]}
    set_fields = set()
    for e in allflow:
        if e["Type"] == "EmbeddedData" and e is not first:
            for d in e["EmbeddedData"]:
                set_fields.add(d["Field"])
    # fields written by the choice widget JS (setEmbeddedData) must also be declared. The widget writes
    # `<field>`+T where T is the trial index; expand over the ACTUAL trial count (count of choice_*_q
    # questions), not a hardcoded 7 - surveys vary (backbone/SIM = 7 trials, format/price-free = 3).
    n_trials = sum(1 for q in sqs if re.match(r"choice_\d+_q$", q["Payload"].get("DataExportTag", "")))
    js_fields = set()
    for q in sqs:
        js = q["Payload"].get("QuestionJS", "")
        for m in re.findall(r"(?:setEmbeddedData|ed)\(\s*'([^']+)'\s*\+\s*T", js):
            js_fields |= {f"{m}{t}" for t in range(1, n_trials + 1)}   # e.g. choice_ -> choice_1..K
    undeclared = (set_fields | js_fields) - declared
    check("9 all embedded-data fields declared up front", first["Type"] == "EmbeddedData" and not undeclared,
          f"undeclared={sorted(undeclared)[:5]}" if undeclared else f"{len(declared)} declared")

    # Rule 10: export tags unique + semantic (no duplicates; no default Q<number> on data-bearing)
    tags = [q["Payload"].get("DataExportTag", "") for q in sqs]
    dups = sorted({t for t in tags if tags.count(t) > 1})
    defaults = [t for t in tags if DEFAULT_TAG_RE.match(t)]
    check("10 export tags unique & semantic", not dups and not defaults,
          f"dups={dups} defaults={defaults}" if (dups or defaults) else f"{len(tags)} tags ok")

    # Rule 11: no placeholder strings anywhere (consent / completion / stimulus)
    blob = json.dumps(qsf, ensure_ascii=False)
    hits = sorted({m for m in PLACEHOLDER_MARKERS if m in blob})
    check("11 no placeholder strings (LAUNCH GUARD)", not hits,
          f"present={hits} (expected until consent+code supplied)" if hits else "clean")

    # Rule 12: structural closure
    q_in_blocks = []
    content_blocks = []
    for b in bl.values():
        if b.get("Type") == "Trash":
            continue
        qids = [el["QuestionID"] for el in b.get("BlockElements", []) if el.get("Type") == "Question"]
        q_in_blocks += qids
        content_blocks.append(b["ID"])
    all_qids = {q["PrimaryAttribute"] for q in sqs}
    placed_once = (sorted(q_in_blocks) == sorted(set(q_in_blocks)) and set(q_in_blocks) == all_qids)
    flow_block_ids = [e["ID"] for e in block_runs]
    blocks_exist = all(i in {b["ID"] for b in bl.values()} for i in flow_block_ids)
    content_refd_once = sorted(flow_block_ids) == sorted(content_blocks)
    check("12 structural closure (Q in 1 block; content block in flow once; refs exist)",
          placed_once and blocks_exist and content_refd_once,
          f"placed_once={placed_once} refs_exist={blocks_exist} refd_once={content_refd_once}")

    # Rule 13: per-question-type payload shape matches the real Qualtrics importer (the ESDEF10 family).
    # ROOT CAUSE we hit on this batch (2026-06-13, verified against the live importer): a Meta/Browser
    # question whose choices lacked "TextEntry": 1 (and that carried a spurious ChoiceOrder/Validation,
    # and lacked QuestionText_Unsafe) was REJECTED with QualtricsErrorCode ESDEF10 "Data validation
    # failure" (CS_5.2 / HTTP 500), even though every other element imported cleanly and our internal
    # rules 1-12 all passed. The validator agreed with itself but DISAGREED with the importer; that gap
    # is exactly what this rule closes. A real UI Meta export: every Choice has TextEntry=1, has
    # QuestionText_Unsafe, and has NO ChoiceOrder and NO Validation. We assert that shape, plus the
    # minimal required-field set every SQ payload needs, so a future drift fails HERE, not at upload.
    REQUIRED_SQ_KEYS = {"QuestionType", "Selector", "QuestionID", "DataExportTag",
                        "Configuration", "DataVisibility", "Language"}
    r13_problems = []
    for e in sqs:
        p = e["Payload"]
        qid = p.get("QuestionID", "?")
        qt, sel = p.get("QuestionType"), p.get("Selector")
        missing = REQUIRED_SQ_KEYS - set(p)
        if missing:
            r13_problems.append(f"{qid}({qt}): missing {sorted(missing)}")
        if qt == "Meta":
            choices = p.get("Choices", {})
            if not choices:
                r13_problems.append(f"{qid}(Meta): no Choices")
            bad_te = [k for k, c in choices.items() if c.get("TextEntry") != 1]
            if bad_te:
                r13_problems.append(f"{qid}(Meta): choices missing TextEntry=1 -> {bad_te[:3]} "
                                    f"(this is the ESDEF10 trigger)")
            if "QuestionText_Unsafe" not in p:
                r13_problems.append(f"{qid}(Meta): missing QuestionText_Unsafe")
            if "ChoiceOrder" in p:
                r13_problems.append(f"{qid}(Meta): has ChoiceOrder (a real Meta export has none)")
            if "Validation" in p:
                r13_problems.append(f"{qid}(Meta): has Validation (a real Meta export has none)")
        # MC/Matrix questions must carry ChoiceOrder so option ordering survives import.
        if qt in ("MC", "Matrix") and p.get("Choices") and "ChoiceOrder" not in p:
            r13_problems.append(f"{qid}({qt}): has Choices but no ChoiceOrder")
    check("13 question payload shape matches importer (ESDEF10 family)", not r13_problems,
          "; ".join(r13_problems[:4]) if r13_problems else f"{len(sqs)} questions shape-ok")

    # Rule 14: total BlockRandomizer setter children must stay under the Qualtrics importer cap.
    # SECOND ESDEF10 ROOT CAUSE on this batch (2026-06-13, measured against the live importer): a flow
    # whose BlockRandomizer dispenses MORE THAN ~2,500 EmbeddedData-setter children is REJECTED with
    # ESDEF10, regardless of nesting (the importer counts TOTAL randomizer children across the whole
    # flow, not per-randomizer; 4x700 and 7x400 nested both failed exactly like one flat 2,800).
    # Measured: 2,000 and 2,400 import; 2,600 and 2,800 fail -> the safe ceiling is 2,400. The three
    # 2,800-script surveys (pictures/words/price-free) hit this; backbone (180), calibration, and
    # similarity (1,000) are safe. This is a HARD importer limit, not a payload-byte limit (even=off
    # at 2,800 still failed). An earlier design assumed M setter
    # children import at any M; at M>2,400 that assumption breaks and the dispensing mechanism needs a
    # decided by the authors redesign (move the script table into JS-read embedded data, or reduce distinct
    # scripts). Until then a >2,400 production file will NOT import; this rule fails it here, loudly.
    RANDOMIZER_CHILD_CAP = 2400
    rand_children = 0
    for e in allflow:
        if e["Type"] == "BlockRandomizer":
            rand_children += sum(1 for c in e.get("Flow", []) if c.get("Type") == "EmbeddedData")
    check("14 randomizer setter children <= importer cap (2400)", rand_children <= RANDOMIZER_CHILD_CAP,
          f"{rand_children} setter children" + ("" if rand_children <= RANDOMIZER_CHILD_CAP
              else f" EXCEEDS cap {RANDOMIZER_CHILD_CAP} -> will fail import with ESDEF10"))

    # ---- report ----
    width = max(len(r) for r, _, _ in results)
    print(f"== validate_qsf.py : {os.path.basename(path)} ==")
    hard_fail = False
    for rule, ok, detail in results:
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}] {rule:<{width}}  {detail}")
        if not ok and not rule.startswith("11"):
            hard_fail = True
    n_pass = sum(1 for _, ok, _ in results if ok)
    print(f"-- {n_pass}/{len(results)} rules pass --")
    placeholder_only = (not hard_fail) and any(not ok and r.startswith("11") for r, ok, _ in results)
    if hard_fail:
        print("RESULT: HARD FAIL - do NOT import.")
        sys.exit(1)
    if placeholder_only:
        print("RESULT: STRUCTURE OK - only the rule-11 LAUNCH GUARD is open (supply real consent + "
              "completion code, then re-validate before the live import check).")
        sys.exit(0)
    print("RESULT: ALL RULES PASS - ready for the live import-and-click-through check.")
    sys.exit(0)

if __name__ == "__main__":
    main()
