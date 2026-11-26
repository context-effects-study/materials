# models/

This folder contains the model side of the study: the program that sends the choice sets to the language models, the
exact plan of calls, the pre-registered wording of the prompts, and the rule for the order of the options. We have
collected no confirmatory model data.

| File | What it is |
|---|---|
| `run.py` | The program that calls the models. It builds each prompt from `../stimuli/stimuli.json`, with the same option text that the surveys show. It sends the prompt, reads the letter of the chosen option from the reply, decodes it with the codebook that the human data use, and logs one record for each call (`../analysis/DATA_DICTIONARY.md`, part B, lists the fields) |
| `model_registry.json` | Each model's exact id, the route of its calls, the parameters that each reasoning setting sends, its temperature settings, its limits on the length of a reply, and the calls it receives in each condition. `run.py` reads it as `MODEL_REGISTRY` |
| `prompt_materials.json` | The pre-registered wording of the prompts (Web Appendix D): the three wordings of the choice question, the twenty personas and the suspicion probe. `run.py` refuses to run if this file differs from the wording pre-registered in `run.py` |
| `mot_orders.json` | The twelve pre-registered option orders of each extremity menu of twelve options, drawn once with a fixed seed. `run.py` refuses the file unless the seed reproduces every order |
| `build_manifest.py`, `MANIFEST.md` | The exact plan of calls, computed from the stimuli and the registry: 8,629,438 calls in all, with 3,537 distinct neutral prompts per image-capable model and 3,510 per text-only model |
| `order_plan.py` | The one rule for the order in which the options are shown, which the program and the plan share |
| `batch.py` | Sends the calls of the closed models of OpenAI, Anthropic, Google, xAI and Mistral through their developers' batch services, which bill half the price, and reads the answers with the parsing of `run.py` |
| `test_batch.py`, `batch_fixtures.json` | Tests `batch.py` against made-up batch services, with no network |
| `test_vllm_route.py` | Tests the route of the models with open weights against a made-up vLLM server on this computer |
| `selftest_mutants.py` | Shows that the self-test of `run.py` catches a broken builder of requests |
| `SAMPLE_CALLS.jsonl` | One prompt for each kind of choice set and format, as a model receives it, from a run of `run.py` without the network |

## The models

The lineup has 106 models in three groups: closed models of the current generation, closed models of the
previous generation, and models with open weights, which anyone can run unchanged at a fixed revision of their
weights. In Table 3 of the manuscript, we group them by developer, and in Table
WA-D1 of the web appendix, we give the settings and conditions of each model. On 2026-11-24, we checked every model id against the providers' public lists
of models. We made no call to a model to do this.

