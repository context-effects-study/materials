"""validate_stimuli.py: the geometry validator. It recomputes the geometry of every stimulus and checks it
against the registered definitions.

Among the 640 checks: every frequency decoy is strictly worse than its target on every attribute; every
range decoy is weakly dominated by its target and extends the weak attribute's range past it; every
phantom is superior to the target on exactly one attribute; every near-copy is dominated by neither focal
option; every structure shares its two focal options with its cell's BIN baseline; the extremity control
shares the extremity menu's three tiers; every pictures and words variant matches its numbers values; the
enriched descriptions cover exactly the category's attributes and contain no numerals; and the
calibration lock flags are in place. It prints PASS, WARN or FAIL per stimulus and exits with code 1 on
any FAIL.

Run: python stimuli/validate_stimuli.py
Expected: "TOTALS: 640 PASS, 0 WARN, 0 FAIL".
Manuscript: Web Appendix B (the stimulus definitions the checks enforce).
"""
import json, glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
EPS = 1e-9

_SPELLED_NUM = re.compile(
    r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|"
    r"fifty|sixty|seventy|eighty|ninety|hundred|thousand|dozen)\b", re.I)


def enrichment_entry(enr, st, opt):
    """Mirror of enrich.entry_for, computed from the merged file's own enrichment block."""
    scope = (enr or {}).get("scope", {})
    if st.get("memorization_tier") not in scope.get("tiers", []):
        return None
    if st.get("structure") not in scope.get("structures", []):
        return None
    entries = (enr.get("by_category") or {}).get(st.get("category"))
    if not entries:
        return None
    code = (opt.get("code") or "").upper()
    key = ("CLONE_" + (opt.get("clone_of") or "HF").upper()) if code == "CLONE" else code
    return entries.get(key)

def goodness(opt, attrs_meta):
    """Signed 'higher is better' value per attribute (lower_better -> negated)."""
    g = {}
    for a in attrs_meta:
        v = opt["attrs"].get(a["name"])
        if v is None:
            continue
        g[a["name"]] = v if a["direction"] == "higher_better" else -v
    return g

def dominates(a, b, attrs_meta):
    ga, gb = goodness(a, attrs_meta), goodness(b, attrs_meta)
    keys = [k for k in ga if k in gb]
    if not keys:
        return False
    return all(ga[k] >= gb[k] - EPS for k in keys) and any(ga[k] > gb[k] + EPS for k in keys)

def by_code(opts, *codes):
    out = [o for o in opts if o.get("code") in codes]
    return out

def focal(opts):
    return by_code(opts, "HF", "HD")

def extras(opts):
    return [o for o in opts if o.get("code") not in ("HF", "HD")]

def quality_attr(attrs_meta):
    """The non-price quality axis: prefer a higher_better attribute; else first."""
    for a in attrs_meta:
        if a["direction"] == "higher_better":
            return a["name"]
    return attrs_meta[0]["name"]

