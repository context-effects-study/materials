# The human surveys

This folder holds the five Qualtrics surveys that will collect the human choices in the confirmatory study, the
file that decodes each survey's data, and a walkthrough that shows every screen a participant sees. Nothing here
has been fielded. The surveys run only after Stage 1 acceptance, as registered.

## The five surveys

Each participant takes one survey only.

| File | Survey | Participants (about) | Choices each | Choices in total |
|---|---|---|---|---|
| `backbone.qsf` | Survey 1, the numeric survey: all nine kinds of choice page, shown with numbers, in ten product categories | 9,000 | 7 | 63,000 |
| `survey2_sim.qsf` | Survey 2, the similarity survey: similarity pages only, shown with numbers, so each similarity condition reaches its registered size with the near copy placed next to either original option | 1,000 | 7 | 7,000 |
| `survey3_words.qsf` | Survey 3, words version: two-option, frequency-decoy and compromise pages with every attribute value and price spelled out in words (Bluetooth speakers, external hard drives, televisions, water bottles) | 2,800 | 3 | 8,400 |
| `survey3_pictures.qsf` | Survey 3, pictures version: the same pages with the values drawn as bars and no numbers (Bluetooth speakers, televisions, water bottles) | 2,100 | 3 | 6,300 |
| `survey4_pricefree.qsf` | Survey 4, the price-free survey: two-option, frequency-decoy, range-decoy and phantom pages whose options differ on two quality ratings and carry no price (external hard drives, restaurants, televisions) | 2,800 | 3 | 8,400 |
| | Total | 17,700 | | 93,100 |

The nine kinds of choice page in Survey 1 are the two-option baseline, compromise, frequency decoy, range decoy,
phantom (a better option marked currently unavailable), upscaling, similarity, the twelve-option extremity menu,
and its three-option control. Survey 1 covers seven categories with published values, each split evenly between
the published numbers and new numbers, and three invented categories.

Every survey follows the same order: a consent page, an instructions page, an attention check, the choice pages,
two demographic questions (gender and age), and a closing page that returns the participant to Prolific. The
attention check never stops a participant; failing it excludes the participant from the analysis. Besides the
choices, each survey records the time spent on every choice page, the answers to the attention check and the
demographic questions, the browser details and screen size, and the Prolific identifiers passed in the study link
(used only to enforce one survey per person). Qualtrics' duplicate-submission prevention and its invisible bot
check are switched on.

## How each participant gets a set of choice pages

Each participant is dealt one pre-built script: a list of choice pages, balanced so that every condition receives
its registered number of choices and no participant sees a category twice. The order of the options on a page
varies across participants, except in the pictures version, where it is the order drawn in the picture.

- Surveys 1 and 2 hold all their scripts inside the survey (180 and 1,000), and Qualtrics hands them out evenly.
- Surveys 3 and 4 have more scripts than a Qualtrics survey can hold (2,800, 2,100 and 2,800). Right after the
  attention check they fetch a script from a small web service that hands out the least-used one. If the service
  does not answer, the participant sees a page asking them to return the study on Prolific, before any choice.
  In these copies the service address is a placeholder (`https://STUDY-ASSIGNMENT-SERVICE.example/assign`); it is
  the only line in which these three files, and their mapping files, differ from the files held for the study.

## The walkthrough

`SURVEY_WALKTHROUGH.pdf` (30 pages) shows every distinct screen: the consent page, the instructions, the attention
check, one page of every kind of choice page in numbers, words and pictures, the demographic questions, the closing
page, and the two pages shown when a participant stops early. Each screen was rendered from these survey files,
filled with a real participant script, in a web browser. It is the easiest way to see Surveys 3 and 4, whose
choice pages depend on the assignment service.

## The mapping files

Each `*_MAPPING.json` records how the survey was built and what is needed to read its data export:

- `backbone_MAPPING.json`: the random seed and version the survey was built with, a short hash of the 180-script
  set, the correct answer of the attention check (option 5, "Strongly agree"), and the key that turns the
  category and page-type numbers used in the scripts into their names.
- The other four: the survey's name and version, a short hash of its script deal, the number of scripts and of
  choices per participant, whether scripts come from inside the survey or from the assignment service (with the
  service address and the survey name it asks for), the address of the pictures (pictures version only), and the
  correct answer of the attention check.

For each choice, the data export also records the page shown, the order of its options and the option chosen,
so the choices can be decoded from the export alone.

## Importing a survey into your own Qualtrics account

1. In Qualtrics, create a new project from a file: on the Projects page choose to create a survey project and,
   when asked how to start, choose to import a QSF file. (From inside any existing survey, Tools, then
   Import/Export, then Import survey, does the same.)
2. Choose one of the `.qsf` files and import it. `survey2_sim.qsf` is large (about 16 MB) and can take a minute.
3. Open the survey and click Preview. A preview may record a test response, in your own account only.

What to expect in a preview:

- The consent page shows placeholder text. Click either button and the arrow appears. On every choice page the
  arrow appears only after an option is chosen.
- Surveys 1 and 2 run from start to finish. At the end the preview tries to open Prolific with a placeholder
  completion code, which is not part of the survey.
- Surveys 3 and 4 show the consent page, the instructions and the attention check, then the page that asks the
  participant to return the study, because the assignment service address is a placeholder. Their choice pages
  are in the walkthrough.
- The pictures version loads its nine pictures from a web address written in the file. The same nine pictures
  are in `images/`, named by page kind (BIN two-option, FRQ frequency decoy, SOT compromise), category, and t2
  for the new-values tier.

## Placeholders until the Stage 2 launch

Two things are placeholders on purpose and are filled in only at the approved Stage 2 launch: the consent text
(the bracketed note on the consent page is replaced with the approved consent text) and the Prolific completion
code (`cc=REPLACE_COMPLETION_CODE` in the closing redirect). While they stand, a survey cannot be fielded by
accident. The assignment service address is a placeholder only in these copies; the surveys held for the study
carry the working one. The pages, their wording, the values, the scripts and the option orders stay as they are.

## Checking the files

`SHA256SUMS.txt` lists a SHA-256 checksum for every file in this folder except this README.
