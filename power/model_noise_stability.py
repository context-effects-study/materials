"""model_noise_stability.py: how often each planted model profile routes to its intended scenario once the model
answers carry the sampling noise of the repeated draws.

It runs the full analysis (analyze.build_pack) many times on the dress-rehearsal profiles at the planned human
sizes, with every pattern-test result judged against its bootstrap interval, under three kinds of model
noise: noise-free, every call an independent draw at the planted share, and each condition giving its modal
answer in 90 percent of its draws. The design requirement: each profile routes to its intended scenario or to
not resolved, and to a wrong scenario in at most 1 of 20 runs. Each run uses its own interpreter. Standard
library only. Seeds 20260929 plus 1000 times the run number.

Output: power/MODEL_NOISE_STABILITY.md and power/model_noise_stability_runs.csv (one row per run).
Manuscript: Analysis Plan and Web Appendix E.

Run: python power/model_noise_stability.py      (about 17 minutes)
"""
import argparse, csv, json, os, random, sys, tempfile, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.abspath(os.path.join(HERE, "..", "analysis"))
sys.path.insert(0, ANALYSIS)
import analyze  # noqa: E402
import call_bootstrap  # noqa: E402
import synth    # noqa: E402

# The ceiling and refusal archetypes route to CRITERION_FAIL deterministically under any draw noise (a 97 percent
# binary share, half the calls refused), and the persona and sequential arms serve only their own readings, so
# the sweep leaves them out to fit the memory of a shared machine; the rehearsal covers all of them.
EXPECT = {"FAITHFUL": "S1", "PARROT": "S2", "REASONER": "S3", "OVERRIDER": "S4", "DIVIDED_A": "S5",
          "DIVIDED_B": "S5", "CONVERGE_OLD": "S6", "CONVERGE_NEW": "S6", "WALK1_PARROT": "S2",
          "WALK2_MIXED": "PARTIAL", "R4_ARGUABLE_OVERRIDE": "REVERSED_LADDER_OVERRIDE",
          "R4_ARGUABLE_NORECOG": "REVERSED_LADDER", "OVERSHOOT_T1": "COMPOSITE"}
WITH_FORMATS = ("FAITHFUL", "REASONER", "WALK2_MIXED", "PARROT", "OVERRIDER", "DIVIDED_A", "DIVIDED_B",
                "CONVERGE_OLD", "CONVERGE_NEW", "WALK1_PARROT", "CEILING", "REFUSER")
NOISE = {"deterministic": dict(consistency="exact"),
         "independent": dict(consistency=None),
         "consistent": dict(consistency=0.9)}
GATE_NOISE = "independent"
GATE_MAX_WRONG = 1          # the set criterion: a wrong scenario in at most 1 of 20 runs per archetype
LEVELS = (0.95, 0.90, 0.80, 0.50)
NR = analyze.NOT_RESOLVED_SCENARIO


def outcome(model, got, possible):
    """intended / not_resolved / not_resolved_excluded / wrong for one archetype in one run, each archetype on its
    own route. A NOT_RESOLVED
    route whose possible scenarios do not include the intended one is reported apart (not_resolved_excluded): it
    claims no scenario, so the set criterion allows it, but the intervals have already set the intended one out."""
    want = EXPECT[model]
    if got == want:
        return "intended"
    if got == NR:
        return "not_resolved" if (possible is None or want in possible) else "not_resolved_excluded"
    return "wrong"


VARIANTS = {"favoured": dict(open_blocks="favoured"), "guard": dict(s1_point_guard=True),
            "favoured_guard": dict(open_blocks="favoured", s1_point_guard=True)}
# The registered rule includes the guard (s1_point_guard=True is the router's default), so "guard" is now the registered rule
# itself and "favoured" already carries the guard; the earlier comparison without the guard is in the earlier report.
VARIANT_WORDS = {"ruled": "the registered rule (an open account reading "
                          "blocks every later route, and withholds S1 only when its estimate points to an account)",
                 "favoured": "an open account reading blocks only when its estimate points to the route (guard kept)",
                 "guard": "the registered rule again (the guard is part of the rule)",
                 "favoured_guard": "the same as the second row (the guard is part of every rule)"}


