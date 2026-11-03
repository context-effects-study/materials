# Calibration wave 3, the final wave (July 2, 2026)

Wave 3 tested again the 16 pairs that were still open after wave 2. It showed values adjusted pair by pair, on
fuller product pages. Each respondent answered two comprehension questions (about 130 answers for each structure),
the comprehension question about the pictures, and the realism questions again. We wrote the decision rule of the
final wave into the design document before this wave's data existed (`../CALIBRATION_DESIGN.md`). `REPORT.md`
gives what the wave found and how every pair ended, and `../FINAL_LOCK_LIST_2026-07-02.json` gives the final
values.

## The study

| Field | Value |
|---|---|
| Platform | Prolific (recruitment and payment); Qualtrics (the survey) |
| Public study name | "Consumer choices (about 5 minutes)" |
| Survey | `survey/calibration_wave3.qsf`, exactly as fielded |
| Published | 16:11 UTC on July 2, 2026 |
| Places | 462 (set so that at least 150 respondents would be kept for each pair of the three categories with three pairs, and about 130 for each structure of the comprehension questions) |
| Pay | $1.13 for about 5 minutes ($12.70 to $14.10 an hour across the expected range of durations) |
| Total cost | $696.13 including the platform's fees |
| Screening | As in waves 1 and 2, with every participant of both earlier waves excluded |
| Submissions | 477: 462 approved, 7 returned and 8 timed out (Prolific filled the returned places again) |

Before publication, we completed one live run of the survey, from the first page to the completion page: nine
choices, both comprehension pages, the question about the pictures and all three realism pages.

## Files

| File | What it is |
|---|---|
| `survey/calibration_wave3.qsf` | The Qualtrics survey as fielded |
| `survey/calibration_wave3.pdf` | A printable view of the same survey: the flow, every block and every question (written by `../../surveys/print_survey.py`) |
| `survey/calibration_wave3_MAPPING.json` | The design key: the 16 pairs and the values that each showed, the 42 ordered pairs of comprehension structures, the answer keys, the question about the pictures and the realism questions |
| `survey/wave3_pairs.json` | The values of this wave, pair by pair, with the reason for each adjustment and the text of the fuller descriptions |
| `survey/images/` | The four pictures of this wave (the SVG source and the PNG file that the survey showed) |
| `data/raw/calibration_wave3_export.csv` | The complete Qualtrics export with labels, 478 rows, de-identified. Nothing in this repository writes to it |
| `data/raw/calibration_wave3_export.json` | The same responses in Qualtrics' JSON format, de-identified in the same way |
| `data/processed/calibration_wave3_participants.csv` | One row for each row of the export: whether it is a test row, whether it was kept, and the reasons for any exclusion |
| `data/processed/calibration_wave3_choices.csv` | One row for each kept choice (4,131 rows) |
| `codebook_export.csv`, `codebook_participants.csv`, `codebook_choices.csv` | The data dictionaries |
| `results/calibration_report_wave3.md` | The original report, which `../calibration_analysis.py` wrote from the original export on July 2, 2026. Where it says that values "lock at" a label of two characters, the label is the working name of the final calibration values |
| `REPORT.md` | What the wave found and how every pair ended |

## Every row of the export

The 478 rows of the export are 462 approved completions (all present, with no duplicates), 5 respondents who
completed after the Prolific timer ran out (kept, because payment status is not one of the pre-registered exclusion
rules), and 11 test rows that we wrote before launch (participant ids beginning STRESS_W3_, removed before the
analysis). The analysis kept 459 respondents (4,131 choices) and excluded 8: 4 failed the attention check, and 4
answered too fast.

## De-identification

We de-identified the data as in wave 1. Participant ids are sequential (W3-0001 onward), and the authors keep the
key. The Prolific study id and submission id, the IP address, the location and the browser fields are blank. The
test rows keep their labels. We read every optional comment before deposit, and none identifies anyone.

## Reproduce the numbers of this wave

From the root of the repository:

```
python calibration/wave3/reproduce.py
```

The script runs `../calibration_analysis.py` with this wave's export and design key, writes the report to
`reproduction/calibration_report_wave3.md`, and compares every row of every table with the original report.

Web Appendix F reports the results in Tables WA-F5 and WA-F6, in the wave-3 column of Table WA-F7 and in the realism
ratings of wave 3.
