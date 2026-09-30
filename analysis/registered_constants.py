"""registered_constants.py: every numeric cutoff the registered analysis uses, in one named structure.

Each field is a registered decision: the human replication criterion (Holm level, Bayes factor threshold
and prior scale), the compromise precondition and the stimulus hard limits, the per-model data-quality
criterion (parse floor, refusal ceiling, room-to-move limits), the first-choice comparability check, the
fidelity-class ratios, the cutoffs of the pattern tests T1 to T5, the recognition cutoff, and the bounds of
the equivalence and secondary readings. MEANING gives each field its plain one-line meaning, HOLM_FAMILIES
the correction families, and TIE_BREAK_RULE the rule for a model's majority class. analyze.py reads every
cutoff from here. Changing a value after data exist is a deviation that must be reported.
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
    MOST_FAILED_MIN: int = 4                 # this many of the six non-similarity effects failing -> S7
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
    FIRST_TRIAL_MIN_EFFECT_PP: float = 8.0   # after a fallback, confirmatory only at or above this size
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
    RECOGNITION_CUTOFF: float = 0.50         # recognition-probe rate at or above this = "knows it"
    T3_LADDER_STEP: float = 0.30             # ladder: top-minus-bottom gap above this = declines (or reversed)
    T3_LADDER_FLAT: float = 0.12             # ladder: |top-minus-bottom| below this = flat
    T5_TRAJECTORY_STEP: float = 0.15         # trajectory: new-minus-old fidelity beyond this = moves
    T5_REASONING_STEP: float = 0.15          # reasoning toggle: off-minus-on fidelity above this = lowers
    MODEL_ACCOUNT_MIN_AGREE: int = 4         # per-effect accounts must agree on this many effects
    # ---- Equivalence and secondary readings ----
    PHANTOM_BAND_PP: float = 4.0             # phantom equivalence bound, plus or minus, percentage points
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
# memorization tier, format). The analysis computes all seven from the calibration record, by the decision rule
# and by the point rule, and REFUSES to run when the result differs from this list; no flag decides anything.
DEVIATION_SENSITIVITY_PAIRS = (
    ("backpacks", 2, "numbers"), ("earbuds", 2, "numbers"), ("restaurants", 2, "numbers"),
    ("standing_desks", 3, "numbers"), ("water_bottles", 2, "pictures"), ("electric_kettles", 3, "numbers"),
    ("water_bottles", 1, "numbers"),
)

# (step label as the manuscript's Analysis Plan names it, plain reader-facing meaning). Order follows the
# dataclass. The step labels are printed verbatim in Table WA-E1.
S0H = "Step 0, human criterion"
S0M = "Step 0, model criterion"
S1S = "Step 1, stimulus handling"
S1F = "Step 1, first-trial check"
S1T = "Method, similarity supplement check"
S2C = "Step 2, fidelity classes"
S2E = "Method, model estimates"
S3P = "Step 3, pattern tests"
MEANING = {
    "HOLM_ALPHA": (S0H, "Holm-corrected significance level, applied separately within each registered family "
                        "(the six non-similarity effects; similarity alone; the four format interaction tests)."),
    "BF_GATE": (S0H, "An effect replicates only if its Bayes factor for an effect in the predicted direction "
                     "over no effect is above 3."),
    "BF_PRIOR_SCALE_PP": (S0H, "Scale of the half-normal prior on the effect (positive values only): about the "
                               "median published effect across the seven effects."),
    "MOST_FAILED_MIN": (S0H, "Scenario S7 (Human effects fail) applies when four or more of the six "
                             "non-similarity effects fail the human replication criterion."),
    "POSITIVE_CONTROL_ALPHA": (S0H, "The positive controls are the frequency-decoy cells whose target is the "
                                    "premium option and the compromise effect. The premium-target frequency-decoy "
                                    "control holds when its pooled contrast runs in the predicted direction, is "
                                    "significant at .05, and has a Bayes factor above 3; the compromise control "
                                    "holds when compromise meets the human replication criterion."),
    "PARSE_FLOOR": (S0M, "A model cell needs at least 95 percent readable answers."),
    "REFUSAL_CEIL": (S0M, "A model may refuse at most 5 percent of calls."),
    "CEIL_HI": (S0M, "A model's share of one option above 90 percent in a two-option cell leaves no room to "
                     "move; that cell is held out."),
    "CEIL_LO": (S0M, "A model's share of one option below 10 percent in a two-option cell leaves no room to "
                     "move; that cell is held out."),
    "NOT_ASSESSABLE_FRAC": (S0M, "A model is not assessable when it loses more than one third of its cells, "
                                 "counting together the cells with fewer than 95 percent readable answers "
                                 "(unreadable answers and refusals both count against a cell) and the cells held "
                                 "out by the ceiling rule."),
    "COMPROMISE_TARGET_MAX_BASELINE_PCT": (S1S, "A compromise cell is descriptive when the compromise target's "
                                                "measured two-option share is at or above 50 percent."),
    "COMPROMISE_RULE_COVERS_PUBLISHED_TIER": (S1S, "The compromise rule above also applies to the published-"
                                                   "values tier, whose values were never adjusted (five of its "
                                                   "seven compromise targets start at 64.6 to 80.0 percent), "
                                                   "because the compromise effect can reverse when the target "
                                                   "starts ahead."),
    "HARD_LIMIT_LO_PCT": (S1S, "Lower registered limit on a two-option baseline share, applied to the measured "
                               "share itself (the point estimate)."),
    "HARD_LIMIT_HI_PCT": (S1S, "Upper registered limit on a two-option baseline share, applied to the measured "
                               "share itself (the point estimate)."),
    "FIRST_TRIAL_ALPHA": (S1F, "Family-wise level for comparing first-choice and later-choice estimates across "
                               "the seven pooled effects (Holm)."),
    "FIRST_TRIAL_MIN_DIVERGENCE_PP": (S1F, "The check fires only if a significant effect also differs by more "
                                           "than 5 points between the full-sample and the first-trial estimate."),
    "FIRST_TRIAL_MIN_EFFECT_PP": (S1F, "After the check fires, an effect is confirmatory only if its first-trial "
                                       "size is at least 8 points; a smaller effect that replicates is classed "
                                       "descriptively only and leaves the model's overall class, the model-level "
                                       "account and every pattern test."),
    "SIM_TOPUP_ALPHA": (S1T, "The similarity effect is estimated separately from core-design choices and from "
                             "similarity-supplement choices; their difference is tested at .05."),
    "SIM_TOPUP_MAX_GAP_PP": (S1T, "If the two estimates differ by more than 5 points and the difference is "
                                  "significant, the core-design estimate becomes the similarity benchmark."),
    "NEAR_NULL_HUMAN_PP": (S2C, "Human effects smaller than 2 points are not classed."),
    "HIGH_RATIO": (S2C, "HIGH: same direction and the model effect is between 70 and 150 percent of the human "
                        "effect."),
    "OVER_RATIO": (S2C, "OVER: same direction and above 150 percent of the human effect. An OVER effect on the "
                        "published-values tier is read as consistent with retrieval of a described regularity, "
                        "and so is a model phantom effect that is OVER against a replicated human phantom effect "
                        "or, where the human phantom effect failed the criterion, larger than 3 points in the "
                        "phantom's predicted direction."),
    "PARTIAL_RATIO": (S2C, "PARTIAL: same direction and 25 to 70 percent of the human effect; below 25 percent, "
                           "or reversed by 3 points or less, is LOW."),
    "ANTI_MIN_PP": (S2C, "The registered minimum model effect. ANTI: a model effect opposite in sign to a "
                         "replicated human effect and larger than 3 points (a smaller reversal is LOW). The same "
                         "3 points decide whether a model shows an effect in the knows-it-versus-shows-it test, "
                         "whether a model effect in a cell whose effect failed in humans is reported as an "
                         "effect without a human counterpart, and whether a budget-target human effect reads as "
                         "the disadvantaged-target reversal in the decoy-target moderator."),
    "BOOTSTRAP_RESAMPLES": (S2E, "Beside every model effect the analysis reports the number of calls behind it "
                                 "and a percentile bootstrap interval from 2,000 resamples of the calls, drawn "
                                 "within each combination of stimulus, option order and paraphrase, with a fixed "
                                 "seed; the interval describes the model effect and is never a test. The same "
                                 "2,000 resamples, drawn together with resamples of the human participants within "
                                 "each cell, give the intervals the pattern-test readings are resolved against."),
    "BOOTSTRAP_LEVEL": (S2E, "The bootstrap interval covers the central 95 percent of the resampled effects."),
    "BOOTSTRAP_SEED": (S2E, "The fixed seed of the bootstrap, so the reported intervals reproduce exactly."),
    "FIDELITY_FOLD_AT": (S3P, "A group's fidelity is the model effect divided by the human effect, pooled across "
                              "the group's cells and weighted by the size of the human effect. A value above 1 "
                              "is folded to 2 minus the value, so an overshoot and an undershoot of the same "
                              "size count alike."),
    "FIDELITY_RATIO_MIN": (S3P, "Every group fidelity is capped below at -1 (a full reversal)."),
    "T1_STEEP_DROP": ("Step 3, memorization test (T1)",
                      "Steep: fidelity falls by more than 0.30 from the published-values tier to the new-values "
                      "tier, compared on the same categories (each effect on the categories it has on both tiers). "
                      "The invented tier is a supporting extension, reported descriptively."),
    "T1_FLAT_SLOPE": ("Step 3, memorization test (T1)",
                      "Flat: fidelity changes by less than 0.10 between the two tiers. A steep reading also needs "
                      "the 95 percent interval of the drop to lie wholly above 0.10, and a flat reading "
                      "needs that interval to lie wholly below 0.30; any other result is not resolved."),
    "RECOGNITION_CUTOFF": ("Step 3, knows-it-versus-shows-it test (T2)",
                           "A model knows the manipulation when the recognition probe detects it in at least "
                           "half of the probe calls. For a reversed ladder, recognition at or above this on "
                           "every attraction or compromise effect the model misses (classed LOW or ANTI) reads "
                           "as rational override on choice sets that offer an argument; otherwise the reversed "
                           "ladder is reported with no account attributed."),
    "T3_LADDER_STEP": ("Step 3, argument-strength test (T3)",
                       "Declines: the top position exceeds the bottom position by more than 0.30; a resolved "
                       "decline reads as reason construction (S3). Reversed: the bottom position exceeds both the "
                       "top and the middle position by more than 0.30."),
    "T3_LADDER_FLAT": ("Step 3, argument-strength test (T3)",
                       "Flat: the top and bottom positions lie within 0.12 of one another. A declining or reversed "
                       "reading also needs the 95 percent interval of each difference it uses to lie wholly beyond "
                       "0.12, and a flat reading needs the interval of the top minus the bottom position to lie "
                       "wholly within 0.30 either way; any other result is not resolved."),
    "T5_TRAJECTORY_STEP": ("Step 3, trajectory test (T5)",
                           "Rising or falling: newer-generation fidelity minus older-generation fidelity beyond "
                           "0.15 either way, with its whole 95 percent interval beyond 0.15 on the same side; flat: "
                           "a difference within 0.15, with the whole interval within 0.15; any other result is not "
                           "resolved."),
    "T5_REASONING_STEP": ("Step 3, trajectory test (T5)",
                          "Reasoning comparison: reasoning lowers fidelity when fidelity at the lower reasoning "
                          "setting exceeds "
                          "fidelity at the higher setting by more than 0.15, with its whole 95 percent interval "
                          "above 0.15; no clear effect when the difference and its whole interval lie at or below "
                          "0.15; any other result is not resolved."),
    "MODEL_ACCOUNT_MIN_AGREE": ("Precedence rule, accounts",
                                "A model-level account is claimed only when the per-effect readings agree on at "
                                "least four of the six non-similarity effects that passed the human criterion; "
                                "otherwise accounts are reported per effect only."),
    "PHANTOM_BAND_PP": ("Phantom equivalence",
                        "The pooled human phantom effect is judged absent when its 90 percent interval lies "
                        "inside minus 4 to plus 4 points."),
    "PHANTOM_EQUIV_ALPHA": ("Phantom equivalence",
                            "The equivalence judgment is two one-sided tests at .05 each, which is the 90 percent "
                            "interval."),
    "ASYMMETRY_EQUAL_PP": ("Secondary readings",
                           "Decoy-target moderator: premium and budget target effects within 2 points read as "
                           "symmetric."),
    "DIVERGENCE_EQUAL_PP": ("Secondary readings",
                            "Persona condition and sequential sessions: within 2 points of the neutral condition "
                            "reads as agreement."),
    "FORMAT_MODEL_FOLLOW_RATIO": ("Secondary readings",
                                  "Format module: when the human format interaction is significant, a model "
                                  "follows it if its own interaction has the same sign and at least 25 percent "
                                  "of the human size."),
    "RERUN_RULE": ("Re-running the model calls",
                   "A re-run of the model calls reproduces a model effect when the deposited estimate lies "
                   "inside the re-run's 95 percent bootstrap interval over calls."),
}

# How each value prints in the reader-facing table (units a reader expects).
UNITS = {
    "BF_PRIOR_SCALE_PP": "points", "FIRST_TRIAL_MIN_DIVERGENCE_PP": "points", "FIRST_TRIAL_MIN_EFFECT_PP": "points",
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
