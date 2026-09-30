# surveys/

The five confirmatory human surveys, the code that generates them from `../stimuli/stimuli.json`, the
balanced participant scripts, and the assignment service used by three of them. Regenerating the surveys
reproduces the deposited files byte for byte.

## The five surveys (`out/`, each with its design mapping)

| File | Survey |
|---|---|
| `backbone.qsf` | Survey 1, the numeric backbone: seven choices per participant across all nine structures, dealt through 180 pre-built balanced scripts inside Qualtrics |
| `survey2_sim.qsf` | Survey 2, the similarity top-up (the second clone placement) |
| `survey3_words.qsf` | Survey 3, format module, words (numeric values spelled out) |
| `survey3_pictures.qsf` | Survey 3, format module, pictures (magnitude-bar images; three categories) |
| `survey4_pricefree.qsf` | Survey 4, the price-free robustness test |

Each `*_MAPPING.json` is the key that decodes the survey's export: the cells, the scripts, the option
codes, the answer key of the attention check and the deal hashes. The surveys carry placeholder consent
text and a placeholder completion code (`cc=REPLACE_COMPLETION_CODE`), which are replaced only at launch, so
the deposited files cannot be fielded by accident. The recruitment, assignment and top-up procedure is in
`../docs/HUMAN_PROTOCOL.md`; the exclusion rules are in `SURVEY_SPEC.md`.

## Code and documents

| File | What it is |
|---|---|
| `generate_qsf.py`, `generate_survey.py` | Generate the backbone and the four other surveys |
| `deal.py`, `DEAL_RESULTS.md` | The balanced script deals of Surveys 2 to 4 and their balance proofs |
| `scriptset_sim.py`, `scriptset_180.csv`, `SCRIPTSET_RESULTS.md` | The 180 backbone scripts and their balance proof, with a dropout simulation |
| `validate_qsf.py` | Checks a survey file against the Qualtrics import rules and the launch placeholders |
| `qsf_selftest.py`, `survey_selftest.py` | Rebuild the design from the survey files alone and check it (backbone; Surveys 2 to 4) |
| `generate_calibration.py`, `generate_anchor.py`, `calibration_selftest.py` | The generators of the calibration surveys and the realism comparison survey, and the check of the fielded calibration files (the fielded files are in `../calibration/*/survey/`) |
| `rasterize.py`, `make_wave2_images.py`, `make_wave3_images.py` | Picture tools: SVG to PNG, and the calibration waves' images |
| `SURVEY_SPEC.md` | The registered exclusion rules |
| `png/` | The pictures-format images as served to participants and sent to vision models |
| `walkthrough/` | Every distinct screen of the five surveys, in one PDF, with the screenshots |
| `assign_worker/` | The assignment service for Surveys 3 and 4 (below) |

The same five surveys and mappings, with the walkthrough, the pictures and instructions for importing them
into Qualtrics, are also in `../survey_package/`.

## Regenerate and check

```
python surveys/generate_qsf.py         # backbone.qsf and its mapping
python surveys/generate_survey.py      # the other four surveys and their mappings
python surveys/qsf_selftest.py         # the backbone design, rebuilt from the file
python surveys/validate_qsf.py surveys/out/backbone.qsf   # passes every rule except the launch placeholder
```

## The assignment service

The words, pictures and price-free surveys deal more scripts than a Qualtrics randomizer can hold, so a
small service (`assign_worker/`, a Cloudflare Worker) hands each new participant the least-used script at
the start of the survey. If the service cannot answer, the survey ends before any choice with no completion
code, and the slot is refilled by the top-up rule. The service's data bundle is not deposited; it is
rebuilt from the deposited stimuli and deals by `assign_worker/build_worker_data.py`, and the deal hashes it
records must equal the ones in the survey mappings, which shows the service serves exactly the registered
scripts.
