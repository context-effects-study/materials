"""generate_anchor.py: build the realism comparison survey.

Each rater saw four of the seven published categories' tier-2 product pages, dealt evenly, rendered
exactly as wave 3 rendered the invented categories' pages (same two-attribute layout, same enriched
descriptions), and rated each on the identical 7-point question "does this read like a real product
page?", with an optional comment. The survey changes no stimulus and no value; it gives the realism
threshold a comparison. The fielded file, exactly as launched, is
calibration/realism_study/survey/realism_study.qsf.
Manuscript: Web Appendix F (the realism comparison).

Run: python surveys/generate_anchor.py
"""
from __future__ import annotations
import argparse, hashlib, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_qsf as G
import generate_calibration as GC          # single-source parity: overrides, realism item, static render
import enrich as EN

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
STIMULI = os.path.join(ROOT, "stimuli", "stimuli.json")
def _first_existing(*cands):
    return next((p for p in cands if os.path.exists(p)), cands[0])
PAIRS_KIT = _first_existing(os.path.join(ROOT, "pretest", "wave3_pairs.json"),
                            os.path.join(ROOT, "calibration", "wave3", "survey", "wave3_pairs.json"))
LOCK_LIST = _first_existing(os.path.join(ROOT, "pretest", "FINAL_LOCK_LIST_2026-07-02.json"),
                            os.path.join(ROOT, "calibration", "FINAL_LOCK_LIST_2026-07-02.json"))
OUT_DIR = os.path.join(HERE, "out")

ANCHOR_VERSION = "anchor-realism-qsf-1.0"
SURVEY_NAME = "LLM Context Effects - Realism Anchor (Published Categories)"
SURVEY_TITLE = "Product Pages Study"
BUILD_DATE_DEFAULT = "2026-07-02"

PAGES_PER_RATER = 4
N_PARTICIPANTS = 112               # 112 x 4 / 7 = 64 nominal per category (>=60 kept at <=2.5% excl.)
PAY_USD = 0.40                     # ~90-120 s session -> ~$12-16/hr; the authors' task spec $0.35-0.40
FEE_MULT = 1.3334                  # the realized Prolific fee multiplier (calibration waves 1-3)

# The anchor preamble (recorded deviation): raters make no choices, so the wave preambles
# ("...from one of the choices you made earlier..." / "...from another product category in this
# study...") cannot apply. The measurement sentence + scale are VERBATIM from generate_calibration.
REALISM_Q_TEXT_ANCHOR = (
    "The product options above are from one product category. "
    "How realistic do they seem to you — do they read like a <b>real product page</b> you might "
    "see when shopping online?")
_WAVE_SENTENCE = ("How realistic do they seem to you — do they read like a <b>real product page</b> "
                  "you might see when shopping online?")
assert _WAVE_SENTENCE in GC.REALISM_Q_TEXT and _WAVE_SENTENCE in GC.REALISM_Q_TEXT_STATIC \
    and _WAVE_SENTENCE in REALISM_Q_TEXT_ANCHOR, "measurement sentence drifted from the wave item"

STUDY_INFO_HTML = (
    "<b>Study information</b><br><br>"
    "In this study you will look at a few product pages, one at a time, and rate how realistic "
    "each one seems, plus a couple of quick questions. The whole study takes about 2 minutes.<br><br>"
    "Your responses are anonymous. We collect no personal information beyond the recruitment platform's "
    "identifier, which is used only to make sure each person takes the study once. You will be paid "
    "through the platform after you finish.<br><br>"
    "Taking part is voluntary and you can stop at any time. If you agree to take part, choose "
    "“Yes” below and click the arrow to begin.")


