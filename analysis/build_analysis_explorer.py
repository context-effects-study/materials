"""build_analysis_explorer.py: builds analysis-explorer.html, one offline page that draws, for every simulated model of
the analysis rehearsal, each step of the registered analysis (Steps 0 to 4) with Play controls, ends at the scenario the
model is assigned, and sorts all simulated models into the checking order of Step 4.

The page reaches no result of its own: it displays the files in analysis/results_pack/, which analysis/analyze.py writes
when it runs on the simulated data in analysis/demo_data/, the cutoffs in analysis/registered_constants.py, and the
scenario each simulated model was built to reach (analysis/synth.py). Every result label the analysis writes is
translated into a plain sentence through a fixed table, and the script stops on a label the table does not cover. Run
it after analysis/analyze.py.

Output: analysis-explorer.html (at the repository root; opens in any browser, offline).

Run: python analysis/build_analysis_explorer.py
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Two layouts: the public release (this file in analysis/, the pack beside it, the page at the root) and the working
# repository (the pack and the page each in their own folder there).
if os.path.isdir(os.path.join(HERE, "results_pack")):
    ANALYSIS = HERE
    OUT = os.path.join(HERE, "..", "analysis-explorer.html")
    MANUSCRIPT = None
else:
    ANALYSIS = os.path.join(HERE, "..", "engines", "analysis")
    OUT = os.path.join(HERE, "offline", "analysis-explorer.html")
    MANUSCRIPT = os.path.join(HERE, "..", "..", "manuscript", "main.md")
PACK = os.path.join(ANALYSIS, "results_pack")
sys.path.insert(0, ANALYSIS)
from registered_constants import C as RC  # noqa: E402
from synth import MODEL_ARCHETYPES  # noqa: E402

EFFECTS = {"FRQ": "Attraction, frequency decoy", "RNG": "Attraction, range decoy", "PHT": "Phantom decoy",
           "SOT": "Compromise", "SYM": "Upscaling", "MOT": "Extremity", "SIM": "Similarity"}
SHORT = {"FRQ": "Frequency decoy", "RNG": "Range decoy", "PHT": "Phantom", "SOT": "Compromise", "SYM": "Upscaling",
         "MOT": "Extremity", "SIM": "Similarity"}
ORDER = ["FRQ", "RNG", "SOT", "SYM", "PHT", "MOT", "SIM"]
TIERS = {"1": "published values", "2": "new values", "3": "invented categories"}

# Each simulated model: a plain name and what it was built to show (the planted behavior).
MODELS = {
    "FAITHFUL": ("Matches people everywhere",
                 "Built to match people on every effect, in every tier and format, without naming the decoy when "
                 "asked."),
    "PARROT": ("Matches people only on the published values",
               "Built to match people on the published values only and to show much smaller effects on new values."),
    "REASONER": ("Matches people where the set gives a reason",
                 "Built to match people where the choice set gives a clear reason (attraction) and to fall short "
                 "where it gives none (extremity)."),
    "OVERRIDER": ("Names the decoy and chooses against it",
                  "Built to name the decoy when asked and to choose against it, so its effects run opposite to "
                  "people's."),
    "DIVIDED_A": ("Two models of one family: the first",
                  "One of two models of the same family: this one matches people."),
    "DIVIDED_B": ("Two models of one family: the second",
                  "One of two models of the same family: this one reverses people's effects."),
    "CONVERGE_OLD": ("Older model of a family that improves",
                     "The older model of a family whose newer model matches people more closely."),
    "CONVERGE_NEW": ("Newer model of a family that improves",
                     "The newer model of a family whose older model matched people less closely."),
    "WALK1_PARROT": ("Walk-through 1 of Web Appendix C",
                     "Matches people on the published values and not on new values."),
    "WALK2_MIXED": ("Walk-through 2 of Web Appendix C",
                    "Matches people on most effects, reverses compromise and names the compromise manipulation when "
                    "asked."),
    "CEILING": ("Picks the same option almost every time",
                "Built to pick the same option in nearly every two-option set, so a decoy has no room to move it."),
    "REFUSER": ("Often refuses to answer", "Built to refuse or give unreadable answers in many calls."),
    "R4_ARGUABLE_OVERRIDE": ("Walk-through 3, the manipulation named",
                             "Walk-through 3 of Web Appendix C (a reviewer's case): misses attraction and compromise, "
                             "matches upscaling and extremity, and names the manipulation where it misses the effect."),
    "R4_ARGUABLE_NORECOG": ("Walk-through 3, the manipulation not named",
                            "The same reviewer's case, but the model does not name the manipulation where it misses "
                            "the effect."),
    "OVERSHOOT_T1": ("Exaggerates effects on the published values",
                     "Built to show every effect three times larger than people on the published values and at the "
                     "human size on new values."),
}

# The registered checking order of Step 4 (Analysis Plan, Step 4), with the paper's requirement for each row. For a
# scenario row the requirement is the "What the results must show" cell of Table 4; for the three rows that are not
# scenarios it is the Step 4 text. `source` must occur in the manuscript when the manuscript is present; `tests` are the
# pattern tests a row depends on, used to mark a passed row whose test was not resolved.
STEPS = [
    dict(title="Reversed ordering, manipulation identified",
         need="Fidelity rises down the argument-strength ordering (T3), and the model identifies the manipulation on "
              "every attraction or compromise effect it misses (T2). Conclusion: rational override on the choice sets "
              "that give an argument.",
         source="(1) a reversed argument-strength ordering, with the manipulation identified on every attraction or "
                "compromise effect the model misses, which we conclude is rational override on the choice sets that "
                "give an argument", tests=["T3", "T2"]),
    dict(title="S4, rational override",
         need="First way: the model identifies the manipulation and does not show the effect on at least one effect "
              "(T2), with a LOW or ANTI overall class.",
         source="First way: the model identifies the manipulation and does not show the effect on at least one effect "
                "(T2), with a LOW or ANTI overall class.", tests=["T2"], code="S4"),
    dict(title="S2, retrieval only",
         need="A resolved steep fall in fidelity from the published values to new values (T1)",
         source="A resolved steep fall in fidelity from the published values to new values (T1)", tests=["T1"],
         code="S2"),
    dict(title="S6, rising fidelity",
         need="A resolved rise in fidelity across the generations of the model's family (T5), whatever the class of "
              "the current model; checked before S1",
         source="A resolved rise in fidelity across the generations of the model's family (T5), whatever the class of "
                "the current model; checked before S1", tests=["T5"], code="S6"),
    dict(title="S5, family-specific",
         need="The models of one family receive different overall classes",
         source="The models of one family receive different overall classes", tests=[], code="S5"),
    dict(title="Reversed ordering, manipulation not identified",
         need="Fidelity rises down the argument-strength ordering (T3) without that recognition. Reported as a "
              "difference from people with no account attached.",
         source="(6) a reversed ordering without that recognition, which we report as a difference from people with "
                "no account attached", tests=["T3"]),
    dict(title="S1, high fidelity",
         need="HIGH overall class and no effect classed LOW or ANTI; no resolved steep fall from the published values "
              "to new values (T1); no resolved decline or reversal down the argument-strength ordering (T3); the model "
              "shows each of its effects without identifying the manipulation (T2)",
         source="HIGH overall class and no effect classed LOW or ANTI; no resolved steep fall from the published values "
                "to new values (T1); no resolved decline or reversal down the argument-strength ordering (T3); the "
                "model shows each of its effects without identifying the manipulation (T2)", tests=[], code="S1"),
    dict(title="S3, reason construction",
         need="A resolved decline in fidelity down the argument-strength ordering (T3)",
         source="A resolved decline in fidelity down the argument-strength ordering (T3)", tests=["T3"], code="S3"),
    dict(title="Mixed pattern",
         need="HIGH on some effects and LOW or ANTI on others. Reported as a mixed pattern, with each effect's class "
              "and account side by side.",
         source="(9) a mixed pattern, HIGH on some effects and LOW or ANTI on others, which we report as a mixed "
                "pattern, with each effect's class and account side by side", tests=[]),
    dict(title="S4, systematic inversion",
         need="Second way: an ANTI overall class without recognition (systematic inversion)",
         source="Second way: an ANTI overall class without recognition (systematic inversion)", tests=["T2"],
         code="S4"),
]
NONE_ROW = dict(title="None of the ten applies",
                need="We report the model by the result of each test, under the two rules of Step 4.",
                source="We report a model that matches none by the result of each test, under the two rules of Step 4",
                tests=[])

# The registered one-line conclusion of each scenario (Table 4); checked against the source when present.
CONCLUSIONS = {
    "S1": "The model reproduces the human context effects we tested; synthetic respondents are defensible within the "
          "tested scope.",
    "S2": "The model reproduces effects described in the literature and does not simulate people facing new stimuli; "
          "validation on new stimuli is required before a synthetic panel is trusted.",
    "S3": "The model matches people less closely as the choice sets offer weaker reasons that can be stated, and least "
          "closely on the extremity effect, whose menu offers none.",
    "S4": "When asked, the model identifies the manipulation, and its choices do not follow it, or, without "
          "identifying it, its effects run opposite to people's; either way, synthetic data from it would "
          "systematically remove or reverse the effects consumer research studies.",
    "S5": "No statement holds for language models as a class; each model needs its own validation.",
    "S6": "Fidelity is higher in the newer model of this family; the comparison across generations measures the size "
          "of the difference.",
    "S7": "The human replication is the main contribution; the effects that missed the replication criterion, named "
          "in the report, were not detected under calibrated testing with high power.",
}

# Where each planted scenario of synth.py is expected to land (an index into STEPS, or a key below).
PLANTED_LANDING = {"S1": 6, "S2": 2, "S3": 7, "S4": 1, "S5": 4, "S6": 3, "WALK1": 2, "WALK2": 8,
                   "GATE_CEILING": "step0", "GATE_REFUSAL": "step0", "REVERSED_LADDER_OVERRIDE": 0,
                   "REVERSED_LADDER": 5, "COMPOSITE": "none"}
SCENARIO_ROW = {"REVERSED_LADDER_OVERRIDE": 0, "S2": 2, "S6": 3, "S5": 4, "REVERSED_LADDER": 5, "S1": 6, "S3": 7,
                "PARTIAL": 8}


def plain_t1(r):
    s = r["reading"]
    if s.startswith("uninformative"):
        return "Not interpreted: a positive control failed in people."
    if s.startswith("steep"):
        return "Fidelity falls steeply from the published values to the new values, and the fall is resolved: the " \
               "pattern fits retrieval of published results (S2)."
    if s.startswith("flat"):
        return "Fidelity does not change between the two tiers, and this is resolved: retrieval alone does not " \
               "explain how the model responds to the choice sets."
    if s.startswith("not resolved"):
        return "Not resolved: the interval is too wide to decide, so no scenario is based on this test."
    if s.startswith("non-monotone"):
        return "Neither a steep fall nor no difference: described only."
    if s.startswith("insufficient"):
        return "Not computed: the model has too few readable tiers."
    raise SystemExit(f"unknown memorization label: {s!r}")


def plain_t2(s):
    if s.startswith("uninformative"):
        return "Not interpreted: a positive control failed in people."
    if s.startswith("recognizes-but-does-not-show"):
        return "Identifies the manipulation and does not show the effect (rational override)."
    if s.startswith("recognizes-and-shows"):
        return "Identifies the manipulation and shows the effect (reproduction of a known effect)."
    if s.startswith("shows-without-recognizing"):
        return "Shows the effect without identifying the manipulation."
    if s.startswith("neither"):
        return "Neither identifies the manipulation nor shows the effect."
    if s.startswith("no pooled estimate"):
        return "No pooled estimate (the effect failed in people or was not scored)."
    if s.startswith("not resolved"):
        return "Not resolved: the interval is too wide to decide."
    raise SystemExit(f"unknown recognition label: {s!r}")


def plain_t3(r):
    s = r["reading"]
    if s.startswith("uninformative"):
        return "Not interpreted: a positive control failed in people."
    if s.startswith("declines"):
        return "Fidelity declines down the argument-strength ordering, and the decline is resolved: the pattern fits " \
               "reason construction (S3)."
    if s.startswith("reversed"):
        if r.get("attribution", "").startswith("rational override"):
            return "Fidelity rises down the ordering, and the model identifies the manipulation where it misses the " \
                   "effect: rational override on the choice sets that give an argument."
        return "Fidelity rises down the ordering, without that recognition: a difference from people with no account " \
               "attached."
    if s.startswith("flat"):
        return "No difference between the top and the bottom of the ordering, and this is resolved: no support for " \
               "reason construction."
    if s.startswith("not resolved"):
        return "Not resolved: the interval is too wide to decide, so no scenario is based on this test."
    if s.startswith("insufficient"):
        return "Not computed: too few positions of the ordering have a scored effect."
    raise SystemExit(f"unknown argument-strength label: {s!r}")


def plain_t5(r):
    s = r["trajectory"]
    if s.startswith("uninformative"):
        return "Not interpreted: a positive control failed in people."
    if s.startswith("newer more faithful"):
        return "Fidelity rises from the older to the newer model, and the rise is resolved: rising fidelity (S6)."
    if s.startswith("newer less faithful"):
        return "Fidelity falls from the older to the newer model: reported, with no scenario."
    if s.startswith("flat across"):
        return "No difference between the generations: the size of the difference is reported."
    if s.startswith("not resolved"):
        return "Not resolved: the interval is too wide to decide."
    if s.startswith("insufficient"):
        return "Not computed: this family has no older and newer model in the design."
    raise SystemExit(f"unknown trajectory label: {s!r}")


def plain_reasoning(s):
    if not s:
        return ""
    if s.startswith("reasoning-on lowers fidelity"):
        return "Switching reasoning on lowers fidelity: reported beside the knows-it-versus-shows-it result."
    if s.startswith("reasoning-on raises"):
        return "Switching reasoning on raises fidelity: reported by its size."
    if s.startswith("flat") or s.startswith("no difference"):
        return "Switching reasoning on does not change fidelity: reported by its size."
    if s.startswith("not resolved"):
        return "Reasoning comparison not resolved."
    raise SystemExit(f"unknown reasoning label: {s!r}")


def plain_account(s):
    s = s.strip()
    table = [
        ("deep pattern-mimicry", "deep mimicry"),
        ("rational-override", "rational override"),
        ("reproduction of a known effect", "reproduction of a known effect"),
        ("systematic inversion", "systematic inversion (no account)"),
        ("partial", "PARTIAL, reported by its class"),
        ("low fidelity", "LOW, reported by its class"),
        ("overshoot on the phantom", "OVER on the phantom: consistent with retrieval of a published finding"),
        ("overshoot", "OVER, reported by its class"),
        ("human-null", "not scored: the effect failed in people"),
        ("uninformative", "not interpreted: a positive control failed"),
        ("descriptive", "described only"),
        ("not scorable", "not scored"),
    ]
    for prefix, text in table:
        if s.startswith(prefix):
            if prefix == "human-null" and "without a human counterpart" in s:
                text += "; the model shows an effect people do not show"
            return text
    raise SystemExit(f"unknown account label: {s!r}")


def plain_class(cls):
    """The class column of effect_classes.csv, in the paper's words; the five classes print as they are."""
    if cls in ("HIGH", "OVER", "PARTIAL", "LOW", "ANTI", ""):
        return cls
    if cls.startswith("excluded"):
        return "not classed"
    if cls.startswith("no-human-counterpart"):
        return "not classed: the model shows an effect that people do not show"
    if cls.startswith("uninformative"):
        return "not classed: a positive control failed"
    if cls.startswith("descriptive"):
        return "described only"
    raise SystemExit(f"unknown class label: {cls!r}")


