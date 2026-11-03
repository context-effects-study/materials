# Calibration wave 2 (July 2, 2026)

Wave 2 tested again the 17 pairs that were outside the target band after wave 1, at adjusted values that each
category's formats shared. It also asked the corrected and the reworded comprehension questions, and it asked
respondents to rate the realism of the three invented categories. We wrote the changes that set this wave after
the wave-1 data and before this wave launched, and `../CALIBRATION_DESIGN.md` records them. `REPORT.md` gives what
the wave found and what we decided.

## The study

| Field | Value |
|---|---|
| Platform | Prolific (recruitment and payment); Qualtrics (the survey) |
| Public study name | "Consumer choices (about 4 minutes)" |
| Survey | `survey/calibration_wave2.qsf`, exactly as fielded |
| Published | 13:39 UTC on July 2, 2026; all places filled in about 38 minutes |
| Places | 312 (set so that about 101 respondents would be kept for each pair of the three categories with three pairs) |
| Pay | $1.00 for about 4 minutes (about $14 an hour) |
| Total cost | $416.04 including the platform's fees |
| Screening | As in wave 1, with every participant of wave 1 excluded |
| Submissions | 326: 312 approved, 11 returned and 3 timed out |

## Files

| File | What it is |
|---|---|
| `survey/calibration_wave2.qsf` | The Qualtrics survey as fielded |
| `survey/calibration_wave2.pdf` | A printable view of the same survey: the flow, every block and every question (written by `../../surveys/print_survey.py`) |
| `survey/calibration_wave2_MAPPING.json` | The design key: the 17 pairs and the values that each showed, the comprehension questions with their answer keys, and the realism questions |
| `survey/wave2_pairs.json` | The adjusted values of this wave, with the reason for each adjustment |
| `survey/images/` | The three pictures that this wave showed at adjusted values (the SVG source and the PNG file that the survey showed) |
| `data/raw/calibration_wave2_export.csv` | The complete Qualtrics export with labels, 320 rows, de-identified. Nothing in this repository writes to it |
| `data/raw/calibration_wave2_export.json` | The same responses in Qualtrics' JSON format, de-identified in the same way |
| `data/processed/calibration_wave2_participants.csv` | One row for each row of the export: whether it is a test row, whether it was kept, and the reasons for any exclusion |
| `data/processed/calibration_wave2_choices.csv` | One row for each kept choice (3,090 rows) |
| `codebook_export.csv`, `codebook_participants.csv`, `codebook_choices.csv` | The data dictionaries |
| `results/calibration_report_wave2.md` | The original report, which `../calibration_analysis.py` wrote from the original export on July 2, 2026 |
| `REPORT.md` | What the wave found and what we decided |

## Every row of the export

The 320 rows of the export are 312 approved completions (every approved respondent is present, with no
duplicates) and 8 test rows that we wrote before launch (participant ids beginning STRESS_W2_, removed before the
analysis). The returned and timed-out submissions left no row. The analysis kept 309 respondents (3,090 choices)
and excluded 3: 2 failed the attention check, and 1 answered too fast.

## De-identification

We de-identified the data as in wave 1. Participant ids are sequential (W2-0001 onward), and the authors keep the
key. The Prolific study id and submission id, the IP address, the location and the browser fields are blank. The
test rows keep their labels. We read every optional comment on the realism pages before deposit, and none
identifies anyone.

## Reproduce the numbers of this wave

From the root of the repository:

```
python calibration/wave2/reproduce.py
```

The script runs `../calibration_analysis.py` with this wave's export and design key, writes the report to
`reproduction/calibration_report_wave2.md`, and compares every row of every table with the original report.

Web Appendix F reports the results in Table WA-F4, in the wave-2 column of Table WA-F7 and in the realism ratings of
wave 2.
