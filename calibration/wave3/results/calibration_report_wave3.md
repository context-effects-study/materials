# Calibration report - wave3

(Auto-written by pretest/calibration_analysis.py. Export: `calibration_wave3_for_analysis.csv`. Band: TARGET 40-45% / hard limits 25-75%. Bundled design: one choice per category per respondent; respondent = cluster; the per-pair cluster-robust error equals the binomial error because no respondent contributes twice to a pair.)

- responses ingested: 467 rows -> 4131 kept choice rows from 459 kept respondents; 8 respondents excluded ([('speeder', 4), ('attention', 4)])
- unmapped BIN rows (not a calibration pair): 0
- pairs with a within-pair duplicate respondent (must be 0): 0

**TERMINAL WAVE.** Every pair is scored against the terminal lock criterion (CALIBRATION_DESIGN wave-3 amendment (a), fixed 2026-07-02 before any wave-3 data): LOCK when the point estimate is in [40, 45]; OR the 95% CI overlaps that band AND the point is in [33, 50] (compromise target disadvantaged and non-extreme). A pair failing both routes to its pre-registered stimulus-defect contingency and is reported. Locked values (with the enrichment content) enter stimuli.json at G3, followed by the EXC re-derivation step.

## Published tier-2 (adjustable)

| pair | n | TARGET share | 95% CI | cluster SE | band verdict | terminal lock verdict | disposition |
|---|---|---|---|---|---|---|---|
| pub_t2::BIN_backpacks_t2 | 459 | 28.5% | [24.6, 32.8] | 2.1pp | ADJUST | DEFECT CONTINGENCY (pre-registered) | route to the pre-registered stimulus-defect contingency (terminal wave) |
| pub_t2::BIN_bluetooth_speakers_t2 | 153 | 35.9% | [28.8, 43.8] | 3.9pp | ADJUST | LOCK (CI-overlap route) | values lock at G3 (with the enrichment content) |
| pub_t2::BIN_earbuds_t2 | 459 | 61.0% | [56.5, 65.4] | 2.3pp | ADJUST | DEFECT CONTINGENCY (pre-registered) | route to the pre-registered stimulus-defect contingency (terminal wave) |
| pub_t2::BIN_hard_drives_t2 | 151 | 47.0% | [39.2, 55.0] | 4.1pp | ADJUST | LOCK (CI-overlap route) | values lock at G3 (with the enrichment content) |
| pub_t2::BIN_restaurants_t2 | 459 | 31.2% | [27.1, 35.5] | 2.2pp | ADJUST | DEFECT CONTINGENCY (pre-registered) | route to the pre-registered stimulus-defect contingency (terminal wave) |
| pub_t2::BIN_televisions_t2 | 153 | 49.0% | [41.2, 56.9] | 4.1pp | ADJUST | LOCK (CI-overlap route) | values lock at G3 (with the enrichment content) |

## Invented tier-3 (adjustable)

| pair | n | TARGET share | 95% CI | cluster SE | band verdict | terminal lock verdict | disposition |
|---|---|---|---|---|---|---|---|
| inv_t3::BIN_electric_kettles_t3 | 459 | 44.7% | [40.2, 49.2] | 2.3pp | IN BAND | LOCK (point in band) | values lock at G3 (with the enrichment content) |
| inv_t3::BIN_standing_desks_t3 | 459 | 66.7% | [62.2, 70.8] | 2.2pp | ADJUST | DEFECT CONTINGENCY (pre-registered) | route to the pre-registered stimulus-defect contingency (terminal wave) |

## Format module - words (adjustable wording)

| pair | n | TARGET share | 95% CI | cluster SE | band verdict | terminal lock verdict | disposition |
|---|---|---|---|---|---|---|---|
| words::BIN_bluetooth_speakers_t2 | 153 | 34.0% | [27.0, 41.8] | 3.8pp | ADJUST | LOCK (CI-overlap route) | values lock at G3 (with the enrichment content) |
| words::BIN_hard_drives_t2 | 155 | 40.0% | [32.6, 47.9] | 3.9pp | IN BAND | LOCK (point in band) | values lock at G3 (with the enrichment content) |
| words::BIN_televisions_t2 | 156 | 49.4% | [41.6, 57.1] | 4.0pp | ADJUST | LOCK (CI-overlap route) | values lock at G3 (with the enrichment content) |
| words::BIN_water_bottles_t2 | 229 | 44.1% | [37.8, 50.6] | 3.3pp | IN BAND | LOCK (point in band) | values lock at G3 (with the enrichment content) |

