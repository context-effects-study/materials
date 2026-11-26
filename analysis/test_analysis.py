"""test_analysis.py: tests of the registered analysis, one per rule it applies.

Each test builds a small data set in which one rule decides the outcome (for example the direction
requirement of the human criterion, the Holm families, the fidelity classes and their tie rule, the
first-choice check, the phantom reading, the positive control, the interval rule of the tests of the three
accounts and the re-run rule) and checks that analyze.py applies the rule exactly as the Analysis Plan states it. Test
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
    """When the check fires inside build_pack, the criterion must read the FIRST-TRIAL estimates of ALL SEVEN effects and
    apply the replication criterion to them with no size screen (2026-11-25, the editor's read, item 2.9: the 8-point
    floor selected effects on their observed size). Planted: a replicating effect under 8 points in first choices
    (similarity here), which the old floor left out and the new rule keeps confirmatory."""
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
    firsts = [r for r in brk if int(r["trial_position"]) == 1]
    for st in analyze.EFFECTS:      # every benchmark switches, not only the effect whose estimates diverged
        first = analyze.human_contrast(firsts, st)
        assert abs(res["criterion"][st]["delta_pp"] - first["delta"] * 100) < 1e-9, f"{st}: the criterion did not switch"
    for st, g in res["criterion"].items():
        assert g["confirmatory"] == g["replicated"], st
    small = [st for st, g in res["criterion"].items() if g["replicated"] and g["delta_pp"] < 8.0]
    assert small, "the planted data must hold a replicating effect under 8 points, or the test proves nothing"
    assert res["numbers"]["human.first_trial.benchmark"] == "first choices, all seven effects"


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
# Defect 10 and the three added rules (re-aimed at the simple rule of 2026-11-02)
# ------------------------------------------------------------------------------------------------
def test_reversed_ordering_is_described_and_decides_nothing():
    """A model that misses the effects whose sets give an argument and matches those that give none has a reversed
    ordering: T3 describes it (no account is attached, no recognition is read), and decision tree B routes the model
    by its signatures alone: it does not match people, and with the decoy named where it misses the effect rational
    override is present (S5); without the decoy named, every signature is absent (S6)."""
    fid = {"FRQ": 0.02, "RNG": 0.02, "SOT": -1.0, "MOT": 0.95, "SYM": 0.9}
    t3 = analyze.test_T3_ladder(fid)
    assert t3["reading"].startswith("reversed ladder") and t3["reversed"], t3
    assert "attribution" not in t3 and "missed_effects" not in t3, t3
    classes = {"FRQ": "LOW", "RNG": "LOW", "SOT": "ANTI", "SYM": "HIGH", "MOT": "HIGH"}
    named = analyze.route_model(_T1_FLAT, "T", t3, "LOW", classes, t2_override=True)
    unnamed = analyze.route_model(_T1_FLAT, "F", t3, "LOW", classes)
    assert named[1] == "S5" and unnamed[1] == "S6", (named, unnamed)
    # a peaked middle (compromise faithful, extremity faithful, attraction missed) is not a reversal.
    t3_mid = analyze.test_T3_ladder({"FRQ": 0.0, "RNG": 0.0, "SOT": 1.0, "MOT": 0.9})
    assert not t3_mid["reading"].startswith("reversed"), t3_mid
    # the registered decline still reads as a decline.
    assert analyze.test_T3_ladder({"FRQ": 1.0, "RNG": 1.0, "SOT": 0.45, "MOT": 0.2})["reading"].startswith("declines")


def test_effect_without_a_human_counterpart():
    assert analyze.gate_exit_class(0.05) == "no-human-counterpart"
    assert analyze.gate_exit_class(-0.05) == "no-human-counterpart"
    assert analyze.gate_exit_class(0.02) == "excluded(criterion-exit)"


def test_human_effects_fail_needs_four_of_the_six_non_similarity_effects():
    four = synth.gen_human(700, random.Random(51), icc=0.10, null_effects={"RNG", "SYM", "MOT"})
    three_plus_sim = synth.gen_human(700, random.Random(52), icc=0.10, null_effects={"RNG", "SYM", "SIM"})
    assert analyze.human_gate(four)[4] is True
    g3 = analyze.human_gate(three_plus_sim)
    assert g3[0]["SIM"]["replicated"] is False and g3[4] is False, "similarity counted toward HUMAN_FAIL"


def test_no_account_is_attached_effect_by_effect():
    """The simple rule reports, for each effect, its class (or that it fails in people, with an effect without a
    human counterpart when the model shows one) and whether the model named the decoy; no account is attached."""
    criterion = {st: dict(replicated=st not in ("PHT", "SIM")) for st in analyze.EFFECTS}
    classes = {"FRQ": "HIGH", "RNG": "LOW", "SOT": "ANTI", "SYM": "OVER", "MOT": "PARTIAL"}
    t2_per = {"FRQ": dict(knows=True), "RNG": dict(knows=False), "SOT": dict(knows=True), "SYM": dict(knows=False)}
    cls, named = analyze.per_effect_report(criterion, classes, t2_per, no_counterpart={"PHT"})
    assert cls == {"FRQ": "HIGH", "RNG": "LOW", "SOT": "ANTI", "SYM": "OVER", "MOT": "PARTIAL",
                   "PHT": "fails in people, and the model shows an effect without a human counterpart",
                   "SIM": "fails in people"}, cls
    assert named == {"FRQ": "yes", "RNG": "no", "SOT": "yes", "SYM": "no", "MOT": "not in the test",
                     "PHT": "not in the test", "SIM": "not in the test"}, named
    for retired in ("attribute_effect_accounts", "model_level_account", "route_resolved", "S1_QUALIFIER",
                    "ARGUMENT_OVERRIDE", "QUESTIONS", "answer_questions", "_three_state"):
        assert not hasattr(analyze, retired), f"a retired part of the old rule is still in the code: {retired}"
    assert not hasattr(analyze.RC, "MODEL_ACCOUNT_MIN_AGREE"), "the four-of-six account rule is still registered"


# ================================================================================================
# the registered rules
# ================================================================================================
def _exact_model(key, eff, n=120, family=None, bin_share=None, arm=None, id_prefix=None, generation="new",
                 one_call_per_point=False, reasoning_mode=None):
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
                    if reasoning_mode is not None:
                        rec["reasoning_mode"] = reasoning_mode
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
                  # tree B (2026-11-03): matches people and names the decoys whose effects it shows (S2)
                  "KNOWN": [dict(r, model_key="KNOWN") for r in
                            synth.gen_model("CONVERGE_NEW", 120, random.Random(76), noise="exact")],
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
    elif name == "POOL":
        # the roster of 2026-11-24: a family with two older and two newer models. Pooled, the older generation has
        # 0.5 of the human size and the newer 0.9 (a rise of 0.4); among the models that switch reasoning off
        # (POOL_OLD_A and POOL_NEW_B, both 0.4) there is no difference. A second family has newer models only.
        H = synth.gen_human(400, random.Random(71), icc=0.0, sim_topup_participants=300)
        def scaled(k):
            return lambda st, t, c: k * _planted(st, t, c)
        spec = {"POOL_OLD_A": (0.4, "old", "off"), "POOL_OLD_B": (0.6, "old", "lowest"),
                "POOL_NEW_A": (1.4, "new", "lowest"), "POOL_NEW_B": (0.4, "new", "off"),
                "SOLO_NEW_A": (1.0, "new", "off"), "SOLO_NEW_B": (0.9, "new", "off"),
                # review finding 5.1: an older model with no reasoning mode and a newer one with reasoning off
                "NA_OLD": (0.4, "old", "not_applicable"), "NA_NEW": (0.8, "new", "off")}
        fam = {"POOL": "famPOOL", "SOLO": "famSOLO", "NA": "famNA"}
        models = {k: _exact_model(k, scaled(f), family=fam[k.split("_")[0]],
                                  generation=g, one_call_per_point=True, reasoning_mode=rm)
                  for k, (f, g, rm) in spec.items()}
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
    """An OVER phantom against a replicated human phantom, and an OVER published tier, read as consistent with
    retrieval of a described regularity; an OVER effect other than the phantom, on a tier other than the published
    one, carries no such reading (reported by its class)."""
    R = analyze.over_readings
    assert R("PHT", "OVER", True, 0.09, "HIGH") == ["OVER on the phantom: " + analyze.RETRIEVAL_READING]
    assert R("FRQ", "OVER", True, 0.20, "HIGH") == []
    assert R("FRQ", "HIGH", True, 0.10, "OVER") == ["OVER on the published tier: " + analyze.RETRIEVAL_READING]
    assert R("PHT", "OVER", False, 0.09, None) != R("PHT", "OVER", True, 0.09, None)


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
    assert pc["failed"] == ["FRQ"] and pc["frq_premium"]["n_strata"] == 1, pc
    assert pc["frq_premium"]["ci_lo_pp"] < 0 < pc["frq_premium"]["ci_hi_pp"], pc


def test_i2_failed_positive_control_makes_its_row_and_the_pattern_tests_uninformative():
    res, _ = _pack("B")
    assert res["failed_controls"] == ["FRQ"]
    frq = [r for r in res["fidelity_rows"] if r["model"] == "FAITHFUL" and r["structure"] == "FRQ"]
    assert frq and all(r["class"] == analyze.UNINFORMATIVE for r in frq), [r["class"] for r in frq]
    ec = next(r for r in res["effect_class_rows"] if r["model"] == "FAITHFUL" and r["effect"] == "FRQ")
    assert ec["class"] == analyze.UNINFORMATIVE
    for rows, key in ((res["test_T1_rows"], "reading"), (res["test_T3_rows"], "reading"),
                      (res["test_T4_rows"], "reading")):
        r = next(x for x in rows if x["model"] == "FAITHFUL")
        assert r[key].startswith("uninformative"), (key, r[key])
    fam = synth.MODEL_ARCHETYPES["FAITHFUL"]["family"]
    r = next(x for x in res["test_T5_rows"] if x["family"] == fam)
    assert r["trajectory"].startswith("uninformative"), r["trajectory"]
    t2 = next(r for r in res["test_T2_rows"] if r["model"] == "FAITHFUL" and r["structure"] == "FRQ")
    assert t2["reading"].startswith("uninformative")
    route = next(r for r in res["routing_rows"] if r["model"] == "FAITHFUL")
    # tree B: the failed control leaves T1 and T3 not judged, which does not block a match; this model matches people
    # on the other effects with no failure present, so it reaches S1
    assert (route["scenario"] == "S1" and route["matches_people"] == "yes"
            and route["positive_controls"].startswith("failed")
            and route["signatures"].startswith("S3=not judged;S4=not judged;S5=")), route


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
    t3 = analyze.test_T3_ladder(fid, {"FRQ": 2.5, "RNG": 2.5, "SOT": 2.5, "MOT": 1.0})
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
    t5 = next(r for r in res["reasoning_rows"] if r["model"] == "REASONING_PAIR")
    assert t5["reasoning_reading"].startswith("reasoning-on lowers fidelity"), t5
    # the reasoning comparison is a result for one model, reported beside its conclusion
    route = next(r for r in res["routing_rows"] if r["model"] == "REASONING_PAIR")
    assert route["reasoning"].startswith("reasoning-on lowers fidelity"), route["reasoning"]


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
    ok = T3(fid, None, ci=dict(top_minus_bottom=(0.20, 0.80), bottom_minus_middle=(-0.7, -0.1)), resolve=True)
    assert ok["reading"].startswith("declines"), ok
    op = T3(fid, None, ci=dict(top_minus_bottom=(0.10, 0.80), bottom_minus_middle=(-0.7, -0.1)), resolve=True)
    assert op["reading"].startswith(analyze.NOT_RESOLVED) and op["p_declines"] == "U", op
    flat3 = {"FRQ": 0.9, "RNG": 0.9, "SOT": 0.9, "MOT": 0.95}
    assert T3(flat3, None, ci=dict(top_minus_bottom=(-0.25, 0.20), bottom_minus_middle=(-0.2, 0.3)),
              resolve=True)["reading"].startswith("flat")
    assert T3(flat3, None, ci=dict(top_minus_bottom=(-0.35, 0.20), bottom_minus_middle=(-0.2, 0.3)),
              resolve=True)["reading"].startswith(analyze.NOT_RESOLVED)
    rev = {"FRQ": 0.1, "RNG": 0.1, "SOT": 0.1, "MOT": 0.9}
    r = T3(rev, None, ci=dict(top_minus_bottom=(-1.0, -0.5), bottom_minus_middle=(0.5, 1.0)), resolve=True)
    assert r["reversed"] and r["p_reversed"] == "T" and r["p_declines"] == "F", r     # described; a decline set out
    r = T3(rev, None,
           ci=dict(top_minus_bottom=(-1.0, -0.5), bottom_minus_middle=(0.05, 1.0)), resolve=True)
    assert not r["reversed"] and r["p_reversed"] == "U" and r["reading"].startswith(analyze.NOT_RESOLVED), r
    # every reading set out: still not resolved, described, all three states F
    r = T3({"FRQ": 1.0, "RNG": 1.0, "SOT": 0.9, "MOT": 0.8}, None,
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
# an interval that rules a steep fall out without resolving the flat reading: question 2 is answered no
_T1_NO_FALL_OPEN_FLAT = dict(reading="not resolved: x", point_reading="non-monotone or shallow: x", p_steep="F",
                             p_flat="U", resolved=False)
_T3_FLAT = dict(reading="flat: x", point_reading="flat: x", reversed=False, point_reversed=False,
                p_declines="F", p_reversed="F", p_flat="T", resolved=True)
_T3_DECL = dict(_T3_FLAT, reading="declines down the ladder -> x", point_reading="declines down the ladder -> x",
                p_declines="T", p_flat="F", resolved=True)
_T3_OPEN_DECL_PT = dict(_T3_FLAT, reading="not resolved: x", point_reading="declines down the ladder -> x",
                        p_declines="U", p_flat="F", resolved=False)
# an argument-strength reading left open whose estimate is flat (it points to no decline)
_T3_OPEN_FLAT_PT = dict(_T3_FLAT, reading="not resolved: x", point_reading="flat: x", p_declines="U", p_flat="U",
                        resolved=False)
_T3_REV = dict(_T3_FLAT, reading="reversed ladder: x", point_reading="reversed ladder: x", reversed=True,
               point_reversed=True, p_reversed="T", p_flat="F")
_UNINF = "uninformative (positive control failed): x"
_ALL_HIGH = {"FRQ": "HIGH", "RNG": "HIGH", "SOT": "HIGH", "SYM": "HIGH", "MOT": "HIGH"}


def _route(t1=None, t3=None, overall="HIGH", t2_state="F", classes=None, **kw):
    """The simple router on hand-made test results (defaults: no fall, no decline, nothing named, all HIGH)."""
    if classes is None:
        classes = dict(_ALL_HIGH) if overall == "HIGH" else {st: overall for st in _ALL_HIGH}
    return analyze.route_model(t1 or _T1_FLAT, t2_state, t3 or _T3_FLAT, overall, classes, **kw)


def test_tree_b_step_1_match_needs_the_classes_and_no_failure_present():
    """Step 1 of decision tree B, with the authors' rule of 2026-11-03 ("Match + no failure present"): the model matches
    people when its overall class is HIGH, no effect is classed LOW or ANTI (PARTIAL and OVER effects are allowed),
    and none of the three failure signatures is present. A HIGH model with a resolved decline or a resolved steep fall
    does not match and is reported by its signatures; a signature that is not resolved or not judged does not block
    the match."""
    none_present = {"S3": "absent", "S4": "not resolved", "S5": "not judged"}
    assert analyze.classes_match("HIGH", _ALL_HIGH)
    assert analyze.classes_match("HIGH", dict(_ALL_HIGH, MOT="PARTIAL", SYM="OVER"))
    assert not analyze.classes_match("HIGH", dict(_ALL_HIGH, SOT="ANTI"))
    assert not analyze.classes_match("HIGH", dict(_ALL_HIGH, SOT="LOW"))
    for cls in ("OVER", "PARTIAL", "LOW", "ANTI"):
        assert not analyze.classes_match(cls, {st: cls for st in _ALL_HIGH}), cls
    assert analyze.matches_people("HIGH", _ALL_HIGH, none_present, [])
    for code in ("S3", "S4", "S5"):
        assert not analyze.matches_people("HIGH", _ALL_HIGH, dict(none_present, **{code: "present"}), []), code
    assert not analyze.matches_people("HIGH", _ALL_HIGH, none_present, ["S4"])
    assert _route()[1] == "S1"
    # a HIGH model with a resolved decline down the argument-strength ordering is NOT S1: it is S4
    b, s, poss = _route(t3=_T3_DECL)
    assert s == "S4" and poss == ["S4"] and "a failure is present" in b, (b, s, poss)
    assert _route(t1=_T1_STEEP)[1] == "S3"
    assert _route(t1=_T1_STEEP, t3=_T3_DECL)[1] == "S3+S4"
    assert _route(t2_state="T", t2_override=True)[1] == "S5"
    # open tests whose estimates point to no failure do not block a match
    b, s, poss = _route(t1=_T1_OPEN_FLAT_PT, t3=_T3_OPEN_FLAT_PT, t2_state="U")
    assert s == "S1" and poss == ["S1"] and "matches people" in b, (b, s, poss)
    assert _route(classes=dict(_ALL_HIGH, MOT="PARTIAL"))[1] == "S1"
    assert _route(classes=dict(_ALL_HIGH, SOT="ANTI"))[1] == "S6"
    assert _route(overall="OVER", classes={st: "OVER" for st in _ALL_HIGH})[1] == "S6"
    assert analyze.MATCH_CONCLUSIONS == ("S1", "S2") and analyze.SCENARIO_NAMES["S1"] == "High fidelity"


def test_tree_b_s2_matches_people_and_names_the_decoy():
    """A model that matches people and names the decoy on at least one effect is S2, a known effect reproduced; the test
    cannot tell whether it reproduces the effect deliberately or as learned. Settled for tree B: naming the decoy on an
    effect the model does not show, at the point and not resolved as a failure, is also S2, because S1 needs every
    effect shown without naming the decoy; a resolved knows-without-shows is the rational-override failure, so such a
    model does not match people (S5)."""
    b, s, poss = _route(t2_known_shown=True)
    assert s == "S2" and poss == ["S2"] and "names the decoy" in b, (b, s, poss)
    assert _route(t2_override=True, t2_state="F")[1] == "S2"             # the point reading decides within a match
    # an open override that the point estimate shows (named, not shown) points to rational override: no match
    assert _route(t2_override=True, t2_state="U")[1:] == (analyze.NOT_RESOLVED_SCENARIO, ["S5", "S2"])
    assert _route(t2_override=True, t2_state="T")[1] == "S5"             # a present override blocks it
    assert _route(t1=_T1_STEEP, t2_known_shown=True)[1] == "S3"          # a present fall blocks it
    assert _route(classes=dict(_ALL_HIGH, SOT="ANTI"), t2_known_shown=True)[1] != "S2"   # no match, no S2
    assert analyze.SCENARIO_NAMES["S2"] == "Matches people and names the decoy"


def test_tree_b_a_test_that_points_to_a_failure_blocks_the_match():
    """the authors' second rule of 2026-11-03 ("No failure points to it"): a model matches people only when no test shows
    or points to a failure. A signature that is not resolved points to its failure when its estimate passes the
    cutoff: T1 an estimated steep fall, T3 an estimated decline (each above 0.30), rational override the manipulation
    known, by the point estimate, on an effect the model does not show. A model blocked this way goes to step 2 and is
    not resolved, with that signature still possible and then the match it would reach (S1 or S2); a model whose
    classes do not match keeps S6 at the end of the list. A signature that is not judged points nowhere."""
    # a HIGH model whose T3 decline is estimated above 0.30 but not resolved is not S1
    b, s, poss = _route(t3=_T3_OPEN_DECL_PT)
    assert (s == analyze.NOT_RESOLVED_SCENARIO and poss == ["S4", "S1"]
            and "suggested: reason-based choice" in b), (b, s, poss)
    assert _route(t1=_T1_OPEN_STEEP_PT)[1:] == (analyze.NOT_RESOLVED_SCENARIO, ["S3", "S1"])
    assert _route(t1=_T1_OPEN_STEEP_PT, t3=_T3_OPEN_DECL_PT)[1:] == (analyze.NOT_RESOLVED_SCENARIO, ["S3", "S4", "S1"])
    assert _route(t3=_T3_OPEN_DECL_PT, t2_known_shown=True)[1:] == (analyze.NOT_RESOLVED_SCENARIO, ["S4", "S2"])
    assert _route(t2_state="U")[1] == "S1"                            # open override, nothing named at the point
    assert _route(t3=_T3_OPEN_DECL_PT, overall="PARTIAL")[1:] == (analyze.NOT_RESOLVED_SCENARIO, ["S4", "S6"])
    assert _route(t1=dict(_T1_OPEN_STEEP_PT, reading=_UNINF))[1] == "S1"   # not judged: not interpreted
    st = analyze.signature_states(_T1_OPEN_STEEP_PT, "U", _T3_OPEN_FLAT_PT)
    assert analyze.pointing_signatures(st, _T1_OPEN_STEEP_PT, _T3_OPEN_FLAT_PT, True) == ["S3", "S5"]
    assert analyze.pointing_signatures(st, _T1_OPEN_STEEP_PT, _T3_OPEN_FLAT_PT, False) == ["S3"]
    st = analyze.signature_states(_T1_STEEP, "F", _T3_DECL)          # resolved signatures are present, not pointing
    assert analyze.pointing_signatures(st, _T1_STEEP, _T3_DECL, True) == []


def test_tree_b_each_failure_signature_alone():
    """Step 2, for a model that does not match people: each signature alone is the conclusion. Rational override needs a
    resolved knows-without-shows on at least one effect and, under tree B, no LOW or ANTI overall class: a model that
    is HIGH overall (with or without a reversed effect), or PARTIAL or OVER overall, also shows it."""
    assert _route(t1=_T1_STEEP, overall="PARTIAL")[1:] == ("S3", ["S3"])
    assert _route(t3=_T3_DECL, overall="PARTIAL")[1:] == ("S4", ["S4"])
    for overall, classes in (("LOW", None), ("ANTI", None), ("PARTIAL", None), ("OVER", None),
                             ("HIGH", dict(_ALL_HIGH, SOT="ANTI")), ("HIGH", None)):
        b, s, poss = _route(overall=overall, classes=classes, t2_state="T", t2_override=True)
        assert s == "S5" and poss == ["S5"] and "rational override present" in b, (overall, b, s, poss)
    # the resolved state decides, not the point flag
    assert _route(overall="PARTIAL", t2_state="F", t2_override=True)[1] == "S6"
    assert _route(overall="PARTIAL", t2_state=None, t2_override=True)[1] == "S5"      # no state: the point flag
    assert _route(overall="PARTIAL", t2_state=None, t2_override=False)[1] == "S6"
    # a reversed ordering is no signature
    assert _route(t3=_T3_REV, overall="PARTIAL")[1] == "S6"
    # without a stored state the reading text decides
    assert _route(t1=dict(reading="steep: x"), overall="LOW")[1] == "S3"
    assert _route(t1=dict(reading="flat: x"), overall="LOW")[1] == "S6"


def test_tree_b_several_signatures_at_once():
    """There is no order among the signatures and no stop: every present signature is reported, joined in the order
    S3, S4, S5, and the name joins their names."""
    cases = [(dict(t1=_T1_STEEP, t3=_T3_DECL), "S3+S4"), (dict(t1=_T1_STEEP, t2_state="T"), "S3+S5"),
             (dict(t3=_T3_DECL, t2_state="T"), "S4+S5"), (dict(t1=_T1_STEEP, t3=_T3_DECL, t2_state="T"), "S3+S4+S5")]
    for kw, want in cases:
        b, s, poss = _route(overall="LOW", **kw)
        assert s == want and poss == want.split("+"), (kw, b, s, poss)
    assert analyze.scenario_name("S3") == "Retrieval"
    assert analyze.scenario_name("S3+S4") == "Retrieval and reason-based choice"
    assert analyze.scenario_name("S3+S4+S5") == "Retrieval and reason-based choice and rational override"
    # an open signature does not stop the others: the present one is the conclusion, and the open one is listed as
    # still possible beside it
    b, s, poss = _route(t1=_T1_OPEN_STEEP_PT, t3=_T3_DECL, overall="PARTIAL")
    assert s == "S4" and poss == ["S4", "S3"] and "still possible beside it: S3" in b, (b, s, poss)
    b, s, poss = _route(t1=_T1_STEEP, overall="PARTIAL", t2_state="U", t2_override=True)
    assert s == "S3" and poss == ["S3", "S5"], (b, s, poss)
    assert "retrieval present, reason-based choice absent, rational override inconclusive" in b, b


def test_tree_b_s6_when_every_signature_is_absent():
    """S6, a failure that no account predicts: the model does not match people and every signature is absent (the
    mixed pattern, a reversed ordering, an ANTI overall class without recognition, a PARTIAL or OVER overall class). A
    steep fall set out by its interval is absent even when no difference is not resolved either."""
    for kw in (dict(classes=dict(_ALL_HIGH, SOT="ANTI")), dict(t3=_T3_REV, overall="LOW"), dict(overall="ANTI"),
               dict(overall="PARTIAL"), dict(overall="OVER"), dict(t1=_T1_NO_FALL_OPEN_FLAT, overall="PARTIAL")):
        b, s, poss = _route(**kw)
        assert s == "S6" and poss == ["S6"] and "a failure that no account predicts" in b, (kw, b, s, poss)
    assert analyze.CATCH_ALL == "S6" and analyze.SCENARIO_NAMES["S6"] == "A failure that no account predicts"
    st = analyze.signature_states(_T1_FLAT, "F", _T3_REV)
    assert st == {"S3": "absent", "S4": "absent", "S5": "absent"}, st
    assert analyze.signatures_text(st) == "S3=absent;S4=absent;S5=absent"


def test_tree_b_not_resolved_report():
    """When no signature is present and at least one is not resolved, the model is reported as not resolved, with the
    signatures that are still possible and S6 (every open one could still turn out absent)."""
    b, s, poss = _route(t1=_T1_OPEN_FLAT_PT, overall="PARTIAL")
    assert s == analyze.NOT_RESOLVED_SCENARIO and poss == ["S3", "S6"] and "retrieval inconclusive" in b, (b, s, poss)
    b, s, poss = _route(t3=_T3_OPEN_DECL_PT, overall="LOW", t2_state="U", t2_override=True)
    assert s == analyze.NOT_RESOLVED_SCENARIO and poss == ["S4", "S5", "S6"], (b, s, poss)
    b, s, poss = _route(t1=_T1_OPEN_STEEP_PT, t3=_T3_OPEN_DECL_PT, overall="PARTIAL", t2_state="U")
    assert s == analyze.NOT_RESOLVED_SCENARIO and poss == ["S3", "S4", "S5", "S6"], (b, s, poss)
    assert analyze.signature_states(_T1_OPEN_FLAT_PT, "U", _T3_OPEN_DECL_PT) == {
        "S3": "not resolved", "S4": "not resolved", "S5": "not resolved"}
    # how a route compares with a planted scenario (the rehearsal's noise table and the stability study)
    ro = analyze.route_outcome
    assert ro("S3", "S3", ["S3"]) == "intended"
    assert ro("S3", analyze.NOT_RESOLVED_SCENARIO, ["S3", "S6"]) == "not_resolved"
    assert ro("S3", analyze.NOT_RESOLVED_SCENARIO, ["S4", "S6"]) == "not_resolved_excluded"
    assert ro("S3+S5", "S3", ["S3", "S5"]) == "partly_resolved"
    assert ro("S3+S5", "S3", ["S3"]) == "wrong"
    assert ro("S3", "S3+S4", ["S3", "S4"]) == "wrong"
    assert ro("S1", "S2", ["S2"]) == "wrong"


def test_tree_b_step_0_comes_first():
    """Step 0: when four or more of the six effects other than similarity fail in people, every model is HUMAN_FAIL (the model
    comparison is only described); a model whose answers cannot be read is not assessable. Both come before step 1."""
    b, s, poss = _route(t1=_T1_STEEP, human_effects_fail=True)
    assert s == "HUMAN_FAIL" and poss == ["HUMAN_FAIL"] and "fail in people" in b, (b, s)
    assert _route(t1=_T1_STEEP, not_assessable=True)[1] == "CRITERION_FAIL"
    assert _route(not_assessable=True)[1] == "CRITERION_FAIL"                      # a match does not skip Step 0
    assert _route(human_effects_fail=True, not_assessable=True)[1] == "HUMAN_FAIL"
    assert analyze.SCENARIO_NAMES["HUMAN_FAIL"] == "Human effects fail"


def test_tree_b_failed_positive_control_leaves_t1_and_t3_not_judged():
    """A failed positive control makes the memorization and argument-strength tests uninformative: their signatures are
    reported as not judged, which, like not resolved, is neither present nor absent. Rational override is still read
    on the other effects, and a model that matches people is unaffected."""
    t1u, t3u = dict(_T1_FLAT, reading=_UNINF, p_steep="F"), dict(_T3_FLAT, reading=_UNINF, p_declines="F")
    st = analyze.signature_states(t1u, "F", t3u)
    assert st == {"S3": "not judged", "S4": "not judged", "S5": "absent"}, st
    b, s, poss = _route(t1=t1u, t3=t3u, overall="PARTIAL")
    assert (s == analyze.NOT_RESOLVED_SCENARIO and poss == ["S3", "S4", "S6"]
            and "retrieval not tested" in b), (b, s, poss)
    b, s, poss = _route(t1=t1u, t3=t3u, overall="ANTI", t2_state="T", t2_override=True)
    assert s == "S5" and poss == ["S5", "S3", "S4"], (b, s, poss)
    assert _route(t1=t1u, t3=t3u)[1] == "S1"


def test_tree_b_end_to_end_human_effects_fail():
    """End to end: on human data where four or more of the six effects other than similarity fail, the pipeline
    routes every assessable model to HUMAN_FAIL before step 1 of the tree, whatever the model does."""
    H = synth.gen_human(300, random.Random(81), icc=0.0, surprise=True)
    models = {"FAITHFUL_S5": _exact_model("FAITHFUL_S5", _planted),
              "PARROT_S5": _exact_model("PARROT_S5", lambda st, t, c: _planted(st, t, c) if t == 1 else 0.0)}
    tmp = _scratch("simple_rule_s5")
    saved = (analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR)
    try:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = tmp, os.path.join(tmp, "tests"), os.path.join(tmp, "figures")
        res = analyze.build_pack(H, models, human_rows_first_trial=H, mode="TEST", design=analyze.Design.for_synth())
    finally:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = saved
    assert res["most_failed"] is True and res["s5_triggered"] is True
    route = {r["model"]: r for r in res["routing_rows"]}
    for m in models:
        assert route[m]["scenario"] == "HUMAN_FAIL" and route[m]["possible_scenarios"] == "HUMAN_FAIL", route[m]
        assert route[m]["matches_people"] == "not asked (Step 0)" and route[m]["signatures"] == "not read (Step 0)"
        assert route[m]["pointing"] == "not read (Step 0)"
        assert res["numbers"][f"model.{m}.scenario"] == "HUMAN_FAIL"


def test_phantom_equivalence_is_read_only_when_the_phantom_misses_the_criterion():
    """2026-10-17 (editor audit SC-12): a phantom that meets the replication criterion is present even when its 90%
    interval lies inside plus or minus 2 points; a phantom that misses it is absent when inside, not detected when not."""
    inside, outside = dict(equivalent=True), dict(equivalent=False)
    assert analyze.phantom_reading(True, inside).startswith("present")
    assert analyze.phantom_reading(False, inside).startswith("absent")
    assert analyze.phantom_reading(False, outside).startswith("not detected")


def test_phantom_band_is_two_points():
    """2026-11-24 (the authors): the phantom equivalence band is plus or minus 2 points, not 4, because the published phantom
    effect is about 4 points. With a standard error of 0.5 points the 90 percent interval is the estimate plus or minus
    0.82 points: an estimate of 1.0 point (interval 0.18 to 1.82) is absent, and an estimate of 1.5 points (0.68 to 2.32)
    is not detected, although a band of 4 points would have called it absent. The reading names the band."""
    assert analyze.RC.PHANTOM_BAND_PP == 2.0 and analyze.PHANTOM_BAND == 0.02
    import registered_constants
    meaning = registered_constants.MEANING["PHANTOM_BAND_PP"][1]      # the row Table WA-E1 prints
    assert "inside minus 2 to plus 2 points" in meaning and "4" not in meaning, meaning
    absent = analyze.phantom_equivalence(0.010, 0.005)
    assert absent["equivalent"] and absent["band_pp"] == 2.0, absent
    assert 0.17 < absent["ci90_lo_pp"] < 0.19 and 1.81 < absent["ci90_hi_pp"] < 1.83, absent
    wide = analyze.phantom_equivalence(0.015, 0.005)
    assert not wide["equivalent"], wide
    assert statlib.tost_equivalence(0.015, 0.005, 0.04, analyze.RC.PHANTOM_EQUIV_ALPHA)[2]   # a 4-point band would pass
    neg = analyze.phantom_equivalence(-0.015, 0.005)
    assert not neg["equivalent"], neg
    assert analyze.phantom_reading(False, absent) == "absent: the 90 percent interval lies inside plus or minus 2 points"
    assert analyze.phantom_reading(False, wide) == ("not detected: the 90 percent interval reaches beyond plus or minus "
                                                    "2 points")


def test_trajectory_readings_are_the_registered_ones():
    """The trajectory test is reported beside each model and decides nothing (2026-11-02): no reading names a
    scenario, a rise and a fall both say so."""
    T5 = analyze.test_T5_trajectory
    assert T5(0.5, 0.9)["trajectory"] == "newer more faithful -> fidelity is higher in the newer generation; no scenario assigned"
    assert "no scenario" in T5(0.9, 0.5)["trajectory"]
    assert "no difference between generations" in T5(0.7, 0.75)["trajectory"]
    for a, b in ((0.5, 0.9), (0.9, 0.5), (0.7, 0.75)):
        assert "(S" not in T5(a, b)["trajectory"], T5(a, b)["trajectory"]


def test_r5_format_test_is_descriptive_and_reason_construction_reads_the_ladder():
    """T4 reports its difference and interval with no reading and decides no scenario; reason construction (S4) needs
    a resolved decline down the argument-strength ladder. The router does not even take the format test."""
    r = analyze.test_T4_formats({"numbers": 0.9, "pictures": 0.2}, None, {"numbers": 0.9, "pictures": 0.2},
                                diff_ci=(0.5, 0.9), resolve=True)
    assert (r["reading"].startswith("descriptive") and r["p_falls"] == r["p_flat"] == "F" and r["resolved"]
            and r["diff_lo"] == 0.5 and r["diff_hi"] == 0.9), r
    import inspect
    assert "t4" not in inspect.signature(analyze.route_model).parameters
    assert _route(t3=_T3_DECL, overall="PARTIAL")[1] == "S4"
    assert _route(t3=_T3_DECL)[1] == "S4"            # the authors 2026-11-03: a present failure blocks the match


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


def test_tree_b_end_to_end_faithful_models_and_what_is_reported_beside():
    """End to end (pack A, 400 choices per human cell): the faithful models match people (their classes match and no
    failure is present; a 'no difference' memorization reading that is not resolved does not block the match), so
    they reach S1; the twin pair's trajectory (no difference) and its shared class are reported beside both models;
    the CUSTOM model does not match people, every signature state is written, and its open fall leaves it not resolved
    with retrieval still possible (never S3); the KNOWN model (synth's CONVERGE_NEW) matches people and names the
    decoys whose effects it shows, so it reaches S2."""
    res, _ = _pack("A")
    route = {r["model"]: r for r in res["routing_rows"]}
    for m in ("REASONING_PAIR", "TWIN_OLD", "TWIN_NEW"):
        t1 = next(r for r in res["test_T1_rows"] if r["model"] == m)
        t3 = next(r for r in res["test_T3_rows"] if r["model"] == m)
        assert route[m]["scenario"] == "S1", (m, route[m]["scenario"], t1["reading"][:60])
        assert route[m]["matches_people"] == "yes" and "=present" not in route[m]["signatures"], route[m]
        assert route[m]["pointing"] == "none" and res["numbers"][f"model.{m}.pointing"] == "none", route[m]
        assert res["numbers"][f"model.{m}.matches_people"] == "yes"
        assert t1["p_steep"] != "T" and t3["p_declines"] != "T", (m, t1["reading"][:60], t3["reading"][:60])
    assert route["KNOWN"]["scenario"] == "S2" and route["KNOWN"]["matches_people"] == "yes", route["KNOWN"]
    assert ("FRQ=yes" in route["KNOWN"]["named_decoy"] and "MOT=not in the test" in route["KNOWN"]["named_decoy"]
            and "SIM=not in the test" in route["KNOWN"]["named_decoy"]), route["KNOWN"]
    assert route["CUSTOM"]["matches_people"] == "no", route["CUSTOM"]
    sig = dict(p.split("=") for p in route["CUSTOM"]["signatures"].split(";"))
    assert set(sig) == {"S3", "S4", "S5"} and set(sig.values()) <= set(analyze.SIGNATURE_STATES), sig
    assert res["numbers"]["model.CUSTOM.signatures"] == route["CUSTOM"]["signatures"]
    assert any(not next(r for r in res["test_T1_rows"] if r["model"] == m)["resolved"]
               for m in ("REASONING_PAIR", "TWIN_OLD", "TWIN_NEW")), "pack A no longer has an open flat reading"
    twin = next(r for r in res["test_T5_rows"] if r["family"] == "famTWIN")
    assert twin["trajectory"].startswith("flat across generations"), twin
    assert (twin["older_models"], twin["newer_models"]) == ("TWIN_OLD", "TWIN_NEW"), twin
    for m in ("TWIN_OLD", "TWIN_NEW"):
        assert "trajectory" not in route[m], "the family's comparison of generations is reported beside a model"
        assert route[m]["family_consistent"] == "yes" and route[m]["family_classes"] == "TWIN_NEW=HIGH;TWIN_OLD=HIGH"
    assert route["REASONING_PAIR"]["family_consistent"] == "one model"
    # CUSTOM falls only on the invented tier, which is descriptive, so it is not retrieval (S3); its invented-tier
    # fidelity is reported beside the registered reading
    t1c = next(r for r in res["test_T1_rows"] if r["model"] == "CUSTOM")
    assert route["CUSTOM"]["scenario"] != "S3" and not t1c["reading"].startswith("steep"), (route["CUSTOM"], t1c)
    assert t1c["descriptive_fidelity_invented_tier"] < t1c["fidelity_t1"], t1c
    assert (route["CUSTOM"]["scenario"] == analyze.NOT_RESOLVED_SCENARIO
            and route["CUSTOM"]["possible_scenarios"].split(";")[0] == "S3"), route["CUSTOM"]
    t2 = [r for r in res["test_T2_rows"] if r["model"] == "REASONING_PAIR"]
    assert t2 and all(r["override_state"] in ("T", "F", "U") for r in t2)
    # the T2 intervals are computed and used: pack B's FAITHFUL draws its probe answers, so its
    # recognition rates carry intervals of positive width, and every pooled effect carries its interval over calls
    resb, _ = _pack("B")
    tb = [r for r in resb["test_T2_rows"] if r["model"] == "FAITHFUL" and not r["reading"].startswith("uninformative")]
    assert tb and all(r["behavior_lo_pp"] != "" and r["behavior_lo_pp"] <= r["behavior_pp"] <= r["behavior_hi_pp"]
                      for r in tb), tb
    assert any(r["excess_lo"] != "" and r["excess_lo"] < r["excess_rate"] < r["excess_hi"]
               for r in tb), [(r["excess_lo"], r["excess_rate"], r["excess_hi"]) for r in tb]
    for r in tb:                          # the states follow the intervals
        assert abs(r["excess_rate"] - (r["recognition_rate"] - r["two_option_rate"])) < 1e-3, r
        want_k = ("T" if r["excess_lo"] >= 0.5 and r["knows"] else
                  ("F" if r["excess_hi"] < 0.5 and not r["knows"] else "U"))
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
    t5 = next(r for r in res["test_T5_rows"] if r["family"] == "famTWIN")
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
    """bootstrap=False: every memorization reading is not resolved. Under decision tree B a faithful model still
    reaches S1, because a match is read from the classes and needs no interval. A retrieval-shaped model, which does
    not match people and whose estimate points to S3, is not resolved with S3 possible."""
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
    t3 = next(r for r in res["test_T3_rows"] if r["model"] == "FAITHFUL_X")
    assert route["FAITHFUL_X"]["scenario"] == "S1" and route["FAITHFUL_X"]["matches_people"] == "yes", \
        route["FAITHFUL_X"]
    assert t1["p_steep"] in ("F", "U") and t3["p_declines"] in ("F", "U"), (t1, t3)
    assert route["PARROT_X"]["scenario"] == "S7" and "S3" in route["PARROT_X"]["possible_scenarios"], \
        route["PARROT_X"]
    # its fall is open and its estimate is steep, so the routing file records that the test points to retrieval
    assert route["PARROT_X"]["pointing"].split(";")[0] == "S3", route["PARROT_X"]


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
    assert ("PHT=fails in people, and the model shows an effect without a human counterpart"
            in route["PHANTOM_RECITER"]["effect_classes"]), route["PHANTOM_RECITER"]
    assert analyze.RETRIEVAL_READING in route["PHANTOM_RECITER"]["over_readings"], route["PHANTOM_RECITER"]
    assert analyze.RETRIEVAL_READING not in route["PHANTOM_REVERSED"]["over_readings"]
    R = analyze.over_readings
    assert R("PHT", "", False, 0.05, None) == ["phantom larger than 3 points where the human phantom failed: "
                                               + analyze.RETRIEVAL_READING]
    assert R("PHT", "", False, 0.03, None) == [] and R("PHT", "", False, -0.05, None) == []


# ---- rule 5 (F7): effects below the first-trial floor are descriptive ------------------------------------
def test_first_trial_fallback_classes_every_replicating_effect():
    """2026-11-25 (the editor's read, item 2.9): after the first-trial fallback, the replication criterion on the
    first-choice estimates alone decides which effects are confirmatory; the old 8-point floor, which left a smaller
    replicating effect out of the classes and the tests of the three accounts, is gone. Planted: first-trial data
    in which effects under 8 points replicate; each must be classed and enter the most frequent class."""
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
    small = [st for st in analyze.EFFECTS if g[st]["replicated"] and g[st]["delta_pp"] < 8.0]
    assert res["numbers"]["human.first_trial.fallback_triggered"] is True and small, small
    assert all(g[st]["confirmatory"] for st in small), {st: g[st]["confirmatory"] for st in small}
    assert not hasattr(analyze, "DESCRIPTIVE_FLOOR") and not hasattr(analyze.RC, "FIRST_TRIAL_MIN_EFFECT_PP")
    ec = {r["effect"]: r for r in res["effect_class_rows"]}
    for st in small:
        assert ec[st]["class"] in analyze.SCORED_CLASSES, ec[st]
    conf = [st for st in analyze.REGULARITY_EFFECTS if g[st]["confirmatory"]]
    overall = res["agreement_rows"][0]["class"]
    assert overall == analyze.majority_class([ec[st]["class"] for st in conf if st in ec]), overall
    mr = res["model_results"]["FAITHFUL_F"]
    assert all(mr["fidelity_by_struct"].get(st) is not None for st in small), mr["fidelity_by_struct"]
    assert all(any(c["structure"] == st for c in mr["scored_cells"]) for st in small)


# ---- rule 14: the printed table ---------------------------------------------------------------------
def test_i2_printed_table_is_reader_facing():
    import print_constants as P
    text = P.build()
    wa = text.split("## Where each row lives")[0]
    for word in ("regularity effect", "regularity-violating", "arguable", "knows-it test", "Step 0a", "Step 0b",
                 "True", "False", "—"):
        assert word not in wa, f"house word or code value in the printed table: {word!r}"
    for name, step in (("COMPROMISE_TARGET_MAX_BASELINE_PCT", "Human benchmarks"), ("HARD_LIMIT_LO_PCT", "Human benchmarks"),
                       ("HARD_LIMIT_HI_PCT", "Human benchmarks")):
        import registered_constants as R
        assert R.MEANING[name][0].startswith(step), (name, R.MEANING[name][0])
    assert "| Human benchmarks, stimulus handling | Yes |" in wa and "| Re-running the model calls | 95 percent |" in wa
    dev_row = next(ln for ln in wa.splitlines() if "remove seven calibration pairs" in ln)
    assert "televisions" not in dev_row, "the deviation row is not the seven"
    assert "inconclusive" in wa, "the resolution rule is missing from the printed table"
    # 2026-11-24 (the terms of the writing pass): the parts of the Analysis Plan by heading, the classes in words
    for word in ("Step 0", "Step 1", "Step 2", "Step 3", "Step 4", "not resolved", "HIGH", "OVER", "PARTIAL", " LOW",
                 "ANTI", "tier", "recognition call", "knows-it-versus-shows-it", "memorization test", "trajectory test"):
        assert word not in wa, f"an internal name in the printed table: {word!r}"
    # the authors' terminology rule (2026-09-29): no 'arm', 'backbone' or 'top-up' anywhere a reader looks
    import re
    reader = wa + text.split("## Rules stated with the constants")[1]
    for pat in (r"\barms?\b", r"backbone", r"top-up", r"numeric backbone"):
        assert not re.search(pat, reader, re.I), f"in-house term in the printed table or its rules: {pat!r}"


def test_generations_pool_all_their_members():
    """The roster of 2026-11-24: each
    generation's fidelity pools the cells of ALL its members within the family, and the comparison is repeated within
    the models that switch reasoning off, with reasoning off in both. A planted family: older models at 0.4 and 0.6
    of the human size, newer at 1.4 and 0.4, so the pooled generations differ by 0.4 (rising), while the two models
    that switch reasoning off (0.4 and 0.4) do not differ. No single pair of members gives both readings, so the test
    fails if one member stood for its generation. A family with newer models only has no comparison."""
    res, _ = _pack("POOL")
    fams = {r["family"]: r for r in res["test_T5_rows"]}
    assert len(res["test_T5_rows"]) == len(fams) == 3, "the comparison of generations is one row per family"
    r = fams["famPOOL"]
    assert (r["older_models"], r["newer_models"]) == ("POOL_OLD_A;POOL_OLD_B", "POOL_NEW_A;POOL_NEW_B"), r
    assert (r["older_models_off"], r["newer_models_off"]) == ("POOL_OLD_A", "POOL_NEW_B"), r
    assert (r["n_old"], r["n_new"], r["n_old_off"], r["n_new_off"]) == (2, 2, 1, 1), r
    assert abs(r["delta"] - 0.4) < 0.08, f"pooled generations differ by {r['delta']}, planted 0.4"
    assert r["trajectory"].startswith("newer more faithful"), r["trajectory"]
    assert abs(r["delta_reasoning_off"]) < 0.08, f"reasoning-off generations differ by {r['delta_reasoning_off']}"
    assert r["trajectory_reasoning_off"].startswith("flat across generations"), r["trajectory_reasoning_off"]
    # the pooled value is the generation's, not one member's: every single old/new pair differs by 0.2 to 1.0 raw
    fid = {m: res["model_results"][m]["fid_primary"] for m in res["model_results"]}
    single = [fid[n] - fid[o] for o in ("POOL_OLD_A", "POOL_OLD_B") for n in ("POOL_NEW_A", "POOL_NEW_B")]
    assert all(abs(d - r["delta"]) > 0.05 for d in single), (single, r["delta"])
    solo = fams["famSOLO"]
    assert solo["trajectory"].startswith("insufficient generations"), solo["trajectory"]
    assert solo["trajectory_reasoning_off"].startswith("no models that switch reasoning off"), solo
    assert res["numbers"]["family.famPOOL.T5.trajectory_reasoning_off"].startswith("flat across generations")
    # review finding 5.1: a model with no reasoning mode counts as reasoning off in the repeat
    na = fams["famNA"]
    assert (na["n_old_off"], na["n_new_off"]) == (1, 1), na
    assert na["trajectory_reasoning_off"].startswith("newer more faithful"), na["trajectory_reasoning_off"]


def test_reasoning_side_is_crossed_high_else_default():
    """The roster of 2026-11-24: the reasoning-on side of T5 is a model's crossed records at HIGH
    where it runs HIGH, else at DEFAULT; the other crossed settings, the ladder and the temperatures are left out,
    and the primary records stay in the confirmatory estimates."""
    def rec(arm, setting, mode="neutral"):
        return {"prompting_mode": mode, "arm": arm, "setting": setting}
    both = [rec("primary", "OFF"), rec("crossed", "DEFAULT"), rec("crossed", "HIGH"), rec("crossed", "LOW"),
            rec("ladder", "MAX"), rec("temp_1", "OFF"), rec("persona", "OFF", "persona")]
    keep, reason, other = analyze.split_arms(both)
    assert [r["setting"] for r in reason] == ["HIGH"], reason
    assert other == 4 and [r["arm"] for r in keep] == ["primary", "persona"], (keep, other)
    only_default = [rec("primary", "LOW"), rec("crossed", "DEFAULT"), rec("crossed", "DEFAULT")]
    keep, reason, other = analyze.split_arms(only_default)
    assert [r["setting"] for r in reason] == ["DEFAULT", "DEFAULT"] and other == 0, reason
    none = [rec("primary", "DEFAULT"), rec("temp_0", "DEFAULT")]
    keep, reason, other = analyze.split_arms(none)
    assert reason == [] and other == 1
    old = [rec("primary", None), rec("reasoning_on", None)]
    assert len(analyze.split_arms(old)[1]) == 1, "records of the older arm name must still form the reasoning side"


# ================================================================================================
# 2026-11-25: the confirmatory rules that the editor's read of 2026-11-24 found open
#. Each test is written to FAIL on the code
# before these rules (git 5439038) and PASS after it.
# ================================================================================================
def _probe_rows(key, rate_by_struct, n=10, family=None, prefix=None):
    """Suspicion-probe records on the synthetic lattice: for each category, stimulus set and structure in
    rate_by_struct (BIN for the two-option sets), n probe calls of which exactly round(rate * n) score 1."""
    recs, i = [], 0
    for cat in synth.CATS:
        for tier in ([1, 2] if cat in synth.PUB else [3]):
            for st, rate in rate_by_struct.items():
                k1 = round(rate * n)
                for k in range(n):
                    recs.append(dict(record_id=f"{prefix or key}P{i}", model_key=key, category=cat, structure=st,
                                     tier=tier, format="numbers", prompting_mode="recognition",
                                     recognition=(1 if k < k1 else 0), exclusion_flag=False,
                                     stimulus_id=f"s_{cat}_{st}_{tier}", position_order=f"o{k + 1}",
                                     paraphrase_id=k + 1, family=family or key, generation="new"))
                    i += 1
    return recs


def _with_release(recs, date):
    return [dict(r, release=date) for r in recs]


def _pack_r14():
    """People: extremity and the range decoy planted at zero (both fail the replication criterion), every other effect
    at its planted size. Models (all faithful to the planted truth unless said otherwise; probe shares exact):
      R14_RNGNAMER  shows no range effect and names the range decoy in every probe (the range decoy failed in people)
      R14_SIMNAMER  shows no similarity or extremity effect and names their added options in every probe
      R14_YESALL    names the decoy in 90 percent of probes and calls 90 percent of two-option sets constructed
      R14_EARLY / R14_ANCIENT / R14_LATE  faithful, released before the extremity paper, before both papers, after
                    both"""
    if "R14" in _PACKS:
        return _PACKS["R14"]
    H = synth.gen_human(400, random.Random(141), icc=0.0, null_effects={"MOT", "RNG"})
    none = {"FRQ": 0.0, "RNG": 0.0, "SOT": 0.0, "SYM": 0.0, "SIM": 0.0, "MOT": 0.0, "BIN": 0.0}
    models = {
        "R14_RNGNAMER": (_exact_model("R14_RNGNAMER", lambda st, t, c: 0.0 if st == "RNG" else _planted(st, t, c))
                         + _probe_rows("R14_RNGNAMER", dict(none, RNG=1.0))),
        "R14_SIMNAMER": (_exact_model("R14_SIMNAMER", lambda st, t, c: 0.0 if st in ("SIM", "MOT") else _planted(st, t, c))
                         + _probe_rows("R14_SIMNAMER", dict(none, SIM=1.0, MOT=1.0))),
        "R14_YESALL": (_exact_model("R14_YESALL", _planted)
                       + _probe_rows("R14_YESALL", {"FRQ": 0.9, "RNG": 0.9, "SOT": 0.9, "SYM": 0.9, "BIN": 0.9})),
        "R14_EARLY": _with_release(_exact_model("R14_EARLY", _planted) + _probe_rows("R14_EARLY", none), "2025-06-01"),
        "R14_ANCIENT": _with_release(_exact_model("R14_ANCIENT", _planted) + _probe_rows("R14_ANCIENT", none),
                                     "2022-01-01"),
        "R14_LATE": _with_release(_exact_model("R14_LATE", _planted) + _probe_rows("R14_LATE", none), "2026-03-01"),
        # answers the probe on every set but the upscaling sets, and shows no upscaling effect
        "R14_NOSYMPROBE": (_exact_model("R14_NOSYMPROBE", lambda st, t, c: 0.0 if st == "SYM" else _planted(st, t, c))
                           + _probe_rows("R14_NOSYMPROBE", {k: v for k, v in none.items() if k != "SYM"})),
    }
    tmp = _scratch("r14_pack")
    saved = (analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR)
    try:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = tmp, os.path.join(tmp, "tests"), os.path.join(tmp, "figures")
        res = analyze.build_pack(H, models, human_rows_with_formats=H, human_rows_first_trial=H, mode="TEST",
                                 design=analyze.Design.for_synth())
    finally:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = saved
    _PACKS["R14"] = (res, H)
    return _PACKS["R14"]


def test_positive_control_reads_calibrated_premium_target_cells_at_new_values():
    """the authors' decision of 2026-11-25 ("Redefine, no new data"): the frequency-decoy positive control is judged only
    on the cells at the new values whose decoy favors the premium option and whose two-option pair met the
    calibration rule. Planted: no frequency-decoy effect at the published values of the premium-target categories, a
    strong reversal in the premium-target pair that missed the rule (synthetic category 0, new values), and a clear
    effect in the one calibrated premium-target pair at the new values (category 1). The control must read that one
    pair and hold; read over every stimulus set, as before, it failed."""
    rng = random.Random(1411)
    H = synth.gen_human(700, random.Random(1410), icc=0.0, published_n_per_tier=350, null_on_hd_target={"FRQ"})
    ctrl = {}
    for r in H:
        if r["structure"] == "BIN" and r["format"] == "numbers":
            ctrl.setdefault((str(r["category"]), int(r["tier"])), []).append(int(r["chose_target"]))
    share = {k: sum(v) / len(v) for k, v in ctrl.items()}
    for r in H:
        if r["structure"] == "FRQ" and r["format"] == "numbers" and int(r["tier"]) == 2:
            c = str(r["category"])
            if c == "1":
                r["chose_target"] = 1 if rng.random() < share[(c, 2)] + 0.20 else 0
            elif c == "0":
                r["chose_target"] = 1 if rng.random() < max(0.0, share[(c, 2)] - 0.30) else 0
    d = analyze.Design.for_synth()
    assert ("0", 2, "numbers") in d.deviation_slices and ("1", 2, "numbers") not in d.deviation_slices
    criterion = analyze.human_gate(H, d, {"SOT": d.compromise_descriptive})[0]
    pc = analyze.positive_control_check(H, d, criterion, {"SOT": d.compromise_descriptive})
    assert pc["frq_premium"]["n_strata"] == 1, pc          # the one calibrated premium-target pair at new values
    assert pc["frq_premium"]["holds"] and "FRQ" not in pc["failed"], pc
    assert pc["frq_premium"]["delta_pp"] > 10, pc


def test_positive_control_cells_on_the_registered_stimuli():
    """The Main's rule of 2026-11-25 (after the control's power was reported): the frequency-decoy control reads
    every premium-target cell of the stimulus sets that we built (the new values and the new categories) whose pair
    met the calibration rule. On the registered stimuli, these are the external hard drives and the televisions at
    the new values and the robot vacuums, and no other cell: the backpacks and the earbuds at the new values missed
    the rule, the published values are left out, and the other built cells favor the budget option."""
    d = analyze.Design.from_stimuli()
    rng = random.Random(1412)
    rows, pid = [], 0
    cats = sorted({c for (c, t, s, p) in d.targets if s == "FRQ"})
    for cat in cats:
        for tier in (1, 2, 3):
            if (cat, tier, "FRQ", None) not in d.targets:
                continue
            for st in ("FRQ", "BIN"):
                for _ in range(40):
                    pid += 1
                    y = int(rng.random() < 0.5)
                    rows.append(dict(structure=st, category=cat, tier=tier, format="numbers", participant_id=f"p{pid}",
                                     chose_target=y, chose_hd=y, trial_position=2))
    criterion = {"SOT": dict(replicated=True, delta_pp=5.0)}
    pc = analyze.positive_control_check(rows, d, criterion)
    assert pc["frq_premium"]["cells"] == "hard_drives|t2;robot_vacuums|t3;televisions|t2", pc["frq_premium"]["cells"]


def test_extremity_failing_in_people_leaves_reason_based_choice_not_tested():
    """The editor's item 2.2(a): extremity is the whole bottom position of the argument-strength ordering, so when it
    fails in people the test of reason-based choice is not run, as for a failed positive control, and the
    reason-based-choice failure is not tested for every model (before, an empty position read as absent, which let a
    model reach the conclusion that no account predicts its failure)."""
    res, _ = _pack_r14()
    assert res["criterion"]["MOT"]["replicated"] is False and not res["failed_controls"]
    for r in res["test_T3_rows"]:
        assert r["reading"].startswith(analyze.NOT_TESTED_EXTREMITY), r["reading"]
    for route in res["routing_rows"]:
        assert "S4=not judged" in route["signatures"], route["signatures"]
        assert route["scenario"] != analyze.CATCH_ALL, route    # never "all three absent" with one not tested
    states = analyze.signature_states(dict(reading=analyze.NOT_TESTED_EXTREMITY + "; x"), "F",
                                      dict(reading=analyze.NOT_TESTED_EXTREMITY + "; x"))
    assert states["S3"] == "not judged" and states["S4"] == "not judged"


def test_rational_override_counts_only_effects_that_replicate_in_people():
    """The editor's item 2.2(b): a model that names the decoy and shows no effect where people show none either
    resists a push that people do not feel, so an effect that failed the replication criterion is not part of the
    test of rational override."""
    per, ov = analyze.test_T2_recognition({"RNG": 1.0}, {"RNG": 0.0}, failed_in_people={"RNG"})
    assert ov is False and per["RNG"]["override_state"] == "F", per["RNG"]
    assert per["RNG"]["reading"] == analyze.T2_FAILED_IN_PEOPLE
    res, _ = _pack_r14()
    assert res["criterion"]["RNG"]["replicated"] is False
    route = next(r for r in res["routing_rows"] if r["model"] == "R14_RNGNAMER")
    assert "S5=absent" in route["signatures"], route["signatures"]
    t2 = next(r for r in res["test_T2_rows"] if r["model"] == "R14_RNGNAMER" and r["structure"] == "RNG")
    assert t2["knows"] and t2["reading"] == analyze.T2_FAILED_IN_PEOPLE, t2
    # the report beside the conclusion says so too, never "yes" (the review of 2026-11-25, M7)
    assert "RNG=not in the test (fails in people)" in route["named_decoy"], route["named_decoy"]


def test_similarity_and_extremity_leave_the_test_of_rational_override():
    """The editor's items 1.7 and 2.5(a): similarity leaves the test (the notes promise that it enters no pooled
    summary, and a similarity effect can come from differences in taste alone), and extremity leaves it (its menu has
    no single added option, so a yes alone counted). A model that names their added options and shows neither
    effect must not show the rational-override failure."""
    assert analyze.T2_EFFECTS == ("FRQ", "RNG", "SOT", "SYM")
    per, ov = analyze.test_T2_recognition({"SIM": 1.0, "MOT": 1.0}, {"SIM": 0.0, "MOT": 0.0})
    assert ov is False and "SIM" not in per and "MOT" not in per and "PHT" not in per, per
    res, _ = _pack_r14()
    route = next(r for r in res["routing_rows"] if r["model"] == "R14_SIMNAMER")
    assert "S5=absent" in route["signatures"], route["signatures"]
    assert "SIM=not in the test" in route["named_decoy"] and "MOT=not in the test" in route["named_decoy"], route


def test_naming_the_decoy_is_judged_against_the_two_option_probes():
    """The editor's item 2.5(c): each model's probes of the two-option sets are its baseline. A model names the decoy
    only when its share of probes that name the added option exceeds, by at least one half, its share of two-option
    probes that call the set constructed. A model that calls 90 percent of every set constructed names nothing."""
    per, _ = analyze.test_T2_recognition({"FRQ": 0.9}, {"FRQ": 0.0}, baseline_by_struct={"FRQ": 0.6})
    assert per["FRQ"]["knows"] is False and abs(per["FRQ"]["excess_rate"] - 0.3) < 1e-9, per["FRQ"]
    per, _ = analyze.test_T2_recognition({"FRQ": 0.9}, {"FRQ": 0.0}, baseline_by_struct={"FRQ": 0.4})
    assert per["FRQ"]["knows"] is True and per["FRQ"]["override_state"] == "T", per["FRQ"]
    per, _ = analyze.test_T2_recognition({"FRQ": 0.9}, {"FRQ": 0.0}, baseline_by_struct={"FRQ": 0.1},
                                         recog_ci={"FRQ": (0.45, 0.95)})
    assert per["FRQ"]["knows_state"] == "U", per["FRQ"]      # the excess's interval reaches below one half
    res, _ = _pack_r14()
    t2 = [r for r in res["test_T2_rows"] if r["model"] == "R14_YESALL"]
    assert t2 and all(abs(r["two_option_rate"] - 0.9) < 1e-9 and not r["knows"] for r in t2), t2
    route = next(r for r in res["routing_rows"] if r["model"] == "R14_YESALL")
    assert route["scenario"] != "S2" and "=yes" not in route["named_decoy"], route


def test_training_cutoff_limits_the_test_of_retrieval():
    """The editor's item 2.2(c): a model whose training data end before a source paper went online (its stated
    cutoff, else its release date) could not have read that paper's values, so its test of retrieval uses only the
    other paper's categories; when both papers went online later, the test is not run for the model."""
    assert analyze.readable_papers("2025-06-01") == {"upscaling"}
    assert analyze.readable_papers("2022-01-01") == set()
    assert analyze.readable_papers("2026-03-01") == {"upscaling", "extremity"}
    assert analyze.readable_papers(None) == {"upscaling", "extremity"}
    res, _ = _pack_r14()
    d = analyze.Design.for_synth()
    t1 = {r["model"]: r for r in res["test_T1_rows"]}
    up = {c for c, p in d.source_paper.items() if p == "upscaling"}
    assert t1["R14_EARLY"]["papers_read"] == "upscaling", t1["R14_EARLY"]
    used = {c for part in t1["R14_EARLY"]["paired_categories"].split(";") if part
            for c in part.split(":")[1].split("/")}
    assert used and used <= up, (used, up)
    late = {c for part in t1["R14_LATE"]["paired_categories"].split(";") if part
            for c in part.split(":")[1].split("/")}
    assert late - up, "a model trained after both papers uses the extremity paper's categories too"
    assert t1["R14_ANCIENT"]["reading"].startswith(analyze.NOT_TESTED_DATES), t1["R14_ANCIENT"]
    route = next(r for r in res["routing_rows"] if r["model"] == "R14_ANCIENT")
    assert "S3=not judged" in route["signatures"], route["signatures"]
    # the deviation sensitivity re-run of the test follows the same rule (the review of 2026-11-25, M6)
    sens = next(r for r in res["sens_model_rows"] if r["model"] == "R14_ANCIENT")
    assert sens["sensitivity_T1"].startswith(analyze.NOT_TESTED_DATES), sens["sensitivity_T1"]
    early = set(next(r for r in res["sens_model_rows"] if r["model"] == "R14_EARLY")["sensitivity_T1_categories"]
                .split(";")) - {""}
    assert early and early <= up, (early, up)     # a model that could read one paper: that paper's categories only
    # the registry of models gives the release date when the developer states no cutoff (found through the stimuli file,
    # so the check also runs in the mutation battery's scratch copies; models/ in the working repository tree,
    # models/ in the public release)
    root = os.path.dirname(os.path.dirname(analyze.STIMULI_PATH))
    regs = [p for p in (os.path.join(root, "engines", "model_runner", "model_registry.json"),
                        os.path.join(root, "models", "model_registry.json")) if os.path.exists(p)]
    assert regs, f"no model registry beside {root} in either layout"
    assert analyze.registry_dates(regs[0]).get("llama31-8b") == "2024-07-23"


