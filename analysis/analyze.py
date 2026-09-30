"""analyze.py: the registered analysis, from the human choices and the model log to the results pack.

It reads the human long table (analysis/ingest.py) and the model call log (models/run.py), whose fields are
listed in analysis/DATA_DICTIONARY.md, and writes the results pack (part C there): the human benchmarks
with the validity criteria of Step 0, the fidelity map and agreement scores of Step 2, the pattern tests
T1 to T5 and the secondary contrasts of Step 3, the routing of the decision tree to the seven named
scenarios, and every number the results section will cite (numbers.json). All statistics are in
statlib.py, in plain Python.

Two ways to run, one pipeline:
  python analysis/analyze.py
      the dress rehearsal: synth.py plants known human effects and twelve model behavior profiles, each
      built to produce one named scenario or walk-through; the analysis runs on them and the run passes
      only if it recovers every planted effect and routes every profile to its scenario. Fixed seed
      20260613. Writes analysis/results_pack/ and analysis/RESULTS_PACK_SELFTEST.md.
  python analysis/analyze.py --human human_long.csv --model model_log.jsonl
      the same code on real data (used at Stage 2).
Manuscript: Analysis Plan (Steps 0 to 3, the precedence rule, Table 3 and the two worked walk-throughs)
and Web Appendices C and E.
"""
from __future__ import annotations
import os, sys, json, csv, random, argparse, time, platform, math, tempfile, itertools
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth
import statlib
import call_bootstrap
from registered_constants import (C as RC, HOLM_FAMILIES, TIE_BREAK_RULE, CALIBRATION_DECISION_RULE,
                                  DEVIATION_SENSITIVITY_PAIRS, CLASS_ORDER)

PACK = os.path.join(HERE, "results_pack")
TESTS_DIR = os.path.join(PACK, "tests")
FIGS_DIR = os.path.join(PACK, "figures")

# The tested effects (BIN is the shared control; PHT is the diagnostic fragile effect).
EFFECTS = ["FRQ", "RNG", "PHT", "SOT", "SYM", "SIM", "MOT"]
# The six non-similarity effects: the pooled tallies, the S7 count, the overall class, the account rule.
REGULARITY_EFFECTS = list(HOLM_FAMILIES["non_similarity"])
# The positive controls named in the protocol (Step 0): the frequency-decoy cells whose target is the
# premium option (tested on those cells alone) and the compromise effect (its replication criterion).
POSITIVE_CONTROLS = ["FRQ", "SOT"]
# Which pattern tests USE each effect by design.
TESTS_USING = {"FRQ": ("T1", "T2", "T3", "T4", "T5"), "SOT": ("T1", "T2", "T3", "T4", "T5")}
# The effects whose decoy target can be the budget option (the counterbalance of the attraction decoys).
DECOY_TARGET_EFFECTS = ("FRQ", "RNG", "PHT")
# The format module (attraction-frequency and compromise, words and pictures against numbers).
FORMAT_EFFECTS = ("FRQ", "SOT")
FORMAT_SIDES = ("words", "pictures")
FORMAT_TIER = 2
# the memorization test compares the published-values tier
# with the new-values tier on the same categories, paired; the invented tier (3) is a supporting descriptive extension.
T1_TIERS = (1, 2)
# the format test is descriptive only (estimate and interval, no reading, decides no scenario); reason
# construction (S3) rests on a resolved decline down the argument-strength ladder, with T4 reported beside it.
DESCRIPTIVE_T4 = True
# the pre-format cutoffs, used only when DESCRIPTIVE_T4 is False (a comparison; not registered, not printed)
T4_PRE_ROUND5_DROP = 0.30
T4_PRE_ROUND5_FLAT = 0.12
# The argument-strength ladder's registered anchor rungs.
LADDER_TOP = ("FRQ", "RNG")
LADDER_MIDDLE = "SOT"
LADDER_BOTTOM = "MOT"
ARGUABLE_ANCHORS = ("FRQ", "RNG", "SOT")      # the attraction and compromise rungs
ARGUMENT_OVERRIDE = "rational override on choice sets that offer an argument"

# Registered thresholds, bound from the ONE constants structure (registered_constants.py). Effects are
# proportions inside the code and points in every output, so point-valued constants are divided by 100.
PARSE_FLOOR = RC.PARSE_FLOOR
REFUSAL_CEIL = RC.REFUSAL_CEIL
CEIL_HI = RC.CEIL_HI
CEIL_LO = RC.CEIL_LO
NOT_ASSESSABLE_FRAC = RC.NOT_ASSESSABLE_FRAC
HOLM_ALPHA = RC.HOLM_ALPHA
BF_GATE = RC.BF_GATE
BF_PRIOR_SCALE = RC.BF_PRIOR_SCALE_PP / 100.0
PHANTOM_BAND_PP = RC.PHANTOM_BAND_PP
PHANTOM_BAND = RC.PHANTOM_BAND_PP / 100.0
FIRST_TRIAL_MIN_EFFECT_PP = RC.FIRST_TRIAL_MIN_EFFECT_PP
HIGH_RATIO = RC.HIGH_RATIO
OVER_RATIO = RC.OVER_RATIO
PARTIAL_RATIO = RC.PARTIAL_RATIO
MIN_MODEL_EFFECT = RC.ANTI_MIN_PP / 100.0   # the registered minimum model effect (3 points)
ANTI_MIN_PP = MIN_MODEL_EFFECT              # legacy name (a proportion, despite the suffix)
NEAR_NULL_HUMAN = RC.NEAR_NULL_HUMAN_PP / 100.0
FID_MIN, FOLD_AT = RC.FIDELITY_RATIO_MIN, RC.FIDELITY_FOLD_AT
# The re-run rule reads a re-run against the re-run pack's own interval over calls (boot_lo_pp, boot_hi_pp), which
# is computed at BOOTSTRAP_LEVEL; the two registered levels must therefore agree, or the printed rule and the
# applied one would differ.
if RC.RERUN_RULE != RC.BOOTSTRAP_LEVEL:
    raise ValueError("RERUN_RULE must equal BOOTSTRAP_LEVEL: a re-run is read against the re-run's own bootstrap "
                     "interval over calls, which the pack computes at BOOTSTRAP_LEVEL")

# The scenario names a reader sees; the IDs stay as data keys.
SCENARIO_NAMES = {
    "S1": "High fidelity", "S2": "Retrieval only", "S3": "Reason construction", "S4": "Rational override",
    "S5": "Family-specific", "S6": "Rising fidelity", "S7": "Human effects fail",
    "S7-not-triggered": "Human effects hold (S7 not triggered)",
    "REVERSED_LADDER_OVERRIDE": "Reversed ladder, rational override on choice sets that offer an argument",
    "REVERSED_LADDER": "Reversed ladder, no account attributed",
    "PARTIAL": "Partial fidelity (per-effect accounts side by side)",
    "COMPOSITE": "Composite of the individual readings", "CRITERION_FAIL": "Not assessable (Step 0b)",
    "NOT_RESOLVED": "Not resolved (the route depends on a pattern test the intervals leave open)",
}
NOT_RESOLVED_SCENARIO = "NOT_RESOLVED"

# Fidelity-map classes that never enter agreement scoring.
UNINFORMATIVE = "uninformative (positive control failed)"
# rule on F7: after a first-trial fallback, an effect that replicates below the 8-point floor is
# classed descriptively only and leaves the overall class and the pattern tests.
DESCRIPTIVE_FLOOR = "descriptive only (below the 8-point first-trial floor)"
NON_SCORED = ("n/a", "excluded(no-room)", "excluded(criterion-exit)", "no-human-counterpart", UNINFORMATIVE,
              DESCRIPTIVE_FLOOR)
# The classes a scored model effect can take.
SCORED_CLASSES = ("ANTI", "HIGH", "LOW", "OVER", "PARTIAL")


def _int(v, default=0):
    """Read a 0/1 or integer field that may arrive as int, float, or CSV string ('' -> default)."""
    if v is None:
        return default
    if isinstance(v, (int, bool)):
        return int(v)
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _pts(x):
    """A proportion in percentage points, rounded to 9 decimals, so a registered point cutoff compares
    exactly (47/100 - 50/100 is -3.0000000000000027 points unrounded, which would read as beyond 3)."""
    return round(x * 100.0, 9)


def _r3(x):
    """A value rounded to 3 decimals for a descriptive column, blank when missing."""
    return round(x, 3) if isinstance(x, (int, float)) else ""


def _fold(x):
    """The registered combine of a group fidelity: above 1 becomes 2 minus the value, so an
    overshoot and an undershoot of the same size count alike; then the lower cap at -1."""
    if x > FOLD_AT:
        x = 2.0 * FOLD_AT - x
    return max(FID_MIN, x)


_clamp_fid = _fold   # legacy name kept for callers; the old upper cap of 1.5 is retired


# ===================================================================================================
# THE DESIGN INDEX -- what the analysis needs to know that the long table does not carry.
# ===================================================================================================
def _find_stimuli():
    env = os.environ.get("CONTEXT_FX_STIMULI")
    if env and os.path.exists(env):
        return env
    d = HERE
    for _ in range(5):
        d = os.path.dirname(d)
        p = os.path.join(d, "stimuli", "stimuli.json")
        if os.path.exists(p):
            return p
    return None


STIMULI_PATH = _find_stimuli()


def _terminal_share(arm):
    """The last measured target share (percent) in one calibration arm record, or None: the highest
    wave found either as a wave block ('wave3': {...target_share_pct}) or as a trail entry
    ('waveN_share_pct_at_...'; the trail key suffix varies by how the values were reached). One picker
    for both uses: the same wave as _terminal_record."""
    return _terminal_record(arm)[0]


def _terminal_record(arm):
    """(share_pct, [lo, hi] or None) of the last measured wave of one calibration arm: a wave block
    carries its Wilson interval; a trail entry carries only the share."""
    best = None
    for n in (1, 2, 3):
        w = arm.get(f"wave{n}")
        if isinstance(w, dict) and w.get("target_share_pct") is not None:
            ci = w.get("wilson95")
            best = max(best or (0, 0.0, None), (n, float(w["target_share_pct"]), list(ci) if ci else None),
                       key=lambda t: t[0])
    for k, v in (arm.get("trail") or {}).items():
        if k.startswith("wave") and "_share_pct" in k and v is not None and k[4:5].isdigit():
            if best is None or int(k[4]) > best[0]:
                best = (int(k[4]), float(v), None)
    return (best[1], best[2]) if best else (None, None)


def meets_calibration_rule(share_pct, ci=None):
    """The registered final-wave decision rule (Web Appendix F), applied to the COMPROMISE TARGET's share
    (the premium option, by option identity): final when the share lies inside the band, or when its 95
    percent interval overlaps the band while the share stays between the interval-route limits."""
    r = CALIBRATION_DECISION_RULE
    if r["band_lo_pct"] <= share_pct <= r["band_hi_pct"]:
        return True
    if ci is None:
        return False
    lo, hi = ci
    overlaps = hi >= r["band_lo_pct"] and lo <= r["band_hi_pct"]
    return bool(overlaps and r["interval_route_lo_pct"] <= share_pct <= r["interval_route_hi_pct"])


class Design:
    """Slice-level design facts, keyed by slice = (category, memorization tier, format).

    targets: (category, tier, structure, placement) -> "HD" or "HF", the option each effect targets
        (placement is set only for similarity: clone_HF, where the uncloned option is HD, or clone_HD).
        Empty for synthetic data, whose rows code chose_target against an abstract target.
    bin_focal: category -> the option the BIN rows' TARGET label denotes in the human and model feeds
        (ingest.load_stimuli and run.cat_target_focal_map read the category's first decoy target).
    baseline_pct: slice -> measured calibration share (percent) of the calibration target option.
    hd_baseline_pct: slice -> the same measurement expressed as the share of the HD option.
    deviation_slices: the registered deviation sensitivity set (eight pairs): the adjustable pairs that
        failed the calibration decision rule by option identity and were retained, plus the published
        pairs carrying the hard-limit flag. Computed from the calibration record and checked against
        registered_constants.DEVIATION_SENSITIVITY_PAIRS (from_stimuli refuses a mismatch).
    deviation_flag_mismatch / compromise_flag_mismatch: slices where the CALIBRATION_DEVIATION (or
        COMPROMISE_PRECONDITION_VIOLATED) flags in stimuli.json disagree with the set computed by option
        identity. The analysis never reads the flags to decide anything; the rehearsal checks both lists
        are empty, and the real-data path (run_real) refuses to run while either is not.
    compromise_descriptive: slices whose compromise TARGET starts at or above 50 percent (by option
        identity), so the compromise test's precondition fails and the cell is descriptive only.
    flagged_compromise: the slices stimuli.json flags COMPROMISE_PRECONDITION_VIOLATED (kept for the
        cross-check report; the rule above is what the analysis applies).
    price_free: the price-free variant categories (their own robustness arm, never in the backbone).
    format_categories: format -> categories fielded in that format (tier 2)."""

    def __init__(self, targets=None, bin_focal=None, baseline_pct=None, hd_baseline_pct=None,
                 deviation_slices=None, compromise_descriptive=None, flagged_compromise=None,
                 price_free=None, format_categories=None, source="none", deviation_flag_mismatch=None,
                 compromise_flag_mismatch=None):
        self.deviation_flag_mismatch = list(deviation_flag_mismatch or [])
        self.compromise_flag_mismatch = list(compromise_flag_mismatch or [])
        self.targets = dict(targets or {})
        self.bin_focal = dict(bin_focal or {})
        self.baseline_pct = dict(baseline_pct or {})
        self.hd_baseline_pct = dict(hd_baseline_pct or {})
        self.deviation_slices = set(deviation_slices or ())
        self.compromise_descriptive = set(compromise_descriptive or ())
        self.flagged_compromise = set(flagged_compromise or ())
        self.price_free = set(price_free or ())
        self.format_categories = {k: set(v) for k, v in (format_categories or {}).items()}
        self.source = source

    @property
    def has_identity(self):
        return bool(self.targets)

    def target(self, cat, tier, struct, placement=None):
        """The option (HD/HF) the effect targets in this slice, or None when identities are unknown."""
        if not self.targets:
            return None
        if struct == "SYM":
            return "HD"
        if struct == "SIM":
            pl = placement if placement in ("clone_HF", "clone_HD") else "clone_HF"
            return self.targets.get((cat, tier, "SIM", pl))
        return self.targets.get((cat, tier, struct, None))

    def outside_hard_limits(self, sl):
        b = self.baseline_pct.get(sl)
        return b is not None and (b < RC.HARD_LIMIT_LO_PCT or b > RC.HARD_LIMIT_HI_PCT)

    @classmethod
    def null(cls):
        return cls(source="none")

    @classmethod
    def from_stimuli(cls, path=None):
        path = path or STIMULI_PATH
        S = json.load(open(path, encoding="utf-8"))
        cats = {c["id"]: c for c in S["categories"]}
        price_free = {cid for cid, c in cats.items()
                      if c.get("price_free") or c.get("price_free_variant_of") or cid.endswith("_pf")}
        bin_focal = {}
        for r in S["stimuli"]:
            if r["structure"] != "BIN" and r.get("target"):
                bin_focal.setdefault(r["category"], r["target"])
        targets = {}
        for r in S["stimuli"]:
            st, cat, tier = r["structure"], r["category"], int(r["memorization_tier"])
            if st in ("BIN", "MOT", "EXC"):
                continue
            if st == "SIM":
                targets[(cat, tier, "SIM", "clone_HF")] = r.get("target")
                pv = (r.get("placement_variants") or {}).get("clone_HD")
                if pv:
                    targets[(cat, tier, "SIM", "clone_HD")] = pv.get("target")
            elif st == "SYM":
                targets[(cat, tier, "SYM", None)] = "HD"
            elif r.get("target"):
                targets[(cat, tier, st, None)] = r["target"]
        baseline, hd_base, flagged, fmt_cats = {}, {}, set(), {"words": set(), "pictures": set()}
        flag_deviation = set()        # what the flags say (cross-check only; wording never drives the set)
        adjustable_fail, published_limit, check_only = set(), set(), set()
        for r in S["stimuli"]:
            cat, tier = r["category"], int(r["memorization_tier"])
            if r["structure"] == "BIN":
                arms = ((r.get("calibration") or {}).get("arms") or {})
                for fmt, arm in arms.items():
                    status = str(arm.get("status", "")).upper()
                    if status.startswith("EXIT"):
                        continue
                    share = _terminal_share(arm)
                    if share is None:
                        continue
                    baseline[(cat, tier, fmt)] = share
                    hd_base[(cat, tier, fmt)] = share if bin_focal.get(cat) == "HD" else 100.0 - share
                    # the deviation set, by option identity (the compromise target is the premium option).
                    t_share, t_ci = _terminal_record(arm)
                    if bin_focal.get(cat) != "HD" and t_share is not None:
                        t_share = 100.0 - t_share
                        t_ci = [100.0 - t_ci[1], 100.0 - t_ci[0]] if t_ci else None
                    if status.startswith("CHECK_ONLY"):
                        check_only.add((cat, tier, fmt))
                        # the registered hard limits apply to the measured POINT share
                        if t_share is not None and not (RC.HARD_LIMIT_LO_PCT <= t_share <= RC.HARD_LIMIT_HI_PCT):
                            published_limit.add((cat, tier, fmt))
                    elif t_share is not None and not meets_calibration_rule(t_share, t_ci):
                        adjustable_fail.add((cat, tier, fmt))
                for f in r.get("flags", []):
                    if f.startswith("CALIBRATION_DEVIATION"):
                        fmt = "pictures" if "pictures arm" in f else ("words" if "words arm" in f else "numbers")
                        flag_deviation.add((cat, tier, fmt))
                    elif f.startswith("CALIBRATION_HARD_LIMIT_FLAG"):
                        flag_deviation.add((cat, tier, "numbers"))
                fv = r.get("format_variants") or {}
                for fmt in ("words", "pictures"):
                    if fmt in fv:
                        fmt_cats[fmt].add(cat)
            elif r["structure"] == "SOT":
                for f in r.get("flags", []):
                    if f.startswith("COMPROMISE_PRECONDITION_VIOLATED"):
                        fmt = "pictures" if "PICTURES ARM ONLY" in f else "numbers"
                        flagged.add((cat, tier, fmt))
        comp_desc = set()
        for (cat, tier, fmt), hd_share in hd_base.items():
            tgt = targets.get((cat, tier, "SOT", None))
            if tgt is None:
                continue
            share_t = hd_share if tgt == "HD" else 100.0 - hd_share
            if tier == 1 and not RC.COMPROMISE_RULE_COVERS_PUBLISHED_TIER:
                continue
            if share_t >= RC.COMPROMISE_TARGET_MAX_BASELINE_PCT:
                comp_desc.add((cat, tier, fmt))
        # The registered set: every pair is COMPUTED from the calibration
        # record: the adjustable pairs that fail the decision rule by option identity, and the published
        # (check-only) pairs whose measured point share lies outside the 25 to 75 percent hard limits. The result
        # must equal the registered list of seven, or the analysis refuses. The flags are only cross-checked.
        registered = set(DEVIATION_SENSITIVITY_PAIRS)
        deviation = adjustable_fail | published_limit
        if deviation != registered:
            raise ValueError(
                "the deviation sensitivity set computed from the calibration record (decision rule by option identity, "
                "hard limits on the point share) does not match the registered list: computed-only "
                f"{sorted(deviation - registered)}, registered-only {sorted(registered - deviation)}; refusing to run")
        mismatch = sorted(deviation ^ flag_deviation)
        design = cls(targets=targets, bin_focal=bin_focal, baseline_pct=baseline, hd_baseline_pct=hd_base,
                     deviation_slices=deviation, compromise_descriptive=comp_desc, flagged_compromise=flagged,
                     price_free=price_free, format_categories=fmt_cats, source=os.path.basename(path),
                     deviation_flag_mismatch=mismatch)
        design.compromise_flag_mismatch = sorted(comp_desc ^ flagged)
        return design

    @classmethod
    def for_synth(cls, real=None):
        """The REAL slice-level facts carried onto the synthetic lattice (synth.CAT_NAMES), identities
        left empty because synthetic rows code chose_target against an abstract target."""
        if real is None:
            real = cls.from_stimuli() if STIMULI_PATH else None
        if real is None:
            return cls(source="synthetic (no stimuli.json found)")
        inv = {v: str(k) for k, v in synth.CAT_NAMES.items()}

        def tr(sl):
            return (inv[sl[0]], sl[1], sl[2]) if sl[0] in inv else None
        return cls(targets={}, bin_focal={},
                   baseline_pct={tr(k): v for k, v in real.baseline_pct.items() if tr(k)},
                   hd_baseline_pct={tr(k): v for k, v in real.hd_baseline_pct.items() if tr(k)},
                   deviation_slices={tr(s) for s in real.deviation_slices if tr(s)},
                   compromise_descriptive={tr(s) for s in real.compromise_descriptive if tr(s)},
                   flagged_compromise={tr(s) for s in real.flagged_compromise if tr(s)},
                   price_free=set(),
                   format_categories={f: {inv[c] for c in cs if c in inv}
                                      for f, cs in real.format_categories.items()},
                   source="synthetic lattice carrying " + real.source,
                   deviation_flag_mismatch=real.deviation_flag_mismatch,
                   compromise_flag_mismatch=real.compromise_flag_mismatch)


NULL_DESIGN = Design.null()


# ===================================================================================================
# SHARED SCORING -- consumes contract-A human rows and contract-B model records identically.
# ===================================================================================================
_INDEX_CACHE = {}


_INDEX_CACHE_SIZE = 6   # a small recently-used cache; the old 48 entries kept every dataset a run
#                         had touched alive (a cache entry holds its list), which exhausted memory once the
#                         model arm carried the full repeated-draw plan.


def _index(rows):
    """Rows grouped by (structure, category, tier, format, prompting_mode); cached per list object. The
    cache keeps only the most recently used lists (build_pack works on one model and the human data at a
    time), so a dataset no longer in use is released."""
    key = id(rows)
    hit = _INDEX_CACHE.get(key)
    if hit is not None and hit[0] is rows and hit[1] == len(rows):
        _INDEX_CACHE[key] = _INDEX_CACHE.pop(key)      # mark as most recently used
        return hit[2]
    while len(_INDEX_CACHE) >= _INDEX_CACHE_SIZE:
        _INDEX_CACHE.pop(next(iter(_INDEX_CACHE)))     # evict the least recently used entry
    idx = defaultdict(list)
    for r in rows:
        idx[(r["structure"], str(r["category"]), _int(r["tier"]), r["format"], r.get("prompting_mode"))].append(r)
    _INDEX_CACHE[key] = (rows, len(rows), idx)
    return idx


def _in_scope(cat, scope, design):
    if scope == "all":
        return True
    pf = cat in design.price_free
    return pf if scope == "pricefree" else (not pf)


def _is_ext(r, kind):
    if kind == "human":
        return _int(r.get("chose_ext")) == 1 or r.get("choice") in ("EXT", "EXTREME")
    return r.get("parsed_choice") == "EXT"


def _is_clone(r, kind):
    if kind == "human":
        return _int(r.get("chose_clone")) == 1 or r.get("choice") == "CLONE"
    return r.get("parsed_choice") == "CLONE"


def _placement(r):
    """The similarity clone placement: human rows carry sim_placement (ingest.py); model records carry
    placement (run.py; None there means the base clone_HF delivery). None = the base placement."""
    for field in ("sim_placement", "placement"):
        p = r.get(field)
        if p in ("clone_HF", "clone_HD"):
            return p
    return None


def _pid(r, kind):
    return r["participant_id"] if kind == "human" else r.get("record_id")


def _treat_y(r, kind):
    return _int(r["chose_target"]) if kind == "human" else model_derive_target(r)


def _bin_chose_hd(r, kind, design):
    """1 when this BIN chooser took the HD option. Human rows carry chose_hd; model BIN records carry
    TARGET/COMP relative to the category-level BIN focal, which the design index knows."""
    if kind == "human":
        return _int(r.get("chose_hd"))
    y = model_derive_target(r)
    if y is None:
        return None
    return y if design.bin_focal.get(str(r["category"])) == "HD" else 1 - y


def _ctrl_y(r, kind, target, design):
    """The matched-control outcome: did the BIN chooser take the option THIS effect targets? With no
    identity information (synthetic rows) the row's own target indicator is used."""
    if target is None:
        return _treat_y(r, kind)
    hd = _bin_chose_hd(r, kind, design)
    if hd is None:
        return None
    return hd if target == "HD" else 1 - hd


def _row_target_kind(rows):
    """Synthetic fallback for the decoy-target moderator: the row-level is_hd flag."""
    return "HD" if rows and _int(rows[0].get("is_hd")) == 1 else "HF"


def _strata(rows, effect, kind, tiers=(1, 2, 3), fmt="numbers", mode="neutral", design=None,
            drop=(), trial=None, scope="backbone", cats=None, target_kind=None):
    """Build the matched strata for one registered contrast. Each stratum is one slice (category x
    tier x format; for similarity also the clone placement) holding the treatment rows and the rows
    of ITS matched control (BIN, or EXC for extremity), each as (cluster id, 0/1 outcome).
    Registered statistic per structure: FRQ/RNG/PHT target share; SOT relative share target/(target +
    competitor) with the new extreme excluded; SIM relative share uncloned/(uncloned + rival) with the
    clone excluded; SYM high-desirability share; MOT extreme-tier share against EXC.
    Returns (strata, n_excluded) where n_excluded counts model records excluded as refusals/unparseable."""
    design = design or NULL_DESIGN
    idx = _index(rows)
    md = None if kind == "human" else mode
    ctrl_struct = "EXC" if effect == "MOT" else "BIN"
    tiers = tuple(tiers)
    keys = sorted(k for k in idx if k[0] == effect and k[2] in tiers and k[3] == fmt and k[4] == md)
    out = []
    n_excl = 0
    for (_, cat, tier, f, _m) in keys:
        if not _in_scope(cat, scope, design):
            continue
        if cats is not None and cat not in cats:
            continue
        if (cat, tier, f) in drop:
            continue
        treat_rows = idx[(effect, cat, tier, f, md)]
        ctrl_rows = idx.get((ctrl_struct, cat, tier, f, md), [])
        if trial == "first":
            treat_rows = [r for r in treat_rows if _int(r["trial_position"]) == 1]
            ctrl_rows = [r for r in ctrl_rows if _int(r["trial_position"]) == 1]
        elif trial == "later":
            treat_rows = [r for r in treat_rows if _int(r["trial_position"]) != 1]
            ctrl_rows = [r for r in ctrl_rows if _int(r["trial_position"]) != 1]
        groups = defaultdict(list)
        for r in treat_rows:
            if kind == "model" and r.get("exclusion_flag"):
                n_excl += 1
                continue
            if effect == "SOT" and _is_ext(r, kind):
                continue
            if effect == "SIM" and _is_clone(r, kind):
                continue
            y = _treat_y(r, kind)
            if y is None:
                n_excl += 1
                continue
            # a missing placement is the base placement (clone_HF), on both sides, so human and
            # model similarity strata always share keys (the pooled model effect uses the human weights).
            pl = (_placement(r) or "clone_HF") if effect == "SIM" else None
            groups[pl].append((_pid(r, kind), y))
        n_excl += sum(1 for r in ctrl_rows if kind == "model" and r.get("exclusion_flag"))
        for pl in sorted(groups, key=lambda p: str(p)):
            t = groups[pl]
            tgt = None if effect == "MOT" else design.target(cat, tier, effect, pl)
            if target_kind is not None:
                here = tgt if tgt is not None else _row_target_kind(treat_rows)
                if here != target_kind:
                    continue
            c = []
            for r in ctrl_rows:
                if kind == "model" and r.get("exclusion_flag"):
                    continue
                y = _treat_y(r, kind) if effect == "MOT" else _ctrl_y(r, kind, tgt, design)
                if y is None:
                    continue
                c.append((_pid(r, kind), y))
            out.append(((cat, tier, f, pl), t, c))
    return out, n_excl


def human_contrast(rows, effect, tiers=(1, 2, 3), fmt="numbers", design=None, drop=(), trial=None,
                   scope="backbone", cats=None, target_kind=None):
    """The registered human contrast pooled over the requested slices: each slice against its own
    matched control, weighted by treatment count, with a cluster-robust (participant) standard error,
    a 95 percent interval, and the registered Bayes factor."""
    strata, _ = _strata(rows, effect, "human", tiers, fmt, None, design, drop, trial, scope, cats,
                        target_kind)
    delta, se, nt, nc, ncl = statlib.stratified_diff([(t, c) for _, t, c in strata])
    lo, hi = statlib.ci(delta, se, 0.95)
    slices = {key: (sum(y for _, y in t) / len(t) - sum(y for _, y in c) / len(c), len(t))
              for key, t, c in strata if t and c}
    return dict(delta=delta, se=se, ci_lo=lo, ci_hi=hi, n=nt + nc, n_clusters=ncl,
                bf10=statlib.bf10_halfnormal(delta, se, BF_PRIOR_SCALE),
                n_strata=len(slices), slices=slices)


def human_weights(hcontrast):
    """The human confirmatory slice weights (treatment counts) of one human contrast, keyed by slice.
    rule 3: a model's pooled effect uses the SAME slices and weights as the human test it is read
    against, so the two pooled numbers are the same weighted average of slice effects."""
    return {k: n for k, (_, n) in (hcontrast.get("slices") or {}).items()}


def _pooled_over(slices_delta, weights):
    """sum(w_k d_k) / sum(w_k) over the slices present in both maps; None when none is."""
    keys = [k for k in slices_delta if k in weights and weights[k] > 0]
    if not keys:
        return None
    W = sum(weights[k] for k in keys)
    return sum(weights[k] * slices_delta[k] for k in keys) / W


def control_arm(boot, effect, key, c, design, mode=None):
    """The resampled matched control of one slice (model calls or human choices; the same rule both sides).
    One resampling per control slice, shared by every effect and both similarity placements that use it (review
    finding 3): the arm is kept in the premium (HD) coding and a budget-targeted (HF) coding is its mirror image.
    the second revision: the coding is part of the arm's key, so a control coded against an abstract target (tgt None, no
    identity information) can never share a cached arm with an HD-coded one."""
    cat, tier, f, pl = key
    tgt = None if effect == "MOT" else design.target(cat, tier, effect, pl)
    ctrl = "EXC" if effect == "MOT" else "BIN"
    flip = (tgt == "HF")
    coding = "HD" if tgt in ("HD", "HF") else "raw"
    base = [(rid, 1 - y) for rid, y in c] if flip else c
    ca = boot.arm(("C", ctrl, (cat, tier, f), mode, coding), base)
    return boot.flipped(ca) if flip else ca


