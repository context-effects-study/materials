"""generate_survey.py: build the four other confirmatory surveys as importable Qualtrics files.

  survey2_sim.qsf        the similarity top-up: 1,000 scripts of seven choices, both clone placements
  survey3_words.qsf      the format module, words: 2,800 scripts of three choices
  survey3_pictures.qsf   the format module, pictures: 2,100 scripts of three choices
  survey4_pricefree.qsf  the price-free robustness test: 2,800 scripts of three choices

It reuses the backbone's builders from generate_qsf.py and takes the balanced deals from deal.py. The
similarity survey carries its scripts in a Qualtrics randomizer; the three larger surveys have more
scripts than a Qualtrics randomizer can hold, so they ask the small assignment service in
surveys/assign_worker/ for a script at the start of each response (a Web Service element) and store it in
embedded data. Either way the export carries every design variable, and it decodes through
analysis/ingest.py.

Output: the four .qsf files and their _MAPPING.json files in surveys/out/.
Manuscript: Method ("Human study") and Table 2.

Run: python surveys/generate_survey.py
"""
from __future__ import annotations
import argparse, hashlib, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_qsf as G          # reuse the proven builders, widgets, and import-safe element shapes
import deal

OUT_DIR = os.path.join(HERE, "out")
# Image host for the pictures version: the whole-set magnitude-bar PNGs (rasterize.py, 2x scale, no
# metadata; the same files as surveys/png/) are served from a static web address under /img/, checked
# to load and to be byte-identical to these files. The vision model is shown
# the same PNG bytes (CONTRACTS B), so humans and models see identical pictures.
HOSTBASE = "https://context-effects-fidelity.pages.dev/img"
DEBRIEF_HTML = ("<div style='max-width:720px;margin:0 auto;font-size:15px;line-height:1.65;color:#222'>"
                "<h3>Thank you</h3><p>You have finished the choices. This study looks at how people choose "
                "among products when the set of options is arranged in different ways. Please do not share "
                "the specific options with future participants. Click the arrow to return to Prolific.</p></div>")
ATTN_TEXT = ("To show you are reading carefully, please select <b>“Strongly agree”</b> below, "
             "regardless of your actual opinion.")
ATTN_CHOICES = ["Strongly disagree", "Disagree", "Neither agree nor disagree", "Agree", "Strongly agree"]
# Worker-SPOF graceful screen-out message (CRIT-WORKER-SPOF). Shown only if the assignment call failed,
# BEFORE any choice page. Plain English; tells the participant to return their submission so they are not
# penalised; carries NO Prolific completion code (the participant never answers empty trials, so no
# unusable paid data is collected). The replacement participant is recruited under the existing top-up
# rule (HUMAN_PROTOCOL.md §4).
ASSIGN_FAIL_HTML = (
    "<div style='max-width:720px;margin:0 auto;font-size:15px;line-height:1.65;color:#222'>"
    "<h3>We could not start your study materials</h3>"
    "<p>We hit a brief technical issue assigning your study materials, so we cannot start the task for "
    "you right now. We are sorry for the inconvenience.</p>"
    "<p><b>Please return your submission on Prolific so you are not penalized.</b> No payment is "
    "affected by returning, and your Prolific record is not harmed by a return. You do not need to "
    "do anything else.</p></div>")

def instr_html(k):
    word = {3: "three", 7: "seven"}.get(k, str(k))
    return ("<div style='max-width:720px;margin:0 auto;font-size:15px;line-height:1.65;color:#222'>"
            "<h3>How this task works</h3>"
            f"<p>On each of the next {word} pages you will see a short shopping scenario and a set of "
            "options. Imagine you are really shopping, and choose the <b>one</b> option you would pick.</p>"
            "<p>There are no right or wrong answers. Please read each option's details before choosing. "
            "Click the arrow to begin.</p></div>")

