"""calibration_lock.py: the decisions of the final calibration lock (July 2, 2026), in one place.

build_stimuli.py reads this module together with calibration/FINAL_LOCK_LIST_2026-07-02.json, which holds
every pair's final values, measured share and interval. This module holds what the lock list does not:
  - the routing of every calibrated pair: LOCK, CHECK_ONLY (published tier-1 values, never adjusted),
    RUN_WITH_DEVIATION (five pairs that stayed outside the target band after the third wave and remain
    in the design with the deviation recorded), and EXIT (the pictures version of the hard-drives pair,
    beyond the 25 to 75 percent limits in all three waves, removed from the design);
  - the per-format values of the two pictures pairs that were calibrated separately in wave 3;
  - the enriched product descriptions (model names and plain-language qualifiers) fielded in wave 3;
  - the strengthened frequency-decoy and range-decoy margins adopted after the wave-3 comprehension checks.

Nothing here invents a number: shares, intervals and final values are read from the lock list.
Manuscript: Web Appendix F (Table WA-F6 and the text on the five retained pairs and the removed pair).

Imported by build_stimuli.py; not run on its own.
"""

G3_DATE = "2026-07-02"

# The staged lock list (numeric authority for final values + measured shares per arm).
LOCK_LIST_REL = "../calibration/FINAL_LOCK_LIST_2026-07-02.json"

# The strengthened geometry-check parameters (wave-3 amendment (d), adopted at the final calibration lock): the FRQ
# decoy's dominance margins move from (12%, 8%) to (25%, 25%) of the strong-attribute span /
# price, and the range decoy's weak-axis price extension from x1.7 to x2.2 of the target's
# price (rng_b_factor 0.7 -> 1.2). Passed as explicit arguments to geometry.build by every
# generator from final calibration lock on. FRQ margins reach only the engine-generated tiers (2 and 3): tier-1
# frequency decoys are published values and are never regenerated. The range decoy is
# engine-constructed at every tier (the M1 correction), so the wider extension applies to all
# tiers; the price-free arm keeps its own registered gentle-cut rule (untouched by these).
GEOMETRY_STRENGTHENED = dict(frq_margins=(0.25, 0.25), rng_b_factor=1.2)

# The registered hard limits on a two-option baseline (CALIBRATION_DESIGN; calibration_analysis
# HARD_LO/HARD_HI): a measured POINT share outside [25, 75] is a hard-limit case. Added 2026-09-29
# when the check-only hard-limit flag moved from a word match on the lock list's band
# verdict to this point-share test; HARD_LIMIT_FLAG_ARMS is the set it must produce (tier-1 water
# bottles, 80.0). Tier-1 televisions (74.7, interval [65.2, 82.4]) is inside the limits and carries
# no hard-limit flag; its record's band verdict still says the interval straddles 75.
HARD_LIMITS_PCT = (25.0, 75.0)
HARD_LIMIT_FLAG_ARMS = {"pub_t1::BIN_water_bottles_t1"}

# ---------------------------------------------------------------------------------------------
# Routing verdicts per calibration arm (arm ids exactly as in the lock list).
# status: LOCK | CHECK_ONLY | RUN_WITH_DEVIATION | EXIT
# ---------------------------------------------------------------------------------------------
ROUTING = {
    # tier-1 published arms: values fixed by fidelity; shares reported, never adjusted.
    "pub_t1::BIN_backpacks_t1": "CHECK_ONLY",
    "pub_t1::BIN_bluetooth_speakers_t1": "CHECK_ONLY",
    "pub_t1::BIN_earbuds_t1": "CHECK_ONLY",
    "pub_t1::BIN_hard_drives_t1": "CHECK_ONLY",
    "pub_t1::BIN_restaurants_t1": "CHECK_ONLY",
    "pub_t1::BIN_televisions_t1": "CHECK_ONLY",
    "pub_t1::BIN_water_bottles_t1": "CHECK_ONLY",
    # the 12 locked adjustable arms
    "pub_t2::BIN_water_bottles_t2": "LOCK",
    "inv_t3::BIN_robot_vacuums_t3": "LOCK",
    # corrected 2026-09-29: LOCK at the final calibration lock, scored on the budget
    # option's share (44.7); by option identity the compromise target took 55.3 and the pair fails
    # the terminal criterion, so it is retained with its measured baseline like the arms below.
    # The lock list (calibration/FINAL_LOCK_LIST_2026-07-02.json) keeps the final calibration lock verdict as history.
    "inv_t3::BIN_electric_kettles_t3": "RUN_WITH_DEVIATION",
    "pub_t2::BIN_bluetooth_speakers_t2": "LOCK",
    "pub_t2::BIN_hard_drives_t2": "LOCK",
    "pub_t2::BIN_televisions_t2": "LOCK",
    "words::BIN_bluetooth_speakers_t2": "LOCK",
    "words::BIN_hard_drives_t2": "LOCK",
    "words::BIN_televisions_t2": "LOCK",
    "words::BIN_water_bottles_t2": "LOCK",
    "pictures::BIN_bluetooth_speakers_t2": "LOCK",
    "pictures::BIN_televisions_t2": "LOCK",
    # the six defect-routed arms, per the authors' signed routing
    "pub_t2::BIN_backpacks_t2": "RUN_WITH_DEVIATION",
    "pub_t2::BIN_restaurants_t2": "RUN_WITH_DEVIATION",
    "pub_t2::BIN_earbuds_t2": "RUN_WITH_DEVIATION",
    "inv_t3::BIN_standing_desks_t3": "RUN_WITH_DEVIATION",
    "pictures::BIN_water_bottles_t2": "RUN_WITH_DEVIATION",
    "pictures::BIN_hard_drives_t2": "EXIT",
}

