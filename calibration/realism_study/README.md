# The realism comparison study (July 2, 2026)

In waves 2 and 3, the invented categories missed the realism threshold, a mean of 5.0 on the 7-point question
"does this read like a real product page?". Nobody had rated the page of a published category on that question. In
this study, 112 new raters, none of whom took part in a calibration wave, rated the pages of the seven published
categories, which we showed exactly as wave 3 showed the invented ones. We added the study after the wave-3 data,
to learn how to interpret the realism ratings of the invented categories. It changed no stimulus and no value.
`REPORT.md` gives what it found.

## The study

| Field | Value |
|---|---|
| Platform | Prolific (recruitment and payment); Qualtrics (the survey) |
| Public study name | "Rate a few product pages (about 2 minutes)" |
| Survey | `survey/realism_study.qsf`, exactly as fielded: consent, an attention check, the pages of four of the seven published categories, assigned evenly, each with the 7-point question that wave 3 used, an optional comment, and the demographic questions |
| Published | 18:07 UTC on July 2, 2026; all places filled in about 17 minutes |
| Places | 112 (64 ratings for each category by design) |
| Pay | $0.40 for about 2 minutes |
| Total cost | $59.73 including the platform's fees |
| Screening | As in the calibration waves, with every participant of the three waves excluded |

## Files

| File | What it is |
|---|---|
| `survey/realism_study.qsf`, `survey/realism_study_MAPPING.json` | The Qualtrics survey as fielded, and its design key |
| `survey/realism_study.pdf` | A printable view of the same survey: the flow, every block and every question (written by `../../surveys/print_survey.py`) |
| `data/raw/realism_export.csv` | The complete Qualtrics export with labels, 117 rows, de-identified. Nothing in this repository writes to it |
| `data/raw/realism_export.json` | The same responses in Qualtrics' JSON format, de-identified in the same way |
| `data/processed/realism_ratings.csv` | One row for each rating: the respondent, the category, the rating, the time on the page, and whether the rating was kept |
| `codebook_export.csv`, `codebook_ratings.csv` | The data dictionaries |
| `results/realism_results.json` | The output of `../anchor_analysis.py`. For each category and pooled over categories, it gives the mean rating with its 95 percent interval and the share of ratings of 5 or higher, and it gives the differences between the published and the invented categories (Welch tests). The keys are `anchor_rows`, `anchor_kept` and `anchor_excluded` (this study); `published_per_category` and `published_pooled_respmean` (the mean of each rater's mean); `wave3_rows`, `wave3_kept`, `invented_per_category` and `invented_pooled_respmean` (wave 3, computed again from the wave-3 export); and `parity_welch_pooled` and `published_pooled_minus_invented_category` |
| `REPORT.md` | What the study found |

## Every row of the export

The 117 rows of the export are 112 approved completions, 1 respondent who completed after the Prolific timer ran
out (kept), and 4 test rows that we wrote before launch (participant ids beginning STRESS_ANCHOR_, removed before
the analysis). The analysis kept 111 respondents (444 ratings, 63 or 64 for each category). It excluded 2
respondents: 1 failed the attention check, and 1 answered too fast.

## De-identification

We de-identified the data as in the calibration waves. Participant ids are sequential (RS-0001 onward), and the
authors keep the key. The Prolific study id and submission id, the IP address, the location and the browser
fields are blank. The test rows keep their labels. We read every optional comment before deposit, and none
identifies anyone.

## Reproduce

From the root of the repository:

```
python calibration/realism_study/reproduce.py
```

The script runs the original analysis (`../anchor_analysis.py`, which applies the exclusion rules of the
confirmatory studies to the export above). The analysis writes `results/realism_results.json` again, and the script
checks that every number equals the deposited one. Web Appendix F reports the results (the realism comparison and
Table WA-F1).
