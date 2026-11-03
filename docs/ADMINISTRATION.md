# Running the surveys: step-by-step instructions

A research assistant follows these steps to run the five confirmatory surveys on Prolific and Qualtrics at Stage
2, after in-principle acceptance. The steps follow the protocol in `docs/HUMAN_PROTOCOL.md` (recruitment,
assignment, replacement and exclusions) and the way in which we ran the four calibration studies on July 2, 2026
(`calibration/<study>/README.md` gives the record of each). No step changes a pre-registered decision, and where a
step names a number (pay, screening or sizes), it is the pre-registered number. Paths start at the root of the
repository.

## Before launching a survey

1. Take the survey file from this repository: `surveys/out/<survey>.qsf`, or the identical copy in
   `survey_package/`. Do not edit its questions, blocks, scripts, embedded data or option orders.
2. Fill in the two placeholders. Replace the bracketed placeholder on the consent page with the approved consent
   text, and replace `REPLACE_COMPLETION_CODE` in the closing redirect with the completion code of the survey's
   Prolific study. Then run `python surveys/validate_qsf.py surveys/out/<survey>.qsf`, which must pass every rule.
   It refuses the file while either placeholder remains.
3. Import the file into Qualtrics as a new survey (`survey_package/README.md` gives the steps). Keep the survey
   inactive until step 12.
4. For the words, pictures and price-free surveys (Surveys 3 and 4), set up the assignment service. Rebuild its
   data with `python surveys/assign_worker/build_worker_data.py`, and check that the hashes of the script sets that
   it prints equal the hashes in `surveys/out/*_MAPPING.json`. Deploy the service (`surveys/assign_worker/README.md`)
   and enter its `/assign` address in the survey's Web Service element. Its `/health` address must report 2,800
   scripts for the words survey, 2,100 for the pictures survey and 2,800 for the price-free survey.
5. For the pictures survey, put the nine files of `surveys/png/` at the web address that the survey uses for
   images. Open each address once to check that the file loads and is the same file (the same size and checksum).
6. Preview the survey from start to finish in Qualtrics: the consent page, the instructions, the attention check,
   every choice page, the demographic questions and the closing page. On a choice page, the participant must not be
   able to go on before choosing an option. Qualtrics marks preview responses with the preview channel, and the
   exclusion rules remove them.
7. If you need a live test (a real response through the study address before launch), put a participant id that
   starts with `STRESS_` in the address. The analysis removes these rows by that prefix. Do not delete test rows in
   Qualtrics: the export keeps them, and the exclusion rules remove them.

## Setting up the Prolific study

8. Create one Prolific study for each survey. The study address is the Qualtrics survey address followed by
   `?PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}`, so that the survey stores
   the three ids in embedded data. Set the completion code to the one that you wrote into the survey in step 2.
9. Set the screening of `docs/HUMAN_PROTOCOL.md`, section 2: adults who live in the US or the UK, are fluent in
   English, have an approval rate of 95 percent or more, and have at least 10 approved submissions. Restrict the
   study to desktop computers, unless the check before launch has shown that the choice pages, including the menu of
   12 options, display correctly on a phone.
10. Keep each person to one survey. With Prolific's participant blocklist, exclude everyone who took part in an
    earlier survey of this study, including the four calibration studies.
11. Pay at least about $12 an hour. Open about 30 places first, set the pay from their median completion time, and
    keep that pay for the whole study.
12. Activate the Qualtrics survey, and then publish the Prolific study.

## During and after data collection

13. Approve every submission that returns the completion code, as in the calibration studies. The attention check
    and the time rule decide who enters the analysis. The analysis code applies them (`surveys/SURVEY_SPEC.md`), and
    no response is removed from the data.
14. Download the complete Qualtrics export in both formats, CSV with the text of the choices and JSON with numeric
    codes, and keep every row. Store the raw exports privately, because they contain the Prolific ids.
15. Count the rows of the export against the approved, returned and timed-out submissions on Prolific, as the
    README of each calibration study does, and write the count down.
16. Recruit more participants by the rule in `docs/HUMAN_PROTOCOL.md`, section 4. Count the completed responses that
    the exclusion rules keep, for each cell, tier and clone placement. Open new places for the scripts whose cells
    are short, and stop when every cell is within a few percent of its target.
17. After the final export, set the Qualtrics survey to inactive and complete the Prolific study.
18. De-identify the exports for deposit in the same way as the calibration data (`calibration/*/README.md`).
    Replace each Prolific participant id with a sequential id, and let the authors keep the key. Leave blank the
    Prolific study id and submission id, the IP address, the location and the browser fields. Keep every row and
    every other column. Read the free-text answers before deposit.
19. For each survey, run `python analysis/ingest.py --export <export.csv> --out <survey>_long.csv`. The five
    tables have the same columns, so join them into one file, `human_long.csv`, with one header row. Then run
    `python analysis/analyze.py --human human_long.csv --model model_log.jsonl`.
