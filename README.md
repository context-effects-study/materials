# Do Large Language Models Reproduce Human Context Effects in Consumer Choice? Data and code

This repository holds the data, materials and code of a Registered Report at the *Journal of Consumer
Research* (Stage 1). In the study, people and ten large language models answer the same product-choice
questions. We test whether the models reproduce seven context effects that people show: the attraction effect
with a frequency decoy, with a range decoy and with a phantom decoy, and the compromise, extremity, upscaling and
similarity effects.

## What the Stage 1 guidelines ask for, and where it is

The journal's guidelines for Registered Reports ask that the Stage 1 repository hold all the materials that the
study uses. The table lists each item and the file or folder that holds it.

| Item | Where |
|---|---|
| Survey and experiment stimuli | `stimuli/stimuli.json` (all 165 stimuli); `stimulus-explorer.html` (every stimulus as people and models see it); `surveys/out/` and `survey_package/` (the five confirmatory surveys); `surveys/png/` (the pictures); `models/prompt_materials.json` (the wording of the model prompts) |
| Data dictionary | `analysis/DATA_DICTIONARY.md` (the confirmatory human data, the model call log and the results files); `calibration/<study>/codebook_*.csv` (every data file of the calibration pre-test) |
| Instructions for research assistants | `docs/ADMINISTRATION.md` (how to run each survey on Prolific and Qualtrics, step by step) |
| Plans for running the study | `docs/HUMAN_PROTOCOL.md` (recruitment, assignment, replacement and exclusions); `surveys/SURVEY_SPEC.md` (the exclusion rules); `models/README.md` and `models/MANIFEST.md` (the model conditions and the exact plan of model calls) |
| Decision tree | `figures/figure3.png` (Figure 3: does the model match people, and if not, why not); `analysis/analyze.py` applies it; `analysis/REGISTERED_CONSTANTS.md` lists every cutoff; Web Appendix Table WA-E5 states what each outcome will mean |
| Power analysis | `power/` (every power figure in the Method and Web Appendix E, each with its script; for the pattern tests, the smallest difference that each test can detect, Table WA-E4) |
| Data analysis code | `analysis/` (the pre-registered analysis, its tests and its mutation check); `calibration/` (the analyses of the pre-test) |
| Simulated data | `analysis/demo_data/` (simulated data in the formats of the real data) and `analysis/results_pack/` (the results files that the analysis wrote from them) |

Reviewers see this copy through an anonymized GitHub repository. At in-principle acceptance, the same files go
to a public archive with a DOI. At Stage 2, a new version of that archive adds the confirmatory data.

## About this release

This is the Stage 1 release. It holds everything that a reader needs to check and rerun the plan:

- the stimuli, and the code that builds and checks them;
- the completed calibration pre-test: four studies, with de-identified data, codebooks, surveys and analysis
  code;
- the five confirmatory surveys, ready to import;
- the program that sends the choice questions to the models, with its exact plan of calls;
- the pre-registered analysis, tested end to end on simulated data and checked by unit tests;
- the power analyses;
- every figure, with the script that draws each figure computed from data.

We have collected no confirmatory data. At Stage 2, we will add the confirmatory human data, the log of every
model call and the results files to a new version of this release.

## Start here

- `stimulus-explorer.html` opens offline in any web browser and shows all 165 stimuli. You can filter the
  stimuli by product category, effect, stimulus tier and format. For each choice set, the page shows the
  options as a participant sees them, names the role of each option, and gives the exact text that each model
  receives.
- `analysis-explorer.html` opens offline in any web browser. Before collecting data, we ran the analysis on
  simulated people and on simulated models, each built to behave in one known way. For each simulated model, the
  page shows the five steps of the analysis. Press Play, and the page draws each step in turn with that model's
  numbers: whether a comparison is possible, the human effects, the model's effects on the
  fidelity map, and each pattern test against its cutoffs. It ends with the two questions of Step 4: does the
  model match people, and if not, which failures does it show? The last step gives the conclusion that the
  code reached and whether the model was built to reach it. In a second view, all the simulated models are
  sorted by their conclusions. A third view shows the folders of this repository in the order in which the study
  uses them, from the calibration pre-test and the stimulus file, through the surveys and the model program, to the
  analysis and its results files. You do not need to read code to use the page.
