"""registered_constants.py: every numeric cutoff the registered analysis uses, in one place.

Each field is a registered decision: the human replication criterion (Holm level, Bayes factor threshold
and prior scale), the compromise precondition and the stimulus hard limits, the per-model data-quality
criterion (parse floor, refusal ceiling, room-to-move limits), the first-choice comparability check, the
fidelity-class ratios, the cutoffs of the three tests and the two descriptive comparisons, the cutoff for
naming the decoy in the suspicion probe, and the bounds of the equivalence and secondary readings. MEANING
gives each field its plain one-line meaning, HOLM_FAMILIES the correction families, and TIE_BREAK_RULE the
rule for a model's most frequent class. analyze.py reads every cutoff from here. Changing a value after data exist
is a deviation that must be reported.
Manuscript: Analysis Plan and Web Appendix E (the table of every numerical rule).

Imported by analyze.py; rows() returns the table of constants and their meanings.
"""
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class RegisteredConstants:
    # ---- Step 0: the human replication criterion ----
    HOLM_ALPHA: float = 0.05                 # family-wise level of the Holm correction, every family
    BF_GATE: float = 3.0                     # Bayes factor (BF10) must exceed this
    BF_PRIOR_SCALE_PP: float = 10.0          # half-normal prior scale on the effect, percentage points
    MOST_FAILED_MIN: int = 4                 # this many of the six non-similarity effects failing -> human effects fail
    POSITIVE_CONTROL_ALPHA: float = 0.05     # the premium-target frequency-decoy control's test level
    # ---- Step 0: the per-model data-quality criterion ----
    PARSE_FLOOR: float = 0.95
    REFUSAL_CEIL: float = 0.05
    CEIL_HI: float = 0.90                    # model binary share above this -> no room to move
    CEIL_LO: float = 0.10                    # model binary share below this -> no room to move
    NOT_ASSESSABLE_FRAC: float = 1.0 / 3.0   # losing more than this share of cells -> not assessable
    # ---- Step 1: stimulus handling (calibration record) ----
    COMPROMISE_TARGET_MAX_BASELINE_PCT: float = 50.0   # compromise target must start below this share
    COMPROMISE_RULE_COVERS_PUBLISHED_TIER: bool = True  # the rule above applies to the tier-1 cells too
    HARD_LIMIT_LO_PCT: float = 25.0          # registered hard limits on a two-option baseline
    HARD_LIMIT_HI_PCT: float = 75.0
    # ---- Step 1: the first-trial comparability check ----
    FIRST_TRIAL_ALPHA: float = 0.05          # family-wise level (Holm across the seven pooled effects)
    FIRST_TRIAL_MIN_DIVERGENCE_PP: float = 5.0   # and the full-vs-first-trial gap must exceed this
    #                                          (FIRST_TRIAL_MIN_EFFECT_PP, the 8-point floor after a fallback, was removed
    #                                          on 2026-11-25: it selected effects on their observed size; after a fallback
    #                                          the replication criterion on the first-trial estimates alone decides)
    # ---- Step 1: the similarity top-up check ----
    SIM_TOPUP_ALPHA: float = 0.05            # backbone vs top-up similarity: significance level
    SIM_TOPUP_MAX_GAP_PP: float = 5.0        # and the gap must exceed this for the backbone to take over
    # ---- Step 2: fidelity classes ----
    NEAR_NULL_HUMAN_PP: float = 2.0          # human effects smaller than this are not scored
    HIGH_RATIO: float = 0.70
    OVER_RATIO: float = 1.50                 # same direction and above this share of the human effect = OVER
    PARTIAL_RATIO: float = 0.25
    ANTI_MIN_PP: float = 3.0                 # the registered minimum model effect (ANTI, shows-it, no-counterpart)
    # ---- Step 2: the model estimates ----
    BOOTSTRAP_RESAMPLES: int = 2000          # percentile bootstrap over calls, descriptive only
    BOOTSTRAP_LEVEL: float = 0.95
    BOOTSTRAP_SEED: int = 20260929
    # ---- Step 3: pattern tests ----
    FIDELITY_FOLD_AT: float = 1.0            # a group fidelity above this is combined to 2 minus the value
    FIDELITY_RATIO_MIN: float = -1.0         # and every group fidelity is capped below at this value
    T1_STEEP_DROP: float = 0.30              # memorization: fidelity drop tier 1 -> tier 2 (paired) above this = steep
    T1_FLAT_SLOPE: float = 0.10              # memorization: |tier 1 -> tier 2 change| below this = flat
    RECOGNITION_CUTOFF: float = 0.50         # recognition-question rate at or above this = "knows it"
    T3_LADDER_STEP: float = 0.30             # ordering: top-minus-bottom gap above this = declines (or reversed)
    T3_LADDER_FLAT: float = 0.12             # ordering: |top-minus-bottom| below this = flat
    T5_TRAJECTORY_STEP: float = 0.15         # trajectory: new-minus-old fidelity beyond this = moves
    T5_REASONING_STEP: float = 0.15          # reasoning toggle: off-minus-on fidelity above this = lowers
    # ---- Equivalence and secondary readings ----
    PHANTOM_BAND_PP: float = 2.0             # phantom equivalence bound, plus or minus, percentage points
    #                                          (4.0 until 2026-11-24; the authors narrowed it to 2 points, because the
    #                                          published phantom effect is about 4 points and a band of 4 could
    #                                          call an effect of that size absent)
    PHANTOM_EQUIV_ALPHA: float = 0.05        # two one-sided tests at this level = the 90 percent interval
    ASYMMETRY_EQUAL_PP: float = 2.0          # decoy-target moderator: |HD minus HF| below this = symmetric
    DIVERGENCE_EQUAL_PP: float = 2.0         # persona and sequential arms: |gap| below this = agrees
    FORMAT_MODEL_FOLLOW_RATIO: float = 0.25  # format module: model interaction >= this share of human's
    # ---- Re-running the model calls ----
    RERUN_RULE: float = 0.95                 # a re-run reproduces a model effect when the deposited estimate
    #                                          lies inside the re-run's bootstrap interval at this level