def render_option_words(words_dict, cat_meta, rec=None, opt=None):
    """A WORDS-format option card: each attribute's spelled-out magnitude (from stimuli.json
    format_variants.words), in category order. Same per-attribute text the model's words prompt uses,
    so the human card and the model prompt stay consistent in the words arm too. final calibration lock (2026-07-02):
    in the enrichment scope the card is the ENRICHED blurb (model name + spelled value + qualifier,
    via the shared enrich renderer); all four words categories sit in scope, the sparse branch stays
    as the out-of-scope fallback."""
    if rec is not None and opt is not None:
        entry = G.enrich.entry_for(G.enrichment_block(), rec, opt)
        if entry is not None:
            return G.enrich.option_words_html(opt, cat_meta, entry)
    lines = []
    for a in cat_meta["attributes"]:
        if a["name"] in words_dict:
            lines.append(f"<div class='cfx-attr'>{words_dict[a['name']]}</div>")
    return "".join(lines)

def choice_html_pic(t):
    """Picture choice page: the whole-set magnitude-bar image (one image per choice set, options labelled
    A/B/C in the image) + a forced radio set matching those labels. Reuses the WIDGET_CSS + criterion."""
    return (G.WIDGET_CSS +
            f"<div id='cfx-err-{t}' class='cfx-err'>The options could not be loaded. Please refresh the page; "
            f"if this persists, return to Prolific and message us.</div>"
            f"<div id='cfx-stem-{t}' class='cfx-stem'></div>"
            f"<img id='cfx-img-{t}' alt='the options, shown as magnitude bars' "
            f"style='max-width:100%;display:block;margin:0 auto 14px;border:1px solid #e3e6e9;border-radius:8px'>"
            f"<div id='cfx-opts-{t}' class='cfx-opts'></div>"
            f"<textarea id='cfx-stemdata-{t}' style='display:none'>${{e://Field/cell{t}_stem}}</textarea>"
            f"<textarea id='cfx-optsdata-{t}' style='display:none'>${{e://Field/cell{t}_options}}</textarea>"
            f"<textarea id='cfx-imgdata-{t}' style='display:none'>${{e://Field/cell{t}_image}}</textarea>")

def choice_js_pic(t):
    """Picture widget JS: load the image, render labelled-radio options, criterion Next until a choice is made,
    write choice_t + choice_t_code. Stays gated if the image or options fail to load (no silent dead page).

    HOST NORMALIZATION (2026-07-01): the widget takes only the image FILENAME from the assignment payload
    and joins it to the HOSTBASE baked into this QSF at build time, so the QSF (regenerated + re-imported
    at every host change, per the launch procedure) is the single authority for WHERE pictures are served.
    Rationale: the pictures arm's script table lives in the assignment Worker, whose deployed bundle still
    carries the build-time host of ITS last deploy (currently the pre-launch placeholder; the Worker is
    not redeployed in this pass). Normalizing here makes the survey render correctly regardless of which
    host string the Worker's stored payload carries; once the Worker data is regenerated with the real
    host (CFX_IMAGE_HOST=<host> bash regen_and_deploy.sh --deploy, a decided by the authors step), this join is a
    no-op (basename(real URL) + same HOSTBASE = the same URL)."""
    return ("Qualtrics.SurveyEngine.addOnload(function(){});\n"
            "Qualtrics.SurveyEngine.addOnReady(function(){\n"
            "  var self=this, T=" + str(t) + ";\n"
            "  var HB=" + json.dumps(HOSTBASE.rstrip("/")) + ";\n"
            "  function ed(k,v){ try{ Qualtrics.SurveyEngine.setEmbeddedData(k,v); }catch(e){} }\n"
            "  function $(id){ return document.getElementById(id); }\n"
            + G._gate_js(f"cfx-gate-{t}") +
            "  var rawO=($('cfx-optsdata-'+T)||{}).value||'[]';\n"
            "  var stem=($('cfx-stemdata-'+T)||{}).value||'';\n"
            "  var img=($('cfx-imgdata-'+T)||{}).value||'';\n"
            "  if(img){ img=HB+'/'+img.split('/').pop(); }\n"
            "  var opts; try{opts=JSON.parse(rawO);}catch(e){opts=[];}\n"
            "  if(!opts.length||!img){ var er=$('cfx-err-'+T); if(er)er.style.display='block'; return; }\n"
            "  $('cfx-stem-'+T).innerHTML=stem;\n"
            "  var im=$('cfx-img-'+T); if(im){ im.src=img; }\n"
            "  var wrap=$('cfx-opts-'+T);\n"
            "  opts.forEach(function(o,i){\n"
            "    var card=document.createElement('label'); card.className='cfx-card';\n"
            "    card.innerHTML=\"<input type='radio' name='cfx-\"+T+\"' value='\"+(i+1)+\"'>\"+o.html;\n"
            "    card.querySelector('input').addEventListener('change',function(){\n"
            "      ed('choice_'+T, String(i+1)); ed('choice_'+T+'_code', o.code);\n"
            "      var cs=wrap.querySelectorAll('.cfx-card'); for(var k=0;k<cs.length;k++){cs[k].classList.remove('sel');}\n"
            "      card.classList.add('sel'); unlock();\n"
            "    });\n"
            "    wrap.appendChild(card);\n"
            "  });\n"
            "});\n")

