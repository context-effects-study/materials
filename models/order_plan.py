"""order_plan.py: the one rule for the order in which options are shown to a model.

An order is a tuple of option indices; build_prompt() in run.py shows the options in that order at letters
A, B, C and so on. Structures with at most three options use every permutation (2 for BIN, 6 for each
three-option structure). The 12-option extremity menu (MOT) uses 12 fixed stratified orders: each order
assigns the three quality tiers to the three blocks of four positions, cycling through the tier
permutations, and shuffles the options within each tier with a fixed seed (MOT_SEED = 20260613), so the 12
orders are identical on every machine. run.py (the prompts) and build_manifest.py (the counts) both import
this module, so the plan and the prompts cannot disagree.
Manuscript: Method ("Model study", position orders).

Imported by run.py and build_manifest.py; not run on its own.
"""
import itertools
import random

# Fixed seed for the MOT within-tier shuffles. "Generated once, seeded, fixed" (the registered variation plan). Changing this seed changes the registered orders, so it is pinned and must not move
# after pre-registration.
MOT_SEED = 20260613
MOT_N_ORDERS = 12          # the pre-registered count (the registered variation plan, build_manifest ORDERS["MOT"])
MOT_TIER_BLOCK = 4         # options per menu-quality tier (4 High, 4 Middle, 4 Low) -> three blocks of 4


def _mot_stratified_orders(n_opts):
    """The 12 pre-registered stratified orders for a 12-option, 3-equal-tier MOT menu.

    Block layout: option indices 0..3 are the High tier, 4..7 Middle, 8..11 Low (the order MOT options
    are written in stimuli.json). An order is built by (1) choosing which tier occupies each of the
    three position blocks, then (2) shuffling the four options within each tier. Tier-to-block
    assignment cycles through the 6 tier permutations (so every tier visits every block across the set);
    the within-tier shuffles come from a single seeded RNG so the whole set is reproducible byte-for-byte.
    """
    block = MOT_TIER_BLOCK
    n_tiers = n_opts // block                       # 3 for the 12-option menu
    # the option indices that make up each tier block, in stimuli.json order
    tiers = [list(range(t * block, (t + 1) * block)) for t in range(n_tiers)]
    tier_perms = list(itertools.permutations(range(n_tiers)))   # 6 ways to assign tiers to blocks
    rng = random.Random(MOT_SEED)
    orders = []
    for i in range(MOT_N_ORDERS):
        assign = tier_perms[i % len(tier_perms)]    # which tier sits in block 0, block 1, block 2
        order = []
        for tier_idx in assign:
            slot = tiers[tier_idx][:]               # the 4 option indices of this tier
            rng.shuffle(slot)                       # shuffle options WITHIN the tier, seeded
            order.extend(slot)
        orders.append(tuple(order))
    return orders


# ===================================================================================================
# SUPERSEDED 2026-09-29: the tier-block orders above (_mot_stratified_orders) kept every quality level in a
# block of four positions. The participants' twelve-option menus shuffle all twelve positions freely, so the authors set that the models get the same kind of order. The function above is kept
# for the record (and as the selftest mutant that restores the blocks); nothing calls it for a prompt.
#
# THE REGISTERED MENU ORDERS: for EACH twelve-option menu stimulus, twelve
# FULL shuffles of the twelve positions, drawn once from a fixed seed keyed by the stimulus id, no two alike,
# and written into mot_orders.json beside this file (the plan the runner reads). The runner refuses the file
# if it differs from what the seed regenerates, so every build is identical. Still twelve orders per menu, so
# every call count is unchanged.
# ===================================================================================================
import json
import os

MOT_SHUFFLE_SEED = 20260929
MOT_ORDERS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mot_orders.json")


def mot_shuffle_orders(stim_id, n_opts=12, n_orders=MOT_N_ORDERS):
    """Twelve full shuffles of range(n_opts) for one menu stimulus: a private Random seeded by
    '<MOT_SHUFFLE_SEED>|<stimulus id>' (a string seed is hashed the same way on every machine), each shuffle a
    uniform permutation, a repeat redrawn so no two orders are identical."""
    rng = random.Random(f"{MOT_SHUFFLE_SEED}|{stim_id}")
    orders = []
    while len(orders) < n_orders:
        o = tuple(rng.sample(range(n_opts), n_opts))
        if o not in orders:
            orders.append(o)
    return orders


