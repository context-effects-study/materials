# models/

The model side of the study: the runner that sends the choice sets to the language models, the exact call
plan, the registered prompt wording, and the rule for the order of the options. No confirmatory model data
have been collected.

| File | What it is |
|---|---|
| `run.py` | The runner. It builds each prompt from `../stimuli/stimuli.json` with the same option text the surveys show, sends it, parses the chosen letter, decodes it with the codebook the human data use, and logs one record per call (fields in `../analysis/DATA_DICTIONARY.md`, part B). `MODEL_REGISTRY` in this file holds every model's exact id, route, reasoning and temperature settings and output limits |
| `prompt_materials.json` | The registered prompt wording (Web Appendix D): the three paraphrases of the choice question, the twenty personas and the recognition probe. The runner refuses to run if this file differs from the wording registered in `run.py` |
| `mot_orders.json` | The twelve registered option orders of each twelve-option extremity menu, drawn once with a fixed seed; the runner refuses the file unless the seed reproduces every order |
| `build_manifest.py`, `MANIFEST.md` | The exact call plan computed from the stimulus file: 1,285,630 calls; 3,537 distinct neutral prompts per image-capable model and 3,510 per text-only model |
| `order_plan.py` | The one rule for the order in which options are shown, shared by the runner and the plan |
| `selftest_mutants.py` | Shows that the runner's self-test catches a broken request builder |
| `SAMPLE_CALLS.jsonl` | One rendered prompt per structure and format, from the runner's dry run, to read what a model is shown |

## The model lineup

10 models: six current flagships and four older generations, so that each of four developers has
an old and a new member (the generation comparison, test T5). Ids were verified on 2026-09-29
against the providers' public model listings; no completion call was made.

| Developer | Model | Tier | Exact id sent | Route | Open weights (repository, commit) | Reasoning contrast | Temperature conditions |
|---|---|---|---|---|---|---|---|
| OpenAI | GPT-6 Astra | current flagship | `gpt-6-astra` | openai |  | yes | no |
| Anthropic | Claude Opus 5.5 | current flagship | `claude-opus-5-5` | anthropic |  | no | no |
| Google | Gemini 3.8 Flash | current flagship | `gemini-3.8-flash` | google via host google-ai-studio |  | yes | yes |
| Alibaba | Qwen3.8-Max (0902 snapshot) | current flagship | `qwen/qwen3.8-max-0902` | openrouter via host alibaba |  | yes | yes |
| DeepSeek | DeepSeek V4 Pro (GA, 0813) | current flagship | `deepseek/deepseek-v4-pro-0813` | openrouter via host novita (fp8) | deepseek-ai/DeepSeek-V4-Pro-0813 at 72e1d3230f6c | yes | yes |
| Meta | Muse Spark 1.3 | current flagship | `meta/muse-spark-1.3` | openrouter via host meta |  | no | yes |
| OpenAI | GPT-4.1 | older generation | `gpt-4.1-2025-04-14` | openai |  | no | yes |
| Anthropic | Claude Opus 4.8 | older generation | `claude-opus-4-8` | anthropic |  | yes | no |
| DeepSeek | DeepSeek R1 | older generation | `deepseek/deepseek-r1` | openrouter via host novita (fp8) | deepseek-ai/DeepSeek-R1 at 56d4cbbb4d29 | no | yes |
| Meta | Llama 4 Maverick | older generation | `meta-llama/llama-4-maverick` | openrouter via host novita (fp8) | meta-llama/Llama-4-Maverick-17B-128E-Instruct at 73d14711bcc7 | no | yes |

"Route" is where the call is sent: a provider's own API, or OpenRouter pinned to one named host (with its
quantization where the host declares one) with no fallback to other hosts, so the serving host cannot
change silently. Open-weight models are registered to a Hugging Face repository and commit. Every call logs
the model id requested and the id the provider returned, so a change of snapshot during collection is
visible in the data. A registered substitution rule in `run.py` governs what happens if a model is
withdrawn before or during collection.

## The conditions and the repeated draws

Each estimate is a choice share over the designed variations of the prompt (the registered position orders
and three paraphrases, and twenty personas in the persona condition). At the provider's default
temperature each call is one draw from the model's distribution of answers, so the confirmatory condition
also repeats every prompt: 10 draws per text prompt and 60 per picture prompt, which gives a pictures cell
as many calls as a three-option numbers cell. Each draw is a separate call with no conversation history.

- **Neutral condition (confirmatory, every model):** the provider's default temperature (1.0 for the two
  models whose developers recommend it), reasoning off where an off switch exists and the lowest accepted
  level where it does not; 10 draws per text prompt, 60 per picture prompt. Only these calls enter the
  confirmatory estimates.
- **Reasoning contrast:** the same prompts with reasoning at the provider's standard high level, on the five
  models marked above; 5 draws per text prompt, 30 per picture prompt. The low side is the model's neutral
  setting.
- **Temperature conditions:** the neutral prompts re-run at temperature 0 and 1.0, only on the seven models
  whose API accepts the parameter (marked above); reported as robustness, never as primary evidence.
- **Persona, sequential and recognition conditions:** one call per prompt.

The exact settings sent in each condition are in `MODEL_REGISTRY` and are recorded on every call.

## Commands (none of these makes a network call)

```
python models/run.py --selftest        # the registry, the prompt materials and every request payload, with planted faults
python models/selftest_mutants.py      # broken request builders must each fail the self-test
python models/build_manifest.py        # rewrites MANIFEST.md
python models/run.py --out-dir <dir>   # dry run on synthetic replies; writes model_log.jsonl and SAMPLE_CALLS.jsonl
```

`python run_all.py --part models` runs all four and checks the plan and the sample prompts against the
deposited copies. Real calls (`python models/run.py --live ...`) need the providers' API keys in the
environment (OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY or GEMINI_API_KEY, OPENROUTER_API_KEY) and the
`openai` and `anthropic` Python packages; they are made only at Stage 2 (see the README at the root, "The model
responses at Stage 2").