# The registered criterion that handles each run-with-deviation arm (recorded on the stimulus; the
# numeric baseline/CI/n are attached from the lock list at build time, never typed here).
DEVIATION_GATE = {
    "pub_t2::BIN_backpacks_t2": (
        "baseline below the registered band and the terminal criterion's floor of 33 percent; "
        "the compromise target stays the minority option, so the compromise precondition holds; "
        "every result on the tier-2 backpacks cells is reported against this documented "
        "out-of-band baseline under the Analysis Plan's stimulus-defect reporting."),
    "pub_t2::BIN_restaurants_t2": (
        "baseline below the registered band and the terminal criterion's floor of 33 percent; "
        "the compromise target stays the minority option, so the compromise precondition holds; "
        "every result on the tier-2 restaurants cells is reported against this documented "
        "out-of-band baseline under the Analysis Plan's stimulus-defect reporting."),
    "pub_t2::BIN_earbuds_t2": (
        "baseline above 50 percent: the compromise target starts AHEAD, violating the corrected "
        "compromise test's registered precondition for this slice - the tier-2 earbuds "
        "compromise (SOT) cell is pre-flagged uninformative for the compromise test; the "
        "remaining tests on the slice are reported against the documented baseline."),
    # NOTE 2026-09-29: this final calibration lock text is WRONG about the compromise target (it reads the
    # budget option's share as the compromise target's). It is kept here as the final calibration lock record only:
    # build_stimuli.py no longer writes it anywhere. The standing desks' record and flag take the
    # corrected texts in IDENTITY_RECORD_TEXT and IDENTITY_FLAG_TEXT below.
    "inv_t3::BIN_standing_desks_t3": (
        "baseline above 50 percent: the compromise target starts AHEAD, violating the corrected "
        "compromise test's registered precondition for this slice - the tier-3 standing-desks "
        "compromise (SOT) cell is pre-flagged uninformative for the compromise test; the "
        "remaining tests are reported against the documented baseline. (Realism: at parity with "
        "the published categories on the 2026-07-02 anchored comparison; see the calibration "
        "trail.)"),
    "pictures::BIN_water_bottles_t2": (
        "pictures-format baseline above 50 percent at values that are in band as numbers and as "
        "words (a stable pictures-over-numbers baseline shift measured three waves running): "
        "the pictures water-bottles compromise (SOT) cell is pre-flagged uninformative for the "
        "compromise test; the pictures FRQ and BIN cells run and are reported against the "
        "documented baseline."),
}

