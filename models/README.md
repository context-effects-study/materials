# models/

This folder holds the model side of the study: the program that sends the choice sets to the language models, the
exact plan of calls, the pre-registered wording of the prompts, and the rule for the order of the options. We have
collected no confirmatory model data.

| File | What it is |
|---|---|
| `run.py` | The program that calls the models. It builds each prompt from `../stimuli/stimuli.json`, with the same option text that the surveys show. It sends the prompt, reads the letter of the chosen option from the reply, decodes it with the codebook that the human data use, and logs one record for each call (`../analysis/DATA_DICTIONARY.md`, part B, lists the fields). `MODEL_REGISTRY` in this file holds each model's exact id, the route of its calls, its reasoning and temperature settings, and its limits on the length of a reply |
| `prompt_materials.json` | The pre-registered wording of the prompts (Web Appendix D): the three wordings of the choice question, the twenty personas and the recognition question. `run.py` refuses to run if this file differs from the wording pre-registered in `run.py` |
| `mot_orders.json` | The twelve pre-registered option orders of each extremity menu of twelve options, drawn once with a fixed seed. `run.py` refuses the file unless the seed reproduces every order |
| `build_manifest.py`, `MANIFEST.md` | The exact plan of calls, computed from the stimulus file: 1,285,630 calls in all, with 3,537 distinct neutral prompts per image-capable model and 3,510 per text-only model |
| `order_plan.py` | The one rule for the order in which the options are shown, which the program and the plan share |
| `selftest_mutants.py` | Shows that the self-test of `run.py` catches a broken builder of requests |
| `SAMPLE_CALLS.jsonl` | One prompt for each structure and format, as a model receives it, from a run of `run.py` without the network |

## The ten models

The lineup has 10 models: six current models from six developers and four older models from four of the
same developers, so that each of these four developers has an older and a current model (the trajectory test, T5,
compares them). On 2026-09-29, we checked every model id against the providers' public lists of models. We
made no call to a model to do this.

| Developer | Model | Generation | Exact id sent | Route | Open weights (repository, commit) | Reasoning contrast | Temperature check |
|---|---|---|---|---|---|---|---|
| OpenAI | GPT-6 Astra | current | `gpt-6-astra` | openai |  | yes | no |
| Anthropic | Claude Opus 5.5 | current | `claude-opus-5-5` | anthropic |  | no | no |
| Google | Gemini 3.8 Flash | current | `gemini-3.8-flash` | google via host google-ai-studio |  | yes | yes |
| Alibaba | Qwen3.8-Max (0902 snapshot) | current | `qwen/qwen3.8-max-0902` | openrouter via host alibaba |  | yes | yes |
| DeepSeek | DeepSeek V4 Pro (GA, 0813) | current | `deepseek/deepseek-v4-pro-0813` | openrouter via host novita (fp8) | deepseek-ai/DeepSeek-V4-Pro-0813 at 72e1d3230f6c | yes | yes |
| Meta | Muse Spark 1.3 | current | `meta/muse-spark-1.3` | openrouter via host meta |  | no | yes |
| OpenAI | GPT-4.1 | older | `gpt-4.1-2025-04-14` | openai |  | no | yes |
| Anthropic | Claude Opus 4.8 | older | `claude-opus-4-8` | anthropic |  | yes | no |
| DeepSeek | DeepSeek R1 | older | `deepseek/deepseek-r1` | openrouter via host novita (fp8) | deepseek-ai/DeepSeek-R1 at 56d4cbbb4d29 | no | yes |
| Meta | Llama 4 Maverick | older | `meta-llama/llama-4-maverick` | openrouter via host novita (fp8) | meta-llama/Llama-4-Maverick-17B-128E-Instruct at 73d14711bcc7 | no | yes |

"Route" is where the program sends a call: either a provider's own API, or OpenRouter, fixed to one named host (and
to the numeric precision that the host states, where it states one), with no fallback to other hosts, so that the
host cannot change without notice. Each model with open weights is fixed to a Hugging Face repository and a commit.
Every call logs the model id requested and the id that the provider returned, so a change of the model's version
during data collection shows in the data. A substitution rule, fixed in advance in `run.py`, says what we do if a
provider withdraws a model before or during data collection.

## The conditions and the repeated calls

Each model effect is a share of choices over the planned variations of the prompt: the pre-registered option orders
and the three wordings of the question, and the twenty personas in the persona condition. At the provider's default
temperature, each call is one draw from the model's distribution of answers, so the confirmatory condition also
repeats every prompt: 10 calls for each text prompt and 60 for each picture prompt. A cell shown as pictures then
receives as many calls as a cell of three options shown as numbers. Each call is separate, with no history of the
conversation.

- **The neutral condition (confirmatory, every model).** The provider's default temperature (1.0 for the two models
  whose developers recommend it), and reasoning switched off where the provider allows it, or else set to the lowest
  level that the provider accepts. Each text prompt is called 10 times and each picture prompt 60 times. Only these
  calls enter the confirmatory estimates.
- **The reasoning comparison.** The same prompts with reasoning at the provider's standard high level, on the five
  models marked "yes" in the column "Reasoning contrast". Each text prompt is called 5 times and each picture prompt
  30 times. The comparison is with the model's neutral setting.
- **The temperature check.** The neutral prompts again at temperatures of 0 and 1.0, only on the seven models whose
  API accepts the setting (marked "yes" in the column "Temperature check"). We report this check as a description,
  never as primary evidence.
- **The persona, sequential and recognition conditions.** One call for each prompt.

`MODEL_REGISTRY` holds the exact settings sent in each condition, and every call records them.

## Commands (none of these calls a model)

```
python models/run.py --selftest        # checks the model settings, the prompt wording and every request
python models/selftest_mutants.py      # each broken builder of requests must fail the self-test
python models/build_manifest.py        # rewrites MANIFEST.md
python models/run.py --out-dir <dir>   # made-up replies, no network; writes model_log.jsonl, SAMPLE_CALLS.jsonl
```

`python run_all.py --part models` runs all four and checks the plan and the sample prompts against the copies in
this repository. Real calls (`python models/run.py --live ...`) need the providers' API keys in the environment
(OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY or GEMINI_API_KEY, and OPENROUTER_API_KEY) and the `openai` and
`anthropic` Python packages. We will make them only at Stage 2 (see "The model responses at Stage 2" in the README
at the root).
