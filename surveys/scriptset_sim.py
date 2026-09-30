"""scriptset_sim.py: the 180 backbone scripts and the proof that they are balanced.

The backbone crosses ten categories with nine structures (90 cells). Each participant makes seven choices,
never repeating a category or a structure. A double-diagonal construction gives 10 x 9 x 2 = 180 scripts in
which every cell appears equally often, each published cell receives its 350 tier-1 and 350 tier-2
choices, and every cell is the first choice equally often (the first-choice subsample). The script
simulates 9,000 arrivals with 10 percent dropout (seed 99) to show that even presentation keeps the cells
balanced.

Output: surveys/scriptset_180.csv (the scripts generate_qsf.py deals) and surveys/SCRIPTSET_RESULTS.md.
Manuscript: Method ("Human study") and Table 2.

Run: python surveys/scriptset_sim.py
"""
import random
from collections import Counter

N_CAT, N_STR, K = 10, 9, 7
N_PUBLISHED = 7          # category indices 0..6 published, 7..9 invented
N_SCRIPTS = 180          # 10 x 9 x 2 copies (was 160 = 10 x 8 x 2, pre-path-a)
N_PER_SCRIPT = 50        # 9,000 / 180
CELLS = [(c, s) for c in range(N_CAT) for s in range(N_STR)]


def tier_of(cat, i, r):
    if cat >= N_PUBLISHED:
        return 3
    return 1 if (i + r) % 2 == 0 else 2


def construct():
    """180 scripts; each entry is (category, structure, tier)."""
    scripts = []
    for r in (0, 1):
        for a in range(N_CAT):
            for b in range(N_STR):
                sc = []
                for i in range(K):
                    c, s = (a + i) % N_CAT, (b + i) % N_STR
                    sc.append((c, s, tier_of(c, i, r)))
                scripts.append(sc)
    return scripts


def verify(scripts):
    out = []
    appear = Counter()           # (cell) -> script-slots
    tiered = Counter()           # (cell, tier) -> script-slots
    firsts = Counter()           # cell -> times first
    first_tier = Counter()       # (cell, tier) -> times first
    pos_tier = Counter()         # (cell, position, tier) -> count
    rule_violations = 0
    for sc in scripts:
        cats = [c for c, _, _ in sc]
        strs = [s for _, s, _ in sc]
        if len(set(cats)) != K or len(set(strs)) != K:
            rule_violations += 1
        c0, s0, t0 = sc[0]
        firsts[(c0, s0)] += 1
        first_tier[((c0, s0), t0)] += 1
        for pos, (c, s, t) in enumerate(sc, start=1):
            appear[(c, s)] += 1
            tiered[((c, s), t)] += 1
            pos_tier[((c, s), pos, t)] += 1
    out.append(("180 scripts of 7", len(scripts) == N_SCRIPTS and all(len(s) == K for s in scripts), f"{len(scripts)}"))
    out.append(("no repeated category/structure in any script", rule_violations == 0, f"{rule_violations} violations"))
    out.append(("every cell in exactly 14 script-slots", all(appear[c] == 14 for c in CELLS), f"min {min(appear.values())}, max {max(appear.values())}"))
    pub_ok = all(tiered[((c, s), 1)] == 7 and tiered[((c, s), 2)] == 7
                 for (c, s) in CELLS if c < N_PUBLISHED)
    inv_ok = all(tiered[((c, s), 3)] == 14
                 for (c, s) in CELLS if c >= N_PUBLISHED)
    out.append(("published cells: 7 tier-1 + 7 tier-2 slots (=350/350 at even dealing)", pub_ok, "checked all 63"))
    out.append(("invented cells: 14 tier-3 slots (=700)", inv_ok, "checked all 27"))
    out.append(("every cell first in exactly 2 scripts (=100 first-trials)", all(firsts[c] == 2 for c in CELLS), ""))
    ft_ok = all(first_tier[((c, s), 1)] == 1 and first_tier[((c, s), 2)] == 1
                for (c, s) in CELLS if c < N_PUBLISHED)
    out.append(("published first-trials split 1+1 across tiers (=50/50)", ft_ok, ""))
    # Published cells: each (cell, position, tier) once (both tiers visit
    # every position). Invented cells: tier 3 at every position TWICE
    # (once per copy) - same balance, single tier. Both mean every
    # cell-position pair collects equal observations within each tier.
    pt_ok = all(
        v == (1 if cell[0] < N_PUBLISHED else 2)
        for ((cell, pos, t), v) in pos_tier.items()
    )
    out.append(("per-tier position balance (published: each cell-position-tier once; invented: tier-3 twice)", pt_ok, f"{len(pos_tier)} combos"))
    return out


