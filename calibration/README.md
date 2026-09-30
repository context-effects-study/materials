# The stimulus calibration pre-test

Before any confirmatory choice is collected, every two-option pair on which a context effect is measured
had to sit in a target band: the compromise target chosen by 40 to 45 percent, its rival by 55 to 60
percent, and never outside 25 to 75 percent. Otherwise an effect would be tested against a ceiling. Three
calibration waves and one realism comparison study ran on Prolific on July 2, 2026 (400, 312, 462 and 112
approved participants; 1,286 in all; $1,571.93 including platform fees). Each wave measured the open pairs,
adjusted those outside the band, and re-tested them. Web Appendix F of
the manuscript reports the pre-test in full; every number there comes from the files in this folder.

The calibration data set stimulus values only. They never enter a confirmatory analysis, and calibration
participants are excluded from the confirmatory samples.

## One folder per study

| Folder | Study | Approved | Kept for analysis | Output of record |
|---|---|---|---|---|
| `wave1/` | Wave 1: all 25 pairs at their starting values | 400 | 392 respondents, 3,920 choices | Tables WA-F2, WA-F3, WA-F7 |
| `wave2/` | Wave 2: the 17 pairs still open, realism ratings added | 312 | 309 respondents, 3,090 choices | Tables WA-F4, WA-F7 |
| `wave3/` | Wave 3, the final wave: the 16 pairs still open | 462 | 459 respondents, 4,131 choices | Tables WA-F5, WA-F6, WA-F7 |
| `realism_study/` | Published pages rated on the realism question | 112 | 111 respondents, 444 ratings | Realism comparison, Table WA-F1 |

Each study folder holds the same things: `README.md` (the study's record: platform, dates, pay, cost,
screening, row reconciliation, de-identification), `survey/` (the Qualtrics file exactly as fielded, a
printable PDF view of it, its design key and, where the wave changed values, the value file and images),
`data/raw/` (the de-identified export, every row kept, test rows labelled; read-only), `data/processed/`
(the analysis-ready files, with every row's exclusion flag and reason), a codebook for every data file,
`reproduce.py` (rebuilds the study's reported numbers from its export and checks them against the output of
record), `results/` (the output of record) and `REPORT.md` (what the study found and what was decided). The
exclusions are applied in code, by the analysis of record, never by removing rows from the data.

## Shared files

| File | What it is |
|---|---|
| `CALIBRATION_DESIGN.md` | The design of the pre-test and every change between waves, in the order they were made |
| `calibration_analysis.py` | The analysis of each wave (shares, intervals, band verdicts, adjustment suggestions, comprehension checks, realism scores, the final-wave decision rule, the report) |
| `anchor_analysis.py` | The analysis of the realism comparison study |
| `make_choice_files.py` | Writes the processed files of every study from the raw exports |
| `study_check.py` | The comparison each study's `reproduce.py` runs (a rebuilt report against the report of record) |
| `FINAL_LOCK_LIST_2026-07-02.json` | Every pair's final values, measured share, interval, verdict and routing; `stimuli/build_stimuli.py` checks the stimulus file against it |
| `RNG_KEY_CORRECTION_2026-07-02.md` | The corrected answer key of the wave-1 range question, with both scorings |

## Reproduce

`python run_all.py --part calibration` from the repository root reruns all four analyses from the deposited
exports, compares every table row with the reports of record, rebuilds the processed files and the survey
views, and checks the calibration surveys' design. One study alone: `python calibration/wave1/reproduce.py`
(and likewise `wave2`, `wave3`, `realism_study`).
