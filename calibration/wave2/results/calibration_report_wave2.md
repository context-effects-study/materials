# Calibration report - wave2

(Auto-written by pretest/calibration_analysis.py. Export: `calibration_wave2_for_analysis.csv`. Band: TARGET 40-45% / hard limits 25-75%. Bundled design: one choice per category per respondent; respondent = cluster; the per-pair cluster-robust error equals the binomial error because no respondent contributes twice to a pair.)

- responses ingested: 312 rows -> 3090 kept choice rows from 309 kept respondents; 3 respondents excluded ([('attention', 2), ('speeder', 1)])
- unmapped BIN rows (not a calibration pair): 0
- pairs with a within-pair duplicate respondent (must be 0): 0

## Published tier-2 (adjustable)

| pair | n | TARGET share | 95% CI | cluster SE | verdict | mechanical nudge (logged) |
|---|---|---|---|---|---|---|
| pub_t2::BIN_backpacks_t2 | 309 | 39.8% | [34.5, 45.4] | 2.8pp | ADJUST | raise HF price 34.99 -> 34.99 (imbalance 0.2pp -> +0.2% of value, rounded) |
| pub_t2::BIN_bluetooth_speakers_t2 | 104 | 64.4% | [54.9, 73.0] | 4.7pp | ADJUST | raise HD price 109.0 -> 129.0 (from the shown wave value) (imbalance 19.4pp -> +19.4% of value, rounded) |
| pub_t2::BIN_earbuds_t2 | 309 | 56.0% | [50.4, 61.4] | 2.8pp | ADJUST | raise HD price 32.99 -> 36.99 (from the shown wave value) (imbalance 11.0pp -> +11.0% of value, rounded) |
| pub_t2::BIN_hard_drives_t2 | 102 | 74.5% | [65.3, 82.0] | 4.3pp | ADJUST | raise HD price 119.0 -> 149.0 (from the shown wave value) (imbalance 29.5pp -> +29.5% of value, rounded) |
| pub_t2::BIN_restaurants_t2 | 309 | 39.8% | [34.5, 45.4] | 2.8pp | ADJUST | raise HF price 22 -> 21.99 (imbalance 0.2pp -> +0.2% of value, rounded) |
| pub_t2::BIN_televisions_t2 | 103 | 61.2% | [51.5, 70.0] | 4.8pp | ADJUST | raise HD price 459.0 -> 529.0 (from the shown wave value) (imbalance 16.2pp -> +16.2% of value, rounded) |

## Invented tier-3 (adjustable)

| pair | n | TARGET share | 95% CI | cluster SE | verdict | mechanical nudge (logged) |
|---|---|---|---|---|---|---|
| inv_t3::BIN_electric_kettles_t3 | 309 | 68.0% | [62.6, 72.9] | 2.7pp | ADJUST | raise HF price 31.99 -> 38.99 (from the shown wave value) (imbalance 23.0pp -> +23.0% of value, rounded) |
| inv_t3::BIN_robot_vacuums_t3 | 309 | 42.1% | [36.7, 47.6] | 2.8pp | IN BAND |  |
| inv_t3::BIN_standing_desks_t3 | 309 | 69.6% | [64.2, 74.4] | 2.6pp | ADJUST | raise HF price 269.0 -> 339.0 (from the shown wave value) (imbalance 24.6pp -> +24.6% of value, rounded) |

## Format module - words (adjustable wording)

| pair | n | TARGET share | 95% CI | cluster SE | verdict | mechanical nudge (logged) |
|---|---|---|---|---|---|---|
| words::BIN_bluetooth_speakers_t2 | 100 | 59.0% | [49.2, 68.1] | 4.9pp | ADJUST | raise HD price 109.0 -> 119.0 (from the shown wave value) (imbalance 14.0pp -> +14.0% of value, rounded) |
| words::BIN_hard_drives_t2 | 102 | 61.8% | [52.1, 70.6] | 4.8pp | ADJUST | raise HD price 119.0 -> 139.0 (from the shown wave value) (imbalance 16.8pp -> +16.8% of value, rounded) |
| words::BIN_televisions_t2 | 103 | 53.4% | [43.8, 62.7] | 4.9pp | ADJUST | raise HD price 459.0 -> 499.0 (from the shown wave value) (imbalance 8.4pp -> +8.4% of value, rounded) |
| words::BIN_water_bottles_t2 | 154 | 37.7% | [30.4, 45.5] | 3.9pp | ADJUST | raise HF price 8.99 -> 8.99 (imbalance 2.3pp -> +2.3% of value, rounded) |

