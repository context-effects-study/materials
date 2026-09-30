#!/usr/bin/env python3
"""calibration_analysis.py: the analysis of each calibration wave.

For one wave's Qualtrics export it
  1. reads the export through analysis/ingest.py, the same reader and the same registered exclusions as
     the confirmatory surveys (preview, incomplete, duplicate, failed attention check, and a median
     choice-page time under 3 seconds); engineering test rows, marked by the STRESS prefix on the
     participant id, are dropped first;
  2. maps every kept choice to its calibration pair and computes the target option's share per pair, with
     a 95 percent Wilson interval and a cluster-robust standard error (respondent = cluster);
  3. gives each pair its verdict against the registered band (target chosen by 40 to 45 percent; outside
     25 to 75 percent is a hard flag; tier-1 published pairs are reported, never adjusted);
  4. logs the mechanical price adjustment the registered rule suggests (waves 1 and 2);
  5. scores the structure comprehension checks against the registered 70 percent benchmark, and, in waves
     2 and 3, the realism ratings of the invented categories against the 5.0 threshold;
  6. in wave 3, applies the final-wave decision rule fixed before any wave-3 data: a pair locks when its
     share is inside 40 to 45 percent, or when its 95 percent interval overlaps 40 to 45 and the share is
     between 33 and 50 percent;
  7. writes the report.
The calibration data never enter a confirmatory analysis.

Run (from the release root; run_all.py does this for all three waves):
  python calibration/calibration_analysis.py --export calibration/wave1/data/raw/calibration_wave1_export.csv
      --wave wave1 --mapping calibration/wave1/survey/calibration_wave1_MAPPING_rng_corrected.json
      --label reproduction --out reproduction/calibration_report_wave1.md
  (likewise for wave2 and wave3 with their own export and mapping)
  python calibration/calibration_analysis.py --selftest | --selftest-wave2 | --selftest-wave3
      (synthetic data with known shares; asserts the analysis recovers them)
Manuscript: Web Appendix F, Tables WA-F2, WA-F3 (wave 1), WA-F4 (wave 2), WA-F5 (wave 3) and WA-F7
(comprehension checks), and the calibration paragraphs of the Method.
"""
from __future__ import annotations
import argparse, csv, io, json, math, os, random, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
# Layout: the survey engine lives at
# surveys/ in the working repository and at surveys/ in the public deposit; take the first
# that exists. working repository behavior is unchanged.
ENGINE = next((p for p in (os.path.join(ROOT, "engines", "human_qualtrics"),
                           os.path.join(ROOT, "surveys")) if os.path.isdir(p)),
              os.path.join(ROOT, "engines", "human_qualtrics"))
sys.path.insert(0, ENGINE)
# In the deposit, ingest.py lives in analysis/ (it is the analysis-side export reader); in the
# working repository it lives with the survey engine. Put the analysis dir on the path too when it exists.
_AN = os.path.join(ROOT, "analysis")
if os.path.isdir(_AN):
    sys.path.insert(0, _AN)
import ingest as I                                   # the fixed Contract-A reader (exclusions included)
import generate_calibration as GC                    # the pair table (single source, from stimuli.json)

# final calibration lock NOTE (2026-07-02): the calibration waves were fielded BEFORE the terminal value lock, from
# the stimulus file preserved at stimuli/stimuli_prelock.json. The final calibration lock lock then rewrote
# stimuli.json (new values; the exited pictures hard-drives variant removed), so re-running a wave
# analysis against the live file would no longer derive the 25-pair pre-lock design. Point the
# pair table and the ingest decode at the snapshot when it exists (the exact source the fielded
# instruments and the official wave runs used); fall back to the live file otherwise. This mirrors
# the same note in calibration_selftest.py.
_SNAPSHOT = os.path.join(ROOT, "stimuli", "stimuli_prelock.json")
if os.path.exists(_SNAPSHOT):
    GC.STIMULI = _SNAPSHOT
    I.STIM = _SNAPSHOT

STIMULI = os.path.join(ROOT, "stimuli", "stimuli.json")
MAPPING = next((p for p in (os.path.join(ENGINE, "out", "calibration_MAPPING.json"),
                            os.path.join(HERE, "wave1", "survey", "calibration_wave1_MAPPING.json"))
                if os.path.exists(p)),
               os.path.join(ENGINE, "out", "calibration_MAPPING.json"))
DEFAULT_OUT = os.path.join(ROOT, "reproduction", "calibration_report.md")

BAND_LO, BAND_HI = 40.0, 45.0                        # registered TARGET band (%)
HARD_LO, HARD_HI = 25.0, 75.0                        # hard-flag limits (%)
GEO_BENCHMARK = 0.70                                 # registered detection benchmark
ADJUSTABLE_BLOCKS = {"pub_t2", "inv_t3", "format_words", "format_pictures"}


# ---------------- pair table + row->arm mapping ----------------

def pair_table():
    S, cats, by_id, _ = GC.load_stimuli()
    pairs, _ = GC.select_calibration_pairs(S, cats)
    by_key = {}                                       # (stimulus_id, format) -> pair
    for p in pairs:
        by_key[(p["stimulus_id"], p["format"])] = p
    return pairs, by_key, S, cats, by_id


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def cluster_robust_se(rows_for_pair):
    """Cluster-robust SE of the share (respondent = cluster): sqrt( sum_c (sum_i in c (y_i - p))^2 ) / n.
    With one observation per cluster (the one-per-category rule guarantees this within a pair) it equals
    the heteroskedasticity-robust binomial SE sqrt(p(1-p)/n) up to the n/(n-1) small-sample factor."""
    n = len(rows_for_pair)
    if n == 0:
        return float("nan")
    p = sum(y for _, y in rows_for_pair) / n
    by_c = collections.defaultdict(float)
    for cid, y in rows_for_pair:
        by_c[cid] += (y - p)
    g = len(by_c)
    if g <= 1:
        return float("nan")
    ssq = sum(v * v for v in by_c.values())
    return math.sqrt(ssq * g / (g - 1)) / n


def round_price(x):
    """Round a suggested price to a realistic price point (mechanical, logged)."""
    if x < 20:
        # nearest .49 / .99 step
        base = math.floor(x)
        cands = [base - 0.01, base + 0.49, base + 0.99]
        return round(min(cands, key=lambda c: abs(c - x)), 2)
    if x < 100:
        return round(round(x) - 0.01, 2)              # x.99 at the nearest dollar
    return float(int(round(x / 10.0) * 10) - 1)       # e.g. 249


