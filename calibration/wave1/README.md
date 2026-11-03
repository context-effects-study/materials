# Calibration wave 1 (July 2, 2026)

Wave 1 measured all 25 two-option pairs of the calibration at their starting values. Each respondent made ten
choices between two options, one in each product category that has a pair, and then answered one comprehension
question about one structure. `../CALIBRATION_DESIGN.md` gives the design, including the change that set the form
and the size of this wave. `REPORT.md` gives what the wave found and what we decided.

## The study

| Field | Value |
|---|---|
| Platform | Prolific (recruitment and payment); Qualtrics (the survey) |
| Public study name | "Consumer choices (about 3 minutes)" |
| Survey | `survey/calibration_wave1.qsf`, exactly as fielded |
| Published | 11:27 UTC on July 2, 2026; all places filled in about 29 minutes |
| Places | 400 |
| Pay | $0.75 for about 3 minutes (median duration 192 seconds, about $13.43 an hour) |
| Total cost | $400.03 including the platform's fees |
| Screening | Lives in the US or the UK, fluent in English, an approval rate of 95 to 100 percent, 10 to 100,000 earlier approved submissions, desktop computers only, one submission per person |
| Submissions | 408: 400 approved, 6 returned and 2 timed out |

We read every value above from the Prolific and Qualtrics records after the study closed. Before publication, we
ran one live preview from start to finish. Its row is in the export, and the rule for previews excludes it.

## Files

| File | What it is |
|---|---|
| `survey/calibration_wave1.qsf` | The Qualtrics survey as fielded (import it into Qualtrics to see every page) |
| `survey/calibration_wave1.pdf` | A printable view of the same survey: the flow, every block and every question (written by `../../surveys/print_survey.py`) |
| `survey/calibration_wave1_MAPPING.json` | The design key of the survey as fielded: the pairs, the assignment of pairs to choices, and the comprehension questions with their answer keys |
| `survey/calibration_wave1_MAPPING_rng_corrected.json` | The same key with only the answer key of the range question corrected (see `../RNG_KEY_CORRECTION_2026-07-02.md`). The original report of this wave is scored with this file |
| `data/raw/calibration_wave1_export.csv` | The complete Qualtrics export with labels, 409 rows, de-identified (see below). Nothing in this repository writes to it |
| `data/raw/calibration_wave1_export.json` | The same responses in Qualtrics' JSON format with numeric codes, de-identified in the same way |
| `data/processed/calibration_wave1_participants.csv` | One row for each row of the export: whether it is a test row, whether it was kept, and the reasons for any exclusion |
| `data/processed/calibration_wave1_choices.csv` | One row for each kept choice (3,920 rows): the pair, the group, the category, the tier, the format, the order of the options, the option chosen, and whether it was the target |
| `codebook_export.csv` | The data dictionary of the export: every column of the CSV file with its key in the JSON file, its type, the values observed, its units and its meaning |
| `codebook_participants.csv`, `codebook_choices.csv` | The data dictionaries of the two processed files |
| `results/calibration_report_wave1.md` | The original report, which `../calibration_analysis.py` wrote from the original export on July 2, 2026 |
| `REPORT.md` | What the wave found and what we decided |

## Every row of the export

The 409 rows of the export are:

- 400 approved completions (every approved respondent is present);
- 1 respondent who completed after the Prolific timer ran out (kept, because payment status is not one of the
  pre-registered exclusion rules);
- 7 test rows that we wrote before launch (participant ids beginning STRESS_, removed before the analysis);
- 1 preview row (removed by the rule for previews).

The 6 returned submissions and the 1 remaining timed-out submission left no row.

Of the 402 rows that the exclusion rules read, the analysis kept 392 respondents (3,920 choices) and excluded 10: 6
answered too fast, 2 failed the attention check, 1 did both, and 1 was the preview.

## De-identification

This copy differs from the export that Qualtrics produced in these fields only. We replaced the Prolific
participant id with a sequential id (W1-0001, W1-0002 and so on, in order of first appearance), and the authors keep
the key. The Prolific study id and submission id, the IP address, the location and the four browser fields are
blank. The test rows keep their STRESS_ and PREVIEW_ labels. Wave 1 asked no free-text question. It asked for age
and gender, and both are included.

## Reproduce the numbers of this wave

From the root of the repository:

```
python calibration/wave1/reproduce.py
```

`reproduce.py` runs the original analysis (`../calibration_analysis.py`, which applies the exclusion rules to the
export above) with this wave's export and design key. It writes the report to
`reproduction/calibration_report_wave1.md` and compares every row of every table with the original report. It
prints the number of identical rows and exits with an error if any row differs. `python run_all.py --part
calibration` runs it together with the other three studies. Web Appendix F reports the results in Tables WA-F2
and WA-F3 and in the wave-1 column of Table WA-F7.
