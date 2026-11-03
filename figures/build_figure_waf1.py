"""build_figure_waf1.py: draws Figure WA-F1, the course of the eighteen adjustable calibration pairs over the
three waves.

It reads Tables WA-F3, WA-F4 and WA-F5 (figures/figure_waf1_tables.md, the tables exactly as the web appendix
prints them; each row equals the same pair's row in the wave's report of record) and draws one small panel per
pair: the target share in each wave with its 95 percent interval, the registered target band (40 to 45
percent) as a pale blue tint and the registered limits (25 and 75 percent) as dashed lines. The four
categories tested in three formats come first, one column per category and one row per format; the other three
published categories and the three new categories (tier 3) follow. The last point of each pair has the colour of the
pair's final status, which is printed beside it (final, retained or removed). The type is IBM Plex Sans, read
from the font files in figures/fonts/ (SIL Open Font License, figures/fonts/license.txt).

It stops unless every pair has a wave-1 row, the tables agree on the pair names, each pair's status agrees with
the outcome the tables print, and every text is at least 6.5 point, inside the image, clear of other text and
clear of the points and intervals of its own panel. With --selftest it plants errors of each kind and shows
that every one is refused.

Output: figures/figure_waf1.png (6.5 inches wide, 300 dpi).
Needs: matplotlib (see requirements.txt).

Run: python figures/build_figure_waf1.py
     python figures/build_figure_waf1.py --selftest
"""
import argparse
import copy
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
WA = os.path.join(HERE, "figure_waf1_tables.md")
OUT = os.path.join(HERE, "figure_waf1.png")
FONTS = os.path.join(HERE, "fonts")

ORDER = ["Backpacks, new values", "Bluetooth speakers, new values", "Earbuds, new values", "Hard drives, new values",
         "Restaurants, new values", "Televisions, new values", "Water bottles, new values",
         "Electric kettles (new category)", "Robot vacuums (new category)", "Standing desks (new category)",
         "Bluetooth speakers, words", "Hard drives, words", "Televisions, words", "Water bottles, words",
         "Bluetooth speakers, pictures", "Hard drives, pictures", "Televisions, pictures", "Water bottles, pictures"]
STATUS = {"Backpacks, new values": "retained", "Restaurants, new values": "retained", "Earbuds, new values": "retained",
          "Standing desks (new category)": "retained", "Water bottles, pictures": "retained",
          "Electric kettles (new category)": "retained",  # fails by option identity (2026-09-29; WA-F)
          "Hard drives, pictures": "removed"}

# the layout: (row label, [(pair, panel title or None), ...]); group 1 takes its titles from the column headings
COLUMNS = ["Bluetooth speakers", "Hard drives", "Televisions", "Water bottles"]
GROUP1 = [(fmt, [(f"{c}, {fmt.lower()}", None) for c in COLUMNS]) for fmt in ("New values", "Words", "Pictures")]
GROUP2 = [("New values", [(f"{c}, new values", c) for c in ("Backpacks", "Earbuds", "Restaurants")]),
          ("New categories", [(f"{c} (new category)", c) for c in ("Electric kettles", "Robot vacuums", "Standing desks")])]

# colours and type (the figure tokens of the redrawn figures)
INK, INK2, AXIS, RULE = "#1d1d1f", "#5b5f66", "#7a7b7d", "#dedede"
BAND, LIMIT, COURSE = "#e3e8f8", "#9a9ea6", "#aeb4c0"
STATUS_COLOUR = {"final": "#2441c3", "retained": "#5b5f66", "removed": "#b5432f"}
LABEL_PT, NOTE_PT, TICK_PT, MIN_PT = 7.5, 7.0, 6.5, 6.5

# geometry, in inches
W = 6.5
AX_X0, AX_W, AX_GAP = 0.98, 1.265, 0.14
AX_H, ROW_GAP = 0.78, 0.11
TITLE_H, TICKS_H, TOP, BOTTOM, GROUP_GAP = 0.19, 0.20, 0.05, 0.04, 0.16
XLIM, YLIM = (0.72, 4.30), (14, 98)
REF_X = (0.80, 3.16)            # the band and the limits run under the data, not under the status labels
DPI = 300


class Refused(Exception):
    pass


def font(weight, size):
    path = os.path.join(FONTS, f"IBMPlexSans-{weight}.ttf")
    if not os.path.isfile(path):
        raise Refused(f"font file missing: {path}")
    return FontProperties(fname=path, size=size)