def effective_pub_t2_records():
    """The 7 published categories' tier-2 BIN records at their wave-3 effective values, plus the
    enrichment content - every value hard-asserted against the staged lock list."""
    S, cats, by_id, _ = GC.load_stimuli()
    kit = json.load(open(PAIRS_KIT, encoding="utf-8"))
    lock = json.load(open(LOCK_LIST, encoding="utf-8"))
    enrichment = {k: v for k, v in (kit.get("enrichment") or {}).items() if k != "note"}
    EN.validate_enrichment(enrichment, cats)

    pub_cats = sorted(c for c, v in cats.items()
                      if v.get("published") and (not v.get("price_free"))
                      and v.get("price_free_variant_of") is None)
    assert len(pub_cats) == 7, pub_cats

    # apply the wave-3 per-arm overrides for the pub_t2 numbers arms (in memory; disk untouched)
    pub_ov = {a: o for a, o in (kit.get("arm_value_overrides") or {}).items() if a.startswith("pub_t2::")}
    eff_by_arm, applied = GC.apply_arm_overrides(by_id, cats, pub_ov)

    lock_by_cat = {a["category"]: a for a in lock["arms"] if a["tier"] == 2 and a["format"] == "numbers"}
    recs, trail = {}, {}
    for cat in pub_cats:
        sid = f"BIN_{cat}_t2"
        arm = f"pub_t2::{sid}"
        rec = eff_by_arm.get(arm) or by_id[sid]
        # HARD ASSERT: effective values == the staged lock list's final_values (per option/attribute)
        fv = lock_by_cat[cat]["final_values"]
        for o in rec["options"]:
            for attr, v in fv[o["code"]].items():
                assert abs(float(o["attrs"][attr]) - float(v)) < 1e-9, \
                    f"{arm}: effective {o['code']}.{attr}={o['attrs'][attr]} != lock list {v}"
        assert cat in enrichment, f"enrichment missing for {cat}"
        recs[cat] = rec
        trail[cat] = {"stimulus_id": sid, "arm_id": arm,
                      "overrides_applied": applied.get(arm, []),
                      "final_values": fv,
                      "lock_verdict": lock_by_cat[cat]["terminal_lock_verdict"]}
    return recs, cats, enrichment, trail


