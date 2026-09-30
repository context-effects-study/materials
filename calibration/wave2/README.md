# Calibration wave 2 (July 2, 2026)

Wave 2 re-tested the 17 pairs that were outside the target band after wave 1, at the adjusted values
(shared across each category's formats), with the corrected and clarified comprehension items and the
realism ratings of the three invented categories. The amendment that set this wave, written after the
wave-1 data and before this wave launched, is in `../CALIBRATION_DESIGN.md`. What the wave found and
decided is in `REPORT.md`.

## The study

| Field | Value |
|---|---|
| Platform | Prolific (recruitment and payment); Qualtrics (the survey) |
| Public study name | "Consumer choices (about 4 minutes)" |
| Survey | `survey/calibration_wave2.qsf`, exactly as fielded |
| Published | 13:39 UTC on July 2, 2026; all places filled in about 38 minutes |
| Places | 312 (sized to give about 101 kept respondents on each pair of the three categories with three pairs) |
| Pay | $1.00 for about 4 minutes (about $14 per hour) |
| Total cost | $416.04 including platform fees |
| Screening | As in wave 1, and every wave-1 participant excluded |
| Submissions | 326: 312 approved, 11 returned, 3 timed out |

## Files

| File | What it is |
|---|---|
| `survey/calibration_wave2.qsf` | The Qualtrics survey as fielded |
| `survey/calibration_wave2.pdf` | A printable view of the same survey: the flow, every block and every question (written by `../../surveys/print_survey.py`) |
| `survey/calibration_wave2_MAPPING.json` | The design key: the 17 pairs, the values each showed, the comprehension items with their answer keys, the realism items |
| `survey/wave2_pairs.json` | The adjusted values of this wave with the reasoning for each adjustment |
| `survey/images/` | The three pictures-format images this wave showed at adjusted values (SVG source and the PNG served) |
| `data/raw/calibration_wave2_export.csv` | The complete Qualtrics export (labels), 320 rows, de-identified. Read-only |
| `data/raw/calibration_wave2_export.json` | The same responses in Qualtrics' JSON format, de-identified the same way |
| `data/processed/calibration_wave2_participants.csv` | One row per export row: test row or not, kept or not, and the exclusion reasons |
| `data/processed/calibration_wave2_choices.csv` | One row per kept choice (3,090 rows) |
| `codebook_export.csv`, `codebook_participants.csv`, `codebook_choices.csv` | Data dictionaries |
| `results/calibration_report_wave2.md` | The report of record, written by `../calibration_analysis.py` from the original export on July 2, 2026 |
| `REPORT.md` | What the wave found and what was decided |

## Row reconciliation

320 export rows = 312 approved completes (every approved respondent present, no duplicates) + 8
engineering test rows (participant id beginning STRESS_W2_, removed before the analysis). The returned and
timed-out submissions left no row. The analysis kept 309 respondents (3,090 choices); 3 were excluded
(2 failed the attention check, 1 too fast).

## De-identification

As in wave 1: sequential participant ids (W2-0001 onward; the key is kept by the authors); the Prolific
study and submission ids, IP address, location and browser fields blank; test rows keep their labels. The optional
free-text comments on the realism pages were read in full before deposit; none identifies anyone.

## Reproduce this wave's numbers

From the repository root:

```
python calibration/wave2/reproduce.py
```

It runs `../calibration_analysis.py` with this wave's export and mapping, writes the report to
`reproduction/calibration_report_wave2.md`, and compares every table row with the report of record.

Output of record: Web Appendix F, Table WA-F4, the wave-2 column of Table WA-F7, and the wave-2 realism
scores.
