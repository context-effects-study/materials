"""test_analysis.py: tests of the registered analysis, one per rule it applies.

Each test builds a small data set in which one rule decides the outcome (for example the direction
requirement of the human criterion, the Holm families, the fidelity classes and their tie rule, the
first-choice check, the phantom reading, the positive control, the interval rule of the pattern tests and the
re-run rule) and checks that analyze.py applies the rule exactly as the Analysis Plan states it. Test
outputs go to a fixed scratch folder under the system's temporary folder, which is reused on every run.
Plain Python; pytest also collects the test_* functions.

Run: python analysis/test_analysis.py --no-write      (exit 0 when every test passes; about half a minute)
     python analysis/test_analysis.py --quick         (the faster subset)
"""
import json, math, os, random, shutil, sys, tempfile, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth      # noqa: E402
import statlib    # noqa: E402
import analyze    # noqa: E402

QUICK = "--quick" in sys.argv
POWER_DIR = os.path.abspath(os.path.join(HERE, "..", "power"))


def _design_synth():
    return analyze.Design.for_synth()


def _scratch(name):
    """A FIXED scratch folder for test outputs, reused and overwritten on every run and never deleted
    (the authors' standing rule of 2026-09-29: no delete operation of any kind, temporary folders included)."""
    p = os.path.join(tempfile.gettempdir(), "context_effects_release_scratch", name)
    os.makedirs(os.path.join(p, "tests"), exist_ok=True)
    os.makedirs(os.path.join(p, "figures"), exist_ok=True)
    return p


# ------------------------------------------------------------------------------------------------
# Defect 1: direction and the registered Bayes factor
# ------------------------------------------------------------------------------------------------
def test_reversed_human_effect_is_not_replicated():
    """A significantly REVERSED human effect must not count as replicated (old code: it did)."""
    H = synth.gen_human(700, random.Random(11), icc=0.10, effect_overrides={"RNG": -0.05})
    criterion = analyze.human_gate(H)[0]
    g = criterion["RNG"]
    assert g["holm_reject"], "the planted reversal should be significant"
    assert g["delta_pp"] < 0, "the planted reversal should be negative"
    assert g["replicated"] is False, f"a reversed effect was scored replicated (delta {g['delta_pp']:.2f}pp)"


def test_direction_requirement_holds_even_with_a_two_sided_bayes_factor():
    """The direction requirement is its own check: even if the Bayes factor were non-directional, a
    significantly reversed effect must not replicate."""
    H = synth.gen_human(700, random.Random(11), icc=0.10, effect_overrides={"RNG": -0.05})
    saved = statlib.bf10_halfnormal

    def two_sided(delta, se, scale):          # a full normal prior: no direction
        s2, p2 = se * se, scale * scale
        return math.exp(-0.5 * math.log(s2 + p2) - 0.5 * delta * delta / (s2 + p2)
                        + 0.5 * math.log(s2) + 0.5 * delta * delta / s2) if se > 0 else 1e12
    try:
        statlib.bf10_halfnormal = two_sided
        criterion = analyze.human_gate(H)[0]
    finally:
        statlib.bf10_halfnormal = saved
    assert criterion["RNG"]["bf10"] > 3.0, "the stand-in Bayes factor should favour an effect here"
    assert criterion["RNG"]["replicated"] is False, "a reversed effect replicated once the Bayes factor lost its direction"


def test_bayes_factor_is_directional_half_normal():
    """The registered BF: reversed estimates give evidence AGAINST a positive effect; the closed form
    matches numerical integration of the half-normal prior."""
    assert hasattr(statlib, "bf10_halfnormal"), "no registered Bayes factor (only the BIC proxy)"
    assert statlib.bf10_halfnormal(-0.05, 0.01, 0.10) < 1.0 / 3.0
    assert statlib.bf10_halfnormal(0.10, 0.01, 0.10) > 3.0
    d, se, sc = 0.03, 0.012, 0.10
    num, n = 0.0, 20000
    for i in range(n):
        t = (i + 0.5) / n
        num += (math.exp(-0.5 * ((d - t) / se) ** 2) / (se * math.sqrt(2 * math.pi)) *
                2 * math.exp(-0.5 * (t / sc) ** 2) / (sc * math.sqrt(2 * math.pi)) / n)
    den = math.exp(-0.5 * (d / se) ** 2) / (se * math.sqrt(2 * math.pi))
    assert abs(num / den - statlib.bf10_halfnormal(d, se, sc)) < 1e-4


# ------------------------------------------------------------------------------------------------
# Defect 2: Holm families
# ------------------------------------------------------------------------------------------------
def test_similarity_is_outside_the_regularity_holm_family():
    """Holm runs within the six regularity effects; similarity is its own family (old: one family of 7)."""
    over = {st: 0.03 for st in ("FRQ", "RNG", "SOT", "SYM", "MOT", "SIM")}
    H = synth.gen_human(150, random.Random(12), icc=0.10, effect_overrides=over)
    criterion = analyze.human_gate(H)[0]
    six = ["FRQ", "RNG", "PHT", "SOT", "SYM", "MOT"]
    expect = statlib.holm({st: criterion[st]["raw_p"] for st in six}, alpha=0.05)
    for st in six:
        assert abs(criterion[st]["holm_p"] - expect[st][1]) < 1e-12, \
            f"{st}: Holm p {criterion[st]['holm_p']:.5f} is not the six-effect family value {expect[st][1]:.5f}"
    assert abs(criterion["SIM"]["holm_p"] - criterion["SIM"]["raw_p"]) < 1e-12, "similarity was corrected with the others"


# ------------------------------------------------------------------------------------------------
# Defect 3: the first-trial rule
# ------------------------------------------------------------------------------------------------
def test_first_trial_rule_false_alarm_at_or_below_5_percent():
    """Simulated at the planned first-trial cell sizes (power/first_trial_rule_sim.py)."""
    sys.path.insert(0, POWER_DIR)
    import first_trial_rule_sim as sim
    reps = 4000 if QUICK else 20000
    if not hasattr(analyze, "first_trial_decide"):
        # the pre-repair pipeline: the point rule on the tier-1 frequency decoy only.
        analyze.first_trial_decide = lambda per: dict(fired=False, fired_effects=[], per_effect=per)
        _, old = sim.rate(reps, 20260929)
        raise AssertionError(f"no registered first-trial rule; the old point rule's false-alarm rate is {old:.3f}")
    new, old = sim.rate(reps, 20260929)
    assert new <= 0.05, f"simulated false-alarm rate {new:.4f} is above 5 percent"
    assert old > 0.10, "the old rule's documented false-alarm rate did not reproduce"


def test_first_trial_rule_on_rows_null_quiet_break_fires():
    """The row-level path: no divergence -> quiet; a planted first-trial divergence on FRQ -> fires."""
    null = synth.gen_human(700, random.Random(21), icc=0.10, published_n_per_tier=350)
    brk = synth.gen_human(700, random.Random(22), icc=0.10, published_n_per_tier=350, first_trial_break=True)
    assert analyze.first_trial_check(null)["fired"] is False
    b = analyze.first_trial_check(brk)
    assert b["fired"] is True and "FRQ" in b["fired_effects"]


def test_fallback_switches_the_benchmark_end_to_end():
    """When the check fires inside build_pack, the criterion must read the FIRST-TRIAL estimates and apply
    the 8-point confirmatory floor (the old code only set a flag)."""
    brk = synth.gen_human(700, random.Random(22), icc=0.10, published_n_per_tier=350, first_trial_break=True)
    models = {"FAITHFUL": synth.gen_model("FAITHFUL", 60, random.Random(23))}
    tmp = _scratch("fallback_pack")
    saved = (analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR)
    try:
        analyze.PACK = tmp
        analyze.TESTS_DIR = os.path.join(tmp, "tests")
        analyze.FIGS_DIR = os.path.join(tmp, "figures")
        res = analyze.build_pack(brk, models, human_rows_with_formats=brk, human_rows_first_trial=brk,
                                 mode="TEST", design=analyze.Design.null())
    finally:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = saved
    assert res["numbers"]["human.first_trial.fallback_triggered"] is True
    first = analyze.human_contrast([r for r in brk if int(r["trial_position"]) == 1], "FRQ")
    assert abs(res["criterion"]["FRQ"]["delta_pp"] - first["delta"] * 100) < 1e-9, "the criterion did not switch to first trials"
    for st, g in res["criterion"].items():
        assert g["confirmatory"] == (g["replicated"] and g["delta_pp"] >= 8.0), st


def test_simulation_estimator_matches_the_pipeline_estimator():
    """The simulation's count-based estimator equals statlib.stratified_diff on expanded rows."""
    sys.path.insert(0, POWER_DIR)
    import first_trial_rule_sim as sim
    parts = [(20, 50, 18, 50), (41, 100, 45, 100), (160, 350, 150, 350)]
    d, se = sim._stratified(parts)
    strata = []
    pid = 0
    for kt, nt, kc, nc in parts:
        t = [(f"t{pid + i}", 1 if i < kt else 0) for i in range(nt)]
        pid += nt
        c = [(f"c{pid + i}", 1 if i < kc else 0) for i in range(nc)]
        pid += nc
        strata.append((t, c))
    d2, se2, _, _, _ = statlib.stratified_diff(strata)
    assert abs(d - d2) < 1e-12 and abs(se - se2) < 1e-12


# ------------------------------------------------------------------------------------------------
# Defect 4: the phantom equivalence test
# ------------------------------------------------------------------------------------------------
def test_phantom_equivalence_needs_the_interval_inside_the_band():
    """Point estimate inside +/-4 but 90% interval crossing +4 -> NOT equivalent (old: point check)."""
    if not hasattr(analyze, "phantom_equivalence"):
        old = statlib.within_phantom_band(3.0, 4.0)
        raise AssertionError(f"no equivalence test; the old point check returns within_band={old} for 3pp +/- 1pp")
    r = analyze.phantom_equivalence(0.03, 0.01)
    assert r["equivalent"] is False, "an interval crossing the bound was judged equivalent"
    assert analyze.phantom_equivalence(0.005, 0.005)["equivalent"] is True
    assert analyze.phantom_equivalence(-0.03, 0.01)["equivalent"] is False


# ------------------------------------------------------------------------------------------------
# Defect 5: the format-by-effect interaction
# ------------------------------------------------------------------------------------------------
def test_format_interaction_detects_a_planted_interaction():
    assert hasattr(analyze, "format_interaction_tests"), "no format-by-effect interaction test in the pipeline"
    d = _design_synth()
    planted = synth.gen_human(700, random.Random(31), icc=0.10, with_formats=True,
                              format_attenuation={"pictures": 0.0})
    t = analyze.format_interaction_tests(planted, d)
    assert t["FRQ:pictures"]["significant"] and t["FRQ:pictures"]["interaction_pp"] < 0
    null = synth.gen_human(700, random.Random(32), icc=0.10, with_formats=True)
    tn = analyze.format_interaction_tests(null, d)
    assert not any(v["significant"] for v in tn.values()), \
        f"a null format module produced a significant interaction: {[k for k, v in tn.items() if v['significant']]}"


# ------------------------------------------------------------------------------------------------
# Defect 6: the calibration record and the matched control
# ------------------------------------------------------------------------------------------------
def test_compromise_precondition_by_option_identity():
    """The compromise-descriptive set is computed from the measured baseline of the compromise TARGET
    (the HD option), not from the category-level calibration label."""
    d = analyze.Design.from_stimuli()
    cd = d.compromise_descriptive
    for sl in [("electric_kettles", 3, "numbers"), ("earbuds", 2, "numbers"), ("water_bottles", 2, "pictures"),
               ("bluetooth_speakers", 1, "numbers"), ("earbuds", 1, "numbers"), ("restaurants", 1, "numbers"),
               ("televisions", 1, "numbers"), ("water_bottles", 1, "numbers")]:
        assert sl in cd, f"{sl} should be descriptive (compromise target starts ahead)"
    assert ("standing_desks", 3, "numbers") not in cd, "standing desks' compromise target (HD) starts at 33.3 percent"
    assert len(cd) == 8
    # Re-aimed 2026-09-29 after corrected the flags: on the real file the flags must AGREE
    # with the set computed by option identity, and the computation must not follow the flags: with the
    # flags set as they stood before the correction (on the standing desks, missing on the kettles and the
    # five published pairs), the computed set is still the same eight.
    assert d.compromise_flag_mismatch == [], f"flags disagree with the computed set: {d.compromise_flag_mismatch}"
    S = json.load(open(analyze.STIMULI_PATH, encoding="utf-8"))
    for r in S["stimuli"]:
        if r["structure"] == "SOT":
            r["flags"] = [f for f in r.get("flags", []) if not f.startswith("COMPROMISE_PRECONDITION_VIOLATED")]
            if r["id"] in ("SOT_standing_desks_t3", "SOT_earbuds_t2"):
                r["flags"].append("COMPROMISE_PRECONDITION_VIOLATED (the pre-correction flag)")
    p = os.path.join(_scratch("stimuli_variants"), "stimuli_old_compromise_flags.json")
    json.dump(S, open(p, "w", encoding="utf-8"))
    d_old = analyze.Design.from_stimuli(p)
    assert d_old.compromise_descriptive == cd, sorted(d_old.compromise_descriptive ^ cd)
    assert d_old.compromise_flag_mismatch, "a mis-set flag was not reported"


def test_compromise_descriptive_slices_leave_the_confirmatory_contrast():
    """A slice in the descriptive set does not enter the pooled compromise contrast."""
    d = _design_synth()
    H = synth.gen_human(300, random.Random(41), icc=0.0)
    drop = {"SOT": d.compromise_descriptive}
    full = analyze.human_contrast(H, "SOT", (1, 2, 3), "numbers", d)
    kept = analyze.human_contrast(H, "SOT", (1, 2, 3), "numbers", d, drop["SOT"])
    assert kept["n_strata"] == full["n_strata"] - len([s for s in d.compromise_descriptive if s[2] == "numbers"])


def _row(pid, cat, struct, tier, chose_target, chose_hd=0, choice="", fmt="numbers", placement="NA",
         chose_ext=0, chose_clone=0, tp=2):
    return dict(participant_id=pid, category=cat, structure=struct, tier=tier, format=fmt,
                trial_position=tp, chose_target=chose_target, chose_hd=chose_hd, choice=choice,
                sim_placement=placement, chose_ext=chose_ext, chose_clone=chose_clone)


def test_matched_control_is_coded_against_the_effects_target():
    """Bluetooth speakers, tier 2: the frequency decoy targets the budget (HF) option while the binary
    rows' TARGET label means the premium (HD) option. 60 percent of binary choosers take HD, so the
    control share of the effect's target is 40 percent; 50 percent pick the target with the decoy:
    the effect is +10 points (old code: 50 - 60 = -10)."""
    d = analyze.Design.from_stimuli()
    rows = []
    for i in range(100):
        hd = 1 if i < 60 else 0
        rows.append(_row(f"b{i}", "bluetooth_speakers", "BIN", 2, chose_target=hd, chose_hd=hd))
        rows.append(_row(f"f{i}", "bluetooth_speakers", "FRQ", 2, chose_target=(1 if i < 50 else 0)))
    c = analyze.human_effect(rows, "FRQ", 2, "numbers", design=d)
    assert abs(c["delta"] - 0.10) < 1e-9, f"effect {c['delta']:.3f}, expected +0.100"


def test_similarity_is_a_relative_share():
    """40 uncloned, 30 rival, 30 clone choosers against a 50/50 binary: relative share 40/70 -> +7.1 points
    (old code: absolute share 0.40 - 0.50 = -10)."""
    rows = []
    for i in range(100):
        rows.append(_row(f"b{i}", 1, "BIN", 1, chose_target=(1 if i < 50 else 0)))
        if i < 40:
            rows.append(_row(f"s{i}", 1, "SIM", 1, 1, choice="TARGET"))
        elif i < 70:
            rows.append(_row(f"s{i}", 1, "SIM", 1, 0, choice="COMP"))
        else:
            rows.append(_row(f"s{i}", 1, "SIM", 1, 0, choice="CLONE", chose_clone=1))
    c = analyze.human_effect(rows, "SIM", 1, "numbers")
    assert abs(c["delta"] - (40 / 70 - 0.5)) < 1e-9, f"effect {c['delta']:.4f}"


