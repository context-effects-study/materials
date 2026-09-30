"""generate_formats.py: the words and pictures versions of the format module.

The same effects are tested with the attributes shown as numbers (the backbone), as words (numeric values
spelled out) and as pictures (magnitude bars without numerals). The module covers four published
categories (bluetooth speakers, water bottles, hard drives, televisions) for the BIN, FRQ and SOT
structures at tier 2. Each variant is stored as a format_variants block on the tier-2 numbers stimulus:
spelled values for words, and one image per choice set (file name and SHA-256) for pictures. Two pictures
pairs carry their own calibrated values (see calibration_lock.py); the pictures version of the hard-drives
pair left the design at the final calibration lock.

Called by build_stimuli.py after the constructed structures are rebuilt, so the variants always derive
from the final numbers cells.
Manuscript: Method (the format module) and Web Appendix B.
"""
import os
import render
import geometry
from calibration_lock import (GEOMETRY_STRENGTHENED, PIC_ANCHORS, PIC_EXIT, ENRICHMENT,
                     enrichment_key)

FMT_CATS = ["bluetooth_speakers", "water_bottles", "hard_drives", "televisions"]
FMT_STRUCTS = ("BIN", "FRQ", "SOT")

_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
         "fifteen sixteen seventeen eighteen nineteen").split()
_TENS = ("_ _ twenty thirty forty fifty sixty seventy eighty ninety").split()

def _u999(n):
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else "-" + _ONES[n % 10])
    return _ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + _u999(n % 100))

def _int2words(n):
    n = int(n)
    if n < 1000:
        return _u999(n)
    if n < 1000000:
        th, r = n // 1000, n % 1000
        return _u999(th) + " thousand" + ("" if r == 0 else " " + _u999(r))
    return str(n)

def _num2words(v):
    if abs(v - round(v)) < 1e-9:
        return _int2words(round(v))
    s = f"{v:.1f}"
    whole, frac = s.split(".")
    return _int2words(int(whole)) + " point " + _ONES[int(frac)]

def attr_words(name, unit, v):
    u = (unit or "").lower()
    nl = name.lower()
    if "$" in u or "usd" in u or "price" in nl or "cost" in nl:
        d = int(v)
        c = round((v - d) * 100)
        return _int2words(d) + " dollars" + ("" if c == 0 else " and " + _int2words(c) + " cents")
    if "star" in u or "star" in nl:
        return _num2words(v) + " stars"
    if "0-100" in u or "100-point" in u:
        return _num2words(v) + " out of 100"
    unit_word = (unit or name).replace("_", " ")
    return _num2words(v) + " " + unit_word

def _words_render(options, attrs_meta):
    return [{"code": o["code"],
             "words": {a["name"]: attr_words(a["name"], a.get("unit", ""), o["attrs"][a["name"]])
                       for a in attrs_meta}}
            for o in options]

def _cap_from_unit(unit):
    u = (unit or "").lower()
    if "out of 5" in u or "/5" in u or "stars" in u:
        return 5.0
    if "0-100" in u or "100-point" in u or "100 point" in u or "0 to 100" in u:
        return 100.0
    return None


def _pictures_options(cat_id, cat, struct, numbers_options):
    """The option set the PICTURES variant of this cell carries. Per-format-value categories
    (PIC_ANCHORS) rebuild BIN/FRQ/SOT from the pictures anchor via the geometry engine (same
    strengthened parameters as the numbers build); everyone else shares the numbers options."""
    anc = PIC_ANCHORS.get(cat_id)
    if anc is None:
        return [dict(o, attrs=dict(o["attrs"])) for o in numbers_options], False
    attrs = cat["attributes"]
    higher = [a for a in attrs if a["direction"] == "higher_better"][0]
    lower = [a for a in attrs if a["direction"] == "lower_better"][0]
    caps = {}
    c = _cap_from_unit(higher.get("unit"))
    if c:
        caps[higher["name"]] = c
    anchor = {"A": {"name": higher["name"], "hf": anc["A"][0], "hd": anc["A"][1]},
              "B": {"name": lower["name"], "hf": anc["B"][0], "hd": anc["B"][1]}}
    built = {b["structure"]: b for b in geometry.build(
        anchor, attrs, price_free=False, caps=caps, tier=2, cat_id=cat_id,
        decoy_target=geometry.DECOY_TARGET.get(cat_id, "HD"), **GEOMETRY_STRENGTHENED)}
    return [dict(o) for o in built[struct]["options"]], True


def apply(stimuli, cat_by_id, assets_dir):
    """Augment the 4-category tier-2 BIN/FRQ/SOT numbers stimuli with words + pictures variants.
    final calibration lock (2026-07-02): hard_drives gets NO pictures variant (its pictures arm exited the design);
    bluetooth_speakers/televisions pictures variants carry their own locked values; SVGs render
    ENRICHED at the variant's own values."""
    n = 0
    for s in stimuli:
        if (s["category"] in FMT_CATS and s.get("memorization_tier") == 2
                and s["structure"] in FMT_STRUCTS and s.get("format") == "numbers"):
            cat = cat_by_id[s["category"]]
            attrs = cat["attributes"]
            s["format_variants"] = {"words": _words_render(s["options"], attrs)}
            if s["category"] not in PIC_EXIT:
                pic_opts, per_format = _pictures_options(s["category"], cat, s["structure"],
                                                         s["options"])
                enr = {o["code"]: ENRICHMENT[s["category"]][enrichment_key(o)] for o in pic_opts}
                fn, sha = render.option_svg_enriched(pic_opts, attrs, cat["label"], assets_dir,
                                                     s["id"], enr)
                s["format_variants"]["pictures"] = {
                    "image_ref": f"assets/{fn}", "image_sha256": sha, "image_format": "svg",
                    "options": pic_opts, "per_format_values": per_format,
                    "note": ("quantitative-magnitude rendering (Brendl 2023): bars, no numerals; "
                             "ENRICHED render (final calibration lock: names + qualifiers + attribute-naming legend, "
                             "the form the terminal calibration fielded); "
                             + ("PER-FORMAT LOCKED VALUES (wave-3 amendment (b) departure: the "
                                "pictures arm locked at its own values; `options` here are the "
                                "pictures column's values, rebuilt from the pictures anchor)"
                                if per_format else
                                "values shared with the numbers arm (`options` duplicated for "
                                "uniform consumption)")
                             + "; rasterize to PNG for the survey host + vision-model calls"),
                }
            n += 1
    return n
