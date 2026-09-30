# The human study protocol

How the confirmatory human data will be collected: the surveys, recruitment, how each participant is
assigned a script, the top-up rule, what a participant sees, the exclusions, and how the export reaches the
analysis. No confirmatory human data have been collected; the surveys run after Stage 1 acceptance.

## 1. The five confirmatory surveys

| # | Survey | Cells | Participants | Choices each | File |
|---|---|---|---|---|---|
| 1 | Numeric backbone | 10 categories x 9 structures = 90 | 9,000 | 7 | `surveys/out/backbone.qsf` |
| 2 | Similarity top-up (both clone placements) | 10 similarity cells x 2 placements | 1,000 | 7 | `surveys/out/survey2_sim.qsf` |
| 3a | Format module, words | 3 structures x 4 categories = 12 | 2,800 | 3 | `surveys/out/survey3_words.qsf` |
| 3b | Format module, pictures | 3 structures x 3 categories = 9 | 2,100 | 3 | `surveys/out/survey3_pictures.qsf` |
| 4 | Price-free robustness test | 4 structures x 3 categories = 12 | 2,800 | 3 | `surveys/out/survey4_pricefree.qsf` |

The backbone fills each similarity cell to 700 (350 per clone placement); the top-up survey adds 700 per
placement, so each similarity cell reaches 1,400. The pictures module covers three categories because the
pictures version of the hard-drives pair left the design at the final calibration lock. In total: 93,100
confirmatory choices across 123 cells from about 17,700 participants (about 19,000 including the completed
calibration pre-test, which is not part of the confirmatory data).

## 2. Recruitment on Prolific

- **Platform.** Each survey is one Prolific study pointing at one Qualtrics survey. The study link passes
  `PROLIFIC_PID`, `STUDY_ID` and `SESSION_ID`, which the survey stores in embedded data.
- **Who.** Adults (18 or older, Prolific's own age screen), fluent in English, resident in the US or UK,
  with an approval rate of 95 percent or more and at least 10 prior approved submissions.
- **One person, one survey.** A participant appears in at most one of the surveys, the calibration waves
  included. Prolific's allowlists and blocklists enforce this: everyone who starts any survey is excluded
  from all the others. This keeps the within-person no-repeat logic valid across surveys and keeps the
  calibration sample independent of the confirmatory samples.
- **Pay.** A fair rate of about $12 per hour or more. The fee per study is set from the median completion
  time of a soft launch (the first 30 or so participants) and then fixed for the whole run. The completion
  code is given only by the survey's normal end redirect; people who decline consent or are screened out
  reach an end page without a code.
- **Device.** Desktop and mobile are allowed only if the launch check confirms that the choice widget
  displays correctly on a phone, including the 12-option extremity menu; otherwise the study is restricted to
  desktop through a Prolific screen. (The calibration waves ran on desktop only.)

## 3. How a participant is assigned

**The backbone and the similarity top-up.** Each participant is dealt one pre-built script by a single
Qualtrics block randomizer set to even presentation. A script is a fixed sequence of seven choices. The
180 backbone scripts (`surveys/scriptset_180.csv`, built by `surveys/scriptset_sim.py`) never repeat a
product category or a structure within a person; each of the 90 cells appears in 14 script positions; each
published cell's positions split exactly 7 tier-1 and 7 tier-2; each cell is the first choice in two scripts;
and the similarity cells split 7 and 7 between the two clone placements. The script writes all seven cells'
design variables into embedded data, so the export alone reconstructs the design. The similarity top-up
deals 1,000 scripts (`surveys/deal.py`) the same way.

Within-person constraints (no repeats, the seven-choice sequence) hold exactly by construction; the fill of
each cell is approximately even. Even presentation balances presentations, not completed responses, so a
participant who abandons still counts as a presentation, and completed fill per cell varies by a few
percent. The design's dropout simulation shows the analysis tolerates this (at 10 percent dropout, 658 to
676 completed per cell against a target of 700, with no constraint violated; `surveys/SCRIPTSET_RESULTS.md`).