| Developer | Model | Group | Exact id sent | Route | Open weights (repository, commit) | Settings run | Temperature check |
|---|---|---|---|---|---|---|---|
| OpenAI | GPT-6.2 Astra | closed, current | `gpt-6.2-astra` | openai |  | low, default | no |
| OpenAI | GPT-6.2 Sol | closed, current | `gpt-6.2-sol` | openai |  | low, default, high | no |
| OpenAI | GPT-6.1 Terra | closed, current | `gpt-6.1-terra` | openai |  | off, default, high | yes |
| OpenAI | GPT-6 Luna | closed, current | `gpt-6-luna` | openai |  | off, default, high, low, max | yes |
| Anthropic | Claude Fable 5.2 | closed, current | `claude-fable-5-2` | anthropic |  | low, default | no |
| Anthropic | Claude Opus 5.5 | closed, current | `claude-opus-5-5` | anthropic |  | low, default | no |
| Anthropic | Claude Sonnet 5.5 | closed, current | `claude-sonnet-5-5` | anthropic |  | off, default | no |
| Anthropic | Claude Haiku 5.5 | closed, current | `claude-haiku-5-5` | anthropic |  | off, default, high, low, max | no |
| Google | Gemini 4 Carbon | closed, current | `gemini-4-carbon` | google |  | low, default | no |
| Google | Gemini 4 Neon | closed, current | `gemini-4-neon` | google |  | low, default | no |
| Google | Gemini 4 Hydrogen | closed, current | `gemini-4-hydrogen` | google |  | low, default | no |
| Google | Gemini 3.5 Flash-Lite | closed, current | `gemini-3.5-flash-lite` | google |  | low, high | no |
| xAI | Grok 4.7 | closed, current | `grok-4.7` | xai |  | low, default | no |
| Mistral | Mistral Large 4 | closed, current | `mistral-large-2610` | mistral |  | low, default, high | yes |
| Alibaba | Qwen4-Max | closed, current | `qwen/qwen4-max` | openrouter via host alibaba |  | off, default | yes |
| Alibaba | Qwen3.8-Flash | closed, current | `qwen/qwen3.8-flash` | openrouter via host alibaba |  | off, default, low | yes |
| DeepSeek | DeepSeek V4 Pro | closed, current | `deepseek/deepseek-v4-pro` | openrouter via host deepseek |  | off, default | yes |
| Zhipu | GLM-5.4 (GLM-5.3 until its API opens) | closed, current | `z-ai/glm-5.4` | openrouter via host z-ai |  | off, default | yes |
| MiniMax | MiniMax M3.1 Flash | closed, current | `minimax/minimax-m3.1-flash` | openrouter via host minimax |  | off, default | yes |
| ByteDance | Seed 2.1 Turbo | closed, current | `bytedance-seed/seed-2-1-turbo` | openrouter via host bytedance |  | off, default | yes |
| Meta | Muse Wonder | closed, current | `meta/muse-wonder` | openrouter via host meta |  | low, default | no |
| OpenAI | GPT-5.6 Luna | closed, previous | `gpt-5.6-luna` | openai |  | off, default | yes |
| OpenAI | GPT-5.4 mini | closed, previous | `gpt-5.4-mini` | openai |  | off | yes |
| Anthropic | Claude Haiku 4.5 | closed, previous | `claude-haiku-4-5-20251001` | anthropic |  | off | no |
| Anthropic | Claude Sonnet 5 | closed, previous | `claude-sonnet-5` | anthropic |  | off, default | no |
| Google | Gemini 3 Flash | closed, previous | `gemini-3-flash-preview` | google |  | low, default | no |
| Google | Gemini 2.5 Flash-Lite | closed, previous | `gemini-2.5-flash-lite` | google |  | off | yes |
| Google | Gemini 3.1 Pro | closed, previous | `gemini-3.1-pro-preview` | google |  | low, default | no |
| xAI | Grok 4.3 | closed, previous | `grok-4.3` | xai |  | low, default | no |
| Alibaba | Qwen3.8-Max | closed, previous | `qwen/qwen3.8-max-0902` | openrouter via host alibaba |  | low, default | no |
| MiniMax | MiniMax M3 | closed, previous | `minimax/minimax-m3` | openrouter via host minimax |  | off, default | yes |
| Alibaba | Qwen 2.5 7B Instruct | open weights | `Qwen/Qwen2.5-7B-Instruct` | vllm | Qwen/Qwen2.5-7B-Instruct at a09a35458c70 | off | yes |
| Alibaba | Qwen 2.5 32B Instruct | open weights | `Qwen/Qwen2.5-32B-Instruct` | vllm | Qwen/Qwen2.5-32B-Instruct at 5ede1c97bbab | off | yes |
| Alibaba | Qwen3 30B A3B Instruct 2507 | open weights | `Qwen/Qwen3-30B-A3B-Instruct-2507` | vllm | Qwen/Qwen3-30B-A3B-Instruct-2507 at 0d7cf23991f4 | off | yes |
| Alibaba | Qwen3 32B | open weights | `Qwen/Qwen3-32B` | vllm | Qwen/Qwen3-32B at 9216db5781bf | off, default | yes |
| Alibaba | Qwen3.5 0.8B | open weights | `Qwen/Qwen3.5-0.8B` | vllm | Qwen/Qwen3.5-0.8B at 2fc06364715b | off, default | yes |
| Alibaba | Qwen3.5 2B | open weights | `Qwen/Qwen3.5-2B` | vllm | Qwen/Qwen3.5-2B at 15852e8c1636 | off, default | yes |
| Alibaba | Qwen3.5 4B | open weights | `Qwen/Qwen3.5-4B` | vllm | Qwen/Qwen3.5-4B at 851bf6e806ef | off, default | yes |
| Alibaba | Qwen3.5 9B | open weights | `Qwen/Qwen3.5-9B` | vllm | Qwen/Qwen3.5-9B at c20223623576 | off, default | yes |
| Alibaba | Qwen3.5 27B | open weights | `Qwen/Qwen3.5-27B` | vllm | Qwen/Qwen3.5-27B at 81a287ca484a | off, default | yes |
| Alibaba | Qwen3.5 35B A3B | open weights | `Qwen/Qwen3.5-35B-A3B` | vllm | Qwen/Qwen3.5-35B-A3B at 2508b2437e38 | off, default | yes |
| Alibaba | Qwen3.5 122B A10B FP8 | open weights | `Qwen/Qwen3.5-122B-A10B-FP8` | vllm | Qwen/Qwen3.5-122B-A10B-FP8 at a099dee70ccf | off, default | yes |
| Alibaba | Qwen3.6 27B | open weights | `Qwen/Qwen3.6-27B` | vllm | Qwen/Qwen3.6-27B at 1cda14dd71a3 | off, default | yes |
| Alibaba | Qwen3.8 27B | open weights | `Qwen/Qwen3.8-27B` | vllm | Qwen/Qwen3.8-27B at 1d4bf0f2ff60 | off, default | yes |
| Meta | Llama 3.2 3B Instruct | open weights | `unsloth/Llama-3.2-3B-Instruct` | vllm | unsloth/Llama-3.2-3B-Instruct at 006f5dcd1393 | off | yes |
| Meta | Llama 3.1 8B Instruct | open weights | `unsloth/Llama-3.1-8B-Instruct` | vllm | unsloth/Llama-3.1-8B-Instruct at 4699cc75b550 | off | yes |
| Google | Gemma 3 27B | open weights | `unsloth/gemma-3-27b-it` | vllm | unsloth/gemma-3-27b-it at 7a5a3053dbd5 | off | yes |
| Google | Gemma 4 12B | open weights | `google/gemma-4-12B-it` | vllm | google/gemma-4-12B-it at 43c9d014b231 | off, default | yes |
| Google | Gemma 4 26B A4B | open weights | `google/gemma-4-26B-A4B-it` | vllm | google/gemma-4-26B-A4B-it at 4d7ae4984b7d | off, default | yes |
| Google | Gemma 4 31B | open weights | `unsloth/gemma-4-31b-it` | vllm | unsloth/gemma-4-31b-it at 51c9f6265ea3 | off, default | yes |
| Allen AI | OLMo 3 7B Instruct | open weights | `allenai/Olmo-3-7B-Instruct` | vllm | allenai/Olmo-3-7B-Instruct at 6e5971d9eba4 | off | yes |
| Allen AI | OLMo 3.1 32B Instruct | open weights | `allenai/Olmo-3.1-32B-Instruct` | vllm | allenai/Olmo-3.1-32B-Instruct at ac0587e4a774 | off | yes |
| OpenAI | gpt-oss 20B | open weights | `openai/gpt-oss-20b` | vllm | openai/gpt-oss-20b at 6cee5e81ee83 | low, default, high | yes |
| OpenAI | gpt-oss 120B | open weights | `openai/gpt-oss-120b` | vllm | openai/gpt-oss-120b at b5c939de8f75 | low, default, high | yes |
| Mistral | Ministral 3 14B | open weights | `mistralai/Ministral-3-14B-Instruct-2512-BF16` | vllm | mistralai/Ministral-3-14B-Instruct-2512-BF16 at 3cea74c1ebaf | off | yes |
| Microsoft | Phi-4 | open weights | `microsoft/phi-4` | vllm | microsoft/phi-4 at 2db69c1c3e91 | off | yes |
| IBM | Granite 4.1 30B | open weights | `ibm-granite/granite-4.1-30b` | vllm | ibm-granite/granite-4.1-30b at 4fae6278f713 | off | yes |
| IBM | Granite 4.2 30B | open weights | `ibm-granite/granite-4.2-30b` | vllm | ibm-granite/granite-4.2-30b at 9e668ce1c538 | off, default | yes |
| NVIDIA | Nemotron 3 Nano 30B A3B | open weights | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` | vllm | nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 at bf77c3174f68 | off, default | yes |
| Zhipu | GLM-4.7-Flash | open weights | `zai-org/GLM-4.7-Flash` | vllm | zai-org/GLM-4.7-Flash at 7dd20894a642 | off, default | yes |
| Baidu | ERNIE 4.5 21B A3B | open weights | `baidu/ERNIE-4.5-21B-A3B-PT` | vllm | baidu/ERNIE-4.5-21B-A3B-PT at 87db95487941 | off | yes |
| Marin | Marin 8B Instruct | open weights | `marin-community/marin-8b-instruct` | vllm | marin-community/marin-8b-instruct at 0378f9c932bd | off | yes |
| DeepSeek | DeepSeek V4.1 Flash | open weights | `deepseek-ai/DeepSeek-V4.1-Flash` | vllm | deepseek-ai/DeepSeek-V4.1-Flash at 314113f8a7da | off, default | yes |
| Zhipu | GLM-5.3-Flash FP8 | open weights | `zai-org/GLM-5.3-Flash` | vllm | zai-org/GLM-5.3-Flash at 46a050bec130 | low, default, high | yes |
| Alibaba | Qwen 2.5 72B Instruct | open weights | `Qwen/Qwen2.5-72B-Instruct` | vllm | Qwen/Qwen2.5-72B-Instruct at 495f39366efe | off | yes |
| Alibaba | Qwen3 235B A22B | open weights | `Qwen/Qwen3-235B-A22B-FP8` | vllm | Qwen/Qwen3-235B-A22B-FP8 at 39eb2b067ea6 | off, default | yes |
| Alibaba | Qwen3-Next 80B A3B Instruct | open weights | `Qwen/Qwen3-Next-80B-A3B-Instruct` | vllm | Qwen/Qwen3-Next-80B-A3B-Instruct at 9c7f2fbe8446 | off | yes |
| Alibaba | Qwen3.6 35B A3B | open weights | `Qwen/Qwen3.6-35B-A3B` | vllm | Qwen/Qwen3.6-35B-A3B at 345d467b117d | off, default | yes |
| Alibaba | Qwen3.5 397B A17B FP8 | open weights | `Qwen/Qwen3.5-397B-A17B-FP8` | vllm | Qwen/Qwen3.5-397B-A17B-FP8 at ea5b4f81096f | off, default | yes |
| Alibaba | Qwen3.8-Flash-Next | open weights | `Qwen/Qwen3.8-Flash-Next-FP8` | vllm | Qwen/Qwen3.8-Flash-Next-FP8 at 7fb48d708ca6 | off, default, low | yes |
| Meta | Llama 3.3 70B Instruct | open weights | `meta-llama/Llama-3.3-70B-Instruct` | vllm | meta-llama/Llama-3.3-70B-Instruct at 6f6073b42301 | off | yes |
| Meta | Llama 4 Scout 17B-16E | open weights | `meta-llama/Llama-4-Scout-17B-16E-Instruct` | vllm | meta-llama/Llama-4-Scout-17B-16E-Instruct at 92f3b1597a19 | off | yes |
| Meta | Llama 4 Maverick 17B-128E FP8 | open weights | `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8` | vllm | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 at 94125d2bd830 | off | yes |
| Meta | Muse Glimmer 30B | open weights | `meta-models/Muse-Glimmer-30B` | vllm | meta-models/Muse-Glimmer-30B at 1297fd7dfeac | off, default | yes |
| Google | Gemma 2 27B | open weights | `google/gemma-2-27b-it` | vllm | google/gemma-2-27b-it at aaf20e6b9f4c | off | yes |
| Google | Gemma 4 E4B | open weights | `google/gemma-4-E4B-it` | vllm | google/gemma-4-E4B-it at 4ecc2ba63bca | off, default | yes |
| Google | Gemma 4 E2B | open weights | `google/gemma-4-E2B-it` | vllm | google/gemma-4-E2B-it at 4adf15748de9 | off, default | yes |
| DeepSeek | DeepSeek V3 | open weights | `deepseek-ai/DeepSeek-V3` | vllm | deepseek-ai/DeepSeek-V3 at e815299b0bcb | off | yes |
| DeepSeek | DeepSeek R1 | open weights | `deepseek-ai/DeepSeek-R1` | vllm | deepseek-ai/DeepSeek-R1 at 56d4cbbb4d29 | default | yes |
| DeepSeek | DeepSeek V4 Flash 0731 | open weights | `deepseek-ai/DeepSeek-V4-Flash-0731` | vllm | deepseek-ai/DeepSeek-V4-Flash-0731 at 7872f01b1d1f | off, default, max | yes |
| Zhipu | GLM-4.5-Air | open weights | `zai-org/GLM-4.5-Air-FP8` | vllm | zai-org/GLM-4.5-Air-FP8 at f9a9c5acf5e5 | off, default | yes |
| MiniMax | MiniMax M2 | open weights | `MiniMaxAI/MiniMax-M2` | vllm | MiniMaxAI/MiniMax-M2 at 2a6104622dd8 | default | yes |
| MiniMax | MiniMax M2.7 | open weights | `MiniMaxAI/MiniMax-M2.7` | vllm | MiniMaxAI/MiniMax-M2.7 at 0a6536713b0b | default | yes |
| Mistral | Mistral Small 3.2 24B | open weights | `mistralai/Mistral-Small-3.2-24B-Instruct-2506` | vllm | mistralai/Mistral-Small-3.2-24B-Instruct-2506 at 95a6d26c4bfb | off | yes |
| Mistral | Magistral Small 2509 | open weights | `mistralai/Magistral-Small-2509` | vllm | mistralai/Magistral-Small-2509 at a31cc96ab10c | default | yes |
| Mistral | Mistral Small 4 119B A6.5B | open weights | `mistralai/Mistral-Small-4-119B-2603` | vllm | mistralai/Mistral-Small-4-119B-2603 at 7ecb947bde38 | off, high | yes |
| Allen AI | OLMo 2 7B Instruct | open weights | `allenai/OLMo-2-1124-7B-Instruct` | vllm | allenai/OLMo-2-1124-7B-Instruct at 470b1fba1ae0 | off | yes |
| Allen AI | OLMo 2 32B Instruct | open weights | `allenai/OLMo-2-0325-32B-Instruct` | vllm | allenai/OLMo-2-0325-32B-Instruct at 6be039a1d9a0 | off | yes |
| Allen AI | Olmo Hybrid 7B Instruct | open weights | `allenai/Olmo-Hybrid-Instruct-DPO-7B` | vllm | allenai/Olmo-Hybrid-Instruct-DPO-7B at ec62da5af010 | off | yes |
| Microsoft | Phi-3.5-mini | open weights | `microsoft/Phi-3.5-mini-instruct` | vllm | microsoft/Phi-3.5-mini-instruct at 2fe192450127 | off | yes |
| Microsoft | Phi-4-reasoning 14B | open weights | `microsoft/Phi-4-reasoning` | vllm | microsoft/Phi-4-reasoning at 1de18ec97600 | default | yes |
| Microsoft | Phi-4-reasoning-vision 15B | open weights | `microsoft/Phi-4-reasoning-vision-15B` | vllm | microsoft/Phi-4-reasoning-vision-15B at c3e4fac79dda | off, default | yes |
| IBM | Granite 4.2 8B | open weights | `ibm-granite/granite-4.2-8b` | vllm | ibm-granite/granite-4.2-8b at a7042144125c | off, default | yes |
| NVIDIA | Nemotron Nano 9B v2 | open weights | `nvidia/NVIDIA-Nemotron-Nano-9B-v2` | vllm | nvidia/NVIDIA-Nemotron-Nano-9B-v2 at 6533e8de2c68 | off, default | yes |
| NVIDIA | Nemotron 3 Super 120B A12B | open weights | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8` | vllm | nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8 at 744b1880a379 | off, default, low | yes |
| NVIDIA | Nemotron 3.5 Lightning 30B A3B | open weights | `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16` | vllm | nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 at a9904d24bcc1 | off, default | yes |
| Baidu | ERNIE 5.5 Flash (preview) | open weights | `baidu/ERNIE-5.5-Flash-Preview-FP8` | vllm | baidu/ERNIE-5.5-Flash-Preview-FP8 at be26a1d08b61 | off, default, low | yes |
| Thinking Machines | Inkling 2 Mini | open weights | `thinkingmachines/Inkling-2-Mini` | vllm | thinkingmachines/Inkling-2-Mini at c9d028302cd0 | low, default, high | yes |
| Tencent | Hy4 Flash | open weights | `tencent/Hy4-flash-FP8` | vllm | tencent/Hy4-flash-FP8 at 8a1b19890d35 | off, default | yes |
| Tencent | Hy3 | open weights | `tencent/Hy3` | vllm | tencent/Hy3 at a960ebc3da32 | off, high, low | yes |
| Xiaomi | MiMo V2.6 Flash | open weights | `XiaomiMiMo/MiMo-V2.6-Flash-RL` | vllm | XiaomiMiMo/MiMo-V2.6-Flash-RL at f657ba2f7d24 | off, default | yes |
| StepFun | Step 3.5 Flash | open weights | `stepfun-ai/Step-3.5-Flash` | vllm | stepfun-ai/Step-3.5-Flash at ab446a3de5e1 | off, default | yes |
| Cohere | Command A+ | open weights | `CohereLabs/command-a-plus-05-2026-bf16` | vllm | CohereLabs/command-a-plus-05-2026-bf16 at 5fb6fde5fd12 | off, default | yes |
| Swiss AI | Apertus v1.5 8B | open weights | `swiss-ai/Apertus-v1.5-8B-RL` | vllm | swiss-ai/Apertus-v1.5-8B-RL at 59ae9fc39c91 | off | yes |
| LG | EXAONE 4.5 33B | open weights | `LGAI-EXAONE/EXAONE-4.5-33B` | vllm | LGAI-EXAONE/EXAONE-4.5-33B at 570aa4b15a4f | off, default | yes |
| ByteDance | Seed-OSS 36B | open weights | `ByteDance-Seed/Seed-OSS-36B-Instruct` | vllm | ByteDance-Seed/Seed-OSS-36B-Instruct at 497f1dca95eb | off, default | yes |