- `survey_package/` holds the five confirmatory surveys, ready to import into your own Qualtrics account, with
  instructions and a document that shows every screen (`SURVEY_WALKTHROUGH.pdf`).
- `python run_all.py` reruns every script that writes a result and checks each result against the copy in this
  repository (see "Instructions").

## Overview

| Folder or file | What it holds | Manuscript |
|---|---|---|
| `stimulus-explorer.html` | All 165 stimuli as participants and models see them (one file that works offline) | Method; Web Appendix B |
| `analysis-explorer.html` | Steps 0 to 4 of the analysis for each simulated model, drawn step by step with Play controls; all simulated models sorted by their conclusions; a map of the folders (one file that works offline) | Analysis Plan; Figure 3; Table 4 |
| `calibration/` | The calibration pre-test: its design and every change between waves, and one folder for each of its four studies (waves 1, 2 and 3, and the realism comparison study) | Method, Human study; Web Appendix F |
| `stimuli/` | The stimulus file (165 stimuli), the code that builds and checks it, and the source of every published value | Method; Table 2; Web Appendix B |
| `surveys/` | The five confirmatory Qualtrics surveys, the code that writes them, the participant scripts, a document with every screen, and the web service that assigns scripts in three of the surveys | Method, Human study; Table 2 |
| `survey_package/` | The same five surveys, ready to import, with the screens document, the pictures and instructions | Method, Human study |
| `models/` | The program that calls the models, the ten models and their settings, the pre-registered prompt wording, and the exact plan of 1,285,630 calls | Method, Model study; Table 2; Table 3; Web Appendix D |
| `analysis/` | The pre-registered analysis, its table of cutoffs, the program that reads a Qualtrics export, the data dictionary, the run on simulated data with its results files, the unit tests and the mutation check | Analysis Plan; Table 4; Web Appendices C and E |
| `power/` | The power analyses and the simulations of the design | Method, Human study; Web Appendix E |
| `figures/` | Every figure of the manuscript and the web appendix, with the script that draws each figure computed from data | Figures 1 to 3; Web Appendices A, B, E and F |
| `docs/` | The protocol of the human study and the step-by-step instructions for running the surveys | Method, Human study |
| `run_all.py` | Reruns every script that writes a result and checks each result against the copy in this repository | all of the above |

## Data availability and sources

**The calibration pre-test data, which we collected.** Four online studies ran on July 2, 2026. We recruited and
paid participants through Prolific, and Qualtrics hosted the surveys. Calibration waves 1, 2 and 3 had 400, 312
and 462 approved participants, and the realism comparison study had 112. In all, 1,286 participants were
approved, at a cost of $1,571.93 including the platform's fees. Participants were adults who lived in the US or
the UK, were fluent in English, and took part on a desktop computer. Each participant gave consent on the first
page of the survey, and the consent text is in each survey file. The README of each study gives its dates, pay
and screening, and it accounts for every row of the export.

The files in `calibration/*/data/raw/` are the complete Qualtrics exports, as a CSV file with labels and a JSON
file with numeric codes. We de-identified them before deposit in three ways:

- We replaced each Prolific participant id with a sequential id in order of first appearance (W1-0001, W2-0001,
  W3-0001, RS-0001 and so on). The authors keep the key that links the two ids.
- We left the Prolific study id and submission id blank.
- We left the IP address, the location and the browser fields blank.

Everything else is as Qualtrics exported it, including age, gender, timings and the free-text comments. We read
every comment before deposit, and none identifies anyone. The analysis never uses the fields that we removed,
and every original report can be rebuilt from these files (`run_all.py`). The authors keep the original exports,
which contain Prolific ids, and do not share them, to protect the participants. To verify a specific result, a
researcher can examine them with the authors on request, under the terms on which the data were collected. Before
each launch, we submitted test responses, which Qualtrics stored as rows of the export. The exports keep these rows,
their participant ids begin with STRESS_, and the analysis removes them.

**Stimulus values from published studies.** The tier-1 stimuli use the exact option values of the published
studies of each effect. `stimuli/fragments/<category>_receipts.md` lists every such value with its source
(authors, year, journal and DOI).

