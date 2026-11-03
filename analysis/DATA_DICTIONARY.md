# Data dictionary of the confirmatory study

The confirmatory study uses three data formats. `ingest.py` writes the human data (A) from a Qualtrics export,
with one row per choice. `../models/run.py` writes the model call log (B), with one record per call.
`analyze.py` reads A and B and writes the results files (C). The script that writes the simulated data
(`synth.py`) uses exactly the formats A and B. The data files of the calibration pre-test have their own
codebooks, in `../calibration/<study>/`.

## A. The human data (one row per choice)

| Column | Type | Values and meaning |
|---|---|---|
| `participant_id` | text | a one-way hash of the Prolific id ("P" followed by 15 hexadecimal characters) |
| `script_id` | text | the pre-built script that the participant received |
| `trial_position` | integer | the position of the choice in the script: 1 to 7 in the core-design and similarity surveys, 1 to 3 in the format and price-free surveys. Position 1 is the participant's first choice, which forms the sample of first choices |
| `cell_id` | text | the design cell, written as `<category>_<structure>` |
| `category` | category | the product category |
| `structure` | category | BIN, FRQ, RNG, PHT, SOT, MOT, EXC, SYM or SIM (the codebook below defines each) |
| `tier` | integer | the stimulus tier: 1, published values; 2, new values in a published category; 3, a new category that no published study of context effects used |
| `format` | category | numbers, words or pictures |
| `position_order` | text | the codes of the options in the order shown |
| `stimulus_id` | text | the stimulus in `../stimuli/stimuli.json`. For the two pictures pairs that have their own calibrated values, the values are under `format_variants.pictures.options` |
| `sim_placement` | category | in similarity cells, the focal option that the near-copy copies; NA in other cells |
| `choice` | category | the option chosen, decoded with the codebook below |
| `chose_target` | 0 or 1 | 1 when the participant chose the target (BIN, SOT, FRQ, RNG, PHT, SIM) |
| `chose_ext` | 0 or 1 | 1 when the participant chose the new extreme option (SOT) |
| `chose_hd` | 0 or 1 | 1 when the participant chose the premium option (SYM). It can be computed for any cell from `is_hd` in the stimulus file |
| `chose_clone` | 0 or 1 | 1 when the participant chose the near-copy (SIM) |
| `chose_extreme_tier` | 0 or 1 | 1 when the participant chose an option in the high or the low quality tier, and 0 for the middle tier (MOT and EXC). The extremity effect is the mean of this column in MOT minus its mean in EXC |
| `rt_page_sec` | seconds | the time from the loading of the choice page to the submission of the choice |
| `completed_all` | 0 or 1 | 1 when the participant completed every choice of the script |
| `consent`, `age`, `gender`, `device` | as exported | the answer to the consent question, the age in years and the gender that the participant reported, and the device, where Qualtrics recorded it |
| `qsf_sha256`, `export_ts` | text | the SHA-256 hash of the survey file and the time of the export, which tie the table to its sources |

**The codebook of each structure.**

| Structure | Decoded values | Notes |
|---|---|---|
| BIN (the two-option set) | TARGET, COMP | The two focal options. TARGET is the category's compromise target, the option that starts behind its rival in the calibrated two-option set, and COMP is its rival. The stimulus file records which option is the premium option (`is_hd`) |
| SOT (compromise) | TARGET, COMP, EXT | The two options of the BIN set plus one new extreme option beyond the target, so that the target becomes the middle option. The effect is the relative share TARGET / (TARGET + COMP) in SOT minus the same share in the matched BIN set. A choice of EXT is valid and recorded, but it does not enter the relative share. The design never adds a separate middle option |
| FRQ, RNG (frequency and range decoys) | TARGET, COMP, DECOY | TARGET is the option that is better than the decoy |
| PHT (phantom) | TARGET, COMP | The phantom is better than the target on exactly one attribute and is marked unavailable. A participant cannot choose it; a choice of it would be an exclusion, never a share |
| SYM (upscaling) | HD, HF, DECOY | The symmetric decoy is worse than both focal options. The upscaling effect is measured on the share of the premium option (HD) |
| SIM (similarity) | TARGET, COMP, CLONE | CLONE is the near-copy of one focal option. The similarity effect is the relative share of the option that was not copied, against its rival, minus the same share in the matched BIN set |
| MOT (the extremity menu) | T1S1 to T3S4 | The 12 options of the menu, coded by quality tier and slot. Here "T" is the quality tier inside the menu, not the stimulus tier. The analysis reads MOT through `chose_extreme_tier` |
| EXC (the extremity control) | EXC_H, EXC_M, EXC_L | One option at each of the three quality tiers of the matched MOT menu, at the center of each tier, so that the two menus differ only in how many options each tier holds |