def test_probe_interval_resamples_within_each_stimulus():
    """The review of 2026-11-25 (H1): run.py gives each probe call of a stimulus its own option order and paraphrase,
    so a bootstrap within grid points would hold one call per point and give the share of naming the decoy no width;
    the rule resamples the calls within each stimulus. A model that names the decoy in 9 of 10 probes per stimulus
    must therefore carry an interval of clear width."""
    res, _ = _pack_r14()
    t2 = [r for r in res["test_T2_rows"] if r["model"] == "R14_YESALL"]
    assert t2 and all(r["excess_hi"] - r["excess_lo"] > 0.08 for r in t2), \
        [(r["structure"], r["excess_lo"], r["excess_hi"]) for r in t2]


def test_rational_override_without_readable_probes_is_inconclusive():
    """The review of 2026-11-25 (M5): when a model answers the probe on other sets but on no set of an effect (or on
    none of its two-option sets), whether it names the decoy there cannot be read, so the rational-override failure
    is inconclusive, never absent; a model that does not match people then stays inconclusive and cannot reach the
    conclusion that no account predicts its failure."""
    res, _ = _pack_r14()
    t2 = next(r for r in res["test_T2_rows"] if r["model"] == "R14_NOSYMPROBE" and r["structure"] == "SYM")
    assert t2["reading"] == analyze.T2_NO_PROBE and t2["knows_state"] == "U" and t2["override_state"] == "U", t2
    route = next(r for r in res["routing_rows"] if r["model"] == "R14_NOSYMPROBE")
    assert "S5=not resolved" in route["signatures"] and route["scenario"] != analyze.CATCH_ALL, route
    assert "SYM=unknown (no readable probe answers)" in route["named_decoy"], route["named_decoy"]


