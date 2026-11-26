# MODEL-CALL MANIFEST - exact plan from stimuli.json and the model registry 
(Computed from the final stimuli.json and model_registry.json by build_manifest.py. No API calls were made.)

**Stimuli (entries):** 165.  **Distinct neutral prompts (grid points) per model:** 3,537 for each of the 39 image-capable models (3,510 text prompts and 27 picture prompts) and 3,510 for each of the 67 text-only models, which run no picture cells (not applicable).  **Models:** 106 (21 closed models of the current generation, 10 of the previous generation, 75 with open weights), from 24 developers.

Picture cells run in the canonical option order only: the model receives the same whole-set PNG
the participants see, with the options labelled Option A, B, C in that order, and the human
picture arm never rotates it. Numbers, words and similarity
placements run every registered order.

Twelve-option extremity menus run twelve registered full shuffles of the twelve positions per menu
stimulus (mot_orders.json, drawn once from seed 20260929 and checked against it on every load),
the same kind of order the participants' menus get.

## Settings and repeated draws
Each model's reasoning controls are mapped onto five common settings: OFF, LOW (the lowest effort with
reasoning on), DEFAULT (what a user gets without changing anything), HIGH and MAX. The confirmatory
neutral grid runs at the model's lowest setting (OFF where reasoning can be switched off). At the
provider's default temperature each call is one draw from the model's answers, so a grid point is called
more than once; the number depends on the model's price per million output tokens (premium: $20 or more;
standard: $3 to $20; budget: under $3, and every open model). A picture prompt is called six times as
often as a text prompt, so a pictures cell (one order x 3 frames) holds as many calls as a three-option
numbers cell (6 orders x 3 frames). Each draw is a separate API call with no conversation history, every
call record holds its `draw_index` and its `setting`, and the plan is draw-major within each model.

| Price tier | models | draws a text prompt, lowest setting | at the default and high settings | other levels | three-option numbers cell, lowest setting |
|---|---|---|---|---|---|
| premium | 5 | 10 | 1 | - | 180 |
| standard | 2 | 10 | - | - | 180 |
| standard | 12 | 10 | 1 | - | 180 |
| budget | 32 | 10 | - | - | 180 |
| budget | 52 | 10 | 5 | - | 180 |
| budget | 3 | 10 | 5 | 2 | 180 |

Persona, temperature, sequential and recognition calls run once per grid point, at the lowest setting.

## Neutral prompts per model, by structure (distinct grid points)
| Structure | orders | image-capable model | text-only model |
|---|---|---|---|
| BIN | 2 | 153 | 144 |
| FRQ | 6 | 441 | 432 |
| RNG | 6 | 360 | 360 |
| PHT | 6 | 360 | 360 |
| SOT | 6 | 387 | 378 |
| SYM | 6 | 306 | 306 |
| SIM | 6 | 612 | 612 |
| MOT | 12 | 612 | 612 |
| EXC | 6 | 306 | 306 |
| **all** | | **3,537** | **3,510** |

## Calls by condition (all models)
| Condition | calls |
|---|---|
| Neutral at the lowest setting (confirmatory) | 3,783,780 |
| Neutral at the default and high settings (and low effort where reasoning can be switched off) | 1,299,186 |
| Neutral at the other reasoning levels | 21,708 |
| Persona (x20, lowest setting) | 2,111,400 |
| Temperature check (0 and 1.0, lowest setting) | 618,894 |
| Sequential 7-choice sessions | 742,000 |
| Recognition probe (per stimulus x3 paraphrases) | 52,470 |
| **TOTAL** | **8,629,438** |