# ---------------------------------------------------------------------------------------------------
# the tables
# ---------------------------------------------------------------------------------------------------
def table(text, caption):
    block = text.split(caption, 1)[1]
    rows = []
    for line in block.splitlines()[1:]:
        if line.startswith("|---") or line.startswith("| Pair"):
            continue
        if not line.startswith("|"):
            if rows:
                break
            continue
        rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows


def read_tables(text):
    """waves[pair][wave] = (share, lo, hi); rows[pair][wave] = the table row as printed."""
    waves, rows = {}, {}
    for w, cap in ((1, "**TABLE WA-F3.**"), (2, "**TABLE WA-F4.**"), (3, "**TABLE WA-F5.**")):
        for r in table(text, cap):
            m = re.match(r"\[([0-9.]+), ([0-9.]+)\]", r[3])
            if not m:
                raise Refused(f"cannot read the interval in {cap}: {r}")
            waves.setdefault(r[0], {})[w] = (float(r[2]), float(m.group(1)), float(m.group(2)))
            rows.setdefault(r[0], {})[w] = r
    return waves, rows


def check_pairs(waves):
    missing = [p for p in ORDER if p not in waves or 1 not in waves[p]]
    extra = [p for p in waves if p not in ORDER]
    laid = [p for _, row in GROUP1 + GROUP2 for p, _ in row]
    errs = []
    if missing or extra:
        errs.append(f"pairs missing {missing} or unexpected {extra}")
    if sorted(laid) != sorted(ORDER):
        errs.append(f"the layout places {sorted(set(laid) ^ set(ORDER))} wrongly or twice")
    return errs


def status_from_tables(pair, rows):
    """The final status as the tables print it, read independently of STATUS."""
    r = rows[pair]
    if 3 in r:
        outcome = r[3][5]
        if "outside 25-75 in all three waves" in outcome:
            return "removed"
        return "final" if outcome.startswith("Final") else "retained"
    last = r[max(r)]
    return "final" if "kept as final" in last[-1] else None


def check_status(rows, status):
    errs = []
    for pair in ORDER:
        want = status.get(pair, "final")
        got = status_from_tables(pair, rows)
        if got != want:
            errs.append(f"{pair}: drawn as {want!r}, but the tables print the outcome {got!r}")
    return errs


# ---------------------------------------------------------------------------------------------------
# the drawing
# ---------------------------------------------------------------------------------------------------
def layout_height():
    h = TOP + TITLE_H + 3 * AX_H + 2 * ROW_GAP + TICKS_H + GROUP_GAP
    h += 2 * (TITLE_H + AX_H) + ROW_GAP + TICKS_H + BOTTOM
    return h


def draw(waves, status, tweak=None):
    """Draw the figure; return (fig, problems). Nothing is saved here."""
    H = layout_height()
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    fig.patch.set_facecolor("white")
    f_label, f_note = font("Medium", LABEL_PT), font("Regular", NOTE_PT)
    f_tick, f_status = font("Regular", TICK_PT), font("SemiBold", NOTE_PT)

    def axes_at(x_in, top_in):
        return fig.add_axes([x_in / W, (H - top_in - AX_H) / H, AX_W / W, AX_H / H])

    labels, marks = [], {}          # status labels and, per axes, the points and intervals they must not cover
    y = TOP
    groups = [(GROUP1, True), (GROUP2, False)]
    for gi, (group, headed) in enumerate(groups):
        if headed:
            # one heading per column, and the measure once, above the tick column
            for ci, c in enumerate(COLUMNS):
                fig.text((AX_X0 + ci * (AX_W + AX_GAP)) / W, 1 - (y + TITLE_H - 0.05) / H, c, fontproperties=f_label,
                         color=INK, ha="left", va="baseline")
            fig.text((AX_X0 - 0.06) / W, 1 - (y + TITLE_H - 0.05) / H, "Target share (%)", fontproperties=f_note,
                     color=INK2, ha="right", va="baseline")
            y += TITLE_H
        for ri, (row_label, pairs) in enumerate(group):
            if not headed:
                y += TITLE_H
            last_row = ri == len(group) - 1
            fig.text(0.0, 1 - (y + AX_H / 2) / H, row_label, fontproperties=f_label, color=INK, ha="left",
                     va="center")
            for ci, (pair, title) in enumerate(pairs):
                ax = axes_at(AX_X0 + ci * (AX_W + AX_GAP), y)
                lab = panel(ax, pair, waves[pair], status.get(pair, "final"), f_status, marks)
                labels.append(lab)
                if title:
                    ax.text(0.0, 1.0, title, transform=ax.transAxes, fontproperties=f_label, color=INK, ha="left",
                            va="bottom")
                if ci == 0:
                    for v, txt, col in ((75, "75", INK2), (42.5, "40 to 45", STATUS_COLOUR["final"]),
                                        (25, "25", INK2)):
                        ax.text(-0.025, v, txt, transform=ax.get_yaxis_transform(), fontproperties=f_tick,
                                color=col, ha="right", va="center")
                if last_row:
                    for t in ax.get_xticklabels():
                        t.set_fontproperties(f_tick)
                        t.set_color(INK2)
                    if ci == 0:
                        ax.annotate("Wave", xy=(3, 0), xycoords=("data", "axes fraction"), xytext=(9, -3.5),
                                    textcoords="offset points", fontproperties=f_tick, color=INK2, ha="left",
                                    va="top")
                else:
                    ax.tick_params(labelbottom=False)
            y += AX_H + (TICKS_H if last_row else ROW_GAP)
        if gi == 0:
            yr = 1 - (y + GROUP_GAP / 2 - 0.06) / H
            fig.add_artist(Line2D([0, 1], [yr, yr], transform=fig.transFigure, color=RULE, lw=0.6))
            y += GROUP_GAP
    if tweak:
        tweak(fig, labels)
    return fig, check_text(fig, labels, marks)


