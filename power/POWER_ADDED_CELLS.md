# Power of the added cells (similarity with two clone placements, price-free arm, extremity control)
(Same two-proportion test as power_sim.py /
RESULTS.md; only per-arm N differs. Baseline p=0.5, conservative max-variance.)

| Test | N/arm | 4pp a.05 | 4pp a.05/7 | 6pp a.05 | 6pp a.05/7 | 8pp a.05/7 |
|---|---|---|---|---|---|---|
| SIM per-placement, pooled (10 cats x 700) | 7000 | 1.00 | 0.98 | 1.00 | 1.00 | 1.00 |
| SIM per-placement, per category (700) | 700 | 0.32 | 0.12 | 0.62 | 0.33 | 0.63 |
| Price-free attraction, pooled (3 cats x 700) | 2100 | 0.74 | 0.46 | 0.97 | 0.89 | 0.99 |
| Price-free attraction, per category (700) | 700 | 0.32 | 0.12 | 0.62 | 0.33 | 0.63 |
| Extremity MOT-vs-EXC, pooled (10 cats x 700) | 7000 | 1.00 | 0.98 | 1.00 | 1.00 | 1.00 |
| Extremity MOT-vs-EXC, per category (700) | 700 | 0.32 | 0.12 | 0.62 | 0.33 | 0.63 |

Reading (plain English):
- SIM per-placement POOLED (7,000/arm) matches the confirmatory pooled level in RESULTS.md
  (~1.00 at a 4-point effect): the two-placement design keeps EACH placement at full pooled
  power, so testing both the clone-budget and clone-premium placements costs nothing in power.
- The PRICE-FREE attraction arm POOLED (2,100/arm) is powered for ~6-point effects (about 0.9
  at 6pp under the Bonferroni floor) and descriptive at 4 points - the same level the tier-3
  cells carry in the tier allocation; appropriate for a robustness arm.
- The EXTREMITY MOT-vs-EXC contrast POOLED (7,000/arm) carries the same ~1.00 power at a
  4-point effect as the other pooled backbone tests (0.98 under the Bonferroni floor); the
  published Sharif extremity effect (~8-18 points) is well above the powered floor. Per
  category and per tier the contrast is descriptive, as for the rest of the backbone.
- Per-category cells (700/arm) are descriptive moderators, exactly as in the main backbone.
Conclusion: the added cells need NO new power method; their power is the existing pooled and
tier-3 levels at the stated N. The allocation FILL for the 9-structure cell set (80 non-
similarity backbone cells x 700, incl. the 10 EXC cells + 10 SIM cells x 1,400 + 12 price-
free cells) uses the same greedy double-diagonal as scriptset_sim.py (structure-count-
agnostic, 180 scripts as of path a Wave 2); the emitted scriptset_180.csv is its exact CSV.
