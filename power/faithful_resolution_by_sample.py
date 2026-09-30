"""faithful_resolution_by_sample.py: how large a sample the planted faithful model needs before the analysis
routes it to its intended scenario (S1) at the registered 95 percent level.

At the planned sizes the faithful profile is not resolved in the routing-stability runs
(power/model_noise_stability.py). This script runs the full analysis on that profile alone, with the human cells
scaled by 1, 2, 4 and 8 times the planned sizes, under model calls with no draw noise (so every interval comes
from the human side), with the registered 10 independent draws per text prompt, and with 40 or 160 draws per
text prompt (picture prompts keep 60). It reports how often the profile routes to S1 and which readings stay
open. Nothing registered changes; the level stays 95 percent. Each run uses its own interpreter. Seeds
20260929 plus 1000 times the seed number.

Output: power/FAITHFUL_RESOLUTION_BY_SAMPLE.md.
Manuscript: Analysis Plan and Web Appendix E (what resolution would pass the faithful model).

Run: python power/faithful_resolution_by_sample.py      (about 8 minutes)
"""
import argparse, json, os, random, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "analysis")))
import analyze  # noqa: E402
import synth    # noqa: E402

SCALES = (1, 2, 4, 8)
MODEL_NOISE = ("none", "independent", "independent_40", "independent_160")
# the plan: every human scale for the noise-free and the registered model calls; 2 and 8 times for more draws
PLAN = ([("none", sc) for sc in SCALES] + [("independent", sc) for sc in SCALES]
        + [(n, sc) for n in ("independent_40", "independent_160") for sc in (2, 8)])
NOISE_WORDS = {"none": "no draw noise", "independent": "10 independent draws per text prompt (registered)",
               "independent_40": "40 independent draws per text prompt", "independent_160": "160 independent draws "
                                                                                     "per text prompt"}