C = RegisteredConstants()

# The tie-break for a model's majority class is a rule, not a number; it is registered alongside.
# authors' rule 2026-09-29 (after an independent manuscript read): ties go to the LESS FAITHFUL class,
# from the most to the least conservative (replaces the earlier alphabetical order).
CLASS_ORDER = ("ANTI", "LOW", "PARTIAL", "OVER", "HIGH")
TIE_BREAK_RULE = ("the less faithful class, in the order " + ", ".join(CLASS_ORDER) +
                  " (most to least conservative); the first wins")

# The Holm families (the Method: "within families of effects"; similarity is scored apart).
HOLM_FAMILIES = {
    "non_similarity": ["FRQ", "RNG", "PHT", "SOT", "SYM", "MOT"],
    "similarity": ["SIM"],
    "format_interaction": ["FRQ:words", "FRQ:pictures", "SOT:words", "SOT:pictures"],
}

# The registered calibration decision rule for the final wave (Web Appendix F): a pair is final when the
# compromise target's share lies inside the band, or when its 95 percent interval overlaps the band while
# the share itself stays between the two interval-route limits. The analysis reads it only to CHECK the
# registered deviation list below against the calibration record, by option identity.
CALIBRATION_DECISION_RULE = dict(band_lo_pct=40.0, band_hi_pct=45.0,
                                 interval_route_lo_pct=33.0, interval_route_hi_pct=50.0)

# The registered deviation sensitivity set: the six
# adjustable pairs retained after failing the decision rule, by option identity, and the published pairs whose
# measured POINT share lies outside the 25 to 75 percent hard limits (only water bottles, 80.0 percent;
# televisions at 74.7 percent is inside, and its hard-limit flag is a data error). SEVEN pairs. (category,
# stimulus tier, format). The analysis computes all seven from the calibration record, by the decision rule
# and by the point rule, and REFUSES to run when the result differs from this list; no flag decides anything.
DEVIATION_SENSITIVITY_PAIRS = (
    ("backpacks", 2, "numbers"), ("earbuds", 2, "numbers"), ("restaurants", 2, "numbers"),
    ("standing_desks", 3, "numbers"), ("water_bottles", 2, "pictures"), ("electric_kettles", 3, "numbers"),
    ("water_bottles", 1, "numbers"),
)

# The two papers that printed the published values, with the date each went online (its publisher's online date, read
# from Crossref on 2026-11-25), keyed as Design.source_paper names them. The test of retrieval (the editor's read of
# 2026-11-24, item 2.2(c)): a model whose training data end before a paper went online could not have read that paper's
# values, so its test uses only the other paper's categories, and when both papers went online after its training
# data end, the test is not run for that model. A model's training cutoff is the date its developer states, else its
# release date, as recorded in the registry of models on the first day of data collection.
SOURCE_PAPERS_ONLINE = {
    "upscaling": ("Evangelidis, Levav, and Simonson (2023)", "2022-12-19"),
    "extremity": ("Sharif, Webb, and Bhatia (2025)", "2025-11-25"),
}

