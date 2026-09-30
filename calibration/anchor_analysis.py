"""anchor_analysis.py: the analysis of the realism comparison study.

The invented categories missed the registered realism threshold (a mean of 5.0 on the 7-point question
"does this read like a real product page?") in waves 2 and 3, but no published category's page had ever
been rated on that question. This study rated the seven published categories' pages, rendered exactly as
wave 3 rendered the invented ones, and this script compares the two, recomputing the invented categories'
wave-3 scores from the wave-3 export under the same exclusions (incomplete, duplicate participant, failed
attention check, median rating-page time under 3 seconds). Engineering test rows (STRESS prefix) are
dropped first.

Input:  calibration/realism_study/data/raw/realism_export.csv and calibration/wave3/data/raw/calibration_wave3_export.csv
Output: calibration/realism_study/results/realism_results.json (per-category means, the pooled means and
        the published-minus-invented difference with its 95 percent interval); prints the same table.
Manuscript: Web Appendix F (the realism comparison paragraph and Table WA-F1).

Run: python calibration/anchor_analysis.py
"""
import csv, io, json, math, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
# Input resolution: the working repository holds the raw
# *_for_analysis.csv files (raw export minus the engineering-test rows; still carries raw
# participant ids, never deposited). The public deposit holds only the scrubbed copies (ids
# hashed, IP/geolocation blanked, test rows kept for auditability). Take the for_analysis file
# when present, else the scrubbed one; load() strips the STRESS_-prefixed test rows either way
# (a no-op on for_analysis files), so both inputs yield the identical analysis sample.
def _first(*cands):
    return next((p for p in cands if os.path.exists(p)), cands[0])
ANCHOR_CSV = _first(os.path.join(HERE, "realism_study", "data", "raw", "realism_export.csv"),
                    os.path.join(HERE, "realism_study", "data", "raw", "realism_export.csv"))
WAVE3_CSV = _first(os.path.join(HERE, "wave3", "data", "raw", "calibration_wave3_export.csv"),
                   os.path.join(HERE, "wave3", "data", "raw", "calibration_wave3_export.csv"))
OUT_JSON = os.path.join(HERE, "realism_study", "results", "realism_results.json")

PUB_CATS = ["backpacks", "bluetooth_speakers", "earbuds", "hard_drives",
            "restaurants", "televisions", "water_bottles"]
INV_CATS = ["electric_kettles", "robot_vacuums", "standing_desks"]
SPEEDER_FLOOR = 3.0
ATTN_PASS = "Strongly agree"


def load(path):
    rows = list(csv.reader(io.StringIO(open(path, encoding="utf-8-sig").read())))
    header = rows[0]
    out = [dict(zip(header, r)) for r in rows[3:]]
    # Engineering-test rows carry a STRESS_ participant-id prefix; drop them by prefix (the
    # standing rule). No-op on *_for_analysis.csv inputs, which are already stripped.
    return [r for r in out if not (r.get("PROLIFIC_PID") or "").startswith("STRESS")], header


def rating_value(s):
    s = (s or "").strip()
    if not s:
        return None
    return int(s.split(" ")[0].split("-")[0])          # "1 - Not at all realistic" -> 1; "4" -> 4


def keep_rows(rows, timer_cols_of):
    """Apply the fixed exclusions; returns (kept, excluded_reasons)."""
    kept, excl, seen = [], [], set()
    for row in rows:
        pid = (row.get("PROLIFIC_PID") or "").strip()
        reasons = []
        if str(row.get("Finished", "1")).strip() in ("0", "False", "false", ""):
            reasons.append("incomplete")
        if pid in seen:
            reasons.append("duplicate")
        if (row.get("attention_1") or "").strip() != ATTN_PASS:
            reasons.append("attention")
        ps = []
        for c in timer_cols_of(row):
            try:
                ps.append(float(row.get(c, "")))
            except (TypeError, ValueError):
                pass
        if ps and statistics.median(ps) < SPEEDER_FLOOR:
            reasons.append("speeder")
        seen.add(pid)
        (excl if reasons else kept).append((row, reasons))
    return [r for r, _ in kept], [(r.get("PROLIFIC_PID", "")[:6], why) for r, why in excl]


def tstar(df):
    # two-sided 97.5% t quantile (Peizer-Pratt style approximation via normal for df>200; small-df table)
    table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
             9: 2.262, 10: 2.228, 15: 2.131, 20: 2.086, 30: 2.042, 40: 2.021, 60: 2.000,
             80: 1.990, 100: 1.984, 120: 1.980, 200: 1.972}
    if df >= 500:
        return 1.960
    ks = sorted(table)
    lo = max(k for k in ks if k <= df) if df >= 1 else 1
    hi = min((k for k in ks if k >= df), default=200)
    if lo == hi:
        return table[lo]
    w = (df - lo) / (hi - lo)
    return table[lo] * (1 - w) + table[hi] * w


def mstats(vals):
    n = len(vals)
    m = statistics.mean(vals)
    sd = statistics.stdev(vals) if n > 1 else float("nan")
    se = sd / math.sqrt(n)
    t = tstar(n - 1)
    ge5 = sum(1 for v in vals if v >= 5)
    p = ge5 / n
    z = 1.959964
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    hw = (z / den) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return {"n": n, "mean": m, "sd": sd, "ci95": [m - t * se, m + t * se],
            "pct_ge5": 100 * p, "pct_ge5_wilson95": [100 * (ctr - hw), 100 * (ctr + hw)]}