def model_contrast(recs, effect, tiers, fmt="numbers", mode="neutral", design=None, drop=(),
                   scope="backbone", cats=None, weights=None, boot=None):
    """The model effect over the requested slices, computed within matched slices exactly as the human
    contrast is: the mean over the enumerated grid and its repeated draws. No standard error,
    no test, no power, by protocol.

    weights: optional {slice: weight}; when given, the slices are
    weighted by them and only slices present in both are used; otherwise by the model's own treatment
    counts. boot: an optional call_bootstrap.CallBootstrap; when given, the result also carries the
    descriptive percentile interval over calls (boot_lo, boot_hi) and the largest number of calls behind
    one grid point (max_draws).
    Returns dict(delta, model_share, control_share, n_used, n_excluded, slices, parts, ...) or None when
    no slice has both arms."""
    design = design or NULL_DESIGN
    strata, nx = _strata(recs, effect, "model", tiers, fmt, mode, design, drop, None, scope, cats)
    kept = [(key, t, c) for key, t, c in strata if t and c]
    if weights is not None:
        kept = [(key, t, c) for key, t, c in kept if weights.get(key, 0) > 0]
    if not kept:
        return None
    W = sum((weights[key] if weights is not None else len(t)) for key, t, _ in kept)
    delta = ps = bs = 0.0
    n_used = 0
    slices = {}
    parts = []
    for key, t, c in kept:
        w = (weights[key] if weights is not None else len(t)) / W
        mt = sum(y for _, y in t) / len(t)
        mc = sum(y for _, y in c) / len(c)
        delta += w * (mt - mc)
        ps += w * mt
        bs += w * mc
        n_used += len(t) + len(c)
        slices[key] = (mt - mc, len(t))
        if boot is not None:
            ta = boot.arm(("T", effect, key, mode), t)
            parts.append((w, ta, control_arm(boot, effect, key, c, design, mode)))
    out = dict(delta=delta, model_share=ps, control_share=bs, n_used=n_used, n_excluded=nx,
               slices=slices, parts=parts, boot_lo=None, boot_hi=None, max_draws="")
    if boot is not None:
        out["boot_lo"], out["boot_hi"] = boot.interval(parts)
        out["max_draws"] = max(max(p[1][3], p[2][3]) for p in parts)
    return out


def matched_contrast(h, recs, effect, tiers, fmt="numbers", design=None, drop=(), cats=None, boot=None,
                     mode="neutral"):
    """rule 3: the model's pooled effect on the SAME slices, with the SAME slice weights (the human
    treatment counts), as the human estimate h it is read against. Returns (model contrast or None, the
    human effect pooled over the slices the model also has)."""
    w = human_weights(h)
    m = model_contrast(recs, effect, tuple(tiers), fmt, mode, design, drop, "backbone", cats, weights=w, boot=boot)
    if m is None:
        return None, None
    hd = _pooled_over({k: d for k, (d, _) in h["slices"].items()}, {k: w[k] for k in m["slices"]})
    return m, hd


def paraphrase_signs(recs, effect, tiers, fmt="numbers", mode="neutral", design=None, drop=(),
                     scope="backbone", cats=None, weights=None):
    """rule 6. The pooled model effect computed separately for each paraphrase (treatment and control
    calls restricted to that paraphrase, same slices and weights). Returns (deltas {paraphrase: delta},
    prompt_sensitive) where prompt_sensitive is True when the signs differ across the paraphrases (a zero
    counts as its own sign) and None when fewer than two paraphrases are present."""
    design = design or NULL_DESIGN
    para = {r.get("record_id"): r.get("paraphrase_id") for r in recs}
    strata, _ = _strata(recs, effect, "model", tiers, fmt, mode, design, drop, None, scope, cats)
    ids = sorted({para.get(rid) for _, t, c in strata for rid, _ in t + c} - {None}, key=str)
    deltas = {}
    for p in ids:
        sd = {}
        for key, t, c in strata:
            tp = [y for rid, y in t if para.get(rid) == p]
            cp = [y for rid, y in c if para.get(rid) == p]
            if tp and cp:
                sd[key] = sum(tp) / len(tp) - sum(cp) / len(cp)
        w = weights if weights is not None else {k: 1 for k in sd}
        d = _pooled_over(sd, w)
        if d is not None:
            deltas[p] = d
    if len(deltas) < 2:
        return deltas, None
    signs = {(1 if d > 0 else (-1 if d < 0 else 0)) for d in deltas.values()}
    return deltas, len(signs) > 1


def human_effect(human_rows, struct, tier, fmt="numbers", first_trial=False, design=None, drop=()):
    """The registered human effect for one tier (pooled over its categories), full sample or first
    trials only. Kept under its original name for the callers and the tests."""
    return human_contrast(human_rows, struct, (tier,), fmt, design, drop,
                          "first" if first_trial else None)


def human_effect_pooled(human_rows, struct, fmt="numbers", is_hd=None, design=None, drop=()):
    """The pooled human effect for one effect, optionally restricted to the slices whose decoy targets
    the high-desirability option (is_hd=True) or the high-feasibility option (is_hd=False). The
    counterbalance is applied only in the new-value and invented tiers (the published tier keeps the
    published premium target), so the moderator reads tiers 2 and 3; the pooled effect reads all."""
    if is_hd is None:
        c = human_contrast(human_rows, struct, (1, 2, 3), fmt, design, drop)
    else:
        c = human_contrast(human_rows, struct, (2, 3), fmt, design, drop,
                           target_kind=("HD" if is_hd else "HF"))
    return dict(delta=c["delta"], se=c["se"], delta_pp=c["delta"] * 100, n_clusters=c["n_clusters"])


def model_derive_target(rec):
    """Derive chose_target (0/1) for one contract-B model record from parsed_choice, using the SAME
    per-structure codebook the human side uses. None for refusals/unparseable (excluded)."""
    if rec.get("exclusion_flag"):
        return None
    pc = rec.get("parsed_choice")
    if pc is None:
        return None
    st = rec["structure"]
    if st == "MOT":
        return 1 if pc in ("T1S1", "T1S2", "T1S3", "T1S4", "T3S1", "T3S2", "T3S3", "T3S4") else 0
    if st == "EXC":
        # extremity control: extreme tier = High or Low (EXC_H/EXC_L); Middle (EXC_M) is the non-extreme.
        return 1 if pc in ("EXC_H", "EXC_L") else 0
    if st == "SYM":
        return 1 if pc == "HD" else 0
    return 1 if pc == "TARGET" else 0


def model_effect(model_recs, struct, tier, fmt="numbers", design=None, drop=(), cats=None):
    """The model effect for one tier. Returns (delta, model_share, control_share, n_used, n_excluded),
    the original signature; delta is None when the tier has no matched cell."""
    m = model_contrast(model_recs, struct, (tier,), fmt, "neutral", design, drop, "backbone", cats)
    if m is None:
        return None, None, None, 0, 0
    return m["delta"], m["model_share"], m["control_share"], m["n_used"], m["n_excluded"]


def model_effect_pooled_mode(model_recs, struct, mode, fmt="numbers", design=None):
    """The model effect for ONE prompting mode, pooled across tiers, as a population quantity (no SE,
    no CI, no power, by protocol). Used only for the registered neutral-vs-persona and
    single-shot-vs-sequential DIVERGENCE readings (the Analysis Plan ). Returns the pooled delta
    in proportion, or None when the mode has no records for this effect."""
    m = model_contrast(model_recs, struct, (1, 2, 3), fmt, mode, design)
    return None if m is None else m["delta"]


def model_binary_share(model_recs, tier, fmt="numbers"):
    """The model's raw binary target share in the BIN control cells of one tier and format -- used for
    the ceiling rule (no room to move if above 90 percent or below 10 percent)."""
    idx = _index(model_recs)
    k = n = 0
    for key, recs in idx.items():
        if key[0] == "BIN" and key[2] == tier and key[3] == fmt and key[4] == "neutral":
            for r in recs:
                y = model_derive_target(r)
                if y is not None:
                    k += y; n += 1
    return (k / n if n else 0.0), n


# ===================================================================================================
# STEP 0 -- validity criteria.
# ===================================================================================================
def holm_by_family(raw_p):
    """Holm within each registered family (registered_constants.HOLM_FAMILIES): the six regularity
    effects are corrected among themselves and similarity, scored apart, is its own family.
    Returns ({effect: (raw_p, adjusted_p, reject)}, {effect: family})."""
    families = {k: v for k, v in HOLM_FAMILIES.items() if k != "format_interaction"}
    tab, fam_of = {}, {}
    for fam, members in families.items():
        present = {st: raw_p[st] for st in members if st in raw_p}
        tab.update(statlib.holm(present, alpha=HOLM_ALPHA))
        for st in present:
            fam_of[st] = fam
    return tab, fam_of


def human_gate(human_rows, design=None, drop_by_effect=None, trial=None, fallback=False,
               scope="backbone"):
    """Step 0a: the per-effect human replication criterion. An effect replicates when its pooled
    contrast (numeric backbone, all tiers, each slice against its matched control) is significant
    after Holm WITHIN ITS REGISTERED FAMILY, runs in the REGISTERED DIRECTION (a positive difference),
    and has a half-normal Bayes factor above three. After a first-trial fallback (fallback=True) an
    effect is confirmatory only if its size is at least the registered 8-point floor. Returns the criterion
    dict, the pooled estimates, the Holm table, whether the positive controls held, and whether four
    or more of the six non-similarity effects failed (the S7 branch)."""
    design = design or NULL_DESIGN
    drop_by_effect = drop_by_effect or {}
    pooled = {}
    raw_p = {}
    for st in EFFECTS:
        c = human_contrast(human_rows, st, (1, 2, 3), "numbers", design,
                           drop_by_effect.get(st, ()), trial, scope)
        z = c["delta"] / c["se"] if c["se"] > 0 else 0.0
        p = statlib.two_sided_p_from_z(z)
        pooled[st] = dict(delta=c["delta"], se=c["se"], z=z, p=p, bf10=c["bf10"],
                          n_clusters=c["n_clusters"], ci_lo=c["ci_lo"], ci_hi=c["ci_hi"])
        raw_p[st] = p
    holm_tab, fam_of = holm_by_family(raw_p)
    criterion = {}
    for st in EFFECTS:
        p, adj, reject = holm_tab[st]
        d = pooled[st]["delta"]
        bf = pooled[st]["bf10"]
        right_direction = d > 0
        replicated = bool(reject and right_direction and bf > BF_GATE)
        confirmatory = bool(replicated and ((not fallback) or d * 100 >= FIRST_TRIAL_MIN_EFFECT_PP))
        criterion[st] = dict(replicated=replicated, confirmatory=confirmatory, raw_p=p, holm_p=adj,
                        holm_reject=reject, holm_family=fam_of[st], right_direction=right_direction,
                        bf10=bf, delta_pp=d * 100, ci_lo_pp=pooled[st]["ci_lo"] * 100,
                        ci_hi_pp=pooled[st]["ci_hi"] * 100,
                        is_positive_control=(st in POSITIVE_CONTROLS))
    controls_held = all(criterion[c]["replicated"] for c in POSITIVE_CONTROLS)
    n_failed_regular = sum(1 for st in REGULARITY_EFFECTS if not criterion[st]["replicated"])
    most_failed = n_failed_regular >= RC.MOST_FAILED_MIN
    return criterion, pooled, holm_tab, controls_held, most_failed


def phantom_equivalence(delta, se):
    """The registered phantom equivalence judgment on the POOLED HUMAN phantom effect: two one-sided
    tests at .05, i.e. the 90 percent interval must lie entirely inside minus 4 to plus 4 points. It
    separates a phantom effect that is shown to be absent (smaller than 4 points either way) from one
    that is merely not detected."""
    lo, hi, eq, p = statlib.tost_equivalence(delta, se, PHANTOM_BAND, RC.PHANTOM_EQUIV_ALPHA)
    equivalent = eq
    return dict(equivalent=bool(equivalent), ci90_lo_pp=lo * 100, ci90_hi_pp=hi * 100, p_tost=p,
                delta_pp=delta * 100, band_pp=PHANTOM_BAND_PP)


def first_trial_check(human_rows, design=None, drop_by_effect=None):
    """Step 1 comparability check. For each of the seven pooled confirmatory contrasts (numeric
    backbone, all tiers), compare the estimate from participants' FIRST choices with the estimate from
    their LATER choices (independent samples of choices), and record the gap between the full-sample
    and the first-trial estimate. The decision is first_trial_decide."""
    design = design or NULL_DESIGN
    drop_by_effect = drop_by_effect or {}
    per = {}
    for st in EFFECTS:
        dr = drop_by_effect.get(st, ())
        full = human_contrast(human_rows, st, (1, 2, 3), "numbers", design, dr, None)
        first = human_contrast(human_rows, st, (1, 2, 3), "numbers", design, dr, "first")
        later = human_contrast(human_rows, st, (1, 2, 3), "numbers", design, dr, "later")
        se_fl = math.sqrt(first["se"] ** 2 + later["se"] ** 2)
        d_fl = later["delta"] - first["delta"]
        z = d_fl / se_fl if se_fl > 0 else 0.0
        per[st] = dict(full_pp=full["delta"] * 100, first_pp=first["delta"] * 100,
                       later_pp=later["delta"] * 100,
                       divergence_pp=(full["delta"] - first["delta"]) * 100,
                       first_minus_later_se_pp=se_fl * 100, z=z,
                       p=statlib.two_sided_p_from_z(z),
                       n_first=first["n"], n_full=full["n"])
    return first_trial_decide(per)


def first_trial_decide(per):
    """The registered first-trial rule. Holm across the seven effects at family-wise .05 on the
    first-versus-later difference; an effect DIVERGES when its difference is significant after Holm
    AND its full-sample and first-trial estimates differ by more than 5 points. The fallback fires when
    any effect diverges. Because the rule is a subset of a family-wise .05 Holm rejection, its
    false-alarm rate under no contamination is at most 5 percent (simulated at the planned first-trial
    cell sizes in power/first_trial_rule_sim.py)."""
    holm_tab = statlib.holm({st: per[st]["p"] for st in per}, alpha=RC.FIRST_TRIAL_ALPHA)
    fired = []
    for st in per:
        _, adj, rej = holm_tab[st]
        diverges = bool(rej and abs(per[st]["divergence_pp"]) > RC.FIRST_TRIAL_MIN_DIVERGENCE_PP)
        per[st].update(holm_p=adj, holm_reject=bool(rej), diverges=diverges)
        if diverges:
            fired.append(st)
    return dict(per_effect=per, fired=bool(fired), fired_effects=fired)


def model_gate(model_recs):
    """Step 0b: per-model criterion. Parse rate, refusal rate, and the ceiling rule. A model that loses more
    than one third of its cells (structure x category x tier x format) to unreadable answers, refusals,
    or ceilings is not assessable.

    The ceiling rule is applied per BINARY CELL, one category x tier x format (2026-09-29; the old code
    pooled the binary share over every category of a tier, and because the BIN rows' TARGET label means
    the premium option in most categories but the budget option in others, a model choosing the premium
    option every time could pool to a middling share and escape the rule). A model whose share of either
    option exceeds 90 percent in a binary cell leaves no room to move there, so every effect contrast
    built on that category-tier-format slice is held out for that model (no_room_slices); a pooled
    fidelity cell (effect x tier x format) with no slice left is excluded(no-room) (no_room_cells)."""
    idx = _index(model_recs)
    n_calls = n_refusal = n_unparse = 0
    cells = set()
    cell_calls = defaultdict(lambda: [0, 0])  # [excluded, total]
    no_room_slices = set()
    for (st, cat, tier, fmt, mode), recs in idx.items():
        if mode != "neutral":
            continue
        cell = (st, cat, tier, fmt)
        cells.add(cell)
        for r in recs:
            n_calls += 1
            cell_calls[cell][1] += 1
            if r.get("exclusion_flag"):
                cell_calls[cell][0] += 1
                if r.get("exclusion_reason") == "refusal":
                    n_refusal += 1
                else:
                    n_unparse += 1
        if st == "BIN":
            ys = [y for y in (model_derive_target(r) for r in recs) if y is not None]
            if ys:
                share = sum(ys) / len(ys)
                if share > CEIL_HI or share < CEIL_LO:
                    no_room_slices.add((cat, tier, fmt))
    parse_rate = 1.0 - (n_unparse + n_refusal) / n_calls if n_calls else 0.0
    refusal_rate = n_refusal / n_calls if n_calls else 0.0
    lost_cells = {c for c, (exc, tot) in cell_calls.items() if tot > 0 and (1.0 - exc / tot) < PARSE_FLOOR}
    no_room_cellset = {c for c in cells if (c[1], c[2], c[3]) in no_room_slices}
    bin_cats = defaultdict(set)
    for (st, cat, tier, fmt) in cells:
        if st == "BIN":
            bin_cats[(tier, fmt)].add(cat)
    no_room_cells = set()
    for (tier, fmt), cats_tf in bin_cats.items():
        if cats_tf and all((c, tier, fmt) in no_room_slices for c in cats_tf):
            for st in EFFECTS:
                no_room_cells.add((st, tier, fmt))
    total_cells = len(cells)
    n_lost = len(lost_cells | no_room_cellset)
    frac_lost = n_lost / total_cells if total_cells else 0.0
    parse_ok = parse_rate >= PARSE_FLOOR
    refusal_ok = refusal_rate <= REFUSAL_CEIL
    not_assessable = (frac_lost > NOT_ASSESSABLE_FRAC) or (not parse_ok) or (not refusal_ok)
    return dict(parse_rate=parse_rate, refusal_rate=refusal_rate, parse_ok=parse_ok,
                refusal_ok=refusal_ok, no_room_cells=no_room_cells, no_room_slices=no_room_slices,
                lost_cells=lost_cells, frac_lost=frac_lost, not_assessable=not_assessable,
                total_cells=total_cells, n_lost=n_lost)


# ===================================================================================================
# STEP 2 -- fidelity classification.
# ===================================================================================================
def classify_cell(model_eff, human_eff):
    """Sort one model effect against its (replicated) human benchmark, or 'n/a' when the human effect
    is itself below the 2-point scoring floor. Registered rule:
      opposite sign (or zero): ANTI when the model effect is larger than 3 points, otherwise LOW (the old
                               code fell through to the size ratio here and scored -2.9 against +4 HIGH);
      same direction:          OVER above 150 percent of the human effect, HIGH from 70 to 150 percent,
                               PARTIAL from 25 to 70 percent, LOW below 25 percent.
    classify_cell is called only for effects that replicated in humans (a failed effect exits scoring
    through gate_exit_class), so ANTI is always a reversal of a replicated effect."""
    if abs(_pts(human_eff)) < RC.NEAR_NULL_HUMAN_PP:
        return "n/a"
    same_sign = (model_eff > 0) == (human_eff > 0) and _pts(model_eff) != 0
    if not same_sign:
        return "ANTI" if abs(_pts(model_eff)) > RC.ANTI_MIN_PP else "LOW"
    ratio = round(abs(model_eff) / abs(human_eff), 9)   # rounded: 0.7 and 1.5 sit exactly on their cutoffs
    if ratio > OVER_RATIO:
        return "OVER"
    if ratio >= HIGH_RATIO:
        return "HIGH"
    if ratio >= PARTIAL_RATIO:
        return "PARTIAL"
    return "LOW"


def majority_class(classes):
    """The most frequent scored class; ties go to the LESS FAITHFUL class. 'n/a' when nothing
    is scored."""
    real = [c for c in classes if c in SCORED_CLASSES]
    if not real:
        return "n/a"
    top = max(real.count(c) for c in set(real))
    return next(c for c in CLASS_ORDER if c in real and real.count(c) == top)


def gate_exit_class(model_eff):
    """A cell whose effect FAILED the human criterion leaves every agreement measure. If the model's
    own effect there is larger than the registered minimum model effect (3 points, either sign), the
    cell is reported as an effect without a human counterpart; otherwise it is a plain criterion exit.
    ANTI stays reserved for a model effect opposite in sign to a REPLICATED human effect."""
    if model_eff is not None and abs(_pts(model_eff)) > RC.ANTI_MIN_PP:
        return "no-human-counterpart"
    return "excluded(criterion-exit)"


def agreement(cells):
    """Summarize a model's scorable cells: sign-agreement rate, mean absolute deviation in points,
    calibration slope, dominant class. cells is a list of dicts with human_pp/model_pp/class."""
    scorable = [c for c in cells if c["class"] not in NON_SCORED]
    if not scorable:
        return dict(sign_agreement=0.0, mad_pp=0.0, calibration_slope=float("nan"),
                    dominant_class="n/a", n_scored=0)
    sign = sum(1 for c in scorable if (c["human_pp"] > 0) == (c["model_pp"] > 0)) / len(scorable)
    mad = sum(abs(c["model_pp"] - c["human_pp"]) for c in scorable) / len(scorable)
    slope = statlib.ols_slope([c["human_pp"] for c in scorable], [c["model_pp"] for c in scorable])
    classes = [c["class"] for c in scorable]
    # the registered tie rule (ties to the less faithful class; registered_constants.TIE_BREAK_RULE). Since
    # 2026-09-29 the class that routes is the overall class on pooled estimates (overall_class); this per-tier
    # majority is kept for legacy callers.
    dom = majority_class(classes)
    return dict(sign_agreement=round(sign, 3), mad_pp=round(mad, 2),
                calibration_slope=round(slope, 3) if slope == slope else float("nan"),
                dominant_class=dom, n_scored=len(scorable))


def fidelity_ratio_for(rows_subset):
    """A group's fidelity for the pattern tests: the model effect divided by the
    human effect, pooled across the group's cells and weighted by the size of the human effect (the sum
    of the model effects projected onto the human-effect direction over the sum of the human
    magnitudes), then combined: a value above 1 becomes 2 minus the value, so an overshoot and an
    undershoot of the same size count alike, and the result is capped below at -1. 1 = the human size,
    0 = no effect or twice the human size, negative = reversed or far overshooting. None when the group
    carries no human effect to be faithful to. The combine applies to the POOLED group value, as the rule
    words it; an overshoot on one cell can therefore offset an undershoot on another inside a group
."""
    num = 0.0
    den = 0.0
    for c in rows_subset:
        if c["class"] in NON_SCORED:
            continue
        h = c["human_pp"]
        if abs(h) < NEAR_NULL_HUMAN * 100:
            continue
        num += c["model_pp"] * (1.0 if h > 0 else -1.0)
        den += abs(h)
    if den == 0:
        return None
    return _fold(num / den)


group_fidelity = fidelity_ratio_for


def group_ratio_raw(rows_subset):
    """The same pooled group value BEFORE the combine and the cap (1 = the human size, above 1 = overshoot).
    The directional pattern readings use it to require an undershoot (see UNDERSHOOT_NOTE)."""
    num = den = 0.0
    for c in rows_subset:
        if c["class"] in NON_SCORED:
            continue
        h = c["human_pp"]
        if abs(h) < NEAR_NULL_HUMAN * 100:
            continue
        num += c["model_pp"] * (1.0 if h > 0 else -1.0)
        den += abs(h)
    return None if den == 0 else num / den


# the combine makes an overshoot and an undershoot of the same size count alike, which
# is right for the "flat" readings but inverts the directional ones, because every account predicts an
# UNDERSHOOT in a named group. A directional reading therefore
# fires only when that group's unfolded value is below 1; an overshoot there is reported descriptively (its
# cells carry their own OVER class).
UNDERSHOOT_NOTE = ("the lower group overshoots the human effect (unfolded value above 1), so no undershoot "
                   "reading: reported descriptively")


def _undershoots(raw, key):
    """True when no unfolded value is supplied (legacy callers) or the group's unfolded value is below 1."""
    if raw is None:
        return True
    v = raw.get(key)
    return v is not None and v < FOLD_AT


# ===================================================================================================
# STEP 3 -- the five pattern tests. Each reads its planted pattern from the same scored cells.
# ===================================================================================================
# ---------------------------------------------------------------------------------------------------
# rule 1: every T1, T3, T4 and T5 reading is resolved against the
# 95 percent interval of a JOINT bootstrap (human participants resampled within cells, model calls within grid
# points, together; resolution_reps below). A directional reading fires only when its point crosses the cutoff
# AND the interval excludes the flat region (and the opposite direction); a flat reading fires only when its
# point lies inside the flat cutoff AND the interval excludes the directional cutoff. Each registered reading is
# therefore true (T), set out by the interval (F), or open (U). A test is resolved when one reading is T (that
# reading), or when every reading is F (no registered reading: reported descriptively, as before); otherwise it
# is NOT RESOLVED and supports no scenario (route_resolved enumerates what an open reading could be). With
# resolve=False a test returns the old point reading (kept for descriptive re-readings and legacy callers).
# ---------------------------------------------------------------------------------------------------
NOT_RESOLVED = "not resolved"


def _tfu(true, false):
    """The three-valued state of one registered reading: 'T' fires, 'F' is set out, 'U' is open. When the point
    meets the firing conditions but the whole interval sits on the other side of the cutoff (the combine can put a
    point outside its own percentile interval), the evidence disagrees with itself and the reading stays open
."""
    if true and false:
        return "U"
    return "T" if true else ("F" if false else "U")


def _ci_have(ci):
    return ci is not None and ci[0] is not None and ci[1] is not None


def _ci_text(ci):
    if not _ci_have(ci):
        return "no interval"
    f = lambda v: ("-inf" if v == -math.inf else ("+inf" if v == math.inf else f"{v:.3f}"))
    return f"{f(ci[0])} to {f(ci[1])}"


def _ci_end(v):
    """One end of a resolution interval as printed: rounded, '-inf'/'+inf' when undefined replicates leave it
    unbounded (call_bootstrap.interval), '' when there is no interval (the bootstrap was not run)."""
    if v is None:
        return ""
    if math.isinf(v):
        return "-inf" if v < 0 else "+inf"
    return round(v, 3)


def _ruled_out_all(point_reading, what, ci):
    """The reading when the interval rules out every registered reading of a test. It supports no scenario;
    route_resolved's only option for it is 'neither', so the route is the one the old descriptive reading gave."""
    return (f"{NOT_RESOLVED}: the 95 percent interval of {what} ({_ci_text(ci)}) rules out every registered reading "
            f"(point reading: {point_reading}); reported descriptively, supports no scenario")


def _not_resolved(point_reading, what, ci):
    return (f"{NOT_RESOLVED}: the 95 percent interval of {what} ({_ci_text(ci)}) does not settle the reading "
            f"(point reading: {point_reading}); supports no scenario")


def _drop_states(drop, slope, drop_ci, steps, guard=True):
    """The states of the steep and flat memorization readings for one drop across `steps` tier steps:
    steep fires when the drop exceeds 0.30, the undershoot guard holds and the interval's lower end lies above
    the flat region (0.10 per tier step); it is set out when the guard fails or the interval's upper end is at
    or below 0.30. Flat fires when the slope is within 0.10 per step and the interval's upper end is below 0.30;
    it is set out when the interval lies wholly outside the flat region."""
    have = _ci_have(drop_ci)
    dlo, dhi = (drop_ci if have else (None, None))
    flat_w = RC.T1_FLAT_SLOPE * steps
    p_steep = _tfu(have and drop > RC.T1_STEEP_DROP and guard and dlo > flat_w,
                   (not guard) or (have and dhi <= RC.T1_STEEP_DROP))
    p_flat = _tfu(have and abs(slope) < RC.T1_FLAT_SLOPE and dhi < RC.T1_STEEP_DROP,
                  have and (dlo >= flat_w or dhi <= -flat_w))
    return p_steep, p_flat


def test_T1_memorization(cells_by_tier, raw=None, drop_ci=None, resolve=False):
    """T1: does fidelity fall down the memorization gradient? The registered call passes two tiers,
    the published-values tier (1) and the new-values tier (2), paired by category; any first and last tier work.
    cells_by_tier maps tier -> pooled (combined) group fidelity; raw (optional) maps tier -> the unfolded
    value, and "steep" then needs the invented tier to undershoot (UNDERSHOOT_NOTE). With resolve=True the
    reading is resolved against drop_ci, the 95 percent interval of the drop (first minus last tier present):
      steep  drop above 0.30, the undershoot guard met, and the interval's lower end above the flat region
             (0.10 per tier step);
      flat   slope within 0.10 per tier step, and the interval's upper end below 0.30;
      otherwise not resolved.
    Returns the per-tier fidelity, the slope, the drop, its interval, the states and the reading."""
    t = {ti: cells_by_tier.get(ti) for ti in (1, 2, 3)}
    present = [ti for ti in (1, 2, 3) if t[ti] is not None]
    if len(present) < 2:
        return dict(reading="insufficient tiers", slope=0.0, drop_lo="", drop_hi="", p_steep="F", p_flat="F",
                    resolved=True, **{f"fidelity_t{ti}": t[ti] for ti in (1, 2, 3)})
    lo, hi = present[0], present[-1]
    slope = (t[hi] - t[lo]) / (hi - lo)
    drop = (t[lo] or 0) - (t[hi] or 0)
    guard = _undershoots(raw, hi)
    if drop > RC.T1_STEEP_DROP and not guard:
        point = "non-monotone or shallow: " + UNDERSHOOT_NOTE
    elif drop > RC.T1_STEEP_DROP:
        point = "steep: fidelity falls down the gradient -> retrieval, not behavior (S2)"
    elif abs(slope) < RC.T1_FLAT_SLOPE:
        point = "flat: fidelity is genuine behavior, not retrieval"
    else:
        point = "non-monotone or shallow: reported descriptively, no causal reading"
    out = dict(slope=round(slope, 3), drop=round(drop, 3), drop_lo="", drop_hi="", point_reading=point,
               **{f"fidelity_t{ti}": (round(t[ti], 3) if t[ti] is not None else "") for ti in (1, 2, 3)})
    if not resolve:
        return dict(out, reading=point, p_steep=("T" if point.startswith("steep") else "F"),
                    p_flat=("T" if point.startswith("flat") else "F"), resolved=True)
    have = _ci_have(drop_ci)
    dlo, dhi = (drop_ci if have else (None, None))
    p_steep, p_flat = _drop_states(drop, slope, drop_ci, hi - lo, guard)
    if p_steep == "T" or p_flat == "T":
        reading = point
    elif p_steep == "F" and p_flat == "F":
        reading = _ruled_out_all(point, "the drop", drop_ci)
    else:
        reading = _not_resolved(point, "the drop", drop_ci)
    return dict(out, reading=reading, drop_lo=_ci_end(dlo), drop_hi=_ci_end(dhi), p_steep=p_steep, p_flat=p_flat,
                resolved=not reading.startswith(NOT_RESOLVED))


