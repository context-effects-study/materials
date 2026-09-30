"""synth.py: the synthetic data for the analysis dress rehearsal.

It writes data in exactly the shapes the study will produce: a human long table (one row per choice, the
columns analysis/ingest.py writes) and a model call log (one record per call, the fields models/run.py
writes). Into both it plants known truths: human effect sizes, model behavior profiles, a recognition-probe
outcome, a format drop and a generation trajectory, so analyze.py can be scored against an answer key.
The profiles cover every named scenario of the decision tree and the two worked walk-throughs. Fixed seed.

Run: python analysis/synth.py      (a short check that the planted human effects are recovered)
"""
import random, math
from collections import defaultdict

# ---------------------------------------------------------------------------
# The fixed lattice (placeholders for the real stimuli.json coordinates).
# ---------------------------------------------------------------------------
CATS = list(range(10))                 # categories 0-6 are "published", 7-9 are "invented"
PUB = set(range(7))                    # published categories carry tiers 1 (classic) and 2 (new values)
INVENTED = set(range(7, 10))           # invented categories carry only tier 3 (never published)
# 2026-09-29 revision: the real category each synthetic index stands for, so the rehearsal can carry
# the REAL calibration record (measured baselines, deviation flags, compromise-precondition slices,
# format-module categories) onto the synthetic lattice and exercise every flag-driven branch. Only the
# slice-level design facts travel; option identities (HD/HF targets) do not, because synthetic rows code
# chose_target against an abstract target (analyze.Design.from_synth keeps targets empty).
CAT_NAMES = {0: "backpacks", 1: "bluetooth_speakers", 2: "earbuds", 3: "hard_drives", 4: "restaurants",
             5: "televisions", 6: "water_bottles", 7: "electric_kettles", 8: "robot_vacuums",
             9: "standing_desks"}
# Rate at which a similarity chooser picks the CLONE, and a compromise chooser the new extreme, drawn
# independently of the planted effect, so the registered RELATIVE shares recover the planted truth.
CLONE_RATE = 0.25
EXT_RATE = 0.25

# The decoy-target HD/HF split (the design review-decision (b); R3-2C; CONTRACTS sec.A: "decoy targets split HD/HF
# across categories", carried in stimuli.json's is_hd). For the attraction decoys (FRQ/RNG/PHT) some
# categories make the high-desirability option the target (HD) and some make the high-feasibility
# option the target (HF). The registered moderator reads whether the effect is asymmetric across these
# two target kinds (Heath-Chatterjee). The split is planted only on the PUBLISHED categories and
# balanced there (three HD, three HF), so the pooled effect that the criterion and the FRQ recovery check
# read is unchanged and so the memorization gradient (tier 3 = the invented neutral categories) is not
# perturbed by the asymmetry. A synthetic stimuli.json is not needed at analysis-validation time.
DECOY_TARGET = {0: "HD", 1: "HD", 2: "HD", 3: "HF", 4: "HF", 5: "HF",
                6: "neutral", 7: "neutral", 8: "neutral", 9: "neutral"}

def cat_decoy_target(cat):
    """'HD' when the category's decoy target is the high-desirability option, 'HF' when it is the
    high-feasibility option, 'neutral' when this category does not carry the asymmetry split."""
    return DECOY_TARGET.get(cat, "neutral")

def cat_is_hd(cat):
    """True only for the HD-target categories (used for the is_hd contract column). The HF and neutral
    categories are both is_hd = 0; the moderator separates them by the decoy-target field, not by this
    flag, but the contract column itself is binary, so neutral categories carry is_hd = 0."""
    return cat_decoy_target(cat) == "HD"

# Planted asymmetry multiplier for the decoy-target split: the HD-target arm carries a stronger
# effect, the HF-target arm a weaker effect, which is the predicted Heath-Chatterjee asymmetry the
# moderator is built to detect. Applied only to the attraction decoys (FRQ/RNG/PHT) on the HD/HF
# categories. The two multipliers average to 1.0 across the balanced three-HD/three-HF published
# split, so the pooled FRQ/RNG/PHT effect is unchanged; only the HD-versus-HF split carries the
# asymmetry. (PHT is a planted null, so the split leaves it null on both arms.)
HD_TARGET_MULT = 1.40
HF_TARGET_MULT = 0.60
STRUCTS = ["BIN", "SOT", "FRQ", "RNG", "PHT", "SYM", "SIM", "MOT", "EXC"]
# The seven tested effects (BIN is the shared control for six of them; EXC is the extremity control for
# MOT, NOT itself a tested effect; PHT is planted as a human null on purpose). EFFECT_STRUCTS lists the
# treatment structures that carry an effect to recover; EXC is excluded here exactly as BIN is.
EFFECT_STRUCTS = ["FRQ", "RNG", "PHT", "SOT", "SYM", "SIM", "MOT"]
FORMATS = ["numbers", "words", "pictures"]

# Planted HUMAN effect sizes (proportion points on the registered statistic), per the verified
# landscape record. These are the truths the human benchmark must recover.
TRUTH = {"FRQ": 0.10, "RNG": 0.13, "PHT": 0.00,   # phantom planted NULL (the fragile, diagnostic effect)
         "SOT": 0.12, "SYM": 0.18, "SIM": 0.06, "MOT": 0.10}
TIER_ATTEN = {1: 1.00, 2: 0.85, 3: 0.75}          # Hasan: novel stimuli give weaker human effects
BASE = 0.42                                         # disadvantaged-target baseline (the 40-45 band)

# The argument-strength ladder rank used by the LADDER/REASONER plant: higher rung = stronger
# articulable argument the choice set hands the chooser. Attraction decoys at the top, compromise
# mid, extremity at the bottom. (Source: the Analysis Plan T3; analysis_plan T3.)
LADDER_RANK = {"FRQ": 1.00, "RNG": 1.00, "PHT": 0.30, "SOT": 0.45, "SYM": 0.55, "SIM": 0.45, "MOT": 0.20}

# Format fidelity multiplier used by the text-bound (REASONER) plant for test T4: full on numbers,
# weaker on words, gone on pictures. A faithful model uses 1.0 across all three.
TEXTBOUND_FORMAT = {"numbers": 1.00, "words": 0.55, "pictures": 0.05}


def invlogit(x):
    return 1.0 / (1.0 + math.exp(-x))


def _clip(p):
    return min(0.999, max(0.001, p))