def welch(a, b):
    """Difference mean(a)-mean(b) with Welch 95% CI + t/df."""
    na, nb = len(a), len(b)
    ma, mb = statistics.mean(a), statistics.mean(b)
    va, vb = statistics.variance(a), statistics.variance(b)
    se = math.sqrt(va / na + vb / nb)
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    t = (ma - mb) / se
    ts = tstar(df)
    return {"diff": ma - mb, "se": se, "t": t, "df": df, "ci95": [ma - mb - ts * se, ma - mb + ts * se]}


def main():
    # ---- anchor (published categories) ----
    rows, header = load(ANCHOR_CSV)
    anchor_timers = lambda row: [f"rea_timer_{c}_Page Submit" for c in PUB_CATS
                                 if (row.get(f"rea_timer_{c}_Page Submit") or "").strip()]
    kept, excl = keep_rows(rows, anchor_timers)
    print(f"[anchor] {len(rows)} rows -> {len(kept)} kept; {len(excl)} excluded: "
          f"{[w for _, w in excl]}")

    per_cat, resp_means = {}, []
    for cat in PUB_CATS:
        vals = [rating_value(r.get(f"realism_{cat}")) for r in kept]
        vals = [v for v in vals if v is not None]
        per_cat[cat] = mstats(vals)
    for r in kept:
        vs = [rating_value(r.get(f"realism_{c}")) for c in PUB_CATS]
        vs = [v for v in vs if v is not None]
        if vs:
            resp_means.append(statistics.mean(vs))
    pooled_pub = mstats(resp_means)

    # ---- invented (wave 3), recomputed from raw under the same fixed rules ----
    w3rows, w3header = load(WAVE3_CSV)
    w3_timers = lambda row: [c for c in w3header if c.startswith("timer_") and c.endswith("_Page Submit")
                             and (row.get(c) or "").strip()]
    w3kept, w3excl = keep_rows(w3rows, w3_timers)
    print(f"[wave3] {len(w3rows)} rows -> {len(w3kept)} kept; {len(w3excl)} excluded "
          f"(official run kept 459)")

    inv_cat, inv_resp_means = {}, []
    for cat in INV_CATS:
        vals = [rating_value(r.get(f"realism_{cat}")) for r in w3kept]
        vals = [v for v in vals if v is not None]
        inv_cat[cat] = mstats(vals)
    for r in w3kept:
        vs = [rating_value(r.get(f"realism_{c}")) for c in INV_CATS]
        vs = [v for v in vs if v is not None]
        if vs:
            inv_resp_means.append(statistics.mean(vs))
    pooled_inv = mstats(inv_resp_means)

    # ---- parity: pooled published vs pooled invented (independent samples of respondents) ----
    parity = welch(resp_means, inv_resp_means)

    # per invented category vs the pooled published respondent-mean
    per_inv_vs_pub = {}
    for cat in INV_CATS:
        vals = [rating_value(r.get(f"realism_{cat}")) for r in w3kept]
        vals = [v for v in vals if v is not None]
        per_inv_vs_pub[cat] = welch(resp_means, vals)

    def fmt(s):
        return (f"n={s['n']:>4}  mean={s['mean']:.2f}  SD={s['sd']:.2f}  "
                f"CI[{s['ci95'][0]:.2f},{s['ci95'][1]:.2f}]  %>=5={s['pct_ge5']:.0f}% "
                f"[{s['pct_ge5_wilson95'][0]:.0f},{s['pct_ge5_wilson95'][1]:.0f}]")

    print("\n== PUBLISHED categories (the anchor) ==")
    for cat in PUB_CATS:
        print(f"  {cat:<20} {fmt(per_cat[cat])}")
    print(f"  {'POOLED (resp-mean)':<20} {fmt(pooled_pub)}")
    print("\n== INVENTED categories (wave 3, recomputed from raw) ==")
    for cat in INV_CATS:
        print(f"  {cat:<20} {fmt(inv_cat[cat])}")
    print(f"  {'POOLED (resp-mean)':<20} {fmt(pooled_inv)}")
    print("\n== PARITY (published - invented, pooled respondent means, Welch) ==")
    print(f"  diff={parity['diff']:+.3f}  95% CI [{parity['ci95'][0]:+.3f}, {parity['ci95'][1]:+.3f}]  "
          f"t={parity['t']:.2f} df={parity['df']:.0f}")
    for cat in INV_CATS:
        d = per_inv_vs_pub[cat]
        print(f"  published_pooled - {cat}: {d['diff']:+.3f} [{d['ci95'][0]:+.3f}, {d['ci95'][1]:+.3f}]")

    json.dump({"anchor_rows": len(rows), "anchor_kept": len(kept),
               "anchor_excluded": [w for _, w in excl],
               "published_per_category": per_cat, "published_pooled_respmean": pooled_pub,
               "wave3_rows": len(w3rows), "wave3_kept": len(w3kept),
               "invented_per_category": inv_cat, "invented_pooled_respmean": pooled_inv,
               "parity_welch_pooled": parity,
               "published_pooled_minus_invented_category": per_inv_vs_pub},
              open(OUT_JSON, "w", encoding="utf-8"), indent=1)
    print(f"\n[write] {OUT_JSON}")


if __name__ == "__main__":
    main()
