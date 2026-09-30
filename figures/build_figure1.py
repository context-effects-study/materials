#!/usr/bin/env python3
"""build_figure1.py: draws Figure 1, the registered decision tree of the analysis, for print.

The tree's structure and node titles follow the Analysis Plan and Table 3; sub-labels are shortened where
space requires, and the registered wording stays in the manuscript. The layout is portrait, so that at the
printed width of 6.5 inches every label is at least 6 point. The script measures every text line in a
headless Chromium browser and stops if a line leaves its box, if a label collides, or if a dash other than a
hyphen appears.

Output: figures/figure1.svg and figures/figure1.png (rendered at three times the SVG size).
Needs: playwright with Chromium (see requirements.txt).

Run: python figures/build_figure1.py
"""
import os, json

HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = HERE

# ---------------------------------------------------------------- palette
GROUPS = {
    "input":      "#64748b",
    "criteria":      "#0e7490",
    "human":      "#0f766e",
    "map":        "#2a78d6",
    "tests":      "#7c3aed",
    "precedence": "#b45309",
    "scenarios":  "#86198f",
    "exits":      "#8f8f8f",
}
CLASS_ACCENT = {"HIGH": "#166534", "OVER": "#0e7490", "PARTIAL": "#bd8004", "LOW": "#64748b", "ANTI": "#be123c"}
EDGE = {
    "flow":       {"label": "advances",              "color": "#7C8AA5", "dash": None},
    "fails":      {"label": "criterion not met",     "color": "#9AA0AA", "dash": "6 4"},
    "classifies": {"label": "sorted into a class",   "color": "#2a78d6", "dash": None},
    "reads":      {"label": "feeds a pattern test",  "color": "#7c3aed", "dash": None},
    "overrides":  {"label": "override (registered)", "color": "#b45309", "dash": None},
    "routes":     {"label": "routes to a scenario",  "color": "#86198f", "dash": None},
    "apart":      {"label": "scored apart",          "color": "#9AA0AA", "dash": "6 4"},
}
EDGE_ORDER = ["flow", "fails", "classifies", "reads", "overrides", "routes", "apart"]

FONT = "ui-sans-serif, system-ui, 'Segoe UI', Helvetica, Arial, sans-serif"
CANVAS_FONT = "ui-sans-serif, system-ui, 'Segoe UI', Arial"
TITLE_PX, SUB_PX, PILL_PX, EYE_PX, LEG_PX = 15.5, 13, 13, 13, 13
TITLE_LH, SUB_LH = 19, 15.5

# ---------------------------------------------------------------- layout constants
W = 1010                      # viewBox width; at 6.5in print width 13px = 6.02pt effective
MARGIN = 28
TM = 20                       # top margin
# 2026-07-12 polish: wider band gaps so the stage pills separate cleanly from the band
# above and every arrow gets a real shaft (the old gaps left 2px pill clearance and
# 8px arrow stubs).
GAPS = [34, 36, 36, 50, 44, 50]   # gaps between the 7 bands (4 and 6 also carry a rail under their pill)
LEGEND_GAP, LEGEND_H, BM = 10, 38, 8
BH = [46, 48, 62, 158, 78, 46, 90]   # band heights (content vertically centered)

# ---------------------------------------------------------------- node spec
def N(id, band, x, w, accent, title, sub=None, dashed=False, hub=False, eyebrow=None):
    return dict(id=id, band=band, x=x, w=w, accent=accent, dashed=dashed, hub=hub,
                title=title, sub=sub or [], eyebrow=eyebrow)