def test_T2_recognition(recog_by_struct, behavior_by_struct, uninformative=(), descriptive=(), recog_ci=None,
                        behavior_ci=None):
    """T2: knows-it-versus-shows-it. recog_by_struct maps struct -> recognition rate; behavior_by_struct
    maps struct -> the signed behavioral effect. Returns per-struct readings and a model-level flag
    for 'recognizes-but-does-not-show' (the override that takes precedence over magnitude readings). An
    effect whose positive control failed reads as uninformative and never sets the flag.
    Registered rule (b): rational override needs a RESOLVED knows-without-shows reading:
    recog_ci maps struct -> the 95 percent interval of the recognition rate (the probe calls resampled within
    each stimulus) and behavior_ci maps struct -> the 95 percent interval of the pooled model effect (its calls
    resampled within each grid point). 'Knows' is resolved when the rate and its whole interval lie at or above the
    cutoff (or both below it); 'shows' when the effect and its whole interval lie above 3 points (or both at or
    below 3 points); knows-without-shows ('override_state') is T when knows is T and shows is F, F when knows is
    F or shows is T, and open otherwise. Without intervals the states are the point readings."""
    recog_ci = recog_ci or {}
    behavior_ci = behavior_ci or {}
    per = {}
    override_any = False
    for st in EFFECTS:
        if st == "PHT":
            continue
        rec = recog_by_struct.get(st, 0.0)
        beh = behavior_by_struct.get(st, 0.0)
        shows = _pts(beh) > RC.ANTI_MIN_PP               # shows the human-direction effect (> 3 points)
        knows = rec >= RC.RECOGNITION_CUTOFF
        rci, bci = recog_ci.get(st), behavior_ci.get(st)
        k_state = (_tfu(knows and rci[0] >= RC.RECOGNITION_CUTOFF, (not knows) and rci[1] < RC.RECOGNITION_CUTOFF)
                   if _ci_have(rci) else ("T" if knows else "F"))
        s_state = (_tfu(shows and _pts(bci[0]) > RC.ANTI_MIN_PP, (not shows) and _pts(bci[1]) <= RC.ANTI_MIN_PP)
                   if _ci_have(bci) else ("T" if shows else "F"))
        o_state = "T" if (k_state == "T" and s_state == "F") else ("F" if (k_state == "F" or s_state == "T") else "U")
        if st not in behavior_by_struct:
            o_state = "F"               # no pooled estimate for this effect: no knows-without-shows reading
        if st in uninformative:
            reading = UNINFORMATIVE + ": no registered reading"
            o_state = "F"
        elif st in descriptive:
            reading = DESCRIPTIVE_FLOOR + ": no registered reading"
            o_state = "F"
        elif st not in behavior_by_struct:
            reading = "no pooled estimate: no registered reading"
        elif knows and not shows:
            reading = "recognizes-but-does-not-show -> rational override (predicts LOW/ANTI)"
            override_any = True
        elif knows and shows:
            reading = "recognizes-and-shows -> deliberate/learned reproduction"
        elif (not knows) and shows:
            reading = "shows-without-recognizing -> deep behavioral mimicry"
        else:
            reading = "neither -> no context sensitivity at any level"
        per[st] = dict(recognition_rate=round(rec, 3), behavior_pp=round(beh * 100, 2),
                       knows=knows, shows=shows, reading=reading, knows_state=k_state, shows_state=s_state,
                       override_state=o_state,
                       recognition_lo=(round(rci[0], 3) if _ci_have(rci) else ""),
                       recognition_hi=(round(rci[1], 3) if _ci_have(rci) else ""),
                       behavior_lo_pp=(round(bci[0] * 100, 2) if _ci_have(bci) else ""),
                       behavior_hi_pp=(round(bci[1] * 100, 2) if _ci_have(bci) else ""))
    return per, override_any


def t2_override_state(per):
    """The model-level state of the rational-override reading: T when some effect is a resolved
    knows-without-shows, F when every effect's reading rules it out, open otherwise."""
    states = [d.get("override_state", "F") for d in per.values()]
    return "T" if "T" in states else ("U" if "U" in states else "F")


def test_T3_ladder(fidelity_by_struct, effect_classes=None, recog_by_struct=None, raw=None, ci=None,
                   resolve=False):
    """T3 with the earlier resolution. ci = dict(top_minus_bottom=(lo, hi), bottom_minus_middle=(lo, hi)
    or None when the middle rung is absent), the 95 percent intervals of the joint bootstrap. With resolve=True:
      declines  top minus bottom above 0.30 (the bottom rung undershooting), with its interval's lower end above
                0.12 (the flat cutoff);
      reversed  bottom above the top and the middle rung by more than 0.30 (both undershooting), with both
                intervals' lower ends above 0.12;
      flat      top and bottom within 0.12, with the interval of top minus bottom inside 0.30 either way;
      otherwise not resolved (when the intervals rule out every reading, the reading says so, is reported
      descriptively and routes as 'neither').
    The reversed ladder's attribution (recognition on the missed effects) is always computed from the point
    classes and kept in private keys, so an open reversed reading can be routed with what it would attribute."""
    res = _test_T3_point(fidelity_by_struct, effect_classes, recog_by_struct, raw)
    res.update(point_reading=res["reading"], point_reversed=res["reversed"])
    if not resolve:
        res.update(p_declines=("T" if res["reading"].startswith("declines") else "F"),
                   p_reversed=("T" if res["reversed"] else "F"),
                   p_flat=("T" if res["reading"].startswith("flat") else "F"), resolved=True,
                   tmb_lo="", tmb_hi="", bmm_lo="", bmm_hi="")
        return res
    if res["reading"] == "insufficient rungs":
        res.update(p_declines="F", p_reversed="F", p_flat="F", resolved=True, tmb_lo="", tmb_hi="", bmm_lo="",
                   bmm_hi="")
        return res
    ci = ci or {}
    tmb = ci.get("top_minus_bottom")
    bmm = ci.get("bottom_minus_middle")
    have = _ci_have(tmb)
    mid = res["mid_rung"] if res["mid_rung"] != "" else None
    d = res["_top_minus_bottom"]
    step, flat = RC.T3_LADDER_STEP, RC.T3_LADDER_FLAT
    guard_dec, guard_rev = res["_guard_declines"], res["_guard_reversed"]
    lo, hi = (tmb if have else (None, None))
    mid_have = mid is not None and _ci_have(bmm)
    p_declines = _tfu(have and d > step and guard_dec and lo > flat,
                      (not guard_dec) or (have and hi <= step))
    rev_point = (-d > step) and (mid is None or res["_bottom_minus_middle"] > step)
    rev_int = have and -hi > flat and (mid is None or (mid_have and bmm[0] > flat))
    rev_out = (have and -lo <= step) or (mid is not None and mid_have and bmm[1] <= step)
    p_reversed = _tfu(rev_point and guard_rev and rev_int, (not guard_rev) or rev_out)
    p_flat = _tfu(have and abs(d) < flat and -step < lo and hi < step, have and (lo >= flat or hi <= -flat))
    base_keys = dict(tmb_lo=_ci_end(lo), tmb_hi=_ci_end(hi),
                     bmm_lo=(_ci_end(bmm[0]) if mid_have else ""), bmm_hi=(_ci_end(bmm[1]) if mid_have else ""),
                     p_declines=p_declines, p_reversed=p_reversed, p_flat=p_flat)
    if "T" in (p_declines, p_reversed, p_flat):
        res.update(base_keys, resolved=True)
        if p_reversed != "T":
            res.update(reversed=False)
        return res
    if p_declines == "F" and p_reversed == "F" and p_flat == "F":
        # every reading set out: not resolved as the rule words it, reported descriptively, routes as 'neither'
        res.update(base_keys, reading=_ruled_out_all(res["reading"], "top minus bottom rung", tmb), reversed=False,
                   resolved=False, attribution="", missed_effects="", missed_recognition="")
        return res
    res.update(base_keys, reading=_not_resolved(res["reading"], "top minus bottom rung"
                                                + (" and bottom minus middle rung" if mid is not None else ""),
                                                tmb), reversed=False, resolved=False, attribution="",
               missed_effects="", missed_recognition="")
    return res


def _test_T3_point(fidelity_by_struct, effect_classes=None, recog_by_struct=None, raw=None):
    """T3 (supporting): does fidelity change down the argument-strength ladder? Reads the registered
    anchor rungs: attraction (FRQ, RNG) at the top, compromise (SOT) in the middle, extremity (MOT) at
    the bottom. Since 2026-09-29 each rung is the combined group fidelity of the effect's POOLED
    estimate (it was the tier-1 cell, where five of the seven compromise cells are descriptive).
      declines  top minus bottom above 0.30 -> reason-construction;
      reversed  (2026-09-29) bottom above BOTH the top and the middle rung by more than 0.30, i.e.
                fidelity lower where the set offers a statable argument and higher where it offers
                none -> evidence AGAINST reason-construction. Attribution by the knows-it-versus-shows-it
                test on the effects the model misses (attraction or compromise classed LOW or ANTI):
                recognition at or above the registered cutoff on every one of them -> rational override
                on choice sets that offer an argument; otherwise -> a divergence with no account
                attributed;
      flat      |top minus bottom| below 0.12 -> the ladder gives the account no support;
      otherwise non-monotone or shallow -> reported descriptively, no registered reading."""
    effect_classes = effect_classes or {}
    recog_by_struct = recog_by_struct or {}
    high = [fidelity_by_struct[s] for s in LADDER_TOP if fidelity_by_struct.get(s) is not None]
    low = fidelity_by_struct.get(LADDER_BOTTOM)
    mid = fidelity_by_struct.get(LADDER_MIDDLE)
    base = dict(reversed=False, attribution="", missed_effects="", missed_recognition="")
    if not high or low is None:
        return dict(reading="insufficient rungs", high_rung=None, mid_rung="", low_rung=low, **base)
    h = sum(high) / len(high)
    step = RC.T3_LADDER_STEP
    # the directional guard (UNDERSHOOT_NOTE): a decline needs the bottom rung to undershoot; a reversal
    # needs the top rungs (and the middle one when present) to undershoot.
    top_under = raw is None or all(_undershoots(raw, s) for s in LADDER_TOP if fidelity_by_struct.get(s) is not None)
    mid_under = raw is None or mid is None or _undershoots(raw, LADDER_MIDDLE)
    # what a reversed reading would attribute (computed always, so an open reversed reading carries it)
    missed = [st for st in ARGUABLE_ANCHORS if effect_classes.get(st) in ("LOW", "ANTI")]
    rec = {st: recog_by_struct.get(st, 0.0) for st in missed}
    recognized = bool(missed) and all(v >= RC.RECOGNITION_CUTOFF for v in rec.values())
    rev_base = dict(reversed=True, attribution=(ARGUMENT_OVERRIDE if recognized else "no account attributed"),
                    missed_effects=";".join(missed),
                    missed_recognition=";".join(f"{k}={round(v, 3)}" for k, v in rec.items()))
    rev_reading = ("reversed ladder: fidelity rises down the ladder -> evidence against reason-construction; "
                   + ("recognized on every missed attraction or compromise effect -> " + ARGUMENT_OVERRIDE
                      if recognized else "not recognized on the missed effects -> divergence, no account attributed"))
    if h - low > step and not _undershoots(raw, LADDER_BOTTOM):
        reading = "non-monotone or shallow: " + UNDERSHOOT_NOTE
    elif h - low > step:
        reading = "declines down the ladder -> reason-construction (S3)"
    elif (low - h > step) and (mid is None or low - mid > step) and not (top_under and mid_under):
        reading = "non-monotone or shallow: " + UNDERSHOOT_NOTE
    elif (low - h > step) and (mid is None or low - mid > step):
        reading = rev_reading
        base = dict(rev_base)
    elif abs(h - low) < RC.T3_LADDER_FLAT:
        reading = "flat: pattern mimicry at depth, ladder gives the account no support"
    else:
        reading = "non-monotone or shallow: flagged, reported descriptively, no registered reading"
    return dict(reading=reading, high_rung=round(h, 3), mid_rung=(round(mid, 3) if mid is not None else ""),
                low_rung=round(low, 3), _top_minus_bottom=h - low,
                _bottom_minus_middle=(low - mid if mid is not None else None),
                _guard_declines=_undershoots(raw, LADDER_BOTTOM), _guard_reversed=(top_under and mid_under),
                _reversed_reading=rev_reading, _reversed_base=rev_base, **base)


def test_T4_formats(fidelity_by_format, undefined=None, raw=None, diff_ci=None, resolve=False):
    """T4: does fidelity fall from numbers to pictures? Under DESCRIPTIVE_T4, the difference and its 95
    percent interval are reported with no reading and T4 decides no scenario; the readings below remain only for
    DESCRIPTIVE_T4 = False.
    fidelity_by_format maps format -> group fidelity on the MATCHED format-module slices (the numbers
    value is computed on the pictures categories). undefined: {format: reason}
    for a format whose human effect is under 2 points (or whose numbers counterpart is); such a format
    has no registered reading, and when it is pictures (or the numbers counterpart), T4 is reported
    descriptively."""
    undefined = undefined or {}
    num = fidelity_by_format.get("numbers")
    pic = fidelity_by_format.get("pictures")
    wor = fidelity_by_format.get("words")
    note = "; ".join(f"{f}: {why}" for f, why in sorted(undefined.items()))
    fixed = dict(p_falls="F", p_flat="F", resolved=True, diff_lo="", diff_hi="")
    if "pictures" in undefined or "numbers" in undefined:
        return dict(reading="descriptive: a human effect under 2 points, so no fidelity difference is computed for "
                            "that format (" + note + ")", numbers=num, words=wor, pictures=pic, undefined=note,
                    **fixed)
    if num is None or pic is None:
        return dict(reading="insufficient formats", numbers=num, words=wor, pictures=pic, undefined=note, **fixed)
    d = num - pic
    guard = _undershoots(raw, "pictures")
    if d > T4_PRE_ROUND5_DROP and not guard:
        point = "shallow or reversed: " + UNDERSHOOT_NOTE
    elif d > T4_PRE_ROUND5_DROP:
        point = "falls numbers->pictures -> text-bound argument reading (S3 confirmatory)"
    elif abs(d) < T4_PRE_ROUND5_FLAT:
        point = "flat across formats -> representation-general simulation"
    elif pic > num:
        point = "higher in pictures than in numbers: reported descriptively"
    else:
        point = "shallow decline: reported descriptively"
    out = dict(numbers=round(num, 3), words=(round(wor, 3) if wor is not None else ""), pictures=round(pic, 3),
               undefined=note, diff_lo="", diff_hi="", point_reading=point)
    if DESCRIPTIVE_T4:
        # T4 is descriptive only. The difference numbers minus pictures
        # and its 95 percent interval are reported; there is no reading, and T4 decides no scenario.
        have = _ci_have(diff_ci)
        lo, hi = (diff_ci if have else (None, None))
        text = (f"descriptive: numbers minus pictures {d:+.3f}"
                + (f" (95 percent interval {_ci_end(lo)} to {_ci_end(hi)})" if have else "")
                + "; no registered reading, decides no scenario")
        return dict(out, reading=text, point_reading=text, diff_lo=_ci_end(lo), diff_hi=_ci_end(hi), p_falls="F",
                    p_flat="F", resolved=True)
    if not resolve:
        return dict(out, reading=point, p_falls=("T" if point.startswith("falls") else "F"),
                    p_flat=("T" if point.startswith("flat") else "F"), resolved=True)
    # rule 1: falls needs the interval of numbers minus pictures above the flat cutoff (0.12); flat
    # needs that interval below the directional cutoff (0.30).
    have = _ci_have(diff_ci)
    lo, hi = (diff_ci if have else (None, None))
    p_falls = _tfu(have and d > T4_PRE_ROUND5_DROP and guard and lo > T4_PRE_ROUND5_FLAT,
                   (not guard) or (have and hi <= T4_PRE_ROUND5_DROP))
    p_flat = _tfu(have and abs(d) < T4_PRE_ROUND5_FLAT and hi < T4_PRE_ROUND5_DROP,
                  have and (lo >= T4_PRE_ROUND5_FLAT or hi <= -T4_PRE_ROUND5_FLAT))
    if p_falls == "T" or p_flat == "T":
        reading = point
    elif p_falls == "F" and p_flat == "F":
        reading = _ruled_out_all(point if not (point.startswith("falls") or point.startswith("flat"))
                                 else ("higher in pictures than in numbers: reported descriptively" if d < 0
                                       else "shallow decline: reported descriptively"),
                                 "numbers minus pictures", diff_ci)
    else:
        reading = _not_resolved(point, "numbers minus pictures", diff_ci)
    return dict(out, reading=reading, diff_lo=_ci_end(lo), diff_hi=_ci_end(hi), p_falls=p_falls, p_flat=p_flat,
                resolved=not reading.startswith(NOT_RESOLVED))


def test_T5_trajectory(fidelity_old, fidelity_new, reasoning_on=None, reasoning_off=None, traj_ci=None,
                       reason_ci=None, resolve=False):
    """T5: older vs newer generation, plus reasoning on/off. Positive = newer more faithful (rising).
    With resolve=True each reading is resolved against the 95 percent interval of its
    difference (traj_ci: newer minus older; reason_ci: the lower minus the higher reasoning setting):
    rising (falling) needs the difference and the whole interval above 0.15 (below -0.15); flat needs the
    difference and the whole interval within 0.15; reasoning lowers fidelity when the difference and the whole
    interval exceed 0.15, and has no clear effect when both lie at or below 0.15; otherwise not resolved."""
    step = RC.T5_TRAJECTORY_STEP
    p_rising = p_falling = p_flat = "F"
    tlo = thi = rlo = rhi = None
    point = "insufficient generations"
    if fidelity_old is None or fidelity_new is None:
        traj = "insufficient generations"
        delta = ""
    else:
        delta = fidelity_new - fidelity_old
        if delta > step:
            point = "newer more faithful -> fidelity rises with capability (today's map is a floor)"
        elif delta < -step:
            point = "newer less faithful -> fidelity is not a free byproduct of capability"
        else:
            point = "flat across generations -> capability gains do not buy simulation validity"
        if not resolve:
            traj = point
            p_rising = "T" if delta > step else "F"
            p_falling = "T" if delta < -step else "F"
            p_flat = "T" if abs(delta) <= step else "F"
        else:
            have = _ci_have(traj_ci)
            tlo, thi = (traj_ci if have else (None, None))
            p_rising = _tfu(have and delta > step and tlo > step, have and thi <= step)
            p_falling = _tfu(have and delta < -step and thi < -step, have and tlo >= -step)
            p_flat = _tfu(have and abs(delta) <= step and tlo >= -step and thi <= step,
                          have and (tlo > step or thi < -step))
            traj = point if "T" in (p_rising, p_falling, p_flat) else _not_resolved(point, "newer minus older",
                                                                                    traj_ci)
    reasoning_reading = ""
    if reasoning_on is not None and reasoning_off is not None:
        r = reasoning_off - reasoning_on
        rstep = RC.T5_REASONING_STEP
        rpoint = ("reasoning-on lowers fidelity -> deliberation toward 'correct' answers (links T2)"
                  if r > rstep else "reasoning toggle: no clear effect")
        if not resolve:
            reasoning_reading = rpoint
        else:
            rhave = _ci_have(reason_ci)
            rlo, rhi = (reason_ci if rhave else (None, None))
            if rhave and r > rstep and rlo > rstep:
                reasoning_reading = rpoint
            elif rhave and r <= rstep and rhi <= rstep:
                reasoning_reading = rpoint
            else:
                reasoning_reading = _not_resolved(rpoint, "the lower minus the higher reasoning setting", reason_ci)
    return dict(trajectory=traj, delta=(round(delta, 3) if delta != "" else ""), point_trajectory=point,
                reasoning_reading=reasoning_reading, traj_lo=_ci_end(tlo), traj_hi=_ci_end(thi),
                reason_lo=_ci_end(rlo), reason_hi=_ci_end(rhi), p_rising=p_rising, p_falling=p_falling,
                p_flat=p_flat, resolved=not traj.startswith(NOT_RESOLVED))


def group_fold_reps(members):
    """Replicates of a group's combined fidelity under the joint bootstrap.
    members: list of (sign, model_reps, human_reps), one per cell the POINT estimate scores (membership and each
    cell's sign are fixed by the point: a scored class and a human effect of at least 2 points, sign = the
    human effect's sign), reps as lists of equal length. Replicate b is combine(sum s*m_b / sum s*h_b), the point's
    formula on the resampled effects; it is None (undefined) where the resampled human effects project to zero
    or below. Returns None when members is empty or any member lacks replicates."""
    if not members or any(mr is None or hr is None for _, mr, hr in members):
        return None
    n = len(members[0][1])
    num = [0.0] * n
    den = [0.0] * n
    for s, mr, hr in members:
        num = [a + s * x for a, x in zip(num, mr)]
        den = [a + s * x for a, x in zip(den, hr)]
    return [(_fold(a / d) if d > 0 else None) for a, d in zip(num, den)]


def diff_reps(a, b):
    """Replicate-wise a minus b (None where either is undefined); None when either list is missing."""
    if a is None or b is None:
        return None
    return [(x - y if x is not None and y is not None else None) for x, y in zip(a, b)]


def mean_reps(lists):
    """Replicate-wise mean of several replicate lists (None where any is undefined)."""
    if not lists or any(x is None for x in lists):
        return None
    return [(None if any(v is None for v in vs) else sum(vs) / len(vs)) for vs in zip(*lists)]


def rep_interval(reps):
    """The 95 percent resolution interval of a replicate list (call_bootstrap.interval, conservative about
    undefined replicates); None when there are no replicates (the bootstrap was not run)."""
    if not reps:
        return None
    return call_bootstrap.interval(reps, RC.BOOTSTRAP_LEVEL)


def test_T1_sensitivity(slice_cells, design, t1_primary, resolve=False):
    """The registered memorization sensitivity analysis (2026-09-29). The published tier carries its
    published baselines (several between 64 and 80 percent) and sparse text, while tiers 2 and 3 were
    calibrated toward 40 to 45 percent and enriched, so the registered gradient mixes novelty with
    baseline position. Two re-readings, the registered test itself unchanged:
      (a) RESTRICTED: the same pooled-per-tier fidelity, using only slices whose measured calibration
          baseline lies inside the 25-75 hard limits;
      (b) RESTRICTED AND ADJUSTED: a weighted regression across those slices of slice fidelity on the
          memorization tier, the slice's baseline distance from 50 percent, and the decoy-target identity, weights = the slice's summed human effect sizes; the
          adjusted drop is minus the tier coefficient times the tier span. The identity is a yes-or-no fact of the
          category-tier cell: 1 when its attraction decoys (frequency, range, phantom, which share one
          target per cell) target the budget option, else 0 (0 on every published-tier cell). A covariate
          that does not vary across the slices (no identity information) is left out, and the output
          says so.
    slice_cells: list of dict(category, tier, structure, human_pp, model_pp, w, slice_budget) for the
    non-similarity effects that passed the human criterion (slice_budget, or failing it budget_target,
    defaults to False)."""
    kept = [c for c in slice_cells if not design.outside_hard_limits((c["category"], c["tier"], "numbers"))]
    # the re-readings compare the tiers on the same categories,
    # as the registered test does: a category leaves both of the compared tiers of an effect when either tier's slice
    # is out (the invented tier has its own categories and is never paired; the pipeline no longer passes it)
    tiers_in = {c["tier"] for c in slice_cells} & set(T1_TIERS)
    on = defaultdict(set)
    for c in kept:
        on[(c["structure"], str(c["category"]))].add(c["tier"])
    kept = [c for c in kept if c["tier"] not in T1_TIERS or on[(c["structure"], str(c["category"]))] >= tiers_in]
    # rule 1: each slice may carry replicates of its model and human effects (mr, hr, proportions)
    # from the joint bootstrap; with resolve=True both re-readings are resolved against their intervals.
    has_reps = bool(kept) and all(c.get("mr") is not None and c.get("hr") is not None for c in kept)
    B = len(kept[0]["mr"]) if has_reps else 0
    # (a) pooled per tier over in-limit slices (pool model and human effects within tier first, the
    # registered T1 construction, so a noisy single slice cannot dominate).
    raw_by_tier = {}
    by_tier = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0.0, None, None]))
    for c in kept:
        acc = by_tier[c["tier"]][c["structure"]]
        acc[0] += c["w"] * c["human_pp"]
        acc[1] += c["w"] * c["model_pp"]
        acc[2] += c["w"]
        if has_reps:
            if acc[3] is None:
                acc[3], acc[4] = [0.0] * B, [0.0] * B
            acc[3] = [a + c["w"] * 100.0 * x for a, x in zip(acc[3], c["hr"])]
            acc[4] = [a + c["w"] * 100.0 * x for a, x in zip(acc[4], c["mr"])]
    cells_by_tier, reps_by_tier = {}, {}
    for tier, per_st in by_tier.items():
        cells, members = [], []
        for st, (hs, ms, ws, hrep, mrep) in per_st.items():
            if ws <= 0:
                continue
            h, m = hs / ws, ms / ws
            cls = "n/a" if abs(h) < NEAR_NULL_HUMAN * 100 else "scored"
            cells.append(dict(human_pp=h, model_pp=m, **{"class": cls}))
            if cls == "scored" and has_reps:
                members.append((1.0 if h > 0 else -1.0, [x / ws for x in mrep], [x / ws for x in hrep]))
        r = fidelity_ratio_for(cells)
        if r is not None:
            cells_by_tier[tier] = r
            raw_by_tier[tier] = group_ratio_raw(cells)
            reps_by_tier[tier] = group_fold_reps(members) if has_reps else None
    present = sorted(cells_by_tier)
    drop_ci = (rep_interval(diff_reps(reps_by_tier[present[0]], reps_by_tier[present[-1]]))
               if has_reps and len(present) >= 2 else None)
    # the undershoot guard (F12) holds for the re-readings too: a steep
    # reading needs the last tier's unfolded value below 1, here and in the adjusted regression below.
    t1_r = test_T1_memorization(cells_by_tier, raw_by_tier, drop_ci=drop_ci, resolve=resolve)
    last_under = _undershoots(raw_by_tier, present[-1]) if present else True
    # (b) slice-level weighted regression with the baseline distance and the decoy-target identity.
    per_slice = defaultdict(lambda: [0.0, 0.0, 0.0, None, None])
    for c in kept:
        h = c["human_pp"]
        if abs(h) < NEAR_NULL_HUMAN * 100:
            continue
        acc = per_slice[(c["category"], c["tier"])]
        s = 1.0 if h > 0 else -1.0
        acc[0] += c["model_pp"] * s
        acc[1] += abs(h)
        # the cell's decoy-target identity: 1 when the cell's attraction
        # decoys target the budget option, else 0.
        if c.get("slice_budget", c.get("budget_target")):
            acc[2] = 1.0
        if has_reps:
            if acc[3] is None:
                acc[3], acc[4] = [0.0] * B, [0.0] * B
            acc[3] = [a + s * 100.0 * x for a, x in zip(acc[3], c["mr"])]     # numerator replicates
            acc[4] = [a + s * 100.0 * x for a, x in zip(acc[4], c["hr"])]     # denominator replicates
    rowsx, Y, W, NUMR, DENR = [], [], [], [], []
    for (cat, tier), (num, den, bud, numr, denr) in sorted(per_slice.items(),
                                                           key=lambda kv: (str(kv[0][0]), kv[0][1])):
        b = design.baseline_pct.get((cat, tier, "numbers"))
        if den <= 0 or b is None:
            continue
        rowsx.append((float(tier), abs(b - 50.0), bud))
        Y.append(_fold(num / den))
        W.append(den)
        NUMR.append(numr)
        DENR.append(denr)

    def _varies(j):
        vals = [r[j] for r in rowsx]
        return len(vals) > 0 and (max(vals) - min(vals)) > 1e-12
    use = [j for j in (1, 2) if _varies(j)]          # covariates that carry information
    X = [[1.0, r[0]] + [r[j] for j in use] for r in rowsx]
    omitted = [name for j, name in ((1, "baseline distance"), (2, "decoy-target identity")) if j not in use]
    coef = (statlib.wls(X, Y, W) if len(X) >= 3 + len(use) and len({x[1] for x in X}) >= 2 else None)
    if coef is None:
        adj = dict(adjusted_slope="", adjusted_drop="", baseline_coef="", target_coef="", n_slices=len(X),
                   covariates_omitted=";".join(omitted),
                   adjusted_reading="insufficient slices for the adjusted regression")
    else:
        b_tier = coef[1]
        b_base = coef[2 + use.index(1)] if 1 in use else ""
        b_targ = coef[2 + use.index(2)] if 2 in use else ""
        span = max(r[0] for r in rowsx) - min(r[0] for r in rowsx)
        drop = -span * b_tier
        what = "baseline position and decoy-target identity"
        if drop > RC.T1_STEEP_DROP and not last_under:
            rd = "shallow or rising after adjustment: " + UNDERSHOOT_NOTE
        elif drop > RC.T1_STEEP_DROP:
            rd = f"steep after restricting to in-limit baselines and adjusting for {what}"
        elif abs(b_tier) < RC.T1_FLAT_SLOPE:
            rd = f"flat after restricting to in-limit baselines and adjusting for {what}"
        else:
            rd = "shallow or rising after adjustment: reported descriptively"
        adj_ci = None
        if resolve:
            # the adjusted drop recomputed on every joint-bootstrap replicate: the slice ratios, their weights
            # (the slice's summed human effects) and the fit, with the slices and covariates of the point fit.
            if has_reps and all(r is not None for r in NUMR):
                reps = []
                for bi in range(B):
                    yb, wb, ok = [], [], True
                    for nr_, dr_ in zip(NUMR, DENR):
                        if dr_[bi] <= 0:
                            ok = False
                            break
                        yb.append(_fold(nr_[bi] / dr_[bi]))
                        wb.append(dr_[bi])
                    cb = statlib.wls(X, yb, wb) if ok else None
                    reps.append(-span * cb[1] if cb is not None else None)
                adj_ci = rep_interval(reps)
            p_steep, p_flat = _drop_states(drop, b_tier, adj_ci, span, last_under)
            if p_steep == "F" and p_flat == "F":
                rd = _ruled_out_all(rd, "the adjusted drop", adj_ci)
            elif p_steep != "T" and p_flat != "T":
                rd = _not_resolved(rd, "the adjusted drop", adj_ci)
        adj = dict(adjusted_slope=round(b_tier, 3), adjusted_drop=round(drop, 3),
                   adjusted_drop_lo=(_ci_end(adj_ci[0]) if _ci_have(adj_ci) else ""),
                   adjusted_drop_hi=(_ci_end(adj_ci[1]) if _ci_have(adj_ci) else ""),
                   baseline_coef=(round(b_base, 4) if b_base != "" else ""),
                   target_coef=(round(b_targ, 4) if b_targ != "" else ""), n_slices=len(X),
                   covariates_omitted=";".join(omitted), adjusted_reading=rd)
    return dict(primary_reading=t1_primary["reading"], restricted_reading=t1_r["reading"],
                restricted_drop=t1_r.get("drop", ""), restricted_drop_lo=t1_r.get("drop_lo", ""),
                restricted_drop_hi=t1_r.get("drop_hi", ""), restricted_slope=t1_r.get("slope", ""),
                n_slices_dropped=len({(c["category"], c["tier"]) for c in slice_cells}) -
                                 len({(c["category"], c["tier"]) for c in kept}),
                **adj)


# ===================================================================================================
# THE TREE ROUTER -- applies precedence and attributes accounts PER EFFECT, ending at a scenario.
# ===================================================================================================
def effect_level_classes(scored_cells):
    """LEGACY (per-tier cells): collapse a model's scored cells to one class per effect by majority.
    Since 2026-09-29 the registered class per effect is computed on the effect's POOLED
    estimate in build_pack; this helper remains for callers that hold only per-tier cells."""
    by_struct = defaultdict(list)
    for c in scored_cells:
        by_struct[c["structure"]].append(c["class"])
    out = {}
    for st, classes in by_struct.items():
        cls = majority_class(classes)
        if cls != "n/a":
            out[st] = cls
    return out


def overall_class(effect_classes, criterion):
    """rule 3: a model's overall class is its most frequent class across the six non-similarity
    effects that passed the human criterion (ties by the registered alphabetical rule)."""
    return majority_class([effect_classes.get(st) for st in REGULARITY_EFFECTS
                           if criterion[st].get("confirmatory", criterion[st]["replicated"])
                           and effect_classes.get(st) is not None])