def panel(ax, pair, pts, status, f_status, marks):
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_facecolor("none")
    ax.fill_between(REF_X, 40, 45, color=BAND, lw=0, zorder=0)
    for v in (25, 75):
        ax.plot(REF_X, [v, v], color=LIMIT, lw=0.5, dashes=(3, 2), zorder=1)
    pts = sorted(pts.items())
    xs, ys = [w for w, _ in pts], [v[0] for _, v in pts]
    colour = STATUS_COLOUR[status]
    if len(xs) > 1:
        ax.plot(xs, ys, color=COURSE, lw=1.0, zorder=2, solid_capstyle="round")
    for i, (w, (s, lo, hi)) in enumerate(pts):
        c = colour if i == len(pts) - 1 else COURSE
        ax.plot([w, w], [lo, hi], color=c, lw=0.8, zorder=3, solid_capstyle="butt")
        ax.plot(w, s, "o", ms=3.6 if i == len(pts) - 1 else 3.0, color=c, mec="white", mew=0.5, zorder=4)
    marks[ax] = [(w, s, lo, hi) for w, (s, lo, hi) in pts]
    w, (s, _, _) = pts[-1]
    lab = ax.text(w + 0.15, s, status, fontproperties=f_status, color=colour, ha="left", va="center", zorder=5)
    lab.pair = pair
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_bounds(1, 3)
    ax.spines["bottom"].set_color(AXIS)
    ax.spines["bottom"].set_linewidth(0.5)
    ax.set_xticks([1, 2, 3])
    ax.set_yticks([])
    ax.tick_params(axis="x", length=2, width=0.5, color=AXIS, pad=1.5)
    return lab


# ---------------------------------------------------------------------------------------------------
# the text check: size, canvas, overlap with other text, overlap with the marks of its own panel
# ---------------------------------------------------------------------------------------------------
def all_texts(fig):
    out = [t for t in fig.texts if t.get_text().strip()]
    for ax in fig.axes:
        out += [t for t in ax.texts if t.get_text().strip()]
        out += [t.label1 for t in ax.xaxis.get_major_ticks() if t.label1.get_visible() and t.label1.get_text()]
    return out


def check_text(fig, labels, marks):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    errs = []
    texts = all_texts(fig)
    boxes = [(t, t.get_window_extent(r)) for t in texts]
    cw, ch = fig.bbox.width, fig.bbox.height
    for t, b in boxes:
        if t.get_fontsize() < MIN_PT - 1e-9:
            errs.append(f"text under {MIN_PT} pt: {t.get_text()!r} at {t.get_fontsize()} pt")
        if b.x0 < -0.5 or b.y0 < -0.5 or b.x1 > cw + 0.5 or b.y1 > ch + 0.5:
            errs.append(f"text leaves the canvas: {t.get_text()!r}")
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i][1], boxes[j][1]
            if a.x0 < b.x1 - 0.5 and b.x0 < a.x1 - 0.5 and a.y0 < b.y1 - 0.5 and b.y0 < a.y1 - 0.5:
                errs.append(f"texts overlap: {boxes[i][0].get_text()!r} and {boxes[j][0].get_text()!r}")
    pad = 1.0
    for lab in labels:
        ax = lab.axes
        b = lab.get_window_extent(r)
        for other in fig.axes:
            if other is not ax and b.overlaps(other.bbox):
                errs.append(f"{lab.pair}: its label {lab.get_text()!r} reaches into the next panel")
        tr = ax.transData
        for w, s, lo, hi in marks[ax]:
            (x, yl), (_, yh) = tr.transform((w, lo)), tr.transform((w, hi))
            _, ys = tr.transform((w, s))
            rad = 3.6 / 72 * DPI / 2
            hit_whisker = b.x0 - pad < x < b.x1 + pad and min(yl, yh) < b.y1 + pad and max(yl, yh) > b.y0 - pad
            hit_point = (b.x0 - pad - rad < x < b.x1 + pad + rad) and (b.y0 - pad - rad < ys < b.y1 + pad + rad)
            if hit_whisker or hit_point:
                errs.append(f"{lab.pair}: its label {lab.get_text()!r} covers a point or interval of its panel")
                break
    return errs