# ---------------------------------------------------------------------------------------------
# The option-identity arms.
# In the electric kettles and the standing desks the calibration records count HF, the budget
# option (the category-level calibration target, which the tier-3 frequency, range and phantom
# decoys target), while the compromise target is HD. build_stimuli.py re-scores the registered
# terminal lock criterion (CALIBRATION_DESIGN wave-3 amendment (a)) on BOTH options' shares from
# the lock list's own counts (k_target, n) and refuses unless the verdicts equal IDENTITY_EXPECTED
# below: (verdict on the recorded share, verdict on the compromise target's share).
#   kettles: HF 44.7 locks, but HD 55.3 [50.8, 59.8] fails -> the pair is retained with a
#            CALIBRATION_DEVIATION flag it never carried.
#   desks:   HF 66.7 fails and HD 33.3 [29.2, 37.8] fails too -> the deviation stands either way,
#            but the compromise target starts behind, so its compromise cell stays confirmatory.
# The flag for each arm is composed from IDENTITY_FLAG_TEXT, whose numbers are placeholders filled
# at build time from the lock list (never typed here). The calibration records keep their final calibration lock
# status, verdict and deviation_gate lines byte-identical; these flags supersede them. Keep the
# phrases "words arm" and "pictures arm" out of these texts: analyze.Design reads them to tell a
# flag's format. Placeholders: {g3} {fmt} {n} {limit} {rec_code} {rec_role} {rec_pct} {rec_ci}
# {comp_code} {comp_role} {comp_pct} {comp_ci}.
# ---------------------------------------------------------------------------------------------
IDENTITY_EXPECTED = {
    "inv_t3::BIN_electric_kettles_t3": ("LOCK", "FAIL"),
    "inv_t3::BIN_standing_desks_t3": ("FAIL", "FAIL"),
}
IDENTITY_FLAG_TEXT = {
    "inv_t3::BIN_electric_kettles_t3": (
        "CALIBRATION_DEVIATION (added 2026-09-29, {fmt} arm): by option identity this pair fails "
        "the registered calibration rule. The compromise target ({comp_code}, {comp_role}) took "
        "{comp_pct} percent {comp_ci} of the two-option choice (n={n}, wave 3), above {limit} "
        "percent and outside the registered band. The {rec_pct} percent {rec_ci} on which the pair "
        "was locked at the final calibration lock is the share of {rec_code}, {rec_role}: this category's calibration "
        "target and the option its tier-3 frequency, range and phantom decoys target, not the "
        "compromise target. The pair is retained at its locked values with its measured baseline, "
        "and every result on the slice is reported against it; the tier-3 electric-kettles "
        "compromise (SOT) cell is descriptive only (see its COMPROMISE_PRECONDITION_VIOLATED "
        "flag). The calibration record on this cell was corrected the same day: its status is now "
        "RUN_WITH_DEVIATION, and its final calibration lock verdict (LOCK, point in band) is marked as scored on the "
        "budget option's share."),
    "inv_t3::BIN_standing_desks_t3": (
        "CALIBRATION_DEVIATION (final calibration lock {g3}, {fmt} arm; text corrected 2026-09-29): terminal baseline "
        "{rec_pct} percent {rec_ci} for {rec_code}, {rec_role}, and {comp_pct} percent {comp_ci} "
        "for {comp_code}, {comp_role} and the compromise target (n={n}, wave 3). The pair fails "
        "the registered calibration rule either way. The final calibration lock lock recorded the {rec_pct}: "
        "{rec_code} is this category's calibration target and the option its tier-3 frequency, "
        "range and phantom decoys target. The compromise target starts BEHIND, so the compromise "
        "precondition holds and the tier-3 standing-desks compromise (SOT) cell stays in the "
        "confirmatory compromise test. The pair is retained with its measured baseline: the decoy "
        "cells that target {rec_role} start from the above-band {rec_pct}, and every result on "
        "the slice is reported against the documented baseline. (Realism: at parity with the "
        "published categories on the 2026-07-02 anchored comparison; see the calibration trail.) "
        "The final calibration lock version of this flag read the {rec_pct} as the compromise target's share and "
        "pre-flagged the compromise cell by mistake; the calibration record on this cell was "
        "corrected the same day."),
}

# The calibration-record text for the two option-identity arms. build_stimuli.py writes these over the lock list's final calibration lock wording
# in the BIN cell's calibration record (terminal_lock_verdict, band_verdict, disposition,
# deviation_gate), and appends TRAIL_NOTE to the trail's QUALITY-step line, whose share and
# "aimed at 42.5%" are the budget option's. Only text: every number in the record (the wave3
# block, the trail's shares and value moves) stays exactly as the lock list has it. Same
# placeholders as IDENTITY_FLAG_TEXT; the texts are written for rec_code HF and comp_code HD, and
# the build refuses otherwise.
IDENTITY_TRAIL_NOTE = (
    " [Note 2026-09-29: the shares in this line and its 42.5 percent aim are shares of "
    "{rec_code}, {rec_role}, this category's calibration target; the registered band applies to "
    "the compromise target ({comp_code}, {comp_role}), whose share is 100 minus each of them.]")