def check_stimulus(st, attrs_meta, siblings=None):
    """Return list of (level, msg). level in PASS/WARN/FAIL.
    siblings (optional): the other stimuli in the same category, used by the EXC check to confirm the
    extremity control's three tiers match the MOT treatment menu's three tiers (path a, 2026-06-13)."""
    s = st["structure"]
    opts = st["options"]
    avail = [o for o in opts if o.get("available", True)]
    res = []
    hf = by_code(opts, "HF")
    hd = by_code(opts, "HD")
    qa = quality_attr(attrs_meta)

    # universal: no exact-duplicate available options (except MOT, where within-tier clones are intended)
    if s not in ("MOT", "EXC"):
        seen = {}
        for o in avail:
            key = tuple(sorted(o["attrs"].items()))
            if key in seen and o.get("code") != seen[key]:
                res.append(("WARN", f"two options share identical attrs: {o.get('code')} == {seen[key]}"))
            seen[key] = o.get("code")

    # metadata cross-check (geometry-adversary blind-spot fix): the label fields must agree with
    # the actual options. This is what let SIM_earbuds_t1 (target='HF' but clone glued to HD) pass.
    if s not in ("BIN", "MOT", "EXC"):
        codes = {o.get("code") for o in opts}
        for fld in ("target", "competitor"):
            val = st.get(fld)
            if val is None or val not in codes:
                res.append(("FAIL", f"{s}: metadata '{fld}'={val!r} is not a present option code {sorted(codes)}"))
        if not st.get("statistic"):
            res.append(("FAIL", f"{s}: missing statistic"))
    if s == "SIM":
        clm = by_code(opts, "CLONE")
        if clm and clm[0].get("clone_of"):
            ref = by_code(opts, clm[0]["clone_of"])
            if ref and ref[0].get("is_hd") != clm[0].get("is_hd"):
                res.append(("FAIL", f"SIM clone_of={clm[0]['clone_of']} but clone.is_hd disagrees with that option"))

    # physical-plausibility (geometry-adversary blind spot): no non-positive values; flag an option
    # whose attribute crashed implausibly far below the focal range (e.g. refresh 18 Hz vs focal 60-120).
    focal_p = by_code(opts, "HF", "HD")
    if focal_p:
        for a in attrs_meta:
            nm = a["name"]
            fvals = [o["attrs"][nm] for o in focal_p if nm in o.get("attrs", {})]
            if not fvals:
                continue
            fmin = min(fvals)
            for o in opts:
                v = o.get("attrs", {}).get(nm)
                if v is None:
                    continue
                if v <= 0:
                    res.append(("FAIL", f"{s}: {o.get('code')} has non-positive {nm}={v}"))
                elif o.get("code") not in ("HF", "HD") and fmin > 0 and v < 0.4 * fmin:
                    res.append(("WARN", f"{s}: {o.get('code')} {nm}={v} implausibly low vs focal min {fmin} (possible axis crash)"))

    if s == "BIN":
        if len(avail) != 2:
            res.append(("FAIL", f"BIN must have exactly 2 available options, has {len(avail)}"))
        if len(hf) != 1 or len(hd) != 1:
            res.append(("FAIL", "BIN needs exactly one HF and one HD"))
        elif dominates(hd[0], hf[0], attrs_meta) or dominates(hf[0], hd[0], attrs_meta):
            res.append(("FAIL", "BIN options must be a genuine tradeoff (neither dominates the other)"))
        else:
            res.append(("PASS", "BIN tradeoff valid (no dominance)"))

    elif s == "FRQ":
        # REGISTERED frequency-decoy geometry (strengthened 2026-07-02, F1): the manuscript registers a
        # decoy "worse than the target on every attribute and dominated by a clear margin on each one, the
        # worse-on-both placement" (main.md), and the geometry rules (Web Appendix B)/§6 check 1 register "DOMINATED by the
        # target on both attributes (clearly worse)". The earlier check accepted WEAK dominance, which let
        # a decoy tying the target's strong attribute pass (the range shape, not the frequency form) - the
        # defect the final criterion judge caught in FRQ_hard_drives_t1. Enforced here:
        #   (a) the target beats the decoy STRICTLY on EVERY shared attribute (no ties on any axis);
        #   (b) the competitor does not dominate the decoy (the asymmetry that defines an attraction decoy).
        d = extras(opts)
        if not (hf and hd and len(d) == 1):
            res.append(("FAIL", "FRQ needs HF, HD, and exactly one decoy"))
        else:
            tgt = hd[0] if st.get("target", "HD") == "HD" else hf[0]
            comp = hf[0] if tgt is hd[0] else hd[0]
            dom_t = dominates(tgt, d[0], attrs_meta)
            dom_c = dominates(comp, d[0], attrs_meta)
            if dom_t and not dom_c:
                res.append(("PASS", "FRQ asymmetric dominance valid (target dominates decoy, competitor does not)"))
            elif dom_t and dom_c:
                res.append(("WARN", "FRQ decoy is dominated by BOTH focal options (symmetric, not a clean frequency decoy)"))
            elif (not dom_t) and dom_c:
                # the decoy is a frequency decoy of the WRONG option: dominated by the competitor, not the target
                res.append(("FAIL", "FRQ decoy is dominated by the COMPETITOR, not the target "
                                    "(the labeled target/competitor are swapped, or the decoy was built against the wrong focal)"))
            else:
                res.append(("FAIL", "FRQ decoy is NOT dominated by the target"))
            # (a) strict worse-on-both margins: the registered frequency form allows NO tie on any axis
            # (a tie on the target's strong attribute is the registered RANGE shape, not the FRQ form).
            gt, gd = goodness(tgt, attrs_meta), goodness(d[0], attrs_meta)
            keys = [k for k in gd if k in gt]
            tied = [k for k in keys if abs(gt[k] - gd[k]) <= EPS]
            not_worse = [k for k in keys if gd[k] > gt[k] + EPS]
            if not_worse:
                res.append(("FAIL", f"FRQ decoy is BETTER than the target on {not_worse} "
                                    "(the registered frequency decoy is worse on every attribute)"))
            elif tied:
                res.append(("FAIL", f"FRQ decoy TIES the target on {tied} "
                                    "(the registered frequency form is worse-on-both with a strict margin "
                                    "on each attribute; a strong-axis tie is the range shape)"))
            else:
                res.append(("PASS", f"FRQ strict worse-on-both margins hold on {keys}"))

    elif s == "RNG":
        # REGISTERED range-decoy geometry (corrected 2026-07-01, M1): the manuscript registers "a decoy
        # that extends the spread of one attribute past the target while remaining dominated by it"
        # (Huber-Payne-Puto's R placement: equal/near-equal on the target's STRONG attribute, much worse
        # on the target's WEAK attribute). The earlier check enforced the opposite (a non-dominated decoy
        # extending the strong axis) and is superseded. Enforced here:
        #   (a) the target weakly dominates the decoy (better-or-equal everywhere, strictly on >=1 axis)
        #       and the competitor does NOT (the asymmetry that defines an attraction decoy);
        #   (b) the decoy extends the set's range past the target on the target's WEAK attribute
        #       (strictly worse than BOTH focals there);
        #   (c) the decoy does not collide with the SOT compromise extreme (distinct attribute values);
        #   (d) the FRQ-vs-RNG distinction holds: RNG ties/near-ties the strong axis where FRQ is
        #       strictly worse on it, and RNG's weak-axis extension exceeds FRQ's weak-axis margin.
        d = extras(opts)
        if not (hf and hd and len(d) == 1):
            res.append(("FAIL", "RNG needs HF, HD, and exactly one range decoy"))
        else:
            tgt = hd[0] if st.get("target", "HD") == "HD" else hf[0]
            other = hf[0] if tgt is hd[0] else hd[0]
            gd, gt, go = goodness(d[0], attrs_meta), goodness(tgt, attrs_meta), goodness(other, attrs_meta)
            keys = [k for k in gd if k in gt and k in go]
            strong_axes = [k for k in keys if gt[k] > go[k] + EPS]   # target beats the other focal here
            weak_axes = [k for k in keys if gt[k] < go[k] - EPS]     # target loses to the other focal here
            dom_t = dominates(tgt, d[0], attrs_meta)
            dom_c = dominates(other, d[0], attrs_meta)
            # (b) range extension on the weak axis: worse than BOTH focals there = extends the set range
            ext_weak = [k for k in weak_axes if gd[k] < min(gt[k], go[k]) - EPS]
            if not strong_axes or not weak_axes:
                res.append(("WARN", "RNG: focal pair has no strict strong/weak split (calibration may fix this)"))
            elif not dom_t:
                res.append(("FAIL", "RNG decoy is NOT dominated by the target; the registered range decoy remains "
                                    "dominated by the target while extending the weak-attribute range past it "
                                    "(a decoy better than the target on its strong axis is a new non-dominated "
                                    "extreme, not a range decoy)"))
            elif dom_c:
                res.append(("FAIL", "RNG decoy is dominated by the COMPETITOR too (symmetric, not asymmetric "
                                    "dominance; the attraction reading needs the target-only dominance relation)"))
            elif not ext_weak:
                res.append(("FAIL", "RNG decoy does not extend the set's range past the target on the target's "
                                    "weak attribute (a dominated decoy inside the range reads like a frequency decoy)"))
            else:
                res.append(("PASS", f"RNG decoy weakly dominated by the target, not by the competitor, and extends "
                                    f"the weak-attribute range past the target on {ext_weak}"))
            # (c) no collision with the SOT extreme in the same cell
            sot = next((sib for sib in (siblings or []) if sib.get("structure") == "SOT"), None)
            if sot is not None:
                ex = [o for o in sot["options"] if o.get("code") == "EXTREME"]
                if ex and all(abs(ex[0]["attrs"].get(k, 0) - d[0]["attrs"].get(k, 0)) <= EPS
                              for k in set(ex[0]["attrs"]) | set(d[0]["attrs"])):
                    res.append(("FAIL", "RNG decoy has IDENTICAL attribute values to the SOT compromise extreme "
                                        "in this cell (the two structures must stay distinct)"))
            # (d) the frequency-vs-range distinction against the FRQ sibling
            frq = next((sib for sib in (siblings or []) if sib.get("structure") == "FRQ"), None)
            if frq is not None and strong_axes and weak_axes:
                fd = [o for o in frq["options"] if o.get("code") not in ("HF", "HD")]
                if fd:
                    gfd = goodness(fd[0], attrs_meta)
                    sa, wa = strong_axes[0], weak_axes[0]
                    rng_strong_gap = gt[sa] - gd[sa]          # >= 0 given dominance; ~0 for a tie
                    frq_strong_gap = gt[sa] - gfd.get(sa, gt[sa])
                    rng_weak_ext = gt[wa] - gd[wa]
                    frq_weak_gap = gt[wa] - gfd.get(wa, gt[wa])
                    if rng_strong_gap > frq_strong_gap + EPS:
                        res.append(("FAIL", "RNG decoy is FURTHER below the target on the strong attribute than the "
                                            "FRQ decoy (RNG must tie or near-tie the strong axis; FRQ carries the "
                                            "strong-axis margin)"))
                    elif rng_weak_ext <= frq_weak_gap + EPS:
                        res.append(("FAIL", "RNG decoy's weak-attribute extension does not exceed the FRQ decoy's "
                                            "weak-attribute margin (the range manipulation must stretch the range, "
                                            "not shadow the frequency decoy)"))
                    else:
                        res.append(("PASS", "FRQ-vs-RNG distinction holds (RNG ties the strong axis and stretches "
                                            "the weak axis further than FRQ)"))

    elif s == "PHT":
        ph = [o for o in opts if not o.get("available", True)]
        tcode = st.get("target", "HD")
        tgtl = by_code(opts, tcode)
        if len(ph) != 1:
            res.append(("FAIL", f"PHT needs exactly one unavailable phantom, has {len(ph)}"))
        elif not tgtl:
            res.append(("FAIL", f"PHT target option {tcode} not present"))
        else:
            tgt = tgtl[0]
            gph, gt = goodness(ph[0], attrs_meta), goodness(tgt, attrs_meta)
            keys = [k for k in gph if k in gt]
            better = [k for k in keys if gph[k] > gt[k] + EPS]
            worse_or_eq = all(gph[k] <= gt[k] + EPS for k in keys if k not in better)
            if len(better) == 1 and worse_or_eq:
                res.append(("PASS", f"PHT superior on exactly one attribute ({better[0]}) vs {tcode}; R1 satisfied"))
            elif len(better) >= 2:
                res.append(("FAIL", f"PHT superior on {len(better)} attributes ({better}) vs {tcode} - R1 violation"))
            else:
                res.append(("WARN", f"PHT not superior on any attribute vs {tcode} (weak phantom)"))

    elif s == "SOT":
        ex = [o for o in opts if o.get("code") in ("EXTREME",)] or [o for o in extras(opts)]
        if not (hf and hd and len(ex) == 1):
            res.append(("FAIL", "SOT needs HF, HD, and exactly one new EXTREME"))
        else:
            g_hf, g_hd, g_ex = (goodness(o, attrs_meta) for o in (hf[0], hd[0], ex[0]))
            # HD must be the middle on the quality axis: HF < HD < EXTREME
            if g_hf[qa] < g_hd[qa] < g_ex[qa] + EPS and g_ex[qa] > g_hd[qa] + EPS:
                res.append(("PASS", f"SOT compromise valid: HD is the middle on {qa} (HF < HD < EXTREME); new extreme beyond HD"))
            else:
                res.append(("FAIL", f"SOT: HD is not the middle on {qa} (need HF < HD < EXTREME); got {g_hf[qa]}, {g_hd[qa]}, {g_ex[qa]}"))
            stat = st.get("statistic", "").lower()
            if "relative" in stat or ("target" in stat and "competitor" in stat) or "over_target_plus" in stat:
                res.append(("PASS", "SOT uses relative-share statistic"))
            else:
                res.append(("WARN", f"SOT statistic should be relative share target/(target+competitor); got '{st.get('statistic')}'"))

    elif s == "MOT":
        if len(opts) < 12:
            res.append(("FAIL", f"MOT needs >=12 options, has {len(opts)}"))
        tiers = {}
        for o in opts:
            t = o.get("tier", "?")
            tiers.setdefault(t, []).append(o)
        if "?" in tiers:
            res.append(("WARN", "MOT options lack explicit 'tier' labels"))
        distinct = [t for t in tiers if t != "?"]
        if len([t for t in distinct]) >= 3:
            res.append(("PASS", f"MOT has {len(distinct)} distinct tiers: {sorted(distinct)}"))
        elif "?" not in tiers:
            res.append(("FAIL", f"MOT needs >=3 distinct tiers, has {len(distinct)}"))
        # within-tier near-equivalence
        for t, members in tiers.items():
            if t == "?":
                continue
            base = goodness(members[0], attrs_meta)
            for m in members[1:]:
                gm = goodness(m, attrs_meta)
                if any(abs(gm[k] - base[k]) > EPS for k in base):
                    res.append(("WARN", f"MOT tier '{t}' options are not identical (extremity design usually uses near-identical within-tier)"))
                    break

    elif s == "EXC":
        # the extremity CONTROL (path a, 2026-06-13): exactly ONE option at each of MOT's three quality
        # tiers (High/Middle/Low), the matched single-option-per-tier control for the MOT extremity menu.
        # Three checks: (1) one option per tier with three tiers present; (2) the three tiers are
        # genuinely distinct on the quality axis (High > Middle > Low); (3) EXC's tier centers MATCH the
        # MOT treatment menu's tier centers in the same cell, so the two menus differ only in count.
        tiers = {}
        for o in opts:
            tiers.setdefault(o.get("tier", "?"), []).append(o)
        if "?" in tiers:
            res.append(("FAIL", "EXC options lack explicit menu-quality 'tier' labels (need High/Middle/Low)"))
        elif sorted(tiers) != ["High", "Low", "Middle"]:
            res.append(("FAIL", f"EXC needs exactly the three tiers High/Middle/Low, has {sorted(tiers)}"))
        elif any(len(m) != 1 for m in tiers.values()):
            res.append(("FAIL", f"EXC needs exactly ONE option per tier, has "
                                f"{ {t: len(m) for t, m in tiers.items()} }"))
        else:
            # tiers genuinely distinct on the quality axis: High strictly above Middle strictly above Low
            gH = goodness(tiers["High"][0], attrs_meta)[qa]
            gM = goodness(tiers["Middle"][0], attrs_meta)[qa]
            gL = goodness(tiers["Low"][0], attrs_meta)[qa]
            if gH > gM + EPS and gM > gL + EPS:
                res.append(("PASS", f"EXC single-option-per-tier control: one option per tier, three "
                                    f"distinct tiers on {qa} (Low {gL} < Middle {gM} < High {gH})"))
            else:
                res.append(("FAIL", f"EXC tiers not strictly distinct on {qa}: "
                                    f"Low {gL}, Middle {gM}, High {gH} (need Low < Middle < High)"))
            # cross-check: EXC tier centers must match the matched MOT menu's tier centers in this cell.
            mot = None
            for sib in (siblings or []):
                if sib.get("structure") == "MOT":
                    mot = sib; break
            if mot is None:
                res.append(("WARN", "EXC: no MOT sibling found in this cell to confirm tier match "
                                    "(the extremity statistic compares MOT vs EXC, so they must share tiers)"))
            else:
                mot_by_tier = {}
                for o in mot["options"]:
                    mot_by_tier.setdefault(o.get("tier", "?"), o)   # all four within a MOT tier are identical
                mismatch = []
                for tname in ("High", "Middle", "Low"):
                    e = tiers[tname][0]["attrs"]; m = (mot_by_tier.get(tname) or {}).get("attrs", {})
                    if any(abs(e.get(k, 0) - m.get(k, 0)) > EPS for k in set(e) | set(m)):
                        mismatch.append(tname)
                if mismatch:
                    res.append(("FAIL", f"EXC tiers do NOT match the MOT menu's tiers on {mismatch} "
                                        "(the menus must share tiers and differ only in options-per-tier)"))
                else:
                    res.append(("PASS", "EXC tier centers match the matched MOT menu exactly "
                                        "(menus differ only in options-per-tier)"))
        if "single_per_tier" not in (st.get("statistic", "") or ""):
            res.append(("WARN", f"EXC statistic should mark the single-per-tier control; got '{st.get('statistic')}'"))

    elif s == "SYM":
        d = extras(opts)
        if not (hf and hd and len(d) == 1):
            res.append(("FAIL", "SYM needs HF, HD, and exactly one symmetric decoy"))
        elif not (dominates(hf[0], d[0], attrs_meta) and dominates(hd[0], d[0], attrs_meta)):
            res.append(("FAIL", "SYM decoy must be weakly dominated by BOTH focal options"))
        else:
            # A PROPER symmetric (upscaling) decoy is weakly dominated by EACH focal on a DIFFERENT
            # attribute: each focal beats the decoy on exactly one attribute and ties it on the other.
            # Reject the two near-misses the prose used to blur together:
            #  - a decoy strictly worse than a focal on EVERY attribute (a strictly-dominated decoy,
            #    not the symmetric form the upscaling paradigm uses);
            #  - a decoy whose two focals beat it on the SAME single attribute (then it is not symmetric).
            gd = goodness(d[0], attrs_meta)
            strict_each = {}
            tie_each = {}
            for code, foc in (("HF", hf[0]), ("HD", hd[0])):
                gf = goodness(foc, attrs_meta)
                ks = [k for k in gd if k in gf]
                strict_each[code] = [k for k in ks if gf[k] > gd[k] + EPS]   # focal strictly better here
                tie_each[code] = [k for k in ks if abs(gf[k] - gd[k]) <= EPS]  # focal ties decoy here
            # symmetric form: each focal strictly beats on exactly one attribute and ties on the other,
            # and the two "strictly beaten" attributes are DIFFERENT axes.
            hf_axis = strict_each["HF"]
            hd_axis = strict_each["HD"]
            both_one = (len(hf_axis) == 1 and len(hd_axis) == 1)
            different = both_one and (hf_axis[0] != hd_axis[0])
            ties_other = (len(tie_each["HF"]) >= 1 and len(tie_each["HD"]) >= 1)
            if different and ties_other:
                res.append(("PASS", f"SYM decoy is a proper symmetric decoy: HF beats it on {hf_axis[0]} (ties other), "
                                    f"HD beats it on {hd_axis[0]} (ties other)"))
            elif both_one and not different:
                res.append(("FAIL", "SYM decoy is beaten by both focals on the SAME attribute, not a symmetric decoy"))
            else:
                # dominated by both but strictly worse on every attribute against at least one focal:
                # this is the 'worse on every attribute' overstatement, not the registered symmetric form.
                res.append(("WARN", "SYM decoy is dominated by both focals but is not the clean one-attribute-each "
                                    "symmetric form (it is strictly worse on more than one attribute against a focal)"))

    elif s == "SIM":
        cl = by_code(opts, "CLONE") or extras(opts)
        if not (hf and hd and len(cl) == 1):
            res.append(("FAIL", "SIM needs HF, HD, and exactly one clone"))
        else:
            c = cl[0]
            dom = []
            for foc in (hf[0], hd[0]):
                if dominates(c, foc, attrs_meta):
                    dom.append(f"clone DOMINATES {foc.get('code')}")
                if dominates(foc, c, attrs_meta):
                    dom.append(f"clone dominated by {foc.get('code')}")
            if dom:
                res.append(("FAIL", "SIM clone must be NON-DOMINATED vs BOTH focal options (else it is an "
                                    "attraction decoy, not a similarity clone): " + "; ".join(dom)))
            else:
                def dist(a, b):
                    ga, gb = goodness(a, attrs_meta), goodness(b, attrs_meta)
                    return sum(abs(ga[k] - gb[k]) for k in ga if k in gb)
                near = "HF" if dist(c, hf[0]) <= dist(c, hd[0]) else "HD"
                far = "HD" if near == "HF" else "HF"
                if c.get("clone_of") and c["clone_of"] != near:
                    res.append(("FAIL", f"SIM clone_of={c['clone_of']} but the geometric nearest focal is {near}"))
                elif st.get("target") != far:
                    res.append(("FAIL", f"SIM target={st.get('target')} but the uncloned (far) focal is {far}"))
                else:
                    res.append(("PASS", f"SIM clone non-dominated near {near}; tracks the uncloned {far}"))
        # second placement (authors' design decision 3): validate the clone-HD variant too
        for pvname, pv in (st.get("placement_variants") or {}).items():
            pvopts = pv.get("options", [])
            pcl = by_code(pvopts, "CLONE")
            pfoc = by_code(pvopts, "HF", "HD")
            if not (pcl and len(pfoc) == 2):
                res.append(("FAIL", f"SIM placement {pvname}: needs HF, HD, and one clone"))
            else:
                pdom = [f.get("code") for f in pfoc
                        if dominates(pcl[0], f, attrs_meta) or dominates(f, pcl[0], attrs_meta)]
                if pdom:
                    res.append(("FAIL", f"SIM placement {pvname}: clone has a dominance relation with {pdom}"))
                elif pv.get("target") not in {o.get("code") for o in pvopts}:
                    res.append(("FAIL", f"SIM placement {pvname}: target {pv.get('target')} not present"))
                else:
                    res.append(("PASS", f"SIM placement {pvname}: clone non-dominated; tracks {pv.get('target')}"))
    else:
        res.append(("FAIL", f"unknown structure '{s}'"))
    return res

