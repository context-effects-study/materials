"""render.py: the deterministic picture renderer for the pictures format.

Draws a choice set as one SVG in which every attribute is a proportional bar and no numerals appear (the
quantitative-magnitude form). Price bars are amber with a "lower is better" caption. option_svg_enriched
adds the model names, the plain-language qualifiers and a legend naming each attribute (wave 3 onward).
The output is plain SVG text, so the same input always gives the same bytes; each image is returned with
its SHA-256 so the image a person or a model sees can be checked. PNG copies for the survey host and for
vision-model calls are made by surveys/rasterize.py.
Manuscript: Method (the pictures format) and Web Appendix B.

Imported by generate_formats.py and the wave image scripts; not run on its own.
"""
import hashlib, os

def _bar(x, y, w, h, frac, fill="#3b7a57"):
    frac = max(0.0, min(1.0, frac))
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#eee" stroke="#999"/>'
            f'<rect x="{x}" y="{y}" width="{w*frac:.1f}" height="{h}" fill="{fill}"/>')

def option_svg(options, attrs_meta, category_label, out_dir, stem_id):
    """One SVG per choice set: rows=options, per-attribute magnitude cue. Returns (filename, sha256)."""
    os.makedirs(out_dir, exist_ok=True)
    names = [a["name"] for a in attrs_meta]
    smax = {n: (max(o["attrs"][n] for o in options) * 1.15) or 1.0 for n in names}
    rowh, pad, colw, W = 56, 16, 185, 16 + 80 + 185 * len(attrs_meta) + 16
    H = pad * 2 + 26 + rowh * len(options) + 20   # +caption row
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Arial,sans-serif">',
           f'<rect width="{W}" height="{H}" fill="white"/>',
           f'<text x="{pad}" y="20" font-size="14" font-weight="bold">{category_label}</text>']
    letters = "ABCDEFG"
    y = pad + 26
    for i, o in enumerate(options):
        svg.append(f'<text x="{pad}" y="{y+18}" font-size="12" font-weight="bold">Option {letters[i]}</text>')
        cx = pad + 78
        for a in attrs_meta:
            n = a["name"]
            v = o["attrs"][n]
            svg.append(f'<text x="{cx}" y="{y+8}" font-size="9" fill="#555">{n.replace("_", " ")}</text>')
            # all attributes as proportional magnitude bars (ratings too - whole-star rounding
            # collapsed 4.6/4.7/5.0 and killed the bluetooth effect). Colour encodes direction so a
            # vision model cannot read a long price bar as "better".
            color = "#3b7a57" if a["direction"] == "higher_better" else "#d9822b"
            svg.append(_bar(cx, y + 12, 150, 13, v / smax[n], color))
            cx += colw
        y += rowh
    svg.append(f'<text x="{pad}" y="{H-7}" font-size="9" fill="#555">'
               f'Each bar shows the amount (no numbers). Green = quality, longer is better; '
               f'amber = price, longer is more expensive.</text>')
    svg.append("</svg>")
    data = ("\n".join(svg)).encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    fn = f"{stem_id}.svg"
    open(os.path.join(out_dir, fn), "wb").write(data)
    return fn, sha


def _wrap(text, width):
    """Greedy word-wrap for SVG text (no <tspan> auto-wrap in plain SVG)."""
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def option_svg_enriched(options, attrs_meta, category_label, out_dir, stem_id, enrichment):
    """The WAVE-3 ENRICHED variant of option_svg (2026-07-02; CALIBRATION_DESIGN wave-3 amendment
    (c)). Same deterministic string-SVG idiom and the same magnitude-bar manipulation (proportional
    bars, NO numerals anywhere); adds, per option row, the brand-neutral numeral-free model name
    under the option letter and each attribute's plain-language numeral-free qualifier under its
    bar - and the caption legend now names the ACTUAL attributes (the recorded wave-2 water-bottles
    legend-confusion fix: 'green = quality' misread when the quality attribute IS capacity).
    `enrichment` = {option_code: {"name": ..., "qualifiers": {attr: ...}}}. The original option_svg
    is untouched (wave-1/2 assets regenerate byte-identically). Returns (filename, sha256)."""
    os.makedirs(out_dir, exist_ok=True)
    names = [a["name"] for a in attrs_meta]
    smax = {n: (max(o["attrs"][n] for o in options) * 1.15) or 1.0 for n in names}
    rowh, pad, colw, labw = 96, 16, 215, 150
    W = pad + labw + colw * len(attrs_meta) + pad
    q_attrs = [a["name"].replace("_", " ") for a in attrs_meta if a["direction"] == "higher_better"]
    p_attrs = [a["name"].replace("_", " ") for a in attrs_meta if a["direction"] != "higher_better"]
    caption = ("Each bar shows the amount (no numbers). Longer green bar = more "
               + " / ".join(q_attrs) + " (better); longer amber bar = higher "
               + " / ".join(p_attrs) + " (more expensive).")
    H = pad * 2 + 26 + rowh * len(options) + 22
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Arial,sans-serif">',
           f'<rect width="{W}" height="{H}" fill="white"/>',
           f'<text x="{pad}" y="20" font-size="14" font-weight="bold">{category_label}</text>']
    letters = "ABCDEFG"
    y = pad + 26
    for i, o in enumerate(options):
        entry = enrichment[o["code"]]
        svg.append(f'<text x="{pad}" y="{y+14}" font-size="12" font-weight="bold">Option {letters[i]}</text>')
        ny = y + 27
        for ln in _wrap(entry["name"], 22)[:2]:
            svg.append(f'<text x="{pad}" y="{ny}" font-size="9" fill="#333">{ln}</text>')
            ny += 11
        cx = pad + labw
        for a in attrs_meta:
            n = a["name"]
            v = o["attrs"][n]
            svg.append(f'<text x="{cx}" y="{y+8}" font-size="9" fill="#555">{n.replace("_", " ")}</text>')
            color = "#3b7a57" if a["direction"] == "higher_better" else "#d9822b"
            svg.append(_bar(cx, y + 12, 150, 13, v / smax[n], color))
            qy = y + 38
            for ln in _wrap(entry["qualifiers"][n], 38)[:3]:
                svg.append(f'<text x="{cx}" y="{qy}" font-size="8.5" font-style="italic" fill="#666">{ln}</text>')
                qy += 11
            cx += colw
        y += rowh
    svg.append(f'<text x="{pad}" y="{H-7}" font-size="9" fill="#555">{caption}</text>')
    svg.append("</svg>")
    data = ("\n".join(svg)).encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    fn = f"{stem_id}.svg"
    open(os.path.join(out_dir, fn), "wb").write(data)
    return fn, sha