def one_run(seed, scale, noise):
    rng = random.Random(seed)
    H = synth.gen_human(700 * scale, rng, icc=0.10, with_formats=True, sim_topup_participants=1000 * scale,
                        published_n_per_tier=350 * scale)
    if noise == "none":
        recs = synth.gen_model("FAITHFUL", 200, rng, with_formats=True, consistency="exact")
        # every call its own grid point (a unique session_id, a grid field the neutral arm otherwise leaves empty),
        # so the call bootstrap cannot move the model side. (consistency="exact" alone keeps one remainder prompt per
        # paraphrase mixed, which in a two-option cell of six prompts is a large share of the calls.)
        for i, r in enumerate(recs):
            if r.get("prompting_mode") == "neutral":
                r["session_id"] = f"call{i}"
    else:
        # "independent" is the registered 10 draws per text prompt; "independent_<d>" draws each text prompt d times
        # (picture prompts keep their registered 60 draws)
        draws = int(noise.split("_")[1]) if "_" in noise else synth.DRAWS_TEXT
        saved_draws = dict(synth.DRAWS_BY_STRUCT)
        synth.DRAWS_BY_STRUCT.clear()
        synth.DRAWS_BY_STRUCT.update({s: draws for s in synth.STRUCTS})
        try:
            recs = synth.gen_model("FAITHFUL", 200, rng, with_formats=True, consistency=None)
        finally:
            synth.DRAWS_BY_STRUCT.clear()
            synth.DRAWS_BY_STRUCT.update(saved_draws)
    tmp = os.path.join(tempfile.gettempdir(), "context_effects_release_scratch", "faithful_by_sample_pack")
    os.makedirs(os.path.join(tmp, "tests"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "figures"), exist_ok=True)
    saved = (analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR)
    try:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = tmp, os.path.join(tmp, "tests"), os.path.join(tmp, "figures")
        res = analyze.build_pack(H, {"FAITHFUL": recs}, H, H, seed=seed, mode="FAITHFUL_BY_SAMPLE",
                                 design=analyze.Design.for_synth())
    finally:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = saved
    route = res["routing_rows"][0]
    t1, t3, t4 = res["test_T1_rows"][0], res["test_T3_rows"][0], res["test_T4_rows"][0]
    return dict(seed=seed, scale=scale, noise=noise, scenario=route["scenario"],
                possible=route.get("possible_scenarios", ""),
                t1=t1["reading"].split(":")[0], t1_ci=f"{t1.get('drop_lo')} to {t1.get('drop_hi')}",
                t3=t3["reading"].split(":")[0], t3_ci=f"{t3.get('tmb_lo')} to {t3.get('tmb_hi')}",
                t4=t4["reading"].split(":")[0].split(" ")[0], t4_ci=f"{t4.get('diff_lo')} to {t4.get('diff_hi')}",
                t4_p_falls=t4.get("p_falls", ""),
                first_trial_fired=int(res["first_trial"]["fired"]), topup_fired=int(res["topup"]["fired"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--one", nargs=3, help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.one:
        print(json.dumps(one_run(int(args.one[0]), int(args.one[1]), args.one[2])))
        return
    t0 = time.time()
    rows = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for noise, scale in PLAN:
        for s in range(args.seeds):
            p = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", str(20260929 + 1000 * s),
                                str(scale), noise], capture_output=True, text=True, env=env)
            if p.returncode != 0:
                raise SystemExit(f"run {noise} scale {scale} seed {s} failed: {p.stderr.strip().splitlines()[-1:]}")
            rows.append(json.loads(p.stdout.strip().splitlines()[-1]))
            print(f"{noise} scale {scale} seed {s}: {rows[-1]['scenario']}", flush=True)
    L = ["# The faithful archetype at larger samples (what resolution would reach S1)", "",
         f"(Generated by faithful_resolution_by_sample.py, 2026-09-29, {len(rows)} runs of the full pipeline, joint "
         f"bootstrap on, registered 95 percent level, {round(time.time() - t0)} s. Scale 1 is the planned design: 350 "
         "choices per published-tier cell and 700 per invented cell. Model calls with no draw noise carry the planted "
         "shares exactly, so every interval comes from the human side; with independent draws every call is a fresh "
         "draw at the planted share, the registered noise, at 10 draws per text prompt (registered) or more; picture prompts "
         "keep their 60 draws.)", "",
         "| model calls | human sample | runs routed to S1 | not resolved | readings left open (share of runs: T1 / T3 "
         "/ T4) | median T1 drop interval | median T4 difference interval |", "|---|---|---|---|---|---|---|"]

    def med(rs, key):
        lo = sorted(float(r[key].split(" to ")[0]) for r in rs if r[key].split(" to ")[0] not in ("", "-inf", "+inf"))
        hi = sorted(float(r[key].split(" to ")[1]) for r in rs if r[key].split(" to ")[1] not in ("", "-inf", "+inf"))
        return f"{lo[len(lo) // 2]:.2f} to {hi[len(hi) // 2]:.2f}" if lo and hi else "n/a"
    for noise, scale in PLAN:
        rs = [r for r in rows if r["scale"] == scale and r["noise"] == noise]
        n = len(rs)
        s1 = sum(1 for r in rs if r["scenario"] == "S1")
        nr = sum(1 for r in rs if r["scenario"] == analyze.NOT_RESOLVED_SCENARIO)
        opn = " / ".join(f"{sum(1 for r in rs if r[k].startswith('not')) / n:.2f}" for k in ("t1", "t3", "t4"))
        L.append(f"| {NOISE_WORDS[noise]} | {scale} times the planned sizes | {s1} of {n} | {nr} of {n} | {opn} | "
                 f"{med(rs, 't1_ci')} | {med(rs, 't4_ci')} |")
    wrong = [r for r in rows if r["scenario"] not in ("S1", analyze.NOT_RESOLVED_SCENARIO)]
    L += ["", f"Runs routed to a scenario other than S1 or not resolved: {len(wrong)}"
          + ("" if not wrong else " (" + ", ".join(f"{r['noise']} scale {r['scale']}: {r['scenario']}"
                                                   for r in wrong) + ")") + ".",
          "", "S1 needs the memorization reading resolved as flat (the drop's interval below 0.30), the format reading "
              "ruled out as falling (a flat reading, or a falling reading the interval or the undershoot guard rules "
              "out), and the ladder's reversed reading ruled out.", ""]
    text = "\n".join(L)
    open(os.path.join(HERE, "FAITHFUL_RESOLUTION_BY_SAMPLE.md"), "w", encoding="utf-8", newline="\n").write(text)
    print(text)


if __name__ == "__main__":
    main()