NODES = [
    N("input", 0, 350, 310, GROUPS["input"], ["Every scorable cell"],
      ["model × effect × category × tier × format"]),
    N("criterion-human", 1, 175, 310, GROUPS["criteria"], ["The human replication criterion"],
      ["replicated in our calibrated human sample?"]),
    N("criterion-model", 1, 525, 310, GROUPS["criteria"], ["The model data-quality criterion"],
      ["parse ≥ 95% · refusals ≤ 5% · the ceiling rule"]),
    N("exit-human", 2, 33, 265, GROUPS["exits"], ["Effect not replicated in humans"],
      ["human result reported; model", "effects there reported apart"], dashed=True),
    N("bench", 2, 350, 310, GROUPS["human"], ["Human benchmarks"],
      ["effect size + interval per cell", "first-trial fallback"]),
    N("exit-model", 2, 715, 265, GROUPS["exits"], ["Not assessable as a respondent"],
      ["reported apart from the map"], dashed=True),
    # band 3: classes grid (left) + map hub (right) + sim below the hub
    # five classes (2026-09-29: OVER added, same direction and above 150% of the human effect)
    N("class-HIGH", 3, 65, 210, CLASS_ACCENT["HIGH"], ["HIGH"], ["matches people"]),
    N("class-OVER", 3, 319, 210, CLASS_ACCENT["OVER"], ["OVER"], ["overshoots people"]),
    N("class-PARTIAL", 3, 65, 210, CLASS_ACCENT["PARTIAL"], ["PARTIAL"],
      ["direction, not size"]),
    N("class-LOW", 3, 319, 210, CLASS_ACCENT["LOW"], ["LOW"],
      ["does not track context"]),
    N("class-ANTI", 3, 65, 210, CLASS_ACCENT["ANTI"], ["ANTI"],
      ["systematically reversed"]),
    N("map", 3, 575, 320, GROUPS["map"], ["The fidelity map"],
      ["model vs human effect size, every scorable cell"], hub=True,
      eyebrow="THE STUDY'S MAIN RESULT"),
    N("sim", 3, 625, 220, GROUPS["map"], ["Similarity, scored apart"],
      ["heterogeneity diagnostic,", "never pooled"], dashed=True),
    N("t1", 4, 33, 182, GROUPS["tests"], ["T1 · Memorization", "gradient"],
      ["the retrieval account"]),
    N("t2", 4, 224, 182, GROUPS["tests"], ["T2 · Knows-it vs", "shows-it"],
      ["rational override"]),
    N("t3", 4, 415, 182, GROUPS["tests"], ["T3 · Argument-", "strength ladder"],
      ["reason construction"]),
    N("t4", 4, 606, 182, GROUPS["tests"], ["T4 · Format"],
      ["reason construction", "(descriptive)"]),
    N("t5", 4, 797, 182, GROUPS["tests"], ["T5 · Trajectory"],
      ["generations,", "reasoning on/off"]),
    N("prec", 5, 325, 360, GROUPS["precedence"], ["The precedence rule"],
      ["two registered overrides resolve overlaps"]),
    N("S1", 6, 45, 218, GROUPS["scenarios"], ["S1 · High fidelity"]),
    N("S2", 6, 279, 218, GROUPS["scenarios"], ["S2 · Retrieval only"]),
    N("S3", 6, 513, 218, GROUPS["scenarios"], ["S3 · Reason construction"]),
    N("S4", 6, 747, 218, GROUPS["scenarios"], ["S4 · Rational override"]),
    N("S5", 6, 45, 218, GROUPS["scenarios"], ["S5 · Family-specific"]),
    N("S6", 6, 279, 218, GROUPS["scenarios"], ["S6 · Rising fidelity"]),
    N("S7", 6, 513, 218, GROUPS["scenarios"], ["S7 · Human effects fail"]),
    N("fallback", 6, 747, 218, GROUPS["scenarios"], ["No scenario matched"], dashed=True),
]
NODE = {n["id"]: n for n in NODES}

# (band, text, color, x, clear-window): the window is the x-range guaranteed free of crossing
# edges in that pill's gap row; the build FAILS if the measured pill exceeds it. x=None means
# "place after the previous pill on the same row".
PILLS = [
    (0, "INPUTS", GROUPS["input"], 40, (28, 342)),
    (1, "STEP 0 · VALIDITY CRITERIA", GROUPS["criteria"], 40, (28, 497)),
    (2, "STEP 1 · HUMAN BENCHMARKS", GROUPS["human"], 445, (438, 680)),
    (3, "STEP 2 · THE FIDELITY MAP", GROUPS["map"], 40, (28, 607)),
    (3, "FIDELITY CLASSES", GROUPS["map"], None, (28, 607)),
    (4, "STEP 3 · WHERE FIDELITY FAILS", GROUPS["tests"], 40, (28, 590)),
    (5, "PRECEDENCE RULE", GROUPS["precedence"], 138, (131, 307)),
    (6, "THE SEVEN SCENARIOS", GROUPS["scenarios"], 40, (28, 497)),
]

