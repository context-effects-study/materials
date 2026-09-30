# What the dress rehearsal shows, and its limits

The dress rehearsal is what `python analysis/analyze.py` runs. It builds data with known answers planted in
them (`synth.py`), runs the registered analysis on those data, and checks that the analysis recovers each
planted answer and writes the complete results pack. It uses no real data and no network. Its table of
checks, each marked PASS or FAIL with the value found, is written to `RESULTS_PACK_SELFTEST.md` on every run,
and the run exits with an error unless every check passes.

## What the planted data cover

- **Step 0, the validity criteria.** Human effects planted to replicate (the two positive controls,
  attraction with a frequency decoy and compromise), a planted true null (the phantom, which must fail the
  replication criterion and fall inside the equivalence band), a planted reversed effect (which must not
  count as replicated), and models built to fail the data-quality criterion (a refuser and a model at the
  ceiling) beside one that passes.
- **Step 1, the human benchmarks.** Effects recovered near their planted sizes, with cluster-robust
  intervals and first-choice-only estimates, and a planted divergence that the first-choice check must catch
  while raising no false alarm on the main data.
- **Step 2, the fidelity map and classes.** Each model's effects scored against the human benchmark into
  HIGH, OVER, PARTIAL, LOW or ANTI on the pooled estimate, with sign agreement, mean absolute deviation and a
  calibration slope. The synthetic model log carries the registered repeated draws (10 per text prompt, 60
  per picture prompt), and beside every model effect the pack reports the number of calls and a descriptive
  bootstrap interval over calls. By design the model effects carry no test and no power.
- **Step 3, the pattern tests.** A planted memorization gradient (T1), a planted recognition-probe outcome
  (T2), a planted decline down the argument-strength ladder (T3), a planted drop from numbers to pictures
  (T4) and a planted rise across two generations of one model family (T5), each reading resolved against
  its interval; the format interaction tests with and without a planted attenuation; the secondary contrasts
  and moderators; the positive control and the first-choice check.
- **The decision tree.** Every planted model profile must be routed to the scenario it was built to show
  (S1 to S7, the reversed-ladder readings, and the not-assessable branch), and the two worked walk-throughs
  must reach their registered readings. How often each profile still reaches its scenario once the model
  answers carry the sampling noise of the repeated draws is measured separately by
  `power/model_noise_stability.py`.
- **The rules one by one.** `test_analysis.py` checks each rule on small data in which that rule alone decides
  the outcome, and `mutate_checks.py` breaks each rule in a copy of the code and requires a test or the
  rehearsal to fail.
- **The pack.** Every file is written with no missing value except the cells that are blank by definition,
  every number the manuscript cites has its key in `numbers.json`, and at the fixed seed every data file is
  identical from run to run (only the runtime line of `RUN_REPORT.md` changes).

## Limits

- **Synthetic data only.** The analysis of real data (`analyze.py --human ... --model ...`) runs the same
  scoring, testing and routing code, and it has been run end to end on synthetic files written in the real
  data formats; it has not been run on real data because none exist yet.
- **The rehearsal proves the code does what the plan says, not that the plan is right.** The planted truths
  are chosen to exercise every branch; they are not predictions.
- **The cluster-robust standard error** of a two-cell contrast is computed in closed form with each
  participant as a cluster (`statlib.cluster_robust_diff_props`). This is the standard estimator for that
  contrast and is exact when each participant appears once per cell, which the backbone's no-repeat design
  ensures.