def nudge_suggestion(share_pct, rec, cat_target_focal, overrides=None):
    """The registered mechanical heuristic: shift the too-popular option's price by 10% of its value per
    10 share-points of imbalance (distance from the nearest band edge), rounded to a realistic point.
    `overrides` (wave 2+): the mapping's value_overrides_applied - the wave SHOWED those values, so the
    nudge bases on the shown (overridden) price, not the pre-nudge stimuli.json value."""
    tf = cat_target_focal.get(rec["category"])
    opts = {o["code"]: o for o in rec["options"]}
    if share_pct < BAND_LO:
        popular = next(c for c in opts if c != tf)     # COMP too popular
        imbalance = BAND_LO - share_pct
    else:
        popular = tf                                   # TARGET too popular
        imbalance = share_pct - BAND_HI
    price = opts[popular]["attrs"].get("price")
    shown = ""
    ov = (overrides or {}).get(rec["category"])
    if ov and ov.get("stimulus") == rec["id"] and ov.get("attribute") == "price":
        if ov.get("option") == popular:
            price = float(ov["to"])
            shown = " (from the shown wave value)"
    if price is None:
        return f"no price attribute on {popular} - manual review"
    shift = price * (imbalance / 10.0) * 0.10
    new_price = round_price(price + shift)
    return (f"raise {popular} price {price} -> {new_price}{shown} "
            f"(imbalance {imbalance:.1f}pp -> +{imbalance:.1f}% of value, rounded)")


def verdict_for(share_pct, block):
    if BAND_LO <= share_pct <= BAND_HI:
        return "IN BAND"
    if not (HARD_LO <= share_pct <= HARD_HI):
        return "HARD FLAG (outside 25-75; stimulus-defect branch)"
    return "ADJUST" if block in ADJUSTABLE_BLOCKS else "OUT OF BAND (tier-1 CHECK-ONLY; reported, never adjusted)"


# the TERMINAL LOCK CRITERION (wave 3; CALIBRATION_DESIGN wave-3 amendment (a), fixed 2026-07-02
# BEFORE any wave-3 data): the point window [33, 50] keeps the compromise target disadvantaged
# (<= 50: still the minority option) and non-extreme (>= 33: comfortably inside the 25-75 limits).
TERM_POINT_LO, TERM_POINT_HI = 33.0, 50.0


def terminal_verdict(share_pct, ci_lo, ci_hi):
    """Score one pair against the terminal lock criterion. Route 1: point in the registered band.
    Route 2: the 95% CI overlaps the band AND the point keeps the target disadvantaged and
    non-extreme. Anything else routes to the pre-registered stimulus-defect contingencies."""
    if share_pct != share_pct:                          # NaN: no data
        return "NO DATA"
    if BAND_LO <= share_pct <= BAND_HI:
        return "LOCK (point in band)"
    if ci_lo <= BAND_HI and ci_hi >= BAND_LO and TERM_POINT_LO <= share_pct <= TERM_POINT_HI:
        return "LOCK (CI-overlap route)"
    return "DEFECT CONTINGENCY (pre-registered)"


# ---------------- the analysis proper ----------------

