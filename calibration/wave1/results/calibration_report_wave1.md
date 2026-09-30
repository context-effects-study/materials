# Calibration report - wave1

(Auto-written by pretest/calibration_analysis.py. Export: `calibration_wave1_for_analysis.csv`. Band: TARGET 40-45% / hard limits 25-75%. Bundled design: one choice per category per respondent; respondent = cluster; the per-pair cluster-robust error equals the binomial error because no respondent contributes twice to a pair.)

- responses ingested: 402 rows -> 3920 kept choice rows from 392 kept respondents; 10 respondents excluded ([('speeder', 6), ('attention', 2), ('preview', 1), ('attention;speeder', 1)])
- unmapped BIN rows (not a calibration pair): 0
- pairs with a within-pair duplicate respondent (must be 0): 0

## Published tier-1 (CHECK-ONLY - never adjusted)

| pair | n | TARGET share | 95% CI | cluster SE | verdict | mechanical nudge (logged) |
|---|---|---|---|---|---|---|
| pub_t1::BIN_backpacks_t1 | 196 | 42.9% | [36.1, 49.9] | 3.5pp | IN BAND |  |
| pub_t1::BIN_bluetooth_speakers_t1 | 98 | 73.5% | [64.0, 81.2] | 4.5pp | OUT OF BAND (tier-1 CHECK-ONLY; reported, never adjusted) | (check-only: reported, values fixed by fidelity to the published source) |
| pub_t1::BIN_earbuds_t1 | 197 | 71.6% | [64.9, 77.4] | 3.2pp | OUT OF BAND (tier-1 CHECK-ONLY; reported, never adjusted) | (check-only: reported, values fixed by fidelity to the published source) |
| pub_t1::BIN_hard_drives_t1 | 98 | 43.9% | [34.5, 53.7] | 5.0pp | IN BAND |  |
| pub_t1::BIN_restaurants_t1 | 195 | 64.6% | [57.7, 71.0] | 3.4pp | OUT OF BAND (tier-1 CHECK-ONLY; reported, never adjusted) | (check-only: reported, values fixed by fidelity to the published source) |
| pub_t1::BIN_televisions_t1 | 95 | 74.7% | [65.2, 82.4] | 4.5pp | OUT OF BAND (tier-1 CHECK-ONLY; reported, never adjusted) | (check-only: reported, values fixed by fidelity to the published source) |
| pub_t1::BIN_water_bottles_t1 | 100 | 80.0% | [71.1, 86.7] | 4.0pp | HARD FLAG (outside 25-75; stimulus-defect branch) | route to the pre-registered stimulus-defect branch |

## Published tier-2 (adjustable)

| pair | n | TARGET share | 95% CI | cluster SE | verdict | mechanical nudge (logged) |
|---|---|---|---|---|---|---|
| pub_t2::BIN_backpacks_t2 | 196 | 49.5% | [42.6, 56.4] | 3.6pp | ADJUST | raise HD price 59.99 -> 62.99 (imbalance 4.5pp -> +4.5% of value, rounded) |
| pub_t2::BIN_bluetooth_speakers_t2 | 97 | 61.9% | [51.9, 70.9] | 5.0pp | ADJUST | raise HD price 89.99 -> 109.0 (imbalance 16.9pp -> +16.9% of value, rounded) |
| pub_t2::BIN_earbuds_t2 | 195 | 53.8% | [46.8, 60.7] | 3.6pp | ADJUST | raise HD price 29.99 -> 32.99 (imbalance 8.8pp -> +8.8% of value, rounded) |
| pub_t2::BIN_hard_drives_t2 | 98 | 69.4% | [59.7, 77.6] | 4.7pp | ADJUST | raise HD price 99.99 -> 119.0 (imbalance 24.4pp -> +24.4% of value, rounded) |
| pub_t2::BIN_restaurants_t2 | 197 | 51.8% | [44.8, 58.7] | 3.6pp | ADJUST | raise HD price 58 -> 61.99 (imbalance 6.8pp -> +6.8% of value, rounded) |
| pub_t2::BIN_televisions_t2 | 99 | 60.6% | [50.8, 69.7] | 4.9pp | ADJUST | raise HD price 399.99 -> 459.0 (imbalance 15.6pp -> +15.6% of value, rounded) |
| pub_t2::BIN_water_bottles_t2 | 96 | 41.7% | [32.3, 51.7] | 5.1pp | IN BAND |  |

## Invented tier-3 (adjustable)

