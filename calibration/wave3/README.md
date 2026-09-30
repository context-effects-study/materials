# Calibration wave 3, the final wave (July 2, 2026)

Wave 3 re-tested the 16 pairs still open after wave 2, at values adjusted pair by pair on enriched product
pages, with two comprehension-check items per respondent (about 130 answers per structure), the picture
comprehension item and the realism re-check. The final-wave decision rule was written into the design
document before this wave's data existed (`../CALIBRATION_DESIGN.md`). What the wave found and how every
pair ended is in `REPORT.md`; the final values are in `../FINAL_LOCK_LIST_2026-07-02.json`.

## The study

| Field | Value |
|---|---|
| Platform | Prolific (recruitment and payment); Qualtrics (the survey) |
| Public study name | "Consumer choices (about 5 minutes)" |
| Survey | `survey/calibration_wave3.qsf`, exactly as fielded |
| Published | 16:11 UTC on July 2, 2026 |
| Places | 462 (sized to give at least 150 kept respondents on each pair of the three categories with three pairs and about 130 per comprehension-check structure) |
| Pay | $1.13 for about 5 minutes ($12.70 to $14.10 per hour across the expected range of durations) |
| Total cost | $696.13 including platform fees |
| Screening | As in waves 1 and 2, and every participant of both earlier waves excluded |
| Submissions | 477: 462 approved, 7 returned, 8 timed out (returned places were filled again) |

Before publication one live run-through reached the completion page (nine choices, both comprehension
pages, the picture item and all three realism pages).

## Files

| File | What it is |
|---|---|
| `survey/calibration_wave3.qsf` | The Qualtrics survey as fielded |
| `survey/calibration_wave3.pdf` | A printable view of the same survey: the flow, every block and every question (written by `../../surveys/print_survey.py`) |
| `survey/calibration_wave3_MAPPING.json` | The design key: the 16 pairs and the values each showed, the 42 ordered pairs of comprehension structures, the answer keys, the picture item and the realism items |
| `survey/wave3_pairs.json` | The values of this wave pair by pair, the reasoning for each adjustment, and the enriched description content |
| `survey/images/` | The four pictures-format images of this wave (SVG source and the PNG served) |
| `data/raw/calibration_wave3_export.csv` | The complete Qualtrics export (labels), 478 rows, de-identified. Read-only |
| `data/raw/calibration_wave3_export.json` | The same responses in Qualtrics' JSON format, de-identified the same way |
| `data/processed/calibration_wave3_participants.csv` | One row per export row: test row or not, kept or not, and the exclusion reasons |
| `data/processed/calibration_wave3_choices.csv` | One row per kept choice (4,131 rows) |
| `codebook_export.csv`, `codebook_participants.csv`, `codebook_choices.csv` | Data dictionaries |
| `results/calibration_report_wave3.md` | The report of record, written by `../calibration_analysis.py` from the original export on July 2, 2026. Where it says values "lock at" a two-character label, the label is the working name of the final calibration lock |
| `REPORT.md` | What the wave found and how every pair ended |

## Row reconciliation

478 export rows = 462 approved completes (all present, no duplicates) + 5 respondents who completed after
the Prolific timer ran out (kept: payment status is not a registered exclusion) + 11 engineering test rows
(participant id beginning STRESS_W3_, removed before the analysis). The analysis kept 459 respondents
(4,131 choices); 8 were excluded (4 failed the attention check, 4 too fast).

## De-identification

As in wave 1: sequential participant ids (W3-0001 onward; the key is kept by the authors); the Prolific
study and submission ids, IP address, location and browser fields blank; test rows keep their labels. The optional
free-text comments were read in full before deposit; none identifies anyone.

## Reproduce this wave's numbers

From the repository root:

```
python calibration/wave3/reproduce.py
```

It runs `../calibration_analysis.py` with this wave's export and mapping, writes the report to
`reproduction/calibration_report_wave3.md`, and compares every table row with the report of record.

Output of record: Web Appendix F, Tables WA-F5 and WA-F6, the wave-3 column of Table WA-F7, and the
wave-3 realism scores.