def analyze(export_csv, label="real", wave="wave1", out_path=DEFAULT_OUT, mapping_path=None):
    pairs, by_key, S, cats, by_id = pair_table()
    mp = mapping_path or MAPPING
    mapping = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    # restrict the pair table to the arms THIS wave actually dealt (wave 2 deals a subset)
    dealt = {p["arm_id"] for p in mapping.get("calibration_pairs", [])} or None
    if dealt:
        pairs = [p for p in pairs if p["arm_id"] in dealt]
    overrides = mapping.get("value_overrides_applied") or {}
    by_id2, cats2, ctf = I.load_stimuli()
    pk, pl = I.load_pass_key()
    raw_rows = I.read_qualtrics_csv(export_csv)
    # Test responses carry a STRESS_ participant-id prefix (the standing rule: engineering test
    # rows are removed by prefix at analysis, never deleted from the export). The official wave
    # runs were fed *_for_analysis.csv files with those rows already stripped, so this drop is a
    # no-op there; it makes a run on the deposited scrubbed exports (which keep the test rows for
    # auditability) reproduce the official numbers. 
    raw_rows = [r for r in raw_rows if not (r.get("PROLIFIC_PID") or "").startswith("STRESS")]
    long_rows, excl = I.ingest(raw_rows, by_id2, cats2, ctf, pk, pl)

    # map kept BIN rows -> pairs
    per_pair = collections.defaultdict(list)          # arm_id -> [(participant_id, chose_target)]
    unmapped = 0
    for r in long_rows:
        if r["structure"] != "BIN":
            continue
        p = by_key.get((r["stimulus_id"], r["format"]))
        if p is None:
            unmapped += 1
            continue
        y = r["chose_target"]
        if y == "":
            continue
        per_pair[p["arm_id"]].append((r["participant_id"], int(y)))

    n_participants = len({r["participant_id"] for r in long_rows})
    dup_check_bad = 0
    for arm, obs in per_pair.items():
        ids = [cid for cid, _ in obs]
        if len(ids) != len(set(ids)):
            dup_check_bad += 1                        # someone answered the same pair twice (should never)

    results = []
    for p in pairs:
        obs = per_pair.get(p["arm_id"], [])
        n = len(obs)
        k = sum(y for _, y in obs)
        share = (k / n * 100) if n else float("nan")
        lo, hi = wilson_ci(k, n)
        se_cl = cluster_robust_se(obs)
        se_bin = math.sqrt((k / n) * (1 - k / n) / n) if n and 0 < k < n else (0.0 if n else float("nan"))
        rec = by_id[p["stimulus_id"]]
        v = verdict_for(share, p["block"]) if n else "NO DATA"
        term = terminal_verdict(share, lo * 100, hi * 100) if wave == "wave3" else None
        nudge = ""
        if wave == "wave3":
            # terminal wave: no next wave to nudge into - the trail column carries the lock verdict's
            # consequence instead of a mechanical suggestion
            if n and term == "DEFECT CONTINGENCY (pre-registered)":
                nudge = "route to the pre-registered stimulus-defect contingency (terminal wave)"
            elif n:
                nudge = "values lock at the final calibration lock (with the enrichment content)"
        elif n and v in ("ADJUST",):
            nudge = nudge_suggestion(share, rec, ctf, overrides=overrides)
        elif n and v.startswith("OUT OF BAND (tier-1"):
            nudge = "(check-only: reported, values fixed by fidelity to the published source)"
        elif n and v.startswith("HARD FLAG"):
            nudge = "route to the pre-registered stimulus-defect branch"
        results.append({"arm": p["arm_id"], "block": p["block"], "category": p["category"],
                        "stimulus": p["stimulus_id"], "format": p["format"], "n": n, "k": k,
                        "share_pct": share, "ci_lo": lo * 100, "ci_hi": hi * 100,
                        "se_cluster_pp": se_cl * 100 if se_cl == se_cl else float("nan"),
                        "se_binomial_pp": se_bin * 100 if se_bin == se_bin else float("nan"),
                        "verdict": v, "terminal": term, "nudge": nudge})

    # geometry manipulation checks (from the RAW rows: label exports; only the assigned item is
    # non-empty). Wave 3 deals TWO items per respondent: each structure aggregates over BOTH page
    # columns (export_tags = [geo1_x, geo2_x]); earlier waves carry the single export_tag.
    geo = []
    for gi in mapping.get("geometry_items", []):
        cols = gi.get("export_tags") or [gi["export_tag"]]
        vals = [row.get(c, "").strip() for row in raw_rows for c in cols if row.get(c, "").strip()]
        n = len(vals)
        k = sum(1 for v in vals if v == gi["correct_choice_label"])
        rate = k / n if n else float("nan")
        geo.append({"structure": gi["structure"], "tag": "+".join(cols), "n": n, "k": k, "rate": rate,
                    "correct": gi["correct_choice_label"],
                    "pass": (rate >= GEO_BENCHMARK) if n else None})

    # realism check (wave 2+: the registered invented-category plausibility items riding in the wave).
    # Labels export "1 - Not at all realistic" .. "7 - Completely realistic": parse the leading integer.
    realism = []
    rea_comments = []
    rc = mapping.get("realism_check") or {}
    kept_rids = None                                   # realism scored on KEPT respondents (fixed rules)
    if rc.get("items"):
        excl_ids = {e["participant_id"] for e in excl}
        for it in rc["items"]:
            col = it["export_tag"]
            scores = []
            for row in raw_rows:
                v = (row.get(col, "") or "").strip()
                if not v:
                    continue
                pid = I.pid_hash(row.get("PROLIFIC_PID", "") or row.get("ResponseId", ""))
                if pid in excl_ids:
                    continue
                try:
                    scores.append(int(str(v).split("-")[0].strip().split()[0]))
                except (ValueError, IndexError):
                    pass
            n = len(scores)
            mean = sum(scores) / n if n else float("nan")
            sd = (sum((s - mean) ** 2 for s in scores) / (n - 1)) ** 0.5 if n > 1 else float("nan")
            realism.append({"category": it["category"], "tag": col, "n": n, "mean": mean, "sd": sd,
                            "pct_ge5": (sum(1 for s in scores if s >= 5) / n * 100) if n else float("nan"),
                            "pass": (mean >= 5.0) if n else None})
        ccol = rc.get("comment_tag", "realism_comments")
        for row in raw_rows:
            c = (row.get(ccol, "") or "").strip()
            if c:
                pid = I.pid_hash(row.get("PROLIFIC_PID", "") or row.get("ResponseId", ""))
                if pid not in excl_ids:
                    rea_comments.append(c)

    # the picture-comprehension item (wave 3, amendment (e); kept respondents; DESCRIPTIVE)
    piccomp = None
    pc = mapping.get("pic_comprehension") or {}
    if pc.get("export_tag"):
        excl_ids_pc = {e["participant_id"] for e in excl}
        col = pc["export_tag"]
        vals = []
        for row in raw_rows:
            v = (row.get(col, "") or "").strip()
            if not v:
                continue
            pid = I.pid_hash(row.get("PROLIFIC_PID", "") or row.get("ResponseId", ""))
            if pid in excl_ids_pc:
                continue
            vals.append(v)
        n = len(vals)
        k = sum(1 for v in vals if v == pc["correct_choice_label"])
        piccomp = {"tag": col, "n": n, "k": k, "rate": (k / n) if n else float("nan"),
                   "correct": pc["correct_choice_label"]}

    # ---- report ----
    lines = []
    lines.append(f"# Calibration report - {wave}")
    if label != "real":
        lines.append("")
        lines.append("> **NOT A REAL CALIBRATION - `" + label.upper() + "` DATA.** This report was "
                     "generated from a test/synthetic export to prove the pipeline end-to-end. No real "
                     "calibration has run; nothing here informs any stimulus value.")
    lines.append("")
    lines.append(f"(Auto-written by calibration/calibration_analysis.py. Export: `{os.path.basename(export_csv)}`. "
                 f"Band: TARGET {BAND_LO:.0f}-{BAND_HI:.0f}% / hard limits {HARD_LO:.0f}-{HARD_HI:.0f}%. "
                 "Bundled design: one choice per category per respondent; respondent = cluster; the "
                 "per-pair cluster-robust error equals the binomial error because no respondent "
                 "contributes twice to a pair.)")
    lines.append("")
    lines.append(f"- responses ingested: {len(raw_rows)} rows -> {len(long_rows)} kept choice rows from "
                 f"{n_participants} kept respondents; {len(excl)} respondents excluded "
                 f"({collections.Counter(e['reasons'] for e in excl).most_common(5)})")
    lines.append(f"- unmapped BIN rows (not a calibration pair): {unmapped}")
    lines.append(f"- pairs with a within-pair duplicate respondent (must be 0): {dup_check_bad}")
    lines.append("")
    if wave == "wave3":
        lines.append("**TERMINAL WAVE.** Every pair is scored against the terminal lock criterion "
                     "(CALIBRATION_DESIGN wave-3 amendment (a), fixed 2026-07-02 before any wave-3 "
                     f"data): LOCK when the point estimate is in [{BAND_LO:.0f}, {BAND_HI:.0f}]; OR "
                     f"the 95% CI overlaps that band AND the point is in [{TERM_POINT_LO:.0f}, "
                     f"{TERM_POINT_HI:.0f}] (compromise target disadvantaged and non-extreme). A pair "
                     "failing both routes to its pre-registered stimulus-defect contingency and is "
                     "reported. Locked values (with the enrichment content) enter stimuli.json at the final calibration lock, "
                     "followed by the EXC re-derivation step.")
        lines.append("")
    term_col = " terminal lock verdict |" if wave == "wave3" else ""
    trail_col = "disposition" if wave == "wave3" else "mechanical nudge (logged)"
    for block, title in (("pub_t1", "Published tier-1 (CHECK-ONLY - never adjusted)"),
                         ("pub_t2", "Published tier-2 (adjustable)"),
                         ("inv_t3", "Invented tier-3 (adjustable)"),
                         ("format_words", "Format module - words (adjustable wording)"),
                         ("format_pictures", "Format module - pictures (adjustable rendering)")):
        if not any(r["block"] == block for r in results):
            continue                                   # a wave that dealt no pairs of this block (wave 2+)
        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"| pair | n | TARGET share | 95% CI | cluster SE | band verdict |{term_col} {trail_col} |")
        lines.append("|---|---|---|---|---|---|" + ("---|" if term_col else "") + "---|")
        for r in results:
            if r["block"] != block:
                continue
            share = f"{r['share_pct']:.1f}%" if r["n"] else "-"
            ci = f"[{r['ci_lo']:.1f}, {r['ci_hi']:.1f}]" if r["n"] else "-"
            se = f"{r['se_cluster_pp']:.1f}pp" if r["n"] and r["se_cluster_pp"] == r["se_cluster_pp"] else "-"
            tcell = f" {r['terminal']} |" if term_col else ""
            lines.append(f"| {r['arm']} | {r['n']} | {share} | {ci} | {se} | {r['verdict']} |{tcell} {r['nudge']} |")
        lines.append("")
    lines.append("## Geometry manipulation checks (structural validity; >=70% registered benchmark)")
    lines.append("")
    giv = mapping.get("geometry_instrument_version")
    if giv:
        lines.append(f"(Instrument: {giv})")
        lines.append("")
    lines.append("| structure | n | correct answers | rate | benchmark |")
    lines.append("|---|---|---|---|---|")
    for g in geo:
        rate = f"{g['rate']*100:.0f}%" if g["n"] else "-"
        bench = ("PASS" if g["pass"] else "FAIL") if g["n"] else "no data"
        lines.append(f"| {g['structure']} | {g['n']} | {g['k']} | {rate} | {bench} |")
    lines.append("")
    if piccomp:
        lines.append("## Picture-comprehension item (DESCRIPTIVE — amendment (e); no registered criterion)")
        lines.append("")
        rate = f"{piccomp['rate']*100:.0f}%" if piccomp["n"] else "-"
        lines.append(f"Respondents shown it (kept, dealt >=1 pictures pair): {piccomp['n']}; answered "
                     f"the computed key ({piccomp['correct']}: the option with more of the green-bar "
                     f"quality feature): {piccomp['k']} = **{rate}**. Reported with the trail as a "
                     "comprehension indicator for the pictures manipulation; nothing depends on it.")
        lines.append("")
    if realism:
        lines.append("## Realism check — invented categories (registered threshold: mean >= 5.0 on the "
                     "7-point 'reads like a real product page' item + no recurring confusion in comments)")
        lines.append("")
        if wave == "wave3":
            lines.append("(Wave-3 re-check at the ENRICHED descriptions — the registered 'revise "
                         "wording and re-check' remedy after the three wave-2 misses. kettles + desks "
                         "re-shown from the respondent's own dealt slots at the wave-3 values; "
                         "robot_vacuums — locked in wave 2, not dealt — shown as a static enriched "
                         "page at its locked values. Scored on kept respondents.)")
        else:
            lines.append("(The registered order put this check BEFORE the first calibration wave; it rides "
                         "IN wave 2 instead — the ordering deviation is documented in CALIBRATION_WAVE1 s4 "
                         "and the wave-2 MAPPING. Values shown to raters = the wave-2 shared values. Scored "
                         "on kept respondents.)")
        lines.append("")
        lines.append("| category | n | mean | SD | % ratings >= 5 | verdict |")
        lines.append("|---|---|---|---|---|---|")
        for r in realism:
            verdict = ("PASS" if r["pass"] else "FAIL (revise wording + re-check)") if r["n"] else "no data"
            mean = f"{r['mean']:.2f}" if r["n"] else "-"
            sd = f"{r['sd']:.2f}" if r["n"] > 1 else "-"
            p5 = f"{r['pct_ge5']:.0f}%" if r["n"] else "-"
            lines.append(f"| {r['category']} | {r['n']} | {mean} | {sd} | {p5} | {verdict} |")
        lines.append("")
        lines.append(f"Open comments (kept respondents, non-empty): {len(rea_comments)}. "
                     "Reviewed for recurring confusion; the raw texts stay in the export "
                     "(never quoted at length here to keep the deposit scrub simple).")
        lines.append("")
    if wave == "wave3":
        lines.append("RR hygiene: calibration responses never enter confirmatory analyses; wave 3 is "
                     "the TERMINAL wave — pairs lock under the criterion above or route to their "
                     "pre-registered defect contingencies (no further waves); locked values + the "
                     "enrichment content enter stimuli.json (calibration_locked) at the final calibration lock, followed by "
                     "the mandatory EXC re-derivation step and the geometry.py margin parameters "
                     "under the locking rule (CALIBRATION_DESIGN wave-3 amendment).")
    else:
        lines.append("RR hygiene: calibration responses never enter confirmatory analyses; adjustments follow "
                     "the mechanical heuristic above and are re-tested in the next wave; tier-1 pairs are "
                     "reported as-is; final values are locked into stimuli.json (calibration_locked) at the final calibration lock, "
                     "followed by the mandatory EXC re-derivation step (CALIBRATION_DESIGN).")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[calibration_analysis] {len(long_rows)} kept rows / {n_participants} respondents -> {out_path}")
    return results, geo, excl, realism, piccomp


