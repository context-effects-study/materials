# Data dictionary of the confirmatory study

Three formats connect the study: the human long table (A), written by `ingest.py` from a Qualtrics export;
the model call log (B), written by `../models/run.py`; and the results pack (C), written by `analyze.py` from
A and B. The synthetic generator (`synth.py`) writes A and B in exactly these formats. The calibration
pre-test's data files have their own codebooks in `../calibration/<study>/`.

## A. The human long table (one row per choice)

| Column | Type | Values and meaning |
|---|---|---|
| `participant_id` | text | one-way hash of the Prolific id ("P" and 15 hexadecimal characters) |
| `script_id` | text | the pre-built script the participant received |
| `trial_position` | integer | 1 to 7 (backbone and similarity surveys) or 1 to 3 (format and price-free surveys); 1 is the first choice, the first-choice subsample |
| `cell_id` | text | the design cell, `<category>_<structure>` |
| `category` | category | the product category |
| `structure` | category | BIN, FRQ, RNG, PHT, SOT, MOT, EXC, SYM or SIM |
| `tier` | integer | 1 published values, 2 published category with new values, 3 invented category |
| `format` | category | numbers, words or pictures |
| `position_order` | text | the option codes in the order shown |
| `stimulus_id` | text | the stimulus in `../stimuli/stimuli.json`; for the two pictures pairs calibrated per format, the values are read through the format (`format_variants.pictures.options`) |
| `sim_placement` | category | for similarity cells, which focal option the near-copy copies; NA otherwise |
| `choice` | category | the option chosen, decoded with the codebook below |
| `chose_target` | 0 or 1 | chose the target (BIN, SOT, FRQ, RNG, PHT, SIM) |
| `chose_ext` | 0 or 1 | chose the new extreme (SOT) |
| `chose_hd` | 0 or 1 | chose the premium option (SYM; derivable everywhere from `is_hd` in the stimulus file) |
| `chose_clone` | 0 or 1 | chose the near-copy (SIM) |
| `chose_extreme_tier` | 0 or 1 | chose an option in the High or Low tier rather than the Middle tier (MOT and EXC; the extremity statistic is MOT minus EXC on this indicator) |
| `rt_page_sec` | seconds | time from page load to submitting the choice page |
| `completed_all` | 0 or 1 | the participant completed every choice of the script |
| `consent`, `age`, `gender`, `device` | as exported | consent answer, self-reported age in years and gender, device field where recorded |
| `qsf_sha256`, `export_ts` | text | SHA-256 of the survey file and the time of the export, to tie the table to its sources |

**The codebook, per structure.**

