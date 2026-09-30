"""build_stimuli.py: build stimuli/stimuli.json, the single stimulus file every survey, model prompt and
appendix table reads.

It merges the per-category source files in stimuli/fragments/ (published tier-1 values, generated tier-2
and tier-3 values, the price-free categories), rebuilds the constructed structures of every cell from the
cell's two-option pair with the geometry engine (geometry.py), adds the words and pictures variants
(generate_formats.py), and applies the final calibration lock: the calibrated values, checked against
calibration/FINAL_LOCK_LIST_2026-07-02.json (the build stops if any value disagrees), the per-pair
calibration records, the deviation flags, the removal of the one pair that left the design, and the
enriched product descriptions (calibration_lock.py, enrich.py). The extremity control (EXC) is re-derived
from the locked extremity menu (MOT) on every build.

Output: stimuli/stimuli.json (165 stimuli). Never edit that file by hand.
Manuscript: the stimulus values behind the Method, Table 2 and Web Appendix B, and the final calibrated
values in Web Appendix F (Table WA-F6).

Run: python stimuli/build_stimuli.py
"""
import copy, json, glob, math, os
import geometry
import generate_formats
import calibration_lock
import enrich

HERE = os.path.dirname(os.path.abspath(__file__))

def norm_category(frag):
    """Accept either {'category': {...}} or {'meta': {...}}; return canonical category dict."""
    c = dict(frag.get("category") or frag.get("meta") or {})
    cid = c.get("id") or c.get("category_id")
    label = c.get("label") or c.get("category_label")
    out = {
        "id": cid,
        "label": label,
        "category_number_v1": c.get("category_number_v1"),
        "attributes": c.get("attributes", []),
        "price_free": c.get("price_free", False),
        "published": c.get("published", True),
        "memorization_tier_source": c.get("memorization_tier", 1),
        "source": c.get("source"),
        "geometry_constraints": c.get("geometry_constraints", []),
        "price_free_variant_of": c.get("price_free_variant_of"),
    }
    return out

