"""build_manifest.py: compute the exact model-call plan from stimuli/stimuli.json.

For each of the ten models it counts the neutral prompts (every stimulus, in every registered position
order, three paraphrases, each format and each similarity clone placement), then adds the persona,
reasoning, temperature, sequential and recognition conditions. No model is called.

Output: models/MANIFEST.md (907,594 calls; 3,636 neutral prompts per model).
Manuscript: Method ("Model study") and Table 2.

Run: python models/build_manifest.py
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Layout: root = the nearest ancestor holding stimuli/
# (working repository: two levels up from models/; public deposit: one level up from models/).
def _find_root(start):
    d = start
    for _ in range(4):
        d = os.path.dirname(d)
        if os.path.isdir(os.path.join(d, "stimuli")):
            return d
    return os.path.abspath(os.path.join(start, "..", ".."))
STIM = os.path.join(_find_root(HERE), "stimuli", "stimuli.json")
sys.path.insert(0, HERE)
from order_plan import n_orders_for   # ONE canonical order rule, shared with run.py (no count drift)

# Position-order COUNT per structure, computed from the SAME rule run.py uses to emit the prompts
# (order_plan.n_orders_for, keyed by the option count). BIN=2, every trinary=6, MOT (12 options)=12.
# EXC is a trinary single-option-per-tier menu, so 6 orders, exactly like the other trinaries. This
# table is derived, not hand-typed, so build_manifest's count can never diverge from run.py's prompts.
ORDERS = {"BIN": n_orders_for(2), "SOT": n_orders_for(3), "FRQ": n_orders_for(3),
          "RNG": n_orders_for(3), "PHT": n_orders_for(3), "SYM": n_orders_for(3),
          "SIM": n_orders_for(3), "MOT": n_orders_for(12), "EXC": n_orders_for(3)}
PARAPHRASES = 3
PERSONAS = 20
N_MODELS = 10
N_REASON = 5            # the five registered reasoning-contrast slots (run.py reasoning_contrast=True)
N_TEMP = 7              # the seven registered temperature-arm models (run.py temperature_arm=True)
SEQ_SESSIONS = 1000     # sequential 7-choice sessions per model
# Registered repeated draws (2026-09-29): calls per grid point. A pictures cell (1 order x 3 frames x 60 = 180)
# carries as many calls as a three-option numbers cell (6 orders x 3 frames x 10 = 180); in the contrast arm 90.
NEUTRAL_DRAWS, NEUTRAL_PICTURE_DRAWS = 10, 60
CONTRAST_DRAWS, CONTRAST_PICTURE_DRAWS = 5, 30
# earlier plan totals (kept for the change note)
PREVIOUS_TOTALS = (("before the picture protocol of 2026-09-29", 907594),
                   ("with the picture protocol and one call per grid point", 883654))

# runner arm -> manifest row label (run.py --count compares them one by one)
ARM_LABELS = {
    "primary": "Neutral (confirmatory grid, 10 draws; 60 per picture prompt)",
    "persona": "Persona (x20)",
    "reasoning_on": "Reasoning contrast (5 slots, high side, 5 draws; 30 per picture prompt)",
    "temp_0": "Temperature robustness (7 models x 2 temps, neutral)",
    "sequential": "Sequential 7-choice sessions",
    "recognition": "Recognition probe (per stimulus x3 paraphrases)",
}

def registry_arms():
    """The slot lists the runner will actually execute, read from run.py's MODEL_REGISTRY. The registered
    constants above are the design; this is the engine. main() REFUSES to write a manifest when the two
    disagree (added 2026-09-29 with the roster update, so a roster edit can never silently move a count)."""
    import run
    reg = run.MODEL_REGISTRY
    return (reg, [k for k in reg], run.models_for_arm("reasoning_on"), run.models_for_arm("temp_0"),
            run.validate_registry(reg), run.IDS_VERIFIED_ON)

def delivery_split(stim, vision=True):
    """(text prompts, picture prompts): the distinct neutral prompts (grid points) one stimulus expands into for
    one model, for each delivery form orders x paraphrases. numbers, words and each SIM placement run every
    order (order_plan.n_orders_for(option count): BIN 2, trinary 6, MOT 12). pictures run the canonical order
    only, and only on an image-capable model (vision=False gives 0 picture prompts)."""
    o = n_orders_for(len(stim["options"]))
    fv = stim.get("format_variants") or {}
    text = o * PARAPHRASES                                           # numbers
    text += o * PARAPHRASES if "words" in fv else 0                  # words
    text += o * PARAPHRASES * len(stim.get("placement_variants") or {})  # SIM placements
    pics = 1 * PARAPHRASES if (vision and "pictures" in fv) else 0   # pictures: canonical order only
    return text, pics

def delivery_prompts(stim, vision=True):
    """Distinct neutral prompts (grid points) of one stimulus for one model: text plus picture prompts."""
    return sum(delivery_split(stim, vision))

def compute_plan():
    """The whole plan as numbers: per-model grid points (text and picture), per-slot calls of the two
    repeated-draw arms, every arm's calls, the total."""
    reg, lineup, reason_slots, temp_slots, _, _ = registry_arms()
    stimuli = json.load(open(STIM, encoding="utf-8"))["stimuli"]
    n_stim = len(stimuli)
    text = {k: sum(delivery_split(s, reg[k]["accepts_images"])[0] for s in stimuli) for k in lineup}
    pics = {k: sum(delivery_split(s, reg[k]["accepts_images"])[1] for s in stimuli) for k in lineup}
    per_model = {k: text[k] + pics[k] for k in lineup}
    neutral_calls = {k: NEUTRAL_DRAWS * text[k] + NEUTRAL_PICTURE_DRAWS * pics[k] for k in lineup}
    contrast_calls = {k: CONTRAST_DRAWS * text[k] + CONTRAST_PICTURE_DRAWS * pics[k] for k in reason_slots}
    by_struct = {}
    for s in stimuli:
        v, t = delivery_prompts(s, True), delivery_prompts(s, False)
        a = by_struct.setdefault(s["structure"], [0, 0])
        a[0] += v; a[1] += t
    arms = {
        ARM_LABELS["primary"]: sum(neutral_calls.values()),
        ARM_LABELS["persona"]: PERSONAS * sum(per_model.values()),
        ARM_LABELS["reasoning_on"]: sum(contrast_calls.values()),
        ARM_LABELS["temp_0"]: 2 * sum(per_model[k] for k in temp_slots),
        ARM_LABELS["sequential"]: SEQ_SESSIONS * 7 * len(lineup),
        ARM_LABELS["recognition"]: n_stim * PARAPHRASES * len(lineup),
    }
    # every slot's calls by arm (the per-slot table in MANIFEST.md; cost_estimate.py reads the same numbers)
    by_slot = {k: {"primary": neutral_calls[k],
                   "reasoning_on": contrast_calls.get(k, 0),
                   "persona": PERSONAS * per_model[k],
                   "temperature": 2 * per_model[k] if k in temp_slots else 0,
                   "sequential": SEQ_SESSIONS * 7,
                   "recognition": n_stim * PARAPHRASES} for k in lineup}
    return dict(n_stim=n_stim, per_model=per_model, text=text, pics=pics, neutral_calls=neutral_calls,
                contrast_calls=contrast_calls, by_slot=by_slot, by_struct=by_struct, arms=arms,
                total=sum(arms.values()), reason_slots=reason_slots, temp_slots=temp_slots,
                vision=sum(1 for k in lineup if reg[k]["accepts_images"]), text_only=[k for k in lineup
                if not reg[k]["accepts_images"]])

