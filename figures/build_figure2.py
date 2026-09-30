"""build_figure2.py: draws Figure 2, one frequency-decoy choice set (Bluetooth speakers, new values) in the three
registered formats as participants see it.

Panels A (numbers) and B (words) are the survey's own option cards, written by the survey generators'
functions; panel C is the registered picture file that participants and vision models receive, checked by
its hash. The survey joins a value and its description with an em dash; the figure reproduces that separator
inside the cards and nowhere else. The script stops on any printed value, name or description that differs
from stimuli.json, any card line that differs from the survey's text, text under 6 point or outside its box,
or a figure larger than 6.5 by 5.677 inches.

Output: figures/figure2.png (3,120 pixels wide, 480 dpi).
Needs: playwright with Chromium and Pillow (see requirements.txt).

Run: python figures/build_figure2.py
"""
import base64
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figure2.png")
sys.path.insert(0, HERE)
import build_stimulus_figures as BSF   # noqa: E402  (loads the survey writers, the runner and the readers)

STIM_ID = "FRQ_bluetooth_speakers_t2"
SEP = " — "                 # the survey's own separator (stimuli/enrich.py option_numbers_html)
W_PX, MAX_H_PX, MIN_FONT_PX = 624, 545.0, 8.0     # 6.5 in; 5.677 in; 6 pt at 1 px = 0.75 pt
PIC_PX = 576                     # 6.0 in: the picture's 8.5 px text prints at exactly 6.0 pt
DPR = 5

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#fff}
body{font-family:Arial,Helvetica,sans-serif;color:#1c1c1c}
.fig{width:624px;padding:3px}
.stem{font-size:9px;line-height:1.3}
.stem .lbl{font-weight:bold}
.cols{display:flex;gap:10px;margin-top:2px}
.panel{flex:1 1 0;min-width:0}
.sect{font-size:10px;font-weight:bold;letter-spacing:.04em;border-bottom:1px solid #8c8c8c;padding-bottom:1px}
.opt{position:relative;margin-top:7px}
.tab{position:absolute;left:6px;top:-5px;z-index:1;font-size:8px;line-height:8px;font-weight:bold;text-transform:uppercase;letter-spacing:.02em;padding:0 3px;border:1px solid #1c1c1c;border-radius:2px;background:#fff;color:#1c1c1c;white-space:nowrap}
.tab.target{background:#1c1c1c;color:#fff}
.tab.added{background:#dcdcdc;border-color:#6a6a6a}
.card{border:1px solid #bfc6cd;border-radius:5px;background:#fff;padding:5px 6px 1px}
.cfx-attr{font-size:9px;line-height:1.2}
.picblock{margin-top:5px}
.pic{display:block;width:576px;margin:3px 0 0 0;border:1px solid #d5d9dd;border-radius:4px}
"""


def refuse(msg):
    print("REFUSED: " + msg)
    sys.exit(1)


def text_lines(fragment):
    """The visible lines of a survey card fragment (one per cfx-attr div), tags removed."""
    return [html.unescape(re.sub(r"<[^>]+>", "", m)) for m in re.findall(r"<div class='cfx-attr'>(.*?)</div>", fragment)]


def main():
    BSF.DATA, BSF.CATS = BSF.load()
    focal = BSF.focal_words(BSF.DATA, BSF.CATS)
    sets = {d["fmt"]: d for d in BSF.build_sets(BSF.DATA, BSF.CATS) if d["stim"]["id"] == STIM_ID}
    if set(sets) != {"numbers", "words", "pictures"}:
        refuse(f"{STIM_ID} does not have the three formats: {sorted(sets)}")
    for d in sets.values():
        if BSF.check_geometry(d):
            refuse("; ".join(BSF.check_geometry(d)))

    def cards(d):
        out = []
        for i, o in enumerate(d["options"]):
            if d["fmt"] == "numbers":
                raw = BSF.GQ.render_option_html(d["stim"], o, d["cat"])
            else:
                raw = BSF.GS.render_option_words(d["words"][o["code"]], d["cat"], d["stim"], o)
            label, kind = BSF.role_of(d, o, focal)
            out.append(f"<div class='opt' data-code='{o['code']}' data-idx='{i}'><div class='tab {kind}'>"
                       f"{html.escape(label)}</div><div class='card'>{raw}</div></div>")
        return "".join(out)

    pic = sets["pictures"]
    payload = BSF.picture_payload(pic)           # the registered PNG, hash-checked; SVG, bars and names checked
    svg = open(os.path.join(BSF.ASSET_DIR, pic["image"]["image_ref"]), encoding="utf-8").read()
    min_pic_pt = min(float(x) for x in re.findall(r'font-size="([0-9.]+)"', svg)) * PIC_PX / payload["svg_w"] * 0.75
    if min_pic_pt < 6.0 - 1e-9:
        refuse(f"the picture's smallest text would print at {min_pic_pt:.2f} pt")
    stem = sets["numbers"]["stim"]["stem"]
    page = (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='fig'>"
            f"<div class='stem'><span class='lbl'>Question above each set:</span> “{html.escape(stem)}”</div>"
            f"<div class='cols'><section class='panel' data-set='{sets['numbers']['key']}'>"
            f"<div class='sect'>A. NUMBERS</div>{cards(sets['numbers'])}</section>"
            f"<section class='panel' data-set='{sets['words']['key']}'>"
            f"<div class='sect'>B. WORDS</div>{cards(sets['words'])}</section></div>"
            f"<section class='picblock' data-set='{pic['key']}'><div class='sect'>C. PICTURES</div>"
            f"<img class='pic' alt='' src='data:image/png;base64,{payload['b64']}'></section></div></body></html>")
    if "–" in page:
        refuse("an en dash in the page")

    from playwright.sync_api import sync_playwright
    from PIL import Image
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        pg = br.new_page(viewport={"width": W_PX + 40, "height": 900}, device_scale_factor=DPR)
        pg.set_content(page)
        pg.wait_for_load_state("load")
        rec = pg.evaluate(BSF.EXTRACT_JS, ".fig")
        dash_nodes = pg.evaluate("""() => { const out = [], w = document.createTreeWalker(document.querySelector('.fig'), NodeFilter.SHOW_TEXT);
            while (w.nextNode()) { const n = w.currentNode; if (n.textContent.includes('\\u2014'))
              out.push([n.parentElement.className, n.textContent]); } return out; }""")
        errs = []
        if abs(rec["width"] - W_PX) > 0.5:
            errs.append(f"width {rec['width']:.1f} px, not {W_PX}")
        if rec["height"] > MAX_H_PX + 0.01:
            errs.append(f"height {rec['height']:.1f} px = {rec['height'] / 96:.3f} in, over {MAX_H_PX / 96:.3f} in")
        small = [f for f in rec["fonts"] if f[0] < MIN_FONT_PX - 1e-6]
        if small:
            errs.append(f"text under 6 pt: {small[:3]}")
        if rec["outside"] or rec["overflow"]:
            errs.append(f"text outside its box {rec['outside'][:3]} or overflow {rec['overflow'][:3]}")
        for w_img, _ in rec["imgs"]:
            if abs(w_img - PIC_PX) > 0.5:
                errs.append(f"picture drawn {w_img:.1f} px wide, not {PIC_PX}")
        # every em dash is the survey's separator inside a card line, and nowhere else
        for cls, t in dash_nodes:
            if cls != "cfx-attr" or t.count("—") != 1 or SEP not in t:
                errs.append(f"an em dash outside the survey's separator: {cls!r} {t!r}")
        by_set = {}
        for o in rec["opts"]:
            by_set.setdefault(o["set"], []).append(o)
        n_sep = 0
        for fmt in ("numbers", "words", "pictures"):
            d = sets[fmt]
            got = by_set.get(d["key"], [])
            if fmt == "pictures":            # the picture carries its options; build_stimulus_figures checked it
                continue
            if sorted(o["idx"] for o in got) != list(range(len(d["options"]))):
                errs.append(f"{fmt}: {len(got)} options printed for {len(d['options'])}")
                continue
            for o in got:
                opt = d["options"][o["idx"]]
                if opt["code"] != o["code"]:
                    errs.append(f"{fmt}: option {o['idx']} printed as {o['code']}")
                    continue
                if fmt == "pictures":
                    if o["lines"] != [f"Option {BSF.LETTERS[o['idx']]}"]:
                        errs.append(f"pictures: button {o['idx']} reads {o['lines']}")
                    continue
                entry = BSF.enrichment_entry(d, opt)
                want = [entry["name"]] + [BSF.value_text(d, opt, a) + SEP + entry["qualifiers"][a["name"]]
                                          for a in d["cat"]["attributes"]]
                raw = (BSF.GQ.render_option_html(d["stim"], opt, d["cat"]) if fmt == "numbers" else
                       BSF.GS.render_option_words(d["words"][opt["code"]], d["cat"], d["stim"], opt))
                if o["lines"] != want or text_lines(raw) != want:
                    errs.append(f"{fmt} {opt['code']}: printed {o['lines']!r}, survey writes {text_lines(raw)!r}, "
                                f"expected {want!r}")
                for line, a in zip(o["lines"][1:], d["cat"]["attributes"]):
                    n_sep += line.count(SEP)
                    vt = line.split(SEP, 1)[0]
                    got_v = BSF.spelled_value(vt) if fmt == "words" else BSF.printed_value(vt)
                    if abs(got_v - float(opt["attrs"][a["name"]])) > 1e-9:
                        errs.append(f"{fmt} {opt['code']}: {a['name']} printed {got_v}, stimuli.json has "
                                    f"{opt['attrs'][a['name']]}")
                label, _ = BSF.role_of(d, opt, focal)
                if (o["tab"] or "").lower() != label.lower():
                    errs.append(f"{fmt} {opt['code']}: tab {o['tab']!r}, role {label!r}")
                is_target = opt["code"] == d["stim"]["target"]
                if is_target != (o["tab"] or "").lower().startswith("target"):
                    errs.append(f"{fmt} {opt['code']}: target tab does not match stimuli.json target")
        if n_sep != len(dash_nodes) or n_sep != 12:
            errs.append(f"{n_sep} separators in card lines, {len(dash_nodes)} em dashes on the page, expected 12")
        out = OUT
        if "--draft" in sys.argv:            # look at a layout that fails its checks, never as the manuscript file
            out = os.path.join(BSF.SHOTS_DIR, "drafts", "figure2_draft.png")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            print("DRAFT: " + (" | ".join(errs) if errs else "all checks pass"))
        elif errs:
            br.close()
            refuse("\n  ".join(errs))
        pg.locator(".fig").screenshot(path=out)
        br.close()
    if "--draft" in sys.argv:
        return
    im = Image.open(OUT)
    im.save(OUT, dpi=(480, 480), optimize=True)
    print(f"wrote {os.path.normpath(OUT)}: {im.size[0]} x {im.size[1]} px, {im.size[0] / 480:.2f} x "
          f"{im.size[1] / 480:.3f} in at 480 dpi; {len(rec['opts'])} options and 12 separators checked against "
          f"stimuli.json and the survey writers; smallest text {min(f[0] for f in rec['fonts']) * 0.75:.2f} pt "
          f"(picture {min_pic_pt:.2f} pt)")


if __name__ == "__main__":
    main()
