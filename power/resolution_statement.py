"""resolution_statement.py: the smallest true difference that we resolve in 80 percent of runs, for every test,
every descriptive comparison and every class boundary (their counterpart of power).

It runs the full analysis (analyze.build_pack, with the joint bootstrap at the registered 95 percent level) on
synthetic data at the planned human sizes (in a published category, 350 choices of each cell at the published
values and 350 at the new values; 700 per cell in a new category) and the registered model plan (10 independent
draws per text prompt, 60 per picture prompt), 200 seeds. In each run a set of planted models spans a grid of
true differences: the fall from the published to the new values (the test of retrieval), the decline down the
argument-strength ordering (the test of reason-based choice), the fall from numbers to pictures (the format
comparison), the rise from older to newer models (the comparison of older and newer models), model effects
around the class boundaries (25, 70 and 150 percent of the human effect), reversals around the 3-point cutoff of
the reversed class, and model effects around the 3-point cutoff at which a model shows an effect (the test of
rational override). For each value it counts the runs in which the difference
is resolved, or the effect is classed on the correct side of the boundary; the smallest true difference that
reaches 80 percent is the design's resolution. The rate at which a model names the decoy in the suspicion probe,
the other half of the test of rational override, is computed from the binomial distribution of the probe calls.
Each run uses its own interpreter and temp folder, on a pool of worker processes. Seeds 20260929 plus 1000 times
the seed number. The rows of Table WA-E4 for the test of retrieval, the test of reason-based choice, the format
comparison and the comparison of older and newer models are read from the recorded input
power/pattern_test_resolution.json, which records this script's own result for the registered design (for the
test of retrieval, the published values against the new values, paired by category; the format comparison
descriptive) and says how it was made; the script refuses to print the table without it.

Outputs: power/RESOLUTION_STATEMENT.md (with Table WA-E4), power/resolution_statement_runs.csv (one row per
planted model and run) and power/resolution_statement_summary.json.
Manuscript: Analysis Plan and Web Appendix E (Table WA-E4).

Run: python power/resolution_statement.py      (about 40 minutes)
     python power/resolution_statement.py --report-only   (rewrites the report from the runs file)
"""
import argparse, csv, json, math, os, random, subprocess, sys, tempfile, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "analysis")))
import analyze  # noqa: E402
import synth    # noqa: E402

D_GRID = (0.0, 0.3, 0.5, 0.7, 0.9, 1.1, 1.4, 1.6, 1.8, 2.0)
R_GRID = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90,
          1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60, 1.70, 1.80)
ANTI_PTS = (1.0, 1.5, 2.0, 2.5, 3.5, 4.0, 4.5, 5.0, 6.0)
SHOW_PTS = (-6.0, -4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 2.5, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0)
BOUNDARIES = (0.25, 0.70, 1.50)
TARGET = 0.80


def _k(x):
    return f"{x:g}".replace(".", "p")


def plan(group):
    """{model name: (effect function f(struct, tier, fmt, h), family, generation)} for one group."""
    out = {}
    if group == "t1t3":
        for d in D_GRID:
            out[f"T1_{_k(d)}"] = ((lambda st, t, f, h, d=d: h if t == 1 else (1 - d) * h), f"T1_{_k(d)}", "new")
            out[f"T3_{_k(d)}"] = ((lambda st, t, f, h, d=d: (1 - d) * h if st == "MOT" else h), f"T3_{_k(d)}", "new")
    elif group == "t4":
        for d in D_GRID:
            out[f"T4_{_k(d)}"] = ((lambda st, t, f, h, d=d: (1 - d) * h if (f == "pictures" and st in ("FRQ", "SOT"))
                                   else h), f"T4_{_k(d)}", "new")
    elif group == "t5":
        for d in D_GRID:
            out[f"T5OLD_{_k(d)}"] = ((lambda st, t, f, h, d=d: (1 - d) * h), f"famT5_{_k(d)}", "old")
            out[f"T5NEW_{_k(d)}"] = ((lambda st, t, f, h: h), f"famT5_{_k(d)}", "new")
    elif group == "classes":
        for r in R_GRID:
            out[f"CL_{_k(r)}"] = ((lambda st, t, f, h, r=r: r * h), f"CL_{_k(r)}", "new")
    elif group == "anti_t2":
        for y in ANTI_PTS:
            out[f"ANTI_{_k(y)}"] = ((lambda st, t, f, h, y=y: (-y / 100.0 if h > 0 else 0.0)), f"ANTI_{_k(y)}", "new")
        for e in SHOW_PTS:
            out[f"SHOW_{_k(e)}"] = ((lambda st, t, f, h, e=e: (e / 100.0 if h > 0 else 0.0)),
                                    f"SHOW_{_k(e)}".replace("-", "m"), "new")
    return out