def cells_to_pairs(script_id, cells, by_cell, cats, salt):
    """Resolve one participant's explicit cells -> the embedded-data field pairs (mirrors
    generate_qsf.script_cells but for explicit category/structure/tier/placement, no index map).
    Format-aware: numbers cells render via the shared renderer; words cells render the spelled
    format_variants.words (pictures are a separate build - see the registered picture format)."""
    rng = random.Random(G.SHUFFLE_SEED + f"-{salt}-{script_id}")
    pairs = [("script_id", str(script_id))]
    for t, cell in enumerate(cells, start=1):
        cat, struct, tier = cell["category"], cell["structure"], int(cell["tier"])
        placement = cell.get("sim_placement", "NA")
        rec = by_cell[(cat, struct, tier)]
        opt_src = rec["options"]
        if struct == "SIM" and placement == "clone_HD" and rec.get("placement_variants"):
            opt_src = rec["placement_variants"]["clone_HD"]["options"]
        fmt = cell.get("format", "numbers")
        image_url = None
        if fmt == "pictures":
            pic = rec["format_variants"]["pictures"]     # canonical order: the whole-set image is
            shown = pic.get("options") or opt_src        # pre-rendered in this order - do NOT shuffle.
            # final calibration lock: the variant's own `options` are authoritative (the two per-format-locked pictures
            # cells carry different values than the numbers row; the rest duplicate the numbers values)
            image_url = HOSTBASE + "/" + os.path.basename(pic["image_ref"]).replace(".svg", ".png")
            LETTERS = "ABCDEFG"
            opts_json = [{"code": o["code"], "available": o.get("available", True),
                          "html": f"Option {LETTERS[i]}"} for i, o in enumerate(shown)]
        else:
            opts = opt_src[:]
            order = list(range(len(opts)))
            rng.shuffle(order)
            shown = [opts[k] for k in order]
            if fmt == "words":
                wmap = {w["code"]: w["words"] for w in rec["format_variants"]["words"]}
                opts_json = [{"code": o["code"], "available": o.get("available", True),
                              "html": render_option_words(wmap[o["code"]], cats[cat], rec, o)} for o in shown]
            else:
                opts_json = [{"code": o["code"], "available": o.get("available", True),
                              "html": G.render_option_html(rec, o, cats[cat])} for o in shown]
        # SIZE GUARD (final calibration lock, 2026-07-02): the enriched cards grew the similarity survey's 1,000-setter
        # QSF past the importer's request-size ceiling (a 17.6 MB file drew ESRV145 where the
        # pre-enrichment 15.9 MB imported). Two loss-free shavings keep the payload semantically
        # identical: drop the default "available": true key (the widget tests o.available===false,
        # so an absent key means available - only the phantom's false must ship), and let the
        # emitter serialize compactly (see emit()).
        for oj in opts_json:
            if oj.get("available") is True:
                del oj["available"]
        pairs += [
            (f"cell{t}_id", f"{cat}_{struct}"), (f"cell{t}_category", cat),
            (f"cell{t}_structure", struct), (f"cell{t}_tier", str(tier)),
            (f"cell{t}_format", fmt),
            (f"cell{t}_order", ",".join(o["code"] for o in shown)),
            (f"cell{t}_stimulus", rec["id"]), (f"cell{t}_sim_placement", placement),
            (f"cell{t}_stem", rec["stem"]),
            (f"cell{t}_options", json.dumps(opts_json, ensure_ascii=False, separators=(",", ":"))),
        ]
        if image_url is not None:
            pairs.append((f"cell{t}_image", image_url))
    return pairs

