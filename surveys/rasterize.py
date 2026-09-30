"""rasterize.py: convert the pictures-format SVG images to PNG for the survey host and for vision-model calls.

The same PNG a participant sees is the image a vision model is sent. Tries cairosvg, then the rsvg-convert
or inkscape command-line tools, and otherwise prints the equivalent Playwright call. The deposited PNGs in
surveys/png/ are the files that were served; this script is needed only to rebuild them.

Run: python surveys/rasterize.py --out png
"""
import argparse, glob, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.abspath(os.path.join(HERE, "..", "stimuli", "assets"))
SCALE = 2                                       # 2x for crisp bars on hi-dpi screens

def via_cairosvg(svgs, out):
    import cairosvg                              # raises ImportError if unavailable
    for s in svgs:
        png = os.path.join(out, os.path.basename(s).replace(".svg", ".png"))
        cairosvg.svg2png(url=s, write_to=png, scale=SCALE)
    return True

def via_cli(svgs, out):
    for exe, cmd in (("rsvg-convert", lambda s, p: ["rsvg-convert", "-z", str(SCALE), "-o", p, s]),
                     ("inkscape", lambda s, p: ["inkscape", s, "--export-type=png", f"--export-filename={p}"])):
        if _has(exe):
            for s in svgs:
                p = os.path.join(out, os.path.basename(s).replace(".svg", ".png"))
                subprocess.run(cmd(s, p), check=True)
            return True
    return False

def _has(exe):
    from shutil import which
    return which(exe) is not None

def via_playwright(svgs, out):
    """Deterministic Playwright/Chromium rasteriser (the launch machine's real path, 2026-07-01: this
    Windows box has neither the cairo DLL nor rsvg/inkscape, but Playwright+chromium is installed for
    the survey click-throughs). Renders each SVG at deviceScaleFactor=SCALE and screenshots the <svg>
    element exactly (no viewport margins). Chromium screenshots carry no author/EXIF metadata."""
    from playwright.sync_api import sync_playwright   # raises ImportError if unavailable
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 900, "height": 700}, device_scale_factor=SCALE)
        for s in svgs:
            png = os.path.join(out, os.path.basename(s).replace(".svg", ".png"))
            pg.goto("file:///" + s.replace(os.sep, "/"))
            pg.locator("svg").first.screenshot(path=png)
        b.close()
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "png"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    svgs = sorted(glob.glob(os.path.join(ASSETS, "*.svg")))
    if not svgs:
        print(f"[rasterize] no SVGs in {ASSETS}"); sys.exit(1)
    print(f"[rasterize] {len(svgs)} SVGs -> {args.out} (scale {SCALE}x)")
    try:
        if via_cairosvg(svgs, args.out):
            print(f"[rasterize] done via cairosvg ({len(svgs)} PNGs). Upload {args.out}/* to HOSTBASE.")
            return
    except (ImportError, OSError):
        pass      # cairosvg installed but the cairo DLL missing raises OSError (this Windows box)
    if via_cli(svgs, args.out):
        print(f"[rasterize] done via CLI ({len(svgs)} PNGs). Upload {args.out}/* to HOSTBASE.")
        return
    try:
        if via_playwright(svgs, args.out):
            print(f"[rasterize] done via Playwright/Chromium ({len(svgs)} PNGs). Upload {args.out}/* to HOSTBASE.")
            return
    except ImportError:
        pass
    print("[rasterize] no rasteriser found. Options:\n"
          "  pip install cairosvg   then re-run; OR install rsvg-convert / inkscape; OR Playwright:\n"
          "    from playwright.sync_api import sync_playwright\n"
          "    with sync_playwright() as p:\n"
          "      b=p.chromium.launch(); pg=b.new_page()\n"
          "      for svg in svgs:\n"
          "        pg.goto('file://'+svg); pg.screenshot(path=svg.replace('.svg','.png'), full_page=True)\n"
          "      b.close()")
    sys.exit(2)

if __name__ == "__main__":
    main()
