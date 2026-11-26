# Clustered power: pooled FRQ-vs-BIN, 10 categories, participant random intercepts
(clustered_power.py, 2026-06-12; 600 reps/cell; cluster-robust sandwich on participant.
Critical 1.96 = alpha .05; 2.690 = alpha .05/7 Bonferroni floor.)

| ICC | effect | cluster-robust power (.05 / .05/7) | naive power | max cluster size |
|---|---|---|---|---|
| 0.00 | 4pp | 1.00 / 0.98 | 1.00 | 2 |
| 0.00 | 6pp | 1.00 / 1.00 | 1.00 | 2 |
| 0.05 | 4pp | 1.00 / 0.97 | 1.00 | 2 |
| 0.05 | 6pp | 1.00 / 1.00 | 1.00 | 2 |
| 0.10 | 4pp | 1.00 / 0.95 | 0.99 | 2 |
| 0.10 | 6pp | 1.00 / 1.00 | 1.00 | 2 |
| 0.20 | 4pp | 0.99 / 0.94 | 0.99 | 2 |
| 0.20 | 6pp | 1.00 / 1.00 | 1.00 | 2 |

## Verdict
The pooled per-effect confirmatory test stays at or near power 1.00 even at
ICC 0.20, and cluster-robust power tracks naive power closely, because each
participant contributes at most ONE observation per arm (max cluster size 2)
and the random intercept appears on both arms in different categories, so it
largely differences out of the between-arm contrast. Clustering is real and
the registered analysis is cluster-robust, but it does not threaten the
pooled confirmatory power. (Aggregate/cross-structure analyses, which DO
stack many obs per participant, use the same cluster-robust SEs by default.)