# ---------------------------------------------------------------------------
# Model archetypes. Each is built to drive ONE decision-tree outcome. The
# scenario it is meant to show is recorded so the rehearsal can assert routing.
# family lets S5 (Family-specific) be planted as two members of one family
# that disagree. generation/reasoning drive the trajectory test T5.
# ---------------------------------------------------------------------------
MODEL_ARCHETYPES = {
    # S1 High fidelity: matches humans everywhere, flat across tiers and formats, does not
    # recognize the manipulation (shows-without-recognizing).
    "FAITHFUL":   dict(scenario="S1", family="famA", generation="new", reasoning="off"),
    # S2 Retrieval only (the original MEMORIZER): effect only on the classic published tier.
    "PARROT":     dict(scenario="S2", family="famB", generation="new", reasoning="off"),
    # S3 Reason construction (the original LADDER, now also text-bound across formats for the
    # confirmatory T4 signature): fidelity graded down the argument ladder AND falling numbers->pictures.
    "REASONER":   dict(scenario="S3", family="famC", generation="new", reasoning="off"),
    # S4 Rational override: recognizes the decoy but does not move; inverts the effects (ANTI/LOW).
    "OVERRIDER":  dict(scenario="S4", family="famD", generation="new", reasoning="on"),
    # S5 Family-specific: two members of one family disagree -> family-specific patterns.
    "DIVIDED_A":  dict(scenario="S5", family="famE", generation="new", reasoning="off"),  # faithful member
    "DIVIDED_B":  dict(scenario="S5", family="famE", generation="new", reasoning="off"),  # anti member
    # S6 Rising fidelity: PARTIAL today, but the NEWER generation of this family is more faithful (rising T5).
    "CONVERGE_OLD": dict(scenario="S6", family="famF", generation="old", reasoning="off"),
    "CONVERGE_NEW": dict(scenario="S6", family="famF", generation="new", reasoning="off"),
    # Two worked walk-throughs from the Analysis Plan.
    # Walk 1: match on classic, diverge on novel (headline retrieval surprise) -> S2 reading via T1.
    "WALK1_PARROT": dict(scenario="WALK1", family="famG", generation="new", reasoning="off"),
    # Walk 2: faithful on attraction-frequency, reverses compromise, flat T1, recognizes compromise.
    "WALK2_MIXED": dict(scenario="WALK2", family="famH", generation="new", reasoning="off"),
    # A ceiling-heavy model: picks the target in nearly every binary set, so no room to move ->
    # the model criterion's not-assessable / no-room-to-move branch (Step 0b).
    "CEILING":    dict(scenario="GATE_CEILING", family="famI", generation="new", reasoning="off"),
    # A refuser: high refusal/unparse rate -> the model criterion's parse/refusal failure branch.
    "REFUSER":    dict(scenario="GATE_REFUSAL", family="famJ", generation="new", reasoning="off"),
    # Reviewer 4's own example: the model misses the established effects whose
    # sets offer a statable argument (attraction LOW, compromise reversed) and matches the effects whose
    # sets offer none (upscaling, extremity). Two versions: it RECOGNIZES the manipulation on the effects
    # it misses (-> rational override on arguable sets), or it does not (-> reversed ladder, no account).
    "R4_ARGUABLE_OVERRIDE": dict(scenario="REVERSED_LADDER_OVERRIDE", family="famK", generation="new",
                                 reasoning="off"),
    "R4_ARGUABLE_NORECOG":  dict(scenario="REVERSED_LADDER", family="famL", generation="new",
                                 reasoning="off"),
    # rule 2: overshoots every effect threefold on the published tier and matches the human
    # size on the other two tiers. Its pooled class is OVER and each published-tier cell reads "consistent
    # with retrieval of a described regularity"; with the combined fidelity the memorization test no longer
    # reads the overshoot as a steep gradient.
    "OVERSHOOT_T1": dict(scenario="COMPOSITE", family="famM", generation="new", reasoning="off"),
}

# ---------------------------------------------------------------------------
# The registered model call plan the synthetic model arm mirrors. Orders per structure in numbers and words; pictures run one
# fixed order. Each grid point (stimulus x order x paraphrase) is called DRAWS_TEXT times, DRAWS_PICTURES
# for pictures. Similarity carries two clone placements of six orders each (12 grid orders per slice).
# ---------------------------------------------------------------------------
ORDERS = {"BIN": 2, "FRQ": 6, "RNG": 6, "PHT": 6, "SOT": 6, "SYM": 6, "SIM": 12, "MOT": 12, "EXC": 6}
PARAPHRASES = 3
DRAWS_TEXT = 10
DRAWS_PICTURES = 60
DRAWS_BY_STRUCT = {}          # optional per-structure override of DRAWS_TEXT (the stability sweep's remedy runs)
DRAWS_PICTURES_BY_STRUCT = {} # optional per-structure override of DRAWS_PICTURES
PERSONAS = 20                 # the persona arm: one call per persona x order x paraphrase
SEQ_CALLS_PER_CELL = 45       # the sequential arm: 1,000 seven-choice sessions spread over the backbone cells
RECOG_CALLS_PER_STIMULUS = 3  # the recognition probe: three calls per stimulus