# ---------------- synthetic bundled selftest ----------------

def synth_export(path, n_participants=400, seed="calib-synth-2026"):
    """Build a synthetic BUNDLED wide export (Qualtrics 3-header-row shape) with PLANTED per-pair shares,
    dealing pairs within category round-robin (even fill), one choice per category per respondent."""
    pairs, by_key, S, cats, by_id = pair_table()
    _, _, ctf = I.load_stimuli()
    slots = GC.group_slots(pairs)                      # [(t, category, [pair, ...])]
    rng = random.Random(seed)
    # plant a share per pair: cycle 0.42 (in band) / 0.62 (adjust) / 0.20 (hard flag)
    plan = {}
    cyc = [0.42, 0.62, 0.20]
    for i, p in enumerate(sorted(pairs, key=lambda x: x["arm_id"])):
        plan[p["arm_id"]] = cyc[i % 3]
    header = ["ResponseId", "PROLIFIC_PID", "DistributionChannel", "Finished", "consent",
              "attention_1", "age", "gender", "script_id", "calib_wave"]
    K = len(slots)
    for (t, _, _) in slots:
        header += [f"cell{t}_{s}" for s in ("calib_arm", "calib_block", "id", "category", "structure",
                                            "tier", "format", "order", "stimulus", "sim_placement")]
        header += [f"choice_{t}", f"choice_{t}_code", f"timer_{t}_Page Submit"]
    rows = []
    rr = {cat: 0 for (_, cat, _) in slots}             # per-category round-robin pointer
    for pid in range(n_participants):
        row = {h: "" for h in header}
        row.update({"ResponseId": f"R_synth{pid:05d}", "PROLIFIC_PID": f"SYN{pid:05d}",
                    "DistributionChannel": "anonymous", "Finished": "True", "consent": "yes",
                    "attention_1": "Strongly agree", "age": "35", "gender": "Woman",
                    "script_id": "calib_wave1", "calib_wave": "wave1"})
        for (t, cat, cat_pairs) in slots:
            arm = cat_pairs[rr[cat] % len(cat_pairs)]
            rr[cat] += 1
            rec = by_id[arm["stimulus_id"]]
            tf = ctf.get(rec["category"])
            other = next(o["code"] for o in rec["options"] if o["code"] != tf)
            y = 1 if rng.random() < plan[arm["arm_id"]] else 0
            code = tf if y else other
            row.update({
                f"cell{t}_calib_arm": arm["arm_id"], f"cell{t}_calib_block": arm["block"],
                f"cell{t}_id": f"{cat}_BIN", f"cell{t}_category": cat, f"cell{t}_structure": "BIN",
                f"cell{t}_tier": str(rec["memorization_tier"]), f"cell{t}_format": arm["format"],
                f"cell{t}_order": ",".join(o["code"] for o in rec["options"]),
                f"cell{t}_stimulus": rec["id"], f"cell{t}_sim_placement": "NA",
                f"choice_{t}": "1", f"choice_{t}_code": code,
                f"timer_{t}_Page Submit": f"{rng.uniform(4.0, 8.0):.2f}",
            })
        rows.append(row)
    # one decliner + one speeder + one attention-fail (prove the exclusions ride along)
    bad = []
    b1 = {h: "" for h in header}; b1.update({"ResponseId": "R_dec", "PROLIFIC_PID": "SYN_DEC",
          "DistributionChannel": "anonymous", "Finished": "True", "consent": "no"})
    bad.append(b1)
    b2 = dict(rows[0]); b2.update({"ResponseId": "R_speed", "PROLIFIC_PID": "SYN_SPEED"})
    for (t, _, _) in slots:
        b2[f"timer_{t}_Page Submit"] = "0.8"
    bad.append(b2)
    b3 = dict(rows[1]); b3.update({"ResponseId": "R_attn", "PROLIFIC_PID": "SYN_ATTN",
                                   "attention_1": "Agree"})
    bad.append(b3)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerow(["question text"] * len(header))            # metadata row 2
        w.writerow(['{"ImportId":"x"}'] * len(header))         # metadata row 3
        for row in rows + bad:
            w.writerow([row.get(h, "") for h in header])
    return plan, K