def route_at_level(res, model, level, t5_rows, family_of, generation_of, **opts):
    """Re-read one model's T1, T3 and T4 (and its family's T5) at another interval level from the replicates the
    pack kept, and route it again with the same three-valued router. At 0.95 this reproduces the pack's route."""
    mr = res["model_results"][model]
    rr = mr["resolution_reps"]
    iv = lambda reps: (call_bootstrap.interval(reps, level) if reps else None)  # noqa: E731
    t1 = analyze.test_T1_memorization(rr["t1_points"], rr["t1_raw"], drop_ci=iv(rr["t1"]), resolve=True)
    has_mid = rr["t3_points"].get(analyze.LADDER_MIDDLE) is not None
    t3 = analyze.test_T3_ladder(rr["t3_points"], mr["eff_cls"], mr["recog_by_struct"], rr["t3_raw"],
                                ci=dict(top_minus_bottom=iv(rr["t3_tmb"]),
                                        bottom_minus_middle=(iv(rr["t3_bmm"]) if has_mid else None)), resolve=True)
    t4 = analyze.test_T4_formats(rr["t4_points"], rr["t4_undefined"], rr["t4_raw"], diff_ci=iv(rr["t4"]),
                                 resolve=True)
    fam = family_of[model]
    members = [m for m in family_of if family_of[m] == fam]
    gens = {generation_of[m]: m for m in members}
    has_gen = "old" in gens and "new" in gens
    t5_pack = next((r for r in t5_rows if r["model"] == model), {"trajectory": "n/a"})
    if has_gen:
        new, old = res["model_results"][gens["new"]], res["model_results"][gens["old"]]
        t5 = analyze.test_T5_trajectory(old["fid_primary"], new["fid_primary"],
                                        traj_ci=iv(analyze.diff_reps(new["fid_primary_reps"], old["fid_primary_reps"])),
                                        resolve=True)
    else:
        t5 = t5_pack
    if res["failed_controls"]:
        # a failed positive control makes every pattern-test reading uninformative (resolved, routing nowhere),
        # exactly as build_pack marks them
        t1 = dict(t1, reading="uninformative", p_steep="F", p_flat="F", resolved=True)
        t3 = dict(t3, reading="uninformative", reversed=False, attribution="", p_declines="F", p_reversed="F",
                  p_flat="F", resolved=True)
        t4 = dict(t4, reading="uninformative", p_falls="F", p_flat="F", resolved=True)
        t5 = dict(t5, trajectory="uninformative", p_rising="F", p_falling="F", p_flat="F", resolved=True)
    fam_consistent = len({res["model_results"][m]["overall"] for m in members}) <= 1
    _, s, poss = analyze.route_resolved(model, mr["scored_cells"], t1, mr["t2_override"], t3, t4, t5, mr["ginfo"],
                                        mr["agree"], fam_consistent, has_gen, effect_classes=mr["eff_cls"],
                                        overall=mr["overall"], t2_state=mr["t2_state"], **opts)
    open_tests = [n for n, t in (("T1", t1), ("T3", t3), ("T4", t4)) if not t.get("resolved", True)]
    if has_gen and not t5.get("resolved", True):
        open_tests.append("T5")
    # diagnostics (after the review): readings whose point lies outside its own interval (the combine can put it
    # there), and the largest share of undefined replicates among the tests' replicate lists
    outside = 0
    for point, reps in _points_and_reps(rr):
        if point is None or not reps:
            continue
        lo, hi = call_bootstrap.interval(reps, level)
        if lo is not None and not (lo <= point <= hi):
            outside += 1
    undef = max([sum(1 for v in reps if v is None) / len(reps) for reps in
                 (rr["t1"], rr["t3_tmb"], rr["t3_bmm"], rr["t4"]) if reps] or [0.0])
    return s, poss, open_tests, outside, undef


def _points_and_reps(rr):
    """(point, replicates) of every difference a reading is resolved on: the T1 drop, T3's two differences, T4's."""
    out = []
    tp = sorted(rr["t1_points"])
    if len(tp) >= 2:
        out.append((rr["t1_points"][tp[0]] - rr["t1_points"][tp[-1]], rr["t1"]))
    f = rr["t3_points"]
    top = [f[s] for s in analyze.LADDER_TOP if f.get(s) is not None]
    low, mid = f.get(analyze.LADDER_BOTTOM), f.get(analyze.LADDER_MIDDLE)
    if top and low is not None:
        out.append((sum(top) / len(top) - low, rr["t3_tmb"]))
        if mid is not None:
            out.append((low - mid, rr["t3_bmm"]))
    p = rr["t4_points"]
    if p.get("numbers") is not None and p.get("pictures") is not None:
        out.append((p["numbers"] - p["pictures"], rr["t4"]))
    return out


