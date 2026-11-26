"""make_wave3_images.py: render the wave-3 pictures images of the calibration pre-test.

Re-renders all four pictures pairs through the enriched renderer (model names, qualifiers under the bars,
and a legend naming each attribute) at the wave-3 values in calibration/wave3/survey/wave3_pairs.json.
The fielded images are in calibration/wave3/survey/images/.

Run: python surveys/make_wave3_images.py
"""
import copy, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "stimuli"))
import render                                       # option_svg_enriched: the wave-3 enriched renderer
import enrich as EN                                 # content-contract validation

STIMULI = os.path.join(ROOT, "stimuli", "stimuli.json")
KIT = os.path.join(ROOT, "calibration", "wave3", "survey", "wave3_pairs.json")
OUT = os.path.join(HERE, "out", "wave3_assets")
PNG_OUT = os.path.join(OUT, "png")
SCALE = 2                                           # rasterize.py's scale (crisp bars on hi-dpi)


def main():
    S = json.load(open(STIMULI, encoding="utf-8"))
    cats = {c["id"]: c for c in S["categories"]}
    by_id = {r["id"]: r for r in S["stimuli"]}
    kit = json.load(open(KIT, encoding="utf-8"))
    enrichment = {k: v for k, v in kit["enrichment"].items() if k != "note"}
    EN.validate_enrichment(enrichment, cats)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PNG_OUT, exist_ok=True)

    made = []
    for arm_id, ovs in sorted(kit["arm_value_overrides"].items()):
        if not arm_id.startswith("pictures::"):
            continue
        sid = arm_id.split("::")[1]
        rec = by_id[sid]
        opts = copy.deepcopy(rec["options"])
        for ov in ovs:                              # the PICTURES arm's own effective values (per-arm)
            opt = next(o for o in opts if o["code"] == ov["option"])
            cur = opt["attrs"][ov["attribute"]]
            assert abs(float(cur) - float(ov["from"])) < 1e-9, \
                f"{sid} {ov['option']}.{ov['attribute']}: stimuli.json has {cur}, kit says {ov['from']}"
            opt["attrs"][ov["attribute"]] = ov["to"]
        cat = rec["category"]
        fn, sha = render.option_svg_enriched(opts, cats[cat]["attributes"], cats[cat]["label"],
                                             OUT, f"{sid}_wave3", enrichment[cat])
        made.append((fn, sha))
        shown = {o["code"]: o["attrs"] for o in opts}
        print(f"[wave3_images] {fn}  sha256={sha[:16]}  values={shown}")

    # rasterize exactly like rasterize.py's Playwright path (this box's proven rasterizer)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1000, "height": 700}, device_scale_factor=SCALE)
        for fn, _ in made:
            svg = os.path.join(OUT, fn)
            png = os.path.join(PNG_OUT, fn.replace(".svg", ".png"))
            pg.goto("file:///" + svg.replace(os.sep, "/"))
            pg.locator("svg").first.screenshot(path=png)
            h = hashlib.sha256(open(png, "rb").read()).hexdigest()
            print(f"[wave3_images] {os.path.basename(png)}  {os.path.getsize(png)//1024}KB  png-sha={h[:16]}")
        b.close()
    print(f"[wave3_images] done: {len(made)} wave-3 images in {PNG_OUT}; host them at the survey's image address "
          "and check that each loads before importing the wave-3 survey.")


if __name__ == "__main__":
    main()