"Route" is where the program sends a call: a developer's own API; OpenRouter, fixed to one named host (and to the
numeric precision that the host states, where it states one), with no fallback to other hosts, so that the host
cannot change without notice; or a vLLM server that runs a model with open weights. The closed models of OpenAI,
Anthropic, Google, xAI and Mistral answer through their developers' batch services, except in the choice sequences,
which run live. Each model with open weights is fixed to a Hugging Face repository and a commit. Every call logs the
model id requested and the id that the provider returned, so a change of the model's version during data collection
shows in the data. In `run.py`, we fix in advance a substitution rule for what we
do if a provider withdraws a model before or during data collection.

"Settings run" lists the reasoning settings at which a model answers the neutral prompts, its lowest setting first.
We map the reasoning controls of each model onto five common settings: off; low, the lowest effort with reasoning on;
default, the setting that a user gets without changing anything; high; and maximum. `model_registry.json` contains the
parameters that each setting sends to each model.

## The conditions and the repeated calls

Each model effect is a share of choices over the planned variations of the prompt: the pre-registered option orders
and the three wordings of the question, and the twenty personas in the persona condition. At the provider's default
temperature, each call is one draw from the model's distribution of answers, so the neutral condition repeats every
prompt. Each call is separate, with no history of the conversation, except in the choice sequences.

