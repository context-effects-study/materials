# The protocol of the human study

This document says how we will collect the confirmatory human data: the surveys, the recruitment, how each
participant receives a script, the rule for recruiting more participants, what a participant sees, the exclusions,
and how the export reaches the analysis. We have collected no confirmatory human data. The surveys run after the
Stage 1 acceptance.

## 1. The five confirmatory surveys

| # | Survey | Cells | Participants | Choices each | File |
|---|---|---|---|---|---|
| 1 | The core design, shown as numbers | 10 categories x 9 structures = 90 | 9,000 | 7 | `surveys/out/backbone.qsf` |
| 2 | The similarity supplement (both placements of the clone) | 10 similarity cells x 2 placements | 1,000 | 7 | `surveys/out/survey2_sim.qsf` |
| 3a | The format module, words | 3 structures x 4 categories = 12 | 2,800 | 3 | `surveys/out/survey3_words.qsf` |
| 3b | The format module, pictures | 3 structures x 3 categories = 9 | 2,100 | 3 | `surveys/out/survey3_pictures.qsf` |
| 4 | The price-free categories | 4 structures x 3 categories = 12 | 2,800 | 3 | `surveys/out/survey4_pricefree.qsf` |

Survey 1 brings each similarity cell to 700 choices (350 for each placement of the clone), and the similarity
supplement adds 700 for each placement, so that each similarity cell reaches 1,400. The pictures version of the
format module has three categories, because the pictures pair of the hard drives left the design when we fixed the
final calibration values. In all, the surveys collect 93,100 confirmatory choices in 123 cells from about 17,700
participants. With the completed calibration pre-test, which is not part of the confirmatory data, the study has
about 19,000 participants.

## 2. Recruitment on Prolific

- **Platform.** Each survey has its own Prolific study, whose address opens the Qualtrics survey. The address passes
  `PROLIFIC_PID`, `STUDY_ID` and `SESSION_ID`, and the survey stores them in embedded data.