def test_an_empty_comparison_is_not_tested_never_absent():
    """The editor's item 2.2 (2026-11-25): when a test cannot compare its two sides for a model, the failure is not
    tested, never absent, so the model cannot reach the conclusion that no account predicts its failure by a missing
    comparison. Planted, with every human effect replicating: a model with no extremity calls (the bottom position
    of the argument-strength ordering is empty) and a model with no calls at the published values (the test of
    retrieval has one stimulus set only)."""
    H = synth.gen_human(400, random.Random(143), icc=0.0)
    models = {"NO_MOT": [r for r in _exact_model("NO_MOT", _planted) if r["structure"] not in ("MOT", "EXC")],
              "NO_PUB": [r for r in _exact_model("NO_PUB", _planted) if int(r["tier"]) != 1]}
    tmp = _scratch("empty_comparison_pack")
    saved = (analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR)
    try:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = tmp, os.path.join(tmp, "tests"), os.path.join(tmp, "figures")
        res = analyze.build_pack(H, models, human_rows_with_formats=H, human_rows_first_trial=H, mode="TEST",
                                 design=analyze.Design.for_synth())
    finally:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = saved
    assert res["criterion"]["MOT"]["replicated"] and not res["failed_controls"], res["criterion"]["MOT"]
    t3 = next(r for r in res["test_T3_rows"] if r["model"] == "NO_MOT")
    assert t3["reading"].startswith(analyze.NOT_TESTED_ENDS), t3["reading"]
    t1 = next(r for r in res["test_T1_rows"] if r["model"] == "NO_PUB")
    assert t1["reading"].startswith(analyze.NOT_TESTED_ENDS), t1["reading"]
    route = {r["model"]: r for r in res["routing_rows"]}
    assert "S4=not judged" in route["NO_MOT"]["signatures"], route["NO_MOT"]["signatures"]
    assert "S3=not judged" in route["NO_PUB"]["signatures"], route["NO_PUB"]["signatures"]