- **The neutral condition (confirmatory, every model).** The model's lowest reasoning setting, which is off where the
  model allows it, and the provider's default temperature, or the temperature that the developer recommends. Each
  text prompt is called 10 times and each picture prompt 60 times, so a cell shown as pictures receives as many calls
  as a cell of three options shown as numbers. Only these calls enter the confirmatory estimates of the model effects.
- **The suspicion probe (confirmatory, every model).** A separate call for each choice set in each of the three
  wordings, which asks whether anything about the choice set is strategically constructed and which option was added
  to make another option look better or worse. The test of rational override uses these answers.
- **The reasoning comparison.** The neutral prompts at the model's other settings in the column "Settings run". How
  many times we call each prompt depends on the model's price per million output tokens, because the developers of
  closed models bill the hidden reasoning steps as output. For the models with open weights and the closed models
  that cost less than $3, we call each text prompt 5 times and each picture prompt 30 times (2 and 12 times at the
  maximum setting). For the closed models that cost $3 or more, we call each text prompt once and each picture prompt
  6 times.
- **The temperature check.** The neutral prompts again at temperatures of 0 and 1.0, at the lowest setting, on the
  models marked "yes" in the column "Temperature check". We report this check as a description, never as primary
  evidence.
- **The persona condition.** The neutral prompts with each of the twenty personas, one call for each prompt and
  persona, at the lowest setting, on the current closed models that cost less than $3 and one recent model from each
  developer of open models.