**Confirmatory human and model data.** We have not collected them yet (Stage 1). See "The model responses at
Stage 2".

**License.** The code is under the MIT License, and the data and all other materials are under CC BY 4.0
(`LICENSE`).

| Data file | Source | Provided | License |
|---|---|---|---|
| `calibration/wave1/data/raw/calibration_wave1_export.{csv,json}` | the authors, through Prolific and Qualtrics, July 2, 2026 | yes, de-identified | CC BY 4.0 |
| `calibration/wave2/data/raw/calibration_wave2_export.{csv,json}` | as above | yes, de-identified | CC BY 4.0 |
| `calibration/wave3/data/raw/calibration_wave3_export.{csv,json}` | as above | yes, de-identified | CC BY 4.0 |
| `calibration/realism_study/data/raw/realism_export.{csv,json}` | as above | yes, de-identified | CC BY 4.0 |
| `calibration/*/data/processed/*.csv` | written by `calibration/make_choice_files.py` from the files above | yes | CC BY 4.0 |
| tier-1 values in `stimuli/fragments/` | the published studies, cited in the `*_receipts.md` files | yes | the facts belong to their sources |

Every data file has a codebook. For the pre-test, `calibration/<study>/codebook_*.csv` gives each variable's
type, values, units and meaning, and the codebook of each export also gives the key of each column in the JSON
file. For the confirmatory data, `analysis/DATA_DICTIONARY.md` describes the three formats: the human data with
one row per choice, the model call log and the results files.

## Computational requirements

- **Software.** The code needs Python 3.13, and we tested it with Python 3.13.13 (64-bit). Everything except
  the figures and one power simulation uses only the Python standard library. `requirements.txt` lists, at the
  tested versions, the four packages that the rest needs and the packages that they install:
  - numpy, for `power/clustered_power.py`;
  - matplotlib, for Figure WA-F1;
  - Playwright and Pillow, for the Web Appendix B figures, the stimulus explorer and the checks of both.

  After installing the packages, run `python -m playwright install chromium` once. The live model calls of
  Stage 2 also need the providers' API keys, but nothing in this repository needs them.
- **Tested on.** Windows 11 (64-bit), in a new virtual environment made from `requirements.txt` alone (see
  "Tested from a fresh copy" at the end of this file).
- **Hardware.** An ordinary desktop or laptop computer, with no GPU, and about 200 MB of free disk space for the
  repository and the files that `run_all.py` writes. The code needs no network access, except once to download
  the packages and the browser.
- **Runtime.** On the test computer, `python run_all.py` takes about 7 minutes. The clustered power simulation
  takes about 2 minutes, the self-tests of the model program and the run of the analysis on simulated data
  take 1 to 2 minutes each, and every other step takes seconds. `python run_all.py --quick` takes about 4
  minutes. `python run_all.py --full` adds four long checks, which take about an hour and a half in all: the
  stability of the conclusions under the noise of repeated model calls (about 17 minutes), the resolution
  statement (about 45 minutes), the sample that the simulated model that matches people would need (about 8
  minutes) and the mutation check (15 to 20 minutes).

## Instructions

From the root of the repository:

```
python -m venv .venv
.venv\Scripts\activate          (Windows)   or   source .venv/bin/activate   (macOS, Linux)
pip install -r requirements.txt
python -m playwright install chromium
python run_all.py
```

`run_all.py` runs every step listed below, in order. After each step, it compares the files that the step
wrote with the copies in this repository (images pixel by pixel) and prints a summary. It exits with an error
if any step does not reproduce its files. The calibration reports are written to `reproduction/` and compared
row by row with the original reports in `calibration/*/results/`. A new report differs from the original in
three places only: its first line, which names the input file; the title of one column; and the working label
of the final calibration values. The figures drawn from data, the stimulus explorer, the printable views of the
four calibration surveys and two reports of the analysis run (`analysis/results_pack/RUN_REPORT.md` and
`analysis/RESULTS_PACK_SELFTEST.md`) are rebuilt in place and compared with the copies in this repository. With
the versions in `requirements.txt`, they come out identical, except for the run times that the two reports
print. Everything else that the checks write goes to `reproduction/`. Every script that uses random numbers
has a fixed seed, and the header of each script names it (for example, 20260613 for the run of the analysis on
simulated data, 20260929 for the newer power simulations, 11 and 7 for the older power simulations, and
"context-fx-backbone-2026" for Survey 1).

