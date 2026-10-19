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
    ("Step 3, pattern tests",
     "A scenario that names an account is claimed only when the result it depends on is resolved: "
     "retrieval (S2) needs a resolved steep fall in the memorization test, reason construction (S3) a "
     "resolved decline down the argument-strength ordering, rational override (S4) a resolved finding that "
     "the model knows the manipulation and does not show the effect, on at least one effect, together with a "
     "LOW or ANTI overall class, the conclusions about a reversed ordering a resolved reversal, and rising "
     "fidelity (S6) a resolved rise across generations. When a result that such a scenario depends on is "
     "not resolved, neither that scenario nor any later one in the decision tree is claimed, and the model is "
     "reported as not resolved, with the possible scenarios listed, unless every way the result could be "
     "resolved leads to the same scenario (rational override and systematic inversion are both S4); high "
     "fidelity (S1) is the one exception and has its own rule in the next row."),
    ("Step 3, pattern tests",
     "High fidelity (S1) needs the HIGH overall class, no effect classed LOW or ANTI, every effect the model shows "
     "shown without identifying "
     "the manipulation (S1 is not claimed when the manipulation is identified for any effect that is shown), "
     "and no resolved steep fall in the memorization test, reversed ordering or decline down the "
     "argument-strength ordering. A result that is not resolved prevents S1 from being claimed only when its "
     "estimate, taken alone, agrees with an account (a steep fall in the memorization test, a reversed "
     "ordering, a decline down the ordering, a rise across generations); the model is then reported as not "
     "resolved, with high fidelity and every account whose test is not resolved listed as possible. "
     'Otherwise, when any pattern test is not resolved, S1 is reported with the note "pattern tests not '
     "resolved at the design's resolution\", naming the tests that are not resolved. S1 is not claimed when a "
     "positive control failed."),
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
    ("Step 4, scenarios and accounts",
     "We check the scenarios in this order, and the first that applies is our conclusion for the model: (1) a "
     "reversed argument-strength ordering with the manipulation identified on every attraction or compromise "
     "effect the model misses, which we conclude is rational override on the choice sets that give an argument; "
     "(2) S4, when the model identifies the manipulation on at least one effect and its choices do not follow it, "
     "with a LOW or ANTI "
     "overall class; (3) S2; (4) S6; (5) S5; (6) a reversed ordering without that recognition, reported as a "
     "difference from people with no account attached; (7) S1; (8) S3; (9) a mixed pattern, HIGH on some effects "
     "and LOW or ANTI on others, reported as a mixed pattern, with each effect's class and account; (10) S4 for an "
     "ANTI overall class without recognition (systematic inversion). A model that matches none is reported by "
     "the result of each test."),
    ("Step 4, scenarios and accounts",
     "A family's pattern is consistent when all its models receive the same overall class; when the models of a "
     "family receive different overall classes, the pattern is family-specific (S5), reported per family, and "
     "the combined map is labeled heterogeneous."),
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
    # the Method's rows first (the Method precedes the Analysis Plan), then the steps in the Plan's order;
    # stable, so each rule row follows its group's numbers
    printed.sort(key=lambda r: (0 if r[0].startswith("Method") else 1, order.index(r[0])))
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
        "The undershoot requirement applies to the memorization sensitivity re-readings too. A scenario that "
        "attributes an account (retrieval, reason construction, rational override, the reversed orderings, rising "
        "fidelity) is claimed only on its resolved reading; when that reading is open, neither it nor any later "
        "scenario is claimed and the model is reported as not resolved, with the scenarios left open, unless every "
        "way the reading could resolve leads to the same scenario. High fidelity "
        "needs no resolved steep "
        "memorization reading, reversed ordering or decline down the ordering, is blocked by an open reading only when that "
        "reading's estimate points to an account, and carries the qualifier \"pattern tests not resolved at the "
        "design's resolution\" (naming the open tests) whenever a pattern test is open. The human resample treats "
        "each participant's choices in different "
        "cells as independent; beside each pooled human effect, the width of its resampled interval is reported as a "
        "share of the width of its registered cluster-robust interval.",
        "- **Phantom read as retrieval.** A model phantom effect reads as consistent with retrieval of a described "
        f"regularity when it is OVER against a replicated human phantom effect, or larger than {C.ANTI_MIN_PP:g} "
        "points in the phantom's predicted direction where the human phantom effect failed the criterion.",
        f"- **First-trial floor.** After the first-trial check fires, an effect that replicates but is smaller than "
        f"{C.FIRST_TRIAL_MIN_EFFECT_PP:g} points is classed descriptively only; it leaves the model's overall class, "
        "the model-level account and every pattern test.",
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
        f"reason construction; recognition at or above {C.RECOGNITION_CUTOFF:g} on every attraction or compromise "
        "effect the model misses attributes it to rational override on choice sets that offer an argument, "
        "otherwise no account is attributed.",
        f"- **Effect without a human counterpart.** In a cell whose effect failed the human criterion, a model "
        f"effect larger than {C.ANTI_MIN_PP:g} points (either sign) is listed per model and effect; it never "
        "enters an agreement measure, and ANTI stays reserved for reversals of replicated human effects.",
        f"- **S7, Human effects fail.** {C.MOST_FAILED_MIN} or more of the six non-similarity effects fail.",
        f"- **Model-level account.** Claimed only when {C.MODEL_ACCOUNT_MIN_AGREE} or more of the six "
        "non-similarity effects that passed the human criterion carry the same per-effect account.",
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