def test_the_fall_on_extremity_alone():
    """Web Appendix E.11 (2026-11-26): beside the test of retrieval, the fall in fidelity on extremity alone, whose
    menus differ between the stimulus sets in none of the three ways for which the adjusted test adjusts. Planted
    paired cells: extremity at fidelity 1.0 on the published values and 0.4 on the new values (a fall of 0.6), with
    other effects that must not enter it; replicates planted so the interval brackets the fall. A clean control: no
    extremity cell at the new values gives blanks, never a number."""
    reps = lambda v: [v] * 50                      # noqa: E731  (no spread: the interval equals the point)
    paired = {1: [("MOT", 10.0, 10.0, 1.0, reps(10.0), reps(10.0)), ("FRQ", 1.0, 10.0, 1.0, reps(1.0), reps(10.0))],
              2: [("MOT", 4.0, 10.0, 1.0, reps(4.0), reps(10.0)), ("FRQ", 9.0, 10.0, 1.0, reps(9.0), reps(10.0))]}
    out = analyze.descriptive_fall_one_effect(paired, "MOT", "fall")
    assert out["fall"] == 0.6 and out["fall_lo"] == 0.6 and out["fall_hi"] == 0.6, out
    paired[2] = [x for x in paired[2] if x[0] != "MOT"]
    out = analyze.descriptive_fall_one_effect(paired, "MOT", "fall")
    assert out == {"fall": "", "fall_lo": "", "fall_hi": ""}, out


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
    "test_reversed_ordering_is_described_and_decides_nothing", "test_effect_without_a_human_counterpart",
    "test_human_effects_fail_needs_four_of_the_six_non_similarity_effects", "test_no_account_is_attached_effect_by_effect",
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
    "test_r2_phantom_retrieval_reading", "test_first_trial_fallback_classes_every_replicating_effect",
    # the registered rules (a) to (d)
    "test_phantom_equivalence_is_read_only_when_the_phantom_misses_the_criterion",
    "test_phantom_band_is_two_points",
    "test_trajectory_readings_are_the_registered_ones",
    "test_r4_kept_members_reproduce_the_registered_readings",
    "test_r5_format_test_is_descriptive_and_reason_construction_reads_the_ladder",
    "test_r5_memorization_sensitivity_is_paired_and_one_step",
    "test_r3_knows_without_shows_is_resolved_against_intervals",
    # decision tree B (2026-11-03): the match, S2, each signature, several at once, S6, not resolved, a failed
    # control and Step 0
    "test_tree_b_step_1_match_needs_the_classes_and_no_failure_present", "test_tree_b_s2_matches_people_and_names_the_decoy",
    "test_tree_b_a_test_that_points_to_a_failure_blocks_the_match",
    "test_tree_b_each_failure_signature_alone", "test_tree_b_several_signatures_at_once",
    "test_tree_b_s6_when_every_signature_is_absent", "test_tree_b_not_resolved_report",
    "test_tree_b_step_0_comes_first", "test_tree_b_end_to_end_human_effects_fail",
    "test_tree_b_failed_positive_control_leaves_t1_and_t3_not_judged",
    "test_tree_b_end_to_end_faithful_models_and_what_is_reported_beside",
    # the roster of 2026-11-24
    "test_reasoning_side_is_crossed_high_else_default",
    "test_generations_pool_all_their_members",
    # 2026-11-25: the confirmatory rules of the editor's read
    "test_positive_control_reads_calibrated_premium_target_cells_at_new_values",
    "test_positive_control_cells_on_the_registered_stimuli",
    "test_extremity_failing_in_people_leaves_reason_based_choice_not_tested",
    "test_rational_override_counts_only_effects_that_replicate_in_people",
    "test_similarity_and_extremity_leave_the_test_of_rational_override",
    "test_naming_the_decoy_is_judged_against_the_two_option_probes",
    "test_training_cutoff_limits_the_test_of_retrieval",
    "test_an_empty_comparison_is_not_tested_never_absent",
    "test_probe_interval_resamples_within_each_stimulus",
    "test_rational_override_without_readable_probes_is_inconclusive",
    # 2026-11-26: the fall on extremity alone, beside the test of retrieval (Web Appendix E.11)
    "test_the_fall_on_extremity_alone",
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
