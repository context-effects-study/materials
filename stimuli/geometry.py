"""geometry.py: the deterministic geometry engine that builds every choice-set structure from a two-option pair.

Given a category's binary pair (a premium option HD and a budget option HF on two attributes), build()
constructs the nine registered structures by fixed rules:
  BIN  the two-option baseline
  FRQ  frequency decoy: a third option worse than the target on both attributes
  RNG  range decoy: matches the target on its strong attribute and extends the range of the weak
       attribute past the target, so the target weakly dominates it
  PHT  phantom: superior to the target on exactly one attribute, shown as unavailable
  SOT  compromise: a new extreme beyond the target, so the target becomes the middle option
  MOT  extremity treatment: a 12-option menu in three quality tiers (four options per tier)
  EXC  extremity control: one option at each of the three MOT tiers
  SYM  upscaling: a symmetric decoy dominated by both focal options
  SIM  similarity: a near-copy of one focal option, dominated by neither
Attribute caps (for example a 5.0-star ceiling) are respected, and values are rounded to realistic steps.
A cell whose premium option already sits at a cap is flagged, never shipped silently.

Tier-1 published values are kept exactly for the structures that have a published form; the constructed
structures (PHT, SIM, SOT, RNG) are rebuilt from the published pair for every cell. The values of the
first submission are kept, with their sources, in stimuli/fragments/*_receipts.md.
Manuscript: Method ("Effects and registered tests") and Web Appendix B.

Imported by build_stimuli.py and the tier generators; not run on its own.
"""

def _round(name, v):
    """Realistic, discrete rounding per attribute kind."""
    n = name.lower()
    if "price" in n or "cost" in n:
        return round(v, 2)     # round to the cent; do NOT force .99 (it drifted whole-dollar
        #                        published focal prices: $40 -> $39.99 vs the published $40)
    if "rating" in n or "star" in n:
        return round(v, 1) if v <= 5 else round(v)              # stars: 1 dp; 0-100 rating: integer
    if "review" in n:
        return int(round(v / 100.0) * 100)                     # review counts -> nearest 100
    return round(v)                                             # storage/capacity/quality -> whole

def anchor_from_bin(bin_stim, attrs_meta):
    """Reconstruct the {A,B} anchor from a BIN stimulus's HF/HD options."""
    opts = {o.get("code", "").upper(): o for o in bin_stim["options"]}
    hf, hd = opts.get("HF"), opts.get("HD")
    higher = [a for a in attrs_meta if a["direction"] == "higher_better"]
    lower = [a for a in attrs_meta if a["direction"] == "lower_better"]
    if not (hf and hd and higher and lower):
        return None                                            # price-free or malformed: caller skips
    an, bn = higher[0]["name"], lower[0]["name"]
    return {"A": {"name": an, "hf": hf["attrs"][an], "hd": hd["attrs"][an]},
            "B": {"name": bn, "hf": hf["attrs"][bn], "hd": hd["attrs"][bn]}}

# R3-2C decoy-target counterbalance: which focal the ATTRACTION decoys (FRQ/RNG/PHT) favour, in
# tier-2 and tier-3 (tier-1 keeps the published premium target). ~half HD (premium), ~half HF (budget)
# across the 10 categories, so the attraction effect is not confounded with always-favouring-premium.
DECOY_TARGET = {
    "hard_drives": "HD", "bluetooth_speakers": "HF", "earbuds": "HD", "restaurants": "HF",
    "televisions": "HD", "water_bottles": "HF", "backpacks": "HD",
    "standing_desks": "HF", "robot_vacuums": "HD", "electric_kettles": "HF",
}  # 5 HD, 5 HF