def one_run(seed, noise_key):
    cfg = NOISE[noise_key]
    rng = random.Random(seed)
    analyze._INDEX_CACHE.clear()     # drop the previous run's data (memory only)
    H = synth.gen_human(700, rng, icc=0.10, with_formats=True, sim_topup_participants=1000,
                        published_n_per_tier=350)
    models = {m: synth.gen_model(m, 200, rng, with_formats=(m in WITH_FORMATS), consistency=cfg["consistency"])
              for m in EXPECT}
    # one fixed scratch pack folder, overwritten by every run and never deleted (the authors' standing rule of
    # 2026-09-29: no delete operation of any kind, temporary folders included).
    tmp = os.path.join(tempfile.gettempdir(), "context_effects_release_scratch", "stability_pack")
    os.makedirs(os.path.join(tmp, "tests"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "figures"), exist_ok=True)
    saved_paths = (analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR)
    try:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = tmp, os.path.join(tmp, "tests"), os.path.join(tmp, "figures")
        res = analyze.build_pack(H, models, H, H, seed=seed, mode="STABILITY", design=analyze.Design.for_synth())
    finally:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = saved_paths
    route = {r["model"]: r["scenario"] for r in res["routing_rows"]}
    possible = {r["model"]: r.get("possible_scenarios", "") for r in res["routing_rows"]}
    family_of = {m: synth.MODEL_ARCHETYPES[m]["family"] for m in EXPECT}
    generation_of = {m: synth.MODEL_ARCHETYPES[m]["generation"] for m in EXPECT}
    row = dict(seed=seed, noise=noise_key)
    for m in EXPECT:
        got = route.get(m, "missing")
        poss = [p for p in possible.get(m, "").split(";") if p]
        row[f"route_{m}"] = got
        row[f"qualifier_{m}"] = next((r.get("qualifier", "") for r in res["routing_rows"] if r["model"] == m), "")
        for vname, vopts in VARIANTS.items():
            row[f"route_{vname}_{m}"] = route_at_level(res, m, 0.95, res["test_T5_rows"], family_of, generation_of,
                                                       **vopts)[0]
        row[f"possible_{m}"] = ";".join(poss)
        row[f"out_{m}"] = outcome(m, got, poss or None)
        for lv in LEVELS:
            s, poss_lv, open_tests, outside, undef = route_at_level(res, m, lv, res["test_T5_rows"], family_of,
                                                                     generation_of)
            key = f"{int(round(lv * 100))}"
            row[f"out{key}_{m}"] = outcome(m, s, poss_lv)
            if lv == 0.95:
                row[f"open_{m}"] = ";".join(open_tests)
                row[f"check95_{m}"] = int(s == got)       # the re-read at 95 percent must equal the pack
                row[f"outside_{m}"] = outside             # readings whose point lies outside its interval
                row[f"undef_{m}"] = round(undef, 4)       # largest share of undefined replicates
    t1 = {r["model"]: r for r in res["test_T1_rows"]}
    t4 = {r["model"]: r for r in res["test_T4_rows"]}
    row.update(T1_FAITHFUL=t1["FAITHFUL"]["reading"].split(":")[0],
               T1_FAITHFUL_ci=f"{t1['FAITHFUL'].get('drop_lo')}..{t1['FAITHFUL'].get('drop_hi')}",
               T4_FAITHFUL=t4["FAITHFUL"]["reading"].split(":")[0].split(" ")[0],
               T4_FAITHFUL_ci=f"{t4['FAITHFUL'].get('diff_lo')}..{t4['FAITHFUL'].get('diff_hi')}",
               topup_fired=int(res["topup"]["fired"]), first_trial_fired=int(res["first_trial"]["fired"]))
    return row