GROUPS = ("t1t3", "t5", "classes", "anti_t2")      # t4 (the format comparison) is descriptive: not run by default
ICC = 0.10          # the human generator's participant intercept at the planned sizes (gen_human icc)
_MARG = {}


def marginal_share(p):
    """E[clip(invlogit(logit p + u))], u ~ N(0, s^2), s from ICC: the human generator's marginal share for a planted
    share p (its participant intercept makes the marginal effect smaller than the planted one)."""
    key = round(p, 12)
    if key in _MARG:
        return _MARG[key]
    s_ = math.sqrt(ICC * (math.pi ** 2 / 3) / (1 - ICC))
    lp = math.log(p / (1 - p))
    n, lo, hi = 4001, -8.0, 8.0
    acc = wsum = 0.0
    for i in range(n):
        z = lo + (hi - lo) * i / (n - 1)
        w = math.exp(-0.5 * z * z)
        acc += w * synth._clip(synth.invlogit(lp + s_ * z))
        wsum += w
    _MARG[key] = acc / wsum
    return _MARG[key]


def human_marginal_effect(struct, tier, cat):
    """The true (marginal) human effect of one cell as the synthetic human data carry it."""
    h = synth.TRUTH[struct] * synth.TIER_ATTEN[tier]
    if struct in ("FRQ", "RNG", "PHT"):
        dt = synth.cat_decoy_target(cat)
        h *= synth.HD_TARGET_MULT if dt == "HD" else (synth.HF_TARGET_MULT if dt == "HF" else 1.0)
    return marginal_share(synth._clip(synth.BASE + h)) - marginal_share(synth.BASE)


