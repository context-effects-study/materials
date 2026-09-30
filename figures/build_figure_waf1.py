"""build_figure_waf1.py: draws Figure WA-F1, the course of the eighteen adjustable calibration pairs over the
three waves.

It reads Tables WA-F3, WA-F4 and WA-F5 (figures/figure_waf1_tables.md, the tables exactly as the web appendix
prints them; each row equals the same pair's row in the wave's report of record) and draws one small panel per
pair: the target share in each wave with its 95 percent interval, the registered target band (40 to 45
percent) shaded and the registered limits (25 and 75 percent) dashed. Each panel's title gives the pair and
its final status. It stops unless every pair has a wave-1 row and the tables agree on the pair names.

Output: figures/figure_waf1.png (6.5 inches wide, 300 dpi).
Needs: matplotlib (see requirements.txt).

Run: python figures/build_figure_waf1.py
"""
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
WA = os.path.join(HERE, "figure_waf1_tables.md")
OUT = os.path.join(HERE, "figure_waf1.png")

ORDER = ["Backpacks, new values", "Bluetooth speakers, new values", "Earbuds, new values", "Hard drives, new values",
         "Restaurants, new values", "Televisions, new values", "Water bottles, new values",
         "Electric kettles (invented)", "Robot vacuums (invented)", "Standing desks (invented)",
         "Bluetooth speakers, words", "Hard drives, words", "Televisions, words", "Water bottles, words",
         "Bluetooth speakers, pictures", "Hard drives, pictures", "Televisions, pictures", "Water bottles, pictures"]
STATUS = {"Backpacks, new values": "retained", "Restaurants, new values": "retained", "Earbuds, new values": "retained",
          "Standing desks (invented)": "retained", "Water bottles, pictures": "retained",
          "Electric kettles (invented)": "retained",  # fails by option identity (2026-09-29; WA-F)
          "Hard drives, pictures": "removed"}


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


def main():
    text = open(WA, encoding="utf-8").read()
    waves = {}
    for w, cap in ((1, "**TABLE WA-F3.**"), (2, "**TABLE WA-F4.**"), (3, "**TABLE WA-F5.**")):
        for r in table(text, cap):
            m = re.match(r"\[([0-9.]+), ([0-9.]+)\]", r[3])
            if not m:
                sys.exit(f"REFUSED: cannot read the interval in {cap}: {r}")
            waves.setdefault(r[0], {})[w] = (float(r[2]), float(m.group(1)), float(m.group(2)))
    missing = [p for p in ORDER if p not in waves or 1 not in waves[p]]
    extra = [p for p in waves if p not in ORDER]
    if missing or extra:
        sys.exit(f"REFUSED: pairs missing {missing} or unexpected {extra}")

    plt.rcParams.update({"font.family": "Arial", "font.size": 7, "axes.linewidth": 0.6})
    fig, axes = plt.subplots(3, 6, figsize=(6.5, 4.4), sharex=True, sharey=True)
    for ax, pair in zip(axes.flat, ORDER):
        ax.axhspan(40, 45, color="#d7e9dc", zorder=0)
        for y in (25, 75):
            ax.axhline(y, color="#8a8a8a", lw=0.6, ls=(0, (3, 2)), zorder=1)
        pts = sorted(waves[pair].items())
        xs = [w for w, _ in pts]
        ys = [v[0] for _, v in pts]
        ax.plot(xs, ys, color="#2f3b4c", lw=1.2, zorder=3)
        for w, (s, lo, hi) in pts:
            ax.plot([w, w], [lo, hi], color="#2f3b4c", lw=0.8, zorder=2)
            ax.plot(w, s, "o", ms=3.6, color="#2f3b4c", mec="white", mew=0.6, zorder=4)
        status = STATUS.get(pair, "final")
        if "(invented)" in pair:
            cat, variant = pair.replace(" (invented)", ""), "invented"
        else:
            cat, variant = pair.split(", ")
        ax.set_title(f"{cat}\n{variant}, {status}", fontsize=6.3, pad=3, linespacing=1.15)
        ax.set_xlim(0.6, 3.4)
        ax.set_ylim(15, 100)
        ax.set_xticks([1, 2, 3])
        ax.tick_params(length=2, width=0.5, labelsize=6.3)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.grid(False)
    for ax in axes[:, 0]:
        ax.set_ylabel("Target share (%)", fontsize=6.5)
    for ax in axes[-1, :]:
        ax.set_xlabel("Wave", fontsize=6.5)
    fig.tight_layout(h_pad=0.9, w_pad=0.4)
    fig.savefig(OUT, dpi=300)
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