# The assignment Worker (survey_assign_worker) that does the balanced even-presentation deal OUT of
# Qualtrics for the three large arms (price-free/words/pictures) whose 2,800 scripts exceed the importer's
# randomizer-child cap. The survey calls GET <WORKER_URL>/assign?arm=<arm> at survey start (a Web Service
# flow element) and stores the returned JSON into embedded data. The service address is set at deployment.
WORKER_URL = os.environ.get("CFX_ASSIGN_WORKER_URL",
                            "https://STUDY-ASSIGNMENT-SERVICE.example")
# arm name the Worker expects, keyed by this generator's survey_label
WORKER_ARM = {"survey4_pricefree": "price-free", "survey3_words": "words", "survey3_pictures": "pictures"}

def build_survey(name, title, survey_label, scripts, k, consent_text, completion_url, build_date,
                 picture_mode=False, assign_mode="randomizer"):
    cats, by_cell, pub, inv, pf = deal.load()
    deal_sha = hashlib.sha256(json.dumps(scripts, sort_keys=True).encode()).hexdigest()[:12]
    # per-survey deterministic SurveyID / ResponseSetID (re-seed generate_qsf's id generator)
    G._rng = random.Random("survey-ids-" + name)
    G.SID = G._qid("SV_"); G.RSID = G._qid("RS_")
    SID, RSID = G.SID, G.RSID
    BID = {n: G._qid("BL_") for n in ["consent", "instr", "demo", "debrief"]}
    BID.update({f"choice{t}": G._qid("BL_") for t in range(1, k + 1)}); BID["Trash"] = G._qid("BL_")
    if assign_mode == "webservice":
        BID["assign_fail"] = G._qid("BL_")          # the worker-SPOF screen-out message block

    Q = {}
    Q["consent"] = G.sq_db("QID1", "consent_q", G.consent_widget_html(consent_text), G.consent_js(), "Consent")
    if G.INCLUDE_CAPTCHA:                     # default OFF (D3, 2026-07-01); QID2 stays reserved for it
        Q["captcha"] = G.sq_captcha("QID2", "captcha_1", "Captcha")
    Q["meta"] = G.sq_meta("QID3", "browser_meta", "Browser meta")
    Q["instr"] = G.sq_db("QID4", "instructions", instr_html(k), None, "Instructions")
    Q["attn"] = G.sq_mc("QID5", "attention_1", ATTN_TEXT, ATTN_CHOICES, "Attention check")
    qn = 6
    for t in range(1, k + 1):
        Q[f"timer{t}"] = G.sq_timing(f"QID{qn}", f"timer_{t}", f"Timer page {t}"); qn += 1
        chtml = choice_html_pic(t) if picture_mode else G.choice_html(t)
        chjs = choice_js_pic(t) if picture_mode else G.choice_js(t)
        Q[f"choice{t}"] = G.sq_db(f"QID{qn}", f"choice_{t}_q", chtml, chjs, f"Choice page {t}"); qn += 1
    Q["gender"] = G.sq_mc(f"QID{qn}", "gender", "What is your gender?",
                          ["Woman", "Man", "Non-binary", "Prefer not to say"], "Gender", force=True); qn += 1
    Q["age"] = G.sq_text(f"QID{qn}", "age", "What is your age (in years)?", "Age", content_type="ValidNumber"); qn += 1
    Q["debrief"] = G.sq_db(f"QID{qn}", "debrief", DEBRIEF_HTML, None, "Debrief"); qn += 1
    if assign_mode == "webservice":
        # the worker-SPOF screen-out message (a plain DB/TB page; no JS criterion needed, the participant just
        # reads it and the next click lands on a bare EndSurvey with no completion code).
        Q["assign_fail"] = G.sq_db(f"QID{qn}", "assign_fail", ASSIGN_FAIL_HTML, None, "Assignment failed")
    questions = [Q["consent"]] + ([Q["captcha"]] if G.INCLUDE_CAPTCHA else []) + [Q["meta"], Q["instr"], Q["attn"]]
    for t in range(1, k + 1):
        questions += [Q[f"timer{t}"], Q[f"choice{t}"]]
    questions += [Q["gender"], Q["age"], Q["debrief"]]
    if assign_mode == "webservice":
        questions += [Q["assign_fail"]]
    qid = lambda key: Q[key]["PrimaryAttribute"]

    consent_qids = [qid("consent")] + ([qid("captcha")] if G.INCLUDE_CAPTCHA else []) + [qid("meta")]
    blocks = [G.block(BID["consent"], "Consent", consent_qids, btype="Default"),
              G.block(BID["instr"], "Instructions & attention", [qid("instr"), qid("attn")], page_breaks=True)]
    for t in range(1, k + 1):
        blocks.append(G.block(BID[f"choice{t}"], f"Choice {t}", [qid(f"timer{t}"), qid(f"choice{t}")]))
    blocks += [G.block(BID["demo"], "Demographics", [qid("gender"), qid("age")]),
               G.block(BID["debrief"], "Debrief", [qid("debrief")])]
    if assign_mode == "webservice":
        blocks.append(G.block(BID["assign_fail"], "Assignment failed", [qid("assign_fail")]))
    blocks += [{"Type": "Trash", "SubType": "", "Description": "Trash / Unused Questions",
                "ID": BID["Trash"], "BlockElements": []}]
    blocks_payload = {str(i + 1): b for i, b in enumerate(blocks)}

    fields = ["PROLIFIC_PID", "STUDY_ID", "SESSION_ID", "consent", "qsf_build", "assignment_version", "script_id"]
    if assign_mode == "webservice":
        fields.append("assign_ok")          # worker-SPOF guard flag (pre-seeded "", set from the Worker's ok)
    for t in range(1, k + 1):
        fields += [f"cell{t}_{s}" for s in
                   ("id", "category", "structure", "tier", "format", "order", "stimulus", "sim_placement", "stem", "options")]
        if picture_mode:
            fields.append(f"cell{t}_image")
        fields += [f"choice_{t}", f"choice_{t}_code"]

    # Assignment: either the in-Qualtrics BlockRandomizer over pre-built setter children (the small arms),
    # or a single Web Service call to the assignment Worker (the three large arms whose 2,800 scripts
    # exceed the importer's randomizer-child cap). Both deal the SAME balanced even-presentation scripts;
    # the Web Service moves WHERE the deal happens out of Qualtrics so the full design imports.
    if assign_mode == "webservice":
        arm = WORKER_ARM[survey_label]
        # the per-trial design + render fields the Worker returns and the choice widget reads; script_id
        # and assignment_version come from the Worker too (so the export still reconstructs the design).
        # `ok` -> assign_ok is the worker-SPOF guard the branch tests (the Worker returns "ok": true on a
        # good assignment); the ResponseMap key is the Worker's JSON field `ok`, stored into `assign_ok`.
        ws_fields = ["script_id"]
        ws_responsemap_extra = [{"key": "ok", "value": "assign_ok"}]
        for t in range(1, k + 1):
            ws_fields += [f"cell{t}_{s}" for s in
                          ("id", "category", "structure", "tier", "format", "order", "stimulus",
                           "sim_placement", "stem", "options")]
            if picture_mode:
                ws_fields.append(f"cell{t}_image")
        assign_el = G.flow_webservice(f"{WORKER_URL}/assign", ws_fields, arm, extra_map=ws_responsemap_extra)
    else:
        setters = [G.ed_set_many(cells_to_pairs(i + 1, sc, by_cell, cats, name)) for i, sc in enumerate(scripts)]
        assign_el = G.flow_randomizer(setters, subset=1, even=True)

    flow = [G.ed_decl(fields), G.ed_set("qsf_build", f"{G.VERSION}+{build_date}"),
            G.ed_set("assignment_version", deal_sha)]
    if assign_mode == "webservice":
        # pre-seed the worker-SPOF guard flag to "" up front so the "Is Not Equal to true" branch test is
        # reliable even if the Web Service call never fires (the empty default makes "Is Empty" / "!= true"
        # both detect a failed/absent assignment).
        flow.append(G.ed_set("assign_ok", ""))
    flow += [G.flow_block(BID["consent"]),
             G.flow_branch_decline(G.flow_end(redirect_url=None)), G.flow_block(BID["instr"]),
             assign_el]
    if assign_mode == "webservice":
        # THE NON-NEGOTIABLE FIX (CRIT-WORKER-SPOF): immediately after the Web Service call and BEFORE the
        # first choice block, branch on a failed assignment to a graceful screen-out (message block + bare
        # EndSurvey, NO completion code) so a failed assignment can NEVER let a participant answer empty trials.
        flow.append(G.flow_branch_assign_fail([G.flow_block(BID["assign_fail"]), G.flow_end(redirect_url=None)]))
    for t in range(1, k + 1):
        flow.append(G.flow_block(BID[f"choice{t}"]))
    flow += [G.flow_block(BID["demo"]), G.flow_block(BID["debrief"]), G.flow_end(redirect_url=completion_url)]
    max_fl = G.assign_flow_ids(flow, [1])

    # ---- scaffold (mirrors generate_qsf.build; SID/RSID are this survey's) ----
    # Count computed from the real max FlowID (root-cause-#2 guard, D2 fix 2026-07-01: the similarity
    # survey's 1,000-setter flow reaches FL_1019, far past the old hardcoded 200).
    survey_flow = {"SurveyID": SID, "Element": "FL", "PrimaryAttribute": "Survey Flow",
                   "SecondaryAttribute": None, "TertiaryAttribute": None,
                   "Payload": {"Type": "Root", "FlowID": "FL_1", "Flow": flow,
                               "Properties": {"Count": max_fl + G.FLOW_COUNT_MARGIN, "RemovedFieldsets": []}}}
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
                                  "NextButton": " &#8594; ", "SurveyTitle": title, "SkinLibrary": "qualtrics",
                                  "SkinType": "templated",
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
    survey_entry = {"SurveyID": SID, "SurveyName": name, "SurveyDescription": None, "SurveyOwnerID": None,
                    "SurveyBrandID": None, "DivisionID": None, "SurveyLanguage": "EN",
                    "SurveyActiveResponseSet": RSID, "SurveyStatus": "Inactive",
                    "SurveyStartDate": "0000-00-00 00:00:00", "SurveyExpirationDate": "0000-00-00 00:00:00",
                    "SurveyCreationDate": f"{build_date} 00:00:00", "CreatorID": None,
                    "LastModified": f"{build_date} 00:00:00", "LastAccessed": "0000-00-00 00:00:00",
                    "LastActivated": "0000-00-00 00:00:00", "Deleted": None}
    qsf = {"SurveyEntry": survey_entry, "SurveyElements": elements}
    mapping = {"survey": survey_label, "version": G.VERSION, "build_date": build_date,
               "deal_sha256_12": deal_sha, "n_scripts": len(scripts), "k_trials": k,
               "assign_mode": assign_mode,
               "worker_url": (f"{WORKER_URL}/assign" if assign_mode == "webservice" else None),
               "worker_arm": (WORKER_ARM[survey_label] if assign_mode == "webservice" else None),
               "include_captcha": G.INCLUDE_CAPTCHA,
               "image_hostbase": (HOSTBASE if picture_mode else None),
               "attention_1_correct": len(ATTN_CHOICES), "attention_1_correct_label": ATTN_CHOICES[-1]}
    return qsf, mapping, len(questions), len([b for b in blocks if b.get("Type") != "Trash"])