def synth_export_w2(path, mapping, n_participants=312, seed="calib-synth-w2-2026"):
    """Synthetic WAVE-2 export: the 17 dealt arms (from the wave-2 MAPPING), planted per-pair shares,
    planted geometry answers at 80% correct against the v2.2 keys, and planted realism ratings
    (kettles ~6.2 PASS / vacuums ~5.6 PASS / desks ~4.2 FAIL) + comments - proving the analysis parses
    the whole wave-2 structure and issues the registered verdicts."""
    pairs, by_key, S, cats, by_id = pair_table()
    _, _, ctf = I.load_stimuli()
    dealt = {p["arm_id"] for p in mapping["calibration_pairs"]}
    pairs = [p for p in pairs if p["arm_id"] in dealt]
    slots = GC.group_slots(pairs)
    rng = random.Random(seed)
    plan = {}
    cyc = [0.42, 0.62, 0.20]
    for i, p in enumerate(sorted(pairs, key=lambda x: x["arm_id"])):
        plan[p["arm_id"]] = cyc[i % 3]
    geo_items = mapping["geometry_items"]
    rc = mapping["realism_check"]
    rea_truth = {"electric_kettles": 6.2, "robot_vacuums": 5.6, "standing_desks": 4.2}
    header = ["ResponseId", "PROLIFIC_PID", "DistributionChannel", "Finished", "consent",
              "attention_1", "age", "gender", "script_id", "calib_wave", "geo_structure"]
    header += [gi["export_tag"] for gi in geo_items]
    header += [it["export_tag"] for it in rc["items"]] + [rc["comment_tag"]]
    for (t, _, _) in slots:
        header += [f"cell{t}_{s}" for s in ("calib_arm", "calib_block", "id", "category", "structure",
                                            "tier", "format", "order", "stimulus", "sim_placement")]
        header += [f"choice_{t}", f"choice_{t}_code", f"timer_{t}_Page Submit"]
    rows = []
    rr = {cat: 0 for (_, cat, _) in slots}
    for pid in range(n_participants):
        row = {h: "" for h in header}
        row.update({"ResponseId": f"R_synw2{pid:05d}", "PROLIFIC_PID": f"SW2{pid:05d}",
                    "DistributionChannel": "anonymous", "Finished": "True", "consent": "yes",
                    "attention_1": "Strongly agree", "age": "35", "gender": "Woman",
                    "script_id": "calib_wave2", "calib_wave": "wave2"})
        for (t, cat, cat_pairs) in slots:
            arm = cat_pairs[rr[cat] % len(cat_pairs)]
            rr[cat] += 1
            rec = by_id[arm["stimulus_id"]]
            tf = ctf.get(rec["category"])
            other = next(o["code"] for o in rec["options"] if o["code"] != tf)
            y = 1 if rng.random() < plan[arm["arm_id"]] else 0
            code = tf if y else other
            row.update({
                f"cell{t}_calib_arm": arm["arm_id"], f"cell{t}_calib_block": arm["block"],
                f"cell{t}_id": f"{cat}_BIN", f"cell{t}_category": cat, f"cell{t}_structure": "BIN",
                f"cell{t}_tier": str(rec["memorization_tier"]), f"cell{t}_format": arm["format"],
                f"cell{t}_order": ",".join(o["code"] for o in rec["options"]),
                f"cell{t}_stimulus": rec["id"], f"cell{t}_sim_placement": "NA",
                f"choice_{t}": "1", f"choice_{t}_code": code,
                f"timer_{t}_Page Submit": f"{rng.uniform(4.0, 8.0):.2f}",
            })
        gi = geo_items[pid % len(geo_items)]           # one geometry structure per respondent
        row["geo_structure"] = gi["structure"]
        wrong = [c for c in gi["choices"] if c != gi["correct_choice_label"]]
        row[gi["export_tag"]] = gi["correct_choice_label"] if rng.random() < 0.80 else rng.choice(wrong)
        for it in rc["items"]:                          # every respondent rates all 3 invented categories
            mu = rea_truth[it["category"]]
            score = min(7, max(1, round(rng.gauss(mu, 1.0))))
            row[it["export_tag"]] = f"{score} - anchor" if score in (1, 7) else str(score)
        if pid % 25 == 0:
            row[rc["comment_tag"]] = "The desk price felt a bit high but the pages looked real."
        rows.append(row)
    # one decliner + one speeder + one attention-fail (prove the exclusions ride along)
    bad = []
    b1 = {h: "" for h in header}; b1.update({"ResponseId": "R_dec", "PROLIFIC_PID": "SW2_DEC",
          "DistributionChannel": "anonymous", "Finished": "True", "consent": "no"})
    bad.append(b1)
    b2 = dict(rows[0]); b2.update({"ResponseId": "R_speed", "PROLIFIC_PID": "SW2_SPEED"})
    for (t, _, _) in slots:
        b2[f"timer_{t}_Page Submit"] = "0.8"
    bad.append(b2)
    b3 = dict(rows[1]); b3.update({"ResponseId": "R_attn", "PROLIFIC_PID": "SW2_ATTN",
                                   "attention_1": "Agree"})
    bad.append(b3)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerow(["question text"] * len(header))
        w.writerow(['{"ImportId":"x"}'] * len(header))
        for row in rows + bad:
            w.writerow([row.get(h, "") for h in header])
    return plan, len(slots), rea_truth