IDENTITY_RECORD_TEXT = {
    "inv_t3::BIN_electric_kettles_t3": {
        "terminal_lock_verdict": (
            "DEFECT CONTINGENCY by option identity (corrected 2026-09-29): the compromise target "
            "({comp_code}, {comp_role}) took {comp_pct} percent {comp_ci}, which fails the "
            "registered terminal criterion. The final calibration lock verdict, LOCK (point in band), was scored on the "
            "{rec_pct} percent {rec_ci} of {rec_code}, {rec_role}, which is the share the wave3 "
            "block of this record holds."),
        "band_verdict": (
            "OUT OF BAND by option identity: the compromise target took {comp_pct} percent, above "
            "{limit} percent. The final calibration lock verdict IN BAND was read on the {rec_pct} percent of "
            "{rec_code}, {rec_role} (corrected 2026-09-29)."),
        "disposition": (
            "RETAINED WITH ITS MEASURED BASELINE (corrected 2026-09-29): the pair fields at the "
            "values locked at the final calibration lock (with the enrichment content). Every share in this record (the "
            "wave3 block and the trail) is the share of {rec_code}, {rec_role}; the compromise "
            "target ({comp_code}, {comp_role}) took {comp_pct} percent {comp_ci} (n={n}, wave 3). "
            "By option identity the pair fails the registered calibration rule, so it is retained "
            "like the other adjustable pairs that failed it, with its measured baseline reported "
            "beside every result on the slice."),
        "deviation_gate": (
            "by option identity the pair fails the registered calibration rule: the compromise "
            "target ({comp_code}, {comp_role}) starts AHEAD at {comp_pct} percent {comp_ci}, above "
            "{limit} percent, so the tier-3 electric-kettles compromise (SOT) cell is descriptive "
            "only. The {rec_pct} percent on which the pair locked at the final calibration lock is the share of "
            "{rec_code}, {rec_role}, the option its tier-3 frequency, range and phantom decoys "
            "target. The pair is retained with its measured baseline, and every result on the "
            "slice is reported against it (status corrected from LOCK on 2026-09-29)."),
    },
    "inv_t3::BIN_standing_desks_t3": {
        "terminal_lock_verdict": (
            "DEFECT CONTINGENCY (pre-registered), either way (option identity checked 2026-09-29): "
            "{rec_code}, {rec_role}, took {rec_pct} percent {rec_ci}, the share the wave3 block of "
            "this record holds, and the compromise target ({comp_code}, {comp_role}) took "
            "{comp_pct} percent {comp_ci}; both fail the registered terminal criterion."),
        "band_verdict": (
            "OUT OF BAND either way: {rec_code}, {rec_role}, {rec_pct} percent; the compromise "
            "target ({comp_code}), {comp_pct} percent (option identity checked 2026-09-29)."),
        "disposition": (
            "RETAINED WITH ITS MEASURED BASELINE (the authors' routing, signed 2026-07-02; text "
            "corrected 2026-09-29): every share in this record (the wave3 block and the trail) is "
            "the share of {rec_code}, {rec_role}, this category's calibration target; the "
            "compromise target ({comp_code}, {comp_role}) took {comp_pct} percent {comp_ci} "
            "(n={n}, wave 3). The pair fails the registered calibration rule either way and is "
            "retained with its measured baseline."),
        "deviation_gate": (
            "baseline above the registered band for {rec_code}, {rec_role} ({rec_pct} percent "
            "{rec_ci}), and below it for the compromise target ({comp_code}, {comp_role}, "
            "{comp_pct} percent {comp_ci}): the pair fails the registered calibration rule either "
            "way. {rec_code} is this category's calibration target and the option its tier-3 "
            "frequency, range and phantom decoys target. The compromise target starts BEHIND, so "
            "the compromise precondition holds and the tier-3 standing-desks compromise (SOT) cell "
            "stays in the confirmatory compromise test; the decoy cells that target {rec_role} "
            "start from the above-band {rec_pct}, and every result on the slice is reported "
            "against the documented baseline. (Realism: at parity with the published categories "
            "on the 2026-07-02 anchored comparison; see the calibration trail.) Text corrected "
            "2026-09-29: the final calibration lock version read the {rec_pct} as the compromise target's share and "
            "pre-flagged the compromise cell by mistake."),
    },
}

EXIT_RECORD = {
    "pictures::BIN_hard_drives_t2": (
        "EXIT at the final calibration lock (the authors' routing, 2026-07-02): the pictures rendering of the hard-drives pair "
        "stayed beyond the registered 25-75 hard limits in all three calibration waves (91.9, "
        "84.8, 79.1 percent), the registered no-room / stimulus-defect case. Its three "
        "pictures-format cells (BIN, FRQ, SOT) exit the confirmatory inventory; the numbers and "
        "words hard-drives arms locked at the same values and run. The 92 percent "
        "picture-comprehension result shows the bars are read correctly, so the inflation is a "
        "property of the magnitude-bar rendering itself, reported in the calibration trail."),
}

# ---------------------------------------------------------------------------------------------
# The compromise precondition. A compromise
# (SOT) cell is descriptive only whenever its compromise target's measured two-option share, read
# by option identity from the terminal calibration record, is at or above this limit. The share is
# COMPUTED by build_stimuli.py from the lock list (never typed here); the set of cells it must
# produce is registered below, and the build refuses when the two disagree. Tier-1 pairs are
# included (their published values stay unadjusted; the flag only routes the cell). The exited
# pictures hard-drives arm has no fielded compromise cell and is skipped.
# ---------------------------------------------------------------------------------------------
COMPROMISE_TARGET_MAX_BASELINE_PCT = 50.0
COMPROMISE_DESCRIPTIVE_CELLS = {          # (SOT stimulus id, format arm)
    ("SOT_bluetooth_speakers_t1", "numbers"),
    ("SOT_earbuds_t1", "numbers"),
    ("SOT_restaurants_t1", "numbers"),
    ("SOT_televisions_t1", "numbers"),
    ("SOT_water_bottles_t1", "numbers"),
    ("SOT_earbuds_t2", "numbers"),
    ("SOT_water_bottles_t2", "pictures"),
    ("SOT_electric_kettles_t3", "numbers"),
}