- **The choice sequences in one conversation.** 1,000 sequences of seven choices for each model, built from the human
  sequences of the main design, at the lowest setting.

`MANIFEST.md` gives the calls of every model in every condition. `model_registry.json` contains the exact settings sent
in each condition, and every call records them.

## Commands

None of these six commands calls a model:

```
python models/run.py --selftest        # checks the model settings, the prompt wording and every request
python models/selftest_mutants.py      # each broken builder of requests must fail the self-test
python models/build_manifest.py        # rewrites MANIFEST.md
python models/run.py --out-dir <dir>   # made-up replies, no network; writes model_log.jsonl, SAMPLE_CALLS.jsonl
python models/test_batch.py            # the batch services, made up, with no network
python models/test_vllm_route.py       # the route of the open models, against a made-up vLLM server
```

`python run_all.py --part models` runs the first four and checks the plan and the sample prompts against the copies
in this repository. Real calls (`python models/run.py --live ...` and `python models/batch.py submit ...`) need the
providers' API keys in the environment (OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY or GEMINI_API_KEY,
XAI_API_KEY, MISTRAL_API_KEY and OPENROUTER_API_KEY), a vLLM server for the models with open weights (its address in
VLLM_BASE_URL), and the `openai`, `anthropic` and `httpx` Python packages. We will make them only at Stage 2 (see
"The model responses at Stage 2" in the README at the root).