def commit_free_gb():
    """Free commit (page file plus RAM) on Windows, in GB; None elsewhere or on failure."""
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            return m.ullAvailPageFile / 1e9
    except Exception:  # noqa: BLE001
        return None
    return None


def run_in_subprocess(seed, noise_key):
    """One run in a fresh interpreter, so its memory goes back to the system when it ends (a long-lived
    process keeps what it freed, and this machine is shared). Waits while free commit is under 1.2 GB."""
    import subprocess
    for _ in range(40):
        f = commit_free_gb()
        if f is None or f >= 1.2:
            break
        time.sleep(30)
    else:
        raise SystemExit("free commit memory stayed under 1.2 GB for 20 minutes; stopping (runs so far are banked)")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", str(seed), noise_key],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise SystemExit(f"run {seed} {noise_key} failed: {p.stderr.strip().splitlines()[-1:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def rates(rs, m, prefix="out"):
    """(intended, not resolved with the intended scenario still possible, not resolved with it excluded, wrong)
    as shares of the runs, and the count of wrong runs."""
    n = len(rs)
    c = defaultdict(int)
    for r in rs:
        c[r[f"{prefix}_{m}"]] += 1
    return (c["intended"] / n, c["not_resolved"] / n, c["not_resolved_excluded"] / n, c["wrong"] / n,
            c["wrong"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out", default=os.path.join(HERE, "MODEL_NOISE_STABILITY.md"))
    ap.add_argument("--one", nargs=2, metavar=("SEED", "NOISE"), help=argparse.SUPPRESS)
    ap.add_argument("--report-only", action="store_true",
                    help="rebuild the report from the banked model_noise_stability_runs.csv without running")
    args = ap.parse_args()
    if args.one:
        print(json.dumps(one_run(int(args.one[0]), args.one[1])))
        return
    t0 = time.time()
    runs = []
    plan = [(n, s) for n in ("independent", "deterministic", "consistent") for s in range(args.seeds)]
    csv_path = os.path.join(HERE, "model_noise_stability_runs.csv")
    if args.report_only:
        with open(csv_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                for k in list(r):
                    if k.startswith(("check95_", "outside_")):
                        r[k] = int(r[k])
                    elif k.startswith("undef_"):
                        r[k] = float(r[k])
                runs.append(r)
        plan = []
    for i, (n, s) in enumerate(plan):
        runs.append(run_in_subprocess(20260929 + 1000 * s, n))
        # banked after every run (overwritten, never deleted), so a stopped sweep keeps what it measured
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(runs[0].keys()))
            w.writeheader()
            w.writerows(runs)
        print(f"{i + 1}/{len(plan)} runs, {round(time.time() - t0)} s", flush=True)
    groups = defaultdict(list)
    for r in runs:
        groups[r["noise"]].append(r)
    order = [n for n in ("independent", "deterministic", "consistent") if n in groups]
    L = ["# The design requirement: routing of the planted archetypes with every reading resolved against its interval", "",
         f"(Generated by model_noise_stability.py, 2026-09-29, {len(runs)} runs of the full pipeline with the joint "
         "bootstrap on"
         + (" (report rebuilt from the banked model_noise_stability_runs.csv)" if args.report_only
            else f", {round(time.time() - t0)} s") + ". Planned human sizes: 350 choices per published-tier cell, 700 "
         "per invented cell. Seeds 20260929 + 1000 k.)", "",
         "Model noise: independent = every call an independent draw at the planted share (10 draws per text prompt, "
         "60 per picture prompt; the registered noise and the criterion's condition); deterministic = the same prompts with every "
         "prompt answering one option in all its draws, except one remainder prompt per paraphrase that keeps the cell's "
         "share exact (in a two-option cell of six prompts that remainder is a large share of the calls, so this "
         "condition still carries some model-side noise; faithful_resolution_by_sample.py removes it entirely); "
         "consistent = each prompt gives its modal answer in 90 percent of its draws.", "",
         "## Share of runs per archetype (95 percent, the registered level)", "",
         "Each cell: intended scenario / not resolved with the intended scenario still possible / not resolved with "
         "the intended scenario already ruled out / wrong scenario. Each archetype is counted on its own route.", "",
         "| archetype (intended) | " + " | ".join(f"{n} (n={len(groups[n])})" for n in order) + " |",
         "|---|" + "---|" * len(order)]
    for m, want in EXPECT.items():
        cells = []
        for n in order:
            a, b, x, c, _ = rates(groups[n], m)
            cells.append(f"{a:.2f} / {b:.2f} / {x:.2f} / {c:.2f}")
        L.append(f"| {m} ({want}) | " + " | ".join(cells) + " |")
    # which readings stay open, per archetype, under the criterion's condition
    # the route counts per archetype
    L += ["", f"## Route counts per archetype under {GATE_NOISE} draws ({len(groups.get(GATE_NOISE, []))} runs)", "",
          "S1 counts include S1 with a qualifier (in brackets: how many of them carry one).", "",
          "| archetype (intended) | routes |", "|---|---|"]
    for m, want in EXPECT.items():
        gr = groups.get(GATE_NOISE, [])
        counts = defaultdict(int)
        for r in gr:
            counts[r[f"route_{m}"]] += 1
        q = sum(1 for r in gr if r[f"route_{m}"] == "S1" and r.get(f"qualifier_{m}"))
        parts = [f"{sc} {n}" + (f" ({q} qualified)" if sc == "S1" and q else "")
                 for sc, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
        L.append(f"| {m} ({want}) | " + ", ".join(parts) + " |")
    # the design comparisons: the registered rule against three alternatives, from the same runs
    L += ["", f"## The same {GATE_NOISE} runs under alternative routing rules (comparisons, not the registered rule)", "",
          "| rule | FAITHFUL routed to S1 | archetypes with a wrong scenario in more than 1 of 20 runs | criterion |",
          "|---|---|---|---|"]
    gr = groups.get(GATE_NOISE, [])
    for vname in ("ruled",) + tuple(VARIANTS):
        key = (lambda m: f"route_{m}") if vname == "ruled" else (lambda m, v=vname: f"route_{v}_{m}")
        if not gr or key("FAITHFUL") not in gr[0]:
            continue
        n_s1 = sum(1 for r in gr if r[key("FAITHFUL")] == "S1")
        bad = []
        for m, want in EXPECT.items():
            nw = sum(1 for r in gr if r[key(m)] not in (want, NR))
            if nw > GATE_MAX_WRONG * len(gr) / 20.0:
                bad.append(f"{m} {nw}")
        ok = (not bad) and n_s1 > len(gr) / 2.0
        L.append(f"| {VARIANT_WORDS[vname]} | {n_s1} of {len(gr)} | {'; '.join(bad) or 'none'} | "
                 f"{'passes' if ok else 'fails'} |")
    for vname in VARIANTS:
        if not gr or f"route_{vname}_FAITHFUL" not in gr[0]:
            continue
        L += ["", f"Route counts under: {VARIANT_WORDS[vname]}", "", "| archetype (intended) | routes |", "|---|---|"]
        for m, want in EXPECT.items():
            counts = defaultdict(int)
            for r in gr:
                counts[r[f"route_{vname}_{m}"]] += 1
            L.append(f"| {m} ({want}) | " + ", ".join(f"{sc} {n}" for sc, n in
                                                      sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))) + " |")
    L += ["", f"## Readings left open under {GATE_NOISE} draws (share of runs in which each test is not resolved)", "",
          "| archetype | T1 | T3 | T4 | T5 |", "|---|---|---|---|---|"]
    rs = groups.get(GATE_NOISE, [])
    for m in EXPECT:
        if rs:
            L.append(f"| {m} | " + " | ".join(f"{sum(1 for r in rs if t in r[f'open_{m}'].split(';')) / len(rs):.2f}"
                                             for t in ("T1", "T3", "T4", "T5")) + " |")
    # diagnostics the review asked for: points outside their own interval, and undefined replicates
    L += ["", f"## Interval diagnostics under {GATE_NOISE} draws", "",
          "| archetype | runs with a point outside its own interval | largest share of undefined replicates |",
          "|---|---|---|"]
    for m in EXPECT:
        if rs:
            L.append(f"| {m} | {sum(1 for r in rs if r[f'outside_{m}'] > 0)} of {len(rs)} | "
                     f"{max(r[f'undef_{m}'] for r in rs):.3f} |")
    # what a less demanding interval would give (a re-reading of the same replicates; the registered level stays
    # 95 percent, and the criterion is never loosened)
    L += ["", f"## The same runs re-read at other interval levels ({GATE_NOISE} draws)", "",
          "Each cell as above. A narrower level is NOT the same as a larger sample: the estimates stay exactly as "
          "noisy as they are here, so this shows how the readings behave with a less demanding interval, not what more "
          "data would give (more data would also move the estimates toward their planted values). For scale only, at "
          "the normal approximation a 90 percent interval is as wide as the 95 percent interval of about 1.4 times the "
          "samples, 80 percent about 2.3 times, 50 percent about 8.5 times.", "",
          "| archetype (intended) | " + " | ".join(f"{int(lv * 100)} percent" for lv in LEVELS) + " |",
          "|---|" + "---|" * len(LEVELS)]
    for m, want in EXPECT.items():
        if rs:
            cells = []
            for lv in LEVELS:
                a, b, x, c, _ = rates(rs, m, f"out{int(round(lv * 100))}")
                cells.append(f"{a:.2f} / {b:.2f} / {x:.2f} / {c:.2f}")
            L.append(f"| {m} ({want}) | " + " | ".join(cells) + " |")
    consistent_95 = all(r[f"check95_{m}"] for r in runs for m in EXPECT)
    L += ["", f"Re-reading at 95 percent reproduces every route in the pack: {'yes' if consistent_95 else 'NO'}.", ""]

    def share(key, field, val):
        g = groups[key]
        return f"{sum(1 for r in g if str(r[field]).startswith(val)) / len(g):.2f}"
    L += ["## Other checks (share of runs)", "", "| reading | " + " | ".join(order) + " |", "|---|" + "---|" * len(order)]
    for label, field, val in (("FAITHFUL T1 flat (resolved)", "T1_FAITHFUL", "flat"),
                              ("FAITHFUL T1 not resolved", "T1_FAITHFUL", "not resolved"),
                              ("FAITHFUL T1 steep (a false retrieval reading)", "T1_FAITHFUL", "steep"),
                              # the format test is descriptive (no reading), so these two rows read 0 by
                              # construction; a false reason-construction route shows as a wrong route in the tables
                              ("FAITHFUL T4 flat (descriptive, always 0)", "T4_FAITHFUL", "flat"),
                              ("FAITHFUL T4 falls (descriptive, always 0)", "T4_FAITHFUL", "falls"),
                              ("similarity supplement check fires (no planted difference)", "topup_fired", "1"),
                              ("first-trial check fires (no planted divergence)", "first_trial_fired", "1")):
        L.append(f"| {label} | " + " | ".join(share(k, field, val) for k in order) + " |")
    # THE DESIGN criterion (refuses): under independent draws at the planned sizes, a wrong scenario in at most one run
    # of twenty per archetype. NOT_RESOLVED is allowed and reported.
    fails = []
    if rs:
        for m in EXPECT:
            nwrong = rates(rs, m)[-1]
            allowed = GATE_MAX_WRONG * len(rs) / 20.0
            if nwrong > allowed:
                fails.append(f"{m} wrong in {nwrong} of {len(rs)} runs")
        # the faithful archetype reaches S1, with or without the qualifier, in
        # most runs
        n_s1 = sum(1 for r in rs if r["route_FAITHFUL"] == "S1")
        if not n_s1 > len(rs) / 2.0:
            fails.append(f"FAITHFUL reaches S1 in only {n_s1} of {len(rs)} runs")
    L += ["", "## The design requirement", "",
          (f"Under {GATE_NOISE} draws at the planned human sizes, a wrong scenario appears in at most {GATE_MAX_WRONG} of "
           "20 runs per archetype, and the faithful archetype reaches S1 (with or without the qualifier) in most runs. "
           + ("PASS." if rs and not fails and consistent_95 else
              ("REFUSED: " + "; ".join(fails) + "." if fails else
               ("REFUSED: the 95 percent re-reading does not reproduce the pack." if rs else
                "NOT RUN (no independent runs).")))), ""]
    text = "\n".join(L)
    open(args.out, "w", encoding="utf-8", newline="\n").write(text)
    print(text)
    sys.exit(1 if fails or not rs or not consistent_95 else 0)


if __name__ == "__main__":
    main()
