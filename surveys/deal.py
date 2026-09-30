"""deal.py: the balanced participant-script deals for the similarity, format and price-free surveys.

A script is one participant's ordered list of choices. Each deal is built greedily with a fixed seed
("sim-2026", "fmt-2026", "pf-2026") and is balanced by construction where the arithmetic allows: every
cell is filled evenly, no participant sees a product category twice, tiers are valid, and the two
clone placements of the similarity structure are balanced. The verify functions prove each property.
generate_survey.py and surveys/assign_worker/build_worker_data.py read these deals.

Output: surveys/DEAL_RESULTS.md (the balance proofs).
Manuscript: Method ("Human study").

Run: python surveys/deal.py
"""
import collections, json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
# Layout: root = the nearest ancestor holding stimuli/
# (working repository: two levels up from surveys/; public deposit: one level up from surveys/).
def _find_root(start):
    d = start
    for _ in range(4):
        d = os.path.dirname(d)
        if os.path.isdir(os.path.join(d, "stimuli")):
            return d
    return os.path.abspath(os.path.join(start, "..", ".."))
ROOT = _find_root(HERE)
STIM = os.path.join(ROOT, "stimuli", "stimuli.json")

def load():
    S = json.load(open(STIM, encoding="utf-8"))
    cats = {c["id"]: c for c in S["categories"]}
    by_cell = {(r["category"], r["structure"], r["memorization_tier"]): r for r in S["stimuli"]}
    bb = lambda v: v.get("price_free_variant_of") is None and not v.get("price_free")
    pub = sorted(c for c, v in cats.items() if v.get("published") and bb(v))
    inv = sorted(c for c, v in cats.items() if not v.get("published") and bb(v))
    pf = sorted(c for c, v in cats.items() if v.get("price_free") or v.get("price_free_variant_of"))
    return cats, by_cell, pub, inv, pf

# ---- Survey 4: price-free robustness arm (AE 8a) -------------------------------------------------
# 3 price-free categories x 4 structures (BIN/FRQ/RNG/PHT), all tier 2 = 12 cells x 700 = 8,400 choices.
# Each participant sees all 3 categories (one trial each, no-repeat-category binds at 3); within each
# category the structure is dealt least-filled-first. 2,800 participants x 3 = 8,400; 2,800/4 = 700 per
# (category, structure) EXACTLY, since each category appears once per participant and its 4 structures
# are dealt round-robin by least fill.
def deal_pricefree(pf, n=2800, seed="pf-2026"):
    rng = random.Random(seed)
    structs = ["BIN", "FRQ", "RNG", "PHT"]
    fill = collections.Counter()
    scripts = []
    for _ in range(n):
        cells = []
        for cat in rng.sample(pf, len(pf)):                      # all 3 categories, random order
            s = min(structs, key=lambda s: (fill[(cat, s)], rng.random()))   # least-filled structure
            fill[(cat, s)] += 1
            cells.append({"category": cat, "structure": s, "tier": 2, "format": "numbers", "sim_placement": "NA"})
        scripts.append(cells)
    return scripts, fill

# ---- Survey 2: similarity two-placement top-up --------------------------------------------------
# SIM x 10 categories x 2 placements (clone_HF / clone_HD). 1,000 participants x 7 SIM trials = 7,000.
# Each participant sees 7 distinct categories (of 10), dealt least-appeared-first so each category appears
# 1,000*7/10 = 700 times; within a category, (placement, tier) is dealt least-filled. Published categories
# carry tiers {1,2}, invented {3}. So per (cat, placement): 350; published split 175 tier-1 + 175 tier-2;
# invented 350 tier-3. Combined with Survey 1's 350/placement -> 700/placement, the registered target.
def deal_sim_topup(pub, inv, n=1000, k=7, seed="sim-2026"):
    rng = random.Random(seed)
    allcats = pub + inv
    pubset = set(pub)
    appear = collections.Counter()
    fill = collections.Counter()                                # (cat, placement, tier)
    scripts = []
    for _ in range(n):
        cats_k = sorted(allcats, key=lambda c: (appear[c], rng.random()))[:k]   # 7 least-appeared, distinct
        rng.shuffle(cats_k)
        cells = []
        for cat in cats_k:
            appear[cat] += 1
            tiers = [1, 2] if cat in pubset else [3]
            cand = [(pl, ti) for pl in ("clone_HF", "clone_HD") for ti in tiers]
            pl, ti = min(cand, key=lambda x: (fill[(cat, x[0], x[1])], rng.random()))
            fill[(cat, pl, ti)] += 1
            cells.append({"category": cat, "structure": "SIM", "tier": ti, "format": "numbers",
                          "sim_placement": pl})
        scripts.append(cells)
    return scripts, fill, appear