# ---------------------------------------------------------------------------------------------
# Per-format value support (the wave-3 amendment (b) per-arm departure, adopted at the final calibration lock): the two
# pictures arms whose terminal locks landed at different values than their category's
# numbers/words arms. The pictures variant of every format cell in these categories is built
# from THIS anchor (BIN focals; FRQ/SOT constructed from it by the geometry engine), while the
# numbers and words arms keep the category anchor. water_bottles' pictures arm shares the
# category values (it is listed in ROUTING, not here). hard_drives' pictures arm exits.
# ---------------------------------------------------------------------------------------------
PIC_ANCHORS = {
    # category -> {"A": (HF, HD) on the quality attribute, "B": (HF, HD) on price}
    "bluetooth_speakers": {"A": (3.8, 4.7), "B": (44.99, 84.99)},
    "televisions": {"A": (70, 96), "B": (139.99, 429.00)},
}
PIC_EXIT = {"hard_drives"}

# ---------------------------------------------------------------------------------------------
# ENRICHMENT (amendment (c) adopted at the final calibration lock). HF/HD entries are the calibrated wave-3 kit content
# VERBATIM (calibration/wave3_pairs.json "enrichment"). The constructed-option entries (DECOY,
# RANGE_DECOY, PHANTOM, EXTREME, SYM_DECOY, CLONE_HF, CLONE_HD) are authored at the final calibration lock under the
# same contract: brand-neutral numeral-free names, one plain-language numeral-free qualifier
# per attribute, value-congruent with the locked geometry (including the per-format pictures
# values, where the same entry must fit both renderings). Validated by
# enrich.validate_enrichment plus the final calibration lock coverage checks in validate_stimuli.py.
# ---------------------------------------------------------------------------------------------
ENRICHMENT_SCOPE = {
    "tiers": [2, 3],
    "structures": ["BIN", "FRQ", "RNG", "PHT", "SOT", "SYM", "SIM"],
    "note": ("Adjustable tiers only; tier-1 text stays exactly as published. MOT and EXC stay "
             "sparse: the extremity statistic is MOT minus EXC, an internally matched pair "
             "outside the calibrated binary control; the price-free variant categories sit "
             "outside the calibration set and stay sparse as registered."),
}