# (the part of the Analysis Plan, named by its heading as the manuscript names it, plain reader-facing meaning). Order
# follows the dataclass. The labels are printed verbatim in Table WA-E1 (2026-11-24: by heading, never "Step N").
S0H = "Validity criteria, human criterion"
S0M = "Validity criteria, model criterion"
S1S = "Human benchmarks, stimulus handling"
S1F = "Human benchmarks, first-trial check"
S1T = "Method, similarity supplement check"
S2C = "Fidelity map and classes"
S2E = "Method, model estimates"
S3P = "Tests of the three accounts"
S3R = "Tests of the three accounts, test of retrieval"
S3O = "Tests of the three accounts, test of rational override"
S3B = "Tests of the three accounts, test of reason-based choice"
S3G = "Tests of the three accounts, comparison of older and newer models"
MEANING = {
    "HOLM_ALPHA": (S0H, "Holm-corrected significance level, applied separately within each family fixed in advance "
                        "(the six effects other than similarity; similarity alone; the four tests of whether the format "
                        "changes an effect)."),
    "BF_GATE": (S0H, "An effect replicates only if its Bayes factor for an effect in the predicted direction "
                     "over no effect is above 3."),
    "BF_PRIOR_SCALE_PP": (S0H, "Scale of the half-normal prior on the effect (positive values only): about the "
                               "median published effect across the seven effects."),
    "MOST_FAILED_MIN": (S0H, "When four or more of the six effects other than similarity fail the human "
                             "replication criterion, we conclude that the human replication is the main "
                             "contribution (human effects fail), and we only describe each model's comparison with people."),
    "POSITIVE_CONTROL_ALPHA": (S0H, "The positive controls are the frequency-decoy cells of the stimulus sets that we built "
                                    "(the new values and the new categories) in which the decoy favors the premium option and "
                                    "whose two-option pair met the calibration rule (the external hard drives and the "
                                    "televisions at the new values and the robot vacuums), and the compromise effect. The frequency-decoy control passes when its pooled difference is "
                                    "in the predicted direction, is significant at .05, and has a Bayes factor above 3; the "
                                    "compromise control passes when compromise meets the human replication criterion."),
    "PARSE_FLOOR": (S0M, "A model cell needs at least 95 percent readable answers. A model is not assessable when "
                         "fewer than 95 percent of its answers in the neutral condition are readable."),
    "REFUSAL_CEIL": (S0M, "A model is not assessable when more than 5 percent of its calls in the neutral condition "
                          "are refusals."),
    "CEIL_HI": (S0M, "A model's share of one option above 90 percent in a two-option cell means that the model almost "
                     "always makes the same choice, so a decoy can barely change it; that cell is left out."),
    "CEIL_LO": (S0M, "A model's share of one option below 10 percent in a two-option cell means that nearly all of the "
                     "model's choices are of the other option, so a decoy can barely change them; that cell is left out."),
    "NOT_ASSESSABLE_FRAC": (S0M, "A model is not assessable when it loses more than a third of its cells, when "
                                 "fewer than 95 percent of its answers in the neutral condition are readable, or "
                                 "when more than 5 percent of its calls in the neutral condition are refusals. A "
                                 "model loses a cell when fewer than 95 percent of the cell's answers are readable "
                                 "(unreadable answers and refusals both count against a cell) or when we leave the "
                                 "cell out under the ceiling rule."),
    "COMPROMISE_TARGET_MAX_BASELINE_PCT": (S1S, "A compromise cell is only described, not tested, when the compromise "
                                                "target's measured two-option share is 50 percent or more."),
    "COMPROMISE_RULE_COVERS_PUBLISHED_TIER": (S1S, "The compromise rule above also applies to the published "
                                                   "values, which were never adjusted (five of their "
                                                   "seven compromise targets start at 64.6 to 80.0 percent), "
                                                   "because the compromise effect can reverse when the target "
                                                   "starts ahead."),
    "HARD_LIMIT_LO_PCT": (S1S, "Lower limit, fixed in advance, on a two-option baseline share, applied to the measured "
                               "share itself (the point estimate)."),
    "HARD_LIMIT_HI_PCT": (S1S, "Upper limit, fixed in advance, on a two-option baseline share, applied to the measured "
                               "share itself (the point estimate)."),
    "FIRST_TRIAL_ALPHA": (S1F, "Family-wise level for comparing first-choice and later-choice estimates across "
                               "the seven pooled effects (Holm)."),
    "FIRST_TRIAL_MIN_DIVERGENCE_PP": (S1F, "The first-trial estimates become the benchmark only if a significant effect also differs by more "
                                           "than 5 points between the full-sample and the first-trial estimate. They then "
                                           "become the benchmark of all seven effects, and we apply the human replication "
                                           "criterion to them; every effect that meets it stays confirmatory, whatever its "
                                           "size."),
    "SIM_TOPUP_ALPHA": (S1T, "The similarity effect is estimated separately from choices in the main design and from "
                             "similarity-supplement choices; their difference is tested at .05."),
    "SIM_TOPUP_MAX_GAP_PP": (S1T, "If the two estimates differ by more than 5 points and the difference is "
                                  "significant, the estimate from the main design becomes the similarity benchmark."),
    "NEAR_NULL_HUMAN_PP": (S2C, "Human effects smaller than 2 points are not classed."),
    "HIGH_RATIO": (S2C, "Close: same sign and the model effect is between 70 and 150 percent of the human effect."),
    "OVER_RATIO": (S2C, "Larger: same sign and above 150 percent of the human effect. We count a larger effect on the "
                        "published values as consistent with retrieval of a published finding, and the same for a "
                        "model phantom effect that is larger against a replicated human phantom effect or, where the "
                        "human phantom effect failed the criterion, more than 3 points in the phantom's predicted "
                        "direction."),
    "PARTIAL_RATIO": (S2C, "Smaller: same sign and 25 to 70 percent of the human effect; below 25 percent, or reversed by 3 "
                           "points or less, is much smaller."),
    "ANTI_MIN_PP": (S2C, "The smallest model effect that counts. Reversed: a model effect opposite in sign to a replicated "
                         "human effect and larger than 3 points (a smaller reversal is much smaller). We use the same "
                         "3-point cutoff to decide whether a model shows an effect in the test of rational override, whether a model effect "
                         "in a cell whose effect failed in people is reported as an effect without a human "
                         "counterpart, and whether a budget-target human effect counts as the disadvantaged-target "
                         "reversal (a fall in the share of the budget option the decoy was built to favor) in the "
                         "comparison of decoy targets."),
    "BOOTSTRAP_RESAMPLES": (S2E, "Beside every model effect, we report the number of calls behind it "
                                 "and a percentile bootstrap interval from 2,000 resamples of the calls, drawn "
                                 "within each combination of stimulus, option order and paraphrase, with a fixed "
                                 "seed; we use this interval to describe the model effect, never as a test. We draw "
                                 "the same 2,000 resamples together with resamples of the human participants within "
                                 "each cell, and we judge the result of each test of the three accounts against the "
                                 "intervals from these joint resamples."),
    "BOOTSTRAP_LEVEL": (S2E, "The bootstrap interval covers the central 95 percent of the resampled effects."),
    "BOOTSTRAP_SEED": (S2E, "The fixed seed of the bootstrap, so the reported intervals reproduce exactly."),
    "FIDELITY_FOLD_AT": (S3P, "A group's fidelity (a group is one side of a comparison in these tests, such as one stimulus set, one "
                              "position in the argument-strength ordering, or one generation) is the model effect divided by the human effect, pooled across the "
                              "group's cells and weighted by the size of the human effect. A value above 1 is replaced by 2 minus "
                              "the value, so an effect that is too large and one that is too small by the same amount count alike."),
    "FIDELITY_RATIO_MIN": (S3P, "Every group fidelity is capped below at -1 (a full reversal)."),
    "T1_STEEP_DROP": (S3R,
                      "Steep fall: fidelity falls by more than 0.30 from the published values to the new values, "
                      "compared on the same categories (each effect on the categories it has in both stimulus sets). "
                      "We only describe the new categories, as an extension of the comparison."),
    "T1_FLAT_SLOPE": (S3R,
                      "No difference: fidelity changes by less than 0.10 between the two stimulus sets. We conclude a "
                      "steep fall only when the 95 percent interval of the fall also lies wholly above 0.10, and no "
                      "difference only when that interval lies wholly below 0.30; any other result is "
                      "inconclusive."),
    "RECOGNITION_CUTOFF": (S3O,
                           "A model names the decoy of an effect when the share of its answers to the suspicion probe of "
                           "that effect's choice sets that name the added option exceeds, by at least one half, the share "
                           "of its answers to the probe of the matching two-option sets that call the set strategically "
                           "constructed. A model that never calls a two-option set constructed must name the decoy in at "
                           "least half of its answers, and a model that calls every set constructed cannot name the "
                           "decoy by saying yes alone."),
    "T3_LADDER_STEP": (S3B,
                       "Decline: fidelity at the top position exceeds fidelity at the bottom position by more than "
                       "0.30; a decline confirmed by its interval is the reason-based-choice failure (S4). Reversal: fidelity at the bottom "
                       "position exceeds fidelity at both the top and the middle position by more than 0.30. We "
                       "describe a reversal and draw no conclusion from it."),
    "T3_LADDER_FLAT": (S3B,
                       "No difference: the top and bottom positions lie within 0.12 of one another. We conclude a "
                       "decline or a reversal only when the 95 percent interval of each difference that it uses also lies "
                       "wholly beyond 0.12, and no difference only when the interval of the top minus the bottom "
                       "position lies wholly within 0.30 either way; any other result is inconclusive."),
    "T5_TRAJECTORY_STEP": (S3G,
                           "Rise or fall: newer-generation fidelity minus older-generation fidelity beyond "
                           "0.15 either way, with its whole 95 percent interval beyond 0.15 on the same side; no "
                           "difference: a difference within 0.15, with the whole interval within 0.15; any other result "
                           "is inconclusive. A family is a developer's closed models or its open models. The fidelity "
                           "of a generation pools the choice sets of all the family's models of that generation (the "
                           "models of each generation are named in Table WA-D1, and their sizes are not held fixed), and we "
                           "repeat the comparison with reasoning off in both generations, within the models that can "
                           "switch reasoning off and those that have no reasoning mode. We report the result once for "
                           "each family and draw no conclusion about any model from it."),
    "T5_REASONING_STEP": (S3G,
                          "Reasoning comparison: fidelity is lower with more reasoning when fidelity at the lower "
                          "reasoning setting exceeds "
                          "fidelity at the higher setting by more than 0.15, with its whole 95 percent interval "
                          "above 0.15; no clear effect when the difference and its whole interval lie at or below "
                          "0.15; any other result is inconclusive."),
    "PHANTOM_BAND_PP": ("Phantom equivalence",
                        "We apply the equivalence judgment only when the pooled human phantom effect misses the "
                        "replication criterion: the phantom then counts as absent when its 90 percent interval lies "
                        "inside minus 2 to plus 2 points, and as not detected otherwise. A phantom that meets the "
                        "criterion is reported as present."),
    "PHANTOM_EQUIV_ALPHA": ("Phantom equivalence",
                            "The equivalence judgment is two one-sided tests at .05 each, which is the 90 percent "
                            "interval."),
    "ASYMMETRY_EQUAL_PP": ("Secondary comparisons",
                           "Decoy targets: when premium-target and budget-target effects lie within 2 points of each "
                           "other, we conclude that the effect is symmetric."),
    "DIVERGENCE_EQUAL_PP": ("Secondary comparisons",
                            "Persona condition and choice sequences in one conversation: when a result lies within 2 points of the neutral "
                            "condition, we conclude that the two agree."),
    "FORMAT_MODEL_FOLLOW_RATIO": ("Secondary comparisons",
                                  "Format conditions: when the human format interaction is significant, a model reproduces it if its "
                                  "own interaction has the same sign and at least 25 percent of the human size."),
    "RERUN_RULE": ("Re-running the model calls",
                   "We conclude that a re-run of the model calls reproduces a model effect when the deposited "
                   "estimate lies inside the re-run's 95 percent bootstrap interval over calls."),
}

# How each value prints in the reader-facing table (units a reader expects).
UNITS = {
    "BF_PRIOR_SCALE_PP": "points", "FIRST_TRIAL_MIN_DIVERGENCE_PP": "points",
    "SIM_TOPUP_MAX_GAP_PP": "points", "NEAR_NULL_HUMAN_PP": "points", "ANTI_MIN_PP": "points",
    "PHANTOM_BAND_PP": "points", "ASYMMETRY_EQUAL_PP": "points", "DIVERGENCE_EQUAL_PP": "points",
    "COMPROMISE_TARGET_MAX_BASELINE_PCT": "percent", "HARD_LIMIT_LO_PCT": "percent", "HARD_LIMIT_HI_PCT": "percent",
}


def rows():
    """(group, name, value, meaning) for every registered constant, in declaration order."""
    out = []
    for f in fields(RegisteredConstants):
        grp, meaning = MEANING[f.name]
        out.append((grp, f.name, getattr(C, f.name), meaning))
    return out