def plain_model_account(s):
    m = re.match(r"(.*?) \((\d+) of (\d+) eligible effects agree\)$", s)
    if s.startswith("none (model not assessable)"):
        return "No account: the model is not assessable."
    if not m:
        raise SystemExit(f"unknown model-level account: {s!r}")
    acc, n, k = m.group(1), m.group(2), m.group(3)
    if acc == "per-effect only":
        return f"No account explains the model as a whole: at most {n} of {k} eligible effects support the same one."
    # a class is not an account: a majority of PARTIAL, LOW, OVER or uncued ANTI effects is reported by its class
    by_class = {"partial": "PARTIAL", "low fidelity": "LOW", "overshoot": "OVER"}
    if acc in by_class:
        return (f"No account explains the model as a whole: {n} of {k} eligible effects are {by_class[acc]}, which we "
                f"report by class.")
    if acc == "systematic inversion":
        return (f"No account explains the model as a whole: {n} of {k} eligible effects are ANTI without identification "
                f"of the manipulation (systematic inversion).")
    names = {"deep pattern-mimicry": "deep mimicry", "rational override": "rational override",
             "reproduction of a known effect": "reproduction of a known effect",
             "retrieval of a described regularity": "retrieval of a published finding"}
    if acc not in names:
        raise SystemExit(f"unknown model-level account: {acc!r}")
    return f"{names[acc]}: {n} of {k} eligible effects support it (four are needed)."


def landing(row):
    """Where the code's route ends: an index into STEPS, or 'step0', 'open', 'none' or 's4either'."""
    sc, br = row["scenario"], row["branch"]
    if sc == "CRITERION_FAIL":
        return "step0"
    if sc == "NOT_RESOLVED":
        return "open"
    if sc == "COMPOSITE":
        return "none"
    if br.startswith("S4: reached whichever way"):
        return "s4either"
    if sc == "S4":
        return 1 if br.startswith("T2") else 9
    if sc not in SCENARIO_ROW:
        raise SystemExit(f"unknown scenario code: {sc!r}")
    return SCENARIO_ROW[sc]


def possible_rows(text):
    out = []
    for code in [c for c in text.split(";") if c]:
        if code == "S4":
            out += [1, 9]
        elif code == "S7":
            continue
        elif code in SCENARIO_ROW:
            out.append(SCENARIO_ROW[code])
        elif code == "COMPOSITE":
            out.append("none")
        else:
            raise SystemExit(f"unknown possible scenario: {code!r}")
    return out


