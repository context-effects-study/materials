# RUN_REPORT

(Auto-written every run.)

- mode: REHEARSAL
- seed: 20260613
- python: 3.13.13 (Windows)
- runtime_sec: 17.1
- human choice rows: 280000
- models scored: 15
- Bayes factor: half-normal prior, positive direction, scale 10.0 points
- tie-break for a majority class: the less faithful class, in the order ANTI, LOW, PARTIAL, OVER, HIGH (most to least conservative); the first wins

## Exclusion accounting (model calls)

| model | parse_rate | refusal_rate | cells lost | not assessable |
|---|---|---|---|---|
| FAITHFUL | 1.0 | 0.0 | 0+0 no-room | False |
| PARROT | 1.0 | 0.0 | 0+0 no-room | False |
| REASONER | 1.0 | 0.0 | 0+0 no-room | False |
| OVERRIDER | 1.0 | 0.0 | 0+0 no-room | False |
| DIVIDED_A | 1.0 | 0.0 | 0+0 no-room | False |
| DIVIDED_B | 1.0 | 0.0 | 0+0 no-room | False |
| CONVERGE_OLD | 1.0 | 0.0 | 0+0 no-room | False |
| CONVERGE_NEW | 1.0 | 0.0 | 0+0 no-room | False |
| WALK1_PARROT | 1.0 | 0.0 | 0+0 no-room | False |
| WALK2_MIXED | 1.0 | 0.0 | 0+0 no-room | False |
| CEILING | 1.0 | 0.0 | 0+35 no-room | True |
| REFUSER | 0.4978 | 0.2998 | 195+0 no-room | True |
| R4_ARGUABLE_OVERRIDE | 1.0 | 0.0 | 0+0 no-room | False |
| R4_ARGUABLE_NORECOG | 1.0 | 0.0 | 0+0 no-room | False |
| OVERSHOOT_T1 | 1.0 | 0.0 | 0+0 no-room | False |

## Human criterion (Step 0a)

| effect | Holm family | replicated | direction ok | Holm p | BF10 |
|---|---|---|---|---|---|
| FRQ | non_similarity | True | True | 0.0 | 1000000000000.0 |
| RNG | non_similarity | True | True | 0.0 | 1000000000000.0 |
| PHT | non_similarity | False | False | 0.294 | 0.02 |
| SOT | non_similarity | True | True | 0.0 | 1000000000000.0 |
| SYM | non_similarity | True | True | 0.0 | 1000000000000.0 |
| SIM | similarity | True | True | 0.0 | 1000000000000.0 |
| MOT | non_similarity | True | True | 0.0 | 1000000000000.0 |

## Scenario routing

| model | scenario | name |
|---|---|---|
| FAITHFUL | S1 | High fidelity |
| PARROT | S2+S4 | Retrieval only and rational override |
| REASONER | S3 | Reason construction |
| OVERRIDER | S4 | Rational override |
| DIVIDED_A | S1 | High fidelity |
| DIVIDED_B | S6 | A failure that no account predicts |
| CONVERGE_OLD | S6 | A failure that no account predicts |
| CONVERGE_NEW | S7 | A known effect reproduced |
| WALK1_PARROT | S2 | Retrieval only |
| WALK2_MIXED | S4 | Rational override |
| CEILING | CRITERION_FAIL | Not assessable (Step 0) |
| REFUSER | CRITERION_FAIL | Not assessable (Step 0) |
| R4_ARGUABLE_OVERRIDE | S4 | Rational override |
| R4_ARGUABLE_NORECOG | S6 | A failure that no account predicts |
| OVERSHOOT_T1 | S6 | A failure that no account predicts |
| (human data) | S5 | Human effects fail |