def build(completion_url, build_date):
    recs, cats, enrichment, trail = effective_pub_t2_records()
    pub_cats = sorted(recs)

    G._rng = random.Random("survey-ids-anchor-realism")
    G.SID = G._qid("SV_")
    G.RSID = G._qid("RS_")
    SID, RSID = G.SID, G.RSID

    BID = {n: G._qid("BL_") for n in ["consent", "instr", "comment", "demo", "debrief", "Trash"]}
    BID.update({cat: G._qid("BL_") for cat in pub_cats})

    attn_text = ("To show you are reading carefully, please select <b>“Strongly agree”</b> below, "
                 "regardless of your actual opinion.")
    attn_choices = ["Strongly disagree", "Disagree", "Neither agree nor disagree", "Agree", "Strongly agree"]
    attn_correct = len(attn_choices)
    instr_html = (
        "<div style='max-width:720px;margin:0 auto;font-size:15px;line-height:1.65;color:#222'>"
        "<h3>How this task works</h3>"
        f"<p>This is a short study about how product pages read. On each of the next {PAGES_PER_RATER} "
        "pages you will see one product page showing two options from a product category. You will not "
        "choose between them; just read the page and rate how realistic it seems.</p>"
        "<p>There are no right or wrong answers. Please read each page before answering. "
        "Click the arrow to begin.</p></div>")
    debrief_html = (
        "<div style='max-width:720px;margin:0 auto;font-size:15px;line-height:1.65;color:#222'>"
        "<h3>Thank you</h3><p>You have finished. This study helps us check how the product pages used "
        "in a later study read to real shoppers. Please do not share the specific pages with future "
        "participants. Click the arrow to return to Prolific.</p></div>")

    Q = {}
    Q["consent"] = G.sq_db("QID1", "consent_q", G.consent_widget_html(STUDY_INFO_HTML), G.consent_js(),
                           "Consent")
    Q["meta"] = G.sq_meta("QID3", "browser_meta", "Browser meta")
    Q["instr"] = G.sq_db("QID4", "instructions", instr_html, None, "Instructions")
    Q["attn"] = G.sq_mc("QID5", "attention_1", attn_text, attn_choices, "Attention check")
    qn = 6
    for cat in pub_cats:
        rhtml = GC.realism_static_html(recs[cat], cats[cat], enrichment[cat])
        Q[f"timer_{cat}"] = G.sq_timing(f"QID{qn}", f"rea_timer_{cat}", f"Timer realism ({cat})"); qn += 1
        Q[f"ctx_{cat}"] = G.sq_db(f"QID{qn}", f"realism_ctx_{cat}", rhtml, None,
                                  f"Realism context ({cat})"); qn += 1
        Q[f"rate_{cat}"] = G.sq_mc(f"QID{qn}", f"realism_{cat}", REALISM_Q_TEXT_ANCHOR,
                                   GC.REALISM_CHOICES, f"Realism rating ({cat})", force=True); qn += 1
    Q["comment"] = GC.sq_essay(f"QID{qn}", "realism_comments", GC.REALISM_COMMENT_TEXT,
                               "Realism open comments"); qn += 1
    Q["gender"] = G.sq_mc(f"QID{qn}", "gender", "What is your gender?",
                          ["Woman", "Man", "Non-binary", "Prefer not to say"], "Gender", force=True); qn += 1
    Q["age"] = G.sq_text(f"QID{qn}", "age", "What is your age (in years)?", "Age",
                         content_type="ValidNumber"); qn += 1
    Q["debrief"] = G.sq_db(f"QID{qn}", "debrief", debrief_html, None, "Debrief")

    questions = [Q["consent"], Q["meta"], Q["instr"], Q["attn"]]
    for cat in pub_cats:
        questions += [Q[f"timer_{cat}"], Q[f"ctx_{cat}"], Q[f"rate_{cat}"]]
    questions += [Q["comment"], Q["gender"], Q["age"], Q["debrief"]]
    qid = lambda key: Q[key]["PrimaryAttribute"]

    blocks = [
        G.block(BID["consent"], "Consent", [qid("consent"), qid("meta")], btype="Default"),
        G.block(BID["instr"], "Instructions & attention", [qid("instr"), qid("attn")], page_breaks=True),
    ]
    for cat in pub_cats:
        blocks.append(G.block(BID[cat], f"Realism rating ({cat})",
                              [qid(f"timer_{cat}"), qid(f"ctx_{cat}"), qid(f"rate_{cat}")]))
    blocks += [
        G.block(BID["comment"], "Realism open comments", [qid("comment")]),
        G.block(BID["demo"], "Demographics", [qid("gender"), qid("age")]),
        G.block(BID["debrief"], "Debrief", [qid("debrief")]),
        {"Type": "Trash", "SubType": "", "Description": "Trash / Unused Questions",
         "ID": BID["Trash"], "BlockElements": []},
    ]
    blocks_payload = {str(i + 1): b for i, b in enumerate(blocks)}

    fields = ["PROLIFIC_PID", "STUDY_ID", "SESSION_ID", "consent", "qsf_build"]

    deal_sha = hashlib.sha256(json.dumps(pub_cats + [PAGES_PER_RATER], sort_keys=True,
                                         default=str).encode()).hexdigest()[:12]
    flow = [
        G.ed_decl(fields),
        G.ed_set("qsf_build", f"{ANCHOR_VERSION}+{build_date}"),
        G.flow_block(BID["consent"]),
        G.flow_branch_decline(G.flow_end(redirect_url=None)),
        G.flow_block(BID["instr"]),
        G.flow_randomizer([G.flow_block(BID[cat]) for cat in pub_cats],
                          subset=PAGES_PER_RATER, even=True),
        G.flow_block(BID["comment"]),
        G.flow_block(BID["demo"]),
        G.flow_block(BID["debrief"]),
        G.flow_end(redirect_url=completion_url),
    ]
    max_fl = G.assign_flow_ids(flow, [1])

    survey_flow = {"SurveyID": SID, "Element": "FL", "PrimaryAttribute": "Survey Flow",
                   "SecondaryAttribute": None, "TertiaryAttribute": None,
                   "Payload": {"Type": "Root", "FlowID": "FL_1", "Flow": flow,
                               "Properties": {"Count": max_fl + G.FLOW_COUNT_MARGIN,
                                              "RemovedFieldsets": []}}}
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
                                  "NextButton": " &#8594; ", "SurveyTitle": SURVEY_TITLE,
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
        "SurveyID": SID, "SurveyName": SURVEY_NAME, "SurveyDescription": None, "SurveyOwnerID": None,
        "SurveyBrandID": None, "DivisionID": None, "SurveyLanguage": "EN",
        "SurveyActiveResponseSet": RSID, "SurveyStatus": "Inactive",
        "SurveyStartDate": "0000-00-00 00:00:00", "SurveyExpirationDate": "0000-00-00 00:00:00",
        "SurveyCreationDate": f"{build_date} 00:00:00", "CreatorID": None,
        "LastModified": f"{build_date} 00:00:00", "LastAccessed": "0000-00-00 00:00:00",
        "LastActivated": "0000-00-00 00:00:00", "Deleted": None,
    }
    qsf = {"SurveyEntry": survey_entry, "SurveyElements": elements}

    mapping = {
        "survey": "realism_anchor",
        "version": ANCHOR_VERSION, "build_date": build_date,
        "purpose": ("the author flag (a), CALIBRATION_WAVE3 s6.4: rate the PUBLISHED categories' tier-2 "
                    "pages on the identical 7-point 'reads like a real product page' item, so the 5.0 "
                    "realism threshold (set with no anchor) has a comparison for the invented "
                    "categories' 4.36-4.68 wave-3 scores. Changes NO stimuli, NO values."),
        "deal": {"rule": (f"one BlockRandomizer SubSet={PAGES_PER_RATER} EvenPresentation over the 7 "
                          "category rating blocks: each rater rates exactly 4 randomly assigned "
                          "categories, presentation order randomized by the same randomizer"),
                 "participants_nominal": N_PARTICIPANTS,
                 "n_per_category_nominal": N_PARTICIPANTS * PAGES_PER_RATER // 7,
                 "pay_usd": PAY_USD, "fee_multiplier": FEE_MULT,
                 "cost_all_in": round(N_PARTICIPANTS * PAY_USD * FEE_MULT, 2),
                 "assignment_version": deal_sha},
        "item": {"question_text": REALISM_Q_TEXT_ANCHOR,
                 "scale": GC.REALISM_CHOICES,
                 "comment_text": GC.REALISM_COMMENT_TEXT,
                 "preamble_deviation": ("the measurement sentence + scale are VERBATIM from the wave-2/3 "
                                        "realism item; only the one-sentence preamble differs (anchor "
                                        "raters make no choices): wave piped = 'The product options above "
                                        "are from one of the choices you made earlier, shown again.'; "
                                        "wave static = 'The product options above are from another product "
                                        "category in this study, shown the same way.'; anchor = 'The "
                                        "product options above are from one product category.'")},
        "render": ("STATIC baked context via generate_calibration.realism_static_html (the wave-3 "
                   "robot_vacuums static realism architecture): G.WIDGET_CSS + stem + cfx-card per option "
                   "+ enrich.option_numbers_html (enriched numbers format), canonical option order"),
        "categories": {cat: trail[cat] for cat in pub_cats},
        "enrichment_source": "calibration/wave3_pairs.json 'enrichment' (validated numeral-free)",
        "attention_1_correct": attn_correct, "attention_1_correct_label": attn_choices[-1],
        "exclusion_rules": ("frozen calibration rules: incomplete, duplicate PID, attention_1 != "
                            "'Strongly agree', speeder (median rating-page Page Submit < 3.0 s), "
                            "STRESS_/test PID prefixes removed"),
        "invented_wave3_comparison": {"electric_kettles": 4.36, "robot_vacuums": 4.53,
                                      "standing_desks": 4.68,
                                      "source": "rereview/CALIBRATION_WAVE3_2026-07-02.md s4 (n=459 each)"},
        "rr_hygiene": ("stimuli.json untouched; values are the wave-3 in-memory effective values, "
                       "hard-asserted against calibration/FINAL_LOCK_LIST_2026-07-02.json; anchor responses "
                       "never enter confirmatory analyses; anchor participants join the confirmatory "
                       "exclusion allowlist like all calibration participants"),
    }
    return qsf, mapping, len(questions), len([b for b in blocks if b.get("Type") != "Trash"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--completion-url", default=G.PLACEHOLDER_COMPLETION)
    ap.add_argument("--build-date", default=BUILD_DATE_DEFAULT)
    ap.add_argument("--out", default=os.path.join(OUT_DIR, "anchor_realism.qsf"))
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    qsf, mapping, n_q, n_b = build(args.completion_url, args.build_date)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(qsf, f, ensure_ascii=False)
    map_out = args.out.replace(".qsf", "_MAPPING.json")
    with open(map_out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    reloaded = json.loads(open(args.out, encoding="utf-8").read())
    rq = sum(1 for e in reloaded["SurveyElements"] if e["Element"] == "SQ")
    blp = next(e for e in reloaded["SurveyElements"] if e["Element"] == "BL")["Payload"]
    rb = len([b for b in blp.values() if b.get("Type") != "Trash"])
    fl = next(e for e in reloaded["SurveyElements"] if e["Element"] == "FL")["Payload"]
    rnd = [x for x in fl["Flow"] if x.get("Type") == "BlockRandomizer"]
    assert rq == n_q and rb == n_b, "round-trip count mismatch"
    assert len(rnd) == 1 and rnd[0]["SubSet"] == PAGES_PER_RATER and len(rnd[0]["Flow"]) == 7
    assert fl["Properties"]["Count"] > max(
        int(x["FlowID"].split("_")[1]) for x in rnd[0]["Flow"])
    print(f"[generate_anchor] wrote {args.out}")
    print(f"[generate_anchor] questions={rq} blocks={rb} randomizer=SubSet {rnd[0]['SubSet']} of "
          f"{len(rnd[0]['Flow'])} flow_count={fl['Properties']['Count']} "
          f"size={os.path.getsize(args.out)//1024}KB")
    print(f"[generate_anchor] mapping -> {map_out}")
    print(f"[generate_anchor] completion_url={args.completion_url}")


if __name__ == "__main__":
    main()