# ---------------------------------------------------------------- geometry
def band_tops():
    tops, y = [], TM
    for i, h in enumerate(BH):
        tops.append(y)
        y += h + (GAPS[i] if i < len(GAPS) else 0)
    total = tops[-1] + BH[-1] + LEGEND_GAP + LEGEND_H + BM
    return tops, total

BT, H = band_tops()

GRID_ROW_H, GRID_ROW_GAP = 44, 12
CLASS_ROW = {"class-HIGH": 0, "class-OVER": 0, "class-PARTIAL": 1, "class-LOW": 1, "class-ANTI": 2}
MAP_H, SIM_H, SIM_GAP = 62, 58, 14
SCN_ROW_H, SCN_ROW_GAP = 34, 22

def node_rect(n):
    b = n["band"]; top = BT[b]; h = BH[b]
    if n["id"].startswith("class-"):
        row = CLASS_ROW[n["id"]]
        gh = GRID_ROW_H * 3 + GRID_ROW_GAP * 2
        y0 = top + (h - gh) / 2 + row * (GRID_ROW_H + GRID_ROW_GAP)
        return (n["x"], y0, n["w"], GRID_ROW_H)
    if n["id"] == "map":
        return (n["x"], top, n["w"], MAP_H)
    if n["id"] == "sim":
        return (n["x"], top + MAP_H + SIM_GAP, n["w"], SIM_H)
    if n["band"] == 6:
        row = 0 if n["id"] in ("S1", "S2", "S3", "S4") else 1
        y0 = top + row * (SCN_ROW_H + SCN_ROW_GAP)
        return (n["x"], y0, n["w"], SCN_ROW_H)
    return (n["x"], top, n["w"], h)

def cx(nid):
    x, _, w, _ = node_rect(NODE[nid]); return x + w / 2

# ---------------------------------------------------------------- svg helpers
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def rgba(hex_, a):
    n = int(hex_.lstrip("#"), 16)
    return f"rgba({(n>>16)&255}, {(n>>8)&255}, {n&255}, {a})"