def read(name):
    with open(os.path.join(PACK, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def check_against_manuscript():
    if not MANUSCRIPT or not os.path.exists(MANUSCRIPT):
        return
    text = open(MANUSCRIPT, encoding="utf-8").read().replace("\r\n", "\n")
    for code, sentence in CONCLUSIONS.items():
        if sentence not in text:
            raise SystemExit(f"the conclusion printed for {code} differs from Table 4 of the manuscript")
    for i, s in enumerate(STEPS + [NONE_ROW], 1):
        if s["source"] not in text:
            raise SystemExit(f"row {i} of the checking order differs from the Analysis Plan or Table 4: "
                             f"{s['source'][:70]!r}")


def build():
    check_against_manuscript()
    numbers = json.load(open(os.path.join(PACK, "numbers.json"), encoding="utf-8"))
    routing_all = read("tree_routing.csv")
    routing = [r for r in routing_all if not r["model"].startswith("(")]
    human_s7 = next((r for r in routing_all if r["model"].startswith("(")), None)
    criteria = read("validity_criteria.csv")
    human = {g["key"]: g for g in criteria if g["gate_type"] == "human_effect"}
    classes = read("effect_classes.csv")
    agree = {r["model"]: r for r in read("agreement_scores.csv")}
    t1 = {r["model"]: r for r in read(os.path.join("tests", "T1_memorization.csv"))}
    t2 = read(os.path.join("tests", "T2_recognition.csv"))
    t3 = {r["model"]: r for r in read(os.path.join("tests", "T3_ladder.csv"))}
    t5 = {r["model"]: r for r in read(os.path.join("tests", "T5_trajectory.csv"))}
    bench = [b for b in read("human_benchmarks.csv") if b["category"] == "pooled" and b["format"] == "numbers"]

    people = []
    for code in ORDER:
        g = human.get(code)
        if g is None:
            continue
        tiers = [dict(tier=TIERS[b["tier"]], est=num(b["effect_pp"]), lo=num(b["ci_lo_pp"]), hi=num(b["ci_hi_pp"]))
                 for b in bench if b["effect"] == code and b["tier"] in TIERS]
        people.append(dict(code=code, name=EFFECTS[code], short=SHORT[code], replicated=g["replicated"] == "True",
                           delta=num(g["delta_pp"]), bf=num(g["bf10"]), control=g["is_positive_control"] == "True",
                           tiers=tiers))
    failing = sum(1 for p in people if p["code"] != "SIM" and not p["replicated"])

    models = []
    for r in routing:
        m = r["model"]
        if m not in MODELS or m not in MODEL_ARCHETYPES:
            raise SystemExit(f"no plain description or planted scenario for the simulated model {m!r}")
        accounts = {}
        for part in r["per_effect_accounts"].split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                accounts[k] = plain_account(v)
        eff = []
        for c in classes:
            if c["model"] != m:
                continue
            cls = plain_class(c["class"] or c["descriptive_class"] or "")
            eff.append(dict(code=c["effect"], name=EFFECTS[c["effect"]], short=SHORT[c["effect"]],
                            human=num(c["human_pp"]), model=num(c["model_pp"]), cls=cls,
                            account=accounts.get(c["effect"], ""), onmap=c["effect"] != "SIM"))
        eff.sort(key=lambda e: ORDER.index(e["code"]))
        tally = {}
        for e in eff:
            if e["onmap"] and e["cls"] in ("HIGH", "OVER", "PARTIAL", "LOW", "ANTI"):
                tally[e["cls"]] = tally.get(e["cls"], 0) + 1
        rec = []
        for x in t2:
            if x["model"] == m:
                rec.append(dict(code=x["structure"], short=SHORT.get(x["structure"], x["structure"]),
                                rate=num(x["recognition_rate"]), effect=num(x["behavior_pp"]),
                                knows=x["knows"] == "True", shows=x["shows"] == "True",
                                open=(x["knows_state"] == "U" or x["shows_state"] == "U"), text=plain_t2(x["reading"])))
        rec.sort(key=lambda e: ORDER.index(e["code"]) if e["code"] in ORDER else 99)
        a1, a3, a5 = t1.get(m, {}), t3.get(m, {}), t5.get(m, {})
        top, bottom = num(a3.get("high_rung")), num(a3.get("low_rung"))
        land = landing(r)
        planted = PLANTED_LANDING.get(MODEL_ARCHETYPES[m]["scenario"])
        if planted is None:
            raise SystemExit(f"no landing for the planted scenario {MODEL_ARCHETYPES[m]['scenario']!r}")
        possible = possible_rows(r["possible_scenarios"]) if land == "open" else []
        as_built = (land == planted or (land == "s4either" and planted in (1, 9))
                    or (land == "open" and planted in possible))
        g = f"model.{m}.criterion."
        models.append(dict(
            id=m, name=MODELS[m][0], planted=MODELS[m][1], family=r["family"],
            step0=dict(parse=numbers.get(g + "parse_rate"), refusal=numbers.get(g + "refusal_rate"),
                      lost=numbers.get(g + "frac_cells_lost"), noroom=numbers.get(g + "n_no_room_cells"),
                      assessable=numbers.get(g + "not_assessable") is False),
            overall=(agree.get(m, {}).get("class") or ""), sign=num(agree.get(m, {}).get("sign_agreement")),
            mad=num(agree.get(m, {}).get("mad_pp")), slope=num(agree.get(m, {}).get("calibration_slope")),
            effects=eff, tally=tally, recognition=rec,
            t1=dict(pub=num(a1.get("fidelity_t1")), new=num(a1.get("fidelity_t2")), drop=num(a1.get("drop")),
                    lo=num(a1.get("drop_lo")), hi=num(a1.get("drop_hi")), text=plain_t1(a1) if a1 else ""),
            t3=dict(top=top, mid=num(a3.get("mid_rung")), bottom=bottom,
                    tmb=(round(top - bottom, 3) if top is not None and bottom is not None else None),
                    lo=num(a3.get("tmb_lo")), hi=num(a3.get("tmb_hi")), text=plain_t3(a3) if a3 else ""),
            t5=dict(delta=num(a5.get("delta")), lo=num(a5.get("traj_lo")), hi=num(a5.get("traj_hi")),
                    text=plain_t5(a5) if a5 else "", reasoning=plain_reasoning(a5.get("reasoning_reading", ""))),
            land=land, possible=possible, planted_land=planted, as_built=as_built,
            qualifier=bool(r["qualifier"]), open_tests=[t for t in r.get("open_pattern_tests", "").split(";") if t],
            conclusion=CONCLUSIONS.get(r["scenario"], ""), model_account=plain_model_account(r["model_level_account"])))

    cut = dict(t1_steep=RC.T1_STEEP_DROP, t1_flat=RC.T1_FLAT_SLOPE, t3_step=RC.T3_LADDER_STEP,
               t3_flat=RC.T3_LADDER_FLAT, t5_step=RC.T5_TRAJECTORY_STEP, recog=RC.RECOGNITION_CUTOFF,
               show=RC.ANTI_MIN_PP, high=RC.HIGH_RATIO, over=RC.OVER_RATIO, partial=RC.PARTIAL_RATIO,
               near_null=RC.NEAR_NULL_HUMAN_PP, s7=RC.MOST_FAILED_MIN)
    data = dict(people=people, failing=failing, models=models,
                steps=[{k: s[k] for k in ("title", "need", "tests")} | {"code": s.get("code", "")}
                       for s in STEPS + [NONE_ROW]],
                cut=cut, conclusions=CONCLUSIONS, s7=bool(human_s7 and human_s7["scenario"] == "S7"))
    # the rehearsal's human sample per cell, read from the code that sets it (the page states it)
    found = re.search(r"\n    N_HUMAN = (\d+)", open(os.path.join(ANALYSIS, "analyze.py"), encoding="utf-8").read())
    if not found:
        raise SystemExit("the rehearsal's N_HUMAN was not found in analyze.py")
    page = PAGE.replace("__NHUMAN__", f"{int(found.group(1)):,}").replace("__NMODELS__", str(len(models)))
    page = page.replace("__DATA__", json.dumps(data, sort_keys=True, separators=(",", ":")).replace("</", "<\\/"))
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print(f"wrote {os.path.normpath(OUT)} ({len(models)} simulated models)")


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Analysis explorer</title>
<style>
:root{--ink:#22201c;--ink2:#6a645b;--ink3:#9a9389;--rule:#e6e1d8;--card:#ffffff;--bg:#f7f5f1;--soft:#f1ede6;
--human:#0f7c8a;--model:#6b4fbb;--accent:#da7756;--accent-soft:#fbeee8;
--HIGH:#2e7d4f;--OVER:#b8860b;--PARTIAL:#6f8193;--LOW:#9a958c;--ANTI:#c0392b;--open:#c9891b}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
button{font:inherit;color:inherit}
.top{max-width:1240px;margin:0 auto;padding:28px 20px 8px}
.top h1{font-size:26px;line-height:1.2;margin:0 0 10px;letter-spacing:-.01em}
.top p{margin:0 0 8px;color:var(--ink2);max-width:880px}
.top .small{font-size:13px;color:var(--ink3)}
code,.mono{font-family:Consolas,Menlo,monospace;font-size:12.5px}
.tabs{max-width:1240px;margin:8px auto 0;padding:0 20px;display:flex;gap:6px;flex-wrap:wrap}
.tabs button{border:1px solid var(--rule);background:var(--card);border-radius:999px;padding:7px 16px;cursor:pointer}
.tabs button.on{background:var(--ink);border-color:var(--ink);color:#fff}
.view{max-width:1240px;margin:0 auto;padding:16px 20px 40px}
.one{display:grid;grid-template-columns:290px minmax(0,1fr);gap:18px;align-items:start}
.picker{display:flex;flex-direction:column;gap:6px}
.picker .lbl{font-size:12px;color:var(--ink3);text-transform:uppercase;letter-spacing:.06em;margin:2px 4px}
.pick{display:block;width:100%;text-align:left;border:1px solid var(--rule);background:var(--card);border-radius:12px;padding:9px 12px;cursor:pointer;transition:border-color .15s,box-shadow .15s}
.pick:hover{border-color:#d3cabb}
.pick.on{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.pick .nm{font-weight:600;font-size:14px;line-height:1.3}
.pick .to{font-size:12px;color:var(--ink2);margin-top:2px}
.stage{background:var(--card);border:1px solid var(--rule);border-radius:18px;overflow:hidden;min-width:0}
.head{padding:18px 22px 12px;border-bottom:1px solid var(--rule)}
.head h2{margin:0;font-size:20px}
.head .planted{color:var(--ink2);margin-top:4px}
.head .code{color:var(--ink3);font-size:12px;margin-top:2px}
.rail{display:flex;align-items:center;gap:0;padding:14px 22px;border-bottom:1px solid var(--rule);overflow-x:auto}
.rail .dot{display:flex;align-items:center;gap:8px;border:0;background:none;cursor:pointer;padding:4px 6px;border-radius:999px;white-space:nowrap;color:var(--ink3)}
.rail .dot i{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;border:2px solid var(--rule);font-style:normal;font-size:12px;font-weight:700;background:var(--card)}
.rail .dot.done{color:var(--ink2)}.rail .dot.done i{border-color:var(--ink2);background:var(--soft)}
.rail .dot.on{color:var(--ink)}.rail .dot.on i{border-color:var(--accent);background:var(--accent);color:#fff}
.rail .dot.skip{opacity:.4}
.rail .bar{flex:1 1 16px;min-width:12px;height:2px;background:var(--rule)}
.controls{display:flex;gap:8px;align-items:center;padding:12px 22px;border-bottom:1px solid var(--rule);flex-wrap:wrap}
.controls button{border:1px solid var(--rule);background:var(--card);border-radius:999px;padding:7px 14px;cursor:pointer}
.controls button:disabled{opacity:.4;cursor:default}
.controls .play{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600;min-width:110px}
.controls .hint{color:var(--ink3);font-size:12.5px;margin-left:auto}
.panel{padding:18px 22px 22px;min-height:420px}
.q{font-size:18px;font-weight:600;margin:0 0 4px}
.qs{color:var(--ink2);margin:0 0 14px;max-width:820px}
.where{font-size:12.5px;color:var(--ink3);border-top:1px solid var(--rule);padding:10px 22px;background:#fcfbf9}
.cols{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:22px;align-items:start}
.box{border:1px solid var(--rule);border-radius:14px;padding:12px 14px;background:#fff}
.box h3{font-size:14px;margin:0 0 8px}
.gauge{margin:10px 0 14px}.gauge .t{display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px}
.gauge .gt{position:relative;height:14px;border-radius:7px;background:var(--soft)}
.gauge .fill{position:absolute;left:0;top:0;bottom:0;border-radius:7px}
.gauge .mark{position:absolute;top:-4px;bottom:-4px;width:2px;background:var(--ink)}
.gauge .mk{font-size:11.5px;color:var(--ink3);margin-top:3px}
.stamp{display:inline-block;margin-top:6px;padding:8px 14px;border-radius:12px;font-weight:600;transition:opacity .2s}
.ok{color:var(--HIGH)}.no{color:var(--ANTI)}
.stamp.ok{background:#e8f3ec;color:var(--HIGH)}.stamp.no{background:#f8e5e2;color:var(--ANTI)}.stamp.mid{background:#fbf1de;color:#8a5a00}
.prow{display:grid;grid-template-columns:24px 1fr auto;gap:8px;align-items:center;padding:5px 0;border-bottom:1px solid var(--rule);font-size:13.5px}
.prow:last-child{border-bottom:0}
.tick{display:inline-grid;place-items:center;width:20px;height:20px;border-radius:50%;font-size:12px;font-weight:700;color:#fff;transition:transform .25s,opacity .25s}
.tag{font-size:11px;border:1px solid var(--rule);border-radius:999px;padding:0 7px;color:var(--ink2)}
.chip{display:inline-block;border-radius:6px;padding:1px 7px;color:#fff;font-size:12px;font-weight:700;letter-spacing:.02em}
table.t{border-collapse:collapse;width:100%;font-size:13px}
table.t th,table.t td{text-align:left;padding:5px 6px;border-bottom:1px solid var(--rule);vertical-align:top}
table.t th{color:var(--ink3);font-weight:600;font-size:12px}
.tests{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px}
.test{border:1px solid var(--rule);border-radius:14px;padding:12px 14px;transition:border-color .2s,box-shadow .2s}
.test.focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.test h3{font-size:14px;margin:0 0 2px}.test .what{font-size:12.5px;color:var(--ink2);margin:0 0 6px}
.verdict{margin-top:6px;padding:7px 10px;border-radius:10px;background:var(--soft);font-size:13px;transition:opacity .25s}
.ladder{position:relative;margin:4px 0 0 0}
.lrow{position:relative;display:grid;grid-template-columns:44px 1fr;gap:10px;align-items:start;padding:7px 10px 7px 0;border-radius:12px;transition:background .2s}
.lrow .n{display:grid;place-items:center;width:28px;height:28px;margin-left:8px;border-radius:50%;border:2px solid var(--rule);background:#fff;font-size:12px;font-weight:700;color:var(--ink3);position:relative;z-index:1}
.lrow .tt{font-weight:600;font-size:14px}.lrow .nd{font-size:12.5px;color:var(--ink2)}
.lrow .st{font-size:12px;color:var(--ink3);margin-top:1px}
.lrow.passed .n{border-color:var(--ink3);color:var(--ink3)}
.lrow.passed .tt{color:var(--ink2)}
.lrow.hit{background:var(--accent-soft)}.lrow.hit .n{border-color:var(--accent);background:var(--accent);color:#fff}
.lrow.maybe{background:#fbf1de}.lrow.maybe .n{border-color:var(--open);color:#8a5a00}
.track{position:absolute;left:21px;top:20px;bottom:20px;width:2px;background:var(--rule)}
.token{position:absolute;left:12px;width:20px;height:20px;border-radius:50%;background:var(--model);box-shadow:0 0 0 4px rgba(107,79,187,.18);z-index:2}
.concl{margin-top:14px;border-radius:14px;padding:14px 16px;border:1px solid var(--accent);background:#fff;transition:opacity .3s,transform .3s}
.concl .k{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--accent);font-weight:700}
.concl .h{font-size:17px;font-weight:600;margin:2px 0 6px}
.concl p{margin:6px 0 0}
.built{display:inline-block;margin-top:8px;font-size:13px;padding:3px 10px;border-radius:999px;background:#e8f3ec;color:var(--HIGH);font-weight:600}
.built.no{background:#f8e5e2;color:var(--ANTI)}.built.mid{background:#fbf1de;color:#8a5a00}
svg{display:block;max-width:100%;height:auto}
svg text{font:11.5px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;fill:var(--ink2)}
/* all models */
.sorter{background:var(--card);border:1px solid var(--rule);border-radius:18px;padding:16px 18px}
.sorter .bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.sorter .bar button{border:1px solid var(--rule);background:var(--card);border-radius:999px;padding:7px 14px;cursor:pointer}
.sorter .bar .play{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.srow{display:grid;grid-template-columns:minmax(180px,300px) 1fr;gap:12px;align-items:center;padding:8px 6px;border-top:1px solid var(--rule)}
.srow .ln{font-weight:600;font-size:13.5px}.srow .ld{font-size:12px;color:var(--ink3)}
.slots{display:flex;gap:6px;flex-wrap:wrap;min-height:30px;align-items:center}
.mchip{border:1px solid var(--rule);background:#fff;border-radius:999px;padding:4px 11px;font-size:12.5px;cursor:pointer;display:inline-flex;gap:6px;align-items:center}
.mchip b{display:inline-grid;place-items:center;width:16px;height:16px;border-radius:50%;font-size:10px;color:#fff;background:var(--HIGH)}
.mchip b.mid{background:var(--open)}.mchip b.no{background:var(--ANTI)}
.mchip.drop{animation:drop .55s cubic-bezier(.2,.9,.3,1.2) both}
@keyframes drop{from{opacity:0;transform:translateY(-26px) scale(.9)}to{opacity:1;transform:none}}
.s7{margin:0 0 12px;padding:10px 12px;border-radius:12px;background:var(--soft);font-size:13px;color:var(--ink2)}
/* files */
.flow{display:flex;flex-direction:column;align-items:stretch;gap:0;max-width:900px}
.fbox{background:var(--card);border:1px solid var(--rule);border-radius:14px;padding:12px 14px}
.fbox .fp{font-family:Consolas,Menlo,monospace;font-size:13px;font-weight:700}
.fbox .fd{color:var(--ink2);font-size:13.5px;margin-top:2px}
.farrow{display:flex;align-items:center;gap:10px;padding:6px 0 6px 24px;color:var(--ink3);font-size:12.5px}
.farrow:before{content:"";width:2px;height:22px;background:var(--rule)}
.frow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
@media (max-width:980px){.one{grid-template-columns:1fr}.picker{position:static;flex-direction:row;overflow-x:auto;padding-bottom:4px}
.pick{min-width:210px}.picker .lbl{display:none}.cols,.tests{grid-template-columns:1fr}.frow{grid-template-columns:1fr}
.srow{grid-template-columns:1fr}.controls .hint{display:none}}
@media (max-width:560px){.top h1{font-size:21px}.panel{padding:14px}.head,.rail,.controls,.where{padding-left:14px;padding-right:14px}}
</style></head><body>
<div class="top">
<h1>How the registered analysis reaches a conclusion for each model</h1>
<p>Before collecting any data, we ran the analysis code on simulated people and on __NMODELS__ simulated models, each
built to behave in one known way. Choose a model and press Play. The page shows the five steps of the Analysis Plan in
order, with the numbers the code wrote for that model, and ends at the scenario the code assigned to it.</p>
<p class="small">The page reaches no result of its own. Every class, test result and scenario is read from
<code>analysis/results_pack/</code>, which <code>analysis/analyze.py</code> writes, every cutoff from
<code>analysis/registered_constants.py</code>, and what each model was built to show from <code>analysis/synth.py</code>.
The simulated people make __NHUMAN__ choices per cell, more than the planned 350 to 700, so that each planted pattern is
clear: the run checks which branch of the decision tree the code takes for each pattern. How often a test reaches a
conclusion at the planned sizes is reported in Web Appendix E (Table WA-E4); at those sizes we do not expect a
conclusion of no difference on the memorization, argument-strength and trajectory tests.</p>
</div>
<div class="tabs" role="tablist"><button class="on" data-v="one">One model, step by step</button><button data-v="all">All __NMODELS__ models at once</button><button data-v="files">Where the files are</button></div>
<div class="view" id="v-one"><div class="one"><div class="picker" id="picker"></div>
<div class="stage"><div class="head" id="head"></div><div class="rail" id="rail"></div>
<div class="controls"><button class="play" id="play">Play</button><button id="back">Back</button><button id="next">Next</button><button id="restart">Start again</button><span class="hint">Space plays or pauses; the arrow keys move between steps.</span></div>
<div class="panel" id="panel"></div><div class="where" id="where"></div></div></div></div>
<div class="view" id="v-all" hidden></div>
<div class="view" id="v-files" hidden></div>
<script>
const D = __DATA__;
const C = D.cut;
const RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const f2 = x => x == null ? 'not computed' : (Math.round(x * 100) / 100).toFixed(2);
const f1 = x => x == null ? 'not computed' : (Math.round(x * 10) / 10).toFixed(1);
const pct = x => x == null ? '' : Math.round(x * 100) + '%';
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const part = (t, a, b) => clamp((t - a) / (b - a), 0, 1);          // the share of [a, b] that t has passed
const CLS = ['HIGH', 'OVER', 'PARTIAL', 'LOW', 'ANTI'];
const col = c => CLS.includes(c) ? `var(--${c})` : 'var(--ink3)';
const chip = c => CLS.includes(c) ? `<span class="chip" style="background:${col(c)}">${c}</span>` : `<span style="color:var(--ink3)">${esc(c || '')}</span>`;
const STEPNAMES = ['Readable', 'People', 'Closeness', 'Pattern tests', 'Scenario'];

// ---------- the five steps, each drawn as a function of its progress values (0 to 1) ----------
let TOK = null;
const rowNum = r => r === 'none' ? 10 : r;
function rowLabel(i) { return D.steps[rowNum(i)].title; }
// the row of the checking order where the code's route ends (-1: stopped at Step 0)
function target(m) {
  if (m.land === 'step0') return -1;
  if (m.land === 'open') return Math.min(...m.possible.map(rowNum));
  if (m.land === 's4either') return 1;
  return rowNum(m.land);
}
function landText(m) {
  if (m.land === 'step0') return 'Stops at Step 0: not assessable as a survey respondent';
  if (m.land === 'open') return 'Not resolved: ' + m.possible.map(rowLabel).join(' or ');
  if (m.land === 's4either') return 'S4, either way';
  return rowLabel(m.land);
}

function step0(m, p) {
  const g = m.step0;
  const ppl = D.people.map((e, i) => {
    const on = p.a >= (i + 1) / D.people.length;
    return `<div class="prow"><span class="tick" style="background:${e.replicated ? 'var(--HIGH)' : 'var(--ANTI)'};opacity:${on ? 1 : 0};transform:scale(${on ? 1 : .4})">${e.replicated ? '&#10003;' : '&#10005;'}</span>` +
      `<span>${esc(e.name)} ${e.control ? '<span class="tag">positive control</span>' : ''}</span><span style="opacity:${on ? 1 : 0}" class="${e.replicated ? 'ok' : 'no'}">${e.replicated ? 'replicates' : 'does not replicate'}</span></div>`;
  }).join('');
  const gauge = (label, v, line, lineText, good) => {
    const w = v == null ? 0 : clamp(v, 0, 1) * 100 * ease(p.b);
    return `<div class="gauge"><div class="t"><span>${label}</span><b>${p.b > .05 ? pct(v) : ''}</b></div><div class="gt">` +
      `<div class="fill" style="width:${w}%;background:${good ? 'var(--HIGH)' : 'var(--ANTI)'}"></div><div class="mark" style="left:${line * 100}%"></div></div><div class="mk">${lineText}</div></div>`;
  };
  const parseOk = g.parse != null && g.parse >= 0.95, refOk = g.refusal != null && g.refusal <= 0.05, lostOk = g.lost != null && g.lost <= 1 / 3;
  const stamp = g.assessable ? `<div class="stamp ok" style="opacity:${p.c}">The comparison can be made: on to Step 1</div>`
    : `<div class="stamp no" style="opacity:${p.c}">Not assessable as a survey respondent: the analysis stops here for this model</div>`;
  return `<p class="q">Can the comparison be made at all?</p><p class="qs">Two validity criteria come first. An effect must be present in people before a model can be asked to match it, and the model's answers must be readable.</p>` +
    `<div class="cols"><div class="box"><h3>In people: does each effect replicate?</h3>${ppl}` +
    `<p class="qs" style="margin:10px 0 0;font-size:13px;opacity:${part(p.a, .85, 1)}">${D.failing} of the six effects other than similarity ${D.failing === 1 ? 'fails' : 'fail'} in people. If four or more failed, every model would be reported under S7 and the model comparison only described.</p></div>` +
    `<div class="box"><h3>This model's answers</h3>` +
    gauge('Answers from which a choice can be read', g.parse, .95, 'At least 95% needed (line)', parseOk) +
    gauge('Refusals', g.refusal, .05, 'At most 5% allowed (line)', refOk) +
    gauge('Cells lost to refusals, unreadable answers or ceilings', g.lost, 1 / 3, `At most one third allowed (line)${g.noroom ? `; ${g.noroom} cells where one option takes more than 90% of choices` : ''}`, lostOk) +
    stamp + `</div></div>`;
}

function step1(m, p) {
  const max = Math.max(20, ...D.people.map(e => Math.max(e.delta || 0, ...e.tiers.map(t => t.hi || 0))));
  const W = 640, L = 170, R = 20, rowH = 46, H = D.people.length * rowH + 56;
  const x = v => L + (clamp(v, -4, max) + 4) / (max + 4) * (W - L - R);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="human effects by tier">`;
  for (let t = 0; t <= max; t += 5) s += `<line x1="${x(t)}" x2="${x(t)}" y1="10" y2="${H - 42}" stroke="#eee8de"/><text x="${x(t)}" y="${H - 26}" text-anchor="middle">${t}</text>`;
  s += `<line x1="${x(0)}" x2="${x(0)}" y1="10" y2="${H - 42}" stroke="#bdb5a8"/>`;
  const marks = {'published values': '#0f7c8a', 'new values': '#3aa6b3', 'invented categories': '#93cdd4'};
  D.people.forEach((e, i) => {
    const y = 20 + i * rowH, t = ease(part(p.a, i / D.people.length * .6, i / D.people.length * .6 + .4));
    s += `<text x="0" y="${y + 13}" style="font-weight:600;fill:#22201c">${esc(e.short)}</text>`;
    s += `<text x="0" y="${y + 28}">${e.replicated ? 'replicates' : 'fails in people'}</text>`;
    const v = (e.delta || 0) * t;
    s += `<rect x="${Math.min(x(0), x(v))}" y="${y + 2}" width="${Math.abs(x(v) - x(0))}" height="14" rx="4" fill="${e.replicated ? 'var(--human)' : '#bdb5a8'}"/>`;
    if (t > .9) s += `<text x="${x(v) + (v >= 0 ? 6 : -6)}" y="${y + 13}" text-anchor="${v >= 0 ? 'start' : 'end'}" style="fill:#22201c">${f1(e.delta)} points</text>`;
    e.tiers.forEach((tr, k) => {
      const yy = y + 24 + k * 6, o = part(p.b, k / 3, k / 3 + .34);
      if (tr.lo != null && tr.hi != null) s += `<line x1="${x(tr.lo)}" x2="${x(tr.hi)}" y1="${yy}" y2="${yy}" stroke="${marks[tr.tier]}" stroke-width="2" opacity="${o}"/>`;
      if (tr.est != null) s += `<circle cx="${x(tr.est)}" cy="${yy}" r="2.6" fill="${marks[tr.tier]}" opacity="${o}"/>`;
    });
  });
  s += `<text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">effect in people (percentage points)</text></svg>`;
  const legend = Object.entries(marks).map(([k, c]) => `<span style="display:inline-flex;align-items:center;gap:5px;margin-right:12px"><span style="width:14px;height:3px;background:${c};display:inline-block"></span>${k}</span>`).join('');
  return `<p class="q">How large is each effect in people?</p><p class="qs">These are the benchmarks every model is compared with, the same for all simulated models. The thick bar is the pooled effect; below it, the estimate and 95% interval on each stimulus tier.</p>` +
    `<div class="box">${s}<div style="font-size:12.5px;color:var(--ink2);margin-top:6px;opacity:${p.b}">${legend}</div></div>`;
}

function fidelityMap(m, p) {
  const pts = m.effects.filter(e => e.onmap && e.human != null && e.model != null);
  const xmax = Math.max(14, ...pts.map(e => e.human)) * 1.15, xmin = Math.min(0, ...pts.map(e => e.human)) - 1.5;
  const ymax = Math.max(xmax * 1.6, ...pts.map(e => e.model * 1.12)), ymin = Math.min(-8, ...pts.map(e => e.model * 1.15));
  const W = 420, H = 400, L = 42, B = 34, T = 10, R = 64;
  const X = v => L + (v - xmin) / (xmax - xmin) * (W - L - R), Y = v => T + (ymax - v) / (ymax - ymin) * (H - T - B);
  const poly = (pts2, c, o) => `<polygon points="${pts2.map(q => X(q[0]) + ',' + Y(clamp(q[1], ymin, ymax))).join(' ')}" fill="${c}" opacity="${o}"/>`;
  const a = C.show, xn = C.near_null;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="fidelity map">`;
  s += `<defs><clipPath id="cp"><rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}"/></clipPath></defs><g clip-path="url(#cp)">`;
  s += poly([[0, ymin], [xmax, ymin], [xmax, -a], [0, -a]], 'var(--ANTI)', .13);
  s += poly([[0, -a], [xmax, -a], [xmax, C.partial * xmax], [0, 0]], 'var(--LOW)', .13);
  s += poly([[0, 0], [xmax, C.partial * xmax], [xmax, C.high * xmax], [0, 0]], 'var(--PARTIAL)', .14);
  s += poly([[0, 0], [xmax, C.high * xmax], [xmax, C.over * xmax], [0, 0]], 'var(--HIGH)', .16);
  s += poly([[0, 0], [xmax, C.over * xmax], [xmax, ymax], [0, ymax]], 'var(--OVER)', .12);
  s += `<rect x="${X(0)}" y="${T}" width="${X(xn) - X(0)}" height="${H - T - B}" fill="#fff" opacity=".75"/>`;
  s += `<line x1="${X(0)}" y1="${Y(0)}" x2="${X(xmax)}" y2="${Y(xmax)}" stroke="#22201c" stroke-width="1.4"/>`;
  s += `</g><line x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}" stroke="#bdb5a8"/><line x1="${X(0)}" x2="${X(0)}" y1="${T}" y2="${H - B}" stroke="#bdb5a8"/>`;
  const lab = (cls, y) => `<text x="${W - R + 6}" y="${clamp(Y(y), T + 10, H - B - 2)}" style="font-weight:700;fill:${col(cls)}">${cls}</text>`;
  s += lab('OVER', Math.min(ymax * .97, (C.over + .35) * xmax)) + lab('HIGH', (C.high + C.over) / 2 * xmax) + lab('PARTIAL', (C.partial + C.high) / 2 * xmax) + lab('LOW', C.partial / 2 * xmax) + lab('ANTI', Math.max(ymin * .6, -a - 4));
  const ang = Math.atan2(Y(0) - Y(xmax), X(xmax) - X(0)) * 180 / Math.PI, v0 = xmax * .2;
  s += `<text transform="translate(${X(v0)} ${Y(v0) - 5}) rotate(${-ang})" style="fill:#22201c">model = people</text>`;
  for (let t = 0; t <= xmax; t += 5) s += `<text x="${X(t)}" y="${H - B + 14}" text-anchor="middle">${t}</text>`;
  s += `<text x="${(L + W - R) / 2}" y="${H - 4}" text-anchor="middle" style="fill:var(--human);font-weight:600">effect in people (points)</text>`;
  s += `<text transform="translate(11 ${(T + H - B) / 2}) rotate(-90)" text-anchor="middle" style="fill:var(--model);font-weight:600">effect in the model (points)</text>`;
  const at = pts.map((e, i) => {
    const t = ease(part(p.a, i / pts.length * .55, i / pts.length * .55 + .45));
    return {e, t, cx: X(e.human), cy: Y(lerp(0, e.model, t))};
  });
  // labels sit to the right of their dots, pushed apart so that no two overlap
  const lab2 = at.slice().sort((u, v) => u.cy - v.cy);
  lab2.forEach((q, i) => { q.ly = q.cy + 4; if (i && q.ly - lab2[i - 1].ly < 14) q.ly = lab2[i - 1].ly + 14; });
  const over = lab2.length ? lab2[lab2.length - 1].ly - (H - B - 4) : 0;
  if (over > 0) lab2.forEach(q => q.ly -= over);
  at.forEach(({e, t, cx, cy, ly}) => {
    const classed = CLS.includes(e.cls), c = p.b > .02 && classed ? col(e.cls) : 'var(--model)';
    s += `<circle cx="${cx}" cy="${cy}" r="7" fill="${classed ? c : '#fff'}" stroke="${classed ? '#fff' : 'var(--ink3)'}" stroke-width="2"/>`;
    if (Math.abs(ly - 4 - cy) > 5) s += `<line x1="${cx + 7}" y1="${cy}" x2="${cx + 16}" y2="${ly - 4}" stroke="#bdb5a8" opacity="${t}"/>`;
    s += `<text x="${cx + 18}" y="${ly}" style="fill:#22201c;opacity:${t}">${esc(e.short)}</text>`;
  });
  return s + '</svg>';
}

function step2(m, p) {
  const rows = m.effects.map((e, i) => {
    const o = part(p.b, i / m.effects.length * .7, i / m.effects.length * .7 + .3);
    return `<tr style="opacity:${.25 + .75 * o}"><td>${esc(e.short)}${e.onmap ? '' : '<div style="font-size:11.5px;color:var(--ink3)">analyzed separately, not on the map</div>'}</td><td>${f1(e.human)}</td><td>${f1(e.model)}</td><td>${o > .5 ? chip(e.cls) : ''}</td><td>${o > .5 ? esc(e.account) : ''}</td></tr>`;
  }).join('');
  const n = Object.values(m.tally).reduce((a, b) => a + b, 0);
  let bar = '<div style="display:flex;height:22px;border-radius:7px;overflow:hidden;background:var(--soft)">', k = 0;
  CLS.forEach(c => { const v = m.tally[c] || 0; if (v) { const w = v / Math.max(n, 1) * 100 * ease(p.c); bar += `<div style="width:${w}%;background:${col(c)};color:#fff;font-size:11.5px;font-weight:700;display:grid;place-items:center;overflow:hidden">${w > 9 ? c + ' ' + v : ''}</div>`; } });
  bar += '</div>';
  return `<p class="q">How close is the model to people on each effect?</p><p class="qs">Each dot is one effect: its position across is the effect in people, its height the effect in the model. The diagonal is a perfect match; the shaded bands are the five fidelity classes. Effects under ${C.near_null} points in people are not classed (white strip).</p>` +
    `<div class="cols"><div class="box">${fidelityMap(m, p)}</div><div><table class="t"><tr><th>Effect</th><th>People</th><th>Model</th><th>Class</th><th>Account for this effect</th></tr>${rows}</table>` +
    `<div style="margin-top:14px;opacity:${p.c > 0 ? 1 : .3}"><div style="font-size:13px;color:var(--ink2);margin-bottom:4px">Classes of the effects other than similarity</div>${bar}</div>` +
    `<div class="stamp ${m.overall === 'HIGH' ? 'ok' : (m.overall === 'ANTI' || m.overall === 'LOW' ? 'no' : 'mid')}" style="opacity:${part(p.c, .7, 1)}">Overall class: ${esc(m.overall || 'none')}</div>` +
    `<p style="font-size:13px;color:var(--ink2);opacity:${part(p.c, .8, 1)}">The most frequent class, ties going to the less faithful one. Sign agreement ${pct(m.sign)}, mean absolute deviation ${f1(m.mad)} points, slope ${f2(m.slope)}.<br><b style="color:var(--ink)">Account for the model as a whole:</b> ${esc(m.model_account)}</p></div></div>`;
}

function numberLine(est, lo, hi, zones, t, label) {
  const W = 420, H = 64, a = -2, b = 2, x = v => 14 + (clamp(v, a, b) - a) / (b - a) * (W - 28);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">`;
  zones.forEach(z => { s += `<rect x="${x(z[0])}" y="14" width="${x(z[1]) - x(z[0])}" height="22" fill="${z[2]}" opacity=".16" rx="3"/><text x="${(x(z[0]) + x(z[1])) / 2}" y="10" text-anchor="middle" style="fill:${z[2]};font-weight:600">${esc(z[3])}</text>`; });
  s += `<line x1="14" x2="${W - 14}" y1="36" y2="36" stroke="#22201c"/>`;
  for (let v = a; v <= b + 1e-9; v += .5) s += `<line x1="${x(v)}" x2="${x(v)}" y1="36" y2="40" stroke="#22201c"/><text x="${x(v)}" y="53" text-anchor="middle">${v.toFixed(1)}</text>`;
  if (est != null) {
    const e = lerp(0, est, ease(part(t, 0, .45))), w = ease(part(t, .45, .85));
    if (lo != null && hi != null) s += `<line x1="${x(lerp(est, lo, w))}" x2="${x(lerp(est, hi, w))}" y1="25" y2="25" stroke="var(--model)" stroke-width="4" stroke-linecap="round" opacity="${w}"/>`;
    s += `<circle cx="${x(e)}" cy="25" r="6" fill="var(--model)" stroke="#fff" stroke-width="2"/>`;
  }
  return s + '</svg>';
}

function bars(items, t) {
  return items.map(([lab, v], i) => {
    const w = v == null ? 0 : Math.abs(v) / 1 * 50 * ease(part(t, i * .12, i * .12 + .4));
    return `<div style="display:grid;grid-template-columns:150px 1fr 44px;gap:8px;align-items:center;font-size:12.5px;margin:3px 0"><span>${lab}</span>` +
      `<div style="position:relative;height:12px;background:var(--soft);border-radius:6px"><div style="position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:#bdb5a8"></div>` +
      `<div style="position:absolute;top:0;bottom:0;border-radius:6px;background:var(--model);${v != null && v < 0 ? `right:50%;width:${w}%` : `left:50%;width:${w}%`}"></div></div><b>${f2(v)}</b></div>`;
  }).join('') + '<div style="font-size:11.5px;color:var(--ink3);margin-left:158px">fidelity from minus 1 to 1; 1 means the model matches people</div>';
}

function quadrant(m, t) {
  const pts = m.recognition.filter(r => r.rate != null && r.effect != null);
  const xr = Math.max(10, ...pts.map(r => Math.abs(r.effect))) * 1.2;
  const W = 440, H = 250, L = 40, R = 108, T = 10, B = 30;
  const X = v => L + (clamp(v, -xr, xr) + xr) / (2 * xr) * (W - L - R), Y = v => T + (1 - clamp(v, 0, 1)) * (H - T - B);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="knows it versus shows it">`;
  s += `<rect x="${X(C.show)}" y="${Y(1)}" width="${X(xr) - X(C.show)}" height="${Y(C.recog) - Y(1)}" fill="var(--OVER)" opacity=".10"/>`;
  s += `<rect x="${X(-xr)}" y="${Y(1)}" width="${X(C.show) - X(-xr)}" height="${Y(C.recog) - Y(1)}" fill="var(--ANTI)" opacity=".08"/>`;
  s += `<rect x="${X(C.show)}" y="${Y(C.recog)}" width="${X(xr) - X(C.show)}" height="${Y(0) - Y(C.recog)}" fill="var(--HIGH)" opacity=".10"/>`;
  s += `<line x1="${X(C.show)}" x2="${X(C.show)}" y1="${T}" y2="${H - B}" stroke="#bdb5a8" stroke-dasharray="4 3"/><line x1="${L}" x2="${X(xr)}" y1="${Y(C.recog)}" y2="${Y(C.recog)}" stroke="#bdb5a8" stroke-dasharray="4 3"/>`;
  // the quadrant names sit in two short lines against the recognition cutoff, where few dots fall
  const two = (x, y, a, b, anchor) => `<text x="${x}" y="${y}" text-anchor="${anchor}" style="font-size:10.5px">${a}</text><text x="${x}" y="${y + 12}" text-anchor="${anchor}" style="font-size:10.5px">${b}</text>`;
  s += two(X(-xr) + 4, Y(C.recog) - 18, 'identifies it,', 'does not show it', 'start') + two(X(xr) - 4, Y(C.recog) - 18, 'identifies it', 'and shows it', 'end');
  s += two(X(-xr) + 4, Y(C.recog) + 14, 'neither', '', 'start') + two(X(xr) - 4, Y(C.recog) + 14, 'shows it, does', 'not identify it', 'end');
  for (let v = -Math.floor(xr / 5) * 5; v <= xr; v += 5) s += `<text x="${X(v)}" y="${H - B + 14}" text-anchor="middle">${v}</text>`;
  s += `<text x="${(L + X(xr)) / 2}" y="${H - 2}" text-anchor="middle">effect in the model, in the human direction (points)</text>`;
  s += `<text transform="translate(11 ${(T + H - B) / 2}) rotate(-90)" text-anchor="middle">share of calls that identify it</text>`;
  s += `<text x="${L - 4}" y="${Y(1) + 4}" text-anchor="end">1</text><text x="${L - 4}" y="${Y(C.recog) + 4}" text-anchor="end">${C.recog}</text><text x="${L - 4}" y="${Y(0) + 4}" text-anchor="end">0</text>`;
  const at = pts.map((r, i) => {
    const k = ease(part(t, i / pts.length * .6, i / pts.length * .6 + .4));
    return {r, k, cx: X(lerp(0, r.effect, k)), cy: Y(lerp(0, r.rate, k))};
  });
  // the names are listed in a column to the right of the chart, in the order of the dots' heights, each joined to its dot
  const col = at.slice().sort((u, v) => u.cy - v.cy);
  col.forEach((q, i) => { q.ly = q.cy + 4; if (i && q.ly - col[i - 1].ly < 14) q.ly = col[i - 1].ly + 14; });
  const over = col.length ? col[col.length - 1].ly - (H - B) : 0;
  if (over > 0) col.forEach(q => q.ly -= over);
  at.forEach(({r, k, cx, cy, ly}) => {
    s += `<line x1="${cx}" y1="${cy}" x2="${X(xr) + 8}" y2="${ly - 4}" stroke="#d3cabb" opacity="${k}"/>`;
    s += `<circle cx="${cx}" cy="${cy}" r="6" fill="${r.open ? '#fff' : 'var(--model)'}" stroke="var(--model)" stroke-width="2"/>`;
    s += `<text x="${X(xr) + 12}" y="${ly}" style="fill:#22201c;opacity:${k}">${esc(r.short)}</text>`;
  });
  return s + '</svg>';
}

function step3(m, p) {
  const t1 = m.t1, t3 = m.t3, t5 = m.t5;
  const focus = ['t1', 't2', 't3', 't5'].find(k => p[k] > 0 && p[k] < 1);
  const panel = (k, title, what, body, verdict) => `<div class="test ${focus === k ? 'focus' : ''}"><h3>${title}</h3><p class="what">${what}</p>${body}${verdict ? `<div class="verdict" style="opacity:${part(p[k], .85, 1)}">${esc(verdict)}</div>` : ''}</div>`;
  // effects with the same result are listed together
  const groups = [];
  m.recognition.forEach(r => { const g = groups.find(x => x.text === r.text); if (g) g.names.push(r.short); else groups.push({text: r.text, names: [r.short]}); });
  const recList = groups.map(g => `<div style="font-size:12.5px;color:var(--ink2);margin-top:3px"><b style="color:var(--ink)">${esc(g.names.join(', '))}</b>: ${esc(g.text)}</div>`).join('');
  const t5body = t5.delta == null ? ''
    : numberLine(t5.delta, t5.lo, t5.hi, [[C.t5_step, 2, 'var(--HIGH)', 'rise'], [-2, -C.t5_step, 'var(--ANTI)', 'fall']], p.t5, 'trajectory test');
  return `<p class="q">Where does the model fall short of people? The pattern tests</p><p class="qs">Each line shows the estimate (dot) and its 95% interval (bar) against the cutoffs fixed in advance (shaded). A test reaches a conclusion only when the estimate passes a cutoff and the whole interval is on the same side; otherwise it is not resolved.</p>` +
    `<div class="tests">` +
    panel('t1', 'Memorization test (T1)', `Fidelity on the published values against new values in the same categories. A steep fall needs more than ${C.t1_steep.toFixed(2)}; no difference needs less than ${C.t1_flat.toFixed(2)}.`,
      bars([['published values', t1.pub], ['new values', t1.new]], p.t1) + numberLine(t1.drop, t1.lo, t1.hi, [[C.t1_steep, 2, 'var(--ANTI)', 'steep fall'], [-C.t1_flat, C.t1_flat, 'var(--HIGH)', 'no difference']], p.t1, 'memorization test') +
      `<div style="font-size:11.5px;color:var(--ink3)">the line shows the fall, published minus new</div>`, t1.text) +
    panel('t2', 'Knows-it-versus-shows-it test (T2)', `When asked, does the model identify the manipulation (at least ${pct(C.recog)} of its recognition calls), and do its choices show the effect (more than ${C.show} points in the human direction)? Hollow dots are not resolved.`,
      quadrant(m, p.t2) + `<div style="opacity:${part(p.t2, .8, 1)}">${recList}</div>`, '') +
    panel('t3', 'Argument-strength test (T3)', `Fidelity at the top (attraction), middle (compromise) and bottom (extremity) of the ordering. A decline needs the top more than ${C.t3_step.toFixed(2)} above the bottom; no difference needs them within ${C.t3_flat.toFixed(2)}; a reversal also needs the bottom more than ${C.t3_step.toFixed(2)} above the middle.`,
      bars([['top: attraction', t3.top], ['middle: compromise', t3.mid], ['bottom: extremity', t3.bottom]], p.t3) +
      numberLine(t3.tmb, t3.lo, t3.hi, [[C.t3_step, 2, 'var(--ANTI)', 'decline'], [-2, -C.t3_step, 'var(--OVER)', 'reversal'], [-C.t3_flat, C.t3_flat, 'var(--HIGH)', 'no difference']], p.t3, 'argument-strength test') +
      `<div style="font-size:11.5px;color:var(--ink3)">the line shows the top minus the bottom</div>`, t3.text) +
    panel('t5', 'Trajectory test (T5)', `Fidelity of the newer model of the family minus the older one. A rise or a fall needs more than ${C.t5_step.toFixed(2)}.`, t5body, (t5.text || '') + (t5.reasoning ? ' ' + t5.reasoning : '')) +
    `</div><p style="font-size:13px;color:var(--ink2);margin-top:12px"><b>Format test (T4).</b> Described only, with its estimate and interval; no scenario depends on it.</p>`;
}

function rowState(m, i) {
  // Step 3: a result that is not resolved blocks its scenario and every later one except S1, which is then reported
  // with a note naming the open tests
  const own = D.steps[i].tests.filter(t => m.open_tests.includes(t));
  const first = D.steps.findIndex(s => s.tests.some(t => m.open_tests.includes(t)));
  if (own.length) return `not resolved (${own.join(', ')}), so not claimed; only S1 can still be reached`;
  if (first >= 0 && i > first) return 'not claimed: an earlier result is not resolved (S1 is the one exception)';
  return 'does not apply';
}

function step4(m, p) {
  if (m.land === 'step0') return `<p class="q">Which scenario applies?</p><div class="concl"><div class="k">Where the code places this model</div><div class="h">Stops at Step 0</div><p>The model is not assessable as a survey respondent, so it is reported in its own table and no scenario is checked.</p>${built(m)}</div>`;
  const rows = D.steps.length, tgt = target(m);
  const pos = tgt * ease(p.a);
  TOK = pos;
  let h = `<p class="q">Which scenario applies?</p><p class="qs">We check the scenarios in this fixed order, and the first that applies is the conclusion for the model. The dot moves down the list one check at a time.</p><div class="ladder"><div class="track"></div>`;
  for (let i = 0; i < rows; i++) {
    const passed = i < pos - .5 && i !== tgt, hitNow = p.a >= 1 && (i === tgt || (m.land === 's4either' && i === 9));
    const maybe = p.a >= 1 && m.land === 'open' && m.possible.map(rowNum).includes(i);
    const s = D.steps[i];
    h += `<div class="lrow ${passed ? 'passed' : ''} ${hitNow && m.land !== 'open' ? 'hit' : ''} ${maybe ? 'maybe' : ''}"><span class="n">${i < 10 ? i + 1 : ''}</span><div><div class="tt">${esc(s.title)}</div><div class="nd">${esc(s.need)}</div>` +
      `${passed ? `<div class="st">${esc(rowState(m, i))}</div>` : ''}${hitNow && m.land !== 'open' ? '<div class="st" style="color:var(--accent);font-weight:600">applies: this is the conclusion</div>' : ''}${maybe ? '<div class="st" style="color:#8a5a00;font-weight:600">possible, not resolved</div>' : ''}</div></div>`;
  }
  h += `<div class="token" id="tok"></div></div>`;
  const code = m.land === 'none' || m.land === 'open' ? '' : D.steps[tgt].code;
  const concl = m.land === 'open' ? `The code does not claim a scenario: a test the scenario depends on is not resolved. The possible scenarios are ${m.possible.map(rowLabel).join(' and ')}.`
    : (m.conclusion ? m.conclusion : D.steps[tgt].need);
  h += `<div class="concl" style="opacity:${p.b};transform:translateY(${(1 - p.b) * 8}px)"><div class="k">Where the code places this model</div><div class="h">${esc(landText(m))}</div>` +
    `<p>${code ? '<b>Registered conclusion (Table 4):</b> ' : ''}${esc(concl)}</p>` +
    (m.qualifier ? `<p style="color:#8a5a00">With the note "pattern tests not resolved at the design's resolution": ${esc(m.open_tests.join(', '))} not resolved.</p>` : '') +
    `<p style="color:var(--ink2);font-size:13.5px"><b style="color:var(--ink)">Account for the model as a whole:</b> ${esc(m.model_account)}</p>${built(m)}</div>`;
  return h;
}

function built(m) {
  const want = m.planted_land === 'step0' ? 'Step 0' : rowLabel(m.planted_land);
  if (m.land === 'open' && m.as_built) return `<span class="built mid">Built to reach: ${esc(want)}. Left open, with that scenario among the possible ones</span>`;
  return m.as_built ? `<span class="built">Built to reach: ${esc(want)}. Reached as built</span>` : `<span class="built no">Built to reach: ${esc(want)}. Reached something else</span>`;
}

const STEPS = [
  {draw: step0, beats: [['a', 1300], ['b', 1300], ['c', 500]], where: ['Analysis Plan, Step 0', 'human_gate and model_gate']},
  {draw: step1, beats: [['a', 1500], ['b', 1200]], where: ['Analysis Plan, Step 1', 'the human benchmarks (human_benchmarks.csv)']},
  {draw: step2, beats: [['a', 1800], ['b', 1400], ['c', 1100]], where: ['Analysis Plan, Step 2, and Web Appendix Figure WA-E1', 'classify_cell and the overall class (effect_classes.csv, agreement_scores.csv)']},
  {draw: step3, beats: [['t1', 1900], ['t2', 1900], ['t3', 1900], ['t5', 1400]], where: ['Analysis Plan, Step 3, and Web Appendix Table WA-E5', 'test_T1_memorization, test_T2_recognition, test_T3_ladder and test_T5_trajectory (results_pack/tests/)']},
  {draw: step4, beats: [['a', 2600], ['b', 700]], where: ['Analysis Plan, Step 4, Figure 3 and Table 4', 'route_resolved (tree_routing.csv)']},
];

// ---------- the player ----------
let cur = D.models[0], si = 0, P = {}, run = 0, playing = false, paused = false, finished = false;
const $ = id => document.getElementById(id);
function full(i) { const o = {}; STEPS[i].beats.forEach(b => o[b[0]] = 1); return o; }
function zero(i) { const o = {}; STEPS[i].beats.forEach(b => o[b[0]] = 0); return o; }
function skipped(i) { return cur.land === 'step0' && i > 0 && i < 4; }
function draw() {
  TOK = null;
  $('panel').innerHTML = STEPS[si].draw(cur, P);
  // the dot on the Step 4 list sits beside the row it has reached, measured from the rows as drawn
  const tok = $('tok'), rows = [...$('panel').querySelectorAll('.lrow')];
  if (tok && rows.length && TOK != null) {
    const i = Math.floor(TOK), f = TOK - i, a = rows[Math.min(i, rows.length - 1)], b = rows[Math.min(i + 1, rows.length - 1)];
    tok.style.top = (lerp(a.offsetTop, b.offsetTop, f) + 11) + 'px';
  }
}
function chrome() {
  $('head').innerHTML = `<h2>${esc(cur.name)}</h2><div class="planted">${esc(cur.planted)}</div><div class="code">In the code: <span class="mono">${esc(cur.id)}</span></div>`;
  $('rail').innerHTML = STEPNAMES.map((n, i) => `${i ? '<span class="bar"></span>' : ''}<button class="dot ${i === si ? 'on' : (i < si ? 'done' : '')} ${skipped(i) ? 'skip' : ''}" data-i="${i}" ${skipped(i) ? 'disabled title="Skipped: the model stops at Step 0"' : ''}><i>${i}</i>Step ${i}: ${n}</button>`).join('');
  $('rail').querySelectorAll('.dot').forEach(b => b.onclick = () => go(+b.dataset.i));
  const onDot = $('rail').querySelector('.dot.on');
  if (onDot) $('rail').scrollLeft = Math.max(0, onDot.offsetLeft - 60);
  const w = STEPS[si].where;
  $('where').innerHTML = `In the paper: ${w[0]}. In the code: <span class="mono">analysis/analyze.py</span>, ${esc(w[1])}.`;
  $('back').disabled = si === 0; $('next').disabled = si === 4;
  $('play').textContent = playing && !paused ? 'Pause' : (finished ? 'Play again' : 'Play');
  document.querySelectorAll('.pick').forEach(b => b.classList.toggle('on', b.dataset.id === cur.id));
}
function tween(ms, key, id) {
  return new Promise(res => {
    if (RM) { P[key] = 1; draw(); return res(id === run); }
    let el = 0, last = null;
    const f = ts => {
      if (id !== run) return res(false);
      if (last == null) last = ts;
      if (!paused) el += ts - last;
      last = ts;
      P[key] = clamp(el / ms, 0, 1); draw();
      if (P[key] < 1) requestAnimationFrame(f); else res(true);
    };
    requestAnimationFrame(f);
  });
}
const hold = (ms, id) => new Promise(res => { let el = 0, last = null; const f = ts => { if (id !== run) return res(false); if (last == null) last = ts; if (!paused) el += ts - last; last = ts; if (el < ms) requestAnimationFrame(f); else res(true); }; requestAnimationFrame(f); });
async function playFrom(i) {
  const id = ++run; playing = true; paused = false; finished = false;
  while (i <= 4) {
    if (skipped(i)) { i++; continue; }
    si = i; P = zero(i); chrome(); draw();
    for (const [k, ms] of STEPS[i].beats) if (!(await tween(ms, k, id))) return;
    if (i < 4 && !(await hold(RM ? 300 : 1300, id))) return;
    i++;
  }
  playing = false; finished = true; chrome();
}
function go(i) { if (skipped(i)) return; run++; playing = false; paused = false; finished = i === 4; si = clamp(i, 0, 4); P = full(si); chrome(); draw(); }
function pick(id) { cur = D.models.find(m => m.id === id); go(0); finished = false; chrome(); }
$('play').onclick = () => {
  if (playing && !paused) { paused = true; chrome(); return; }
  if (playing && paused) { paused = false; chrome(); return; }
  playFrom(finished ? 0 : si);
};
$('back').onclick = () => { let n = si - 1; while (n > 0 && skipped(n)) n--; go(Math.max(0, n)); };
$('next').onclick = () => { let n = si + 1; while (n < 4 && skipped(n)) n++; go(n); };
$('restart').onclick = () => playFrom(0);
document.addEventListener('keydown', e => {
  if ($('v-one').hidden || e.target.closest('input,textarea')) return;
  if (e.key === ' ') { e.preventDefault(); $('play').click(); }
  if (e.key === 'ArrowRight') $('next').click();
  if (e.key === 'ArrowLeft') $('back').click();
});
$('picker').innerHTML = '<div class="lbl">Simulated models</div>' + D.models.map(m => `<button class="pick" data-id="${esc(m.id)}"><div class="nm">${esc(m.name)}</div><div class="to">${esc(landText(m))}</div></button>`).join('');
$('picker').querySelectorAll('.pick').forEach(b => b.onclick = () => pick(b.dataset.id));
pick(D.models[0].id);

// ---------- all models at once ----------
function sortRows() {
  const L = [{key: -1, title: 'Stops at Step 0', need: 'Not assessable as a survey respondent'}];
  D.steps.forEach((s, i) => L.push({key: i, title: (i < 10 ? (i + 1) + '. ' : '') + s.title, need: s.need}));
  return L;
}
function sorter(animate) {
  const order = D.models.map((m, i) => [m, i]);
  let h = `<div class="sorter"><div class="bar"><button class="play" id="sortplay">Play: sort every model</button><span style="color:var(--ink2);font-size:13px">Each simulated model drops into the first check that applies to it, in the registered order. Click a model to follow it step by step.</span></div>`;
  h += `<div class="s7">${D.s7 ? 'If four or more of the six effects other than similarity fail in people, every model is reported under S7. On a separate simulated sample built with four failing effects, the code reached S7.' : ''}</div>`;
  sortRows().forEach(l => {
    const here = order.filter(([m]) => target(m) === l.key || (m.land === 's4either' && l.key === 9));
    h += `<div class="srow"><div><div class="ln">${esc(l.title)}</div><div class="ld">${esc(l.need)}</div></div><div class="slots">` +
      here.map(([m, i]) => `<button class="mchip ${animate ? 'drop' : ''}" style="animation-delay:${animate && !RM ? i * 0.22 : 0}s" data-id="${esc(m.id)}"><b class="${m.as_built ? (m.land === 'open' ? 'mid' : '') : 'no'}">${m.as_built ? '&#10003;' : '&#10005;'}</b>${esc(m.name)}</button>`).join('') + (here.length ? '' : '<span style="font-size:12.5px;color:var(--ink3)">No simulated model ends here in this rehearsal.</span>') + `</div></div>`;
  });
  h += `<p style="font-size:12.5px;color:var(--ink3);margin:10px 0 0">A check mark means the code placed the model where it was built to land (synth.py); a cross would mean it did not.</p></div>`;
  $('v-all').innerHTML = h;
  $('sortplay').onclick = () => sorter(true);
  $('v-all').querySelectorAll('.mchip').forEach(b => b.onclick = () => { show('one'); pick(b.dataset.id); });
}

// ---------- where the files are ----------
$('v-files').innerHTML = `<div class="flow">
<div class="fbox"><div class="fp">calibration/</div><div class="fd">The pre-test with real participants that set the option values (Web Appendix F).</div></div><div class="farrow">sets the values in</div>
<div class="fbox"><div class="fp">stimuli/stimuli.json</div><div class="fd">All 165 choice sets in one file; <span class="mono">stimulus-explorer.html</span> shows each one.</div></div><div class="farrow">the same file generates the surveys and the prompts</div>
<div class="frow"><div class="fbox"><div class="fp">surveys/ and survey_package/</div><div class="fd">The five surveys that people answer.</div></div><div class="fbox"><div class="fp">models/</div><div class="fd">The prompts and the exact call plan for the ten models.</div></div><div class="fbox"><div class="fp">power/</div><div class="fd">The power and resolution simulations reported in the Method and Web Appendix E.</div></div></div>
<div class="farrow">people's answers and the models' answers go into</div>
<div class="fbox"><div class="fp">analysis/analyze.py</div><div class="fd">The registered analysis, with every cutoff in <span class="mono">analysis/registered_constants.py</span>. Before real data exist it runs on <span class="mono">analysis/demo_data/</span>, the simulated people and models that <span class="mono">analysis/synth.py</span> writes.</div></div><div class="farrow">writes every number to</div>
<div class="fbox"><div class="fp">analysis/results_pack/</div><div class="fd">The fidelity map, the classes, each pattern test and the scenario of each model. This page displays these files.</div></div><div class="farrow">checked by</div>
<div class="fbox"><div class="fp">run_all.py</div><div class="fd">Re-runs every step and compares every output with the copy deposited here.</div></div></div>`;

function show(v) {
  ['one', 'all', 'files'].forEach(k => $('v-' + k).hidden = k !== v);
  document.querySelectorAll('.tabs button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  if (v === 'all') sorter(true);
  if (v !== 'one') { run++; playing = false; paused = false; chrome(); }
}
document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => show(b.dataset.v));
</script></body></html>
"""

if __name__ == "__main__":
    build()
