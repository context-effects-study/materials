"""generate_calibration.py: build the calibration pre-test surveys (waves 1, 2 and 3).

Wave 1 measured all 25 two-option calibration pairs. Each respondent made one choice in each of the ten
product categories that carry a pair (never the same category twice, in any format), with the pair shown
within a category dealt evenly and the order of the ten choice pages randomized, followed by one structure
comprehension-check item. Wave 2 re-tested the pairs outside the band at adjusted values and added the
realism ratings of the invented categories; wave 3 re-tested the remaining pairs, used enriched
descriptions and asked two comprehension-check items and a picture comprehension item. The adjustments of
each wave are read from its pairs file (calibration/wave2/survey/wave2_pairs.json,
calibration/wave3/survey/wave3_pairs.json) and applied in memory; stimuli.json is not changed by this
script. The fielded files, exactly as launched, are in calibration/wave*/survey/.

calibration_analysis.py imports the pair table from here, so the analysis and the instrument use one
definition of the pairs.
Manuscript: Web Appendix F.

Run: python surveys/generate_calibration.py      (wave 1)
     python surveys/generate_calibration.py --pairs-file calibration/wave2/survey/wave2_pairs.json --wave wave2
     python surveys/generate_calibration.py --pairs-file calibration/wave3/survey/wave3_pairs.json --wave wave3
"""
from __future__ import annotations
import argparse, hashlib, json, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import copy
import generate_qsf as G          # reuse the proven builders, widgets, and import-safe element shapes
import generate_survey as GS      # the LIVE image host (HOSTBASE) + the pictures-widget pattern

# Layout: root = the nearest ancestor holding stimuli/
# (working repository: two levels up from surveys/; public deposit: one level up from surveys/).
ROOT = G.ROOT
sys.path.insert(0, os.path.join(ROOT, "stimuli"))
import generate_formats as GF     # attr_words: the spelled-out words idiom (wave-2 value overrides)
import enrich as EN               # wave-3 enriched-description renderer (single content source)
import geometry as GEO            # wave-3 geometry-check cells rebuilt in memory (margin correction)
STIMULI = os.path.join(ROOT, "stimuli", "stimuli.json")
OUT_DIR = os.path.join(HERE, "out")

CALIB_VERSION = "calibration-qsf-3.0"          # 3.0 = wave-3 terminal kit (per-arm overrides + enrichment
                                               # + geometry v3 2-item deal + pic-comprehension), 2026-07-02;
                                               # 2.2 = wave-2 shared values; 2.1 = real study-info; 2.0 = bundled
SURVEY_NAME = "LLM Context Effects - Calibration Pre-test (Human)"
SURVEY_TITLE = "Shopping Choices Study"

# The calibration pre-test's REAL study-information text (the authors' 2026-07-01 call: the calibration is an
# anonymous, minimal-risk stimulus pre-test and carries plain study information, not IRB consent boilerplate;
# the five confirmatory surveys keep the PLACEHOLDER guard until the authors pastes the IRB-approved text).
# Wave-aware: the wave-2 session adds the realism block, so its stated length and task list differ.
def study_info_html(minutes_text, task_text):
    return (
        "<b>Study information</b><br><br>"
        f"In this study you will make a series of quick choices between consumer products, shown a page "
        f"at a time, plus {task_text}. The whole study takes about {minutes_text}.<br><br>"
        "Your responses are anonymous. We collect no personal information beyond the recruitment platform's "
        "identifier, which is used only to make sure each person takes the study once. You will be paid "
        "through the platform after you finish.<br><br>"
        "Taking part is voluntary and you can stop at any time. If you agree to take part, choose "
        "“Yes” below and click the arrow to begin.")

STUDY_INFO_HTML = study_info_html("3 minutes", "one short comparison question")          # wave-1 text (v2.1)
STUDY_INFO_HTML_W2 = study_info_html(
    "4 minutes", "a few short questions about the options")                              # wave-2 text (v2.2)
STUDY_INFO_HTML_W3 = study_info_html(
    "5 minutes", "a few short questions about the options you saw")                      # wave-3 text (v3.0)

# Wave-1 registered numbers (CALIBRATION_DESIGN "The wave procedure (BUNDLED design)"; re-dialed
# 2026-07-01 per the authors' cheaper directive, was 560/140). Recorded in MAPPING for the protocol; the
# generator itself is count-agnostic (recruitment happens on Prolific).
WAVE1_PARTICIPANTS = 400          # = 4 (max pairs per category) x 100 (per-pair n target)
WAVE1_N_PER_PAIR_MIN = 100

# Wave-2 session + recruitment numbers (recorded in MAPPING; recruitment happens on Prolific).
# Session: wave-1 realized median 192 s (WAVE1_LAUNCH_RECORD) + the realism block (3 rating pages + an
# optional comment, ~60 s) -> ~4.2 min expected median. That materially exceeds the wave-1 ~3-minute
# session, so pay moves proportionally: $1.00 per session ~= $14/hr at 4.2 min (inside the protocol's
# $12-15/hr fair-rate language; wave 1 realized $13.43/hr at $0.75 / 192 s).
WAVE2_N_PER_ARM_MIN = 100         # the registered per-pair precision target, unchanged
WAVE2_SESSION_MIN_EST = 4.2       # expected median minutes (192 s wave-1 median + ~60 s realism block)
WAVE2_PAY_USD = 1.00              # per participant (~$14/hr at the expected 4.2-minute median)
WAVE2_FEE_MULT = 1.3334           # wave-1 realized Prolific fee multiplier ($400.03 / $300.00)

# Wave-3 session + recruitment numbers (CALIBRATION_DESIGN wave-3 amendment (f); recorded in MAPPING).
# Session grounded on the wave-2 REALIZED export medians (total 255 s; 9.6 s/choice; 33.8 s geometry
# page; realism 17/9/8 s): 9 choices instead of 10 (-10 s), enriched cards (+~4 s x 9), a second
# geometry page (+~24 s), the picture-comprehension item (+~13 s weighted) -> ~5.0-5.3 min median.
WAVE3_PARTICIPANTS = 462          # 154/binding arm (>=150 kept at <=2.5% excl.); geometry 2N/7 = 132/structure
WAVE3_N_PER_ARM_MIN = 150         # the terminal wave's per-arm precision target (binding arms)
WAVE3_GEO_N_MIN = 120             # the cap-relief geometry floor (7x150 kept needs ~539 = ~$812 > the $700 cap)
WAVE3_SESSION_MIN_EST = 5.2       # expected median minutes (see the component build above)
WAVE3_PAY_USD = 1.13              # per participant ($696.11 all-in at 462 - inside the $700 cap;
                                  # $12.7-14.1/hr across the honest session range; the authors confirms at launch)
WAVE3_FEE_MULT = 1.3334           # the realized Prolific fee multiplier (waves 1 + 2)
WAVE3_COST_CAP = 700.00

# The geometry manipulation-check structures and their registered items (CALIBRATION_DESIGN "GEOMETRY
# CALIBRATION"). Each is shown WITH the structure's choice set; the item probes STRUCTURAL validity, NOT
# the outcome (the RR line: we calibrate that each stimulus is a VALID instance of its structure, we do
# NOT tune values until the effect appears). One item per structure; EXC is deliberately ABSENT (it
# inherits MOT's tiers; see module docstring + the path-a EXC re-derivation step).
#   key: structure code; (export-tag suffix, question text, the answer choices, the registered-correct
#   choice index 1-based). The "correct" key is the structurally-intended answer, recorded in MAPPING for
#   the analysis script's pass-rate test; it is NOT scored inside the QSF.
GEOMETRY_ITEMS = [
    # FRQ + SOT are DYNAMIC (choices=None): the v2.2 clarified items reference the lettered option cards
    # (Option A/B/C in shown order), so their choices + correct key are computed at build time from the
    # built cell via _clarified_geometry_item() - never hardcoded (the RNG stale-key lesson).
    ("FRQ", "dominance", None, None, None),
    # RNG: wording unchanged from wave 1 (a clean confirmation re-check); the ANSWER KEY is corrected
    # 1 -> 2 (2026-07-02): the rebuilt post-M1 range decoy (dominated, weak-axis-extending) ties the
    # target's strong attribute and extends the PRICE range - capacity gap 25 L vs price gap $67, so
    # "The second feature" is the literal correct reading of the built stimulus. Wave 1 re-scored at
    # this key: 29/57 = 51% (still FAIL vs 70%); see calibration/RNG_KEY_CORRECTION_2026-07-02.md.
    ("RNG", "range",
     "Look at the three options above. On which feature do the options differ by the <b>widest</b> "
     "amount (the largest gap between the lowest and the highest value)?",
     ["The first feature", "The second feature", "The features differ by about the same amount",
      "I cannot tell"], 2),
    ("PHT", "phantom_comprehension",
     "One of the options above is marked <b>currently unavailable</b>. Compared with the other "
     "options, that unavailable option is:",
     ["Better on one feature and equal or worse on the rest", "Worse on every feature",
      "Exactly the same as another option", "There was no unavailable option", "I cannot tell"], 1),
    ("SOT", "compromise_extreme", None, None, None),
    ("SYM", "upscaling_symmetric",
     "Look at the three options above. Is any one option clearly worse than <b>both</b> of the other "
     "two options?",
     ["Yes, one option is worse than both of the others", "No option is worse than both others",
      "I cannot tell"], 1),
    ("MOT", "tier_distinctness",
     "The options above fall into groups by quality level. How many <b>distinct</b> quality levels "
     "(tiers) do you see among the options?",
     ["One level", "Two levels", "Three levels", "More than three levels", "I cannot tell"], 3),
    ("SIM", "clone_recognition",
     "Look at the three options above. Are any two of the options <b>nearly identical</b> to each "
     "other (almost the same on every feature)?",
     ["Yes, two options are nearly identical", "No, all three options are clearly different",
      "I cannot tell"], 1),
]

# The geometry structures whose context cards are LETTERED (Option A/B/C) so the clarified items can
# reference a concrete option. FRQ + SOT only: the four wave-1-passing structures (PHT/SYM/MOT/SIM) and
# the RNG confirmation re-check keep the exact wave-1 presentation.
LETTERED_GEO = {"FRQ", "SOT"}
GEO_LETTERS = "ABCDEFGHIJKL"


