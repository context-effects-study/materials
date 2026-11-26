# Demonstration data

These files hold simulated data in the exact formats of the data that the confirmatory study will collect.
`analysis/write_demo_data.py` writes them from the simulated data on which we ran the analysis
(`analysis/synth.py`, seed 20260613). They contain no real responses. We built known effects into them so
that the run can check that the analysis finds those effects, and these effects are not predictions.

| File | Format | Rows |
|---|---|---|
| `human_long_demo.csv` | the human data with one row per choice, `analysis/DATA_DICTIONARY.md` part A | 280,000 choices from 274,000 simulated participants |
| `model_log_demo.jsonl` | the model call log, part B (the fields that the analysis reads) | 38,340 calls in the neutral condition of the simulated model FAITHFUL |

`python analysis/analyze.py` analyzes these data, together with the other fourteen simulated models, which it
builds again in memory, and it must end with ALL CHECKS PASS. `python analysis/write_demo_data.py` writes
both files again, identical to these.