def route_model(model, scored_cells, t1, t2_override, t3, t4, t5, gate_info, agree,
                family_consistent, family_rising, effect_classes=None, overall=None):
    """Route one model's outcome to a decision-tree branch, ending at a named scenario or an
    individual-reading composite. Applies the registered precedence rules:
      (1) a steep T1 gradient overrides T3 (recitation shaped like reasoning), including a reversed
          ladder;
      (2) T2 recognizes-but-does-not-show overrides the magnitude (fidelity-class) readings; a reversed
          ladder whose missed effects are all recognized is the more specific form of this override
          and is read first.
    effect_classes / overall: the pooled per-effect classes and the overall class; when not
    given (legacy callers) they are derived from the per-tier cells and agree.
    A pattern-test reading marked uninformative starts with
    'uninformative' and so triggers no branch.
    Returns (branch_label, scenario)."""
    if gate_info["not_assessable"]:
        return ("Step 0b: model loses >1/3 cells or fails parse/refusal -> not assessable", "CRITERION_FAIL")
    dom = overall if overall is not None else agree["dominant_class"]
    t1_steep = t1["reading"].startswith("steep")
    t3_declines = t3["reading"].startswith("declines")
    t3_reversed = bool(t3.get("reversed"))
    # Reversed ladder with recognition on every missed attraction or compromise effect (2026-09-29).
    if t3_reversed and not t1_steep and t3.get("attribution") == ARGUMENT_OVERRIDE:
        return ("T3 reversed ladder + recognition on every missed attraction or compromise effect -> "
                + ARGUMENT_OVERRIDE + " (evidence against reason-construction)",
                "REVERSED_LADDER_OVERRIDE")
    # Precedence (2): rational override (this model's own behavior takes precedence even in a family).
    if t2_override and dom in ("LOW", "ANTI"):
        return ("T2 recognizes-but-does-not-show overrides magnitude -> rational override", "S4")
    # Precedence (1): steep memorization gradient sets the headline over T3.
    if t1_steep:
        return ("T1 steep gradient (overrides T3) -> fidelity only on classic tier", "S2")
    # S6 (Rising fidelity) before S1/S5: a rising family is a trajectory story.
    if family_rising:
        return ("PARTIAL/HIGH today + rising T5 across the family generations", "S6")
    # S5 (Family-specific): family-specific patterns that are not a clean generation improvement.
    if not family_consistent:
        return ("family-specific patterns -> per-model validation only", "S5")
    # Reversed ladder without recognition: read before S1, because a model faithful on the argument-free
    # effects and missing the arguable ones can carry a HIGH majority class without being faithful.
    if t3_reversed:
        return ("T3 reversed ladder, not recognized on the missed effects -> evidence against "
                "reason-construction; divergence reported with no account attributed", "REVERSED_LADDER")
    # Faithful everywhere. Under registered rule (a), S1 no longer needs a flat
    # memorization reading, only the absence of a steep one (and of a ladder decline).
    if (dom == "HIGH" and not t1_steep and not t2_override and not t3_declines
            and not any(str(t.get("reading", "")).startswith("uninformative") for t in (t1, t3))):
        return ("HIGH + no steep T1 + shows-without-recognizing", "S1")
    # S3 (Reason construction): a decline down the argument-strength ladder.
    if t3_declines:
        return ("T3 decline down the argument-strength ladder -> reason-construction", "S3")
    # PARTIAL fidelity at the MODEL level: faithful on some effects, reversed or low on others.
    eff_classes = effect_classes if effect_classes is not None else effect_level_classes(scored_cells)
    faithful_effects = [st for st, c in eff_classes.items() if c == "HIGH"]
    reversed_low_effects = [st for st, c in eff_classes.items() if c in ("ANTI", "LOW")]
    if faithful_effects and reversed_low_effects:
        return ("mixed at the effect level: faithful on some effects, reversed or low on others "
                "-> PARTIAL fidelity (per-effect accounts side by side)", "PARTIAL")
    if dom == "PARTIAL" and t5["trajectory"].startswith("newer more faithful"):
        return ("PARTIAL today + rising T5", "S6")
    if dom == "ANTI":
        return ("ANTI class without recognition override -> systematic inversion", "S4")
    return (f"individual-reading composite (dominant {dom})", "COMPOSITE")


# one qualifier, covering whichever pattern tests are open
S1_QUALIFIER = "pattern tests not resolved at the design's resolution"


def _uninf(t, key="reading"):
    return str(t.get(key, "")).startswith("uninformative")


def route_resolved(model, scored_cells, t1, t2_override, t3, t4, t5, gate_info, agree, family_consistent,
                   family_has_generations, effect_classes=None, overall=None, t2_state=None, open_blocks="any",
                   s1_point_guard=True):
    """The router with interval-resolved readings (the second revision, rule 1, as amended by the authors'
    rules (a) and (b)). It walks the registered precedence order of route_model:
      - A route that attributes an account is STRICT: it is taken only when its own reading is
        resolved in its favour (T). When its own reading is open (U), the route is blocked: it is not taken and no
        later route may be taken either, except S1, which
        only the earlier guard below withholds (and then leaves possible, with every account left open). When
        its own reading is set out (F), the walk goes on. A resolved steep memorization reading excludes both
        reversed ladders; an open one blocks them (the steep reading would take precedence if resolved).
      - S1 (High fidelity) needs the HIGH overall class, the effects shown without recognition as registered (the
        knows-it-versus-shows-it reading at the point), and NO resolved steep memorization reading, reversed ladder
        or ladder decline. An open reading blocks it only when that reading's estimate
        points to an account (a steep gradient, a reversed ladder, a ladder decline, a rise across generations; round
        4 adopted this
        guard). When any pattern test is not resolved, S1 carries the one qualifier "pattern tests not resolved at
        the design's resolution" and the open tests are listed.
      - The class- and family-based routes (family-specific S5, PARTIAL, systematic inversion, COMPOSITE) read no
        interval; they are taken unless a blocked route precedes them, in which case the model is NOT_RESOLVED
        with the blocked scenarios and this one left possible.
    t2_state: the model-level state of the knows-it-versus-shows-it override ('T', 'F' or 'U'; see
    t2_override_state); None falls back to the point flag (legacy callers).
    open_blocks and s1_point_guard: the registered rule is the default; the other values exist for the design comparisons of the stability sweep only
    (open_blocks="favoured" lets an open account reading block later routes only when its point estimate favours the
    route; s1_point_guard=False never withholds S1 for an open reading).
    Returns (branch, scenario, the scenarios left possible)."""
    if gate_info["not_assessable"]:
        return ("Step 0b: model loses >1/3 cells or fails parse/refusal -> not assessable", "CRITERION_FAIL", ["CRITERION_FAIL"])
    dom = overall if overall is not None else agree["dominant_class"]

    def state(t, key, text_key, prefix):
        if _uninf(t, text_key):
            return "F"
        if key in t:
            return t[key]
        return "T" if str(t.get(text_key, "")).startswith(prefix) else "F"

    def favours(t, text_key, point_key, prefix):
        if _uninf(t, text_key):
            return False
        return str(t.get(point_key, t.get(text_key, ""))).startswith(prefix)

    s_steep = state(t1, "p_steep", "reading", "steep")
    f_steep = favours(t1, "reading", "point_reading", "steep")
    s_rev = state(t3, "p_reversed", "reading", "reversed")
    if "p_reversed" not in t3 and t3.get("reversed") and not _uninf(t3):
        s_rev = "T"
    f_rev = (not _uninf(t3)) and bool(t3.get("point_reversed", t3.get("reversed")))
    rev_attr = (t3.get("_reversed_base") or {}).get("attribution") or t3.get("attribution", "")
    # reason construction (S3) rests on a resolved decline down the argument-strength ladder; the
    # format test is descriptive and decides no scenario
    s_decl = state(t3, "p_declines", "reading", "declines")
    f_decl = favours(t3, "reading", "point_reading", "declines")
    s_rise = state(t5, "p_rising", "trajectory", "newer more faithful") if family_has_generations else "F"
    f_rise = family_has_generations and favours(t5, "trajectory", "point_trajectory", "newer more faithful")
    s_kws = t2_state if t2_state is not None else ("T" if t2_override else "F")
    f_kws = bool(t2_override)
    eff_classes = effect_classes if effect_classes is not None else effect_level_classes(scored_cells)
    faithful_effects = [st for st, c in eff_classes.items() if c == "HIGH"]
    reversed_low_effects = [st for st, c in eff_classes.items() if c in ("ANTI", "LOW")]

    # (scenario, branch, applies, strict, own state, point favours)
    steps = [
        ("REVERSED_LADDER_OVERRIDE",
         "T3 reversed ladder + recognition on every missed attraction or compromise effect -> "
         + ARGUMENT_OVERRIDE + " (evidence against reason-construction)",
         rev_attr == ARGUMENT_OVERRIDE and s_steep != "T", True,
         (s_rev if s_steep == "F" else ("U" if s_rev != "F" else "F")), f_rev),
        ("S4", "T2 recognizes-but-does-not-show overrides magnitude -> rational override",
         dom in ("LOW", "ANTI"), True, s_kws, f_kws),
        ("S2", "T1 steep gradient (overrides T3) -> fidelity only on classic tier", True, True, s_steep, f_steep),
        ("S6", "PARTIAL/HIGH today + rising T5 across the family generations", bool(family_has_generations), True,
         s_rise, f_rise),
        ("S5", "family-specific patterns -> per-model validation only", not family_consistent, False, "T", True),
        ("REVERSED_LADDER", "T3 reversed ladder, not recognized on the missed effects -> evidence against "
         "reason-construction; divergence reported with no account attributed", rev_attr != ARGUMENT_OVERRIDE, True,
         s_rev, f_rev),
        # S1 under rule (a); a failed positive control leaves the pattern tests uninformative and S1 is not
        # claimed
        ("S1", "", dom == "HIGH" and not t2_override and s_steep != "T" and s_decl != "T" and s_rev != "T"
         and not (_uninf(t1) or _uninf(t3)),
         False, "T", True),
        ("S3", "T3 resolved decline down the argument-strength ladder -> reason-construction (the format test, T4, "
         "reported beside it, descriptive)", True, True, s_decl, f_decl),
        ("PARTIAL", "mixed at the effect level: faithful on some effects, reversed or low on others -> PARTIAL "
         "fidelity (per-effect accounts side by side)", bool(faithful_effects and reversed_low_effects), False, "T",
         True),
        ("S6", "PARTIAL today + rising T5", dom == "PARTIAL" and bool(family_has_generations), True, s_rise, f_rise),
        ("S4", "ANTI class without recognition override -> systematic inversion", dom == "ANTI", False, "T", True),
        ("COMPOSITE", f"individual-reading composite (dominant {dom})", True, False, "T", True),
    ]
    blocked = []
    for scen, branch, applies, strict, own, fav in steps:
        if not applies:
            continue
        if scen == "S1":
            # the earlier guard: an open reading whose estimate points to an account withholds S1; the model is
            # NOT_RESOLVED between S1 (the open readings resolve against their accounts) and those accounts. The
            # accounts before S1 are already in `blocked`; reason construction (S3) comes after S1 and is added here
            # when its reading is open, on the same terms as the accounts before it (open_blocks).
            if s1_point_guard and ((s_steep == "U" and f_steep) or (s_rev == "U" and f_rev)
                                   or (s_decl == "U" and f_decl) or (s_rise == "U" and f_rise)):
                s3_open = s_decl == "U" and (f_decl or open_blocks == "any")
                return _blocked(blocked + (["S3"] if s3_open else []), "S1")
            # otherwise S1 is never blocked by an open reading (rule (a)); it carries the one qualifier and
            # names every pattern test that stays open
            open_tests = [n for n, t in (("T1", t1), ("T3", t3)) if not t.get("resolved", True) and not _uninf(t)]
            if family_has_generations and not t5.get("resolved", True) and not _uninf(t5, "trajectory"):
                open_tests.append("T5")
            lbl = "HIGH + no resolved steep T1, reversed ladder or ladder decline + shows-without-recognizing"
            if open_tests:
                lbl += "; qualifier: " + S1_QUALIFIER + " (open: " + ", ".join(open_tests) + ")"
            return lbl, "S1", ["S1"]
        if strict:
            if own == "T":
                if blocked:
                    return _blocked(blocked, scen)
                return branch, scen, [scen]
            if own == "U" and (fav or open_blocks == "any"):
                blocked.append(scen)
            continue
        if blocked:
            return _blocked(blocked, scen)
        return branch, scen, [scen]
    return _blocked(blocked, "COMPOSITE")


def _blocked(blocked, then):
    possible = sorted(set(blocked) | {then})
    if len(possible) == 1:
        # every way the open reading could resolve ends at the same scenario (for example rational override or
        # systematic inversion, both S4): the scenario stands, the account it rests on is reported as open
        return (f"{then}: reached whichever way the open reading resolves; the account it rests on is not resolved",
                then, possible)
    return ("not resolved: the estimates point to " + ", ".join(dict.fromkeys(blocked)) + ", whose reading the "
            "95 percent interval leaves open, so no later route is claimed; possible scenarios "
            + ", ".join(possible), NOT_RESOLVED_SCENARIO, possible)


# ===================================================================================================
# THE PER-EFFECT ACCOUNT ATTRIBUTION (accounts attach to EFFECTS, not models).
# ===================================================================================================
OVERSHOOT = "overshoot (same direction, above 150 percent of the human size)"
RETRIEVAL_READING = "consistent with retrieval of a described regularity"
OVER_PHANTOM = "overshoot on the phantom, " + RETRIEVAL_READING
ACCOUNT_FAMILY = {
    "deep pattern-mimicry": "deep pattern-mimicry",
    "rational-override": "rational override",
    "rational-override (reversal)": "rational override",
    "partial (direction transfers, size off)": "partial",
    "low fidelity": "low fidelity",
    OVERSHOOT: "overshoot",
    OVER_PHANTOM: "retrieval of a described regularity",
}


def attribute_effect_accounts(model, scored_cells, recog_by_struct, criterion, no_counterpart=None,
                              effect_classes=None, pooled=None, phantom_retrieval=False):
    """For each effect, attribute the account implicated, per the per-effect rule: a single model can
    fall under different accounts for different effects. Returns {struct: account}.

    effect_classes / pooled: the effect's class on its pooled estimate and the
    pooled (model_pp, human_pp); the model 'shows' the effect when its pooled effect exceeds 3 points in
    the human direction, the T2 rule. Without them (legacy callers) the per-tier cells are used.

    An effect that fails the human criterion exits fidelity scoring entirely (general rule, driven by the
    criterion result, not by any effect name). If the model nonetheless shows an effect larger than the
    registered minimum there, the account says so: an effect without a human counterpart."""
    no_counterpart = no_counterpart or set()
    out = {}
    by_struct = defaultdict(list)
    for c in scored_cells:
        by_struct[c["structure"]].append(c)
    for st in EFFECTS:
        if not criterion[st]["replicated"]:
            out[st] = ("human-null (exits fidelity scoring); model shows an effect without a human counterpart"
                       if st in no_counterpart else "human-null (exits fidelity scoring)")
            if st == "PHT" and phantom_retrieval:
                out[st] += "; " + RETRIEVAL_READING
            continue
        if effect_classes is not None:
            cls = effect_classes.get(st)
            if cls in (UNINFORMATIVE, DESCRIPTIVE_FLOOR):
                out[st] = cls
                continue
            if cls not in SCORED_CLASSES:
                out[st] = "not scorable"
                continue
            mp, hp = (pooled or {}).get(st, (0.0, 1.0))
            shows = round(mp * (1.0 if hp > 0 else -1.0), 9) > RC.ANTI_MIN_PP
        else:
            cs = [c for c in by_struct.get(st, []) if c["class"] not in NON_SCORED]
            if not cs:
                out[st] = "not scorable"
                continue
            cls = majority_class([c["class"] for c in cs])
            shows = any(c["model_pp"] > 0 and c["human_pp"] > 0 for c in cs)
        rec = recog_by_struct.get(st, 0.0)
        if rec >= RC.RECOGNITION_CUTOFF and not shows:
            out[st] = "rational-override"
        elif cls == "HIGH":
            out[st] = "deep pattern-mimicry"
        elif cls == "OVER":
            out[st] = OVER_PHANTOM if st == "PHT" else OVERSHOOT
        elif cls == "ANTI":
            out[st] = "rational-override (reversal)"
        elif cls == "PARTIAL":
            out[st] = "partial (direction transfers, size off)"
        else:
            out[st] = "low fidelity"
    return out


def model_level_account(accounts, criterion):
    """The registered model-level account rule (2026-09-29): an account is claimed for the MODEL only
    when the per-effect readings agree on at least four of the six non-similarity effects that passed
    the human criterion; otherwise accounts are reported per effect only.
    Returns (account or 'per-effect only', n_agreeing, n_eligible)."""
    eligible = [st for st in REGULARITY_EFFECTS if criterion[st].get("confirmatory", criterion[st]["replicated"])
                and accounts.get(st) in ACCOUNT_FAMILY]
    counts = Counter(ACCOUNT_FAMILY[accounts[st]] for st in eligible)
    if not counts:
        return "per-effect only", 0, len(eligible)
    best = max(sorted(counts), key=lambda k: counts[k])
    if counts[best] >= RC.MODEL_ACCOUNT_MIN_AGREE:
        return best, counts[best], len(eligible)
    return "per-effect only", counts[best], len(eligible)


# ===================================================================================================
# THE FORMAT MODULE'S HEADLINE TEST -- the human format-by-effect interaction.
# ===================================================================================================
def format_categories_for(rows, design, fmt, effect):
    """The categories a format comparison uses: those fielded in that format (tier 2), with, for the
    compromise, any category whose compromise cell is descriptive in either format removed, so the
    numbers comparison row always covers exactly the same categories as the format row."""
    cats = set(design.format_categories.get(fmt) or ())
    if not cats:
        idx = _index(rows)
        cats = {k[1] for k in idx if k[0] == effect and k[2] == FORMAT_TIER and k[3] == fmt}
    if effect == "SOT":
        cats = {c for c in cats if (c, FORMAT_TIER, fmt) not in design.compromise_descriptive
                and (c, FORMAT_TIER, "numbers") not in design.compromise_descriptive}
    return {c for c in cats if _in_scope(c, "backbone", design)}


def format_interaction_tests(human_rows, design=None):
    """The registered headline test of the format module: for attraction-frequency and compromise, does
    showing the attributes as words (or as pictures) change the HUMAN effect relative to numbers? The
    interaction is (effect in the format) minus (effect in numbers), on the same categories at tier 2;
    the two estimates come from different surveys, so their variances add. Holm across the four tests
    (FRQ and SOT, words and pictures) at family-wise .05. Returns {key: row}."""
    design = design or NULL_DESIGN
    tests, raw = {}, {}
    for st in FORMAT_EFFECTS:
        for fmt in FORMAT_SIDES:
            cats = format_categories_for(human_rows, design, fmt, st)
            if not cats:
                continue
            ef = human_contrast(human_rows, st, (FORMAT_TIER,), fmt, design, cats=cats)
            en = human_contrast(human_rows, st, (FORMAT_TIER,), "numbers", design, cats=cats)
            if ef["n_strata"] == 0 or en["n_strata"] == 0:
                continue
            inter = ef["delta"] - en["delta"]
            se = math.sqrt(ef["se"] ** 2 + en["se"] ** 2)
            z = inter / se if se > 0 else 0.0
            p = statlib.two_sided_p_from_z(z)
            lo, hi = statlib.ci(inter, se, 0.95)
            key = f"{st}:{fmt}"
            tests[key] = dict(test=key, effect=st, format=fmt, categories=";".join(sorted(cats)),
                              format_pp=round(ef["delta"] * 100, 2), numbers_pp=round(en["delta"] * 100, 2),
                              interaction_pp=round(inter * 100, 2), ci_lo_pp=round(lo * 100, 2),
                              ci_hi_pp=round(hi * 100, 2), z=round(z, 3), raw_p=p,
                              n_format=ef["n"], n_numbers=en["n"], _inter=inter)
            raw[key] = p
    holm = statlib.holm(raw, alpha=HOLM_ALPHA) if raw else {}
    for key, row in tests.items():
        _, adj, rej = holm[key]
        row["holm_p"] = round(adj, 5)
        row["raw_p"] = round(row["raw_p"], 5)
        row["significant"] = bool(rej)
        if not rej:
            row["reading"] = "no detectable format change in the human effect"
        elif row["_inter"] < 0:
            row["reading"] = f"{row['format']} weaken the human effect relative to numbers"
        else:
            row["reading"] = f"{row['format']} strengthen the human effect relative to numbers"
    return tests


# ===================================================================================================
# THE POSITIVE CONTROLS AND THE SIMILARITY TOP-UP CHECK.
# ===================================================================================================
def positive_control_check(human_rows, design, criterion, drop_by_effect=None):
    """The registered positive controls: the frequency-decoy cells whose target is the PREMIUM option
    (tested on those cells alone: predicted direction, significant at .05, Bayes factor above 3) and the
    compromise effect (its human replication criterion). Returns dict(frq_premium=..., sot=...,
    failed=[effects whose control failed]). A failed control makes that effect's fidelity-map row and
    every pattern-test reading that uses it uninformative (build_pack applies this)."""
    design = design or NULL_DESIGN
    drop_by_effect = drop_by_effect or {}
    c = human_contrast(human_rows, "FRQ", (1, 2, 3), "numbers", design, drop_by_effect.get("FRQ", ()), None,
                       "backbone", None, target_kind="HD")
    z = c["delta"] / c["se"] if c["se"] > 0 else 0.0
    p = statlib.two_sided_p_from_z(z)
    frq_holds = bool(c["n_strata"] > 0 and c["delta"] > 0 and p < RC.POSITIVE_CONTROL_ALPHA
                     and c["bf10"] > BF_GATE)
    sot_holds = bool(criterion["SOT"]["replicated"])
    failed = [st for st, ok in (("FRQ", frq_holds), ("SOT", sot_holds)) if not ok]
    return dict(frq_premium=dict(delta_pp=c["delta"] * 100, ci_lo_pp=c["ci_lo"] * 100, ci_hi_pp=c["ci_hi"] * 100,
                                 p=p, bf10=c["bf10"], n_strata=c["n_strata"], holds=frq_holds),
                sot=dict(delta_pp=criterion["SOT"]["delta_pp"], holds=sot_holds), failed=failed)


def topup_participants(rows):
    """The similarity top-up survey's participants: each makes seven similarity choices, while a
    backbone participant never meets the same structure twice, so any participant with two or more
    similarity rows is a top-up participant (identified from the data, not from a survey label)."""
    cnt = Counter(r["participant_id"] for r in rows if r["structure"] == "SIM")
    return {p for p, n in cnt.items() if n >= 2}


def similarity_topup_check(human_rows, design=None):
    """rule 10. The similarity effect estimated separately from backbone choices and from top-up
    choices, on the similarity slices both surveys fill, each against the same backbone binary control
    and with the same slice weights (the combined similarity choices per slice), so the control cancels
    in the difference. If the two differ by more than 5 points and the difference is significant at .05
    (cluster-robust, participant as cluster), the backbone estimate becomes the similarity benchmark.
    Returns a dict (fired=False with a note when no top-up choices exist)."""
    design = design or NULL_DESIGN
    tp = topup_participants(human_rows)
    strata, _ = _strata(human_rows, "SIM", "human", (1, 2, 3), "numbers", None, design, (), None, "backbone")
    use = []
    for key, t, c in strata:
        tb = [(pid, y) for pid, y in t if pid not in tp]
        tt = [(pid, y) for pid, y in t if pid in tp]
        if tb and tt and c:
            use.append((key, tb, tt, c))
    base = dict(n_topup_participants=len(tp), n_slices=len(use))
    if not use:
        return dict(fired=False, backbone_pp="", topup_pp="", diff_pp="", diff_se_pp="", z="", p="",
                    n_backbone=0, n_topup=0,
                    benchmark="core design and similarity supplement (no supplement choices found)",
                    topup_pids=tp, **base)
    W = sum(len(tb) + len(tt) for _, tb, tt, _ in use)
    bb_terms, tu_terms, diff_terms = [], [], []
    for _, tb, tt, c in use:
        w = (len(tb) + len(tt)) / W
        bb_terms += [(w, tb), (-w, c)]
        tu_terms += [(w, tt), (-w, c)]
        diff_terms += [(w, tt), (-w, tb)]
    bb, _, _ = statlib.weighted_linear_contrast(bb_terms)
    tu, _, _ = statlib.weighted_linear_contrast(tu_terms)
    d, se, _ = statlib.weighted_linear_contrast(diff_terms)
    z = d / se if se > 0 else 0.0
    p = statlib.two_sided_p_from_z(z)
    fired = bool(abs(d) * 100 > RC.SIM_TOPUP_MAX_GAP_PP and p < RC.SIM_TOPUP_ALPHA)
    return dict(fired=fired, backbone_pp=bb * 100, topup_pp=tu * 100, diff_pp=d * 100, diff_se_pp=se * 100,
                z=z, p=p, n_backbone=sum(len(tb) for _, tb, _, _ in use),
                n_topup=sum(len(tt) for _, _, tt, _ in use),
                benchmark=("core design only (the similarity supplement check fired)" if fired
                           else "core design and similarity supplement"),
                topup_pids=tp, **base)


CONFIRMATORY_ARMS = (None, "", "primary")


def split_arms(recs):
    """Review finding 10: run.py writes the reasoning-contrast and temperature arms with prompting_mode
    'neutral' too, so a log holding them would pool them into the confirmatory estimates. The confirmatory
    neutral records are the primary arm's (or records without an arm field); the reasoning-contrast arm's
    neutral records are returned apart for T5's reasoning reading; the temperature arms' are counted and
    left out (their readings are not part of this pipeline). Non-neutral records (persona, sequential,
    recognition) are kept. Returns (records for the pipeline, reasoning_on records, number left out)."""
    keep, reason, other = [], [], 0
    for r in recs:
        if r.get("prompting_mode") == "neutral" and r.get("arm") not in CONFIRMATORY_ARMS:
            if r.get("arm") == "reasoning_on":
                reason.append(r)
            else:
                other += 1
            continue
        keep.append(r)
    return keep, reason, other


def rerun_reproduces(deposited_pp, rerun_lo_pp, rerun_hi_pp):
    """The registered re-run rule: a re-run of the model calls
    reproduces a model effect when the deposited estimate lies inside the re-run's 95 percent bootstrap interval
    over calls (rerun_lo_pp and rerun_hi_pp are that interval's ends: the boot_lo_pp and boot_hi_pp of the same
    effect in the re-run's own pack, computed at BOOTSTRAP_LEVEL, which the module asserts equals RERUN_RULE)."""
    return rerun_lo_pp <= deposited_pp <= rerun_hi_pp


def _mark_uninformative(reading, failed):
    """rule 9: a pattern-test reading that uses an effect whose positive control failed."""
    return f"{UNINFORMATIVE} ({', '.join(failed)}); computed reading, not interpreted: {reading}"


def is_picture_order(rec):
    """Whether a model call showed the options in the canonical order, the one fixed order of the picture
    prompts (run.py: an order is a list of option indices, the canonical order is the identity; the
    synthetic generator writes its canonical order as 'o1')."""
    po = rec.get("position_order")
    if isinstance(po, (list, tuple)):
        return list(po) == list(range(len(po)))
    if isinstance(po, str):
        s = po.strip()
        if s.startswith("["):
            try:
                v = json.loads(s)
                return isinstance(v, list) and v == list(range(len(v)))
            except ValueError:
                return False
        return s == "o1"
    return False


def _budget_target(design, cat, tier, st):
    """Whether this effect's decoy target in this slice is the budget option: from stimuli.json when the
    design carries option identities; on the synthetic lattice from synth's decoy-target split."""
    if st not in DECOY_TARGET_EFFECTS:
        return False
    if design.has_identity:
        return design.target(cat, tier, st) == "HF"
    try:
        return synth.cat_decoy_target(int(cat)) == "HF"
    except (TypeError, ValueError):
        return False