def _clarified_geometry_item(struct, shown):
    """Build the v2.2 clarified FRQ / SOT item from the geometry cell's SHOWN option order (the same
    fixed seeded order geometry_setter_pairs renders and geo_order records). Returns
    (question_text, choices, correct_1based). The correct letter is computed, never hardcoded:
      FRQ -> the position of the dominated decoy (code DECOY);
      SOT -> the position of the new extreme (code EXTREME), with the premium/basic direction read off
             the built values (the extreme extends the premium direction when its price tops the set).
    the authors' 2026-07-02 wording decisions: FRQ = a concrete, single-target 'which one?' form;
    SOT = an explicit 'most premium / most basic' question with option references."""
    codes = [o["code"] for o in shown]
    letters = [GEO_LETTERS[i] for i in range(len(shown))]
    if struct == "FRQ":
        pos = codes.index("DECOY") + 1
        choices = [f"Yes — Option {L} is clearly worse than another option on every feature"
                   for L in letters]
        choices += ["No — every option is better than each other option on at least one feature",
                    "I cannot tell"]
        text = ("Look at the lettered options above. Is any one option clearly <b>worse than another "
                "option on every feature</b> listed? If so, which one?")
        return text, choices, pos
    if struct == "SOT":
        pos = codes.index("EXTREME") + 1
        ext = shown[pos - 1]
        prices = [o["attrs"].get("price") for o in shown]
        premium = ext["attrs"].get("price") == max(p for p in prices if p is not None)
        word, gloss = (("premium", "the highest-end option, with the most capability at the highest price")
                       if premium else
                       ("basic", "the lowest-end option, with the least capability at the lowest price"))
        choices = [f"Option {L}" for L in letters] + ["I cannot tell"]
        text = (f"Look at the lettered options above. Which option is the <b>most {word}</b> one "
                f"({gloss})?")
        return text, choices, pos
    raise ValueError(struct)


def load_stimuli():
    S = json.load(open(STIMULI, encoding="utf-8"))
    cats = {c["id"]: c for c in S["categories"]}
    by_id = {r["id"]: r for r in S["stimuli"]}
    by_cell = {(r["category"], r["structure"], r["memorization_tier"]): r for r in S["stimuli"]}
    return S, cats, by_id, by_cell


def backbone_cat(cats, cat_id):
    """A backbone category = not price-free and not the price-free variant of another (matches the
    backbone filter in generate_qsf.load_design)."""
    c = cats[cat_id]
    return (not c.get("price_free")) and (c.get("price_free_variant_of") is None)


def select_calibration_pairs(S, cats):
    """The 25 BIN calibration pairs, reconciled to the as-built stimuli.json BIN cells, in the exact
    blocks CALIBRATION_DESIGN "What gets calibrated: 25 binary pairs" specifies:
      7 published tier-1 (numbers; CHECK-only)  + 7 published tier-2 (numbers; adjustable)
    + 3 invented tier-3 (numbers; adjustable)   + 4 words-format BIN + 4 pictures-format BIN  = 25.
    Each entry: dict(arm_id, stimulus_id, block, format, category). The price-free BIN variants are NOT
    calibration pairs (they belong to Survey 4 robustness)."""
    bins = [r for r in S["stimuli"] if r["structure"] == "BIN" and backbone_cat(cats, r["category"])]
    pub_t1 = sorted(r["id"] for r in bins if cats[r["category"]]["published"] and r["memorization_tier"] == 1)
    pub_t2 = sorted(r["id"] for r in bins if cats[r["category"]]["published"] and r["memorization_tier"] == 2)
    inv_t3 = sorted(r["id"] for r in bins if not cats[r["category"]]["published"] and r["memorization_tier"] == 3)
    fmt_words = sorted(r["id"] for r in bins
                       if r.get("format_variants") and "words" in r["format_variants"])
    fmt_pics = sorted(r["id"] for r in bins
                      if r.get("format_variants") and "pictures" in r["format_variants"])
    by_id = {r["id"]: r for r in bins}
    pairs = []
    for blk, fmt, sids in (("pub_t1", "numbers", pub_t1), ("pub_t2", "numbers", pub_t2),
                           ("inv_t3", "numbers", inv_t3), ("format_words", "words", fmt_words),
                           ("format_pictures", "pictures", fmt_pics)):
        short = {"pub_t1": "pub_t1", "pub_t2": "pub_t2", "inv_t3": "inv_t3",
                 "format_words": "words", "format_pictures": "pictures"}[blk]
        for sid in sids:
            pairs.append({"arm_id": f"{short}::{sid}", "stimulus_id": sid, "block": blk,
                          "format": fmt, "category": by_id[sid]["category"]})
    return pairs, {"pub_t1": pub_t1, "pub_t2": pub_t2, "inv_t3": inv_t3,
                   "format_words": fmt_words, "format_pictures": fmt_pics}


def group_slots(pairs):
    """Group the dealt pairs by product category -> the one-per-category choice slots. Categories are
    sorted alphabetically and bound to fixed trial slots t = 1..K (the slot is a CATEGORY coordinate;
    presentation order is randomized separately by the block-order randomizer). Returns
    [(t, category, [pair, ...]), ...]."""
    by_cat = {}
    for p in pairs:
        by_cat.setdefault(p["category"], []).append(p)
    slots = []
    for t, cat in enumerate(sorted(by_cat), start=1):
        slots.append((t, cat, sorted(by_cat[cat], key=lambda p: p["arm_id"])))
    return slots


def render_words(rec, cat_meta):
    wmap = {w["code"]: w["words"] for w in rec["format_variants"]["words"]}
    return wmap


def pair_setter_pairs(arm, rec, cats, t, enr=None):
    """Resolve one BIN calibration pair -> the embedded-data field pairs for its category's trial slot t.
    Mirrors generate_qsf.script_cells / generate_survey.cells_to_pairs exactly, so the calibration export
    decodes through the SAME ingest path (same cell{t}_* field family). Pictures pairs additionally set
    cell{t}_image (canonical option order, whole-set image; the registered picture format).
    `enr` (wave 3): the category's enrichment block {option_code: {name, qualifiers}} - when present,
    option bodies render through stimuli/enrich.py (name + canonical value + qualifier; one content
    source across numbers/words) and pictures arms point at the <sid>_wave3.png enriched re-render with
    'Option X - <name>' card labels (amendment (c))."""
    cat = rec["category"]
    rng = random.Random(G.SHUFFLE_SEED + "-calib-" + arm["arm_id"])
    opts = rec["options"][:]
    order = list(range(len(opts)))
    rng.shuffle(order)                                  # shown order is a design variable, as in the main QSFs
    shown = [opts[k] for k in order]
    fmt = arm["format"]
    image_url = None
    if fmt == "words":
        if enr:
            opts_json = [{"code": o["code"], "available": o.get("available", True),
                          "html": EN.option_words_html(o, cats[cat], enr[o["code"]])} for o in shown]
        else:
            wmap = render_words(rec, cats[cat])
            opts_json = [{"code": o["code"], "available": o.get("available", True),
                          "html": "".join(f"<div class='cfx-attr'>{wmap[o['code']][a['name']]}</div>"
                                          for a in cats[cat]["attributes"] if a["name"] in wmap[o["code"]])}
                         for o in shown]
    elif fmt == "pictures":
        shown = opts                                    # canonical order: the whole-set image is pre-rendered
        if enr:
            image_url = GS.HOSTBASE.rstrip("/") + "/" + rec["id"] + "_wave3.png"
        else:
            pic = rec["format_variants"]["pictures"]
            image_url = GS.HOSTBASE.rstrip("/") + "/" + os.path.basename(pic["image_ref"]).replace(".svg", ".png")
        LETTERS = "ABCDEFG"
        opts_json = [{"code": o["code"], "available": o.get("available", True),
                      "html": (f"Option {LETTERS[i]} — {enr[o['code']]['name']}" if enr
                               else f"Option {LETTERS[i]}")} for i, o in enumerate(shown)]
    else:
        if enr:
            opts_json = [{"code": o["code"], "available": o.get("available", True),
                          "html": EN.option_numbers_html(o, cats[cat], enr[o["code"]])} for o in shown]
        else:
            opts_json = [{"code": o["code"], "available": o.get("available", True),
                          "html": G.render_option_html(rec, o, cats[cat])} for o in shown]
    pairs = [
        (f"cell{t}_calib_arm", arm["arm_id"]), (f"cell{t}_calib_block", arm["block"]),
        (f"cell{t}_id", f"{cat}_BIN"), (f"cell{t}_category", cat),
        (f"cell{t}_structure", "BIN"), (f"cell{t}_tier", str(rec["memorization_tier"])),
        (f"cell{t}_format", fmt),
        (f"cell{t}_order", ",".join(o["code"] for o in shown)),
        (f"cell{t}_stimulus", rec["id"]), (f"cell{t}_sim_placement", "NA"),
        (f"cell{t}_stem", rec["stem"]),
        (f"cell{t}_options", json.dumps(opts_json, ensure_ascii=False)),
    ]
    if image_url is not None:
        pairs.append((f"cell{t}_image", image_url))
    return pairs


def choice_html_cal(t):
    """Format-aware calibration choice page: the same widget shell as generate_survey.choice_html_pic
    (stem + optional whole-set image + radio cards + hidden piped-data textareas). The image element is
    present on every slot; the JS shows it only when the dealt pair carries cell{t}_image (a pictures
    pair) and hides it otherwise (numbers/words pairs)."""
    return (G.WIDGET_CSS +
            f"<div id='cfx-err-{t}' class='cfx-err'>The options could not be loaded. Please refresh the page; "
            f"if this persists, return to Prolific and message us.</div>"
            f"<div id='cfx-stem-{t}' class='cfx-stem'></div>"
            f"<img id='cfx-img-{t}' alt='the options, shown as magnitude bars' "
            f"style='max-width:100%;display:none;margin:0 auto 14px;border:1px solid #e3e6e9;border-radius:8px'>"
            f"<div id='cfx-opts-{t}' class='cfx-opts'></div>"
            f"<textarea id='cfx-stemdata-{t}' style='display:none'>${{e://Field/cell{t}_stem}}</textarea>"
            f"<textarea id='cfx-optsdata-{t}' style='display:none'>${{e://Field/cell{t}_options}}</textarea>"
            f"<textarea id='cfx-imgdata-{t}' style='display:none'>${{e://Field/cell{t}_image}}</textarea>")


