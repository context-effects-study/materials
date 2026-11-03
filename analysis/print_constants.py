"""print_constants.py: prints every registered cutoff of the analysis as Table WA-E1 of Web Appendix E.

The table is built from the same object analyze.py reads (registered_constants.py), so the value printed and
the value the analysis applies cannot differ. The first table has the appendix's layout (step, value,
meaning); the second gives each row's name in the code.

Output: analysis/REGISTERED_CONSTANTS.md (also printed to the screen).
Manuscript: Web Appendix E, Table WA-E1.

Run: python analysis/print_constants.py
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from registered_constants import (C, HOLM_FAMILIES, CLASS_ORDER, CALIBRATION_DECISION_RULE,  # noqa: E402
                                  DEVIATION_SENSITIVITY_PAIRS, UNITS, rows)

DEFAULT_OUT = os.path.join(HERE, "REGISTERED_CONSTANTS.md")

FAMILY_WORDS = {
    "non_similarity": "the six effects other than similarity (frequency decoy, range decoy, phantom, compromise, "
                      "upscaling, extremity)",
    "similarity": "similarity alone, because it is analyzed separately",
    "format_interaction": "the four tests of whether the format changes an effect (frequency decoy and compromise, each in "
                          "words and in pictures, against numbers)",
}

CATEGORY_WORDS = {"backpacks": "backpacks", "earbuds": "earbuds", "restaurants": "restaurants",
                  "standing_desks": "standing desks", "water_bottles": "water bottles",
                  "electric_kettles": "electric kettles", "televisions": "televisions"}
TIER_WORDS = {1: "published values", 2: "new values", 3: "invented category"}

# Rules registered with the constants that carry no single number: printed as "Rule" rows.
RULE_ROWS = [
    ("Step 2, fidelity classes",
     "A model's class for an effect is computed on the effect's pooled estimate, pooled over the same "
     "categories and tiers, with the same weights, as the human confirmatory test; the classes of single "
     "tiers and categories are descriptive. A model's overall class is its most frequent class across the six "
     "effects other than similarity that passed the human criterion; ties go to the less faithful class, in the "
     "order " + ", ".join(CLASS_ORDER) + "."),
    ("Method, model estimates",
     "A model effect is the mean over every combination of stimulus, option order and paraphrase and the "
     "repeated calls of each. An effect is flagged prompt-sensitive when its pooled sign differs across the "
     "three paraphrases; the flag is descriptive, is reported beside the class, and at small effects often "
     "reflects the variation between repeated calls."),
    ("Step 3, pattern tests",
     "We conclude that a group falls short (a steep fall from the published values to the new values, a "
     "decline or a reversal down the argument-strength ordering) only when that group's value before the "
     "replacement by 2 minus the value is also below 1; a group whose effect is too large is only described, "
     "and its cells are classed OVER."),
    ("Step 3, pattern tests",
     "Every result of the memorization, argument-strength and trajectory tests is judged against a 95 "
     "percent interval from 2,000 resamples that redraw, together, the human participants within each "
     "cell and the model calls within each combination of stimulus, option order and paraphrase. Each "
     "resample recomputes the quantity the conclusion uses, with the cells in each group, and the sign "
     "each cell is scored with, set once from the full-sample estimates; a resample in which a group's "
     "human effects sum to zero or less leaves that group's fidelity undefined and counts as minus "
     "infinity for the lower end of the interval and plus infinity for the upper end, so such "
     "resamples can only widen it."),
    ("Step 3, pattern tests",
     "We conclude that a difference exists when its estimate passes the cutoff and its interval lies wholly "
     "outside the range treated as no difference; we conclude that there is no difference when the estimate "
     "lies inside that range and the interval lies wholly short of the cutoff. A result whose estimate meets "
     "these conditions while its whole interval lies on the other side of the cutoff (a percentile interval "
     "need not contain the estimate) is not resolved. Any other result is reported as not resolved, and no "
     "scenario is based on it; when the interval rules out every conclusion fixed in advance for a test, the "
     "result is described but is still not resolved."),
    ("Step 3, knows-it-versus-shows-it test (T2)",
     "For rational override, both parts are judged against 95 percent intervals: the model knows the "
     "manipulation when its recognition rate and the rate's interval (recognition calls resampled within each stimulus) "
     "lie at or above one half, and it does not show the effect when its pooled effect and that effect's interval "
     "over calls lie at or below 3 points."),
    ("Step 3, format test (T4)",
     "Descriptive only: fidelity in numbers, words and pictures, and the difference between numbers "
     "and pictures with its 95 percent interval, are reported beside the argument-strength test. No "
     "conclusion is drawn from the format test and no scenario depends on it. It is also reported with the "
     "model's numbers calls restricted to the option order its picture shows, on the model side only."),
    ("Step 4, the conclusion for each model",
     "Before Step 4, Step 0 applies: when four or more of the six effects other than similarity fail in people, "
     "every model is reported under S5, and a model that loses more than a third of its cells is not assessable. "
     "For every other model we look for three failures, with no order among them: a steep fall in fidelity from the "
     "published values to the new values (T1), Retrieval only (S2); a decline down the argument-strength ordering "
     "(T3), Reason construction (S3); and the manipulation identified on at least one effect whose pooled effect is "
     "not above 3 points (T2), Rational override (S4). A failure is present when its result is resolved, absent when "
     "the interval rules it out, and otherwise not resolved; a failed positive control leaves the first two not "
     "judged."),
    ("Step 4, the conclusion for each model",
     "A model matches people when its overall class is HIGH, no effect is classed LOW or ANTI, no failure is "
     "present, and no test points to a failure: no failure that is not resolved has an estimate past its cutoff (an "
     "estimated fall or decline above 0.30, or the manipulation identified, by its estimate, on an effect whose pooled "
     "effect is not above 3 points). A model that matches people and identifies the manipulation on no effect is reported under S1 (High "
     "fidelity); one that identifies the manipulation on at least one effect is reported under S7 (A known effect "
     "reproduced). For a model that does not match people, the conclusion is every failure that is present. When "
     "all three are absent, the model is reported under S6, a failure that no account predicts. When none is "
     "present and at least one is not resolved or not judged, the model is reported as not resolved, with the "
     "failures that are still possible."),
    ("Step 4, the conclusion for each model",
     "For every model we report each effect's class and whether the model identified the manipulation, with no "
     "account attached. Beside the conclusion we report the trajectory test and whether all models of the "
     "family receive the same overall class. Neither of these changes the conclusion."),
    ("Step 1, stimulus handling",
     "The deviation sensitivity analysis removes seven calibration pairs: the six pairs retained after "
     "failing the calibration rule (backpacks, earbuds and restaurants at new values, the standing desks, "
     "the pictures water-bottles pair, and the electric kettles) and the published water-bottles pair, whose "
     "measured share, 80.0 percent, lies outside the 25 to 75 percent limits. The analysis computes the seven "
     "from the calibration record and stops if they differ from this list."),
]
SHARE_AS_PERCENT = ("PARSE_FLOOR", "REFUSAL_CEIL", "CEIL_HI", "CEIL_LO", "RERUN_RULE")


def fmt_value(name, v):
    """The value as a reader sees it in Table WA-E1."""
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if name.endswith("_FRAC"):
        return "1/3" if abs(v - 1 / 3) < 1e-9 else f"{v:g}"
    if name in SHARE_AS_PERCENT:
        return f"{v * 100:g} percent"
    if name == "BOOTSTRAP_RESAMPLES":
        return f"{v:,}"
    if name == "BOOTSTRAP_SEED":
        return str(v)
    s = f"{v:,}" if isinstance(v, int) else f"{v:g}"
    unit = UNITS.get(name)
    return f"{s} {unit}" if unit else s


def build():
    table_rows = rows()
    lines = [
        "# The registered analysis constants",
        "",
        "Generated by analysis/print_constants.py from analysis/registered_constants.py, the",
        "single structure the analysis code reads. The first table is Table WA-E1 as",
        "it prints: its values and meanings come from the same object the code applies, so the two cannot",
        "differ. Changing any value after data exist is a reported deviation.",
        "",
        "## Table WA-E1, ready to print",
        "",
        "**TABLE WA-E1.** THE REGISTERED CUTOFFS",
        "",
        "| Step | Value | Meaning |",
        "|---|---|---|",
    ]
    printed = [(grp, fmt_value(name, value), meaning) for grp, name, value, meaning in table_rows]
    printed += [(grp, "Rule", meaning) for grp, meaning in RULE_ROWS]
    order = []
    for grp, _, _ in printed:          # step order = first appearance in the dataclass (the Analysis Plan's)
        if grp not in order:
            order.append(grp)
    # the Method's rows first (the Method precedes the Analysis Plan), then the steps in the Plan's order (a group
    # named only by rule rows, such as the format test and Step 4, sits with its step), then the other groups;
    # stable, so each rule row follows its group's numbers
    def step_no(grp):
        return int(grp[5]) if grp.startswith("Step ") and grp[5].isdigit() else 9
    printed.sort(key=lambda r: (0 if r[0].startswith("Method") else 1, step_no(r[0]), order.index(r[0])))
    for grp, value, meaning in printed:
        lines.append(f"| {grp} | {value} | {meaning} |")
    lines += [
        "",
        "*Note.* A fidelity value is a model effect divided by the matched human effect, with the sign kept; "
        "in the pattern tests a group's value above 1 is folded to 2 minus the value. \"Points\" are "
        "percentage points.",
        "",
        "## Where each row lives in the code (for the cross-check; not for printing)",
        "",
        "| Step | Name in registered_constants.py | Value |",
        "|---|---|---|",
    ]
    for grp, name, value, _ in table_rows:
        lines.append(f"| {grp} | {name} | {fmt_value(name, value)} |")
    lines += ["", "## The Holm families", "", "| Family | Members |", "|---|---|"]
    for fam, members in HOLM_FAMILIES.items():
        lines.append(f"| {fam} | {FAMILY_WORDS[fam]} ({', '.join(members)}) |")
    dev = "; ".join(f"{CATEGORY_WORDS.get(c, c)}, {TIER_WORDS[t]}, {f}" for c, t, f in DEVIATION_SENSITIVITY_PAIRS)
    r = CALIBRATION_DECISION_RULE
    lines += [
        "",
        "## Rules stated with the constants",
        "",
        f"- **Human replication criterion.** An effect replicates when its pooled contrast is significant after "
        f"Holm within its family at {C.HOLM_ALPHA:g}, runs in the predicted (positive) direction, and has a Bayes "
        f"factor above {C.BF_GATE:g}. The Bayes factor compares a half-normal prior on the effect (positive values "
        f"only, scale {C.BF_PRIOR_SCALE_PP:g} points) with no effect, using a normal likelihood built from the "
        "pooled estimate and its cluster-robust standard error (Dienes 2014).",
        f"- **Positive controls.** The frequency-decoy cells whose target is the premium option (predicted "
        f"direction, significant at {C.POSITIVE_CONTROL_ALPHA:g}, Bayes factor above {C.BF_GATE:g}) and the "
        "compromise effect (its replication criterion). If one fails, that effect's row of the fidelity map and "
        "every pattern-test reading that uses the effect (the memorization, argument-strength and trajectory "
        "tests, the descriptive format comparison, and that effect's knows-it-versus-shows-it reading) are reported "
        "as uninformative "
        "about simulation.",
        f"- **First-trial check.** Scope: the seven pooled contrasts of the core design. For each, the "
        f"effect in participants' first choices is compared with the effect in their later choices; the check "
        f"fires when a difference is significant at family-wise {C.FIRST_TRIAL_ALPHA:g} (Holm across the seven) "
        f"and the full-sample and first-trial estimates differ by more than {C.FIRST_TRIAL_MIN_DIVERGENCE_PP:g} "
        "points. Simulated false-alarm rate at the planned sizes: 0.047 (power/FIRST_TRIAL_RULE_SIM.md).",
        f"- **Similarity supplement check.** The similarity effect is estimated from core-design choices and from "
        f"similarity-supplement choices in the same cells, each against the core design's two-option control and "
        f"with the same cell weights. If the two differ by more than {C.SIM_TOPUP_MAX_GAP_PP:g} points and the "
        f"difference is significant at {C.SIM_TOPUP_ALPHA:g}, the core-design estimate becomes the similarity "
        "benchmark.",
        f"- **Classes.** HIGH: same direction, {C.HIGH_RATIO:g} to {C.OVER_RATIO:g} times the human effect; OVER: "
        f"same direction and above {C.OVER_RATIO:g} times; PARTIAL: {C.PARTIAL_RATIO:g} to {C.HIGH_RATIO:g} times; "
        f"LOW: below {C.PARTIAL_RATIO:g} times, or opposite in sign by {C.ANTI_MIN_PP:g} points or less; ANTI: "
        f"opposite in sign to a replicated human effect by more than {C.ANTI_MIN_PP:g} points. Human effects "
        f"under {C.NEAR_NULL_HUMAN_PP:g} points are not classed.",
        f"- **Model estimates.** Each model effect is reported with the number of calls behind it and a percentile "
        f"bootstrap interval from {C.BOOTSTRAP_RESAMPLES:,} resamples of the calls, drawn within each combination "
        f"of stimulus, option order and paraphrase (seed {C.BOOTSTRAP_SEED}); descriptive, never a test.",
        f"- **Resolving the pattern-test readings.** The same {C.BOOTSTRAP_RESAMPLES:,} resamples are drawn together "
        "with resamples of the human choices within each cell (each participant contributes one choice to a cell), "
        "and every quantity a pattern-test reading uses (a group's folded fidelity, a difference between groups, "
        "a difference between two models or two reasoning settings) is recomputed on each resample, with the "
        "groups' members and signs fixed by the point estimates. A resample in which a group's human effects sum "
        "to zero or less leaves that group undefined and widens the interval at both ends. A reading that a "
        "difference exists needs its estimate past the cutoff and its 95 percent interval clear of the "
        "no-difference range (memorization, published-values against new-values tier on the same categories: drop "
        "above 0.30 and interval above 0.10; argument-strength: each difference above 0.30 and its interval above "
        "0.12; trajectory and reasoning: difference and whole interval beyond 0.15). A reading of no difference "
        "needs its estimate inside the no-difference range and its interval short of the cutoff (memorization: "
        "interval below 0.30; argument-strength: within 0.30 either way; trajectory: within 0.15). The format test "
        "is descriptive (estimate and interval, no reading). Any other result is not resolved and supports no scenario; "
        "when the interval rules out every registered reading, the result is described and is still not resolved. "
        "The undershoot requirement applies to the memorization sensitivity re-readings too. Each failure of Step 4 "
        "is present on its resolved result, absent when the interval rules that result out, and otherwise not "
        "resolved; a present failure, or one not resolved whose estimate passes its cutoff, keeps a model from "
        "matching people, and a model that does not match people "
        "with no failure present and at least one not resolved is reported as not resolved, with the conclusions "
        "still possible listed. The human resample treats "
        "each participant's choices in different "
        "cells as independent; beside each pooled human effect, the width of its resampled interval is reported as a "
        "share of the width of its registered cluster-robust interval.",
        "- **Phantom read as retrieval.** A model phantom effect reads as consistent with retrieval of a described "
        f"regularity when it is OVER against a replicated human phantom effect, or larger than {C.ANTI_MIN_PP:g} "
        "points in the phantom's predicted direction where the human phantom effect failed the criterion.",
        f"- **First-trial floor.** After the first-trial check fires, an effect that replicates but is smaller than "
        f"{C.FIRST_TRIAL_MIN_EFFECT_PP:g} points is classed descriptively only; it leaves the model's overall class "
        "and every pattern test.",
        f"- **Folded fidelity.** A pattern-test group's fidelity is the sum of its model effects, each taken in the "
        f"direction of the matched human effect, divided by the sum of the human effect sizes; a value above "
        f"{C.FIDELITY_FOLD_AT:g} is folded to {2 * C.FIDELITY_FOLD_AT:g} minus the value, and every value is capped "
        f"below at {C.FIDELITY_RATIO_MIN:g}. A reading that a group falls short also needs its value before "
        "folding to be below 1.",
        f"- **Format test when a human effect is small.** If the human effect in words or pictures is under "
        f"{C.NEAR_NULL_HUMAN_PP:g} points, no fidelity difference is computed for that format (the format test is "
        "descriptive in every case).",
        "- **Memorization sensitivity.** The published-values and new-values tiers, each effect on the same "
        "categories in both tiers; baselines inside the 25 to 75 percent limits only, then a weighted "
        "regression of each category-tier cell's fidelity on the stimulus tier, the cell's baseline distance "
        "from 50 percent, and whether the cell's decoys target the premium or the budget option. Both re-readings "
        "are resolved against their own 95 percent intervals, as the memorization test is.",
        f"- **Phantom equivalence.** The quantity bounded is the pooled human phantom effect. It is judged "
        f"absent when its 90 percent interval lies inside minus {C.PHANTOM_BAND_PP:g} to plus "
        f"{C.PHANTOM_BAND_PP:g} points.",
        f"- **Reversed ordering.** When the bottom position (extremity) exceeds both the top position (attraction) "
        f"and the middle position (compromise) by more than {C.T3_LADDER_STEP:g}, the reading is evidence against "
        "reason construction; it is described and leads to no conclusion of its own.",
        f"- **Effect without a human counterpart.** In a cell whose effect failed the human criterion, a model "
        f"effect larger than {C.ANTI_MIN_PP:g} points (either sign) is listed per model and effect; it never "
        "enters an agreement measure, and ANTI stays reserved for reversals of replicated human effects.",
        f"- **S5, Human effects fail.** {C.MOST_FAILED_MIN} or more of the six non-similarity effects fail; every "
        "model is then reported under S5.",
        "- **No account per effect.** Each effect is reported with its class and whether the model identified the "
        "manipulation; no account is attached to an effect, and no account needs a count of effects.",
        f"- **Deviation sensitivity set.** {dev}. The analysis computes all seven pairs from the calibration record: "
        f"the six adjustable pairs by option identity under the calibration rule (a pair is final when the "
        f"compromise target's share lies in {r['band_lo_pct']:g} to {r['band_hi_pct']:g} percent, or when its 95 "
        f"percent interval overlaps that band while the share stays between {r['interval_route_lo_pct']:g} and "
        f"{r['interval_route_hi_pct']:g} percent), and the published pairs whose measured share (the point "
        f"estimate) lies outside the {C.HARD_LIMIT_LO_PCT:g} to {C.HARD_LIMIT_HI_PCT:g} percent limits, which is "
        "only the water-bottles pair at 80.0 percent. It refuses to run when the result differs from this list. "
        "The calibration flags are only cross-checked against it; no flag decides anything.",
        f"- **Re-running the model calls.** A re-run reproduces a model effect when the deposited estimate lies "
        f"inside the re-run's {C.RERUN_RULE * 100:g} percent bootstrap interval over calls.",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    text = build()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w", encoding="utf-8", newline="\n").write(text)
    print(text)


if __name__ == "__main__":
    main()