# ===================================================================================================
# THE DRIVER -- builds the whole pack from a human dataset + a dict of model datasets.
# ===================================================================================================
def build_pack(human_rows, models, human_rows_with_formats=None, human_rows_first_trial=None,
               seed=0, runtime=0.0, mode="REHEARSAL", surprise_human_rows=None, design=None, bootstrap=True,
               keep_members=False):
    """Run the full pipeline and write the complete contract-C results pack. models is a dict
    {model_key: list-of-contract-B-records}. design is the Design index (stimuli.json for real data,
    Design.for_synth() for the rehearsal). bootstrap=False skips the bootstrap.
    Returns a big dict of everything computed."""
    design = design or NULL_DESIGN
    os.makedirs(PACK, exist_ok=True)
    os.makedirs(TESTS_DIR, exist_ok=True)
    os.makedirs(FIGS_DIR, exist_ok=True)
    numbers = {}
    hb_all = human_rows_with_formats or human_rows

    # The registered stimulus handling: compromise cells whose target starts ahead are descriptive only
    # (dropped from every confirmatory compromise contrast, human and model alike); the sensitivity set
    # drops every deviation-flagged slice for every effect as well.
    comp_desc = set(design.compromise_descriptive)
    drop_confirm = {"SOT": comp_desc}
    drop_sens = {st: set(design.deviation_slices) | (comp_desc if st == "SOT" else set()) for st in EFFECTS}

    # ---- Step 1, the similarity top-up check: backbone versus top-up similarity choices ----
    topup = similarity_topup_check(hb_all, design)
    ft_input = human_rows_first_trial or hb_all
    if topup["fired"]:
        # the backbone estimate becomes the similarity benchmark: top-up similarity rows leave every
        # human estimate (the first-trial check included).
        tpids = topup["topup_pids"]
        hb_all = [r for r in hb_all if not (r["structure"] == "SIM" and r["participant_id"] in tpids)]
        ft_input = [r for r in ft_input if not (r["structure"] == "SIM" and r["participant_id"] in tpids)]
    numbers["human.SIM.topup_check.fired"] = topup["fired"]
    numbers["human.SIM.topup_check.benchmark"] = topup["benchmark"]
    for k in ("backbone_pp", "topup_pp", "diff_pp", "diff_se_pp", "p"):
        v = topup[k]
        numbers[f"human.SIM.topup_check.{k}"] = round(v, 5) if isinstance(v, float) else v

    # ---- Step 1 first: the comparability check decides which benchmark the criterion reads ----
    ft = first_trial_check(ft_input, design, drop_confirm)
    fallback = ft["fired"]
    if fallback:
        # the first-trial estimates become the benchmark for the numeric backbone.
        hb_source = [r for r in hb_all if not (r["format"] == "numbers" and _in_scope(str(r["category"]), "backbone", design)
                                               and _int(r["trial_position"]) != 1)]
    else:
        hb_source = hb_all
    numbers["human.first_trial.fallback_triggered"] = bool(fallback)
    numbers["human.first_trial.fired_effects"] = ";".join(ft["fired_effects"])
    numbers["human.first_trial.confirmatory_floor_pp"] = FIRST_TRIAL_MIN_EFFECT_PP
    numbers["human.first_trial.divergence_pp"] = round(max(abs(v["divergence_pp"]) for v in ft["per_effect"].values()), 2)
    for st, v in ft["per_effect"].items():
        numbers[f"human.first_trial.{st}.divergence_pp"] = round(v["divergence_pp"], 2)
        numbers[f"human.first_trial.{st}.holm_p"] = round(v["holm_p"], 5)

    # ---- Step 0a: human criterion ----
    criterion, pooled, holm_tab, controls_held, most_failed = human_gate(hb_source, design, drop_confirm,
                                                                    fallback=fallback)
    pooled_h = pooled   # the human pooled estimates (the per-model loop below reuses the name `pooled`)
    for st in EFFECTS:
        numbers[f"human.{st}.criterion.replicated"] = criterion[st]["replicated"]
        numbers[f"human.{st}.criterion.confirmatory"] = criterion[st]["confirmatory"]
        numbers[f"human.{st}.criterion.holm_p"] = round(criterion[st]["holm_p"], 5)
        numbers[f"human.{st}.criterion.holm_family"] = criterion[st]["holm_family"]
        numbers[f"human.{st}.criterion.bf10"] = round(criterion[st]["bf10"], 3)
        numbers[f"human.{st}.criterion.right_direction"] = criterion[st]["right_direction"]
        numbers[f"human.{st}.pooled.delta_pp"] = round(criterion[st]["delta_pp"], 2)
        numbers[f"human.{st}.pooled.ci_lo_pp"] = round(criterion[st]["ci_lo_pp"], 2)
        numbers[f"human.{st}.pooled.ci_hi_pp"] = round(criterion[st]["ci_hi_pp"], 2)
    numbers["human.criterion.bf_prior"] = f"half-normal, positive direction, scale {RC.BF_PRIOR_SCALE_PP} points"
    numbers["human.criterion.n_regularity_failed"] = sum(1 for st in REGULARITY_EFFECTS if not criterion[st]["replicated"])

    # ---- Step 0, the positive controls ----
    pc = positive_control_check(hb_source, design, criterion, drop_confirm)
    failed_controls = pc["failed"]
    controls_held = not failed_controls
    # effects that replicate but fall under the 8-point floor after a first-trial fallback
    floor_effects = {st for st in EFFECTS if criterion[st]["replicated"] and not criterion[st]["confirmatory"]}
    numbers["human.first_trial.below_floor_effects"] = ";".join(sorted(floor_effects))
    phantom_retrieval = set()     # models whose phantom reads as retrieval
    numbers["human.positive_controls.frq_premium.delta_pp"] = round(pc["frq_premium"]["delta_pp"], 2)
    numbers["human.positive_controls.frq_premium.holds"] = pc["frq_premium"]["holds"]
    numbers["human.positive_controls.sot.holds"] = pc["sot"]["holds"]
    numbers["human.positive_controls.failed"] = ";".join(failed_controls)

    # memo for human contrasts (the hot path is re-reading the same slices for many models).
    _hc = {}

    def hc(st, tiers, fmt="numbers", drop=frozenset(), cats=None, trial=None):
        key = (st, tuple(tiers), fmt, frozenset(drop), (frozenset(cats) if cats is not None else None), trial)
        if key not in _hc:
            _hc[key] = human_contrast(hb_source, st, tiers, fmt, design, drop, trial, "backbone", cats)
        return _hc[key]

    def drop_for(st, sens=False):
        return frozenset((drop_sens if sens else drop_confirm).get(st, ()))

    # ---- rule 1: the human half of the joint bootstrap behind the pattern-test readings. The human
    #      choices of every cell are resampled with replacement within the cell (each participant contributes
    #      one choice to a cell), 2,000 times with the registered seed; every human estimate a reading uses is
    #      recomputed on the same resamples, and replicate b of the human side is paired with replicate b of
    #      every model's calls (resampled within grid points), so the two sides vary together. ----
    NB = RC.BOOTSTRAP_RESAMPLES
    hboot = (call_bootstrap.CallBootstrap([], "human", NB, RC.BOOTSTRAP_SEED, RC.BOOTSTRAP_LEVEL, within="cell")
             if bootstrap else None)
    _hstrata = {}

    def h_reps(st, tiers, fmt, drop, cats, weights, keys):
        """Replicates of the human effect pooled over the slices `keys` with `weights` (the human treatment
        counts), the construction of matched_contrast's human side; None without the bootstrap."""
        if hboot is None:
            return None
        k = (st, tuple(tiers), fmt, frozenset(drop), (frozenset(cats) if cats is not None else None))
        if k not in _hstrata:
            _hstrata[k] = {key: (t, c) for key, t, c in
                           _strata(hb_source, st, "human", tiers, fmt, None, design, drop, None, "backbone", cats)[0]
                           if t and c}
        strata = _hstrata[k]
        items = [(weights[key], hboot.arm(("T", st, key), strata[key][0]),
                  control_arm(hboot, st, key, strata[key][1], design))
                 for key in sorted(keys, key=repr) if key in strata and weights.get(key, 0) > 0]
        return call_bootstrap.combine(items, NB)

    # A check on the human half's premise: the within-cell resample keeps
    # a participant's choices in different cells independent, while the registered human test treats a
    # participant as a cluster. For every pooled human effect, the width of the within-cell bootstrap interval
    # is reported as a share of the width of the registered cluster-robust 95 percent interval (1 = the same).
    if hboot is not None:
        for st in EFFECTS:
            hp = hc(st, (1, 2, 3), "numbers", drop_for(st))
            if hp["n_strata"] == 0 or not (hp["ci_hi"] > hp["ci_lo"]):
                continue
            lo_b, hi_b = call_bootstrap.interval(h_reps(st, (1, 2, 3), "numbers", drop_for(st), None,
                                                        human_weights(hp), hp["slices"].keys()), RC.BOOTSTRAP_LEVEL)
            if lo_b is not None and math.isfinite(lo_b) and math.isfinite(hi_b):
                numbers[f"human.{st}.pooled.within_cell_bootstrap_width_ratio"] = round(
                    (hi_b - lo_b) / (hp["ci_hi"] - hp["ci_lo"]), 3)

    # ---- Step 1: human benchmarks (effect x tier x format, pooled over categories) ----
    fmts_present = sorted(set(r["format"] for r in hb_source))
    bench_rows = []
    for st in EFFECTS:
        for tier in (1, 2, 3):
            for fmt in fmts_present:
                full = hc(st, (tier,), fmt, drop_for(st))
                if full["n_strata"] == 0:
                    continue
                ftr = human_contrast(hb_all, st, (tier,), fmt, design, drop_for(st), "first")
                bench_rows.append(dict(
                    effect=st, category="pooled", tier=tier, format=fmt,
                    effect_pp=round(full["delta"] * 100, 2),
                    ci_lo_pp=round(full["ci_lo"] * 100, 2), ci_hi_pp=round(full["ci_hi"] * 100, 2),
                    n=full["n"], n_clusters=full["n_clusters"],
                    first_trial_pp=round(ftr["delta"] * 100, 2),
                    bf10=round(full["bf10"], 3)))
                numbers[f"human.{st}.t{tier}.{fmt}.delta_pp"] = round(full["delta"] * 100, 2)
                numbers[f"human.{st}.t{tier}.{fmt}.first_trial_pp"] = round(ftr["delta"] * 100, 2)
                # every category on its own
                for cat in sorted({k[0] for k in full["slices"]}, key=str):
                    cc = hc(st, (tier,), fmt, drop_for(st), {cat})
                    if cc["n_strata"] == 0:
                        continue
                    cft = human_contrast(hb_all, st, (tier,), fmt, design, drop_for(st), "first", "backbone", {cat})
                    bench_rows.append(dict(
                        effect=st, category=cat, tier=tier, format=fmt,
                        effect_pp=round(cc["delta"] * 100, 2),
                        ci_lo_pp=round(cc["ci_lo"] * 100, 2), ci_hi_pp=round(cc["ci_hi"] * 100, 2),
                        n=cc["n"], n_clusters=cc["n_clusters"], first_trial_pp=round(cft["delta"] * 100, 2),
                        bf10=round(cc["bf10"], 3)))
    cat_cells = [(r["effect"], r["category"], r["tier"], r["format"]) for r in bench_rows if r["category"] != "pooled"]

    # ---- The descriptive-only compromise slices, each reported on its own ----
    descriptive_rows = []
    for (cat, tier, fmt) in sorted(comp_desc, key=lambda s: (str(s[0]), s[1], s[2])):
        c = human_contrast(hb_source, "SOT", (tier,), fmt, design, (), None, "backbone", {cat})
        if c["n_strata"] == 0:
            continue
        descriptive_rows.append(dict(source="human", category=cat, tier=tier, format=fmt,
                                     effect_pp=round(c["delta"] * 100, 2), ci_lo_pp=round(c["ci_lo"] * 100, 2),
                                     ci_hi_pp=round(c["ci_hi"] * 100, 2),
                                     baseline_target_pct=design.hd_baseline_pct.get((cat, tier, fmt), ""),
                                     reason="compromise target starts at or above 50 percent"))
    numbers["design.compromise_descriptive_slices"] = ";".join(
        f"{c}|t{t}|{f}" for (c, t, f) in sorted(comp_desc, key=lambda s: (str(s[0]), s[1], s[2])))
    numbers["design.deviation_slices"] = ";".join(
        f"{c}|t{t}|{f}" for (c, t, f) in sorted(design.deviation_slices, key=lambda s: (str(s[0]), s[1], s[2])))

    # ---- The phantom equivalence judgment (pooled human phantom effect, +/-4 points, 90% interval) ----
    peq = phantom_equivalence(pooled["PHT"]["delta"], pooled["PHT"]["se"])
    numbers["human.PHT.equivalence_band_pp"] = PHANTOM_BAND_PP
    numbers["human.PHT.within_band"] = peq["equivalent"]
    numbers["human.PHT.equivalence.ci90_lo_pp"] = round(peq["ci90_lo_pp"], 2)
    numbers["human.PHT.equivalence.ci90_hi_pp"] = round(peq["ci90_hi_pp"], 2)
    numbers["human.PHT.equivalence.p_tost"] = round(peq["p_tost"], 6)

    # ---- The format module's headline test: the human format-by-effect interaction ----
    fmt_tests = format_interaction_tests(hb_source, design)
    for key, row in fmt_tests.items():
        k = key.replace(":", ".")
        numbers[f"human.format_interaction.{k}.interaction_pp"] = row["interaction_pp"]
        numbers[f"human.format_interaction.{k}.holm_p"] = row["holm_p"]
        numbers[f"human.format_interaction.{k}.significant"] = row["significant"]

    # ---- Secondary prediction: attraction RANGE > FREQUENCY (the Method) ----
    frq_pooled = human_effect_pooled(hb_source, "FRQ", design=design)
    rng_pooled = human_effect_pooled(hb_source, "RNG", design=design)
    rng_minus_frq_pp = rng_pooled["delta_pp"] - frq_pooled["delta_pp"]
    numbers["human.FRQ.pooled_all_tiers.delta_pp"] = round(frq_pooled["delta_pp"], 2)
    numbers["human.RNG.pooled_all_tiers.delta_pp"] = round(rng_pooled["delta_pp"], 2)
    numbers["human.RNG_vs_FRQ.contrast_pp"] = round(rng_minus_frq_pp, 2)
    numbers["human.RNG_vs_FRQ.range_exceeds_frequency"] = bool(rng_minus_frq_pp > 0)

    # ---- Decoy-target HD/HF asymmetry moderator (the Method; the Analysis Plan) ----
    asym_rows = []
    for st in ("FRQ", "RNG", "PHT"):
        hd = human_effect_pooled(hb_source, st, is_hd=True, design=design)
        hf = human_effect_pooled(hb_source, st, is_hd=False, design=design)
        diff_pp = hd["delta_pp"] - hf["delta_pp"]
        if hf["delta_pp"] < -RC.ANTI_MIN_PP:
            reading = "HF target reversed -> Evangelidis disadvantaged-target reversal"
        elif abs(diff_pp) < RC.ASYMMETRY_EQUAL_PP:
            reading = "HD equals HF -> symmetric attraction (against the asymmetry account)"
        elif diff_pp > 0:
            reading = "HD present, HF weaker -> Heath-Chatterjee asymmetry (the headline expectation)"
        else:
            reading = "HF stronger than HD -> reverse asymmetry, reported descriptively"
        asym_rows.append(dict(effect=st, hd_target_pp=round(hd["delta_pp"], 2),
                              hf_target_pp=round(hf["delta_pp"], 2),
                              hd_minus_hf_pp=round(diff_pp, 2), reading=reading))
        numbers[f"human.{st}.decoy_target.hd_pp"] = round(hd["delta_pp"], 2)
        numbers[f"human.{st}.decoy_target.hf_pp"] = round(hf["delta_pp"], 2)
        numbers[f"human.{st}.decoy_target.hd_minus_hf_pp"] = round(diff_pp, 2)
        numbers[f"human.{st}.decoy_target.reading"] = reading

    # ---- The price-free robustness arm (never pooled into the backbone tests) ----
    pf_rows = []
    for st in ("FRQ", "RNG", "PHT"):
        c = human_contrast(hb_source, st, (1, 2, 3), "numbers", design, (), None, "pricefree")
        if c["n_strata"] == 0:
            continue
        pf_rows.append(dict(source="human", effect=st, effect_pp=round(c["delta"] * 100, 2),
                            ci_lo_pp=round(c["ci_lo"] * 100, 2), ci_hi_pp=round(c["ci_hi"] * 100, 2), n=c["n"]))
        numbers[f"human.price_free.{st}.delta_pp"] = round(c["delta"] * 100, 2)

    # ---- The registered sensitivity analysis: every deviation-flagged slice excluded ----
    sgate, _, _, s_controls, s_most = human_gate(hb_source, design, drop_sens, fallback=fallback)
    s_failed_controls = positive_control_check(hb_source, design, sgate, drop_sens)["failed"]
    sens_human_rows = []
    for st in EFFECTS:
        sens_human_rows.append(dict(effect=st, primary_pp=round(criterion[st]["delta_pp"], 2),
                                    sensitivity_pp=round(sgate[st]["delta_pp"], 2),
                                    primary_replicated=criterion[st]["replicated"],
                                    sensitivity_replicated=sgate[st]["replicated"],
                                    sensitivity_holm_p=round(sgate[st]["holm_p"], 5),
                                    sensitivity_bf10=round(sgate[st]["bf10"], 3)))
        numbers[f"human.sensitivity_deviation_excluded.{st}.delta_pp"] = round(sgate[st]["delta_pp"], 2)
        numbers[f"human.sensitivity_deviation_excluded.{st}.replicated"] = sgate[st]["replicated"]
    numbers["human.sensitivity_deviation_excluded.gate_changes"] = ";".join(
        st for st in EFFECTS if criterion[st]["replicated"] != sgate[st]["replicated"])

    # ---- Steps 2 & 3 per model ----
    # rule 3 (2026-09-29): a model's class for an effect is computed on the effect's POOLED estimate
    # (the same slices and slice weights as the human confirmatory test); the per-tier classes of the
    # fidelity map are descriptive. rule 5: every model point carries its number of calls and a
    # descriptive bootstrap interval over calls. rule 9: an effect whose positive control failed is
    # uninformative, and so is every pattern test that uses it.
    fidelity_rows = []
    effect_class_rows = []
    agreement_rows = []
    test_T1_rows, test_T2_rows, test_T3_rows, test_T4_rows, test_T5_rows = [], [], [], [], []
    t4_point_rows = []
    t1_sens_rows = []
    divergence_rows = []   # neutral-vs-persona and single-shot-vs-sequential readings
    routing_rows = []
    model_gate_rows = []
    no_counterpart_rows = []
    fmt_model_rows = []
    category_rows = []     # every model effect in every category, tier and format (descriptive)
    no_room_rows = []      # the cells each model holds out under the ceiling rule
    sens_model_rows = []
    model_results = {}

    def _meta_of(m, field, default):
        if m in synth.MODEL_ARCHETYPES:
            return synth.MODEL_ARCHETYPES[m][field]
        recs = models.get(m) or []
        for r in recs:
            if r.get(field) not in (None, ""):
                return r[field]
        return default
    family_of = {m: _meta_of(m, "family", m) for m in models}
    generation_of = {m: _meta_of(m, "generation", "new") for m in models}
    members_by_family = defaultdict(list)
    for m, fam in family_of.items():
        members_by_family[fam].append(m)

    def heff(st, tier, fmt="numbers", sens=False, cats=None, extra=frozenset()):
        return hc(st, (tier,), fmt, drop_for(st, sens) | extra, cats)["delta"]

    def matched(recs, boot, st, tiers, fmt="numbers", sens=False, cats=None, extra=frozenset(), mode="neutral"):
        """rule 3: the model's pooled effect on the SAME slices, with the SAME slice weights, as the
        human estimate it is read against. Returns (model contrast or None, the human effect on those
        slices, the full human contrast)."""
        drop = drop_for(st, sens) | extra
        h = hc(st, tuple(tiers), fmt, drop, cats)
        m, hd = matched_contrast(h, recs, st, tiers, fmt, design, drop, cats, boot, mode)
        return m, hd, h

    def _pp(x):
        return round(x * 100, 2) if isinstance(x, (int, float)) else ""

    # the backbone numbers slices (category, tier) the memorization sensitivity reads.
    idx_h = _index(hb_source)
    backbone_slices = sorted({(k[1], k[2]) for k in idx_h if k[0] == "BIN" and k[3] == "numbers"
                              and _in_scope(k[1], "backbone", design)}, key=lambda s: (str(s[0]), s[1]))

    for model, recs in models.items():
        recs, recs_reason, n_other_arms = split_arms(recs)
        numbers[f"model.{model}.records_left_out_other_neutral_arms"] = n_other_arms
        ginfo = model_gate(recs)
        nr = frozenset(ginfo["no_room_slices"])   # this model's binary cells at ceiling: held out
        boot = (call_bootstrap.CallBootstrap(recs, model, RC.BOOTSTRAP_RESAMPLES, RC.BOOTSTRAP_SEED,
                                             RC.BOOTSTRAP_LEVEL) if bootstrap else None)

        def mreps(m):
            """Replicates of a model contrast under its call bootstrap (None without the bootstrap)."""
            if m is None or not m.get("parts"):
                return None
            return call_bootstrap.combine(m["parts"], NB)

        def hreps_for(m, st, tiers, fmt="numbers", sens=False, cats=None, extra=frozenset()):
            """Replicates of the human side of a matched contrast m (the same slices and weights)."""
            if m is None:
                return None
            drop = drop_for(st, sens) | extra
            h = hc(st, tuple(tiers), fmt, drop, cats)
            return h_reps(st, tiers, fmt, drop, cats, human_weights(h), m["slices"].keys())

        def member(m, hpp, st, tiers, fmt="numbers", sens=False, cats=None, extra=frozenset()):
            """One cell of a group under the joint bootstrap: (sign of the human effect, model reps, human reps)."""
            return (1.0 if hpp > 0 else -1.0, mreps(m), hreps_for(m, st, tiers, fmt, sens, cats, extra))
        model_gate_rows.append(dict(
            model=model, parse_rate=round(ginfo["parse_rate"], 4),
            refusal_rate=round(ginfo["refusal_rate"], 4), parse_ok=ginfo["parse_ok"],
            refusal_ok=ginfo["refusal_ok"], n_no_room_cells=len(ginfo["no_room_cells"]),
            n_lost_cells=len(ginfo["lost_cells"]), frac_cells_lost=round(ginfo["frac_lost"], 3),
            not_assessable=ginfo["not_assessable"]))
        numbers[f"model.{model}.criterion.parse_rate"] = round(ginfo["parse_rate"], 4)
        numbers[f"model.{model}.criterion.refusal_rate"] = round(ginfo["refusal_rate"], 4)
        numbers[f"model.{model}.criterion.not_assessable"] = ginfo["not_assessable"]

        recog_by_struct = {}
        for st in EFFECTS:
            if st == "PHT":
                continue
            yes = tot = 0
            for r in recs:
                if r["prompting_mode"] == "recognition" and r["structure"] == st:
                    tot += 1
                    if r.get("recognition") == 1:
                        yes += 1
            recog_by_struct[st] = yes / tot if tot else 0.0

        # ---- the fidelity map's points: every effect x tier (numbers), classed descriptively ----
        scored_cells = []
        no_counterpart = set()
        tier_class = {}
        tier_match, pooled_match, fmt_match = {}, {}, {}     # model contrasts the pattern bootstrap reads
        kept = dict(tier={}, pooled={}, fmt={})             # group members (read only when keep_members is on)
        for st in EFFECTS:
            passed = criterion[st]["replicated"]
            for tier in (1, 2, 3):
                m, he, _ = matched(recs, boot, st, (tier,), extra=nr)
                if m is None:
                    continue
                meff = m["delta"]
                tier_match[(st, tier)] = m
                ceiling = (st, tier, "numbers") in ginfo["no_room_cells"]
                if not passed:
                    cls = gate_exit_class(meff)
                elif ceiling:
                    cls = "excluded(no-room)"
                elif st in failed_controls:
                    cls = UNINFORMATIVE
                elif st in floor_effects:
                    cls = DESCRIPTIVE_FLOOR
                else:
                    cls = classify_cell(meff, he)
                tier_class[(st, tier)] = cls
                row = dict(model=model, structure=st, tier=tier, format="numbers",
                           human_pp=round(he * 100, 2), model_pp=round(meff * 100, 2),
                           deviation_pp=round((meff - he) * 100, 2), n_calls=m["n_used"],
                           boot_lo_pp=_pp(m["boot_lo"]), boot_hi_pp=_pp(m["boot_hi"]),
                           max_draws_per_grid_point=m["max_draws"], ceiling_flag=int(ceiling),
                           class_basis="descriptive (one tier)", **{"class": cls})
                fidelity_rows.append(row)
                if cls == "no-human-counterpart":
                    no_counterpart.add(st)
                    no_counterpart_rows.append(dict(model=model, effect=st, tier=tier, format="numbers",
                                                    model_pp=round(meff * 100, 2), human_pp=round(he * 100, 2),
                                                    n_calls=m["n_used"], boot_lo_pp=_pp(m["boot_lo"]),
                                                    boot_hi_pp=_pp(m["boot_hi"]), human_gate="failed"))
                if cls not in NON_SCORED:
                    scored_cells.append(row)
                numbers[f"model.{model}.{st}.t{tier}.numbers.model_pp"] = round(meff * 100, 2)
                numbers[f"model.{model}.{st}.t{tier}.numbers.class"] = cls
        numbers[f"model.{model}.no_human_counterpart"] = ";".join(sorted(no_counterpart))

        # ---- every category, tier and format on its own ----
        for (st, cat, tier, fmt) in cat_cells:
            if (str(cat), tier, fmt) in nr or (cat, tier, fmt) in nr:
                continue                                    # listed in no_room_cells.csv
            hcat = hc(st, (tier,), fmt, drop_for(st), {cat})
            mcat = model_contrast(recs, st, (tier,), fmt, "neutral", design, drop_for(st) | nr, "backbone", {cat},
                                  weights=human_weights(hcat), boot=boot)
            if mcat is None:
                continue
            if not criterion[st]["replicated"]:
                ccls = gate_exit_class(mcat["delta"])
            elif st in failed_controls:
                ccls = UNINFORMATIVE
            elif st in floor_effects:
                ccls = DESCRIPTIVE_FLOOR
            else:
                ccls = classify_cell(mcat["delta"], hcat["delta"])
            category_rows.append(dict(model=model, effect=st, category=cat, tier=tier, format=fmt,
                                      human_pp=round(hcat["delta"] * 100, 2), human_ci_lo_pp=round(hcat["ci_lo"] * 100, 2),
                                      human_ci_hi_pp=round(hcat["ci_hi"] * 100, 2), model_pp=round(mcat["delta"] * 100, 2),
                                      n_calls=mcat["n_used"], boot_lo_pp=_pp(mcat["boot_lo"]),
                                      boot_hi_pp=_pp(mcat["boot_hi"]), **{"class": ccls},
                                      class_basis="descriptive (one category, tier and format)"))
        for (cat, tier, fmt) in sorted(nr, key=lambda s: (str(s[0]), s[1], s[2])):
            no_room_rows.append(dict(model=model, level="two-option cell", category=cat, tier=tier, format=fmt,
                                     effect="every effect built on this cell"))
        for (st, tier, fmt) in sorted(ginfo["no_room_cells"], key=lambda s: (s[0], s[1], s[2])):
            no_room_rows.append(dict(model=model, level="effect and tier, every category at the ceiling",
                                     category="all", tier=tier, format=fmt, effect=st))

        # ---- rule 3: each effect's class on its POOLED estimate (the confirmatory model point) ----
        eff_cls, pooled, pooled_m = {}, {}, {}
        for st in EFFECTS:
            passed = criterion[st]["replicated"]
            m, he, h = matched(recs, boot, st, (1, 2, 3), extra=nr)
            if m is None:
                eff_cls[st] = "excluded(no-room)" if passed else "excluded(criterion-exit)"
                continue
            meff = m["delta"]
            pooled_match[st] = m
            descriptive_class = ""
            if not passed:
                cls = gate_exit_class(meff)
            elif st in failed_controls:
                cls = UNINFORMATIVE
            elif st in floor_effects:
                cls = DESCRIPTIVE_FLOOR
                descriptive_class = classify_cell(meff, he)
            else:
                cls = classify_cell(meff, he)
            eff_cls[st] = cls
            pooled[st] = (meff * 100, he * 100)
            pooled_m[st] = meff
            pdeltas, psens = paraphrase_signs(recs, st, (1, 2, 3), "numbers", "neutral", design,
                                              drop_for(st) | nr, "backbone", None, weights=human_weights(h))
            notes = []
            # the phantom's retrieval reading: OVER against a replicated human phantom, or a
            # model phantom larger than 3 points (in the phantom's predicted direction) where the human phantom
            # effect failed the criterion.
            if passed and st == "PHT" and cls == "OVER":
                notes.append("OVER on the phantom: " + RETRIEVAL_READING)
            if st == "PHT" and not passed and _pts(meff) > RC.ANTI_MIN_PP:
                notes.append("phantom larger than 3 points where the human phantom failed: " + RETRIEVAL_READING)
                phantom_retrieval.add(model)
            if passed and tier_class.get((st, 1)) == "OVER":
                notes.append("OVER on the published tier: " + RETRIEVAL_READING)
            over_reading = "; ".join(notes)
            psens_out = "n/a" if psens is None else psens
            effect_class_rows.append(dict(
                model=model, effect=st, human_gate=("passed" if passed else "failed"),
                human_pp=round(he * 100, 2), model_pp=round(meff * 100, 2),
                deviation_pp=round((meff - he) * 100, 2), n_calls=m["n_used"],
                boot_lo_pp=_pp(m["boot_lo"]), boot_hi_pp=_pp(m["boot_hi"]),
                max_draws_per_grid_point=m["max_draws"], prompt_sensitive=psens_out,
                paraphrase_pp=";".join(f"{p}:{d * 100:+.2f}" for p, d in
                                       sorted(pdeltas.items(), key=lambda kv: str(kv[0]))),
                over_reading=over_reading, descriptive_class=descriptive_class,
                class_basis=("descriptive (below the first-trial floor)" if st in floor_effects
                             else "confirmatory (pooled over categories and tiers)"),
                **{"class": cls}))
            pre = f"model.{model}.{st}.pooled"
            numbers[f"{pre}.model_pp"] = round(meff * 100, 2)
            numbers[f"{pre}.human_pp"] = round(he * 100, 2)
            numbers[f"{pre}.class"] = cls
            numbers[f"{pre}.n_calls"] = m["n_used"]
            numbers[f"{pre}.boot_lo_pp"] = _pp(m["boot_lo"])
            numbers[f"{pre}.boot_hi_pp"] = _pp(m["boot_hi"])
            numbers[f"{pre}.prompt_sensitive"] = psens_out
            numbers[f"{pre}.over_reading"] = over_reading
        overall = overall_class(eff_cls, criterion)

        # ---- T5's reasoning half: the reasoning-contrast arm against the primary arm,
        #      on the same pooled estimates and combined group fidelity as the generation comparison ----
        primary_sts = [st for st in REGULARITY_EFFECTS if st in pooled and criterion[st]["replicated"]
                       and eff_cls.get(st) in SCORED_CLASSES]
        primary_cells = [dict(human_pp=pooled[st][1], model_pp=pooled[st][0], **{"class": eff_cls[st]})
                         for st in primary_sts]
        fid_primary = fidelity_ratio_for(primary_cells)
        fid_primary_reps = group_fold_reps([member(pooled_match[st], pooled[st][1], st, (1, 2, 3), extra=nr)
                                            for st in primary_sts if abs(pooled[st][1]) >= NEAR_NULL_HUMAN * 100])
        fid_reason = fid_reason_reps = None
        if recs_reason:
            boot_r = (call_bootstrap.CallBootstrap(recs_reason, f"{model}|reasoning_on", RC.BOOTSTRAP_RESAMPLES,
                                                   RC.BOOTSTRAP_SEED, RC.BOOTSTRAP_LEVEL) if bootstrap else None)
            cells_r, members_r = [], []
            for st in primary_sts:
                mr, her, _ = matched(recs_reason, boot_r, st, (1, 2, 3), extra=nr)
                if mr is not None:
                    cells_r.append(dict(human_pp=her * 100, model_pp=mr["delta"] * 100, **{"class": "scored"}))
                    if abs(her) >= NEAR_NULL_HUMAN:
                        members_r.append(member(mr, her, st, (1, 2, 3), extra=nr))
            fid_reason = fidelity_ratio_for(cells_r)
            fid_reason_reps = group_fold_reps(members_r)
            boot_r = None
        recs_reason = None

        agree = agreement(scored_cells)
        agreement_rows.append(dict(
            model=model, **{"class": overall},
            sign_agreement=agree["sign_agreement"], mad_pp=agree["mad_pp"],
            calibration_slope=("" if agree["calibration_slope"] != agree["calibration_slope"] else agree["calibration_slope"]),
            cells_scored=agree["n_scored"], cells_excluded=len(ginfo["no_room_cells"]) + len(ginfo["lost_cells"]),
            effects_classed=sum(1 for st in REGULARITY_EFFECTS
                                if criterion[st]["replicated"] and eff_cls.get(st) in SCORED_CLASSES)))
        numbers[f"model.{model}.dominant_class"] = overall
        numbers[f"model.{model}.overall_class"] = overall
        numbers[f"model.{model}.sign_agreement"] = agree["sign_agreement"]
        numbers[f"model.{model}.mad_pp"] = agree["mad_pp"]

        # ---- T1, descriptive per-tier values over every category (similarity held out); the invented tier is a
        #      supporting descriptive extension ----
        cells_by_tier, raw_by_tier, reps_by_tier = {}, {}, {}
        for tier in (1, 2, 3):
            sub = [c for c in scored_cells if c["tier"] == tier and c["structure"] != "SIM"]
            r = fidelity_ratio_for(sub)
            if r is not None:
                cells_by_tier[tier] = r
                raw_by_tier[tier] = group_ratio_raw(sub)
                mem = [(c["structure"], c["model_pp"], c["human_pp"])
                       + member(tier_match[(c["structure"], tier)], c["human_pp"], c["structure"], (tier,), extra=nr)
                       for c in sub if abs(c["human_pp"]) >= NEAR_NULL_HUMAN * 100]
                reps_by_tier[tier] = group_fold_reps([x[3:] for x in mem])
                kept["tier"][tier] = mem
        # ---- T1: the published-values tier against the
        #      new-values tier on the SAME categories, paired: each effect restricted to the categories it has on
        #      both tiers (after the descriptive and no-room slices), each tier pooled with its registered slice
        #      weights over those categories; group fidelity is the combined ratio of sums, as for every group ----
        paired, paired_cats = {t: [] for t in T1_TIERS}, {}
        for st in EFFECTS:
            if st == "SIM" or any(tier_class.get((st, t)) is None or tier_class.get((st, t)) in NON_SCORED
                                  for t in T1_TIERS):
                continue
            cats12 = [{k[0] for k in hc(st, (t,), "numbers", drop_for(st) | nr, None)["slices"]} for t in T1_TIERS]
            common = cats12[0] & cats12[1]
            if not common:
                continue
            ms = [matched(recs, boot, st, (t,), cats=common, extra=nr) for t in T1_TIERS]
            if any(mt is None or abs(het) < NEAR_NULL_HUMAN for mt, het, _ in ms):
                continue
            for t, (mt, het, _) in zip(T1_TIERS, ms):
                paired[t].append((st, mt["delta"] * 100, het * 100)
                                 + member(mt, het * 100, st, (t,), cats=common, extra=nr))
            paired_cats[st] = sorted(common, key=str)
        kept["tier_paired"], kept["tier_paired_cats"] = paired, paired_cats
        t1_points, t1_raw, t1_reps = {}, {}, {}
        for t in T1_TIERS:
            den = sum(abs(x[2]) for x in paired[t])
            if paired[t] and den > 0:
                t1_raw[t] = sum(x[3] * x[1] for x in paired[t]) / den
                t1_points[t] = _fold(t1_raw[t])
                t1_reps[t] = group_fold_reps([x[3:] for x in paired[t]])
        t1_drop_reps = (diff_reps(t1_reps[T1_TIERS[0]], t1_reps[T1_TIERS[-1]]) if len(t1_points) == len(T1_TIERS)
                        else None)
        t1_ci = rep_interval(t1_drop_reps)
        t1 = test_T1_memorization(t1_points, t1_raw, drop_ci=t1_ci, resolve=True)
        t1 = dict(t1, paired_categories=";".join(f"{st}:{'/'.join(str(c) for c in cs)}"
                                                 for st, cs in paired_cats.items()),
                  descriptive_fidelity_all_categories_t1=_r3(cells_by_tier.get(1)),
                  descriptive_fidelity_all_categories_t2=_r3(cells_by_tier.get(2)),
                  descriptive_fidelity_invented_tier=_r3(cells_by_tier.get(3)))
        if failed_controls:
            t1 = dict(t1, reading=_mark_uninformative(t1["reading"], failed_controls), p_steep="F", p_flat="F",
                      resolved=True)
        test_T1_rows.append(dict(model=model, **t1))
        numbers[f"model.{model}.T1.reading"] = t1["reading"]
        numbers[f"model.{model}.T1.slope"] = t1["slope"]
        numbers[f"model.{model}.T1.drop_lo"] = t1.get("drop_lo", "")
        numbers[f"model.{model}.T1.drop_hi"] = t1.get("drop_hi", "")
        numbers[f"model.{model}.T1.descriptive_fidelity_invented_tier"] = t1.get("descriptive_fidelity_invented_tier",
                                                                                   "")

        # ---- T1 registered sensitivity: in-limit baselines, then adjusted for baseline position and
        #      decoy-target identity ----
        slice_cells = []
        for st in REGULARITY_EFFECTS:
            if not criterion[st]["replicated"] or st in floor_effects:
                continue
            for (cat, tier) in backbone_slices:
                if tier not in T1_TIERS:
                    continue                    # the tiers the registered memorization test compares
                if (st, tier, "numbers") in ginfo["no_room_cells"]:
                    continue
                if (cat, tier, "numbers") in drop_for(st) or (cat, tier, "numbers") in nr:
                    continue
                h = hc(st, (tier,), "numbers", drop_for(st), {cat})
                if h["n_strata"] == 0:
                    continue
                m = model_contrast(recs, st, (tier,), "numbers", "neutral", design, drop_for(st), "backbone", {cat},
                                   boot=boot)
                if m is None:
                    continue
                slice_cells.append(dict(category=cat, tier=tier, structure=st, human_pp=h["delta"] * 100,
                                        model_pp=m["delta"] * 100, w=max(1, h["n"]),
                                        budget_target=_budget_target(design, cat, tier, st),
                                        slice_budget=_budget_target(design, cat, tier, "FRQ"),
                                        mr=mreps(m), hr=hreps_for(m, st, (tier,), cats={cat})))
        t1s = test_T1_sensitivity(slice_cells, design, t1, resolve=True)
        slice_cells = None
        if failed_controls:
            for k in ("restricted_reading", "adjusted_reading"):
                t1s[k] = _mark_uninformative(t1s[k], failed_controls)
        t1_sens_rows.append(dict(model=model, **t1s))
        numbers[f"model.{model}.T1.sensitivity.restricted_reading"] = t1s["restricted_reading"]
        numbers[f"model.{model}.T1.sensitivity.adjusted_reading"] = t1s["adjusted_reading"]
        numbers[f"model.{model}.T1.sensitivity.adjusted_drop"] = t1s["adjusted_drop"]

        # ---- T2: recognition, against each effect's pooled estimate ----
        behavior_by_struct = {st: pooled_m[st] for st in EFFECTS if st != "PHT" and st in pooled_m}
        # rule (b): the recognition rate's interval (the probe calls resampled within each stimulus)
        # and the pooled model effect's interval over calls resolve the knows-without-shows reading
        recog_ci, behavior_ci = {}, {}
        if boot is not None:
            for st in recog_by_struct:
                rows_r = [(r.get("record_id"), 1 if r.get("recognition") == 1 else 0) for r in recs
                          if r["prompting_mode"] == "recognition" and r["structure"] == st]
                if rows_r:
                    a = boot.arm(("RECOG", st), rows_r)
                    recog_ci[st] = (call_bootstrap.interval(a[1], RC.BOOTSTRAP_LEVEL) if a[1] is not None
                                    else (a[0], a[0]))
            for st, m in pooled_match.items():
                if m.get("boot_lo") is not None:
                    behavior_ci[st] = (m["boot_lo"], m["boot_hi"])
        t2_per, t2_override = test_T2_recognition(recog_by_struct, behavior_by_struct, set(failed_controls),
                                                  descriptive=floor_effects, recog_ci=recog_ci,
                                                  behavior_ci=behavior_ci)
        if boot is None:
            for d in t2_per.values():          # no bootstrap: nothing resolves
                if not d["reading"].startswith(("uninformative", "descriptive")):
                    d.update(knows_state="U", shows_state="U", override_state="U")
        t2_state = t2_override_state(t2_per)
        for st, d in t2_per.items():
            test_T2_rows.append(dict(model=model, structure=st, **d))
        numbers[f"model.{model}.T2.override"] = t2_override
        numbers[f"model.{model}.T2.override_state"] = t2_state

        # ---- T3: the ladder on each effect's pooled estimate, with the reversed-ladder reading ----
        fidelity_by_struct, raw_by_struct, rung_reps = {}, {}, {}
        for st in EFFECTS:
            if st in pooled and eff_cls.get(st) in SCORED_CLASSES:
                mp, hp = pooled[st]
                cell = [dict(human_pp=hp, model_pp=mp, **{"class": eff_cls[st]})]
                fidelity_by_struct[st] = fidelity_ratio_for(cell)
                raw_by_struct[st] = group_ratio_raw(cell)
                if abs(hp) >= NEAR_NULL_HUMAN * 100:
                    kept["pooled"][st] = (st, mp, hp) + member(pooled_match[st], hp, st, (1, 2, 3), extra=nr)
                    rung_reps[st] = group_fold_reps([kept["pooled"][st][3:]])
                else:
                    rung_reps[st] = None
            else:
                fidelity_by_struct[st] = None
        top_reps = mean_reps([rung_reps.get(s) for s in LADDER_TOP if fidelity_by_struct.get(s) is not None])
        low_reps = rung_reps.get(LADDER_BOTTOM) if fidelity_by_struct.get(LADDER_BOTTOM) is not None else None
        mid_reps = rung_reps.get(LADDER_MIDDLE) if fidelity_by_struct.get(LADDER_MIDDLE) is not None else None
        t3_tmb_reps = diff_reps(top_reps, low_reps)
        t3_bmm_reps = (diff_reps(low_reps, mid_reps) if fidelity_by_struct.get(LADDER_MIDDLE) is not None else None)
        t3_ci = dict(top_minus_bottom=rep_interval(t3_tmb_reps),
                     bottom_minus_middle=(rep_interval(t3_bmm_reps)
                                          if fidelity_by_struct.get(LADDER_MIDDLE) is not None else None))
        t3 = test_T3_ladder(fidelity_by_struct, eff_cls, recog_by_struct, raw_by_struct, ci=t3_ci, resolve=True)
        if failed_controls:
            t3 = dict(t3, reading=_mark_uninformative(t3["reading"], failed_controls), reversed=False,
                      attribution="", p_declines="F", p_reversed="F", p_flat="F", resolved=True)
        test_T3_rows.append(dict(model=model, **t3))
        numbers[f"model.{model}.T3.reading"] = t3["reading"]
        numbers[f"model.{model}.T3.attribution"] = t3["attribution"]

        # ---- T4: formats, group fidelity on the per-format pooled estimates (tier 2, same categories);
        #      a format whose human effect is under 2 points has no registered reading ----
        fidelity_by_format, t4_undefined, raw_by_format, reps_by_format = {}, {}, {}, {}
        for fmt in ("numbers", "words", "pictures"):
            ref = "pictures" if fmt in ("numbers", "pictures") else "words"
            cells, members = [], []
            for st in FORMAT_EFFECTS:
                if st in floor_effects:
                    continue                    # below the first-trial floor: leaves the pattern tests
                cats = format_categories_for(hb_source, design, ref, st)
                if not cats:
                    continue
                m, he, _ = matched(recs, boot, st, (FORMAT_TIER,), fmt, cats=cats, extra=nr)
                fmt_match[(fmt, st)] = m
                if m is None:
                    continue
                t4_point_rows.append(dict(model=model, format=fmt, compared_on=f"{ref} categories", effect=st,
                                          categories=";".join(sorted(str(c) for c in cats)),
                                          human_pp=round(he * 100, 2), model_pp=round(m["delta"] * 100, 2),
                                          n_calls=m["n_used"], boot_lo_pp=_pp(m["boot_lo"]),
                                          boot_hi_pp=_pp(m["boot_hi"]), max_draws_per_grid_point=m["max_draws"]))
                if abs(he) < NEAR_NULL_HUMAN:
                    t4_undefined[fmt] = f"human {st} effect {he * 100:.2f} points"
                    continue
                cells.append(dict(human_pp=he * 100, model_pp=m["delta"] * 100, **{"class": "scored"}))
                members.append((st, m["delta"] * 100, he * 100)
                               + member(m, he, st, (FORMAT_TIER,), fmt, cats=cats, extra=nr))
            kept["fmt"][(fmt, ref)] = members
            if fmt in t4_undefined:
                continue
            r = fidelity_ratio_for(cells)
            if r is not None:
                fidelity_by_format[fmt] = r
                raw_by_format[fmt] = group_ratio_raw(cells)
                reps_by_format[fmt] = group_fold_reps([x[3:] for x in members])
        if keep_members:
            # the design study's pooled format option also needs numbers on the words categories (not registered)
            mem_nw, nw_undefined = [], {}
            for st in FORMAT_EFFECTS:
                cats_w = format_categories_for(hb_source, design, "words", st)
                if st in floor_effects or not cats_w:
                    continue
                m, he, _ = matched(recs, boot, st, (FORMAT_TIER,), "numbers", cats=cats_w, extra=nr)
                if m is not None and abs(he) >= NEAR_NULL_HUMAN:
                    mem_nw.append((st, m["delta"] * 100, he * 100)
                                  + member(m, he, st, (FORMAT_TIER,), "numbers", cats=cats_w, extra=nr))
                elif m is not None:
                    nw_undefined["numbers on the words categories"] = f"human {st} effect {he * 100:.2f} points"
            kept["fmt"][("numbers", "words")] = mem_nw
            kept["t4_undefined"] = dict(t4_undefined, **nw_undefined)
        t4_diff_reps = (diff_reps(reps_by_format.get("numbers"), reps_by_format.get("pictures"))
                        if "numbers" in reps_by_format and "pictures" in reps_by_format else None)
        t4_ci = rep_interval(t4_diff_reps)
        t4 = test_T4_formats(fidelity_by_format, t4_undefined, raw_by_format, diff_ci=t4_ci, resolve=True)
        # The registered order check (main.md, T4): picture prompts keep one fixed option order while numbers
        # prompts rotate every order, so T4 is also reported with the model's numbers calls restricted to the
        # picture's order (the canonical order). The human benchmark is unchanged. Descriptive beside T4.
        recs_po = [r for r in recs if r.get("format") != "numbers" or is_picture_order(r)]
        cells_po = []
        for st in FORMAT_EFFECTS:
            if st in floor_effects:
                continue
            cats = format_categories_for(hb_source, design, "pictures", st)
            if not cats:
                continue
            m_po, he_po, _ = matched(recs_po, None, st, (FORMAT_TIER,), "numbers", cats=cats, extra=nr)
            if m_po is None or abs(he_po) < NEAR_NULL_HUMAN:
                continue
            cells_po.append(dict(human_pp=he_po * 100, model_pp=m_po["delta"] * 100, **{"class": "scored"}))
        fid_num_po = fidelity_ratio_for(cells_po) if cells_po else None
        recs_po = None
        t4_po = test_T4_formats(dict(fidelity_by_format, numbers=fid_num_po) if fid_num_po is not None
                                else {k: v for k, v in fidelity_by_format.items() if k != "numbers"}, t4_undefined,
                                raw_by_format)
        # rule 6: the picture-order check is model side only and descriptive (a point reading with no
        # interval, never a registered reading and never a route).
        t4 = dict(t4, numbers_picture_order=(round(fid_num_po, 3) if fid_num_po is not None else ""),
                  reading_picture_order=("descriptive, model side only (the model's numbers calls restricted to the "
                                         "picture's order; the human benchmark unchanged): " + t4_po["reading"]))
        if failed_controls:
            t4 = dict(t4, reading=_mark_uninformative(t4["reading"], failed_controls),
                      reading_picture_order=_mark_uninformative(t4["reading_picture_order"], failed_controls),
                      p_falls="F", p_flat="F", resolved=True)
        test_T4_rows.append(dict(model=model, **t4))
        numbers[f"model.{model}.T4.reading"] = t4["reading"]

        # ---- The model side of the format interaction (descriptive; no test on the model arm) ----
        for key, trow in fmt_tests.items():
            cats = set(trow["categories"].split(";"))
            mf, _, _ = matched(recs, boot, trow["effect"], (FORMAT_TIER,), trow["format"], cats=cats, extra=nr)
            mn, _, _ = matched(recs, boot, trow["effect"], (FORMAT_TIER,), "numbers", cats=cats, extra=nr)
            if mf is None or mn is None:
                continue
            mint = mf["delta"] - mn["delta"]
            lo, hi = boot.difference_interval(mf["parts"], mn["parts"]) if boot is not None else (None, None)
            if trow["significant"]:
                hint = trow["_inter"]
                follows = ((mint > 0) == (hint > 0)) and abs(mint) >= RC.FORMAT_MODEL_FOLLOW_RATIO * abs(hint)
                reading = ("model follows the human format change" if follows
                           else "model does not follow the human format change")
            else:
                reading = "human shows no format change; model interaction reported descriptively"
            if trow["effect"] in failed_controls:
                reading = _mark_uninformative(reading, [trow["effect"]])
            fmt_model_rows.append(dict(model=model, test=key, human_interaction_pp=trow["interaction_pp"],
                                       model_interaction_pp=round(mint * 100, 2),
                                       n_calls=mf["n_used"] + mn["n_used"], boot_lo_pp=_pp(lo),
                                       boot_hi_pp=_pp(hi), reading=reading))

        # ---- Persona/sequential divergence readings. These arms make one call per grid
        #      point, so they carry the number of calls and no resampling interval. ----
        for arm, pmode in (("persona", "persona"), ("sequential", "sequential")):
            neu_c = model_contrast(recs, "FRQ", (1, 2, 3), "numbers", "neutral", design)
            sec_c = model_contrast(recs, "FRQ", (1, 2, 3), "numbers", pmode, design)
            if neu_c is None or sec_c is None:
                continue
            neu, sec = neu_c["delta"], sec_c["delta"]
            div_pp = (sec - neu) * 100
            if arm == "persona":
                if abs(div_pp) < RC.DIVERGENCE_EQUAL_PP:
                    reading = "persona agrees with neutral -> fidelity robust to both prompting methods"
                elif div_pp > 0:
                    reading = "persona more faithful than neutral -> silicon sampling helps"
                else:
                    reading = "persona less faithful than neutral -> persona injects artifacts"
            else:
                if abs(div_pp) < RC.DIVERGENCE_EQUAL_PP:
                    reading = "sequential agrees with single-shot -> order/history does not move the effect"
                else:
                    reading = "sequential differs from single-shot -> the model carries within-session history"
            if "FRQ" in failed_controls:
                reading = _mark_uninformative(reading, ["FRQ"])
            divergence_rows.append(dict(model=model, arm=arm, neutral_pp=round(neu * 100, 2),
                                        secondary_pp=round(sec * 100, 2),
                                        divergence_pp=round(div_pp, 2), n_calls_neutral=neu_c["n_used"],
                                        n_calls_secondary=sec_c["n_used"], reading=reading))
            numbers[f"model.{model}.divergence.{arm}.neutral_pp"] = round(neu * 100, 2)
            numbers[f"model.{model}.divergence.{arm}.secondary_pp"] = round(sec * 100, 2)
            numbers[f"model.{model}.divergence.{arm}.divergence_pp"] = round(div_pp, 2)
            numbers[f"model.{model}.divergence.{arm}.reading"] = reading

        # ---- The price-free arm, model side ----
        for st in ("FRQ", "RNG", "PHT"):
            m = model_contrast(recs, st, (1, 2, 3), "numbers", "neutral", design, nr, "pricefree", boot=boot)
            if m is not None:
                pf_rows.append(dict(source=model, effect=st, effect_pp=round(m["delta"] * 100, 2),
                                    ci_lo_pp="", ci_hi_pp="", boot_lo_pp=_pp(m["boot_lo"]),
                                    boot_hi_pp=_pp(m["boot_hi"]), n=m["n_used"]))

        # ---- The model side of the descriptive-only compromise slices ----
        for (cat, tier, fmt) in sorted(comp_desc, key=lambda s: (str(s[0]), s[1], s[2])):
            m = model_contrast(recs, "SOT", (tier,), fmt, "neutral", design, nr, "backbone", {cat}, boot=boot)
            if m is None:
                continue
            descriptive_rows.append(dict(source=model, category=cat, tier=tier, format=fmt,
                                         effect_pp=round(m["delta"] * 100, 2), ci_lo_pp="", ci_hi_pp="",
                                         boot_lo_pp=_pp(m["boot_lo"]), boot_hi_pp=_pp(m["boot_hi"]),
                                         n=m["n_used"],
                                         baseline_target_pct=design.hd_baseline_pct.get((cat, tier, fmt), ""),
                                         reason="compromise target starts at or above 50 percent"))

        # ---- The deviation sensitivity, model side: classes on pooled estimates and T1 with every
        #      deviation-flagged slice out ----
        s_eff, s_cells = {}, []
        for st in EFFECTS:
            if not sgate[st]["replicated"]:
                continue
            m, he, _ = matched(recs, None, st, (1, 2, 3), sens=True, extra=nr)
            if m is None:
                continue
            s_eff[st] = (UNINFORMATIVE if st in s_failed_controls
                         else (DESCRIPTIVE_FLOOR if not sgate[st]["confirmatory"] else classify_cell(m["delta"], he)))
            for tier in (1, 2, 3):
                mt, het, _ = matched(recs, boot, st, (tier,), sens=True, extra=nr)
                if mt is None or (st, tier, "numbers") in ginfo["no_room_cells"]:
                    continue
                s_cells.append(dict(structure=st, tier=tier, human_pp=het * 100, model_pp=mt["delta"] * 100,
                                    _m=mt, **{"class": s_eff[st] if s_eff[st] in (UNINFORMATIVE, DESCRIPTIVE_FLOOR)
                                              else classify_cell(mt["delta"], het)}))
        s_overall = overall_class(s_eff, sgate)
        # the tiers the registered memorization test compares, paired on common categories as it is, with every deviation-flagged slice out
        s_by_tier, s_reps, s_raw = {}, {}, {}
        s_paired = {t: [] for t in T1_TIERS}
        for st in EFFECTS:
            cells_t = {c["tier"]: c for c in s_cells if c["structure"] == st}
            if st == "SIM" or any(t not in cells_t or cells_t[t]["class"] in NON_SCORED for t in T1_TIERS):
                continue
            cats_t = [{k[0] for k in hc(st, (t,), "numbers", drop_for(st, True) | nr, None)["slices"]}
                      for t in T1_TIERS]
            common = set.intersection(*cats_t)
            if not common:
                continue
            ms = [matched(recs, boot, st, (t,), sens=True, cats=common, extra=nr) for t in T1_TIERS]
            if any(mt is None or abs(het) < NEAR_NULL_HUMAN for mt, het, _ in ms):
                continue
            for t, (mt, het, _) in zip(T1_TIERS, ms):
                s_paired[t].append((mt["delta"] * 100, het * 100)
                                   + member(mt, het * 100, st, (t,), sens=True, cats=common, extra=nr))
        for t in T1_TIERS:
            den = sum(abs(x[1]) for x in s_paired[t])
            if s_paired[t] and den > 0:
                s_raw[t] = sum(x[2] * x[0] for x in s_paired[t]) / den     # the undershoot guard (F12) reads it
                s_by_tier[t] = _fold(s_raw[t])
                s_reps[t] = group_fold_reps([x[2:] for x in s_paired[t]])
        sp = sorted(s_by_tier)
        s_t1 = test_T1_memorization(s_by_tier, s_raw, drop_ci=(rep_interval(diff_reps(s_reps[sp[0]], s_reps[sp[-1]]))
                                                                if len(sp) >= 2 else None), resolve=True)
        s_cells = None
        if s_failed_controls:
            s_t1 = dict(s_t1, reading=_mark_uninformative(s_t1["reading"], s_failed_controls))
        sens_model_rows.append(dict(model=model, primary_class=overall, sensitivity_class=s_overall,
                                    primary_T1=t1["reading"], sensitivity_T1=s_t1["reading"]))
        numbers[f"model.{model}.sensitivity_deviation_excluded.dominant_class"] = s_overall

        model_results[model] = dict(ginfo=ginfo, agree=agree, scored_cells=scored_cells, eff_cls=eff_cls,
                                    fid_primary=fid_primary, fid_reason=fid_reason,
                                    fid_primary_reps=fid_primary_reps, fid_reason_reps=fid_reason_reps,
                                    # the replicates each reading was resolved against (in memory only; the
                                    # stability sweep re-reads them at other interval levels)
                                    members=(kept if keep_members else None),
                                    resolution_reps=dict(t1=t1_drop_reps, t3_tmb=t3_tmb_reps, t3_bmm=t3_bmm_reps,
                                                         t4=t4_diff_reps, t1_raw=t1_raw, t3_raw=raw_by_struct,
                                                         t4_raw=raw_by_format, t1_points=t1_points,
                                                         t3_points=fidelity_by_struct, t4_points=fidelity_by_format,
                                                         t4_undefined=t4_undefined),
                                    overall=overall, pooled=pooled, t1=t1, t2_override=t2_override,
                                    t2_state=t2_state,
                                    t2_per=t2_per, t3=t3, t4=t4, recog_by_struct=recog_by_struct,
                                    fidelity_by_struct=fidelity_by_struct, no_counterpart=no_counterpart,
                                    t1_sensitivity=t1s)

    # ---- T5: trajectory, per family that has old+new members, on the combined group fidelity of the
    #      pooled estimates of the non-similarity effects that passed ----
    fidelity_overall = {}
    for m, res in model_results.items():
        cells = [dict(human_pp=hp, model_pp=mp, **{"class": res["eff_cls"][st]})
                 for st, (mp, hp) in res["pooled"].items()
                 if st in REGULARITY_EFFECTS and criterion[st]["replicated"] and res["eff_cls"].get(st) in SCORED_CLASSES]
        fidelity_overall[m] = fidelity_ratio_for(cells)
    for fam, members in members_by_family.items():
        gens = {generation_of[m]: m for m in members}
        for m in members:
            res_m = model_results[m]
            # rule 1: the generation difference and the reasoning difference each carry the interval of
            # the joint bootstrap (the two models' calls resampled on their own, the human side shared).
            reason_ci = rep_interval(diff_reps(res_m["fid_primary_reps"], res_m["fid_reason_reps"]))
            if "old" in gens and "new" in gens:
                traj_ci = rep_interval(diff_reps(model_results[gens["new"]]["fid_primary_reps"],
                                                 model_results[gens["old"]]["fid_primary_reps"]))
                t5 = test_T5_trajectory(fidelity_overall.get(gens["old"]), fidelity_overall.get(gens["new"]),
                                        reasoning_on=res_m["fid_reason"], reasoning_off=res_m["fid_primary"],
                                        traj_ci=traj_ci, reason_ci=reason_ci, resolve=True)
            else:
                t5 = test_T5_trajectory(None, None, reasoning_on=res_m["fid_reason"],
                                        reasoning_off=res_m["fid_primary"], reason_ci=reason_ci, resolve=True)
            if failed_controls:
                t5 = dict(t5, trajectory=_mark_uninformative(t5["trajectory"], failed_controls),
                          reasoning_reading=(_mark_uninformative(t5["reasoning_reading"], failed_controls)
                                             if t5["reasoning_reading"] else ""),
                          p_rising="F", p_falling="F", p_flat="F", resolved=True)
            test_T5_rows.append(dict(model=m, family=fam, **t5))
            numbers[f"model.{m}.T5.trajectory"] = t5["trajectory"]
            numbers[f"model.{m}.T5.reasoning_reading"] = t5["reasoning_reading"]

    # ---- family consistency (Step 4) and routing ----
    family_consistent = {}
    family_has_generations = {}
    for fam, members in members_by_family.items():
        doms = set(model_results[m]["overall"] for m in members)
        family_consistent[fam] = (len(doms) <= 1)
        gens = {generation_of[m]: m for m in members}
        # the rising-fidelity branch reads the family's T5 trajectory (every member of a family with an older and
        # a newer member carries the same generation comparison); route_resolved reads it from each model's row.
        family_has_generations[fam] = "old" in gens and "new" in gens

    pc_text = ("held" if not failed_controls
               else "failed: " + ", ".join({"FRQ": "frequency decoy (premium target)",
                                            "SOT": "compromise"}[st] for st in failed_controls))
    for model, res in model_results.items():
        fam = family_of[model]
        t5_for = next((r for r in test_T5_rows if r["model"] == model), {"trajectory": "n/a"})
        # rule 1: the three-valued router (an open reading supports no scenario)
        branch, scenario, possible = route_resolved(
            model, res["scored_cells"], res["t1"], res["t2_override"], res["t3"], res["t4"],
            t5_for, res["ginfo"], res["agree"],
            family_consistent.get(fam, True), family_has_generations.get(fam, False),
            effect_classes=res["eff_cls"], overall=res["overall"], t2_state=res["t2_state"])
        accounts = attribute_effect_accounts(model, res["scored_cells"], res["recog_by_struct"], criterion,
                                             res["no_counterpart"], effect_classes=res["eff_cls"],
                                             pooled=res["pooled"], phantom_retrieval=(model in phantom_retrieval))
        mla, n_agree, n_elig = model_level_account(accounts, criterion)
        if res["ginfo"]["not_assessable"]:
            mla = "none (model not assessable)"   # no account is claimed for a model that fails Step 0b
        over_notes = [f"{r['effect']}: {r['over_reading']}" for r in effect_class_rows
                      if r["model"] == model and r["over_reading"]]
        routing_rows.append(dict(model=model, family=fam, branch=branch, scenario=scenario,
                                 model_level_account=(mla if res["ginfo"]["not_assessable"]
                                                      else f"{mla} ({n_agree} of {n_elig} eligible effects agree)"),
                                 per_effect_accounts=";".join(f"{k}={v}" for k, v in sorted(accounts.items())),
                                 over_readings=" | ".join(over_notes), positive_controls=pc_text,
                                 possible_scenarios=";".join(possible),
                                 qualifier=(S1_QUALIFIER if "; qualifier: " in branch else ""),
                                 open_pattern_tests=(branch.split("(open: ", 1)[1].rstrip(")").replace(", ", ";")
                                                     if "; qualifier: " in branch else "")))
        numbers[f"model.{model}.scenario_qualifier"] = (
            routing_rows[-1]["qualifier"] + (" (open: " + routing_rows[-1]["open_pattern_tests"].replace(";", ", ")
                                             + ")" if routing_rows[-1]["open_pattern_tests"] else ""))
        numbers[f"model.{model}.scenario"] = scenario
        numbers[f"model.{model}.branch"] = branch
        numbers[f"model.{model}.model_level_account"] = mla
        for st, acc in accounts.items():
            numbers[f"model.{model}.account.{st}"] = acc

    # ---- S7 human-side scenario (four or more of the six non-similarity effects fail) ----
    s7_triggered = most_failed
    if surprise_human_rows is not None:
        sgate7, _, _, scontrols, smost = human_gate(surprise_human_rows, design, drop_confirm)
        s7_triggered = smost
        routing_rows.append(dict(model="(human data)", family="-",
                                 branch="Step 0a: four or more of the six non-similarity effects fail the human criterion",
                                 scenario="S7" if s7_triggered else "S7-not-triggered",
                                 model_level_account="-",
                                 per_effect_accounts=";".join(f"{st}={'fail' if not sgate7[st]['replicated'] else 'replicate'}" for st in EFFECTS)))
        numbers["human.surprise.scenario"] = "S7" if s7_triggered else "S7-not-triggered"
        numbers["human.surprise.n_failed"] = sum(1 for st in REGULARITY_EFFECTS if not sgate7[st]["replicated"])

    # =========================== WRITE THE PACK ===========================
    _write_csv(os.path.join(PACK, "human_benchmarks.csv"),
               ["effect", "category", "tier", "format", "effect_pp", "ci_lo_pp", "ci_hi_pp",
                "n", "n_clusters", "first_trial_pp", "bf10"], bench_rows)
    _write_csv(os.path.join(PACK, "fidelity_map.csv"),
               ["model", "structure", "tier", "format", "human_pp", "model_pp", "deviation_pp", "n_calls",
                "boot_lo_pp", "boot_hi_pp", "max_draws_per_grid_point", "ceiling_flag", "class", "class_basis"],
               fidelity_rows)
    _write_csv(os.path.join(PACK, "category_map.csv"),
               ["model", "effect", "category", "tier", "format", "human_pp", "human_ci_lo_pp", "human_ci_hi_pp",
                "model_pp", "n_calls", "boot_lo_pp", "boot_hi_pp", "class", "class_basis"], category_rows)
    _write_csv(os.path.join(PACK, "no_room_cells.csv"),
               ["model", "level", "category", "tier", "format", "effect"], no_room_rows)
    _write_csv(os.path.join(PACK, "effect_classes.csv"),
               ["model", "effect", "human_gate", "human_pp", "model_pp", "deviation_pp", "n_calls", "boot_lo_pp",
                "boot_hi_pp", "max_draws_per_grid_point", "class", "descriptive_class", "prompt_sensitive",
                "paraphrase_pp", "over_reading", "class_basis"], effect_class_rows)
    _write_csv(os.path.join(PACK, "agreement_scores.csv"),
               ["model", "class", "effects_classed", "sign_agreement", "mad_pp", "calibration_slope",
                "cells_scored", "cells_excluded"], agreement_rows)
    gates_rows = []
    for st in EFFECTS:
        gates_rows.append(dict(gate_type="human_effect", key=st, replicated=criterion[st]["replicated"],
                               confirmatory=criterion[st]["confirmatory"], direction_ok=criterion[st]["right_direction"],
                               holm_family=criterion[st]["holm_family"],
                               holm_p=round(criterion[st]["holm_p"], 5), bf10=round(criterion[st]["bf10"], 3),
                               delta_pp=round(criterion[st]["delta_pp"], 2),
                               parse_rate="", refusal_rate="", not_assessable="",
                               is_positive_control=criterion[st]["is_positive_control"]))
    for mg in model_gate_rows:
        gates_rows.append(dict(gate_type="model", key=mg["model"], replicated="", confirmatory="",
                               direction_ok="", holm_family="", holm_p="", bf10="", delta_pp="",
                               parse_rate=mg["parse_rate"], refusal_rate=mg["refusal_rate"],
                               not_assessable=mg["not_assessable"], is_positive_control=""))
    _write_csv(os.path.join(PACK, "validity_criteria.csv"),
               ["gate_type", "key", "replicated", "confirmatory", "direction_ok", "holm_family", "holm_p",
                "bf10", "delta_pp", "parse_rate", "refusal_rate", "not_assessable", "is_positive_control"],
               gates_rows)
    _write_csv(os.path.join(TESTS_DIR, "T1_memorization.csv"),
               ["model", "fidelity_t1", "fidelity_t2", "slope", "drop", "drop_lo", "drop_hi", "reading",
                "paired_categories", "descriptive_fidelity_all_categories_t1",
                "descriptive_fidelity_all_categories_t2", "descriptive_fidelity_invented_tier"], test_T1_rows)
    _write_csv(os.path.join(TESTS_DIR, "T1_memorization_sensitivity.csv"),
               ["model", "primary_reading", "restricted_reading", "restricted_drop", "restricted_drop_lo",
                "restricted_drop_hi", "restricted_slope", "n_slices_dropped", "adjusted_slope", "adjusted_drop",
                "adjusted_drop_lo", "adjusted_drop_hi", "baseline_coef", "target_coef", "covariates_omitted",
                "n_slices", "adjusted_reading"], t1_sens_rows)
    _write_csv(os.path.join(TESTS_DIR, "T2_recognition.csv"),
               ["model", "structure", "recognition_rate", "recognition_lo", "recognition_hi", "behavior_pp",
                "behavior_lo_pp", "behavior_hi_pp", "knows", "shows", "reading", "knows_state", "shows_state",
                "override_state"], test_T2_rows)
    _write_csv(os.path.join(TESTS_DIR, "T3_ladder.csv"),
               ["model", "high_rung", "mid_rung", "low_rung", "tmb_lo", "tmb_hi", "bmm_lo", "bmm_hi", "reading",
                "attribution", "missed_effects", "missed_recognition"], test_T3_rows)
    _write_csv(os.path.join(TESTS_DIR, "T4_formats.csv"),
               ["model", "numbers", "words", "pictures", "undefined", "diff_lo", "diff_hi", "reading",
                "numbers_picture_order", "reading_picture_order"], test_T4_rows)
    _write_csv(os.path.join(TESTS_DIR, "T4_format_points.csv"),
               ["model", "format", "compared_on", "effect", "categories", "human_pp", "model_pp", "n_calls",
                "boot_lo_pp", "boot_hi_pp", "max_draws_per_grid_point"], t4_point_rows)
    tu_row = {k: (round(v, 5) if isinstance(v, float) else v) for k, v in topup.items() if k != "topup_pids"}
    _write_csv(os.path.join(TESTS_DIR, "similarity_topup_check.csv"),
               ["backbone_pp", "topup_pp", "diff_pp", "diff_se_pp", "z", "p", "fired", "benchmark",
                "n_backbone", "n_topup", "n_topup_participants", "n_slices"], [tu_row])
    _write_csv(os.path.join(TESTS_DIR, "positive_controls.csv"),
               ["control", "delta_pp", "ci_lo_pp", "ci_hi_pp", "p", "bf10", "holds", "affected_if_failed"],
               [dict(control="frequency decoy, premium-target cells",
                     **{k: (round(v, 5) if isinstance(v, float) else v) for k, v in pc["frq_premium"].items()
                        if k != "n_strata"},
                     affected_if_failed="FRQ fidelity-map row; T1, T2 (FRQ), T3, T4, T5"),
                dict(control="compromise (its replication criterion)", delta_pp=round(pc["sot"]["delta_pp"], 2),
                     ci_lo_pp=round(criterion["SOT"]["ci_lo_pp"], 2), ci_hi_pp=round(criterion["SOT"]["ci_hi_pp"], 2),
                     p=round(criterion["SOT"]["holm_p"], 5), bf10=round(criterion["SOT"]["bf10"], 3), holds=pc["sot"]["holds"],
                     affected_if_failed="SOT fidelity-map row; T1, T2 (SOT), T3, T4, T5")])
    _write_csv(os.path.join(TESTS_DIR, "T5_trajectory.csv"),
               ["model", "family", "trajectory", "delta", "traj_lo", "traj_hi", "reasoning_reading", "reason_lo",
                "reason_hi"], test_T5_rows)
    _write_csv(os.path.join(TESTS_DIR, "decoy_target_asymmetry.csv"),
               ["effect", "hd_target_pp", "hf_target_pp", "hd_minus_hf_pp", "reading"], asym_rows)
    _write_csv(os.path.join(TESTS_DIR, "prompt_mode_divergence.csv"),
               ["model", "arm", "neutral_pp", "secondary_pp", "divergence_pp", "n_calls_neutral",
                "n_calls_secondary", "reading"], divergence_rows)
    ft_rows = [dict(effect=st, **{k: (round(v, 5) if isinstance(v, float) else v) for k, v in d.items()})
               for st, d in ft["per_effect"].items()]
    _write_csv(os.path.join(TESTS_DIR, "first_trial_check.csv"),
               ["effect", "full_pp", "first_pp", "later_pp", "divergence_pp", "first_minus_later_se_pp",
                "z", "p", "holm_p", "holm_reject", "diverges", "n_first", "n_full"], ft_rows)
    _write_csv(os.path.join(TESTS_DIR, "phantom_equivalence.csv"),
               ["delta_pp", "ci90_lo_pp", "ci90_hi_pp", "band_pp", "p_tost", "equivalent"],
               [{k: (round(v, 6) if isinstance(v, float) else v) for k, v in peq.items()}])
    _write_csv(os.path.join(TESTS_DIR, "format_interaction.csv"),
               ["test", "effect", "format", "categories", "format_pp", "numbers_pp", "interaction_pp",
                "ci_lo_pp", "ci_hi_pp", "z", "raw_p", "holm_p", "significant", "n_format", "n_numbers",
                "reading"], list(fmt_tests.values()))
    _write_csv(os.path.join(TESTS_DIR, "format_interaction_models.csv"),
               ["model", "test", "human_interaction_pp", "model_interaction_pp", "n_calls", "boot_lo_pp",
                "boot_hi_pp", "reading"], fmt_model_rows)
    _write_csv(os.path.join(PACK, "no_human_counterpart.csv"),
               ["model", "effect", "tier", "format", "model_pp", "human_pp", "n_calls", "boot_lo_pp", "boot_hi_pp",
                "human_gate"], no_counterpart_rows)
    _write_csv(os.path.join(PACK, "descriptive_slices.csv"),
               ["source", "category", "tier", "format", "effect_pp", "ci_lo_pp", "ci_hi_pp", "boot_lo_pp",
                "boot_hi_pp", "n", "baseline_target_pct", "reason"], descriptive_rows)
    _write_csv(os.path.join(PACK, "price_free_arm.csv"),
               ["source", "effect", "effect_pp", "ci_lo_pp", "ci_hi_pp", "boot_lo_pp", "boot_hi_pp", "n"], pf_rows)
    _write_csv(os.path.join(PACK, "sensitivity_deviation_human.csv"),
               ["effect", "primary_pp", "sensitivity_pp", "primary_replicated", "sensitivity_replicated",
                "sensitivity_holm_p", "sensitivity_bf10"], sens_human_rows)
    _write_csv(os.path.join(PACK, "sensitivity_deviation_models.csv"),
               ["model", "primary_class", "sensitivity_class", "primary_T1", "sensitivity_T1"], sens_model_rows)
    secondary_rows = [dict(
        contrast="range_minus_frequency",
        frequency_pp=round(frq_pooled["delta_pp"], 2), range_pp=round(rng_pooled["delta_pp"], 2),
        contrast_pp=round(rng_minus_frq_pp, 2),
        reading=("range exceeds frequency (registered ordering)" if rng_minus_frq_pp > 0
                 else "range does not exceed frequency (against the secondary prediction)"))]
    _write_csv(os.path.join(PACK, "secondary_contrasts.csv"),
               ["contrast", "frequency_pp", "range_pp", "contrast_pp", "reading"], secondary_rows)
    for r in routing_rows:
        r["scenario_name"] = SCENARIO_NAMES.get(r["scenario"], r["scenario"])
    _write_csv(os.path.join(PACK, "tree_routing.csv"),
               ["model", "family", "branch", "scenario", "scenario_name", "model_level_account",
                "per_effect_accounts", "over_readings", "positive_controls", "possible_scenarios", "qualifier",
                "open_pattern_tests"],
               routing_rows)

    numbers["design.source"] = design.source
    numbers["design.deviation_flag_mismatch"] = ";".join(f"{c}|t{t}|{f}" for (c, t, f) in design.deviation_flag_mismatch)
    numbers["design.compromise_flag_mismatch"] = ";".join(f"{c}|t{t}|{f}" for (c, t, f) in design.compromise_flag_mismatch)
    json.dump(numbers, open(os.path.join(PACK, "numbers.json"), "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)

    dashboard = dict(
        meta=dict(title="LLM context-effect fidelity map", mode=mode, seed=seed,
                  generated="2026-06-13"),
        agreement=agreement_rows, scenarios=[dict(model=r["model"], scenario=r["scenario"]) for r in routing_rows],
        human_gate={st: criterion[st]["replicated"] for st in EFFECTS})
    json.dump(dashboard, open(os.path.join(PACK, "dashboard_data.json"), "w", encoding="utf-8", newline="\n"),
              indent=2, sort_keys=True)

    open(os.path.join(FIGS_DIR, "draw_fidelity_map.py"), "w", encoding="utf-8", newline="\n").write(
        "# A placeholder. The fidelity-map figure is drawn at Stage 2\n"
        "# from results_pack/numbers.json; this stub keeps figures/ present in the pack so the\n"
        "# contract-C directory shape is complete. It reads numbers.json and would render the diagonal\n"
        "# plot; intentionally no plotting dependency is imported (the public repo runs on bare Python).\n"
        "import json, os\n"
        "N = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'numbers.json')))\n"
        "print('fidelity-map figure would be drawn from', len(N), 'numbers.json keys')\n")

    _write_run_report(seed, runtime, mode, human_rows, models, criterion, model_gate_rows, routing_rows)

    return dict(numbers=numbers, criterion=criterion, controls_held=controls_held, most_failed=most_failed,
                fidelity_rows=fidelity_rows, agreement_rows=agreement_rows, routing_rows=routing_rows,
                model_gate_rows=model_gate_rows, test_T1_rows=test_T1_rows, test_T2_rows=test_T2_rows,
                test_T3_rows=test_T3_rows, test_T4_rows=test_T4_rows, test_T5_rows=test_T5_rows,
                bench_rows=bench_rows, model_results=model_results, s7_triggered=s7_triggered,
                asym_rows=asym_rows, divergence_rows=divergence_rows,
                rng_minus_frq_pp=rng_minus_frq_pp, first_trial=ft, phantom=peq, format_tests=fmt_tests,
                fmt_model_rows=fmt_model_rows, no_counterpart_rows=no_counterpart_rows,
                descriptive_rows=descriptive_rows, sens_human_rows=sens_human_rows,
                sens_model_rows=sens_model_rows, sensitivity_gate=sgate, t1_sens_rows=t1_sens_rows,
                pooled=pooled_h, effect_class_rows=effect_class_rows, t4_point_rows=t4_point_rows,
                topup=topup, positive_controls=pc, failed_controls=failed_controls,
                category_rows=category_rows, no_room_rows=no_room_rows)


def _write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k, "")) for k in fields})


