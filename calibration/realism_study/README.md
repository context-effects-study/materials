# The realism comparison study (July 2, 2026)

The invented categories missed the realism threshold (a mean of 5.0 on the 7-point question "does this read
like a real product page?") in waves 2 and 3. No published category's page had been rated on that
question, so this study asked 112 new raters, none of whom took part in any calibration wave, to rate the
seven published categories' pages, rendered exactly as wave 3 rendered the invented ones. It was added
after the wave-3 data, as a change to how the realism results are read; it changed no stimulus and no
value. What it found is in `REPORT.md`.

## The study

| Field | Value |
|---|---|
| Platform | Prolific (recruitment and payment); Qualtrics (the survey) |
| Public study name | "Rate a few product pages (about 2 minutes)" |
| Survey | `survey/realism_study.qsf`, exactly as fielded: consent, attention check, four of the seven published categories' pages dealt evenly, each with the same 7-point question wave 3 used, an optional comment, and demographic questions |
| Published | 18:07 UTC on July 2, 2026; all places filled in about 17 minutes |
| Places | 112 (64 ratings per category by design) |
| Pay | $0.40 for about 2 minutes |
| Total cost | $59.73 including platform fees |
| Screening | As in the calibration waves, and every participant of all three waves excluded |

## Files

| File | What it is |
|---|---|
| `survey/realism_study.qsf`, `survey/realism_study_MAPPING.json` | The Qualtrics survey as fielded and its design key |
| `survey/realism_study.pdf` | A printable view of the same survey: the flow, every block and every question (written by `../../surveys/print_survey.py`) |
| `data/raw/realism_export.csv` | The complete Qualtrics export (labels), 117 rows, de-identified. Read-only |
| `data/raw/realism_export.json` | The same responses in Qualtrics' JSON format, de-identified the same way |
| `data/processed/realism_ratings.csv` | One row per rating (respondent, category, rating, page time, kept or not) |
| `codebook_export.csv`, `codebook_ratings.csv` | Data dictionaries |
| `results/realism_results.json` | The analysis output of `../anchor_analysis.py`: per-category and pooled means with 95 percent intervals, the share rating 5 or higher, and the published-minus-invented differences (Welch). Keys: `anchor_rows`, `anchor_kept`, `anchor_excluded` (this study), `published_per_category`, `published_pooled_respmean` (the mean of each rater's mean), `wave3_rows`, `wave3_kept`, `invented_per_category`, `invented_pooled_respmean` (wave 3, recomputed from the wave-3 export), `parity_welch_pooled`, `published_pooled_minus_invented_category` |
| `REPORT.md` | What the study found |

## Row reconciliation

117 export rows = 112 approved completes + 1 respondent who completed after the Prolific timer ran out
(kept) + 4 engineering test rows (participant id beginning STRESS_ANCHOR_, removed before the analysis).
The analysis kept 111 respondents (444 ratings, 63 or 64 per category); 2 were excluded (1 failed the
attention check, 1 too fast).

## De-identification

As in the calibration waves: sequential participant ids (RS-0001 onward; the key is kept by the authors);
the Prolific study and submission ids, IP address, location and browser fields blank; test rows keep their
labels. The optional comments were read in full before deposit; none identifies anyone.

## Reproduce

From the repository root:

```
python calibration/realism_study/reproduce.py
```

It runs the analysis of record (`../anchor_analysis.py`, which applies the registered exclusions to the
export above), which rewrites `results/realism_results.json`, and checks that every number equals the
deposited file's. Output of record: Web Appendix F (the
realism comparison and Table WA-F1).