# ---------------------------------------------------------------------------------------------------
def build(text):
    waves, rows = read_tables(text)
    errs = check_pairs(waves)
    if errs:
        raise Refused("; ".join(errs))
    errs = check_status(rows, STATUS)
    if errs:
        raise Refused("\n  ".join(errs))
    fig, errs = draw(waves, STATUS)
    if errs:
        plt.close(fig)
        raise Refused("\n  ".join(errs[:20]))
    return fig


def selftest():
    text = open(WA, encoding="utf-8").read()
    waves, rows = read_tables(text)
    fig, clean = draw(waves, STATUS)
    plt.close(fig)
    clean += check_pairs(waves) + check_status(rows, STATUS)
    print(f"  clean figure: {len(clean)} failures (must be 0)" + (f"  {clean[:3]}" if clean else ""))
    ok = not clean

    def first_label(name):
        def tw(fig, labels):
            for lab in labels:
                if lab.pair == name:
                    return lab
        return tw

    def move_onto_heading(fig, labels):
        lab = first_label("Bluetooth speakers, new values")(fig, labels)
        head = next(t for t in fig.texts if t.get_text() == "Hard drives")
        lab.set_transform(fig.transFigure)
        lab.set_position(head.get_position())

    def onto_own_point(fig, labels):
        lab = first_label("Earbuds, new values")(fig, labels)
        x, y = lab.get_position()
        lab.set_position((x - 0.15, y))

    def off_canvas(fig, labels):
        lab = first_label("Robot vacuums (new category)")(fig, labels)
        lab.set_position((40, lab.get_position()[1]))

    def tiny(fig, labels):
        first_label("Standing desks (new category)")(fig, labels).set_fontsize(6)

    def into_next_panel(fig, labels):
        lab = first_label("Hard drives, words")(fig, labels)
        lab.set_text("retained with measured baseline")

    w_missing = copy.deepcopy(waves)
    del w_missing["Televisions, words"][1]
    w_extra = copy.deepcopy(waves)
    w_extra["Kettles, words"] = {1: (40.0, 30.0, 50.0)}
    flipped = dict(STATUS, **{"Backpacks, new values": "final"})
    removed_wrong = dict(STATUS, **{"Water bottles, pictures": "removed"})
    rows_edited = copy.deepcopy(rows)
    rows_edited["Hard drives, words"][3][5] = "Did not calibrate (above 50)"
    cases = [
        ("a pair without its wave-1 row", lambda: check_pairs(w_missing)),
        ("a pair the layout does not know", lambda: check_pairs(w_extra)),
        ("a retained pair drawn as final", lambda: check_status(rows, flipped)),
        ("a retained pair drawn as removed", lambda: check_status(rows, removed_wrong)),
        ("a table outcome that no longer says final", lambda: check_status(rows_edited, STATUS)),
    ]
    for name, tw in (("a status label on a column heading", move_onto_heading),
                     ("a status label on its own point", onto_own_point),
                     ("a status label off the canvas", off_canvas),
                     ("a status label at 6 pt", tiny),
                     ("a status label that runs into the next panel", into_next_panel)):
        def run(tw=tw):
            f, e = draw(waves, STATUS, tw)
            plt.close(f)
            return e
        cases.append((name, run))
    for name, fn in cases:
        errs = fn()
        print(f"  planted: {name:<48} refused: {'yes' if errs else 'NO'}" + (f"  ({errs[0][:80]})" if errs else ""))
        ok &= bool(errs)
    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv[1:])
    if a.selftest:
        return selftest()
    fig = build(open(WA, encoding="utf-8").read())
    fig.savefig(OUT, dpi=DPI, facecolor="white")
    plt.close(fig)
    print("wrote", os.path.normpath(OUT))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Refused as e:
        sys.exit(f"REFUSED: {e}")