def simulate(scripts, n=9000, dropout=0.10, even=True, seed=99):
    rng = random.Random(seed)
    fill = Counter()
    tier_fill = Counter()
    first_fill = Counter()
    deck = list(range(N_SCRIPTS))
    rng.shuffle(deck)
    for i in range(n):
        s = deck[i % N_SCRIPTS] if even else rng.randrange(N_SCRIPTS)
        sc = scripts[s]
        quit_at = rng.randint(2, K) if rng.random() < dropout else K + 1
        for pos, (c, st, t) in enumerate(sc, start=1):
            if pos >= quit_at:
                break
            fill[(c, st)] += 1
            tier_fill[((c, st), t)] += 1
            if pos == 1:
                first_fill[(c, st)] += 1
    t = [fill[c] for c in CELLS]
    f = [first_fill[c] for c in CELLS]
    pub_t1 = [tier_fill[((c, s), 1)] for (c, s) in CELLS if c < N_PUBLISHED]
    return ((min(t), sum(t) / len(t), max(t)),
            (min(f), sum(f) / len(f), max(f)),
            (min(pub_t1), sum(pub_t1) / len(pub_t1), max(pub_t1)))


def main():
    scripts = construct()
    lines = ["# Script-set v3: 180 scripts with tiers: construction and proof",
             "(Generated by scriptset_sim.py v3, 2026-06-13. v3 grows the backbone from 8",
             "to 9 effect structures for the EXC extremity control (contract v1.1, path a),",
             "so the double-diagonal now emits 10 x 9 x 2 = 180 scripts (was 160). v2",
             "(2026-06-12) had superseded the 80-script version, which could not realize the",
             "350/350 tier split (an error caught in review). Category indices 0-6 = the",
             "published categories, 7-9 = invented; the real-name and structure mappings are",
             "seeded shuffles at QSF time. Each participant still sees 7 of the 9 structures",
             "with no structure repeated, so the no-repeat rule is easier, not harder.)",
             "", "## Deterministic verification", ""]
    allpass = True
    for name, ok, detail in verify(scripts):
        lines.append(f"- {name}: {'PASS' if ok else 'FAIL'} ({detail})")
        allpass &= ok
    lines.append("")
    lines.append("## Simulated dealing (9,000 participants, 50 per script at even dealing)")
    lines.append("")
    lines.append("| Scenario | Cell fill | First-trial fill | Published tier-1 fill |")
    lines.append("|---|---|---|---|")
    for label, even, drop in [("Even dealing, no dropout", True, 0.0),
                              ("Even dealing, 10% abandon", True, 0.10),
                              ("Random dealing, 10% abandon (worst case)", False, 0.10)]:
        t, f, t1 = simulate(scripts, even=even, dropout=drop)
        lines.append(f"| {label} | {t[0]} / {t[1]:.0f} / {t[2]} | {f[0]} / {f[1]:.0f} / {f[2]} | {t1[0]} / {t1[1]:.0f} / {t1[2]} |")
    lines.append("")
    lines.append("## Top-up rule (unchanged in kind, finer in grain)")
    lines.append("")
    lines.append("Monitor completions per script; after the main wave, one top-up wave")
    lines.append("with per-script quotas until every script reaches 50 completions.")
    lines.append("Script-level top-up restores cell-level AND tier-level balance exactly,")
    lines.append("because tiers are properties of script slots. Abandoned partials keep")
    lines.append("their completed first trials.")
    lines.append("")
    lines.append(f"Overall: {'ALL CHECKS PASS' if allpass else 'FAILURES PRESENT'}.")

    with open(__file__.replace("scriptset_sim.py", "scriptset_180.csv"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write("script_id,position,category,structure,tier\n")
        for i, sc in enumerate(scripts, start=1):
            for pos, (c, s, t) in enumerate(sc, start=1):
                fh.write(f"{i},{pos},{c},{s},{t}\n")

    with open(__file__.replace("scriptset_sim.py", "SCRIPTSET_RESULTS.md"),
              "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
