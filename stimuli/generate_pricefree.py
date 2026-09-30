"""generate_pricefree.py: the price-free categories for the attraction robustness test.

To rule out that the attraction effects depend on price acting as a quality signal, the four attraction
structures (BIN, FRQ, RNG, PHT) are re-tested on categories described by two quality attributes and no
price: hard drives, restaurants and televisions. Each is stored as its own category (id <parent>_pf,
price_free = true, linked by price_free_variant_of) so it does not enter the memorization comparison.
Compromise, extremity and upscaling need a single quality ordering and are not part of this test.
These cells were not calibrated.

Writes stimuli/fragments/<category>_pf.json and the matching receipts file.
Manuscript: Method (the price-free robustness test) and Web Appendix B.

Run: python stimuli/generate_pricefree.py   (then python stimuli/build_stimuli.py)
"""
import json, os, geometry

HERE = os.path.dirname(os.path.abspath(__file__))
KEEP = {"BIN", "FRQ", "RNG", "PHT"}   # attraction family only

# Each: id, label, parent, two QUALITY attributes (A = HD-strong, B = HF-strong), anchor, caps, stem.
CATS = [
    # 2nd quality attributes chosen with HEADROOM (both 0-100-style, not floor-bound) so a worse
    # decoy stays physically plausible (the geometry check caught refresh_rate crashing to 18 Hz).
    {"id": "televisions_pf", "label": "Televisions (price-free: picture vs sound)",
     "parent": "televisions",
     "attrs": [("picture_quality", "0-100 expert scale", "higher_better"),
               ("sound_quality", "0-100 expert scale", "higher_better")],
     "anchor": {"A": (65, 95), "B": (95, 78)}, "caps": {"picture_quality": 100.0, "sound_quality": 100.0},
     "stem": "Imagine you are shopping for a 40-inch television. Two experts rate picture quality and "
             "sound quality, each on a 0-100 scale (higher is better). You are considering the "
             "following options. Which would you choose?"},
    {"id": "restaurants_pf", "label": "Restaurants (price-free: food vs service)",
     "parent": "restaurants",
     "attrs": [("food_rating", "0-100", "higher_better"), ("service_rating", "0-100", "higher_better")],
     "anchor": {"A": (72, 95), "B": (93, 76)}, "caps": {"food_rating": 100.0, "service_rating": 100.0},
     "stem": "Imagine you are choosing a restaurant. Each is rated 0-100 on food and, separately, "
             "0-100 on service. You are considering the following options. Which would you choose?"},
    {"id": "hard_drives_pf", "label": "External hard drives (price-free: capacity vs speed)",
     "parent": "hard_drives",
     "attrs": [("capacity", "TB", "higher_better"), ("read_speed", "MB/s", "higher_better")],
     "anchor": {"A": (2, 8), "B": (3000, 1200)}, "caps": {},
     "stem": "Imagine you are shopping for an external hard drive. Each lists its capacity (TB) and "
             "its read speed (MB/s, higher is faster). You are considering the following options. "
             "Which would you choose?"},
]

def main():
    made = 0
    for c in CATS:
        attrs = [{"name": n, "unit": u, "direction": d} for (n, u, d) in c["attrs"]]
        anchor = {"A": {"name": c["attrs"][0][0], "hf": c["anchor"]["A"][0], "hd": c["anchor"]["A"][1]},
                  "B": {"name": c["attrs"][1][0], "hf": c["anchor"]["B"][0], "hd": c["anchor"]["B"][1]}}
        allstims = geometry.build(anchor, attrs, price_free=True, caps=c["caps"], tier=2,
                                  cat_id=c["id"], stem=c["stem"], decoy_target="HD")
        stims = [s for s in allstims if s["structure"] in KEEP]
        for s in stims:
            s["source"] = ("PRICE-FREE robustness arm (AE 8a): two quality attributes, no price; "
                           "attraction family only; NOT calibration_locked")
            s["calibration_locked"] = False
        frag = {"category": {"id": c["id"], "label": c["label"], "attributes": attrs,
                             "price_free": True, "published": True, "memorization_tier": 2,
                             "price_free_variant_of": c["parent"],
                             "source": f"Price-free variant of {c['parent']} (AE 8a robustness arm)",
                             "geometry_constraints": []},
                "stimuli": stims}
        json.dump(frag, open(os.path.join(HERE, "fragments", f"{c['id']}.json"), "w",
                             encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False)
        rc = (f"# {c['label']} - price-free robustness arm receipts\n\n"
              f"Price-free variant of {c['parent']}: two QUALITY attributes "
              f"({c['attrs'][0][0]} x {c['attrs'][1][0]}), NO price, so the attraction effects "
              f"(BIN/FRQ/RNG/PHT) can be tested without price acting as a quality signal (AE 8a / "
              f"Gui-Toubia unblinding). Compromise/extremity/upscaling are excluded (they need a single "
              f"quality ordering). Values realistic; locked at the final calibration.\n")
        open(os.path.join(HERE, "fragments", f"{c['id']}_receipts.md"), "w",
             encoding="utf-8", newline="\n").write(rc)
        made += 1
        print(f"  price-free {c['id']}: {len(stims)} structures {sorted(s['structure'] for s in stims)}")
    print(f"\nwrote {made} price-free variant categories (attraction family only). "
          f"Run build_stimuli.py + validate_stimuli.py")

if __name__ == "__main__":
    main()