def _arithmetic(p, reg, lineup):
    """The arithmetic behind each arm total, as printed in MANIFEST.md (grouped by identical slots)."""
    def groups(keys, f):
        out = {}
        for k in keys:
            out.setdefault(f(k), []).append(k)
        return out
    def fmt_groups(keys, f):
        parts = []
        for expr, ks in sorted(groups(keys, f).items(), key=lambda kv: -len(kv[1])):
            wrapped = f"({expr})" if " " in expr else expr
            parts.append(f"{len(ks)} x {wrapped}" if len(ks) > 1 else expr)
        return " + ".join(parts)
    tp = lambda k: (p["text"][k], p["pics"][k])
    def draws_expr(k, dt, dp):
        t, q = tp(k)
        return f"{t:,} x {dt} + {q} x {dp}" if q else f"{t:,} x {dt}"
    grid = lambda k: format(p["per_model"][k], ",")
    return {
        "primary": fmt_groups(lineup, lambda k: draws_expr(k, NEUTRAL_DRAWS, NEUTRAL_PICTURE_DRAWS)),
        "persona": "%d x (%s)" % (PERSONAS, fmt_groups(lineup, grid)),
        "reasoning_on": fmt_groups(p["reason_slots"], lambda k: draws_expr(k, CONTRAST_DRAWS, CONTRAST_PICTURE_DRAWS)),
        "temp_0": "2 x (%s)" % fmt_groups(p["temp_slots"], grid),
        "sequential": f"{SEQ_SESSIONS:,} x 7 x {len(lineup)}",
        "recognition": f"{p['n_stim']} x {PARAPHRASES} x {len(lineup)}",
    }

