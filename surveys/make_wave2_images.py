"""make_wave2_images.py: render the wave-2 pictures images of the calibration pre-test.

Re-renders the three pictures pairs whose values changed in wave 2 at the adjusted values in
calibration/wave2/survey/wave2_pairs.json, with the same deterministic renderer as the stimuli
(stimuli/render.py). The fielded images are in calibration/wave2/survey/images/.

Run: python surveys/make_wave2_images.py
"""
import copy, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "stimuli"))
import render                                       # the deterministic wave-1 magnitude-bar renderer

STIMULI = os.path.join(ROOT, "stimuli", "stimuli.json")
KIT = os.path.join(ROOT, "calibration", "wave2", "survey", "wave2_pairs.json")
OUT = os.path.join(HERE, "out", "wave2_assets")
PNG_OUT = os.path.join(OUT, "png")
SCALE = 2                                           # rasterize.py's scale (crisp bars on hi-dpi)


def main():
    S = json.load(open(STIMULI, encoding="utf-8"))
    cats = {c["id"]: c for c in S["categories"]}
    by_id = {r["id"]: r for r in S["stimuli"]}
    kit = json.load(open(KIT, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PNG_OUT, exist_ok=True)

    made = []
    for cat_id, ov in sorted((kit.get("value_overrides") or {}).items()):
        rec = by_id[ov["stimulus"]]
        if "pictures" not in (rec.get("format_variants") or {}):
            continue                                # numbers-only category: no image to re-render
        opts = copy.deepcopy(rec["options"])
        opt = next(o for o in opts if o["code"] == ov["option"])
        cur = opt["attrs"][ov["attribute"]]
        assert abs(float(cur) - float(ov["from"])) < 1e-9, \
            f"{ov['stimulus']} {ov['option']}.{ov['attribute']}: stimuli.json has {cur}, kit says {ov['from']}"
        opt["attrs"][ov["attribute"]] = ov["to"]
        fn, sha = render.option_svg(opts, cats[cat_id]["attributes"], cats[cat_id]["label"],
                                    OUT, f"{ov['stimulus']}_wave2")
        made.append((fn, sha))
        print(f"[wave2_images] {fn}  sha256={sha[:16]}  ({ov['option']}.{ov['attribute']} "
              f"{ov['from']} -> {ov['to']})")

    if not made:
        print("[wave2_images] no pictures-bearing overrides in the kit; nothing to render")
        return

    # rasterize exactly like rasterize.py's Playwright path (this box's proven rasterizer)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 900, "height": 700}, device_scale_factor=SCALE)
        for fn, _ in made:
            svg = os.path.join(OUT, fn)
            png = os.path.join(PNG_OUT, fn.replace(".svg", ".png"))
            pg.goto("file:///" + svg.replace(os.sep, "/"))
            pg.locator("svg").first.screenshot(path=png)
            h = hashlib.sha256(open(png, "rb").read()).hexdigest()
            print(f"[wave2_images] {os.path.basename(png)}  {os.path.getsize(png)//1024}KB  png-sha={h[:16]}")
        b.close()
    print(f"[wave2_images] done: {len(made)} wave-2 images in {PNG_OUT}; host them at the survey's image address "
          "and check that each loads before importing the wave-2 survey.")


if __name__ == "__main__":
    main()
