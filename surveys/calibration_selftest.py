#!/usr/bin/env python3
"""calibration_selftest.py: rebuild the design of each fielded calibration survey from the file and check it.

Using only a wave's survey file and mapping (calibration/wave*/survey/), it checks that every calibration
pair of the wave is present, that each choice slot is bound to one product category (so no respondent can
see a category twice), that pairs fill evenly within a category, that the order of the choice pages is
randomized, that pictures pairs carry an image, that the comprehension items attach to the right
structures, that every value adjustment of the wave's pairs file appears in the shown option text, and
that the embedded-data fields match what calibration_analysis.py reads. The fielded waves were built from
the stimulus file as it stood before the final calibration lock, preserved as stimuli/stimuli_prelock.json.

Run: python surveys/calibration_selftest.py [--wave2 | --wave3]
"""
import json, os, collections, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_survey as GS                     # the live HOSTBASE the picture URLs must sit on

# Layout: root = the nearest ancestor holding stimuli/
# (working repository: two levels up; public deposit: one level up from surveys/). The fielded calibration
# instruments live in ./out/ in the working repository and at <root>/calibration/instruments/ in the
# deposit; the wave kits live at <root>/calibration/ (working repository) or <root>/calibration/ (deposit).
ROOT = GS.G.ROOT
def _first_existing(*cands):
    return next((p for p in cands if os.path.exists(p)), cands[0])
_RELEASE_INSTRUMENTS = {
    "calibration.qsf": "wave1/survey/calibration_wave1.qsf",
    "calibration_MAPPING.json": "wave1/survey/calibration_wave1_MAPPING.json",
    "calibration_wave2.qsf": "wave2/survey/calibration_wave2.qsf",
    "calibration_wave2_MAPPING.json": "wave2/survey/calibration_wave2_MAPPING.json",
    "calibration_wave3.qsf": "wave3/survey/calibration_wave3.qsf",
    "calibration_wave3_MAPPING.json": "wave3/survey/calibration_wave3_MAPPING.json",
}
def _artifact(name):
    return _first_existing(os.path.join(HERE, "out", name),
                           os.path.join(ROOT, "calibration", *_RELEASE_INSTRUMENTS.get(name, name).split("/")))
# Note: the calibration waves are COMPLETE and their QSFs are fixed FIELDED
# artifacts, generated from the PRE-LOCK stimulus source. the final calibration lock then wrote the calibrated
# values into stimuli.json (and removed the exited pictures hard-drives variant), so the live
# file no longer derives the 25-pair pre-lock design the wave instruments carried. The selftest
# therefore validates the wave artifacts against the preserved pre-lock snapshot
# (stimuli/stimuli_prelock.json), byte-for-byte the source they were built from; if
# the snapshot is ever absent it falls back to the live file (and the derived-set check will
# then report the final calibration exit).
_SNAPSHOT = os.path.join(ROOT, "stimuli", "stimuli_prelock.json")
STIMULI = _SNAPSHOT if os.path.exists(_SNAPSHOT) else os.path.join(ROOT, "stimuli", "stimuli.json")
KIT = _first_existing(os.path.join(ROOT, "pretest", "wave2_pairs.json"),
                      os.path.join(ROOT, "calibration", "wave2", "survey", "wave2_pairs.json"))
KIT3 = _first_existing(os.path.join(ROOT, "pretest", "wave3_pairs.json"),
                       os.path.join(ROOT, "calibration", "wave3", "survey", "wave3_pairs.json"))

WAVES = {
    "wave1": {
        "qsf": _artifact("calibration.qsf"),
        "map": _artifact("calibration_MAPPING.json"),
        "n_pairs": 25, "n_slots": 10,
        "block_counts": {"pub_t1": 7, "pub_t2": 7, "inv_t3": 3, "format_words": 4, "format_pictures": 4},
        "cat_multiplicity": sorted([4, 4, 4, 4, 2, 2, 2, 1, 1, 1]),
        "rnd_sizes": [2, 2, 2, 4, 4, 4, 4],
        "n_direct": 3,
        "fmt_mix": {"numbers": 17, "words": 4, "pictures": 4},
        "geo_prefixes": ("geo",),
    },
    "wave2": {
        "qsf": _artifact("calibration_wave2.qsf"),
        "map": _artifact("calibration_wave2_MAPPING.json"),
        "n_pairs": 17, "n_slots": 10,
        "block_counts": {"pub_t2": 6, "inv_t3": 3, "format_words": 4, "format_pictures": 4},
        "cat_multiplicity": sorted([3, 3, 3, 2, 1, 1, 1, 1, 1, 1]),
        "rnd_sizes": [2, 3, 3, 3],
        "n_direct": 6,
        "fmt_mix": {"numbers": 9, "words": 4, "pictures": 4},
        "geo_prefixes": ("geo",),
    },
    "wave3": {
        "qsf": _artifact("calibration_wave3.qsf"),
        "map": _artifact("calibration_wave3_MAPPING.json"),
        "n_pairs": 16, "n_slots": 9,
        "block_counts": {"pub_t2": 6, "inv_t3": 2, "format_words": 4, "format_pictures": 4},
        "cat_multiplicity": sorted([3, 3, 3, 2, 1, 1, 1, 1, 1]),
        "rnd_sizes": [2, 3, 3, 3],
        "n_direct": 5,
        "fmt_mix": {"numbers": 8, "words": 4, "pictures": 4},
        "geo_prefixes": ("geo1", "geo2"),
    },
}
GEO_STRUCTS = {"FRQ", "RNG", "PHT", "SOT", "SYM", "MOT", "SIM"}      # EXC deliberately absent


def fields_of(setter):
    return {d["Field"]: d.get("Value") for d in setter["EmbeddedData"]}


