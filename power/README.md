# Power

This folder holds the power of the pre-registered tests of the human study, computed by formula and by simulation,
with the numbers that the Method and Web Appendix E cite. It also holds simulations of the whole analysis. These
show how often each simulated model still reaches its intended conclusion when every model answer is a random draw,
and the smallest difference that each pattern test can detect.

| File | What it is |
|---|---|
| `power_sim.py`, `RESULTS.md` | Power for one category (about 700 choices in each condition), for the ten categories pooled (about 7,000), and for the pooled first choices of each participant (about 1,000). Each is computed by the normal approximation and checked with 50,000 simulated experiments (seed 11), at alpha .05 and at the strictest correction for multiple tests (alpha divided by seven) |
| `clustered_power.py`, `CLUSTERED_POWER.md` | Whether the correlation among one participant's seven choices lowers the power of the pooled tests. The simulation gives each participant a random intercept, at several sizes of the correlation within a participant, and compares tests that treat each participant as a cluster with tests that do not (seed 7; needs numpy) |
| `power_added_cells.py`, `POWER_ADDED_CELLS.md` | Power for the cells added to Survey 1: both placements of the clone in the similarity set, the price-free test and the extremity control |
| `power_format_interaction.py`, `POWER_FORMAT_INTERACTION.md` | Power of the four tests of whether the format changes an effect, at the planned sizes, with the numbers version at the actual sizes of its cells in Survey 1 (Table WA-E3; seed 20260929) |
| `power_compromise_pooled.py`, `POWER_COMPROMISE_POOLED.md` | Power of the pooled compromise test once the compromise cells that are only described leave it, and of the other five effects except similarity, with the Holm correction across those six effects (seed 20260929) |
| `first_trial_rule_sim.py`, `FIRST_TRIAL_RULE_SIM.md` | The rate of false alarms and the power of the pre-registered check of first choices, at the planned sizes of the cells (Table WA-E2; seed 20260929) |
| `model_noise_stability.py`, `MODEL_NOISE_STABILITY.md`, `model_noise_stability_runs.csv` | How often each simulated model reaches its intended conclusion, reaches no resolved conclusion, or reaches a wrong one, when every model call is a random draw at the share that we built into the model. The simulation runs the whole analysis 20 times for each condition |
| `resolution_statement.py`, `RESOLUTION_STATEMENT.md`, `resolution_statement_runs.csv`, `resolution_statement_summary.json` | For the pattern tests, the counterpart of power: the smallest true difference that each pattern test (T1 to T5) and each boundary between fidelity classes detects in 80 percent of runs, at the planned sizes and with the pre-registered plan of model calls (Table WA-E4; the whole analysis, 20 seeds) |
| `pattern_test_resolution.json` | A stored input that this folder does not compute: the rows of Table WA-E4 for the pattern tests T1, T3, T4 and T5 in the pre-registered design. They come from a simulation of the design that we ran before registration, with 20 runs at each true difference from 0.2 to 2 and the pre-registered functions of the tests. The file says how we made it, and `resolution_statement.py` reads it |
| `faithful_resolution_by_sample.py`, `FAITHFUL_RESOLUTION_BY_SAMPLE.md` | How large a sample the simulated model that matches people needs before the analysis concludes, at the pre-registered 95 percent level, that it matches. The simulation uses human samples of 1 to 8 times the planned size, with and without the noise of repeated model calls |

## What the numbers mean

1. **The pooled tests are the confirmatory tests.** Pooled across ten categories (about 7,000 choices in each
   condition), the power to detect an effect of 4 percentage points is 1.00 at alpha .05, and 0.98 under the
   strictest correction (alpha divided by seven).
2. **The results of single categories are reported, but they are not confirmatory.** In one category (700 choices
   in each condition), the power to detect an effect of 8 points is 0.85 at alpha .05, but only 0.63 under the
   strictest correction. The protocol therefore makes the pooled tests confirmatory and describes how the effects
   differ across categories.
3. **The check of first choices has enough power when pooled.** With one choice per participant (about 1,000 in
   each condition, pooled), the power to detect an effect of 8 points is 0.95 at alpha .05 (0.82 under the strictest
   correction). `FIRST_TRIAL_RULE_SIM.md` gives the rate of false alarms and the power of the pre-registered check
   directly.
4. **The tests of the format and the pooled compromise test** have their power at the planned sizes in
   `POWER_FORMAT_INTERACTION.md` and `POWER_COMPROMISE_POOLED.md`.
5. **The pattern tests have no power in the usual sense,** because we run no significance test on a model effect.
   Their counterpart is the smallest true difference that each test detects in 80 percent of runs
   (`RESOLUTION_STATEMENT.md`, Table WA-E4). `FAITHFUL_RESOLUTION_BY_SAMPLE.md` shows how large a sample the analysis
   would need to conclude that the simulated model that matches people does match.

The analysis applies the Holm correction within families of tests, which can only give more power than the floors
in points 1 to 3.

## Run

```
python power/power_sim.py                  # about 20 seconds
python power/clustered_power.py            # about 2 minutes
python power/power_added_cells.py
python power/power_format_interaction.py
python power/power_compromise_pooled.py
python power/first_trial_rule_sim.py       # about 30 seconds
python power/model_noise_stability.py      # about 17 minutes
python power/resolution_statement.py       # about 45 minutes
python power/faithful_resolution_by_sample.py   # about 8 minutes
```

`python run_all.py --part power` runs all but the last three and checks each report against the copy in this
repository. `python run_all.py --part power --full` adds the last three.