def model_effect(model, struct, tier, fmt):
    """The planted true model effect (proportion points) for one archetype x cell x format.
    Returns the signed effect to add to BASE for the target share. BIN is always 0 (it is the
    control). This is the single place a model archetype's behavior is defined."""
    if struct in ("BIN", "EXC"):
        return 0.0                                # BIN = shared control; EXC = the extremity control arm
    h = TRUTH[struct] * TIER_ATTEN[tier]          # the human effect this model is being compared to
    a = MODEL_ARCHETYPES[model]
    if model == "FAITHFUL":
        return h
    if model == "PARROT":
        if struct == "PHT" and tier == 1:
            # 2026-09-29: this retrieval-only model recites the published phantom on tier 1 (+8 points)
            # although the planted human phantom is null: the rehearsal case for "an effect without a
            # human counterpart". The phantom exits fidelity scoring, so no routing input changes.
            return 0.08
        return h if tier == 1 else 0.0
    if model == "REASONER":
        # fidelity graded by the argument ladder AND by format (text-bound).
        return h * LADDER_RANK[struct] * TEXTBOUND_FORMAT[fmt]
    if model == "OVERRIDER":
        # detects and corrects: inverts every effect (ANTI). reasoning-on deepens the inversion.
        return -h
    if model == "DIVIDED_A":
        return h                                   # faithful member of the divided family
    if model == "DIVIDED_B":
        return -h                                  # anti member of the same family
    if model == "CONVERGE_OLD":
        return 0.45 * h                            # partial today
    if model == "CONVERGE_NEW":
        return 0.95 * h                            # newer generation closer to human (rising T5)
    if model == "WALK1_PARROT":
        return h if tier == 1 else 0.0             # match classic, diverge novel
    if model == "WALK2_MIXED":
        # faithful on attraction-frequency; reverses compromise; everything else faithful; flat T1.
        base_h = TRUTH[struct] * TIER_ATTEN[tier]
        if struct == "SOT":
            return -base_h                         # compromise reversed
        return base_h                              # FRQ and the rest faithful, tier-flat by using base_h
    if model == "CEILING":
        return 0.0                                 # handled specially: target share forced near 1
    if model == "REFUSER":
        return h                                   # would be faithful, but most calls refuse/unparse
    if model in ("R4_ARGUABLE_OVERRIDE", "R4_ARGUABLE_NORECOG"):
        if struct in ("FRQ", "RNG"):
            return 0.0                             # attraction missed (LOW)
        if struct == "SOT":
            return -h                              # compromise reversed (ANTI)
        return h                                   # upscaling, extremity, similarity, phantom faithful
    if model == "OVERSHOOT_T1":
        return 3.0 * h if tier == 1 else h         # threefold on the published tier, faithful elsewhere
    return 0.0


def model_recognizes(model, struct):
    """The planted recognition-probe outcome for test T2 (knows-it). True = the probe (run in
    isolated calls) reports the model detects the decoy/manipulation for this structure.
    OVERRIDER recognizes everything (and does not move). WALK2 recognizes the compromise it reverses.
    FAITHFUL does not recognize (shows-without-recognizing). Others: low recognition by default."""
    if model == "OVERRIDER":
        return True
    if model == "WALK2_MIXED":
        return struct == "SOT"                     # recognizes the compromise it reverses
    if model == "R4_ARGUABLE_OVERRIDE":
        return struct in ("FRQ", "RNG", "SOT")     # recognizes the arguable sets it declines to follow
    return False