def main():
    reg, lineup, reason_slots, temp_slots, reg_problems, verified_on = registry_arms()
    mismatch = []
    if len(lineup) != N_MODELS:
        mismatch.append(f"registry has {len(lineup)} slots, the design registers {N_MODELS}")
    if len(reason_slots) != N_REASON:
        mismatch.append(f"registry has {len(reason_slots)} reasoning-contrast slots, the design registers {N_REASON}")
    if len(temp_slots) != N_TEMP:
        mismatch.append(f"registry has {len(temp_slots)} temperature-arm models, the design registers {N_TEMP}")
    mismatch += reg_problems
    if mismatch:
        sys.exit("build_manifest REFUSES: the model registry does not reproduce the registered design:\n  "
                 + "\n  ".join(mismatch))
    p = compute_plan()
    vis = next(k for k in lineup if reg[k]["accepts_images"])
    txt = next(k for k in lineup if not reg[k]["accepts_images"])
    vis_n, txt_n = p["per_model"][vis], p["per_model"][txt]
    vis_pics = p["pics"][vis]
    arms, total = p["arms"], p["total"]
    text_names = ", ".join(reg[k]["model_name"] for k in p["text_only"])
    arith = _arithmetic(p, reg, lineup)
    arm_keys = {v: k for k, v in ARM_LABELS.items()}
    three = n_orders_for(3) * PARAPHRASES

    out = ["# MODEL-CALL MANIFEST - exact plan from stimuli.json ",
           "(Computed from the final stimuli.json by build_manifest.py. No API calls were made.)",
           "",
           f"**Stimuli (entries):** {p['n_stim']}.  **Distinct neutral prompts (grid points) per model:** {vis_n:,} "
           f"for each of the {p['vision']} image-capable slots ({vis_n - vis_pics:,} text prompts and {vis_pics} "
           f"picture prompts) and {txt_n:,} for each text-only slot ({text_names}), which run no picture cells "
           f"(not applicable).  **Neutral-arm calls per slot:** {p['neutral_calls'][vis]:,} (image-capable) and "
           f"{p['neutral_calls'][txt]:,} (text-only).  **Primary lineup:** {N_MODELS} models.",
           "",
           "Picture cells run in the canonical option order only: the model receives the same whole-set PNG",
           "the participants see, with the options labelled Option A, B, C in that order, and the human",
           "picture arm never rotates it. Numbers, words and similarity",
           "placements run every registered order.",
           "",
           "Twelve-option extremity menus run twelve registered full shuffles of the twelve positions per menu",
           "stimulus (mot_orders.json, drawn once from seed 20260929 and checked against it on every load),",
           "the same kind of order the participants' menus get; until 2026-09-29 they ran orders that kept each",
           "quality level in a block of positions. Still twelve orders per menu, so no count changes.",
           "",
           "## Repeated draws per grid point (registered 2026-09-29)",
           "At the provider's default temperature each call is one draw from the model's answers, so the",
           "confirmatory arm calls every grid point more than once. Each draw is a separate API call with no",
           "conversation history, and every call record carries its `draw_index` (0 in the arms that do not",
           "repeat). The plan is draw-major within each model: the whole grid at draw 0, then at draw 1, and so on.",
           "",
           "| Arm | calls per text grid point | calls per picture prompt | three-option numbers cell | pictures cell |",
           "|---|---|---|---|---|",
           f"| Neutral (confirmatory) | {NEUTRAL_DRAWS} | {NEUTRAL_PICTURE_DRAWS} | {three * NEUTRAL_DRAWS} | "
           f"{PARAPHRASES * NEUTRAL_PICTURE_DRAWS} |",
           f"| Reasoning contrast, high side | {CONTRAST_DRAWS} | {CONTRAST_PICTURE_DRAWS} | {three * CONTRAST_DRAWS} | "
           f"{PARAPHRASES * CONTRAST_PICTURE_DRAWS} |",
           "| Persona, temperature, sequential, recognition | 1 | 1 | | |",
           "",
           f"A three-option numbers cell is {n_orders_for(3)} orders x {PARAPHRASES} frames; a pictures cell is one "
           f"order x {PARAPHRASES} frames.",
           "",
           "## Neutral prompts per model, by structure (distinct grid points)",
           "| Structure | orders | image-capable slot | text-only slot |", "|---|---|---|---|"]
    for st in ["BIN", "FRQ", "RNG", "PHT", "SOT", "SYM", "SIM", "MOT", "EXC"]:
        v, t = p["by_struct"].get(st, [0, 0])
        out.append(f"| {st} | {ORDERS[st]} | {v:,} | {t:,} |")
    out += [f"| **all** | | **{vis_n:,}** | **{txt_n:,}** |",
            "", "## Calls by arm (primary lineup)", "| Arm | calls | arithmetic |", "|---|---|---|"]
    for k, v in arms.items():
        out.append(f"| {k} | {v:,} | {arith[arm_keys[k]]} |")
    name = lambda k: f"{reg[k]['model_name']} (`{reg[k]['api_id']}`)"
    out += [f"| **TOTAL** | **{total:,}** | |", "",
            "## Calls per slot",
            "| Slot | Model | Neutral | Reasoning contrast | Persona | Temperature (2 temps) | Sequential | "
            "Recognition | Slot total |",
            "|---|---|---|---|---|---|---|---|---|"]
    for k in lineup:
        b = p["by_slot"][k]
        cells = [b["primary"], b["reasoning_on"], b["persona"], b["temperature"], b["sequential"], b["recognition"]]
        out.append(f"| {reg[k]['slot']} | {reg[k]['model_name']} | " + " | ".join(f"{c:,}" if c else "-" for c in cells)
                   + f" | {sum(cells):,} |")
    out += [f"| | **all** | " + " | ".join(f"**{sum(p['by_slot'][k][a] for k in lineup):,}**" for a in
                                           ("primary", "reasoning_on", "persona", "temperature", "sequential",
                                            "recognition")) + f" | **{total:,}** |", "",
            f"## The lineup these counts run on (run.py MODEL_REGISTRY; ids verified {verified_on})",
            "| Slot | Role | Model | Reasoning in the primary condition | Contrast arm | Temperature arm | Picture cells |",
            "|---|---|---|---|---|---|---|"]
    for k in lineup:
        r = reg[k]
        prim = {"true_off": "off", "lowest_effort": f"lowest level (`{r['reasoning_primary']}`)",
                "always_on": "always on (no control)", "no_reasoning": "none (no reasoning mode)"}[r["off_state"]]
        out.append(f"| {r['slot']} | {r['developer']}, {r['tier'].replace('_', ' ')} | {name(k)} | {prim} | "
                   f"{'yes' if k in reason_slots else 'no'} | {'yes' if k in temp_slots else 'no'} | "
                   f"{'yes' if r['accepts_images'] else 'not applicable (text only)'} |")
    out += ["",
            f"Build check: the registry reproduces the registered design ({len(lineup)} slots, "
            f"{len(reason_slots)} contrast slots, {len(temp_slots)} temperature-arm models); this script "
            "refuses to write the manifest when it does not. `python run.py --count` enumerates every call",
            "from the runner's own generator and must agree with every row above.",
            "",
            "The runner executes this plan and can resume an interrupted run. The model calls run at Stage 2,",
            "after in-principle acceptance."]
    open(os.path.join(HERE, "MANIFEST.md"), "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("\n".join(out[:6]))
    print(f"\nTOTAL CALLS: {total:,}  (grid points per image-capable slot {vis_n:,}, per text-only slot {txt_n:,}; "
          f"neutral calls per slot {p['neutral_calls'][vis]:,} and {p['neutral_calls'][txt]:,}; {p['n_stim']} stimuli)")
    for k, v in arms.items():
        print(f"  {k}: {v:,}  = {arith[arm_keys[k]]}")

if __name__ == "__main__":
    main()