| Structure | Decoded values | Notes |
|---|---|---|
| BIN | TARGET, COMP | the two focal options. TARGET is the category's compromise target, the option that starts behind (the calibration band); COMP is its rival. Which option is premium is carried separately (`is_hd`) |
| SOT (compromise) | TARGET, COMP, EXT | the two binary options plus one new extreme beyond the target, so the target becomes the middle option. The statistic is the relative share TARGET / (TARGET + COMP) against the matched BIN; choices of EXT are valid and recorded but leave the relative share. No free-standing middle option is ever added |
| FRQ, RNG | TARGET, COMP, DECOY | TARGET is the option that dominates the decoy |
| PHT | TARGET, COMP | the phantom is better than the target on exactly one attribute and marked unavailable; a choice of the phantom cannot be made and would be an exclusion, never a share |
| SYM | HD, HF, DECOY | the symmetric decoy is dominated by both focal options; the upscaling statistic reads the premium (HD) share |
| SIM | TARGET, COMP, CLONE | CLONE is the near-copy of one focal option; the similarity statistic is the relative share of the option that was not copied, against the matched BIN |
| MOT (extremity treatment) | T1S1 to T3S4 | menu tier by slot (12 options; "T" is the menu's quality tier, not the memorization tier); read through `chose_extreme_tier` |
| EXC (extremity control) | EXC_H, EXC_M, EXC_L | one option at each of MOT's three tiers, built from the matched menu's tier centers, so the two menus differ only in how many options sit in each tier |

**The shared baseline.** Within each category and memorization tier, one BIN cell is the comparison
condition for six tests (compromise, frequency, range, phantom, upscaling, similarity). The seventh,
extremity, compares the MOT menu with its matched EXC control. Because the six tests share a baseline, Holm's
correction, valid under any dependence, is used.

**Invariants** `ingest.py` asserts: no product category repeated within a participant; every choice decodes
to a valid value for its structure (a phantom choice is routed to the exclusions); every cell exists in the
stimulus file.

## B. The model call log (one JSON record per call)

| Field | Meaning |
|---|---|
| `record_id` | deterministic hash of the run, model, stimulus, condition and draw, so an interrupted run resumes without duplicates |
| `draw_index` | which repeated draw of the same prompt this call is: 0 to 9 for a neutral text prompt, 0 to 59 for a neutral picture prompt, 0 to 4 (text) or 0 to 29 (pictures) on the high side of the reasoning contrast, and 0 in the persona, temperature, sequential and recognition conditions |
| `run_id` | the collection run |
| `model_key` | the model's slot in `MODEL_REGISTRY` (for example `openai_flagship`) |
| `model_id_requested`, `model_id_echoed` | the id sent and the id the provider returned; a mismatch is flagged |
| `provider`, `api_flavor` | where the call went and in which request format |
| `prompting_mode` | neutral, persona, sequential or recognition |
| `persona_id` | the persona, in the persona condition |
| `paraphrase_id` | which of the three registered phrasings |
| `arm` | the condition: primary (the neutral, confirmatory one), reasoning_on, temp_0, temp_1, persona, sequential or recognition |
| `reasoning_mode`, `reasoning_requested`, `reasoning_effective` | the reasoning setting registered for the condition (off, lowest, on, always on, not applicable), the setting sent, and the setting the provider reports having applied |
| `temperature_requested`, `sampling_params_effective` | the temperature sent (empty = provider default) and the sampling parameters the provider applied or the text with which it rejected them |
| `image_ref`, `image_sha256`, `image_source_svg_sha256` | the picture file sent, its hash, and the hash of the SVG it was drawn from, for pictures calls |
| `cell_id`, `category`, `structure`, `tier`, `format`, `position_order`, `stimulus_id` | the design coordinates, as in A |
| `placement` | for similarity cells, which focal option the near-copy copies (clone_HF or clone_HD), as `sim_placement` in A |
| `shown_codes` | the option codes in the order shown |
| `session_id`, `seq_index` | the sequential-condition session and the position within it |
| `prompt_text` | the full prompt sent |
| `raw_response` | the model's reply, unprocessed |
| `parsed_choice`, `parse_method` | the option identified in the reply, and how (exact match, fallback pattern, failed; `dry_run` in a dry run) |
| `exclusion_flag`, `exclusion_reason` | refusal, unparseable reply, latency or id mismatch |
| `latency_ms`, `cost_usd`, `timestamp` | time taken, cost and time of the call (UTC) |
| `family`, `generation`, `model_slot`, `model_tier` | the developer family, old or new generation, slot and tier (for test T5) |
| `model_substituted_from` | empty, or the model originally registered for the slot and the reason, date and rule of a substitution |

Invariants: `record_id` is unique; every combination of model, stimulus, condition and draw in the plan
appears exactly once.

## C. The results pack (`results_pack/`)

Everything the results section will cite is written here, and the manuscript binds to the keys of
`numbers.json`, never to hand-typed numbers. The files `analyze.py` writes, with their size in the rehearsal:

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
| `tree_routing.csv` | 16 | `model`, `family`, `branch`, `scenario`, `scenario_name`, `model_level_account`, `per_effect_accounts`, `over_readings`, `positive_controls`, `possible_scenarios`, `qualifier`, `open_pattern_tests` | the branch of the decision tree and the named scenario each model and effect reached |
| `validity_criteria.csv` | 22 | `gate_type`, `key`, `replicated`, `confirmatory`, `direction_ok`, `holm_family`, `holm_p`, `bf10`, `delta_pp`, `parse_rate`, `refusal_rate`, `not_assessable`, `is_positive_control` | Step 0: the human replication criterion per effect and the data-quality criterion per model (parse, refusal and ceiling rates) |
| `tests/T1_memorization.csv` | 15 | `model`, `fidelity_t1`, `fidelity_t2`, `slope`, `drop`, `drop_lo`, `drop_hi`, `reading`, `paired_categories`, `descriptive_fidelity_all_categories_t1`, `descriptive_fidelity_all_categories_t2`, `descriptive_fidelity_invented_tier` | T1: fidelity across the memorization tiers, per model |
| `tests/T1_memorization_sensitivity.csv` | 15 | `model`, `primary_reading`, `restricted_reading`, `restricted_drop`, `restricted_drop_lo`, `restricted_drop_hi`, `restricted_slope`, `n_slices_dropped`, `adjusted_slope`, `adjusted_drop`, `adjusted_drop_lo`, `adjusted_drop_hi`, `baseline_coef`, `target_coef`, `covariates_omitted`, `n_slices`, `adjusted_reading` | T1 without the out-of-limit slices and adjusted for the baseline |
| `tests/T2_recognition.csv` | 90 | `model`, `structure`, `recognition_rate`, `recognition_lo`, `recognition_hi`, `behavior_pp`, `behavior_lo_pp`, `behavior_hi_pp`, `knows`, `shows`, `reading`, `knows_state`, `shows_state`, `override_state` | T2: recognition-probe rates and readings |
| `tests/T3_ladder.csv` | 15 | `model`, `high_rung`, `mid_rung`, `low_rung`, `tmb_lo`, `tmb_hi`, `bmm_lo`, `bmm_hi`, `reading`, `attribution`, `missed_effects`, `missed_recognition` | T3: fidelity down the argument-strength ladder |
| `tests/T4_format_points.csv` | 72 | `model`, `format`, `compared_on`, `effect`, `categories`, `human_pp`, `model_pp`, `n_calls`, `boot_lo_pp`, `boot_hi_pp`, `max_draws_per_grid_point` | T4: each model's effect in numbers, words and pictures on the categories compared, with the human effect, the calls and the bootstrap interval |
| `tests/T4_formats.csv` | 15 | `model`, `numbers`, `words`, `pictures`, `undefined`, `diff_lo`, `diff_hi`, `reading`, `numbers_picture_order`, `reading_picture_order` | T4: fidelity in numbers, words and pictures |
| `tests/T5_trajectory.csv` | 15 | `model`, `family`, `trajectory`, `delta`, `traj_lo`, `traj_hi`, `reasoning_reading`, `reason_lo`, `reason_hi` | T5: older against newer generation within each developer family |
| `tests/decoy_target_asymmetry.csv` | 3 | `effect`, `hd_target_pp`, `hf_target_pp`, `hd_minus_hf_pp`, `reading` | the moderator comparing decoys that target the premium option with decoys that target the budget option |
| `tests/first_trial_check.csv` | 7 | `effect`, `full_pp`, `first_pp`, `later_pp`, `divergence_pp`, `first_minus_later_se_pp`, `z`, `p`, `holm_p`, `holm_reject`, `diverges`, `n_first`, `n_full` | the comparability check of all choices against first choices only |
| `tests/format_interaction.csv` | 4 | `test`, `effect`, `format`, `categories`, `format_pp`, `numbers_pp`, `interaction_pp`, `ci_lo_pp`, `ci_hi_pp`, `z`, `raw_p`, `holm_p`, `significant`, `n_format`, `n_numbers`, `reading` | the human format-by-effect interaction tests (Holm) |
| `tests/format_interaction_models.csv` | 44 | `model`, `test`, `human_interaction_pp`, `model_interaction_pp`, `n_calls`, `boot_lo_pp`, `boot_hi_pp`, `reading` | the models' format-by-effect interactions against the human ones |
| `tests/phantom_equivalence.csv` | 1 | `delta_pp`, `ci90_lo_pp`, `ci90_hi_pp`, `band_pp`, `p_tost`, `equivalent` | two one-sided tests of the phantom effect against the equivalence band |
| `tests/positive_controls.csv` | 2 | `control`, `delta_pp`, `ci_lo_pp`, `ci_hi_pp`, `p`, `bf10`, `holds`, `affected_if_failed` | the positive control (the frequency decoy on premium-target cells): its human effect, interval, test and Bayes factor, and the readings that depend on it |
| `tests/prompt_mode_divergence.csv` | 2 | `model`, `arm`, `neutral_pp`, `secondary_pp`, `divergence_pp`, `n_calls_neutral`, `n_calls_secondary`, `reading` | the persona and sequential conditions against the neutral condition |
| `tests/similarity_topup_check.csv` | 1 | `backbone_pp`, `topup_pp`, `diff_pp`, `diff_se_pp`, `z`, `p`, `fired`, `benchmark`, `n_backbone`, `n_topup`, `n_topup_participants`, `n_slices` | the similarity effect in the numeric survey against the similarity survey: the difference, its test and the numbers of choices |

Pass condition (the same as the dress rehearsal's): the pack renders with no missing value, every key the
manuscript refers to exists in `numbers.json`, and the decision tree routes every planted profile correctly.
