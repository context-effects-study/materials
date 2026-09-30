"""generate_tier3.py: the tier-3 stimuli, three invented product categories that never appeared in a
context-effects study (standing desks, robot vacuums, electric kettles).

Tier 3 is the top step of the memorization comparison: a model cannot have read a result for these
categories. Each is a price and quality trade-off built by the same geometry engine as the published
categories; the anchor pairs hold the calibrated values from the final calibration lock. Realism was
checked in calibration waves 2 and 3 and in the realism comparison study.

Writes stimuli/fragments/<category>.json and <category>_receipts.md for the three categories.
Manuscript: Method (memorization tiers), Web Appendix B, and Web Appendix F.

Run: python stimuli/generate_tier3.py   (then python stimuli/build_stimuli.py)
"""
import json, os, geometry
from calibration_lock import GEOMETRY_STRENGTHENED

HERE = os.path.dirname(os.path.abspath(__file__))

# Each: id, label, [(attr,unit,direction) x2 - A=quality(higher_better), B=price], anchor A/B = (HF,HD), stem.
CATS = [
    {"id": "standing_desks", "label": "Standing desks",
     "attrs": [("weight_capacity", "lbs", "higher_better"), ("price", "USD", "lower_better")],
     "anchor": {"A": (110, 300), "B": (269.00, 429.99)},   # was (150,300) / (199.99,429.99)
     "stem": "Imagine you are shopping for a standing desk. You are considering the following options:"},
    {"id": "robot_vacuums", "label": "Robot vacuums",
     "attrs": [("suction", "Pa", "higher_better"), ("price", "USD", "lower_better")],
     "anchor": {"A": (2000, 6000), "B": (159.00, 499.99)},  # was (149.99,499.99); locked wave 2
     "stem": "Imagine you are shopping for a robot vacuum. You are considering the following options:"},
    {"id": "electric_kettles", "label": "Electric kettles",
     "attrs": [("power", "watts", "higher_better"), ("price", "USD", "lower_better")],
     "anchor": {"A": (1000, 2400), "B": (31.99, 59.99)},    # was (1500,2400) / (24.99,59.99)
     "stem": "Imagine you are shopping for an electric kettle. You are considering the following options:"},
]

def main():
    made = 0
    for c in CATS:
        attrs = [{"name": n, "unit": u, "direction": d} for (n, u, d) in c["attrs"]]
        anchor = {"A": {"name": c["attrs"][0][0], "hf": c["anchor"]["A"][0], "hd": c["anchor"]["A"][1]},
                  "B": {"name": c["attrs"][1][0], "hf": c["anchor"]["B"][0], "hd": c["anchor"]["B"][1]}}
        stims = geometry.build(anchor, attrs, price_free=False, caps={}, tier=3,
                               cat_id=c["id"], stem=c["stem"],
                               decoy_target=geometry.DECOY_TARGET.get(c["id"], "HD"),
                               **GEOMETRY_STRENGTHENED)
        # EXC never rides in a fragment: build_stimuli.py derives it from the merged MOT cell
        # (exc_from_mot), the authoritative path that also serves the published tier-1 menus.
        stims = [s for s in stims if s["structure"] != "EXC"]
        for s in stims:
            s["source"] = ("INVENTED tier-3 (never-published category; memorization gradient top "
                           "rung); anchor = the final calibration values (2026-07-02); locked "
                           "by build_stimuli.py")
            s["calibration_locked"] = False
        frag = {"category": {"id": c["id"], "label": c["label"], "attributes": attrs,
                             "price_free": False, "published": False, "memorization_tier": 3,
                             "source": "INVENTED for the never-published tier-3 (no context-effects paper uses this category)",
                             "geometry_constraints": []},
                "stimuli": stims}
        json.dump(frag, open(os.path.join(HERE, "fragments", f"{c['id']}.json"), "w",
                             encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False)
        rc = ("# %s - invented tier-3 receipts\n(Anchors locked at the final calibration, July 2, 2026.)\n\n"
              "Never-published category (absent from the context-effects canon). All structures "
              "built by geometry.py to the same geometry as the published categories. The anchor "
              "(HF/HD) carries the TERMINAL calibration values (three waves, 2026-07-02; numeric "
              "authority calibration/FINAL_LOCK_LIST_2026-07-02.json; routing stimuli/calibration_lock.py). "
              "Price x quality (not price-free) to keep the memorization-tier comparison clean.\n"
              % c["label"])
        open(os.path.join(HERE, "fragments", f"{c['id']}_receipts.md"), "w",
             encoding="utf-8", newline="\n").write(rc)
        made += 1
        print(f"  tier-3 {c['id']}: 8 structures, anchor A={c['anchor']['A']} B={c['anchor']['B']}")
    print(f"\nwrote {made} invented tier-3 categories. Run build_stimuli.py + validate_stimuli.py --merged")

if __name__ == "__main__":
    main()
