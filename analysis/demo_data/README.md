# Demonstration data

Synthetic data in the exact formats the confirmatory study will produce, written by
`analysis/write_demo_data.py` from the dress rehearsal's own synthetic data (`analysis/synth.py`, seed
20260613). They contain no real responses. The effects planted in them are the rehearsal's answer key, not
predictions.

| File | Format | Rows |
|---|---|---|
| `human_long_demo.csv` | the human long table, `analysis/DATA_DICTIONARY.md` part A | 280,000 choices from 274,000 synthetic participants |
| `model_log_demo.jsonl` | the model call log, part B (the fields the analysis reads) | 38,340 neutral-condition calls of the planted profile FAITHFUL |

`python analysis/analyze.py` analyzes these data (with the other fourteen planted profiles, which it
regenerates in memory) and must end with ALL CHECKS PASS. `python analysis/write_demo_data.py` rewrites
both files identically.
