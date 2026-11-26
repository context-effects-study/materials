"""build_manifest.py: compute the exact model-call plan from stimuli/stimuli.json and models/model_registry.json.

For each model it counts the neutral prompts (every stimulus, in every registered position order, three
paraphrases, each format and each placement of the near-copy in the similarity set) and multiplies them by the
model's draws at each reasoning setting it runs, then adds the persona and temperature conditions, the choice
sequences in one conversation and the suspicion probe. Which conditions, settings and draws each model runs is in
its registry entry. No model is called.

Output: models/MANIFEST.md (8,629,438 calls; 3,537 distinct neutral prompts per image-capable model and 3,510 per text-only model).
Manuscript: Method ("Language Models and Prompts") and Web Appendix D.

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
ORDERS = {"BIN": n_orders_for(2), "SOT": n_orders_for(3), "FRQ": n_orders_for(3),
          "RNG": n_orders_for(3), "PHT": n_orders_for(3), "SYM": n_orders_for(3),
          "SIM": n_orders_for(3), "MOT": n_orders_for(12), "EXC": n_orders_for(3)}
PARAPHRASES = 3
PERSONAS = 20
SEQ_SESSIONS = 1000     # sequential 7-choice sessions per model
# earlier plan totals (kept for the change note)
PREVIOUS_TOTALS = (("before the picture protocol of 2026-09-29", 907594),
                   ("with the picture protocol and one call per grid point", 883654),
                   ("with the repeated draws of 2026-09-29, on ten models", 1285630))

# condition -> manifest row label (cost_plan.py's condition names; run.py --count compares them one by one)
CONDITION_LABELS = {
    "primary": "Neutral at the lowest setting (confirmatory)",
    "crossed": "Neutral at the default and high settings (and low effort where reasoning can be switched off)",
    "ladder": "Neutral at the other reasoning levels",
    "persona": "Persona (x20, lowest setting)",
    "temperature": "Temperature check (0 and 1.0, lowest setting)",
    "sequential": "Sequential 7-choice sessions",
    "recognition": "Recognition probe (per stimulus x3 paraphrases)",
}
ARM_CONDITION = {"primary": "primary", "crossed": "crossed", "ladder": "ladder", "persona": "persona",
                 "temp_0": "temperature", "temp_1": "temperature", "sequential": "sequential",
                 "recognition": "recognition"}


def registry():
    import run
    return run.MODEL_REGISTRY, run.validate_registry(run.MODEL_REGISTRY), run.IDS_VERIFIED_ON


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


def model_calls(m, text, pics, n_stim):
    """One model's calls as {(arm, setting): calls}, in the order the runner runs them."""
    p = m["plan"]
    prim = p["primary"]["setting"]
    out = {("primary", prim): p["primary"]["draws"] * text + p["primary"]["picture_draws"] * pics}
    for arm in ("crossed", "ladder"):
        for c in p[arm]:
            out[(arm, c["setting"])] = c["draws"] * text + c["picture_draws"] * pics
    if p["temperature"]:
        out[("temp_0", prim)] = text + pics
        out[("temp_1", prim)] = text + pics
    if p["persona"]:
        out[("persona", prim)] = PERSONAS * (text + pics)
    out[("sequential", prim)] = SEQ_SESSIONS * 7
    out[("recognition", prim)] = n_stim * PARAPHRASES
    return out


def compute_plan():
    """The whole plan as numbers: per-model grid points (text and picture), every model's calls by arm and setting,
    every condition's calls, the total."""
    reg, _, _ = registry()
    stimuli = json.load(open(STIM, encoding="utf-8"))["stimuli"]
    n_stim = len(stimuli)
    text = {k: sum(delivery_split(s, reg[k]["accepts_images"])[0] for s in stimuli) for k in reg}
    pics = {k: sum(delivery_split(s, reg[k]["accepts_images"])[1] for s in stimuli) for k in reg}
    calls = {k: model_calls(reg[k], text[k], pics[k], n_stim) for k in reg}
    by_condition = {c: 0 for c in CONDITION_LABELS}
    for k in reg:
        for (arm, _), n in calls[k].items():
            by_condition[ARM_CONDITION[arm]] += n
    by_struct = {}
    for s in stimuli:
        v, t = delivery_prompts(s, True), delivery_prompts(s, False)
        a = by_struct.setdefault(s["structure"], [0, 0])
        a[0] += v
        a[1] += t
    return dict(n_stim=n_stim, text=text, pics=pics, per_model={k: text[k] + pics[k] for k in reg}, calls=calls,
                by_condition=by_condition, by_struct=by_struct, total=sum(by_condition.values()),
                model_total={k: sum(calls[k].values()) for k in reg},
                vision=sum(1 for k in reg if reg[k]["accepts_images"]),
                text_only=[k for k in reg if not reg[k]["accepts_images"]])


