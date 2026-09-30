"""selftest_mutants.py: shows that the runner's self-test catches a broken request builder.

run.py --selftest plants faults in copies of the model registry and must refuse each one. This script does
the same for the request builder: it swaps in deliberately broken versions in memory (for example one that
drops the reasoning setting, changes the reasoning effort, sends the wrong temperature or routes a direct
model through the wrong id), runs the self-test and requires it to fail, then runs the unchanged self-test,
which must pass. Nothing on disk changes and no network is used.

Run: python models/selftest_mutants.py      (exit 0 when every broken version is caught and the clean run passes)
"""
import contextlib, io, sys
import run

ORIG = run.build_request

def _wrap(mutate):
    def fn(k, arm="primary", route=None):
        q = ORIG(k, arm, route)
        mutate(k, q)
        return q
    return fn

def _drop_reasoning(k, q):
    q["kwargs"].pop("reasoning_effort", None)
    q["kwargs"].get("extra_body", {}).pop("reasoning", None)

def _disable_opus55(k, q):
    if k == "anthropic_flagship":
        q["kwargs"]["thinking"] = {"type": "disabled"}

def _change_effort(k, q):
    eb = q["kwargs"].get("extra_body", {})
    if "output_config" in eb:
        eb["output_config"] = {"effort": "medium"}

def _june_cap_sent(k, q):
    # the fault as it would really occur: the SENT ceiling is 10 while the recorded value still looks right
    for key in ("max_tokens", "max_completion_tokens"):
        if key in q["kwargs"]:
            q["kwargs"][key] = 10

def _drop_primary_temperature(k, q):
    if k in ("deepseek_flagship", "meta_older") and "temperature" in q["kwargs"] \
            and q["kwargs"]["temperature"] == run.MODEL_REGISTRY[k]["temperature"]:
        del q["kwargs"]["temperature"]

def _direct_route_openrouter_id(k, q):
    if q["route"] in ("openai", "anthropic", "google"):
        q["model_id"] = run.MODEL_REGISTRY[k]["openrouter_id"]

def _record_wrong_temperature(k, q):
    if q["kwargs"].get("temperature") is not None:
        q["temperature_requested"] = None

MUTANTS = {
    "temperature sent on every call": _wrap(lambda k, q: q["kwargs"].__setitem__("temperature", 0.7)),
    "reasoning setting dropped (the June runner's behavior)": _wrap(_drop_reasoning),
    "OpenRouter host pin dropped": _wrap(lambda k, q: q["kwargs"].get("extra_body", {}).pop("provider", None)),
    "thinking disabled on Claude Opus 5.5 (a 400 on the live API)": _wrap(_disable_opus55),
    "Anthropic effort changed from the registered level": _wrap(_change_effort),
    "June 10-token output cap restored in the SENT value": _wrap(_june_cap_sent),
    "registered primary temperature 1.0 dropped (DeepSeek V4 Pro, Llama)": _wrap(_drop_primary_temperature),
    "a direct route sends the OpenRouter id": _wrap(_direct_route_openrouter_id),
    "temperature recorded as none while one is sent": _wrap(_record_wrong_temperature),
}

# Second group: faults outside the request builder.
ORIG_CALL, ORIG_ROUTE = run.call_model, run.google_route

def _call_drops_extra_body(clients, spec):
    def br(k, arm="primary", route=None):
        q = ORIG(k, arm, route)
        return dict(q, kwargs={kk: vv for kk, vv in q["kwargs"].items() if kk != "extra_body"})
    run.build_request = br
    try:
        return ORIG_CALL(clients, spec)
    finally:
        run.build_request = ORIG

def _call_hides_errors(clients, spec):
    r = ORIG_CALL(clients, spec)
    return dict(r, error=None) if r["error"] else r

ORIG_PARSE_PROBE, ORIG_ORDERS, ORIG_MESSAGES, ORIG_ITER = (run.parse_probe, run.orders_for_delivery,
                                                           run.build_messages, run.iter_specs)