def test_compromise_extreme_label_from_ingest_is_excluded():
    """ingest.py writes the new extreme as choice 'EXTREME' with chose_ext = 1; it must leave the
    relative-share denominator (old code only recognized 'EXT')."""
    rows = []
    for i in range(100):
        rows.append(_row(f"b{i}", 1, "BIN", 1, chose_target=(1 if i < 50 else 0)))
        if i < 40:
            rows.append(_row(f"s{i}", 1, "SOT", 1, 1, choice="TARGET"))
        elif i < 70:
            rows.append(_row(f"s{i}", 1, "SOT", 1, 0, choice="COMP"))
        else:
            rows.append(_row(f"s{i}", 1, "SOT", 1, 0, choice="EXTREME", chose_ext=1))
    c = analyze.human_effect(rows, "SOT", 1, "numbers")
    assert abs(c["delta"] - (40 / 70 - 0.5)) < 1e-9, f"effect {c['delta']:.4f}"


def _mrec(i, cat, struct, tier, parsed, placement=None, fmt="numbers"):
    return dict(record_id=f"r{i}", model_key="m", category=cat, structure=struct, tier=tier, format=fmt,
                prompting_mode="neutral", parsed_choice=parsed, exclusion_flag=False, placement=placement)


def test_ceiling_rule_is_per_binary_cell():
    """A model that picks the premium option in every tier-3 binary cell is at ceiling in each cell. The
    BIN TARGET label means the budget option in kettles and desks and the premium option in vacuums, so
    the old pooled share was 1/3 and nothing was flagged."""
    recs, i = [], 0
    for cat, focal in (("electric_kettles", "HF"), ("robot_vacuums", "HD"), ("standing_desks", "HF")):
        for _ in range(100):
            recs.append(_mrec(i, cat, "BIN", 3, "TARGET" if focal == "HD" else "COMP")); i += 1
            recs.append(_mrec(i, cat, "FRQ", 3, "TARGET")); i += 1
    g = analyze.model_gate(recs)
    assert g.get("no_room_slices") == {("electric_kettles", 3, "numbers"), ("robot_vacuums", 3, "numbers"),
                                       ("standing_desks", 3, "numbers")}, g.get("no_room_slices")
    assert ("FRQ", 3, "numbers") in g["no_room_cells"]


def test_model_similarity_reads_the_runners_placement_field():
    """Model records carry the clone placement as `placement` (run.py). Backpacks tier 2, a model that
    takes the premium option 60 percent of the time in the binary cell and shows a +10-point relative-share
    similarity effect in BOTH placements (records decoded against each placement's own uncloned option):
    the pooled effect must be +10 (reading no placement gives 0)."""
    d = analyze.Design.from_stimuli()
    recs, i = [], 0
    for k in range(100):
        recs.append(_mrec(i, "backpacks", "BIN", 2, "TARGET" if k < 60 else "COMP")); i += 1  # focal HD
    for placement, uncloned_share in ((None, 0.70), ("clone_HD", 0.50)):
        for k in range(100):
            recs.append(_mrec(i, "backpacks", "SIM", 2, "TARGET" if k < 100 * uncloned_share else "COMP",
                              placement=placement)); i += 1
    m = analyze.model_contrast(recs, "SIM", (2,), "numbers", "neutral", d)
    assert abs(m["delta"] - 0.10) < 1e-9, f"model similarity effect {m['delta']:.3f}, expected +0.100"


def test_price_free_categories_stay_out_of_the_backbone_gate():
    d = analyze.Design.from_stimuli()
    rows = []
    for i in range(200):
        rows.append(_row(f"b{i}", "hard_drives", "BIN", 2, chose_target=(1 if i < 90 else 0),
                         chose_hd=(1 if i < 90 else 0)))
        rows.append(_row(f"f{i}", "hard_drives", "FRQ", 2, chose_target=(1 if i < 110 else 0)))
        rows.append(_row(f"pb{i}", "hard_drives_pf", "BIN", 2, chose_target=(1 if i < 90 else 0),
                         chose_hd=(1 if i < 90 else 0)))
        rows.append(_row(f"pf{i}", "hard_drives_pf", "FRQ", 2, chose_target=(1 if i < 190 else 0)))
    c = analyze.human_contrast(rows, "FRQ", (2,), "numbers", d)
    assert abs(c["delta"] - 0.10) < 1e-9, f"price-free rows leaked into the backbone contrast ({c['delta']:.3f})"


# ------------------------------------------------------------------------------------------------
# Defect 7: memorization sensitivity
# ------------------------------------------------------------------------------------------------
def test_memorization_sensitivity_adjusts_for_baseline():
    """A pattern that is ENTIRELY baseline-driven (fidelity high wherever the baseline is far from 50,
    which is mostly the published tier) reads as a gradient in the primary test (not flat) and flat once
    the baseline distance is in the regression."""
    d = analyze.Design.for_synth()
    cells = []
    for (cat, tier, fmt), b in d.baseline_pct.items():
        if fmt != "numbers":
            continue
        fid = 0.1 + 0.03 * abs(b - 50.0)          # baseline position alone drives fidelity (at most 1.0)
        for st in ("FRQ", "RNG", "SOT", "SYM", "MOT"):
            cells.append(dict(category=cat, tier=tier, structure=st, human_pp=10.0, model_pp=10.0 * fid, w=350))
    by_tier = {}
    for t in (1, 2, 3):
        sub = [c for c in cells if c["tier"] == t]
        by_tier[t] = sum(c["model_pp"] for c in sub) / sum(c["human_pp"] for c in sub)
    primary = analyze.test_T1_memorization(by_tier)
    s = analyze.test_T1_sensitivity(cells, d, primary)
    assert not primary["reading"].startswith("flat"), primary
    assert s["adjusted_reading"].startswith("flat"), s
    assert abs(s["adjusted_slope"]) < 0.02, s


# ------------------------------------------------------------------------------------------------
# Defect 8: the constants structure
# ------------------------------------------------------------------------------------------------
def test_every_constant_has_a_meaning_and_prints():
    import registered_constants as R
    import print_constants as P
    from dataclasses import fields
    text = P.build()
    for f in fields(R.RegisteredConstants):
        assert f.name in R.MEANING, f"{f.name} has no plain-English meaning"
        assert f"| {f.name} |" in text, f"{f.name} missing from the printed table"
    assert "—" not in text, "em dash in the printed table"


# ------------------------------------------------------------------------------------------------
# Defect 10 and the three added rules
# ------------------------------------------------------------------------------------------------
_GATE_INFO = dict(not_assessable=False)
_FLAT = dict(reading="flat: fidelity is genuine behavior, not retrieval")
_T4 = dict(reading="insufficient formats")
_T5 = dict(trajectory="insufficient generations")


def _r4_cells():
    cells = []
    for st, cls, mp in (("FRQ", "LOW", 0.2), ("RNG", "LOW", 0.2), ("SOT", "ANTI", -10.0),
                        ("SYM", "HIGH", 15.0), ("MOT", "HIGH", 9.0), ("SIM", "HIGH", 5.0)):
        for tier in (1, 2, 3):
            cells.append(dict(structure=st, tier=tier, human_pp=10.0, model_pp=mp, **{"class": cls}))
    return cells


def test_reversed_ladder_routes_by_recognition():
    fid = {"FRQ": 0.02, "RNG": 0.02, "SOT": -1.0, "MOT": 0.95, "SYM": 0.9}
    classes = {"FRQ": "LOW", "RNG": "LOW", "SOT": "ANTI", "SYM": "HIGH", "MOT": "HIGH"}
    t3_hi = analyze.test_T3_ladder(fid, classes, {"FRQ": 0.9, "RNG": 0.85, "SOT": 0.9})
    t3_lo = analyze.test_T3_ladder(fid, classes, {"FRQ": 0.9, "RNG": 0.2, "SOT": 0.9})
    override = getattr(analyze, "ARGUMENT_OVERRIDE", "rational override on arguable sets")
    assert t3_hi["reading"].startswith("reversed ladder") and t3_hi["attribution"] == override
    assert t3_lo["reading"].startswith("reversed ladder") and t3_lo["attribution"] == "no account attributed"
    cells = _r4_cells()
    agree = analyze.agreement(cells)
    r_hi = analyze.route_model("m", cells, _FLAT, False, t3_hi, _T4, _T5, _GATE_INFO, agree, True, False)
    r_lo = analyze.route_model("m", cells, _FLAT, False, t3_lo, _T4, _T5, _GATE_INFO, agree, True, False)
    assert r_hi[1] == "REVERSED_LADDER_OVERRIDE", r_hi
    assert r_lo[1] == "REVERSED_LADDER", r_lo
    # a peaked middle (compromise faithful, extremity faithful, attraction missed) is not a reversal.
    t3_mid = analyze.test_T3_ladder({"FRQ": 0.0, "RNG": 0.0, "SOT": 1.0, "MOT": 0.9}, classes, {})
    assert not t3_mid["reading"].startswith("reversed"), t3_mid
    # the registered decline still reads as a decline.
    assert analyze.test_T3_ladder({"FRQ": 1.0, "RNG": 1.0, "SOT": 0.45, "MOT": 0.2})["reading"].startswith("declines")


def test_effect_without_a_human_counterpart():
    assert analyze.gate_exit_class(0.05) == "no-human-counterpart"
    assert analyze.gate_exit_class(-0.05) == "no-human-counterpart"
    assert analyze.gate_exit_class(0.02) == "excluded(criterion-exit)"


def test_s7_needs_four_of_the_six_non_similarity_effects():
    four = synth.gen_human(700, random.Random(51), icc=0.10, null_effects={"RNG", "SYM", "MOT"})
    three_plus_sim = synth.gen_human(700, random.Random(52), icc=0.10, null_effects={"RNG", "SYM", "SIM"})
    assert analyze.human_gate(four)[4] is True
    g3 = analyze.human_gate(three_plus_sim)
    assert g3[0]["SIM"]["replicated"] is False and g3[4] is False, "similarity counted toward S7"


def test_model_level_account_needs_four_agreeing_effects():
    criterion = {st: dict(replicated=True) for st in analyze.EFFECTS}
    three = {"FRQ": "deep pattern-mimicry", "RNG": "deep pattern-mimicry", "SOT": "deep pattern-mimicry",
             "SYM": "low fidelity", "MOT": "partial (direction transfers, size off)", "PHT": "low fidelity",
             "SIM": "deep pattern-mimicry"}
    assert analyze.model_level_account(three, criterion)[0] == "per-effect only", "similarity counted toward the account"
    four = dict(three, SYM="deep pattern-mimicry")
    assert analyze.model_level_account(four, criterion)[0] == "deep pattern-mimicry"
    gate_fail = dict(criterion, SYM=dict(replicated=False))
    assert analyze.model_level_account(four, gate_fail)[0] == "per-effect only", "a failed effect counted"


# ================================================================================================
# the registered rules
# ================================================================================================
def _exact_model(key, eff, n=120, family=None, bin_share=None, arm=None, id_prefix=None, generation="new",
                 one_call_per_point=False):
    """Contract-B records on the synthetic lattice (numbers only) whose answers carry EXACTLY the share
    BASE + eff(struct, tier, cat) in every cell (the binary control at bin_share(cat, tier) when given),
    three paraphrases cycling, unique ids; arm sets the contract-B arm field; generation the model's
    generation; one_call_per_point gives
    every call its own option order, so no grid point varies under the call bootstrap (a deterministic model)."""
    recs, i = [], 0
    for cat in synth.CATS:
        for tier in ([1, 2] if cat in synth.PUB else [3]):
            for st in synth.STRUCTS:
                b = bin_share(cat, tier) if bin_share else synth.BASE
                p = synth._clip((b if st == "BIN" else synth.BASE) + (0.0 if st in ("BIN", "EXC") else eff(st, tier, cat)))
                for k, lab in enumerate(synth._exact_labels(st, n, p)):
                    rec = dict(record_id=f"{id_prefix or key}{i}", model_key=key, category=cat, structure=st,
                               tier=tier, format="numbers", prompting_mode="neutral", parsed_choice=lab,
                               exclusion_flag=False, stimulus_id=f"s_{cat}_{st}_{tier}",
                               position_order=(f"o{k + 1}" if one_call_per_point else "o1"),
                               paraphrase_id=(k % 3) + 1, family=family or key, generation=generation)
                    if arm is not None:
                        rec["arm"] = arm
                    recs.append(rec)
                    i += 1
    return recs


def _planted(st, tier, cat):
    """The synthetic human truth of one cell (with the premium/budget asymmetry of the attraction decoys)."""
    e = synth.TRUTH[st] * synth.TIER_ATTEN[tier]
    if st in ("FRQ", "RNG", "PHT"):
        dt = synth.cat_decoy_target(cat)
        e *= synth.HD_TARGET_MULT if dt == "HD" else (synth.HF_TARGET_MULT if dt == "HF" else 1.0)
    return e


def _custom_pooled(st, tier, cat):
    """Faithful at tiers 1 and 2 (range at half size) and strongly reversed at tier 3 for the frequency
    decoy, range and compromise; upscaling and extremity faithful everywhere. Per tier the majority class
    is HIGH; on the pooled estimates three of the five non-similarity effects that pass are LOW."""
    if st in ("FRQ", "RNG", "SOT") and tier == 3:
        return -0.35 if st != "RNG" else -0.30
    if st == "RNG":
        return 0.5 * _planted(st, tier, cat)
    return _planted(st, tier, cat)


_PACKS = {}


def _pack(name):
    """Two small shared packs (one build each per process). A: normal human data; models CUSTOM (the
    pooled-class case) and OVERSHOOT_T1. B: the stress data (premium-target frequency decoy null in
    humans, pictures effects null in humans, a top-up survey 15 points apart from the backbone), model
    FAITHFUL with formats."""
    if name in _PACKS:
        return _PACKS[name]
    if name == "A":
        H = synth.gen_human(400, random.Random(71), icc=0.0, sim_topup_participants=300)
        models = {"CUSTOM": _exact_model("CUSTOM", _custom_pooled),
                  "OVERSHOOT_T1": synth.gen_model("OVERSHOOT_T1", 120, random.Random(72), noise="exact"),
                  # twice the human effect on the published tier only: pooled HIGH, published-tier OVER
                  "OVER_T1_ONLY": _exact_model("OVER_T1_ONLY", lambda st, t, c: (2.0 if t == 1 else 1.0) * _planted(st, t, c)),
                  # faithful, but its binary control in category 0, tier 1 sits at 95 percent (no room to move)
                  "NOROOM": _exact_model("NOROOM", lambda st, t, c: (0.30 if (c, t) == (0, 1) else _planted(st, t, c)),
                                         bin_share=lambda c, t: 0.95 if (c, t) == (0, 1) else synth.BASE),
                  # a primary arm at the human size and a reasoning-contrast arm at a quarter of it
                  "REASONING_PAIR": (_exact_model("REASONING_PAIR", _planted, arm="primary", id_prefix="RPp")
                                     + _exact_model("REASONING_PAIR", lambda st, t, c: 0.25 * _planted(st, t, c),
                                                    arm="reasoning_on", id_prefix="RPr")
                                     + _exact_model("REASONING_PAIR", lambda st, t, c: -_planted(st, t, c),
                                                    arm="temp_1", id_prefix="RPt")),
                  # the second revision, rule on F10: the human phantom fails in this data (planted null); a model phantom
                  # of +5 points reads as retrieval, +3 points exactly and -5 points do not
                  "PHANTOM_RECITER": _exact_model("PHANTOM_RECITER", lambda st, t, c: 0.05 if st == "PHT"
                                                  else _planted(st, t, c)),
                  # 100 calls per cell, so the binary control (42 of 100) and the phantom (45 of 100) give a
                  # pooled phantom effect of exactly 3 points
                  "PHANTOM_3PT": _exact_model("PHANTOM_3PT", lambda st, t, c: 0.03 if st == "PHT"
                                              else _planted(st, t, c), n=100),
                  "PHANTOM_REVERSED": _exact_model("PHANTOM_REVERSED", lambda st, t, c: -0.05 if st == "PHT"
                                                   else _planted(st, t, c)),
                  # the second revision, rule 1: an older and a newer twin with identical answers (the joint bootstrap
                  # pairs their human replicates, so their difference is exactly zero on every resample)
                  "TWIN_OLD": _exact_model("TWIN_OLD", _planted, family="famTWIN", generation="old",
                                           one_call_per_point=True),
                  "TWIN_NEW": _exact_model("TWIN_NEW", _planted, family="famTWIN", generation="new",
                                           one_call_per_point=True)}
    else:
        H = synth.gen_human(400, random.Random(73), icc=0.0, with_formats=True, null_on_hd_target={"FRQ"},
                            format_attenuation={"pictures": 0.0}, sim_topup_participants=1000, topup_shift=0.15)
        models = {"FAITHFUL": synth.gen_model("FAITHFUL", 120, random.Random(74), with_formats=True, noise="exact")
                  + synth.gen_persona_seq_arms("FAITHFUL", 60, random.Random(75), noise="exact")}
    tmp = _scratch(f"i2_pack_{name}")
    saved = (analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR)
    try:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = tmp, os.path.join(tmp, "tests"), os.path.join(tmp, "figures")
        res = analyze.build_pack(H, models, human_rows_with_formats=H, human_rows_first_trial=H, mode="TEST",
                                 design=analyze.Design.for_synth())
    finally:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = saved
    _PACKS[name] = (res, H)
    return _PACKS[name]


