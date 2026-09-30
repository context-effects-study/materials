# Power

The power of the human study's registered tests, computed by formula and by simulation, with the numbers
the Method and Web Appendix E cite, and a check of how reliably the decision tree routes the planted model
profiles once the model answers carry sampling noise.

| File | What it is |
|---|---|
| `power_sim.py`, `RESULTS.md` | Power per category (about 700 choices per condition), pooled over ten categories (about 7,000) and for the pooled first-choice subsample (about 1,000), by the normal approximation and by 50,000 simulated draws (seed 11); the multiple-testing correction at its most conservative (alpha divided by seven) |
| `clustered_power.py`, `CLUSTERED_POWER.md` | Whether the correlation among one participant's seven choices reduces the power of the pooled tests (participant random intercepts at several intra-class correlations; cluster-robust against naive tests; seed 7; needs numpy) |
| `power_added_cells.py`, `POWER_ADDED_CELLS.md` | Power for the cells added to the numeric survey: both similarity clone placements, the price-free test and the extremity control |
| `power_format_interaction.py`, `POWER_FORMAT_INTERACTION.md` | Power of the four format-by-effect interaction tests at the planned sizes, with the numbers comparison at the numeric survey's actual cell sizes (Table WA-E3; seed 20260929) |
| `power_compromise_pooled.py`, `POWER_COMPROMISE_POOLED.md` | Power of the pooled compromise test after the descriptive compromise cells leave it, and of the other five non-similarity effects, at the registered Holm family of six (seed 20260929) |
| `first_trial_rule_sim.py`, `FIRST_TRIAL_RULE_SIM.md` | The false-alarm rate and power of the registered first-choice check at the planned cell sizes (Table WA-E2; seed 20260929) |
| `model_noise_stability.py`, `MODEL_NOISE_STABILITY.md`, `model_noise_stability_runs.csv` | How often each planted model profile routes to its intended scenario, to not resolved, or to a wrong scenario, when every model call is a random draw at the planted share (the full analysis, 20 seeds per condition) |
| `resolution_statement.py`, `RESOLUTION_STATEMENT.md`, `resolution_statement_runs.csv`, `resolution_statement_summary.json` | The pattern-test counterpart of power: the smallest true difference each pattern test (T1 to T5) and each class boundary resolves in 80 percent of runs at the planned sizes and the registered model plan (Table WA-E4; the full analysis, 20 seeds) |
| `pattern_test_resolution.json` | A recorded input, not recomputed here: the pattern-test rows of Table WA-E4 (T1, T3, T4, T5) for the registered design, from a simulation of the design run before registration (20 runs per value on the grid 0.2 to 2, the registered test functions and router). The file says how it was made; `resolution_statement.py` reads it |
| `faithful_resolution_by_sample.py`, `FAITHFUL_RESOLUTION_BY_SAMPLE.md` | How large a sample the planted faithful profile needs before it routes to its intended scenario at the registered 95 percent level (human sizes 1 to 8 times the plan, with and without draw noise) |

## What the numbers mean

1. **The pooled tests are the confirmatory level.** Across ten categories (about 7,000 choices per
   condition), power is effectively 1.00 for effects as small as 4 percentage points, and at least 0.98
   under the most conservative correction (alpha divided by all seven effect families).
2. **Per-category results are reported but not confirmatory.** One category (700 per condition) detects an
   8-point effect with power 0.85 at alpha .05 but only 0.63 under the conservative correction, so the
   protocol registers the pooled tests as confirmatory and reports the variation across categories as a
   described moderator.
3. **The first-choice check has adequate power at the pooled level.** The one-choice-per-person subsample
   (about 1,000 per condition pooled) detects an 8-point effect with power 0.95 (0.82 under the
   conservative correction). `FIRST_TRIAL_RULE_SIM.md` gives the registered check's false-alarm rate and
   power directly.
4. **The format interaction and the pooled compromise test** are reported at their actual planned sizes in
   `POWER_FORMAT_INTERACTION.md` and `POWER_COMPROMISE_POOLED.md`.
5. **The pattern tests have no power in the usual sense**, because a model effect carries no test. Their
   counterpart is the smallest true difference each reading resolves in 80 percent of runs
   (`RESOLUTION_STATEMENT.md`, Table WA-E4), and `FAITHFUL_RESOLUTION_BY_SAMPLE.md` shows what sample would let
   the faithful profile be resolved.

Holm's correction within families, which the analysis uses, can only improve on the floors in points 1 to 3.

## Run

```
python power/power_sim.py                  # about 20 seconds
python power/clustered_power.py            # about 2.5 minutes
python power/power_added_cells.py
python power/power_format_interaction.py
python power/power_compromise_pooled.py
python power/first_trial_rule_sim.py       # about 30 seconds
python power/model_noise_stability.py      # about 17 minutes
python power/resolution_statement.py       # about 40 minutes
python power/faithful_resolution_by_sample.py   # about 8 minutes
```

`python run_all.py --part power` runs all but the last three and checks each report against the deposited
copy; `python run_all.py --part power --full` adds the last three.