- **Who.** Adults (18 or older, by Prolific's own age screen) who are fluent in English, live in the US or the UK,
  have an approval rate of 95 percent or more, and have at least 10 earlier approved submissions.
- **One person, one survey.** A participant takes part in at most one of the surveys, including the calibration
  waves. Prolific's allowlists and blocklists enforce this: everyone who starts one survey is excluded from all the
  others. So the rules against repeats within a person hold across surveys, and the calibration sample stays
  separate from the confirmatory samples.
- **Pay.** A fair rate of about $12 an hour or more. We set the pay of each study from the median completion time
  of its first 30 or so participants and then keep it for the whole study. Only the normal end of the survey gives
  the completion code. People who decline consent or are screened out reach an end page without a code.
- **Device.** We allow phones as well as desktop computers only if the check before launch shows that the choice
  pages, including the extremity menu of 12 options, display correctly on a phone. Otherwise, a Prolific screen
  restricts the study to desktop computers. The calibration waves ran on desktop computers only.

## 3. How each participant receives a script

**Survey 1 and the similarity supplement.** Qualtrics assigns each participant one pre-built script, with one
randomizer set to even presentation. A script is a fixed sequence of seven choices. The 180 scripts of Survey 1
(`surveys/scriptset_180.csv`, built by `surveys/scriptset_sim.py`) meet five conditions:

- no script repeats a product category or a structure;
- each of the 90 cells appears in 14 positions across the scripts;
- the 14 positions of each published cell split into exactly 7 with tier-1 values and 7 with tier-2 values;
- each cell is the first choice of two scripts;
- the similarity cells split 7 and 7 between the two placements of the clone.

The survey writes the design variables of all seven cells into embedded data, so that the design can be rebuilt
from the export alone. The similarity supplement assigns its 1,000 scripts (`surveys/deal.py`) in the same way.

The rules within a person (no repeats, and the sequence of seven choices) hold exactly, because the scripts are
built that way. The number of completed responses in each cell is only approximately even. Even presentation
balances how often each script is shown, not how many responses are completed. A participant who stops partway
still counts as a presentation, so the completed responses of a cell can differ by a few percent from its target.
A simulation of participants who stop partway shows how large this difference is. With 10 percent of participants
stopping, each cell has 658 to 676 completed choices against a target of 700, and no rule within a person is broken
(`surveys/SCRIPTSET_RESULTS.md`).

**The words, pictures and price-free surveys.** These surveys assign 2,800, 2,100 and 2,800 pre-built scripts of
three choices each (`surveys/deal.py`). Qualtrics cannot import a randomizer with more than about 2,500 elements, so
a small web service assigns these scripts (`surveys/assign_worker/`). At the start of the survey, before any choice,
the survey makes one call to the service. The service returns the script of that survey that has been assigned least
often so far (ties are broken at random) and adds one to its count. The survey stores the script in embedded data,
and the three choice pages show it exactly as the pages of Survey 1 show a script from the randomizer. The service
only assigns scripts, and it never receives responses or personal data. The scripts, the balance and the rules
against repeats within a person are the same as with a randomizer. The service updates its counts without a strict
lock, so two participants who start at the same moment can sometimes receive the same script. Across thousands of
participants, this gives the same variation of a few percent that the simulation of participants who stop partway
covers, and the rule in section 4 restores the balance from the completed responses in the export, never from the
service's counts.

**If the service fails.** Each of these three surveys sets a field, `assign_ok`, from the service's reply. Before the
first choice page, the survey sends anyone for whom this field is not `true` to a short page. That page ends the
survey without a completion code and asks the person to return the submission on Prolific. A participant whose
assignment failed therefore never sees an empty choice page, and the rule in section 4 fills the place again. During
data collection, we watch the service's `/health` and `/stats` addresses and pause a study if the service is not
working properly. `surveys/survey_selftest.py` checks this part of the survey files.

## 4. Recruiting more participants

1. After each round of data collection, count the completed responses that the exclusion rules keep, for each cell,
   and for each tier of each published cell. Read the counts from the embedded-data fields of the export
   (`cell{t}_category`, `cell{t}_structure`, `cell{t}_tier`, `cell{t}_sim_placement`) after applying the exclusion
   rules. The targets are 700 for each cell, 700 for each placement of the clone, and a split of 350 and 350 between
   the two tiers of every published cell.
2. Recruit by script: open new places for the scripts whose cells are short. Tier and placement belong to positions
   in the scripts, so this step restores the balance of cells, tiers and placements together.
3. Stop when every cell has reached its target, within a few percent. The simulation of participants who stop
   partway shows that a difference of this size does no harm.

## 5. What a participant sees

A participant sees, in order:

- the consent page (declining ends the survey without a completion code);
- the instructions and one required attention check;
- in the three surveys that use the assignment service, nothing visible while the survey fetches the script;
- the timed choice pages (seven in Survey 1 and the similarity supplement, three in the others), one cell on each
  page. The same code (`stimuli/render_shared.py`) writes the options for the participants and for the models, and
  the participant must choose before moving on;
- two demographic questions (gender and age);
- a debriefing;
- the return to Prolific with the completion code.

## 6. Exclusions

`surveys/SURVEY_SPEC.md` gives the pre-registered rules: the attention check; the floor of 3 seconds on the median
time that the choice pages were on screen (the Page Submit timer); the removal of preview, incomplete and duplicate
responses; and the rule that every exclusion applies in the same way in every condition. The Page Submit timer
measures how long a choice page was on screen before the participant moved on. The survey also records the time of
the first click, as a second measure.

## 7. How the options are shown

One function writes the option values for both the human surveys and the model program, so that a person and a
model never see options formatted differently. The choice is made in a small widget written in JavaScript, not in a
standard multiple-choice question, because the structures have two to twelve options and the pictures format needs
options that are images. The widget shows the Next button only after a choice. The export records the position chosen
(`choice_t`), the code of the option (`choice_t_code`) and the order in which the options were shown
(`cell{t}_order`), so that each choice can be decoded from the export.

## 8. From the export to the analysis

`analysis/ingest.py` reads the Qualtrics export of each survey. It checks the expected columns, applies the exclusion
rules, decodes each choice to the option chosen, and writes the table that the analysis reads, with one row per
choice (`analysis/DATA_DICTIONARY.md` gives the columns). The same analysis already runs on simulated data
(`analysis/`).

## 9. At launch

The consent text and the completion code in the survey files are placeholders, and `surveys/validate_qsf.py` refuses
the files until someone adds the real text and code. We import each survey into Qualtrics and complete it from
start to finish before we publish its Prolific study.