# ---------------------------------------------------------------- build
def build_svg(mw):
    """mw(text, px, weight, ls) -> measured width from Chromium."""
    OUT = []
    P = OUT.append
    errors = []

    P(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:g}" '
      f'font-family="{FONT}">')
    P(f'<rect width="{W}" height="{H:g}" fill="#ffffff"/>')
    P("<defs>")
    for t, m in EDGE.items():
        P(f'<marker id="a-{t}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5.6" '
          f'markerHeight="5.6" orient="auto-start-reverse">'
          f'<path d="M 0 1 L 9 5 L 0 9 z" fill="{m["color"]}"/></marker>')
    P("</defs>")

    def poly(points, etype, arrow=True):
        m = EDGE[etype]
        d = "M" + " L".join(f"{x:g},{y:g}" for x, y in points)
        dash = f' stroke-dasharray="{m["dash"]}"' if m["dash"] else ""
        mk = f' marker-end="url(#a-{etype})"' if arrow else ""
        P(f'<path d="{d}" fill="none" stroke="{m["color"]}" stroke-width="1.8" '
          f'stroke-linejoin="round" stroke-linecap="round"{dash}{mk}/>')

    def comb(trunk_x, src_y, rail_y, drop_xs, dst_y, etype):
        m = EDGE[etype]
        dash = f' stroke-dasharray="{m["dash"]}"' if m["dash"] else ""
        xs = sorted(drop_xs + [trunk_x])
        P(f'<path d="M{trunk_x:g},{src_y:g} L{trunk_x:g},{rail_y:g} '
          f'M{xs[0]:g},{rail_y:g} L{xs[-1]:g},{rail_y:g}" '
          f'fill="none" stroke="{m["color"]}" stroke-width="1.8" stroke-linecap="round"{dash}/>')
        for x in drop_xs:
            P(f'<path d="M{x:g},{rail_y:g} L{x:g},{dst_y:g}" fill="none" stroke="{m["color"]}" '
              f'stroke-width="1.8" stroke-linecap="round"{dash} marker-end="url(#a-{etype})"/>')

    # ---- edges (behind nodes) ----
    b = lambda i: BT[i]
    bot = lambda i: BT[i] + BH[i]
    comb(505, bot(0), b(1) - 12, [cx("criterion-human"), cx("criterion-model")], b(1), "flow")
    poly([(260, bot(1)), (260, b(2))], "fails")
    poly([(430, bot(1)), (430, b(2))], "flow")
    poly([(790, bot(1)), (790, b(2))], "fails")
    mapx, mapy, mapw, maph = node_rect(NODE["map"])
    poly([(688, bot(1)), (688, mapy)], "flow")
    poly([(615, bot(2)), (615, mapy)], "flow")
    simx, simy, simw, simh = node_rect(NODE["sim"])
    poly([(735, mapy + maph), (735, simy)], "apart")
    # map -> classes (classifies): rail A right of col2, rail B between the columns.
    # The trunk leaves the map's LEFT EDGE at the hub's mid-height (anchored to the box,
    # not floating below its corner); the cross-link to rail B runs in the row gap.
    r1y = node_rect(NODE["class-HIGH"])[1] + GRID_ROW_H / 2
    r2y = node_rect(NODE["class-LOW"])[1] + GRID_ROW_H / 2
    r3y = node_rect(NODE["class-ANTI"])[1] + GRID_ROW_H / 2
    midy = (r1y + r2y) / 2
    map_my = mapy + maph / 2
    railA, railB = 552, 297
    col2r, col1r = 319 + 210, 65 + 210
    m = EDGE["classifies"]
    P(f'<path d="M{mapx:g},{map_my:g} L{railA},{map_my:g} M{railA},{r1y:g} L{railA},{r2y:g} '
      f'M{railA},{midy:g} L{railB},{midy:g} M{railB},{r1y:g} L{railB},{r3y:g}" '
      f'fill="none" stroke="{m["color"]}" stroke-width="1.8" stroke-linecap="round"/>')
    for railx, colr, ys in ((railA, col2r, (r1y, r2y)), (railB, col1r, (r1y, r2y, r3y))):
        for yy in ys:
            P(f'<path d="M{railx},{yy:g} L{colr},{yy:g}" fill="none" stroke="{m["color"]}" '
              f'stroke-width="1.8" stroke-linecap="round" marker-end="url(#a-classifies)"/>')
    # map -> tests (reads comb); the trunk leaves the hub's bottom, left of sim
    comb(598, mapy + maph, b(4) - 12, [cx(t) for t in ("t1", "t2", "t3", "t4", "t5")],
         b(4), "reads")
    # tests -> precedence (the format test is descriptive and decides no scenario, so its line is drawn apart)
    g5 = b(5)
    entries = {"t1": 385, "t2": 445, "t3": cx("t3"), "t4": 565, "t5": 625}
    rails = {"t1": g5 - 38, "t2": g5 - 30, "t4": g5 - 22, "t5": g5 - 14}
    poly([(cx("t3"), bot(4)), (cx("t3"), g5)], "flow")
    for t, etype in (("t1", "overrides"), ("t2", "overrides"), ("t4", "apart"), ("t5", "flow")):
        ry = rails[t]
        poly([(cx(t), bot(4)), (cx(t), ry), (entries[t], ry), (entries[t], g5)], etype)
    # precedence -> scenarios (routes comb, two rails) + fallback (fails top entry)
    scn_top = b(6)
    rail1y = scn_top - 12
    r2top = node_rect(NODE["S5"])[1]
    rail2y = r2top - 12
    mr = EDGE["routes"]
    P(f'<path d="M505,{bot(5):g} L505,{rail1y:g} M33,{rail1y:g} L{cx("S4"):g},{rail1y:g} '
      f'M33,{rail1y:g} L33,{rail2y:g} M33,{rail2y:g} L{cx("S7"):g},{rail2y:g}" '
      f'fill="none" stroke="{mr["color"]}" stroke-width="1.8" stroke-linecap="round"/>')
    for s in ("S1", "S2", "S3", "S4"):
        P(f'<path d="M{cx(s):g},{rail1y:g} L{cx(s):g},{scn_top:g}" fill="none" '
          f'stroke="{mr["color"]}" stroke-width="1.8" marker-end="url(#a-routes)"/>')
    for s in ("S5", "S6", "S7"):
        P(f'<path d="M{cx(s):g},{rail2y:g} L{cx(s):g},{r2top:g}" fill="none" '
          f'stroke="{mr["color"]}" stroke-width="1.8" marker-end="url(#a-routes)"/>')
    fx, fy, fw, fh = node_rect(NODE["fallback"])
    pmy = b(5) + BH[5] / 2
    # top entry with a real shaft, matching the sibling scenario drops (the old right-edge
    # entry jammed its arrowhead against the canvas margin)
    poly([(325 + 360, pmy), (974, pmy), (974, rail2y), (fx + fw / 2, rail2y),
          (fx + fw / 2, fy)], "fails")

    # ---- pills (measured; window-checked) ----
    prev_end = None
    for band, text, col, px_, window in PILLS:
        tw = mw(text, PILL_PX, 700, 0.8)
        x0 = px_ if px_ is not None else prev_end + 14
        # 6px above the band it labels; bands 4 and 6 carry a horizontal rail at band-top - 12,
        # so their pills sit a rung higher to clear it (10px above the rail).
        y0 = BT[band] - (42 if band in (4, 6) else 26)
        if band == 0:
            y0 = BT[0] + BH[0] / 2 - 10   # beside the input node, in the top margin row
        if x0 < window[0] or x0 + tw + 18 > window[1]:
            errors.append(f"pill '{text}' [{x0:.0f}..{x0 + tw + 18:.0f}] outside window {window}")
        P(f'<rect x="{x0:g}" y="{y0:g}" width="{tw + 18:g}" height="20" rx="10" '
          f'fill="{rgba(col, 0.06)}" stroke="{rgba(col, 0.35)}"/>')
        P(f'<text x="{x0 + 9:g}" y="{y0 + 14.5:g}" font-size="{PILL_PX}" font-weight="700" '
          f'letter-spacing="0.8" fill="{col}">{esc(text)}</text>')
        prev_end = x0 + tw + 18

    # ---- nodes ----
    for n in NODES:
        x, y, w, h = node_rect(n)
        acc = n["accent"]
        fill = rgba(acc, 0.07) if n["hub"] else "#ffffff"
        sw = 2.4 if n["hub"] else 1.4
        dash = ' stroke-dasharray="6 4"' if n["dashed"] else ""
        P(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="9" fill="{fill}" '
          f'stroke="{rgba(acc, 0.75 if n["hub"] else 0.55)}" stroke-width="{sw}"{dash}/>')
        tx = x + 13
        eye = 17 if n["eyebrow"] else 0
        block = eye + len(n["title"]) * TITLE_LH + len(n["sub"]) * SUB_LH
        ty = y + (h - block) / 2 + 13
        interior = w - 26
        if n["eyebrow"]:
            if mw(n["eyebrow"], EYE_PX, 700, 1.1) > interior:
                errors.append(f"eyebrow overflows {n['id']}: {n['eyebrow']}")
            P(f'<text x="{tx:g}" y="{ty:g}" font-size="{EYE_PX}" font-weight="700" '
              f'letter-spacing="1.1" fill="{acc}">{esc(n["eyebrow"])}</text>')
            ty += eye
        for line in n["title"]:
            if mw(line, TITLE_PX, 600, 0) > interior:
                errors.append(f"title overflows {n['id']}: {line}")
            P(f'<text x="{tx:g}" y="{ty:g}" font-size="{TITLE_PX}" font-weight="600" '
              f'fill="#171717">{esc(line)}</text>')
            ty += TITLE_LH
        for line in n["sub"]:
            if mw(line, SUB_PX, 400, 0) > interior:
                errors.append(f"sub overflows {n['id']}: {line}")
            P(f'<text x="{tx:g}" y="{ty:g}" font-size="{SUB_PX}" fill="#444444">{esc(line)}</text>')
            ty += SUB_LH

    # ---- legend (two rows) ----
    ly = BT[6] + BH[6] + LEGEND_GAP + 12
    for r, row in enumerate((EDGE_ORDER[:4], EDGE_ORDER[4:])):
        lx = MARGIN + 2
        yy = ly + r * 19
        for t in row:
            m = EDGE[t]
            dash = ' stroke-dasharray="5 4"' if m["dash"] else ""
            P(f'<line x1="{lx}" y1="{yy - 4}" x2="{lx + 18}" y2="{yy - 4}" '
              f'stroke="{m["color"]}" stroke-width="2.4"{dash}/>')
            P(f'<text x="{lx + 24}" y="{yy}" font-size="{LEG_PX}" fill="#4d4d4d">{esc(m["label"])}</text>')
            lx += 24 + mw(m["label"], LEG_PX, 400, 0) + 26
        if lx - 26 > W - MARGIN:
            errors.append(f"legend row {r + 1} overflows the canvas ({lx - 26:.0f} > {W - MARGIN})")
    P("</svg>")
    return "\n".join(OUT), errors