## Format module - pictures (adjustable rendering)

| pair | n | TARGET share | 95% CI | cluster SE | band verdict | terminal lock verdict | disposition |
|---|---|---|---|---|---|---|---|
| pictures::BIN_bluetooth_speakers_t2 | 153 | 37.3% | [30.0, 45.1] | 3.9pp | ADJUST | LOCK (CI-overlap route) | values lock at G3 (with the enrichment content) |
| pictures::BIN_hard_drives_t2 | 153 | 79.1% | [72.0, 84.8] | 3.3pp | HARD FLAG (outside 25-75; stimulus-defect branch) | DEFECT CONTINGENCY (pre-registered) | route to the pre-registered stimulus-defect contingency (terminal wave) |
| pictures::BIN_televisions_t2 | 150 | 38.7% | [31.2, 46.7] | 4.0pp | ADJUST | LOCK (CI-overlap route) | values lock at G3 (with the enrichment content) |
| pictures::BIN_water_bottles_t2 | 230 | 59.1% | [52.7, 65.3] | 3.2pp | ADJUST | DEFECT CONTINGENCY (pre-registered) | route to the pre-registered stimulus-defect contingency (terminal wave) |

## Geometry manipulation checks (structural validity; >=70% registered benchmark)

(Instrument: v2.2 (2026-07-02): RNG answer key corrected 1->2 to match the rebuilt dominated weak-axis-extending range decoy (wording unchanged — a confirmation re-check; wave 1 re-scored 29/57=51% at this key); FRQ + SOT clarified to concrete option-referencing forms with lettered context cards (Option A/B/C, computed keys); PHT/SYM/MOT/SIM identical to wave 1 (re-checks). Stimulus VALUES untouched. Decision rule pre-stated in CALIBRATION_DESIGN: a second FRQ/SOT miss of the 70% benchmark triggers ONE final registered margin-strengthening correction + a small wave-3 re-check.)

| structure | n | correct answers | rate | benchmark |
|---|---|---|---|---|
| FRQ | 135 | 46 | 34% | FAIL |
| RNG | 133 | 61 | 46% | FAIL |
| PHT | 131 | 114 | 87% | PASS |
| SOT | 130 | 115 | 88% | PASS |
| SYM | 137 | 97 | 71% | PASS |
| MOT | 134 | 124 | 93% | PASS |
| SIM | 134 | 44 | 33% | FAIL |

## Picture-comprehension item (DESCRIPTIVE — amendment (e); no registered gate)

Respondents shown it (kept, dealt >=1 pictures pair): 389; answered the computed key (Option B: the option with more of the green-bar quality feature): 358 = **92%**. Reported with the trail as a comprehension indicator for the pictures manipulation; it gates nothing.

## Realism check — invented categories (registered threshold: mean >= 5.0 on the 7-point 'reads like a real product page' item + no recurring confusion in comments)

(Wave-3 re-check at the ENRICHED descriptions — the registered 'revise wording and re-check' remedy after the three wave-2 misses. kettles + desks re-shown from the respondent's own dealt slots at the wave-3 values; robot_vacuums — locked in wave 2, not dealt — shown as a static enriched page at its locked values. Scored on kept respondents.)

| category | n | mean | SD | % ratings >= 5 | verdict |
|---|---|---|---|---|---|
| electric_kettles | 459 | 4.36 | 1.65 | 53% | FAIL (revise wording + re-check) |
| robot_vacuums | 459 | 4.53 | 1.51 | 54% | FAIL (revise wording + re-check) |
| standing_desks | 459 | 4.68 | 1.51 | 60% | FAIL (revise wording + re-check) |

Open comments (kept respondents, non-empty): 122. Reviewed for recurring confusion; the raw texts stay in the export (never quoted at length here to keep the deposit scrub simple).

RR hygiene: calibration responses never enter confirmatory analyses; wave 3 is the TERMINAL wave — pairs lock under the criterion above or route to their pre-registered defect contingencies (no further waves); locked values + the enrichment content enter stimuli.json (calibration_locked) at G3, followed by the mandatory EXC re-derivation step and the geometry.py margin parameters under the freeze protocol (CALIBRATION_DESIGN wave-3 amendment).