def _write_run_report(seed, runtime, mode, human_rows, models, criterion, model_gate_rows, routing_rows):
    lines = [
        "# RUN_REPORT", "",
        "(Auto-written every run.)", "",
        f"- mode: {mode}",
        f"- seed: {seed}",
        f"- python: {platform.python_version()} ({platform.system()})",
        f"- runtime_sec: {round(runtime, 2)}",
        f"- human choice rows: {len(human_rows)}",
        f"- models scored: {len([m for m in models])}",
        f"- Bayes factor: half-normal prior, positive direction, scale {RC.BF_PRIOR_SCALE_PP} points",
        f"- tie-break for a majority class: {TIE_BREAK_RULE}",
        "", "## Exclusion accounting (model calls)", "",
        "| model | parse_rate | refusal_rate | cells lost | not assessable |", "|---|---|---|---|---|",
    ]
    for mg in model_gate_rows:
        lines.append(f"| {mg['model']} | {mg['parse_rate']} | {mg['refusal_rate']} | "
                     f"{mg['n_lost_cells']}+{mg['n_no_room_cells']} no-room | {mg['not_assessable']} |")
    lines += ["", "## Human criterion (Step 0a)", "",
              "| effect | Holm family | replicated | direction ok | Holm p | BF10 |", "|---|---|---|---|---|---|"]
    for st in EFFECTS:
        lines.append(f"| {st} | {criterion[st]['holm_family']} | {criterion[st]['replicated']} | {criterion[st]['right_direction']} | "
                     f"{round(criterion[st]['holm_p'], 4)} | {round(criterion[st]['bf10'], 2)} |")
    lines += ["", "## Scenario routing", "", "| model | scenario | name |", "|---|---|---|"]
    for r in routing_rows:
        lines.append(f"| {r['model']} | {r['scenario']} | {SCENARIO_NAMES.get(r['scenario'], r['scenario'])} |")
    open(os.path.join(PACK, "RUN_REPORT.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


# ===================================================================================================
# THE SYNTHETIC DRESS REHEARSAL (default run). Plants the whole tree, asserts recovery + routing.
# ===================================================================================================
# The synthetic model arm of the PASS/FAIL rehearsal: the registered grid (orders x paraphrases x 10 draws, 60
# for pictures) with answers allocated EXACTLY at the planted shares, so the pass condition tests the code and
# not the luck of one seed. The set binomial draws (every call an independent draw at the planted share, and
# a 90-percent-consistent variant) are re-routed at the same seed in a REPORTED section of the selftest, and
# power/model_noise_stability.py measures their routing rates over many seeds: under that noise some
# planted routes are unstable, a design finding, not a code defect.
REHEARSAL_CONSISTENCY = "exact"
REHEARSAL_WITH_FORMATS = ("FAITHFUL", "REASONER", "WALK2_MIXED", "PARROT", "OVERRIDER", "DIVIDED_A", "DIVIDED_B",
                          "CONVERGE_OLD", "CONVERGE_NEW", "WALK1_PARROT", "CEILING", "REFUSER")


def run_rehearsal(consistency="default"):
    t0 = time.time()
    seed = 20260613
    rng = random.Random(seed)
    if consistency == "default":
        consistency = REHEARSAL_CONSISTENCY
    N_HUMAN = 1400      # per cell; large enough for the planted criterion pass/fail AND the planted tier
    #                     gradients to be unambiguous. Raised from 700 on 2026-09-29: with the calibration
    #                     record now applied (the invented kettles compromise slice is descriptive only), the
    #                     tier-3 human benchmark rests on fewer slices, and at 700 its sampling error moved
    #                     the faithful archetype's memorization slope past the flat cutoff on the new random
    #                     stream. The rehearsal tests routing, not inference; the side datasets below that
    #                     test the first-trial rule and the criterion use the planned sizes.
    N_MODEL = 200       # used only by the June exact allocation (noise="exact"). Since the pass
    # the synthetic model arm follows the registered call plan instead: every
    #                     grid point (stimulus x order x paraphrase) is called 10 times (pictures 60), each
    #                     call an independent draw at the planted share, so the rehearsal meets the sampling
    #                     noise of a default temperature. power/model_noise_stability.py reports how
    #                     often each archetype routes as planted across many seeds under this noise.
    N_TOPUP = 1000      # the similarity top-up survey's participants (seven similarity choices each)

    # main human dataset (with formats). 2026-09-29: the main dataset carries NO planted first-trial
    # divergence (it is the null check for the first-trial rule); the divergence is planted in its own
    # dataset below, at the planned first-trial cell sizes. It carries the similarity top-up participants
    # with no planted difference (the null check for the top-up rule).
    H = synth.gen_human(N_HUMAN, rng, icc=0.10, with_formats=True, sim_topup_participants=N_TOPUP)
    # a separate S7 "surprise" human dataset where most effects fail the criterion.
    H_surprise = synth.gen_human(N_HUMAN, rng, icc=0.10, surprise=True)

    models = {}
    for m in synth.MODEL_ARCHETYPES:
        with_formats = m in REHEARSAL_WITH_FORMATS
        models[m] = synth.gen_model(m, N_MODEL, rng, with_formats=with_formats, consistency=consistency)
    persona_seq_rng = random.Random(seed + 101)
    models["FAITHFUL"] += synth.gen_persona_seq_arms("FAITHFUL", N_MODEL, persona_seq_rng, with_formats=True,
                                                     consistency=consistency)

    design = Design.for_synth()
    res = build_pack(H, models, human_rows_with_formats=H, human_rows_first_trial=H,
                     seed=seed, runtime=0.0, mode="REHEARSAL", surprise_human_rows=H_surprise, design=design)
    runtime = time.time() - t0
    _write_run_report(seed, runtime, "REHEARSAL", H, models, res["criterion"], res["model_gate_rows"], res["routing_rows"])
    # keep only what the checks below read, so the side datasets fit in memory (no file is touched)
    n_models = len(models)
    models = {"FAITHFUL": models["FAITHFUL"]}
    H_surprise = None
    _INDEX_CACHE.clear()   # the cache also holds the released list

    # ---------------- ASSERTIONS (rule C7 + contract-C pass condition) ----------------
    checks = []

    def find_route(model):
        return next((r for r in res["routing_rows"] if r["model"] == model), None)

    missing = _scan_missing(PACK)
    checks.append(("pack renders with ZERO missing values", len(missing) == 0, str(missing[:3])))

    need_keys = [
        "human.FRQ.pooled.delta_pp", "human.FRQ.criterion.replicated", "human.PHT.within_band",
        "human.first_trial.fallback_triggered", "model.FAITHFUL.dominant_class",
        "model.FAITHFUL.scenario", "model.OVERRIDER.scenario", "model.PARROT.scenario",
        "model.REASONER.T4.reading", "model.WALK2_MIXED.account.SOT",
        "human.PHT.equivalence.ci90_lo_pp", "human.format_interaction.FRQ.pictures.significant",
        "model.FAITHFUL.model_level_account", "model.PARROT.no_human_counterpart",
    ]
    have = all(k in res["numbers"] for k in need_keys)
    checks.append(("numbers.json carries every key the manuscript references", have,
                   str([k for k in need_keys if k not in res["numbers"]])))

    g = res["criterion"]
    checks.append(("human criterion: positive controls FRQ+SOT replicate", g["FRQ"]["replicated"] and g["SOT"]["replicated"], ""))
    checks.append(("human criterion: phantom PHT fails (planted null) and is EQUIVALENT (90% interval inside +/-4pp)",
                   (not g["PHT"]["replicated"]) and res["numbers"]["human.PHT.within_band"],
                   f"PHT delta_pp={g['PHT']['delta_pp']:.2f} CI90=[{res['phantom']['ci90_lo_pp']:.2f}, {res['phantom']['ci90_hi_pp']:.2f}]"))

    t1_parrot = next(r for r in res["test_T1_rows"] if r["model"] == "PARROT")
    checks.append(("T1 detects PARROT steep memorization gradient", t1_parrot["reading"].startswith("steep"), t1_parrot["reading"]))
    t1_faith = next(r for r in res["test_T1_rows"] if r["model"] == "FAITHFUL")
    # the flat reading needs the interval of the drop below 0.30; at the rehearsal's human
    # sizes that interval can be wider, so FAITHFUL's T1 is flat or not resolved, and never steep.
    checks.append(("T1 reads FAITHFUL as flat, or leaves it not resolved (never steep)",
                   (t1_faith["reading"].startswith("flat") or t1_faith["reading"].startswith(NOT_RESOLVED))
                   and t1_faith["p_steep"] != "T", t1_faith["reading"][:160]))
    t2_over = [r for r in res["test_T2_rows"] if r["model"] == "OVERRIDER" and r["structure"] == "FRQ"]
    checks.append(("T2 reads OVERRIDER as recognizes-but-does-not-show",
                   bool(t2_over) and t2_over[0]["reading"].startswith("recognizes-but-does-not-show"),
                   t2_over[0]["reading"] if t2_over else "missing"))
    t3_reason = next(r for r in res["test_T3_rows"] if r["model"] == "REASONER")
    checks.append(("T3 detects REASONER ladder decline", t3_reason["reading"].startswith("declines"), t3_reason["reading"]))
    t4_reason = next(r for r in res["test_T4_rows"] if r["model"] == "REASONER")
    checks.append(("T4 reported descriptively for REASONER (no reading, decides no scenario)",
                   t4_reason["reading"].startswith("descriptive") and t4_reason["p_falls"] == "F", t4_reason["reading"]))
    t5_conv = [r for r in res["test_T5_rows"] if r["model"] == "CONVERGE_NEW"]
    checks.append(("T5 detects CONVERGE family rising trajectory",
                   bool(t5_conv) and t5_conv[0]["trajectory"].startswith("newer more faithful"),
                   t5_conv[0]["trajectory"] if t5_conv else "missing"))

    mg = {r["model"]: r for r in res["model_gate_rows"]}
    checks.append(("model criterion: REFUSER -> not assessable", mg["REFUSER"]["not_assessable"] is True, ""))
    checks.append(("model criterion: CEILING -> no-room cells flagged, not assessable",
                   mg["CEILING"]["not_assessable"] is True and mg["CEILING"]["n_no_room_cells"] > 0, ""))
    checks.append(("model criterion: FAITHFUL -> assessable", mg["FAITHFUL"]["not_assessable"] is False, ""))

    expect = {
        "FAITHFUL": "S1", "PARROT": "S2", "REASONER": "S3", "OVERRIDER": "S4",
        "CONVERGE_OLD": "S6", "CONVERGE_NEW": "S6", "WALK1_PARROT": "S2",
        "R4_ARGUABLE_OVERRIDE": "REVERSED_LADDER_OVERRIDE", "R4_ARGUABLE_NORECOG": "REVERSED_LADDER",
        "OVERSHOOT_T1": "COMPOSITE",
    }
    # a route stands only when the intervals settle every reading it depends on. At the
    # rehearsal's human sizes the memorization and format intervals of FAITHFUL, REASONER, CONVERGE_OLD,
    # WALK2_MIXED and the two reversed-ladder archetypes reach a cutoff their route depends on (for the reversed
    # ladders, the steep cutoff that the precedence rule would put ahead of the ladder), so those archetypes may
    # route to NOT_RESOLVED; they pass only if their planted scenario is among the ones left possible (never a
    # wrong scenario). Every other archetype must route exactly as planted. The rates over many seeds are the
    # stability sweep's (power/model_noise_stability.py).
    # Rule (a): FAITHFUL must reach S1, with the qualifier when its memorization reading is open.
    may_stay_open = {"REASONER", "CONVERGE_OLD", "WALK2_MIXED", "R4_ARGUABLE_OVERRIDE", "R4_ARGUABLE_NORECOG"}

    def routed_as_planted(r, want, model):
        if r is None:
            return False
        if r["scenario"] == want:
            return True
        return (model in may_stay_open and r["scenario"] == NOT_RESOLVED_SCENARIO
                and want in r["possible_scenarios"].split(";"))
    for model, want in expect.items():
        r = find_route(model)
        lbl = (f"routing: {model} -> {want}" + (" (or not resolved with {want} still possible)".format(want=want)
                                                 if model in may_stay_open else ""))
        checks.append((lbl, routed_as_planted(r, want, model),
                       (f"{r['scenario']} (possible: {r['possible_scenarios']})" if r else "missing")))
    divided = [r for r in res["routing_rows"] if r["model"] in ("DIVIDED_A", "DIVIDED_B")]
    checks.append(("routing: DIVIDED family -> S5 (family-specific)",
                   any(r["scenario"] == "S5" for r in divided),
                   ",".join(r["scenario"] for r in divided)))
    s7 = next((r for r in res["routing_rows"] if r["model"] == "(human data)"), None)
    checks.append(("routing: human data with most effects failing -> S7 (Human effects fail)",
                   s7 is not None and s7["scenario"] == "S7",
                   s7["scenario"] if s7 else "missing"))
    for model in ("CEILING", "REFUSER"):
        r = find_route(model)
        checks.append((f"routing: {model} -> CRITERION_FAIL", r is not None and r["scenario"] == "CRITERION_FAIL",
                       r["scenario"] if r else "missing"))

    w1 = find_route("WALK1_PARROT")
    checks.append(("walk-through 1 (match classic / diverge novel) -> S2 via T1", w1 and w1["scenario"] == "S2", w1["scenario"] if w1 else "missing"))
    w2 = find_route("WALK2_MIXED")
    w2_ok = w2 and ("FRQ=deep pattern-mimicry" in w2["per_effect_accounts"]) and ("SOT=rational-override" in w2["per_effect_accounts"])
    checks.append(("walk-through 2 (faithful FRQ, reversed SOT) -> per-effect accounts side by side", bool(w2_ok),
                   w2["per_effect_accounts"] if w2 else "missing"))

    frq_t1 = res["numbers"].get("human.FRQ.t1.numbers.delta_pp", 0)
    checks.append(("human FRQ tier-1 effect recovered near planted +10pp", abs(frq_t1 - 10.0) <= 3.0, f"{frq_t1}pp"))
    sim_pooled = res["numbers"].get("human.SIM.pooled.delta_pp", 0)
    # pooled over 7 published slices at tier 1, 7 at tier 2, and 3 invented slices at tier 3.
    sim_planted = 100 * synth.TRUTH["SIM"] * (7 * synth.TIER_ATTEN[1] + 7 * synth.TIER_ATTEN[2]
                                              + 3 * synth.TIER_ATTEN[3]) / 17.0
    checks.append(("human SIM relative-share effect recovered near its planted size",
                   abs(sim_pooled - sim_planted) <= 2.0, f"{sim_pooled}pp vs planted ~{round(sim_planted, 2)}pp"))

    # ==================== FIVE FIXES (2026-06-13): each ends in a rehearsal check ====================
    checks.append(("FIX1 walk-through 2 routes to PARTIAL (registered verdict, not HIGH/COMPOSITE), or is not resolved "
                   "with PARTIAL still possible",
                   routed_as_planted(w2, "PARTIAL", "WALK2_MIXED"),
                   (f"{w2['scenario']} (possible: {w2['possible_scenarios']})" if w2 else "missing")))
    pht_cells = [r for r in res["fidelity_rows"] if r["structure"] == "PHT"]
    pht_none_scored = all(r["class"] in ("excluded(criterion-exit)", "no-human-counterpart") for r in pht_cells)
    checks.append(("FIX2a phantom (criterion-failed) cells exit scoring: none score as a fidelity class",
                   pht_none_scored and len(pht_cells) > 0,
                   f"{sum(1 for r in pht_cells if r['class'] == 'excluded(criterion-exit)')} exit + "
                   f"{sum(1 for r in pht_cells if r['class'] == 'no-human-counterpart')} no-counterpart of {len(pht_cells)}"))
    rng2 = random.Random(seed + 7)
    H_two_null = synth.gen_human(N_HUMAN, rng2, icc=0.10, null_effects={"SIM"})
    g2, _, _, _, _ = human_gate(H_two_null, design)
    H_two_null = None
    _INDEX_CACHE.clear()   # the cache also holds the released list
    second_fails = (not g2["PHT"]["replicated"]) and (not g2["SIM"]["replicated"])
    others_hold = all(g2[st]["replicated"] for st in ("FRQ", "RNG", "SOT", "SYM", "MOT"))
    accounts2 = attribute_effect_accounts("FAITHFUL", [], {}, g2)
    faithful_sim = model_effect(models["FAITHFUL"], "SIM", 1, "numbers", design)[0]
    both_exit = (accounts2["PHT"].startswith("human-null") and accounts2["SIM"].startswith("human-null")
                 and gate_exit_class(faithful_sim) == "no-human-counterpart")
    checks.append(("FIX2b criterion-driven exit is general: a SECOND criterion-failed effect (SIM) also exits",
                   second_fails and others_hold and both_exit,
                   f"PHT_repl={g2['PHT']['replicated']} SIM_repl={g2['SIM']['replicated']} "
                   f"FAITHFUL SIM t1={round((faithful_sim or 0) * 100, 2)}pp -> {gate_exit_class(faithful_sim)}"))
    rng_vs_frq = res["numbers"].get("human.RNG_vs_FRQ.contrast_pp")
    checks.append(("FIX3 secondary contrast range > frequency computed and ordered as registered",
                   rng_vs_frq is not None and res["numbers"].get("human.RNG_vs_FRQ.range_exceeds_frequency") is True
                   and rng_vs_frq > 0, f"RNG-FRQ={rng_vs_frq}pp"))
    frq_hd = res["numbers"].get("human.FRQ.decoy_target.hd_minus_hf_pp")
    rng_hd = res["numbers"].get("human.RNG.decoy_target.hd_minus_hf_pp")
    frq_read = res["numbers"].get("human.FRQ.decoy_target.reading", "")
    checks.append(("FIX4 decoy-target HD/HF asymmetry moderator computed with planted HD>HF direction",
                   frq_hd is not None and rng_hd is not None and frq_hd > 0 and rng_hd > 0
                   and "Heath-Chatterjee" in frq_read, f"FRQ HD-HF={frq_hd}pp ({frq_read[:40]})"))
    persona_row = next((r for r in res["divergence_rows"] if r["model"] == "FAITHFUL" and r["arm"] == "persona"), None)
    seq_row = next((r for r in res["divergence_rows"] if r["model"] == "FAITHFUL" and r["arm"] == "sequential"), None)
    persona_ok = persona_row is not None and persona_row["divergence_pp"] > 2.0 and "persona more faithful" in persona_row["reading"]
    seq_ok = seq_row is not None and seq_row["divergence_pp"] < -2.0 and "within-session history" in seq_row["reading"]
    checks.append(("FIX5 neutral-vs-persona divergence computed with planted persona-stronger reading",
                   persona_ok, persona_row["reading"] if persona_row else "missing"))
    checks.append(("FIX5 single-shot-vs-sequential divergence computed with planted history reading",
                   seq_ok, seq_row["reading"] if seq_row else "missing"))

    # ==================== THE 2026-09-29 revision: one rehearsal case per defect ====================
    # D1: a significantly REVERSED human effect must not replicate.
    H_rev = synth.gen_human(N_HUMAN, random.Random(seed + 302), icc=0.10, effect_overrides={"RNG": -0.05})
    grev, _, _, _, _ = human_gate(H_rev, design)
    H_rev = None
    _INDEX_CACHE.clear()   # the cache also holds the released list
    checks.append(("D1 a significantly REVERSED human effect (RNG planted at -5pp) is NOT replicated",
                   grev["RNG"]["holm_reject"] and grev["RNG"]["delta_pp"] < 0 and not grev["RNG"]["replicated"]
                   and grev["RNG"]["bf10"] < 1.0,
                   f"RNG {grev['RNG']['delta_pp']:.2f}pp Holm p={grev['RNG']['holm_p']:.2e} BF10={grev['RNG']['bf10']:.3g}"))
    checks.append(("D1 registered half-normal Bayes factor: FRQ BF10 > 3, phantom BF10 < 1",
                   g["FRQ"]["bf10"] > BF_GATE and g["PHT"]["bf10"] < 1.0,
                   f"FRQ BF10={g['FRQ']['bf10']:.3g} PHT BF10={g['PHT']['bf10']:.3g}"))
    # D2: the Holm families.
    fam_ok = (g["SIM"]["holm_family"] == "similarity"
              and all(g[st]["holm_family"] == "non_similarity" for st in REGULARITY_EFFECTS))
    checks.append(("D2 Holm within families: six non-similarity effects together, similarity alone", fam_ok,
                   ",".join(f"{st}:{g[st]['holm_family']}" for st in EFFECTS)))
    # D3: the first-trial rule.
    checks.append(("D3 first-trial rule: no false alarm on the main data (no planted divergence)",
                   res["numbers"]["human.first_trial.fallback_triggered"] is False,
                   f"max |full-first|={res['numbers']['human.first_trial.divergence_pp']}pp"))
    H_break = synth.gen_human(N_HUMAN, random.Random(seed + 301), icc=0.10, first_trial_break=True,
                              published_n_per_tier=350)
    ftb = first_trial_check(H_break, design, {"SOT": design.compromise_descriptive})
    gfb, _, _, _, _ = human_gate([r for r in H_break if _int(r["trial_position"]) == 1], design,
                                 {"SOT": design.compromise_descriptive}, fallback=True)
    H_break = None   # release each side dataset once its check is computed (memory only; no file is touched)
    _INDEX_CACHE.clear()   # the cache also holds the released list
    floor_ok = all(gfb[st]["confirmatory"] == (gfb[st]["replicated"] and gfb[st]["delta_pp"] >= FIRST_TRIAL_MIN_EFFECT_PP)
                   for st in EFFECTS)
    checks.append(("D3 first-trial rule fires on the planted divergence at planned first-trial sizes; the fallback applies the 8-point floor",
                   ftb["fired"] and ftb["fired_effects"] == ["FRQ"] and floor_ok,
                   f"fired={ftb['fired_effects']} FRQ |full-first|={ftb['per_effect']['FRQ']['divergence_pp']:.2f}pp "
                   f"non-confirmatory after fallback: {[st for st in EFFECTS if gfb[st]['replicated'] and not gfb[st]['confirmatory']]}"))
    # D4 is the phantom equivalence check above. D5: the format interaction.
    fsig = [k for k, v in res["format_tests"].items() if v["significant"]]
    checks.append(("D5 format interaction: none detected on the main data (no planted interaction)",
                   len(res["format_tests"]) == 4 and not fsig, f"tests={sorted(res['format_tests'])} significant={fsig}"))
    H_fmt = synth.gen_human(N_HUMAN, random.Random(seed + 303), icc=0.10, with_formats=True,
                            format_attenuation={"pictures": 0.0})
    ftests = format_interaction_tests(H_fmt, design)
    H_fmt = None
    _INDEX_CACHE.clear()   # the cache also holds the released list
    checks.append(("D5 format interaction: planted pictures attenuation detected (FRQ:pictures, Holm), words untouched",
                   ftests["FRQ:pictures"]["significant"] and ftests["FRQ:pictures"]["interaction_pp"] < 0
                   and not ftests["FRQ:words"]["significant"],
                   f"FRQ:pictures {ftests['FRQ:pictures']['interaction_pp']}pp Holm p={ftests['FRQ:pictures']['holm_p']}; "
                   f"FRQ:words {ftests['FRQ:words']['interaction_pp']}pp"))
    # D6: the calibration record is read.
    cd_h = [r for r in res["descriptive_rows"] if r["source"] == "human"]
    checks.append(("D6 compromise cells whose target starts ahead are held out of the pooled compromise contrast and reported as descriptive",
                   len(cd_h) == len(design.compromise_descriptive) and len(cd_h) > 0,
                   f"{len(cd_h)} descriptive slices: {res['numbers']['design.compromise_descriptive_slices']}"))
    sot_full = human_contrast(H, "SOT", (1, 2, 3), "numbers", design)
    sot_drop = human_contrast(H, "SOT", (1, 2, 3), "numbers", design, design.compromise_descriptive)
    checks.append(("D6 the pooled compromise criterion reads the contrast with the descriptive slices removed",
                   abs(g["SOT"]["delta_pp"] - sot_drop["delta"] * 100) < 1e-9
                   and abs(sot_full["delta"] - sot_drop["delta"]) > 1e-6,
                   f"criterion {g['SOT']['delta_pp']:.3f}pp = held-out contrast {sot_drop['delta'] * 100:.3f}pp "
                   f"(all slices {sot_full['delta'] * 100:.3f}pp)"))
    sg = res["sensitivity_gate"]
    checks.append(("D6 registered sensitivity (every deviation-flagged slice excluded) computed; positive controls still replicate",
                   sg["FRQ"]["replicated"] and sg["SOT"]["replicated"] and len(res["sens_model_rows"]) == n_models,
                   f"criterion changes: '{res['numbers']['human.sensitivity_deviation_excluded.gate_changes']}'"))
    # D7: the memorization sensitivity.
    s_par = next(r for r in res["t1_sens_rows"] if r["model"] == "PARROT")
    s_fai = next(r for r in res["t1_sens_rows"] if r["model"] == "FAITHFUL")
    checks.append(("D7 memorization sensitivity: PARROT stays steep (in-limit, and baseline-adjusted); FAITHFUL stays "
                   "flat or not resolved, never steep (both re-readings are resolved against their intervals)",
                   s_par["restricted_reading"].startswith("steep") and s_par["adjusted_reading"].startswith("steep")
                   and all(s_fai[k].startswith("flat") or s_fai[k].startswith(NOT_RESOLVED)
                           for k in ("restricted_reading", "adjusted_reading")),
                   f"PARROT adj drop={s_par['adjusted_drop']} ({s_par['n_slices']} slices, {s_par['n_slices_dropped']} dropped); "
                   f"FAITHFUL adj slope={s_fai['adjusted_slope']}"))
    # D10: the reversed ladder.
    r4o = next(r for r in res["test_T3_rows"] if r["model"] == "R4_ARGUABLE_OVERRIDE")
    r4n = next(r for r in res["test_T3_rows"] if r["model"] == "R4_ARGUABLE_NORECOG")
    checks.append(("D10 Reviewer 4's pattern WITH recognition -> reversed ladder, rational override on choice sets that offer an argument",
                   r4o["reversed"] and r4o["attribution"] == ARGUMENT_OVERRIDE,
                   f"{r4o['reading'][:60]} missed={r4o['missed_effects']} rec={r4o['missed_recognition']}"))
    checks.append(("D10 Reviewer 4's pattern WITHOUT recognition -> reversed ladder, no account attributed",
                   r4n["reversed"] and r4n["attribution"] == "no account attributed",
                   f"missed={r4n['missed_effects']} rec={r4n['missed_recognition']}"))
    # R1: an effect without a human counterpart.
    par_nc = [r for r in res["no_counterpart_rows"] if r["model"] == "PARROT" and r["effect"] == "PHT"]
    anti_on_failed = [r for r in res["fidelity_rows"] if not g[r["structure"]]["replicated"] and r["class"] == "ANTI"]
    checks.append(("R1 PARROT's published-tier phantom (humans null) is listed as an effect without a human counterpart; no ANTI on a failed effect",
                   len(par_nc) >= 1 and not anti_on_failed,
                   f"{[(r['tier'], r['model_pp']) for r in par_nc]}"))
    # R2: S7 needs four of the six non-similarity effects.
    H4 = synth.gen_human(N_HUMAN, random.Random(seed + 304), icc=0.10, null_effects={"RNG", "SYM", "MOT"})
    _, _, _, _, m4 = human_gate(H4, design)
    H4 = None
    _INDEX_CACHE.clear()   # the cache also holds the released list
    H3 = synth.gen_human(N_HUMAN, random.Random(seed + 305), icc=0.10, null_effects={"RNG", "SYM", "SIM"})
    g3, _, _, _, m3 = human_gate(H3, design)
    H3 = None
    _INDEX_CACHE.clear()   # the cache also holds the released list
    checks.append(("R2 S7 needs four of the six non-similarity effects: 4 fail -> S7; 3 fail (+ similarity) -> not S7",
                   m4 is True and m3 is False and not g3["SIM"]["replicated"], f"4-fail->{m4}, 3-fail+SIM->{m3}"))
    # R3: the model-level account rule.
    fa = find_route("FAITHFUL"); re_ = find_route("REASONER"); ov = find_route("OVERRIDER")
    checks.append(("R3 model-level account: FAITHFUL claims deep pattern-mimicry, OVERRIDER rational override, REASONER per-effect only",
                   fa["model_level_account"].startswith("deep pattern-mimicry")
                   and ov["model_level_account"].startswith("rational override")
                   and re_["model_level_account"].startswith("per-effect only"),
                   f"FAITHFUL: {fa['model_level_account']}; REASONER: {re_['model_level_account']}"))

    # one rehearsal case per rule ====================
    # rule 1: a reversal of 3 points or less is LOW, a larger one ANTI.
    r1 = (classify_cell(-0.029, 0.04), classify_cell(-0.020, 0.025), classify_cell(-0.035, 0.04))
    checks.append(("I2-1 a model effect opposite to the human effect: -2.9 vs +4 and -2.0 vs +2.5 are LOW, -3.5 vs +4 is ANTI",
                   r1 == ("LOW", "LOW", "ANTI"), str(r1)))
    # rule 2: the OVER class and its retrieval reading.
    ov_rows = [r for r in res["effect_class_rows"] if r["model"] == "OVERSHOOT_T1" and r["human_gate"] == "passed"
               and r["effect"] in REGULARITY_EFFECTS]
    ov_agree = next(r for r in res["agreement_rows"] if r["model"] == "OVERSHOOT_T1")
    t1_ov = next(r for r in res["test_T1_rows"] if r["model"] == "OVERSHOOT_T1")
    checks.append(("I2-2 OVER: a threefold published-tier overshoot is OVER overall, every published-tier cell reads as "
                   "retrieval of a described regularity, and T1 does not read it as steep",
                   ov_agree["class"] == "OVER" and bool(ov_rows)
                   and all("published tier" in r["over_reading"] for r in ov_rows)
                   and not t1_ov["reading"].startswith("steep"),
                   f"overall={ov_agree['class']} classes={[r['class'] for r in ov_rows]} T1={t1_ov['reading'][:40]}"))
    # rule 3: classes on the pooled estimate, with the human confirmatory slices and weights.
    fa_rows = {r["effect"]: r for r in res["effect_class_rows"] if r["model"] == "FAITHFUL"}
    same_pool = all(abs(fa_rows[st]["human_pp"] - g[st]["delta_pp"]) < 0.01 for st in EFFECTS if st in fa_rows)
    maj_ok = all(a["class"] == majority_class([r["class"] for r in res["effect_class_rows"]
                                               if r["model"] == a["model"] and r["effect"] in REGULARITY_EFFECTS
                                               and r["human_gate"] == "passed"])
                 for a in res["agreement_rows"] if not mg[a["model"]]["not_assessable"])
    checks.append(("I2-3 classes on pooled estimates: the human side of each class is the confirmatory pooled estimate, "
                   "and each model's overall class is the majority of its six non-similarity classes",
                   same_pool and maj_ok, f"same pooling={same_pool} majority rule={maj_ok}"))
    # rule 5: every model point carries its calls and a bootstrap interval; the grid is drawn 10 (60) times.
    fm_ok = all(r["n_calls"] > 0 and r["boot_lo_pp"] != "" and r["boot_lo_pp"] <= r["boot_hi_pp"]
                for r in res["fidelity_rows"])
    draws_num = {r["max_draws_per_grid_point"] for r in res["fidelity_rows"] if r["model"] == "FAITHFUL"}
    draws_pic = {r["max_draws_per_grid_point"] for r in res["t4_point_rows"]
                 if r["model"] == "FAITHFUL" and r["format"] == "pictures"}
    fa_frq = fa_rows.get("FRQ", {})
    checks.append(("I2-5 every model point carries its number of calls and a bootstrap interval over calls "
                   "(10 draws per text grid point, 60 per picture grid point)",
                   fm_ok and draws_num == {synth.DRAWS_TEXT} and draws_pic == {synth.DRAWS_PICTURES},
                   f"FAITHFUL FRQ {fa_frq.get('model_pp')}pp [{fa_frq.get('boot_lo_pp')}, {fa_frq.get('boot_hi_pp')}] "
                   f"from {fa_frq.get('n_calls')} calls; draws {sorted(draws_num)} / pictures {sorted(draws_pic)}"))
    # rule 6: the prompt-sensitivity flag sits beside every class.
    psens_ok = all(r["prompt_sensitive"] in (True, False, "n/a") for r in res["effect_class_rows"])
    checks.append(("I2-6 prompt sensitivity flagged beside every pooled class (FAITHFUL's upscaling effect is not flagged)",
                   psens_ok and fa_rows.get("SYM", {}).get("prompt_sensitive") is False,
                   f"FAITHFUL SYM by paraphrase: {fa_rows.get('SYM', {}).get('paraphrase_pp')}"))
    # rule 8: the memorization sensitivity regression carries the decoy-target covariate.
    checks.append(("I2-8 memorization sensitivity adjusts for decoy-target identity beside baseline distance",
                   s_fai["target_coef"] != "" and s_par["target_coef"] != "" and "budget" not in s_fai["covariates_omitted"],
                   f"FAITHFUL target coef={s_fai['target_coef']} baseline coef={s_fai['baseline_coef']}"))
    # rule 9: the positive controls hold on the main data; a premium-target frequency-decoy null fails.
    H_pc = synth.gen_human(N_HUMAN, random.Random(seed + 306), icc=0.10, null_on_hd_target={"FRQ"})
    gpc, _, _, _, _ = human_gate(H_pc, design, {"SOT": design.compromise_descriptive})
    pc_fail = positive_control_check(H_pc, design, gpc, {"SOT": design.compromise_descriptive})
    H_pc = None
    _INDEX_CACHE.clear()   # the cache also holds the released list
    checks.append(("I2-9 positive controls: both hold on the main data; a null on the premium-target frequency-decoy cells fails that control",
                   res["failed_controls"] == [] and pc_fail["failed"] == ["FRQ"],
                   f"main failed={res['failed_controls']}; planted premium null: FRQ premium "
                   f"{pc_fail['frq_premium']['delta_pp']:.2f}pp, failed={pc_fail['failed']}"))
    # rule 10: the similarity top-up check.
    H_tu = synth.gen_human(N_HUMAN, random.Random(seed + 307), icc=0.10, sim_topup_participants=N_TOPUP,
                           topup_shift=0.10)
    tu_fire = similarity_topup_check(H_tu, design)
    H_tu = None
    _INDEX_CACHE.clear()   # the cache also holds the released list
    checks.append(("I2-10 similarity supplement check: quiet on the main data; fires on a planted 10-point supplement "
                   "difference",
                   res["topup"]["fired"] is False and res["topup"]["n_topup"] > 0 and tu_fire["fired"] is True,
                   f"main diff={res['topup']['diff_pp']:.2f}pp p={res['topup']['p']:.3f}; planted diff="
                   f"{tu_fire['diff_pp']:.2f}pp p={tu_fire['p']:.2g}"))
    # rule 11: the deviation set is the registered SEVEN, computed from the calibration
    # record (the decision rule by option identity; the hard limits on the point share), never read from flags.
    # The flag cross-check may list only the televisions hard-limit flag, a data error is removing (its
    # point share, 74.7, is inside the limits); any other disagreement fails the check.
    known_flag_error = [("televisions", 1, "numbers")]
    checks.append(("I2-11 the deviation sensitivity set is the registered seven pairs computed from the calibration "
                   "record, and the calibration flags agree with the sets computed by option identity (apart from "
                   "the televisions flag, a known error in the flag)",
                   Design.from_stimuli().deviation_slices == set(DEVIATION_SENSITIVITY_PAIRS)
                   and len(design.deviation_slices) == 7
                   and design.deviation_flag_mismatch in ([], known_flag_error)
                   and not design.compromise_flag_mismatch,
                   f"{res['numbers']['design.deviation_slices']}; flag mismatches: deviation "
                   f"{design.deviation_flag_mismatch}, compromise {design.compromise_flag_mismatch}"))

    # the second revision, rule 1: every pattern-test reading is resolved against the joint bootstrap. FAITHFUL's prompts
    # are deterministic (every draw of a prompt gives the same answer), so its intervals come from the human side
    # alone: they must have positive width, and every assessable model's T1, T3 and T4 rows carry interval ends.
    t1_rows = {r["model"]: r for r in res["test_T1_rows"]}
    t3_rows = {r["model"]: r for r in res["test_T3_rows"]}
    widths_ok = (isinstance(t1_faith["drop_lo"], float) and isinstance(t1_faith["drop_hi"], float)
                 and t1_faith["drop_lo"] < t1_faith["drop_hi"]
                 and t1_faith["drop_lo"] <= t1_faith["drop"] <= t1_faith["drop_hi"])
    ends_ok = all(t1_rows[m]["drop_lo"] != "" and t3_rows[m]["tmb_lo"] != ""
                  for m in t1_rows if not mg[m]["not_assessable"])
    fa_route = find_route("FAITHFUL")
    checks.append(("R3-a FAITHFUL reaches S1 without a resolved flat memorization reading, qualified 'pattern tests not "
                   "resolved at the design's resolution' whenever a pattern test is open, the open tests listed",
                   fa_route is not None and fa_route["scenario"] == "S1"
                   and ((fa_route["qualifier"] == S1_QUALIFIER) == bool(fa_route["open_pattern_tests"]))
                   and (("T1" in fa_route["open_pattern_tests"].split(";")) == (not t1_faith["resolved"])),
                   f"{fa_route['scenario'] if fa_route else 'missing'}; qualifier: "
                   f"{fa_route['qualifier'] if fa_route else ''}; T1 resolved: {t1_faith['resolved']}"))
    checks.append(("R2-1 every T1 and T3 reading is resolved against an interval of the joint bootstrap; the human side "
                   "varies (FAITHFUL's deterministic prompts still give a T1 interval of positive width around its point)",
                   widths_ok and ends_ok,
                   f"FAITHFUL drop {t1_faith['drop']} [{t1_faith['drop_lo']}, {t1_faith['drop_hi']}]; "
                   f"routes {', '.join(r['model'] + '=' + r['scenario'] for r in res['routing_rows'] if r['scenario'] == NOT_RESOLVED_SCENARIO)}"))

    # ============ THE RULED SAMPLING NOISE: reported as a finding, not a pass condition ============
    want_all = dict(expect, DIVIDED_A="S5", DIVIDED_B="S5", WALK2_MIXED="PARTIAL", CEILING="CRITERION_FAIL",
                    REFUSER="CRITERION_FAIL")
    noise_table = []
    models = None
    if consistency == "exact":
        scratch = os.path.join(tempfile.gettempdir(), "context_effects_release_scratch", "rehearsal_noise_pack")
        for label, cons in (("every call an independent draw at the planted share", None),
                            ("each prompt gives its modal answer in 90 percent of its draws", 0.9)):
            nrng = random.Random(seed + 500)
            nmodels = {m: synth.gen_model(m, N_MODEL, nrng, with_formats=(m in REHEARSAL_WITH_FORMATS),
                                          consistency=cons) for m in synth.MODEL_ARCHETYPES}
            nmodels["FAITHFUL"] += synth.gen_persona_seq_arms("FAITHFUL", N_MODEL, random.Random(seed + 101),
                                                              with_formats=True, consistency=cons)
            os.makedirs(os.path.join(scratch, "tests"), exist_ok=True)
            os.makedirs(os.path.join(scratch, "figures"), exist_ok=True)
            saved = (globals()["PACK"], globals()["TESTS_DIR"], globals()["FIGS_DIR"])
            try:
                globals().update(PACK=scratch, TESTS_DIR=os.path.join(scratch, "tests"),
                                 FIGS_DIR=os.path.join(scratch, "figures"))
                nres = build_pack(H, nmodels, human_rows_with_formats=H, human_rows_first_trial=H, seed=seed,
                                  mode="REHEARSAL_NOISE", design=design)
            finally:
                globals().update(PACK=saved[0], TESTS_DIR=saved[1], FIGS_DIR=saved[2])
            nmodels = None       # release before the next noise level (memory only)
            _INDEX_CACHE.clear()   # the cache also holds the released list
            routes = {r["model"]: r["scenario"] for r in nres["routing_rows"]}
            t1n = {r["model"]: r["reading"].split(":")[0] for r in nres["test_T1_rows"]}
            for model, want in want_all.items():
                noise_table.append((label, model, want, routes.get(model, "missing"), t1n.get(model, "")))

    runtime = time.time() - t0
    _print_and_write_selftest(checks, res, runtime, seed, noise_table)
    allok = all(ok for _, ok, _ in checks)
    sys.exit(0 if allok else 1)


def _scan_missing(pack_dir):
    """Scan every CSV in the pack for empty cells that should not be empty. Some columns are
    legitimately blank by contract; those are whitelisted."""
    allowed_blank = {
        "validity_criteria.csv": {"replicated", "confirmatory", "direction_ok", "holm_family", "holm_p", "bf10", "delta_pp",
                      "parse_rate", "refusal_rate", "not_assessable", "is_positive_control"},
        "agreement_scores.csv": {"calibration_slope"},
        "tests/T1_memorization.csv": {"fidelity_t1", "fidelity_t2", "drop", "drop_lo", "drop_hi", "paired_categories",
                                      "descriptive_fidelity_all_categories_t1", "descriptive_fidelity_all_categories_t2",
                                      "descriptive_fidelity_invented_tier"},
        "tests/T1_memorization_sensitivity.csv": {"restricted_drop", "restricted_drop_lo", "restricted_drop_hi",
                                                  "adjusted_slope", "adjusted_drop", "adjusted_drop_lo",
                                                  "adjusted_drop_hi", "baseline_coef", "target_coef",
                                                  "covariates_omitted"},
        "tests/T3_ladder.csv": {"mid_rung", "high_rung", "low_rung", "attribution", "missed_effects",
                                "missed_recognition", "tmb_lo", "tmb_hi", "bmm_lo", "bmm_hi"},
        "tests/T4_formats.csv": {"words", "numbers", "pictures", "undefined", "numbers_picture_order", "diff_lo",
                                 "diff_hi"},
        "tests/T5_trajectory.csv": {"delta", "reasoning_reading", "traj_lo", "traj_hi", "reason_lo", "reason_hi"},
        "tests/T2_recognition.csv": {"recognition_lo", "recognition_hi", "behavior_lo_pp", "behavior_hi_pp"},
        "tests/similarity_topup_check.csv": {"backbone_pp", "topup_pp", "diff_pp", "diff_se_pp", "z", "p"},
        "effect_classes.csv": {"over_reading", "paraphrase_pp", "descriptive_class"},
        "tree_routing.csv": {"over_readings", "positive_controls", "possible_scenarios", "qualifier",
                             "open_pattern_tests"},
        "descriptive_slices.csv": {"ci_lo_pp", "ci_hi_pp", "boot_lo_pp", "boot_hi_pp", "n", "baseline_target_pct"},
        "price_free_arm.csv": {"ci_lo_pp", "ci_hi_pp", "boot_lo_pp", "boot_hi_pp"},
    }
    missing = []
    for root, _, files in os.walk(pack_dir):
        for fn in files:
            if not fn.endswith(".csv"):
                continue
            rel = os.path.relpath(os.path.join(root, fn), pack_dir).replace("\\", "/")
            wl = allowed_blank.get(rel, set())
            with open(os.path.join(root, fn), encoding="utf-8") as f:
                rdr = csv.DictReader(f)
                for i, row in enumerate(rdr):
                    for k, v in row.items():
                        if (v is None or str(v).strip() == "") and k not in wl:
                            missing.append(f"{rel}:row{i+1}:{k}")
    return missing


def _print_and_write_selftest(checks, res, runtime, seed, noise_table=None):
    lines = [
        "# Full dress rehearsal (analyze.py on synthetic data)",
        "",
        "(synth.py plants known human effects",
        "and a model archetype for every named scenario S1-S7, the two worked walk-throughs, and Reviewer 4's",
        "reversed-ladder pattern; this rehearsal runs the REAL pipeline and asserts the complete contract-C pack",
        "renders and routes every planted branch, plus one planted case per repaired defect. The Stage 2 run executes the",
        "SAME code on real contract-A/B exports.)",
        "",
        f"seed={seed}  runtime={round(runtime,2)}s  pack=results_pack/",
        "",
        "## PASS/FAIL table",
        "| check | result | detail |",
        "|---|---|---|",
    ]
    for label, ok, detail in checks:
        lines.append(f"| {label} | {'PASS' if ok else 'FAIL'} | {detail} |")
    allok = all(ok for _, ok, _ in checks)
    lines += ["", f"## OVERALL: {'ALL CHECKS PASS' if allok else 'FAILURE'}", "",
              "Scenario routing: " + ", ".join(f"{r['model']}={r['scenario']}" for r in res["routing_rows"]) + "."]
    if noise_table:
        n_ok = sum(1 for _, _, want, got, _ in noise_table if got == want)
        n_open = sum(1 for _, _, want, got, _ in noise_table if got == NOT_RESOLVED_SCENARIO)
        n_wrong = len(noise_table) - n_ok - n_open
        lines += ["", "## The same archetypes under the ruled sampling noise (REPORTED, not a pass condition)", "",
                  "The pass/fail table above runs the registered call plan (orders x paraphrases x 10 draws, 60 for "
                  "pictures) with every prompt deterministic and the cell shares exactly as planted. Below, the same "
                  "seed re-routes every archetype with the ruled binomial draws. A route that is not resolved is the "
                  "design's precision, not a code defect; power/MODEL_NOISE_STABILITY.md gives the rates over "
                  f"many seeds. Here: {n_ok} of {len(noise_table)} routed as planted, {n_open} not resolved, "
                  f"{n_wrong} to another scenario.", "",
                  "| model noise | archetype | planted | routed | T1 reading |", "|---|---|---|---|---|"]
        for label, model, want, got, t1r in noise_table:
            flag = ("" if got == want else (" (open)" if got == NOT_RESOLVED_SCENARIO else " (another scenario)"))
            lines.append(f"| {label} | {model} | {want} | {got}{flag} | {t1r} |")
    text = "\n".join(lines) + "\n"
    open(os.path.join(HERE, "RESULTS_PACK_SELFTEST.md"), "w", encoding="utf-8", newline="\n").write(text)
    print(text)


# ===================================================================================================
# THE REAL-DATA PATH (wired, unrun). Reads contract-A CSV + contract-B JSONL and runs the SAME code.
# ===================================================================================================
def load_human_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_model_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def run_real(human_csv, model_jsonl, stimuli=None):
    """Run the identical pipeline on real exports. The model JSONL may carry MANY models; we split by
    model_key. The design index is read from stimuli.json (the single source of stimulus truth)."""
    t0 = time.time()
    human_rows = load_human_csv(human_csv)
    recs = []
    for path in (model_jsonl if isinstance(model_jsonl, (list, tuple)) else [model_jsonl]):
        recs += load_model_jsonl(path)   # e.g. model_log.jsonl and model_log_reasoning_on.jsonl (split by arm)
    models = defaultdict(list)
    for r in recs:
        models[r["model_key"]].append(r)
    spath = stimuli or STIMULI_PATH
    if not spath or not os.path.exists(spath):
        raise SystemExit("[real] stimuli.json not found; the design index (targets, calibration record, "
                         "price-free and format categories) is required for the registered analysis")
    design = Design.from_stimuli(spath)
    if design.deviation_flag_mismatch or design.compromise_flag_mismatch:
        raise SystemExit("[real] the calibration flags in stimuli.json disagree with the sets computed by option "
                         f"identity (deviation: {design.deviation_flag_mismatch}; compromise: "
                         f"{design.compromise_flag_mismatch}); correct the flags before the confirmatory run")
    res = build_pack(human_rows, dict(models), human_rows_with_formats=human_rows,
                     human_rows_first_trial=human_rows, seed=-1, runtime=time.time() - t0,
                     mode="REAL", surprise_human_rows=None, design=design)
    print(f"[real] wrote results_pack/ from {len(human_rows)} human rows and "
          f"{len(recs)} model records across {len(models)} models.")
    return res


def main():
    ap = argparse.ArgumentParser(description="LLM context-effect analysis pipeline (synthetic rehearsal by default).")
    ap.add_argument("--human", help="contract-A human long CSV (from ingest.py). Triggers the real path.")
    ap.add_argument("--model", nargs="+", help="contract-B model JSONL log(s) (from the model engine): the "
                    "primary log, optionally with the reasoning-contrast log. Triggers the real path.")
    ap.add_argument("--stimuli", help="stimuli.json (default: the repository's stimuli/stimuli.json)")
    ap.add_argument("--rehearsal-consistency", default="default",
                    help="rehearsal only: the synthetic model's per-prompt consistency (a share such as 0.9, or "
                         "'independent' for every call an independent draw at the planted share)")
    args = ap.parse_args()
    if args.human or args.model:
        if not (args.human and args.model):
            ap.error("the real path needs BOTH --human and --model")
        run_real(args.human, args.model, args.stimuli)
        sys.exit(0)
    c = args.rehearsal_consistency
    run_rehearsal("default" if c == "default" else (None if c == "independent" else float(c)))


if __name__ == "__main__":
    main()