ENRICHMENT = {
    "backpacks": {
        "HF": {"name": "Ridgeline Daypack", "qualifiers": {"capacity": "room for a laptop, lunch, and a light jacket", "price": "an easy-on-the-wallet everyday pack"}},
        "HD": {"name": "Crestway Trek Pack", "qualifiers": {"capacity": "expedition-size space for weekend trips and bulky gear", "price": "a step up in price"}},
        "DECOY": {"name": "Summitline Cargo Pack", "qualifiers": {"capacity": "space for most weekend hauls", "price": "toward the top of the backpack price range"}},
        "RANGE_DECOY": {"name": "Peakford Expedition Pack", "qualifiers": {"capacity": "full expedition-size space", "price": "a serious premium price"}},
        "PHANTOM": {"name": "Traildom Ultra Pack", "qualifiers": {"capacity": "cavernous space for gear-heavy trips", "price": "a step up in price"}},
        "EXTREME": {"name": "Basecamp Hauler Pack", "qualifiers": {"capacity": "hauls more than most trips ever need", "price": "a top-shelf price"}},
        "SYM_DECOY": {"name": "Cityline Commuter Pack", "qualifiers": {"capacity": "room for a laptop, lunch, and a light layer", "price": "a step up in price"}},
        "CLONE_HF": {"name": "Ridgeway Daypack", "qualifiers": {"capacity": "room for a laptop, lunch, and a light jacket", "price": "an easy-on-the-wallet everyday pack"}},
        "CLONE_HD": {"name": "Crestline Trek Pack", "qualifiers": {"capacity": "expedition-size space for weekend trips and bulky gear", "price": "a step up in price"}},
    },
    "bluetooth_speakers": {
        "HF": {"name": "EchoTone Portable Speaker", "qualifiers": {"rating": "well-liked by everyday listeners", "price": "an easy-entry price"}},
        "HD": {"name": "NimbusSound Portable Speaker", "qualifiers": {"rating": "a favorite among reviewers", "price": "a premium price"}},
        "DECOY": {"name": "SoundCove Portable Speaker", "qualifiers": {"rating": "reviews sit a notch behind the leaders", "price": "a mid-tier price"}},
        "RANGE_DECOY": {"name": "BreezeBeat Portable Speaker", "qualifiers": {"rating": "reviews trail the pack", "price": "priced with the entry models"}},
        "PHANTOM": {"name": "TonePort Portable Speaker", "qualifiers": {"rating": "everyday listeners rate it kindly", "price": "a light-on-the-wallet price"}},
        "EXTREME": {"name": "AuraPeak Portable Speaker", "qualifiers": {"rating": "top marks across the board", "price": "a flagship price"}},
        "SYM_DECOY": {"name": "DriftTone Portable Speaker", "qualifiers": {"rating": "everyday-grade listener marks", "price": "a premium price"}},
        "CLONE_HF": {"name": "EchoTune Portable Speaker", "qualifiers": {"rating": "well-liked by everyday listeners", "price": "an easy-entry price"}},
        "CLONE_HD": {"name": "NimbusBeat Portable Speaker", "qualifiers": {"rating": "a favorite among reviewers", "price": "a premium price"}},
    },
    "earbuds": {
        "HF": {"name": "BeatBuds Wireless Earbuds", "qualifiers": {"reviews": "a solid base of buyer feedback", "price": "pocket-money pricing"}},
        "HD": {"name": "TempoPods Wireless Earbuds", "qualifiers": {"reviews": "a very large base of buyer feedback", "price": "a mid-range price"}},
        "DECOY": {"name": "PulseBuds Wireless Earbuds", "qualifiers": {"reviews": "a large base of buyer feedback", "price": "at the top of the earbud price range"}},
        "RANGE_DECOY": {"name": "SonicPods Wireless Earbuds", "qualifiers": {"reviews": "a very large base of buyer feedback", "price": "priced like premium over-ear gear"}},
        "PHANTOM": {"name": "EchoBuds Wireless Earbuds", "qualifiers": {"reviews": "among the largest feedback bases around", "price": "a mid-range price"}},
        "EXTREME": {"name": "MegaPods Wireless Earbuds", "qualifiers": {"reviews": "a massive base of buyer feedback", "price": "an upper-shelf price"}},
        "SYM_DECOY": {"name": "AirChime Wireless Earbuds", "qualifiers": {"reviews": "a solid base of buyer feedback", "price": "a mid-range price"}},
        "CLONE_HF": {"name": "BeatPods Wireless Earbuds", "qualifiers": {"reviews": "a solid base of buyer feedback", "price": "pocket-money pricing"}},
        "CLONE_HD": {"name": "TempoBuds Wireless Earbuds", "qualifiers": {"reviews": "a very large base of buyer feedback", "price": "a mid-range price"}},
    },
    "electric_kettles": {
        "HF": {"name": "BrewMate Electric Kettle", "qualifiers": {"power": "takes its time to reach a boil", "price": "a modest price"}},
        "HD": {"name": "ThermoJet Electric Kettle", "qualifiers": {"power": "brings water to a rolling boil fast", "price": "a premium price"}},
        "DECOY": {"name": "WarmWave Electric Kettle", "qualifiers": {"power": "a slow, patient heater", "price": "a mid-tier price"}},
        "RANGE_DECOY": {"name": "CozyPot Electric Kettle", "qualifiers": {"power": "warms water at a crawl", "price": "priced with the modest models"}},
        "PHANTOM": {"name": "BrewJoy Electric Kettle", "qualifiers": {"power": "unhurried on its way to a boil", "price": "a pocket-friendly price"}},
        "EXTREME": {"name": "VoltBrew Electric Kettle", "qualifiers": {"power": "boils in a blink", "price": "a top-shelf price"}},
        "SYM_DECOY": {"name": "SteamLine Electric Kettle", "qualifiers": {"power": "leisurely on its way to a boil", "price": "a premium price"}},
        "CLONE_HF": {"name": "BrewMade Electric Kettle", "qualifiers": {"power": "takes its time to reach a boil", "price": "a modest price"}},
        "CLONE_HD": {"name": "ThermoJolt Electric Kettle", "qualifiers": {"power": "brings water to a rolling boil fast", "price": "a premium price"}},
    },
    "hard_drives": {
        "HF": {"name": "DataPort External Drive", "qualifiers": {"storage": "space for large photo and document libraries", "price": "a value price"}},
        "HD": {"name": "VaultMax External Drive", "qualifiers": {"storage": "room for full-system backups and years of media", "price": "a step-up price"}},
        "DECOY": {"name": "StorEdge External Drive", "qualifiers": {"storage": "room for large media collections", "price": "at the top of the desktop-drive price range"}},
        "RANGE_DECOY": {"name": "ArchivePro External Drive", "qualifiers": {"storage": "space for full backups and years of media", "price": "priced like specialist server gear"}},
        "PHANTOM": {"name": "DataVault Pro External Drive", "qualifiers": {"storage": "cavernous space for whole-studio archives", "price": "a step-up price"}},
        "EXTREME": {"name": "MaxStore External Drive", "qualifiers": {"storage": "archive-grade space beyond most home needs", "price": "a top-shelf price"}},
        "SYM_DECOY": {"name": "FlexDrive External Drive", "qualifiers": {"storage": "room for big photo and document libraries", "price": "a step-up price"}},
        "CLONE_HF": {"name": "DataDock External Drive", "qualifiers": {"storage": "space for large photo and document libraries", "price": "a value price"}},
        "CLONE_HD": {"name": "VaultMate External Drive", "qualifiers": {"storage": "room for full-system backups and years of media", "price": "a step-up price"}},
    },
    "restaurants": {
        "HF": {"name": "The Corner Table", "qualifiers": {"rating": "a dependable neighborhood spot", "price": "casual-dining entree prices"}},
        "HD": {"name": "Maison Laurent", "qualifiers": {"rating": "among the area's top-rated tables", "price": "fine-dining entree prices"}},
        "DECOY": {"name": "Harbor House Grill", "qualifiers": {"rating": "reviews run middling", "price": "casual-dining prices, edging upward"}},
        "RANGE_DECOY": {"name": "The Copper Skillet", "qualifiers": {"rating": "reviews trail the neighborhood pack", "price": "casual-dining entree prices"}},
        "PHANTOM": {"name": "The Garden Fork", "qualifiers": {"rating": "steady neighborhood reviews", "price": "weeknight-friendly entree prices"}},
        "EXTREME": {"name": "Atelier Rousseau", "qualifiers": {"rating": "at the very top of the local rankings", "price": "special-occasion tasting prices"}},
        "SYM_DECOY": {"name": "The Gilded Spoon", "qualifiers": {"rating": "steady, unremarkable reviews", "price": "fine-dining entree prices"}},
        "CLONE_HF": {"name": "The Corner Booth", "qualifiers": {"rating": "a dependable neighborhood spot", "price": "casual-dining entree prices"}},
        "CLONE_HD": {"name": "Maison Colette", "qualifiers": {"rating": "among the area's top-rated tables", "price": "fine-dining entree prices"}},
    },
    "robot_vacuums": {
        "HF": {"name": "TidyBot Robot Vacuum", "qualifiers": {"suction": "handles everyday dust and crumbs on hard floors", "price": "an entry-level price"}},
        "HD": {"name": "OrbitClean Robot Vacuum", "qualifiers": {"suction": "strong enough for carpets and pet hair", "price": "a flagship price"}},
        "DECOY": {"name": "SweepStar Robot Vacuum", "qualifiers": {"suction": "strong pull for carpets and rugs", "price": "beyond the usual flagship price"}},
        "RANGE_DECOY": {"name": "VacPrime Robot Vacuum", "qualifiers": {"suction": "carpet-and-pet-hair strength", "price": "priced like a commercial cleaner"}},
        "PHANTOM": {"name": "TurboSweep Robot Vacuum", "qualifiers": {"suction": "deep-clean pull beyond the usual flagships", "price": "a flagship price"}},
        "EXTREME": {"name": "CycloneMax Robot Vacuum", "qualifiers": {"suction": "industrial-grade pull", "price": "a top-shelf price"}},
        "SYM_DECOY": {"name": "GlideBot Robot Vacuum", "qualifiers": {"suction": "fine for everyday dust on hard floors", "price": "a flagship price"}},
        "CLONE_HF": {"name": "TidyMate Robot Vacuum", "qualifiers": {"suction": "handles everyday dust and crumbs on hard floors", "price": "an entry-level price"}},
        "CLONE_HD": {"name": "OrbitSweep Robot Vacuum", "qualifiers": {"suction": "strong enough for carpets and pet hair", "price": "a flagship price"}},
    },
    "standing_desks": {
        "HF": {"name": "LiftMate Standing Desk", "qualifiers": {"weight_capacity": "suited to a laptop-and-monitor setup", "price": "a starter price"}},
        "HD": {"name": "TerraRise Standing Desk", "qualifiers": {"weight_capacity": "holds a full multi-monitor workstation with ease", "price": "a premium price"}},
        "DECOY": {"name": "DeskRise Standing Desk", "qualifiers": {"weight_capacity": "best kept to a light laptop setup", "price": "a mid-tier price"}},
        "RANGE_DECOY": {"name": "AeroLift Standing Desk", "qualifiers": {"weight_capacity": "suited only to the lightest gear", "price": "priced with the starter models"}},
        "PHANTOM": {"name": "StandEase Standing Desk", "qualifiers": {"weight_capacity": "happily carries a laptop-and-monitor setup", "price": "an easy-entry price"}},
        "EXTREME": {"name": "IronCrest Standing Desk", "qualifiers": {"weight_capacity": "built for a full studio of equipment", "price": "a flagship price"}},
        "SYM_DECOY": {"name": "UpDeck Standing Desk", "qualifiers": {"weight_capacity": "fits a laptop-and-monitor workstation", "price": "a premium price"}},
        "CLONE_HF": {"name": "LiftMade Standing Desk", "qualifiers": {"weight_capacity": "suited to a laptop-and-monitor setup", "price": "a starter price"}},
        "CLONE_HD": {"name": "TerraLift Standing Desk", "qualifiers": {"weight_capacity": "holds a full multi-monitor workstation with ease", "price": "a premium price"}},
    },
    "televisions": {
        "HF": {"name": "ClearView Smart TV", "qualifiers": {"picture_quality": "a crisp, watchable everyday picture", "price": "a budget-friendly price"}},
        "HD": {"name": "CinemaMax Smart TV", "qualifiers": {"picture_quality": "near the top of the expert rankings", "price": "a premium price"}},
        "DECOY": {"name": "VistaPrime Smart TV", "qualifiers": {"picture_quality": "a strong expert score", "price": "above the going rate for this class"}},
        "RANGE_DECOY": {"name": "OpticaPro Smart TV", "qualifiers": {"picture_quality": "expert scores in the top ranks", "price": "priced like a home-theater flagship"}},
        "PHANTOM": {"name": "LumaElite Smart TV", "qualifiers": {"picture_quality": "the best expert score in its class", "price": "a premium price"}},
        "EXTREME": {"name": "CineRoyal Smart TV", "qualifiers": {"picture_quality": "expert scores at the very top", "price": "a top-shelf price"}},
        "SYM_DECOY": {"name": "ViewCast Smart TV", "qualifiers": {"picture_quality": "an everyday picture that does the job", "price": "a premium price"}},
        "CLONE_HF": {"name": "ClearVista Smart TV", "qualifiers": {"picture_quality": "a crisp, watchable everyday picture", "price": "a budget-friendly price"}},
        "CLONE_HD": {"name": "CinemaPro Smart TV", "qualifiers": {"picture_quality": "near the top of the expert rankings", "price": "a premium price"}},
    },
    "water_bottles": {
        "HF": {"name": "AquaPod Water Bottle", "qualifiers": {"capacity": "right for a workout or a short commute", "price": "an impulse-buy price"}},
        "HD": {"name": "HydraTank Water Bottle", "qualifiers": {"capacity": "enough to skip refills most of the day", "price": "a mid-shelf price"}},
        "DECOY": {"name": "SipMate Water Bottle", "qualifiers": {"capacity": "runs small for a full workout", "price": "a low price for the shelf"}},
        "RANGE_DECOY": {"name": "DewDrop Water Bottle", "qualifiers": {"capacity": "barely enough for a coffee break", "price": "priced like an impulse buy"}},
        "PHANTOM": {"name": "AquaLite Water Bottle", "qualifiers": {"capacity": "sized for a workout or a quick errand", "price": "spare-change pricing"}},
        "EXTREME": {"name": "TrailKeg Water Bottle", "qualifiers": {"capacity": "carries a full day of water and then some", "price": "a top-shelf price"}},
        "SYM_DECOY": {"name": "PureFlask Water Bottle", "qualifiers": {"capacity": "sized for a single workout", "price": "a mid-shelf price"}},
        "CLONE_HF": {"name": "AquaPebble Water Bottle", "qualifiers": {"capacity": "right for a workout or a short commute", "price": "an impulse-buy price"}},
        "CLONE_HD": {"name": "HydraJug Water Bottle", "qualifiers": {"capacity": "enough to skip refills most of the day", "price": "a mid-shelf price"}},
    },
}

# Option code -> enrichment key. CLONE resolves through its clone_of field (CLONE_HF / CLONE_HD).
CODE_TO_KEY = {"HF": "HF", "HD": "HD", "DECOY": "DECOY", "RANGE_DECOY": "RANGE_DECOY",
               "PHANTOM": "PHANTOM", "EXTREME": "EXTREME", "SYM_DECOY": "SYM_DECOY"}


def enrichment_key(opt):
    """The enrichment-table key for one option dict (CLONE resolves via clone_of)."""
    code = (opt.get("code") or "").upper()
    if code == "CLONE":
        return "CLONE_" + (opt.get("clone_of") or "HF").upper()
    return CODE_TO_KEY.get(code)


def stimulus_is_enriched(stim):
    """Whether the final calibration lock enrichment scope covers this stimulus (category, tier, structure)."""
    return (stim.get("category") in ENRICHMENT
            and stim.get("memorization_tier") in ENRICHMENT_SCOPE["tiers"]
            and stim.get("structure") in ENRICHMENT_SCOPE["structures"])