def _probe_accepts_any_letter(raw, n_shown):
    return ORIG_PARSE_PROBE(raw, 12)                       # forgets how many options were shown

def _pictures_rotated(fmt, n_opts, stim_id=None):
    return run.orders_for(n_opts, stim_id)                 # rotates the letters under a fixed picture

def _history_dropped(spec, route):
    return ORIG_MESSAGES(dict(spec, history=[]), route)    # every sequential decision starts a new chat

def _opening_everywhere(stimuli, cats, models, arm="primary", draws="all"):
    # takes draws (2026-09-29): without it this mutant crashed inside run_collection and was counted as killed
    # by the crash, not by the selftest check it exists to prove
    for sp in ORIG_ITER(stimuli, cats, models, arm=arm, draws=draws):
        if sp["mode"] == "sequential" and not sp["prompt"].startswith(run.SEQUENTIAL_OPENING):
            sp = dict(sp, prompt=run.SEQUENTIAL_OPENING + run.SEQUENTIAL_SEPARATOR + sp["prompt"])
        yield sp

ORIG_BUILD_PROBE, ORIG_PARAPHRASES, ORIG_ADDED = run.build_probe, run.PARAPHRASES, run.PROBE_SINGLE_ADDED
ORIG_VERBS, ORIG_PURPOSES = run.FRAME_VERBS, run.FRAME_2_PURPOSES
ORIG_DECODE = run.decode_choice
ORIG_ORDERS_FOR = run.orders_for
ORIG_STEM_EXPL = run.stem_explanation

def _menu_tier_blocks(n_opts, stim_id=None):
    import order_plan
    if n_opts == 12:
        return order_plan._mot_stratified_orders(12)     # the June tier-block orders, restored
    return ORIG_ORDERS_FOR(n_opts, stim_id)
ORIG_DRAWS_FOR, ORIG_ROW, ORIG_SRID = run.draws_for, run.contract_b_row, run.spec_record_id

def _decode_ignores_placement(structure, code, stim, opts, cat_target_focal, placement=None):
    return ORIG_DECODE(structure, code, stim, opts, cat_target_focal)   # the pre-fix behaviour

# The repeated draws (2026-09-29). These replace the draw RULE (draws_for) rather than the DRAWS constants, so
# they test the enumeration checks themselves: the constants still read 10/60/5/30 while the plan is wrong.
def _row_without_draw(*a, **kw):
    row = ORIG_ROW(*a, **kw)
    row.pop("draw_index", None)
    return row

def _probe_one_order(stim, cat, call_index=0):
    return ORIG_BUILD_PROBE(stim, cat, 0)                  # the three probe calls identical again