def run_selftest_wave2():
    import tempfile
    w2map = os.path.join(ENGINE, "out", "calibration_wave2_MAPPING.json")
    if not os.path.exists(w2map):
        print("wave-2 MAPPING missing - generate the wave-2 QSF first (generate_calibration.py "
              "--pairs-file wave2_pairs.json --wave wave2)")
        return False
    mapping = json.load(open(w2map, encoding="utf-8"))
    tmp = tempfile.mkdtemp(prefix="calib_selftest_w2_")
    exp = os.path.join(tmp, "synthetic_wave2_export.csv")
    rep = os.path.join(tmp, "calibration_report_W2TEST.md")
    plan, K, rea_truth = synth_export_w2(exp, mapping, n_participants=312)
    results, geo, excl, realism, piccomp = analyze(exp, label="synthetic-selftest-wave2", wave="wave2",
                                                   out_path=rep, mapping_path=w2map)
    ok = True
    def ck(name, cond, detail=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}  {detail}")
        ok &= bool(cond)
    ck("results restricted to the 17 wave-2 arms", len(results) == 17
       and {r["arm"] for r in results} == set(plan), f"{len(results)} arms")
    n_by = {r["arm"]: r["n"] for r in results}
    ck("every wave-2 arm received data", all(n > 0 for n in n_by.values()), f"min n={min(n_by.values())}")
    pairs, _, S, cats, by_id = pair_table()
    mult = collections.Counter()
    dealt = set(plan)
    for p in pairs:
        if p["arm_id"] in dealt:
            mult[p["category"]] += 1
    exp_n = {a: 312 // mult[next(p["category"] for p in pairs if p["arm_id"] == a)] for a in dealt}
    ck("even fill: binding 3-arm categories get participants/3 (=104), water_bottles /2, singles all",
       all(abs(n_by[a] - exp_n[a]) <= 1 for a in n_by),
       f"sample={ {a: (n_by[a], exp_n[a]) for a in sorted(n_by)[:3]} }")
    bad = [(r["arm"], r["share_pct"], plan[r["arm"]] * 100) for r in results
           if abs(r["share_pct"] - plan[r["arm"]] * 100) > 4 * max(r["se_binomial_pp"], 1e-9) + 1.0]
    ck("every arm's share recovers its planted truth (within 4 SE + 1pp)", not bad, str(bad[:3]))
    vbad = [(r["arm"], r["share_pct"], r["verdict"]) for r in results
            if r["n"] and r["verdict"] != verdict_for(r["share_pct"], r["block"])]
    ck("verdicts == the registered share->verdict mapping", not vbad, str(vbad[:3]))
    # nudges base on the SHOWN (overridden) wave-2 price where the popular option was overridden
    ov = mapping.get("value_overrides_applied", {})
    shown_ok = True
    detail = ""
    for r in results:
        if r["verdict"] != "ADJUST" or not r["nudge"]:
            continue
        o = ov.get(r["category"])
        if o and f"{o['option']} price" in r["nudge"]:
            if f"price {float(o['to'])}" not in r["nudge"] or "shown wave value" not in r["nudge"]:
                shown_ok = False; detail = f"{r['arm']}: {r['nudge']}"
    ck("ADJUST nudges base on the shown (overridden) price, flagged as such", shown_ok, detail)
    # geometry: all 7 structures scored against the v2.2 keys; planted 80% -> PASS everywhere
    ck("all 7 geometry structures scored (v2.2 keys incl. corrected RNG + clarified FRQ/SOT)",
       len(geo) == 7 and all(g["n"] > 0 for g in geo), f"{[(g['structure'], g['n']) for g in geo]}")
    ck("planted 80% correct -> every geometry structure PASSES the 70% benchmark",
       all(g["pass"] for g in geo), f"{[(g['structure'], round(g['rate'], 2)) for g in geo]}")
    # realism: means recovered; the planted low category FAILS the registered threshold
    ck("realism items scored for the 3 invented categories", len(realism) == 3
       and all(r["n"] > 250 for r in realism), f"{[(r['category'], r['n']) for r in realism]}")
    rbad = [(r["category"], r["mean"], rea_truth[r["category"]]) for r in realism
            if abs(r["mean"] - rea_truth[r["category"]]) > 0.35]
    ck("realism means recover the planted truths (clipped-gaussian tolerance 0.35)", not rbad, str(rbad))
    ck("realism verdicts: kettles+vacuums PASS, desks FAIL (mean < 5.0 planted)",
       all((r["pass"] is True) == (rea_truth[r["category"]] >= 5.0) for r in realism),
       f"{[(r['category'], r['pass']) for r in realism]}")
    reasons = ";".join(e["reasons"] for e in excl)
    ck("decliner/speeder/attention-fail excluded by the frozen rules",
       "speeder" in reasons and "attention" in reasons and len(excl) >= 3, reasons[:80])
    rep_txt = open(rep, encoding="utf-8").read()
    ck("report carries the realism section + the ordering-deviation note + NO empty tier-1 section",
       "## Realism check" in rep_txt and "ordering deviation" in rep_txt
       and "Published tier-1" not in rep_txt)
    ck("report file written", os.path.exists(rep), rep)
    print("RESULT:", "WAVE-2 CALIBRATION ANALYSIS SELFTEST GREEN" if ok else "SELFTEST FAILURE")
    return ok


def synth_export_w3(path, mapping, n_participants=462, seed="calib-synth-w3-2026"):
    """Synthetic WAVE-3 export: the 16 dealt arms (from the wave-3 MAPPING), planted per-pair shares
    chosen to produce ALL THREE terminal verdicts (0.42 -> LOCK point-in-band; 0.48 -> LOCK CI-overlap;
    0.62 -> DEFECT CONTINGENCY), TWO geometry answers per respondent from different structures (dealt
    as ordered pairs, planted 80% correct against the computed keys), planted realism ratings
    (kettles ~6.2 PASS / vacuums ~5.6 PASS / desks ~4.2 FAIL) + comments, and the picture-comprehension
    item (planted 90% Option B, present only when a pictures arm was dealt)."""
    pairs, by_key, S, cats, by_id = pair_table()
    _, _, ctf = I.load_stimuli()
    dealt = {p["arm_id"] for p in mapping["calibration_pairs"]}
    pairs = [p for p in pairs if p["arm_id"] in dealt]
    slots = GC.group_slots(pairs)
    rng = random.Random(seed)
    plan = {}
    cyc = [0.42, 0.48, 0.62]
    for i, p in enumerate(sorted(pairs, key=lambda x: x["arm_id"])):
        plan[p["arm_id"]] = cyc[i % 3]
    geo_items = mapping["geometry_items"]
    structs = [gi["structure"] for gi in geo_items]
    by_struct = {gi["structure"]: gi for gi in geo_items}
    geo_pairs = [(a, b) for a in structs for b in structs if a != b]      # the 42 ordered pairs
    rc = mapping["realism_check"]
    pc = mapping["pic_comprehension"]
    rea_truth = {"electric_kettles": 6.2, "robot_vacuums": 5.6, "standing_desks": 4.2}
    header = ["ResponseId", "PROLIFIC_PID", "DistributionChannel", "Finished", "consent",
              "attention_1", "age", "gender", "script_id", "calib_wave",
              "geo1_structure", "geo2_structure", "piccheck_slot", pc["export_tag"]]
    for gi in geo_items:
        header += gi["export_tags"]
    header += [it["export_tag"] for it in rc["items"]] + [rc["comment_tag"]]
    for (t, _, _) in slots:
        header += [f"cell{t}_{s}" for s in ("calib_arm", "calib_block", "id", "category", "structure",
                                            "tier", "format", "order", "stimulus", "sim_placement")]
        header += [f"choice_{t}", f"choice_{t}_code", f"timer_{t}_Page Submit"]
    rows = []
    rr = {cat: 0 for (_, cat, _) in slots}
    for pid in range(n_participants):
        row = {h: "" for h in header}
        row.update({"ResponseId": f"R_synw3{pid:05d}", "PROLIFIC_PID": f"SW3{pid:05d}",
                    "DistributionChannel": "anonymous", "Finished": "True", "consent": "yes",
                    "attention_1": "Strongly agree", "age": "35", "gender": "Woman",
                    "script_id": "calib_wave3", "calib_wave": "wave3"})
        pics_dealt = None
        for (t, cat, cat_pairs) in slots:
            arm = cat_pairs[rr[cat] % len(cat_pairs)]
            rr[cat] += 1
            rec = by_id[arm["stimulus_id"]]
            tf = ctf.get(rec["category"])
            other = next(o["code"] for o in rec["options"] if o["code"] != tf)
            y = 1 if rng.random() < plan[arm["arm_id"]] else 0
            code = tf if y else other
            if arm["format"] == "pictures" and pics_dealt is None:
                pics_dealt = t
            row.update({
                f"cell{t}_calib_arm": arm["arm_id"], f"cell{t}_calib_block": arm["block"],
                f"cell{t}_id": f"{cat}_BIN", f"cell{t}_category": cat, f"cell{t}_structure": "BIN",
                f"cell{t}_tier": str(rec["memorization_tier"]), f"cell{t}_format": arm["format"],
                f"cell{t}_order": ",".join(o["code"] for o in rec["options"]),
                f"cell{t}_stimulus": rec["id"], f"cell{t}_sim_placement": "NA",
                f"choice_{t}": "1", f"choice_{t}_code": code,
                f"timer_{t}_Page Submit": f"{rng.uniform(4.0, 8.0):.2f}",
            })
        s1, s2 = geo_pairs[pid % len(geo_pairs)]                # two DIFFERENT structures per respondent
        row["geo1_structure"], row["geo2_structure"] = s1, s2
        for pfx, st in (("geo1", s1), ("geo2", s2)):
            gi = by_struct[st]
            col = next(c for c in gi["export_tags"] if c.startswith(pfx + "_"))
            wrong = [c for c in gi["choices"] if c != gi["correct_choice_label"]]
            row[col] = gi["correct_choice_label"] if rng.random() < 0.80 else rng.choice(wrong)
        if pics_dealt is not None:                               # ~85%: the pic-comprehension item shows
            row["piccheck_slot"] = str(pics_dealt)
            row[pc["export_tag"]] = (pc["correct_choice_label"] if rng.random() < 0.90
                                     else rng.choice([c for c in ("Option A", "I cannot tell")]))
        for it in rc["items"]:                                   # every respondent rates all 3 categories
            mu = rea_truth[it["category"]]
            score = min(7, max(1, round(rng.gauss(mu, 1.0))))
            row[it["export_tag"]] = f"{score} - anchor" if score in (1, 7) else str(score)
        if pid % 25 == 0:
            row[rc["comment_tag"]] = "The pages looked like real product listings; nothing seemed off."
        rows.append(row)
    # one decliner + one speeder + one attention-fail (prove the exclusions ride along)
    bad = []
    b1 = {h: "" for h in header}; b1.update({"ResponseId": "R_dec", "PROLIFIC_PID": "SW3_DEC",
          "DistributionChannel": "anonymous", "Finished": "True", "consent": "no"})
    bad.append(b1)
    b2 = dict(rows[0]); b2.update({"ResponseId": "R_speed", "PROLIFIC_PID": "SW3_SPEED"})
    for (t, _, _) in slots:
        b2[f"timer_{t}_Page Submit"] = "0.8"
    bad.append(b2)
    b3 = dict(rows[1]); b3.update({"ResponseId": "R_attn", "PROLIFIC_PID": "SW3_ATTN",
                                   "attention_1": "Agree"})
    bad.append(b3)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerow(["question text"] * len(header))
        w.writerow(['{"ImportId":"x"}'] * len(header))
        for row in rows + bad:
            w.writerow([row.get(h, "") for h in header])
    return plan, len(slots), rea_truth


def run_selftest_wave3():
    import tempfile
    w3map = os.path.join(ENGINE, "out", "calibration_wave3_MAPPING.json")
    if not os.path.exists(w3map):
        print("wave-3 MAPPING missing - generate the wave-3 QSF first (generate_calibration.py "
              "--pairs-file wave3_pairs.json --wave wave3)")
        return False
    mapping = json.load(open(w3map, encoding="utf-8"))
    tmp = tempfile.mkdtemp(prefix="calib_selftest_w3_")
    exp = os.path.join(tmp, "synthetic_wave3_export.csv")
    rep = os.path.join(tmp, "calibration_report_W3TEST.md")
    plan, K, rea_truth = synth_export_w3(exp, mapping, n_participants=462)
    results, geo, excl, realism, piccomp = analyze(exp, label="synthetic-selftest-wave3", wave="wave3",
                                                   out_path=rep, mapping_path=w3map)
    ok = True
    def ck(name, cond, detail=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}  {detail}")
        ok &= bool(cond)
    ck("results restricted to the 16 wave-3 arms", len(results) == 16
       and {r["arm"] for r in results} == set(plan), f"{len(results)} arms")
    n_by = {r["arm"]: r["n"] for r in results}
    ck("every wave-3 arm received data", all(n > 0 for n in n_by.values()), f"min n={min(n_by.values())}")
    pairs, _, S, cats, by_id = pair_table()
    mult = collections.Counter()
    dealt = set(plan)
    for p in pairs:
        if p["arm_id"] in dealt:
            mult[p["category"]] += 1
    exp_n = {a: 462 // mult[next(p["category"] for p in pairs if p["arm_id"] == a)] for a in dealt}
    ck("even fill: binding 3-arm categories get participants/3 (=154), water_bottles /2 (=231), singles all",
       all(abs(n_by[a] - exp_n[a]) <= 1 for a in n_by),
       f"sample={ {a: (n_by[a], exp_n[a]) for a in sorted(n_by)[:3]} }")
    bad = [(r["arm"], r["share_pct"], plan[r["arm"]] * 100) for r in results
           if abs(r["share_pct"] - plan[r["arm"]] * 100) > 4 * max(r["se_binomial_pp"], 1e-9) + 1.0]
    ck("every arm's share recovers its planted truth (within 4 SE + 1pp)", not bad, str(bad[:3]))
    vbad = [(r["arm"], r["share_pct"], r["verdict"]) for r in results
            if r["n"] and r["verdict"] != verdict_for(r["share_pct"], r["block"])]
    ck("band verdicts == the registered share->verdict mapping", not vbad, str(vbad[:3]))
    # the terminal lock criterion: deterministic re-scoring + all three verdict families realized
    tbad = [(r["arm"], r["terminal"]) for r in results
            if r["n"] and r["terminal"] != terminal_verdict(r["share_pct"], r["ci_lo"], r["ci_hi"])]
    ck("terminal verdicts == the registered criterion on every pair", not tbad, str(tbad[:3]))
    tkinds = collections.Counter(r["terminal"] for r in results)
    ck("the planted design realizes ALL THREE terminal verdicts (both LOCK routes + DEFECT)",
       tkinds.get("LOCK (point in band)", 0) > 0 and tkinds.get("LOCK (CI-overlap route)", 0) > 0
       and tkinds.get("DEFECT CONTINGENCY (pre-registered)", 0) > 0, str(dict(tkinds)))
    # geometry: 7 structures scored over BOTH page columns; ~2N/7 answers each; planted 80% -> PASS
    ck("all 7 geometry structures scored over geo1_+geo2_ (n ~= 2N/7 = 132 each)",
       len(geo) == 7 and all(abs(g["n"] - 132) <= 2 for g in geo),
       f"{[(g['structure'], g['n']) for g in geo]}")
    ck("planted 80% correct -> every geometry structure PASSES the 70% benchmark",
       all(g["pass"] for g in geo), f"{[(g['structure'], round(g['rate'], 2)) for g in geo]}")
    # realism: 3 categories incl. the static robot_vacuums; the planted low category FAILS
    ck("realism items scored for the 3 invented categories (incl. the static robot_vacuums)",
       len(realism) == 3 and all(r["n"] > 400 for r in realism),
       f"{[(r['category'], r['n']) for r in realism]}")
    ck("realism verdicts: kettles+vacuums PASS, desks FAIL (planted)",
       all((r["pass"] is True) == (rea_truth[r["category"]] >= 5.0) for r in realism),
       f"{[(r['category'], r['pass']) for r in realism]}")
    # pic comprehension: the synthetic ROUND-ROBIN deal correlates across categories (pid%3==0 draws
    # pictures in all three 3-arm categories; pid%2==0 in water_bottles), so exactly
    # |{pid: pid%3==0 or pid%2==0}| = 2/3 of respondents carry a pictures arm - the live survey deals
    # independently (~85%), but the selftest asserts ITS OWN scheme's exact expectation.
    exp_pic_n = sum(1 for pid in range(462) if pid % 3 == 0 or pid % 2 == 0)
    ck("pic-comprehension scored on exactly the shown subset (round-robin: 2/3 of kept) at the "
       "planted ~90% key rate",
       piccomp is not None and piccomp["n"] == exp_pic_n and abs(piccomp["rate"] - 0.90) < 0.05,
       f"n={piccomp['n'] if piccomp else None} (expect {exp_pic_n}) "
       f"rate={round(piccomp['rate'], 3) if piccomp else None}")
    reasons = ";".join(e["reasons"] for e in excl)
    ck("decliner/speeder/attention-fail excluded by the frozen rules",
       "speeder" in reasons and "attention" in reasons and len(excl) >= 3, reasons[:80])
    rep_txt = open(rep, encoding="utf-8").read()
    ck("report carries the TERMINAL banner + lock column + pic-comprehension + enriched-realism note "
       "+ NO tier-1 section",
       "TERMINAL WAVE" in rep_txt and "terminal lock verdict" in rep_txt
       and "Picture-comprehension" in rep_txt and "ENRICHED descriptions" in rep_txt
       and "Published tier-1" not in rep_txt)
    ck("report file written", os.path.exists(rep), rep)
    print("RESULT:", "WAVE-3 CALIBRATION ANALYSIS SELFTEST GREEN" if ok else "SELFTEST FAILURE")
    return ok


def run_selftest():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="calib_selftest_")
    exp = os.path.join(tmp, "synthetic_calibration_export.csv")
    rep = os.path.join(tmp, "calibration_report_TEST.md")
    plan, K = synth_export(exp, n_participants=400)
    results, geo, excl, realism, piccomp = analyze(exp, label="synthetic-selftest", wave="wave1", out_path=rep)
    ok = True
    def ck(name, cond, detail=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}  {detail}")
        ok &= bool(cond)
    # coverage: every pair received data; quads ~100 each (400/4), doubles ~200, singles ~400
    n_by_pair = {r["arm"]: r["n"] for r in results}
    ck("all 25 pairs received data", all(n > 0 for n in n_by_pair.values()),
       f"min n={min(n_by_pair.values())}")
    mult = collections.Counter()
    pairs, _, S, cats, by_id = pair_table()
    for p in pairs:
        mult[p["category"]] += 1
    exp_n = {p["arm_id"]: 400 // mult[p["category"]] for p in pairs}
    ck("even fill per category (round-robin: n == participants / pairs-in-category)",
       all(abs(n_by_pair[a] - exp_n[a]) <= 1 for a in n_by_pair),
       f"sample: { {a: (n_by_pair[a], exp_n[a]) for a in list(n_by_pair)[:3]} }")
    # recovery: shares within sampling error of the planted truths
    bad = []
    for r in results:
        truth = plan[r["arm"]] * 100
        se = max(r["se_binomial_pp"], 1e-9)
        if abs(r["share_pct"] - truth) > 4 * se + 1.0:
            bad.append((r["arm"], r["share_pct"], truth))
    ck("every pair's share recovers its planted truth (within 4 SE + 1pp)", not bad, str(bad[:3]))
    # verdicts are exactly the registered mapping of the OBSERVED share (the deterministic unit under
    # test; the planted truth only sets where the share lands, up to sampling noise around the edges)
    vbad = [(r["arm"], r["share_pct"], r["verdict"]) for r in results
            if r["n"] and r["verdict"] != verdict_for(r["share_pct"], r["block"])]
    ck("verdicts == the registered share->verdict mapping on every pair", not vbad, str(vbad[:3]))
    verds = [r["verdict"] for r in results]
    ck("the planted design produces all three verdict families (IN BAND / ADJUST / HARD FLAG)",
       any(v == "IN BAND" for v in verds) and any(v == "ADJUST" for v in verds)
       and any(v.startswith("HARD") for v in verds),
       str(collections.Counter(verds).most_common()))
    # cluster SE ~= binomial SE (one obs per cluster within a pair)
    se_bad = [r["arm"] for r in results
              if r["n"] and abs(r["se_cluster_pp"] - r["se_binomial_pp"]) > 0.25 * max(r["se_binomial_pp"], 1e-9)]
    ck("cluster-robust SE ~= binomial SE per pair (one obs per respondent per pair)", not se_bad, str(se_bad[:3]))
    # nudges logged for ADJUST pairs
    ck("mechanical nudge logged on every ADJUST pair",
       all(r["nudge"] for r in results if r["verdict"] == "ADJUST"))
    # exclusions rode along
    reasons = ";".join(e["reasons"] for e in excl)
    ck("decliner/speeder/attention-fail excluded by the frozen rules",
       "speeder" in reasons and "attention" in reasons and len(excl) >= 3, reasons[:80])
    ck("report file written", os.path.exists(rep), rep)
    print("RESULT:", "CALIBRATION ANALYSIS SELFTEST GREEN" if ok else "SELFTEST FAILURE")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", help="raw Qualtrics CSV export of the calibration survey")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--label", default="real", help='"real" for the final run; anything else stamps a test banner')
    ap.add_argument("--wave", default="wave1")
    ap.add_argument("--mapping", default=None,
                    help="the wave's MAPPING.json (default: the wave-1 out/calibration_MAPPING.json; "
                         "wave 2 runs pass out/calibration_wave2_MAPPING.json)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selftest-wave2", action="store_true")
    ap.add_argument("--selftest-wave3", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if run_selftest() else 1)
    if args.selftest_wave2:
        sys.exit(0 if run_selftest_wave2() else 1)
    if args.selftest_wave3:
        sys.exit(0 if run_selftest_wave3() else 1)
    if not args.export:
        ap.error("provide --export PATH or --selftest / --selftest-wave2 / --selftest-wave3")
    analyze(args.export, label=args.label, wave=args.wave, out_path=args.out, mapping_path=args.mapping)


if __name__ == "__main__":
    main()