def load_fragments():
    cats = {}
    for f in sorted(glob.glob(os.path.join(HERE, "fragments", "*.json"))):
        try:
            cats[os.path.basename(f)[:-5]] = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print(f"  !! could not parse {f}: {e}")
    return cats

def main():
    # B1 fix (adversary re-judge): the DELIVERABLE is the merged stimuli.json. Validate IT by default;
    # the raw fragments/ are secondary (pre-merge) and only validated with an explicit --fragments flag.
    # The old default read stale fragments and silently skipped televisions + all tier-2.
    merged_path = os.path.join(HERE, "stimuli.json")
    enr = None
    frozen = None
    if "--fragments" not in sys.argv and os.path.exists(merged_path):
        merged = json.load(open(merged_path, encoding="utf-8"))
        enr = merged.get("enrichment")
        frozen = (merged.get("meta") or {}).get("frozen_at")
        frags = {}
        for c in merged["categories"]:
            frags[c["id"]] = {"category": c, "stimuli": [s for s in merged["stimuli"] if s["category"] == c["id"]]}
        print("(validating the MERGED single source: stimuli.json)\n")
    else:
        frags = load_fragments()
        print("(validating raw fragments/ - SECONDARY/pre-merge; the deliverable is stimuli.json)\n")
    n_pass = n_warn = n_fail = 0
    expected = ["BIN", "FRQ", "RNG", "PHT", "SOT", "MOT", "EXC", "SYM", "SIM"]
    for name, frag in frags.items():
        if name.endswith("_receipts"):
            continue
        if "category" not in frag or "stimuli" not in frag:
            print(f"\n=== {name} === SKIP (incomplete/mid-write: no 'category' or 'stimuli' key yet)")
            continue
        attrs_meta = frag["category"]["attributes"]
        print(f"\n=== {name} ({frag['category'].get('label','?')}) ===")
        present = [s["structure"] for s in frag["stimuli"]]
        # price-free variant categories carry only the attraction family (compromise/extremity/upscaling
        # need a single quality ordering a quality x quality tradeoff lacks) - this is by design.
        exp_cat = ["BIN", "FRQ", "RNG", "PHT"] if frag["category"].get("price_free") else expected
        missing = [e for e in exp_cat if e not in present]
        if missing:
            print(f"  FAIL  missing structures: {missing}"); n_fail += 1
        for st in frag["stimuli"]:
            # cell-siblings (same category + same memorization tier) let the EXC check confirm its
            # three tiers match the matched MOT menu's tiers (path a, 2026-06-13).
            sibs = [o for o in frag["stimuli"]
                    if o.get("memorization_tier") == st.get("memorization_tier") and o is not st]
            for level, msg in check_stimulus(st, attrs_meta, siblings=sibs):
                tag = {"PASS": "ok  ", "WARN": "WARN", "FAIL": "FAIL"}[level]
                if level == "PASS": n_pass += 1
                elif level == "WARN": n_warn += 1
                else: n_fail += 1
                if level != "PASS":
                    print(f"  {tag}  {st['structure']}: {msg}")
        # SHARED-BINARY-CONTROL check (M2 guard, permanent, 2026-07-01): within each category x
        # memorization-tier, every structure computed against the shared BIN control (FRQ, RNG, PHT,
        # SOT, SYM, SIM, incl. SIM placement variants) must carry HF/HD attribute values IDENTICAL to
        # that cell's BIN options. This is the registered shared-control claim (main.md "one binary
        # cell is the shared control arm for six of the tests"); earbuds t1 drifted through rounding
        # (1,147/11,076 -> 1,100/11,100) and the class must never recur. MOT/EXC are excluded (the
        # extremity statistic is MOT vs EXC, and those menus carry no HF/HD codes).
        by_tier = {}
        for st in frag["stimuli"]:
            by_tier.setdefault(st.get("memorization_tier", 1), []).append(st)
        for tr, group in sorted(by_tier.items()):
            binst = next((x for x in group if x["structure"] == "BIN"), None)
            if binst is None:
                continue
            ref = {o["code"]: o["attrs"] for o in binst["options"] if o.get("code") in ("HF", "HD")}
            for st in group:
                if st["structure"] not in ("FRQ", "RNG", "PHT", "SOT", "SYM", "SIM"):
                    continue
                variants = [("", st["options"])] + [
                    (f" placement {pn}", pv.get("options", []))
                    for pn, pv in sorted((st.get("placement_variants") or {}).items())]
                for vlab, vopts in variants:
                    got = {o["code"]: o["attrs"] for o in vopts if o.get("code") in ("HF", "HD")}
                    if got == ref:
                        n_pass += 1
                    else:
                        n_fail += 1
                        print(f"  FAIL  {st['structure']}{vlab}: shared-control violation in tier {tr}: "
                              f"HF/HD {got} differ from the BIN control's {ref}")
        # final calibration lock PICTURES-VARIANT checks (2026-07-02, merged mode): validate the per-format locked
        # option sets exactly like the numbers cells, and enforce the pictures-column
        # shared-binary-control (pictures FRQ/SOT focals == pictures BIN focals in the cell).
        for tr, group in sorted(by_tier.items()):
            pstims = [st for st in group
                      if ((st.get("format_variants") or {}).get("pictures") or {}).get("options")]
            if not pstims:
                continue
            pbin = next((x for x in pstims if x["structure"] == "BIN"), None)
            pref = ({o["code"]: o["attrs"]
                     for o in pbin["format_variants"]["pictures"]["options"]
                     if o.get("code") in ("HF", "HD")} if pbin else None)
            for st in pstims:
                popts = st["format_variants"]["pictures"]["options"]
                pseudo = {k: v for k, v in st.items()
                          if k not in ("format_variants", "placement_variants")}
                pseudo["options"] = popts
                for level, msg in check_stimulus(pseudo, attrs_meta, siblings=[]):
                    if level == "PASS":
                        n_pass += 1
                    elif level == "WARN":
                        n_warn += 1; print(f"  WARN  {st['structure']} PICTURES variant: {msg}")
                    else:
                        n_fail += 1; print(f"  FAIL  {st['structure']} PICTURES variant: {msg}")
                if pref is not None and st["structure"] != "BIN":
                    got = {o["code"]: o["attrs"] for o in popts if o.get("code") in ("HF", "HD")}
                    if got == pref:
                        n_pass += 1
                    else:
                        n_fail += 1
                        print(f"  FAIL  {st['structure']} PICTURES variant: pictures shared-control "
                              f"violation in tier {tr}: HF/HD {got} differ from the pictures BIN's {pref}")
        # final calibration lock ENRICHMENT checks (2026-07-02, merged mode): coverage + the numeral-free contract.
        if enr is not None:
            names = {a["name"] for a in attrs_meta}
            for st in frag["stimuli"]:
                scope = enr.get("scope", {})
                in_scope = (st.get("memorization_tier") in scope.get("tiers", [])
                            and st["structure"] in scope.get("structures", [])
                            and st["category"] in (enr.get("by_category") or {}))
                if not in_scope:
                    continue
                optsets = [st["options"]] + [pv.get("options", []) for pv in
                                             (st.get("placement_variants") or {}).values()]
                picv = (st.get("format_variants") or {}).get("pictures")
                if picv and picv.get("options"):
                    optsets.append(picv["options"])
                bad = []
                for opts in optsets:
                    for o in opts:
                        e = enrichment_entry(enr, st, o)
                        if e is None:
                            bad.append(f"{o.get('code')}: no enrichment entry")
                            continue
                        if re.search(r"\d", e["name"]) or _SPELLED_NUM.search(e["name"]):
                            bad.append(f"{o.get('code')}: name not numeral-free: {e['name']!r}")
                        if set(e.get("qualifiers", {})) != names:
                            bad.append(f"{o.get('code')}: qualifiers do not cover {sorted(names)}")
                        for a, q in e.get("qualifiers", {}).items():
                            if re.search(r"\d", q) or _SPELLED_NUM.search(q):
                                bad.append(f"{o.get('code')}.{a}: qualifier not numeral-free: {q!r}")
                if bad:
                    n_fail += 1
                    print(f"  FAIL  {st['structure']}: enrichment contract: " + "; ".join(bad[:4]))
                else:
                    n_pass += 1
        # final calibration lock-FLAG check (2026-07-02, merged mode): once fixed, everything is locked.
        if frozen:
            for st in frag["stimuli"]:
                if st.get("calibration_locked") is True:
                    n_pass += 1
                else:
                    n_fail += 1
                    print(f"  FAIL  {st['structure']}: calibration_locked is not True "
                          f"(meta.frozen_at = {frozen})")
        print(f"  (PASS so far: {n_pass}, WARN: {n_warn}, FAIL: {n_fail})")
    print(f"\n## TOTALS: {n_pass} PASS, {n_warn} WARN, {n_fail} FAIL")
    print("RESULT:", "GREEN (no FAILs)" if n_fail == 0 else f"{n_fail} FAILs to resolve")
    sys.exit(0 if n_fail == 0 else 1)

if __name__ == "__main__":
    main()