# ---- Survey 3: format module (words / pictures) -------------------------------------------------
# WORDS: 4 categories x 3 structures (BIN/FRQ/SOT), tier-2 = 12 cells; 2,800 participants x 3 trials =
# 8,400 -> 700 per cell; each participant sees 3 distinct categories of 4, least-appeared-first (each
# category 2,800*3/4 = 2,100 appearances), structure least-filled per category (700 per cell).
# PICTURES (final calibration lock, 2026-07-02): the hard-drives pictures cells EXITED the design at the terminal
# calibration (the registered hard-limit / stimulus-defect contingency), so the pictures arm deals
# 3 categories x 3 structures = 9 cells; 2,100 participants x 3 trials = 6,300 -> 700 per cell; each
# pictures participant sees ALL THREE remaining categories (the no-repeat rule binds at 3). The two
# arms stay SEPARATE surveys (different participants), dealt separately.
FMT_CATS = ["bluetooth_speakers", "water_bottles", "hard_drives", "televisions"]
FMT_CATS_BY_FMT = {
    "words": FMT_CATS,
    "pictures": ["bluetooth_speakers", "water_bottles", "televisions"],   # final calibration lock: hard_drives exited
}
FMT_N_BY_FMT = {"words": 2800, "pictures": 2100}
FMT_STRUCTS = ["BIN", "FRQ", "SOT"]

def deal_format(fmt, n=None, seed="fmt-2026"):
    cats_fmt = FMT_CATS_BY_FMT[fmt]
    n = FMT_N_BY_FMT[fmt] if n is None else n
    rng = random.Random(seed + "-" + fmt)
    appear = collections.Counter()
    fill = collections.Counter()
    scripts = []
    for _ in range(n):
        cats3 = sorted(cats_fmt, key=lambda c: (appear[c], rng.random()))[:3]  # 3 distinct, least-appeared
        rng.shuffle(cats3)
        cells = []
        for cat in cats3:
            appear[cat] += 1
            s = min(FMT_STRUCTS, key=lambda s: (fill[(cat, s)], rng.random()))
            fill[(cat, s)] += 1
            cells.append({"category": cat, "structure": s, "tier": 2, "format": fmt, "sim_placement": "NA"})
        scripts.append(cells)
    return scripts, fill, appear

# ---- verification (the deals must PROVE balance, not assert it) ----------------------------------
def _norepeat(scripts, field):
    return all(len({c[field] for c in s}) == len(s) for s in scripts)

def verify_pricefree(scripts, fill):
    out, ok = [], True
    vals = list(fill.values())
    even = len(fill) == 12 and min(vals) == max(vals) == 700
    ok &= even; out.append(("12 cells each exactly 700", even, f"min {min(vals)}/max {max(vals)}, {len(fill)} cells"))
    nrc = _norepeat(scripts, "category"); ok &= nrc
    out.append(("no repeated category within a participant (all 3 distinct)", nrc, ""))
    three = all(len(s) == 3 for s in scripts); ok &= three
    out.append(("every participant has 3 trials", three, f"{len(scripts)} participants"))
    t2 = all(c["tier"] == 2 for s in scripts for c in s); ok &= t2
    out.append(("all price-free cells tier-2 (HD-target arm)", t2, ""))
    return ok, out

def verify_sim(scripts, fill, appear, pub):
    out, ok = [], True
    pubset = set(pub)
    nrc = _norepeat(scripts, "category"); ok &= nrc
    out.append(("no repeated category within a participant (7 distinct)", nrc, ""))
    seven = all(len(s) == 7 for s in scripts); ok &= seven
    out.append(("every participant has 7 SIM trials", seven, f"{len(scripts)} participants"))
    app = list(appear.values())
    app_even = max(app) - min(app) <= 2 and len(appear) == 10
    ok &= app_even; out.append(("each category appears ~700 times (10 cats)", app_even, f"min {min(app)}/max {max(app)}"))
    pub_cells = [v for (c, pl, ti), v in fill.items() if c in pubset]
    inv_cells = [v for (c, pl, ti), v in fill.items() if c not in pubset]
    pub_ok = pub_cells and max(pub_cells) - min(pub_cells) <= 8
    inv_ok = inv_cells and max(inv_cells) - min(inv_cells) <= 8
    ok &= pub_ok and inv_ok
    out.append(("published (cat,placement,tier) cells ~175 each", pub_ok,
                f"min {min(pub_cells)}/max {max(pub_cells)} over {len(pub_cells)} cells"))
    out.append(("invented (cat,placement,tier=3) cells ~350 each", inv_ok,
                f"min {min(inv_cells)}/max {max(inv_cells)} over {len(inv_cells)} cells"))
    # per (cat, placement) totals ~350
    perpl = collections.Counter()
    for (c, pl, ti), v in fill.items():
        perpl[(c, pl)] += v
    pp = list(perpl.values()); pp_ok = max(pp) - min(pp) <= 8 and len(perpl) == 20
    ok &= pp_ok; out.append(("each (category, placement) ~350 (20 cells)", pp_ok, f"min {min(pp)}/max {max(pp)}"))
    return ok, out