## Calls per model
| Slot | Model | Group | Price tier | Lowest setting | Neutral, lowest setting | Other settings (setting: calls) | Persona | Temperature (2) | Sequential | Recognition | Model total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | GPT-6.2 Astra | closed current | premium | LOW | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 2 | GPT-6.2 Sol | closed current | standard | LOW | 36,720 | DEFAULT: 3,672; HIGH: 3,672 | - | - | 7,000 | 495 | 51,559 |
| 3 | GPT-6.1 Terra | closed current | standard | OFF | 36,720 | DEFAULT: 3,672; HIGH: 3,672 | - | 7,074 | 7,000 | 495 | 58,633 |
| 4 | GPT-6 Luna | closed current | budget | OFF | 36,720 | DEFAULT: 18,360; HIGH: 18,360; LOW: 18,360; MAX: 7,344 | 70,740 | 7,074 | 7,000 | 495 | 184,453 |
| 5 | Claude Fable 5.2 | closed current | premium | LOW | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 6 | Claude Opus 5.5 | closed current | premium | LOW | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 7 | Claude Sonnet 5.5 | closed current | standard | OFF | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 8 | Claude Haiku 5.5 | closed current | budget | OFF | 36,720 | DEFAULT: 18,360; HIGH: 18,360; LOW: 18,360; MAX: 7,344 | 70,740 | - | 7,000 | 495 | 177,379 |
| 9 | Gemini 4 Carbon | closed current | premium | LOW | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 10 | Gemini 4 Neon | closed current | standard | LOW | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 11 | Gemini 4 Hydrogen | closed current | standard | LOW | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 12 | Gemini 3.5 Flash-Lite | closed current | budget | LOW | 36,720 | HIGH: 18,360 | 70,740 | - | 7,000 | 495 | 133,315 |
| 13 | Grok 4.7 | closed current | standard | LOW | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 14 | Mistral Large 4 | closed current | budget | LOW | 36,720 | DEFAULT: 18,360; HIGH: 18,360 | 70,740 | 7,074 | 7,000 | 495 | 158,749 |
| 15 | Qwen4-Max | closed current | standard | OFF | 36,720 | DEFAULT: 3,672 | - | 7,074 | 7,000 | 495 | 54,961 |
| 16 | Qwen3.8-Flash | closed current | budget | OFF | 36,720 | DEFAULT: 18,360; LOW: 18,360 | 70,740 | 7,074 | 7,000 | 495 | 158,749 |
| 17 | DeepSeek V4 Pro | closed current | budget | OFF | 35,100 | DEFAULT: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 18 | GLM-5.4 (GLM-5.3 until its API opens) | closed current | standard | OFF | 35,100 | DEFAULT: 3,510 | - | 7,020 | 7,000 | 495 | 53,125 |
| 19 | MiniMax M3.1 Flash | closed current | budget | OFF | 36,720 | DEFAULT: 18,360 | 70,740 | 7,074 | 7,000 | 495 | 140,389 |
| 20 | Seed 2.1 Turbo | closed current | budget | OFF | 36,720 | DEFAULT: 18,360 | 70,740 | 7,074 | 7,000 | 495 | 140,389 |
| 21 | Muse Wonder | closed current | premium | LOW | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 22 | GPT-5.6 Luna | closed previous | budget | OFF | 36,720 | DEFAULT: 18,360 | - | 7,074 | 7,000 | 495 | 69,649 |
| 23 | GPT-5.4 mini | closed previous | standard | OFF | 36,720 | - | - | 7,074 | 7,000 | 495 | 51,289 |
| 24 | Claude Haiku 4.5 | closed previous | standard | OFF | 36,720 | - | - | - | 7,000 | 495 | 44,215 |
| 25 | Claude Sonnet 5 | closed previous | standard | OFF | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 26 | Gemini 3 Flash | closed previous | standard | LOW | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 27 | Gemini 2.5 Flash-Lite | closed previous | budget | OFF | 36,720 | - | - | 7,074 | 7,000 | 495 | 51,289 |
| 28 | Gemini 3.1 Pro | closed previous | standard | LOW | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 29 | Grok 4.3 | closed previous | budget | LOW | 36,720 | DEFAULT: 18,360 | - | - | 7,000 | 495 | 62,575 |
| 30 | Qwen3.8-Max | closed previous | standard | LOW | 36,720 | DEFAULT: 3,672 | - | - | 7,000 | 495 | 47,887 |
| 31 | MiniMax M3 | closed previous | budget | OFF | 36,720 | DEFAULT: 18,360 | - | 7,074 | 7,000 | 495 | 69,649 |
| 32 | Qwen 2.5 7B Instruct | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 33 | Qwen 2.5 32B Instruct | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 34 | Qwen3 30B A3B Instruct 2507 | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 35 | Qwen3 32B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 36 | Qwen3.5 0.8B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 37 | Qwen3.5 2B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 38 | Qwen3.5 4B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 39 | Qwen3.5 9B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 40 | Qwen3.5 27B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 41 | Qwen3.5 35B A3B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 42 | Qwen3.5 122B A10B FP8 | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 43 | Qwen3.6 27B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 44 | Qwen3.8 27B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 45 | Llama 3.2 3B Instruct | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 46 | Llama 3.1 8B Instruct | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 47 | Gemma 3 27B | open | budget | OFF | 36,720 | - | - | 7,074 | 7,000 | 495 | 51,289 |
| 48 | Gemma 4 12B | open | budget | OFF | 36,720 | DEFAULT: 18,360 | - | 7,074 | 7,000 | 495 | 69,649 |
| 49 | Gemma 4 26B A4B | open | budget | OFF | 36,720 | DEFAULT: 18,360 | - | 7,074 | 7,000 | 495 | 69,649 |
| 50 | Gemma 4 31B | open | budget | OFF | 36,720 | DEFAULT: 18,360 | 70,740 | 7,074 | 7,000 | 495 | 140,389 |
| 51 | OLMo 3 7B Instruct | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 52 | OLMo 3.1 32B Instruct | open | budget | OFF | 35,100 | - | 70,200 | 7,020 | 7,000 | 495 | 119,815 |
| 53 | gpt-oss 20B | open | budget | LOW | 35,100 | DEFAULT: 17,550; HIGH: 17,550 | - | 7,020 | 7,000 | 495 | 84,715 |
| 54 | gpt-oss 120B | open | budget | LOW | 35,100 | DEFAULT: 17,550; HIGH: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 154,915 |
| 55 | Ministral 3 14B | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 56 | Phi-4 | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 57 | Granite 4.1 30B | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 58 | Granite 4.2 30B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 59 | Nemotron 3 Nano 30B A3B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 60 | GLM-4.7-Flash | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 61 | ERNIE 4.5 21B A3B | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 62 | Marin 8B Instruct | open | budget | OFF | 35,100 | - | 70,200 | 7,020 | 7,000 | 495 | 119,815 |
| 63 | DeepSeek V4.1 Flash | open | budget | OFF | 35,100 | DEFAULT: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 64 | GLM-5.3-Flash FP8 | open | budget | LOW | 35,100 | DEFAULT: 17,550; HIGH: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 154,915 |
| 65 | Qwen 2.5 72B Instruct | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 66 | Qwen3 235B A22B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 67 | Qwen3-Next 80B A3B Instruct | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 68 | Qwen3.6 35B A3B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 69 | Qwen3.5 397B A17B FP8 | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 70 | Qwen3.8-Flash-Next | open | budget | OFF | 35,100 | DEFAULT: 17,550; LOW: 17,550 | - | 7,020 | 7,000 | 495 | 84,715 |
| 71 | Llama 3.3 70B Instruct | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 72 | Llama 4 Scout 17B-16E | open | budget | OFF | 36,720 | - | - | 7,074 | 7,000 | 495 | 51,289 |
| 73 | Llama 4 Maverick 17B-128E FP8 | open | budget | OFF | 36,720 | - | - | 7,074 | 7,000 | 495 | 51,289 |
| 74 | Muse Glimmer 30B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 75 | Gemma 2 27B | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 76 | Gemma 4 E4B | open | budget | OFF | 36,720 | DEFAULT: 18,360 | - | 7,074 | 7,000 | 495 | 69,649 |
| 77 | Gemma 4 E2B | open | budget | OFF | 36,720 | DEFAULT: 18,360 | - | 7,074 | 7,000 | 495 | 69,649 |
| 78 | DeepSeek V3 | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 79 | DeepSeek R1 | open | budget | DEFAULT | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 80 | DeepSeek V4 Flash 0731 | open | budget | OFF | 35,100 | DEFAULT: 17,550; MAX: 7,020 | - | 7,020 | 7,000 | 495 | 74,185 |
| 81 | GLM-4.5-Air | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 82 | MiniMax M2 | open | budget | DEFAULT | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 83 | MiniMax M2.7 | open | budget | DEFAULT | 35,100 | - | 70,200 | 7,020 | 7,000 | 495 | 119,815 |
| 84 | Mistral Small 3.2 24B | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 85 | Magistral Small 2509 | open | budget | DEFAULT | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 86 | Mistral Small 4 119B A6.5B | open | budget | OFF | 35,100 | HIGH: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 87 | OLMo 2 7B Instruct | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 88 | OLMo 2 32B Instruct | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 89 | Olmo Hybrid 7B Instruct | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 90 | Phi-3.5-mini | open | budget | OFF | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 91 | Phi-4-reasoning 14B | open | budget | DEFAULT | 35,100 | - | - | 7,020 | 7,000 | 495 | 49,615 |
| 92 | Phi-4-reasoning-vision 15B | open | budget | OFF | 36,720 | DEFAULT: 18,360 | 70,740 | 7,074 | 7,000 | 495 | 140,389 |
| 93 | Granite 4.2 8B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 94 | Nemotron Nano 9B v2 | open | budget | OFF | 35,100 | DEFAULT: 17,550 | - | 7,020 | 7,000 | 495 | 67,165 |
| 95 | Nemotron 3 Super 120B A12B | open | budget | OFF | 35,100 | DEFAULT: 17,550; LOW: 17,550 | - | 7,020 | 7,000 | 495 | 84,715 |
| 96 | Nemotron 3.5 Lightning 30B A3B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 97 | ERNIE 5.5 Flash (preview) | open | budget | OFF | 35,100 | DEFAULT: 17,550; LOW: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 154,915 |
| 98 | Inkling 2 Mini | open | budget | LOW | 35,100 | DEFAULT: 17,550; HIGH: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 154,915 |
| 99 | Hy4 Flash | open | budget | OFF | 35,100 | DEFAULT: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 100 | Hy3 | open | budget | OFF | 35,100 | HIGH: 17,550; LOW: 17,550 | - | 7,020 | 7,000 | 495 | 84,715 |
| 101 | MiMo V2.6 Flash | open | budget | OFF | 35,100 | DEFAULT: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 102 | Step 3.5 Flash | open | budget | OFF | 35,100 | DEFAULT: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 103 | Command A+ | open | budget | OFF | 36,720 | DEFAULT: 18,360 | 70,740 | 7,074 | 7,000 | 495 | 140,389 |
| 104 | Apertus v1.5 8B | open | budget | OFF | 35,100 | - | 70,200 | 7,020 | 7,000 | 495 | 119,815 |
| 105 | EXAONE 4.5 33B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 106 | Seed-OSS 36B | open | budget | OFF | 35,100 | DEFAULT: 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| | **all** | | | | **3,783,780** | **1,320,894** | **2,111,400** | **618,894** | **742,000** | **52,470** | **8,629,438** |