# ---------------------------------------------------------------- verification + raster
def main():
    # collect every string that gets rendered, for one Chromium measuring pass
    strings = set()
    for n in NODES:
        for line in n["title"]: strings.add((line, TITLE_PX, 600, 0))
        for line in n["sub"]: strings.add((line, SUB_PX, 400, 0))
        if n["eyebrow"]: strings.add((n["eyebrow"], EYE_PX, 700, 1.1))
    for _, text, _, _, _ in PILLS: strings.add((text, PILL_PX, 700, 0.8))
    for t in EDGE_ORDER: strings.add((EDGE[t]["label"], LEG_PX, 400, 0))
    req = [{"t": t, "px": px, "w": wgt, "ls": ls} for (t, px, wgt, ls) in strings]

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        pg = br.new_page(viewport={"width": W, "height": int(H + 1)}, device_scale_factor=3)
        pg.goto("about:blank")
        widths = pg.evaluate("""(req) => {
            const c = document.createElement('canvas').getContext('2d');
            const out = {};
            for (const k of req) {
                c.font = `${k.w} ${k.px}px %s`;
                out[`${k.t}|${k.px}|${k.w}|${k.ls}`] =
                    c.measureText(k.t).width + k.ls * Math.max(0, k.t.length - 1);
            }
            return out;
        }""" % CANVAS_FONT.replace("'", "\\'"), req)
        mw = lambda t, px, wgt, ls: widths[f"{t}|{px:g}|{wgt}|{ls:g}"]

        svg, errors = build_svg(mw)
        for ch, name in ((u"—", "em dash"), (u"–", "en dash")):
            if ch in svg:
                errors.append(f"{name} present in the rendered SVG")
        if errors:
            br.close()
            raise SystemExit("FAIL:\n  " + "\n  ".join(errors))

        os.makedirs(MEDIA, exist_ok=True)
        svg_path = os.path.join(MEDIA, "figure1.svg")
        png_path = os.path.join(MEDIA, "figure1.png")
        with open(svg_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)
        pg.goto("file:///" + svg_path.replace("\\", "/"))
        pg.screenshot(path=png_path, clip={"x": 0, "y": 0, "width": W, "height": H})
        br.close()

    print(f"wrote {svg_path}  (viewBox {W} x {H:g}; subtitle {SUB_PX}px = "
          f"{SUB_PX / W * 6.5 * 72:.2f}pt at 6.5in print width)")
    print(f"wrote {png_path}  (3x raster; every text line measured in-engine and fits; "
          f"every pill inside its clear window; no em/en dashes)")

if __name__ == "__main__":
    main()