| pair | n | TARGET share | 95% CI | cluster SE | verdict | mechanical nudge (logged) |
|---|---|---|---|---|---|---|
| inv_t3::BIN_electric_kettles_t3 | 392 | 72.2% | [67.6, 76.4] | 2.3pp | ADJUST | raise HF price 24.99 -> 31.99 (imbalance 27.2pp -> +27.2% of value, rounded) |
| inv_t3::BIN_robot_vacuums_t3 | 392 | 33.7% | [29.2, 38.5] | 2.4pp | ADJUST | raise HF price 149.99 -> 159.0 (imbalance 6.3pp -> +6.3% of value, rounded) |
| inv_t3::BIN_standing_desks_t3 | 392 | 80.1% | [75.9, 83.8] | 2.0pp | HARD FLAG (outside 25-75; stimulus-defect branch) | route to the pre-registered stimulus-defect branch |

## Format module - words (adjustable wording)

| pair | n | TARGET share | 95% CI | cluster SE | verdict | mechanical nudge (logged) |
|---|---|---|---|---|---|---|
| words::BIN_bluetooth_speakers_t2 | 97 | 61.9% | [51.9, 70.9] | 5.0pp | ADJUST | raise HD price 89.99 -> 109.0 (imbalance 16.9pp -> +16.9% of value, rounded) |
| words::BIN_hard_drives_t2 | 97 | 67.0% | [57.2, 75.6] | 4.8pp | ADJUST | raise HD price 99.99 -> 119.0 (imbalance 22.0pp -> +22.0% of value, rounded) |
| words::BIN_televisions_t2 | 99 | 63.6% | [53.8, 72.4] | 4.9pp | ADJUST | raise HD price 399.99 -> 469.0 (imbalance 18.6pp -> +18.6% of value, rounded) |
| words::BIN_water_bottles_t2 | 97 | 32.0% | [23.5, 41.8] | 4.8pp | ADJUST | raise HF price 8.99 -> 9.49 (imbalance 8.0pp -> +8.0% of value, rounded) |

## Format module - pictures (adjustable rendering)

| pair | n | TARGET share | 95% CI | cluster SE | verdict | mechanical nudge (logged) |
|---|---|---|---|---|---|---|
| pictures::BIN_bluetooth_speakers_t2 | 100 | 39.0% | [30.0, 48.8] | 4.9pp | ADJUST | raise HF price 44.99 -> 44.99 (imbalance 1.0pp -> +1.0% of value, rounded) |
| pictures::BIN_hard_drives_t2 | 99 | 91.9% | [84.9, 95.8] | 2.8pp | HARD FLAG (outside 25-75; stimulus-defect branch) | route to the pre-registered stimulus-defect branch |
| pictures::BIN_televisions_t2 | 99 | 50.5% | [40.8, 60.1] | 5.1pp | ADJUST | raise HD price 399.99 -> 419.0 (imbalance 5.5pp -> +5.5% of value, rounded) |
| pictures::BIN_water_bottles_t2 | 99 | 56.6% | [46.7, 65.9] | 5.0pp | ADJUST | raise HD price 24.99 -> 27.99 (imbalance 11.6pp -> +11.6% of value, rounded) |

## Geometry manipulation checks (structural validity; >=70% registered benchmark)

(Instrument: wave-1 instrument (v2.1) RE-SCORED 2026-07-02 with the CORRECTED RNG answer key (1 -> 2, The second feature): the fielded key predated the 2026-07-01 RNG rebuild and keyed the wrong axis for the dominated, weak-axis-extending decoy. Re-scored rate 29/57 = 51% (identical on kept-only: all 57 RNG-assigned respondents survived the exclusions) - still FAIL vs the registered 70%. All other items unchanged from the fielded instrument. Correction note: RNG_KEY_CORRECTION_2026-07-02.md.)

| structure | n | correct answers | rate | benchmark |
|---|---|---|---|---|
| FRQ | 57 | 35 | 61% | FAIL |
| RNG | 57 | 29 | 51% | FAIL |
| PHT | 57 | 43 | 75% | PASS |
| SOT | 58 | 35 | 60% | FAIL |
| SYM | 57 | 51 | 89% | PASS |
| MOT | 59 | 50 | 85% | PASS |
| SIM | 57 | 47 | 82% | PASS |

RR hygiene: calibration responses never enter confirmatory analyses; adjustments follow the mechanical heuristic above and are re-tested in the next wave; tier-1 pairs are reported as-is; final values are locked into stimuli.json (calibration_locked) at G3, followed by the mandatory EXC re-derivation step (CALIBRATION_DESIGN).