# ---------------------------------------------------------------------------
# HUMAN generator (contract A long format). One row per choice. Plants the
# human truths, a per-participant random intercept (clustering via icc), a
# first-trial subsample (trial_position), and a format dimension. A "surprise"
# flag plants the S7 branch (most human effects fail the human criterion).
# ---------------------------------------------------------------------------
def gen_human(n_per_cell, rng, icc=0.10, surprise=False, with_formats=False, first_trial_break=False,
              null_effects=None, effect_overrides=None, format_attenuation=None,
              published_n_per_tier=None, first_trial_share=None, sim_topup_participants=0,
              topup_shift=0.0, null_on_hd_target=None):
    """Generate contract-A human long rows.
    icc: intraclass correlation -> per-participant random intercept (clustering).
    surprise: if True, plant most human effects at NULL (the S7 human-criterion-failure scenario).
    with_formats: if True, also generate the words/pictures format module cells (for T4 human bench).
    first_trial_break: if True, plant a first-trial divergence on FRQ in EVERY tier (first choices
        show the effect 12 points larger, later choices 2 points smaller), to exercise the registered
        first-trial comparability rule (2026-09-29: was tier 1 only, sized for the old point rule).
    null_effects: an optional set of structure names planted at a human NULL, so the criterion-driven
        fidelity exit can be tested on more than one failing effect (PHT plus a second effect). Every
        other effect keeps its planted truth, so the positive controls still replicate.
    effect_overrides: optional {structure: planted effect in proportion} that replaces the planted
        truth at every tier (2026-09-29; used to plant a significantly REVERSED human effect).
    format_attenuation: optional {format: multiplier} applied to the FRQ and SOT effects in that
        format (2026-09-29; plants a format-by-effect interaction for the format module test).
    published_n_per_tier: optional per-tier cell size for the published categories (the real design
        splits each 700-choice cell 350/350 across tiers 1 and 2); None keeps n_per_cell (rehearsal).
    first_trial_share: optional share of each cell's rows placed at trial position 1 (default 1/7,
        the backbone's one first choice in seven).
    sim_topup_participants: the number of similarity top-up participants to add;
        each makes seven similarity choices in seven different categories (trial positions 1 to 7) with
        ONE random intercept, as the top-up survey does.
    topup_shift: a planted difference (proportion) added to the top-up participants' similarity effect.
    null_on_hd_target: structures planted at a human NULL only in the categories whose
        decoy target is the premium (HD) option, to make the premium-target frequency-decoy control fail.
    Returns a list of dict rows whose columns match ingest.py's contract-A output."""
    s = math.sqrt(icc * (math.pi ** 2 / 3) / (1 - icc)) if icc > 0 else 0.0
    null_on_hd_target = set(null_on_hd_target or [])
    null_effects = set(null_effects or [])
    effect_overrides = dict(effect_overrides or {})
    format_attenuation = dict(format_attenuation or {})
    rows = []
    pid = 0
    fmts = FORMATS if with_formats else ["numbers"]
    for cat in CATS:
        tiers = [1, 2] if cat in PUB else [3]
        for struct in STRUCTS:
            for tier in tiers:
                n_cell = (published_n_per_tier if (published_n_per_tier and cat in PUB) else n_per_cell)
                for fmt in fmts:
                    # pictures are not run for the phantom (Brendl boundary; phantom stays out of pictures)
                    if fmt == "pictures" and struct == "PHT":
                        continue
                    if not _format_cell(cat, struct, tier, fmt):
                        continue            # the format module: tier 2, BIN/FRQ/SOT only (2026-09-29)
                    if surprise:
                        # S7: only the two positive controls survive; everything else is a human null.
                        eff = TRUTH[struct] * TIER_ATTEN[tier] if struct in ("FRQ",) else 0.0
                    elif struct in null_effects:
                        eff = 0.0     # planted human null (exits fidelity scoring via the criterion)
                    elif struct in null_on_hd_target and cat_decoy_target(cat) == "HD":
                        eff = 0.0     # planted null on the premium-target cells only
                    elif struct in ("BIN", "EXC"):
                        # BIN is the shared control; EXC is the extremity control (the MOT comparison arm).
                        # Both carry NO planted effect: the extremity effect lives in MOT minus EXC.
                        eff = 0.0
                    else:
                        eff = TRUTH[struct] * TIER_ATTEN[tier]
                    if struct in effect_overrides and not surprise:
                        eff = effect_overrides[struct]      # e.g. a planted REVERSED human effect
                    if struct in ("FRQ", "SOT") and fmt in format_attenuation and not surprise:
                        eff *= format_attenuation[fmt]      # planted format-by-effect interaction
                    # decoy-target HD/HF asymmetry: for the attraction decoys the effect is stronger
                    # when the target is the high-desirability option and weaker when it is the
                    # high-feasibility option (the two arms average to the planted truth across the
                    # balanced published split; neutral categories keep the plain truth).
                    if struct in ("FRQ", "RNG", "PHT") and not surprise and struct not in effect_overrides:
                        dt = cat_decoy_target(cat)
                        if dt == "HD":
                            eff *= HD_TARGET_MULT
                        elif dt == "HF":
                            eff *= HF_TARGET_MULT
                    p_target = BASE + eff
                    # each participant contributes ONE choice to this cell (the backbone is no-repeat),
                    # so a participant is a cluster across the 7 cells they see; we approximate the
                    # cluster by giving each generated row its own participant with a random intercept.
                    for k in range(n_cell):
                        u = rng.gauss(0, s)
                        # trial_position: spread 1..7 so the first-trial subsample exists for every cell
                        # (one first choice in seven, the backbone's share), or at the requested share.
                        if first_trial_share:
                            tp = 1 if (k % int(round(1.0 / first_trial_share))) == 0 else (k % 6) + 2
                        else:
                            tp = (k % 7) + 1
                        p = p_target
                        if first_trial_break and struct == "FRQ" and fmt == "numbers":
                            # first trial shows a LARGER effect than later trials (planted divergence).
                            if tp == 1:
                                p = BASE + eff + 0.12
                            else:
                                p = BASE + eff - 0.02
                        p = _clip(invlogit(math.log(p / (1 - p)) + u))
                        chose = 1 if rng.random() < p else 0
                        rows.append(_human_row(pid, cat, struct, tier, fmt, tp, chose, rng))
                        pid += 1
    # the similarity top-up survey: seven similarity choices per person, seven categories.
    for j in range(sim_topup_participants):
        u = rng.gauss(0, s)
        for k in range(7):
            cat = (j + k) % len(CATS)
            tier = 3 if cat in INVENTED else (1 if ((j // len(CATS)) + k) % 2 == 0 else 2)
            if surprise or "SIM" in null_effects:
                eff = 0.0
            else:
                eff = effect_overrides.get("SIM", TRUTH["SIM"] * TIER_ATTEN[tier])
            p = _clip(BASE + eff + topup_shift)
            p = _clip(invlogit(math.log(p / (1 - p)) + u))
            chose = 1 if rng.random() < p else 0
            row = _human_row(pid, cat, "SIM", tier, "numbers", k + 1, chose, rng)
            row["participant_id"] = f"U{j}"
            rows.append(row)
            pid += 1
    return rows


def _human_row(pid, cat, struct, tier, fmt, tp, chose_target, rng):
    """Build one contract-A row with every codebook-derived column populated, so analyze.py reads
    the SAME columns from synthetic and real data. The non-target codebook columns are filled in a
    way consistent with the structure's codebook (DATA_DICTIONARY.md sec.A)."""
    row = dict(
        participant_id=f"H{pid}", script_id=(pid % 160) + 1, trial_position=tp,
        cell_id=f"c{cat:02d}_{struct}_t{tier}", category=cat, structure=struct, tier=tier,
        format=fmt, position_order="o1", stimulus_id=f"s_{cat}_{struct}_{tier}",
        sim_placement="NA", is_hd=(1 if cat_is_hd(cat) else 0),
        chose_target="", chose_ext="", chose_hd="", chose_clone="", chose_extreme_tier="",
        rt_page_sec=round(5.0 + rng.random() * 10, 2), completed_all=1,
        consent="1", age="35", gender="x", device="desktop", qsf_sha256="SYNTH", export_ts="SYNTH",
    )
    if struct == "BIN":
        row["choice"] = "TARGET" if chose_target else "COMP"
        row["chose_target"] = chose_target
        row["chose_hd"] = chose_target            # in BIN the target is the HD option here (placeholder)
    elif struct == "MOT":
        # extremity TREATMENT: chose_extreme_tier is the registered indicator (menu tier High/Low vs
        # Middle). The extremity statistic is this indicator's MOT share minus its EXC-control share.
        row["chose_extreme_tier"] = chose_target  # reuse the planted bernoulli as the extreme-tier pick
        row["choice"] = "T1S1" if chose_target else "T2S1"
        row["chose_target"] = chose_target        # mirror so the generic target-share path also works
    elif struct == "EXC":
        # extremity CONTROL (single option per tier): same chose_extreme_tier indicator as MOT, drawn at
        # the control rate (no planted effect). The EXC option codes are EXC_H/EXC_M/EXC_L (High = extreme
        # top, Low = extreme bottom, Middle = the non-extreme tier).
        row["chose_extreme_tier"] = chose_target
        row["choice"] = "EXC_H" if chose_target else "EXC_M"
        row["chose_target"] = chose_target        # mirror so the generic path also works
    elif struct == "SOT":
        # compromise: TARGET/COMP/EXT. The REGISTERED statistic is the relative share
        # target/(target+competitor), so chose_target here is the TARGET-vs-COMP indicator drawn at
        # the planted relative proportion (BASE+eff), and EXT is drawn INDEPENDENTLY at a fixed rate.
        # Because EXT is independent of the effect (and the matched BIN control has no EXT), excluding
        # EXT rows from the contrast recovers the planted relative-share effect with the right sign.
        if rng.random() < EXT_RATE:
            row["choice"] = "EXT"; row["chose_ext"] = 1; row["chose_target"] = 0
        else:
            row["chose_ext"] = 0; row["chose_target"] = chose_target
            row["choice"] = "TARGET" if chose_target else "COMP"
    elif struct == "SIM":
        # similarity: TARGET/COMP/CLONE. chose_target = picked the UNCLONED focal option. The REGISTERED
        # statistic is the RELATIVE share uncloned/(uncloned + its rival), so (2026-09-29 repair) the
        # clone is drawn INDEPENDENTLY at a fixed rate, exactly as the compromise extreme is, and the
        # uncloned-versus-rival choice carries the planted relative proportion. The old generator drew
        # the clone only from non-target choosers, which planted an ABSOLUTE-share effect and would have
        # handed the relative-share statistic a spurious 12-point effect even at a planted null.
        if rng.random() < CLONE_RATE:
            row["choice"] = "CLONE"; row["chose_clone"] = 1; row["chose_target"] = 0
        else:
            row["chose_clone"] = 0; row["chose_target"] = chose_target
            row["choice"] = "TARGET" if chose_target else "COMP"
    elif struct == "SYM":
        # upscaling: HD/HF/DECOY. chose_target = chose the HD option (the upscaling statistic).
        row["chose_target"] = chose_target
        row["chose_hd"] = chose_target
        row["choice"] = "HD" if chose_target else ("HF" if rng.random() < 0.7 else "DECOY")
    else:  # FRQ, RNG, PHT decoy structures: TARGET/COMP/DECOY
        row["chose_target"] = chose_target
        if chose_target:
            row["choice"] = "TARGET"
        else:
            row["choice"] = "COMP" if rng.random() < 0.85 else "DECOY"
    # fill any remaining blank codebook columns with 0 so the contract has no missing values.
    for c in ("chose_ext", "chose_hd", "chose_clone", "chose_extreme_tier"):
        if row[c] == "":
            row[c] = 0
    return row


# ---------------------------------------------------------------------------
# MODEL generator (contract B JSONL records). One record per call. Plants the
# per-archetype behavior, the recognition probe (prompting_mode=recognition),
# the format dimension, generation/reasoning for T5, and refusal/unparse rows.
# ---------------------------------------------------------------------------
FORMAT_MODULE_STRUCTS = ("BIN", "FRQ", "SOT")


def _format_cell(cat, struct, tier, fmt):
    """Whether a (category, structure, tier, format) cell exists. Numbers always; words and pictures
    only where the real format module fields them (2026-09-29): tier 2 of the published categories, the
    binary, frequency-decoy and compromise structures. The rehearsal used to generate every structure in
    every format at every tier, which the design never fields and which exhausted memory."""
    if fmt == "numbers":
        return True
    return tier == 2 and cat in PUB and struct in FORMAT_MODULE_STRUCTS


def _spread(n, k):
    """k ones spread evenly over n positions (deterministic)."""
    if n <= 0:
        return []
    k = max(0, min(n, k))
    return [1 if ((i + 1) * k) // n > (i * k) // n else 0 for i in range(n)]


def _exact_labels(struct, n, p_t):
    """The parsed_choice labels for n answered calls carrying EXACTLY the planted target share p_t (and,
    for compromise and similarity, exactly the fixed extreme or clone rate), evenly spread."""
    if n <= 0:
        return []
    if struct in ("SOT", "SIM"):
        other = "EXT" if struct == "SOT" else "CLONE"
        rate = EXT_RATE if struct == "SOT" else CLONE_RATE
        xs = _spread(n, int(round(rate * n)))
        rest = n - sum(xs)
        tg = iter(_spread(rest, int(round(p_t * rest))))
        return [other if x else ("TARGET" if next(tg) else "COMP") for x in xs]
    ch = _spread(n, int(round(p_t * n)))
    n_non = n - sum(ch)
    if struct in ("FRQ", "RNG", "PHT"):
        sec = iter(_spread(n_non, int(round(0.15 * n_non))))
        return ["TARGET" if c else ("DECOY" if next(sec) else "COMP") for c in ch]
    if struct == "SYM":
        sec = iter(_spread(n_non, int(round(0.30 * n_non))))
        return ["HD" if c else ("DECOY" if next(sec) else "HF") for c in ch]
    lab = {"BIN": ("TARGET", "COMP"), "MOT": ("T1S1", "T2S1"), "EXC": ("EXC_H", "EXC_M")}[struct]
    return [lab[0] if c else lab[1] for c in ch]


def _emit_behavior_pass(rows, rid, model, meta, n_per_cell, rng, fmts, mode, eff_mult,
                        persona_id=None, seq_index=None):
    """Emit one full behavioral pass over the grid for a prompting mode. eff_mult scales the
    archetype's planted effect so a mode can express the effect more or less strongly than the neutral
    arm (the planted divergence the readings detect). Appends to rows; returns the next rid."""
    for cat in CATS:
        tiers = [1, 2] if cat in PUB else [3]
        for struct in STRUCTS:
            for tier in tiers:
                for fmt in fmts:
                    if fmt == "pictures" and struct == "PHT":
                        continue
                    if not _format_cell(cat, struct, tier, fmt):
                        continue
                    if model == "CEILING":
                        p_t = 0.97             # picks the target in nearly every set: no room to move
                    else:
                        base_eff = model_effect(model, struct, tier, fmt)
                        # decoy-target HD/HF asymmetry on the attraction decoys (model side mirrors
                        # the human side so the moderator reads the same split on both arms).
                        if struct in ("FRQ", "RNG", "PHT"):
                            dt = cat_decoy_target(cat)
                            if dt == "HD":
                                base_eff *= HD_TARGET_MULT
                            elif dt == "HF":
                                base_eff *= HF_TARGET_MULT
                        p_t = _clip(BASE + base_eff * eff_mult)
                    # exclusions first (REFUSER: a large share of calls refuse or come back unparseable).
                    cell = []
                    for k in range(n_per_cell):
                        excl, excl_reason, parse_method, raw = False, "", "exact", "I choose option A."
                        if model == "REFUSER" and rng.random() < 0.5:
                            if rng.random() < 0.6:
                                excl, excl_reason, parse_method = True, "refusal", "failed"
                                raw = "I am sorry, I cannot help with this."
                            else:
                                excl, excl_reason, parse_method = True, "unparseable", "failed"
                                raw = "It depends on many factors and I would need more context."
                        cell.append((excl, excl_reason, parse_method, raw))
                    # 2026-09-29: the answered calls carry EXACTLY the planted shares (a deterministic,
                    # evenly spread allocation), because a model effect in this design is a population
                    # quantity over the enumerated grid with no sampling noise. The earlier per-call coin
                    # flips made the synthetic model arm noisy enough to move planted routings.
                    labels = iter(_exact_labels(struct, sum(1 for c in cell if not c[0]), p_t))
                    for excl, excl_reason, parse_method, raw in cell:
                        parsed = None if excl else next(labels)
                        rows.append(_model_record(
                            rid, model, meta, cat, struct, tier, fmt, mode,
                            parsed, parse_method, raw, excl, excl_reason,
                            persona_id=persona_id, seq_index=seq_index))
                        rid += 1
    return rid


def _planted_share(model, struct, tier, fmt, cat, eff_mult):
    """The planted target share of one archetype in one cell (the HD/HF asymmetry mirrored on the
    attraction decoys, as the human side plants it)."""
    if model == "CEILING":
        return 0.97                                  # picks the target in nearly every set
    base_eff = model_effect(model, struct, tier, fmt)
    if struct in ("FRQ", "RNG", "PHT"):
        dt = cat_decoy_target(cat)
        if dt == "HD":
            base_eff *= HD_TARGET_MULT
        elif dt == "HF":
            base_eff *= HF_TARGET_MULT
    return _clip(BASE + base_eff * eff_mult)


def _draw_label(struct, p_t, rng):
    """One call's parsed_choice, drawn at the planted share (the compromise extreme and the similarity
    clone are drawn first at their fixed rates, so the registered relative shares carry p_t)."""
    if struct in ("SOT", "SIM"):
        rate = EXT_RATE if struct == "SOT" else CLONE_RATE
        if rng.random() < rate:
            return "EXT" if struct == "SOT" else "CLONE"
        return "TARGET" if rng.random() < p_t else "COMP"
    return _model_choice_label(struct, rng.random() < p_t, rng)


def _grid_shares(p_t, n_points, consistency):
    """Each grid point's own share of the counted option. consistency None: every grid point at the
    planted share p_t (so every call is an independent draw at p_t, the most variable case for a given
    share). consistency c (for example 0.9): a grid point answers its modal option in a share c of its
    draws, so its share is c or 1 - c; the points are assigned so the grid averages EXACTLY to p_t (one
    point takes the remainder), which keeps the planted population effect exact while the draws vary.
    A planted share outside [1 - c, c] falls back to the independent case. consistency "exact" is handled
    by the caller (answers allocated exactly at the planted share: the call structure without draw noise)."""
    if consistency == "exact":
        return [p_t] * n_points
    lo, hi = (1.0 - consistency, consistency) if consistency is not None else (None, None)
    if consistency is None or not (lo <= p_t <= hi) or n_points <= 0:
        return [p_t] * n_points
    x_total = (p_t - lo) / (hi - lo) * n_points      # sum of the mixing weights x_g in [0, 1]
    full = int(math.floor(x_total))
    frac = x_total - full
    xs = [1.0] * full + ([frac] if full < n_points else []) + [0.0] * max(0, n_points - full - 1)
    xs = xs[:n_points]
    # spread the high-share points over the grid instead of putting them first
    order = sorted(range(n_points), key=lambda i: ((i * 7919) % n_points, i))
    shares = [0.0] * n_points
    for slot, i in enumerate(order):
        shares[i] = lo + (hi - lo) * xs[slot]
    return shares


def _deterministic_allocation(struct, grid, p_t):
    """The exact labels of one cell (_exact_labels: the planted shares hold exactly) dealt so that every grid
    point answers one option in all its draws. grid is the list of (persona, order, paraphrase, draw, point)
    calls in emission order; returns one label per call, in that order. The labels are sorted into option
    blocks and the blocks are laid over the grid points in a spread order (the stride of _grid_shares), so the
    options are not tied to one order; only a point that straddles two blocks mixes options. The allocation
    is made within each paraphrase when every paraphrase has at least two grid points (text prompts), so each
    paraphrase carries the planted share exactly and the paraphrase check reads the planted truth; a picture
    prompt has one grid point per paraphrase, so its labels are dealt across the three points instead."""
    by_point = defaultdict(list)
    for idx, call in enumerate(grid):
        by_point[call[-1]].append(idx)
    para_of = {call[-1]: call[2] for call in grid}
    strata = defaultdict(list)
    for g in sorted(by_point):
        strata[para_of[g]].append(g)
    if any(len(pts) < 2 for pts in strata.values()):
        strata = {"all": sorted(by_point)}
    keys = sorted(strata, key=str)
    # the cell's exact labels (one rounding for the whole cell, so the cell share is the June allocation's), sorted
    # into option blocks and dealt round-robin to the paraphrases, so every paraphrase receives each option's count
    # to within one call.
    room = {k: sum(len(by_point[g]) for g in strata[k]) for k in keys}
    got = {k: [] for k in keys}
    j = 0
    for lab in sorted(_exact_labels(struct, len(grid), p_t)):
        while len(got[keys[j % len(keys)]]) >= room[keys[j % len(keys)]]:
            j += 1
        got[keys[j % len(keys)]].append(lab)
        j += 1
    out = [None] * len(grid)
    for key in keys:
        points = strata[key]
        it = iter(sorted(got[key]))
        n_pts = len(points)
        for slot in sorted(range(n_pts), key=lambda i: ((i * 7919) % n_pts, i)):
            for idx in by_point[points[slot]]:
                out[idx] = next(it)
    return out


def _emit_draws_pass(rows, rid, model, meta, rng, fmts, mode, eff_mult, persona_ids=(None,),
                     draws_text=DRAWS_TEXT, draws_pictures=DRAWS_PICTURES, calls_per_cell=None,
                     consistency=None):
    """rule 5: one pass over the registered grid (stimulus x order x paraphrase [x persona]), each grid
    point called draws_text times (draws_pictures for a picture prompt, whose one order is fixed), every
    call a draw at its grid point's share (_grid_shares; with consistency None every call is an
    independent draw at the planted share). calls_per_cell, when given, replaces the grid by that many
    single calls per cell (the sequential arm). Returns the next rid."""
    for cat in CATS:
        tiers = [1, 2] if cat in PUB else [3]
        for struct in STRUCTS:
            for tier in tiers:
                for fmt in fmts:
                    if fmt == "pictures" and struct == "PHT":
                        continue
                    if not _format_cell(cat, struct, tier, fmt):
                        continue
                    p_t = _planted_share(model, struct, tier, fmt, cat, eff_mult)
                    if calls_per_cell is not None:
                        grid = [(None, f"o{(k % ORDERS[struct]) + 1}", (k % PARAPHRASES) + 1, 0, k)
                                for k in range(calls_per_cell)]
                        shares = _grid_shares(p_t, calls_per_cell, consistency)
                    else:
                        n_orders = 1 if fmt == "pictures" else ORDERS[struct]
                        n_draws = ((DRAWS_PICTURES_BY_STRUCT.get(struct, draws_pictures)
                                    if draws_pictures == DRAWS_PICTURES else draws_pictures) if fmt == "pictures"
                                   else (DRAWS_BY_STRUCT.get(struct, draws_text) if draws_text == DRAWS_TEXT
                                         else draws_text))
                        points = [(per, o, pp) for per in persona_ids for o in range(n_orders)
                                  for pp in range(PARAPHRASES)]
                        shares = _grid_shares(p_t, len(points), consistency)
                        grid = [(per, f"o{o + 1}", pp + 1, d, g) for g, (per, o, pp) in enumerate(points)
                                for d in range(n_draws)]
                    exact_iter = None
                    if consistency == "exact":
                        # the registered grid and draws, answers allocated EXACTLY at the planted share across
                        # the cell's calls: the real call structure with no sampling noise. the second revision: each prompt is DETERMINISTIC, answering one option in all its draws (the
                        # labels are grouped by option and dealt to the grid points in a spread order, so at most
                        # one prompt per option boundary carries a remainder that keeps the share exact). The
                        # June allocation spread the labels over every draw, which made each prompt vary.
                        exact_iter = iter(_deterministic_allocation(struct, grid, p_t))
                    for k, (per, order, para, draw, g) in enumerate(grid):
                        excl, excl_reason, parse_method, raw = False, "", "exact", "I choose option A."
                        if model == "REFUSER" and rng.random() < 0.5:
                            if rng.random() < 0.6:
                                excl, excl_reason, parse_method = True, "refusal", "failed"
                                raw = "I am sorry, I cannot help with this."
                            else:
                                excl, excl_reason, parse_method = True, "unparseable", "failed"
                                raw = "It depends on many factors and I would need more context."
                        if exact_iter is not None:
                            lab = next(exact_iter)
                            parsed = None if excl else lab
                        else:
                            parsed = None if excl else _draw_label(struct, shares[g], rng)
                        rec = _model_record(rid, model, meta, cat, struct, tier, fmt, mode, parsed, parse_method,
                                            raw, excl, excl_reason, persona_id=per,
                                            seq_index=((k % 7) + 1 if calls_per_cell is not None else None))
                        rec.update(position_order=order, paraphrase_id=para, draw_index=draw,
                                   session_id=(f"S{k // 7 + 1:04d}" if calls_per_cell is not None else None))
                        rows.append(rec)
                        rid += 1
    return rid


def gen_persona_seq_arms(model, n_per_cell, rng, with_formats=False, noise="draws", consistency=None):
    """Generate ONLY the persona arm and the sequential arm for one archetype (the registered
    secondary arms, ; analysis_plan "set out in Web Appendix E"). Kept separate from
    gen_model so the neutral confirmatory stream is unchanged by adding these arms, while the arms
    stay fully deterministic at the fixed seed. The persona arm is planted to express the effect MORE
    strongly than neutral (so neutral-vs-persona reads "persona more faithful"); the sequential arm
    LESS strongly (so single-shot-vs-sequential reads "the model carries within-session history").
    Returns a list of contract-B records carrying prompting_mode persona and sequential.
    noise="draws": the persona arm is one call per persona x order x paraphrase
    (numbers and words; pictures one order), the sequential arm SEQ_CALLS_PER_CELL single calls per cell;
    noise="exact": the June allocation, n_per_cell answers per cell at exactly the planted shares."""
    meta = MODEL_ARCHETYPES[model]
    fmts = FORMATS if with_formats else ["numbers"]
    rows = []
    rid = 5_000_000       # record ids must not collide with the neutral arm's (contract B: unique ids)
    if noise == "draws":
        rid = _emit_draws_pass(rows, rid, model, meta, rng, fmts, "persona", 1.45,
                               persona_ids=tuple(f"P{i + 1:02d}" for i in range(PERSONAS)),
                               draws_text=1, draws_pictures=1, consistency=consistency)
        rid = _emit_draws_pass(rows, rid, model, meta, rng, ["numbers"], "sequential", 0.55,
                               calls_per_cell=SEQ_CALLS_PER_CELL, consistency=consistency)
        return rows
    rid = _emit_behavior_pass(rows, rid, model, meta, n_per_cell, rng, fmts, "persona", 1.45,
                              persona_id="persona_01")
    rid = _emit_behavior_pass(rows, rid, model, meta, n_per_cell, rng, fmts, "sequential", 0.55,
                              seq_index=1)
    return rows


def gen_model(model, n_per_cell, rng, with_formats=False, noise="draws", consistency=None):
    """Generate contract-B model records for one archetype.
    noise="draws": the registered grid (ORDERS x PARAPHRASES) with
    DRAWS_TEXT calls per grid point (DRAWS_PICTURES for pictures), and RECOG_CALLS_PER_STIMULUS
    recognition calls per stimulus; n_per_cell is ignored. consistency (see _grid_shares): None = every
    call an independent draw at the planted share (the most variable case); a value such as 0.9 = each
    grid point answers its modal option in that share of its draws, the grid averaging exactly to the
    planted share.
    noise="exact": the June allocation, n_per_cell answers per cell carrying exactly the planted shares
    (no sampling noise), with n_per_cell // 5 recognition calls per cell.
    Returns a list of dicts with the contract-B fields analyze.py reads, plus recognition records.
    The persona and sequential secondary arms are generated separately (gen_persona_seq_arms)."""
    meta = MODEL_ARCHETYPES[model]
    rows = []
    fmts = FORMATS if with_formats else ["numbers"]
    rid = 0
    # The neutral confirmatory arm (the default practitioner method, the input to Step-2 scoring).
    if noise == "draws":
        rid = _emit_draws_pass(rows, rid, model, meta, rng, fmts, "neutral", 1.0, consistency=consistency)
    else:
        rid = _emit_behavior_pass(rows, rid, model, meta, n_per_cell, rng, fmts, "neutral", 1.0)
    n_recog = RECOG_CALLS_PER_STIMULUS if noise == "draws" else max(1, n_per_cell // 5)
    # ---- recognition probe records (test T2), isolated calls, never shared with behavior ----
    for cat in CATS:
        tiers = [1, 2] if cat in PUB else [3]
        for struct in STRUCTS:
            if struct == "BIN":
                continue
            for tier in tiers:
                recog = model_recognizes(model, struct)
                # a small noise so the probe is not a perfect indicator (realistic).
                for k in range(n_recog):
                    detected = recog if rng.random() < 0.9 else (not recog)
                    rows.append(_model_record(
                        rid, model, meta, cat, struct, tier, "numbers", "recognition",
                        "YES" if detected else "NO", "exact",
                        "The decoy is the unavailable option." if detected else "Nothing unusual.",
                        False, "", recognition=1 if detected else 0))
                    rid += 1
    return rows


def _model_choice_label(struct, chose_target, rng):
    """Map a target/non-target draw to a contract-B parsed_choice label for the structure."""
    if struct == "BIN":
        return "TARGET" if chose_target else "COMP"
    if struct == "MOT":
        return "T1S1" if chose_target else "T2S1"
    if struct == "EXC":
        return "EXC_H" if chose_target else "EXC_M"
    if struct == "SIM":
        return "TARGET" if chose_target else ("CLONE" if rng.random() < 0.4 else "COMP")
    if struct == "SYM":
        return "HD" if chose_target else ("HF" if rng.random() < 0.7 else "DECOY")
    return "TARGET" if chose_target else ("COMP" if rng.random() < 0.85 else "DECOY")


# the registered call plan with repeated draws makes about 650,000 synthetic records per
# rehearsal, so the records carry every contract-B field the analysis reads (identity, design coordinates, the
# grid-point fields, the draw, the arm, the answer, the exclusion, the probe result, family and generation) and
# omit the bookkeeping fields it never reads (prompt and response text, parse method, provider ids, sampling
# echo, image reference, cost, latency, timestamp), to fit the memory of a shared machine. The full contract-B
# shape is exercised on the runner's own log. False restores it.
COMPACT_RECORDS = True
_BOOKKEEPING = ("run_id", "model_id_requested", "model_id_echoed", "provider", "api_flavor",
                "sampling_params_effective", "image_ref", "image_sha256", "cell_id", "prompt_text",
                "raw_response", "parse_method", "latency_ms", "cost_usd", "timestamp")


def _model_record(rid, model, meta, cat, struct, tier, fmt, mode, parsed, parse_method, raw,
                  excl, excl_reason, recognition=None, persona_id=None, seq_index=None):
    """Build one contract-B record. analyze.py derives chose_target etc. from parsed_choice using
    the SAME codebook as the human side, so model and human share all scoring code."""
    if COMPACT_RECORDS:
        return dict(record_id=f"R{rid}", model_key=model, prompting_mode=mode, persona_id=persona_id,
                    paraphrase_id=0, reasoning_mode=meta["reasoning"], temperature_requested=None,
                    category=cat, structure=struct, tier=tier, format=fmt, position_order="o1",
                    stimulus_id=(cat, struct, tier), seq_index=seq_index, is_hd=(1 if cat_is_hd(cat) else 0),
                    parsed_choice=parsed, exclusion_flag=excl, exclusion_reason=excl_reason,
                    family=meta["family"], generation=meta["generation"], recognition=recognition)
    rec = dict(
        record_id=f"R{rid}", run_id="SYNTH_REHEARSAL", model_key=model,
        model_id_requested=f"{model}_pinned", model_id_echoed=f"{model}_pinned",
        provider="synthetic", api_flavor="synthetic", prompting_mode=mode, persona_id=persona_id,
        paraphrase_id=0, reasoning_mode=meta["reasoning"], temperature_requested=None,
        sampling_params_effective={"note": "synthetic"}, image_ref=(f"img_{struct}.png" if fmt == "pictures" else None),
        image_sha256=("SYNTHHASH" if fmt == "pictures" else None),
        cell_id=f"c{cat:02d}_{struct}_t{tier}", category=cat, structure=struct, tier=tier,
        format=fmt, position_order="o1", stimulus_id=f"s_{cat}_{struct}_{tier}", seq_index=seq_index,
        is_hd=(1 if cat_is_hd(cat) else 0),
        prompt_text="(synthetic prompt)", raw_response=raw, parsed_choice=parsed,
        parse_method=parse_method, exclusion_flag=excl, exclusion_reason=excl_reason,
        latency_ms=120, cost_usd=0.0, timestamp="1970-01-01T00:00:00Z",
        # carried-through synthetic metadata the analysis uses for T5 routing (family/generation):
        family=meta["family"], generation=meta["generation"], recognition=recognition,
    )
    return rec


# ---------------------------------------------------------------------------
# A small standalone recovery check kept for backwards compatibility with the
# original synth.py self-test. The FULL rehearsal lives in analyze.py.
# ---------------------------------------------------------------------------
def _human_target_share_by_cell(rows):
    # Per-cell target share on the registered scale: for SOT the statistic is the RELATIVE share
    # target/(target+competitor), so EXT choices are excluded from the denominator (the same exclusion
    # the analysis engine applies); for every other structure it is the plain target share.
    agg = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["format"] != "numbers":
            continue
        if r["structure"] == "SOT" and r.get("choice") == "EXT":
            continue
        if r["structure"] == "SIM" and r.get("choice") == "CLONE":
            continue   # similarity is a relative share too (2026-09-29)
        a = agg[(r["structure"], r["tier"])]
        a[0] += int(r["chose_target"]); a[1] += 1
    return {k: (v[0] / v[1] if v[1] else 0.0) for k, v in agg.items()}


def main():
    rng = random.Random(20260613)
    H = gen_human(2000, rng, icc=0.0)
    shares = _human_target_share_by_cell(H)
    out = ["# synth.py standalone recovery check (human-effect planting)",
           "(synth.py expanded 2026-06-13. The FULL dress rehearsal is run by analyze.py; this is a",
           "quick sanity check that the human generator plants the target shares it claims.)", ""]
    ok = True
    for st in EFFECT_STRUCTS:
        share = shares.get((st, 1))
        if share is None:
            continue
        # the extremity treatment MOT is measured against the EXC control; every other effect vs BIN.
        control = "EXC" if st == "MOT" else "BIN"
        eff = share - shares.get((control, 1), BASE)
        planted = TRUTH[st] * TIER_ATTEN[1]
        hit = abs(eff - planted) <= 0.02
        ok &= hit
        out.append(f"- {st} t1: planted {planted:+.3f}  recovered {eff:+.3f}  {'OK' if hit else 'MISS'}")
    out.append("")
    out.append(f"## OVERALL: {'PLANTED HUMAN EFFECTS RECOVER' if ok else 'MISS'}")
    open("SYNTH_CHECK.md", "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