**The shared control.** Within each category and stimulus tier, one BIN cell is the control for six tests:
compromise, the frequency decoy, the range decoy, the phantom, upscaling and similarity. The seventh test,
extremity, compares the MOT menu with its matched EXC control. Because the six tests share a control, we
correct for multiple testing with the Holm procedure, which is valid under any dependence among the tests.

**Checks.** `ingest.py` checks three things: no participant sees a product category twice; every choice
decodes to a valid value for its structure (a choice of the phantom is recorded as an exclusion); and every
cell exists in the stimulus file.

## B. The model call log (one JSON record per call)

| Field | Meaning |
|---|---|
| `record_id` | a hash of the run, the model, the stimulus, the condition and the draw, so that an interrupted run can resume without repeating a call |
| `draw_index` | the number of the repeated call of the same prompt: 0 to 9 for a text prompt in the neutral condition, 0 to 59 for a picture prompt in the neutral condition, 0 to 4 (text) or 0 to 29 (pictures) for the high reasoning setting of the reasoning comparison, and 0 in the persona, temperature, sequential and recognition conditions |
| `run_id` | the run of data collection |
| `model_key` | the model's entry in `MODEL_REGISTRY` (for example `openai_flagship`) |
| `model_id_requested`, `model_id_echoed` | the model id sent and the model id that the provider returned; the log flags a difference between them |
| `provider`, `api_flavor` | where the call went, and the request format |
| `prompting_mode` | neutral, persona, sequential or recognition |
| `persona_id` | the persona, in the persona condition |
| `paraphrase_id` | which of the three pre-registered wordings of the question the prompt used |
| `arm` | the condition: primary (the neutral condition, which is confirmatory), reasoning_on, temp_0, temp_1, persona, sequential or recognition |
| `reasoning_mode`, `reasoning_requested`, `reasoning_effective` | the reasoning setting pre-registered for the condition (off, lowest, on, always on, or not applicable), the setting sent, and the setting that the provider reports having applied |
| `temperature_requested`, `sampling_params_effective` | the temperature sent (empty when the provider's default is used), and the sampling settings that the provider applied or its message when it rejected them |
| `image_ref`, `image_sha256`, `image_source_svg_sha256` | for picture prompts: the picture file sent, its hash, and the hash of the SVG file from which it was drawn |
| `cell_id`, `category`, `structure`, `tier`, `format`, `position_order`, `stimulus_id` | the design cell and the stimulus, as in part A |
| `placement` | in similarity cells, the focal option that the near-copy copies (clone_HF or clone_HD), as `sim_placement` in part A |
| `shown_codes` | the codes of the options in the order shown |
| `session_id`, `seq_index` | in the sequential condition, the conversation and the position of the choice in it |
| `prompt_text` | the full prompt sent |
| `raw_response` | the model's reply, unchanged |
| `parsed_choice`, `parse_method` | the option read from the reply, and how it was read (an exact match, a fallback pattern, or a failure; `dry_run` in a run without the network) |
| `exclusion_flag`, `exclusion_reason` | whether the call is excluded, and why: a refusal, a reply from which no choice can be read, a timeout, or a model id that differs from the one requested |
| `latency_ms`, `cost_usd`, `timestamp` | the time that the call took, its cost, and the time of the call (UTC) |
| `family`, `generation`, `model_slot`, `model_tier` | the developer, the generation (older or current), the slot in the lineup and the tier of the model, which the trajectory test (T5) uses |
| `model_substituted_from` | empty, or the model first registered for the slot, with the reason, the date and the rule of the substitution |

**Checks.** Every `record_id` is unique, and every combination of model, stimulus, condition and draw in the plan
appears exactly once.

## C. The results files (`results_pack/`)

The analysis writes to this folder every number that the Stage 2 report will cite, and the report will take each
number from its key in `numbers.json`, never from a number typed by hand. The table lists the files that
`analyze.py` writes, with their sizes in the run on simulated data:

| File | Rows | Columns or keys | What it holds |
|---|---|---|---|
| `RUN_REPORT.md` |  | text | seed, software versions, runtime and exclusion accounting of the run |
| `agreement_scores.csv` | 15 | `model`, `class`, `effects_classed`, `sign_agreement`, `mad_pp`, `calibration_slope`, `cells_scored`, `cells_excluded` | per model: sign agreement, mean absolute deviation (points), calibration slope, fidelity class, cells scored and excluded |
| `category_map.csv` | 1865 | `model`, `effect`, `category`, `tier`, `format`, `human_pp`, `human_ci_lo_pp`, `human_ci_hi_pp`, `model_pp`, `n_calls`, `boot_lo_pp`, `boot_hi_pp`, `class`, `class_basis` | per model, effect, category, tier and format: the human effect with its interval, the model effect with the number of calls and the bootstrap interval over calls, and the class (descriptive: one category, tier and format) |
| `descriptive_slices.csv` | 117 | `source`, `category`, `tier`, `format`, `effect_pp`, `ci_lo_pp`, `ci_hi_pp`, `boot_lo_pp`, `boot_hi_pp`, `n`, `baseline_target_pct`, `reason` | compromise cells whose target starts ahead: held out of the pooled compromise contrast and reported as descriptive |
| `effect_classes.csv` | 98 | `model`, `effect`, `human_gate`, `human_pp`, `model_pp`, `deviation_pp`, `n_calls`, `boot_lo_pp`, `boot_hi_pp`, `max_draws_per_grid_point`, `class`, `descriptive_class`, `prompt_sensitive`, `paraphrase_pp`, `over_reading`, `class_basis` | per model and effect: the pooled human and model effects, their deviation, the calls behind the model effect and its bootstrap interval, the fidelity class and the basis of the class |
| `fidelity_map.csv` | 294 | `model`, `structure`, `tier`, `format`, `human_pp`, `model_pp`, `deviation_pp`, `n_calls`, `boot_lo_pp`, `boot_hi_pp`, `max_draws_per_grid_point`, `ceiling_flag`, `class`, `class_basis` | per model, effect, category, tier and format: the human effect with its interval, the model effect (a population share over the enumerated conditions, no interval), their distance, and the ceiling flag |
| `human_benchmarks.csv` | 164 | `effect`, `category`, `tier`, `format`, `effect_pp`, `ci_lo_pp`, `ci_hi_pp`, `n`, `n_clusters`, `first_trial_pp`, `bf10` | per effect, category, tier and format: the human effect, its interval, n and the first-choice estimate |
| `no_human_counterpart.csv` | 1 | `model`, `effect`, `tier`, `format`, `model_pp`, `human_pp`, `n_calls`, `boot_lo_pp`, `boot_hi_pp`, `human_gate` | model effects on cells whose human effect did not replicate: reported, not scored |
| `no_room_cells.csv` | 66 | `model`, `level`, `category`, `tier`, `format`, `effect` | cells a model could not be scored on because its two-option share leaves no room to move |
| `numbers.json` |  | top-level keys: `design.compromise_descriptive_slices`, `design.compromise_flag_mismatch`, `design.deviation_flag_mismatch`, `design.deviation_slices`, `design.source`, `human.FRQ.criterion.bf10`, `human.FRQ.criterion.confirmatory`, `human.FRQ.criterion.holm_family`, `human.FRQ.criterion.holm_p`, `human.FRQ.criterion.replicated`, `human.FRQ.criterion.right_direction`, `human.FRQ.decoy_target.hd_minus_hf_pp`, ... | every statistic the results cite, under stable dotted keys |
| `price_free_arm.csv` | 0 | `source`, `effect`, `effect_pp`, `ci_lo_pp`, `ci_hi_pp`, `boot_lo_pp`, `boot_hi_pp`, `n` | the price-free robustness test of the attraction effects |
| `secondary_contrasts.csv` | 1 | `contrast`, `frequency_pp`, `range_pp`, `contrast_pp`, `reading` | the registered secondary contrasts (for example the range effect minus the frequency effect) |
| `sensitivity_deviation_human.csv` | 7 | `effect`, `primary_pp`, `sensitivity_pp`, `primary_replicated`, `sensitivity_replicated`, `sensitivity_holm_p`, `sensitivity_bf10` | the registered sensitivity analysis of the human effects with every deviation-flagged slice excluded |
| `sensitivity_deviation_models.csv` | 15 | `model`, `primary_class`, `sensitivity_class`, `primary_T1`, `sensitivity_T1` | the same sensitivity analysis for the model effects |
| `tree_routing.csv` | 16 | `model`, `family`, `branch`, `scenario`, `scenario_name`, `possible_scenarios`, `matches_people`, `signatures`, `pointing`, `effect_classes`, `named_decoy`, `trajectory`, `reasoning`, `family_consistent`, `family_classes`, `over_readings`, `positive_controls` | the conclusion each model reached under Step 0 and the two questions of Step 4 (whether it matches people and, if it does not, the state of each failure: present, absent, not resolved or not judged, and the failures a test points to), the conclusions still possible, each effect's class and whether the model named the decoy, and the trajectory test and family classes reported beside it |
| `validity_criteria.csv` | 22 | `gate_type`, `key`, `replicated`, `confirmatory`, `direction_ok`, `holm_family`, `holm_p`, `bf10`, `delta_pp`, `parse_rate`, `refusal_rate`, `not_assessable`, `is_positive_control` | Step 0: the human replication criterion per effect and the data-quality criterion per model (parse, refusal and ceiling rates) |
| `tests/T1_memorization.csv` | 15 | `model`, `fidelity_t1`, `fidelity_t2`, `slope`, `drop`, `drop_lo`, `drop_hi`, `reading`, `paired_categories`, `descriptive_fidelity_all_categories_t1`, `descriptive_fidelity_all_categories_t2`, `descriptive_fidelity_invented_tier` | T1: fidelity across the memorization tiers, per model |
| `tests/T1_memorization_sensitivity.csv` | 15 | `model`, `primary_reading`, `restricted_reading`, `restricted_drop`, `restricted_drop_lo`, `restricted_drop_hi`, `restricted_slope`, `n_slices_dropped`, `adjusted_slope`, `adjusted_drop`, `adjusted_drop_lo`, `adjusted_drop_hi`, `baseline_coef`, `target_coef`, `covariates_omitted`, `n_slices`, `adjusted_reading` | T1 without the out-of-limit slices and adjusted for the baseline |
| `tests/T2_recognition.csv` | 90 | `model`, `structure`, `recognition_rate`, `recognition_lo`, `recognition_hi`, `behavior_pp`, `behavior_lo_pp`, `behavior_hi_pp`, `knows`, `shows`, `reading`, `knows_state`, `shows_state`, `override_state` | T2: recognition-probe rates and readings |
| `tests/T3_ladder.csv` | 15 | `model`, `high_rung`, `mid_rung`, `low_rung`, `tmb_lo`, `tmb_hi`, `bmm_lo`, `bmm_hi`, `reading` | T3: fidelity down the argument-strength ladder |
| `tests/T4_format_points.csv` | 72 | `model`, `format`, `compared_on`, `effect`, `categories`, `human_pp`, `model_pp`, `n_calls`, `boot_lo_pp`, `boot_hi_pp`, `max_draws_per_grid_point` | T4: each model's effect in numbers, words and pictures on the categories compared, with the human effect, the calls and the bootstrap interval |
| `tests/T4_formats.csv` | 15 | `model`, `numbers`, `words`, `pictures`, `undefined`, `diff_lo`, `diff_hi`, `reading`, `numbers_picture_order`, `reading_picture_order` | T4: fidelity in numbers, words and pictures |
| `tests/T5_trajectory.csv` | 15 | `model`, `family`, `trajectory`, `delta`, `traj_lo`, `traj_hi`, `reasoning_reading`, `reason_lo`, `reason_hi` | T5: older against newer generation within each developer family |
| `tests/decoy_target_asymmetry.csv` | 3 | `effect`, `hd_target_pp`, `hf_target_pp`, `hd_minus_hf_pp`, `reading` | the moderator comparing decoys that target the premium option with decoys that target the budget option |
| `tests/first_trial_check.csv` | 7 | `effect`, `full_pp`, `first_pp`, `later_pp`, `divergence_pp`, `first_minus_later_se_pp`, `z`, `p`, `holm_p`, `holm_reject`, `diverges`, `n_first`, `n_full` | the comparability check of all choices against first choices only |
| `tests/format_interaction.csv` | 4 | `test`, `effect`, `format`, `categories`, `format_pp`, `numbers_pp`, `interaction_pp`, `ci_lo_pp`, `ci_hi_pp`, `z`, `raw_p`, `holm_p`, `significant`, `n_format`, `n_numbers`, `reading` | the human format-by-effect interaction tests (Holm) |
| `tests/format_interaction_models.csv` | 44 | `model`, `test`, `human_interaction_pp`, `model_interaction_pp`, `n_calls`, `boot_lo_pp`, `boot_hi_pp`, `reading` | the models' format-by-effect interactions against the human ones |
| `tests/phantom_equivalence.csv` | 1 | `delta_pp`, `ci90_lo_pp`, `ci90_hi_pp`, `band_pp`, `p_tost`, `equivalent`, `reading` | two one-sided tests of the phantom effect against the equivalence band |
| `tests/positive_controls.csv` | 2 | `control`, `delta_pp`, `ci_lo_pp`, `ci_hi_pp`, `p`, `bf10`, `holds`, `affected_if_failed` | the positive control (the frequency decoy on premium-target cells): its human effect, interval, test and Bayes factor, and the readings that depend on it |
| `tests/prompt_mode_divergence.csv` | 2 | `model`, `arm`, `neutral_pp`, `secondary_pp`, `divergence_pp`, `n_calls_neutral`, `n_calls_secondary`, `reading` | the persona and sequential conditions against the neutral condition |
| `tests/similarity_topup_check.csv` | 1 | `backbone_pp`, `topup_pp`, `diff_pp`, `diff_se_pp`, `z`, `p`, `fired`, `benchmark`, `n_backbone`, `n_topup`, `n_topup_participants`, `n_slices` | the similarity effect in the numeric survey against the similarity survey: the difference, its test and the numbers of choices |

The run on simulated data requires three things of these files: no file has a missing value, every key that the
manuscript refers to exists in `numbers.json`, and every simulated model reaches the conclusion that it was
built to reach.