def main():
    wave = "wave3" if "--wave3" in sys.argv else ("wave2" if "--wave2" in sys.argv else "wave1")
    W = WAVES[wave]
    prefixes = W["geo_prefixes"]
    qsf = json.load(open(W["qsf"], encoding="utf-8"))
    mapping = json.load(open(W["map"], encoding="utf-8"))
    S = json.load(open(STIMULI, encoding="utf-8"))
    by_id = {r["id"]: r for r in S["stimuli"]}
    cats = {c["id"]: c for c in S["categories"]}
    kit = {}
    if wave == "wave2":
        kit = json.load(open(KIT, encoding="utf-8"))
    elif wave == "wave3":
        kit = json.load(open(KIT3, encoding="utf-8"))
    overrides = kit.get("value_overrides", {}) if wave == "wave2" else {}
    arm_overrides = kit.get("arm_value_overrides", {}) if wave == "wave3" else {}

    els = qsf["SurveyElements"]
    flow = next(e for e in els if e["Element"] == "FL")["Payload"]["Flow"]
    fl_payload = next(e for e in els if e["Element"] == "FL")["Payload"]
    sqs = [e for e in els if e["Element"] == "SQ"]
    bl_blocks = list(next(e for e in els if e["Element"] == "BL")["Payload"].values())

    checks = []
    def ck(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    # ---- classify the flow's dealing elements ----
    pair_rnds = []            # per-category EvenPresentation randomizers over pair setters
    direct_setters = []       # single-pair categories appended directly
    geo_rnd = None
    order_rnd = None          # the SubSet=K presentation-order randomizer over the choice BLOCKS
    for e in flow:
        if e["Type"] == "BlockRandomizer":
            kids = e.get("Flow", [])
            if kids and kids[0].get("Type") == "EmbeddedData":
                sample = fields_of(kids[0])
                if f"{prefixes[0]}_structure" in sample:
                    geo_rnd = e
                elif any(k.endswith("_calib_arm") for k in sample):
                    pair_rnds.append(e)
            elif kids and kids[0].get("Type") == "Standard":
                order_rnd = e
        elif e["Type"] == "EmbeddedData":
            kv = fields_of(e)
            # a SETTER carries values; the up-front DECLARATION (flow[0]) declares the same field
            # names with no Value and must not be counted as a pair setter
            if any(k.endswith("_calib_arm") and v for k, v in kv.items()):
                direct_setters.append(e)

    # 0. the dealing skeleton: per-category randomizers + direct singletons + order randomizer + geometry
    n_multi = len(W["rnd_sizes"])
    ck(f"per-category pair randomizers present ({n_multi} multi-pair categories)",
       len(pair_rnds) == n_multi, f"{len(pair_rnds)} randomizers (expect {n_multi})")
    ck(f"single-pair categories set directly ({W['n_direct']})", len(direct_setters) == W["n_direct"],
       f"{len(direct_setters)} direct setters")
    ck("every pair randomizer SubSet=1 + EvenPresentation",
       all(r.get("SubSet") == 1 and r.get("EvenPresentation") is True for r in pair_rnds))
    ck("a geometry randomizer is present (SubSet=1 + EvenPresentation)",
       geo_rnd is not None and geo_rnd.get("SubSet") == 1 and geo_rnd.get("EvenPresentation") is True)
    ck("a presentation-order randomizer runs the choice blocks", order_rnd is not None)

    # 1. collect every pair setter; group by slot; check the slot<->category bijection
    all_setters = [s for r in pair_rnds for s in r["Flow"]] + direct_setters
    arms = {}
    slot_of_arm = {}
    slot_cats = collections.defaultdict(set)
    per_slot_arms = collections.defaultdict(list)
    for s in all_setters:
        kv = fields_of(s)
        slots_here = sorted({int(k.replace("cell", "").split("_")[0]) for k in kv if k.startswith("cell")})
        arm = next((v for k, v in kv.items() if k.endswith("_calib_arm")), None)
        arms[arm] = kv
        ok_one_slot = len(slots_here) == 1
        if not ok_one_slot:
            ck(f"setter {arm} writes exactly one slot", False, f"slots={slots_here}")
            continue
        t = slots_here[0]
        slot_of_arm[arm] = t
        slot_cats[t].add(kv.get(f"cell{t}_category"))
        per_slot_arms[t].append(arm)
    ck(f"{W['n_pairs']} pair setters, one per pair", len(all_setters) == W["n_pairs"],
       f"{len(all_setters)} setters")
    ck(f"arm ids unique ({W['n_pairs']} distinct arms)", len(arms) == W["n_pairs"], f"{len(arms)} distinct")
    ck(f"{W['n_slots']} slots, each bound to exactly ONE category (bijection -> no category repeat is STRUCTURAL)",
       len(slot_cats) == W["n_slots"] and all(len(v) == 1 for v in slot_cats.values())
       and len({next(iter(v)) for v in slot_cats.values()}) == W["n_slots"],
       f"slots={ {t: sorted(v) for t, v in sorted(slot_cats.items())} }")

    # 2. even fill within category by construction: each multi-pair category's arms sit in ONE
    #    SubSet=1 EvenPresentation randomizer (so its pairs are dealt evenly); multiplicities match.
    mult = sorted(len(v) for v in per_slot_arms.values())
    ck(f"category multiplicities = {W['cat_multiplicity']} (every pair dealt; even fill per category)",
       mult == W["cat_multiplicity"], f"{mult}")
    rnd_sizes = sorted(len(r["Flow"]) for r in pair_rnds)
    ck(f"pair-randomizer sizes = the multi-pair multiplicities {W['rnd_sizes']}",
       rnd_sizes == W["rnd_sizes"], f"{rnd_sizes}")

    # 3. each pair resolves to the right backbone BIN cell + valid option JSON + order permutation
    bad_resolve = bad_optjson = order_bad = not_bin = 0
    block_counter = collections.Counter()
    fmt_counter = collections.Counter()
    pic_img_ok = True
    pic_img_detail = ""
    for arm, kv in arms.items():
        t = slot_of_arm.get(arm)
        blk = kv.get(f"cell{t}_calib_block")
        block_counter[blk or "?"] += 1
        fmt = kv.get(f"cell{t}_format")
        fmt_counter[fmt or "?"] += 1
        sid = kv.get(f"cell{t}_stimulus")
        rec = by_id.get(sid)
        if rec is None or rec["structure"] != "BIN":
            not_bin += 1; continue
        c = cats[rec["category"]]
        if c.get("price_free") or c.get("price_free_variant_of"):
            bad_resolve += 1; continue
        try:
            opts = json.loads(kv.get(f"cell{t}_options", ""))
        except Exception:
            bad_optjson += 1; continue
        rec_codes = [o["code"] for o in rec["options"]]
        if len(opts) != len(rec_codes) or {o["code"] for o in opts} != set(rec_codes):
            bad_optjson += 1
        order_codes = (kv.get(f"cell{t}_order") or "").split(",")
        if sorted(order_codes) != sorted(rec_codes):
            order_bad += 1
        if blk == "format_words" and fmt != "words":
            bad_resolve += 1
        if blk == "format_pictures":
            img = kv.get(f"cell{t}_image", "")
            if fmt != "pictures" or not img:
                bad_resolve += 1
            # the D1 fix: the image URL must sit on the REAL host and name the stimulus PNG.
            # Wave 2: an overridden category's image is the wave-2 re-render (<sid>_wave2.png);
            # a no-override category (water_bottles) reuses its wave-1 image (<sid>.png).
            # Wave 3: EVERY pictures arm is the enriched wave-3 re-render (<sid>_wave3.png) - 
            # content changed for all four (amendment (c)), values per-arm for three.
            if wave == "wave3":
                want_png = sid + "_wave3.png"
            else:
                want_png = (sid + "_wave2.png") if rec["category"] in overrides else (sid + ".png")
            if not (img.startswith(GS.HOSTBASE.rstrip("/") + "/") and img.endswith(want_png)):
                pic_img_ok = False; pic_img_detail = f"{arm}: {img} (want ...{want_png})"
            if order_codes != rec_codes:
                order_bad += 1              # pictures keep the canonical (image) order, never shuffled
    ck("every pair resolves to a backbone BIN cell", not_bin == 0 and bad_resolve == 0,
       f"not_bin={not_bin} bad_resolve={bad_resolve}")
    ck("every pair option block valid JSON w/ matching codes", bad_optjson == 0, f"{bad_optjson} bad")
    ck("every pair shown order is a permutation (pictures: canonical)", order_bad == 0, f"{order_bad} bad")
    ck("pictures pairs carry the REAL-host stimulus PNG URL (D1 fix; wave-2 names where overridden)",
       pic_img_ok, pic_img_detail or f"host={GS.HOSTBASE}")

    # 4. the block split matches the wave's design
    ck(f"block split = {W['block_counts']}",
       dict(block_counter) == W["block_counts"], f"{dict(block_counter)}")
    ck(f"format mix = {W['fmt_mix']}",
       all(fmt_counter.get(k) == v for k, v in W["fmt_mix"].items())
       and sum(fmt_counter.values()) == W["n_pairs"], f"{dict(fmt_counter)}")

    # 5. tiers per block correct (t1/t2/t3)
    tier_ok = True
    for arm, kv in arms.items():
        t = slot_of_arm.get(arm)
        blk, tier = kv.get(f"cell{t}_calib_block"), int(kv.get(f"cell{t}_tier", -1))
        if blk == "pub_t1" and tier != 1: tier_ok = False
        if blk == "pub_t2" and tier != 2: tier_ok = False
        if blk == "inv_t3" and tier != 3: tier_ok = False
    ck("memorization tiers per block correct (t1/t2/t3)", tier_ok)

    # 6. the emitted pairs exactly equal the designed set (independent recompute)
    def backbone(r):
        c = cats[r["category"]]
        return (not c.get("price_free")) and (c.get("price_free_variant_of") is None)
    bins = [r for r in S["stimuli"] if r["structure"] == "BIN" and backbone(r)]
    short = {"pub_t1": "pub_t1", "pub_t2": "pub_t2", "inv_t3": "inv_t3",
             "format_words": "words", "format_pictures": "pictures"}
    want_all = set()
    for r in bins:
        if cats[r["category"]]["published"] and r["memorization_tier"] == 1: want_all.add(("pub_t1", r["id"]))
        if cats[r["category"]]["published"] and r["memorization_tier"] == 2: want_all.add(("pub_t2", r["id"]))
        if not cats[r["category"]]["published"] and r["memorization_tier"] == 3: want_all.add(("inv_t3", r["id"]))
        if r.get("format_variants") and "words" in r["format_variants"]: want_all.add(("format_words", r["id"]))
        if r.get("format_variants") and "pictures" in r["format_variants"]: want_all.add(("format_pictures", r["id"]))
    if wave in ("wave2", "wave3"):
        kit_arms = set(kit["arms"])
        want = {(b, sid) for (b, sid) in want_all if f"{short[b]}::{sid}" in kit_arms}
    else:
        want = want_all
    got = {(kv.get(f"cell{slot_of_arm[a]}_calib_block"), kv.get(f"cell{slot_of_arm[a]}_stimulus"))
           for a, kv in arms.items() if a in slot_of_arm}
    ck(f"the {W['n_pairs']} emitted pairs == the designed set (independent recompute)", got == want,
       f"missing={sorted(want - got)[:3]} extra={sorted(got - want)[:3]}")

    # 7. the presentation-order randomizer runs ALL K choice blocks, SubSet=K, EvenPresentation
    choice_blocks = [b for b in bl_blocks if str(b.get("Description", "")).startswith("Choice slot")]
    order_ids = {e.get("ID") for e in (order_rnd or {}).get("Flow", [])}
    ck("K choice blocks exist (one per slot)", len(choice_blocks) == W["n_slots"], f"{len(choice_blocks)} blocks")
    ck("order randomizer SubSet=K over exactly the K choice blocks (EvenPresentation)",
       order_rnd is not None and order_rnd.get("SubSet") == W["n_slots"]
       and order_rnd.get("EvenPresentation") is True
       and order_ids == {b["ID"] for b in choice_blocks},
       f"SubSet={order_rnd.get('SubSet') if order_rnd else None} ids={len(order_ids)}")

    # 8. geometry randomizer: waves 1-2 deal ONE structure (7 single setters); wave 3 deals TWO from
    #    different structures (42 ordered-pair setters, fields geo1_*/geo2_*). geo_kv[prefix][struct]
    #    keeps the first-seen field set per structure per page position (the shown order is seed-fixed
    #    per structure, so any pair setter carrying it is representative).
    geo_setters = geo_rnd["Flow"] if geo_rnd else []
    geo_bad = 0
    geo_kv = {pfx: {} for pfx in prefixes}
    pos_counts = {pfx: collections.Counter() for pfx in prefixes}
    same_pairs = 0
    for s in geo_setters:
        kv = fields_of(s)
        sts = {}
        for pfx in prefixes:
            st = kv.get(f"{pfx}_structure")
            sts[pfx] = st
            pos_counts[pfx][st] += 1
            prev = geo_kv[pfx].get(st)
            sub = {k: v for k, v in kv.items() if k.startswith(pfx + "_")}
            if prev is not None and prev != sub:
                geo_bad += 1                       # a structure must render identically on a page position
            geo_kv[pfx][st] = sub
            rec = by_id.get(kv.get(f"{pfx}_stimulus"))
            if rec is None or rec["structure"] != st:
                geo_bad += 1
            try:
                json.loads(kv.get(f"{pfx}_options", ""))
            except Exception:
                geo_bad += 1
        if len(prefixes) == 2 and sts[prefixes[0]] == sts[prefixes[1]]:
            same_pairs += 1
    n_setters_want = 42 if len(prefixes) == 2 else 7
    ck(f"geometry dealer carries {n_setters_want} setters "
       f"({'42 ordered structure-pairs' if len(prefixes) == 2 else 'one per structure'})",
       len(geo_setters) == n_setters_want, f"{len(geo_setters)} setters")
    ck("geometry arms exactly cover the 7 geometry structures (every page position)",
       all(set(pos_counts[pfx]) == GEO_STRUCTS for pfx in prefixes),
       f"{ {p: sorted(pos_counts[p]) for p in prefixes} }")
    if len(prefixes) == 2:
        ck("wave-3 pair deal: each structure leads in 6 pairs and trails in 6; ZERO same-structure pairs",
           all(all(c == 6 for c in pos_counts[pfx].values()) for pfx in prefixes) and same_pairs == 0,
           f"same_pairs={same_pairs} counts={dict(pos_counts[prefixes[0]])}")
    ck("EXC carries NO geometry arm (path-a: inherits MOT)",
       all("EXC" not in pos_counts[pfx] for pfx in prefixes))
    ck("every geometry arm resolves to a cell of its structure (+ page-invariant field sets)",
       geo_bad == 0, f"{geo_bad} bad")

    # 9. one forced geometry MC item per structure PER PAGE, gated by display logic on its page's
    #    {prefix}_structure field
    items_ok = True
    n_items_total = 0
    geo_items_all = []
    for pfx in prefixes:
        geo_items = [q for q in sqs if str(q["Payload"].get("DataExportTag", "")).startswith(pfx + "_")
                     and q["Payload"].get("QuestionType") == "MC"]
        geo_items_all += geo_items
        n_items_total += len(geo_items)
        item_structs = set()
        for q in geo_items:
            p = q["Payload"]
            if p["Validation"]["Settings"].get("ForceResponse") != "ON":
                items_ok = False
            dl = p.get("DisplayLogic")
            if not dl:
                items_ok = False; continue
            cond = dl["0"]["0"]
            if cond.get("LeftOperand") != f"{pfx}_structure" or cond.get("Operator") != "EqualTo":
                items_ok = False
            item_structs.add(cond.get("RightOperand"))
        if item_structs != GEO_STRUCTS:
            items_ok = False
    ck(f"one forced geometry MC item per structure per page ({7 * len(prefixes)} items, display-logic'd)",
       items_ok and n_items_total == 7 * len(prefixes), f"{n_items_total} items")

    # 10. geometry items live in the Geometry block(s)
    geo_blocks = [b for b in bl_blocks if str(b.get("Description", "")).startswith("Geometry")]
    geo_qids_in_block = {el.get("QuestionID") for b in geo_blocks for el in b.get("BlockElements", [])
                         if el.get("Type") == "Question"}
    geo_block = geo_blocks[0] if geo_blocks else None
    ck(f"all geometry items live in the {len(prefixes)} Geometry block(s)",
       len(geo_blocks) == len(prefixes)
       and all(q["PrimaryAttribute"] in geo_qids_in_block for q in geo_items_all))

    # 11. the K choice widgets are FORMAT-AWARE: each reads cell{t}_options AND cell{t}_image, joins the
    #     image filename onto the QSF-baked host, and writes choice_{t} (+ _code) - the D1 fix, per slot.
    widget_ok = True
    widget_detail = ""
    for t in sorted(slot_cats):
        q = next((q for q in sqs if q["Payload"].get("DataExportTag") == f"choice_{t}_q"), None)
        if q is None:
            widget_ok = False; widget_detail = f"choice_{t}_q missing"; break
        html = q["Payload"]["QuestionText"]
        js = q["Payload"].get("QuestionJS", "")
        if (f"cell{t}_options" not in html or f"cell{t}_image" not in html
                or "'choice_'+T" not in js or GS.HOSTBASE.rstrip("/") not in js
                or "split('/').pop()" not in js):
            widget_ok = False; widget_detail = f"slot {t} widget not format-aware/host-normalizing"; break
    ck("every choice widget is format-aware (reads cell{t}_image, host-normalizes, writes choice_{t})",
       widget_ok, widget_detail)

    # 12. embedded-data contract: cell{1..K}_* families + choice_{t}/_code + geo_* declared (ingest-ready)
    decl = {d["Field"] for d in flow[0]["EmbeddedData"]}
    need = set()
    for t in range(1, W["n_slots"] + 1):
        need |= {f"cell{t}_{s}" for s in ("calib_arm", "calib_block", "id", "category", "structure",
                                          "tier", "format", "order", "stimulus", "sim_placement",
                                          "stem", "options", "image")}
        need |= {f"choice_{t}", f"choice_{t}_code"}
    for pfx in prefixes:
        need |= {f"{pfx}_{s}" for s in ("structure", "category", "stimulus", "order", "stem", "options")}
        if wave in ("wave2", "wave3"):
            need |= {f"{pfx}_letters"}
    need |= {"PROLIFIC_PID", "consent", "script_id", "calib_wave"}
    if wave == "wave3":
        need |= {"piccheck_slot", "piccheck_stimulus"}
    missing = need - decl
    ck("ingest-contract embedded fields all declared up front", not missing, f"missing={sorted(missing)[:5]}")

    # 13. PHT geometry context carries an unavailable (phantom) option (every page position)
    p0 = prefixes[0]
    pht_ok = True
    for pfx in prefixes:
        pht_opts = json.loads(geo_kv[pfx].get("PHT", {}).get(f"{pfx}_options", "[]"))
        pht_ok &= any(o.get("available") is False for o in pht_opts)
    ck("PHT geometry context carries an unavailable (phantom) option", pht_ok)

    # 14. MOT geometry context carries 3 distinct quality tiers (wave 3: from the mapping's rebuilt
    #     cells - the in-memory wave-3 cells intentionally differ from stimuli.json's values)
    if wave == "wave3":
        mot_cells = (mapping.get("geometry_wave3") or {}).get("built_cells", {}).get("MOT", [])
        mot_tiers = {tuple(sorted(o["attrs"].items())) for o in mot_cells}
        ck("MOT geometry context carries 3 distinct quality tiers (rebuilt cell)",
           len(mot_cells) == 12 and len(mot_tiers) == 3, f"{len(mot_cells)} options, {len(mot_tiers)} tiers")
    else:
        mot_setter = geo_kv[p0].get("MOT", {})
        mot_rec = by_id.get(mot_setter.get(f"{p0}_stimulus")) if mot_setter else None
        mot_tiers = {o.get("tier") for o in (mot_rec["options"] if mot_rec else [])}
        ck("MOT geometry context carries 3 distinct quality tiers", len(mot_tiers) == 3,
           f"tiers={sorted(mot_tiers)}")

    # 15. attention check present, forced, pass key recorded & matches
    attn = next((q for q in sqs if q["Payload"].get("DataExportTag") == "attention_1"), None)
    key = mapping.get("attention_1_correct")
    attn_ok = bool(attn) and attn["Payload"]["Validation"]["Settings"].get("ForceResponse") == "ON" and \
        key and len(attn["Payload"]["Choices"]) == key and \
        attn["Payload"]["Choices"][str(key)]["Display"] == mapping.get("attention_1_correct_label")
    ck("attention check present, forced, pass key recorded & matches", attn_ok)

    # 16. a PageTimer inside EVERY choice block AND the geometry block (speeder floor computable)
    qtype = {q["PrimaryAttribute"]: q["Payload"].get("QuestionType") for q in sqs}
    def block_has_timer(b):
        return any(qtype.get(el.get("QuestionID")) == "Timing" for el in b.get("BlockElements", []))
    ck("PageTimer in every choice block and every geometry block",
       all(block_has_timer(b) for b in choice_blocks) and bool(geo_blocks)
       and all(block_has_timer(b) for b in geo_blocks))

    # 17. consent widget sets embedded `consent` (decline branch works)
    consent_q = next((q for q in sqs if q["Payload"].get("DataExportTag") == "consent_q"), None)
    ck("consent widget sets embedded `consent` (decline branch works)",
       bool(consent_q) and "ed('consent'" in consent_q["Payload"].get("QuestionJS", ""))

    # 18. flow Count >= max FlowID (root-cause-#2 guard, D2 fix)
    def walk(fls):
        for e in fls:
            yield e
            if isinstance(e.get("Flow"), list):
                yield from walk(e["Flow"])
    max_fl = max(int(e["FlowID"].split("_")[1]) for e in walk(flow))
    ck("flow Properties.Count >= max FlowID (Count guard)",
       fl_payload["Properties"]["Count"] >= max_fl,
       f"Count={fl_payload['Properties']['Count']} maxFL={max_fl}")

    # 19. MAPPING records the band, the EXC handling, the independence note, and the bundled design
    ck("MAPPING records target band 40-45/55-60",
       mapping.get("target_band", {}).get("TARGET") == "40-45%" and
       mapping.get("target_band", {}).get("COMP") == "55-60%")
    ck("MAPPING records the path-a EXC handling (inherits MOT, no own pair/check)",
       "exc" in (mapping.get("exc_handling", "").lower()) and "mot" in (mapping.get("exc_handling", "").lower()))
    ck("MAPPING records the independent-sample recruitment allowlist",
       "exclu" in (mapping.get("recruitment_note", "").lower()))
    bd = mapping.get("bundled_design", {})
    ck("MAPPING records the bundled design (one per category, wave-1 arithmetic)",
       bd.get("pairs_per_person") == W["n_slots"]
       and bd.get("wave1_participants", 0) >= 4 * bd.get("wave1_n_per_pair_min", 10**9)
       and "one binary choice per product category" in bd.get("rule", ""),
       f"pairs_per_person={bd.get('pairs_per_person')} wave1={bd.get('wave1_participants')}")

    # ================= WAVE-2 SPECIFIC CHECKS (the shared-values kit) =================
    if wave == "wave2":
        sys.path.insert(0, os.path.dirname(HERE))
        from render_shared import render_value
        sys.path.insert(0, os.path.join(ROOT, "stimuli"))
        import generate_formats as GF

        # W1. every shared-value override is IN the emitted payloads and the OLD value is ABSENT
        ov_bad = []
        for cat_id, ov in overrides.items():
            sid, code, attr = ov["stimulus"], ov["option"], ov["attribute"]
            rec = by_id[sid]
            meta = next(a for a in cats[cat_id]["attributes"] if a["name"] == attr)
            new_num = render_value(attr, meta.get("unit", ""), ov["to"])
            old_num = render_value(attr, meta.get("unit", ""), ov["from"])
            new_words = GF.attr_words(attr, meta.get("unit", ""), float(ov["to"]))
            old_words = GF.attr_words(attr, meta.get("unit", ""), float(ov["from"]))
            for arm, kv in arms.items():
                t = slot_of_arm[arm]
                if kv.get(f"cell{t}_stimulus") != sid:
                    continue
                fmt = kv.get(f"cell{t}_format")
                opts = {o["code"]: o for o in json.loads(kv.get(f"cell{t}_options", "[]"))}
                html = opts.get(code, {}).get("html", "")
                if fmt == "numbers" and (new_num not in html or old_num in html):
                    ov_bad.append(f"{arm}: want {new_num!r} wo/ {old_num!r} in {html!r}")
                if fmt == "words" and (new_words not in html or old_words in html):
                    ov_bad.append(f"{arm}: want {new_words!r} in {html!r}")
                if fmt == "pictures" and not (kv.get(f"cell{t}_image", "").endswith(sid + "_wave2.png")):
                    ov_bad.append(f"{arm}: image not wave-2 ({kv.get(f'cell{t}_image')})")
        ck("W1 every shared-value override present in the emitted payloads (old value absent; "
           "numbers+words+pictures)", not ov_bad, "; ".join(ov_bad[:2]))

        # W2. water_bottles (no override) carries UNCHANGED shared values in both format arms
        wb_ok = True
        for arm in ("words::BIN_water_bottles_t2", "pictures::BIN_water_bottles_t2"):
            kv = arms.get(arm, {})
            t = slot_of_arm.get(arm)
            if arm.startswith("words"):
                blob = kv.get(f"cell{t}_options", "")
                if "twenty-four dollars and ninety-nine cents" not in blob or \
                   "eight dollars and ninety-nine cents" not in blob:
                    wb_ok = False
            else:
                if not kv.get(f"cell{t}_image", "").endswith("BIN_water_bottles_t2.png"):
                    wb_ok = False
        ck("W2 water_bottles format arms carry the UNCHANGED shared (in-band) values + wave-1 image", wb_ok)

        # W3. geometry v2.2: RNG key corrected; FRQ/SOT clarified keys INDEPENDENTLY recomputed
        gi = {g["structure"]: g for g in mapping.get("geometry_items", [])}
        ck("W3a RNG key corrected to 'The second feature' (wording unchanged: confirmation re-check)",
           gi.get("RNG", {}).get("correct_choice_key") == 2
           and gi.get("RNG", {}).get("correct_choice_label") == "The second feature"
           and gi.get("RNG", {}).get("choices", [None])[0] == "The first feature")
        frq_order = (geo_kv["geo"].get("FRQ", {}).get("geo_order") or "").split(",")
        sot_order = (geo_kv["geo"].get("SOT", {}).get("geo_order") or "").split(",")
        ck("W3b FRQ clarified key == the dominated decoy's lettered position (recomputed from geo_order)",
           gi.get("FRQ", {}).get("correct_choice_key") == frq_order.index("DECOY") + 1
           and "which one" in gi.get("FRQ", {}).get("question_text", "").lower()
           and gi.get("FRQ", {}).get("lettered_context") is True,
           f"order={frq_order} key={gi.get('FRQ', {}).get('correct_choice_key')}")
        ck("W3c SOT clarified key == the extreme's lettered position (recomputed from geo_order)",
           gi.get("SOT", {}).get("correct_choice_key") == sot_order.index("EXTREME") + 1
           and "most premium" in gi.get("SOT", {}).get("question_text", "").lower()
           and gi.get("SOT", {}).get("lettered_context") is True,
           f"order={sot_order} key={gi.get('SOT', {}).get('correct_choice_key')}")
        ck("W3d lettered context on FRQ+SOT only; geo_letters set 1/0 accordingly",
           all((geo_kv["geo"][st].get("geo_letters") == ("1" if st in ("FRQ", "SOT") else "0"))
               for st in geo_kv["geo"]),
           f"{ {st: geo_kv['geo'][st].get('geo_letters') for st in sorted(geo_kv['geo'])} }")
        geo_ctx = next((q for q in sqs if q["Payload"].get("DataExportTag") == "geo_context_q"), None)
        ck("W3e geometry context widget letters the cards when geo_letters=1",
           bool(geo_ctx) and "geo_letters" in geo_ctx["Payload"]["QuestionText"]
           and "lettered" in geo_ctx["Payload"].get("QuestionJS", ""))
        ck("W3f PHT/SYM/MOT/SIM items identical to wave 1 (re-checks: same keys)",
           gi.get("PHT", {}).get("correct_choice_key") == 1 and gi.get("SYM", {}).get("correct_choice_key") == 1
           and gi.get("MOT", {}).get("correct_choice_key") == 3 and gi.get("SIM", {}).get("correct_choice_key") == 1)

        # W4. the realism block (registered spec riding in wave 2)
        rc = mapping.get("realism_check") or {}
        rea_cats = rc.get("categories", [])
        ck("W4a realism check covers exactly the 3 invented categories",
           sorted(rea_cats) == sorted(["electric_kettles", "robot_vacuums", "standing_desks"]),
           f"{rea_cats}")
        rea_items = [q for q in sqs if str(q["Payload"].get("DataExportTag", "")).startswith("realism_")
                     and q["Payload"].get("QuestionType") == "MC"]
        ck("W4b one forced 7-point realism item per invented category",
           len(rea_items) == 3 and all(len(q["Payload"]["Choices"]) == 7 and
                                       q["Payload"]["Validation"]["Settings"].get("ForceResponse") == "ON"
                                       for q in rea_items),
           f"{[q['Payload']['DataExportTag'] for q in rea_items]}")
        # each realism context re-renders ITS category's dealt slot (same cell{t}_* fields)
        ctx_ok = True
        for it in rc.get("items", []):
            t = it["slot"]
            ctxq = next((q for q in sqs if q["Payload"].get("DataExportTag", "").startswith("realism_ctx")
                         and f"cell{t}_options" in q["Payload"]["QuestionText"]), None)
            if ctxq is None:
                ctx_ok = False
        ck("W4c each realism context re-renders its category's dealt slot (piped cell{t}_* fields)",
           ctx_ok, f"slots={[it['slot'] for it in rc.get('items', [])]}")
        cmt = next((q for q in sqs if q["Payload"].get("DataExportTag") == "realism_comments"), None)
        ck("W4d optional open comment box present (TE, NOT forced)",
           bool(cmt) and cmt["Payload"]["QuestionType"] == "TE"
           and cmt["Payload"]["Validation"]["Settings"].get("ForceResponse") == "OFF")
        rea_block = next((b for b in bl_blocks if str(b.get("Description", "")).startswith("Realism")), None)
        ck("W4e realism block exists, after geometry in the flow, with page timers",
           bool(rea_block) and block_has_timer(rea_block)
           and [b for b in flow if b.get("Type") == "Standard"]  # flow order check below
           , "")
        # flow order: geometry block before realism block before demographics
        std_ids = [e["ID"] for e in flow if e.get("Type") == "Standard"]
        demo_block = next((b for b in bl_blocks if b.get("Description") == "Demographics"), None)
        order_ok = (geo_block and rea_block and demo_block
                    and std_ids.index(geo_block["ID"]) < std_ids.index(rea_block["ID"]) < std_ids.index(demo_block["ID"]))
        ck("W4f flow order: geometry -> realism -> demographics", bool(order_ok))
        ck("W4g MAPPING documents the realism ordering deviation (realism rides IN wave 2; lock after both)",
           "deviation" in json.dumps(rc).lower() and "lock" in rc.get("ordering_deviation", "").lower())

        # W5. the wave-2 deal / pay arithmetic recorded
        wd = mapping.get("wave2_deal") or {}
        ck("W5 MAPPING records the wave-2 deal + pay arithmetic (binding 3-arm categories; 300 nominal / "
           "312 recommended; $1.00 at ~4.2 min)",
           wd.get("max_arms_per_category") == 3 and wd.get("participants_nominal_100") == 300
           and wd.get("participants_recommended") == 312 and wd.get("pay_usd") == 1.0
           and abs(wd.get("cost_at_recommended", 0) - 416.02) < 0.5,
           f"{ {k: wd.get(k) for k in ('participants_nominal_100','participants_recommended','cost_at_300','cost_at_recommended')} }")

        # W6. the study info states the ~4-minute session (pay honesty)
        ck("W6 study-info text states the ~4-minute wave-2 session",
           bool(consent_q) and "4 minutes" in consent_q["Payload"]["QuestionText"])

    # ================= WAVE-3 SPECIFIC CHECKS (the terminal kit) =================
    if wave == "wave3":
        sys.path.insert(0, os.path.dirname(HERE))
        from render_shared import render_value
        sys.path.insert(0, os.path.join(ROOT, "stimuli"))
        import generate_formats as GF
        import geometry as GEO

        enrichment = {k: v for k, v in kit["enrichment"].items() if k != "note"}

        # V1. every PER-ARM override is IN that arm's payload with the OLD value ABSENT
        #     (numbers + words in the option HTML; pictures via the wave-3 image name checked in #3)
        ov_bad = []
        for arm, kv in arms.items():
            t = slot_of_arm[arm]
            fmt = kv.get(f"cell{t}_format")
            if fmt == "pictures":
                continue
            sid = kv.get(f"cell{t}_stimulus")
            cat_id = kv.get(f"cell{t}_category")
            opts = {o["code"]: o for o in json.loads(kv.get(f"cell{t}_options", "[]"))}
            for ov in arm_overrides.get(arm, []):
                meta = next(a for a in cats[cat_id]["attributes"] if a["name"] == ov["attribute"])
                html = opts.get(ov["option"], {}).get("html", "")
                if fmt == "numbers":
                    new_s = render_value(ov["attribute"], meta.get("unit", ""), ov["to"])
                    old_s = render_value(ov["attribute"], meta.get("unit", ""), ov["from"])
                else:
                    new_s = GF.attr_words(ov["attribute"], meta.get("unit", ""), float(ov["to"]))
                    old_s = GF.attr_words(ov["attribute"], meta.get("unit", ""), float(ov["from"]))
                if new_s not in html or old_s in html:
                    ov_bad.append(f"{arm}: want {new_s!r} wo/ {old_s!r}")
        ck("V1 every per-arm override present in ITS arm's payload (old value absent; numbers+words)",
           not ov_bad, "; ".join(ov_bad[:2]))

        # V2. the water_bottles arms carry UNCHANGED values (words spelled originals; pictures via
        #     the built-values note) - their wave-3 job is the enrichment/legend re-test at fixed values
        wb_ok = True
        kv = arms.get("words::BIN_water_bottles_t2", {})
        t = slot_of_arm.get("words::BIN_water_bottles_t2")
        blob = kv.get(f"cell{t}_options", "")
        if "twenty-four dollars and ninety-nine cents" not in blob or \
           "eight dollars and ninety-nine cents" not in blob:
            wb_ok = False
        ck("V2 water_bottles arms carry the UNCHANGED (numbers-arm in-band) values", wb_ok)

        # V3. the enrichment contract in every dealt payload: model name present in numbers/words
        #     cards; 'Option X - name' pictures cards; numeral-free names/qualifiers (module assert)
        enr_bad = []
        for arm, kv in arms.items():
            t = slot_of_arm[arm]
            cat_id = kv.get(f"cell{t}_category")
            fmt = kv.get(f"cell{t}_format")
            opts = {o["code"]: o for o in json.loads(kv.get(f"cell{t}_options", "[]"))}
            for code, entry in enrichment[cat_id].items():
                html = opts.get(code, {}).get("html", "")
                if entry["name"] not in html:
                    enr_bad.append(f"{arm}:{code} name missing")
                if fmt != "pictures" and not all(q in html for q in entry["qualifiers"].values()):
                    enr_bad.append(f"{arm}:{code} qualifier missing")
        try:
            import enrich as EN_mod
            EN_mod.validate_enrichment(enrichment, cats)
            enr_contract = True
        except AssertionError as e:
            enr_contract = False
            enr_bad.append(str(e))
        ck("V3 enrichment in every dealt payload (names+qualifiers; numeral-free contract holds)",
           not enr_bad and enr_contract, "; ".join(enr_bad[:2]))

        # V4. geometry v3: the FRQ/RNG strengthened cells INDEPENDENTLY recomputed from the kit's
        #     registered margins via geometry.build on the locked anchor; keys recomputed from the
        #     shown order; letters on FRQ/SOT only, on BOTH pages
        gspec = kit["geometry_wave3"]
        host = gspec["host_category"]
        am = cats[host]["attributes"]
        anc = gspec["host_stimulus_anchor"]
        higher = next(a["name"] for a in am if a["direction"] == "higher_better")
        lower = next(a["name"] for a in am if a["direction"] == "lower_better")
        anchor = {"A": {"name": higher, "hf": anc["HF"][higher], "hd": anc["HD"][higher]},
                  "B": {"name": lower, "hf": anc["HF"][lower], "hd": anc["HD"][lower]}}
        bin_rec = next(r for r in S["stimuli"] if r["category"] == host and r["structure"] == "BIN")
        indep = {r["structure"]: r for r in GEO.build(
            anchor, am, price_free=False, caps={}, tier=bin_rec["memorization_tier"], cat_id=host,
            stem=bin_rec["stem"], decoy_target=GEO.DECOY_TARGET[host],
            frq_margins=(gspec["frq_margin"]["a_frac"], gspec["frq_margin"]["b_frac"]),
            rng_b_factor=gspec["rng_extension"]["b_factor"])}
        built = (mapping.get("geometry_wave3") or {}).get("built_cells", {})
        geo_val_bad = []
        for st in sorted(GEO_STRUCTS):
            want_opts = [{"code": o["code"], "attrs": o["attrs"], "available": o.get("available", True)}
                         for o in indep[st]["options"]]
            if built.get(st) != want_opts:
                geo_val_bad.append(st)
        ck("V4a all 7 geometry cells == the independent geometry.build recompute at the kit's "
           "registered margins (locked anchor; strengthened FRQ/RNG)", not geo_val_bad,
           f"mismatch: {geo_val_bad}")
        frq_dec = next(o for o in built.get("FRQ", []) if o["code"] == "DECOY")
        rng_dec = next(o for o in built.get("RNG", []) if o["code"] == "RANGE_DECOY")
        ck("V4b FRQ decoy at the STRENGTHENED margins (5,000 Pa / $624.99 vs the 6,000 Pa / $499.99 target)",
           frq_dec["attrs"] == {"suction": 5000, "price": 624.99}, f"{frq_dec['attrs']}")
        ck("V4c RNG decoy at the AMPLIFIED range extension (6,000 Pa / $1,099.98 = x2.2 of the target's price)",
           rng_dec["attrs"] == {"suction": 6000, "price": 1099.98}, f"{rng_dec['attrs']}")
        gi = {g["structure"]: g for g in mapping.get("geometry_items", [])}
        key_bad = []
        for pfx in prefixes:
            frq_order = (geo_kv[pfx].get("FRQ", {}).get(f"{pfx}_order") or "").split(",")
            sot_order = (geo_kv[pfx].get("SOT", {}).get(f"{pfx}_order") or "").split(",")
            if gi.get("FRQ", {}).get("correct_choice_key") != frq_order.index("DECOY") + 1:
                key_bad.append(f"{pfx}:FRQ")
            if gi.get("SOT", {}).get("correct_choice_key") != sot_order.index("EXTREME") + 1:
                key_bad.append(f"{pfx}:SOT")
            for st in GEO_STRUCTS:
                want = "1" if st in ("FRQ", "SOT") else "0"
                if geo_kv[pfx].get(st, {}).get(f"{pfx}_letters") != want:
                    key_bad.append(f"{pfx}:{st}:letters")
        ck("V4d FRQ/SOT keys page-invariant + recomputed from the shown order; letters on FRQ+SOT only "
           "(both pages)", not key_bad, str(key_bad[:4]))
        ck("V4e RNG key stays the corrected 'The second feature'; PHT/SYM/MOT/SIM keys unchanged",
           gi.get("RNG", {}).get("correct_choice_key") == 2
           and gi.get("PHT", {}).get("correct_choice_key") == 1
           and gi.get("SYM", {}).get("correct_choice_key") == 1
           and gi.get("MOT", {}).get("correct_choice_key") == 3
           and gi.get("SIM", {}).get("correct_choice_key") == 1)
        ck("V4f every geometry item carries BOTH page export tags (geo1_/geo2_)",
           all(len(g.get("export_tags", [])) == 2 and
               g["export_tags"][0].startswith("geo1_") and g["export_tags"][1].startswith("geo2_")
               for g in mapping.get("geometry_items", [])))

        # V5. realism: kettles+desks piped to their slots; robot_vacuums STATIC at the locked values
        rc = mapping.get("realism_check") or {}
        rea_items_map = {it["category"]: it for it in rc.get("items", [])}
        static_it = rea_items_map.get("robot_vacuums", {})
        rea_ctx_qs = {q["Payload"]["DataExportTag"]: q for q in sqs
                      if str(q["Payload"].get("DataExportTag", "")).startswith("realism_ctx")}
        static_ctx = None
        for q in rea_ctx_qs.values():
            if "TidyBot" in q["Payload"]["QuestionText"]:
                static_ctx = q
        ck("V5a realism covers the 3 invented categories; robot_vacuums is the STATIC item (no slot)",
           sorted(rc.get("categories", [])) == ["electric_kettles", "robot_vacuums", "standing_desks"]
           and static_it.get("slot") is None and "locked" in str(static_it.get("static", "")),
           f"{sorted(rc.get('categories', []))}")
        ck("V5b the static robot_vacuums context is BAKED with the enriched names + LOCKED values "
           "($159 / $499.99; no piping)",
           bool(static_ctx) and "OrbitClean" in static_ctx["Payload"]["QuestionText"]
           and "$159" in static_ctx["Payload"]["QuestionText"]
           and "$499.99" in static_ctx["Payload"]["QuestionText"]
           and "${e://" not in static_ctx["Payload"]["QuestionText"])
        piped_ok = True
        for c in ("electric_kettles", "standing_desks"):
            t = rea_items_map.get(c, {}).get("slot")
            if t is None or not any(f"cell{t}_options" in q["Payload"]["QuestionText"]
                                    for q in rea_ctx_qs.values()):
                piped_ok = False
        ck("V5c kettles + desks realism contexts re-render THEIR dealt slots (piped)", piped_ok)

        # V6. the picture-comprehension item (amendment (e))
        pc = mapping.get("pic_comprehension") or {}
        pic_mc = next((q for q in sqs if q["Payload"].get("DataExportTag") == "pic_comprehension"), None)
        pic_ctx = next((q for q in sqs if q["Payload"].get("DataExportTag") == "pic_context_q"), None)
        pics_slots_want = sorted(t for t, kvs in per_slot_arms.items()
                                 if any(arms[a].get(f"cell{t}_format") == "pictures" for a in kvs))
        dl_ok = True
        for q in (pic_mc, pic_ctx):
            dl = (q or {}).get("Payload", {}).get("DisplayLogic")
            if not dl:
                dl_ok = False; continue
            conds = [v for k, v in dl["0"].items() if k != "Type"]
            got_slots = sorted(int(c["LeftOperand"].replace("cell", "").replace("_format", ""))
                               for c in conds)
            if got_slots != pics_slots_want or any(c.get("RightOperand") != "pictures" for c in conds):
                dl_ok = False
            if sum(1 for c in conds if c.get("Conjuction") == "Or") != len(conds) - 1:
                dl_ok = False
        ck("V6a pic-comprehension ctx+MC present, forced, display-logic OR over exactly the "
           "pictures-capable slots", bool(pic_mc) and bool(pic_ctx) and dl_ok
           and pic_mc["Payload"]["Validation"]["Settings"].get("ForceResponse") == "ON",
           f"slots={pics_slots_want}")
        ck("V6b pic-comprehension key = Option B (computed + recorded); context JS host-normalizes "
           "and records piccheck_slot",
           pc.get("correct_choice_label") == "Option B" and pc.get("correct_choice_key") == 2
           and sorted(pc.get("pictures_capable_slots", [])) == pics_slots_want
           and "piccheck_slot" in (pic_ctx["Payload"].get("QuestionJS") or "")
           and GS.HOSTBASE.rstrip("/") in (pic_ctx["Payload"].get("QuestionJS") or ""))

        # V7. flow order: choices -> geometry 1 -> geometry 2 -> picture comprehension -> realism -> demo
        std_ids = [e["ID"] for e in flow if e.get("Type") == "Standard"]
        pic_block = next((b for b in bl_blocks if b.get("Description") == "Picture comprehension"), None)
        rea_block3 = next((b for b in bl_blocks if str(b.get("Description", "")).startswith("Realism")), None)
        demo_block3 = next((b for b in bl_blocks if b.get("Description") == "Demographics"), None)
        order_ok = (len(geo_blocks) == 2 and pic_block and rea_block3 and demo_block3
                    and std_ids.index(geo_blocks[0]["ID"]) < std_ids.index(geo_blocks[1]["ID"])
                    < std_ids.index(pic_block["ID"]) < std_ids.index(rea_block3["ID"])
                    < std_ids.index(demo_block3["ID"]))
        ck("V7 flow order: geometry 1 -> geometry 2 -> picture comprehension -> realism -> demographics",
           bool(order_ok))

        # V8. MAPPING records the terminal-lock criterion + the wave-3 deal/pay/cost arithmetic
        tlc = mapping.get("terminal_lock_criterion") or {}
        wd = mapping.get("wave3_deal") or {}
        ck("V8a MAPPING records the terminal lock criterion (fixed before any wave-3 data)",
           tlc.get("band") == [40.0, 45.0] and tlc.get("point_window") == [33.0, 50.0]
           and "defect" in tlc.get("rule", "").lower())
        ck("V8b MAPPING records the wave-3 deal: 462 nominal / 154 per binding arm / 132 per geometry "
           "structure / $1.13 / $696.10 <= the $700 cap",
           wd.get("participants_nominal") == 462 and wd.get("n_per_binding_arm_nominal") == 154
           and wd.get("geometry_n_per_structure_nominal") == 132 and wd.get("pay_usd") == 1.13
           and abs(wd.get("cost_all_in", 0) - 696.10) < 0.25
           and wd.get("cost_all_in", 1e9) <= wd.get("cost_cap", 0),
           f"{ {k: wd.get(k) for k in ('participants_nominal', 'pay_usd', 'cost_all_in')} }")
        ck("V8c MAPPING records the per-arm values departure + the full per-arm override trail",
           bool(mapping.get("per_arm_values_note"))
           and set(mapping.get("arm_value_overrides_applied") or {}) == set(kit["arms"]))

        # V9. the study info states the ~5-minute session (pay honesty)
        ck("V9 study-info text states the ~5-minute wave-3 session",
           bool(consent_q) and "5 minutes" in consent_q["Payload"]["QuestionText"])

    # ---- report ----
    w = max(len(n) for n, _, _ in checks)
    print(f"== calibration_selftest.py [{wave}] : reconstruct the calibration design from the emitted .qsf ==")
    allok = True
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n:<{w}}  {d}")
        allok &= ok
    print(f"-- {sum(1 for _, ok, _ in checks if ok)}/{len(checks)} checks pass --")
    label = {"wave2": ("WAVE-2 SHARED-VALUES CALIBRATION DESIGN (17 PAIRS / 10 SLOTS / OVERRIDES "
                       "IN-PAYLOAD / GEOMETRY v2.2 / REALISM BLOCK)"),
             "wave3": ("WAVE-3 TERMINAL CALIBRATION DESIGN (16 PAIRS / 9 SLOTS / PER-ARM OVERRIDES "
                       "IN-PAYLOAD / ENRICHED DESCRIPTIONS / GEOMETRY v3 2-ITEM PAIR DEAL AT THE "
                       "STRENGTHENED MARGINS / STATIC VACUUMS REALISM / PIC-COMPREHENSION / TERMINAL "
                       "LOCK CRITERION)")}.get(wave,
             "BUNDLED CALIBRATION DESIGN (25 PAIRS / 10 ONE-PER-CATEGORY SLOTS / EVEN DEAL / ORDER "
             "RANDOMIZER / FORMAT-AWARE WIDGET incl. PICTURES / GEOMETRY CHECKS / EXC HANDLING)")
    print("RESULT:", (label + " VERIFIED OFFLINE (the live Qualtrics import-and-click-through is still "
                      "required)." if allok else "CALIBRATION DESIGN CORRUPTION - fix the generator."))
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