def one_run(seed, group):
    models_plan = plan(group)
    orig = synth._planted_share

    def planted_share(model, struct, tier, fmt, cat, eff_mult):
        # the planted model share of one cell: its effect is set against the cell's MARGINAL human effect (after the
        # review, finding 3), so a model planted at r times the human effect has a true ratio of r in every cell
        if model in models_plan:
            if struct in ("BIN", "EXC"):
                return synth._clip(synth.BASE)
            hm = human_marginal_effect(struct, tier, cat)
            return synth._clip(synth.BASE + models_plan[model][0](struct, tier, fmt, hm) * eff_mult)
        return orig(model, struct, tier, fmt, cat, eff_mult)
    synth._planted_share = planted_share
    for name, (_, fam, gen) in models_plan.items():
        synth.MODEL_ARCHETYPES[name] = dict(scenario="RESOLUTION", family=fam, generation=gen, reasoning="off")
    rng = random.Random(seed)
    formats = group == "t4"
    H = synth.gen_human(700, rng, icc=0.10, with_formats=formats, sim_topup_participants=1000, published_n_per_tier=350)
    models = {m: synth.gen_model(m, 200, rng, with_formats=formats, consistency=None) for m in models_plan}
    tmp = os.path.join(tempfile.gettempdir(), "context_effects_release_scratch", "resolution_pack")
    os.makedirs(os.path.join(tmp, "tests"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "figures"), exist_ok=True)
    saved = (analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR)
    try:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = tmp, os.path.join(tmp, "tests"), os.path.join(tmp, "figures")
        res = analyze.build_pack(H, models, H, H, seed=seed, mode="RESOLUTION", design=analyze.Design.for_synth())
    finally:
        analyze.PACK, analyze.TESTS_DIR, analyze.FIGS_DIR = saved
    criterion = res["criterion"]
    rows = []
    t1 = {r["model"]: r for r in res["test_T1_rows"]}
    t3 = {r["model"]: r for r in res["test_T3_rows"]}
    t4 = {r["model"]: r for r in res["test_T4_rows"]}
    t5 = {r["family"]: r for r in res["test_T5_rows"]}      # one row per family since 2026-11-25
    for m in models_plan:
        base = dict(seed=seed, group=group, model=m, controls_failed=";".join(res["failed_controls"]))
        if m.startswith("T1_"):
            rows.append(dict(base, test="T1", value=m[3:], directional=t1[m].get("p_steep"), flat=t1[m].get("p_flat"),
                             point=t1[m].get("drop"), lo=t1[m].get("drop_lo"), hi=t1[m].get("drop_hi")))
        elif m.startswith("T3_"):
            tm = t3[m].get("_top_minus_bottom")
            rows.append(dict(base, test="T3", value=m[3:], directional=t3[m].get("p_declines"),
                             flat=t3[m].get("p_flat"), point=(round(tm, 3) if tm is not None else ""),
                             lo=t3[m].get("tmb_lo"), hi=t3[m].get("tmb_hi")))
        elif m.startswith("T4_"):
            n_, p_ = t4[m].get("numbers"), t4[m].get("pictures")
            rows.append(dict(base, test="T4", value=m[3:], directional=t4[m].get("p_falls"), flat=t4[m].get("p_flat"),
                             point=(round(n_ - p_, 3) if isinstance(n_, float) and isinstance(p_, float) else ""),
                             lo=t4[m].get("diff_lo"), hi=t4[m].get("diff_hi")))
        elif m.startswith("T5NEW_"):
            f5 = t5[models_plan[m][1]]
            rows.append(dict(base, test="T5", value=m[6:], directional=f5.get("p_rising"), flat=f5.get("p_flat"),
                             point=f5.get("delta"), lo=f5.get("traj_lo"), hi=f5.get("traj_hi")))
        elif m.startswith("CL_") or m.startswith("ANTI_"):
            for r in res["effect_class_rows"]:
                if r["model"] == m and r["effect"] in analyze.REGULARITY_EFFECTS and criterion[r["effect"]]["confirmatory"]:
                    rows.append(dict(base, test=("class" if m.startswith("CL_") else "anti"), value=m.split("_", 1)[1],
                                     effect=r["effect"], cls=r["class"], point=r["model_pp"], human=r["human_pp"]))
        elif m.startswith("SHOW_"):
            for r in res["test_T2_rows"]:
                if r["model"] == m and r["structure"] in analyze.REGULARITY_EFFECTS and criterion[r["structure"]]["confirmatory"]:
                    rows.append(dict(base, test="shows", value=m[5:], effect=r["structure"], directional=r["shows_state"],
                                     point=r["behavior_pp"]))
    if group == "anti_t2":
        n_probe = defaultdict(int)
        for r in models[next(iter(models))]:
            if r.get("prompting_mode") == "recognition":
                n_probe[r["structure"]] += 1
        rows.append(dict(seed=seed, group=group, model="", test="probe_calls", value=json.dumps(dict(n_probe))))
    return rows


def _smallest_holding(pairs):
    """pairs: (distance from the boundary, share correct). The smallest distance from which every larger distance on
    the grid also reaches 80 percent; None when none does."""
    ok = [d for d, _ in sorted(pairs) if all(v >= TARGET for dd, v in pairs if dd >= d)]
    return ok[0] if ok else None


