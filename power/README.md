# Power

This folder contains the power of the pre-registered tests of the human study, computed by formula and by simulation,
with the numbers that we cite in the Method and Web Appendix E. It also contains simulations of the whole analysis.
With them, we measure how often each simulated model still reaches its intended conclusion when every model answer
is a random draw, and the smallest difference that we can resolve with each test of the three accounts and each
descriptive comparison.

| File | What it is |
|---|---|
| `power_sim.py`, `RESULTS.md` | Power for one category (about 700 choices in each condition), for the ten categories pooled (about 7,000), and for the pooled first choices of each participant (about 1,000). Each is computed by the normal approximation and checked with 50,000 simulated experiments (seed 11), at alpha .05 and at the strictest correction for multiple tests (alpha divided by seven) |
| `clustered_power.py`, `CLUSTERED_POWER.md` | Whether the correlation among one participant's seven choices lowers the power of the pooled tests. The simulation gives each participant a random intercept, at several sizes of the correlation within a participant, and compares tests that treat each participant as a cluster with tests that do not (seed 7; needs numpy) |
| `power_added_cells.py`, `POWER_ADDED_CELLS.md` | Power for the cells added to Survey 1: both placements of the near-copy in the similarity set, the price-free test and the extremity control |
| `power_format_interaction.py`, `POWER_FORMAT_INTERACTION.md` | Power of the four tests of whether the format changes an effect, at the planned sizes, with the numbers version at the actual sizes of its cells in Survey 1 (Table WA-E3; seed 20260929) |
| `power_compromise_pooled.py`, `POWER_COMPROMISE_POOLED.md` | Power of the pooled compromise test once the compromise cells that are only described leave it, and of the other five effects except similarity, with the Holm correction across those six effects (seed 20260929) |
| `power_control_and_first_trial.py`, `POWER_CONTROL_AND_FIRST_TRIAL.md` | The power of the frequency-decoy positive control on its three cells (the hard drives and the televisions at the new values and the robot vacuums) and of the pooled test of first choices that replaces the benchmarks when the check of first choices applies (Web Appendix E; 4,000 runs per row) |
| `table_simulated_conclusions.py`, `TABLE_SIMULATED_CONCLUSIONS.md` | Table WA-E6: how often the analysis reached each conclusion for each of the thirteen simulated models, read from `model_noise_stability_runs.csv` |
| `first_trial_rule_sim.py`, `FIRST_TRIAL_RULE_SIM.md` | The rate of false alarms and the power of the pre-registered check of first choices, at the planned sizes of the cells (Table WA-E2; seed 20260929) |
| `model_noise_stability.py`, `MODEL_NOISE_STABILITY.md`, `model_noise_stability_runs.csv` | How often each simulated model reaches its intended conclusion, reaches no resolved conclusion, or reaches a wrong one, when every model call is a random draw at the share that we built into the model. The simulation runs the whole analysis 200 times, on a pool of worker processes |
| `resolution_statement.py`, `RESOLUTION_STATEMENT.md`, `resolution_statement_runs.csv`, `resolution_statement_summary.json` | For the three tests and the two descriptive comparisons, the counterpart of power: the smallest true difference that we resolve in 80 percent of runs with each of them and with each boundary between fidelity classes, at the planned sizes and with the pre-registered plan of model calls (Table WA-E4; the whole analysis, 200 seeds, on a pool of worker processes) |
| `pattern_test_resolution.json` | A stored input that this folder does not compute: the rows of Table WA-E4 for the test of retrieval, the test of reason-based choice, the format comparison and the comparison of older and newer models in the pre-registered design. They come from the runs of `resolution_statement.py` itself, with 200 runs at each true difference from 0.3 to 2 and the pre-registered functions of the tests, recorded before registration. The file says how we made it, and `resolution_statement.py` reads it |
| `faithful_resolution_by_sample.py`, `FAITHFUL_RESOLUTION_BY_SAMPLE.md` | How large a sample the simulated model that matches people needs before the analysis concludes, at the pre-registered 95 percent level, that it matches. The simulation uses human samples of 1 to 8 times the planned size, with and without the noise of repeated model calls |

## Meaning of the numbers

1. **The pooled tests are the confirmatory tests.** Pooled across ten categories (about 7,000 choices in each
   condition), the power to detect an effect of 4 percentage points is 1.00 at alpha .05, and 0.98 under the
   strictest correction (alpha divided by seven).
2. **The results of single categories are reported, but they are not confirmatory.** In one category (700 choices
   in each condition), the power to detect an effect of 8 points is 0.85 at alpha .05, but only 0.63 under the
   strictest correction. We therefore make the pooled tests confirmatory and describe how the effects differ
   across categories.
3. **The check of first choices has enough power when pooled.** With one choice per participant (about 1,000 in
   each condition, pooled), the power to detect an effect of 8 points is 0.95 at alpha .05 (0.82 under the strictest
   correction). `FIRST_TRIAL_RULE_SIM.md` gives the rate of false alarms and the power of the pre-registered check
   directly.
4. **The tests of the format and the pooled compromise test** have their power at the planned sizes in
   `POWER_FORMAT_INTERACTION.md` and `POWER_COMPROMISE_POOLED.md`.
5. **The tests of the three accounts and the two descriptive comparisons have no power in the usual sense,**
   because we run no significance test on a model effect. Their counterpart is the smallest true difference that
   we resolve with each in 80 percent of runs (`RESOLUTION_STATEMENT.md`, Table WA-E4). In
   `FAITHFUL_RESOLUTION_BY_SAMPLE.md`, we give how large a sample the analysis would need to conclude that the
   simulated model that matches people does match.

We apply the Holm correction within families of tests, which can only give more power than the floors in points 1
to 3.

## Commands

```
python power/power_sim.py                  # about 20 seconds
python power/clustered_power.py            # about 2 minutes
python power/power_added_cells.py
python power/power_format_interaction.py
python power/power_compromise_pooled.py
python power/first_trial_rule_sim.py       # about 30 seconds
python power/power_control_and_first_trial.py   # about 5 minutes
python power/model_noise_stability.py      # about 10 minutes on 8 workers
python power/table_simulated_conclusions.py
python power/resolution_statement.py       # about 45 minutes
python power/faithful_resolution_by_sample.py   # about 8 minutes
```

`python run_all.py --part power` runs all but the last three and checks each report against the copy in this
repository. `python run_all.py --part power --full` adds the last three.