## The models these counts run on (model_registry.json; roster of 2026-11-24)
| Slot | Model | Developer | Generation | Route | Id sent | Open weights (repository at revision) | Settings offered | Pictures |
|---|---|---|---|---|---|---|---|---|
| 1 | GPT-6.2 Astra | OpenAI | new | openai | `gpt-6.2-astra` |  | LOW, DEFAULT, HIGH, MAX | yes |
| 2 | GPT-6.2 Sol | OpenAI | new | openai | `gpt-6.2-sol` |  | LOW, DEFAULT, HIGH, MAX | yes |
| 3 | GPT-6.1 Terra | OpenAI | new | openai | `gpt-6.1-terra` |  | OFF, LOW, DEFAULT, HIGH, MAX | yes |
| 4 | GPT-6 Luna | OpenAI | new | openai | `gpt-6-luna` |  | OFF, LOW, DEFAULT, HIGH, MAX | yes |
| 5 | Claude Fable 5.2 | Anthropic | new | anthropic | `claude-fable-5-2` |  | LOW, DEFAULT, MAX | yes |
| 6 | Claude Opus 5.5 | Anthropic | new | anthropic | `claude-opus-5-5` |  | LOW, DEFAULT, HIGH, MAX | yes |
| 7 | Claude Sonnet 5.5 | Anthropic | new | anthropic | `claude-sonnet-5-5` |  | OFF, LOW, DEFAULT, MAX | yes |
| 8 | Claude Haiku 5.5 | Anthropic | new | anthropic | `claude-haiku-5-5` |  | OFF, LOW, DEFAULT, HIGH, MAX | yes |
| 9 | Gemini 4 Carbon | Google | new | google | `gemini-4-carbon` |  | LOW, DEFAULT, HIGH | yes |
| 10 | Gemini 4 Neon | Google | new | google | `gemini-4-neon` |  | LOW, DEFAULT, MAX | yes |
| 11 | Gemini 4 Hydrogen | Google | new | google | `gemini-4-hydrogen` |  | LOW, DEFAULT, MAX | yes |
| 12 | Gemini 3.5 Flash-Lite | Google | new | google | `gemini-3.5-flash-lite` |  | LOW, HIGH | yes |
| 13 | Grok 4.7 | xAI | new | xai | `grok-4.7` |  | LOW, DEFAULT, MAX | yes |
| 14 | Mistral Large 4 | Mistral | new | mistral | `mistral-large-2610` |  | LOW, DEFAULT, HIGH | yes |
| 15 | Qwen4-Max | Alibaba | new | openrouter via host alibaba | `qwen/qwen4-max` |  | OFF, LOW, DEFAULT, MAX | yes |
| 16 | Qwen3.8-Flash | Alibaba | new | openrouter via host alibaba | `qwen/qwen3.8-flash` |  | OFF, LOW, DEFAULT | yes |
| 17 | DeepSeek V4 Pro | DeepSeek | new | openrouter via host deepseek | `deepseek/deepseek-v4-pro` |  | OFF, DEFAULT | not applicable (text only) |
| 18 | GLM-5.4 (GLM-5.3 until its API opens) | Zhipu | new | openrouter via host z-ai | `z-ai/glm-5.4` |  | OFF, DEFAULT | not applicable (text only) |
| 19 | MiniMax M3.1 Flash | MiniMax | new | openrouter via host minimax | `minimax/minimax-m3.1-flash` |  | OFF, DEFAULT | yes |
| 20 | Seed 2.1 Turbo | ByteDance | new | openrouter via host bytedance | `bytedance-seed/seed-2-1-turbo` |  | OFF, DEFAULT | yes |
| 21 | Muse Wonder | Meta | new | openrouter via host meta | `meta/muse-wonder` |  | LOW, DEFAULT, HIGH | yes |
| 22 | GPT-5.6 Luna | OpenAI | old | openai | `gpt-5.6-luna` |  | OFF, LOW, DEFAULT, HIGH, MAX | yes |
| 23 | GPT-5.4 mini | OpenAI | old | openai | `gpt-5.4-mini` |  | OFF, LOW, HIGH | yes |
| 24 | Claude Haiku 4.5 | Anthropic | old | anthropic | `claude-haiku-4-5-20251001` |  | OFF | yes |
| 25 | Claude Sonnet 5 | Anthropic | old | anthropic | `claude-sonnet-5` |  | OFF, LOW, DEFAULT, MAX | yes |
| 26 | Gemini 3 Flash | Google | old | google | `gemini-3-flash-preview` |  | LOW, DEFAULT | yes |
| 27 | Gemini 2.5 Flash-Lite | Google | old | google | `gemini-2.5-flash-lite` |  | OFF | yes |
| 28 | Gemini 3.1 Pro | Google | old | google | `gemini-3.1-pro-preview` |  | LOW, DEFAULT | yes |
| 29 | Grok 4.3 | xAI | old | xai | `grok-4.3` |  | LOW, DEFAULT | yes |
| 30 | Qwen3.8-Max | Alibaba | old | openrouter via host alibaba | `qwen/qwen3.8-max-0902` |  | LOW, DEFAULT | yes |
| 31 | MiniMax M3 | MiniMax | old | openrouter via host minimax | `minimax/minimax-m3` |  | OFF, DEFAULT | yes |
| 32 | Qwen 2.5 7B Instruct | Alibaba | old | vllm | `Qwen/Qwen2.5-7B-Instruct` | Qwen/Qwen2.5-7B-Instruct at a09a35458c70 | OFF | not applicable (text only) |
| 33 | Qwen 2.5 32B Instruct | Alibaba | old | vllm | `Qwen/Qwen2.5-32B-Instruct` | Qwen/Qwen2.5-32B-Instruct at 5ede1c97bbab | OFF | not applicable (text only) |
| 34 | Qwen3 30B A3B Instruct 2507 | Alibaba | old | vllm | `Qwen/Qwen3-30B-A3B-Instruct-2507` | Qwen/Qwen3-30B-A3B-Instruct-2507 at 0d7cf23991f4 | OFF | not applicable (text only) |
| 35 | Qwen3 32B | Alibaba | old | vllm | `Qwen/Qwen3-32B` | Qwen/Qwen3-32B at 9216db5781bf | OFF, DEFAULT | not applicable (text only) |
| 36 | Qwen3.5 0.8B | Alibaba | old | vllm | `Qwen/Qwen3.5-0.8B` | Qwen/Qwen3.5-0.8B at 2fc06364715b | OFF, DEFAULT | not applicable (text only) |
| 37 | Qwen3.5 2B | Alibaba | old | vllm | `Qwen/Qwen3.5-2B` | Qwen/Qwen3.5-2B at 15852e8c1636 | OFF, DEFAULT | not applicable (text only) |
| 38 | Qwen3.5 4B | Alibaba | old | vllm | `Qwen/Qwen3.5-4B` | Qwen/Qwen3.5-4B at 851bf6e806ef | OFF, DEFAULT | not applicable (text only) |
| 39 | Qwen3.5 9B | Alibaba | old | vllm | `Qwen/Qwen3.5-9B` | Qwen/Qwen3.5-9B at c20223623576 | OFF, DEFAULT | not applicable (text only) |
| 40 | Qwen3.5 27B | Alibaba | old | vllm | `Qwen/Qwen3.5-27B` | Qwen/Qwen3.5-27B at 81a287ca484a | OFF, DEFAULT | not applicable (text only) |
| 41 | Qwen3.5 35B A3B | Alibaba | old | vllm | `Qwen/Qwen3.5-35B-A3B` | Qwen/Qwen3.5-35B-A3B at 2508b2437e38 | OFF, DEFAULT | not applicable (text only) |
| 42 | Qwen3.5 122B A10B FP8 | Alibaba | old | vllm | `Qwen/Qwen3.5-122B-A10B-FP8` | Qwen/Qwen3.5-122B-A10B-FP8 at a099dee70ccf | OFF, DEFAULT | not applicable (text only) |
| 43 | Qwen3.6 27B | Alibaba | old | vllm | `Qwen/Qwen3.6-27B` | Qwen/Qwen3.6-27B at 1cda14dd71a3 | OFF, DEFAULT | not applicable (text only) |
| 44 | Qwen3.8 27B | Alibaba | new | vllm | `Qwen/Qwen3.8-27B` | Qwen/Qwen3.8-27B at 1d4bf0f2ff60 | OFF, DEFAULT | not applicable (text only) |
| 45 | Llama 3.2 3B Instruct | Meta | old | vllm | `unsloth/Llama-3.2-3B-Instruct` | unsloth/Llama-3.2-3B-Instruct at 006f5dcd1393 | OFF | not applicable (text only) |
| 46 | Llama 3.1 8B Instruct | Meta | old | vllm | `unsloth/Llama-3.1-8B-Instruct` | unsloth/Llama-3.1-8B-Instruct at 4699cc75b550 | OFF | not applicable (text only) |
| 47 | Gemma 3 27B | Google | old | vllm | `unsloth/gemma-3-27b-it` | unsloth/gemma-3-27b-it at 7a5a3053dbd5 | OFF | yes |
| 48 | Gemma 4 12B | Google | new | vllm | `google/gemma-4-12B-it` | google/gemma-4-12B-it at 43c9d014b231 | OFF, DEFAULT | yes |
| 49 | Gemma 4 26B A4B | Google | new | vllm | `google/gemma-4-26B-A4B-it` | google/gemma-4-26B-A4B-it at 4d7ae4984b7d | OFF, DEFAULT | yes |
| 50 | Gemma 4 31B | Google | new | vllm | `unsloth/gemma-4-31b-it` | unsloth/gemma-4-31b-it at 51c9f6265ea3 | OFF, DEFAULT | yes |
| 51 | OLMo 3 7B Instruct | Allen AI | old | vllm | `allenai/Olmo-3-7B-Instruct` | allenai/Olmo-3-7B-Instruct at 6e5971d9eba4 | OFF | not applicable (text only) |
| 52 | OLMo 3.1 32B Instruct | Allen AI | old | vllm | `allenai/Olmo-3.1-32B-Instruct` | allenai/Olmo-3.1-32B-Instruct at ac0587e4a774 | OFF | not applicable (text only) |
| 53 | gpt-oss 20B | OpenAI | new | vllm | `openai/gpt-oss-20b` | openai/gpt-oss-20b at 6cee5e81ee83 | LOW, DEFAULT, HIGH | not applicable (text only) |
| 54 | gpt-oss 120B | OpenAI | new | vllm | `openai/gpt-oss-120b` | openai/gpt-oss-120b at b5c939de8f75 | LOW, DEFAULT, HIGH | not applicable (text only) |
| 55 | Ministral 3 14B | Mistral | old | vllm | `mistralai/Ministral-3-14B-Instruct-2512-BF16` | mistralai/Ministral-3-14B-Instruct-2512-BF16 at 3cea74c1ebaf | OFF | not applicable (text only) |
| 56 | Phi-4 | Microsoft | old | vllm | `microsoft/phi-4` | microsoft/phi-4 at 2db69c1c3e91 | OFF | not applicable (text only) |
| 57 | Granite 4.1 30B | IBM | old | vllm | `ibm-granite/granite-4.1-30b` | ibm-granite/granite-4.1-30b at 4fae6278f713 | OFF | not applicable (text only) |
| 58 | Granite 4.2 30B | IBM | new | vllm | `ibm-granite/granite-4.2-30b` | ibm-granite/granite-4.2-30b at 9e668ce1c538 | OFF, DEFAULT | not applicable (text only) |
| 59 | Nemotron 3 Nano 30B A3B | NVIDIA | old | vllm | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` | nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 at bf77c3174f68 | OFF, DEFAULT | not applicable (text only) |
| 60 | GLM-4.7-Flash | Zhipu | old | vllm | `zai-org/GLM-4.7-Flash` | zai-org/GLM-4.7-Flash at 7dd20894a642 | OFF, DEFAULT | not applicable (text only) |
| 61 | ERNIE 4.5 21B A3B | Baidu | old | vllm | `baidu/ERNIE-4.5-21B-A3B-PT` | baidu/ERNIE-4.5-21B-A3B-PT at 87db95487941 | OFF | not applicable (text only) |
| 62 | Marin 8B Instruct | Marin | new | vllm | `marin-community/marin-8b-instruct` | marin-community/marin-8b-instruct at 0378f9c932bd | OFF | not applicable (text only) |
| 63 | DeepSeek V4.1 Flash | DeepSeek | new | vllm | `deepseek-ai/DeepSeek-V4.1-Flash` | deepseek-ai/DeepSeek-V4.1-Flash at 314113f8a7da | OFF, DEFAULT | not applicable (text only) |
| 64 | GLM-5.3-Flash FP8 | Zhipu | new | vllm | `zai-org/GLM-5.3-Flash` | zai-org/GLM-5.3-Flash at 46a050bec130 | LOW, HIGH, DEFAULT | not applicable (text only) |
| 65 | Qwen 2.5 72B Instruct | Alibaba | old | vllm | `Qwen/Qwen2.5-72B-Instruct` | Qwen/Qwen2.5-72B-Instruct at 495f39366efe | OFF | not applicable (text only) |
| 66 | Qwen3 235B A22B | Alibaba | old | vllm | `Qwen/Qwen3-235B-A22B-FP8` | Qwen/Qwen3-235B-A22B-FP8 at 39eb2b067ea6 | OFF, DEFAULT | not applicable (text only) |
| 67 | Qwen3-Next 80B A3B Instruct | Alibaba | old | vllm | `Qwen/Qwen3-Next-80B-A3B-Instruct` | Qwen/Qwen3-Next-80B-A3B-Instruct at 9c7f2fbe8446 | OFF | not applicable (text only) |
| 68 | Qwen3.6 35B A3B | Alibaba | old | vllm | `Qwen/Qwen3.6-35B-A3B` | Qwen/Qwen3.6-35B-A3B at 345d467b117d | OFF, DEFAULT | not applicable (text only) |
| 69 | Qwen3.5 397B A17B FP8 | Alibaba | old | vllm | `Qwen/Qwen3.5-397B-A17B-FP8` | Qwen/Qwen3.5-397B-A17B-FP8 at ea5b4f81096f | OFF, DEFAULT | not applicable (text only) |
| 70 | Qwen3.8-Flash-Next | Alibaba | new | vllm | `Qwen/Qwen3.8-Flash-Next-FP8` | Qwen/Qwen3.8-Flash-Next-FP8 at 7fb48d708ca6 | OFF, LOW, DEFAULT | not applicable (text only) |
| 71 | Llama 3.3 70B Instruct | Meta | old | vllm | `meta-llama/Llama-3.3-70B-Instruct` | meta-llama/Llama-3.3-70B-Instruct at 6f6073b42301 | OFF | not applicable (text only) |
| 72 | Llama 4 Scout 17B-16E | Meta | old | vllm | `meta-llama/Llama-4-Scout-17B-16E-Instruct` | meta-llama/Llama-4-Scout-17B-16E-Instruct at 92f3b1597a19 | OFF | yes |
| 73 | Llama 4 Maverick 17B-128E FP8 | Meta | old | vllm | `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8` | meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8 at 94125d2bd830 | OFF | yes |
| 74 | Muse Glimmer 30B | Meta | new | vllm | `meta-models/Muse-Glimmer-30B` | meta-models/Muse-Glimmer-30B at 1297fd7dfeac | OFF, DEFAULT | not applicable (text only) |
| 75 | Gemma 2 27B | Google | old | vllm | `google/gemma-2-27b-it` | google/gemma-2-27b-it at aaf20e6b9f4c | OFF | not applicable (text only) |
| 76 | Gemma 4 E4B | Google | new | vllm | `google/gemma-4-E4B-it` | google/gemma-4-E4B-it at 4ecc2ba63bca | OFF, DEFAULT | yes |
| 77 | Gemma 4 E2B | Google | new | vllm | `google/gemma-4-E2B-it` | google/gemma-4-E2B-it at 4adf15748de9 | OFF, DEFAULT | yes |
| 78 | DeepSeek V3 | DeepSeek | old | vllm | `deepseek-ai/DeepSeek-V3` | deepseek-ai/DeepSeek-V3 at e815299b0bcb | OFF | not applicable (text only) |
| 79 | DeepSeek R1 | DeepSeek | old | vllm | `deepseek-ai/DeepSeek-R1` | deepseek-ai/DeepSeek-R1 at 56d4cbbb4d29 | DEFAULT | not applicable (text only) |
| 80 | DeepSeek V4 Flash 0731 | DeepSeek | old | vllm | `deepseek-ai/DeepSeek-V4-Flash-0731` | deepseek-ai/DeepSeek-V4-Flash-0731 at 7872f01b1d1f | OFF, DEFAULT, MAX | not applicable (text only) |
| 81 | GLM-4.5-Air | Zhipu | old | vllm | `zai-org/GLM-4.5-Air-FP8` | zai-org/GLM-4.5-Air-FP8 at f9a9c5acf5e5 | OFF, DEFAULT | not applicable (text only) |
| 82 | MiniMax M2 | MiniMax | old | vllm | `MiniMaxAI/MiniMax-M2` | MiniMaxAI/MiniMax-M2 at 2a6104622dd8 | DEFAULT | not applicable (text only) |
| 83 | MiniMax M2.7 | MiniMax | new | vllm | `MiniMaxAI/MiniMax-M2.7` | MiniMaxAI/MiniMax-M2.7 at 0a6536713b0b | DEFAULT | not applicable (text only) |
| 84 | Mistral Small 3.2 24B | Mistral | old | vllm | `mistralai/Mistral-Small-3.2-24B-Instruct-2506` | mistralai/Mistral-Small-3.2-24B-Instruct-2506 at 95a6d26c4bfb | OFF | not applicable (text only) |
| 85 | Magistral Small 2509 | Mistral | old | vllm | `mistralai/Magistral-Small-2509` | mistralai/Magistral-Small-2509 at a31cc96ab10c | DEFAULT | not applicable (text only) |
| 86 | Mistral Small 4 119B A6.5B | Mistral | new | vllm | `mistralai/Mistral-Small-4-119B-2603` | mistralai/Mistral-Small-4-119B-2603 at 7ecb947bde38 | OFF, HIGH | not applicable (text only) |
| 87 | OLMo 2 7B Instruct | Allen AI | old | vllm | `allenai/OLMo-2-1124-7B-Instruct` | allenai/OLMo-2-1124-7B-Instruct at 470b1fba1ae0 | OFF | not applicable (text only) |
| 88 | OLMo 2 32B Instruct | Allen AI | old | vllm | `allenai/OLMo-2-0325-32B-Instruct` | allenai/OLMo-2-0325-32B-Instruct at 6be039a1d9a0 | OFF | not applicable (text only) |
| 89 | Olmo Hybrid 7B Instruct | Allen AI | new | vllm | `allenai/Olmo-Hybrid-Instruct-DPO-7B` | allenai/Olmo-Hybrid-Instruct-DPO-7B at ec62da5af010 | OFF | not applicable (text only) |
| 90 | Phi-3.5-mini | Microsoft | old | vllm | `microsoft/Phi-3.5-mini-instruct` | microsoft/Phi-3.5-mini-instruct at 2fe192450127 | OFF | not applicable (text only) |
| 91 | Phi-4-reasoning 14B | Microsoft | old | vllm | `microsoft/Phi-4-reasoning` | microsoft/Phi-4-reasoning at 1de18ec97600 | DEFAULT | not applicable (text only) |
| 92 | Phi-4-reasoning-vision 15B | Microsoft | new | vllm | `microsoft/Phi-4-reasoning-vision-15B` | microsoft/Phi-4-reasoning-vision-15B at c3e4fac79dda | OFF, DEFAULT | yes |
| 93 | Granite 4.2 8B | IBM | new | vllm | `ibm-granite/granite-4.2-8b` | ibm-granite/granite-4.2-8b at a7042144125c | OFF, DEFAULT | not applicable (text only) |
| 94 | Nemotron Nano 9B v2 | NVIDIA | old | vllm | `nvidia/NVIDIA-Nemotron-Nano-9B-v2` | nvidia/NVIDIA-Nemotron-Nano-9B-v2 at 6533e8de2c68 | OFF, DEFAULT | not applicable (text only) |
| 95 | Nemotron 3 Super 120B A12B | NVIDIA | old | vllm | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8` | nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8 at 744b1880a379 | OFF, LOW, DEFAULT | not applicable (text only) |
| 96 | Nemotron 3.5 Lightning 30B A3B | NVIDIA | new | vllm | `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16` | nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 at a9904d24bcc1 | OFF, DEFAULT | not applicable (text only) |
| 97 | ERNIE 5.5 Flash (preview) | Baidu | new | vllm | `baidu/ERNIE-5.5-Flash-Preview-FP8` | baidu/ERNIE-5.5-Flash-Preview-FP8 at be26a1d08b61 | OFF, LOW, DEFAULT | not applicable (text only) |
| 98 | Inkling 2 Mini | Thinking Machines | new | vllm | `thinkingmachines/Inkling-2-Mini` | thinkingmachines/Inkling-2-Mini at c9d028302cd0 | LOW, DEFAULT, HIGH | not applicable (text only) |
| 99 | Hy4 Flash | Tencent | new | vllm | `tencent/Hy4-flash-FP8` | tencent/Hy4-flash-FP8 at 8a1b19890d35 | OFF, DEFAULT | not applicable (text only) |
| 100 | Hy3 | Tencent | old | vllm | `tencent/Hy3` | tencent/Hy3 at a960ebc3da32 | OFF, LOW, HIGH | not applicable (text only) |
| 101 | MiMo V2.6 Flash | Xiaomi | new | vllm | `XiaomiMiMo/MiMo-V2.6-Flash-RL` | XiaomiMiMo/MiMo-V2.6-Flash-RL at f657ba2f7d24 | OFF, DEFAULT | not applicable (text only) |
| 102 | Step 3.5 Flash | StepFun | new | vllm | `stepfun-ai/Step-3.5-Flash` | stepfun-ai/Step-3.5-Flash at ab446a3de5e1 | OFF, DEFAULT | not applicable (text only) |
| 103 | Command A+ | Cohere | new | vllm | `CohereLabs/command-a-plus-05-2026-bf16` | CohereLabs/command-a-plus-05-2026-bf16 at 5fb6fde5fd12 | OFF, DEFAULT | yes |
| 104 | Apertus v1.5 8B | Swiss AI | new | vllm | `swiss-ai/Apertus-v1.5-8B-RL` | swiss-ai/Apertus-v1.5-8B-RL at 59ae9fc39c91 | OFF | not applicable (text only) |
| 105 | EXAONE 4.5 33B | LG | new | vllm | `LGAI-EXAONE/EXAONE-4.5-33B` | LGAI-EXAONE/EXAONE-4.5-33B at 570aa4b15a4f | OFF, DEFAULT | not applicable (text only) |
| 106 | Seed-OSS 36B | ByteDance | new | vllm | `ByteDance-Seed/Seed-OSS-36B-Instruct` | ByteDance-Seed/Seed-OSS-36B-Instruct at 497f1dca95eb | OFF, DEFAULT | not applicable (text only) |

Build check: the registry passes run.py's validate_registry, or this script refuses to write the manifest.
`python run.py --count` enumerates every call from the runner's own generator and must agree with every
row above.

The runner executes this plan and can resume an interrupted run. The model calls run at Stage 2,
after in-principle acceptance.