def exc_from_mot(mot_stim, base):
    """Build the EXC extremity control (single option per tier) directly from an existing MOT menu, so
    EXC inherits MOT's exact tier centers (High/Middle/Low). This is the authoritative builder used by
    build_stimuli.py: deriving EXC from the actual MOT cell guarantees the two menus share their three
    tiers EXACTLY and differ only in options-per-tier, even for published tier-1 MOT cells whose
    Middle tier is the real published value (not an engine midpoint). path a, 2026-06-13. `base` carries
    the cell's category/stem/tier/format scaffold (same as build()'s base dict)."""
    by_tier = {}
    for o in mot_stim["options"]:
        if o.get("tier") not in by_tier:                       # the four within a MOT tier are identical
            by_tier[o["tier"]] = o
    exc_opts = []
    for tname in ("High", "Middle", "Low"):
        src = by_tier.get(tname)
        if src is None:
            continue
        exc_opts.append({"code": f"EXC_{tname[0]}", "is_hd": bool(src.get("is_hd")),
                         "available": True, "attrs": dict(src["attrs"]), "tier": tname})
    return {**base, "id": mot_stim["id"].replace("MOT_", "EXC_", 1), "structure": "EXC",
            "options": exc_opts, "target": None, "competitor": None,
            "statistic": "extreme_tier_share_single_per_tier",
            "flags": ["EXC_GENERATED: single-option-per-tier extremity control built from the matched MOT "
                      "menu's tier centers (High/Middle/Low); shares MOT's tiers exactly, differs only in "
                      "options-per-tier (path a, 2026-06-13; compromise SOT untouched)."]}


