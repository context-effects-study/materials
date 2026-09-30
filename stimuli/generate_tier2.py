"""generate_tier2.py: the tier-2 stimuli, meaning the published categories with new attribute values.

Tier 2 is the middle step of the memorization comparison: the same product categories as the published
studies, with values a model cannot have read. For each category the anchor pair holds the calibrated
values from the final calibration lock (calibration/FINAL_LOCK_LIST_2026-07-02.json is the numeric
authority), and geometry.build() constructs every structure from it with the strengthened decoy margins.

Writes one file per category: stimuli/fragments/<category>_t2.json.
Manuscript: Method (memorization tiers), Web Appendix B, and Web Appendix F (final values).

Run: python stimuli/generate_tier2.py   (then python stimuli/build_stimuli.py)
"""
import json, os, geometry
from calibration_lock import GEOMETRY_STRENGTHENED

HERE = os.path.dirname(os.path.abspath(__file__))

# Tier-2 anchors: A = (HF, HD) on the strong (higher_better) attribute; B = (HF, HD) on price.
# locked terminal calibration values (was = the pre-calibration hand-picked anchor).
ANCHORS = {
    "hard_drives":       {"A": (2, 6),        "B": (44.99, 119.00)},   # storage TB (was 1/6, 44.99/99.99)
    "bluetooth_speakers":{"A": (4.2, 4.7),    "B": (44.99, 109.00)},   # rating /5 (was 3.8/4.7, 44.99/89.99)
    "earbuds":           {"A": (4000, 18000), "B": (8.99, 32.99)},     # review count (was 2500/18000, 8.99/29.99)
    "restaurants":       {"A": (72, 95),      "B": (22, 60.99)},       # rating /100, entree $ (was 22/58)
    "televisions":       {"A": (78, 96),      "B": (139.99, 459.00)},  # picture quality /100 (was 70/96, 139.99/399.99)
    "water_bottles":     {"A": (16, 48),      "B": (8.99, 24.99)},     # capacity oz (unchanged; locked wave 1)
    "backpacks":         {"A": (25, 50),      "B": (34.99, 61.99)},    # capacity L (was 34.99/59.99)
}

def cap_from_unit(unit):
    u = (unit or "").lower()
    if "out of 5" in u or "/5" in u or "stars" in u:
        return 5.0
    if "0-100" in u or "100-point" in u or "100 point" in u or "0 to 100" in u:
        return 100.0
    return None

def main():
    sj = json.load(open(os.path.join(HERE, "stimuli.json"), encoding="utf-8"))
    cats = {c["id"]: c for c in sj["categories"]}
    made = 0
    for cid, anc in ANCHORS.items():
        if cid not in cats:
            print(f"  !! {cid} not in stimuli.json; skip"); continue
        cat = cats[cid]
        attrs = cat["attributes"]
        higher = [a for a in attrs if a["direction"] == "higher_better"]
        lower = [a for a in attrs if a["direction"] == "lower_better"]
        if not higher or not lower:
            print(f"  !! {cid}: expected one higher_better + one price attribute; skip"); continue
        A_meta, B_meta = higher[0], lower[0]
        caps = {}
        c = cap_from_unit(A_meta.get("unit"))
        if c: caps[A_meta["name"]] = c
        anchor = {"A": {"name": A_meta["name"], "hf": anc["A"][0], "hd": anc["A"][1]},
                  "B": {"name": B_meta["name"], "hf": anc["B"][0], "hd": anc["B"][1]}}
        stem = next((s["stem"] for s in sj["stimuli"]
                     if s["category"] == cid and s["structure"] == "BIN"),
                    "Imagine you are shopping. You are considering the following options:")
        stims = geometry.build(anchor, attrs, price_free=cat.get("price_free", False),
                               caps=caps, tier=2, cat_id=cid, stem=stem,
                               decoy_target=geometry.DECOY_TARGET.get(cid, "HD"),
                               **GEOMETRY_STRENGTHENED)
        # EXC never rides in a fragment: build_stimuli.py derives it from the merged MOT cell
        # (exc_from_mot), the authoritative path that also serves the published tier-1 menus.
        stims = [s for s in stims if s["structure"] != "EXC"]
        for s in stims:
            s["source"] = ("GENERATED tier-2 (new values, same category; geometry.py); anchor = the "
                           "final calibration values (2026-07-02); locked by build_stimuli.py")
            s["calibration_locked"] = False
        frag = {"_tier2_addon_for": cid, "stimuli": stims}
        json.dump(frag, open(os.path.join(HERE, "fragments", f"{cid}_t2.json"), "w",
                             encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False)
        made += 1
        print(f"  tier-2 {cid}: 8 structures (cap={caps or 'none'})")
    print(f"\nwrote {made} tier-2 fragments. Hotels skipped (a design decision). "
          f"Now run: python build_stimuli.py ; python validate_stimuli.py --merged")

if __name__ == "__main__":
    main()
