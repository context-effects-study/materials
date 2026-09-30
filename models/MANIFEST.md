# MODEL-CALL MANIFEST - exact plan from stimuli.json 
(Computed from the final stimuli.json by build_manifest.py. No API calls were made.)

**Stimuli (entries):** 165.  **Distinct neutral prompts (grid points) per model:** 3,537 for each of the 8 image-capable slots (3,510 text prompts and 27 picture prompts) and 3,510 for each text-only slot (DeepSeek V4 Pro (GA, 0813), DeepSeek R1), which run no picture cells (not applicable).  **Neutral-arm calls per slot:** 36,720 (image-capable) and 35,100 (text-only).  **Primary lineup:** 10 models.

Picture cells run in the canonical option order only: the model receives the same whole-set PNG
the participants see, with the options labelled Option A, B, C in that order, and the human
picture arm never rotates it. Numbers, words and similarity
placements run every registered order.

Twelve-option extremity menus run twelve registered full shuffles of the twelve positions per menu
stimulus (mot_orders.json, drawn once from seed 20260929 and checked against it on every load),
the same kind of order the participants' menus get; until 2026-09-29 they ran orders that kept each
quality level in a block of positions. Still twelve orders per menu, so no count changes.

## Repeated draws per grid point (registered 2026-09-29)
At the provider's default temperature each call is one draw from the model's answers, so the
confirmatory arm calls every grid point more than once. Each draw is a separate API call with no
conversation history, and every call record carries its `draw_index` (0 in the arms that do not
repeat). The plan is draw-major within each model: the whole grid at draw 0, then at draw 1, and so on.

| Arm | calls per text grid point | calls per picture prompt | three-option numbers cell | pictures cell |
|---|---|---|---|---|
| Neutral (confirmatory) | 10 | 60 | 180 | 180 |
| Reasoning contrast, high side | 5 | 30 | 90 | 90 |
| Persona, temperature, sequential, recognition | 1 | 1 | | |

A three-option numbers cell is 6 orders x 3 frames; a pictures cell is one order x 3 frames.

## Neutral prompts per model, by structure (distinct grid points)
| Structure | orders | image-capable slot | text-only slot |
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

## Calls by arm (primary lineup)
| Arm | calls | arithmetic |
|---|---|---|
| Neutral (confirmatory grid, 10 draws; 60 per picture prompt) | 363,960 | 8 x (3,510 x 10 + 27 x 60) + 2 x (3,510 x 10) |
| Persona (x20) | 706,320 | 20 x (8 x 3,537 + 2 x 3,510) |
| Reasoning contrast (5 slots, high side, 5 draws; 30 per picture prompt) | 90,990 | 4 x (3,510 x 5 + 27 x 30) + 3,510 x 5 |
| Temperature robustness (7 models x 2 temps, neutral) | 49,410 | 2 x (5 x 3,537 + 2 x 3,510) |
| Sequential 7-choice sessions | 70,000 | 1,000 x 7 x 10 |
| Recognition probe (per stimulus x3 paraphrases) | 4,950 | 165 x 3 x 10 |
| **TOTAL** | **1,285,630** | |

## Calls per slot
| Slot | Model | Neutral | Reasoning contrast | Persona | Temperature (2 temps) | Sequential | Recognition | Slot total |
|---|---|---|---|---|---|---|---|---|
| 1 | GPT-6 Astra | 36,720 | 18,360 | 70,740 | - | 7,000 | 495 | 133,315 |
| 2 | Claude Opus 5.5 | 36,720 | - | 70,740 | - | 7,000 | 495 | 114,955 |
| 3 | Gemini 3.8 Flash | 36,720 | 18,360 | 70,740 | 7,074 | 7,000 | 495 | 140,389 |
| 4 | Qwen3.8-Max (0902 snapshot) | 36,720 | 18,360 | 70,740 | 7,074 | 7,000 | 495 | 140,389 |
| 5 | DeepSeek V4 Pro (GA, 0813) | 35,100 | 17,550 | 70,200 | 7,020 | 7,000 | 495 | 137,365 |
| 6 | Muse Spark 1.3 | 36,720 | - | 70,740 | 7,074 | 7,000 | 495 | 122,029 |
| 7 | GPT-4.1 | 36,720 | - | 70,740 | 7,074 | 7,000 | 495 | 122,029 |
| 8 | Claude Opus 4.8 | 36,720 | 18,360 | 70,740 | - | 7,000 | 495 | 133,315 |
| 9 | DeepSeek R1 | 35,100 | - | 70,200 | 7,020 | 7,000 | 495 | 119,815 |
| 10 | Llama 4 Maverick | 36,720 | - | 70,740 | 7,074 | 7,000 | 495 | 122,029 |
| | **all** | **363,960** | **90,990** | **706,320** | **49,410** | **70,000** | **4,950** | **1,285,630** |

## The lineup these counts run on (run.py MODEL_REGISTRY; ids verified 2026-09-29)
| Slot | Role | Model | Reasoning in the primary condition | Contrast arm | Temperature arm | Picture cells |
|---|---|---|---|---|---|---|
| 1 | OpenAI, current flagship | GPT-6 Astra (`gpt-6-astra`) | lowest level (`low`) | yes | no | yes |
| 2 | Anthropic, current flagship | Claude Opus 5.5 (`claude-opus-5-5`) | lowest level (`low`) | no | no | yes |
| 3 | Google, current flagship | Gemini 3.8 Flash (`gemini-3.8-flash`) | lowest level (`low`) | yes | yes | yes |
| 4 | Alibaba, current flagship | Qwen3.8-Max (0902 snapshot) (`qwen/qwen3.8-max-0902`) | lowest level (`minimal`) | yes | yes | yes |
| 5 | DeepSeek, current flagship | DeepSeek V4 Pro (GA, 0813) (`deepseek/deepseek-v4-pro-0813`) | off | yes | yes | not applicable (text only) |
| 6 | Meta, current flagship | Muse Spark 1.3 (`meta/muse-spark-1.3`) | lowest level (`minimal`) | no | yes | yes |
| 7 | OpenAI, older generation | GPT-4.1 (`gpt-4.1-2025-04-14`) | none (no reasoning mode) | no | yes | yes |
| 8 | Anthropic, older generation | Claude Opus 4.8 (`claude-opus-4-8`) | off | yes | no | yes |
| 9 | DeepSeek, older generation | DeepSeek R1 (`deepseek/deepseek-r1`) | always on (no control) | no | yes | not applicable (text only) |
| 10 | Meta, older generation | Llama 4 Maverick (`meta-llama/llama-4-maverick`) | none (no reasoning mode) | no | yes | yes |

Build check: the registry reproduces the registered design (10 slots, 5 contrast slots, 7 temperature-arm models); this script refuses to write the manifest when it does not. `python run.py --count` enumerates every call
from the runner's own generator and must agree with every row above.

The runner executes this plan and can resume an interrupted run. The model calls run at Stage 2,
after in-principle acceptance.
