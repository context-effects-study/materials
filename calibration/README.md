# The stimulus calibration pre-test

Each context effect is measured against a set of two options. If nearly everyone already chooses one of the two
options, an added option has no room to raise that option's share. Before collecting any confirmatory choice,
we therefore aimed to place each two-option pair in a target band: the compromise target chosen by 40 to 45
percent of participants, and its rival by 55 to 60 percent, and no share outside 25 to 75 percent. Of the 25
pairs, we could adjust 18. We measured the seven pairs with published values but never changed them, so that
they stay as printed. Three
calibration waves and one realism comparison study ran on Prolific on July 2, 2026, with 400, 312, 462 and 112
approved participants (1,286 in all, at a cost of $1,571.93 including the platform's fees). In each wave, we
measured the pairs that were still open, adjusted the pairs outside the band, and tested them again in the next
wave. Web Appendix F of the manuscript reports the pre-test in full, and every number there comes from the files
in this folder.

We used the calibration data only to set the stimulus values. They never enter a confirmatory analysis, and no
participant of the pre-test can take part in a confirmatory survey.

## One folder for each study

| Folder | Study | Approved | Kept for analysis | Tables of the web appendix |
|---|---|---|---|---|
| `wave1/` | Wave 1: all 25 pairs at their starting values | 400 | 392 participants, 3,920 choices | Tables WA-F2, WA-F3 and WA-F7 |
| `wave2/` | Wave 2: the 17 pairs still open, with realism ratings added | 312 | 309 participants, 3,090 choices | Tables WA-F4 and WA-F7 |
| `wave3/` | Wave 3, the final wave: the 16 pairs still open | 462 | 459 participants, 4,131 choices | Tables WA-F5, WA-F6 and WA-F7 |
| `realism_study/` | Raters judged the pages of the published categories on the realism question | 112 | 111 participants, 444 ratings | Table WA-F1 and the realism comparison |

Each study folder holds the same kinds of file:

- `README.md`, the record of the study: platform, dates, pay, cost, screening, an account of every row of the
  export, and how we de-identified the data;
- `survey/`, the Qualtrics file exactly as fielded, a printable PDF view of it, its design key, and, for the
  waves that changed values, the file of values and the images;
- `data/raw/`, the de-identified export, with every row kept and the test rows labeled (nothing in this
  repository writes to it);
- `data/processed/`, the files ready for analysis, with an exclusion flag and a reason on every row;
- a codebook for every data file;
- `reproduce.py`, which rebuilds the numbers of the study from its export and compares them with the original
  report;
- `results/`, the original report, which the analysis code wrote on July 2, 2026;
- `REPORT.md`, a short account of what the study found and what we decided.

The analysis code applies the exclusions. We never removed a row from the data.

## Files shared by the studies

| File | What it is |
|---|---|
| `CALIBRATION_DESIGN.md` | The design of the pre-test and every change between waves, in the order in which we made them |
| `calibration_analysis.py` | The analysis of each wave: shares, intervals, the result for each pair against the band, the suggested adjustments, the comprehension checks, the realism ratings, the decision rule of the final wave, and the report |
| `anchor_analysis.py` | The analysis of the realism comparison study |
| `make_choice_files.py` | Writes the processed files of every study from the raw exports |
| `study_check.py` | The comparison that the `reproduce.py` script of each study runs: a rebuilt report against the original report |
| `FINAL_LOCK_LIST_2026-07-02.json` | The final values of every pair, with its measured share, its interval, its result and what we did with it. `stimuli/build_stimuli.py` checks the stimulus file against this list |
| `RNG_KEY_CORRECTION_2026-07-02.md` | The corrected answer key of the wave-1 comprehension question about the range decoy, with the scores under both keys |

## Reproduce

From the root of the repository, `python run_all.py --part calibration` reruns all four analyses from the
deposited exports and compares every row of every table with the original reports. It also rebuilds the
processed files and the printable views of the surveys, and it checks the design of the calibration surveys.
To reproduce one study alone, run `python calibration/wave1/reproduce.py` (and likewise for `wave2`, `wave3`
and `realism_study`).
