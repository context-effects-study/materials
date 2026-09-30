#!/usr/bin/env python3
"""generate_qsf.py: build the numeric backbone survey (Survey 1) as an importable Qualtrics file.

The backbone deals 180 pre-built, balanced participant scripts (surveys/scriptset_180.csv, made by
scriptset_sim.py). Each script is seven choices, one per product category, with no category or structure
repeated. One Qualtrics randomizer with even presentation holds 180 embedded-data setters, one per script,
so the scripts are dispensed evenly as participants arrive, and every design variable of every choice
(category, structure, tier, format, option order, stimulus) is written into the response itself. Each
choice page renders its options from stimuli/stimuli.json through render_shared.py, and a small choice
widget records the chosen option's code. The script index is shuffled with a fixed seed
(SHUFFLE_SEED = "context-fx-backbone-2026"), recorded in the mapping file.

Output: surveys/out/backbone.qsf and surveys/out/backbone_MAPPING.json (the key that decodes an export).
The file carries placeholder consent text and a placeholder completion code; both are filled in at launch
(validate_qsf.py refuses the file until they are).
Manuscript: Method ("Human study") and Table 2.

Run: python surveys/generate_qsf.py
     python surveys/generate_qsf.py --consent-file consent.txt --completion-url <Prolific completion URL>
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, random, string, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Layout: this engine lives at surveys/ in
# the working repository (root two levels up) and at surveys/ in the public deposit (root one level up). The
# root is the nearest ancestor that contains stimuli/; behavior in the working repository tree is unchanged.
def _find_root(start):
    d = start
    for _ in range(4):
        d = os.path.dirname(d)
        if os.path.isdir(os.path.join(d, "stimuli")):
            return d
    return os.path.abspath(os.path.join(start, "..", ".."))
ROOT = _find_root(HERE)
sys.path.insert(0, os.path.dirname(HERE))                       # working repository/engines on path
sys.path.insert(0, os.path.join(ROOT, "stimuli"))               # stimuli/ (enrich, final calibration lock, render_shared in the deposit)
from render_shared import render_value                          # QSF-1: shared with the model arm (run.py)
import enrich                                                   # final calibration lock: the enriched-card renderer + entry_for
STIMULI = os.path.join(ROOT, "stimuli", "stimuli.json")
SCRIPTSET = os.path.join(HERE, "scriptset_180.csv")
OUT_DIR = os.path.join(HERE, "out")

VERSION = "backbone-qsf-1.2"          # 1.2 = captcha-off default + real flow Count (2026-07-01); 1.1 = path a
BUILD_DATE_DEFAULT = "2026-07-01"

# The reCAPTCHA-v2 checkbox question (sq_captcha) is a BUILD FLAG, DEFAULT OFF (deviation D3, executed
# by the authors 2026-07-01 during the live stress test: the visible checkbox challenged real automation and
# adds friction for every real participant, so it was deleted from all six live surveys mid-test; the
# invisible RecaptchaV3 survey option STAYS ON as the bot defense). The OFF default here keeps the next
# regeneration in sync with the live surveys. To restore the checkbox: pass --with-captcha (or set
# INCLUDE_CAPTCHA = True). NOTE: the OFF default awaits the authors' standing confirmation - it is one
# switch to put back.
INCLUDE_CAPTCHA = False

# Flow-ID margin for Properties.Count. Qualtrics uses Count as the flow's ID counter: if it is BELOW an
# existing FL_<n>, the import MIS-COMPILES the flow (branches silently die - the qualtrics-toolkit's
# root-cause #2; the similarity survey shipped Count=200 with FL_1019). Count is now COMPUTED from the
# real max FlowID plus this margin, never hardcoded (stress-test defect D2, fixed 2026-07-01).
FLOW_COUNT_MARGIN = 50
SHUFFLE_SEED = "context-fx-backbone-2026"          # seeded index<->name map; recorded in MAPPING.json
PLACEHOLDER_CONSENT = ("[PLACEHOLDER-CONSENT: replace with the IRB-approved consent text before launch. "
                       "validate_qsf.py fails while this marker is present.]")
PLACEHOLDER_COMPLETION = "https://app.prolific.com/submissions/complete?cc=REPLACE_COMPLETION_CODE"

# ---- seeded ID generation (SV_/RS_/BL_ + EXACTLY 15 alnum) -------------------
_rng = random.Random("backbone-qsf-ids-2026")
def _qid(prefix: str) -> str:
    return prefix + "".join(_rng.choice(string.ascii_letters + string.digits) for _ in range(15))

SID = _qid("SV_")
RSID = _qid("RS_")

# ============================ ELEMENT BUILDERS (ported from build_qsf.py) ========================

def sq_db(qid, tag, html, js, desc):
    """Text/Graphic (descriptive) question; all input handled by custom JS (the choice widget)."""
    payload = {
        "QuestionText": html, "QuestionText_Unsafe": html, "DataExportTag": tag,
        "QuestionType": "DB", "Selector": "TB",
        "Configuration": {"QuestionDescriptionOption": "UseText"},
        "QuestionDescription": desc, "ChoiceOrder": [],
        "Validation": {"Settings": {"Type": "None"}}, "GradingData": [], "Language": [],
        "DataVisibility": {"Private": False, "Hidden": False}, "DefaultChoices": False,
        "NextChoiceId": 4, "NextAnswerId": 1, "QuestionID": qid,
    }
    if js is not None:
        payload["QuestionJS"] = js
    return {"SurveyID": SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}

def sq_mc(qid, tag, text, choices, desc, force=True):
    ch = {str(i + 1): {"Display": c} for i, c in enumerate(choices)}
    order = [str(i + 1) for i in range(len(choices))]
    validation = ({"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}}
                  if force else {"Settings": {"Type": "None"}})
    payload = {
        "QuestionText": text, "QuestionText_Unsafe": text, "DataExportTag": tag,
        "QuestionType": "MC", "Selector": "SAVR", "SubSelector": "TX",
        "Configuration": {"QuestionDescriptionOption": "UseText"}, "QuestionDescription": desc,
        "Choices": ch, "ChoiceOrder": order, "Validation": validation,
        "GradingData": [], "Language": [], "DataVisibility": {"Private": False, "Hidden": False},
        "DefaultChoices": False, "NextChoiceId": len(choices) + 1, "NextAnswerId": 1, "QuestionID": qid,
    }
    return {"SurveyID": SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}

def sq_text(qid, tag, text, desc, content_type=None):
    """Single-line text entry (demographics age). content_type='ValidNumber' adds a numeric check."""
    validation = {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}}
    if content_type:
        validation = {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON",
                                   "Type": "ContentType", "ContentType": content_type}}
    payload = {
        "QuestionText": text, "QuestionText_Unsafe": text, "DataExportTag": tag,
        "QuestionType": "TE", "Selector": "SL", "Configuration": {"QuestionDescriptionOption": "UseText"},
        "QuestionDescription": desc, "Validation": validation, "GradingData": [], "Language": [],
        "DataVisibility": {"Private": False, "Hidden": False}, "DefaultChoices": False,
        "SearchSource": {"AllowFreeResponse": "false"}, "NextChoiceId": 4, "NextAnswerId": 1,
        "QuestionID": qid,
    }
    return {"SurveyID": SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}

def sq_timing(qid, tag, desc):
    """PageTimer question (a standard Qualtrics pattern): timer first in the block, same page as the choice.
    Payload shape matched to real Qualtrics exports - the one new question type that drifted from every real export."""
    payload = {
        "QuestionText": "Timing", "QuestionText_Unsafe": "Timing", "QuestionType": "Timing",
        "Selector": "PageTimer", "DataExportTag": tag,
        "Configuration": {"MaxSeconds": "0", "MinSeconds": "0", "QuestionDescriptionOption": "UseText"},
        "QuestionDescription": desc, "Validation": None, "GradingData": [], "Language": [],
        "DataVisibility": {"Private": False, "Hidden": False}, "DefaultChoices": False,
        "NextChoiceId": 4, "NextAnswerId": 1, "QuestionID": qid,
        "Choices": {"1": {"Display": "First Click"}, "2": {"Display": "Last Click"},
                    "3": {"Display": "Page Submit"}, "4": {"Display": "Click Count"}},
    }
    return {"SurveyID": SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}

def sq_captcha(qid, tag, desc):
    payload = {
        "QuestionText": "Please verify that you are human.", "QuestionType": "Captcha", "Selector": "V2",
        "DataExportTag": tag, "Configuration": {"QuestionDescriptionOption": "UseText"},
        "QuestionDescription": desc, "Validation": {"Settings": {"ForceResponse": "ON", "Type": "None"}},
        "GradingData": [], "Language": [], "DataVisibility": {"Private": False, "Hidden": False},
        "NextChoiceId": 4, "NextAnswerId": 1, "QuestionID": qid,
    }
    return {"SurveyID": SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}

def sq_meta(qid, tag, desc):
    """Meta info (browser/device) question - records the participant's environment.

    ESDEF10 ROOT CAUSE + FIX (2026-06-13, working repository worker, verified against the real Qualtrics
    importer): a Meta/Browser question is the ONLY element shape in these surveys the importer
    rejected with QualtricsErrorCode ESDEF10 "Data validation failure" (CS_5.2 / HTTP 500). Every
    other question type (DB/TB, MC/SAVR, TE/SL, Timing/PageTimer, Captcha/V2) and the flow,
    blocks, randomizer, embedded data, and survey options all import as-is. The Meta question must
    match the real UI export's shape EXACTLY: (a) every Choice carries "TextEntry": 1 (the field
    that tells Qualtrics each meta row is a captured value); (b) it has QuestionText_Unsafe; and
    (c) it must NOT carry a ChoiceOrder or a Validation block (a real Meta export has neither, and
    their presence is what trips the importer's schema validator). Bisected by replacing one
    element at a time into a known-importable UI export until the failure flipped to a 200.
    """
    payload = {
        "QuestionText": "Browser Meta Info", "QuestionText_Unsafe": "Browser Meta Info",
        "QuestionType": "Meta", "Selector": "Browser",
        "DataExportTag": tag, "Configuration": {"QuestionDescriptionOption": "UseText"},
        "QuestionDescription": desc,
        "GradingData": [], "Language": [], "DataVisibility": {"Private": False, "Hidden": False},
        "DefaultChoices": False, "NextChoiceId": 4, "NextAnswerId": 1, "QuestionID": qid,
        "Choices": {"1": {"Display": "Browser", "TextEntry": 1}, "2": {"Display": "Version", "TextEntry": 1},
                    "3": {"Display": "Operating System", "TextEntry": 1},
                    "4": {"Display": "Screen Resolution", "TextEntry": 1},
                    "5": {"Display": "Flash Version", "TextEntry": 1},
                    "6": {"Display": "Java Support", "TextEntry": 1},
                    "7": {"Display": "User Agent", "TextEntry": 1}},
    }
    return {"SurveyID": SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}

def block(bid, desc, qids, btype="Standard", page_breaks=False):
    elems = []
    for i, q in enumerate(qids):
        if page_breaks and i > 0:
            elems.append({"Type": "Page Break"})
        elems.append({"Type": "Question", "QuestionID": q})
    return {"Type": btype, "SubType": "", "Description": desc, "ID": bid, "BlockElements": elems,
            "Options": {"BlockLocking": "false", "RandomizeQuestions": "false", "BlockVisibility": "Expanded"}}

def ed_decl(fields):
    eds = [{"Description": f, "Type": "Custom", "Field": f, "VariableType": "String",
            "DataVisibility": [], "AnalyzeText": False} for f in fields]
    return {"Type": "EmbeddedData", "FlowID": None, "EmbeddedData": eds}

def ed_set(field, value):
    return {"Type": "EmbeddedData", "FlowID": None,
            "EmbeddedData": [{"Description": field, "Type": "Custom", "Field": field,
                              "VariableType": "String", "DataVisibility": [], "AnalyzeText": False,
                              "Value": value}]}

def ed_set_many(pairs):
    """ONE EmbeddedData flow element setting many (field, value) pairs - a script setter child."""
    eds = [{"Description": f, "Type": "Custom", "Field": f, "VariableType": "String",
            "DataVisibility": [], "AnalyzeText": False, "Value": v} for f, v in pairs]
    return {"Type": "EmbeddedData", "FlowID": None, "EmbeddedData": eds}

def flow_block(bid):
    # Flow entries that run a block use Type "Standard" (Type "Block" fails the import; rule 2).
    return {"Type": "Standard", "ID": bid, "FlowID": None, "Autofill": []}

def flow_branch_decline(end_flow):
    return {
        "Type": "Branch", "FlowID": None, "Description": "Declined consent",
        "BranchLogic": {"0": {"0": {
            "LogicType": "EmbeddedField", "LeftOperand": "consent", "Operator": "NotEqualTo",
            "RightOperand": "yes", "_HiddenExpression": False, "Type": "Expression",
            "Description": "<span class=\"ConjDesc\">If</span>  <span class=\"LeftOpDesc\">consent</span> <span class=\"OpDesc\">Is Not Equal to</span> <span class=\"RightOpDesc\"> yes </span>",
        }, "Type": "If"}, "Type": "BooleanExpression"},
        "Flow": [end_flow],
    }

def flow_end(redirect_url=None):
    if redirect_url:
        return {"Type": "EndSurvey", "FlowID": None, "EndingType": "Advanced",
                "Options": {"Advanced": "true", "SurveyTermination": "Redirect", "EOSRedirectURL": redirect_url}}
    return {"Type": "EndSurvey", "FlowID": None}          # bare ending (rule 5: no Options)

def flow_branch_assign_fail(fail_flow):
    """Worker-SPOF guard (CRIT-WORKER-SPOF): a Branch placed AFTER the Web Service assignment call and
    BEFORE the first choice block. It fires when the assignment did NOT succeed and routes the participant
    to a graceful screen-out (`fail_flow`: a message block + a bare EndSurvey with no completion code), so
    a failed assignment can NEVER let a participant answer empty trials.

    The test is a SINGLE condition on `assign_ok` (Is Not Equal To "true"), which catches every failure
    mode in one expression (and so stays inside validate_qsf rule 4's single-If branch shape):
      - Worker down / slow / unreachable: the Web Service call writes nothing, so `assign_ok` keeps its
        up-front empty default "" -> "" != "true" -> screen out.
      - Worker reachable but errors (returns {"ok": false, ...}): the ResponseMap stores "false" into
        `assign_ok` -> "false" != "true" -> screen out.
      - Worker succeeds (returns {"ok": true, "script_id": ..., cell fields ...}): `assign_ok` = "true"
        -> the participant proceeds into a fully-populated survey.
    `assign_ok` is pre-seeded to "" up front (so the test is reliable even if the call never fires) and is
    set from the Worker's `ok` flag via the Web Service ResponseMap. script_id and the trial fields ride the
    same response, so a "true" here means the trial fields are present too."""
    return {
        "Type": "Branch", "FlowID": None, "Description": "Assignment failed (worker unavailable/error)",
        "BranchLogic": {"0": {"0": {
            "LogicType": "EmbeddedField", "LeftOperand": "assign_ok", "Operator": "NotEqualTo",
            "RightOperand": "true", "_HiddenExpression": False, "Type": "Expression",
            "Description": "<span class=\"ConjDesc\">If</span>  <span class=\"LeftOpDesc\">assign_ok</span> <span class=\"OpDesc\">Is Not Equal to</span> <span class=\"RightOpDesc\"> true </span>",
        }, "Type": "If"}, "Type": "BooleanExpression"},
        "Flow": fail_flow,
    }

def flow_randomizer(children, subset=1, even=True):
    """BlockRandomizer dispensing SubSet of M children with EvenPresentation (a standard Qualtrics pattern)."""
    return {"Type": "BlockRandomizer", "FlowID": None, "SubSet": subset,
            "EvenPresentation": even, "Flow": children}

def flow_webservice(url, response_fields, arm, extra_map=None):
    """Web Service flow element (Qualtrics calls an external URL at survey start and stores the JSON
    response into embedded data). Used for the three large arms whose ~2,800 pre-built scripts exceed the
    importer's randomizer-child cap (ESDEF10): instead of a BlockRandomizer over 2,800 EmbeddedData
    setters, ONE Web Service call to the assignment Worker (GET <url>?arm=<arm>) returns the assigned
    script's flat field payload, and ResponseMap stores each field into embedded data. The Worker does the
    same even-presentation balanced deal that the randomizer did, so the registered design is preserved;
    only WHERE assignment happens changes. Shape matches the API spec's WebServiceFlowElement example exactly.

    response_fields: the embedded-data field names to pull from the JSON response (the Worker returns a
    FLAT object whose keys ARE these field names, so each ResponseMap entry's key == its value).
    extra_map: optional list of {"key", "value"} ResponseMap entries whose JSON key differs from the
    embedded-data field (used for the worker-SPOF guard: the Worker's `ok` flag -> the `assign_ok` field)."""
    return {
        "Type": "WebService", "FlowID": None, "URL": url, "Method": "GET",
        "RequestParams": [{"key": "arm", "value": arm}],
        "EditBodyParams": [], "Body": [], "ContentType": "application/x-www-form-urlencoded",
        "Headers": [], "FireAndForget": False, "StringifyValues": True,
        # key = JSON path in the (flat) response; value = embedded-data field to store it in
        "ResponseMap": [{"key": f, "value": f} for f in response_fields] + (extra_map or []),
    }

def assign_flow_ids(flow, counter):
    """Assign FL_2.. depth-first; RETURNS the highest FlowID number used, so the caller can set
    Properties.Count >= max FL (the root-cause-#2 guard; see FLOW_COUNT_MARGIN)."""
    for el in flow:
        counter[0] += 1
        el["FlowID"] = f"FL_{counter[0]}"
        if "Flow" in el and isinstance(el["Flow"], list):
            assign_flow_ids(el["Flow"], counter)
    return counter[0]

# ============================ DESIGN RESOLUTION =================================================

def load_design():
    S = json.load(open(STIMULI, encoding="utf-8"))
    cats = {c["id"]: c for c in S["categories"]}
    stim = S["stimuli"]
    is_backbone = lambda v: (v.get("price_free_variant_of") is None) and (not v.get("price_free"))
    pub = sorted(c for c, v in cats.items() if v.get("published") and is_backbone(v))
    inv = sorted(c for c, v in cats.items() if (not v.get("published")) and is_backbone(v))
    structs = sorted({r["structure"] for r in stim if r["category"] in set(pub) | set(inv)})
    # 9 backbone structures as of path a Wave 2 (2026-06-13): the 8 originals plus EXC, the extremity
    # control (contract v1.1). The scriptset (scriptset_180.csv) and build_index_map now DEAL all 9.
    assert len(pub) == 7 and len(inv) == 3 and len(structs) == 9, (len(pub), len(inv), len(structs))
    by_cell = {(r["category"], r["structure"], r["memorization_tier"]): r for r in stim}
    return cats, by_cell, pub, inv, structs

def build_index_map(pub, inv, structs):
    """The seeded shuffle: published->0..6, invented->7..9, structures->0..8 (recorded for the manuscript).
    Path a Wave 2 (2026-06-13): EXC (the extremity control) is now DEALT alongside the original 8
    structures. The scriptset_180.csv was rebuilt for the 9-structure backbone (structure index 0..8), so
    the index->code map covers all 9. The shuffle is seeded and recorded in MAPPING.json, so the abstract
    structure indices in scriptset_180.csv resolve to the same real codes every build."""
    rng = random.Random(SHUFFLE_SEED)
    p, q = pub[:], inv[:]
    s = structs[:]                                       # all 9 backbone structures, incl. EXC (path a)
    rng.shuffle(p); rng.shuffle(q); rng.shuffle(s)
    cat_idx_to_name = {i: p[i] for i in range(7)}
    cat_idx_to_name.update({7 + j: q[j] for j in range(3)})
    str_idx_to_code = {i: s[i] for i in range(len(s))}
    return cat_idx_to_name, str_idx_to_code

_ENRICHMENT_CACHE = None

def enrichment_block():
    """The canonical enrichment block from stimuli.json (final calibration lock, 2026-07-02). Lazy-loaded once."""
    global _ENRICHMENT_CACHE
    if _ENRICHMENT_CACHE is None:
        _ENRICHMENT_CACHE = json.load(open(STIMULI, encoding="utf-8")).get("enrichment") or {}
    return _ENRICHMENT_CACHE

def render_option_html(rec, opt, cat_meta):
    """One option as a compact HTML card body. In the final calibration enrichment scope (adjustable tiers,
    the structures sharing the calibrated binary control) the card is the ENRICHED product-page
    blurb: bold model name, then per attribute the canonical render_value string (QSF-1,
    verbatim) followed by its plain-language qualifier - the form the terminal calibration
    fielded. Outside the scope (tier-1, MOT/EXC, price-free categories) the card stays the
    sparse one-line-per-attribute render, unchanged. Both forms share render_value with the
    model arm, so the value text can never drift between humans and models."""
    entry = enrich.entry_for(enrichment_block(), rec, opt)
    if entry is not None:
        return enrich.option_numbers_html(opt, cat_meta, entry)
    lines = []
    for a in cat_meta["attributes"]:
        n = a["name"]
        if n in opt["attrs"]:
            lines.append(f"<div class='cfx-attr'>{render_value(n, a.get('unit', ''), opt['attrs'][n])}</div>")
    return "".join(lines)

def script_cells(script_rows, cat_map, str_map, by_cell, cats):
    """Resolve one script's 7 rows -> per-cell field pairs (the setter payload)."""
    sid = script_rows[0]["script_id"]
    rng = random.Random(SHUFFLE_SEED + f"-order-{sid}")
    pairs = [("script_id", str(sid))]
    for row in sorted(script_rows, key=lambda r: r["position"]):
        t = row["position"]
        ci, si, tier = int(row["category"]), int(row["structure"]), int(row["tier"])
        cat, struct = cat_map[ci], str_map[si]
        rec = by_cell.get((cat, struct, tier))
        if rec is None:
            raise SystemExit(f"UNRESOLVED CELL script {sid} pos {t}: ({cat},{struct},t{tier}) "
                             f"- check stimuli.json coverage")
        # SIM two-placement (Survey 1: 50/50 clone-HF vs clone-HD). Copy split (scripts
        # 1-90 = copy 0, 91-180 = copy 1, per scriptset_sim.py v3; was 1-80/81-160 at 160 scripts) puts
        # each SIM cell in exactly 7 copy-0 and 7 copy-1 scripts -> 7/7 per placement per cell, balanced
        # by construction (qsf_selftest asserts it). clone_HD swaps in the placement-variant option set;
        # clone_HF is the default.
        placement = "NA"
        opt_src = rec["options"]
        if struct == "SIM":
            placement = "clone_HF" if sid <= 90 else "clone_HD"
            if placement == "clone_HD":
                opt_src = rec["placement_variants"]["clone_HD"]["options"]
        opts = opt_src[:]
        order = list(range(len(opts)))
        rng.shuffle(order)                                   # shown order is a design variable
        shown = [opts[k] for k in order]
        opts_json = [{"code": o["code"], "available": o.get("available", True),
                      "html": render_option_html(rec, o, cats[cat])} for o in shown]
        pairs += [
            (f"cell{t}_id", f"c{ci:02d}_s{si:02d}"),
            (f"cell{t}_category", cat),
            (f"cell{t}_structure", struct),
            (f"cell{t}_tier", str(tier)),
            (f"cell{t}_format", rec.get("format", "numbers")),
            (f"cell{t}_order", ",".join(o["code"] for o in shown)),
            (f"cell{t}_stimulus", rec["id"]),
            (f"cell{t}_sim_placement", placement),
            (f"cell{t}_stem", rec["stem"]),
            (f"cell{t}_options", json.dumps(opts_json, ensure_ascii=False)),
        ]
    return pairs

# ============================ WIDGETS (JS + HTML) ==============================================
# Both widgets use a proven prior-lab criterion (addOnReady, hideNextButton + CSS !important +
# MutationObserver + setTimeout re-asserts + try/catch) - judges B/C found a bare disableNextButton()
# in addOnload is unreliable (Qualtrics re-renders the button; addOnload runs before the DOM/buttons
# are ready). The choice widget also honours each option's `available` flag: an unavailable option
# (the PHT phantom) renders as a greyed, NON-selectable card tagged "currently unavailable" - matching
# the model runner's wording (run.py option_line: " (currently unavailable)") so humans and models see
# the same thing. If options fail to load, the page shows an error and stays GATED (never a silent dead
# page that a participant can click past with no choice).

WIDGET_CSS = """<style>
.cfx-stem{font-size:16px;line-height:1.55;color:#1a1a1a;max-width:720px;margin:0 auto 14px}
.cfx-opts{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:10px}
.cfx-card{display:block;border:1px solid #cfd6dd;border-radius:10px;padding:12px 14px;cursor:pointer;background:#fff;transition:border-color .12s,box-shadow .12s}
.cfx-card:hover{border-color:#9bb0c4}
.cfx-card.sel{border-color:#1f5fae;box-shadow:0 0 0 2px rgba(31,95,174,.18)}
.cfx-card.cfx-un{opacity:.55;cursor:not-allowed;background:#f4f5f6;border-style:dashed}
.cfx-card input{margin-right:10px;transform:translateY(1px)}
.cfx-attr{font-size:15px;color:#222;margin:2px 0}
.cfx-an{color:#566}
.cfx-badge{display:inline-block;font-size:12px;color:#8a4b00;background:#ffe9cc;border-radius:4px;padding:1px 6px;margin-left:6px}
.cfx-err{display:none;color:#b00020;max-width:720px;margin:0 auto 10px;font-size:15px}
.cs-wrap{max-width:720px;margin:0 auto;font-size:15px;line-height:1.6;color:#222}
.cs-actions{display:flex;gap:12px;margin-top:18px;flex-wrap:wrap}
.cs-btn{font-size:15px;padding:10px 16px;border:1px solid #1f5fae;border-radius:8px;background:#fff;color:#1f5fae;cursor:pointer}
.cs-btn.on{background:#1f5fae;color:#fff}
.cs-note{margin-top:12px;color:#444;min-height:20px}
</style>"""

def _gate_js(prefix):
    """The proven hide/observe/re-assert Next-button criterion. `prefix` makes the <style> id unique."""
    return ("  self.hideNextButton();\n"
            "  var gs=document.createElement('style'); gs.id='" + prefix + "';\n"
            "  gs.textContent='#NextButton,input[id=\\\"NextButton\\\"]{display:none !important;visibility:hidden !important;pointer-events:none !important;}#PreviousButton{display:none !important;}';\n"
            "  document.head.appendChild(gs); var done=false;\n"
            "  var obs=new MutationObserver(function(){ if(done)return; if(!document.getElementById('" + prefix + "'))document.head.appendChild(gs); });\n"
            "  try{ obs.observe(document.head,{childList:true}); }catch(e){}\n"
            "  setTimeout(function(){ if(!done)self.hideNextButton(); },500);\n"
            "  setTimeout(function(){ if(!done)self.hideNextButton(); },2000);\n"
            "  function unlock(){ if(done)return; done=true; try{obs.disconnect();}catch(e){}\n"
            "    var g=document.getElementById('" + prefix + "'); if(g&&g.parentNode)g.parentNode.removeChild(g);\n"
            "    try{self.showNextButton();}catch(e){}\n"
            "    var nb=document.getElementById('NextButton'); if(nb){nb.style.display='';nb.style.visibility='';nb.style.pointerEvents='';nb.removeAttribute('disabled');}\n"
            "    setTimeout(function(){try{self.showNextButton();}catch(e){}},120); }\n")

def choice_html(t):
    return (WIDGET_CSS +
            f"<div id='cfx-err-{t}' class='cfx-err'>The options could not be loaded. Please refresh the page; "
            f"if this persists, return to Prolific and message us.</div>"
            f"<div id='cfx-stem-{t}' class='cfx-stem'></div>"
            f"<div id='cfx-opts-{t}' class='cfx-opts'></div>"
            f"<textarea id='cfx-stemdata-{t}' style='display:none'>${{e://Field/cell{t}_stem}}</textarea>"
            f"<textarea id='cfx-optsdata-{t}' style='display:none'>${{e://Field/cell{t}_options}}</textarea>")

def choice_js(t):
    return ("Qualtrics.SurveyEngine.addOnload(function(){});\n"
            "Qualtrics.SurveyEngine.addOnReady(function(){\n"
            "  var self=this, T=" + str(t) + ";\n"
            "  function ed(k,v){ try{ Qualtrics.SurveyEngine.setEmbeddedData(k,v); }catch(e){} }\n"
            "  function $(id){ return document.getElementById(id); }\n"
            + _gate_js(f"cfx-gate-{t}") +
            "  var rawO=($('cfx-optsdata-'+T)||{}).value||'[]';\n"
            "  var stem=($('cfx-stemdata-'+T)||{}).value||'';\n"
            "  var opts; try{opts=JSON.parse(rawO);}catch(e){opts=[];}\n"
            "  if(!opts.length){ var er=$('cfx-err-'+T); if(er)er.style.display='block'; return; }\n"
            "  $('cfx-stem-'+T).innerHTML=stem;\n"
            "  var wrap=$('cfx-opts-'+T);\n"
            "  opts.forEach(function(o,i){\n"
            "    var card=document.createElement('label'); card.className='cfx-card'+(o.available===false?' cfx-un':'');\n"
            "    if(o.available===false){ card.innerHTML=o.html+\"<span class='cfx-badge'>currently unavailable</span>\"; }\n"
            "    else {\n"
            "      card.innerHTML=\"<input type='radio' name='cfx-\"+T+\"' value='\"+(i+1)+\"'>\"+o.html;\n"
            "      card.querySelector('input').addEventListener('change',function(){\n"
            "        ed('choice_'+T, String(i+1)); ed('choice_'+T+'_code', o.code);\n"
            "        var cs=wrap.querySelectorAll('.cfx-card'); for(var k=0;k<cs.length;k++){cs[k].classList.remove('sel');}\n"
            "        card.classList.add('sel'); unlock();\n"
            "      });\n"
            "    }\n"
            "    wrap.appendChild(card);\n"
            "  });\n"
            "});\n")

def consent_widget_html(consent_text):
    return (WIDGET_CSS + "<div class='cs-wrap'>" + consent_text +
            "<div class='cs-actions'>"
            "<button type='button' id='cs-agree' class='cs-btn'>Yes, I consent and wish to begin</button>"
            "<button type='button' id='cs-decline' class='cs-btn'>No, I do not consent</button></div>"
            "<div id='cs-note' class='cs-note'></div></div>")

def consent_js():
    # Adapted from a consent script used in earlier studies. Writes embedded `consent`=yes/no; the flow's
    # decline branch keys on that field. WITHOUT this, the field is never set and the branch ends
    # every participant before any choice (the fatal dead-survey bug judge C found).
    return ("Qualtrics.SurveyEngine.addOnload(function(){});\n"
            "Qualtrics.SurveyEngine.addOnReady(function(){\n"
            "  var self=this;\n"
            "  function ed(k,v){ try{ Qualtrics.SurveyEngine.setEmbeddedData(k,v); }catch(e){} }\n"
            "  function $(id){ return document.getElementById(id); }\n"
            + _gate_js("cs-gate-style") +
            "  function choose(val){\n"
            "    ed('consent', val);\n"
            "    var a=$('cs-agree'), d=$('cs-decline');\n"
            "    if(a)a.classList.toggle('on', val==='yes'); if(d)d.classList.toggle('on', val==='no');\n"
            "    var note=$('cs-note'); if(note){ note.textContent=(val==='yes')?'Thank you. Click the arrow below to begin.':'You have declined. Click the arrow below to exit the study.'; }\n"
            "    unlock();\n"
            "  }\n"
            "  var a=$('cs-agree'); if(a)a.addEventListener('click',function(){ choose('yes'); });\n"
            "  var d=$('cs-decline'); if(d)d.addEventListener('click',function(){ choose('no'); });\n"
            "});\n")

# ============================ MAIN ASSEMBLY =====================================================

def build(consent_text, completion_url, build_date):
    cats, by_cell, pub, inv, structs = load_design()
    cat_map, str_map = build_index_map(pub, inv, structs)

    rows = list(csv.DictReader(open(SCRIPTSET, encoding="utf-8")))
    scripts = {}
    for r in rows:
        scripts.setdefault(int(r["script_id"]), []).append(
            {"script_id": int(r["script_id"]), "position": int(r["position"]),
             "category": r["category"], "structure": r["structure"], "tier": r["tier"]})
    n_scripts = len(scripts)
    assignment_version = hashlib.sha256(open(SCRIPTSET, "rb").read()).hexdigest()[:12]

    # ---- block IDs ----
    def bid(name): return _qid("BL_")
    BID = {n: bid(n) for n in ["consent", "instr", "demo", "debrief"]}
    BID.update({f"choice{t}": bid(f"choice{t}") for t in range(1, 8)})
    BID["Trash"] = bid("Trash")

    # ---- questions ----
    # Attention check matched to SURVEY_SPEC's fixed item (judges B/C: the QSF must not silently ship
    # a different item than the registered spec). Pass value recorded in MAPPING.json, not inferred.
    attn_text = ("To show you are reading carefully, please select <b>“Strongly agree”</b> below, "
                 "regardless of your actual opinion.")
    attn_choices = ["Strongly disagree", "Disagree", "Neither agree nor disagree", "Agree", "Strongly agree"]
    attn_correct = len(attn_choices)                       # "Strongly agree" = choice key 5
    instr_html = (
        "<div style='max-width:720px;margin:0 auto;font-size:15px;line-height:1.65;color:#222'>"
        "<h3>How this task works</h3>"
        "<p>On each of the next seven pages you will see a short shopping scenario and a set of "
        "options. Imagine you are really shopping, and choose the <b>one</b> option you would pick.</p>"
        "<p>There are no right or wrong answers. Please read each option's details before choosing. "
        "Click the arrow to begin.</p></div>")
    debrief_html = (
        "<div style='max-width:720px;margin:0 auto;font-size:15px;line-height:1.65;color:#222'>"
        "<h3>Thank you</h3><p>You have finished the choices. This study looks at how people choose among "
        "products when the set of options is arranged in different ways. Please do not share the specific "
        "options with future participants. Click the arrow to return to Prolific.</p></div>")
    Q = {}
    # Consent is a JS widget (adapted from a consent script used in earlier studies): it SETS embedded `consent`=yes/no, which
    # the decline branch keys on. A native MC would store the answer as a question column and leave
    # `consent` empty -> the branch would end EVERY participant (the dead-survey bug judge C found).
    Q["consent"] = sq_db("QID1", "consent_q", consent_widget_html(consent_text), consent_js(), "Consent")
    if INCLUDE_CAPTCHA:                       # default OFF (D3, 2026-07-01); QID2 stays reserved for it
        Q["captcha"] = sq_captcha("QID2", "captcha_1", "Captcha")
    Q["meta"] = sq_meta("QID3", "browser_meta", "Browser meta")
    Q["instr"] = sq_db("QID4", "instructions", instr_html, None, "Instructions")
    Q["attn"] = sq_mc("QID5", "attention_1", attn_text, attn_choices, "Attention check")
    qn = 6
    for t in range(1, 8):
        Q[f"timer{t}"] = sq_timing(f"QID{qn}", f"timer_{t}", f"Timer page {t}"); qn += 1
        Q[f"choice{t}"] = sq_db(f"QID{qn}", f"choice_{t}_q", choice_html(t), choice_js(t),
                                f"Choice page {t}"); qn += 1
    Q["gender"] = sq_mc(f"QID{qn}", "gender",
                        "What is your gender?", ["Woman", "Man", "Non-binary", "Prefer not to say"],
                        "Gender", force=True); qn += 1
    Q["age"] = sq_text(f"QID{qn}", "age", "What is your age (in years)?", "Age", content_type="ValidNumber"); qn += 1
    Q["debrief"] = sq_db(f"QID{qn}", "debrief", debrief_html, None, "Debrief")

    questions = [Q["consent"]] + ([Q["captcha"]] if INCLUDE_CAPTCHA else []) + [Q["meta"], Q["instr"], Q["attn"]]
    for t in range(1, 8):
        questions += [Q[f"timer{t}"], Q[f"choice{t}"]]
    questions += [Q["gender"], Q["age"], Q["debrief"]]
    qid_of = lambda key: Q[key]["PrimaryAttribute"]

    # ---- blocks ----
    consent_qids = [qid_of("consent")] + ([qid_of("captcha")] if INCLUDE_CAPTCHA else []) + [qid_of("meta")]
    blocks = [
        block(BID["consent"], "Consent", consent_qids, btype="Default"),
        block(BID["instr"], "Instructions & attention", [qid_of("instr"), qid_of("attn")], page_breaks=True),
    ]
    for t in range(1, 8):
        blocks.append(block(BID[f"choice{t}"], f"Choice {t}",
                            [qid_of(f"timer{t}"), qid_of(f"choice{t}")]))   # timer + choice, same page
    blocks += [
        block(BID["demo"], "Demographics", [qid_of("gender"), qid_of("age")], page_breaks=False),
        block(BID["debrief"], "Debrief", [qid_of("debrief")]),
        {"Type": "Trash", "SubType": "", "Description": "Trash / Unused Questions", "ID": BID["Trash"], "BlockElements": []},
    ]
    blocks_payload = {str(i + 1): b for i, b in enumerate(blocks)}

    # ---- embedded-data declaration (rule 9: declare every field up front, no value) ----
    fields = ["PROLIFIC_PID", "STUDY_ID", "SESSION_ID", "consent", "qsf_build", "assignment_version", "script_id"]
    for t in range(1, 8):
        fields += [f"cell{t}_{s}" for s in
                   ("id", "category", "structure", "tier", "format", "order", "stimulus",
                    "sim_placement", "stem", "options")]
        fields += [f"choice_{t}", f"choice_{t}_code"]

    # ---- the 180 script-setter children (path a Wave 2; was 160) ----
    setters = [ed_set_many(script_cells(scripts[sid], cat_map, str_map, by_cell, cats))
               for sid in sorted(scripts)]

    # ---- survey flow ----
    flow = [
        ed_decl(fields),
        ed_set("qsf_build", f"{VERSION}+{build_date}"),
        ed_set("assignment_version", assignment_version),
        flow_block(BID["consent"]),
        flow_branch_decline(flow_end(redirect_url=None)),
        flow_block(BID["instr"]),
        flow_randomizer(setters, subset=1, even=True),
    ]
    for t in range(1, 8):
        flow.append(flow_block(BID[f"choice{t}"]))
    flow += [flow_block(BID["demo"]), flow_block(BID["debrief"]), flow_end(redirect_url=completion_url)]
    max_fl = assign_flow_ids(flow, [1])

    survey_flow = {"SurveyID": SID, "Element": "FL", "PrimaryAttribute": "Survey Flow",
                   "SecondaryAttribute": None, "TertiaryAttribute": None,
                   "Payload": {"Type": "Root", "FlowID": "FL_1", "Flow": flow,
                               "Properties": {"Count": max_fl + FLOW_COUNT_MARGIN, "RemovedFieldsets": []}}}
    survey_blocks = {"SurveyID": SID, "Element": "BL", "PrimaryAttribute": "Survey Blocks",
                     "SecondaryAttribute": None, "TertiaryAttribute": None, "Payload": blocks_payload}
    survey_options = {"SurveyID": SID, "Element": "SO", "PrimaryAttribute": "Survey Options",
                      "SecondaryAttribute": None, "TertiaryAttribute": None,
                      "Payload": {"BackButton": "false", "SaveAndContinue": "true",
                                  "SurveyProtection": "PublicSurvey", "BallotBoxStuffingPrevention": "true",
                                  "RecaptchaV3": "true", "NoIndex": "Yes", "SecureResponseFiles": "true",
                                  "SurveyExpiration": "None", "SurveyTermination": "DefaultMessage",
                                  "Header": "", "Footer": "", "ProgressBarDisplay": "Text",
                                  "PartialData": "+1 week", "ValidationMessage": "", "PreviousButton": "",
                                  "NextButton": " &#8594; ", "SurveyTitle": "Shopping Choices Study",
                                  "SkinLibrary": "qualtrics", "SkinType": "templated",
                                  "Skin": {"brandingId": None, "templateId": "*base", "overrides": None},
                                  "NewScoring": 1}}

    elements = [survey_blocks, survey_flow, survey_options] + questions + [
        {"SurveyID": SID, "Element": "RS", "PrimaryAttribute": RSID,
         "SecondaryAttribute": "Default Response Set", "TertiaryAttribute": None, "Payload": None},
        {"SurveyID": SID, "Element": "QC", "PrimaryAttribute": "Survey Question Count",
         "SecondaryAttribute": str(len(questions)), "TertiaryAttribute": None, "Payload": None},
        {"SurveyID": SID, "Element": "SCO", "PrimaryAttribute": "Scoring", "SecondaryAttribute": None,
         "TertiaryAttribute": None, "Payload": {"ScoringCategories": [], "ScoringCategoryGroups": [],
            "ScoringSummaryCategory": None, "ScoringSummaryAfterQuestions": 0, "ScoringSummaryAfterSurvey": 0,
            "DefaultScoringCategory": None, "AutoScoringCategory": None}},
        {"SurveyID": SID, "Element": "PROJ", "PrimaryAttribute": "CORE", "SecondaryAttribute": None,
         "TertiaryAttribute": "1.1.0", "Payload": {"ProjectCategory": "CORE", "SchemaVersion": "1.1.0"}},
        {"SurveyID": SID, "Element": "STAT", "PrimaryAttribute": "Survey Statistics",
         "SecondaryAttribute": None, "TertiaryAttribute": None,
         "Payload": {"MobileCompatible": True, "ID": "Survey Statistics"}},
    ]
    survey_entry = {
        "SurveyID": SID, "SurveyName": "LLM Context Effects - Numeric Backbone (Human)",
        "SurveyDescription": None, "SurveyOwnerID": None, "SurveyBrandID": None, "DivisionID": None,
        "SurveyLanguage": "EN", "SurveyActiveResponseSet": RSID, "SurveyStatus": "Inactive",
        "SurveyStartDate": "0000-00-00 00:00:00", "SurveyExpirationDate": "0000-00-00 00:00:00",
        "SurveyCreationDate": f"{build_date} 00:00:00", "CreatorID": None,
        "LastModified": f"{build_date} 00:00:00", "LastAccessed": "0000-00-00 00:00:00",
        "LastActivated": "0000-00-00 00:00:00", "Deleted": None,
    }
    qsf = {"SurveyEntry": survey_entry, "SurveyElements": elements}

    mapping = {"seed": SHUFFLE_SEED, "version": VERSION, "build_date": build_date,
               "scriptset_sha256_12": assignment_version, "n_scripts": n_scripts,
               "attention_1_correct": attn_correct, "attention_1_correct_label": attn_choices[-1],
               "category_index_to_name": cat_map, "structure_index_to_code": str_map,
               "published_categories": pub, "invented_categories": inv,
               "note": ("scriptset_180.csv uses abstract indices; this is the seeded map to real "
                        "names. Published categories occupy indices 0-6 and invented 7-9 (the tier "
                        "logic in scriptset_sim.py depends on that split); structure indices 0-8 cover "
                        "all 9 backbone structures, including EXC (path a, contract v1.1).")}
    return qsf, mapping, len(questions), len([b for b in blocks if b.get("Type") != "Trash"]), n_scripts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--consent-file", default=None, help="UTF-8 file with the IRB consent text (HTML ok).")
    ap.add_argument("--completion-url", default=PLACEHOLDER_COMPLETION)
    ap.add_argument("--build-date", default=BUILD_DATE_DEFAULT)
    ap.add_argument("--out", default=os.path.join(OUT_DIR, "backbone.qsf"))
    ap.add_argument("--with-captcha", action="store_true",
                    help="re-include the reCAPTCHA-v2 checkbox question (default OFF per D3, 2026-07-01).")
    args = ap.parse_args()
    if args.with_captcha:
        global INCLUDE_CAPTCHA
        INCLUDE_CAPTCHA = True

    if args.consent_file:
        consent_text = open(args.consent_file, encoding="utf-8").read().strip()
    else:
        consent_text = PLACEHOLDER_CONSENT
        print("[generate_qsf] WARNING: no --consent-file; using PLACEHOLDER consent "
              "(validate_qsf.py will FAIL until replaced).")

    os.makedirs(OUT_DIR, exist_ok=True)
    qsf, mapping, n_q, n_b, n_s = build(consent_text, args.completion_url, args.build_date)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(qsf, f, ensure_ascii=False)
    map_out = args.out.replace(".qsf", "_MAPPING.json")
    with open(map_out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    # round-trip self-check (the ancestor's check)
    reloaded = json.loads(open(args.out, encoding="utf-8").read())
    rq = sum(1 for e in reloaded["SurveyElements"] if e["Element"] == "SQ")
    blp = next(e for e in reloaded["SurveyElements"] if e["Element"] == "BL")["Payload"]
    rb = len([b for b in blp.values() if b.get("Type") != "Trash"])
    print(f"[generate_qsf] wrote {args.out}")
    print(f"[generate_qsf] questions={rq} (QC={n_q}) blocks={rb} scripts={n_s} "
          f"size={os.path.getsize(args.out)//1024}KB")
    print(f"[generate_qsf] mapping -> {map_out}")
    print(f"[generate_qsf] completion_url={args.completion_url}")
    assert rq == n_q and rb == n_b, "round-trip count mismatch"

if __name__ == "__main__":
    main()
