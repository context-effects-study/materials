# surveys/

This folder holds the five confirmatory surveys for people, the code that writes them from `../stimuli/stimuli.json`,
the balanced scripts of choices that participants receive, and the web service that assigns scripts in three of the
surveys. When the code writes the surveys again, the files come out identical, byte for byte, to the deposited ones.

## The five surveys (`out/`, each with its design key)

| File | Survey |
|---|---|
| `backbone.qsf` | Survey 1, the core design: seven choices for each participant across all nine structures, shown as numbers. Qualtrics assigns 180 pre-built, balanced scripts |
| `survey2_sim.qsf` | Survey 2, the similarity supplement, which adds similarity choices with the clone in both placements |
| `survey3_words.qsf` | Survey 3, the format module in words (every value spelled out) |
| `survey3_pictures.qsf` | Survey 3, the format module in pictures (values drawn as bars; three categories) |
| `survey4_pricefree.qsf` | Survey 4, the price-free categories |

Each `*_MAPPING.json` file is the key for decoding the export of its survey: the cells, the scripts, the codes of the
options, the answer of the attention check and the hashes of the script sets. The consent text and the completion
code (`cc=REPLACE_COMPLETION_CODE`) of each survey are placeholders, which we replace only at launch, so that nobody
can field the deposited files by accident. `../docs/HUMAN_PROTOCOL.md` describes recruitment, assignment and the
recruitment of more participants, and `SURVEY_SPEC.md` gives the exclusion rules.

## Code and documents

| File | What it is |
|---|---|
| `generate_qsf.py`, `generate_survey.py` | Write Survey 1 and the four other surveys |
| `deal.py`, `DEAL_RESULTS.md` | Assign the balanced scripts of Surveys 2 to 4, and show that they are balanced |
| `scriptset_sim.py`, `scriptset_180.csv`, `SCRIPTSET_RESULTS.md` | The 180 scripts of Survey 1, the proof that they are balanced, and a simulation of participants who stop partway |
| `validate_qsf.py` | Checks a survey file against the import rules of Qualtrics and against the placeholders of the launch |
| `qsf_selftest.py`, `survey_selftest.py` | Rebuild the design from the survey files alone and check it (Survey 1; Surveys 2 to 4) |
| `generate_calibration.py`, `generate_anchor.py`, `calibration_selftest.py` | Write the calibration surveys and the survey of the realism comparison, and check the fielded calibration files (`../calibration/*/survey/` holds the fielded files) |
| `rasterize.py`, `make_wave2_images.py`, `make_wave3_images.py` | Tools for the pictures: they convert SVG to PNG and draw the pictures of the calibration waves |
| `print_survey.py` | Writes the printable PDF view of each calibration survey |
| `SURVEY_SPEC.md` | The pre-registered exclusion rules |
| `png/` | The pictures, as participants see them and as the models that accept images receive them |
| `walkthrough/` | Every distinct screen of the five surveys, in one PDF, with the screenshots |
| `assign_worker/` | The assignment service for the words, pictures and price-free surveys (see below) |

`../survey_package/` holds the same five surveys and design keys, with the screens document, the pictures and
instructions for importing them into Qualtrics.

## Write the surveys again and check them

```
python surveys/generate_qsf.py         # backbone.qsf and its design key
python surveys/generate_survey.py      # the other four surveys and their design keys
python surveys/qsf_selftest.py         # the design of Survey 1, rebuilt from the file
python surveys/validate_qsf.py surveys/out/backbone.qsf   # passes every rule except the placeholders of the launch
```

## The assignment service

The words, pictures and price-free surveys assign more scripts than a Qualtrics randomizer can hold. A small web
service (`assign_worker/`, a Cloudflare Worker) therefore gives each new participant, at the start of the survey,
the script that has been assigned least often so far. If the service does not answer, the survey ends before any
choice and gives no completion code, and the place is filled again under the rule for recruiting more
participants. We do not deposit the data of the service. `assign_worker/build_worker_data.py` rebuilds them from the
deposited stimuli and scripts, and the hashes of the script sets that it records must equal the hashes in the design
keys of the surveys. This check shows that the service assigns exactly the pre-registered scripts.