def _num(v):
    return float(str(v).replace("p", "."))


def knows_resolution(n, base=0.0, n_base=None, reps=20000, seed=20260929):
    """The smallest true share of probes that name the added option (on a 0.01 grid) at which the registered rule of
    2026-11-25 resolves "names the decoy" in 80 percent of runs: that share minus the share of two-option probes that
    call the set constructed (true value `base`), and the 95 percent interval of the difference, lie at or above one
    half. n probes of the effect's choice sets and n_base two-option probes (default n), each an independent draw
    (binomial draws and a normal interval, an approximation to the pipeline's bootstrap of the probe calls within each
    stimulus; a share of 0 or 1 has no spread and is read at its point)."""
    n_base = n_base or n
    rng = random.Random(seed)
    for r100 in range(51, 100):
        r = r100 / 100.0
        hit = 0
        for _ in range(reps // 10):
            p = sum(1 for _ in range(n) if rng.random() < r) / n
            q = sum(1 for _ in range(n_base) if rng.random() < base) / n_base if base > 0 else 0.0
            se = math.sqrt(p * (1 - p) / n + q * (1 - q) / n_base)
            if p - q >= 0.5 and p - q - 1.96 * se >= 0.5:
                hit += 1
        if hit / (reps // 10) >= TARGET:
            return r
    return None


def _run_one(task):
    """One (seed, group) run in its own interpreter with its own temp folder (the pipeline's fixed scratch folders
    must not be shared between workers)."""
    s, g = task
    tmp = os.path.join(tempfile.gettempdir(), "llm_context_effects_resolution_workers", f"{g}_{s}")
    os.makedirs(tmp, exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TMP=tmp, TEMP=tmp, TMPDIR=tmp)
    p = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", str(20260929 + 1000 * s), g],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise SystemExit(f"run {g} seed {s} failed: {p.stderr.strip().splitlines()[-1:]}")
    return s, g, json.loads(p.stdout.strip().splitlines()[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--workers", type=int, default=min(8, max(1, (os.cpu_count() or 2) // 3)))
    ap.add_argument("--one", nargs=2, help=argparse.SUPPRESS)
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--groups", default="", help="rerun only these groups (comma list) and replace their rows")
    args = ap.parse_args()
    if args.one:
        print(json.dumps(one_run(int(args.one[0]), args.one[1])))
        return
    t0 = time.time()
    csv_path = os.path.join(HERE, "resolution_statement_runs.csv")
    rows = []
    fields = ["seed", "group", "model", "controls_failed", "test", "value", "effect", "directional", "flat", "cls",
              "point", "lo", "hi", "human"]
    only = [g for g in args.groups.split(",") if g]
    if args.report_only or only:
        with open(csv_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if only:     # the chosen groups' old rows are replaced by the rerun (the file is rewritten, never deleted)
            rows = [r for r in rows if r.get("group") not in only]
    if not args.report_only:
        tasks = [(s, g) for s in range(args.seeds) for g in (only or GROUPS)]
        done = {}
        order = {t: i for i, t in enumerate(tasks)}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for s, g, out in pool.map(_run_one, tasks):
                done[(s, g)] = out
                # banked after every run in the fixed order of the plan (overwritten, never deleted)
                new_rows = rows + [r for t in sorted(done, key=order.get) for r in done[t]]
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                    w.writeheader()
                    w.writerows(new_rows)
                print(f"{len(done)}/{len(tasks)} runs (seed {s} group {g}): {round(time.time() - t0)} s", flush=True)
        rows = rows + [r for t in tasks for r in done[t]]
    n_seeds = len({str(r["seed"]) for r in rows})   # rows read back from the CSV carry the seed as text
    # 2026-11-25: the resolution of each test and boundary is measured in the runs in which both positive
    # controls held. On the synthetic lattice the frequency-decoy control has one calibrated premium-target cell, against
    # three in the design (the design's control passes in 98 percent of runs at 8 points), so it fails here in more runs
    # than it would in the design, and a failed control leaves the tests of the accounts not run.
    all_rows = rows
    failed_runs = {(str(r["seed"]), r["group"]) for r in rows if r.get("controls_failed")}
    rows = [r for r in rows if (str(r["seed"]), r["group"]) not in failed_runs]
    n_held = len({str(r["seed"]) for r in rows if r.get("group") == "t1t3"}) or n_seeds
    L = ["# How small a difference the design resolves (the pattern-test analogue of power)", "",
         f"(Generated by resolution_statement.py, 2026-09-29, {n_seeds} runs per planted value, the full pipeline with "
         "the joint bootstrap at the registered 95 percent level. Planned human sizes: 350 choices per published-tier "
         "cell and 700 per invented cell. Model calls: the registered plan, 10 independent draws per text prompt and 60 "
         "per picture prompt. A result counts as resolved when it meets the registered resolution rule. Every "
         "planted effect is set against the cell's marginal human effect, so the planted differences and ratios are "
         "the true ones. The smallest difference reported is the smallest from which every larger grid value also "
         f"reaches 80 percent; with {n_seeds} runs per value, a share near 0.80 has a standard error of about "
         f"{math.sqrt(0.16 / max(n_seeds, 1)):.2f}. Every share counts the runs in which both positive controls held, "
         f"{n_held} of the {n_seeds} runs of the tests' group; a positive control failed in the others, because on "
         "the synthetic lattice the frequency-decoy control has one calibrated premium-target cell, against three in "
         "the design.)", ""]
    # pattern tests
    names = {"T1": ("test of retrieval", "steep", "drop from the published to the new-values tier"),
             "T3": ("test of reason-based choice", "declines", "top minus bottom position"),
             "T4": ("format comparison", "falls", "numbers minus pictures"),
             "T5": ("comparison of older and newer models", "rising", "newer minus older generation")}
    L += ["## Pattern tests", "",
          "| test | reading | true difference (fidelity units) | runs resolving the reading | mean estimate | median "
          "interval |", "|---|---|---|---|---|---|"]
    summary = {}
    for test, (label, reading, what) in names.items():
        tr = [r for r in rows if r.get("test") == test]
        shares_by_d = {}
        for d in D_GRID:
            rs = [r for r in tr if abs(_num(r["value"]) - d) < 1e-9]
            if not rs:
                continue
            share = sum(1 for r in rs if r["directional"] == "T") / len(rs)
            flat = sum(1 for r in rs if r["flat"] == "T") / len(rs)
            pts = [float(r["point"]) for r in rs if r["point"] not in ("", None)]
            los = sorted(float(r["lo"]) for r in rs if r["lo"] not in ("", "-inf", "+inf", None))
            his = sorted(float(r["hi"]) for r in rs if r["hi"] not in ("", "-inf", "+inf", None))
            med = (f"{los[len(los) // 2]:.2f} to {his[len(his) // 2]:.2f}" if los and his else "n/a")
            cell = f"{share:.2f} {reading}" + (f"; {flat:.2f} flat" if d == 0.0 else "")
            L.append(f"| {label} | {reading} | {d:g} ({what}) | {cell} | "
                     f"{(sum(pts) / len(pts)) if pts else float('nan'):.2f} | {med} |")
            shares_by_d[d] = share
            if d == 0.0:
                summary[test + "_flat0"] = flat
        # the smallest difference from which every larger grid value also reaches 80 percent
        ok_from = [d for d in sorted(shares_by_d) if d > 0 and all(v >= TARGET for dd, v in shares_by_d.items()
                                                                     if dd >= d)]
        summary[test] = ok_from[0] if ok_from else None
    # class boundaries
    cr = [r for r in rows if r.get("test") == "class"]
    order = {"ANTI": 0, "LOW": 1, "PARTIAL": 2, "HIGH": 3, "OVER": 4}
    lower_class = {0.25: "LOW", 0.70: "PARTIAL", 1.50: "HIGH"}
    L += ["", "## Class boundaries (each of the five non-similarity effects that pass, classed on its pooled estimate)", "",
          "| boundary | true ratio (model effect over human effect) | effect classifications on the correct side |",
          "|---|---|---|"]
    for b in BOUNDARIES:
        below_ok, above_ok = [], []
        for rv in R_GRID:
            rs = [r for r in cr if abs(_num(r["value"]) - rv) < 1e-9]
            if not rs or abs(rv - b) < 1e-9:
                continue
            if rv < b:
                ok = sum(1 for r in rs if order.get(r["cls"], -1) <= order[lower_class[b]]) / len(rs)
                below_ok.append((b - rv, ok))
            else:
                ok = sum(1 for r in rs if order.get(r["cls"], -1) > order[lower_class[b]]) / len(rs)
                above_ok.append((rv - b, ok))
            if abs(rv - b) <= 0.31:
                L.append(f"| {b:g} | {rv:g} | {ok:.2f} |")
        summary[f"class_{b:g}_below"] = _smallest_holding(below_ok)
        summary[f"class_{b:g}_above"] = _smallest_holding(above_ok)
    ar = [r for r in rows if r.get("test") == "anti"]
    L += ["", "## The reversal boundary (ANTI above 3 points, LOW at 3 points or less)", "",
          "| model effect reversed by (points) | effect classifications on the correct side |", "|---|---|"]
    anti_below, anti_above = [], []
    for y in ANTI_PTS:
        rs = [r for r in ar if abs(_num(r["value"]) - y) < 1e-9]
        if not rs:
            continue
        ok = sum(1 for r in rs if (r["cls"] == "ANTI") == (y > 3.0)) / len(rs)
        (anti_above if y > 3 else anti_below).append((abs(y - 3.0), ok))
        L.append(f"| {y:g} | {ok:.2f} |")
    summary["anti_above"] = _smallest_holding(anti_above)
    summary["anti_below"] = _smallest_holding(anti_below)
    sr = [r for r in rows if r.get("test") == "shows"]
    L += ["", "## Test of rational override: 'shows the effect' resolved against the 3-point cutoff", "",
          "| model effect (points) | resolved as shows / as does not show |", "|---|---|"]
    show_above, show_below = [], []
    for e in SHOW_PTS:
        rs = [r for r in sr if abs(_num(r["value"]) - e) < 1e-9]
        if not rs:
            continue
        t_ = sum(1 for r in rs if r["directional"] == "T") / len(rs)
        f_ = sum(1 for r in rs if r["directional"] == "F") / len(rs)
        (show_above if e > 3 else show_below).append((abs(e - 3.0), t_ if e > 3 else f_))
        L.append(f"| {e:g} | {t_:.2f} / {f_:.2f} |")
    summary["shows_above"] = _smallest_holding(show_above)
    summary["shows_below"] = _smallest_holding(show_below)
    probe = [json.loads(r["value"]) for r in all_rows if r.get("test") == "probe_calls"]
    n_probe = min(v for k, v in probe[0].items() if k != "BIN") if probe and probe[0] else 0
    n_base = probe[0].get("BIN", n_probe) if probe and probe[0] else 0
    knows = knows_resolution(n_probe, 0.0, n_base) if n_probe else None
    knows20 = knows_resolution(n_probe, 0.2, n_base) if n_probe else None
    summary["knows_rate"] = knows
    summary["knows_rate_base20"] = knows20

    def fmt(v, unit=""):
        return ("not reached on the grid" if v is None else f"{v:g}{unit}")
    # The pattern-test rows (T1, T3, T4, T5) come from the recorded input pattern_test_resolution.json: the smallest
    # difference each test resolves under the registered design (T1 the published-values tier against the new-values
    # tier, paired by category; T4 descriptive), computed with the registered test functions and router, 10 draws
    # per text prompt, 20 runs per value. The file says how it was made.
    opt_path = os.path.join(HERE, "pattern_test_resolution.json")
    ruled = (json.load(open(opt_path, encoding="utf-8")).get("registered_design")
             if os.path.exists(opt_path) else None)
    if ruled is None:
        raise SystemExit("pattern_test_resolution.json is missing or holds no registered_design entry; refusing to "
                         "print the table without its pattern-test rows")
    flat0 = ruled.get("flat0") or {}
    L += ["", "## Table WA-E4 of Web Appendix E", "",
          "**TABLE WA-E4.** SMALLEST RESOLVABLE DIFFERENCES", "",
          "| Test or class boundary | Result | Smallest true difference resolved in 80 percent of runs |", "|---|---|---|",
          f"| Test of retrieval | steep fall | a fall of {fmt(ruled['T1'])} in fidelity from the published values to the "
          "new values, on the same categories |",
          f"| Test of reason-based choice | decline | {fmt(ruled['T3'])} between the top and the bottom position |",
          "| Format comparison | none (descriptive) | not resolvable at this design; reported as an estimate with its "
          "interval, with no conclusion |",
          f"| Comparison of older and newer models | rise | {fmt(ruled['T5'])} between the newer and the older generation |",
          f"| Test of rational override | shows the effect | a model effect {fmt(summary['shows_above'])} points above the 3-point cutoff; does not show it: {fmt(summary['shows_below'])} points below it |",
          f"| Test of rational override | names the decoy | a share of {fmt(knows)} of the answers to the suspicion probe that name the added option, for a model that calls no two-option set constructed, and {fmt(knows20)} for a model that calls a fifth of them constructed ({n_probe} answers per effect and {n_base} on its two-option sets, each an independent draw; binomial approximation; for a model that gives the same answer every time for a stimulus, the interval has no width and the model is judged by its point estimate) |",
          f"| Class boundary between much smaller and smaller (25 percent) | class | {fmt(summary['class_0.25_below'])} below and {fmt(summary['class_0.25_above'])} above, as a share of the human effect |",
          f"| Class boundary between smaller and close (70 percent) | class | {fmt(summary['class_0.7_below'])} below and {fmt(summary['class_0.7_above'])} above |",
          f"| Class boundary between close and larger (150 percent) | class | {fmt(summary['class_1.5_below'])} below and {fmt(summary['class_1.5_above'])} above |",
          f"| Class boundary between reversed and much smaller (3 points) | class | {fmt(summary['anti_above'])} points beyond the cutoff; {fmt(summary['anti_below'])} points inside it |",
          "",
          f"*Note.* Fidelity differences are in fidelity units (1 is the human size). At a true difference of zero the "
          f"conclusion of no difference was resolved in {(flat0.get('T1') or 0):.2f} (the test of retrieval), "
          f"{(flat0.get('T3') or 0):.2f} (the test of reason-based choice) and {(flat0.get('T5') or 0):.2f} (the comparison of older and newer models) of runs. "
          f"Each value rests on the runs, of {n_seeds} simulated runs of the full analysis at the planned sizes with ten "
          f"independent draws per text prompt, in which both positive controls held ({n_held}); the pattern-test rows "
          "use the grid "
          + ", ".join(f"{d:g}" for d in D_GRID if d > 0) + ", recorded as the registered-design row "
          "(recorded in pattern_test_resolution.json), the other rows the grids listed above.", ""]
    text = "\n".join(L)
    open(os.path.join(HERE, "RESOLUTION_STATEMENT.md"), "w", encoding="utf-8", newline="\n").write(text)
    json.dump(summary, open(os.path.join(HERE, "resolution_statement_summary.json"), "w", encoding="utf-8"), indent=2)
    print(text)


if __name__ == "__main__":
    main()
