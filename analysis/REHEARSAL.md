# What the run on simulated data checks, and what it cannot show

`python analysis/analyze.py` without arguments runs the pre-registered analysis on simulated data. The script
`synth.py` writes data in which we built known answers. The analysis then runs on those data, and the run checks
that the analysis finds each known answer and writes every results file. The run uses no real data and no
network. On every run, the script writes its table of checks to `RESULTS_PACK_SELFTEST.md`, with each check
marked PASS or FAIL and the value that the analysis found. The run exits with an error unless every check
passes.

## What the simulated data cover

- **Step 0, the validity criteria.** In the simulated people, the two positive controls (the attraction effect
  with a frequency decoy, and the compromise effect) are built to replicate. The phantom effect is built to be
  zero, so it must fail the replication criterion and fall inside the equivalence band. One effect is built to
  reverse, and it must not count as replicated. Two simulated models are built to fail the criterion for
  readable answers: one refuses to answer, and one always chooses the same option. A third model is built to
  pass. A second set of simulated people, in which most effects fail, must lead to the conclusion that the
  human effects failed (S5).
- **Step 1, the human effects.** The analysis must estimate each effect close to the size that we built into
  the data, with intervals that treat each participant's choices as one cluster, and with estimates from first
  choices only. The data also contain one effect that differs between first and later choices. The check of
  first choices must detect it, and it must raise no false alarm on the other effects.
- **Step 2, the fidelity map and the classes.** The analysis places each model effect in one of the classes
  HIGH, OVER, PARTIAL, LOW and ANTI, by comparing its pooled estimate with the human effect. It also computes
  the sign agreement, the mean absolute deviation and the slope of the model effects on the human effects. The
  simulated model log has the pre-registered number of repeated calls (10 for each text prompt and 60 for each
  picture prompt). Beside every model effect, the results files give the number of calls and a descriptive
  bootstrap interval over calls. As pre-registered, no model effect has a significance test or a power
  calculation.
- **Step 3, the pattern tests.** The simulated models include five built patterns: a fall in fidelity from
  the published values to new values (the memorization test, T1); a model that names the decoy and does not
  follow it (the knows-it-versus-shows-it test, T2); a decline in fidelity down the argument-strength ordering
  (T3); a fall from numbers to pictures (the format test, T4, which is only described); and a rise in fidelity
  from the older to the newer model of one developer (the trajectory test, T5). The analysis must detect each
  pattern against its interval. The run also checks the tests of whether the format changes an effect, with and
  without a built-in difference, the secondary comparisons, the positive controls and the check of first
  choices.
- **Step 4, the conclusion for each model.** The analysis asks whether each simulated model matches people and,
  if it does not, which failures it shows. Every simulated model must reach the conclusion that it was built to
  reach. Together, the models cover the seven scenarios S1 to S7, a model that shows two failures at once
  (retrieval and rational override), and a model that cannot be assessed. The three worked walk-throughs of Web
  Appendix C must also reach their pre-registered conclusions. A separate script,
  `power/model_noise_stability.py`, measures how often each simulated model still reaches its conclusion when
  every model answer is a random draw.
- **Each rule on its own.** `test_analysis.py` checks each rule on small data in which that rule alone decides the
  outcome. `mutate_checks.py` breaks each rule in a copy of the code and requires a test or the run on simulated
  data to fail.
- **The results files.** Every file must be complete, with no missing value except in the cells that are blank by
  definition. Every number that the manuscript will cite must have its key in `numbers.json`. With the fixed seed,
  every data file must come out identical on every run; only the line with the run time in `RUN_REPORT.md`
  changes.

## What the run cannot show

- **The data are simulated.** On real data (`analyze.py --human ... --model ...`), the analysis runs the same code
  for scoring, testing and reaching conclusions. We ran it end to end on simulated files written in the formats of
  the real data. We have not run it on real data, because none exist yet.
- **The run shows that the code does what the plan says, not that the plan is right.** We chose the built answers
  so that every branch of the analysis runs. They are not predictions.
- **The standard error of a difference between two cells** treats each participant as a cluster, and the code
  computes it from a formula (`statlib.cluster_robust_diff_props`). This is the standard estimator for such a
  difference. It is exact when each participant appears at most once in each cell, and the design ensures this,
  because no script shows a participant the same cell twice.