**The words, pictures and price-free surveys.** These deal 2,800, 2,100 and 2,800 pre-built scripts of
three choices each (`surveys/deal.py`). A Qualtrics survey cannot import a randomizer with more than about
2,500 elements, so these scripts are dealt by a small assignment service instead
(`surveys/assign_worker/`). At the start of the survey, before any choice is shown, the survey makes one
call to the service, which returns the least-used script of that survey (ties broken at random) and counts
it; the survey stores the script in embedded data and the three choice pages render from it exactly as the
randomizer-fed pages do. The service assigns scripts only; it never receives responses or personal data.
The scripts, the balance and the within-person no-repeat rule are the same as with a randomizer. Because
the service updates its counts without a hard lock, two participants who start at the same instant can
occasionally receive the same script; across thousands of participants this gives the same few-percent
variation the dropout simulation covers, and the top-up rule below restores balance from the completed
responses in the export (never from the service's counts).

**If the service fails.** Each of these three surveys sets a field `assign_ok` from the service's reply and,
before the first choice page, sends anyone for whom it is not `true` to a short page that ends the survey
without a completion code and asks the person to return the submission on Prolific. A participant whose
assignment failed therefore never sees an empty choice page, and the slot is refilled by the top-up rule.
During collection the service's `/health` and `/stats` endpoints are monitored, and a study is paused if the
service is degraded. `surveys/survey_selftest.py` checks this wiring in the survey files.

## 4. The top-up rule

1. After each round of collection, count completed, non-excluded responses per cell and per published cell
   and tier, from the export's embedded-data fields (`cell{t}_category`, `cell{t}_structure`,
   `cell{t}_tier`, `cell{t}_sim_placement`) after the exclusion rules. The target is 700 per cell, 700 per
   similarity placement, and a 350 and 350 tier split on every published cell.
2. Top up at the level of scripts: open new places for the scripts whose cells are short. Because tier and
   placement are properties of script positions, this restores cell, tier and placement balance together.
3. Stop when every cell reaches its target, within a few percent (the tolerance the dropout simulation
   shows to be harmless).

## 5. What a participant sees

Consent (declining ends the survey without a completion code); instructions and one required attention
check; for the three surveys that use the assignment service, one call that fetches the script (invisible
when it succeeds); the timed choice pages (seven in the backbone and similarity surveys, three in the others),
one cell each, with the options rendered by the same code that renders them for the models
(`stimuli/render_shared.py`) and a choice required before moving on; two demographic questions (gender,
age); a debriefing; the redirect to Prolific with the completion code.

## 6. Exclusions

The registered rules are in `surveys/SURVEY_SPEC.md`: the attention check, the 3-second floor on the median
Page Submit time of the choice pages, the removal of previews, incomplete and duplicate responses, and the
symmetry of all rules across conditions. The Page Submit timer is the time a choice page was on screen before
the participant moved on; First Click is kept as a secondary measure.

## 7. How the options are shown

The option values are rendered by one function used by both the human surveys and the model runner, so a
person and a model never see differently formatted options. The choice is a small script-based widget rather
than a native multiple-choice question because the structures have two to twelve options and the pictures
format needs image options. The widget requires a choice before the Next button appears, and the export
records both the position chosen (`choice_t`) and the option's code (`choice_t_code`), decoded with the order
shown (`cell{t}_order`).

## 8. From export to analysis

`analysis/ingest.py` reads each survey's Qualtrics export, checks the expected columns, applies the exclusion
rules, decodes each choice to the option chosen, and writes the long table the analysis reads (one row per
choice; columns in `analysis/DATA_DICTIONARY.md`). The same analysis already runs on synthetic data in the
dress rehearsal (`analysis/`).

## 9. At launch

The survey files carry placeholder consent text and a placeholder completion code, and
`surveys/validate_qsf.py` refuses them until the real text and code are added. Each survey is imported into
Qualtrics and clicked through end to end before its Prolific study is published.
