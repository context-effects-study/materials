# Calibration wave 1 (July 2, 2026)

Wave 1 measured all 25 two-option calibration pairs at their starting values. Each respondent made ten
binary choices, one in each product category that carries a pair, then answered one structure
comprehension-check item. The design document, including the amendment that set this wave's form and
size, is `../CALIBRATION_DESIGN.md`. What the wave found and decided is in `REPORT.md`.

## The study

| Field | Value |
|---|---|
| Platform | Prolific (recruitment and payment); Qualtrics (the survey) |
| Public study name | "Consumer choices (about 3 minutes)" |
| Survey | `survey/calibration_wave1.qsf`, exactly as fielded |
| Published | 11:27 UTC on July 2, 2026; all places filled in about 29 minutes |
| Places | 400 |
| Pay | $0.75 for about 3 minutes (median duration 192 seconds, about $13.43 per hour) |
| Total cost | $400.03 including platform fees |
| Screening | Resident in the US or UK, fluent in English, 95 to 100 percent approval rate, 10 to 100,000 prior approvals, desktop only, one submission per person |
| Submissions | 408: 400 approved, 6 returned, 2 timed out |

Every value above was read back from the Prolific and Qualtrics records after the study closed. Before
publication one live preview ran end to end; its row is in the export and is excluded by the preview rule.

## Files

| File | What it is |
|---|---|
| `survey/calibration_wave1.qsf` | The Qualtrics survey as fielded (import it into Qualtrics to see every page) |
| `survey/calibration_wave1.pdf` | A printable view of the same survey: the flow, every block and every question (written by `../../surveys/print_survey.py`) |
| `survey/calibration_wave1_MAPPING.json` | The design key of the survey as fielded: the pairs, the deal of pairs to choice slots, the comprehension items and their answer keys |
| `survey/calibration_wave1_MAPPING_rng_corrected.json` | The same key with only the range-question answer key corrected (see `../RNG_KEY_CORRECTION_2026-07-02.md`); the wave's report of record is scored with this file |
| `data/raw/calibration_wave1_export.csv` | The complete Qualtrics export (labels), 409 rows, de-identified (below). Read-only: nothing in this repository writes to it |
| `data/raw/calibration_wave1_export.json` | The same responses in Qualtrics' JSON export format (numeric codes), de-identified the same way |
| `data/processed/calibration_wave1_participants.csv` | One row per export row: test row or not, kept or not, and the exclusion reasons |
| `data/processed/calibration_wave1_choices.csv` | One row per kept choice (3,920 rows): pair, block, category, tier, format, option order, decoded choice and whether the target was chosen |
| `codebook_export.csv` | Data dictionary of the export: every column of the CSV with its key in the JSON file, type, observed values, units and meaning |
| `codebook_participants.csv`, `codebook_choices.csv` | Data dictionaries of the two processed files |
| `results/calibration_report_wave1.md` | The report of record, written by `../calibration_analysis.py` from the original export on July 2, 2026 |
| `REPORT.md` | What the wave found and what was decided |

## Row reconciliation

409 export rows = 400 approved completes (every approved respondent present) + 1 respondent who completed
after the Prolific timer ran out (kept: payment status is not a registered exclusion) + 7 engineering test
rows written before launch (participant id beginning STRESS_, removed before the analysis) + 1 preview row
(removed by the preview rule). The 6 returned and 1 remaining timed-out submissions left no row.

402 rows entered the registered exclusion rules: 392 respondents were kept (3,920 choices) and 10 were
excluded (6 too fast, 2 failed the attention check, 1 both, 1 preview).

## De-identification

Compared with the export Qualtrics produced, this copy differs only in these fields: the Prolific
participant id is replaced by a sequential id (W1-0001, W1-0002, and so on, in order of first
appearance; the key is kept by the authors), the Prolific study and submission ids, the IP address, the location and
the four browser fields are blank. Test rows keep their STRESS_ and PREVIEW_ labels. Wave 1 asked no
free-text question. Age and gender were asked and are included.

## Reproduce this wave's numbers

From the repository root:

```
python calibration/wave1/reproduce.py
```

`reproduce.py` runs the analysis of record (`../calibration_analysis.py`, which applies the registered
exclusions to the export above) with this wave's export and mapping, writes the report to
`reproduction/calibration_report_wave1.md`, and compares every table row with the report of record; it prints
the number of identical rows and exits with an error on any difference. `python run_all.py --part calibration`
runs it with the other three studies. Output of record: Web Appendix F, Tables WA-F2 and WA-F3 and the wave-1
column of Table WA-F7.