def build(anchor, attrs_meta, price_free=False, caps=None, tier=2, cat_id="cat",
          stem="Imagine you are shopping. You are considering the following options:",
          decoy_target="HD", frq_margins=(0.12, 0.08), rng_b_factor=0.7):
    """Return a list of 9 stimulus dicts (memorization_tier=tier) for the anchor.
    decoy_target ("HD"|"HF") flips the attraction decoys (FRQ/RNG/PHT) to favour the premium or the
    budget option; SOT/MOT/SYM/SIM are unaffected (not part of the R3-2C decoy-target counterbalance).

    frq_margins / rng_b_factor (added 2026-07-02, the calibration wave-3 registered margin-
    strengthening correction - CALIBRATION_DESIGN wave-3 amendment (d)): frq_margins = (fraction of
    the strong-attribute span the FRQ decoy sits below its target, fraction worse on the weak
    attribute); rng_b_factor = how far the HD-target RNG decoy extends the price range past the
    target (0.7 = 70% higher). DEFAULTS PRESERVE THE PRE-WAVE-3 GEOMETRY EXACTLY (a rebuild of the
    existing stimuli.json is byte-identical); the strengthened values (0.25, 0.25) / 1.2 are used
    by the wave-3 geometry-check kit and enter the confirmatory stimuli only at the final calibration rebuild
    under the locking rule."""
    caps = caps or {}
    A, B = anchor["A"], anchor["B"]
    an, bn = A["name"], B["name"]
    a_lo, a_hi = A["hf"], A["hd"]
    span = a_hi - a_lo
    b_hf, b_hd = B["hf"], B["hd"]
    # "worse on B": for price (lower_better) worse = higher; for a 2nd quality, worse = lower.
    b_worse = (lambda v, f: v * (1 + f)) if not price_free else (lambda v, f: v * (1 - f))
    a_cap = caps.get(an)
    # avoid implausible "perfect" ceilings on 0-100 expert scales (extend only to cap-1, e.g. 99 not
    # 100, since the published max sits at 98-99); small star scales keep their real max (5.0 is plausible).
    a_cap_eff = (a_cap - 1) if (a_cap is not None and a_cap >= 100) else a_cap

    def opt(code, a, b, is_hd, available=True, exact_a=False, exact_b=False, **extra):
        """exact_a / exact_b pass an anchor coordinate through UNROUNDED. Anchor (focal) values are
        published/committed discrete values already; re-rounding them drifted earbuds t1's focals
        (reviews 1,147 -> 1,100 and 11,076 -> 11,100 via the nearest-100 rule) in the regenerated
        PHT/SIM/SOT cells and broke the registered shared-binary-control claim (M2, fixed 2026-07-01).
        Derived (constructed) coordinates keep the realistic rounding."""
        return {"code": code, "is_hd": is_hd, "available": available,
                "attrs": {an: (a if exact_a else _round(an, a)),
                          bn: (b if exact_b else _round(bn, b))}, **extra}

    def beyond_A(frac):
        """(value, no_room, clamped). no_room=True only on a true ceiling collapse."""
        v = a_hi + frac * span
        clamped = False
        if a_cap_eff is not None and v > a_cap_eff:
            v, clamped = a_cap_eff, True
        return v, (v <= a_hi + 1e-9), clamped

    HF = opt("HF", a_lo, b_hf, False, exact_a=True, exact_b=True)
    HD = opt("HD", a_hi, b_hd, True, exact_a=True, exact_b=True)
    base = dict(category=cat_id, memorization_tier=tier, format="numbers", forced=True, stem=stem)
    out = []

    # attraction-decoy target (HD = premium, strong on quality A; HF = budget, strong on price B)
    if decoy_target == "HF":
        t_a, t_b, tcode, ccode = a_lo, b_hf, "HF", "HD"
    else:
        t_a, t_b, tcode, ccode = a_hi, b_hd, "HD", "HF"
    hf_note = (lambda base_flag: base_flag if decoy_target == "HD"
               else base_flag + ["DECOY_TARGET_HF: attraction decoy favours the budget option (R3-2C counterbalance)"])

    out.append({**base, "id": f"BIN_{cat_id}_t{tier}", "structure": "BIN",
                "options": [HF, HD], "target": None, "competitor": None,
                "statistic": None, "flags": []})

    # FRQ: decoy dominated by the TARGET on both attributes (asymmetric; not by the competitor)
    frq = opt("DECOY", t_a - frq_margins[0] * span, b_worse(t_b, frq_margins[1]), False)
    out.append({**base, "id": f"FRQ_{cat_id}_t{tier}", "structure": "FRQ",
                "options": [HF, HD, frq], "target": tcode, "competitor": ccode,
                "statistic": "target_share_vs_binary", "flags": hf_note([])})

    # RNG: the REGISTERED range decoy (corrected 2026-07-01, M1). Huber-Payne-Puto's R placement:
    # the decoy MATCHES the target on the target's STRONG attribute and is far worse on the target's
    # WEAK attribute, extending the set's range past the target in the worse direction. The target
    # therefore weakly dominates it (better on nothing, clearly better on one attribute) while the
    # competitor does not, which is what keeps RNG an attraction structure and distinct from both the
    # FRQ decoy (worse on both attributes by modest margins) and the SOT compromise extreme (which
    # extends the STRONG axis beyond the target). No ceiling logic is needed: the strong-attribute
    # value is the target's own. (The earlier non-dominated build, decoy BETTER than the target on
    # the strong axis, contradicted the registered test; V1 values preserved in *_receipts.md.)
    if decoy_target == "HD":
        # weak axis = B: price for price-bearing (worse = 70% higher, the expensive range extreme);
        # 2nd quality for price-free (a GENTLE 25% cut; a deeper crash made physically implausible values).
        rng_b = b_worse(b_hd, 0.25) if price_free else b_worse(b_hd, rng_b_factor)
        rng = opt("RANGE_DECOY", a_hi, rng_b, False, exact_a=True)
        rflags = []
    else:  # HF target (price-bearing): equal price; quality far below HF extends the quality range down
        # (floored at 45% of HF's value so the decoy stays physically plausible on coarse scales).
        rng_a = max(a_lo - 0.5 * span, 0.45 * a_lo)
        rng = opt("RANGE_DECOY", rng_a, b_hf, False, exact_b=True)
        rflags = ["DECOY_TARGET_HF: range decoy extends the quality range below the budget target "
                  "at equal price (R3-2C counterbalance; registered dominated form)"]
    out.append({**base, "id": f"RNG_{cat_id}_t{tier}", "structure": "RNG",
                "options": [HF, HD, rng], "target": tcode, "competitor": ccode,
                "statistic": "target_share_vs_binary", "flags": rflags})

    # PHT: unavailable phantom superior on the TARGET's strong axis only (PR placement).
    if decoy_target == "HD":
        pav, p_noroom, _ = beyond_A(0.4)
        pht = opt("PHANTOM", pav, b_hd, False, available=False, exact_b=True)   # superior on quality, equal price
        pflags = ["PHT_PR_GENERATED: superior on the strong attribute only, equal on B (R1/Pettibone-Wedell PR)"]
        if p_noroom:
            pflags.append("PHT_NO_ROOM: strong attribute at ceiling; phantom equals HD on A (weak) - flagged for the design review")
    else:  # HF target: phantom superior on price only (cheaper than HF), equal quality, unavailable
        pht = opt("PHANTOM", a_lo, b_hf * 0.9, False, available=False, exact_a=True)
        pflags = ["PHT_PR_GENERATED (HF target): superior on price only (cheaper than the budget option), equal quality (R3-2C)"]
    out.append({**base, "id": f"PHT_{cat_id}_t{tier}", "structure": "PHT",
                "options": [HF, HD, pht], "target": tcode, "competitor": ccode,
                "statistic": "target_share_vs_binary", "flags": pflags})

    eav, e_noroom, _ = beyond_A(0.5)
    ext = opt("EXTREME", eav, b_worse(b_hd, 0.4), False)
    sflags = ["SOT_GENERATED: new extreme beyond HD; HD is the middle; relative-share statistic"]
    if e_noroom:
        sflags.append("SOT_NO_ROOM: A at ceiling; extreme equals HD on A (breaks middle) - flagged for the design review")
    out.append({**base, "id": f"SOT_{cat_id}_t{tier}", "structure": "SOT",
                "options": [HF, HD, ext], "target": "HD", "competitor": "HF",
                "statistic": "target_relative_share_over_target_plus_competitor", "flags": sflags})

    mid_a, mid_b = (a_lo + a_hi) / 2, (b_hf + b_hd) / 2
    # High and Low tiers sit on the anchor values themselves -> exact; Middle is derived -> rounded.
    tiers = [("High", a_hi, b_hd, True, True), ("Middle", mid_a, mid_b, False, False),
             ("Low", a_lo, b_hf, False, True)]
    mot_opts, letters, i = [], "ABCDEFGHIJKL", 0
    for tname, av_, bv_, ishd, ex in tiers:
        for _ in range(4):
            mot_opts.append(opt(letters[i], av_, bv_, ishd, brand=f"Brand {letters[i]}", tier=tname,
                                exact_a=ex, exact_b=ex))
            i += 1
    out.append({**base, "id": f"MOT_{cat_id}_t{tier}", "structure": "MOT",
                "options": mot_opts, "target": None, "competitor": None,
                "statistic": "extreme_tier_share_vs_matched_EXC", "flags": []})

    # EXC: the extremity CONTROL (path a, 2026-06-13, decided by the authors). One option at EACH of MOT's
    # three quality tiers (High, Middle, Low), built from the SAME tier centers as the MOT treatment
    # menu above (the same (av_, bv_) per tier), so EXC and MOT share their tiers exactly and differ
    # ONLY in how many options sit at each tier (one here, four in MOT). This makes the registered
    # extremity statistic "extreme-tier share, MOT vs EXC" a clean Sharif between-menu comparison: two
    # menus over identical tiers differing only in options-per-tier. EXC is its OWN control structure;
    # it does NOT touch the compromise SOT (built above) or the shared BIN control. Each option carries
    # its menu-quality 'tier' label (High/Middle/Low) so the validator can confirm the three tiers are
    # genuinely distinct and match MOT. The High option is the HD option (is_hd True); Middle and Low
    # are the menu-tier centers. No new free-standing middle is created for any compromise statistic
    # (this Middle belongs only to EXC's extremity control, never to the compromise SOT).
    exc_opts = []
    for tname, av_, bv_, ishd, ex in tiers:
        exc_opts.append(opt(f"EXC_{tname[0]}", av_, bv_, ishd, tier=tname, exact_a=ex, exact_b=ex))
    out.append({**base, "id": f"EXC_{cat_id}_t{tier}", "structure": "EXC",
                "options": exc_opts, "target": None, "competitor": None,
                "statistic": "extreme_tier_share_single_per_tier",
                "flags": ["EXC_GENERATED: single-option-per-tier extremity control on MOT's three tiers "
                          "(High/Middle/Low); the matched control for the MOT extremity statistic (path a, "
                          "2026-06-13). Shares MOT's tier centers exactly; differs only in options-per-tier."]})

    sym = opt("SYM_DECOY", a_lo, b_hd, False, exact_a=True, exact_b=True)
    out.append({**base, "id": f"SYM_{cat_id}_t{tier}", "structure": "SYM",
                "options": [HF, HD, sym], "target": "HD", "competitor": "HF",
                "statistic": "hd_share_vs_binary",
                "flags": ["SYM_SAME_PAGE: same-page presentation mandatory"]})

    # SIM: clone is a NON-DOMINATED near-duplicate of HF - one minimum-distinguishable unit BETTER on
    # A and one unit WORSE on B, so neither dominates the other and the step survives realistic
    # rounding (a percentage step rounds away). The clone steals from the option it resembles (HF);
    # the registered statistic tracks the UNCLONED focal (HD).
    def unit_for(name):
        n = name.lower()
        if "price" in n or "cost" in n: return 1.0          # .99 pricing: +$1 stays distinct
        if ("rating" in n or "star" in n) and caps.get(name, 99) <= 5: return 0.1
        if "review" in n: return 100.0
        return 1.0
    uA, uB = unit_for(an), unit_for(bn)
    # clone distance ~12% of the HF-HD gap, floored at one survivable unit, so the clone is a
    # meaningful near-neighbour at EVERY scale (fixes the suction 2000->2001 degeneracy R1 flagged).
    stepA = max(uA, 0.12 * abs(a_hi - a_lo))
    stepB = max(uB, 0.12 * abs(b_hd - b_hf))
    clone_b = (b_hf + stepB) if not price_free else (b_hf - stepB)
    clone_hf = opt("CLONE", a_lo + stepA, clone_b, False, clone_of="HF")
    # Two-placement (the authors decision 3 / R1): also clone the PREMIUM option. clone-HD sits one step
    # LOWER on quality and one step BETTER (cheaper) on price than HD -> a non-dominated near-neighbour
    # of HD that steals from HD; the uncloned focal is then HF.
    clone_hd_b = (b_hd - stepB) if not price_free else (b_hd + stepB)
    clone_hd = opt("CLONE", a_hi - stepA, clone_hd_b, True, clone_of="HD")
    out.append({**base, "id": f"SIM_{cat_id}_t{tier}", "structure": "SIM",
                "options": [HF, HD, clone_hf], "target": "HD", "competitor": "HF",
                "statistic": "uncloned_relative_share_HD_vs_HF", "sim_placement": "clone_HF",
                "placement_variants": {"clone_HD": {
                    "options": [HF, HD, clone_hd], "target": "HF", "competitor": "HD",
                    "statistic": "uncloned_relative_share_HF_vs_HD"}},
                "flags": ["SIM_TWO_PLACEMENT: primary clones the budget option (HF; uncloned focal = HD); "
                          "placement_variants.clone_HD clones the premium option (HD; uncloned focal = HF). "
                          "Delivered as two sub-conditions -> doubles SIM participants (authors' design decision 3); "
                          "the allocation and power are in the cell plan."]})
    return out