def emit(name, title, survey_label, scripts, k, out, consent_text, completion_url, build_date,
         picture_mode=False, assign_mode="randomizer"):
    qsf, mapping, n_q, n_b = build_survey(name, title, survey_label, scripts, k, consent_text,
                                          completion_url, build_date, picture_mode, assign_mode)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        # compact separators (final calibration lock size guard): semantically identical, keeps the 1,000-setter
        # similarity survey under the importer's request-size ceiling
        json.dump(qsf, f, ensure_ascii=False, separators=(",", ":"))
    with open(out.replace(".qsf", "_MAPPING.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"[generate_survey] {survey_label}: wrote {os.path.basename(out)} "
          f"questions={n_q} blocks={n_b} scripts={len(scripts)} size={os.path.getsize(out)//1024}KB")
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--consent-file", default=None)
    ap.add_argument("--completion-url", default=G.PLACEHOLDER_COMPLETION)
    ap.add_argument("--build-date", default=G.BUILD_DATE_DEFAULT)
    ap.add_argument("--with-captcha", action="store_true",
                    help="re-include the reCAPTCHA-v2 checkbox question (default OFF per D3, 2026-07-01).")
    args = ap.parse_args()
    if args.with_captcha:
        G.INCLUDE_CAPTCHA = True
    consent_text = open(args.consent_file, encoding="utf-8").read().strip() if args.consent_file else G.PLACEHOLDER_CONSENT
    if not args.consent_file:
        print("[generate_survey] WARNING: placeholder consent (validate_qsf.py fails until replaced).")

    cats, by_cell, pub, inv, pf = deal.load()
    s4, _ = deal.deal_pricefree(pf)
    s2, _, _ = deal.deal_sim_topup(pub, inv)
    # The three large arms (price-free, words, pictures) assign via the Web Service Worker (their 2,800
    # scripts exceed the importer's randomizer-child cap). Survey 2 (SIM, 1,000 scripts) stays under the
    # cap and keeps the in-Qualtrics BlockRandomizer.
    emit("LLM Context Effects - Price-free Arm (Human)", "Shopping Choices Study", "survey4_pricefree",
         s4, 3, os.path.join(OUT_DIR, "survey4_pricefree.qsf"), consent_text, args.completion_url,
         args.build_date, assign_mode="webservice")
    emit("LLM Context Effects - Similarity Top-up (Human)", "Shopping Choices Study", "survey2_sim",
         s2, 7, os.path.join(OUT_DIR, "survey2_sim.qsf"), consent_text, args.completion_url, args.build_date)
    sw, _, _ = deal.deal_format("words")
    emit("LLM Context Effects - Format Module, Words (Human)", "Shopping Choices Study", "survey3_words",
         sw, 3, os.path.join(OUT_DIR, "survey3_words.qsf"), consent_text, args.completion_url,
         args.build_date, assign_mode="webservice")
    sp, _, _ = deal.deal_format("pictures")
    emit("LLM Context Effects - Format Module, Pictures (Human)", "Shopping Choices Study", "survey3_pictures",
         sp, 3, os.path.join(OUT_DIR, "survey3_pictures.qsf"), consent_text, args.completion_url,
         args.build_date, picture_mode=True, assign_mode="webservice")

if __name__ == "__main__":
    main()