Each part has its own command:

| To reproduce | Command | What it checks |
|---|---|---|
| every calibration result (Web Appendix F) | `python run_all.py --part calibration` | The three wave reports are rebuilt from the deposited exports and compared row by row with the original reports. The step also checks the realism comparison, the processed files, the printable views of the surveys and the design of the calibration surveys. One study alone: `python calibration/wave1/reproduce.py`, and likewise for `wave2`, `wave3` and `realism_study`. |
| the figures and the stimulus explorer | `python run_all.py --part figures` | Figure WA-F1 and Figures WA-B1 to WA-B4 are redrawn and compared pixel by pixel, and the explorer is rebuilt and compared byte by byte. The scripts also check every value, name and role in the figures against the stimulus file. |
| the plan of model calls | `python run_all.py --part models` | `models/MANIFEST.md` is recomputed from the stimulus file (1,285,630 calls). The self-test plants faults in the model settings and in the requests, and the sample prompts come from a run without the network. |
| the analysis | `python run_all.py --part analysis` | The pre-registered analysis runs on simulated data with known answers, and every simulated model must reach the conclusion that it was built to reach. The step also rebuilds the table of cutoffs, the demonstration data files and the analysis explorer, and it runs the unit tests of every rule. |
| the stimuli | `python run_all.py --part stimuli` | The stimulus file is rebuilt and checked, and the tables of Web Appendix B are rebuilt. |
| the surveys | `python run_all.py --part surveys` | The five surveys are rebuilt and compared byte by byte. The step also checks the balance of the scripts, the program that reads an export, the tables of the assignment service and the checksums of the survey package. |
| the power analyses | `python run_all.py --part power` | Every power report is rebuilt. |

You can also run each script of a part on its own, and the README of each folder lists them.
`python run_all.py --quick` skips the slowest steps. `python run_all.py --full` adds four long checks:

- how often each simulated model still reaches its intended conclusion when every model answer is a random
  draw;
- the resolution statement, the smallest true difference that each pattern test and each class boundary
  detects in 80 percent of simulated runs (Table WA-E4);
- the sample that the simulated model that matches people would need before the analysis concludes that it
  matches;
- the mutation check of the analysis, which breaks one rule at a time and requires a test to fail.

## Outputs and the code that makes them