OTHER_MUTANTS = {
    "probe calls all shown in the first order": ("build_probe", _probe_one_order),
    "June frames restored ('a ' before the product phrase)": (
        "PARAPHRASES", {k: v.replace("{product}", "a {product}") for k, v in ORIG_PARAPHRASES.items()}),
    "recognition credited for YES alone on sets with an added option": ("PROBE_SINGLE_ADDED", {}),
    "restaurants back to 'shopping for a restaurant'": ("FRAME_VERBS", {"default": "shopping for"}),
    "restaurants back to 'a restaurant to purchase'": ("FRAME_2_PURPOSES", {"default": "to purchase"}),
    "similarity clone_HD decoded with the base pair (the placement bug)": ("decode_choice", _decode_ignores_placement),
    "twelve-option menus back in quality-level blocks (the June orders)": ("orders_for", _menu_tier_blocks),
    "the participants' explanatory sentence dropped from the frames": ("stem_explanation", lambda stim: ""),
    "Google route hard-wired to direct (the pre-2026-09-29 fallback bug)": ("google_route", lambda: "google"),
    "call_model drops the OpenRouter reasoning and host-pin body": ("call_model", _call_drops_extra_body),
    "API errors written to the data log as rows": ("call_model", _call_hides_errors),
    "probe parser accepts a letter that was not shown": ("parse_probe", _probe_accepts_any_letter),
    "picture cells rotated like text cells": ("orders_for_delivery", _pictures_rotated),
    "sequential decisions sent without the conversation so far": ("build_messages", _history_dropped),
    "sequential opening sent before every decision": ("iter_specs", _opening_everywhere),
    "repeated draws dropped (one call per grid point, the earlier plan)": (
        "draws_for", lambda arm, fmt: 1),
    "picture repeats dropped (a picture prompt called as often as a text grid point)": (
        "draws_for", lambda arm, fmt: ORIG_DRAWS_FOR(arm, "numbers")),
    "contrast draws equal to the neutral draws": (
        "draws_for", lambda arm, fmt: ORIG_DRAWS_FOR("primary" if arm == "reasoning_on" else arm, fmt)),
    "draw_index missing from the call record": ("contract_b_row", _row_without_draw),
    "draw_index left out of the record_id (a later draw resumes as draw 0: an answer reused)": (
        "spec_record_id", lambda run_id, spec: ORIG_SRID(run_id, dict(spec, draw_index=0))),
}
ORIGINALS = {"google_route": ORIG_ROUTE, "call_model": ORIG_CALL, "parse_probe": ORIG_PARSE_PROBE,
             "orders_for_delivery": ORIG_ORDERS, "build_messages": ORIG_MESSAGES, "iter_specs": ORIG_ITER,
             "build_probe": ORIG_BUILD_PROBE, "PARAPHRASES": ORIG_PARAPHRASES, "PROBE_SINGLE_ADDED": ORIG_ADDED,
             "FRAME_VERBS": ORIG_VERBS, "FRAME_2_PURPOSES": ORIG_PURPOSES, "decode_choice": ORIG_DECODE,
             "draws_for": ORIG_DRAWS_FOR, "contract_b_row": ORIG_ROW, "spec_record_id": ORIG_SRID,
             "orders_for": ORIG_ORDERS_FOR, "stem_explanation": ORIG_STEM_EXPL}

def main():
    survivors = []
    for name, fn in MUTANTS.items():
        run.build_request = fn
        with contextlib.redirect_stdout(io.StringIO()):
            rc = run.selftest()
        run.build_request = ORIG
        print(f"  mutant [{name}] -> {'KILLED' if rc == 1 else 'SURVIVED'}")
        if rc != 1:
            survivors.append(name)
    crashed = []
    for name, (attr, fn) in OTHER_MUTANTS.items():
        setattr(run, attr, fn)
        crash = None
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                rc = run.selftest()
        except Exception as e:
            rc = 1          # a crash also refuses, but count it so a crash can never hide a pass
            crash = f"{type(e).__name__}: {str(e)[:100]}"
            crashed.append(name)
        finally:
            for name_, fn_ in ORIGINALS.items():
                setattr(run, name_, fn_)
        # a crash-kill is named (2026-09-29): it proves the mutant breaks the runner, not that a check caught it
        verdict = ("KILLED" + (f" (by a crash, not a check: {crash})" if crash else "")) if rc == 1 else "SURVIVED"
        print(f"  mutant [{name}] -> {verdict}")
        if rc != 1:
            survivors.append(name)
    with contextlib.redirect_stdout(io.StringIO()):
        clean = run.selftest()
    print(f"  clean control -> {'PASS' if clean == 0 else 'FAIL'}")
    if survivors or clean != 0:
        print(f"MUTANTS: FAIL ({len(survivors)} survived; clean control exit {clean})")
        return 1
    n = len(MUTANTS) + len(OTHER_MUTANTS)
    print(f"MUTANTS: PASS ({n} of {n} mutants killed: {len(MUTANTS)} in the request builder, "
          f"{len(OTHER_MUTANTS)} in routing, the call path, the probe, pictures, sequential sessions and the "
          f"repeated draws; {len(crashed)} of them by a crash rather than a check; clean control passes)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