def choice_js_cal(t):
    """Format-aware calibration widget JS (fixes stress-test defect D1): renders the whole-set image when
    the dealt pair carries one (pictures), text/word cards otherwise; holds the Next button until a choice is made;
    writes choice_t + choice_t_code. Host normalization as in generate_survey.choice_js_pic: the image
    FILENAME is joined to the HOSTBASE baked into this QSF at build time, so the QSF is the single
    authority for where pictures are served. A pictures pair whose image cannot be resolved keeps the
    page GATED with the error shown (never a silent blind choice - the D1 failure mode)."""
    return ("Qualtrics.SurveyEngine.addOnload(function(){});\n"
            "Qualtrics.SurveyEngine.addOnReady(function(){\n"
            "  var self=this, T=" + str(t) + ";\n"
            "  var HB=" + json.dumps(GS.HOSTBASE.rstrip("/")) + ";\n"
            "  function ed(k,v){ try{ Qualtrics.SurveyEngine.setEmbeddedData(k,v); }catch(e){} }\n"
            "  function $(id){ return document.getElementById(id); }\n"
            + G._gate_js(f"cfx-gate-{t}") +
            "  var rawO=($('cfx-optsdata-'+T)||{}).value||'[]';\n"
            "  var stem=($('cfx-stemdata-'+T)||{}).value||'';\n"
            "  var img=($('cfx-imgdata-'+T)||{}).value||'';\n"
            "  if(img){ img=HB+'/'+img.split('/').pop(); }\n"
            "  var opts; try{opts=JSON.parse(rawO);}catch(e){opts=[];}\n"
            "  if(!opts.length){ var er=$('cfx-err-'+T); if(er)er.style.display='block'; return; }\n"
            "  $('cfx-stem-'+T).innerHTML=stem;\n"
            "  var im=$('cfx-img-'+T);\n"
            "  if(img && im){ im.src=img; im.style.display='block'; }\n"
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


def geometry_setter_pairs(struct, rec, cats, prefix="geo", seed_tag="-calibgeo-"):
    """Resolve one geometry structure -> the embedded-data fields that render its choice set on the
    geometry page ({prefix}_* family) PLUS the shown option list (the clarified FRQ/SOT items' answer
    keys are computed from it). The geometry page SHOWS the structure's option set (read-only context
    for the manipulation-check question) using the same option JSON the choice widget reads; the actual
    answer is captured by the forced MC item {prefix}_<suffix>. {prefix}_letters=1 makes the context JS
    letter the cards (Option A/B/C, v2.2) so a clarified item can reference a concrete option; the
    wave-1-passing structures keep letters=0 (the exact wave-1 presentation). Wave 3 calls this twice
    per structure (prefix geo1/geo2, seed_tag -calibgeo3-): the shown order depends only on the SEED +
    structure, so a structure renders identically on either page and its computed key is page-invariant.
    Presentation stays the compact v2.2 numeric cards in EVERY wave (amendment (d): the re-check
    isolates the margin change; geometry cards are never enriched). Returns (field_pairs, shown)."""
    cat = rec["category"]
    rng = random.Random(G.SHUFFLE_SEED + seed_tag + struct)
    if struct == "MOT":
        # MOT carries 12 options; keep the canonical order (tier grouping is the thing being judged).
        shown = rec["options"][:]
    else:
        opts = rec["options"][:]
        order = list(range(len(opts)))
        rng.shuffle(order)
        shown = [opts[k] for k in order]
    opts_json = [{"code": o["code"], "available": o.get("available", True),
                  "html": G.render_option_html(rec, o, cats[cat])} for o in shown]
    return [
        (f"{prefix}_structure", struct),
        (f"{prefix}_category", cat),
        (f"{prefix}_stimulus", rec["id"]),
        (f"{prefix}_order", ",".join(o["code"] for o in shown)),
        (f"{prefix}_letters", "1" if struct in LETTERED_GEO else "0"),
        (f"{prefix}_stem", rec["stem"]),
        (f"{prefix}_options", json.dumps(opts_json, ensure_ascii=False)),
    ], shown


def geometry_context_html(prefix="geo"):
    """A read-only render of the geometry structure's option set above the manipulation-check question.
    Reuses the choice widget's CSS + a tiny JS that paints the cards as non-selectable context (no radio,
    no Next-criterion: the criterion lives on the forced MC item that follows). v2.2: when the dealt structure
    carries {prefix}_letters=1 (FRQ/SOT), each card gets a bold 'Option A/B/C' header in shown order so
    the clarified item can reference a concrete option; other structures render exactly as in wave 1.
    Wave 3 instantiates this twice (prefix geo1/geo2 - its two geometry pages)."""
    html = (G.WIDGET_CSS +
            f"<div id='{prefix}-stem' class='cfx-stem'></div>"
            f"<div id='{prefix}-opts' class='cfx-opts'></div>"
            f"<textarea id='{prefix}-stemdata' style='display:none'>${{e://Field/{prefix}_stem}}</textarea>"
            f"<textarea id='{prefix}-optsdata' style='display:none'>${{e://Field/{prefix}_options}}</textarea>"
            f"<textarea id='{prefix}-lettersdata' style='display:none'>${{e://Field/{prefix}_letters}}</textarea>")
    js = ("Qualtrics.SurveyEngine.addOnload(function(){});\n"
          "Qualtrics.SurveyEngine.addOnReady(function(){\n"
          "  function $(id){ return document.getElementById(id); }\n"
          "  var P=" + json.dumps(prefix) + ";\n"
          "  var rawO=($(P+'-optsdata')||{}).value||'[]';\n"
          "  var stem=($(P+'-stemdata')||{}).value||'';\n"
          "  var lettered=(($(P+'-lettersdata')||{}).value||'').trim()==='1';\n"
          "  var LET='" + GEO_LETTERS + "';\n"
          "  var opts; try{opts=JSON.parse(rawO);}catch(e){opts=[];}\n"
          "  var s=$(P+'-stem'); if(s)s.innerHTML=stem;\n"
          "  var wrap=$(P+'-opts'); if(!wrap)return;\n"
          "  opts.forEach(function(o,i){\n"
          "    var card=document.createElement('div');\n"
          "    card.className='cfx-card'+(o.available===false?' cfx-un':'');\n"
          "    var head=lettered?(\"<div style='font-weight:bold;font-size:13px;margin-bottom:4px'>Option \"+LET.charAt(i)+\"</div>\"):'';\n"
          "    card.innerHTML=head+o.html+(o.available===false?\"<span class='cfx-badge'>currently unavailable</span>\":'');\n"
          "    wrap.appendChild(card);\n"
          "  });\n"
          "});\n")
    return html, js


# ---------------- wave-2 shared-value overrides (stimuli.json UNTOUCHED) ----------------

def apply_value_overrides(by_id, cats, overrides):
    """Return {stimulus_id: effective_rec} deep copies with the pairs-kit value overrides applied in
    memory (the authors 2026-07-02: wave 2 generates from the pairs file; stimuli.json changes once, at the
    final lock). Each override is verified against the on-disk value (from) before being applied (to);
    a words variant regenerates the overridden attribute's spelled text via the SAME
    stimuli/generate_formats.attr_words idiom; a pictures variant re-points image_ref at the wave-2
    re-rendered magnitude-bar asset (<stimulus>_wave2.*) - the bars scale with the values, so the
    wave-1 image would misrepresent an overridden set. Returns (effective_by_id, applied_log)."""
    eff = {}
    applied = {}
    for cat_id, ov in (overrides or {}).items():
        sid, code, attr = ov["stimulus"], ov["option"], ov["attribute"]
        rec = copy.deepcopy(by_id[sid])
        opt = next(o for o in rec["options"] if o["code"] == code)
        cur = opt["attrs"][attr]
        if abs(float(cur) - float(ov["from"])) > 1e-9:
            raise SystemExit(f"override 'from' mismatch on {sid} {code}.{attr}: stimuli.json has {cur}, "
                             f"kit says {ov['from']} — reconcile the kit before generating")
        opt["attrs"][attr] = ov["to"]
        fv = rec.get("format_variants") or {}
        if "words" in fv:
            meta = next(a for a in cats[rec["category"]]["attributes"] if a["name"] == attr)
            for w in fv["words"]:
                if w["code"] == code:
                    w["words"][attr] = GF.attr_words(attr, meta.get("unit", ""), float(ov["to"]))
        if "pictures" in fv:
            base = os.path.basename(fv["pictures"]["image_ref"]).rsplit(".", 1)[0]
            fv["pictures"] = dict(fv["pictures"], image_ref=f"assets/{base}_wave2.png",
                                  note="wave-2 re-render at the shared overridden values "
                                       "(make_wave2_images.py); wave-1 asset untouched")
        eff[sid] = rec
        applied[cat_id] = {"stimulus": sid, "option": code, "attribute": attr,
                           "from": ov["from"], "to": ov["to"], "basis": ov.get("basis", "")}
    return eff, applied


def apply_arm_overrides(by_id, cats, arm_overrides):
    """WAVE 3 (amendment (b)): PER-ARM effective records - {arm_id: [override, ...]} where the same
    stimulus may carry different values on its numbers/words/pictures arms (the recorded departure
    from wave-2's shared values). Each override's `from` is verified against the on-disk stimuli.json
    value (the disk never changed between waves - earlier waves applied their overrides in memory
    too), then applied to the arm's own deep copy. Words/pictures re-rendering is NOT done here: in
    wave 3 the words text renders fresh from the effective values through the enrichment renderer,
    and every pictures arm points at its <sid>_wave3.png re-render. Returns (eff_by_arm, applied_log)."""
    eff, applied = {}, {}
    for arm_id, ovs in (arm_overrides or {}).items():
        rec = None
        log = []
        for ov in ovs:
            sid, code, attr = ov["stimulus"], ov["option"], ov["attribute"]
            if rec is None:
                rec = copy.deepcopy(by_id[sid])
            if rec["id"] != sid:
                raise SystemExit(f"arm {arm_id}: overrides span stimuli ({rec['id']} vs {sid})")
            opt = next(o for o in rec["options"] if o["code"] == code)
            cur = opt["attrs"][attr]
            if abs(float(cur) - float(ov["from"])) > 1e-9:
                raise SystemExit(f"arm {arm_id} override 'from' mismatch on {sid} {code}.{attr}: "
                                 f"stimuli.json has {cur}, kit says {ov['from']} — reconcile the kit")
            opt["attrs"][attr] = ov["to"]
            log.append({k: ov[k] for k in ("stimulus", "option", "attribute", "from", "to")}
                       | {"lever": ov.get("lever", ""), "basis": ov.get("basis", "")})
        if rec is not None:
            eff[arm_id] = rec
        applied[arm_id] = log
    return eff, applied


def build_wave3_geo_cells(S, cats, geo_spec):
    """WAVE 3 (amendment (d)): rebuild the 7 geometry-check cells IN MEMORY on the host category
    (robot_vacuums - locked in wave 2, dealt to no one as a wave-3 choice) from its LOCKED anchor,
    with the ONE registered margin-strengthening correction (FRQ margins + RNG range extension) as
    explicit geometry.build parameters. Every non-locked anchor coordinate is verified against
    stimuli.json (only the wave-2 locked HF price may differ from disk). Returns {structure: rec}."""
    host = geo_spec["host_category"]
    am = cats[host]["attributes"]
    bin_rec = next(r for r in S["stimuli"] if r["category"] == host and r["structure"] == "BIN")
    anc = geo_spec["host_stimulus_anchor"]
    higher = next(a["name"] for a in am if a["direction"] == "higher_better")
    lower = next(a["name"] for a in am if a["direction"] == "lower_better")
    disk = {o["code"]: o["attrs"] for o in bin_rec["options"]}
    for code in ("HF", "HD"):
        if abs(float(disk[code][higher]) - float(anc[code][higher])) > 1e-9:
            raise SystemExit(f"wave-3 geometry anchor disagrees with stimuli.json on {code}.{higher}")
    if abs(float(disk["HD"][lower]) - float(anc["HD"][lower])) > 1e-9:
        raise SystemExit(f"wave-3 geometry anchor disagrees with stimuli.json on HD.{lower}")
    anchor = {"A": {"name": higher, "hf": anc["HF"][higher], "hd": anc["HD"][higher]},
              "B": {"name": lower, "hf": anc["HF"][lower], "hd": anc["HD"][lower]}}
    fm = geo_spec["frq_margin"]
    cells = GEO.build(anchor, am, price_free=False, caps={}, tier=bin_rec["memorization_tier"],
                      cat_id=host, stem=bin_rec["stem"], decoy_target=GEO.DECOY_TARGET[host],
                      frq_margins=(fm["a_frac"], fm["b_frac"]),
                      rng_b_factor=geo_spec["rng_extension"]["b_factor"])
    return {r["structure"]: r for r in cells if r["structure"] not in ("BIN", "EXC")}


def locked_host_bin(S, cats, geo_spec):
    """The geometry host's BIN pair at its LOCKED values (in-memory copy; stimuli.json untouched):
    the disk record with the locked anchor coordinates applied. Used by the wave-3 STATIC realism
    context (the locked category is not dealt as a choice, so its enriched page is baked, not piped)."""
    host = geo_spec["host_category"]
    bin_rec = copy.deepcopy(next(r for r in S["stimuli"]
                                 if r["category"] == host and r["structure"] == "BIN"))
    anc = geo_spec["host_stimulus_anchor"]
    for o in bin_rec["options"]:
        for attr, v in anc[o["code"]].items():
            o["attrs"][attr] = v
    return bin_rec


# ---------------- the wave-2 realism block (registered spec, riding in wave 2) ----------------

REALISM_CHOICES = ["1 - Not at all realistic", "2", "3", "4", "5", "6", "7 - Completely realistic"]
REALISM_THRESHOLD = "mean >= 5.0 and no recurring confusion in comments (CALIBRATION_DESIGN step 1)"
REALISM_Q_TEXT = (
    "The product options above are from one of the choices you made earlier, shown again. "
    "How realistic do they seem to you — do they read like a <b>real product page</b> you might "
    "see when shopping online?")
REALISM_COMMENT_TEXT = (
    "Optional: if anything about the product pages in this study seemed unrealistic, confusing, "
    "or odd, please tell us here.")


def realism_context_html(t):
    """A read-only re-render of slot t's dealt product options (stem + option cards), piped from the
    SAME cell{t}_* embedded fields the choice page used - so raters judge exactly the values they saw
    (including any wave-2 shared-value override). No criterion: the forced realism MC on the same page
    carries the response requirement."""
    html = (G.WIDGET_CSS +
            f"<div id='rea-stem-{t}' class='cfx-stem'></div>"
            f"<div id='rea-opts-{t}' class='cfx-opts'></div>"
            f"<textarea id='rea-stemdata-{t}' style='display:none'>${{e://Field/cell{t}_stem}}</textarea>"
            f"<textarea id='rea-optsdata-{t}' style='display:none'>${{e://Field/cell{t}_options}}</textarea>")
    js = ("Qualtrics.SurveyEngine.addOnload(function(){});\n"
          "Qualtrics.SurveyEngine.addOnReady(function(){\n"
          "  var T=" + str(t) + ";\n"
          "  function $(id){ return document.getElementById(id); }\n"
          "  var rawO=($('rea-optsdata-'+T)||{}).value||'[]';\n"
          "  var stem=($('rea-stemdata-'+T)||{}).value||'';\n"
          "  var opts; try{opts=JSON.parse(rawO);}catch(e){opts=[];}\n"
          "  var s=$('rea-stem-'+T); if(s)s.innerHTML=stem;\n"
          "  var wrap=$('rea-opts-'+T); if(!wrap)return;\n"
          "  opts.forEach(function(o){\n"
          "    var card=document.createElement('div');\n"
          "    card.className='cfx-card'+(o.available===false?' cfx-un':'');\n"
          "    card.innerHTML=o.html+(o.available===false?\"<span class='cfx-badge'>currently unavailable</span>\":'');\n"
          "    wrap.appendChild(card);\n"
          "  });\n"
          "});\n")
    return html, js


def sq_essay(qid, tag, text, desc):
    """Multi-line text entry, NOT forced (the optional realism comment box)."""
    payload = {
        "QuestionText": text, "QuestionText_Unsafe": text, "DataExportTag": tag,
        "QuestionType": "TE", "Selector": "ML", "Configuration": {"QuestionDescriptionOption": "UseText"},
        "QuestionDescription": desc, "Validation": {"Settings": {"ForceResponse": "OFF", "Type": "None"}},
        "GradingData": [], "Language": [], "DataVisibility": {"Private": False, "Hidden": False},
        "DefaultChoices": False, "SearchSource": {"AllowFreeResponse": "false"},
        "NextChoiceId": 4, "NextAnswerId": 1, "QuestionID": qid,
    }
    return {"SurveyID": G.SID, "Element": "SQ", "PrimaryAttribute": qid,
            "SecondaryAttribute": desc, "TertiaryAttribute": None, "Payload": payload}


# ---------------- wave-3: static realism context + the picture-comprehension item ----------------

REALISM_Q_TEXT_STATIC = (
    "The product options above are from another product category in this study, shown the same way. "
    "How realistic do they seem to you — do they read like a <b>real product page</b> you might "
    "see when shopping online?")

PICCOMP_Q_TEXT = (
    "One of your earlier choices showed the options as a <b>picture</b> with bars instead of "
    "numbers; that picture is shown again above. According to the picture, which option has "
    "<b>more</b> of the quality feature shown by the <b>green</b> bars?")
PICCOMP_CHOICES = ["Option A", "Option B", "I cannot tell"]
PICCOMP_CORRECT = 2                                   # Option B - asserted from the effective values at build


def realism_static_html(rec, cat_meta, enr):
    """The wave-3 STATIC realism context (amendment (c)): the locked host category's enriched product
    page, BAKED into the question HTML at build time (the category is not dealt as a choice, so there
    is nothing to pipe). Same widget CSS + card classes as the piped contexts, so the page looks
    identical to what choice pages show."""
    cards = "".join(
        f"<div class='cfx-card'>{EN.option_numbers_html(o, cat_meta, enr[o['code']])}</div>"
        for o in rec["options"])
    return (G.WIDGET_CSS +
            f"<div class='cfx-stem'>{rec['stem']}</div>"
            f"<div class='cfx-opts'>{cards}</div>")


def piccomp_context_html(pic_slots):
    """The picture-comprehension context (amendment (e)): hidden pipes for every pictures-capable
    slot's format + image; the JS picks the respondent's FIRST dealt pictures slot, re-renders its
    image (host-normalized exactly like the choice widget), and records which slot fed it
    (piccheck_slot / piccheck_stimulus) for the analysis."""
    pipes = "".join(
        f"<textarea id='pc-fmt-{t}' style='display:none'>${{e://Field/cell{t}_format}}</textarea>"
        f"<textarea id='pc-img-{t}' style='display:none'>${{e://Field/cell{t}_image}}</textarea>"
        f"<textarea id='pc-stim-{t}' style='display:none'>${{e://Field/cell{t}_stimulus}}</textarea>"
        for t in pic_slots)
    html = (G.WIDGET_CSS +
            "<div class='cfx-stem'>Here is one of the pictures you saw earlier, shown again:</div>"
            "<img id='pc-img' alt='the options, shown as magnitude bars' "
            "style='max-width:100%;display:none;margin:0 auto 14px;border:1px solid #e3e6e9;border-radius:8px'>"
            "<div id='pc-err' class='cfx-err'>The picture could not be loaded. Please refresh the page; "
            "if this persists, return to Prolific and message us.</div>" + pipes)
    js = ("Qualtrics.SurveyEngine.addOnload(function(){});\n"
          "Qualtrics.SurveyEngine.addOnReady(function(){\n"
          "  function $(id){ return document.getElementById(id); }\n"
          "  function ed(k,v){ try{ Qualtrics.SurveyEngine.setEmbeddedData(k,v); }catch(e){} }\n"
          "  var HB=" + json.dumps(GS.HOSTBASE.rstrip("/")) + ";\n"
          "  var SLOTS=" + json.dumps(list(pic_slots)) + ";\n"
          "  var img='', slot=0, stim='';\n"
          "  for (var i=0;i<SLOTS.length;i++){ var t=SLOTS[i];\n"
          "    var f=($('pc-fmt-'+t)||{}).value||''; var u=($('pc-img-'+t)||{}).value||'';\n"
          "    if (f.trim()==='pictures' && u.trim()){ img=u.trim(); slot=t; "
          "stim=(($('pc-stim-'+t)||{}).value||'').trim(); break; } }\n"
          "  var im=$('pc-img');\n"
          "  if(img && im){ im.src=HB+'/'+img.split('/').pop(); im.style.display='block'; "
          "ed('piccheck_slot', String(slot)); ed('piccheck_stimulus', stim); }\n"
          "  else { var er=$('pc-err'); if(er)er.style.display='block'; }\n"
          "});\n")
    return html, js


def _display_logic_pics(pic_slots):
    """Display logic: show the picture-comprehension questions only when at least one pictures-format
    pair was dealt - an OR over the pictures-capable slots' cell{t}_format fields (same
    EmbeddedField/EqualTo family the geometry items use, with Qualtrics' 'Conjuction' key)."""
    conds = {}
    for i, t in enumerate(pic_slots):
        c = {"LogicType": "EmbeddedField", "LeftOperand": f"cell{t}_format", "Operator": "EqualTo",
             "RightOperand": "pictures", "_HiddenExpression": False, "Type": "Expression",
             "Description": (f"<span class=\"ConjDesc\">{'Or' if i else 'If'}</span> "
                             f"<span class=\"LeftOpDesc\">cell{t}_format</span> "
                             "<span class=\"OpDesc\">Is Equal to</span> "
                             "<span class=\"RightOpDesc\"> pictures </span>")}
        if i:
            c["Conjuction"] = "Or"
        conds[str(i)] = c
    conds["Type"] = "If"
    return {"0": conds, "Type": "BooleanExpression"}


def build(consent_text, completion_url, build_date, pairs_kit=None, wave="wave1"):
    """pairs_kit: None (all 25 pairs, wave-1 shape) or a dict {"arms": [...], "value_overrides": {...},
    "realism_categories": [...]} (the wave-2 kit; a legacy plain list is normalized by main())."""
    S, cats, by_id, by_cell = load_stimuli()
    pairs, blocks_by_type = select_calibration_pairs(S, cats)
    n_defined = len(pairs)
    assert n_defined == 25, f"expected 25 calibration pairs, got {n_defined} (reconcile against stimuli.json)"
    pair_subset = (pairs_kit or {}).get("arms")
    if pair_subset is not None:
        wanted = set(pair_subset)
        unknown = wanted - {p["arm_id"] for p in pairs}
        if unknown:
            raise SystemExit(f"--pairs-file names unknown arm ids: {sorted(unknown)}")
        pairs = [p for p in pairs if p["arm_id"] in wanted]
        if not pairs:
            raise SystemExit("--pairs-file selected zero pairs")
    wave3 = (wave == "wave3")
    # value overrides, applied to IN-MEMORY copies only (stimuli.json untouched):
    #   wave 2 - per-CATEGORY shared values;  wave 3 - PER-ARM values (amendment (b))
    eff_by_id, overrides_applied = apply_value_overrides(by_id, cats,
                                                         (pairs_kit or {}).get("value_overrides"))
    eff_by_arm, arm_overrides_applied = apply_arm_overrides(by_id, cats,
                                                            (pairs_kit or {}).get("arm_value_overrides"))
    if wave3:
        missing_ov = [p["arm_id"] for p in pairs if p["arm_id"] not in arm_overrides_applied]
        if missing_ov:
            raise SystemExit(f"wave-3 kit must list every dealt arm in arm_value_overrides "
                             f"(empty list = unchanged values); missing: {missing_ov}")
    rec_of = lambda sid: eff_by_id.get(sid, by_id[sid])
    rec_of_arm = lambda arm: eff_by_arm.get(arm["arm_id"]) or rec_of(arm["stimulus_id"])
    # wave-3 enrichment (amendment (c)): validated against the numeral-free content contract
    enrichment = {k: v for k, v in ((pairs_kit or {}).get("enrichment") or {}).items() if k != "note"}
    if wave3:
        if not enrichment:
            raise SystemExit("wave-3 kit must carry the enrichment block (amendment (c))")
        EN.validate_enrichment(enrichment, cats)
    realism_cats = list((pairs_kit or {}).get("realism_categories") or [])
    realism_static = (pairs_kit or {}).get("realism_static") or {}
    geo_spec = (pairs_kit or {}).get("geometry_wave3") if wave3 else None
    slots = group_slots(pairs)                       # [(t, category, [pair, ...])]
    K = len(slots)
    n_pairs = len(pairs)
    slot_of_cat = {cat: t for (t, cat, _) in slots}
    missing_rea = [c for c in realism_cats if c not in slot_of_cat and c not in realism_static]
    if missing_rea:
        raise SystemExit(f"realism_categories neither dealt nor static: {missing_rea}")
    if wave3:
        missing_enr = [cat for cat in list(slot_of_cat) + list(realism_static) if cat not in enrichment]
        if missing_enr:
            raise SystemExit(f"wave-3 enrichment missing categories: {missing_enr}")

    # per-survey deterministic SurveyID / ResponseSetID (re-seed generate_qsf's id generator, as
    # generate_survey.py does, so the calibration ids are stable + distinct from the five main surveys)
    G._rng = random.Random("survey-ids-calibration-" + wave)
    G.SID = G._qid("SV_")
    G.RSID = G._qid("RS_")
    SID, RSID = G.SID, G.RSID

    # geometry structures (EXC excluded by design). Resolve each structure's cell + setter FIRST: the
    # v2.2 clarified FRQ/SOT items derive their choices and answer keys from the built cell's shown
    # order (computed, never hardcoded).
    #   waves 1-2: the canonical published tier-2 cell per structure, from stimuli.json;
    #   wave 3 (amendment (d)): the 7 cells REBUILT IN MEMORY on the locked host category with the
    #   registered margin-strengthening parameters, dealt TWO per respondent (fields geo1_*/geo2_*;
    #   the shown order per structure is seed-fixed, so both pages render a structure identically).
    geo_prefixes = ("geo1", "geo2") if geo_spec else ("geo",)
    geo_seed_tag = "-calibgeo3-" if geo_spec else "-calibgeo-"
    if geo_spec:
        geo_recs = build_wave3_geo_cells(S, cats, geo_spec)
    else:
        geo_recs = {st: _canonical_geo_cell(S, cats, st) for (st, *_ ) in GEOMETRY_ITEMS
                    if any(r["structure"] == st for r in S["stimuli"])}
    geo_setter_pairs, geo_shown = {}, {}                 # prefix -> {struct: field pairs}; struct -> shown
    for st, rec in geo_recs.items():
        for pfx in geo_prefixes:
            fp, shown = geometry_setter_pairs(st, rec, cats, prefix=pfx, seed_tag=geo_seed_tag)
            geo_setter_pairs.setdefault(pfx, {})[st] = fp
            geo_shown[st] = shown
    geom = []
    for (st, suf, text, choices, correct) in GEOMETRY_ITEMS:
        if st not in geo_recs:
            continue
        if choices is None:                          # dynamic clarified item (FRQ / SOT)
            text, choices, correct = _clarified_geometry_item(st, geo_shown[st])
        geom.append((st, suf, text, choices, correct))

    # ---- block IDs ----
    BID = {n: G._qid("BL_") for n in ["consent", "instr", "demo", "debrief", "Trash"]}
    BID.update({pfx: G._qid("BL_") for pfx in geo_prefixes})     # one geometry block per page
    BID.update({f"choice{t}": G._qid("BL_") for (t, _, _) in slots})
    if wave3:
        BID["piccomp"] = G._qid("BL_")
    if realism_cats:
        BID["realism"] = G._qid("BL_")

    # ---- questions ----
    attn_text = ("To show you are reading carefully, please select <b>“Strongly agree”</b> below, "
                 "regardless of your actual opinion.")
    attn_choices = ["Strongly disagree", "Disagree", "Neither agree nor disagree", "Agree", "Strongly agree"]
    attn_correct = len(attn_choices)
    n_word = {10: "ten", 9: "nine", 8: "eight", 7: "seven", 6: "six", 5: "five", 4: "four",
              3: "three", 2: "two", 1: "one"}.get(K, str(K))
    if wave3:
        after_choices = ("you will answer a few quick questions about some further sets of options, "
                         "and rate a few product pages")
    else:
        after_choices = ("you will answer one quick question about a final set of options, and rate a few "
                         "of the product pages you saw" if realism_cats
                         else "you will answer one quick question about a final set of options")
    instr_html = (
        "<div style='max-width:720px;margin:0 auto;font-size:15px;line-height:1.65;color:#222'>"
        "<h3>How this task works</h3>"
        f"<p>This is a short study about how people read product options. On each of the next {n_word} "
        "pages you will see one shopping scenario with two options; imagine you are really shopping, and "
        "choose the <b>one</b> option you would pick. Each page is a different product. After the choices "
        f"{after_choices}.</p>"
        "<p>There are no right or wrong answers. Please read each option's details before answering. "
        "Click the arrow to begin.</p></div>")
    debrief_html = (
        "<div style='max-width:720px;margin:0 auto;font-size:15px;line-height:1.65;color:#222'>"
        "<h3>Thank you</h3><p>You have finished. This study helps us choose the product options for a "
        "later study by checking how people read them. Please do not share the specific options with "
        "future participants. Click the arrow to return to Prolific.</p></div>")

    Q = {}
    Q["consent"] = G.sq_db("QID1", "consent_q", G.consent_widget_html(consent_text), G.consent_js(), "Consent")
    if G.INCLUDE_CAPTCHA:                     # default OFF (D3, 2026-07-01); QID2 stays reserved for it
        Q["captcha"] = G.sq_captcha("QID2", "captcha_1", "Captcha")
    Q["meta"] = G.sq_meta("QID3", "browser_meta", "Browser meta")
    Q["instr"] = G.sq_db("QID4", "instructions", instr_html, None, "Instructions")
    Q["attn"] = G.sq_mc("QID5", "attention_1", attn_text, attn_choices, "Attention check")
    qn = 6
    # the K one-per-category choice pages (same timer + format-aware choice widget on each)
    for (t, cat, _) in slots:
        Q[f"timer{t}"] = G.sq_timing(f"QID{qn}", f"timer_{t}", f"Timer page {t}"); qn += 1
        Q[f"choice{t}"] = G.sq_db(f"QID{qn}", f"choice_{t}_q", choice_html_cal(t), choice_js_cal(t),
                                  f"Choice slot {t} ({cat})"); qn += 1
    # the geometry page(s): read-only context render + the forced manipulation-check MC item(s).
    # Waves 1-2: one page (prefix geo). Wave 3: two pages (geo1, geo2 - amendment (d)); each page
    # carries one MC per structure, display-logic-gated on ITS page's assigned structure.
    for gi_idx, pfx in enumerate(geo_prefixes, start=1):
        geo_html, geo_js = geometry_context_html(pfx)
        page_lbl = f" {gi_idx}" if len(geo_prefixes) > 1 else ""
        Q[f"{pfx}_timer"] = G.sq_timing(f"QID{qn}", f"{pfx}_timer", f"Timer geometry page{page_lbl}"); qn += 1
        Q[f"{pfx}_ctx"] = G.sq_db(f"QID{qn}", f"{pfx}_context_q", geo_html, geo_js,
                                  f"Geometry context{page_lbl}"); qn += 1
        for (st, suf, text, choices, correct) in geom:
            qkey = f"{pfx}_{suf}"
            Q[qkey] = G.sq_mc(f"QID{qn}", qkey, text, choices,
                              f"Geometry check{page_lbl}: {st}", force=True)
            Q[qkey]["Payload"]["DisplayLogic"] = _display_logic_geo(st, field=f"{pfx}_structure")
            qn += 1
    # the wave-3 picture-comprehension page (amendment (e)): context (re-rendered first-dealt
    # pictures image) + one forced MC, both display-logic-gated to respondents dealt >=1 pictures pair
    pic_slots = [t for (t, cat, ps) in slots if any(p["format"] == "pictures" for p in ps)]
    piccomp = bool(wave3 and pic_slots)
    if piccomp:
        # assert the uniform key from the EFFECTIVE values: canonical order is [HF, HD] and HD is
        # higher on the quality attribute in every dealt pictures pair -> correct = Option B
        for (t, cat, ps) in slots:
            qattr = next(a["name"] for a in cats[cat]["attributes"] if a["direction"] == "higher_better")
            for p in ps:
                if p["format"] != "pictures":
                    continue
                r = rec_of_arm(p)
                codes = [o["code"] for o in r["options"]]
                assert codes == ["HF", "HD"], f"{p['arm_id']}: canonical order not [HF, HD]: {codes}"
                hf, hd = r["options"][0], r["options"][1]
                assert hd["attrs"][qattr] > hf["attrs"][qattr], \
                    f"{p['arm_id']}: HD not higher on {qattr} — the uniform Option-B key would be wrong"
        pc_html, pc_js = piccomp_context_html(pic_slots)
        Q["pic_ctx"] = G.sq_db(f"QID{qn}", "pic_context_q", pc_html, pc_js,
                               "Picture comprehension context"); qn += 1
        Q["pic_ctx"]["Payload"]["DisplayLogic"] = _display_logic_pics(pic_slots)
        Q["pic_mc"] = G.sq_mc(f"QID{qn}", "pic_comprehension", PICCOMP_Q_TEXT, PICCOMP_CHOICES,
                              "Picture comprehension", force=True); qn += 1
        Q["pic_mc"]["Payload"]["DisplayLogic"] = _display_logic_pics(pic_slots)
    # the realism block's questions: per invented category (kit order), a timer + a read-only
    # re-render + a forced 7-point plausibility item; then ONE optional comment box. A category dealt
    # as a choice re-renders ITS slot (piped); a LOCKED category (wave 3: robot_vacuums) gets a STATIC
    # baked context at its locked values with the enriched description (amendment (c)).
    for i, cat in enumerate(realism_cats, start=1):
        if cat in slot_of_cat:
            t = slot_of_cat[cat]
            rhtml, rjs = realism_context_html(t)
            rtext = REALISM_Q_TEXT
        else:                                       # static (locked host category, wave 3)
            host_rec = locked_host_bin(S, cats, geo_spec)
            rhtml = realism_static_html(host_rec, cats[cat], enrichment[cat])
            rjs = None
            rtext = REALISM_Q_TEXT_STATIC
        Q[f"rea_timer{i}"] = G.sq_timing(f"QID{qn}", f"rea_timer_{i}", f"Timer realism page {i}"); qn += 1
        Q[f"rea_ctx{i}"] = G.sq_db(f"QID{qn}", f"realism_ctx_{i}", rhtml, rjs,
                                   f"Realism context {i} ({cat})"); qn += 1
        Q[f"rea_rate{i}"] = G.sq_mc(f"QID{qn}", f"realism_{cat}", rtext, REALISM_CHOICES,
                                    f"Realism rating ({cat})", force=True); qn += 1
    if realism_cats:
        Q["rea_comment"] = sq_essay(f"QID{qn}", "realism_comments", REALISM_COMMENT_TEXT,
                                    "Realism open comments"); qn += 1
    Q["gender"] = G.sq_mc(f"QID{qn}", "gender", "What is your gender?",
                          ["Woman", "Man", "Non-binary", "Prefer not to say"], "Gender", force=True); qn += 1
    Q["age"] = G.sq_text(f"QID{qn}", "age", "What is your age (in years)?", "Age", content_type="ValidNumber"); qn += 1
    Q["debrief"] = G.sq_db(f"QID{qn}", "debrief", debrief_html, None, "Debrief")

    questions = [Q["consent"]] + ([Q["captcha"]] if G.INCLUDE_CAPTCHA else []) + [Q["meta"], Q["instr"], Q["attn"]]
    for (t, _, _) in slots:
        questions += [Q[f"timer{t}"], Q[f"choice{t}"]]
    for pfx in geo_prefixes:
        questions += [Q[f"{pfx}_timer"], Q[f"{pfx}_ctx"]]
        questions += [Q[f"{pfx}_{suf}"] for (st, suf, *_ ) in geom]
    if piccomp:
        questions += [Q["pic_ctx"], Q["pic_mc"]]
    for i in range(1, len(realism_cats) + 1):
        questions += [Q[f"rea_timer{i}"], Q[f"rea_ctx{i}"], Q[f"rea_rate{i}"]]
    if realism_cats:
        questions += [Q["rea_comment"]]
    questions += [Q["gender"], Q["age"], Q["debrief"]]
    qid = lambda key: Q[key]["PrimaryAttribute"]

    # ---- blocks ----
    consent_qids = [qid("consent")] + ([qid("captcha")] if G.INCLUDE_CAPTCHA else []) + [qid("meta")]
    blocks = [
        G.block(BID["consent"], "Consent", consent_qids, btype="Default"),
        G.block(BID["instr"], "Instructions & attention", [qid("instr"), qid("attn")], page_breaks=True),
    ]
    for (t, cat, _) in slots:
        blocks.append(G.block(BID[f"choice{t}"], f"Choice slot {t} ({cat})",
                              [qid(f"timer{t}"), qid(f"choice{t}")]))    # timer + choice, same page
    for gi_idx, pfx in enumerate(geo_prefixes, start=1):
        page_lbl = f" {gi_idx}" if len(geo_prefixes) > 1 else ""
        geo_block_qids = [qid(f"{pfx}_timer"), qid(f"{pfx}_ctx")] + \
                         [qid(f"{pfx}_{suf}") for (st, suf, *_ ) in geom]
        blocks.append(G.block(BID[pfx], f"Geometry manipulation check{page_lbl}", geo_block_qids))
    if piccomp:
        blocks.append(G.block(BID["piccomp"], "Picture comprehension",
                              [qid("pic_ctx"), qid("pic_mc")]))
    if realism_cats:
        # one page per category (timer + context + forced rating), then the optional comment page
        rea_elems = []
        for i in range(1, len(realism_cats) + 1):
            if i > 1:
                rea_elems.append({"Type": "Page Break"})
            rea_elems += [{"Type": "Question", "QuestionID": qid(f"rea_timer{i}")},
                          {"Type": "Question", "QuestionID": qid(f"rea_ctx{i}")},
                          {"Type": "Question", "QuestionID": qid(f"rea_rate{i}")}]
        rea_elems += [{"Type": "Page Break"}, {"Type": "Question", "QuestionID": qid("rea_comment")}]
        blocks.append({"Type": "Standard", "SubType": "", "Description": "Realism check (invented categories)",
                       "ID": BID["realism"], "BlockElements": rea_elems,
                       "Options": {"BlockLocking": "false", "RandomizeQuestions": "false",
                                   "BlockVisibility": "Expanded"}})
    blocks += [
        G.block(BID["demo"], "Demographics", [qid("gender"), qid("age")]),
        G.block(BID["debrief"], "Debrief", [qid("debrief")]),
        {"Type": "Trash", "SubType": "", "Description": "Trash / Unused Questions",
         "ID": BID["Trash"], "BlockElements": []},
    ]
    blocks_payload = {str(i + 1): b for i, b in enumerate(blocks)}

    # ---- embedded-data declaration (rule 9: declare every field up front) ----
    fields = ["PROLIFIC_PID", "STUDY_ID", "SESSION_ID", "consent", "qsf_build", "assignment_version",
              "script_id", "calib_wave"]
    for (t, _, _) in slots:
        fields += [f"cell{t}_{s}" for s in
                   ("calib_arm", "calib_block", "id", "category", "structure", "tier", "format", "order",
                    "stimulus", "sim_placement", "stem", "options", "image")]
        fields += [f"choice_{t}", f"choice_{t}_code"]
    for pfx in geo_prefixes:
        fields += [f"{pfx}_{s}" for s in ("structure", "category", "stimulus", "order", "letters",
                                          "stem", "options")]
    if piccomp:
        fields += ["piccheck_slot", "piccheck_stimulus"]

    # ---- the per-category pair randomizers (the bundled deal) ----
    # One EvenPresentation randomizer per multi-pair category (SubSet=1 over its pair setters); a
    # single-pair category's setter is appended directly (a 1-child randomizer adds nothing).
    # rec_of() serves the effective (override-applied) record where the wave-2 kit nudged a value.
    deal_elements = []
    for (t, cat, cat_pairs) in slots:
        setters = [G.ed_set_many(pair_setter_pairs(arm, rec_of_arm(arm), cats, t,
                                                   enr=(enrichment.get(cat) if wave3 else None)))
                   for arm in cat_pairs]
        if len(setters) == 1:
            deal_elements.append(setters[0])
        else:
            deal_elements.append(G.flow_randomizer(setters, subset=1, even=True))
    # ---- the geometry dealer ----
    # waves 1-2: ONE structure per respondent (SubSet=1 over 7 single-structure setters).
    # wave 3 (amendment (d)): TWO structures per respondent from DIFFERENT structures - one
    # EvenPresentation SubSet=1 randomizer over the 42 ORDERED structure-pairs (7x6): each setter
    # writes geo1_* for its first structure and geo2_* for its second, so every structure reaches
    # n = 2N/7 with page position counterbalanced (it leads in 6 pairs and trails in 6).
    if geo_spec:
        import itertools
        geo_setters = [G.ed_set_many(geo_setter_pairs["geo1"][s1] + geo_setter_pairs["geo2"][s2])
                       for (s1, s2) in itertools.permutations(sorted(geo_recs), 2)]
    else:
        geo_setters = [G.ed_set_many(geo_setter_pairs["geo"][st]) for (st, *_ ) in geom]

    # ---- survey flow: consent -> decline branch -> instructions -> [per-category pair randomizers]
    #      -> [choice-order randomizer over the K choice blocks] -> [geometry randomizer] -> geometry
    #      block -> demographics -> debrief -> end ----
    deal_sha = hashlib.sha256(json.dumps([p["arm_id"] for p in pairs] + [st for (st, *_ ) in geom],
                                         sort_keys=True).encode()).hexdigest()[:12]
    choice_order_rnd = {"Type": "BlockRandomizer", "FlowID": None, "SubSet": K,
                        "EvenPresentation": True,
                        "Flow": [G.flow_block(BID[f"choice{t}"]) for (t, _, _) in slots]}
    flow = [
        G.ed_decl(fields),
        G.ed_set("qsf_build", f"{CALIB_VERSION}+{build_date}"),
        G.ed_set("assignment_version", deal_sha),
        G.ed_set("script_id", f"calib_{wave}"),
        G.ed_set("calib_wave", wave),
        G.flow_block(BID["consent"]),
        G.flow_branch_decline(G.flow_end(redirect_url=None)),
        G.flow_block(BID["instr"]),
        *deal_elements,
        choice_order_rnd,
        G.flow_randomizer(geo_setters, subset=1, even=True),
        *[G.flow_block(BID[pfx]) for pfx in geo_prefixes],
        *([G.flow_block(BID["piccomp"])] if piccomp else []),
        *([G.flow_block(BID["realism"])] if realism_cats else []),
        G.flow_block(BID["demo"]),
        G.flow_block(BID["debrief"]),
        G.flow_end(redirect_url=completion_url),
    ]
    max_fl = G.assign_flow_ids(flow, [1])

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
        "SurveyID": SID, "SurveyName": SURVEY_NAME + ("" if wave == "wave1" else f" [{wave}]"),
        "SurveyDescription": None, "SurveyOwnerID": None,
        "SurveyBrandID": None, "DivisionID": None, "SurveyLanguage": "EN", "SurveyActiveResponseSet": RSID,
        "SurveyStatus": "Inactive", "SurveyStartDate": "0000-00-00 00:00:00",
        "SurveyExpirationDate": "0000-00-00 00:00:00", "SurveyCreationDate": f"{build_date} 00:00:00",
        "CreatorID": None, "LastModified": f"{build_date} 00:00:00", "LastAccessed": "0000-00-00 00:00:00",
        "LastActivated": "0000-00-00 00:00:00", "Deleted": None,
    }
    qsf = {"SurveyEntry": survey_entry, "SurveyElements": elements}

    mapping = {
        "survey": "calibration",
        "version": CALIB_VERSION, "build_date": build_date, "wave": wave,
        "seed": G.SHUFFLE_SEED, "assignment_version": deal_sha,
        "n_pairs_defined": n_defined, "n_pairs_dealt": n_pairs, "n_geometry_items": len(geom),
        "include_captcha": G.INCLUDE_CAPTCHA,
        "image_hostbase": GS.HOSTBASE,
        "bundled_design": {
            "pairs_per_person": K,
            "rule": ("one binary choice per product category per respondent (never the same category "
                     "twice, in any format); pair within category dealt by EvenPresentation; the "
                     "presentation order of the choice pages randomized (SubSet=K EvenPresentation "
                     "block randomizer); trial slot t is a CATEGORY coordinate, not a presentation "
                     "position"),
            "wave1_participants": WAVE1_PARTICIPANTS,
            "wave1_n_per_pair_min": WAVE1_N_PER_PAIR_MIN,
            "wave1_arithmetic": ("the binding categories carry 4 pairs, so n per pair = participants/4; "
                                 f"{WAVE1_PARTICIPANTS}/4 = {WAVE1_PARTICIPANTS // 4} on the 4-pair "
                                 "categories; 2-pair categories get participants/2; single-pair "
                                 "categories get every respondent (CALIBRATION_DESIGN wave procedure, "
                                 "2026-07-01)"),
        },
        "slots": {str(t): {"category": cat, "arms": [p["arm_id"] for p in cat_pairs]}
                  for (t, cat, cat_pairs) in slots},
        "pairs_by_block": blocks_by_type,
        "calibration_pairs": [{"arm_id": p["arm_id"], "stimulus_id": p["stimulus_id"],
                               "block": p["block"], "format": p["format"], "category": p["category"]}
                              for p in pairs],
        "geometry_items": [{"structure": st,
                            "export_tag": f"{geo_prefixes[0]}_{suf}",
                            "export_tags": [f"{pfx}_{suf}" for pfx in geo_prefixes],
                            "stimulus_id": geo_recs[st]["id"],
                            "question_text": text, "choices": choices,
                            "lettered_context": st in LETTERED_GEO,
                            "correct_choice_key": correct, "correct_choice_label": choices[correct - 1]}
                           for (st, suf, text, choices, correct) in geom],
        "geometry_instrument_version": ("v2.2 (2026-07-02): RNG answer key corrected 1->2 to match the "
                                        "rebuilt dominated weak-axis-extending range decoy (wording "
                                        "unchanged — a confirmation re-check; wave 1 re-scored 29/57=51% "
                                        "at this key); FRQ + SOT clarified to concrete option-referencing "
                                        "forms with lettered context cards (Option A/B/C, computed keys); "
                                        "PHT/SYM/MOT/SIM identical to wave 1 (re-checks). Stimulus VALUES "
                                        "untouched. Decision rule pre-stated in CALIBRATION_DESIGN: a "
                                        "second FRQ/SOT miss of the 70% benchmark triggers ONE final "
                                        "registered margin-strengthening correction + a small wave-3 "
                                        "re-check."),
        "attention_1_correct": attn_correct, "attention_1_correct_label": attn_choices[-1],
        "target_band": {"TARGET": "40-45%", "COMP": "55-60%", "hard_flag_outside": "25-75%"},
        "value_overrides_applied": overrides_applied,
        "arm_value_overrides_applied": arm_overrides_applied or None,
        "terminal_lock_criterion": ({
            "rule": ("LOCK when the wave-3 point estimate is in [40, 45]; OR the 95% CI overlaps "
                     "[40, 45] AND the point estimate is in [33, 50] (target disadvantaged and "
                     "non-extreme). Fail -> the pre-registered stimulus-defect contingencies, "
                     "reported. Fixed 2026-07-02 in CALIBRATION_DESIGN's wave-3 amendment (a), "
                     "BEFORE any wave-3 data."),
            "band": [40.0, 45.0], "point_window": [33.0, 50.0],
        } if wave3 else None),
        "per_arm_values_note": ("WAVE 3 (amendment (b)): values are PER-ARM — the recorded departure "
                                "from wave-2's shared values (the same shared values landed "
                                "24.8-84.8% across one category's format arms). Trustworthy two-point "
                                "price solves on 4 arms; conservative single QUALITY steps on the "
                                "wrong-signed/extrapolation-only arms; water_bottles format arms "
                                "unchanged. Full per-arm trail in arm_value_overrides_applied and "
                                "calibration/wave3_pairs.json.") if wave3 else None,
        "enrichment": ({
            "spec": ("amendment (c): adjustable tiers only; per option a brand-neutral numeral-free "
                     "model name + per attribute the canonical render_value string verbatim + one "
                     "plain-language numeral-free non-comparative qualifier; ONE content source "
                     "(stimuli/enrich.py + the kit) feeds numbers/words/pictures; pictures use the "
                     "<sid>_wave3.png enriched re-renders with the attribute-naming legend (the "
                     "wave-2 water-bottles legend fix); tier-1 never enriched (none dealt)."),
            "content": enrichment,
        } if wave3 else None),
        "geometry_wave3": ({
            **geo_spec,
            "built_cells": {st: [{ "code": o["code"], "attrs": o["attrs"],
                                   "available": o.get("available", True)} for o in geo_recs[st]["options"]]
                            for st in sorted(geo_recs)},
            "deal_realized": ("42 ordered structure-pairs (7x6) under one EvenPresentation SubSet=1 "
                              "randomizer; fields geo1_*/geo2_*; per-structure n = 2N/7 "
                              f"({2 * WAVE3_PARTICIPANTS // 7} nominal at N={WAVE3_PARTICIPANTS}); "
                              "position counterbalanced (each structure leads in 6 pairs, trails in 6)."),
        } if geo_spec else None),
        "pic_comprehension": ({
            "export_tag": "pic_comprehension",
            "context_tag": "pic_context_q",
            "pictures_capable_slots": pic_slots,
            "correct_choice_key": PICCOMP_CORRECT,
            "correct_choice_label": PICCOMP_CHOICES[PICCOMP_CORRECT - 1],
            "status": ("DESCRIPTIVE comprehension indicator for the pictures manipulation "
                       "(amendment (e)); shown only when >=1 pictures pair was dealt (display "
                       "logic over the pictures-capable slots); the key (Option B = the "
                       "higher-quality HD option under the canonical order) is asserted from the "
                       "effective values at build time; NOT a registered gate."),
        } if piccomp else None),
        "wave3_deal": ({
            "participants_nominal": WAVE3_PARTICIPANTS,
            "n_per_binding_arm_nominal": WAVE3_PARTICIPANTS // 3,
            "n_per_arm_min_kept": WAVE3_N_PER_ARM_MIN,
            "geometry_n_per_structure_nominal": 2 * WAVE3_PARTICIPANTS // 7,
            "geometry_n_min": WAVE3_GEO_N_MIN,
            "session_minutes_est": WAVE3_SESSION_MIN_EST,
            "pay_usd": WAVE3_PAY_USD,
            "fee_multiplier": WAVE3_FEE_MULT,
            "cost_all_in": round(WAVE3_PARTICIPANTS * WAVE3_PAY_USD * WAVE3_FEE_MULT, 2),
            "cost_cap": WAVE3_COST_CAP,
            "arithmetic": ("9 categories carry unlocked arms (robot_vacuums locked in wave 2) -> 9 "
                           "choices per respondent; binding 3-arm categories get 462/3 = 154 nominal "
                           "(>=150 kept at the observed 1.0-2.5% exclusion rates); water_bottles 231; "
                           "singles 462; geometry 2 items/respondent -> 462*2/7 = 132 nominal per "
                           "structure (~129 kept). The $700 cap invoked the pre-stated geometry "
                           "n>=120 relief (7x150 kept needs ~539 respondents ~= $812). Session "
                           "component-built on the wave-2 REALIZED medians (255 s total; 9.6 s/choice; "
                           "33.8 s geometry page): ~5.0-5.3 min -> pay $1.13 = $696.11 all-in "
                           "($12.7-14.1/hr across the honest range; protocol language $12-15/hr; "
                           "the author confirms session + pay at launch per the standing rule; "
                           "alternative $1.25 = $770.04 if the cap is relaxed)."),
        } if wave3 else None),
        "shared_values_rule": ("the author 2026-07-02: each category's nudge derives from the NUMBERS arm's "
                               "wave-1 share; the words/pictures arms carry those SAME values (only the "
                               "format changes). stimuli.json UNTOUCHED this wave — overrides applied in "
                               "memory from the pairs kit; values lock once, at the final lock (G3). A "
                               "recurring pictures ceiling at shared values routes to the registered "
                               "no-room rule, never to per-arm values.") if overrides_applied else None,
        "realism_check": ({
            "categories": realism_cats,
            "items": [({"category": c, "slot": slot_of_cat[c], "export_tag": f"realism_{c}",
                        "stimulus_id": next(p["stimulus_id"] for p in pairs if p["category"] == c)}
                       if c in slot_of_cat else
                       {"category": c, "slot": None, "export_tag": f"realism_{c}",
                        "stimulus_id": locked_host_bin(S, cats, geo_spec)["id"],
                        "static": ("locked category (wave 2), not dealt as a wave-3 choice: baked "
                                   "context at the locked values with the enriched description")})
                      for c in realism_cats],
            "comment_tag": "realism_comments",
            "scale": REALISM_CHOICES,
            "threshold": REALISM_THRESHOLD,
            "ordering_deviation": ("the registered procedure put the ~60-rater realism check BEFORE the "
                                   "calibration wave; wave 1 fielded without it (deviation flagged in "
                                   "CALIBRATION_WAVE1 s4). The check rides IN wave 2 instead — every "
                                   "wave-2 respondent rates all three invented categories' product pages "
                                   "at the values they were shown — and the invented categories' values "
                                   "lock only after BOTH the wave-2 shares and the realism verdicts are "
                                   "in. Documented honestly in the Stage-1 pre-testing trail."),
        } if realism_cats else None),
        "wave2_deal": ({
            "n_per_arm_min": WAVE2_N_PER_ARM_MIN,
            "binding_categories": sorted(cat for (t, cat, ps) in slots if len(ps) == max(len(ps2) for (_, _, ps2) in slots)),
            "max_arms_per_category": max(len(ps) for (_, _, ps) in slots),
            "participants_nominal_100": 100 * max(len(ps) for (_, _, ps) in slots),
            "participants_recommended": 104 * max(len(ps) for (_, _, ps) in slots),
            "arithmetic": ("n per arm = participants / (arms in its category). The binding categories "
                           f"carry {max(len(ps) for (_, _, ps) in slots)} arms, so 300 participants give "
                           "exactly 100 NOMINAL per binding arm — but wave 1 realized a 2.5% exclusion "
                           "rate (392/402 kept), so 300 delivers ~97-98 KEPT. The recommended dial is "
                           f"{104 * max(len(ps) for (_, _, ps) in slots)} (104 nominal per binding arm "
                           "-> ~101 kept at the wave-1 exclusion rate; also divisible by 2 and 3 for "
                           "clean even fills). the author picks the dial at launch."),
            "session_minutes_est": WAVE2_SESSION_MIN_EST,
            "pay_usd": WAVE2_PAY_USD,
            "fee_multiplier": WAVE2_FEE_MULT,
            "cost_at_300": round(300 * WAVE2_PAY_USD * WAVE2_FEE_MULT, 2),
            "cost_at_recommended": round(104 * max(len(ps) for (_, _, ps) in slots)
                                         * WAVE2_PAY_USD * WAVE2_FEE_MULT, 2),
            "pay_note": ("the realism block lengthens the session past the wave-1 ~3 minutes (192 s "
                         f"realized median) to ~{WAVE2_SESSION_MIN_EST} min expected, so pay moves "
                         f"proportionally to ${WAVE2_PAY_USD:.2f} (~$14/hr, inside the protocol's "
                         "$12-15/hr fair-rate language; wave 1 realized $13.43/hr)."),
        } if wave == "wave2" else None),
        "exc_handling": ("EXC carries NO calibration pair and NO geometry item: it is built from MOT "
                         "(exc_from_mot) and re-derived from the LOCKED MOT tiers at G3 (build_stimuli.py "
                         "-> validate_stimuli.py), so it inherits MOT's calibrated tiers; the MOT "
                         "tier-distinctness check serves both menus (CALIBRATION_DESIGN EXC re-derivation "
                         "step)."),
        "recruitment_note": ("Calibration sample is INDEPENDENT of the confirmatory samples: a Prolific "
                             "exclusion allowlist excludes calibration participants from the four main "
                             "studies; calibration responses never enter confirmatory analyses "
                             "(CALIBRATION_DESIGN)."),
        "note": ("25 BIN pairs reconciled to the as-built stimuli.json BIN cells: 7 published tier-1 + 7 "
                 "published tier-2 + 3 invented tier-3 + 4 words + 4 pictures, spanning 10 product "
                 "categories (4+4+4+4-pair categories: the published-format ones; see slots). BUNDLED "
                 "dealing (2026-07-01): one EvenPresentation randomizer per category; each respondent "
                 "answers every category once. Same embedded-data / ingest contract as the main surveys "
                 "(cell{t}_* over t=1..K)."),
    }
    return qsf, mapping, len(questions), len([b for b in blocks if b.get("Type") != "Trash"]), n_pairs, len(geom)