# ---- rule 1: a small reversal is LOW, never HIGH ------------------------------------------------
def test_i2_small_reversal_is_low_not_high():
    """The planted faults from the recheck: -2.9 against +4 and -2.0 against +2.5 were scored HIGH."""
    assert analyze.classify_cell(-0.029, 0.04) == "LOW"
    assert analyze.classify_cell(-0.020, 0.025) == "LOW"
    assert analyze.classify_cell(-0.035, 0.04) == "ANTI"
    assert analyze.classify_cell(0.0, 0.05) == "LOW"


# ---- rule 2: OVER --------------------------------------------------------------------------------
def test_i2_over_class_and_tie_rule():
    """HIGH is 70 to 150 percent; above 150 percent is OVER. Ties go to the LESS FAITHFUL class: the planted tie of two HIGH and two LOW gives LOW."""
    assert analyze.classify_cell(0.061, 0.04) == "OVER"      # 152.5 percent
    assert analyze.classify_cell(0.060, 0.04) == "HIGH"      # exactly 150 percent
    assert analyze.classify_cell(0.028, 0.04) == "HIGH"      # exactly 70 percent
    assert analyze.classify_cell(0.0279, 0.04) == "PARTIAL"
    assert analyze.majority_class(["HIGH", "HIGH", "LOW", "LOW"]) == "LOW"
    assert analyze.majority_class(["PARTIAL", "OVER"]) == "PARTIAL"
    assert analyze.majority_class(["OVER", "HIGH"]) == "OVER"
    assert analyze.majority_class(["LOW", "ANTI"]) == "ANTI"
    assert analyze.majority_class(["HIGH", "HIGH", "LOW"]) == "HIGH"     # a real majority still wins
    criterion = {st: dict(replicated=True) for st in analyze.EFFECTS}
    assert analyze.overall_class({"FRQ": "HIGH", "RNG": "HIGH", "SOT": "LOW", "SYM": "LOW", "MOT": "PARTIAL",
                                  "PHT": "OVER"}, criterion) == "LOW"
    assert analyze.agreement([dict(human_pp=10, model_pp=9, **{"class": c}) for c in ("HIGH", "LOW")])[
        "dominant_class"] == "LOW"


def test_i2_over_on_the_phantom_reads_as_retrieval():
    criterion = {st: dict(replicated=True) for st in analyze.EFFECTS}
    acc = analyze.attribute_effect_accounts("m", [], {}, criterion, effect_classes={"PHT": "OVER", "FRQ": "OVER"},
                                            pooled={"PHT": (9.0, 3.0), "FRQ": (20.0, 10.0)})
    assert "retrieval of a described regularity" in acc["PHT"], acc["PHT"]
    assert acc["FRQ"].startswith("overshoot"), acc["FRQ"]


def test_i2_over_on_the_published_tier_reads_as_retrieval_end_to_end():
    res, _ = _pack("A")
    rows = [r for r in res["effect_class_rows"] if r["model"] == "OVERSHOOT_T1" and r["human_gate"] == "passed"
            and r["effect"] in analyze.REGULARITY_EFFECTS]
    assert rows and all("OVER on the published tier" in r["over_reading"] for r in rows), \
        [(r["effect"], r["over_reading"]) for r in rows]
    t1 = next(r for r in res["test_T1_rows"] if r["model"] == "OVERSHOOT_T1")
    assert not t1["reading"].startswith("steep"), t1["reading"]