| Output | Script | Command |
|---|---|---|
| Table 1, the replication record of the seven effects | none: a summary of the literature (sources in Web Appendix A) | |
| Figure 1, whether a decoy shifts the choices of language models as much as the choices of people | none: a drawing; its option values are the frequency-decoy set of backpacks at new values in `stimuli/stimuli.json`, and its shares are illustrative | |
| Figure 2, the pattern that each account predicts across the design | none: a drawing of the predictions in the Analysis Plan | |
| Table 2, the design: structures, tiers, formats and numbers of choices | `stimuli/build_stimuli.py`, `surveys/scriptset_sim.py`, `surveys/deal.py`, `models/build_manifest.py` | `python run_all.py --part surveys --part models` (cells and scripts in `surveys/out/*_MAPPING.json`; calls in `models/MANIFEST.md`) |
| Table 3, the ten models and how each is run | `models/run.py` (`MODEL_REGISTRY`), listed in `models/README.md` and `models/MANIFEST.md` | `python models/build_manifest.py` |
| Figure 3, does the model match people, and if not, why not | none: a drawing of the decision tree that `analysis/analyze.py` applies | |
| Table 4, the seven pre-registered scenarios | `analysis/analyze.py` (each model's conclusion in `analysis/results_pack/tree_routing.csv`) | `python analysis/analyze.py` |
| The analysis explorer (`analysis-explorer.html`) | `analysis/build_analysis_explorer.py`, from `analysis/results_pack/` | `python analysis/build_analysis_explorer.py` |
| Figure WA-A1, the seven effects as backpack choice sets | none: a drawing; its values are the backpacks stimuli in `stimuli/stimuli.json` | |
| Tables WA-B1 to WA-B15, every option of each product category | `stimuli/gen_appendix_table.py` (writes `stimuli/STIMULUS_APPENDIX.md`) | `python stimuli/gen_appendix_table.py` |
| Figures WA-B1 to WA-B4, one survey page and the three pictures categories | `figures/build_stimulus_figures.py` (writes `figures/stimulus_figures/`) | `python figures/build_stimulus_figures.py` |
| Web Appendix C, the worked walk-throughs, and the secondary comparisons of Web Appendix E | `analysis/analyze.py` | `python analysis/analyze.py` |
| Web Appendix D, the prompt wording (the three wordings of the question, the personas and the recognition question) | `models/run.py` (`REGISTERED_PROMPT_MATERIALS`, also in `models/prompt_materials.json`) | `python models/run.py --selftest` |
| Figure WA-E1, the five fidelity classes on the fidelity map | none: a drawing of the class cutoffs in `analysis/REGISTERED_CONSTANTS.md` | |
| Table WA-E1, every pre-registered cutoff | `analysis/print_constants.py` (writes `analysis/REGISTERED_CONSTANTS.md`) | `python analysis/print_constants.py` |
| Table WA-E2, the rule for first choices | `power/first_trial_rule_sim.py` (writes `power/FIRST_TRIAL_RULE_SIM.md`) | `python power/first_trial_rule_sim.py` |
| Table WA-E3, the power of the format-by-effect interaction | `power/power_format_interaction.py` (writes `power/POWER_FORMAT_INTERACTION.md`) | `python power/power_format_interaction.py` |
| Table WA-E4, the smallest difference that the design detects | `power/resolution_statement.py` (writes `power/RESOLUTION_STATEMENT.md`) | `python power/resolution_statement.py` |
| Table WA-E5, what each check and test compares and what each outcome will mean | the conclusions fixed in advance, which `analysis/analyze.py` applies | `python analysis/analyze.py` |
| The sample that the simulated model that matches people would need (Web Appendix E) | `power/faithful_resolution_by_sample.py` (writes `power/FAITHFUL_RESOLUTION_BY_SAMPLE.md`) | `python power/faithful_resolution_by_sample.py` |
| Power figures in the Method | `power/power_sim.py`, `power/clustered_power.py`, `power/power_added_cells.py`, `power/power_compromise_pooled.py` | `python run_all.py --part power` |
| Table WA-F1, the four calibration studies | the README of each study in `calibration/` (records of the studies, not computed) | |
| Tables WA-F2 and WA-F3, wave 1 | `calibration/calibration_analysis.py` | `python run_all.py --part calibration` |
| Table WA-F4, wave 2 | `calibration/calibration_analysis.py` | as above |
| Table WA-F5, wave 3 | `calibration/calibration_analysis.py` | as above |
| Figure WA-F1, the three calibration waves | `figures/build_figure_waf1.py` | `python figures/build_figure_waf1.py` |
| Table WA-F6, the final status of the 25 pairs | `calibration/FINAL_LOCK_LIST_2026-07-02.json`, which `stimuli/build_stimuli.py` applies and checks | `python stimuli/build_stimuli.py` |
| Table WA-F7, the comprehension checks | `calibration/calibration_analysis.py` | `python run_all.py --part calibration` |
| The realism comparison (Web Appendix F) | `calibration/anchor_analysis.py` | `python calibration/anchor_analysis.py` |

## The model responses at Stage 2

At the provider's default temperature, each model call is one draw from the model's distribution of answers. In
the confirmatory condition, we therefore send every text prompt 10 times and every picture prompt 60 times. We
log every call with these fields (`analysis/DATA_DICTIONARY.md`, part B):

- the full prompt and the model's reply, unchanged;
- the model id that we requested and the id that the provider returned;
- the number of the draw;
- the sampling and reasoning settings that the provider applied;
- whether a choice could be read from the reply;
- the time of the call.

At Stage 2, we will deposit the log of every call, together with the confirmatory human exports and the results
files. Anyone can then reproduce the analysis exactly from the deposited log:

```
python analysis/analyze.py --human human_long.csv --model model_log.jsonl
```

A new run of the model calls reproduces the results only approximately. A proprietary model can answer the same
prompt differently on different days, and providers update and retire their models. We fixed a rule in advance
for a new run with the same model ids and settings: the new run reproduces a model effect when the deposited
estimate lies inside the new run's 95 percent bootstrap interval over calls. The interval is computed by
`analysis/call_bootstrap.py`, the rule is in `analysis/registered_constants.py`, and `analysis/test_analysis.py`
tests it. A model that providers no longer offer cannot be run again, and its results can then be checked only
from the deposited log.

## What is pre-registered and what is not

- **Pre-registered (confirmatory):** the stimuli and their final values; the five surveys; the exclusion rules
  (`surveys/SURVEY_SPEC.md`); the ten models and their conditions, with the pre-registered prompt wording; and
  the analysis in `analysis/analyze.py`, with every cutoff in `analysis/registered_constants.py`
  (`analysis/REGISTERED_CONSTANTS.md` prints them), as the Analysis Plan of the manuscript describes. Only the
  calls of the neutral condition enter the confirmatory model estimates.
- **Not confirmatory:** everything in `calibration/`. We used the pre-test to set the stimulus values before
  registration, and its data never enter a confirmatory analysis. We added two parts during the pre-test, the
  realism comparison study and the comprehension question about the pictures, and both are descriptive. Six
  pairs that failed the calibration rule stay in the design. We decided to keep five of them after seeing the
  wave-3 data, and we kept the sixth, the electric kettles, because we read them as final at the time
  (`calibration/CALIBRATION_DESIGN.md`, last section).
- **Descriptive by design:** the human effects estimated in a single product category; the compromise cells whose
  target starts at a share of 50 percent or more (for the simulated data,
  `analysis/results_pack/descriptive_slices.csv` lists them); and the bootstrap interval beside every model effect.
- **Simulated:** everything in `analysis/results_pack/` comes from the run on simulated data, not from real
  data.

## Things to know

- We wrote the original reports in `calibration/*/results/` on July 2, 2026, with the same analysis code, from
  the original exports. We kept them exactly as written. The wave-3 report names the final calibration values
  by a short working label.
- There are two stimulus files. `stimuli/stimuli.json` holds the final values. We built the calibration surveys
  from the file as it stood before the final values were fixed, and `stimuli/stimuli_prelock.json` keeps that
  version. The calibration analysis reads it.
- Nobody can launch the confirmatory surveys as deposited. Their consent text and completion code are
  placeholders, which we replace only at launch, and `surveys/validate_qsf.py` refuses the files until then.
- A small web service (`surveys/assign_worker/`) assigns scripts in the words, pictures and price-free surveys.
  In the deposited survey files, its address is a placeholder (`https://STUDY-ASSIGNMENT-SERVICE.example/assign`).
  A preview of those three surveys therefore stops at the page that a participant sees when the service does not
  answer, and their choice pages are in the screens document. To run these surveys, set up the service and enter
  its address in the survey's Web Service element.
- From this repository, a reader cannot rerun the Prolific and Qualtrics studies, which need accounts on both
  platforms, or make the live model calls, which need API keys. The model program has a mode without the network,
  which runs the whole loop of calls on made-up replies.
- One input is a stored result, not a computed one. `power/pattern_test_resolution.json` holds the rows of
  Table WA-E4 for the pattern tests T1, T3, T4 and T5. They come from a simulation of the design that we ran
  before registration. That simulation also compared other designs, and it is not part of this release. The
  file says how we made it, and `power/resolution_statement.py` computes every other row of the table.

## Tested from a fresh copy

Before deposit, we copied the built repository to an empty folder and made a new virtual environment there from
`requirements.txt` alone. From the copy, we ran `python run_all.py`, each `--part` command, `--quick`, the four
`calibration/<study>/reproduce.py` scripts and the self-test of `figures/build_stimulus_figures.py`. We then
compared every deposited file in the copy with the original. All were identical except the lines with run times
in `analysis/results_pack/RUN_REPORT.md` and `analysis/RESULTS_PACK_SELFTEST.md`, and the only new files were in
`reproduction/` and in Python's own `__pycache__/` folders. The three long simulations of `--full` ran when we
built the repository, and their outputs are the deposited files in `power/`.