def verify_format(scripts, fill, appear, fmt):
    out, ok = [], True
    cats_fmt = FMT_CATS_BY_FMT[fmt]
    n_cats = len(cats_fmt)
    n_cells = n_cats * len(FMT_STRUCTS)
    nrc = _norepeat(scripts, "category"); ok &= nrc
    out.append((f"no repeated category within a participant (3 distinct of {n_cats})", nrc, ""))
    three = all(len(s) == 3 for s in scripts); ok &= three
    out.append(("every participant has 3 trials", three, f"{len(scripts)} participants"))
    fmt_ok = all(c["format"] == fmt for s in scripts for c in s); ok &= fmt_ok
    out.append((f"all cells format={fmt}", fmt_ok, ""))
    incat = all(c["category"] in cats_fmt for s in scripts for c in s); ok &= incat
    out.append((f"all categories in the {fmt} roster {cats_fmt}", incat, ""))
    vals = list(fill.values()); even = len(fill) == n_cells and max(vals) - min(vals) <= 8
    ok &= even; out.append((f"{n_cells} cells ~700 each ({n_cats} cat x 3 struct)", even,
                            f"min {min(vals)}/max {max(vals)}, {len(fill)} cells"))
    app = list(appear.values()); app_ok = len(appear) == n_cats and max(app) - min(app) <= 6
    ok &= app_ok; out.append((f"each of {n_cats} categories ~2,100 appearances", app_ok,
                              f"min {min(app)}/max {max(app)}"))
    return ok, out

def main():
    cats, by_cell, pub, inv, pf = load()
    s4, f4 = deal_pricefree(pf)
    s2, f2, ap2 = deal_sim_topup(pub, inv)
    sw, fw, aw = deal_format("words")
    sp, fp, ap = deal_format("pictures")
    ok4, o4 = verify_pricefree(s4, f4)
    ok2, o2 = verify_sim(s2, f2, ap2, pub)
    okw, ow = verify_format(sw, fw, aw, "words")
    okp, op = verify_format(sp, fp, ap, "pictures")
    lines = ["# Survey 2, 3, 4 deals - construction and balance proof",
             "(deal.py, 2026-06-13. Greedy balanced deals for the non-backbone surveys; the backbone keeps",
             "its proven 180-script set. Consumed by generate_survey.py.)", "",
             "## Survey 4 - price-free arm (3 cats x 4 structures, tier-2, 2,800 participants x 3)"]
    for n, k, d in o4:
        lines.append(f"- {n}: {'PASS' if k else 'FAIL'} ({d})")
    lines += ["", "## Survey 2 - SIM two-placement top-up (10 cats x 2 placements, 1,000 participants x 7)"]
    for n, k, d in o2:
        lines.append(f"- {n}: {'PASS' if k else 'FAIL'} ({d})")
    lines += ["", "## Survey 3 (words) - format module (4 cats x 3 structures, tier-2, 2,800 participants x 3)"]
    for n, k, d in ow:
        lines.append(f"- {n}: {'PASS' if k else 'FAIL'} ({d})")
    lines += ["", "## Survey 3 (pictures) - separate participants; final roster (3 categories after the "
                  "hard-drives pictures exit), 2,100 participants x 3"]
    for n, k, d in op:
        lines.append(f"- {n}: {'PASS' if k else 'FAIL'} ({d})")
    allok = ok4 and ok2 and okw and okp
    lines += ["", f"## OVERALL: {'ALL DEALS BALANCED' if allok else 'IMBALANCE - FIX'}"]
    open(os.path.join(HERE, "DEAL_RESULTS.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return allok

if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
