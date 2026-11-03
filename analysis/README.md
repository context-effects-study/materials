# analysis/

This folder holds the pre-registered analysis and everything that checks it: the table of every cutoff that the
analysis applies, the program that turns a Qualtrics export into the table that the analysis reads, a run of the
whole analysis on simulated data, and unit tests of each rule. Every script uses only the Python standard library.

| File | What it is |
|---|---|
| `DATA_DICTIONARY.md` | The three data formats: (A) the human data, with one row per choice; (B) the model call log, with one record per call; and (C) the results files that the analysis writes |
| `ingest.py` | Reads a Qualtrics export and writes the human data in format A. It applies the pre-registered exclusions, decodes each choice with the codebook of its structure, replaces each Prolific id with a one-way hash, and checks that the table is complete and consistent. `python analysis/ingest.py --selftest` must end with `INGEST PIPELINE GREEN` |
| `make_synthetic_export.py` | Writes the simulated Qualtrics export that the self-test of `ingest.py` reads |
| `analyze.py` | The pre-registered analysis. Step 0 applies the validity criteria; Step 1 estimates the human effects; Step 2 places each model effect on the fidelity map and in a fidelity class; Step 3 runs the pattern tests; and Step 4 asks whether each model matches people and, if it does not, which failures it shows. The program then writes every results file. Without arguments, it runs the analysis on simulated data. With `--human` and `--model`, it runs the same code on real data |
| `registered_constants.py` | Every numeric cutoff of the analysis, each with its meaning. `analyze.py` reads its cutoffs from this file and from nowhere else |
| `print_constants.py`, `REGISTERED_CONSTANTS.md` | `print_constants.py` prints Table WA-E1, every pre-registered cutoff, from `registered_constants.py`, so that the printed table and the values that the analysis applies are the same |
| `call_bootstrap.py` | Computes the interval that we report beside every model effect. It resamples calls within each prompt 2,000 times with a fixed seed, and the interval is descriptive |
| `synth.py` | Writes the simulated data, in which we built known answers: human effects of known size, and simulated models built to reach each of the seven scenarios and the three worked walk-throughs, with the pre-registered number of repeated calls |
| `statlib.py` | The statistical functions, written in plain Python |
| `REHEARSAL.md` | What the run on simulated data checks, and what it cannot show |
| `RESULTS_PACK_SELFTEST.md` | The table of checks from the last run on simulated data |
| `results_pack/` | The results files of the run on simulated data, exactly as `analyze.py` writes them. They are simulated, not results |
| `write_demo_data.py`, `demo_data/` | The simulated data of the run, written to files in the formats of the real data: a human table of 280,000 choices and a model call log, with a README |
| `test_analysis.py` | The unit tests of the analysis, one or more for each rule. Each test builds data in which one rule decides the outcome, and it checks that `analyze.py` applies that rule as pre-registered |
| `mutate_checks.py` | The mutation check. It breaks one rule at a time in a copy of the code and requires a unit test or the run on simulated data to fail |
| `build_analysis_explorer.py` | Writes `../analysis-explorer.html` from `results_pack/`: a page that follows each simulated model through the five steps of the analysis |

## Run

```
python analysis/analyze.py                  # the run on simulated data (about a minute and a half); ends "ALL CHECKS PASS"
python analysis/print_constants.py          # rewrites REGISTERED_CONSTANTS.md (Table WA-E1)
python analysis/test_analysis.py --no-write # every unit test (about half a minute); ends "OVERALL: ALL PASS"
python analysis/mutate_checks.py            # the mutation check (about 15 minutes); writes MUTATION_REPORT.md
python analysis/build_analysis_explorer.py  # rewrites ../analysis-explorer.html
python analysis/ingest.py --selftest        # reads a simulated export
python analysis/ingest.py --export <survey export.csv> --out human_long.csv
python analysis/analyze.py --human human_long.csv --model model_log.jsonl     # Stage 2
```

`python run_all.py --part analysis` runs the first three commands, the explorer and `write_demo_data.py`. It
checks four outputs against the copies in this repository: the files in `results_pack/`, the table of cutoffs, the
demonstration data and the explorer. Each must come out identical. Every
file in `results_pack/` comes from simulated data. At Stage 2, the same command on the real human exports and the
real model call log will write the results files of the study.
