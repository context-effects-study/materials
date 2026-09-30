# analysis/

The registered analysis, the table of every cutoff it applies, the reader that turns a Qualtrics export into
the analysis table, the synthetic dress rehearsal that runs the whole analysis before any confirmatory data
exist, and the tests that check each rule. Standard-library Python.

| File | What it is |
|---|---|
| `DATA_DICTIONARY.md` | The three data formats: A, the human long table (one row per choice); B, the model call log (one record per call); C, the results pack the analysis writes |
| `ingest.py` | Qualtrics export in, human long table out: the registered exclusions, the per-structure codebook, one-way hashed participant ids, and the table's invariants. `python analysis/ingest.py --selftest` must end `INGEST PIPELINE GREEN` |
| `make_synthetic_export.py` | The synthetic Qualtrics export the ingest self-test reads |
| `analyze.py` | The registered analysis: Step 0 validity criteria, Step 1 human benchmarks, Step 2 fidelity map and classes, Step 3 pattern tests, the precedence rule, the decision tree and the complete results pack. Without arguments it runs the dress rehearsal; with `--human` and `--model` it runs the same code on real data |
| `registered_constants.py` | Every numeric cutoff the analysis uses, each with its meaning; analyze.py reads its cutoffs from here and nowhere else |
| `print_constants.py`, `REGISTERED_CONSTANTS.md` | Prints Table WA-E1 (every registered cutoff) from `registered_constants.py`, so the printed table and the applied values cannot differ |
| `call_bootstrap.py` | The bootstrap interval over calls reported beside every model effect (calls resampled within each prompt; 2,000 resamples, fixed seed; descriptive) |
| `synth.py` | The synthetic data with planted truths: human effects, model profiles for every named scenario and the two walk-throughs, and the registered repeated draws |
| `statlib.py` | The statistics, in plain Python |
| `REHEARSAL.md` | What the dress rehearsal shows and its limits |
| `RESULTS_PACK_SELFTEST.md` | The rehearsal's table of checks, written by the last run |
| `results_pack/` | The rehearsal's results pack, exactly as `analyze.py` writes it (synthetic data, not results) |
| `write_demo_data.py`, `demo_data/` | The demonstration data: the rehearsal's own synthetic data written to files in the registered formats (a human long table of 280,000 choices and a model call log), with a README |
| `test_analysis.py` | Tests of the analysis, one per rule: each builds data in which one rule decides the outcome and checks that analyze.py applies it as registered |
| `mutate_checks.py` | The mutation check: breaks one rule at a time in a scratch copy of the code and requires a test or the rehearsal to fail |

## Run

```
python analysis/analyze.py                  # the dress rehearsal (under a minute); ends "ALL CHECKS PASS"
python analysis/print_constants.py          # rewrites REGISTERED_CONSTANTS.md (Table WA-E1)
python analysis/test_analysis.py --no-write # every test (about half a minute); ends "OVERALL: ALL PASS"
python analysis/mutate_checks.py            # the mutation check (about 15 minutes); writes MUTATION_REPORT.md
python analysis/ingest.py --selftest        # the export reader on a synthetic export
python analysis/ingest.py --export <survey export.csv> --out human_long.csv
python analysis/analyze.py --human human_long.csv --model model_log.jsonl     # Stage 2
```

`python run_all.py --part analysis` runs the first three and checks the rehearsal's results pack and the
cutoff table against the deposited copies. Everything in `results_pack/` comes from synthetic data. At
Stage 2 the same command on the real human exports and the real model log writes the results pack of record.
