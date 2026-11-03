# Full dress rehearsal (analyze.py on synthetic data)

(synth.py plants known human effects
and a model archetype for every named scenario S1-S7 of decision tree B and the three worked walk-throughs
of Web Appendix C; this rehearsal runs the REAL pipeline and asserts the complete contract-C pack
renders and routes every planted branch, plus one planted case per repaired defect. The Stage 2 run executes the
SAME code on real contract-A/B exports.)

seed=20260613  runtime=73.52s  pack=results_pack/

## PASS/FAIL table
| check | result | detail |
|---|---|---|
| pack renders with ZERO missing values | PASS | [] |
| numbers.json carries every key the manuscript references | PASS | [] |
| human criterion: positive controls FRQ+SOT replicate | PASS |  |
| human criterion: phantom PHT fails (planted null) and is EQUIVALENT (90% interval inside +/-4pp) | PASS | PHT delta_pp=-0.47 CI90=[-1.22, 0.27] |
| T1 detects PARROT steep memorization gradient | PASS | steep: fidelity falls down the gradient -> retrieval, not behavior (S2) |
| T1 reads FAITHFUL as flat, or leaves it not resolved (never steep) | PASS | not resolved: the 95 percent interval of the drop (-0.218 to 0.315) does not settle the reading (point reading: flat: fidelity is genuine behavior, not retrieva |
| T2 reads OVERRIDER as recognizes-but-does-not-show | PASS | recognizes-but-does-not-show -> rational override (predicts LOW/ANTI) |
| T3 detects REASONER ladder decline | PASS | declines down the ladder -> reason-construction (S3) |
| T4 reported descriptively for REASONER (no reading, decides no scenario) | PASS | descriptive: numbers minus pictures +0.764 (95 percent interval 0.177 to 1.172); no registered reading, decides no scenario |
| T5 detects CONVERGE family rising trajectory | PASS | newer more faithful -> fidelity is higher in the newer generation; no scenario assigned |
| model criterion: REFUSER -> not assessable | PASS |  |
| model criterion: CEILING -> no-room cells flagged, not assessable | PASS |  |
| model criterion: FAITHFUL -> assessable | PASS |  |
| routing: FAITHFUL -> S1 | PASS | S1 (possible: S1) |
| routing: PARROT -> S2+S4 | PASS | S2+S4 (possible: S2;S4) |
| routing: REASONER -> S3 | PASS | S3 (possible: S3) |
| routing: OVERRIDER -> S4 | PASS | S4 (possible: S4) |
| routing: DIVIDED_A -> S1 | PASS | S1 (possible: S1) |
| routing: DIVIDED_B -> S6 | PASS | S6 (possible: S6) |
| routing: CONVERGE_OLD -> S6 | PASS | S6 (possible: S6) |
| routing: CONVERGE_NEW -> S7 | PASS | S7 (possible: S7) |
| routing: WALK1_PARROT -> S2 | PASS | S2 (possible: S2) |
| routing: WALK2_MIXED -> S4 | PASS | S4 (possible: S4) |
| routing: R4_ARGUABLE_OVERRIDE -> S4 | PASS | S4 (possible: S4) |
| routing: R4_ARGUABLE_NORECOG -> S6 | PASS | S6 (possible: S6) |
| routing: OVERSHOOT_T1 -> S6 | PASS | S6 (possible: S6) |
| beside each model: the DIVIDED family's classes differ (HIGH and ANTI) and are reported, and decide nothing (S1 and S6) | PASS | DIVIDED_A: no (DIVIDED_A=HIGH;DIVIDED_B=ANTI); DIVIDED_B: no (DIVIDED_A=HIGH;DIVIDED_B=ANTI) |
| beside each model: the CONVERGE family's rising trajectory (T5) is reported for both members and decides nothing (S6 and S7) | PASS | CONVERGE_OLD: newer more faithful -> fidelity is highe; CONVERGE_NEW: newer more faithful -> fidelity is highe |
| routing: human data with most effects failing -> S5 (Human effects fail) | PASS | S5 |
| routing: CEILING -> CRITERION_FAIL | PASS | CRITERION_FAIL |
| routing: REFUSER -> CRITERION_FAIL | PASS | CRITERION_FAIL |
| walk-through 1 (match classic / diverge novel) -> S2 via T1 | PASS | S2 |
| walk-through 2 (faithful FRQ, reversed SOT) -> each effect's class and whether the model named the decoy, side by side | PASS | FRQ=HIGH;RNG=HIGH;PHT=fails in people;SOT=ANTI;SYM=HIGH;SIM=HIGH;MOT=HIGH | FRQ=no;RNG=no;PHT=not asked;SOT=yes;SYM=no;SIM=no;MOT=no |
| human FRQ tier-1 effect recovered near planted +10pp | PASS | 9.17pp |
| human SIM relative-share effect recovered near its planted size | PASS | 4.66pp vs planted ~5.36pp |
| FIX1 walk-through 2 routes to S4: its ANTI compromise effect means it does not match people, and it names the compromise decoy without following it (rational override present; retrieval and reason construction absent) | PASS | S4 (S2=absent;S3=absent;S4=present) |
| tree B: PARROT does not match people and shows two failure signatures at once, retrieval and rational override (S2+S4), both reported | PASS | S2+S4 (S2=present;S3=absent;S4=present) |
| tree B: CONVERGE_NEW matches people (no failure present) and names the decoy on effects it shows -> S7, a known effect reproduced | PASS | S7 (FRQ=yes;RNG=yes;PHT=not asked;SOT=yes;SYM=no;SIM=no;MOT=no) |
| FIX2a phantom (criterion-failed) cells exit scoring: none score as a fidelity class | PASS | 41 exit + 1 no-counterpart of 42 |
| FIX2b criterion-driven exit is general: a SECOND criterion-failed effect (SIM) also exits | PASS | PHT_repl=False SIM_repl=False FAITHFUL SIM t1=6.48pp -> no-human-counterpart |
| FIX3 secondary contrast range > frequency computed and ordered as registered | PASS | RNG-FRQ=2.44pp |
| FIX4 decoy-target HD/HF asymmetry moderator computed with planted HD>HF direction | PASS | FRQ HD-HF=2.92pp (HD present, HF weaker -> Heath-Chatterje) |
| FIX5 neutral-vs-persona divergence computed with planted persona-stronger reading | PASS | persona more faithful than neutral -> silicon sampling helps |
| FIX5 single-shot-vs-sequential divergence computed with planted history reading | PASS | sequential differs from single-shot -> the model carries within-session history |
| D1 a significantly REVERSED human effect (RNG planted at -5pp) is NOT replicated | PASS | RNG -3.55pp Holm p=4.44e-15 BF10=0.00449 |
| D1 registered half-normal Bayes factor: FRQ BF10 > 3, phantom BF10 < 1 | PASS | FRQ BF10=1e+12 PHT BF10=0.0231 |
| D2 Holm within families: six non-similarity effects together, similarity alone | PASS | FRQ:non_similarity,RNG:non_similarity,PHT:non_similarity,SOT:non_similarity,SYM:non_similarity,SIM:similarity,MOT:non_similarity |
| D3 first-trial rule: no false alarm on the main data (no planted divergence) | PASS | max |full-first|=2.51pp |
| D3 first-trial rule fires on the planted divergence at planned first-trial sizes; the fallback applies the 8-point floor | PASS | fired=['FRQ'] FRQ |full-first|=-10.15pp non-confirmatory after fallback: ['SOT', 'SIM', 'MOT'] |
| D5 format interaction: none detected on the main data (no planted interaction) | PASS | tests=['FRQ:pictures', 'FRQ:words', 'SOT:pictures', 'SOT:words'] significant=[] |
| D5 format interaction: planted pictures attenuation detected (FRQ:pictures, Holm), words untouched | PASS | FRQ:pictures -7.26pp Holm p=1e-05; FRQ:words 0.73pp |
| D6 compromise cells whose target starts ahead are held out of the pooled compromise contrast and reported as descriptive | PASS | 8 descriptive slices: 1|t1|numbers;2|t1|numbers;2|t2|numbers;4|t1|numbers;5|t1|numbers;6|t1|numbers;6|t2|pictures;7|t3|numbers |
| D6 the pooled compromise criterion reads the contrast with the descriptive slices removed | PASS | criterion 9.786pp = held-out contrast 9.786pp (all slices 10.309pp) |
| D6 registered sensitivity (every deviation-flagged slice excluded) computed; positive controls still replicate | PASS | criterion changes: '' |
| D7 memorization sensitivity: PARROT stays steep (in-limit, and baseline-adjusted); FAITHFUL stays flat or not resolved, never steep (both re-readings are resolved against their intervals) | PASS | PARROT adj drop=0.683 (12 slices, 2 dropped); FAITHFUL adj slope=-0.108 |
| D10 walk-through 3 WITH recognition: fidelity rises down the ordering (described by T3), the model does not match people, and it names the decoy where it misses the effect -> rational override, S4 | PASS | reversed ladder: fidelity rises down the ladder -> evidence ; S4 |
| D10 walk-through 3 WITHOUT recognition: the same reversed ordering, every failure signature absent -> S6 | PASS | reversed ladder: fidelity rises down the ladder -> evidence ; S6 |
| R1 PARROT's published-tier phantom (humans null) is listed as an effect without a human counterpart; no ANTI on a failed effect | PASS | [(1, 8.33)] |
| R2 S5 needs four of the six non-similarity effects: 4 fail -> S5; 3 fail (+ similarity) -> not S5 | PASS | 4-fail->True, 3-fail+SIM->False |
| R3 no account is attached: every model's row reports each effect's class and whether it named the decoy, and the routing file has no account column | PASS | FAITHFUL: FRQ=HIGH;RNG=HIGH;PHT=fails in people;SOT=HIGH;SYM=HIGH;SIM=HIGH;MOT=HIGH |
| I2-1 a model effect opposite to the human effect: -2.9 vs +4 and -2.0 vs +2.5 are LOW, -3.5 vs +4 is ANTI | PASS | ('LOW', 'LOW', 'ANTI') |
| I2-2 OVER: a threefold published-tier overshoot is OVER overall, every published-tier cell reads as retrieval of a described regularity, and T1 does not read it as steep | PASS | overall=OVER classes=['OVER', 'OVER', 'OVER', 'OVER', 'OVER'] T1=not resolved: the 95 percent interval of |
| I2-3 classes on pooled estimates: the human side of each class is the confirmatory pooled estimate, and each model's overall class is the majority of its six non-similarity classes | PASS | same pooling=True majority rule=True |
| I2-5 every model point carries its number of calls and a bootstrap interval over calls (10 draws per text grid point, 60 per picture grid point) | PASS | FAITHFUL FRQ 9.28pp [7.58, 11.08] from 4080 calls; draws [10] / pictures [60] |
| I2-6 prompt sensitivity flagged beside every pooled class (FAITHFUL's upscaling effect is not flagged) | PASS | FAITHFUL SYM by paraphrase: 1:+18.04;2:+17.75;3:+13.43 |
| I2-8 memorization sensitivity adjusts for decoy-target identity beside baseline distance | PASS | FAITHFUL target coef=0.1171 baseline coef=-0.0058 |
| I2-9 positive controls: both hold on the main data; a null on the premium-target frequency-decoy cells fails that control | PASS | main failed=[]; planted premium null: FRQ premium -0.87pp, failed=['FRQ'] |
| I2-10 similarity supplement check: quiet on the main data; fires on a planted 10-point supplement difference | PASS | main diff=-0.10pp p=0.911; planted diff=9.33pp p=0 |
| I2-11 the deviation sensitivity set is the registered seven pairs computed from the calibration record, and the calibration flags agree with the sets computed by option identity (apart from the televisions flag, a known error in the flag) | PASS | 0|t2|numbers;2|t2|numbers;4|t2|numbers;6|t1|numbers;6|t2|pictures;7|t3|numbers;9|t3|numbers; flag mismatches: deviation [], compromise [] |
| R3-a FAITHFUL reaches S1: it matches people (overall class HIGH, no effect LOW or ANTI, no test shows or points to a failure) and names the decoy on no effect | PASS | S1; T1 not resolved: the 95 percent interval of the drop ; T3 flat: pattern mimicry at depth, ladder gives the a |
| R2-1 every T1 and T3 reading is resolved against an interval of the joint bootstrap; the human side varies (FAITHFUL's deterministic prompts still give a T1 interval of positive width around its point) | PASS | FAITHFUL drop 0.044 [-0.218, 0.315]; routes  |

## OVERALL: ALL CHECKS PASS

Scenario routing: FAITHFUL=S1, PARROT=S2+S4, REASONER=S3, OVERRIDER=S4, DIVIDED_A=S1, DIVIDED_B=S6, CONVERGE_OLD=S6, CONVERGE_NEW=S7, WALK1_PARROT=S2, WALK2_MIXED=S4, CEILING=CRITERION_FAIL, REFUSER=CRITERION_FAIL, R4_ARGUABLE_OVERRIDE=S4, R4_ARGUABLE_NORECOG=S6, OVERSHOOT_T1=S6, (human data)=S5.

## The same archetypes under the ruled sampling noise (REPORTED, not a pass condition)

The pass/fail table above runs the registered call plan (orders x paraphrases x 10 draws, 60 for pictures) with every prompt deterministic and the cell shares exactly as planted. Below, the same seed re-routes every archetype with the ruled binomial draws. A route that is not resolved is the design's precision, not a code defect; power/MODEL_NOISE_STABILITY.md gives the rates over many seeds. Here: 23 of 30 routed as planted, 6 not resolved, 1 partly resolved (a planted signature present, the other planted ones still possible), 0 to another scenario.

| model noise | archetype | planted | routed | T1 reading |
|---|---|---|---|---|
| every call an independent draw at the planted share | FAITHFUL | S1 | S1 | not resolved |
| every call an independent draw at the planted share | PARROT | S2+S4 | NOT_RESOLVED (open) | not resolved |
| every call an independent draw at the planted share | REASONER | S3 | S3 | not resolved |
| every call an independent draw at the planted share | OVERRIDER | S4 | S4 | not resolved |
| every call an independent draw at the planted share | DIVIDED_A | S1 | S1 | not resolved |
| every call an independent draw at the planted share | DIVIDED_B | S6 | NOT_RESOLVED (open) | not resolved |
| every call an independent draw at the planted share | CONVERGE_OLD | S6 | NOT_RESOLVED (open) | not resolved |
| every call an independent draw at the planted share | CONVERGE_NEW | S7 | S7 | not resolved |
| every call an independent draw at the planted share | WALK1_PARROT | S2 | S2 | steep |
| every call an independent draw at the planted share | WALK2_MIXED | S4 | S4 | not resolved |
| every call an independent draw at the planted share | R4_ARGUABLE_OVERRIDE | S4 | S4 | not resolved |
| every call an independent draw at the planted share | R4_ARGUABLE_NORECOG | S6 | NOT_RESOLVED (open) | not resolved |
| every call an independent draw at the planted share | OVERSHOOT_T1 | S6 | S6 | not resolved |
| every call an independent draw at the planted share | CEILING | CRITERION_FAIL | CRITERION_FAIL | insufficient tiers |
| every call an independent draw at the planted share | REFUSER | CRITERION_FAIL | CRITERION_FAIL | not resolved |
| each prompt gives its modal answer in 90 percent of its draws | FAITHFUL | S1 | S1 | not resolved |
| each prompt gives its modal answer in 90 percent of its draws | PARROT | S2+S4 | S2 (partly resolved) | steep |
| each prompt gives its modal answer in 90 percent of its draws | REASONER | S3 | S3 | not resolved |
| each prompt gives its modal answer in 90 percent of its draws | OVERRIDER | S4 | S4 | flat |
| each prompt gives its modal answer in 90 percent of its draws | DIVIDED_A | S1 | S1 | not resolved |
| each prompt gives its modal answer in 90 percent of its draws | DIVIDED_B | S6 | S6 | flat |
| each prompt gives its modal answer in 90 percent of its draws | CONVERGE_OLD | S6 | NOT_RESOLVED (open) | flat |
| each prompt gives its modal answer in 90 percent of its draws | CONVERGE_NEW | S7 | S7 | not resolved |
| each prompt gives its modal answer in 90 percent of its draws | WALK1_PARROT | S2 | S2 | steep |
| each prompt gives its modal answer in 90 percent of its draws | WALK2_MIXED | S4 | S4 | not resolved |
| each prompt gives its modal answer in 90 percent of its draws | R4_ARGUABLE_OVERRIDE | S4 | S4 | not resolved |
| each prompt gives its modal answer in 90 percent of its draws | R4_ARGUABLE_NORECOG | S6 | NOT_RESOLVED (open) | not resolved |
| each prompt gives its modal answer in 90 percent of its draws | OVERSHOOT_T1 | S6 | S6 | not resolved |
| each prompt gives its modal answer in 90 percent of its draws | CEILING | CRITERION_FAIL | CRITERION_FAIL | insufficient tiers |
| each prompt gives its modal answer in 90 percent of its draws | REFUSER | CRITERION_FAIL | CRITERION_FAIL | not resolved |