def _find_stimuli():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        d = os.path.dirname(d)
        p = os.path.join(d, "stimuli", "stimuli.json")
        if os.path.exists(p):
            return p
    raise FileNotFoundError("stimuli/stimuli.json not found above order_plan.py")


def build_mot_orders_file(path=MOT_ORDERS_PATH):
    """Write the registered menu orders for every twelve-option stimulus in stimuli.json."""
    stim = json.load(open(_find_stimuli(), encoding="utf-8"))["stimuli"]
    ids = sorted(s["id"] for s in stim if len(s["options"]) > 3)
    doc = {"rule": ("twelve full shuffles of the twelve positions per menu stimulus, drawn once with "
                    "random.Random('<seed>|<stimulus id>'), no two alike"),
           "seed": MOT_SHUFFLE_SEED,
           "orders": {sid: [list(o) for o in mot_shuffle_orders(sid)] for sid in ids}}
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    return doc


_MOT_ORDERS_CACHE = {}


def validate_mot_doc(doc):
    """{stimulus id: [order tuples]} from a mot_orders document, refused (ValueError) unless it was drawn
    with the registered seed and every stimulus's orders equal what the seed regenerates."""
    if doc.get("seed") != MOT_SHUFFLE_SEED:
        raise ValueError("mot_orders.json was drawn with another seed")
    out = {}
    for sid, ords in doc["orders"].items():
        got = [tuple(o) for o in ords]
        if got != mot_shuffle_orders(sid):
            raise ValueError(f"mot_orders.json: the orders of {sid} differ from the registered draw")
        out[sid] = got
    return out


def registered_mot_orders(stim_id):
    """The registered orders of one menu stimulus, read from mot_orders.json and refused unless they equal
    what the seed regenerates (the file can never drift from the rule, nor the rule from the file)."""
    if not _MOT_ORDERS_CACHE:
        if not os.path.exists(MOT_ORDERS_PATH):
            raise FileNotFoundError("mot_orders.json is missing; write it with: python order_plan.py --write")
        doc = json.load(open(MOT_ORDERS_PATH, encoding="utf-8"))
        _MOT_ORDERS_CACHE.update(validate_mot_doc(doc))
    if stim_id not in _MOT_ORDERS_CACHE:
        raise KeyError(f"{stim_id} has no registered menu orders in mot_orders.json")
    return list(_MOT_ORDERS_CACHE[stim_id])


def orders_for(n_opts, stim_id=None):
    """Position orders for a menu of n_opts options, as a list of option-index tuples.

    <=3 options -> all permutations (BIN=2, trinaries=6). A twelve-option menu -> the twelve registered full
    shuffles OF THAT STIMULUS (so stim_id is required). This is the SINGLE source both build_manifest.py
    (counts) and run.py (prompts) use, so the budgeted count and the emitted prompts cannot drift.
    """
    if n_opts <= 3:
        return list(itertools.permutations(range(n_opts)))
    if stim_id is None:
        raise ValueError(f"a {n_opts}-option menu has per-stimulus registered orders: pass the stimulus id")
    return registered_mot_orders(stim_id)


def n_orders_for(n_opts):
    """The COUNT of position orders for a menu of n_opts options (what build_manifest needs).
    Equals len(orders_for(n_opts)) by construction; provided as a cheap, prompt-free helper."""
    if n_opts <= 3:
        f = 1
        for k in range(2, n_opts + 1):
            f *= k
        return f
    return MOT_N_ORDERS


if __name__ == "__main__":
    import sys
    if "--write" in sys.argv:
        doc = build_mot_orders_file()
        print(f"wrote {os.path.basename(MOT_ORDERS_PATH)}: {len(doc['orders'])} menu stimuli x {MOT_N_ORDERS} "
              f"full shuffles, seed {MOT_SHUFFLE_SEED}")
    else:
        print("usage: python order_plan.py --write   (writes the registered menu orders, mot_orders.json)")
