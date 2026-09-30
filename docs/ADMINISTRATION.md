# Running the surveys: step-by-step instructions

These are the instructions a research assistant follows to field the five confirmatory surveys on Prolific and
Qualtrics at Stage 2, after in-principle acceptance. They follow the protocol in `docs/HUMAN_PROTOCOL.md`
(recruitment, assignment, top-up, exclusions) and the way the four calibration studies were fielded on July 2,
2026 (each study's record is in `calibration/<study>/README.md`). Nothing here changes a registered decision;
where a step names a number (pay, screening, sizes), it is the registered number. Paths are from the
repository root.

## Before a survey is launched

1. Take the survey file from the deposit: `surveys/out/<survey>.qsf`, or the identical copy in
   `survey_package/`. Do not edit its questions, blocks, scripts, embedded data or option orders.
2. Fill in the two launch placeholders. Replace the bracketed placeholder on the consent page with the
   approved consent text, and replace `REPLACE_COMPLETION_CODE` in the closing redirect with the completion
   code of the survey's Prolific study. Then run `python surveys/validate_qsf.py surveys/out/<survey>.qsf`,
   which must pass every rule. It refuses the file while either placeholder stands.
3. Import the survey into Qualtrics as a new survey, from the QSF file (the steps are in
   `survey_package/README.md`). Keep the survey inactive until step 12.
4. For Surveys 3 and 4 (words, pictures, price-free), set up the assignment service. Rebuild its data bundle
   with `python surveys/assign_worker/build_worker_data.py`, check that the deal hashes it prints equal the ones
   in `surveys/out/*_MAPPING.json`, deploy it (`surveys/assign_worker/README.md`), and set the survey's Web
   Service element to the service's `/assign` address. Its `/health` address must report 2,800 scripts for
   words, 2,100 for pictures and 2,800 for price-free.
5. For the pictures survey, host the nine files of `surveys/png/` at the image address the survey uses, and
   open each address once to check that it loads and is the same file (same size and checksum).
6. Preview the survey end to end in Qualtrics: consent, instructions, the attention check, every choice page,
   the demographic questions and the closing page. A choice page must not let the participant go on before an
   option is chosen. Qualtrics records preview responses with the preview channel, and the exclusion rules
   remove them.
7. If a live test is needed (a real response through the study link before launch), use a participant id that
   starts with `STRESS_` in the link. The analysis removes these rows by that prefix. Do not delete test rows
   from Qualtrics; the export keeps them and the exclusion rules handle them.

## Setting up the Prolific study

8. Create one Prolific study per survey. The study link is the Qualtrics survey link with
   `?PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}` added, so the survey
   stores the three ids in embedded data. Set the completion code to the one written into the survey in step 2.
9. Set the screening registered in `docs/HUMAN_PROTOCOL.md`, section 2: adults resident in the US or UK, fluent
   in English, an approval rate of 95 percent or more, and at least 10 approved submissions. Restrict the study
   to desktop computers unless the launch check has shown that the choice pages, the 12-option menu included,
   display correctly on a phone.
10. Keep one person to one survey: with Prolific's participant blocklist, exclude everyone who took part in any
    earlier survey of this study, the four calibration studies included.
11. Pay at least about $12 per hour. Launch a soft start of about 30 places, set the fee from its median
    completion time, and keep that fee for the whole run.
12. Activate the Qualtrics survey, then publish the Prolific study.

## During and after collection

13. Approve submissions that return the completion code, as the calibration studies did. The attention check
    and the time rule decide who enters the analysis; they are applied in code (`surveys/SURVEY_SPEC.md`), and
    no response is removed from the data.
14. Download the complete Qualtrics export in both formats, CSV with choice text and JSON with numeric codes,
    keeping every row. Store the raw exports privately, because they contain the Prolific ids.
15. Count the export rows against the approved, returned and timed-out submissions on Prolific, as each
    calibration study's README does, and write the reconciliation down.
16. Top up by the rule in `docs/HUMAN_PROTOCOL.md`, section 4: count completed, non-excluded responses per cell,
    tier and clone placement, open new places for the scripts whose cells are short, and stop when every cell
    is within a few percent of its target.
17. After the final export, set the Qualtrics survey to inactive and complete the Prolific study.
18. De-identify the exports for deposit in the same way as the calibration data (`calibration/*/README.md`):
    replace each Prolific participant id by a sequential id whose key stays with the authors; blank the Prolific
    study and submission ids, the IP address, the location and the browser fields; keep every row and every
    other column. Read the free-text answers before deposit.
19. Run `python analysis/ingest.py --export <export.csv> --out human_long.csv` for each survey, then
    `python analysis/analyze.py --human human_long.csv --model model_log.jsonl`.
