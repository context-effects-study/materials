"""power_added_cells.py: power of the tests on the cells added to the backbone: the similarity cells with
both clone placements, the price-free cells, and the extremity control (the extremity menu against its
single-option-per-tier control, 700 per condition per category, 7,000 pooled).

It uses the same power functions as power_sim.py; only the number of choices per condition differs.
Baseline share 0.5 (the most conservative, maximum-variance case).

Output: power/POWER_ADDED_CELLS.md.
Manuscript: Method (the power paragraph).

Run: python power/power_added_cells.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import power_sim as ps

P_BASE = 0.5
ROWS = [
    ("SIM per-placement, pooled (10 cats x 700)", 7000),
    ("SIM per-placement, per category (700)", 700),
    ("Price-free attraction, pooled (3 cats x 700)", 2100),
    ("Price-free attraction, per category (700)", 700),
    ("Extremity MOT-vs-EXC, pooled (10 cats x 700)", 7000),     # path a Wave 2
    ("Extremity MOT-vs-EXC, per category (700)", 700),          # path a Wave 2
]

def main():
    out = ["# Power of the added cells (similarity with two clone placements, price-free arm, extremity control)",
           "(Same two-proportion test as power_sim.py /",
           f"RESULTS.md; only per-arm N differs. Baseline p={P_BASE}, conservative max-variance.)", "",
           "| Test | N/arm | 4pp a.05 | 4pp a.05/7 | 6pp a.05 | 6pp a.05/7 | 8pp a.05/7 |",
           "|---|---|---|---|---|---|---|"]
    for label, n in ROWS:
        def pw(d, a): return ps.analytic_power(P_BASE, d, n, a)
        out.append(f"| {label} | {n} | {pw(0.04,0.05):.2f} | {pw(0.04,0.05/7):.2f} | "
                   f"{pw(0.06,0.05):.2f} | {pw(0.06,0.05/7):.2f} | {pw(0.08,0.05/7):.2f} |")
    out += ["",
        "Reading (plain English):",
        "- SIM per-placement POOLED (7,000/arm) matches the confirmatory pooled level in RESULTS.md",
        "  (~1.00 at a 4-point effect): the two-placement design keeps EACH placement at full pooled",
        "  power, so testing both the clone-budget and clone-premium placements costs nothing in power.",
        "- The PRICE-FREE attraction arm POOLED (2,100/arm) is powered for ~6-point effects (about 0.9",
        "  at 6pp under the Bonferroni floor) and descriptive at 4 points - the same level the tier-3",
        "  cells carry in the tier allocation; appropriate for a robustness arm.",
        "- The EXTREMITY MOT-vs-EXC contrast POOLED (7,000/arm) carries the same ~1.00 power at a",
        "  4-point effect as the other pooled backbone tests (0.98 under the Bonferroni floor); the",
        "  published Sharif extremity effect (~8-18 points) is well above the powered floor. Per",
        "  category and per tier the contrast is descriptive, as for the rest of the backbone.",
        "- Per-category cells (700/arm) are descriptive moderators, exactly as in the main backbone.",
        "Conclusion: the added cells need NO new power method; their power is the existing pooled and",
        "tier-3 levels at the stated N. The allocation FILL for the 9-structure cell set (80 non-",
        "similarity backbone cells x 700, incl. the 10 EXC cells + 10 SIM cells x 1,400 + 12 price-",
        "free cells) uses the same greedy double-diagonal as scriptset_sim.py (structure-count-",
        "agnostic, 180 scripts as of path a Wave 2); the emitted scriptset_180.csv is its exact CSV."]
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "POWER_ADDED_CELLS.md"),
         "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("\n".join(out))

if __name__ == "__main__":
    main()