# ---- rule 3: classes on the pooled estimate ------------------------------------------------------
def test_i2_pooled_model_effect_uses_the_human_slice_weights():
    """Slice a has 100 human choices per arm, slice b 300; the model has 300 calls in a (effect +20) and
    100 in b (effect 0). With the human weights the pooled model effect is +5 points; with its own call
    counts it would be +15."""
    rows, recs, i = [], [], 0
    for cat, n_h in (("a", 100), ("b", 300)):
        for j in range(n_h):
            rows.append(_row(f"hb{cat}{j}", cat, "BIN", 1, chose_target=(1 if j < n_h // 2 else 0)))
            rows.append(_row(f"hf{cat}{j}", cat, "FRQ", 1, chose_target=(1 if j < n_h * 0.6 else 0)))
    for cat, n_m, share in (("a", 300, 0.70), ("b", 100, 0.50)):
        for j in range(n_m):
            recs.append(_mrec(i, cat, "BIN", 1, "TARGET" if j < n_m // 2 else "COMP")); i += 1
            recs.append(_mrec(i, cat, "FRQ", 1, "TARGET" if j < n_m * share else "COMP")); i += 1
    h = analyze.human_contrast(rows, "FRQ", (1,), "numbers")
    m, hd = analyze.matched_contrast(h, recs, "FRQ", (1,), "numbers", analyze.NULL_DESIGN, ())
    assert abs(m["delta"] - 0.05) < 1e-9, f"pooled model effect {m['delta']:.4f}, expected +0.0500"
    assert abs(hd - h["delta"]) < 1e-12


def test_i2_effect_class_is_on_the_pooled_estimate_end_to_end():
    """CUSTOM is HIGH at tiers 1 and 2 and strongly reversed at tier 3 on three effects: the per-tier
    majority is HIGH, the pooled classes of those three effects are LOW, and the overall class is LOW."""
    res, _ = _pack("A")
    cls = {r["effect"]: r for r in res["effect_class_rows"] if r["model"] == "CUSTOM"}
    for st in ("FRQ", "RNG", "SOT"):
        r = cls[st]
        assert r["class"] == analyze.classify_cell(r["model_pp"] / 100, r["human_pp"] / 100) == "LOW", (st, r)
    tier_major = analyze.majority_class([r["class"] for r in res["fidelity_rows"] if r["model"] == "CUSTOM"
                                         and r["structure"] in analyze.REGULARITY_EFFECTS])
    overall = next(r["class"] for r in res["agreement_rows"] if r["model"] == "CUSTOM")
    assert tier_major == "HIGH" and overall == "LOW", (tier_major, overall)
    g = res["criterion"]
    assert all(abs(cls[st]["human_pp"] - g[st]["delta_pp"]) < 0.01 for st in cls), "not the confirmatory pooling"


def test_i2_knows_it_versus_shows_it_reads_the_pooled_effect():
    """CUSTOM shows the frequency decoy at full size on the published tier and a pooled effect near 1.4
    points: 'shows the effect' (more than 3 points in the human direction) is read on the pooled estimate."""
    res, _ = _pack("A")
    t1cell = next(r for r in res["fidelity_rows"] if r["model"] == "CUSTOM" and r["structure"] == "FRQ" and r["tier"] == 1)
    pooled = next(r for r in res["effect_class_rows"] if r["model"] == "CUSTOM" and r["effect"] == "FRQ")
    t2 = next(r for r in res["test_T2_rows"] if r["model"] == "CUSTOM" and r["structure"] == "FRQ")
    assert t1cell["model_pp"] > 3.0 and pooled["model_pp"] < 3.0, (t1cell["model_pp"], pooled["model_pp"])
    assert t2["shows"] is False and abs(t2["behavior_pp"] - pooled["model_pp"]) < 0.01, t2


# ---- rule 4: the combined group fidelity -------------------------------------------------------------
def test_i2_folded_fidelity_counts_overshoot_like_undershoot():
    c = lambda h, m: dict(human_pp=h, model_pp=m, **{"class": "HIGH"})   # noqa: E731
    assert abs(analyze.fidelity_ratio_for([c(10, 15)]) - 0.5) < 1e-12
    assert abs(analyze.fidelity_ratio_for([c(10, 5)]) - 0.5) < 1e-12
    assert analyze.fidelity_ratio_for([c(10, 35)]) == -1.0
    # the recheck's T4 case: 150 percent in numbers and a perfect match in pictures is not "falls".
    num = analyze.fidelity_ratio_for([c(10, 15), c(8, 12)])
    pic = analyze.fidelity_ratio_for([c(10, 10), c(8, 8)])
    assert not analyze.test_T4_formats({"numbers": num, "pictures": pic})["reading"].startswith("falls")
    # and T1: an overshoot on the published tier with a match elsewhere is not a steep gradient.
    t1 = analyze.test_T1_memorization({1: analyze.fidelity_ratio_for([c(10, 15)]), 2: 1.0,
                                       3: analyze.fidelity_ratio_for([c(10, 10)])})
    assert not t1["reading"].startswith("steep"), t1


# ---- rule 5: repeated draws, calls behind each point, the bootstrap over calls ----------------------
def _grid_recs(spec):
    """spec: list of (struct, order, [labels]) for one slice (cat 'a', tier 1); one record per label."""
    recs, i = [], 0
    for st, order, labels in spec:
        for d, lab in enumerate(labels):
            recs.append(dict(record_id=f"g{i}", category="a", structure=st, tier=1, format="numbers",
                             prompting_mode="neutral", parsed_choice=lab, exclusion_flag=False,
                             stimulus_id=f"s_{st}", position_order=order, paraphrase_id=1, draw_index=d))
            i += 1
    return recs


def test_i2_bootstrap_resamples_within_grid_points():
    """A model with a pure position preference answers each grid point the same way every time: its
    effect is 0 and its interval is exactly [0, 0] (resampling the calls across grid points would invent
    spread that no re-run could show)."""
    import call_bootstrap as cb
    spec = [("BIN", "o1", ["TARGET"] * 10), ("BIN", "o2", ["COMP"] * 10),
            ("FRQ", "o1", ["TARGET"] * 10), ("FRQ", "o2", ["COMP"] * 10)]
    recs = _grid_recs(spec)
    b = cb.CallBootstrap(recs, "m", 2000, 20260929, 0.95)
    m = analyze.model_contrast(recs, "FRQ", (1,), "numbers", "neutral", analyze.NULL_DESIGN, boot=b)
    assert m["delta"] == 0.0 and m["boot_lo"] == 0.0 and m["boot_hi"] == 0.0, m
    assert m["max_draws"] == 10 and m["n_used"] == 40


def test_i2_bootstrap_is_reproducible_and_describes_the_draws():
    import call_bootstrap as cb
    spec = [("BIN", "o1", ["TARGET"] * 4 + ["COMP"] * 6), ("BIN", "o2", ["TARGET"] * 5 + ["COMP"] * 5),
            ("FRQ", "o1", ["TARGET"] * 7 + ["COMP"] * 3), ("FRQ", "o2", ["TARGET"] * 6 + ["COMP"] * 4)]
    recs = _grid_recs(spec)
    runs = []
    for _ in range(2):
        b = cb.CallBootstrap(recs, "m", 2000, 20260929, 0.95)
        runs.append(analyze.model_contrast(recs, "FRQ", (1,), "numbers", "neutral", analyze.NULL_DESIGN, boot=b))
    a, c = runs
    assert (a["boot_lo"], a["boot_hi"]) == (c["boot_lo"], c["boot_hi"]), "the fixed seed does not reproduce"
    # the endpoints of a coarse replicate distribution can coincide by chance, so compare the replicates
    # themselves (treatment and control arms): an unseeded resampler gives different lists
    assert a["parts"][0][1][1] == c["parts"][0][1][1] and a["parts"][0][2][1] == c["parts"][0][2][1], \
        "the resampled effects differ between two runs with the same seed"
    assert abs(a["delta"] - (13 / 20 - 9 / 20)) < 1e-12, "the model effect is not the mean over draws"
    # within-grid binomial variance: treatment (2.1 + 2.4)/400, control (2.4 + 2.5)/400 -> SD 0.153, so the
    # 95 percent interval is about 0.60 wide.
    assert a["boot_lo"] < a["delta"] < a["boot_hi"] and 0.50 < a["boot_hi"] - a["boot_lo"] < 0.70, \
        (a["boot_lo"], a["boot_hi"])
    try:
        cb.CallBootstrap(recs + recs[:1], "m", 10, 1, 0.95)
    except ValueError:
        pass
    else:
        raise AssertionError("a duplicate record_id was accepted")


# ---- rule 6: prompt sensitivity --------------------------------------------------------------------
def test_i2_prompt_sensitivity_flags_a_sign_change_across_paraphrases():
    def recs(p3_share):
        out, i = [], 0
        for para in (1, 2, 3):
            share = 0.7 if para < 3 else p3_share
            for j in range(10):
                for st, lab in (("BIN", "TARGET" if j < 5 else "COMP"),
                                ("FRQ", "TARGET" if j < 10 * share else "COMP")):
                    out.append(dict(record_id=f"p{i}", category="a", structure=st, tier=1, format="numbers",
                                    prompting_mode="neutral", parsed_choice=lab, exclusion_flag=False,
                                    paraphrase_id=para))
                    i += 1
        return out
    d, flag = analyze.paraphrase_signs(recs(0.3), "FRQ", (1,), design=analyze.NULL_DESIGN)
    assert flag is True and len(d) == 3, (d, flag)
    d, flag = analyze.paraphrase_signs(recs(0.7), "FRQ", (1,), design=analyze.NULL_DESIGN)
    assert flag is False, (d, flag)


# ---- rule 7: T4 with a small human format effect ----------------------------------------------------
def _t4_pre_round5(*a, **k):
    """The pre-format readings (DESCRIPTIVE_T4 False), kept only as a comparison rule and tested as such."""
    saved = analyze.DESCRIPTIVE_T4
    analyze.DESCRIPTIVE_T4 = False
    try:
        return analyze.test_T4_formats(*a, **k)
    finally:
        analyze.DESCRIPTIVE_T4 = saved


def test_i2_T4_has_no_registered_reading_when_a_human_format_effect_is_under_2_points():
    r = analyze.test_T4_formats({"numbers": 1.0, "pictures": 0.2}, {"pictures": "human FRQ effect 1.50 points"})
    assert r["reading"].startswith("descriptive"), r
    assert _t4_pre_round5({"numbers": 1.0, "pictures": 0.2})["reading"].startswith("falls")
    res, _ = _pack("B")
    t4 = next(r for r in res["test_T4_rows"] if r["model"] == "FAITHFUL")
    assert "pictures" in t4["undefined"] and "descriptive" in t4["reading"], t4


def test_i2_T4_is_also_reported_on_the_picture_order():
    """main.md registers T4 'also reported with the numbers cells restricted to the picture's order'."""
    assert analyze.is_picture_order({"position_order": [0, 1, 2]})
    assert not analyze.is_picture_order({"position_order": [1, 0, 2]})
    assert analyze.is_picture_order({"position_order": "[0, 1]"}) and analyze.is_picture_order({"position_order": "o1"})
    assert not analyze.is_picture_order({"position_order": "o2"}) and not analyze.is_picture_order({})
    res, _ = _pack("A")
    t4 = next(r for r in res["test_T4_rows"] if r["model"] == "OVERSHOOT_T1")
    assert "reading_picture_order" in t4 and t4["reading_picture_order"], t4


# ---- rule 8: decoy-target identity in the memorization sensitivity ----------------------------------
def test_i2_memorization_sensitivity_adjusts_for_decoy_target():
    """A model that misses every budget-target decoy and matches everything else: the published tier has
    no budget targets, so the primary gradient reads steep; with the decoy-target share in the
    regression the adjusted gradient is flat."""
    d = analyze.Design.from_stimuli()
    cells = []
    for (cat, tier, fmt), b in d.baseline_pct.items():
        if fmt != "numbers" or cat in d.price_free:
            continue
        for st in ("FRQ", "RNG", "PHT", "SOT", "SYM", "MOT"):
            bud = analyze._budget_target(d, cat, tier, st)
            cells.append(dict(category=cat, tier=tier, structure=st, human_pp=10.0, model_pp=0.0 if bud else 10.0,
                              w=350, budget_target=bud))
    by_tier = {}
    for t in (1, 2, 3):
        sub = [c for c in cells if c["tier"] == t]
        by_tier[t] = sum(c["model_pp"] for c in sub) / sum(c["human_pp"] for c in sub)
    primary = analyze.test_T1_memorization(by_tier)
    s = analyze.test_T1_sensitivity(cells, d, primary)
    assert primary["reading"].startswith("steep"), primary
    assert s["adjusted_reading"].startswith("flat") and abs(s["adjusted_slope"]) < 1e-6, s
    assert s["target_coef"] != "" and "decoy-target" not in s["covariates_omitted"], s


# ---- rule 9: the positive controls -------------------------------------------------------------------
def test_i2_positive_control_is_the_premium_target_frequency_decoy():
    """Humans show the frequency decoy in the budget-target and neutral categories and not in the
    premium-target ones: the effect replicates overall, and its positive control still fails."""
    _, H = _pack("B")
    d = analyze.Design.for_synth()
    criterion = analyze.human_gate(H, d, {"SOT": d.compromise_descriptive})[0]
    pc = analyze.positive_control_check(H, d, criterion, {"SOT": d.compromise_descriptive})
    assert criterion["FRQ"]["replicated"] is True, "the planted overall frequency effect should replicate"
    assert pc["failed"] == ["FRQ"] and abs(pc["frq_premium"]["delta_pp"]) < 3.0, pc


def test_i2_failed_positive_control_makes_its_row_and_the_pattern_tests_uninformative():
    res, _ = _pack("B")
    assert res["failed_controls"] == ["FRQ"]
    frq = [r for r in res["fidelity_rows"] if r["model"] == "FAITHFUL" and r["structure"] == "FRQ"]
    assert frq and all(r["class"] == analyze.UNINFORMATIVE for r in frq), [r["class"] for r in frq]
    ec = next(r for r in res["effect_class_rows"] if r["model"] == "FAITHFUL" and r["effect"] == "FRQ")
    assert ec["class"] == analyze.UNINFORMATIVE
    for rows, key in ((res["test_T1_rows"], "reading"), (res["test_T3_rows"], "reading"),
                      (res["test_T4_rows"], "reading"), (res["test_T5_rows"], "trajectory")):
        r = next(x for x in rows if x["model"] == "FAITHFUL")
        assert r[key].startswith("uninformative"), (key, r[key])
    t2 = next(r for r in res["test_T2_rows"] if r["model"] == "FAITHFUL" and r["structure"] == "FRQ")
    assert t2["reading"].startswith("uninformative")
    route = next(r for r in res["routing_rows"] if r["model"] == "FAITHFUL")
    assert route["scenario"] != "S1" and route["positive_controls"].startswith("failed"), route


# ---- rule 10: the similarity top-up check -----------------------------------------------------------
def _topup_rows(n_b, share_b, n_t, share_t, n_c=2000):
    """Two similarity slices (categories 1 and 2, tier 1): backbone similarity choosers (one row each),
    top-up participants (one row in each slice, so two similarity rows each), and a binary control."""
    rows = []
    for cat in (1, 2):
        for j in range(n_c):
            rows.append(_row(f"c{cat}_{j}", cat, "BIN", 1, chose_target=(1 if j < n_c // 2 else 0)))
        for j in range(n_b):
            rows.append(_row(f"b{cat}_{j}", cat, "SIM", 1, chose_target=(1 if j < n_b * share_b else 0), choice="TARGET"))
    for j in range(n_t):
        for cat in (1, 2):
            rows.append(_row(f"U{j}", cat, "SIM", 1, chose_target=(1 if j < n_t * share_t else 0), choice="TARGET"))
    return rows


def test_i2_similarity_topup_check_rule():
    big = analyze.similarity_topup_check(_topup_rows(2000, 0.50, 2000, 0.60))
    assert big["fired"] is True and abs(big["diff_pp"] - 10.0) < 1e-9, big
    small_n = analyze.similarity_topup_check(_topup_rows(20, 0.50, 20, 0.60, n_c=40))
    assert small_n["fired"] is False and abs(small_n["diff_pp"] - 10.0) < 1e-9 and small_n["p"] > 0.05, small_n
    small_gap = analyze.similarity_topup_check(_topup_rows(20000, 0.50, 20000, 0.53, n_c=2000))
    assert small_gap["fired"] is False and small_gap["p"] < 0.05 and abs(small_gap["diff_pp"] - 3.0) < 1e-9, small_gap


def test_i2_topup_check_switches_the_similarity_benchmark_to_the_backbone():
    res, H = _pack("B")
    assert res["topup"]["fired"] is True, res["topup"]
    tp = analyze.topup_participants(H)
    backbone_only = [r for r in H if not (r["structure"] == "SIM" and r["participant_id"] in tp)]
    d = analyze.Design.for_synth()
    exp = analyze.human_contrast(backbone_only, "SIM", (1, 2, 3), "numbers", d)
    assert abs(res["criterion"]["SIM"]["delta_pp"] - exp["delta"] * 100) < 1e-9, "the SIM benchmark kept the top-up"


# ---- rule 11: the deviation set ----------------------------------------------
def _stimuli_variant(name, edit):
    """A copy of stimuli.json with edit(stimuli) applied, written to a fixed scratch file (never deleted)."""
    S = json.load(open(analyze.STIMULI_PATH, encoding="utf-8"))
    edit(S["stimuli"])
    p = os.path.join(_scratch("stimuli_variants"), name)
    json.dump(S, open(p, "w", encoding="utf-8"))
    return p


def _set_wave1_share(recs, stim_id, share):
    for r in recs:
        if r["id"] == stim_id:
            arm = r["calibration"]["arms"]["numbers"]
            arm["wave1"]["target_share_pct"] = share
            arm.setdefault("trail", {})["wave1_share_pct"] = share


def _refuses(path):
    try:
        analyze.Design.from_stimuli(path)
    except ValueError:
        return True
    return False


def test_i2_deviation_set_is_the_registered_seven_by_the_point_rule():
    """The registered set is SEVEN pairs, computed from the calibration record: the six adjustable pairs that fail
    the calibration rule by option identity, and the published pairs whose POINT share lies outside 25 to 75
    percent (water bottles at 80.0; televisions at 74.7 is inside). Nothing is read from the flags: rewording,
    removing or adding a hard-limit flag changes nothing but the cross-check list, and moving a share across a
    limit makes the analysis refuse."""
    import registered_constants as R
    d = analyze.Design.from_stimuli()
    assert d.deviation_slices == set(R.DEVIATION_SENSITIVITY_PAIRS) and len(d.deviation_slices) == 7, d.deviation_slices
    assert ("televisions", 1, "numbers") not in d.deviation_slices and ("water_bottles", 1, "numbers") in d.deviation_slices
    # flags reworded, the kettles given a deviation flag, the televisions hard-limit flag removed: set unchanged,
    # and the cross-check then agrees
    def reword(recs):
        for r in recs:
            r["flags"] = [f.replace("CALIBRATION_DEVIATION", "CALIBRATION_DEVIATION (reworded)", 1)
                          for f in r.get("flags", [])
                          if not (r["id"] == "BIN_televisions_t1" and f.startswith("CALIBRATION_HARD_LIMIT_FLAG"))]
            if r["id"] == "BIN_electric_kettles_t3" and not any(f.startswith("CALIBRATION_DEVIATION") for f in r["flags"]):
                r["flags"].append("CALIBRATION_DEVIATION: premium share 55.3")
    d2 = analyze.Design.from_stimuli(_stimuli_variant("stimuli_reworded_flags.json", reword))
    assert d2.deviation_slices == set(R.DEVIATION_SENSITIVITY_PAIRS) and d2.deviation_flag_mismatch == [], \
        d2.deviation_flag_mismatch
    # a hard-limit flag added to an in-limit published pair: the set is unchanged, the cross-check names the pair
    def flag_earbuds(recs):
        for r in recs:
            if r["id"] == "BIN_earbuds_t1":
                r.setdefault("flags", []).append("CALIBRATION_HARD_LIMIT_FLAG (planted)")
    d3 = analyze.Design.from_stimuli(_stimuli_variant("stimuli_extra_flag.json", flag_earbuds))
    assert d3.deviation_slices == set(R.DEVIATION_SENSITIVITY_PAIRS), "a flag decided the set"
    assert ("earbuds", 1, "numbers") in d3.deviation_flag_mismatch, d3.deviation_flag_mismatch
    # the point share moved across a limit, either way: the analysis refuses
    assert _refuses(_stimuli_variant("stimuli_water_inside.json",
                                     lambda recs: _set_wave1_share(recs, "BIN_water_bottles_t1", 74.0))), \
        "water bottles moved inside the limits and the analysis ran with six pairs"
    assert _refuses(_stimuli_variant("stimuli_tv_outside.json",
                                     lambda recs: _set_wave1_share(recs, "BIN_televisions_t1", 76.0))), \
        "televisions moved outside the limits and the analysis ran with eight pairs"

    def eighth_failure(recs):
        for r in recs:
            if r["id"] == "BIN_hard_drives_t2":
                r["calibration"]["arms"]["words"]["wave3"]["target_share_pct"] = 60.0
    assert _refuses(_stimuli_variant("stimuli_eighth_failure.json", eighth_failure)), \
        "an eighth failing adjustable pair was accepted without refusing"


# ---- rule 12: the re-run rule ----------------------------------------------------
def test_i2_rerun_rule():
    """A re-run reproduces a model effect when the deposited estimate lies inside the re-run's 95 percent
    interval over calls (the interval's ends count as inside)."""
    import registered_constants as R
    assert R.C.RERUN_RULE == 0.95 and not hasattr(R.C, "RERUN_RANGE_PP")
    # the rule reads the re-run pack's own interval, which is computed at BOOTSTRAP_LEVEL
    assert R.C.RERUN_RULE == R.C.BOOTSTRAP_LEVEL
    assert analyze.rerun_reproduces(10.0, 8.0, 12.0)
    assert analyze.rerun_reproduces(8.0, 8.0, 12.0) and analyze.rerun_reproduces(12.0, 8.0, 12.0)
    assert not analyze.rerun_reproduces(7.9, 8.0, 12.0) and not analyze.rerun_reproduces(12.1, 8.0, 12.0)
    # a wide re-run interval accepts a deposited value far from its centre; a narrow one refuses a close value
    assert analyze.rerun_reproduces(4.0, 3.5, 20.0) and not analyze.rerun_reproduces(10.0, 10.5, 11.0)


# ---- rule 13: the compromise power inputs -----------------------------------------------------------
def test_i2_compromise_power_runs_on_the_confirmatory_cells():
    sys.path.insert(0, POWER_DIR)
    import power_compromise_pooled as P
    slices, _, n_all = P.compromise_slices()
    assert sum(n for _, _, n in slices) == 4200 and len(slices) == 10 and n_all == 17, slices
    se = P.se_pooled(4200 * 0.85, 4200)
    assert abs(P.power_directional(0.04, se, 0.05 / 6) - 0.81) < 0.01


# ---- After the independent review (2026-09-29) ----------------------------------------------------------
def test_i2_review_directional_readings_need_an_undershoot():
    """Folding makes an overshoot read like an undershoot; a directional reading must need the undershoot."""
    t4 = _t4_pre_round5({"numbers": 1.0, "pictures": 0.0}, None, {"numbers": 1.0, "pictures": 2.0})
    assert not t4["reading"].startswith("falls"), t4
    assert _t4_pre_round5({"numbers": 1.0, "pictures": 0.2}, None,
                          {"numbers": 1.0, "pictures": 0.2})["reading"].startswith("falls")
    fid = {"FRQ": -0.5, "RNG": -0.5, "SOT": -0.5, "MOT": 1.0}
    t3 = analyze.test_T3_ladder(fid, {"FRQ": "OVER", "RNG": "OVER", "SOT": "OVER", "MOT": "HIGH"}, {},
                                {"FRQ": 2.5, "RNG": 2.5, "SOT": 2.5, "MOT": 1.0})
    assert not t3["reversed"] and not t3["reading"].startswith("reversed"), t3
    t1 = analyze.test_T1_memorization({1: 1.0, 2: 1.0, 3: 0.2}, {1: 1.0, 2: 1.0, 3: 1.8})
    assert not t1["reading"].startswith("steep"), t1
    assert analyze.test_T1_memorization({1: 1.0, 2: 0.6, 3: 0.2}, {1: 1.0, 2: 0.6, 3: 0.2})["reading"].startswith("steep")
    assert _t4_pre_round5({"numbers": 0.6, "pictures": 0.8})["reading"].startswith("higher in pictures")
    assert analyze.test_T4_formats({"numbers": 0.6, "pictures": 0.8})["reading"].startswith("descriptive")


def test_i2_review_exact_three_point_reversal_is_low():
    """47/100 - 50/100 is -3.0000000000000027 in floating point; the registered 3 points must hold."""
    assert analyze.classify_cell(47 / 100 - 50 / 100, 0.04) == "LOW"
    assert analyze.classify_cell(46 / 100 - 50 / 100, 0.04) == "ANTI"
    assert analyze.gate_exit_class(47 / 100 - 50 / 100) == "excluded(criterion-exit)"
    assert analyze.classify_cell(0.07 * 0.4, 0.04) == "HIGH"      # 70 percent computed, not typed


def test_i2_review_no_room_slice_leaves_both_sides_of_the_class():
    """NOROOM's binary control in category 0, tier 1 sits at 95 percent: that slice leaves the model's pooled
    effect AND the human effect it is classed against."""
    res, H = _pack("A")
    d = analyze.Design.for_synth()
    drop = {("0", 1, "numbers")}
    row = next(r for r in res["effect_class_rows"] if r["model"] == "NOROOM" and r["effect"] == "FRQ")
    h = analyze.human_contrast(H, "FRQ", (1, 2, 3), "numbers", d, drop)
    recs = _exact_model("NOROOM", lambda st, t, c: (0.30 if (c, t) == (0, 1) else _planted(st, t, c)),
                        bin_share=lambda c, t: 0.95 if (c, t) == (0, 1) else synth.BASE)
    m, hd = analyze.matched_contrast(h, recs, "FRQ", (1, 2, 3), "numbers", d, drop)
    assert abs(row["human_pp"] - round(hd * 100, 2)) < 1e-9 and abs(row["model_pp"] - round(m["delta"] * 100, 2)) < 1e-9, \
        (row, hd, m["delta"])
    assert abs(row["human_pp"] - res["criterion"]["FRQ"]["delta_pp"]) > 0.01, "the class read the criterion's slices"
    assert any(r["model"] == "NOROOM" and r["category"] == "0" and r["tier"] == 1 for r in res["no_room_rows"])


def test_i2_review_topup_rows_leave_the_first_trial_check():
    res, H = _pack("B")
    tp = analyze.topup_participants(H)
    backbone_only = [r for r in H if not (r["structure"] == "SIM" and r["participant_id"] in tp)]
    exp = analyze.human_contrast(backbone_only, "SIM", (1, 2, 3), "numbers", analyze.Design.for_synth(), (), "first")
    assert res["first_trial"]["per_effect"]["SIM"]["n_first"] == exp["n"], (res["first_trial"]["per_effect"]["SIM"], exp["n"])


def test_i2_review_T4_numbers_undefined_blocks_the_reading():
    r = analyze.test_T4_formats({"numbers": 1.0, "pictures": 0.1}, {"numbers": "human FRQ effect 1.20 points"})
    assert r["reading"].startswith("descriptive"), r


def test_i2_review_similarity_placements_share_one_control_resampling():
    """Backpacks, tier 2: the clone_HF placement targets the premium option, clone_HD the budget option, and
    both read the SAME binary calls. With equal weights the control cancels, so when the similarity calls
    are identical on every draw the interval must have zero width (resampling the control twice, once per
    coding, invented spread)."""
    import call_bootstrap as cb
    d = analyze.Design.from_stimuli()
    recs, i = [], 0
    for g, hd_share in ((0, 0.5), (1, 0.6)):
        for k in range(10):
            recs.append(dict(record_id=f"b{i}", category="backpacks", structure="BIN", tier=2, format="numbers",
                             prompting_mode="neutral", parsed_choice="TARGET" if k < 10 * hd_share else "COMP",
                             exclusion_flag=False, stimulus_id="BIN_backpacks_t2", position_order=[g, 1 - g],
                             paraphrase_id=1)); i += 1
    for placement in ("clone_HF", "clone_HD"):
        for g in range(2):
            for k in range(10):
                recs.append(dict(record_id=f"s{i}", category="backpacks", structure="SIM", tier=2, format="numbers",
                                 prompting_mode="neutral", parsed_choice="TARGET" if g == 0 else "COMP",
                                 exclusion_flag=False, stimulus_id="SIM_backpacks_t2", position_order=[g, 1 - g, 2],
                                 paraphrase_id=1, sim_placement=placement, placement=placement)); i += 1
    b = cb.CallBootstrap(recs, "m", 2000, 20260929, 0.95)
    m = analyze.model_contrast(recs, "SIM", (2,), "numbers", "neutral", d, boot=b)
    assert abs(m["boot_hi"] - m["boot_lo"]) < 1e-12 and abs(m["boot_lo"] - m["delta"]) < 1e-12, m


def test_i2_review_published_tier_over_reading_is_read_from_the_tier_class():
    """OVER_T1_ONLY doubles the effects on the published tier only: an effect can be HIGH pooled and OVER on
    the published tier, and the retrieval reading follows the published-tier class."""
    res, _ = _pack("A")
    t1cls = {r["structure"]: r["class"] for r in res["fidelity_rows"] if r["model"] == "OVER_T1_ONLY" and r["tier"] == 1}
    rows = {r["effect"]: r for r in res["effect_class_rows"] if r["model"] == "OVER_T1_ONLY"}
    over_t1 = [st for st, c in t1cls.items() if c == "OVER" and rows[st]["human_gate"] == "passed"]
    assert over_t1 and all("published tier" in rows[st]["over_reading"] for st in over_t1), (t1cls, rows)
    assert any(rows[st]["class"] == "HIGH" for st in over_t1), {st: rows[st]["class"] for st in over_t1}


def test_i2_review_only_the_primary_arm_is_confirmatory_and_T5_reads_the_reasoning_arm():
    res, _ = _pack("A")
    assert res["numbers"]["model.REASONING_PAIR.records_left_out_other_neutral_arms"] > 0
    cls = {r["effect"]: r["class"] for r in res["effect_class_rows"] if r["model"] == "REASONING_PAIR"}
    assert cls["FRQ"] == "HIGH" and cls["SYM"] == "HIGH", cls   # the reversed temperature arm stayed out
    t5 = next(r for r in res["test_T5_rows"] if r["model"] == "REASONING_PAIR")
    assert t5["reasoning_reading"].startswith("reasoning-on lowers fidelity"), t5


def test_i2_review_failed_control_reaches_the_secondary_readings():
    res, _ = _pack("B")
    fm = [r for r in res["fmt_model_rows"] if r["model"] == "FAITHFUL" and r["test"].startswith("FRQ")]
    dv = [r for r in res["divergence_rows"] if r["model"] == "FAITHFUL"]
    assert fm and all(r["reading"].startswith("uninformative") for r in fm), [r["reading"] for r in fm]
    assert dv and all(r["reading"].startswith("uninformative") for r in dv), [r["reading"] for r in dv]


def test_i2_review_every_category_is_reported():
    res, _ = _pack("A")
    human_cats = [r for r in res["bench_rows"] if r["category"] != "pooled" and r["effect"] == "FRQ" and r["format"] == "numbers"]
    model_cats = [r for r in res["category_rows"] if r["model"] == "CUSTOM" and r["effect"] == "FRQ"]
    assert len(human_cats) == 17 and len(model_cats) == 17, (len(human_cats), len(model_cats))
    assert all(r["boot_lo_pp"] != "" and r["class"] for r in model_cats)


# ================================================================================================
# FURTHER RULES
# ================================================================================================
# ---- rule 1 (F1): readings resolved against the 95 percent interval of the joint bootstrap -------------
def test_r2_T1_resolution_boundaries():
    """Steep needs the drop above 0.30 AND the interval above the flat region (0.10 per tier step, 0.20 across the
    three tiers); flat needs the slope inside 0.10 AND the interval's upper end below 0.30; an interval that rules
    out both is 'neither' (descriptive); anything else is not resolved. No interval (no bootstrap) resolves
    nothing."""
    T = analyze.test_T1_memorization
    steep = {1: 1.0, 2: 0.8, 3: 0.6}         # drop 0.40
    flat = {1: 1.0, 2: 0.95, 3: 0.95}        # drop 0.05, slope -0.025
    shallow = {1: 1.0, 2: 0.875, 3: 0.75}    # drop 0.25, slope -0.125
    assert T(steep, drop_ci=(0.25, 0.60), resolve=True)["reading"].startswith("steep")
    r = T(steep, drop_ci=(0.15, 0.60), resolve=True)
    assert r["reading"].startswith(analyze.NOT_RESOLVED) and r["p_steep"] == "U", r
    assert T(flat, drop_ci=(-0.20, 0.25), resolve=True)["reading"].startswith("flat")
    r = T(flat, drop_ci=(-0.20, 0.35), resolve=True)
    assert r["reading"].startswith(analyze.NOT_RESOLVED) and r["p_flat"] == "U", r
    # an interval that rules out both readings: still NOT RESOLVED, described as such, and
    # routed as 'neither'
    r = T(shallow, drop_ci=(0.21, 0.29), resolve=True)
    assert (r["reading"].startswith(analyze.NOT_RESOLVED) and "rules out every registered reading" in r["reading"]
            and not r["resolved"] and r["p_steep"] == r["p_flat"] == "F"), r
    # a point past the steep cutoff whose whole interval sits at or below it (the combine can do that): open, not
    # steep (review note b)
    r = T(steep, drop_ci=(0.21, 0.29), resolve=True)
    assert r["p_steep"] == "U" and r["reading"].startswith(analyze.NOT_RESOLVED), r
    for ci in (None, (None, None)):
        assert T(steep, drop_ci=ci, resolve=True)["reading"].startswith(analyze.NOT_RESOLVED)
        assert T(flat, drop_ci=ci, resolve=True)["reading"].startswith(analyze.NOT_RESOLVED)
    # the undershoot guard (F12) still blocks steep: an invented-tier overshoot never reads steep
    r = T(steep, {1: 1.0, 2: 1.2, 3: 1.4}, drop_ci=(0.35, 0.45), resolve=True)
    assert r["p_steep"] == "F" and not r["reading"].startswith("steep"), r
    # unbounded ends (undefined replicates) keep a reading open
    assert T(flat, drop_ci=(-math.inf, 0.2), resolve=True)["reading"].startswith("flat")
    assert T(steep, drop_ci=(-math.inf, 0.6), resolve=True)["reading"].startswith(analyze.NOT_RESOLVED)


def test_r2_T3_T4_T5_resolution_boundaries():
    fid = {"FRQ": 1.0, "RNG": 1.0, "SOT": 0.9, "MOT": 0.5}             # declines by 0.50
    T3 = analyze.test_T3_ladder
    ok = T3(fid, {}, {}, None, ci=dict(top_minus_bottom=(0.20, 0.80), bottom_minus_middle=(-0.7, -0.1)), resolve=True)
    assert ok["reading"].startswith("declines"), ok
    op = T3(fid, {}, {}, None, ci=dict(top_minus_bottom=(0.10, 0.80), bottom_minus_middle=(-0.7, -0.1)), resolve=True)
    assert op["reading"].startswith(analyze.NOT_RESOLVED) and op["p_declines"] == "U", op
    flat3 = {"FRQ": 0.9, "RNG": 0.9, "SOT": 0.9, "MOT": 0.95}
    assert T3(flat3, {}, {}, None, ci=dict(top_minus_bottom=(-0.25, 0.20), bottom_minus_middle=(-0.2, 0.3)),
              resolve=True)["reading"].startswith("flat")
    assert T3(flat3, {}, {}, None, ci=dict(top_minus_bottom=(-0.35, 0.20), bottom_minus_middle=(-0.2, 0.3)),
              resolve=True)["reading"].startswith(analyze.NOT_RESOLVED)
    rev = {"FRQ": 0.1, "RNG": 0.1, "SOT": 0.1, "MOT": 0.9}
    cls = {"FRQ": "LOW", "RNG": "LOW", "SOT": "LOW", "MOT": "HIGH"}
    r = T3(rev, cls, {"FRQ": 0.9, "RNG": 0.9, "SOT": 0.9}, None,
           ci=dict(top_minus_bottom=(-1.0, -0.5), bottom_minus_middle=(0.5, 1.0)), resolve=True)
    assert r["reversed"] and r["attribution"] == analyze.ARGUMENT_OVERRIDE, r
    r = T3(rev, cls, {"FRQ": 0.9, "RNG": 0.9, "SOT": 0.9}, None,
           ci=dict(top_minus_bottom=(-1.0, -0.5), bottom_minus_middle=(0.05, 1.0)), resolve=True)
    assert not r["reversed"] and r["p_reversed"] == "U" and r["reading"].startswith(analyze.NOT_RESOLVED), r
    # every reading set out: still not resolved, described, all three states F
    r = T3({"FRQ": 1.0, "RNG": 1.0, "SOT": 0.9, "MOT": 0.8}, {}, {}, None,
           ci=dict(top_minus_bottom=(0.15, 0.25), bottom_minus_middle=(-0.2, 0.0)), resolve=True)
    assert (r["reading"].startswith(analyze.NOT_RESOLVED) and "rules out every" in r["reading"]
            and r["p_declines"] == r["p_reversed"] == r["p_flat"] == "F"), r
    T4 = _t4_pre_round5
    r = T4({"numbers": 0.9, "pictures": 0.7}, None, None, diff_ci=(0.15, 0.25), resolve=True)
    assert (r["reading"].startswith(analyze.NOT_RESOLVED) and "rules out every" in r["reading"]
            and r["p_falls"] == r["p_flat"] == "F"), r
    assert T4({"numbers": 0.9, "pictures": 0.4}, None, None, diff_ci=(0.2, 0.8), resolve=True)["reading"].startswith("falls")
    assert T4({"numbers": 0.9, "pictures": 0.4}, None, None, diff_ci=(0.1, 0.8),
              resolve=True)["reading"].startswith(analyze.NOT_RESOLVED)
    assert T4({"numbers": 0.9, "pictures": 0.85}, None, None, diff_ci=(-0.2, 0.25),
              resolve=True)["reading"].startswith("flat")
    assert T4({"numbers": 0.9, "pictures": 0.85}, None, None, diff_ci=(-0.2, 0.31),
              resolve=True)["reading"].startswith(analyze.NOT_RESOLVED)
    T5 = analyze.test_T5_trajectory
    assert T5(0.5, 0.9, traj_ci=(0.2, 0.6), resolve=True)["trajectory"].startswith("newer more faithful")
    r = T5(0.5, 0.9, traj_ci=(0.1, 0.6), resolve=True)
    assert r["trajectory"].startswith(analyze.NOT_RESOLVED) and r["p_rising"] == "U", r
    assert T5(0.8, 0.85, traj_ci=(-0.1, 0.15), resolve=True)["trajectory"].startswith("flat")
    assert T5(0.8, 0.85, traj_ci=(-0.1, 0.16), resolve=True)["trajectory"].startswith(analyze.NOT_RESOLVED)
    assert T5(0.9, 0.5, traj_ci=(-0.6, -0.2), resolve=True)["trajectory"].startswith("newer less faithful")
    r = T5(None, None, reasoning_on=0.3, reasoning_off=0.9, reason_ci=(0.1, 0.9), resolve=True)
    assert r["reasoning_reading"].startswith(analyze.NOT_RESOLVED), r
    r = T5(None, None, reasoning_on=0.3, reasoning_off=0.9, reason_ci=(0.2, 0.9), resolve=True)
    assert r["reasoning_reading"].startswith("reasoning-on lowers"), r


def _rt(reading, **states):
    return dict(reading=reading, point_reading=states.pop("point", reading), resolved=states.pop("resolved", True),
                **states)


_T1_FLAT = dict(reading="flat: x", point_reading="flat: x", p_steep="F", p_flat="T", resolved=True)
_T1_STEEP = dict(reading="steep: x", point_reading="steep: x", p_steep="T", p_flat="F", resolved=True)
_T1_OPEN_FLAT_PT = dict(reading="not resolved: x", point_reading="flat: x", p_steep="U", p_flat="U", resolved=False)
_T1_OPEN_STEEP_PT = dict(reading="not resolved: x", point_reading="steep: x", p_steep="U", p_flat="F", resolved=False)
_T3_FLAT = dict(reading="flat: x", point_reading="flat: x", reversed=False, point_reversed=False, attribution="",
                p_declines="F", p_reversed="F", p_flat="T", resolved=True,
                _reversed_base=dict(reversed=True, attribution="no account attributed", missed_effects="",
                                    missed_recognition=""))
_T4_FLAT = dict(reading="flat across formats", point_reading="flat across formats", p_falls="F", p_flat="T",
                resolved=True)
_T4_FALLS = dict(reading="falls numbers->pictures", point_reading="falls numbers->pictures", p_falls="T",
                 p_flat="F", resolved=True)
_T4_OPEN_FALLS_PT = dict(reading="not resolved: x", point_reading="falls numbers->pictures", p_falls="U",
                         p_flat="F", resolved=False)
# reason construction (S3) rests on a resolved decline down the argument-strength ladder
_T3_DECL = dict(_T3_FLAT, reading="declines down the ladder -> x", point_reading="declines down the ladder -> x",
                p_declines="T", p_flat="F", resolved=True)
_T3_OPEN_DECL_PT = dict(_T3_FLAT, reading="not resolved: x", point_reading="declines down the ladder -> x",
                        p_declines="U", p_flat="F", resolved=False)
_T5_NONE = dict(trajectory="insufficient generations", point_trajectory="insufficient generations", resolved=True)
_GI = dict(not_assessable=False)


def _route(t1, t3=None, t4=None, t5=None, overall="HIGH", t2_override=False, t2_state=None, classes=None,
           consistent=True, generations=False, **kw):
    classes = classes or {"FRQ": overall if overall in ("HIGH", "LOW", "ANTI", "PARTIAL", "OVER") else "HIGH"}
    return analyze.route_resolved("m", [], t1, t2_override, t3 or _T3_FLAT, t4 or _T4_FLAT, t5 or _T5_NONE, _GI,
                                  dict(dominant_class=overall), consistent, generations, effect_classes=classes,
                                  overall=overall, t2_state=t2_state, **kw)


def test_r3_S1_needs_no_flat_memorization_reading():
    """Rule (a), with the guard: S1 needs the HIGH class, the effects shown without recognition, and NO resolved steep
    memorization reading, reversed ladder or fall across formats; an open reading qualifies it with the one set
    qualifier, unless the open reading's estimate points to an account."""
    b, s, poss = _route(_T1_OPEN_FLAT_PT)
    assert s == "S1" and poss == ["S1"] and analyze.S1_QUALIFIER in b and "(open: T1)" in b, (b, s)
    assert analyze.S1_QUALIFIER == "pattern tests not resolved at the design's resolution"
    b, s, _ = _route(_T1_OPEN_STEEP_PT)                    # the estimate says steep, the interval leaves it open
    assert s == "NOT_RESOLVED", (b, s)                      # the guard withholds S1
    assert _route(_T1_OPEN_STEEP_PT, s1_point_guard=False)[1] == "S1"
    b, s, _ = _route(_T1_FLAT)
    assert s == "S1" and "qualifier" not in b, (b, s)
    b, s, _ = _route(_T1_STEEP)
    assert s == "S2", (b, s)                                # a resolved steep reading takes S2, not S1
    b, s, _ = _route(_T1_FLAT, t3=_T3_DECL)
    assert s == "S3", (b, s)                                # a resolved ladder decline: not S1
    b, s, _ = _route(_T1_FLAT, t3=_T3_OPEN_DECL_PT)
    assert s == "NOT_RESOLVED", (b, s)                      # an open decline whose estimate declines: S1 withheld
    t3_open_flat_pt = dict(_T3_OPEN_DECL_PT, point_reading="flat: x", p_flat="U")
    b, s, _ = _route(_T1_OPEN_FLAT_PT, t3=t3_open_flat_pt)
    assert s == "S1" and b.endswith(analyze.S1_QUALIFIER + " (open: T1, T3)"), (b, s)   # one qualifier, both listed
    t3_rev = dict(_T3_FLAT, reading="reversed ladder: x", point_reading="reversed ladder: x", reversed=True,
                  point_reversed=True, attribution="no account attributed", p_reversed="T", p_flat="F")
    b, s, _ = _route(_T1_FLAT, t3=t3_rev)
    assert s == "REVERSED_LADDER", (b, s)                   # a resolved reversal is taken before S1
    b, s, _ = _route(_T1_OPEN_FLAT_PT, t3=t3_rev)
    assert s == "NOT_RESOLVED", (b, s)                      # ... unless an open steep reading could precede it
    b, s, _ = _route(_T1_OPEN_FLAT_PT, t2_override=True, t2_state="T")
    assert s != "S1", (b, s)                                # recognizes-but-does-not-show at the point: not S1
    b, s, _ = _route(dict(_T1_FLAT, reading="uninformative (positive control failed): x"))
    assert s != "S1", (b, s)                                # a failed positive control: no S1


def test_r3_account_routes_are_strict():
    """Rule (b): an account-attributing route is taken only on a resolved reading; when the estimate points to it
    and the interval leaves it open, the model is NOT_RESOLVED (no later route is claimed); an open reading whose
    estimate points away does not block a later resolved route."""
    b, s, poss = _route(_T1_OPEN_STEEP_PT, overall="PARTIAL")
    assert s == "NOT_RESOLVED" and "S2" in poss, (b, s, poss)
    assert _route(_T1_STEEP, overall="PARTIAL")[1] == "S2"
    b, s, poss = _route(_T1_FLAT, t3=_T3_OPEN_DECL_PT, overall="PARTIAL")
    assert s == "NOT_RESOLVED" and "S3" in poss, (b, s, poss)
    assert _route(_T1_FLAT, t3=_T3_DECL, overall="PARTIAL")[1] == "S3"
    # an open memorization reading blocks every later route whatever its estimate, so even a resolved ladder decline is not claimed
    b, s, poss = _route(_T1_OPEN_FLAT_PT, t3=_T3_DECL, overall="PARTIAL")
    assert s == "NOT_RESOLVED" and {"S2", "S3"} <= set(poss), (b, s, poss)
    # ... and an open decline blocks the class routes after it (PARTIAL here)
    b, s, poss = _route(_T1_FLAT, t3=_T3_OPEN_DECL_PT, overall="PARTIAL", classes={"FRQ": "HIGH", "SOT": "LOW"})
    assert s == "NOT_RESOLVED" and {"S3", "PARTIAL"} <= set(poss), (b, s, poss)
    # an open override whose two outcomes are both S4 (rational override or systematic inversion): S4 stands
    b, s, poss = _route(_T1_FLAT, overall="ANTI", t2_override=True, t2_state="U", classes={"FRQ": "ANTI"})
    assert s == "S4" and poss == ["S4"] and "not resolved" in b, (b, s, poss)
    # rational override: resolved -> S4; open with the point favouring it -> NOT_RESOLVED
    assert _route(_T1_FLAT, overall="LOW", t2_override=True, t2_state="T", classes={"FRQ": "LOW"})[1] == "S4"
    b, s, poss = _route(_T1_FLAT, overall="LOW", t2_override=True, t2_state="U", classes={"FRQ": "LOW"})
    assert s == "NOT_RESOLVED" and "S4" in poss, (b, s, poss)
    # reversed ladder: resolved -> taken (an open memorization reading does not exclude it); open -> NOT_RESOLVED
    t3_rev = dict(_T3_FLAT, reading="reversed ladder: x", point_reading="reversed ladder: x", reversed=True,
                  point_reversed=True, attribution="no account attributed", p_reversed="T", p_flat="F")
    assert _route(_T1_FLAT, t3=t3_rev, overall="LOW", classes={"FRQ": "LOW"})[1] == "REVERSED_LADDER"
    assert _route(_T1_OPEN_FLAT_PT, t3=t3_rev, overall="LOW", classes={"FRQ": "LOW"})[1] == "NOT_RESOLVED"
    t3_open = dict(t3_rev, reading="not resolved: x", reversed=False, attribution="", p_reversed="U",
                   resolved=False)
    b, s, poss = _route(_T1_FLAT, t3=t3_open, overall="LOW", classes={"FRQ": "LOW"})
    assert s == "NOT_RESOLVED" and "REVERSED_LADDER" in poss, (b, s, poss)
    # a resolved steep reading excludes the reversed ladder (precedence through resolved readings), with or without
    # the recognition attribution
    assert _route(_T1_STEEP, t3=t3_rev, overall="LOW", classes={"FRQ": "LOW"})[1] == "S2"
    t3_rev_ovr = dict(t3_rev, attribution=analyze.ARGUMENT_OVERRIDE,
                      _reversed_base=dict(reversed=True, attribution=analyze.ARGUMENT_OVERRIDE, missed_effects="FRQ",
                                          missed_recognition="FRQ=0.9"))
    assert _route(_T1_STEEP, t3=t3_rev_ovr, overall="LOW", classes={"FRQ": "LOW"})[1] == "S2"
    assert _route(_T1_FLAT, t3=t3_rev_ovr, overall="LOW",
                  classes={"FRQ": "LOW"})[1] == "REVERSED_LADDER_OVERRIDE"
    # the reversed ladder with recognition honours an open steep reading as the plain one does
    b, s, poss = _route(_T1_OPEN_STEEP_PT, t3=t3_rev_ovr, overall="LOW", classes={"FRQ": "LOW"})
    assert s == "NOT_RESOLVED" and "REVERSED_LADDER_OVERRIDE" in poss, (b, s, poss)
    # rising fidelity: an open trajectory whose estimate rises blocks the family-specific route
    t5_open = dict(trajectory="not resolved: x", point_trajectory="newer more faithful -> x", p_rising="U",
                   p_falling="F", p_flat="U", resolved=False)
    b, s, poss = _route(_T1_FLAT, t5=t5_open, overall="PARTIAL", consistent=False, generations=True)
    assert s == "NOT_RESOLVED" and {"S5", "S6"} <= set(poss), (b, s, poss)
    t5_rise = dict(t5_open, trajectory="newer more faithful -> x", p_rising="T", resolved=True)
    assert _route(_T1_FLAT, t5=t5_rise, overall="PARTIAL", consistent=False, generations=True)[1] == "S6"


def test_r3_comparison_options_of_the_router():
    """The two options the stability sweep uses to compare designs (never the registered rule, which is the default):
    open_blocks='favoured' lets an open account reading block only when its estimate favours the route; s1_point_guard
    withholds S1 when an open reading's estimate favours an account route."""
    def rt(t1, t3=None, overall="PARTIAL", **kw):
        return analyze.route_resolved("m", [], t1, False, t3 or _T3_FLAT, _T4_FLAT, _T5_NONE, _GI,
                                      dict(dominant_class=overall), True, False, effect_classes={"FRQ": overall},
                                      overall=overall, **kw)[1]
    # an open memorization reading whose estimate is flat: ignored by the registered rule, blocking under 'any'
    assert rt(_T1_OPEN_FLAT_PT, t3=_T3_DECL) == "NOT_RESOLVED"
    assert rt(_T1_OPEN_FLAT_PT, t3=_T3_DECL, open_blocks="favoured") == "S3"
    assert rt(_T1_OPEN_STEEP_PT, t3=_T3_DECL, open_blocks="favoured") == "NOT_RESOLVED"
    # S1 with an open ladder decline: withheld by the registered rule, taken without it
    assert rt(_T1_FLAT, t3=_T3_OPEN_DECL_PT, overall="HIGH") == "NOT_RESOLVED"
    assert rt(_T1_FLAT, t3=_T3_OPEN_DECL_PT, overall="HIGH", s1_point_guard=False) == "S1"
    assert rt(_T1_OPEN_FLAT_PT, overall="HIGH", s1_point_guard=True) == "S1"      # the estimate favours no account


def test_r5_format_test_is_descriptive_and_reason_construction_reads_the_ladder():
    """The final rule: T4 reports its difference and interval with no reading and decides no scenario; reason
    construction (S3) needs a resolved decline down the argument-strength ladder."""
    r = analyze.test_T4_formats({"numbers": 0.9, "pictures": 0.2}, None, {"numbers": 0.9, "pictures": 0.2},
                                diff_ci=(0.5, 0.9), resolve=True)
    assert (r["reading"].startswith("descriptive") and r["p_falls"] == r["p_flat"] == "F" and r["resolved"]
            and r["diff_lo"] == 0.5 and r["diff_hi"] == 0.9), r
    t4_fall = dict(_T4_FLAT, reading="falls numbers->pictures", point_reading="falls numbers->pictures",
                   p_falls="T", p_flat="F")
    t4_open = dict(t4_fall, reading="not resolved: x", p_falls="U", resolved=False)
    assert _route(_T1_FLAT, t4=t4_fall)[1] == "S1"                        # a fall across formats decides nothing
    b, s, _ = _route(_T1_FLAT, t4=t4_open)
    assert s == "S1" and "qualifier" not in b, (b, s)                      # and is never an open pattern test
    assert _route(_T1_FLAT, t4=t4_fall, overall="PARTIAL")[1] == "COMPOSITE"
    assert _route(_T1_FLAT, t3=_T3_DECL, overall="PARTIAL")[1] == "S3"
    assert _route(_T1_FLAT, t3=_T3_DECL)[1] == "S3"                        # a resolved decline: not S1
    assert analyze.route_model("m", [], _T1_FLAT, False, _T3_DECL, _T4_FLAT, _T5_NONE, _GI,
                               dict(dominant_class="PARTIAL"), True, False, effect_classes={"FRQ": "PARTIAL"},
                               overall="PARTIAL")[1] == "S3"
    assert analyze.route_model("m", [], _T1_FLAT, False, _T3_FLAT, t4_fall, _T5_NONE, _GI,
                               dict(dominant_class="HIGH"), True, False, effect_classes={"FRQ": "HIGH"},
                               overall="HIGH")[1] == "S1"


def test_r5_memorization_sensitivity_is_paired_and_one_step():
    """The final rule reaches the sensitivity re-readings: a category out of
    the hard limits on one tier leaves both tiers, and the adjusted drop over tiers 1 and 2 is one tier step."""
    d = analyze.Design.for_synth()
    assert d.outside_hard_limits(("6", 1, "numbers")) and not d.outside_hard_limits(("6", 2, "numbers"))

    def cells(model_t2, model_cat6):
        out = []
        for cat in ("0", "1", "2", "3", "4", "5", "6"):
            for tier in (1, 2):
                m = model_cat6 if cat == "6" else (20.0 if tier == 1 else model_t2)
                out.append(dict(category=cat, tier=tier, structure="FRQ", human_pp=20.0, model_pp=m, w=1,
                                budget_target=False, slice_budget=False))
        return out
    # identical on both tiers except category 6, which is reversed on both tiers and out of limits on tier 1 only:
    # paired, it leaves both tiers and the drop is zero
    r = analyze.test_T1_sensitivity(cells(20.0, -60.0), d, _T1_FLAT)
    assert abs(r["restricted_drop"]) < 1e-9 and not r["restricted_reading"].startswith("steep"), r
    # half the fidelity on the new-values tier: the restricted and the adjusted drop are both 0.5 (one tier step)
    r = analyze.test_T1_sensitivity(cells(10.0, -60.0), d, _T1_FLAT)
    assert abs(r["restricted_drop"] - 0.5) < 1e-9 and abs(r["adjusted_drop"] - 0.5) < 1e-6, r


def test_r4_guard_leaves_S1_possible():
    """The adopted guard: when an open reading's estimate points to an account and withholds S1, the model
    is NOT_RESOLVED between S1 and that account, and nothing else."""
    b, s, poss = _route(_T1_OPEN_STEEP_PT)
    assert s == "NOT_RESOLVED" and poss == ["S1", "S2"], (b, s, poss)
    b, s, poss = _route(_T1_FLAT, t3=_T3_OPEN_DECL_PT)
    assert s == "NOT_RESOLVED" and poss == ["S1", "S3"], (b, s, poss)
    t5_open_rise = dict(trajectory="not resolved: newer more faithful", point_trajectory="newer more faithful",
                        p_rising="U", p_falling="F", p_flat="U", resolved=False)
    b, s, poss = _route(_T1_FLAT, t5=t5_open_rise, generations=True)
    assert s == "NOT_RESOLVED" and poss == ["S1", "S6"], (b, s, poss)
    t3_open_rev = dict(_T3_FLAT, reading="not resolved: x", point_reversed=True, p_reversed="U", p_flat="F",
                       resolved=False)
    b, s, poss = _route(_T1_FLAT, t3=t3_open_rev)
    assert s == "NOT_RESOLVED" and poss == ["REVERSED_LADDER", "S1"], (b, s, poss)
    b, s, poss = _route(_T1_OPEN_STEEP_PT, t3=_T3_OPEN_DECL_PT)
    assert s == "NOT_RESOLVED" and poss == ["S1", "S2", "S3"], (b, s, poss)
    # an open ladder reading whose estimate is flat can still resolve as a decline: under the registered rule
    # (open_blocks "any") reason construction stays possible too
    t3_open_flat_pt = dict(_T3_OPEN_DECL_PT, point_reading="flat: x")
    b, s, poss = _route(_T1_OPEN_STEEP_PT, t3=t3_open_flat_pt)
    assert s == "NOT_RESOLVED" and poss == ["S1", "S2", "S3"], (b, s, poss)
    b, s, poss = _route(_T1_OPEN_STEEP_PT, t3=t3_open_flat_pt, open_blocks="favoured")
    assert s == "NOT_RESOLVED" and poss == ["S1", "S2"], (b, s, poss)
    # an open reading whose estimate favours no account leaves S1 standing, with the qualifier
    b, s, poss = _route(_T1_OPEN_FLAT_PT)
    assert s == "S1" and poss == ["S1"], (b, s, poss)


def test_r4_kept_members_reproduce_the_registered_readings():
    """The design-study switch keep_members (default off) keeps each pattern-test group's members; rebuilding the
    memorization reading from them reproduces the pipeline's reading and interval exactly, and without the switch
    nothing is kept."""
    _, H = _pack("A")
    models = {"KEEP_X": _exact_model("KEEP_X", _planted)}
    tmp = _scratch("r4_keep_members")
    saved = (analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR)
    try:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = tmp, os.path.join(tmp, "tests"), os.path.join(tmp, "figures")
        res = analyze.build_pack(H, models, human_rows_with_formats=H, human_rows_first_trial=H, mode="TEST",
                                 design=analyze.Design.for_synth(), keep_members=True)
    finally:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = saved
    kept = res["model_results"]["KEEP_X"]["members"]
    assert set(kept["tier"]) == {1, 2, 3} and kept["pooled"], kept.keys()
    fold, raw, reps = {}, {}, {}
    for t, mem in kept["tier_paired"].items():           # the registered T1 reads the paired tiers 1 and 2
        num = sum(x[3] * x[1] for x in mem)
        den = sum(abs(x[2]) for x in mem)
        fold[t], raw[t] = analyze._fold(num / den), num / den
        reps[t] = analyze.group_fold_reps([x[3:] for x in mem])
    ci = analyze.rep_interval(analyze.diff_reps(reps[1], reps[2]))
    mine = analyze.test_T1_memorization(fold, raw, drop_ci=ci, resolve=True)
    theirs = next(r for r in res["test_T1_rows"] if r["model"] == "KEEP_X")
    assert (mine["reading"], mine["drop_lo"], mine["drop_hi"]) == (theirs["reading"], theirs["drop_lo"],
                                                                  theirs["drop_hi"]), (mine, theirs)
    assert theirs["fidelity_t3"] == "" and theirs["descriptive_fidelity_invented_tier"] != "", theirs
    assert theirs["paired_categories"], theirs
    for st, x in kept["pooled"].items():
        assert x[0] == st and abs(x[3]) == 1.0 and len(x[4]) == len(x[5]) == analyze.RC.BOOTSTRAP_RESAMPLES
    # option A's paired tiers: the same effects on both tiers, each on the categories it has on BOTH tiers (a
    # compromise slice that is descriptive on either tier is out of both)
    tp, tc = kept["tier_paired"], kept["tier_paired_cats"]
    assert set(tp) == {1, 2} and [x[0] for x in tp[1]] == [x[0] for x in tp[2]] == list(tc), (tp, tc)
    assert tc and "SIM" not in tc and all(tc.values()), tc
    desc = {(str(c), t, f) for c, t, f in analyze.Design.for_synth().compromise_descriptive}
    assert "SOT" in tc and not any((str(c), t, "numbers") in desc for c in tc["SOT"] for t in (1, 2)), tc["SOT"]
    res_a, _ = _pack("A")
    assert all(v.get("members") is None for v in res_a["model_results"].values())


def test_r3_knows_without_shows_is_resolved_against_intervals():
    """Rule (b): rational override needs a RESOLVED knows-without-shows reading: the recognition rate and its
    interval at or above one half, and the pooled model effect and its interval at or below 3 points."""
    rec = {"FRQ": 0.8}
    beh = {"FRQ": -0.05}
    per, ov = analyze.test_T2_recognition(rec, beh, recog_ci={"FRQ": (0.6, 0.95)}, behavior_ci={"FRQ": (-0.08, -0.02)})
    assert ov and per["FRQ"]["override_state"] == "T" and analyze.t2_override_state(per) == "T", per["FRQ"]
    per, _ = analyze.test_T2_recognition(rec, beh, recog_ci={"FRQ": (0.45, 0.95)}, behavior_ci={"FRQ": (-0.08, -0.02)})
    assert per["FRQ"]["knows_state"] == "U" and per["FRQ"]["override_state"] == "U", per["FRQ"]
    per, _ = analyze.test_T2_recognition(rec, {"FRQ": 0.02}, recog_ci={"FRQ": (0.6, 0.95)},
                                         behavior_ci={"FRQ": (-0.01, 0.045)})
    assert per["FRQ"]["shows_state"] == "U" and per["FRQ"]["override_state"] == "U", per["FRQ"]
    per, _ = analyze.test_T2_recognition({"FRQ": 0.2}, beh, recog_ci={"FRQ": (0.1, 0.35)},
                                         behavior_ci={"FRQ": (-0.08, -0.02)})
    assert per["FRQ"]["knows_state"] == "F" and per["FRQ"]["override_state"] == "F", per["FRQ"]
    per, _ = analyze.test_T2_recognition(rec, {"FRQ": 0.08}, recog_ci={"FRQ": (0.6, 0.95)},
                                         behavior_ci={"FRQ": (0.05, 0.11)})
    assert per["FRQ"]["shows_state"] == "T" and per["FRQ"]["override_state"] == "F", per["FRQ"]
    # an effect with no pooled estimate carries no override, at the point or resolved (confirm round, finding 6)
    per, ov = analyze.test_T2_recognition(rec, {}, recog_ci={"FRQ": (0.6, 0.95)})
    assert not ov and per["FRQ"]["override_state"] == "F" and "no pooled estimate" in per["FRQ"]["reading"], per["FRQ"]


def test_r3_pipeline_routes_the_faithful_models_to_S1_with_the_qualifier():
    """End to end (pack A, 400 choices per human cell): the faithful models' memorization reading is not resolved
    and they route to S1 with the set qualifier; the retrieval-shaped CUSTOM model keeps S2."""
    res, _ = _pack("A")
    route = {r["model"]: r for r in res["routing_rows"]}
    for m in ("REASONING_PAIR", "TWIN_OLD", "TWIN_NEW"):
        t1 = next(r for r in res["test_T1_rows"] if r["model"] == m)
        assert route[m]["scenario"] == "S1", (m, route[m]["scenario"], t1["reading"][:60])
        # the one qualifier appears exactly when a pattern test is open, and names T1 exactly when T1 is open
        assert (route[m]["qualifier"] == analyze.S1_QUALIFIER) == bool(route[m]["open_pattern_tests"]), route[m]
        assert ("T1" in route[m]["open_pattern_tests"]) == (not t1["resolved"]), (route[m], t1["reading"][:60])
        assert "T4" not in route[m]["open_pattern_tests"], route[m]
    # CUSTOM falls only on the invented tier, which is now descriptive, so it is not retrieval (S2); its
    # invented-tier fidelity is reported beside the registered reading
    t1c = next(r for r in res["test_T1_rows"] if r["model"] == "CUSTOM")
    assert route["CUSTOM"]["scenario"] != "S2" and not t1c["reading"].startswith("steep"), (route["CUSTOM"], t1c)
    assert t1c["descriptive_fidelity_invented_tier"] < t1c["fidelity_t1"], t1c
    t2 = [r for r in res["test_T2_rows"] if r["model"] == "REASONING_PAIR"]
    assert t2 and all(r["override_state"] in ("T", "F", "U") for r in t2)
    # the T2 intervals are computed and used: pack B's FAITHFUL draws its probe answers, so its
    # recognition rates carry intervals of positive width, and every pooled effect carries its interval over calls
    resb, _ = _pack("B")
    tb = [r for r in resb["test_T2_rows"] if r["model"] == "FAITHFUL" and not r["reading"].startswith("uninformative")]
    assert tb and all(r["behavior_lo_pp"] != "" and r["behavior_lo_pp"] <= r["behavior_pp"] <= r["behavior_hi_pp"]
                      for r in tb), tb
    assert any(r["recognition_lo"] != "" and r["recognition_lo"] < r["recognition_rate"] < r["recognition_hi"]
               for r in tb), [(r["recognition_lo"], r["recognition_rate"], r["recognition_hi"]) for r in tb]
    for r in tb:                          # the states follow the intervals
        want_k = ("T" if r["recognition_lo"] >= 0.5 and r["knows"] else
                  ("F" if r["recognition_hi"] < 0.5 and not r["knows"] else "U"))
        assert r["knows_state"] == want_k, r

def test_r2_interval_is_conservative_about_undefined_replicates():
    import call_bootstrap as cb
    reps = [float(i) for i in range(100)]
    lo, hi = cb.interval(reps, 0.95)
    assert abs(lo - 2.475) < 1e-9 and abs(hi - 96.525) < 1e-9, (lo, hi)
    lo, hi = cb.interval(reps[:97] + [None] * 3, 0.95)       # 3 undefined of 100: both ends unbounded
    assert lo == -math.inf and hi == math.inf, (lo, hi)
    lo, hi = cb.interval(reps[:99] + [None], 0.95)            # 1 undefined: the ends move outward, stay finite
    assert math.isfinite(lo) and math.isfinite(hi) and lo < 2.475 + 1 and hi > 96.0, (lo, hi)
    assert cb.interval(None, 0.95) == (None, None) and cb.interval([], 0.95) == (None, None)


def test_r2_group_fold_reps_recompute_the_point_formula():
    """Replicate b is combine(sum s*m_b / sum s*h_b) with the signs of the point; a resample whose human effects
    project to zero or below is undefined (None)."""
    members = [(1.0, [0.10, 0.12, 0.05], [0.10, 0.08, -0.01]), (-1.0, [-0.05, -0.05, -0.05], [-0.05, -0.06, -0.02])]
    reps = analyze.group_fold_reps(members)
    assert abs(reps[0] - 1.0) < 1e-12, reps                               # 0.15 / 0.15
    assert abs(reps[1] - analyze._fold(0.17 / 0.14)) < 1e-12, reps        # overshoot combined
    assert reps[2] is None or abs(reps[2] - analyze._fold(0.10 / 0.01)) < 1e-12
    assert analyze.group_fold_reps([(1.0, [0.1], [-0.02])]) == [None]
    assert analyze.group_fold_reps([(1.0, None, [0.1])]) is None and analyze.group_fold_reps([]) is None
    assert analyze.diff_reps([1.0, None], [0.5, 0.5]) == [0.5, None]
    assert analyze.mean_reps([[1.0, 2.0], [3.0, None]]) == [2.0, None]
    # the pooled replicate uses the slice weights: weights 1 and 3, slice effects 0.4 and 0.0 on
    # replicate 0 and 0.0 and 0.2 on replicate 1
    import call_bootstrap as cb
    arm = lambda mean, reps: (mean, reps, 10, 10)   # noqa: E731
    items = [(1.0, arm(0.5, [0.6, 0.5]), arm(0.3, [0.2, 0.5])), (3.0, arm(0.4, [0.4, 0.5]), arm(0.4, [0.4, 0.3]))]
    got = cb.combine(items, 2)
    assert abs(got[0] - 0.1) < 1e-12 and abs(got[1] - 0.15) < 1e-12, got


def test_r2_pipeline_replicates_equal_an_independent_recomputation():
    """TWIN_OLD (deterministic, so only the human side varies): its memorization drop replicates, rebuilt here from a
    fresh within-cell human bootstrap with a separate implementation of the pooling, the group combine and the
    difference, equal the pipeline's; and the printed interval is their 2.5th and 97.5th percentiles, the registered
    95 percent level."""
    import call_bootstrap as cb
    import registered_constants as R
    assert R.C.BOOTSTRAP_LEVEL == 0.95
    res, H = _pack("A")
    assert res["first_trial"]["fired"] is False, "the recomputation below reads the full human sample"
    d = analyze.Design.for_synth()
    recs = _exact_model("TWIN_OLD", _planted, family="famTWIN", generation="old", one_call_per_point=True)
    assert not any(r["model"] == "TWIN_OLD" for r in res["no_room_rows"])
    # the registered test compares tier 1 with tier 2 on the categories each effect has on both tiers
    cls_ok = {(r["structure"], r["tier"]) for r in res["fidelity_rows"] if r["model"] == "TWIN_OLD"
              and r["structure"] != "SIM" and r["class"] not in analyze.NON_SCORED}
    effs = sorted({st for st, _ in cls_ok if (st, 1) in cls_ok and (st, 2) in cls_ok})
    B = R.C.BOOTSTRAP_RESAMPLES
    hb = cb.CallBootstrap([], "human", B, R.C.BOOTSTRAP_SEED, R.C.BOOTSTRAP_LEVEL, within="cell")
    num = {t: [0.0] * B for t in (1, 2)}
    den = {t: [0.0] * B for t in (1, 2)}
    n_eff = 0
    for st in effs:
        drop = frozenset(d.compromise_descriptive) if st == "SOT" else frozenset()
        common = set.intersection(*[{k[0] for k in analyze.human_contrast(H, st, (t,), "numbers", d, drop)["slices"]}
                                    for t in (1, 2)])
        if not common:
            continue
        per = {}
        for t in (1, 2):
            h = analyze.human_contrast(H, st, (t,), "numbers", d, drop, cats=common)
            m, hd = analyze.matched_contrast(h, recs, st, (t,), "numbers", d, drop, common)
            per[t] = (m, hd)
        if any(m is None or abs(hd) < 0.02 for m, hd in per.values()):
            continue
        n_eff += 1
        for t, (m, hd) in per.items():
            strata = {k: (tt, c) for k, tt, c in analyze._strata(H, st, "human", (t,), "numbers", None, d, drop,
                                                                  None, "backbone", common)[0] if tt and c}
            wsum, hrep = 0.0, [0.0] * B
            for k in m["slices"]:
                tt, c = strata[k]
                ta, ca = hb.arm(("T", st, k), tt), analyze.control_arm(hb, st, k, c, d)
                for b in range(B):
                    tv = ta[1][b] if ta[1] is not None else ta[0]
                    cv = ca[1][b] if ca[1] is not None else ca[0]
                    hrep[b] += len(tt) * (tv - cv)
                wsum += len(tt)
            sg = 1.0 if hd > 0 else -1.0
            for b in range(B):
                num[t][b] += sg * m["delta"]
                den[t][b] += sg * hrep[b] / wsum
    assert n_eff >= 3, n_eff
    folded = {t: [(analyze._fold(a / c) if c > 0 else None) for a, c in zip(num[t], den[t])] for t in (1, 2)}
    tiers = sorted(folded)
    mine = [(a - b if a is not None and b is not None else None) for a, b in zip(folded[tiers[0]], folded[tiers[-1]])]
    theirs = res["model_results"]["TWIN_OLD"]["resolution_reps"]["t1"]
    assert len(theirs) == B and all((x is None and y is None) or (x is not None and y is not None and abs(x - y) < 1e-9)
                                    for x, y in zip(mine, theirs)), "the pipeline's replicates differ"
    vals = sorted(v for v in mine if v is not None)
    assert len(vals) == B, "undefined replicates in a well-powered group"

    def pct(q):
        pos = q * (B - 1)
        lo = int(pos)
        return vals[lo] + (pos - lo) * (vals[min(lo + 1, B - 1)] - vals[lo])
    t1 = next(r for r in res["test_T1_rows"] if r["model"] == "TWIN_OLD")
    assert abs(t1["drop_lo"] - pct(0.025)) < 6e-4 and abs(t1["drop_hi"] - pct(0.975)) < 6e-4, \
        (t1["drop_lo"], t1["drop_hi"], pct(0.025), pct(0.975))


def test_r2_joint_bootstrap_human_side_varies_and_pairs_across_models():
    """Two identical deterministic models (every call its own grid point, so the call bootstrap cannot move them)
    in one family, one older and one newer: their trajectory difference is exactly zero on every resample (the
    human resamples are shared by both), so T5 reads flat with an interval of [0, 0]; their memorization
    interval still has width, which comes from the human side alone."""
    res, _ = _pack("A")
    t5 = next(r for r in res["test_T5_rows"] if r["model"] == "TWIN_NEW")
    assert t5["traj_lo"] == 0.0 and t5["traj_hi"] == 0.0 and t5["trajectory"].startswith("flat"), t5
    t1 = next(r for r in res["test_T1_rows"] if r["model"] == "TWIN_OLD")
    assert isinstance(t1["drop_lo"], float) and t1["drop_hi"] - t1["drop_lo"] > 0.05, t1
    reps = res["model_results"]["TWIN_OLD"]["fid_primary_reps"]
    assert reps and len(set(round(x, 12) for x in reps if x is not None)) > 50, "the human side does not vary"


def test_r2_human_bootstrap_matches_the_cluster_robust_interval():
    """Resampling the human choices within cells gives, for a pooled human effect, an interval as wide as the
    registered cluster-robust 95 percent interval (each synthetic participant makes one choice per cell)."""
    import call_bootstrap as cb
    _, H = _pack("A")
    d = analyze.Design.for_synth()
    for st in ("FRQ", "SOT", "MOT"):
        h = analyze.human_contrast(H, st, (1, 2, 3), "numbers", d)
        strata = analyze._strata(H, st, "human", (1, 2, 3), "numbers", None, d, (), None, "backbone", None)[0]
        hb = cb.CallBootstrap([], "human", 4000, 20260929, 0.95, within="cell")
        items = [(len(t), hb.arm(("T", st, k), t), analyze.control_arm(hb, st, k, c, d)) for k, t, c in strata if t and c]
        lo, hi = cb.interval(cb.combine(items, 4000), 0.95)
        ratio = (hi - lo) / (h["ci_hi"] - h["ci_lo"])
        assert 0.85 < ratio < 1.15, (st, ratio)


def test_r2_without_the_bootstrap_nothing_resolves():
    """bootstrap=False: every memorization reading is not resolved; a faithful model still routes to S1 with the
    set qualifier (rule (a)), and a retrieval-shaped model, whose estimate points to S2, is not
    resolved (rule (b))."""
    _, H = _pack("A")
    models = {"FAITHFUL_X": _exact_model("FAITHFUL_X", _planted),
              "PARROT_X": _exact_model("PARROT_X", lambda st, t, c: _planted(st, t, c) if t == 1 else 0.0)}
    tmp = _scratch("r2_no_bootstrap")
    saved = (analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR)
    try:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = tmp, os.path.join(tmp, "tests"), os.path.join(tmp, "figures")
        res = analyze.build_pack(H, models, human_rows_with_formats=H, human_rows_first_trial=H, mode="TEST",
                                 design=analyze.Design.for_synth(), bootstrap=False)
    finally:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = saved
    t1 = next(r for r in res["test_T1_rows"] if r["model"] == "FAITHFUL_X")
    assert t1["reading"].startswith(analyze.NOT_RESOLVED) and t1["drop_lo"] == "", t1
    route = {r["model"]: r for r in res["routing_rows"]}
    assert route["FAITHFUL_X"]["scenario"] == "S1" and analyze.S1_QUALIFIER == route["FAITHFUL_X"]["qualifier"], \
        route["FAITHFUL_X"]
    assert route["PARROT_X"]["scenario"] == "NOT_RESOLVED" and "S2" in route["PARROT_X"]["possible_scenarios"], \
        route["PARROT_X"]


def test_r2_synthetic_exact_prompts_are_deterministic():
    """consistency='exact': every prompt answers one option in all its draws, except at most one prompt per
    paraphrase that carries the remainder; the cell share is exact and each paraphrase is within one call."""
    recs = synth.gen_model("FAITHFUL", 200, random.Random(5), consistency="exact")
    from collections import defaultdict
    pts, cell, para = defaultdict(set), defaultdict(list), defaultdict(list)
    for r in recs:
        if r.get("prompting_mode") != "neutral" or r["format"] != "numbers":
            continue
        k = (r["structure"], r["category"], r["tier"])
        pts[k + (r["paraphrase_id"], str(r["position_order"]))].add(r["parsed_choice"])
        cell[k].append(r["parsed_choice"])
        para[k + (r["paraphrase_id"],)].append(r["parsed_choice"])
    mixed = defaultdict(int)
    for kk, labs in pts.items():
        if len(labs) > 1:
            mixed[kk[:4]] += 1
    assert mixed and max(mixed.values()) <= 2, max(mixed.values())       # at most the remainder prompts
    assert sum(1 for v in pts.values() if len(v) == 1) > 0.8 * len(pts), "most prompts are not deterministic"
    for k, labs in cell.items():
        exp = synth._exact_labels(k[0], len(labs), synth._planted_share("FAITHFUL", k[0], k[2], "numbers", k[1], 1.0))
        assert sorted(labs) == sorted(exp), k
        for p in (1, 2, 3):
            pl = para[k + (p,)]
            share = sum(1 for x in pl if x == "TARGET") / len(pl)
            cshare = sum(1 for x in labs if x == "TARGET") / len(labs)
            assert abs(share - cshare) <= 1.0 / len(pl) + 1e-12, (k, p, share, cshare)


def test_r2_arm_key_reused_for_other_rows_is_refused():
    """An arm key names one set of rows: another count, other ids with the same count, or other outcomes are
    refused (review note c); a participant with two choices in one cell is refused."""
    import call_bootstrap as cb
    b = cb.CallBootstrap([], "human", 100, 1, 0.95, within="cell")
    b.arm(("T", "FRQ", "k"), [("a", 1), ("b", 0)])
    b.arm(("T", "FRQ", "k"), [("a", 1), ("b", 0)])
    for other in ([("a", 1), ("b", 0), ("c", 1)], [("a", 1), ("z", 0)], [("a", 1), ("b", 1)]):
        try:
            b.arm(("T", "FRQ", "k"), other)
        except ValueError:
            continue
        raise AssertionError(f"an arm key was reused for different rows: {other}")
    try:
        b.arm(("T", "FRQ", "k2"), [("a", 1), ("a", 0), ("b", 1)])
    except ValueError:
        pass
    else:
        raise AssertionError("a participant with two choices in one cell was resampled as two participants")
    g = cb.CallBootstrap([dict(record_id="r1"), dict(record_id="r2")], "m", 10, 1, 0.95)
    g.arm(("T", "x"), [("r1", 1), ("r1", 0)])       # the call bootstrap has no such premise (ids are calls)


def test_r2_sensitivity_rereadings_keep_the_undershoot_guard():
    """The memorization re-readings (in-limit, and adjusted) never read an invented-tier overshoot as steep: matching on the published tier and overshooting threefold on the invented tier combines to a
    large drop, which the guard sends to 'not steep'."""
    d = analyze.Design.from_stimuli()
    cells = []
    for (cat, tier, fmt), b in d.baseline_pct.items():
        if fmt != "numbers" or cat in d.price_free:
            continue
        for st in ("FRQ", "RNG", "SOT", "SYM", "MOT"):
            cells.append(dict(category=cat, tier=tier, structure=st, human_pp=10.0,
                              model_pp=(30.0 if tier == 3 else 10.0), w=350, budget_target=False))
    s = analyze.test_T1_sensitivity(cells, d, dict(reading="x"))
    assert not s["restricted_reading"].startswith("steep"), s["restricted_reading"]
    assert not s["adjusted_reading"].startswith("steep"), s["adjusted_reading"]
    under = [dict(c, model_pp=(0.0 if c["tier"] == 3 else 10.0)) for c in cells]
    s2 = analyze.test_T1_sensitivity(under, d, dict(reading="x"))
    assert s2["restricted_reading"].startswith("steep") and s2["adjusted_reading"].startswith("steep"), s2


# ---- rule 4 (F10): the phantom read as retrieval ------------------------------------------------------
def test_r2_phantom_retrieval_reading():
    """Where the human phantom fails (planted null), a model phantom larger than 3 points in the phantom's
    direction reads as retrieval of a described regularity; exactly 3 points, or 5 points the other way, do not.
    OVER against a replicated human phantom keeps its reading."""
    res, _ = _pack("A")
    assert res["criterion"]["PHT"]["replicated"] is False
    rows = {r["model"]: r for r in res["effect_class_rows"] if r["effect"] == "PHT"}
    assert "larger than 3 points where the human phantom failed" in rows["PHANTOM_RECITER"]["over_reading"], rows["PHANTOM_RECITER"]
    for m in ("PHANTOM_3PT", "PHANTOM_REVERSED", "REASONING_PAIR"):
        assert "phantom" not in rows[m]["over_reading"], (m, rows[m]["over_reading"])
    route = {r["model"]: r for r in res["routing_rows"]}
    assert "PHT=human-null (exits fidelity scoring); model shows an effect without a human counterpart; " \
           + analyze.RETRIEVAL_READING in route["PHANTOM_RECITER"]["per_effect_accounts"], route["PHANTOM_RECITER"]
    assert analyze.RETRIEVAL_READING not in route["PHANTOM_REVERSED"]["per_effect_accounts"]
    criterion = {st: dict(replicated=True) for st in analyze.EFFECTS}
    acc = analyze.attribute_effect_accounts("m", [], {}, criterion, effect_classes={"PHT": "OVER"}, pooled={"PHT": (9.0, 3.0)})
    assert analyze.RETRIEVAL_READING in acc["PHT"], acc


# ---- rule 5 (F7): effects below the first-trial floor are descriptive ------------------------------------
def test_r2_effects_below_the_first_trial_floor_are_descriptive():
    brk = synth.gen_human(700, random.Random(22), icc=0.10, published_n_per_tier=350, first_trial_break=True)
    models = {"FAITHFUL_F": _exact_model("FAITHFUL_F", _planted)}
    tmp = _scratch("r2_floor_pack")
    saved = (analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR)
    try:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = tmp, os.path.join(tmp, "tests"), os.path.join(tmp, "figures")
        res = analyze.build_pack(brk, models, human_rows_with_formats=brk, human_rows_first_trial=brk, mode="TEST",
                                 design=analyze.Design.for_synth())
    finally:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = saved
    g = res["criterion"]
    floor = [st for st in analyze.EFFECTS if g[st]["replicated"] and not g[st]["confirmatory"]]
    assert res["numbers"]["human.first_trial.fallback_triggered"] is True and floor, floor
    assert res["numbers"]["human.first_trial.below_floor_effects"] == ";".join(sorted(floor))
    ec = {r["effect"]: r for r in res["effect_class_rows"]}
    for st in floor:
        assert ec[st]["class"] == analyze.DESCRIPTIVE_FLOOR and ec[st]["descriptive_class"] in analyze.SCORED_CLASSES, ec[st]
        assert all(r["class"] == analyze.DESCRIPTIVE_FLOOR for r in res["fidelity_rows"] if r["structure"] == st)
    conf = [st for st in analyze.REGULARITY_EFFECTS if g[st]["confirmatory"]]
    overall = res["agreement_rows"][0]["class"]
    assert overall == analyze.majority_class([ec[st]["class"] for st in conf if st in ec]), overall
    mr = res["model_results"]["FAITHFUL_F"]
    assert all(mr["fidelity_by_struct"].get(st) is None for st in floor), mr["fidelity_by_struct"]
    t2 = {r["structure"]: r for r in res["test_T2_rows"]}
    assert all(t2[st]["reading"].startswith(analyze.DESCRIPTIVE_FLOOR) for st in floor if st in t2)
    assert all(not any(c["structure"] == st for c in mr["scored_cells"]) for st in floor)


# ---- rule 14: the printed table ---------------------------------------------------------------------
def test_i2_printed_table_is_reader_facing():
    import print_constants as P
    text = P.build()
    wa = text.split("## Where each row lives")[0]
    for word in ("regularity effect", "regularity-violating", "arguable", "knows-it test", "Step 0a", "Step 0b",
                 "True", "False", "—"):
        assert word not in wa, f"house word or code value in the printed table: {word!r}"
    for name, step in (("COMPROMISE_TARGET_MAX_BASELINE_PCT", "Step 1"), ("HARD_LIMIT_LO_PCT", "Step 1"),
                       ("HARD_LIMIT_HI_PCT", "Step 1")):
        import registered_constants as R
        assert R.MEANING[name][0].startswith(step), (name, R.MEANING[name][0])
    assert "| Step 1, stimulus handling | Yes |" in wa and "| Re-running the model calls | 95 percent |" in wa
    assert "removes seven calibration pairs" in wa and "televisions" not in wa, "the deviation row is not the seven"
    assert "not resolved" in wa, "the resolution rule is missing from the printed table"
    # the authors' terminology rule (2026-09-29): no 'arm', 'backbone' or 'top-up' anywhere a reader looks
    import re
    reader = wa + text.split("## Rules stated with the constants")[1]
    for pat in (r"\barms?\b", r"backbone", r"top-up", r"numeric backbone"):
        assert not re.search(pat, reader, re.I), f"in-house term in the printed table or its rules: {pat!r}"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
ORDER = [
    "test_reversed_human_effect_is_not_replicated",
    "test_direction_requirement_holds_even_with_a_two_sided_bayes_factor",
    "test_bayes_factor_is_directional_half_normal",
    "test_similarity_is_outside_the_regularity_holm_family",
    "test_first_trial_rule_false_alarm_at_or_below_5_percent", "test_first_trial_rule_on_rows_null_quiet_break_fires",
    "test_fallback_switches_the_benchmark_end_to_end", "test_simulation_estimator_matches_the_pipeline_estimator",
    "test_phantom_equivalence_needs_the_interval_inside_the_band",
    "test_format_interaction_detects_a_planted_interaction",
    "test_compromise_precondition_by_option_identity", "test_compromise_descriptive_slices_leave_the_confirmatory_contrast",
    "test_matched_control_is_coded_against_the_effects_target", "test_similarity_is_a_relative_share",
    "test_compromise_extreme_label_from_ingest_is_excluded", "test_price_free_categories_stay_out_of_the_backbone_gate",
    "test_ceiling_rule_is_per_binary_cell", "test_model_similarity_reads_the_runners_placement_field",
    "test_memorization_sensitivity_adjusts_for_baseline", "test_every_constant_has_a_meaning_and_prints",
    "test_reversed_ladder_routes_by_recognition", "test_effect_without_a_human_counterpart",
    "test_s7_needs_four_of_the_six_non_similarity_effects", "test_model_level_account_needs_four_agreeing_effects",
    # the registered rules
    "test_i2_small_reversal_is_low_not_high", "test_i2_over_class_and_tie_rule",
    "test_i2_over_on_the_phantom_reads_as_retrieval", "test_i2_over_on_the_published_tier_reads_as_retrieval_end_to_end",
    "test_i2_pooled_model_effect_uses_the_human_slice_weights", "test_i2_effect_class_is_on_the_pooled_estimate_end_to_end",
    "test_i2_knows_it_versus_shows_it_reads_the_pooled_effect",
    "test_i2_folded_fidelity_counts_overshoot_like_undershoot",
    "test_i2_bootstrap_resamples_within_grid_points", "test_i2_bootstrap_is_reproducible_and_describes_the_draws",
    "test_i2_prompt_sensitivity_flags_a_sign_change_across_paraphrases",
    "test_i2_T4_has_no_registered_reading_when_a_human_format_effect_is_under_2_points",
    "test_i2_T4_is_also_reported_on_the_picture_order",
    "test_i2_memorization_sensitivity_adjusts_for_decoy_target",
    "test_i2_positive_control_is_the_premium_target_frequency_decoy",
    "test_i2_failed_positive_control_makes_its_row_and_the_pattern_tests_uninformative",
    "test_i2_similarity_topup_check_rule", "test_i2_topup_check_switches_the_similarity_benchmark_to_the_backbone",
    "test_i2_deviation_set_is_the_registered_seven_by_the_point_rule", "test_i2_rerun_rule",
    "test_i2_compromise_power_runs_on_the_confirmatory_cells", "test_i2_printed_table_is_reader_facing",
    # after the independent review
    "test_i2_review_directional_readings_need_an_undershoot", "test_i2_review_exact_three_point_reversal_is_low",
    "test_i2_review_no_room_slice_leaves_both_sides_of_the_class", "test_i2_review_topup_rows_leave_the_first_trial_check",
    "test_i2_review_T4_numbers_undefined_blocks_the_reading",
    "test_i2_review_similarity_placements_share_one_control_resampling",
    "test_i2_review_published_tier_over_reading_is_read_from_the_tier_class",
    "test_i2_review_only_the_primary_arm_is_confirmatory_and_T5_reads_the_reasoning_arm",
    "test_i2_review_failed_control_reaches_the_secondary_readings", "test_i2_review_every_category_is_reported",
    # the second revision
    "test_r2_T1_resolution_boundaries", "test_r2_T3_T4_T5_resolution_boundaries",
    "test_r2_interval_is_conservative_about_undefined_replicates",
    "test_r2_group_fold_reps_recompute_the_point_formula", "test_r2_pipeline_replicates_equal_an_independent_recomputation",
    "test_r2_sensitivity_rereadings_keep_the_undershoot_guard",
    "test_r2_joint_bootstrap_human_side_varies_and_pairs_across_models",
    "test_r2_human_bootstrap_matches_the_cluster_robust_interval", "test_r2_without_the_bootstrap_nothing_resolves",
    "test_r2_synthetic_exact_prompts_are_deterministic", "test_r2_arm_key_reused_for_other_rows_is_refused",
    "test_r2_phantom_retrieval_reading", "test_r2_effects_below_the_first_trial_floor_are_descriptive",
    # the registered rules (a) to (d)
    "test_r3_S1_needs_no_flat_memorization_reading", "test_r3_account_routes_are_strict",
    "test_r3_comparison_options_of_the_router", "test_r4_kept_members_reproduce_the_registered_readings",
    "test_r4_guard_leaves_S1_possible",
    "test_r5_format_test_is_descriptive_and_reason_construction_reads_the_ladder",
    "test_r5_memorization_sensitivity_is_paired_and_one_step",
    "test_r3_knows_without_shows_is_resolved_against_intervals",
    "test_r3_pipeline_routes_the_faithful_models_to_S1_with_the_qualifier",
]


def main():
    results = []
    t0 = time.time()
    for name in ORDER:
        fn = globals()[name]
        t = time.time()
        try:
            fn()
            results.append((name, True, "", time.time() - t))
        except Exception as e:  # noqa: BLE001 -- a failing test of any kind is a FAIL
            msg = f"{type(e).__name__}: {e}".replace("\n", " ")[:300]
            results.append((name, False, msg, time.time() - t))
    lines = ["# Tests of the registered analysis (test_analysis.py)", "",
             f"(quick={QUICK}. runtime {round(time.time() - t0, 1)}s.)", "",
             "| test | result | seconds | detail |", "|---|---|---|---|"]
    for name, ok, msg, sec in results:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {sec:.1f} | {msg} |")
    allok = all(ok for _, ok, _, _ in results)
    lines += ["", f"## OVERALL: {'ALL PASS' if allok else 'FAILURES: ' + str(sum(1 for r in results if not r[1]))}"]
    text = "\n".join(lines) + "\n"
    print(text)
    if "--no-write" not in sys.argv:
        open(os.path.join(HERE, "ANALYSIS_TEST_REPORT.md"), "w", encoding="utf-8", newline="\n").write(text)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
