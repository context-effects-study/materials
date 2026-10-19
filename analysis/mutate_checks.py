"""mutate_checks.py: shows that the tests catch a broken analysis (mutation testing).

For each mutant it copies the analysis code into its own scratch folder under the system's temporary folder,
breaks exactly one rule with an exact text edit (the edit must land exactly once, or the run stops), and runs
the tests; if every test still passes it runs the full dress rehearsal as a second layer. A mutant is killed
when either layer fails. The unchanged copy runs first and must pass both layers. The code in this folder is
never edited. Writes analysis/MUTATION_REPORT.md, naming the test that killed each mutant.

Run: python analysis/mutate_checks.py                  (every mutant; about 15 minutes)
     python analysis/mutate_checks.py --only M01,M02   (named mutants only)
"""
import argparse, datetime, os, py_compile, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ("analyze.py", "statlib.py", "synth.py", "registered_constants.py", "print_constants.py",
         "test_analysis.py", "call_bootstrap.py")
# a folder of its own (a stray results file that another run leaves in a shared folder would make the baseline
# fail its missing-value check); override with MUTANTS_SCRATCH_TAG
SCRATCH = os.path.join(tempfile.gettempdir(), "context_effects_release_mutants", datetime.date.today().isoformat(),
                       os.environ.get("MUTANTS_SCRATCH_TAG", "release"))