def _display_logic_geo(struct, field="geo_structure"):
    """Qualtrics display logic: show this geometry MC item only when the page's assigned geometry
    structure (embedded field geo_structure - geo1_/geo2_structure on the wave-3 pages) equals this
    structure. Shape matches the branch-logic family the validator already accepts (EmbeddedField /
    EqualTo)."""
    return {"0": {"0": {
        "LogicType": "EmbeddedField", "LeftOperand": field, "Operator": "EqualTo",
        "RightOperand": struct, "_HiddenExpression": False, "Type": "Expression",
        "Description": (f"<span class=\"ConjDesc\">If</span> <span class=\"LeftOpDesc\">{field}</span> "
                        "<span class=\"OpDesc\">Is Equal to</span> <span class=\"RightOpDesc\"> "
                        + struct + " </span>")},
        "Type": "If"},
        "Type": "BooleanExpression"}


def _canonical_geo_cell(S, cats, struct):
    """One canonical cell per geometry structure: a published backbone tier-2 cell where available, else
    the first cell of that structure. The geometry check tests STRUCTURAL validity (per structure), not a
    per-category outcome, so one representative cell per structure suffices (CALIBRATION_DESIGN GEOMETRY)."""
    recs = [r for r in S["stimuli"] if r["structure"] == struct]
    pub_t2 = [r for r in recs if backbone_cat(cats, r["category"])
              and cats[r["category"]].get("published") and r["memorization_tier"] == 2]
    if pub_t2:
        return sorted(pub_t2, key=lambda r: r["id"])[0]
    bb = [r for r in recs if backbone_cat(cats, r["category"])]
    return sorted(bb or recs, key=lambda r: r["id"])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--consent-file", default=None, help="UTF-8 file with the IRB consent text (HTML ok).")
    ap.add_argument("--completion-url", default=G.PLACEHOLDER_COMPLETION)
    ap.add_argument("--build-date", default=G.BUILD_DATE_DEFAULT)
    ap.add_argument("--out", default=os.path.join(OUT_DIR, "calibration.qsf"))
    ap.add_argument("--with-captcha", action="store_true",
                    help="re-include the reCAPTCHA-v2 checkbox question (default OFF per D3, 2026-07-01).")
    ap.add_argument("--pairs-file", default=None,
                    help="JSON list of arm_ids to deal (wave 2: only the adjusted pairs).")
    ap.add_argument("--wave", default="wave1", help="wave tag stamped into calib_wave (default wave1).")
    args = ap.parse_args()
    if args.with_captcha:
        G.INCLUDE_CAPTCHA = True

    if args.consent_file:
        consent_text = open(args.consent_file, encoding="utf-8").read().strip()
    else:
        consent_text = {"wave1": STUDY_INFO_HTML, "wave2": STUDY_INFO_HTML_W2}.get(
            args.wave, STUDY_INFO_HTML_W3)
        print("[generate_calibration] using the real calibration study-info text (the default since "
              "2026-07-01; wave-2 states ~4 minutes, wave-3 ~5; pass --consent-file to override).")
    pairs_kit = None
    if args.pairs_file:
        loaded = json.load(open(args.pairs_file, encoding="utf-8"))
        # legacy shape (wave-1 era): a plain list of arm ids; v2.0 kit: a dict with arms/value_overrides/
        # realism_categories (calibration/wave2_pairs.json)
        pairs_kit = {"arms": loaded} if isinstance(loaded, list) else loaded

    os.makedirs(OUT_DIR, exist_ok=True)
    qsf, mapping, n_q, n_b, n_pairs, n_geom = build(consent_text, args.completion_url, args.build_date,
                                                    pairs_kit=pairs_kit, wave=args.wave)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(qsf, f, ensure_ascii=False)
    map_out = args.out.replace(".qsf", "_MAPPING.json")
    with open(map_out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    reloaded = json.loads(open(args.out, encoding="utf-8").read())
    rq = sum(1 for e in reloaded["SurveyElements"] if e["Element"] == "SQ")
    blp = next(e for e in reloaded["SurveyElements"] if e["Element"] == "BL")["Payload"]
    rb = len([b for b in blp.values() if b.get("Type") != "Trash"])
    print(f"[generate_calibration] wrote {args.out}")
    print(f"[generate_calibration] questions={rq} (QC={n_q}) blocks={rb} pairs_dealt={n_pairs} "
          f"slots={len(mapping['slots'])} geometry_items={n_geom} size={os.path.getsize(args.out)//1024}KB")
    print(f"[generate_calibration] mapping -> {map_out}")
    print(f"[generate_calibration] completion_url={args.completion_url}")
    assert rq == n_q and rb == n_b, "round-trip count mismatch"


if __name__ == "__main__":
    main()