def main():
    cats, stimuli = [], []
    seen_ids = set()
    for f in sorted(glob.glob(os.path.join(HERE, "fragments", "*.json"))):
        base = os.path.basename(f)
        try:
            frag = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print(f"  !! skip {base}: parse error {e}")
            continue
        if "stimuli" not in frag:
            print(f"  !! skip {base}: no 'stimuli' key")
            continue
        cat = norm_category(frag)
        if cat["id"]:                              # a category-defining fragment (tier-1)
            if cat["id"] not in seen_ids:
                seen_ids.add(cat["id"]); cats.append(cat)
            default_cat = cat["id"]
        else:                                      # an add-on fragment (tier-2/tier-3): stimuli only
            default_cat = frag.get("_tier2_addon_for") or frag.get("_addon_for")
            if not default_cat and frag["stimuli"]:
                default_cat = frag["stimuli"][0].get("category")
            if not default_cat:
                print(f"  !! skip {base}: cannot determine category"); continue
        for st in frag["stimuli"]:
            st = dict(st)
            st["category"] = st.get("category") or default_cat
            st.setdefault("memorization_tier", 1)
            stimuli.append(st)
        print(f"  merged {base}: {len(frag['stimuli'])} stimuli -> {default_cat}")

    # --- schema normalization (R3: code/flags/statistic/tier drift across fragments) ---
    CANON_STAT = {"FRQ": "target_share_vs_binary", "RNG": "target_share_vs_binary",
                  "PHT": "target_share_vs_binary",
                  "SOT": "target_relative_share_over_target_plus_competitor",
                  "MOT": "extreme_tier_share_vs_matched_EXC",
                  "EXC": "extreme_tier_share_single_per_tier",
                  "SYM": "hd_share_vs_binary",
                  "SIM": "uncloned_relative_share_HD_vs_HF", "BIN": None}
    def norm_stim(s):
        for o in s.get("options", []):
            if isinstance(o.get("code"), str):
                o["code"] = o["code"].upper()
            if isinstance(o.get("tier"), str):
                o["tier"] = o["tier"].capitalize()
        fl = s.get("flags", [])
        if isinstance(fl, dict):
            fl = [f"{k}: {v}" for k, v in fl.items()]
        s["flags"] = fl if isinstance(fl, list) else ([] if fl is None else [str(fl)])
        if CANON_STAT.get(s["structure"]) is not None:
            s["statistic"] = CANON_STAT[s["structure"]]
        elif s["structure"] == "BIN":
            s["statistic"] = None
        # drop leftover audit-only keys from extraction (R3 hygiene): keep a fixed whitelist
        ALLOWED = {"id", "category", "structure", "memorization_tier", "format", "forced", "stem",
                   "options", "target", "competitor", "statistic", "source", "flags",
                   "no_published_analog", "calibration_locked", "calibration", "image_ref",
                   "image_sha256", "format_variants", "placement_variants", "sim_placement"}
        for k in [k for k in list(s) if k not in ALLOWED]:
            s.pop(k)
        OPT_ALLOWED = {"code", "is_hd", "available", "attrs", "brand", "tier", "color", "clone_of"}
        for o in s.get("options", []):
            for k in [k for k in list(o) if k not in OPT_ALLOWED]:
                o.pop(k)
        # normalized to False here; the final calibration lock lock step below stamps True on every stimulus
        # (nothing was calibration-locked before final calibration lock; the terminal lock ran 2026-07-02)
        s["calibration_locked"] = False
        if s.get("forced") and isinstance(s.get("stem"), str) and "which would you choose" not in s["stem"].lower():
            s["stem"] = s["stem"].rstrip() + " Which would you choose?"
        return s

    # --- regenerate the CONSTRUCTED structures (PHT->PR, SIM->non-dominated, SOT->corrected compromise,
    #     RNG->registered dominated range decoy) from each cell's BIN anchor, so the geometry check fixes apply
    #     uniformly to tier-1 and tier-2 (R1/R3/adversary; RNG added 2026-07-01, M1) ---
    def cap_from_unit(unit):
        u = (unit or "").lower()
        if "out of 5" in u or "/5" in u or "stars" in u: return 5.0
        if "0-100" in u or "100-point" in u or "0 to 100" in u: return 100.0
        return None
    cat_by_id = {c["id"]: c for c in cats}
    bins = {(s["category"], s.get("memorization_tier", 1)): s for s in stimuli if s["structure"] == "BIN"}
    # the cells that carry an MOT extremity menu; each gets a matched EXC single-per-tier control built
    # below (path a, 2026-06-13). EXC has no published fragment (it is a new control structure), so it is
    # ADDED here from the binary anchor, unlike PHT/SIM/SOT which are REGENERATED over existing entries.
    mot_by_cell = {(s["category"], s.get("memorization_tier", 1)): s for s in stimuli if s["structure"] == "MOT"}
    mot_cells = set(mot_by_cell)
    regen = {}
    new_exc = []
    for (cid, tier), binst in bins.items():
        cat = cat_by_id.get(cid)
        if not cat:
            continue
        anchor = geometry.anchor_from_bin(binst, cat["attributes"])
        if not anchor:
            continue                                   # price-free/malformed: leave fragment as-is
        caps = {}
        for a in cat["attributes"]:
            c = cap_from_unit(a.get("unit"))
            if c:
                caps[a["name"]] = c
        # PHT favours the same focal as the tier's FRQ/RNG: tier-1 stays HD (published); tier-2/3 use
        # the R3-2C counterbalance map. (SIM/SOT are unaffected by decoy_target.)
        dt = "HD" if tier == 1 else geometry.DECOY_TARGET.get(cid, "HD")
        built = {b["structure"]: b for b in geometry.build(
            anchor, cat["attributes"], price_free=cat.get("price_free", False),
            caps=caps, tier=tier, cat_id=cid, stem=binst.get("stem"), decoy_target=dt,
            **calibration_lock.GEOMETRY_STRENGTHENED)}
        # PHT, SIM, SOT, RNG are CONSTRUCTED structures (no faithful published value: PF phantoms are
        # the Pettibone-Wedell null, SIM has no analog, the SOT compromise extreme is a new addition,
        # and the V1 range decoys were the NON-DOMINATED variant that contradicts the registered
        # dominated form, so RNG is rebuilt too - M1 fix, 2026-07-01, decided by the authors).
        # Engine-build them uniformly from each cell's published focal pair (HF/HD stay exact).
        for stype in ("PHT", "SIM", "SOT", "RNG"):
            nb = built[stype]
            nb["memorization_tier"] = tier
            nb["calibration_locked"] = False
            note = {"PHT": "PR phantom per R1/Pettibone-Wedell (published PF preserved in fragments/*_receipts.md)",
                    "SIM": "non-dominated similarity clone; tracks the uncloned focal (the registered similarity rule)",
                    "SOT": "corrected compromise: new extreme beyond HD so HD is the middle (focal pair stays published)",
                    "RNG": "registered dominated range decoy: matches the target's strong attribute, extends the "
                           "weak-attribute range past the target (V1's non-dominated variant preserved in "
                           "fragments/*_receipts.md; corrected 2026-07-01)"}[stype]
            nb["source"] = "ENGINE-CONSTRUCTED %s from the cell's binary anchor; %s" % (stype, note)
            regen[(cid, tier, stype)] = nb
        # EXC extremity control: add ONE per MOT-bearing cell, built DIRECTLY from that cell's MOT menu
        # so EXC inherits MOT's exact tier centers (High/Middle/Low) - including published tier-1 cells
        # whose Middle is the real published value, not an engine midpoint. The two menus then share
        # their three tiers exactly and differ only in options-per-tier (path a, 2026-06-13).
        if (cid, tier) in mot_cells:
            mot_src = mot_by_cell[(cid, tier)]
            exc_base = dict(category=cid, memorization_tier=tier, format="numbers", forced=True,
                            stem=mot_src.get("stem") or binst.get("stem"))
            exc = geometry.exc_from_mot(mot_src, exc_base)
            exc["calibration_locked"] = False
            exc["source"] = ("ENGINE-CONSTRUCTED EXC from the matched MOT menu's tier centers; "
                             "single-option-per-tier extremity control on MOT's three tiers "
                             "(High/Middle/Low), the matched control for the MOT extremity statistic "
                             "(path a, 2026-06-13; compromise SOT untouched).")
            new_exc.append(exc)
    rebuilt = []
    for s in stimuli:
        key = (s["category"], s.get("memorization_tier", 1), s["structure"])
        rebuilt.append(norm_stim(regen.get(key, s)))
    for exc in new_exc:                                  # add the new EXC extremity controls (path a)
        rebuilt.append(norm_stim(exc))
    stimuli = rebuilt
    print(f"  regenerated PHT+SIM+SOT+RNG for {len(regen)//4} cells (PR phantom, non-dominated clone, uniform compromise, dominated range decoy); schema normalized")
    print(f"  added EXC single-per-tier extremity control for {len(new_exc)} MOT-bearing cells (path a)")
    # format module: words + pictures variants on the format categories' tier-2 BIN/FRQ/SOT cells
    # (final calibration lock: hard_drives carries words only - its pictures arm exited; see generate_formats.py)
    n_fmt = generate_formats.apply(stimuli, cat_by_id, os.path.join(HERE, "assets"))
    print(f"  format module: words+pictures variants added to {n_fmt} cells (assets/*.svg)")

    # =================== final calibration lock TERMINAL CALIBRATION LOCK (2026-07-02) ============================
    # The one authorized value-locking step. Values were already built from the locked anchors by
    # the generators; here they are ASSERTED against the lock list (the numeric authority),
    # the per-arm records and routing flags are stamped, the enrichment block is written, and
    # every stimulus is marked calibration_locked.
    # Layout: the lock list lives at calibration/ in the
    # working repository and at calibration/ in the public deposit; take the first that exists.
    _lock_path = next(p for p in
                      (os.path.join(HERE, "..", "pretest", "FINAL_LOCK_LIST_2026-07-02.json"),
                       os.path.join(HERE, "..", "calibration", "FINAL_LOCK_LIST_2026-07-02.json"))
                      if os.path.exists(p))
    lock = json.load(open(_lock_path, encoding="utf-8"))
    by_id = {s["id"]: s for s in stimuli}
    ARM_FMT = {"pub_t1": "numbers", "pub_t2": "numbers", "inv_t3": "numbers",
               "words": "words", "pictures": "pictures"}

    def _opts_match(opts, finals):
        got = {o["code"]: o["attrs"] for o in opts if o.get("code") in ("HF", "HD")}
        for code, want in finals.items():
            have = got.get(code, {})
            for a, v in want.items():
                if a not in have or abs(float(have[a]) - float(v)) > 1e-9:
                    return False, (code, a, v, have.get(a))
        return True, None

    # ---- option identity of the calibration records ----------------
    # Every calibration record counts the category-level calibration target (the rule
    # ingest.load_stimuli applies: the first decoy target listed for the category). That option is
    # the compromise target (HD) in eight categories but HF, the budget option, in the electric
    # kettles and the standing desks.
    cat_focal = {}                           # category -> the option the calibration records count
    for s in stimuli:
        if s["structure"] != "BIN" and s.get("target"):
            cat_focal.setdefault(s["category"], s["target"])
    # the calibration waves decoded choices against the pre-final calibration lock snapshot; its category-level target
    # must be the same option, or the recorded shares would mean something else
    _snap = os.path.join(HERE, "stimuli_prelock.json")
    if os.path.exists(_snap):
        snap_focal = {}
        for s in json.load(open(_snap, encoding="utf-8"))["stimuli"]:
            if s["structure"] != "BIN" and s.get("target"):
                snap_focal.setdefault(s["category"], s["target"])
        for c, t in cat_focal.items():
            assert snap_focal.get(c, t) == t, \
                f"final calibration lock flag fix: {c} calibration target {snap_focal.get(c)} (snapshot) != {t} (built)"
    ROLE = {"HD": "the premium option", "HF": "the budget option"}
    sot_target = {(s["category"], s.get("memorization_tier", 1)): s["target"]
                  for s in stimuli if s["structure"] == "SOT"}

    # The registered terminal lock criterion (CALIBRATION_DESIGN wave-3 amendment (a);
    # calibration/calibration_analysis.terminal_verdict + wilson_ci). Re-implemented here and proven
    # against every recorded wave-3 verdict below before it is used on the other option's share.
    T_BAND, T_POINT = (40.0, 45.0), (33.0, 50.0)

    def _wilson_pct(k, n, z=1.96):
        p = k / n
        d = 1 + z * z / n
        c = (p + z * z / (2 * n)) / d
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
        return max(0.0, c - h) * 100, min(1.0, c + h) * 100

    def _locks(pct, lo, hi):
        if T_BAND[0] <= pct <= T_BAND[1]:
            return True
        return lo <= T_BAND[1] and hi >= T_BAND[0] and T_POINT[0] <= pct <= T_POINT[1]

    for arm in lock["arms"]:
        w = arm.get("wave3") or {}
        if w.get("k_target") is None:
            continue
        k, n = w["k_target"], w["n"]
        lo, hi = _wilson_pct(k, n)
        assert round(100 * k / n, 1) == w["target_share_pct"] and \
            [round(lo, 1), round(hi, 1)] == list(w["wilson95"]), \
            f"final calibration lock flag fix: {arm['arm_id']} share/interval do not reproduce from k={k}, n={n}"
        assert _locks(100 * k / n, lo, hi) == arm["terminal_lock_verdict"].startswith("LOCK"), \
            f"final calibration lock flag fix: terminal criterion re-implementation disagrees on {arm['arm_id']}"

    identity = {}                            # arm_id -> fields for IDENTITY_FLAG_TEXT
    for arm in lock["arms"]:
        cat, tier = arm["category"], arm["tier"]
        comp_t, focal = sot_target.get((cat, tier)), cat_focal.get(cat)
        if comp_t is None or comp_t == focal or calibration_lock.ROUTING[arm["arm_id"]] == "EXIT":
            continue
        w = arm.get("wave3") or {}
        assert w.get("k_target") is not None, f"final calibration lock flag fix: no wave-3 counts for {arm['arm_id']}"
        k, n = w["k_target"], w["n"]
        r_lo, r_hi = _wilson_pct(k, n)
        c_lo, c_hi = _wilson_pct(n - k, n)
        assert [round(100 - c_hi, 1), round(100 - c_lo, 1)] == list(w["wilson95"]), \
            f"final calibration lock flag fix: {arm['arm_id']} complement interval disagrees with the lock list"
        for struct in ("FRQ", "RNG", "PHT"):  # the texts say these decoys target the recorded option
            assert by_id[f"{struct}_{cat}_t{tier}"]["target"] == focal, \
                f"final calibration lock flag fix: {struct}_{cat}_t{tier} does not target {focal}"
        identity[arm["arm_id"]] = dict(
            g3=calibration_lock.G3_DATE, fmt=ARM_FMT[arm["arm_id"].split("::")[0]], n=n,
            limit=f"{calibration_lock.COMPROMISE_TARGET_MAX_BASELINE_PCT:.0f}",
            rec_code=focal, rec_role=ROLE[focal], rec_pct=f"{100 * k / n:.1f}",
            rec_ci=f"[{r_lo:.1f}, {r_hi:.1f}]",
            comp_code=comp_t, comp_role=ROLE[comp_t], comp_pct=f"{100 * (n - k) / n:.1f}",
            comp_ci=f"[{c_lo:.1f}, {c_hi:.1f}]",
            _verdicts=("LOCK" if _locks(100 * k / n, r_lo, r_hi) else "FAIL",
                       "LOCK" if _locks(100 * (n - k) / n, c_lo, c_hi) else "FAIL"))
    got = {a: v["_verdicts"] for a, v in identity.items()}
    assert got == calibration_lock.IDENTITY_EXPECTED, \
        f"final calibration lock flag fix: option-identity verdicts {got} differ from the registered {calibration_lock.IDENTITY_EXPECTED}"
    assert set(identity) == set(calibration_lock.IDENTITY_FLAG_TEXT) == set(calibration_lock.IDENTITY_RECORD_TEXT), \
        "final calibration lock flag fix: identity flag or record texts incomplete"
    print(f"  option identity: {len(identity)} arms whose calibration record counts the budget "
          f"option, re-scored on the compromise target's share: {got}")

    n_arms = 0
    hard_flagged = set()                     # check-only arms given the hard-limit flag (2026-09-29)
    for arm in lock["arms"]:
        sid, arm_id = arm["stimulus_id"], arm["arm_id"]
        status = calibration_lock.ROUTING[arm_id]
        st = by_id.get(sid)
        assert st is not None, f"final calibration lock: lock-list stimulus {sid} was not built"
        fmt = ARM_FMT[arm_id.split("::")[0]]
        if fmt == "pictures":
            pv = (st.get("format_variants") or {}).get("pictures")
            if status == "EXIT":
                assert pv is None, f"final calibration lock: {sid} pictures variant must be removed (EXIT), still present"
            else:
                assert pv is not None and pv.get("options"), f"final calibration lock: {sid} pictures variant lacks options"
                ok, why = _opts_match(pv["options"], arm["final_values"])
                assert ok, f"final calibration lock VALUE MISMATCH {arm_id}: (code, attr, lock, built) = {why}"
        else:
            ok, why = _opts_match(st["options"], arm["final_values"])
            assert ok, f"final calibration lock VALUE MISMATCH {arm_id}: (code, attr, lock, built) = {why}"
        rec = {"status": status,
               "terminal_lock_verdict": arm.get("terminal_lock_verdict"),
               "band_verdict": arm.get("band_verdict"),
               "disposition": arm.get("disposition"),
               "trail": arm.get("trail")}
        for wkey in ("wave1", "wave3"):
            if arm.get(wkey):
                rec[wkey] = arm[wkey]
        # 2026-09-29: the two option-identity arms get corrected record
        # TEXT (whose share the record holds, the compromise target's own share, the verdict by
        # option identity). Numbers are untouched: the wave3 block and the trail's shares and
        # value moves stay exactly as the lock list has them; one note is appended to the
        # trail's QUALITY-step line.
        idf = None
        if arm_id in identity:
            idf = {k: v for k, v in identity[arm_id].items() if not k.startswith("_")}
            assert idf["rec_code"] == "HF" and idf["comp_code"] == "HD", \
                f"final calibration lock flag fix: {arm_id} record texts are written for HF recorded, HD compromise"
            if identity[arm_id]["_verdicts"][1] == "FAIL":
                assert status == "RUN_WITH_DEVIATION", (
                    f"final calibration lock flag fix: {arm_id} fails by option identity but is routed {status}; "
                    "it must be retained with its measured baseline (RUN_WITH_DEVIATION)")
            texts = calibration_lock.IDENTITY_RECORD_TEXT[arm_id]
            for key in ("terminal_lock_verdict", "band_verdict", "disposition"):
                rec[key] = texts[key].format(**idf)
            trail = copy.deepcopy(rec["trail"])
            q = [m for m in trail.get("value_moves", [])
                 if str(m.get("lever", "")).startswith("QUALITY step")]
            assert len(q) == 1, f"final calibration lock flag fix: {arm_id} trail has {len(q)} QUALITY-step lines, not 1"
            q[0]["basis"] = q[0]["basis"] + calibration_lock.IDENTITY_TRAIL_NOTE.format(**idf)
            rec["trail"] = trail
        if status == "RUN_WITH_DEVIATION":
            rec["deviation_gate"] = (calibration_lock.IDENTITY_RECORD_TEXT[arm_id]["deviation_gate"].format(**idf)
                                     if idf is not None else calibration_lock.DEVIATION_GATE[arm_id])
        if idf is not None:                  # every note a reader sees states the compromise share
            for key in ("terminal_lock_verdict", "band_verdict", "disposition", "deviation_gate"):
                assert idf["comp_pct"] in str(rec.get(key, "")), (
                    f"final calibration lock flag fix: {arm_id} record field {key} does not state the compromise "
                    f"target's share ({idf['comp_pct']})")
        if status == "EXIT":
            rec["exit_record"] = calibration_lock.EXIT_RECORD[arm_id]
        cal = st.setdefault("calibration", {
            "locked": True, "g3_date": calibration_lock.G3_DATE,
            "lock_list": "calibration/FINAL_LOCK_LIST_2026-07-02.json",
            "terminal_criterion": lock["terminal_criterion"], "arms": {}})
        cal["arms"][fmt] = rec
        n_arms += 1

        # routing flags, composed from the lock list's own measured numbers (never typed here).
        # 2026-09-29: the option-identity arms (kettles, desks) take the corrected text, which
        # states the compromise target's own share; the record above keeps its final calibration lock text.
        if arm_id in identity:
            txt = calibration_lock.IDENTITY_FLAG_TEXT[arm_id].format(**idf)
            assert txt.startswith("CALIBRATION_DEVIATION") and "words arm" not in txt \
                and ("pictures arm" in txt) == (fmt == "pictures"), f"final calibration lock flag fix: {arm_id} text"
            st["flags"].append(txt)
        elif status == "RUN_WITH_DEVIATION":
            w = arm.get("wave3") or {}
            ci = w.get("wilson95") or ["?", "?"]
            st["flags"].append(
                f"CALIBRATION_DEVIATION (final calibration lock {calibration_lock.G3_DATE}, {fmt} arm): terminal baseline "
                f"{w.get('target_share_pct')} percent [{ci[0]}, {ci[1]}] (n={w.get('n')}, "
                f"wave 3) - " + calibration_lock.DEVIATION_GATE[arm_id])
        # CORRECTED 2026-09-29: the final calibration lock flagged any check-only pair whose lock-list
        # band verdict contained the word "HARD", which caught tier-1 televisions ("OUT OF BAND (CI
        # straddles the 75 hard limit)") at 74.7 percent. The registered hard limits apply to the
        # measured POINT share (calibration/calibration_analysis.verdict_for: outside [25, 75]), and
        # 74.7 is inside them. The flag now follows the point share, and the flagged set must equal
        # calibration_lock.HARD_LIMIT_FLAG_ARMS or the build refuses. (The limits are symmetric, so the
        # option the share is counted on does not matter.)
        w1 = arm.get("wave1") or {}
        p1 = w1.get("target_share_pct")
        lo_lim, hi_lim = calibration_lock.HARD_LIMITS_PCT
        if status == "CHECK_ONLY" and p1 is not None and not (lo_lim <= p1 <= hi_lim):
            hard_flagged.add(arm_id)
            ci = w1.get("wilson95") or ["?", "?"]
            st["flags"].append(
                f"CALIBRATION_HARD_LIMIT_FLAG (final calibration lock {calibration_lock.G3_DATE}): the tier-1 pair measured "
                f"{w1.get('target_share_pct')} percent [{ci[0]}, {ci[1]}] (n={w1.get('n')}, "
                "wave 1) - beyond the 25-75 hard limits; flagged to the Analysis Plan's "
                "stimulus-defect branch exactly as the manuscript's calibration paragraph "
                "pre-committed (tier-1 values are never adjusted).")

    assert hard_flagged == calibration_lock.HARD_LIMIT_FLAG_ARMS, (
        f"final calibration lock flag fix: hard-limit flags {sorted(hard_flagged)} differ from the registered "
        f"{sorted(calibration_lock.HARD_LIMIT_FLAG_ARMS)}")
    print(f"  hard limits: {len(hard_flagged)} check-only pair outside the 25-75 point limits "
          f"({', '.join(sorted(hard_flagged))})")

    # compromise-precondition flags on the SOT cells whose compromise target starts ahead.
    # CORRECTED 2026-09-29. the final calibration lock hard-coded three run-with-deviation arms (tier-2 earbuds, tier-3 standing
    # desks, pictures water bottles), reading each arm's recorded target share as the compromise
    # target's share. That recorded share is the category-level calibration target (the rule
    # ingest.load_stimuli applies: the first decoy target listed for the category), which is HD in
    # eight categories but HF in the electric kettles and the standing desks. So the desks (HF 66.7,
    # HD 33.3) were flagged by mistake, the kettles (HF 44.7, HD 55.3) were missed, and the tier-1
    # pairs (never adjusted; premium targets at 64.6 to 80.0) were never considered. The flag is now
    # computed for EVERY fielded arm from the compromise target's own two-option share, and the
    # resulting set must equal calibration_lock.COMPROMISE_DESCRIPTIVE_CELLS or the build refuses.
    # (cat_focal, ROLE: the option-identity block above the arm loop.)

    def _terminal_share(arm):
        """(percent, where) of the arm's terminal measurement of the category-level target: wave 3
        when recorded, else the tier-1 wave-1 record, else the lock trail's own terminal point."""
        if arm.get("wave3"):
            return arm["wave3"]["target_share_pct"], f"wave 3, n={arm['wave3']['n']}"
        if arm.get("wave1"):
            return arm["wave1"]["target_share_pct"], f"wave 1, n={arm['wave1']['n']}"
        tr = arm.get("trail") or {}
        if tr.get("wave2_share_pct_at_nudged_values") is not None:
            return tr["wave2_share_pct_at_nudged_values"], "wave 2"
        if tr.get("wave1_share_pct_at_original_values") is not None:
            return tr["wave1_share_pct_at_original_values"], "wave 1"
        return None, None

    flagged_cells = set()
    for arm in lock["arms"]:
        arm_id = arm["arm_id"]
        if calibration_lock.ROUTING[arm_id] == "EXIT":
            continue                          # no fielded compromise cell (pictures hard drives)
        fmt = ARM_FMT[arm_id.split("::")[0]]
        cat, tier = arm["category"], arm["tier"]
        sot_id = f"SOT_{cat}_t{tier}"
        sot = by_id.get(sot_id)
        if sot is None:
            continue
        pct, where = _terminal_share(arm)
        assert pct is not None, f"final calibration lock flag fix: no terminal share recorded for {arm_id}"
        comp_t, focal = sot["target"], cat_focal[cat]
        comp_pct = round(pct if comp_t == focal else 100.0 - pct, 1)
        if comp_pct < calibration_lock.COMPROMISE_TARGET_MAX_BASELINE_PCT:
            continue
        flagged_cells.add((sot_id, fmt))
        if comp_t == focal:
            share_txt = f"{comp_pct:.1f} percent of the two-option choice"
        else:
            share_txt = (f"{comp_pct:.1f} percent of the two-option choice (100 minus the "
                         f"{pct:.1f} percent the calibration record gives {focal}, "
                         f"{ROLE[focal]}, which is that record's target for this category)")
        note = ""
        if tier == 1:
            note += " The tier-1 values are published and are never adjusted."
        if fmt == "pictures":
            note += " PICTURES ARM ONLY: the numbers and words compromise cells are unaffected."
        elif fmt == "words":
            note += " WORDS ARM ONLY: the numbers and pictures compromise cells are unaffected."
        sot["flags"].append(
            f"COMPROMISE_PRECONDITION_VIOLATED (final calibration lock {calibration_lock.G3_DATE}; corrected 2026-09-29): the "
            f"compromise target ({comp_t}, {ROLE[comp_t]}) took {share_txt} at the terminal "
            f"calibration measurement ({where}; {fmt} format, recorded on {arm['stimulus_id']}), "
            f"at or above the registered limit of "
            f"{calibration_lock.COMPROMISE_TARGET_MAX_BASELINE_PCT:.0f} percent, so the corrected "
            "compromise test's precondition (the compromise target must start behind its "
            "competitor) fails. This compromise cell fields as built and is reported "
            "descriptively, outside every confirmatory compromise contrast." + note)
    assert flagged_cells == calibration_lock.COMPROMISE_DESCRIPTIVE_CELLS, (
        "final calibration lock flag fix: computed compromise-descriptive cells differ from the registered set: "
        f"extra {sorted(flagged_cells - calibration_lock.COMPROMISE_DESCRIPTIVE_CELLS)}, "
        f"missing {sorted(calibration_lock.COMPROMISE_DESCRIPTIVE_CELLS - flagged_cells)}")
    print(f"  compromise precondition: {len(flagged_cells)} descriptive compromise cells, computed "
          "by option identity and matching the registered set")

    # the exited pictures hard-drives cells: the exit record on all three format cells
    for sid in ("BIN_hard_drives_t2", "FRQ_hard_drives_t2", "SOT_hard_drives_t2"):
        by_id[sid]["flags"].append(calibration_lock.EXIT_RECORD["pictures::BIN_hard_drives_t2"]
                                   + (" (record also on this BIN cell's calibration block)"
                                      if sid.startswith("BIN") else
                                      " (full record on the BIN cell's calibration block)"))

    # lock every stimulus; siblings point at their cell's record
    for s in stimuli:
        s["calibration_locked"] = True
        if "calibration" in s:
            continue
        c = cat_by_id.get(s["category"]) or {}
        if c.get("price_free") or c.get("price_free_variant_of"):
            s["flags"].append(f"G3_LOCKED ({calibration_lock.G3_DATE}): price-free variant category, "
                              "outside the 25-pair calibration set; values frozen as built.")
        elif s.get("memorization_tier") == 1:
            s["flags"].append(f"G3_LOCKED ({calibration_lock.G3_DATE}): tier-1 values fixed by fidelity "
                              "to the published source; the check-only calibration share is "
                              "recorded on this category's tier-1 BIN cell.")
        else:
            s["flags"].append(f"G3_LOCKED ({calibration_lock.G3_DATE}): values frozen from the "
                              "final calibration lock-calibrated binary anchor (calibration record on this "
                              "category-tier's BIN cell).")

    # the canonical enrichment block (amendment (c) adopted at the final calibration lock) + coverage assertion
    enrich.validate_enrichment(calibration_lock.ENRICHMENT, cat_by_id)
    enr_block = {"scope": {"tiers": calibration_lock.ENRICHMENT_SCOPE["tiers"],
                           "structures": calibration_lock.ENRICHMENT_SCOPE["structures"]},
                 "note": calibration_lock.ENRICHMENT_SCOPE["note"],
                 "by_category": calibration_lock.ENRICHMENT}
    n_enriched = 0
    for s in stimuli:
        if not calibration_lock.stimulus_is_enriched(s):
            continue
        optsets = [s["options"]] + [pv.get("options", [])
                                    for pv in (s.get("placement_variants") or {}).values()]
        picv = (s.get("format_variants") or {}).get("pictures")
        if picv and picv.get("options"):
            optsets.append(picv["options"])
        for opts in optsets:
            for o in opts:
                assert enrich.entry_for(enr_block, s, o) is not None, \
                    f"final calibration lock enrichment missing: {s['id']} option {o.get('code')}"
        n_enriched += 1
    print(f"  final calibration lock lock applied: {n_arms} calibration arms asserted against the lock list; "
          f"{n_enriched} stimuli in the enrichment scope; every stimulus calibration_locked")
    # ===========================================================================================

    out = {
        "meta": {
            "version": "1.0-locked",
            "frozen_at": calibration_lock.G3_DATE,
            "design_spec": "the Method section and Web Appendix B of the manuscript",
            "blueprint": "the Method section and Web Appendix B of the manuscript",
            "note": ("Locked single source of truth (terminal calibration lock, 2026-07-02). "
                     "Tier-1 carries exact published values (check-only in calibration); tiers 2 "
                     "and 3 carry the terminal calibration values; the words arms share their "
                     "category's numbers values; the two per-format pictures arms carry their "
                     "own locked values inside format_variants.pictures.options; the pictures "
                     "hard-drives cells exited the design (see meta.g3.exited_cells). The "
                     "enrichment block below is the canonical product-page text for the "
                     "adjustable tiers. Generated by build_stimuli.py from stimuli/fragments/"
                     "*.json - never hand-edit this file."),
            "n_categories": len(cats),
            "n_stimuli": len(stimuli),
            "g3": {
                "date": calibration_lock.G3_DATE,
                "lock_list": "calibration/FINAL_LOCK_LIST_2026-07-02.json",
                "routing": "stimuli/calibration_lock.py (the authors' routing decision, 2026-07-02)",
                "terminal_criterion": lock["terminal_criterion"],
                "exited_cells": ["BIN_hard_drives_t2 (pictures)", "FRQ_hard_drives_t2 (pictures)",
                                 "SOT_hard_drives_t2 (pictures)"],
                "geometry_strengthened": {"frq_margins": [0.25, 0.25], "rng_b_factor": 1.2,
                                          "note": ("wave-3 amendment (d) adopted at the final calibration lock; tier-1 "
                                                   "frequency decoys stay published (never "
                                                   "regenerated); the range decoy is "
                                                   "engine-built at every tier")},
                "pre_lock_snapshot": "stimuli/stimuli_prelock.json",
            },
        },
        "enrichment": enr_block,
        "categories": cats,
        "stimuli": stimuli,
    }
    path = os.path.join(HERE, "stimuli.json")
    json.dump(out, open(path, "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False)
    print(f"\nwrote {os.path.relpath(path, HERE)}: {len(cats)} categories, {len(stimuli)} stimuli")
    # quick structure-coverage report
    from collections import defaultdict
    bycat = defaultdict(list)
    for s in stimuli:
        bycat[s["category"]].append(s["structure"])
    exp_full = {"BIN","FRQ","RNG","PHT","SOT","MOT","EXC","SYM","SIM"}   # EXC = extremity control (path a)
    exp_pf = {"BIN","FRQ","RNG","PHT"}   # price-free arm = attraction family only (by design)
    for c in cats:
        got = set(bycat[c["id"]])
        exp = exp_pf if c.get("price_free") else exp_full
        miss = exp - got
        tag = f"{len(got)}/{len(exp)} structures" + ("  (price-free attraction arm)" if c.get("price_free") else "")
        print(f"  {c['id']:18s}: {tag}" + (f"  MISSING {sorted(miss)}" if miss else "  complete"))

if __name__ == "__main__":
    main()
