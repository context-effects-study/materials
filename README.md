# Do Large Language Models Reproduce Human Context Effects in Consumer Choice? Data and code

Data, materials and code of a Registered Report at the *Journal of Consumer Research* (Stage 1). The study
asks whether, and under what conditions, large language models reproduce the classic context effects of
human choice (attraction with frequency, range and phantom decoys, compromise, extremity, upscaling and
similarity) when they answer the same product-choice questions as people.

## What the Stage 1 guidelines ask for, and where it is

The journal's Registered Report guidelines ask the Stage 1 repository to hold all implementation materials.
Each item, and the file or folder that holds it:

| Item | Where |
|---|---|
| Survey and experiment stimuli | `stimuli/stimuli.json` (all 165 stimuli), `stimulus-explorer.html` (every stimulus as shown to people and to models), `surveys/out/` and `survey_package/` (the five confirmatory surveys), `surveys/png/` (the pictures), `models/prompt_materials.json` (the model prompts) |
| Data dictionary | `analysis/DATA_DICTIONARY.md` (the confirmatory human table, the model call log and the results pack); `calibration/<study>/codebook_*.csv` (every calibration data file) |
| Research assistant instructions | `docs/ADMINISTRATION.md` (fielding each survey on Prolific and Qualtrics, step by step) |
| Implementation plans | `docs/HUMAN_PROTOCOL.md` (recruitment, assignment, top-up, exclusions), `surveys/SURVEY_SPEC.md` (the exclusion rules), `models/README.md` and `models/MANIFEST.md` (the model conditions and the exact call plan) |
| Decision trees | `figures/figure1.png` (Figure 1), implemented in `analysis/analyze.py`, with every cutoff in `analysis/REGISTERED_CONSTANTS.md` |
| Power analysis | `power/` (every power figure in the Method and Web Appendix E, each with its script, and for the pattern tests the resolution statement, the pattern-test counterpart of power) |
| Data analysis code | `analysis/` (the registered analysis, its tests and mutation check), `calibration/` (the pre-test analyses) |
| Simulated data | `analysis/demo_data/` (the dress rehearsal's synthetic data in the registered formats) and `analysis/results_pack/` (the analysis run on them) |

This copy is shared for masked review through an anonymized GitHub repository. At in-principle
acceptance the same file list goes to a public archive with a DOI, and at Stage 2 a new version of that
record adds the confirmatory data.

## About this release

This is the Stage 1 release. It holds everything needed to check and rerun the plan: the stimuli and the
code that builds and checks them; the completed stimulus calibration pre-test (four studies, with
de-identified data, codebooks, surveys and analysis code); the five confirmatory surveys, ready to import;
the model runner and its exact call plan; the registered analysis, rehearsed end to end on synthetic data and
covered by tests; the power analyses; and every figure with the script that draws it. No confirmatory data
have been collected. At Stage 2 the confirmatory human data, the complete model call log and the results pack
will be added to a new version of this release.

## Start here

- `stimulus-explorer.html` opens in any web browser, offline, and shows all 165 stimuli. You can filter by
  product category, effect, tier and format, see each choice set as a participant sees it with every
  option's role named, and read the exact text each model receives.
- `survey_package/` holds the five confirmatory Qualtrics surveys ready to import into your own Qualtrics
  account, with a walkthrough of every screen (`SURVEY_WALKTHROUGH.pdf`) and instructions.
- `python run_all.py` regenerates every reproducible output and checks each against the copy deposited here
  (see "Instructions").

## Overview

| Folder or file | What is inside | Manuscript |
|---|---|---|
| `stimulus-explorer.html` | All 165 stimuli as participants and models see them (offline, one file) | Method; Web Appendix B |
| `calibration/` | The calibration pre-test: its design and dated amendments, and one folder per study (waves 1, 2, 3 and the realism comparison study), each with the survey as fielded and a printable PDF view of it, the de-identified export (every row, exclusions applied in code), processed files with exclusion flags, codebooks, a script that reproduces the study's reported numbers, the report of record and a short report | Method (calibration); Web Appendix F |
| `stimuli/` | The single stimulus file (165 stimuli), the code that builds and checks it, and the source of every published value | Method; Table 2; Web Appendix B |
| `surveys/` | The five confirmatory Qualtrics surveys, their generators and design keys, the participant scripts, a screenshot walkthrough, and the assignment service used by three surveys | Method, Human study; Table 2 |
| `survey_package/` | The same five surveys and design keys, with the walkthrough and the pictures, ready to import | Method, Human study |
| `models/` | The model runner, the ten-model lineup, the registered prompt wording, and the exact call plan (1,285,630 calls) | Method, Model study; Table 2; Table 3; Web Appendix D |
| `analysis/` | The registered analysis, its table of every cutoff, the export reader, the data dictionary, the dress rehearsal with its synthetic data and results pack, the tests and the mutation check | Analysis Plan; Table 4; Web Appendices C and E |
| `power/` | The power analyses and simulations | Method, power; Web Appendix E |
| `figures/` | Figures 1 and 2, Figure WA-F1 and the Web Appendix B stimulus figures, each with the script that draws it | Figures 1 and 2; Web Appendices B and F |
| `docs/` | The human study protocol and the step-by-step instructions for fielding the surveys | Method, Human study |
| `run_all.py` | Regenerates every reproducible output and checks it against the deposited copy | all of the above |

## Data availability and sources

**The calibration pre-test data (collected by the authors).** Four online studies ran on July 2, 2026,
recruited and paid through Prolific, with the surveys hosted on Qualtrics: calibration waves 1, 2 and 3 (400,
312 and 462 approved participants) and a realism comparison study (112), 1,286 approved participants in all,
at a cost of $1,571.93 including platform fees. Participants were adults resident in the US or UK, fluent in
English, taking part on a desktop computer; each gave consent on the first page of the survey (the consent
text is in each survey file). Each study's README gives its dates, pay, screening and the exact
reconciliation of export rows against approved submissions.

The files in `calibration/*/data/raw/` are the complete Qualtrics exports (CSV with labels, and JSON with
numeric codes), de-identified before deposit: the Prolific participant id is replaced by a sequential id in
order of first appearance (W1-0001, W2-0001, W3-0001, RS-0001 and so on), whose key is kept by the authors;
the Prolific study and submission ids, IP address, location and browser fields are blank. Everything else,
including age, gender, timings and the free-text comments (read in full before deposit; none identifies
anyone), is as exported. The analysis never uses the removed fields, and every report of record reproduces
from these files (`run_all.py`). The original exports, which contain Prolific ids, are kept by the authors and
are not shared, to protect participants; for verification of a specific result they can be examined with the
authors on request, subject to the terms under which the data were collected. Engineering test rows written
before each launch are kept in the exports, marked by their participant id (STRESS_ prefix), and removed by
the analysis.

**Stimulus values from published studies.** The tier-1 stimuli use the exact attribute values of the
published studies each effect comes from. Every value is listed with its source (authors, year, journal,
DOI) in `stimuli/fragments/<category>_receipts.md`.

**Confirmatory human and model data.** Not yet collected (Stage 1). See "The model responses at Stage 2".

**Licence.** Code under the MIT License; data and all other materials under CC BY 4.0 (`LICENSE`).

| Data file | Source | Provided | Licence |
|---|---|---|---|
| `calibration/wave1/data/raw/calibration_wave1_export.{csv,json}` | the authors, Prolific and Qualtrics, July 2, 2026 | yes, de-identified | CC BY 4.0 |
| `calibration/wave2/data/raw/calibration_wave2_export.{csv,json}` | as above | yes, de-identified | CC BY 4.0 |
| `calibration/wave3/data/raw/calibration_wave3_export.{csv,json}` | as above | yes, de-identified | CC BY 4.0 |
| `calibration/realism_study/data/raw/realism_export.{csv,json}` | as above | yes, de-identified | CC BY 4.0 |
| `calibration/*/data/processed/*.csv` | written by `calibration/make_choice_files.py` from the files above | yes | CC BY 4.0 |
| tier-1 values in `stimuli/fragments/` | published studies, cited in the receipts files | yes | the facts belong to their sources |

Every data file has a codebook: `calibration/<study>/codebook_*.csv` (variable, type, values, units,
meaning; the export codebook also gives each column's key in the JSON export), and
`analysis/DATA_DICTIONARY.md` for the confirmatory formats (the human long table, the model call log and the
results pack).

## Computational requirements

- **Software.** Python 3.13 (tested with 3.13.13, 64-bit). Everything except the figures and one power
  simulation runs on the Python standard library alone. `requirements.txt` pins, at the tested versions, the
  four packages the rest needs and the packages they install: numpy (`power/clustered_power.py`), matplotlib (Figure WA-F1), and Playwright with Pillow (Figures 1
  and 2, the stimulus figures and the explorer's checks); after installing, run
  `python -m playwright install chromium` once. Live model calls at Stage 2 also need the providers' API keys;
  they are not needed to reproduce anything here.
- **Tested on.** Windows 11 (64-bit), in a fresh virtual environment made from `requirements.txt` alone
  (the record of that test is summarized at the end of this file).
- **Hardware.** An ordinary desktop or laptop, no GPU, and about 200 MB of free disk for the repository and
  the files `run_all.py` writes. No network access is needed, except once to download the packages and the
  browser.
- **Runtime.** About 7 minutes for `python run_all.py` on the test machine: the clustered power simulation
  takes about 2 minutes, the model runner's self-tests and the analysis dress rehearsal between 1 and 2
  minutes each, and every other step seconds. `python run_all.py --quick` takes about 4 minutes. `--full`
  adds four long checks, about 80 minutes in all: the routing-stability simulation (about 17 minutes), the
  resolution statement (about 40), the faithful profile at larger samples (about 8) and the mutation check
  (about 15 to 20).

## Instructions

From the repository root:

```
python -m venv .venv
.venv\Scripts\activate          (Windows)   or   source .venv/bin/activate   (macOS, Linux)
pip install -r requirements.txt
python -m playwright install chromium
python run_all.py
```

`run_all.py` runs every step below in order. After each step it compares what was written with the
deposited copy (images pixel for pixel) and prints a summary; it exits with an error if any step does not
reproduce. The calibration reports are written to `reproduction/` and compared row by row with the reports of
record in `calibration/*/results/`, which differ from a new run only in their first line (the name of the
input file), one column title, and the working label of the final calibration lock. Everything the checks
write goes to `reproduction/`; the deposited folders are left as they were. Every script that uses random
numbers has a fixed seed, named in its header (for example 20260613 for the rehearsal, 20260929 for the
newer power simulations, 11 and 7 for the older ones, "context-fx-backbone-2026" for the backbone survey).

One command for each part:

| To reproduce | Command | What it checks |
|---|---|---|
| every calibration result (Web Appendix F) | `python run_all.py --part calibration` | the three wave reports rebuilt from the deposited exports, row by row against the reports of record; the realism comparison; the processed files; the printable survey views; the calibration surveys' design (one study alone: `python calibration/wave1/reproduce.py`, and likewise for `wave2`, `wave3`, `realism_study`) |
| the stimulus figures and the explorer | `python run_all.py --part figures` | Figures 1, 2 and WA-F1 and every Web Appendix B figure redrawn pixel for pixel, and the explorer rebuilt byte for byte, with the builders' own checks against the stimulus file |
| the call plan | `python run_all.py --part models` | `models/MANIFEST.md` recomputed from the stimulus file (1,285,630 calls), the runner's registry and requests checked with planted faults, the sample prompts from a dry run |
| the analysis rehearsal | `python run_all.py --part analysis` | the registered analysis on synthetic data with planted answers (every profile must route to its scenario), the table of cutoffs, the demonstration data files, and the tests of every rule |
| the stimuli | `python run_all.py --part stimuli` | the stimulus file rebuilt and validated, and the Web Appendix B tables |
| the surveys | `python run_all.py --part surveys` | the five surveys regenerated byte for byte, the script balance, the export reader, the assignment service's tables, the survey package's checksums |
| the power analyses | `python run_all.py --part power` | every power report regenerated |

Each part's scripts can also be run on their own; the README in each folder lists them.
`python run_all.py --quick` skips the slowest steps. `python run_all.py --full` adds four long checks: the
routing stability of the planted model profiles under the sampling noise of the repeated draws, the
resolution statement (the smallest true difference each pattern test and class boundary resolves in 80
percent of runs, Table WA-E4), the sample the planted faithful profile would need to be resolved, and the
mutation check of the analysis, which breaks one rule at a time and requires a test to catch it.

## Outputs and the code that makes them

| Output | Script | Command |
|---|---|---|
| Table 1, the replication record of the seven effects | none: a synthesis of the literature (sources in Web Appendix A) | |
| Table 2, the design: structures, tiers, formats and choice counts | `stimuli/build_stimuli.py`, `surveys/scriptset_sim.py`, `surveys/deal.py`, `models/build_manifest.py` | `python run_all.py --part surveys --part models` (cells and scripts in `surveys/out/*_MAPPING.json`; calls in `models/MANIFEST.md`) |
| Table 3, the ten models and how each is run | `models/run.py` (`MODEL_REGISTRY`), listed in `models/README.md` and `models/MANIFEST.md` | `python models/build_manifest.py` |
| Figure 1, the decision tree | `figures/build_figure1.py` | `python figures/build_figure1.py` |
| Figure 2, one choice set in three formats | `figures/build_figure2.py` | `python figures/build_figure2.py` |
| Table 4, the seven named scenarios | `analysis/analyze.py` (routing in `analysis/results_pack/tree_routing.csv`) | `python analysis/analyze.py` |
| Power figures in the Method | `power/power_sim.py`, `power/clustered_power.py`, `power/power_added_cells.py` | `python run_all.py --part power` |
| Web Appendix B, the stimulus tables and figures | `stimuli/gen_appendix_table.py` (`stimuli/STIMULUS_APPENDIX.md`), `figures/build_stimulus_figures.py` (`figures/stimulus_figures/`) | `python stimuli/gen_appendix_table.py`; `python figures/build_stimulus_figures.py` |
| Web Appendices C and E, the walk-throughs and secondary readings | `analysis/analyze.py` | `python analysis/analyze.py` |
| Web Appendix D, the prompt wording (paraphrases, personas, probe) | `models/run.py` (`REGISTERED_PROMPT_MATERIALS`, also in `models/prompt_materials.json`) | `python models/run.py --selftest` |
| Table WA-E1, every registered cutoff | `analysis/print_constants.py` (`analysis/REGISTERED_CONSTANTS.md`) | `python analysis/print_constants.py` |
| Table WA-E2, the first-choice rule | `power/first_trial_rule_sim.py` (`power/FIRST_TRIAL_RULE_SIM.md`) | `python power/first_trial_rule_sim.py` |
| Table WA-E3, the format interaction | `power/power_format_interaction.py` (`power/POWER_FORMAT_INTERACTION.md`) | `python power/power_format_interaction.py` |
| Table WA-E4, the smallest difference the design resolves | `power/resolution_statement.py` (`power/RESOLUTION_STATEMENT.md`) | `python power/resolution_statement.py` |
| The faithful profile at larger samples (Web Appendix E) | `power/faithful_resolution_by_sample.py` (`power/FAITHFUL_RESOLUTION_BY_SAMPLE.md`) | `python power/faithful_resolution_by_sample.py` |
| Table WA-F1, the four calibration studies | the study READMEs in `calibration/` (records, not computed) | |
| Tables WA-F2 and WA-F3, wave 1 | `calibration/calibration_analysis.py` | `python run_all.py --part calibration` |
| Table WA-F4, wave 2 | `calibration/calibration_analysis.py` | as above |
| Table WA-F5, wave 3 | `calibration/calibration_analysis.py` | as above |
| Figure WA-F1, the three calibration waves | `figures/build_figure_waf1.py` | `python figures/build_figure_waf1.py` |
| Table WA-F6, the final status of the 25 pairs | `calibration/FINAL_LOCK_LIST_2026-07-02.json`, applied and checked by `stimuli/build_stimuli.py` | `python stimuli/build_stimuli.py` |
| Table WA-F7, the comprehension checks | `calibration/calibration_analysis.py` | `python run_all.py --part calibration` |
| The realism comparison (Web Appendix F) | `calibration/anchor_analysis.py` | `python calibration/anchor_analysis.py` |

## The model responses at Stage 2

At the provider's default temperature each model call is one draw from the model's distribution of answers,
so in the confirmatory condition every prompt is sent 10 times and every picture prompt 60 times. Every call
is logged with the full prompt, the raw reply, the model id requested and the id the provider returned, the
draw number, the sampling and reasoning settings actually applied, the parse result and a timestamp
(`analysis/DATA_DICTIONARY.md`, part B). At Stage 2 the complete log of every call will be deposited with the
data, together with the confirmatory human exports and the results pack. The analysis reproduces exactly from
the deposited log:

```
python analysis/analyze.py --human human_long.csv --model model_log.jsonl
```

Re-running the model calls themselves reproduces the results only approximately. Proprietary models can
answer an identical prompt differently on different days, and providers update or retire models. The
registered rule for a re-run, with the same model ids and settings: a re-run reproduces a model effect when
the deposited estimate lies inside the re-run's 95 percent bootstrap interval over calls
(`analysis/call_bootstrap.py`; the rule is in `analysis/registered_constants.py` and is tested in
`analysis/test_analysis.py`). A model that is no longer offered cannot be re-run; its results then rest on the
deposited log.

## What is registered and what is not

- **Registered (confirmatory):** the stimuli and their final values, the five surveys, the exclusion rules
  (`surveys/SURVEY_SPEC.md`), the model lineup and conditions with the registered prompt wording, and the
  analysis in `analysis/analyze.py` with every cutoff in `analysis/registered_constants.py`
  (`analysis/REGISTERED_CONSTANTS.md` prints them), as described in the manuscript's Analysis Plan. Only the
  neutral condition's calls enter the confirmatory model estimates.
- **Not confirmatory:** everything in `calibration/`. The pre-test set stimulus values before registration;
  its data never enter a confirmatory analysis. Within it, the realism comparison study and the picture
  comprehension item were added during the pre-test and are descriptive, and the routing of the pairs kept
  with a documented deviation was decided after the wave-3 data (`calibration/CALIBRATION_DESIGN.md`, last
  section).
- **Descriptive by design:** per-category human results, the compromise cells whose target starts at or above
  50 percent (listed in `analysis/results_pack/descriptive_slices.csv` for the rehearsal), and the bootstrap
  interval beside every model effect.
- **Synthetic:** everything in `analysis/results_pack/` comes from the dress rehearsal, not from data.

## Things to know

- The reports of record in `calibration/*/results/` were written on July 2, 2026 by the same analysis code
  from the original exports. They are kept exactly as written; the wave-3 report refers to the final
  calibration lock by a short working label.
- There are two stimulus files. `stimuli/stimuli.json` holds the final values. The calibration surveys were
  built from the file as it stood before the final lock, kept as `stimuli/stimuli_prelock.json`, and the
  calibration analysis reads that file.
- The confirmatory surveys cannot be launched as deposited. They carry placeholder consent text and a
  placeholder completion code, replaced only at launch, and `surveys/validate_qsf.py` refuses them until then.
- The assignment service (`surveys/assign_worker/`) deals scripts to the words, pictures and price-free
  surveys. In the deposited survey files its address is a placeholder
  (`https://STUDY-ASSIGNMENT-SERVICE.example/assign`), so a preview of those three surveys stops at the page
  shown when the service does not answer; their choice pages are in the walkthrough. To field them, deploy the
  service and point the surveys' Web Service element at it.
- The Prolific and Qualtrics studies themselves and the live model calls cannot be rerun from here, because
  they need accounts and API keys. The runner's dry run exercises the whole call loop without the network.
- One input is recorded rather than recomputed: `power/pattern_test_resolution.json` holds the pattern-test
  rows (T1, T3, T4, T5) of Table WA-E4, from a simulation of the design run before registration that also
  compared alternative designs and is not part of this release. The file says how it was made.
  `power/resolution_statement.py` recomputes every other row of the table.

## Tested from a fresh copy

Before deposit, this repository was copied to an empty folder, a new virtual environment was made there
from `requirements.txt` alone, and `python run_all.py --full`, each `--part` command, `--quick` and the four
`calibration/<study>/reproduce.py` scripts ran from the copy. Afterwards every deposited file in the copy was
compared with the original: all were identical except the runtime lines of
`analysis/results_pack/RUN_REPORT.md` and `analysis/RESULTS_PACK_SELFTEST.md`, and the only new files were
under `reproduction/` and Python's own `__pycache__/` folders.