def cost_plan_conditions(model_key, p=None):
    """One model's calls in cost_plan.py's terms, as {(condition, setting): calls}: the primary condition holds the
    neutral grid at the primary setting plus the sequential sessions and the recognition probe, and the temperature
    condition holds both temperatures. test_registry.py compares this with cost_plan.conditions() for every model."""
    p = p or compute_plan()
    out = {}
    for (arm, s), n in p["calls"][model_key].items():
        cond = ARM_CONDITION[arm]
        if cond in ("sequential", "recognition"):
            cond = "primary"
        out[(cond, s)] = out.get((cond, s), 0) + n
    return out


def _fmt(n):
    return f"{n:,}" if n else "-"


def main():
    reg, problems, verified_on = registry()
    if problems:
        sys.exit("build_manifest REFUSES: the model registry breaks its rules:\n  " + "\n  ".join(problems))
    p = compute_plan()
    keys = list(reg)
    vis = next(k for k in keys if reg[k]["accepts_images"])
    txt = next(k for k in keys if not reg[k]["accepts_images"])
    vis_n, txt_n, vis_pics = p["per_model"][vis], p["per_model"][txt], p["pics"][vis]
    groups = {g: sum(1 for k in keys if reg[k]["group"] == g) for g in ("closed_current", "closed_previous", "open")}
    three = n_orders_for(3) * PARAPHRASES
    tiers = {}   # price tier -> {(lowest-setting draws, crossed draws, ladder draws): number of models in that row}
    for k in keys:
        pl = reg[k]["plan"]
        row = (pl["primary"]["draws"], tuple(sorted({c["draws"] for c in pl["crossed"]})),
               tuple(sorted({c["draws"] for c in pl["ladder"]})))
        counts = tiers.setdefault(reg[k]["price_tier"], {})
        counts[row] = counts.get(row, 0) + 1
    if sum(n for c in tiers.values() for n in c.values()) != len(keys):
        raise SystemExit("REFUSED: the rows of the draws table do not add up to the number of models")

    out = ["# MODEL-CALL MANIFEST - exact plan from stimuli.json and the model registry ",
           "(Computed from the final stimuli.json and model_registry.json by build_manifest.py. No API calls were made.)",
           "",
           f"**Stimuli (entries):** {p['n_stim']}.  **Distinct neutral prompts (grid points) per model:** {vis_n:,} "
           f"for each of the {p['vision']} image-capable models ({vis_n - vis_pics:,} text prompts and {vis_pics} "
           f"picture prompts) and {txt_n:,} for each of the {len(p['text_only'])} text-only models, which run no "
           f"picture cells (not applicable).  **Models:** {len(keys)} ({groups['closed_current']} closed models of the "
           f"current generation, {groups['closed_previous']} of the previous generation, {groups['open']} with open "
           f"weights), from {len({reg[k]['developer'] for k in keys})} developers.",
           "",
           "Picture cells run in the canonical option order only: the model receives the same whole-set PNG",
           "the participants see, with the options labelled Option A, B, C in that order, and the human",
           "picture arm never rotates it. Numbers, words and similarity",
           "placements run every registered order.",
           "",
           "Twelve-option extremity menus run twelve registered full shuffles of the twelve positions per menu",
           "stimulus (mot_orders.json, drawn once from seed 20260929 and checked against it on every load),",
           "the same kind of order the participants' menus get.",
           "",
           "## Settings and repeated draws",
           "Each model's reasoning controls are mapped onto five common settings: OFF, LOW (the lowest effort with",
           "reasoning on), DEFAULT (what a user gets without changing anything), HIGH and MAX. The confirmatory",
           "neutral grid runs at the model's lowest setting (OFF where reasoning can be switched off). At the",
           "provider's default temperature each call is one draw from the model's answers, so a grid point is called",
           "more than once; the number depends on the model's price per million output tokens (premium: $20 or more;",
           "standard: $3 to $20; budget: under $3, and every open model). A picture prompt is called six times as",
           "often as a text prompt, so a pictures cell (one order x 3 frames) holds as many calls as a three-option",
           "numbers cell (6 orders x 3 frames). Each draw is a separate API call with no conversation history, every",
           "call record holds its `draw_index` and its `setting`, and the plan is draw-major within each model.",
           "",
           "| Price tier | models | draws a text prompt, lowest setting | at the default and high settings | other levels | three-option numbers cell, lowest setting |",
           "|---|---|---|---|---|---|"]
    for t in ("premium", "standard", "budget"):
        if t not in tiers:
            continue
        for (prim, crossed, ladder), n in sorted(tiers[t].items()):
            out.append(f"| {t} | {n} | {prim} | {', '.join(map(str, crossed)) or '-'} | "
                       f"{', '.join(map(str, ladder)) or '-'} | {three * prim} |")
    out += ["",
            "Persona, temperature, sequential and recognition calls run once per grid point, at the lowest setting.",
            "",
            "## Neutral prompts per model, by structure (distinct grid points)",
            "| Structure | orders | image-capable model | text-only model |", "|---|---|---|---|"]
    for st in ["BIN", "FRQ", "RNG", "PHT", "SOT", "SYM", "SIM", "MOT", "EXC"]:
        v, t = p["by_struct"].get(st, [0, 0])
        out.append(f"| {st} | {ORDERS[st]} | {v:,} | {t:,} |")
    out += [f"| **all** | | **{vis_n:,}** | **{txt_n:,}** |",
            "", "## Calls by condition (all models)", "| Condition | calls |", "|---|---|"]
    for c, label in CONDITION_LABELS.items():
        out.append(f"| {label} | {p['by_condition'][c]:,} |")
    out += [f"| **TOTAL** | **{p['total']:,}** |", "",
            "## Calls per model",
            "| Slot | Model | Group | Price tier | Lowest setting | Neutral, lowest setting | Other settings (setting: calls) | "
            "Persona | Temperature (2) | Sequential | Recognition | Model total |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in keys:
        r, c = reg[k], p["calls"][k]
        prim = r["plan"]["primary"]["setting"]
        others = "; ".join(f"{s}: {n:,}" for (arm, s), n in c.items() if arm in ("crossed", "ladder")) or "-"
        temp = c.get(("temp_0", prim), 0) + c.get(("temp_1", prim), 0)
        out.append(f"| {r['slot']} | {r['model_name']} | {r['group'].replace('_', ' ')} | {r['price_tier']} | {prim} | "
                   f"{c[('primary', prim)]:,} | {others} | {_fmt(c.get(('persona', prim), 0))} | {_fmt(temp)} | "
                   f"{c[('sequential', prim)]:,} | {c[('recognition', prim)]:,} | {p['model_total'][k]:,} |")
    neutral = sum(p["calls"][k][("primary", reg[k]["plan"]["primary"]["setting"])] for k in keys)
    other = p["by_condition"]["crossed"] + p["by_condition"]["ladder"]
    out += [f"| | **all** | | | | **{neutral:,}** | **{other:,}** | **{p['by_condition']['persona']:,}** | "
            f"**{p['by_condition']['temperature']:,}** | "
            f"**{p['by_condition']['sequential']:,}** | **{p['by_condition']['recognition']:,}** | **{p['total']:,}** |",
            "",
            f"## The models these counts run on (model_registry.json; roster of {verified_on})",
            "| Slot | Model | Developer | Generation | Route | Id sent | Open weights (repository at revision) | "
            "Settings offered | Pictures |",
            "|---|---|---|---|---|---|---|---|---|"]
    for k in keys:
        r = reg[k]
        route = r["route"] + (f" via host {r['provider_pin']['only'][0]}" if r.get("provider_pin") else "")
        hf = f"{r['hf_revision'][0]} at {r['hf_revision'][1][:12]}" if r.get("hf_revision") else ""
        out.append(f"| {r['slot']} | {r['model_name']} | {r['developer']} | {r['generation']} | {route} | "
                   f"`{r['model_id']}` | {hf} | {', '.join(r['levels'])} | "
                   f"{'yes' if r['accepts_images'] else 'not applicable (text only)'} |")
    out += ["",
            "Build check: the registry passes run.py's validate_registry, or this script refuses to write the manifest.",
            "`python run.py --count` enumerates every call from the runner's own generator and must agree with every",
            "row above.",
            "",
            "The runner executes this plan and can resume an interrupted run. The model calls run at Stage 2,",
            "after in-principle acceptance."]
    open(os.path.join(HERE, "MANIFEST.md"), "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("\n".join(out[:6]))
    print(f"\nTOTAL CALLS: {p['total']:,}  (grid points per image-capable model {vis_n:,}, per text-only model "
          f"{txt_n:,}; {p['n_stim']} stimuli; {len(keys)} models)")
    for c, label in CONDITION_LABELS.items():
        print(f"  {label}: {p['by_condition'][c]:,}")


if __name__ == "__main__":
    main()
