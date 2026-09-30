"""power_format_interaction.py: power of the human format-by-effect interaction tests at the planned sizes.

For the frequency decoy and the compromise, each shown in words and in pictures, the interaction is the
effect in that format minus the same effect in numbers, on the same categories at the new-values tier. The
four tests form one Holm family. The numbers comparison uses the numeric survey's new-values cells of the same
categories, which hold half as many choices as the format cells, and the compromise loses the participants
who choose the new extreme. Analytic power and a simulation (20,000 runs, seed 20260929).

Output: power/POWER_FORMAT_INTERACTION.md.
Manuscript: Method (the power paragraph) and Web Appendix E.

Run: python power/power_format_interaction.py
"""
import argparse, math, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0.425          # calibrated binary share (band midpoint)
EFFECT = 0.10         # numbers-format effect (frequency decoy truth; compromise uses 0.12)
EXT_SHARE = 0.25
SIDES = {
    # test: (n categories, format choices per cell, numbers choices per cell, treatment keep share)
    "FRQ:words": (4, 700, 350, 1.0),
    "FRQ:pictures": (3, 700, 350, 1.0),
    "SOT:words": (4, 700, 350, 1.0 - EXT_SHARE),
    "SOT:pictures": (2, 700, 350, 1.0 - EXT_SHARE),
}


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(q):
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if norm_cdf(mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def se_interaction(ncat, n_fmt, n_num, keep, var=0.25):
    """SE of the difference of two effect differences; p(1-p) = 0.25 is the conservative variance the
    earlier calculation used."""
    nt_f, nc_f = ncat * n_fmt * keep, ncat * n_fmt
    nt_n, nc_n = ncat * n_num * keep, ncat * n_num
    return math.sqrt(var * (1 / nt_f + 1 / nc_f + 1 / nt_n + 1 / nc_n))


def analytic_power(delta, se, alpha):
    z = norm_ppf(1 - alpha / 2)
    return norm_cdf(delta / se - z) + norm_cdf(-delta / se - z)


def mde(se, alpha, power=0.80):
    return (norm_ppf(1 - alpha / 2) + norm_ppf(power)) * se


def holm(ps, alpha):
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m, out, running, still = len(items), {}, 0.0, True
    for i, (k, p) in enumerate(items):
        adj = max(running, min(1.0, (m - i) * p))
        running = adj
        if adj > alpha:
            still = False
        out[k] = still
    return out


def simulate(reps, delta, planted, seed=20260929):
    """Monte Carlo with the real sharing structure: the four tests share the binary cells of their
    format and the numbers comparison cells. `planted` = the tests that carry the interaction."""
    rng = random.Random(seed)
    hits = {k: 0 for k in SIDES}
    hits_raw = {k: 0 for k in SIDES}
    cats = {"words": 4, "pictures": 3}
    for _ in range(reps):
        # per-format binary and effect cells, per category (numbers cells shared across the two sides).
        num = {}
        for c in range(4):
            num[("BIN", c)] = rng.binomialvariate(350, BASE)
            for eff, e in (("FRQ", EFFECT), ("SOT", 0.12)):
                n = int(round(350 * (1.0 if eff == "FRQ" else 1 - EXT_SHARE)))
                num[(eff, c)] = (rng.binomialvariate(n, BASE + e), n)
        ps = {}
        for fmt, ncat_fmt in cats.items():
            fb = {c: rng.binomialvariate(700, BASE) for c in range(ncat_fmt)}
            for eff, e in (("FRQ", EFFECT), ("SOT", 0.12)):
                key = f"{eff}:{fmt}"
                ncat = SIDES[key][0]
                keep = SIDES[key][3]
                shift = -delta if key in planted else 0.0
                nt = int(round(700 * keep))
                ft = {c: rng.binomialvariate(nt, BASE + e + shift) for c in range(ncat)}
                # pooled shares over the test's categories
                kf_t, nf_t = sum(ft[c] for c in range(ncat)), nt * ncat
                kf_c, nf_c = sum(fb[c] for c in range(ncat)), 700 * ncat
                kn_t = sum(num[(eff, c)][0] for c in range(ncat)); nn_t = num[(eff, 0)][1] * ncat
                kn_c = sum(num[("BIN", c)] for c in range(ncat)); nn_c = 350 * ncat
                pf_t, pf_c, pn_t, pn_c = kf_t / nf_t, kf_c / nf_c, kn_t / nn_t, kn_c / nn_c
                inter = (pf_t - pf_c) - (pn_t - pn_c)
                v = (pf_t * (1 - pf_t) / nf_t + pf_c * (1 - pf_c) / nf_c +
                     pn_t * (1 - pn_t) / nn_t + pn_c * (1 - pn_c) / nn_c)
                z = inter / math.sqrt(v)
                p = 2 * (1 - norm_cdf(abs(z)))
                ps[key] = p
                if p < 0.05:
                    hits_raw[key] += 1
        rej = holm(ps, 0.05)
        for k in SIDES:
            hits[k] += bool(rej[k])
    return {k: hits[k] / reps for k in SIDES}, {k: hits_raw[k] / reps for k in SIDES}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=20000)
    ap.add_argument("--out", default=os.path.join(HERE, "POWER_FORMAT_INTERACTION.md"))
    args = ap.parse_args()
    d6 = 0.06
    lines = [
        "# Power of the format-by-effect interaction at the planned arm sizes",
        "",
        "(Generated by power_format_interaction.py, 2026-09-29. Two-sided tests. Analytic values use the",
        "conservative variance p(1-p) = 0.25; the simulation uses the calibrated 42.5 percent baseline and",
        "shares the binary and numbers cells across tests exactly as the design does. Seed 20260929.)",
        "",
        "## The earlier figure, reproduced, and why it was too high",
        "",
        "| assumption | words side | pictures side |",
        "|---|---|---|",
        f"| every arm at 2,800 (2,100), alpha .05 (the earlier calculation) | "
        f"{analytic_power(d6, math.sqrt(4 * 0.25 / 2800), 0.05):.3f} | {analytic_power(d6, math.sqrt(4 * 0.25 / 2100), 0.05):.3f} |",
        f"| actual arms: format 2,800 (2,100), numbers row 1,400 (1,050), alpha .05 | "
        f"{analytic_power(d6, se_interaction(4, 700, 350, 1.0), 0.05):.3f} | "
        f"{analytic_power(d6, se_interaction(3, 700, 350, 1.0), 0.05):.3f} |",
        "",
        "## Power at a 6-point interaction, actual arms",
        "",
        "| test | SE (points) | alpha .05 per test (analytic) | alpha .05/4, the Holm floor (analytic) "
        "| Holm family, simulated, only this test planted | Holm family, simulated, all four planted "
        "| smallest interaction at 0.80 power, alpha .05 | at 0.80 power, alpha .05/4 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    sims_one = {}
    for key in SIDES:
        sims_one[key] = simulate(args.reps // 4, d6, {key}, seed=20260929 + len(sims_one))[0][key]
    sim_all, sim_all_raw = simulate(args.reps // 4, d6, set(SIDES), seed=31)
    for key, (ncat, nf, nn, keep) in SIDES.items():
        se = se_interaction(ncat, nf, nn, keep)
        lines.append(f"| {key} | {se * 100:.2f} | {analytic_power(d6, se, 0.05):.3f} | "
                     f"{analytic_power(d6, se, 0.05 / 4):.3f} | {sims_one[key]:.3f} | {sim_all[key]:.3f} | "
                     f"{mde(se, 0.05) * 100:.1f} points | {mde(se, 0.05 / 4) * 100:.1f} points |")
    null_rate, _ = simulate(args.reps // 4, 0.0, set(), seed=99)
    fwer_note = max(null_rate.values())
    lines += [
        "",
        f"Under no interaction the largest per-test Holm rejection rate in the simulation is {fwer_note:.3f} "
        "(each test at or below .05; the family-wise rate is bounded by .05).",
        "",
        "## Reading",
        "",
        "At the actual arm sizes and a two-sided .05 level per test, the frequency-decoy interaction has "
        f"power {analytic_power(d6, se_interaction(4, 700, 350, 1.0), 0.05):.2f} on the words side and "
        f"{analytic_power(d6, se_interaction(3, 700, 350, 1.0), 0.05):.2f} on the pictures side at a "
        "6-point interaction, not 0.89 and 0.79: the numbers comparison row is the backbone's tier-2 cell, "
        "which holds 350 choices per category, half of what the earlier calculation assumed. With the four "
        "tests corrected together by Holm, as the Analysis Plan's family rule requires, the power for a "
        "single planted interaction falls further (the Holm-floor column). The compromise tests are lower "
        "still, because the relative share drops the new-extreme choosers and the pictures compromise test "
        "runs on two categories. At 0.80 power the smallest detectable frequency-decoy interaction is "
        f"{mde(se_interaction(4, 700, 350, 1.0), 0.05) * 100:.1f} points (words) and "
        f"{mde(se_interaction(3, 700, 350, 1.0), 0.05) * 100:.1f} points (pictures) at .05 per test, and "
        f"{mde(se_interaction(4, 700, 350, 1.0), 0.05 / 4) * 100:.1f} and "
        f"{mde(se_interaction(3, 700, 350, 1.0), 0.05 / 4) * 100:.1f} points at the Holm floor.",
        "",
    ]
    open(args.out, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