MUTANTS = [
    ("M01", "direction requirement removed from the human criterion", "analyze.py",
     "        right_direction = d > 0\n", "        right_direction = True\n"),
    ("M02", "direction requirement flipped", "analyze.py",
     "        right_direction = d > 0\n", "        right_direction = d < 0\n"),
    ("M03", "Holm family split dropped (one family of all seven)", "analyze.py",
     '    families = {k: v for k, v in HOLM_FAMILIES.items() if k != "format_interaction"}\n',
     '    families = {"all": list(EFFECTS)}\n'),
    ("M04", "phantom equivalence loosened to a point check", "analyze.py",
     "    equivalent = eq\n", "    equivalent = abs(delta) < PHANTOM_BAND\n"),
    ("M05", "first-trial rule without Holm (raw p below .05)", "analyze.py",
     '        diverges = bool(rej and abs(per[st]["divergence_pp"]) > RC.FIRST_TRIAL_MIN_DIVERGENCE_PP)\n',
     '        diverges = bool(per[st]["p"] < RC.FIRST_TRIAL_ALPHA and abs(per[st]["divergence_pp"]) > RC.FIRST_TRIAL_MIN_DIVERGENCE_PP)\n'),
    ("M06", "first-trial rule reverted to the point rule", "analyze.py",
     '        diverges = bool(rej and abs(per[st]["divergence_pp"]) > RC.FIRST_TRIAL_MIN_DIVERGENCE_PP)\n',
     '        diverges = bool(abs(per[st]["divergence_pp"]) > RC.FIRST_TRIAL_MIN_DIVERGENCE_PP)\n'),
    ("M07", "Bayes factor made non-directional (full normal prior)", "statlib.py",
     "    log_bf = math.log(2.0) + math.log(tail) + log_ratio\n", "    log_bf = log_ratio\n"),
    ("M08", "format interaction tested against zero, not against numbers", "analyze.py",
     '            inter = ef["delta"] - en["delta"]\n', '            inter = ef["delta"]\n'),
    ("M09", "reversed ladder ignores the middle rung", "analyze.py",
     "    elif (low - h > step) and (mid is None or low - mid > step):\n", "    elif (low - h > step):\n"),
    ("M10", "reversed-ladder attribution ignores recognition", "analyze.py",
     "    recognized = bool(missed) and all(v >= RC.RECOGNITION_CUTOFF for v in rec.values())\n",
     "    recognized = bool(missed)\n"),
    ("M11", "effect without a human counterpart never reported", "analyze.py",
     '        return "no-human-counterpart"\n', '        return "excluded(criterion-exit)"\n'),
    ("M12", "S7 back to 'more than half of seven' including similarity", "analyze.py",
     "    most_failed = n_failed_regular >= RC.MOST_FAILED_MIN\n",
     '    most_failed = sum(1 for st in EFFECTS if not criterion[st]["replicated"]) > len(EFFECTS) / 2.0\n'),
    ("M13", "model-level account threshold lowered to three", "analyze.py",
     "    if counts[best] >= RC.MODEL_ACCOUNT_MIN_AGREE:\n", "    if counts[best] >= 3:\n"),
    ("M14", "compromise precondition read from the recorded flags only", "analyze.py",
     "                   deviation_slices=deviation, compromise_descriptive=comp_desc, flagged_compromise=flagged,\n",
     "                   deviation_slices=deviation, compromise_descriptive=flagged, flagged_compromise=flagged,\n"),
    ("M15", "matched control coded with the row's own label", "analyze.py",
     "    if target is None:\n        return _treat_y(r, kind)\n", "    if True:\n        return _treat_y(r, kind)\n"),
    ("M16", "similarity clone kept in the denominator", "analyze.py",
     '            if effect == "SIM" and _is_clone(r, kind):\n', "            if False:\n"),
    ("M17", "price-free categories kept in the backbone", "analyze.py",
     '    return pf if scope == "pricefree" else (not pf)\n', '    return pf if scope == "pricefree" else True\n'),
    ("M18", "memorization adjustment uses an unrelated covariate", "analyze.py",
     "        rowsx.append((float(tier), abs(b - 50.0), bud))\n",
     "        rowsx.append((float(tier), float(len(str(cat))), bud))\n"),
    ("M19", "compromise-descriptive slices left in the confirmatory contrast", "analyze.py",
     '    drop_confirm = {"SOT": comp_desc}\n', "    drop_confirm = {}\n"),
    ("M20", "fallback benchmark not switched to first trials", "analyze.py",
     "    fallback = ft[\"fired\"]\n", "    fallback = False\n"),
    ("M21", "ceiling rule never flags a binary cell", "analyze.py",
     "                    no_room_slices.add((cat, tier, fmt))\n", "                    pass\n"),
    ("M22", "the model runner's placement field ignored", "analyze.py",
     '    for field in ("sim_placement", "placement"):\n', '    for field in ("sim_placement",):\n'),
    # ---------------- (2026-09-29): the registered rules ----------------
    ("N01", "rule 1: the sign bug restored (a small reversal falls through to the size ratio)", "analyze.py",
     '    if not same_sign:\n        return "ANTI" if abs(_pts(model_eff)) > RC.ANTI_MIN_PP else "LOW"\n',
     '    if (not same_sign) and abs(model_eff) > MIN_MODEL_EFFECT:\n        return "ANTI"\n'),
    ("N02", "rule 2: the OVER class removed (overshoot is HIGH again)", "analyze.py",
     "    if ratio > OVER_RATIO:\n", "    if False:\n"),
    ("N03", "rule 2: OVER starts at 150 percent instead of above it", "analyze.py",
     "    if ratio > OVER_RATIO:\n", "    if ratio >= OVER_RATIO:\n"),
    ("N04", "rule 2: the published-tier OVER reading not recorded", "analyze.py",
     '            if passed and tier_class.get((st, 1)) == "OVER":\n', "            if False:\n"),
    ("N05", "rule 3: the overall class taken from the per-tier cells", "analyze.py",
     "        overall = overall_class(eff_cls, criterion)\n",
     '        overall = majority_class([c["class"] for c in scored_cells if c["structure"] in REGULARITY_EFFECTS])\n'),
    ("N06", "rule 3: the model's pooled effect weighted by its own calls, not the human weights", "analyze.py",
     '    m = model_contrast(recs, effect, tuple(tiers), fmt, mode, design, drop, "backbone", cats, weights=w, boot=boot)\n',
     '    m = model_contrast(recs, effect, tuple(tiers), fmt, mode, design, drop, "backbone", cats, weights=None, boot=boot)\n'),
    ("N07", "rule 4: the fold removed (an overshoot counts as fidelity again)", "analyze.py",
     "    if x > FOLD_AT:\n", "    if False:\n"),
    ("N08", "rule 5: the bootstrap resamples calls across grid points", "call_bootstrap.py",
     '            g = groups["cell"] if cell else groups[self.grid.get(rid, ("record", rid))]\n',
     '            g = groups["all"]\n'),
    ("N09", "rule 5: the bootstrap seed not fixed", "call_bootstrap.py",
     "            rng = random.Random(stable_seed(self.seed, self.model_key, arm_key))\n",
     "            rng = random.Random()\n"),
    ("N10", "rule 6: prompt sensitivity never flagged", "analyze.py",
     "    return deltas, len(signs) > 1\n", "    return deltas, False\n"),
    ("N11", "rule 7: a small human format effect no longer blocks the T4 reading", "analyze.py",
     '                    t4_undefined[fmt] = f"human {st} effect {he * 100:.2f} points"\n',
     "                    pass\n"),
    ("N12", "rule 8: the decoy-target covariate dropped from the memorization regression", "analyze.py",
     "    use = [j for j in (1, 2) if _varies(j)]", "    use = [j for j in (1,) if _varies(j)]"),
    ("N13", "rule 9: a failed positive control changes nothing", "analyze.py",
     '    failed_controls = pc["failed"]\n', "    failed_controls = []\n"),
    ("N14", "rule 9: the frequency-decoy control tested on every cell, not the premium-target cells", "analyze.py",
     '                       "backbone", None, target_kind="HD")\n', '                       "backbone", None, target_kind=None)\n'),
    ("N15", "rule 10: the top-up rule ignores significance", "analyze.py",
     "    fired = bool(abs(d) * 100 > RC.SIM_TOPUP_MAX_GAP_PP and p < RC.SIM_TOPUP_ALPHA)\n",
     "    fired = bool(abs(d) * 100 > RC.SIM_TOPUP_MAX_GAP_PP)\n"),
    ("N16", "rule 10: the top-up rule ignores the 5-point gap", "analyze.py",
     "    fired = bool(abs(d) * 100 > RC.SIM_TOPUP_MAX_GAP_PP and p < RC.SIM_TOPUP_ALPHA)\n",
     "    fired = bool(p < RC.SIM_TOPUP_ALPHA)\n"),
    ("N17", "rule 10: the similarity benchmark not switched when the top-up check fires", "analyze.py",
     '    if topup["fired"]:\n', "    if False:\n"),
    ("N18", "rule 11 (F3): the published deviation pairs read from the hard-limit flag", "analyze.py",
     "                        if t_share is not None and not (RC.HARD_LIMIT_LO_PCT <= t_share <= RC.HARD_LIMIT_HI_PCT):\n",
     '                        if any(f.startswith("CALIBRATION_HARD_LIMIT_FLAG") for f in r.get("flags", [])):\n'),
    ("N19", "rule 11: the calibration rule applied to the calibration label, not the premium option", "analyze.py",
     '                    if bin_focal.get(cat) != "HD" and t_share is not None:\n',
     '                    if False and t_share is not None:\n'),
    ("N20", "rule 12 (F4): the re-run rule back to 3 points around the re-run's centre", "analyze.py",
     "    return rerun_lo_pp <= deposited_pp <= rerun_hi_pp\n",
     "    return abs(deposited_pp - (rerun_lo_pp + rerun_hi_pp) / 2.0) <= 3.0\n"),
    ("N21", "the knows-it-versus-shows-it test reads the tier-1 cell again, not the pooled effect", "analyze.py",
     '        behavior_by_struct = {st: pooled_m[st] for st in EFFECTS if st != "PHT" and st in pooled_m}\n',
     '        behavior_by_struct = {st: next((c["model_pp"] / 100.0 for c in scored_cells if c["structure"] == st and c["tier"] == 1), 0.0) for st in EFFECTS if st != "PHT"}\n'),
    # ---------------- the authors' tie rule and the independent review (2026-09-29) ----------------
    ("N22", "tie rule: ties back to alphabetical order (the required mutant)", "analyze.py",
     "    return next(c for c in CLASS_ORDER if c in real and real.count(c) == top)\n",
     "    return max(sorted(set(real)), key=real.count)\n"),
    ("N23", "review 1: T4 'falls' fires on a pictures overshoot", "analyze.py",
     '    guard = _undershoots(raw, "pictures")\n', "    guard = True\n"),
    ("N24", "review 1: T1 'steep' fires on an invented-tier overshoot", "analyze.py",
     "    guard = _undershoots(raw, hi)\n", "    guard = True\n"),
    ("N25", "review 1: T3 'reversed' fires on an attraction and compromise overshoot", "analyze.py",
     "    top_under = raw is None or all(_undershoots(raw, s) for s in LADDER_TOP if fidelity_by_struct.get(s) is not None)\n"
     "    mid_under = raw is None or mid is None or _undershoots(raw, LADDER_MIDDLE)\n",
     "    top_under = True\n    mid_under = True\n"),
    ("N26", "review 3: the shared control resampled once per coding (the two similarity placements)", "analyze.py",
     '    ca = boot.arm(("C", ctrl, (cat, tier, f), mode, coding), base)\n    return boot.flipped(ca) if flip else ca\n',
     '    ca = boot.arm(("C", ctrl, tgt, (cat, tier, f), mode), c)\n    return ca\n'),
    ("N27", "review 12: the 3-point reversal compared unrounded", "analyze.py",
     '        return "ANTI" if abs(_pts(model_eff)) > RC.ANTI_MIN_PP else "LOW"\n',
     '        return "ANTI" if abs(model_eff) * 100 > RC.ANTI_MIN_PP else "LOW"\n'),
    ("N28", "review 10: every neutral arm pooled into the confirmatory estimate", "analyze.py",
     "        recs, recs_reason, n_other_arms = split_arms(recs)\n", "        recs_reason, n_other_arms = [], 0\n"),
    ("N29", "review 8: a failed frequency-decoy control leaves the persona and sequential readings unmarked", "analyze.py",
     '            if "FRQ" in failed_controls:\n', "            if False:\n"),
    ("N30", "review 11 (X01): the class's human side taken from the criterion's pooled estimate", "analyze.py",
     "            pooled[st] = (meff * 100, he * 100)\n",
     '            he = pooled_h[st]["delta"]; pooled[st] = (meff * 100, he * 100)\n'),
    ("N31", "review 11 (X04): no-room slices kept in the pooled class", "analyze.py",
     "            m, he, h = matched(recs, boot, st, (1, 2, 3), extra=nr)\n",
     "            m, he, h = matched(recs, boot, st, (1, 2, 3))\n"),
    ("N32", "review 11 (X03): top-up rows kept in the first-trial check after the top-up check fires", "analyze.py",
     '        ft_input = [r for r in ft_input if not (r["structure"] == "SIM" and r["participant_id"] in tpids)]\n',
     "        pass\n"),
    # ---------------- the registered rules ----------------
    ("N33", "rule 2 (F3): published pairs by the interval crossing 75, not the point share", "analyze.py",
     "                        if t_share is not None and not (RC.HARD_LIMIT_LO_PCT <= t_share <= RC.HARD_LIMIT_HI_PCT):\n",
     "                        if t_ci is not None and t_ci[1] > RC.HARD_LIMIT_HI_PCT:\n"),
    ("N34", "rule 2 (F3): the refusal when the computed set differs from the registered seven removed",
     "analyze.py", "        if deviation != registered:\n", "        if False:\n"),
    ("N35", "rule 3 (F4): the re-run interval's ends counted as outside", "analyze.py",
     "    return rerun_lo_pp <= deposited_pp <= rerun_hi_pp\n", "    return rerun_lo_pp < deposited_pp < rerun_hi_pp\n"),
    ("N36", "rule 4 (F10): the failed-phantom retrieval reading removed", "analyze.py",
     '            if st == "PHT" and not passed and _pts(meff) > RC.ANTI_MIN_PP:\n', "            if False:\n"),
    ("N37", "rule 4 (F10): the failed-phantom reading made two-sided", "analyze.py",
     '            if st == "PHT" and not passed and _pts(meff) > RC.ANTI_MIN_PP:\n',
     '            if st == "PHT" and not passed and abs(_pts(meff)) > RC.ANTI_MIN_PP:\n'),
    ("N38", "rule 4 (F10): the failed-phantom reading at 3 points inclusive", "analyze.py",
     '            if st == "PHT" and not passed and _pts(meff) > RC.ANTI_MIN_PP:\n',
     '            if st == "PHT" and not passed and _pts(meff) >= RC.ANTI_MIN_PP:\n'),
    ("N39", "rule 5 (F7): effects below the first-trial floor classed as confirmatory", "analyze.py",
     '    floor_effects = {st for st in EFFECTS if criterion[st]["replicated"] and not criterion[st]["confirmatory"]}\n',
     "    floor_effects = set()\n"),
    ("N40", "rule 5 (F7): floor effects keep a registered knows-it-versus-shows-it reading", "analyze.py",
     "                                                  descriptive=floor_effects, recog_ci=recog_ci,\n",
     "                                                  descriptive=(), recog_ci=recog_ci,\n"),
    ("N41", "rule 1: T1 steep without its interval", "analyze.py",
     "    p_steep = _tfu(have and drop > RC.T1_STEEP_DROP and guard and dlo > flat_w,\n",
     "    p_steep = _tfu(have and drop > RC.T1_STEEP_DROP and guard,\n"),
    ("N42", "rule 1: T1 flat without its interval", "analyze.py",
     "    p_flat = _tfu(have and abs(slope) < RC.T1_FLAT_SLOPE and dhi < RC.T1_STEEP_DROP,\n",
     "    p_flat = _tfu(have and abs(slope) < RC.T1_FLAT_SLOPE,\n"),
    ("N43", "rule 1: T3 declines without its interval", "analyze.py",
     "    p_declines = _tfu(have and d > step and guard_dec and lo > flat,\n",
     "    p_declines = _tfu(have and d > step and guard_dec,\n"),
    ("N44", "rule 1: T3 flat without its interval", "analyze.py",
     "    p_flat = _tfu(have and abs(d) < flat and -step < lo and hi < step, have and (lo >= flat or hi <= -flat))\n",
     "    p_flat = _tfu(have and abs(d) < flat, have and (lo >= flat or hi <= -flat))\n"),
    ("N45", "rule 1: T3 reversed without the middle rung's interval", "analyze.py",
     "    rev_int = have and -hi > flat and (mid is None or (mid_have and bmm[0] > flat))\n",
     "    rev_int = have and -hi > flat\n"),
    ("N46", "rule 1: T4 falls without its interval (the earlier comparison rule)", "analyze.py",
     "    p_falls = _tfu(have and d > T4_PRE_ROUND5_DROP and guard and lo > T4_PRE_ROUND5_FLAT,\n",
     "    p_falls = _tfu(have and d > T4_PRE_ROUND5_DROP and guard,\n"),
    ("N47", "rule 1: T4 flat without its interval (the earlier comparison rule)", "analyze.py",
     "    p_flat = _tfu(have and abs(d) < T4_PRE_ROUND5_FLAT and hi < T4_PRE_ROUND5_DROP,\n",
     "    p_flat = _tfu(have and abs(d) < T4_PRE_ROUND5_FLAT,\n"),
    ("N48", "rule 1: T5 rising without its interval", "analyze.py",
     "            p_rising = _tfu(have and delta > step and tlo > step, have and thi <= step)\n",
     "            p_rising = _tfu(have and delta > step, have and thi <= step)\n"),
    ("N49", "rule 1: T5 flat without its interval", "analyze.py",
     "            p_flat = _tfu(have and abs(delta) <= step and tlo >= -step and thi <= step,\n",
     "            p_flat = _tfu(have and abs(delta) <= step,\n"),
    ("N50", "rule 1: the reasoning reading without its interval", "analyze.py",
     "            if rhave and r > rstep and rlo > rstep:\n", "            if rhave and r > rstep:\n"),
    ("N51", "rule 1 (the registered router): an open reading the estimate points to is treated as ruled out",
     "analyze.py", "            if own == \"U\" and (fav or open_blocks == \"any\"):\n", "            if False:\n"),
    ("N52", "rule 1: the human side held at its point (no human resampling)", "analyze.py",
     "        return call_bootstrap.combine(items, NB)\n",
     "        return call_bootstrap.combine([(w, (t[0], None) + tuple(t[2:]), (c[0], None) + tuple(c[2:])) "
     "for w, t, c in items], NB)\n"),
    ("N53", "rule 1: the two generations' replicates not paired (the older model's order reversed)", "analyze.py",
     '                                                 model_results[gens["old"]]["fid_primary_reps"]))\n',
     '                                                 model_results[gens["old"]]["fid_primary_reps"][::-1]))\n'),
    ("N54", "rule 1: undefined replicates dropped from the interval", "call_bootstrap.py",
     "    k = len(reps) - len(vals)\n", "    k = 0\n"),
    ("N55", "rule 1: an undefined group replicate replaced by a number", "analyze.py",
     "    return [(_fold(a / d) if d > 0 else None) for a, d in zip(num, den)]\n",
     "    return [(_fold(a / d) if d != 0 else 0.0) for a, d in zip(num, den)]\n"),
    ("N56", "rule 1: the group denominator uses each resampled human effect's size, not its projection",
     "analyze.py", "        den = [a + s * x for a, x in zip(den, hr)]\n", "        den = [a + abs(x) for a, x in zip(den, hr)]\n"),
    ("N57", "rule 1: the synthetic exact prompts no longer deterministic (option blocks interleaved)", "synth.py",
     "        it = iter(sorted(got[key]))\n", "        it = iter(sorted(got[key])[::2] + sorted(got[key])[1::2])\n"),
    ("N58", "rule 1: the synthetic exact labels dealt to the paraphrases unsorted (shares drift)", "synth.py",
     "    for lab in sorted(_exact_labels(struct, len(grid), p_t)):\n",
     "    for lab in _exact_labels(struct, len(grid), p_t):\n"),
    ("N59", "rule 1: an arm key reused for other rows accepted", "call_bootstrap.py",
     "            if self._sigs.get(arm_key) != sig:\n", "            if False:\n"),
    # ---------------- after the earlier independent review ----------------
    ("N60", "R2 review note b: a point past the cutoff fires although its whole interval sits on the other side",
     "analyze.py", '    if true and false:\n        return "U"\n', '    if False:\n        return "U"\n'),
    ("N61", "R2 review 1: every reading ruled out is reported as resolved again", "analyze.py",
     '        reading = _ruled_out_all(point, "the drop", drop_ci)\n',
     '        reading = "non-monotone or shallow: reported descriptively, no causal reading"\n'),
    ("N62", "R2 review 5: the in-limit memorization re-reading without the undershoot guard", "analyze.py",
     "    t1_r = test_T1_memorization(cells_by_tier, raw_by_tier, drop_ci=drop_ci, resolve=resolve)\n",
     "    t1_r = test_T1_memorization(cells_by_tier, drop_ci=drop_ci, resolve=resolve)\n"),
    ("N63", "R2 review 5: the adjusted memorization re-reading without the undershoot guard", "analyze.py",
     "    last_under = _undershoots(raw_by_tier, present[-1]) if present else True\n", "    last_under = True\n"),
    ("N64", "R2 review 3: a participant with two choices in one cell resampled as two participants",
     "call_bootstrap.py", "        if cell and len({rid for rid, _ in rows}) != len(rows):\n", "        if False:\n"),
    ("N65", "R2 review note c: the arm fingerprint reduced to the row count", "call_bootstrap.py",
     "        sig = (len(rows), sum(y for _, y in rows), hash(tuple(rid for rid, _ in rows)))\n",
     "        sig = (len(rows),)\n"),
    # ---------------- the registered rules (a) and (b) ----------------
    ("N66", "R3 (a): S1 needs a resolved flat memorization reading again", "analyze.py",
     # re-aimed 2026-10-17 at the S1 line that now also refuses recognizes-and-shows (it spans two lines)
     '        ("S1", "", dom == "HIGH" and not t2_override and not t2_known_shown and s_steep != "T" and s_decl != "T"\n',
     '        ("S1", "", dom == "HIGH" and not t2_override and not t2_known_shown and t1.get("p_flat") == "T" and s_decl != "T"\n'),
    ("N67", "R3 (a): an open reading blocks S1", "analyze.py",
     '        if scen == "S1":\n', '        if scen == "S1" and not blocked:\n'),
    ("N68", "R3 (a) with R5: S1 claimed despite a resolved ladder decline", "analyze.py",
     'and not t2_known_shown and s_steep != "T" and s_decl != "T"\n',      # re-aimed 2026-10-17
     'and not t2_known_shown and s_steep != "T"\n'),
    ("N69", "R4 (item 4): the ruled qualifier dropped", "analyze.py",
     "            if open_tests:\n                lbl += \"; qualifier: \" + S1_QUALIFIER",
     "            if False:\n                lbl += \"; qualifier: \" + S1_QUALIFIER"),
    ("N70", "R3 (a): S1 claimed after a failed positive control", "analyze.py",
     "         and not (_uninf(t1) or _uninf(t3)),\n", "         and True,\n"),
    ("N71", "R3 (b): an account route taken on an open reading", "analyze.py",
     '            if own == "T":\n', '            if own in ("T", "U"):\n'),
    ("N72", "R3 (b), after the review: an open reading blocks only when its estimate points to the route",
     "analyze.py", '            if own == "U" and (fav or open_blocks == "any"):\n', '            if own == "U" and fav:\n'),
    ("N78", "R3 review 4: the reversed ladder with recognition ignores an open steep reading", "analyze.py",
     '         (s_rev if s_steep == "F" else ("U" if s_rev != "F" else "F")), f_rev),\n',
     '         s_rev, f_rev),\n'),
    ("N79", "R3 review 5: a block that leaves one scenario reported as not resolved", "analyze.py",
     "    if len(possible) == 1:\n", "    if False:\n"),
    ("N80", "R3 review 6: the recognition intervals not passed to the knows-it reading", "analyze.py",
     "                    recog_ci[st] = (call_bootstrap.interval(a[1], RC.BOOTSTRAP_LEVEL) if a[1] is not None\n",
     "                    _unused = (call_bootstrap.interval(a[1], RC.BOOTSTRAP_LEVEL) if a[1] is not None\n"),
    ("N81", "R3 review 6: the pooled-effect intervals not passed to the shows-it reading", "analyze.py",
     "                                                  behavior_ci=behavior_ci)\n",
     "                                                  behavior_ci={})\n"),
    ("N77", "R4: the adopted S1 point guard never applied", "analyze.py",
     "            if s1_point_guard and ((s_steep == \"U\" and f_steep) or (s_rev == \"U\" and f_rev)\n",
     "            if False and ((s_steep == \"U\" and f_steep) or (s_rev == \"U\" and f_rev)\n"),
    # ---------------- the confirmations and the adopted guard ----------------
    ("N82", "R4: the S1 point guard off by default again", "analyze.py",
     "                   s1_point_guard=True, t2_known_shown=False):\n",          # re-aimed 2026-10-17
     "                   s1_point_guard=False, t2_known_shown=False):\n"),
    ("N83", "R4 with R5: the guard ignores an open ladder decline", "analyze.py",
     "                                   or (s_decl == \"U\" and f_decl) or (s_rise == \"U\" and f_rise)):\n",
     "                                   or (s_rise == \"U\" and f_rise)):\n"),
    ("N86", "R4 review, finding 1: the guard drops S1 from the possible scenarios", "analyze.py",
     "                return _blocked(blocked + ([\"S3\"] if s3_open else []), \"S1\")\n",
     "                return _blocked(blocked + ([\"S3\"] if s3_open else []), \"COMPOSITE\")\n"),
    ("N87", "R4 review, finding 1: the guard leaves an open fall's account out of the possible scenarios",
     "analyze.py",
     "                return _blocked(blocked + ([\"S3\"] if s3_open else []), \"S1\")\n",
     "                return _blocked(blocked + ([] if s3_open else []), \"S1\")\n"),
    ("N88", "R4 confirm round: an open decline with a flat estimate left out of the possible scenarios",
     "analyze.py",
     "                s3_open = s_decl == \"U\" and (f_decl or open_blocks == \"any\")\n",
     "                s3_open = s_decl == \"U\" and f_decl\n"),
    ("N89", "R5: the memorization test pairs the tiers on the union of their categories", "analyze.py",
     "            common = cats12[0] & cats12[1]\n", "            common = cats12[0] | cats12[1]\n"),
    # ---------------- the final rule ----------------
    ("N90", "R5: the memorization test compares the invented tier again", "analyze.py",
     "T1_TIERS = (1, 2)\n", "T1_TIERS = (1, 3)\n"),
    ("N91", "R5: the format test gives readings again", "analyze.py",
     "DESCRIPTIVE_T4 = True\n", "DESCRIPTIVE_T4 = False\n"),
    ("N93", "R5 review: the memorization sensitivity keeps two tier steps", "analyze.py",
     "        drop = -span * b_tier\n", "        drop = -2.0 * b_tier\n"),
    ("N94", "R5 review: the memorization sensitivity compares the tiers on different categories", "analyze.py",
     '    kept = [c for c in kept if c["tier"] not in T1_TIERS or on[(c["structure"], str(c["category"]))] >= tiers_in]\n',
     ""),
    # 2026-10-17, the authors' rule: S1 needs every shown effect shown without recognition (no recognizes-and-shows)
    ("N95", "2026-10-17: S1 no longer refuses a model that recognizes and shows an effect", "analyze.py",
     '        ("S1", "", dom == "HIGH" and not t2_override and not t2_known_shown and s_steep != "T" and s_decl != "T"\n',
     '        ("S1", "", dom == "HIGH" and not t2_override and s_steep != "T" and s_decl != "T"\n'),
    ("N96", "2026-10-17: the legacy router ignores recognizes-and-shows for S1", "analyze.py",
     "    if (dom == \"HIGH\" and not t1_steep and not t2_override and not t2_known_shown and not t3_declines\n",
     "    if (dom == \"HIGH\" and not t1_steep and not t2_override and not t3_declines\n"),
    # 2026-10-17, editor audit: the per-effect readings, the phantom reading and the trajectory readings follow the paper
    ("N97", "2026-10-17: a recognized and shown HIGH effect read as deep mimicry again", "analyze.py",
     '        elif cls == "HIGH" and rec >= RC.RECOGNITION_CUTOFF:\n',
     '        elif cls == "HIGH" and rec > 99:\n'),
    ("N98", "2026-10-17: an ANTI effect without recognition counts toward rational override again", "analyze.py",
     '    "systematic inversion (reversed without recognition; no account attributed)": "systematic inversion",\n',
     '    "systematic inversion (reversed without recognition; no account attributed)": "rational override",\n'),
    ("N99", "2026-10-17: the phantom equivalence read even when the phantom meets the criterion", "analyze.py",
     '    if replicated:\n        return "present: meets the replication criterion (equivalence not read)"\n',
     ''),
    ("N101", "2026-10-18: S1 claimed for a HIGH model that reverses one effect", "analyze.py",
     '         and s_rev != "T" and not reversed_low_effects\n',
     '         and s_rev != "T"\n'),
    ("N100", "2026-10-17: a fall across generations prints a scenario again", "analyze.py",
     '            point = "newer less faithful -> fidelity is lower in the newer generation; no scenario assigned"\n',
     '            point = "newer less faithful -> fidelity is not a free byproduct of capability"\n'),
    ("N92", "R5: reason construction read from the format test again", "analyze.py",
     '    s_decl = state(t3, "p_declines", "reading", "declines")\n',
     '    s_decl = state(t4, "p_falls", "reading", "falls")\n'),
    ("N84", "R4 (item 4): the open pattern tests not listed", "analyze.py",
     "                open_pattern_tests=(branch.split(\"(open: \", 1)[1]",
     "                open_pattern_tests=(\"\"[0:0] and branch.split(\"(open: \", 1)[1]"),
    ("N85", "R4 study switch: keep_members stores the invented tier as the new-values tier", "analyze.py",
     '                kept["tier"][tier] = mem\n', '                kept["tier"][min(tier, 2)] = mem\n'),
    ("N73", "R3 (b): rational override read at the point, not resolved", "analyze.py",
     '    s_kws = t2_state if t2_state is not None else ("T" if t2_override else "F")\n',
     '    s_kws = "T" if t2_override else "F"\n'),
    ("N74", "R3 (b): 'knows' resolved without its interval's lower end", "analyze.py",
     "        k_state = (_tfu(knows and rci[0] >= RC.RECOGNITION_CUTOFF,",
     "        k_state = (_tfu(knows and rci[0] >= -1.0,"),
    ("N75", "R3 (b): 'does not show' resolved without its interval's upper end", "analyze.py",
     "(not shows) and _pts(bci[1]) <= RC.ANTI_MIN_PP)", "(not shows))"),
    ("N76", "R3 (b): a resolved steep reading no longer excludes the reversed ladder", "analyze.py",
     '         rev_attr == ARGUMENT_OVERRIDE and s_steep != "T", True,\n',
     '         rev_attr == ARGUMENT_OVERRIDE, True,\n'),
]