## Format module - pictures (adjustable rendering)

| pair | n | TARGET share | 95% CI | cluster SE | verdict | mechanical nudge (logged) |
|---|---|---|---|---|---|---|
| pictures::BIN_bluetooth_speakers_t2 | 105 | 24.8% | [17.5, 33.8] | 4.2pp | HARD FLAG (outside 25-75; stimulus-defect branch) | route to the pre-registered stimulus-defect branch |
| pictures::BIN_hard_drives_t2 | 105 | 84.8% | [76.7, 90.4] | 3.5pp | HARD FLAG (outside 25-75; stimulus-defect branch) | route to the pre-registered stimulus-defect branch |
| pictures::BIN_televisions_t2 | 103 | 36.9% | [28.2, 46.5] | 4.8pp | ADJUST | raise HF price 139.99 -> 139.0 (imbalance 3.1pp -> +3.1% of value, rounded) |
| pictures::BIN_water_bottles_t2 | 155 | 60.0% | [52.1, 67.4] | 3.9pp | ADJUST | raise HD price 24.99 -> 28.99 (imbalance 15.0pp -> +15.0% of value, rounded) |

## Geometry manipulation checks (structural validity; >=70% registered benchmark)

(Instrument: v2.2 (2026-07-02): RNG answer key corrected 1->2 to match the rebuilt dominated weak-axis-extending range decoy (wording unchanged — a confirmation re-check; wave 1 re-scored 29/57=51% at this key); FRQ + SOT clarified to concrete option-referencing forms with lettered context cards (Option A/B/C, computed keys); PHT/SYM/MOT/SIM identical to wave 1 (re-checks). Stimulus VALUES untouched. Decision rule pre-stated in CALIBRATION_DESIGN: a second FRQ/SOT miss of the 70% benchmark triggers ONE final registered margin-strengthening correction + a small wave-3 re-check.)

| structure | n | correct answers | rate | benchmark |
|---|---|---|---|---|
| FRQ | 45 | 20 | 44% | FAIL |
| RNG | 44 | 26 | 59% | FAIL |
| PHT | 45 | 37 | 82% | PASS |
| SOT | 44 | 30 | 68% | FAIL |
| SYM | 45 | 40 | 89% | PASS |
| MOT | 45 | 39 | 87% | PASS |
| SIM | 44 | 25 | 57% | FAIL |

## Realism check — invented categories (registered threshold: mean >= 5.0 on the 7-point 'reads like a real product page' item + no recurring confusion in comments)

(The registered order put this check BEFORE the first calibration wave; it rides IN wave 2 instead — the ordering deviation is documented in CALIBRATION_WAVE1 s4 and the wave-2 MAPPING. Values shown to raters = the wave-2 shared values. Scored on kept respondents.)

| category | n | mean | SD | % ratings >= 5 | verdict |
|---|---|---|---|---|---|
| electric_kettles | 309 | 4.74 | 1.60 | 61% | FAIL (revise wording + re-check) |
| robot_vacuums | 309 | 4.53 | 1.63 | 53% | FAIL (revise wording + re-check) |
| standing_desks | 309 | 4.77 | 1.58 | 59% | FAIL (revise wording + re-check) |

Open comments (kept respondents, non-empty): 89. Reviewed for recurring confusion; the raw texts stay in the export (never quoted at length here to keep the deposit scrub simple).

RR hygiene: calibration responses never enter confirmatory analyses; adjustments follow the mechanical heuristic above and are re-tested in the next wave; tier-1 pairs are reported as-is; final values are locked into stimuli.json (calibration_locked) at G3, followed by the mandatory EXC re-derivation step (CALIBRATION_DESIGN).