def prepare(folder, fname=None, old=None, new=None):
    os.makedirs(folder, exist_ok=True)
    for f in FILES:
        shutil.copy(os.path.join(HERE, f), os.path.join(folder, f))
    tpath = os.path.join(folder, "test_analysis.py")
    src = open(tpath, encoding="utf-8").read()
    real_power = os.path.abspath(os.path.join(HERE, "..", "power")).replace("\\", "/")
    anchor = 'POWER_DIR = os.path.abspath(os.path.join(HERE, "..", "power"))'
    assert src.count(anchor) == 1
    open(tpath, "w", encoding="utf-8", newline="\n").write(src.replace(anchor, f'POWER_DIR = r"{real_power}"'))
    if fname is None:
        return
    target = os.path.join(folder, fname)
    code = open(target, encoding="utf-8").read()
    n = code.count(old)
    if n != 1:
        raise SystemExit(f"mutation anchor found {n} times in {fname}; refusing: {old!r}")
    open(target, "w", encoding="utf-8", newline="\n").write(code.replace(old, new))
    py_compile.compile(target, doraise=True)


def run_layers(folder, env):
    p = subprocess.run([sys.executable, "test_analysis.py", "--quick", "--no-write"], cwd=folder,
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        failed = [ln.split("|")[1].strip() for ln in p.stdout.splitlines() if "| FAIL |" in ln]
        return "KILLED", "tests: " + (", ".join(failed) or (p.stderr.strip().splitlines() or ["crash"])[-1][:120])
    r = subprocess.run([sys.executable, "analyze.py"], cwd=folder, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        failed = [ln.split("|")[1].strip()[:70] for ln in r.stdout.splitlines() if "| FAIL |" in ln]
        return "KILLED", "rehearsal: " + ("; ".join(failed) or (r.stderr.strip().splitlines() or ["crash"])[-1][:120])
    return "SURVIVED", "no test and no rehearsal check failed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    rows = []
    t0 = time.time()
    sys.path.insert(0, HERE)
    import analyze
    if not analyze.STIMULI_PATH:
        raise SystemExit("stimuli.json not found; the design-index tests need it")
    # the scratch copies cannot find stimuli.json by walking up, so point them at it explicitly.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", CONTEXT_FX_STIMULI=analyze.STIMULI_PATH)
    base = os.path.join(SCRATCH, "BASELINE")
    prepare(base)
    status, detail = run_layers(base, env)
    if status != "SURVIVED":
        raise SystemExit(f"the UNMUTATED code does not pass both layers ({detail}); a mutation battery on a "
                         "failing baseline proves nothing, refusing")
    print("baseline passes both layers", flush=True)
    for mid, label, fname, old, new in MUTANTS:
        if only and mid not in only:
            continue
        folder = os.path.join(SCRATCH, mid)
        prepare(folder, fname, old, new)
        status, detail = run_layers(folder, env)
        rows.append((mid, label, status, detail))
        print(rows[-1], flush=True)
    killed = sum(1 for r in rows if r[2] == "KILLED")
    lines = ["# Mutation check on the repaired critical paths", "",
             f"(Generated by mutate_checks.py, {datetime.date.today().isoformat()}. {killed} of {len(rows)} mutants "
             f"killed. Runtime {round(time.time() - t0)}s. The live code was never edited; each mutant ran in its "
             "own scratch copy (kept, never deleted), the anchor had to land exactly once, and the unmutated copy "
             "passed both layers first.)", "",
             "| mutant | what was broken | result | killed by |", "|---|---|---|---|"]
    for mid, label, res, det in rows:
        lines.append(f"| {mid} | {label} | {res} | {det} |")
    text = "\n".join(lines) + "\n"
    # a partial re-run (--only) banks its own file beside the full report, never over it
    out = "MUTATION_REPORT.md" if not only else "MUTATION_REPORT_RERUN.md"
    open(os.path.join(HERE, out), "w", encoding="utf-8", newline="\n").write(text)
    print(text)
    sys.exit(0 if killed == len(rows) else 1)


if __name__ == "__main__":
    main()
