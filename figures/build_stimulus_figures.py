"""build_stimulus_figures.py: draws the Web Appendix B stimulus figures and builds the offline stimulus explorer.

1. figures/stimulus_figures/: every choice set of every product category, drawn as the survey page shows it,
   with each option's role named in words (6.5 inches wide, at most 9 inches tall, no text under 6 point,
   480 dpi).
2. stimulus-explorer.html: one self-contained page with all 165 stimuli, filters, the participant's view,
   each option's role, and the exact text a model receives. It opens offline in any browser.

Nothing is typed twice: option cards come from the survey generators' own functions, the model text from the
runner's own prompt builder (models/run.py), and the pictures from the registered PNG files through the
runner's hash check. The survey joins a value and its description with an em dash; the figures and the
explorer print a spaced hyphen instead. The script stops when a printed value, word, name or description
differs from stimuli.json, when a role label or the design geometry behind it does not hold, when text
overflows its box or is under 6 point, when a figure is taller than 9 inches, when a choice set is missing,
or when the explorer, opened offline in a browser with the network blocked, makes a network request or shows
model text that differs from the runner's. Screenshots of the explorer and a list of the figures go to
reproduction/stimulus_figures/.
Needs: playwright with Chromium and Pillow (see requirements.txt).

Run: python figures/build_stimulus_figures.py              (figures, explorer and every check; a few minutes)
     python figures/build_stimulus_figures.py --selftest   (shows the checks stop planted errors)
"""
import argparse
import base64
import hashlib
import html
import json
import os
import re
import shutil
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
STIM_PATH = os.path.join(ROOT, "stimuli", "stimuli.json")
ASSET_DIR = os.path.join(ROOT, "stimuli")
FIG_DIR = os.path.join(HERE, "stimulus_figures")
OFFLINE_DIR = ROOT
EXPLORER = os.path.join(OFFLINE_DIR, "stimulus-explorer.html")
READY = os.path.join(ROOT, "reproduction", "stimulus_figures")
SHOTS_DIR = os.path.join(READY, "screens")

for _p in (os.path.join(ROOT, "stimuli"), os.path.join(ROOT, "surveys"), os.path.join(ROOT, "models")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from render_shared import render_value      # the one value renderer both arms share
import generate_qsf as GQ                   # the survey card writer (numbers)
import generate_survey as GS                # the survey card writer (words)
import run as RUN                           # the runner: deliveries, orders, prompt builder, picture check

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# print geometry: the page is laid out at 624 CSS px = 6.5 in, so 1 px = 0.75 pt
FIG_W_PX = 624
FIG_MAX_H_PX = 864          # 9 in
MIN_FONT_PX = 8.0           # 6 pt
DPR = 5                     # 3120 px wide = 480 dpi
DPI = round(FIG_W_PX * DPR / 6.5)
PIC_W_PX = 600              # picture width on the page; its smallest text must stay at or above 6 pt

EM, EN = "\u2014", "\u2013"
LETTERS = "ABCDEFGHIJKL"
APPENDIX_ORDER = ["backpacks", "bluetooth_speakers", "earbuds", "electric_kettles", "hard_drives",
                  "hard_drives_pf", "restaurants", "restaurants_pf", "robot_vacuums", "standing_desks",
                  "televisions", "televisions_pf", "water_bottles"]
PRICE_FREE = ["hard_drives_pf", "restaurants_pf", "televisions_pf"]

STRUCT_NAME = {"BIN": "Binary baseline", "SOT": "Compromise", "FRQ": "Attraction, frequency decoy",
               "RNG": "Attraction, range decoy", "PHT": "Phantom decoy", "SYM": "Upscaling",
               "SIM": "Similarity", "MOT": "Extremity menu", "EXC": "Extremity control"}
STRUCT_ORDER = ["BIN", "SOT", "FRQ", "RNG", "PHT", "SYM", "SIM", "EXC", "MOT"]
ADDED = {"DECOY": "frequency decoy", "RANGE_DECOY": "range decoy", "PHANTOM": "phantom, shown as unavailable",
         "EXTREME": "new extreme", "SYM_DECOY": "symmetric decoy"}
TIER_WORDS = {"High": "high tier (extreme)", "Middle": "middle tier", "Low": "low tier (extreme)"}
TIER_LABEL = {1: "Tier 1: published focal values", 2: "Tier 2: new values", 3: "Tier 3: invented category"}
FMT_LABEL = {"numbers": "Numbers", "words": "Words", "pictures": "Pictures"}


class Refused(Exception):
    pass


def refuse(msg):
    raise Refused(msg)


# ---------------------------------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------------------------------
def load():
    data = json.load(open(STIM_PATH, encoding="utf-8"))
    cats = {c["id"]: c for c in data["categories"]}
    if len(data["stimuli"]) != 165 or len(cats) != 13:
        refuse(f"expected 165 stimuli in 13 categories, found {len(data['stimuli'])} in {len(cats)}")
    return data, cats


def focal_words(data, cats):
    """What to call the two original options of each category, read from its binary sets and checked:
    budget and premium where price is an attribute, the attribute each leads on where it is not."""
    out = {}
    for cid, cat in cats.items():
        bins = [s for s in data["stimuli"] if s["category"] == cid and s["structure"] == "BIN"]
        a0, a1 = cat["attributes"][0], cat["attributes"][1]
        for b in bins:
            hf = next(o for o in b["options"] if o["code"] == "HF")
            hd = next(o for o in b["options"] if o["code"] == "HD")
            if not (hd["is_hd"] and not hf["is_hd"]):
                refuse(f"{b['id']}: is_hd flags do not mark HD as the premium option")
            if cat["price_free"]:
                ok = hd["attrs"][a0["name"]] > hf["attrs"][a0["name"]] and hf["attrs"][a1["name"]] > hd["attrs"][a1["name"]]
            else:
                ok = (a0["direction"] == "higher_better" and a1["direction"] == "lower_better"
                      and hd["attrs"][a0["name"]] > hf["attrs"][a0["name"]]
                      and hd["attrs"][a1["name"]] > hf["attrs"][a1["name"]])
            if not ok:
                refuse(f"{b['id']}: the two original options do not trade off as the labels assume")
        if cat["price_free"]:
            out[cid] = {"HD": "higher " + a0["name"].replace("_", " "), "HF": "higher " + a1["name"].replace("_", " ")}
        else:
            out[cid] = {"HF": "budget", "HD": "premium"}
    return out


def build_sets(data, cats):
    """Every choice set the study shows: the 165 stimuli, the second similarity placement of the 17
    similarity stimuli, the 12 words versions and the 9 pictures versions (203 sets), matched one to one
    with the runner's own deliveries so the figures, the explorer and the model text share one list."""
    sets = []
    for s in data["stimuli"]:
        cat = cats[s["category"]]
        prim = s.get("sim_placement") if s["structure"] == "SIM" else None
        base = dict(stim=s, cat=cat, fmt="numbers", placement=prim, options=s["options"], target=s.get("target"),
                    competitor=s.get("competitor"), words=None, image=None)
        sets.append(base)
        for pname, pv in (s.get("placement_variants") or {}).items():
            sets.append(dict(stim=s, cat=cat, fmt="numbers", placement=pname, options=pv["options"],
                             target=pv["target"], competitor=pv["competitor"], words=None, image=None))
        fv = s.get("format_variants") or {}
        if "words" in fv:
            sets.append(dict(stim=s, cat=cat, fmt="words", placement=None, options=s["options"],
                             target=s.get("target"), competitor=s.get("competitor"),
                             words={w["code"]: w["words"] for w in fv["words"]}, image=None))
        if "pictures" in fv:
            sets.append(dict(stim=s, cat=cat, fmt="pictures", placement=None, options=fv["pictures"]["options"],
                             target=s.get("target"), competitor=s.get("competitor"), words=None,
                             image=fv["pictures"]))
    for d in sets:
        d["key"] = f"{d['stim']['id']}|{d['fmt']}|{d['placement'] or ''}"
    keys = [d["key"] for d in sets]
    if len(set(keys)) != len(keys):
        refuse("duplicate choice-set keys")
    # the runner's own deliveries must be exactly these sets, with the same option values
    runner = {}
    for s in data["stimuli"]:
        for label, opts, wmap, image in RUN.deliveries(s):
            fmt, _, pname = label.partition(":")
            placement = pname or (s.get("sim_placement") if (s["structure"] == "SIM" and fmt == "numbers") else None)
            runner[f"{s['id']}|{fmt}|{placement or ''}"] = (opts, wmap, image)
    if set(runner) != set(keys):
        refuse(f"the runner's deliveries differ from the displayed sets: {sorted(set(runner) ^ set(keys))[:6]}")
    for d in sets:
        opts, wmap, image = runner[d["key"]]
        if json.dumps(opts, sort_keys=True) != json.dumps(d["options"], sort_keys=True):
            refuse(f"{d['key']}: runner options differ from the displayed options")
        if (wmap or None) != (d["words"] or None):
            refuse(f"{d['key']}: runner words differ")
    if len(sets) != 203:
        refuse(f"expected 203 choice sets (165 + 17 + 12 + 9), found {len(sets)}")
    return sets


# ---------------------------------------------------------------------------------------------------
# what each option is, in words, and the geometry that makes it so
# ---------------------------------------------------------------------------------------------------
def role_of(dset, opt, focal, short=False):
    """(label, kind) of one option. kind: focal, target, competitor, added, tier. short=True drops the
    budget/premium word where a column heading already carries it (the print matrix)."""
    S, code = dset["stim"]["structure"], opt["code"]
    fw = focal[dset["cat"]["id"]]
    if S == "BIN":
        return (fw[code] + ("" if dset["cat"]["price_free"] else " option"), "focal")
    if S in ("MOT", "EXC"):
        return (TIER_WORDS[opt["tier"]], "tier")
    who = "" if (short or code not in fw) else f" \u00b7 {fw[code]}"
    if code == dset["target"]:
        extra = {"SOT": ", now in the middle", "SIM": ", no clone"}.get(S, "")
        return (f"target{who}{extra}", "target")
    if code == dset["competitor"]:
        return (f"competitor{who}" + (", has a clone" if S == "SIM" else ""), "competitor")
    if code == "CLONE":
        return ((f"clone of {fw[opt['clone_of']]} option" if short else f"clone of the {fw[opt['clone_of']]} option"),
                "added")
    if code in ADDED:
        return (("phantom, unavailable" if (short and code == "PHANTOM") else ADDED[code]), "added")
    refuse(f"{dset['key']}: no role for option {code}")


def _better(a, x, y, name):
    """True if x is strictly better than y on attribute `name` (a = attribute meta)."""
    return x > y if a["direction"] == "higher_better" else x < y


def check_geometry(dset):
    """The design behind the role labels: the target is the option the added option is built around."""
    S = dset["stim"]["structure"]
    attrs = dset["cat"]["attributes"]
    by = {o["code"]: o["attrs"] for o in dset["options"]}
    errs = []

    def better(x, y, a):
        return _better(a, by[x][a["name"]], by[y][a["name"]], a["name"])

    def equal(x, y, a):
        return by[x][a["name"]] == by[y][a["name"]]

    t, c = dset["target"], dset["competitor"]
    if S in ("FRQ", "RNG", "PHT", "SOT", "SYM", "SIM") and ({t, c} != {"HF", "HD"}):
        errs.append(f"{dset['key']}: target and competitor are not the two original options")
        return errs
    if S == "FRQ" and not all(better(t, "DECOY", a) for a in attrs):
        errs.append(f"{dset['key']}: the target does not beat the frequency decoy on both attributes")
    if S == "RNG":
        weak_ok = all(not better("RANGE_DECOY", t, a) for a in attrs) and any(better(t, "RANGE_DECOY", a) for a in attrs)
        if not (weak_ok and any(equal(t, "RANGE_DECOY", a) for a in attrs)):
            errs.append(f"{dset['key']}: the range decoy is not matched on one attribute and dominated by the target")
    if S == "PHT":
        wins = [a for a in attrs if better("PHANTOM", t, a)]
        ties = [a for a in attrs if equal("PHANTOM", t, a)]
        if not (len(wins) == 1 and len(ties) == 1):
            errs.append(f"{dset['key']}: the phantom is not better than the target on exactly one attribute")
        ph = next(o for o in dset["options"] if o["code"] == "PHANTOM")
        if ph.get("available", True):
            errs.append(f"{dset['key']}: the phantom is not marked unavailable")
    if S == "SOT":
        for a in attrs:
            lo, mid, hi = by[c][a["name"]], by[t][a["name"]], by["EXTREME"][a["name"]]
            if not (min(lo, hi) < mid < max(lo, hi)):
                errs.append(f"{dset['key']}: the target is not the middle option on {a['name']}")
    if S == "SYM":
        for f in ("HF", "HD"):
            if not (all(not better("SYM_DECOY", f, a) for a in attrs) and any(better(f, "SYM_DECOY", a) for a in attrs)):
                errs.append(f"{dset['key']}: the symmetric decoy is not dominated by {f}")
    if S == "SIM":
        clone = next(o for o in dset["options"] if o["code"] == "CLONE")
        src = clone["clone_of"]
        other = "HD" if src == "HF" else "HF"
        if c != src or t != other:
            errs.append(f"{dset['key']}: the cloned option is not the competitor")
        # registered placement: about 12 percent of the gap from its original, floored at one whole unit, so
        # on a coarse attribute the clone can sit at the midpoint; it must be strictly nearer on at least one
        near = []
        for a in attrs:
            v, s0, o0 = clone["attrs"][a["name"]], by[src][a["name"]], by[other][a["name"]]
            if not (min(s0, o0) < v < max(s0, o0)) or abs(v - s0) > abs(v - o0) + 1e-9:
                errs.append(f"{dset['key']}: the clone is not between the originals and no farther from the one it copies")
            near.append(abs(v - s0) < abs(v - o0) - 1e-9)
        if not any(near):
            errs.append(f"{dset['key']}: the clone is not nearer to the option it copies on any attribute")
        if not (any(better("CLONE", src, a) for a in attrs) and any(better(src, "CLONE", a) for a in attrs)):
            errs.append(f"{dset['key']}: the clone is not a trade-off against the option it copies")
    if S in ("MOT", "EXC"):
        tiers = [o["tier"] for o in dset["options"]]
        want = {"MOT": ["High"] * 4 + ["Middle"] * 4 + ["Low"] * 4, "EXC": ["High", "Middle", "Low"]}[S]
        if tiers != want:
            errs.append(f"{dset['key']}: tiers are {tiers}")
    return errs


def measure_text(dset, where="figure"):
    S = dset["stim"]["structure"]
    if where == "explorer" and S == "BIN" and dset["fmt"] == "numbers":
        if dset["cat"]["price_free"]:
            return "The shared baseline for the three decoy sets of this category."
        return ("The shared baseline: every other numbers-format set of this category and tier is compared with it, except the "
                "extremity pair.")
    if dset["fmt"] != "numbers":
        fw = dset["fmt"]
        if S == "BIN":
            return f"The shared baseline for the frequency-decoy and compromise sets in {fw}."
        return {"FRQ": f"Measure: the target's share, against the baseline in {fw}.",
                "SOT": (f"Measure: the target's share of target and competitor choices, against the baseline "
                        f"in {fw}.")}[S]
    if S == "BIN":
        if dset["cat"]["price_free"]:
            return "The shared baseline: the three decoy sets below are compared with this pair."
        return "The shared baseline: every set on this page except the extremity pair is compared with it."
    return {
        "FRQ": "Measure: the target's share, against the baseline.",
        "RNG": "Measure: the target's share, against the baseline.",
        "PHT": "Measure: the target's share, against the baseline.",
        "SOT": "Measure: the target's share of target and competitor choices, against the baseline.",
        "SYM": "Measure: the premium option's share, against the baseline.",
        "SIM": "Measure: the target's share of target and competitor choices, against the baseline.",
        "MOT": ("Measure: the share of high-tier and low-tier choices in the menu, minus the same share in the "
                "control, which has one option per tier."),
        "EXC": "The control for the extremity menu: the same three tiers with one option each.",
    }[S]


def panel_name(dset, focal):
    S = dset["stim"]["structure"]
    name = STRUCT_NAME[S]
    if S == "SIM":
        src = "HF" if dset["placement"] == "clone_HF" else "HD"
        name += f", clone of the {focal[dset['cat']['id']][src]} option"
    return name, S


# ---------------------------------------------------------------------------------------------------
# option text: the survey's own card writers, and the independent expectation it is checked against
# ---------------------------------------------------------------------------------------------------
def survey_card_html(dset, opt, idx):
    s, cat = dset["stim"], dset["cat"]
    if dset["fmt"] == "numbers":
        h = GQ.render_option_html(s, opt, cat)
    elif dset["fmt"] == "words":
        h = GS.render_option_words(dset["words"][opt["code"]], cat, s, opt)
    else:
        h = f"<div class='cfx-attr'>Option {LETTERS[idx]}</div>"   # the picture page's answer buttons
    shown = h.replace(" " + EM + " ", " - ")
    if EM in shown or EN in shown:
        refuse(f"{dset['key']}: a dash other than the value separator in the survey card")
    return shown


def in_scope(dset):
    enr = DATA["enrichment"]
    s = dset["stim"]
    return (dset["fmt"] != "pictures" and s["memorization_tier"] in enr["scope"]["tiers"]
            and s["structure"] in enr["scope"]["structures"] and s["category"] in enr["by_category"])


def enrichment_entry(dset, opt):
    key = ("CLONE_" + opt["clone_of"]) if opt["code"] == "CLONE" else opt["code"]
    return DATA["enrichment"]["by_category"][dset["stim"]["category"]][key]


def value_text(dset, opt, a):
    v = opt["attrs"][a["name"]]
    if dset["fmt"] == "words":
        return dset["words"][opt["code"]][a["name"]]
    return render_value(a["name"], a.get("unit", ""), v)


def expected_lines(dset, opt, idx):
    if dset["fmt"] == "pictures":
        return [f"Option {LETTERS[idx]}"]
    lines = []
    entry = enrichment_entry(dset, opt) if in_scope(dset) else None
    if entry:
        lines.append(entry["name"])
    for a in dset["cat"]["attributes"]:
        vt = value_text(dset, opt, a)
        lines.append(vt + (" - " + entry["qualifiers"][a["name"]] if entry else ""))
    return lines


def behind_text(dset, opt):
    return "Values behind the bars (not shown to participants): " + ", ".join(
        render_value(a["name"], a.get("unit", ""), opt["attrs"][a["name"]]) for a in dset["cat"]["attributes"])


_SMALL = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_SMALL.update({w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())})


def _int_words(toks):
    total, cur = 0, 0
    if not toks:
        raise ValueError("no number words")
    for w in toks:
        if w in _SMALL:
            cur += _SMALL[w]
        elif w == "hundred":
            cur *= 100
        elif w == "thousand":
            total, cur = total + cur * 1000, 0
        else:
            raise ValueError(w)
    return total + cur


def spelled_value(text):
    """A spelled-out magnitude read back to a number, independently of the code that spelled it."""
    toks = text.lower().replace("-", " ").split()
    if "dollars" in toks:
        i = toks.index("dollars")
        d = _int_words(toks[:i])
        rest = toks[i + 1:]
        if not rest:
            return float(d)
        if rest[0] != "and" or rest[-1] != "cents":
            raise ValueError(text)
        return d + _int_words(rest[1:-1]) / 100.0
    num = []
    for w in toks:
        if w in _SMALL or w in ("hundred", "thousand", "point"):
            num.append(w)
        else:
            break
    if "point" in num:
        j = num.index("point")
        frac = num[j + 1:]
        if len(frac) != 1:
            raise ValueError(text)
        return _int_words(num[:j]) + _SMALL[frac[0]] / 10.0
    return float(_int_words(num))


def printed_value(text):
    m = re.match(r"^\$?([0-9][0-9,]*(?:\.[0-9]+)?)", text)
    if not m:
        raise ValueError(text)
    return float(m.group(1).replace(",", ""))


def check_option_record(dset, opt, idx, rec, focal):
    """Compare one printed option (rec: lines, tab, row, un, badge, behind) against stimuli.json."""
    errs = []
    key = f"{dset['key']} option {opt['code']}"
    want = expected_lines(dset, opt, idx)
    if rec["lines"] != want:
        errs.append(f"{key}: printed {rec['lines']!r}, expected {want!r}")
    # read every printed value back to a number, independently of the renderer
    if dset["fmt"] != "pictures":
        body = rec["lines"][1:] if in_scope(dset) else rec["lines"]
        attrs = dset["cat"]["attributes"]
        if len(body) != len(attrs):
            errs.append(f"{key}: {len(body)} attribute lines for {len(attrs)} attributes")
        for line, a in zip(body, attrs):
            vt = line.split(" - ", 1)[0] if in_scope(dset) else line
            try:
                got = spelled_value(vt) if dset["fmt"] == "words" else printed_value(vt)
            except ValueError:
                errs.append(f"{key}: cannot read a value from {vt!r}")
                continue
            if abs(got - float(opt["attrs"][a["name"]])) > 1e-9:
                errs.append(f"{key}: printed {a['name']} {got} but stimuli.json has {opt['attrs'][a['name']]}")
            if dset["fmt"] == "words" and vt != dset["words"][opt["code"]][a["name"]]:
                errs.append(f"{key}: words {vt!r} differ from the stored words")
    else:
        vals = (rec.get("behind") or "").split(":", 1)[-1].strip().split(", ")
        attrs = dset["cat"]["attributes"]
        try:
            bad = len(vals) != len(attrs) or any(abs(printed_value(v) - float(opt["attrs"][a["name"]])) > 1e-9
                                                 for v, a in zip(vals, attrs))
        except ValueError:
            bad = True
        if bad:
            errs.append(f"{key}: the values printed below the picture {rec.get('behind')!r} differ from stimuli.json")
    # availability
    un = not opt.get("available", True)
    if rec["un"] != un:
        errs.append(f"{key}: shown {'unavailable' if rec['un'] else 'available'}, stimuli.json says the opposite")
    if un and (rec.get("badge") or "").strip().lower() != "currently unavailable":
        errs.append(f"{key}: the unavailable option lacks its 'currently unavailable' tag")
    if not un and rec.get("badge"):
        errs.append(f"{key}: an available option carries the unavailable tag")
    # role, read from the stimulus fields by a second route
    S = dset["stim"]["structure"]
    tab = (rec.get("tab") or rec.get("row") or "").lower()
    col = (rec.get("col") or "").lower()
    fw = focal[dset["cat"]["id"]]
    # in the print matrix the column heading names the original option; the option must sit in its column
    if rec.get("col") is not None:
        want_col = fw.get(opt["code"]) if opt["code"] in ("HF", "HD") else "added option"
        if want_col not in col:
            errs.append(f"{key}: printed under the column {col!r}, belongs under {want_col!r}")
    who = tab + " " + col
    if S == "BIN":
        ok = tab.startswith(fw[opt["code"]])
        if not dset["cat"]["price_free"]:
            ok = ok and (("premium" in tab) == bool(opt["is_hd"]))
    elif S in ("MOT", "EXC"):
        ok = tab.startswith(opt["tier"].lower() + " tier")
    elif opt["code"] == dset["target"]:
        ok = tab.startswith("target") and fw[opt["code"]] in who
        ok = ok and ("middle" in tab) == (S == "SOT") and ("no clone" in tab) == (S == "SIM")
    elif opt["code"] == dset["competitor"]:
        ok = tab.startswith("competitor") and fw[opt["code"]] in who and ("has a clone" in tab) == (S == "SIM")
    elif opt["code"] == "CLONE":
        ok = tab in (f"clone of the {fw[opt['clone_of']]} option", f"clone of {fw[opt['clone_of']]} option")
    elif S == "PHT":
        ok = tab in ("phantom, shown as unavailable", "phantom, unavailable")
    else:
        ok = tab == {"FRQ": "frequency decoy", "RNG": "range decoy", "SOT": "new extreme",
                     "SYM": "symmetric decoy"}.get(S)
    if not ok:
        errs.append(f"{key}: role label {tab!r} does not match the design")
    return errs


# ---------------------------------------------------------------------------------------------------
# pictures
# ---------------------------------------------------------------------------------------------------
def png_text_chunks(b):
    """Names of PNG ancillary text/metadata chunks (a picture must carry none)."""
    out, i = [], 8
    while i < len(b):
        n = struct.unpack(">I", b[i:i + 4])[0]
        typ = b[i + 4:i + 8].decode("latin-1")
        if typ in ("tEXt", "iTXt", "zTXt", "eXIf", "tIME"):
            out.append(typ)
        i += 12 + n
    return out


def picture_payload(dset):
    """The registered PNG (hash-checked by the runner), its SVG source, and checks that the picture
    draws the stimulus file's values and names."""
    img = dset["image"]
    path, png_sha, svg_sha = RUN.picture_file(img)          # refuses unless the PNG is the registered file
    png = open(path, "rb").read()
    if hashlib.sha256(png).hexdigest() != png_sha:
        refuse(f"{dset['key']}: picture hash mismatch")
    if png_text_chunks(png):
        refuse(f"{dset['key']}: the picture carries metadata chunks {png_text_chunks(png)}")
    svg_path = os.path.join(ASSET_DIR, img["image_ref"])
    svg = open(svg_path, "rb").read()
    if hashlib.sha256(svg).hexdigest() != img["image_sha256"]:
        refuse(f"{dset['key']}: the SVG source hash differs from stimuli.json")
    svgt = svg.decode("utf-8")
    m = re.search(r'<svg[^>]*width="([0-9.]+)"[^>]*height="([0-9.]+)"', svgt)
    svg_w, svg_h = float(m.group(1)), float(m.group(2))
    w, h = struct.unpack(">II", png[16:24])
    if w != 2 * svg_w or h != 2 * svg_h:
        refuse(f"{dset['key']}: the PNG is not the 2x render of its SVG ({w}x{h} vs {svg_w}x{svg_h})")
    fonts = [float(x) for x in re.findall(r'font-size="([0-9.]+)"', svgt)]
    min_pt = min(fonts) * (PIC_W_PX / svg_w) * 0.75
    if min_pt < 6.0 - 1e-9:
        refuse(f"{dset['key']}: the picture's smallest text prints at {min_pt:.2f} pt")
    # bar lengths: 150 * value / (1.15 * max) per attribute, options in order
    attrs = dset["cat"]["attributes"]
    bars = [float(x) for x in re.findall(r'<rect x="[0-9.]+" y="[0-9.]+" width="([0-9.]+)" height="13" fill="#(?!eee)', svgt)]
    opts = dset["options"]
    smax = {a["name"]: max(o["attrs"][a["name"]] for o in opts) * 1.15 for a in attrs}
    want = [150 * o["attrs"][a["name"]] / smax[a["name"]] for o in opts for a in attrs]
    if len(bars) != len(want) or any(abs(b - x) > 0.051 for b, x in zip(bars, want)):
        refuse(f"{dset['key']}: the picture's bars {bars} do not draw the stimulus values {want}")
    texts = " ".join(re.findall(r">([^<]+)</text>", svgt))
    for i, o in enumerate(opts):
        e = enrichment_entry(dict(dset, fmt="numbers"), o)
        for piece in [f"Option {LETTERS[i]}", e["name"]] + list(e["qualifiers"].values()):
            if " ".join(piece.split()) not in " ".join(texts.split()):
                refuse(f"{dset['key']}: the picture does not carry {piece!r}")
    return dict(b64=base64.b64encode(png).decode("ascii"), file=os.path.basename(path), sha=png_sha,
                min_pt=min_pt, svg_w=svg_w, svg_h=svg_h)


# ---------------------------------------------------------------------------------------------------
# the print figures
# ---------------------------------------------------------------------------------------------------
FIG_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#fff}
body{font-family:Arial,Helvetica,sans-serif;color:#1c1c1c}
.fig{width:624px;padding:3px 3px 3px}
.fhead{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid #1c1c1c;padding-bottom:2px}
.fcat{font-size:12px;font-weight:bold}
.fmeta{font-size:9px}
.stem{font-size:9px;line-height:1.3;margin-top:3px}
.stem .lbl{font-weight:bold}
.key{font-size:8px;line-height:1.3;color:#333;margin:2px 0 5px}
.row{display:flex;gap:9px;margin-bottom:6px}
.row>.panel,.row>.info{flex:1 1 0;min-width:0}
.panel{border:1px solid #8c8c8c;border-radius:4px;padding:3px 6px 5px}
.ptitle{font-size:10px;font-weight:bold;line-height:1.25}
.ptitle .code{font-weight:normal;color:#444}
.pmeasure{font-size:8px;line-height:1.25;color:#333;margin-bottom:1px}
.opt{position:relative;margin-top:8px}
.tab{position:absolute;left:6px;top:-5px;z-index:1;font-size:8px;line-height:8px;font-weight:bold;text-transform:uppercase;letter-spacing:.02em;padding:0 3px;border:1px solid #1c1c1c;border-radius:2px;background:#fff;color:#1c1c1c;white-space:nowrap}
.tab.target{background:#1c1c1c;color:#fff}
.tab.added{background:#dcdcdc;border-color:#6a6a6a}
.card{border:1px solid #bfc6cd;border-radius:5px;background:#fff;padding:5px 6px 2px}
.cfx-attr{font-size:9px;line-height:1.2}
.card.un{border-style:dashed;background:#f1f2f3}
.card.un .cfx-attr{color:#5e5e5e}
.cfx-badge{display:inline-block;font-size:8px;line-height:10px;color:#6e3d00;background:#ffe3bd;border-radius:2px;padding:0 3px;margin:1px 0 1px}
.xhead{display:flex;gap:5px;margin:3px 0 0}
.xhead div{font-size:8px;font-weight:bold;line-height:1.2}
.xrow{display:flex;gap:5px;align-items:center}
.xlab{width:62px;flex:none;font-size:8px;font-weight:bold;text-transform:uppercase;line-height:1.2}
.xexc{width:98px;flex:none}
.xsep{width:1px;align-self:stretch;background:#8c8c8c;flex:none}
.xmot{flex:1 1 0;display:flex;gap:4px;min-width:0}
.xmot>.opt,.xexc>.opt{flex:1 1 0;min-width:0;margin-top:3px}
.xrow .card{padding:3px 5px 2px}
.xh1{width:62px;flex:none}.xh2{width:98px;flex:none}.xh3{width:1px;flex:none}.xh4{flex:1 1 0}
.info{border:1px dashed #8c8c8c;border-radius:4px;padding:5px 7px;font-size:8.5px;line-height:1.35;color:#222}
.info b{font-size:9px}
.sect{font-size:10px;font-weight:bold;margin:2px 0 3px;padding-top:2px;border-top:1px solid #8c8c8c}
.picblock{border:1px solid #8c8c8c;border-radius:4px;padding:3px 6px 5px;margin-bottom:6px}
img.pic{display:block;width:600px;margin:3px auto 0;border:1px solid #d5d9dd;border-radius:4px}
.btnrow{display:flex;gap:8px;margin-top:1px}
.btnrow>.opt{flex:1 1 0;min-width:0}
.behind{font-size:8px;color:#333;line-height:1.25;margin-top:2px}
.mx{margin-bottom:6px;border-bottom:1px solid #8c8c8c}
.mxhead,.mxrow{display:flex;gap:5px}
.mxhead{padding-bottom:1px}
.mxhead .mxc{font-size:8px;font-weight:bold;text-transform:uppercase;letter-spacing:.03em;color:#333;padding-left:1px}
.mxrow{border-top:1px solid #8c8c8c;padding:2px 0 4px}
.mxl{width:104px;flex:none;padding:1px 2px 0 0}
.mx.wide .mxl{width:150px}
.mxc{flex:1 1 0;min-width:0}
.mxl .ptitle{font-size:9px;line-height:1.2}
.mxl .pmeasure{margin-top:1px}
.mxrow .opt{margin-top:6px}
.mxempty{margin-top:6px;border:1px dotted #b8b8b8;border-radius:5px;height:calc(100% - 6px);min-height:18px;display:flex;align-items:center;justify-content:center}
.mxempty span{font-size:8px;color:#555}
.pfblock{margin-bottom:4px}
.pfhead{font-size:10px;font-weight:bold;line-height:1.2;margin-top:3px}
.pfblock .stem{font-size:8.5px;margin:1px 0 3px}
.note2{font-size:8px;line-height:1.3;color:#333;margin:-2px 0 6px}
"""


def esc(s):
    return html.escape(s, quote=True)


def card_block(dset, opt, idx, focal, with_tab=True, short=False):
    label, kind = role_of(dset, opt, focal, short)
    un = not opt.get("available", True)
    body = survey_card_html(dset, opt, idx)
    badge = "<span class='cfx-badge'>currently unavailable</span>" if un else ""
    tab = f"<div class='tab {kind}'>{esc(label)}</div>" if with_tab else ""
    behind = f"<div class='behind'>{esc(behind_text(dset, opt))}</div>" if dset["fmt"] == "pictures" else ""
    return (f"<div class='opt' data-code='{esc(opt['code'])}' data-idx='{idx}'>{tab}"
            f"<div class='card{' un' if un else ''}'>{body}{badge}</div>{behind}</div>")


def panel_html(dset, focal, suffix=""):
    name, code = panel_name(dset, focal)
    cards = "".join(card_block(dset, o, i, focal) for i, o in enumerate(dset["options"]))
    return (f"<section class='panel' data-set='{esc(dset['key'])}'><div class='ptitle'>{esc(name)}{esc(suffix)} "
            f"<span class='code'>({code})</span></div><div class='pmeasure'>{esc(measure_text(dset))}</div>"
            f"{cards}</section>")


def extremity_html(exc, mot, focal):
    rows = []
    for tier in ("High", "Middle", "Low"):
        eo = [(i, o) for i, o in enumerate(exc["options"]) if o["tier"] == tier]
        mo = [(i, o) for i, o in enumerate(mot["options"]) if o["tier"] == tier]
        if len(eo) != 1 or len(mo) != 4:
            refuse(f"{mot['key']}: tier {tier} holds {len(eo)} control and {len(mo)} menu options")
        rows.append(
            f"<div class='xrow' data-tier='{tier}'><div class='xlab'>{esc(TIER_WORDS[tier])}</div>"
            f"<div class='xexc' data-set='{esc(exc['key'])}'>{card_block(exc, eo[0][1], eo[0][0], focal, False)}</div>"
            f"<div class='xsep'></div><div class='xmot' data-set='{esc(mot['key'])}'>"
            + "".join(card_block(mot, o, i, focal, False) for i, o in mo) + "</div></div>")
    return ("<section class='panel xpanel'><div class='ptitle'>Extremity menu and its control "
            "<span class='code'>(MOT, EXC)</span></div>"
            f"<div class='pmeasure'>{esc(measure_text(mot))}</div>"
            "<div class='xhead'><div class='xh1'></div><div class='xh2'>Control (EXC)</div>"
            "<div class='xh3'></div><div class='xh4'>Menu (MOT): four options per tier, identical within a tier</div></div>"
            + "".join(rows) + "</section>")


def picture_html(dset, focal):
    pic = picture_payload(dset)
    name, code = panel_name(dset, focal)
    btns = "".join(card_block(dset, o, i, focal) for i, o in enumerate(dset["options"]))
    return (f"<section class='picblock' data-set='{esc(dset['key'])}'><div class='ptitle'>{esc(name)}, pictures "
            f"<span class='code'>({code})</span></div><div class='pmeasure'>{esc(measure_text(dset))}</div>"
            f"<img class='pic' alt='' src='data:image/png;base64,{pic['b64']}'>"
            f"<div class='btnrow'>{btns}</div></section>")


def page(head_left, head_right, stem, key_line, body):
    stem_html = f"<div class='stem'><span class='lbl'>Question above every set:</span> \u201c{esc(stem)}\u201d</div>" if stem else ""
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{FIG_CSS}</style></head><body>"
            f"<div class='fig'><div class='fhead'><span class='fcat'>{esc(head_left)}</span>"
            f"<span class='fmeta'>{esc(head_right)}</span></div>{stem_html}"
            f"<div class='key'>{esc(key_line)}</div>{body}</div></body></html>")


KEY_NUMBERS = ("Tabs above the cards name each option's role for readers; participants saw the cards alone, "
               "in a random order.")
KEY_PICTURES = ("Tabs name each option's role for readers. The picture and its answer buttons are the survey "
                "page's; every participant saw this fixed order.")


def one_stem(sets):
    stems = {d["stim"]["stem"] for d in sets}
    if len(stems) != 1:
        refuse(f"sets on one figure carry {len(stems)} different questions")
    return stems.pop()


def find(sets, cat, tier, S, fmt="numbers", placement=None):
    hits = [d for d in sets if d["cat"]["id"] == cat and d["stim"]["memorization_tier"] == tier
            and d["stim"]["structure"] == S and d["fmt"] == fmt and (placement is None or d["placement"] == placement)]
    if len(hits) != 1:
        refuse(f"expected one set for {cat} tier {tier} {S} {fmt} {placement}, found {len(hits)}")
    return hits[0]


def matrix_html(rows, focal, suffix=""):
    """One row per choice set; the two original options always in the first two columns and the added
    option in the third, so a reader sees what each structure adds by reading down one column."""
    cid = rows[0]["cat"]["id"]
    fw = focal[cid]
    if CATS[cid]["price_free"]:
        heads = [f"Option with the {fw['HF']}", f"Option with the {fw['HD']}", "Added option"]
    else:
        heads = ["Budget option", "Premium option", "Added option"]
    sparse = not any(in_scope(d) for d in rows)      # value-only cards are narrow: give the labels room
    out = [f"<div class='mx{' wide' if sparse else ''}'><div class='mxhead'><div class='mxl'></div>"
           + "".join(f"<div class='mxc'>{esc(h)}</div>" for h in heads) + "</div>"]
    for d in rows:
        name, code = panel_name(d, focal)
        cells = {0: "", 1: "", 2: ""}
        for i, o in enumerate(d["options"]):
            col = {"HF": 0, "HD": 1}.get(o["code"], 2)
            if cells[col]:
                refuse(f"{d['key']}: two options in one column")
            cells[col] = card_block(d, o, i, focal, short=True)
        if not cells[2]:
            cells[2] = "<div class='mxempty'><span>no added option</span></div>"
        out.append(f"<section class='mxrow' data-set='{esc(d['key'])}'><div class='mxl'><div class='ptitle'>"
                   f"{esc(name)}{esc(suffix)} <span class='code'>({code})</span></div>"
                   f"<div class='pmeasure'>{esc(measure_text(d))}</div></div>"
                   + "".join(f"<div class='mxc'>{cells[c]}</div>" for c in range(3)) + "</section>")
    out.append("</div>")
    return "".join(out)


def tier_figure(sets, cid, tier, focal):
    g = lambda S, p=None: find(sets, cid, tier, S, placement=p)   # noqa: E731
    used = [g("BIN"), g("SOT"), g("FRQ"), g("RNG"), g("PHT"), g("SYM"), g("SIM", "clone_HF"), g("SIM", "clone_HD"),
            g("EXC"), g("MOT")]
    body = matrix_html(used[:8], focal)
    body += extremity_html(used[8], used[9], focal)
    cat = CATS[cid]
    return page(cat["label"], f"{TIER_LABEL[tier]}, numbers format", one_stem(used), KEY_NUMBERS, body), used


def formats_figure_1(sets, cid, focal):
    words = [find(sets, cid, 2, S, "words") for S in ("BIN", "FRQ", "SOT")]
    pics = [d for d in sets if d["cat"]["id"] == cid and d["fmt"] == "pictures"]
    fig_numbers = FIG_NO[(cid, 2)]
    keeps_digit = any(re.search(r"\d", v) for d in words for w in d["words"].values() for v in w.values())
    spelled = ("Every value is written out in words, except the 100 of a rating out of 100"
               if keeps_digit else "Every number is written out in words")
    info = (f"{spelled}; the product names, the descriptions and the values are those "
            f"of the numbers version at tier 2 (Figure WA-B{fig_numbers}).")
    if not pics:
        info += (" The pictures version of this category was removed from the design after calibration "
                 "(Web Appendix F), so none is shown.")
    body = "<div class='sect'>Words version</div>"
    body += matrix_html(words, focal, ", words")
    body += f"<div class='note2'>{esc(info)}</div>"
    used = list(words)
    if pics:
        pb = find(sets, cid, 2, "BIN", "pictures")
        own = pb["image"].get("per_format_values")
        body += ("<div class='sect'>Pictures version" + (", with its own calibrated values" if own else
                 ", at the same values as the numbers version") + "</div>")
        body += picture_html(pb, focal)
        used.append(pb)
    cat = CATS[cid]
    return page(cat["label"], "Tier 2: new values, words and pictures formats" if pics else
                "Tier 2: new values, words format", one_stem(used), KEY_NUMBERS if not pics else
                KEY_NUMBERS + " Picture sets keep one fixed order.", body), used


def formats_figure_2(sets, cid, focal, S):
    """One picture per page: each picture must stay at least 6 inches wide to keep its smallest text at
    6 pt, so the frequency-decoy and compromise pictures (3.6 inches tall each) cannot share a page."""
    used = [find(sets, cid, 2, S, "pictures")]
    own = used[0]["image"].get("per_format_values")
    body = ("<div class='sect'>Pictures version, continued" + (", with its own calibrated values" if own else
            ", at the same values as the numbers version") + "</div>")
    body += "".join(picture_html(d, focal) for d in used)
    cat = CATS[cid]
    return page(cat["label"], "Tier 2: new values, pictures format", one_stem(used), KEY_PICTURES, body), used


def pricefree_figure(sets, focal):
    blocks, used = [], []
    for cid in PRICE_FREE:
        cs = [find(sets, cid, 2, S) for S in ("BIN", "FRQ", "RNG", "PHT")]
        used += cs
        cat = CATS[cid]
        attrs = " and ".join(a["name"].replace("_", " ") for a in cat["attributes"])
        label = cat["label"].split(" (")[0] + f", price-free ({attrs})"
        blocks.append(f"<div class='pfblock'><div class='pfhead'>{esc(label)}</div><div class='stem'>"
                      f"<span class='lbl'>Question above every set:</span> \u201c{esc(one_stem(cs))}\u201d</div>"
                      + matrix_html(cs, focal) + "</div>")
    return page("The three price-free categories", "Tier 2: new values, numbers format", None,
                KEY_NUMBERS + " Each category trades two quality attributes and has no price.", "".join(blocks)), used


def figure_plan(sets):
    plan = []
    for cid in APPENDIX_ORDER:
        cat = CATS[cid]
        if cat["price_free"]:
            if cid == PRICE_FREE[0]:
                plan.append(dict(kind="pricefree", cid=cid, slug="price_free_categories"))
            continue
        tiers = sorted({s["memorization_tier"] for s in DATA["stimuli"] if s["category"] == cid})
        for t in tiers:
            plan.append(dict(kind="tier", cid=cid, tier=t, slug=f"{cid}_tier{t}"))
        if any(d["cat"]["id"] == cid and d["fmt"] == "words" for d in sets):
            has_pics = any(d["cat"]["id"] == cid and d["fmt"] == "pictures" for d in sets)
            plan.append(dict(kind="formats1", cid=cid, slug=f"{cid}_words" + ("_and_pictures" if has_pics else "")))
            if has_pics:
                plan.append(dict(kind="formats2", cid=cid, S="FRQ", slug=f"{cid}_pictures_frequency_decoy"))
                plan.append(dict(kind="formats2", cid=cid, S="SOT", slug=f"{cid}_pictures_compromise"))
    for n, f in enumerate(plan, start=1):
        f["n"] = n
        f["file"] = f"figure_wab{n:02d}_{f['slug']}.png"
        if f["kind"] == "tier":
            FIG_NO[(f["cid"], f["tier"])] = n
    return plan


def build_figure_html(f, sets, focal):
    if f["kind"] == "tier":
        return tier_figure(sets, f["cid"], f["tier"], focal)
    if f["kind"] == "formats1":
        return formats_figure_1(sets, f["cid"], focal)
    if f["kind"] == "formats2":
        return formats_figure_2(sets, f["cid"], focal, f["S"])
    return pricefree_figure(sets, focal)


# the page-side reader: every option as printed, every text run's size and box, every overflow
EXTRACT_JS = r"""
(root) => {
  const R = document.querySelector(root);
  const box = R.getBoundingClientRect();
  const out = {height: box.height, width: box.width, opts: [], fonts: [], overflow: [], outside: [], text: R.innerText};
  R.querySelectorAll('.opt').forEach(o => {
    const holder = o.closest('[data-set]');
    const tab = o.querySelector('.tab');
    const row = o.closest('.xrow');
    const badge = o.querySelector('.cfx-badge');
    const behind = o.querySelector('.behind');
    const cell = o.closest('.mxc');
    let col = null;
    if (cell) {
      const i = [...cell.parentElement.children].indexOf(cell);
      col = cell.closest('.mx').querySelector('.mxhead').children[i].innerText;
    }
    out.opts.push({set: holder ? holder.dataset.set : null, code: o.dataset.code, idx: +o.dataset.idx, col: col,
      tab: tab ? tab.innerText : null, row: row ? row.querySelector('.xlab').innerText : null,
      lines: [...o.querySelectorAll('.card .cfx-attr')].map(e => e.innerText),
      un: o.querySelector('.card').classList.contains('un'), badge: badge ? badge.innerText : null,
      behind: behind ? behind.innerText : null});
  });
  const walker = document.createTreeWalker(R, NodeFilter.SHOW_TEXT);
  const boxes = '.tab,.card,.panel,.picblock,.info,.fig,.opt,.behind,.xlab,.xh2,.xh4,.stem,.fhead,.key,.sect,.mxl,.mxc,.mxempty,.note2,.pfhead';
  while (walker.nextNode()) {
    const n = walker.currentNode;
    if (!n.textContent.trim()) continue;
    const el = n.parentElement;
    out.fonts.push([parseFloat(getComputedStyle(el).fontSize), n.textContent.trim().slice(0, 50)]);
    const holder = el.closest(boxes);
    const hb = holder.getBoundingClientRect();
    const rg = document.createRange(); rg.selectNodeContents(n);
    for (const r of rg.getClientRects()) {
      if (r.width === 0) continue;
      if (r.left < hb.left - 0.5 || r.right > hb.right + 0.5 || r.top < hb.top - 0.5 || r.bottom > hb.bottom + 0.5)
        out.outside.push(n.textContent.trim().slice(0, 50));
    }
  }
  R.querySelectorAll('*').forEach(el => {
    if (el.clientWidth > 0 && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1)
        && getComputedStyle(el).overflow !== 'visible')
      out.overflow.push(el.className + ': ' + (el.innerText || '').slice(0, 40));
    if (el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 1 && /\b(card|tab|panel|picblock|info|opt|behind)\b/.test(el.className))
      out.overflow.push(el.className + ' is wider than its box: ' + (el.innerText || '').slice(0, 40));
  });
  document.querySelectorAll('.opt').forEach(o => {
    const t = o.querySelector('.tab'); if (!t) return;
    const a = t.getBoundingClientRect(), b = o.getBoundingClientRect();
    if (a.right > b.right + 0.5) out.overflow.push('tab wider than its card: ' + t.innerText);
  });
  const imgs = [...R.querySelectorAll('img.pic')].map(i => [i.getBoundingClientRect().width, i.naturalWidth]);
  out.imgs = imgs;
  return out;
}
"""


def check_page_record(rec, used, focal, max_h=FIG_MAX_H_PX, pic_w=PIC_W_PX):
    """Every failure on one rendered page: values, roles, coverage, dashes, sizes, overflow, height."""
    errs = []
    if rec["height"] > max_h + 0.01:
        errs.append(f"page is {rec['height']:.0f} px tall ({rec['height'] / 96:.2f} in), over {max_h / 96:.1f} in")
    if abs(rec["width"] - FIG_W_PX) > 0.5:
        errs.append(f"page is {rec['width']:.0f} px wide, not {FIG_W_PX}")
    if EM in rec["text"] or EN in rec["text"]:
        errs.append("an em or en dash is printed")
    small = [f for f in rec["fonts"] if f[0] < MIN_FONT_PX - 1e-6]
    if small:
        errs.append(f"{len(small)} text runs under 6 pt, e.g. {small[:3]}")
    if rec["outside"]:
        errs.append(f"text outside its box: {rec['outside'][:4]}")
    if rec["overflow"]:
        errs.append(f"overflow: {rec['overflow'][:4]}")
    for w, nat in rec.get("imgs", []):
        if abs(w - pic_w) > 0.5:
            errs.append(f"a picture is drawn {w:.1f} px wide, not {pic_w}")
    by_set = {}
    for o in rec["opts"]:
        by_set.setdefault(o["set"], []).append(o)
    want_keys = {d["key"] for d in used}
    if set(by_set) != want_keys:
        errs.append(f"sets printed {sorted(set(by_set) ^ want_keys)[:4]} differ from the sets planned")
    for d in used:
        got = by_set.get(d["key"], [])
        if [o["code"] for o in got] and sorted(o["idx"] for o in got) != list(range(len(d["options"]))):
            errs.append(f"{d['key']}: {len(got)} options printed for {len(d['options'])}")
            continue
        for o in got:
            opt = d["options"][o["idx"]]
            if opt["code"] != o["code"]:
                errs.append(f"{d['key']}: option {o['idx']} printed as {o['code']}, is {opt['code']}")
                continue
            errs += check_option_record(d, opt, o["idx"], o, focal)
        errs += check_geometry(d)
    return errs


def render_figures(sets, focal, only=None, draft=False):
    from playwright.sync_api import sync_playwright
    out_dir = os.path.join(SHOTS_DIR, "drafts") if draft else FIG_DIR
    os.makedirs(out_dir, exist_ok=True)
    plan = figure_plan(sets)
    results, seen = [], {}
    from PIL import Image
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        pg = br.new_page(viewport={"width": FIG_W_PX + 40, "height": 1200}, device_scale_factor=DPR)
        for f in plan:
            if only and f["n"] not in only:
                continue
            page_html, used = build_figure_html(f, sets, focal)
            pg.set_content(page_html)
            pg.wait_for_load_state("load")
            rec = pg.evaluate(EXTRACT_JS, ".fig")
            errs = check_page_record(rec, used, focal)
            if errs and draft:
                print(f"  DRAFT Figure WA-B{f['n']}: " + " | ".join(errs[:6]))
            elif errs:
                br.close()
                refuse(f"Figure WA-B{f['n']} ({f['slug']}):\n  " + "\n  ".join(errs[:20]))
            out = os.path.join(out_dir, f["file"])
            pg.locator(".fig").screenshot(path=out)
            im = Image.open(out)
            im.save(out, dpi=(DPI, DPI), optimize=True)
            for d in used:
                seen[d["key"]] = seen.get(d["key"], 0) + 1
            results.append(dict(f, height_in=rec["height"] / 96, px=im.size, n_sets=len(used),
                                n_options=len(rec["opts"]), min_font_pt=min(x[0] for x in rec["fonts"]) * 0.75,
                                pages=[d["key"] for d in used]))
            print(f"  Figure WA-B{f['n']:<2} {f['file']:<52} {rec['height'] / 96:4.2f} in tall, "
                  f"{len(used):2d} sets, {len(rec['opts']):2d} options, checks passed")
        br.close()
    if not only and not draft:
        missing = [d["key"] for d in sets if seen.get(d["key"]) != 1]
        if missing:
            refuse(f"{len(missing)} choice sets are not printed exactly once in the figures: {missing[:6]}")
    return results


# ---------------------------------------------------------------------------------------------------
# the offline explorer
# ---------------------------------------------------------------------------------------------------
_OPTION_LINE = re.compile(r"^\s+[A-L]\. ")


def split_prompt(prompt):
    """(opening, option lines, response line) of one choice prompt: the opening is every line before the first
    option line (a frame can span two lines when it carries the question's explanatory sentence)."""
    lines = prompt.split("\n")
    k = next(i for i, ln in enumerate(lines) if _OPTION_LINE.match(ln))
    return "\n".join(lines[:k]), "\n".join(lines[k:-1]), lines[-1]


def model_block(dset):
    """The set's three openings and its option lines per registered order, composed exactly as the runner does;
    refuses unless opening + lines + response line equals build_prompt for every frame and order, and unless the
    split matches the runner's own (split_head, where the picture goes in a picture call)."""
    s, cat = dset["stim"], dset["cat"]
    fmt = dset["fmt"]
    orders = RUN.orders_for_delivery(fmt, len(dset["options"]), dset["stim"]["id"])
    heads, blocks = [None] * len(RUN.PARAPHRASES), []
    for oi, order in enumerate(orders):
        per_frame = []
        for j, pid in enumerate(sorted(RUN.PARAPHRASES)):
            prompt, codes = RUN.build_prompt(s, cat, order, pid, fmt, dset["options"], dset["words"])
            head, block, last = split_prompt(prompt)
            if last != RUN.RESP:
                refuse(f"{dset['key']}: the prompt does not end with the registered response line")
            if hasattr(RUN, "split_head") and RUN.split_head(prompt) != (head, block + "\n" + last):
                refuse(f"{dset['key']}: the opening split differs from the runner's split_head")
            if head != RUN.frame_head(pid, cat, s):
                refuse(f"{dset['key']}: the opening differs from the runner's frame_head(pid, cat, stim)")
            if heads[j] is None:
                heads[j] = head
            elif heads[j] != head:
                refuse(f"{dset['key']}: the opening of frame {pid} changes with the option order")
            per_frame.append(block)
        if len(set(per_frame)) != 1:
            refuse(f"{dset['key']}: option lines differ between frames")
        blocks.append(per_frame[0])
    for oi, order in enumerate(orders):
        for j, pid in enumerate(sorted(RUN.PARAPHRASES)):
            prompt, _ = RUN.build_prompt(s, cat, order, pid, fmt, dset["options"], dset["words"])
            if heads[j] + "\n" + blocks[oi] + "\n" + RUN.RESP != prompt:
                refuse(f"{dset['key']}: composed model text differs from the runner's")
    return heads, blocks


def model_note(dset, n_orders):
    if dset["fmt"] == "pictures":
        return ("Sent as one user message, with no system message: the opening question, then the same picture "
                "file the participants see, then the option lines. Picture sets keep one option order, because the "
                "picture is fixed; each is sent under all three opening sentences.")
    if dset["stim"]["structure"] == "MOT":
        return ("Sent as one user message, with no system message. The 12-option menu is sent in 12 registered "
                "option orders, each a full shuffle of the twelve positions, and each order under all three "
                "opening sentences.")
    return (f"Sent as one user message, with no system message. This set is sent in all {n_orders} option orders, "
            f"each under all three opening sentences.")


def explorer_data(sets, focal):
    cats_used = []
    for cid in APPENDIX_ORDER:
        c = CATS[cid]
        cats_used.append(dict(id=cid, label=c["label"].replace(" (price-free: ", " (price-free, ").replace(" vs ", " and ")))
    heads, head_ix = [], {}                      # each distinct opening stored once; sets point to them
    images, out = {}, []
    order_key = {cid: i for i, cid in enumerate(APPENDIX_ORDER)}
    fmt_rank = {"numbers": 0, "words": 1, "pictures": 2}
    ordered = sorted(sets, key=lambda d: (order_key[d["cat"]["id"]], d["stim"]["memorization_tier"],
                                          STRUCT_ORDER.index(d["stim"]["structure"]),
                                          0 if d["placement"] in (None, "clone_HF") else 1, fmt_rank[d["fmt"]]))
    keymap = {}
    for n, d in enumerate(ordered, start=1):
        keymap[f"s{n}"] = d["key"]
        name, code = panel_name(d, focal)
        opts = []
        for i, o in enumerate(d["options"]):
            label, kind = role_of(d, o, focal)
            item = dict(h=survey_card_html(d, o, i), r=label, rk=kind, u=int(not o.get("available", True)))
            if d["fmt"] == "pictures":
                item["b"] = behind_text(d, o)
            opts.append(item)
        set_heads, blocks = model_block(d)
        openings = []
        for h in set_heads:
            if h not in head_ix:
                head_ix[h] = len(heads)
                heads.append(h)
            openings.append(head_ix[h])
        item = dict(k=f"s{n}", id=d["stim"]["id"], cat=d["cat"]["id"], s=d["stim"]["structure"],
                    t=d["stim"]["memorization_tier"], f=d["fmt"], title=name, code=code,
                    measure=measure_text(d, "explorer"),
                    stem=d["stim"]["stem"], opts=opts, m=blocks, op=openings, note=model_note(d, len(blocks)))
        if d["fmt"] == "pictures":
            pic = picture_payload(d)
            images[pic["file"]] = "data:image/png;base64," + pic["b64"]
            item.update(img=pic["file"], sha=pic["sha"])
        if d["fmt"] == "pictures" and d["image"].get("per_format_values"):
            item["own"] = 1
        errs = check_geometry(d)
        if errs:
            refuse("; ".join(errs))
        out.append(item)
    structs = [dict(id=S, label=f"{STRUCT_NAME[S]} ({S})") for S in STRUCT_ORDER]
    return dict(sets=out, cats=cats_used, heads=heads, resp=RUN.RESP, images=images, structs=structs,
                tiers={str(k): v for k, v in TIER_LABEL.items()}, fmts=FMT_LABEL,
                n_stimuli=len({d["stim"]["id"] for d in sets})), keymap


EXPLORER_CSS = r"""
:root{--bg:#f6f4f0;--ink:#1d1b18;--muted:#6a645c;--line:#e4dfd7;--card:#ffffff;--accent:#c4553a;--accent-soft:#fbe9e3;--survey-line:#d5dbe1;--survey-sel:#1f5fae;--code-bg:#1f2227;--code-ink:#e9ecef;color-scheme:light}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
a{color:inherit}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
.top{background:linear-gradient(180deg,#fffdf9 0%,var(--bg) 100%);border-bottom:1px solid var(--line)}
.hero{padding-top:34px;padding-bottom:18px}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);font-weight:700;margin:0 0 6px}
h1{font-size:34px;line-height:1.1;letter-spacing:-.02em;margin:0 0 10px;font-weight:750}
.lede{font-size:17px;color:#3b3731;max-width:760px;margin:0}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 0;padding:0;list-style:none}
.stats li{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px 14px;font-size:13px;color:var(--muted)}
.stats b{display:block;font-size:20px;color:var(--ink);line-height:1.2}
details.about{margin:16px 0 0;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:0 16px}
details.about summary{cursor:pointer;padding:12px 0;font-weight:650;list-style:none}
details.about summary::-webkit-details-marker{display:none}
details.about summary::before{content:"+";display:inline-block;width:18px;color:var(--accent);font-weight:800}
details.about[open] summary::before{content:"\2212"}
details.about ul{margin:0 0 14px;padding-left:20px;color:#3b3731}
details.about li{margin:4px 0}
.bar{border-bottom:1px solid var(--line)}
.filters{padding:14px 0 6px}
.fgroup{display:flex;align-items:flex-start;gap:10px;margin:0 0 8px}
.flabel{flex:none;width:130px;font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;padding-top:8px}
.chips{display:flex;flex-wrap:wrap;gap:6px;padding:2px 2px 4px;min-width:0;flex:1}
.ctlbar{background:rgba(246,244,240,.95);border-bottom:1px solid var(--line);z-index:5}
@media (min-width:721px){.ctlbar{position:sticky;top:0;backdrop-filter:saturate(1.4) blur(8px);-webkit-backdrop-filter:saturate(1.4) blur(8px)}}
.tofilters{position:fixed;right:16px;bottom:18px;z-index:6;border:0;border-radius:999px;background:var(--ink);color:#fff;font:inherit;font-size:14px;font-weight:650;padding:10px 16px;box-shadow:0 6px 20px rgba(0,0,0,.18);cursor:pointer;opacity:0;transform:translateY(10px);pointer-events:none;transition:opacity .2s,transform .2s}
.tofilters.on{opacity:1;transform:none;pointer-events:auto}
.chips::-webkit-scrollbar{display:none}
.chip{flex:none;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer;white-space:nowrap;transition:background .15s,border-color .15s,color .15s}
.chip:hover{border-color:#cfc7bb}
.chip[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:#fff}
.chip .n{opacity:.6;margin-left:6px;font-variant-numeric:tabular-nums}
.chip:disabled{opacity:.38;cursor:default}
.controls{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding-top:10px;padding-bottom:10px}
.switch{display:inline-flex;align-items:center;gap:8px;font-size:14px;cursor:pointer;user-select:none}
.switch input{position:absolute;opacity:0;width:1px;height:1px}
.track{width:40px;height:24px;border-radius:999px;background:#d7d1c8;position:relative;transition:background .2s;flex:none}
.track::after{content:"";position:absolute;top:3px;left:3px;width:18px;height:18px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.25);transition:transform .2s}
.switch input:checked+.track{background:var(--accent)}
.switch input:checked+.track::after{transform:translateX(16px)}
.switch input:focus-visible+.track{outline:2px solid var(--survey-sel);outline-offset:2px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--card)}
.seg button{border:0;background:none;font:inherit;font-size:13px;padding:5px 11px;cursor:pointer;color:var(--ink)}
.seg button[aria-pressed="true"]{background:var(--ink);color:#fff}
.frame-ctl{display:none;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
body.show-model .frame-ctl{display:inline-flex}
.count{margin-left:auto;font-size:13px;color:var(--muted)}
.reset{border:0;background:none;color:var(--accent);font:inherit;font-size:13px;font-weight:650;cursor:pointer;padding:0}
main{padding:22px 0 60px}
.set{background:var(--card);border:1px solid var(--line);border-radius:18px;margin:0 0 18px;box-shadow:0 1px 2px rgba(40,30,20,.04),0 8px 24px rgba(40,30,20,.04);overflow:hidden}
.set[hidden]{display:none}
.set-head{padding:16px 20px 10px;border-bottom:1px solid var(--line)}
.set-title{font-size:19px;line-height:1.25;margin:0 0 8px;font-weight:720;letter-spacing:-.01em}
.set-title .code{font-weight:500;color:var(--muted);font-size:15px}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px}
.tag{font-size:12px;border-radius:999px;padding:2px 10px;background:#f1ede6;color:#4a453e}
.tag.t1{background:#e8f0fb;color:#1f4f8f}.tag.t2{background:#eaf6ee;color:#23633a}.tag.t3{background:#f6ecf8;color:#6b2d7a}
.tag.fw{background:#fff4de;color:#7a4a00}.tag.fp{background:#e9f6f6;color:#11605f}
.measure{margin:0;font-size:14px;color:#4a453e}
.set-body{display:flex;flex-direction:column;gap:0}
.pane{padding:16px 20px 18px;min-width:0}
.pane-title{margin:0 0 10px;font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:750}
.mpane{display:none;border-top:1px solid var(--line);background:#fbfaf8}
body.show-model .mpane{display:block}
@media (min-width:980px){
  body.show-model .set-body{flex-direction:row}
  body.show-model .ppane{flex:1 1 0}
  body.show-model .mpane{flex:1 1 0;border-top:0;border-left:1px solid var(--line)}
}
.screen{background:#fdfdfd;border:1px solid #eceff2;border-radius:14px;padding:16px;max-width:680px;box-shadow:inset 0 1px 0 #fff}
.stem{margin:0 0 12px;font-size:15px;line-height:1.55;color:#1a1a1a}
.opts{display:flex;flex-direction:column;gap:12px}
.owrap{position:relative}
.rtab{display:none;position:absolute;left:12px;top:-9px;z-index:1;font-size:11px;line-height:16px;font-weight:750;letter-spacing:.04em;text-transform:uppercase;padding:0 7px;border-radius:6px;border:1px solid var(--ink);background:#fff;color:var(--ink);white-space:nowrap;max-width:calc(100% - 24px);overflow:hidden;text-overflow:ellipsis}
.rtab.target{background:var(--ink);color:#fff}
.rtab.added{border-style:dashed;border-color:var(--accent);color:var(--accent)}
.rtab.tier,.rtab.focal{border-color:#9a9187;color:#4a453e}
body.show-roles .rtab{display:inline-block}
body.show-roles .opts{gap:18px;padding-top:6px}
.ocard{display:block;border:1px solid var(--survey-line);border-radius:10px;padding:13px 15px;background:#fff;cursor:pointer;transition:border-color .12s,box-shadow .12s}
.ocard:hover{border-color:#9bb0c4}
.ocard.sel{border-color:var(--survey-sel);box-shadow:0 0 0 2px rgba(31,95,174,.18)}
.ocard.un{cursor:not-allowed;background:#f4f5f6;border-style:dashed;color:#6d7278}
.ocard.un .cfx-attr{color:#6d7278}
.vh{position:absolute;opacity:0;width:1px;height:1px;pointer-events:none}
.cfx-attr{font-size:15px;color:#222;margin:2px 0}
.cfx-badge{display:inline-block;font-size:12px;color:#8a4b00;background:#ffe9cc;border-radius:4px;padding:1px 6px;margin-top:4px}
.behind{margin:6px 2px 0;font-size:12.5px;color:var(--muted)}
.picwrap{margin:0 0 14px;border:1px solid #e3e6e9;border-radius:8px;overflow:hidden;background:#fff;cursor:zoom-in}
.picwrap img{display:block;width:100%;height:auto}
.picwrap.zoom{overflow-x:auto;cursor:zoom-out}
.picwrap.zoom img{width:612px;max-width:none}
.pnote{font-size:12.5px;color:var(--muted);margin:10px 2px 0}
.ids{font-size:12px;color:var(--muted);margin:8px 2px 0;word-break:break-all}
.mbar{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin:0 0 10px}
.stepper{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#4a453e}
.stepper button{width:30px;height:30px;border-radius:50%;border:1px solid var(--line);background:#fff;font:inherit;font-size:16px;cursor:pointer;line-height:1}
.stepper button:disabled{opacity:.35;cursor:default}
.copy{margin-left:auto;border:1px solid var(--line);background:#fff;border-radius:8px;font:inherit;font-size:12.5px;padding:4px 10px;cursor:pointer}
.prompt{background:var(--code-bg);color:var(--code-ink);border-radius:12px;padding:14px 16px;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word;overflow-wrap:anywhere;margin:0}
.prompt+.mimg{margin-top:8px}
.mimg{display:block;width:100%;height:auto;border-radius:8px;border:1px solid #d5d9dd;background:#fff}
.mimg+.prompt{margin-top:8px}
.mcap{font-size:12px;color:var(--muted);margin:4px 0 0;word-break:break-all}
.mnote{font-size:12.5px;color:var(--muted);margin:10px 0 0}
.empty{display:none;text-align:center;padding:60px 20px;color:var(--muted)}
.empty.on{display:block}
footer{border-top:1px solid var(--line);padding:18px 0 40px;font-size:12.5px;color:var(--muted)}
@media (max-width:720px){
  .wrap{padding:0 14px}
  .hero{padding-top:24px;padding-bottom:12px}
  .chips{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;-webkit-mask-image:linear-gradient(90deg,#000 88%,transparent);mask-image:linear-gradient(90deg,#000 88%,transparent);padding-right:28px}
  .chips::-webkit-scrollbar{display:none}
  .flabel{padding-top:0}
  h1{font-size:27px}
  .lede{font-size:15.5px}
  .fgroup{flex-direction:column;align-items:stretch;gap:4px}
  .flabel{width:auto}
  .set-head{padding:14px 14px 10px}
  .pane{padding:14px}
  .screen{padding:12px}
  .count{margin-left:0;width:100%}
  .stats li{padding:6px 10px}
  .stats b{font-size:17px}
}
"""

EXPLORER_JS = r"""
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("stimulus-data").textContent);
  var state = {cat: "all", str: "all", tier: "all", fmt: "all", roles: true, model: false, frame: 1};
  var pos = {}, byKey = {}, cards = [];
  D.sets.forEach(function (s) { byKey[s.k] = s; pos[s.k] = 0; });
  var catLabel = {}; D.cats.forEach(function (c) { catLabel[c.id] = c.label; });

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }
  function promptParts(k, frame, oi) {
    var s = byKey[k];
    return {head: D.heads[s.op[frame - 1]], rest: s.m[oi] + "\n" + D.resp};
  }
  function promptText(k, frame, oi) {
    var p = promptParts(k, frame, oi);
    return p.head + "\n" + p.rest;
  }
  window.stimulusExplorer = {
    promptText: promptText,
    keys: function () { return D.sets.map(function (s) { return s.k; }); },
    orders: function (k) { return byKey[k].m.length; }
  };

  function matches(s, skip) {
    return (skip === "cat" || state.cat === "all" || s.cat === state.cat) &&
      (skip === "str" || state.str === "all" || s.s === state.str) &&
      (skip === "tier" || state.tier === "all" || String(s.t) === state.tier) &&
      (skip === "fmt" || state.fmt === "all" || s.f === state.fmt);
  }

  var groups = [
    {id: "cat", label: "Category", opts: [["all", "All categories"]].concat(D.cats.map(function (c) { return [c.id, c.label]; }))},
    {id: "str", label: "Structure", opts: [["all", "All structures"]].concat(D.structs.map(function (x) { return [x.id, x.label]; }))},
    {id: "tier", label: "Memorization tier", opts: [["all", "All tiers"], ["1", D.tiers["1"]], ["2", D.tiers["2"]], ["3", "Tier 3: invented categories"]]},
    {id: "fmt", label: "Format", opts: [["all", "All formats"], ["numbers", "Numbers"], ["words", "Words"], ["pictures", "Pictures"]]}
  ];
  var chipRefs = {};
  function buildFilters() {
    var host = document.getElementById("filters");
    groups.forEach(function (g) {
      var row = el("div", "fgroup");
      row.appendChild(el("div", "flabel", g.label));
      var chips = el("div", "chips");
      chips.setAttribute("role", "group");
      chips.setAttribute("aria-label", g.label);
      chipRefs[g.id] = [];
      g.opts.forEach(function (o) {
        var b = el("button", "chip");
        b.type = "button";
        b.dataset.v = o[0];
        b.appendChild(document.createTextNode(o[1]));
        var n = el("span", "n", "");
        b.appendChild(n);
        b.addEventListener("click", function () { state[g.id] = o[0]; apply(true); });
        chips.appendChild(b);
        chipRefs[g.id].push({b: b, n: n, v: o[0]});
      });
      row.appendChild(chips);
      host.appendChild(row);
    });
  }

  function renderPrompt(s, box) {
    box.textContent = "";
    var p = promptParts(s.k, state.frame, pos[s.k]);
    if (s.img) {
      box.appendChild(el("pre", "prompt", p.head));
      var im = el("img", "mimg");
      im.src = D.images[s.img];
      im.alt = "The picture sent with this message";
      box.appendChild(im);
      box.appendChild(el("p", "mcap", "Picture sent here: " + s.img + " (SHA-256 " + s.sha + ")"));
      box.appendChild(el("pre", "prompt", p.rest));
    } else {
      box.appendChild(el("pre", "prompt", p.head + "\n" + p.rest));
    }
  }

  function copyText(t, btn) {
    function done() { btn.textContent = "Copied"; setTimeout(function () { btn.textContent = "Copy text"; }, 1400); }
    try {
      navigator.clipboard.writeText(t).then(done, fallback);
    } catch (e) { fallback(); }
    function fallback() {
      var ta = el("textarea"); ta.value = t; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); done(); } catch (e2) { btn.textContent = "Select and copy"; }
      document.body.removeChild(ta);
    }
  }

  function setCard(s) {
    var card = el("article", "set");
    card.dataset.k = s.k;
    var head = el("header", "set-head");
    var h = el("h2", "set-title", s.title + (s.f !== "numbers" ? ", " + D.fmts[s.f].toLowerCase() : ""));
    h.appendChild(el("span", "code", " (" + s.code + ")"));
    head.appendChild(h);
    var tags = el("div", "tags");
    tags.appendChild(el("span", "tag", catLabel[s.cat]));
    tags.appendChild(el("span", "tag t" + s.t, D.tiers[String(s.t)]));
    tags.appendChild(el("span", "tag" + (s.f === "words" ? " fw" : s.f === "pictures" ? " fp" : ""), D.fmts[s.f] + (s.own ? ", own calibrated values" : "")));
    head.appendChild(tags);
    head.appendChild(el("p", "measure", s.measure));
    card.appendChild(head);

    var body = el("div", "set-body");
    var pp = el("section", "pane ppane");
    pp.appendChild(el("h3", "pane-title", "What a participant sees"));
    var screen = el("div", "screen");
    screen.appendChild(el("p", "stem", s.stem));
    if (s.img) {
      var pw = el("div", "picwrap");
      pw.setAttribute("role", "button");
      pw.setAttribute("tabindex", "0");
      pw.setAttribute("aria-label", "Picture of the options; select to zoom");
      var im = el("img");
      im.src = D.images[s.img];
      im.alt = "The options drawn as bars, as participants see them";
      pw.appendChild(im);
      var zoom = function () { pw.classList.toggle("zoom"); };
      pw.addEventListener("click", zoom);
      pw.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); zoom(); } });
      screen.appendChild(pw);
    }
    var opts = el("div", "opts");
    s.opts.forEach(function (o, i) {
      var w = el("div", "owrap");
      w.appendChild(el("span", "rtab " + o.rk, o.r));
      var c = el(o.u ? "div" : "label", "ocard" + (o.u ? " un" : ""));
      if (o.u) {
        c.setAttribute("aria-disabled", "true");
      } else {
        var inp = el("input", "vh");
        inp.type = "radio";
        inp.name = "choice-" + s.k;
        inp.addEventListener("change", function () {
          opts.querySelectorAll(".ocard").forEach(function (x) { x.classList.remove("sel"); });
          c.classList.add("sel");
        });
        c.appendChild(inp);
      }
      var b = el("div", "obody");
      b.innerHTML = o.h;
      c.appendChild(b);
      if (o.u) c.appendChild(el("span", "cfx-badge", "currently unavailable"));
      w.appendChild(c);
      if (o.b) w.appendChild(el("p", "behind", o.b));
      opts.appendChild(w);
    });
    screen.appendChild(opts);
    pp.appendChild(screen);
    pp.appendChild(el("p", "pnote", s.img ? "Every participant sees the picture sets in this one order." :
      "Each participant sees the options in a random order; this view keeps one fixed order."));
    pp.appendChild(el("p", "ids", "Stimulus id in the data file: " + s.id));
    body.appendChild(pp);

    var mp = el("section", "pane mpane");
    mp.appendChild(el("h3", "pane-title", "What a model receives"));
    var bar = el("div", "mbar");
    var box = el("div", "pbox");
    if (s.m.length > 1) {
      var st = el("div", "stepper");
      var prev = el("button", "", "\u2039"); prev.type = "button"; prev.setAttribute("aria-label", "Previous option order");
      var lab = el("span", "", "");
      var next = el("button", "", "\u203a"); next.type = "button"; next.setAttribute("aria-label", "Next option order");
      var upd = function () {
        lab.textContent = "Option order " + (pos[s.k] + 1) + " of " + s.m.length;
        prev.disabled = pos[s.k] === 0; next.disabled = pos[s.k] === s.m.length - 1;
        if (state.model) renderPrompt(s, box);
      };
      prev.addEventListener("click", function () { if (pos[s.k] > 0) { pos[s.k]--; upd(); } });
      next.addEventListener("click", function () { if (pos[s.k] < s.m.length - 1) { pos[s.k]++; upd(); } });
      st.appendChild(prev); st.appendChild(lab); st.appendChild(next);
      bar.appendChild(st);
      lab.textContent = "Option order 1 of " + s.m.length;
      prev.disabled = true;
    } else {
      bar.appendChild(el("span", "stepper", "One option order"));
    }
    var cp = el("button", "copy", "Copy text"); cp.type = "button";
    cp.addEventListener("click", function () { copyText(promptText(s.k, state.frame, pos[s.k]), cp); });
    bar.appendChild(cp);
    mp.appendChild(bar);
    mp.appendChild(box);
    mp.appendChild(el("p", "mnote", s.note));
    body.appendChild(mp);
    card.appendChild(body);
    card._box = box;
    return card;
  }

  function apply(push) {
    var shown = 0, stim = {};
    cards.forEach(function (c) {
      var s = byKey[c.dataset.k];
      var on = matches(s);
      c.hidden = !on;
      if (on) {
        shown++; stim[s.id] = 1;
        if (state.model) renderPrompt(s, c._box);
      }
    });
    groups.forEach(function (g) {
      chipRefs[g.id].forEach(function (r) {
        var n = 0;
        D.sets.forEach(function (s) {
          if (!matches(s, g.id)) return;
          if (r.v === "all" || (g.id === "cat" && s.cat === r.v) || (g.id === "str" && s.s === r.v) ||
              (g.id === "tier" && String(s.t) === r.v) || (g.id === "fmt" && s.f === r.v)) n++;
        });
        r.n.textContent = String(n);
        r.b.setAttribute("aria-pressed", String(state[g.id] === r.v));
        r.b.disabled = n === 0 && state[g.id] !== r.v;
      });
    });
    document.body.classList.toggle("show-roles", state.roles);
    document.body.classList.toggle("show-model", state.model);
    document.getElementById("count").textContent = "Showing " + shown + " of " + D.sets.length +
      " choice sets (" + Object.keys(stim).length + " of " + D.n_stimuli + " stimuli)";
    document.getElementById("empty").classList.toggle("on", shown === 0);
    document.querySelectorAll("#frame button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(+b.dataset.v === state.frame));
    });
    if (push) {
      var h = "cat=" + state.cat + "&str=" + state.str + "&tier=" + state.tier + "&fmt=" + state.fmt +
        "&roles=" + (state.roles ? 1 : 0) + "&model=" + (state.model ? 1 : 0) + "&frame=" + state.frame;
      try { history.replaceState(null, "", "#" + h); } catch (e) { }
    }
  }

  function readHash() {
    var h = (location.hash || "").replace(/^#/, "");
    h.split("&").forEach(function (kv) {
      var p = kv.split("="); if (p.length !== 2) return;
      var k = p[0], v = decodeURIComponent(p[1]);
      if (k === "roles" || k === "model") state[k] = v === "1";
      else if (k === "frame") { var f = parseInt(v, 10); if (f >= 1 && f <= 3) state.frame = f; }
      else if (k in state) state[k] = v;
    });
  }

  buildFilters();
  var list = document.getElementById("sets");
  D.sets.forEach(function (s) { var c = setCard(s); cards.push(c); list.appendChild(c); });
  readHash();
  var roles = document.getElementById("roles"), model = document.getElementById("model");
  roles.checked = state.roles; model.checked = state.model;
  roles.addEventListener("change", function () { state.roles = roles.checked; apply(true); });
  model.addEventListener("change", function () { state.model = model.checked; apply(true); });
  document.querySelectorAll("#frame button").forEach(function (b) {
    b.addEventListener("click", function () { state.frame = +b.dataset.v; apply(true); });
  });
  document.getElementById("reset").addEventListener("click", function () {
    state.cat = "all"; state.str = "all"; state.tier = "all"; state.fmt = "all"; apply(true);
  });
  document.getElementById("reset2").addEventListener("click", function () {
    state.cat = "all"; state.str = "all"; state.tier = "all"; state.fmt = "all"; apply(true);
  });
  var tf = document.getElementById("tofilters"), fl = document.getElementById("filters"), lastY = window.scrollY;
  function floatBtn() {
    var y = window.scrollY, up = y < lastY - 4, down = y > lastY + 4;
    if (fl.getBoundingClientRect().bottom >= 0 || down) tf.classList.remove("on");
    else if (up) tf.classList.add("on");
    if (up || down) lastY = y;
  }
  window.addEventListener("scroll", floatBtn, {passive: true});
  tf.addEventListener("click", function () { fl.scrollIntoView({behavior: "smooth", block: "start"}); });
  apply(false);
  floatBtn();
})();
"""

EXPLORER_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stimulus explorer</title>
<style>__CSS__</style>
</head>
<body class="show-roles">
<header class="top">
  <div class="wrap hero">
    <p class="eyebrow">Stimulus explorer</p>
    <h1>Every choice set in the study</h1>
    <p class="lede">All __NSTIM__ stimuli, shown as the survey shows them to participants, with each option's role and the exact text a language model receives for the same set in the study's main condition. This file works offline and makes no network requests.</p>
    <ul class="stats">
      <li><b>__NSTIM__</b>stimuli</li>
      <li><b>__NSETS__</b>choice sets shown</li>
      <li><b>13</b>product categories</li>
      <li><b>9</b>structures</li>
      <li><b>3</b>formats</li>
    </ul>
    <details class="about">
      <summary>How to read this page</summary>
      <ul>
        <li>Each card is one choice set: the question, then one card per option, as on the survey page. Selecting an option highlights it, as in the survey.</li>
        <li>The tabs above the options name each option's role for readers. Participants never saw them. The target is the option an added option is built to help; the competitor is its rival.</li>
        <li>Tier 1 keeps the two original options of each published study at their published values, with the added options rebuilt around them to the registered arrangement; tier 2 uses new values in the same published categories; tier 3 uses three categories no context-effect study has used.</li>
        <li>Formats: numbers (the main study), words (every value written out in words, except the 100 of a rating out of 100) and pictures (bars without numerals). Words and pictures versions exist for the baseline, frequency-decoy and compromise sets of four categories at tier 2; the hard-drives pictures sets were removed after calibration. The pictures sets for Bluetooth speakers and televisions have their own calibrated values, printed below each answer button.</li>
        <li>Options at tiers 2 and 3 carry a product name and a short description of each value; tier-1 options, the extremity sets and the price-free categories show the values alone. On the survey page each value and its description are separated by a long dash; this page prints a short dash.</li>
        <li>The similarity stimuli run twice, once with the clone of the budget option and once with the clone of the premium option, so __NSTIM__ stimuli give __NSETS__ sets with the words and pictures versions.</li>
        <li>Turn on the model text to see the message a model receives. It changes with the opening sentence (three registered wordings) and with the option order, which you can step through. For earbuds, restaurants, televisions and the three price-free categories, the opening also carries the explanatory sentence of the participants' question. This is the main condition; the study also sends each set with a persona sentence in front, inside seven-decision conversations, and as a question asking whether the set was built to steer the choice, and those versions add text to what is shown here.</li>
      </ul>
    </details>
  </div>
</header>
<div class="bar">
  <div class="wrap">
    <div class="filters" id="filters"></div>
  </div>
</div>
<div class="ctlbar">
  <div class="wrap controls">
    <label class="switch"><input type="checkbox" id="roles"><span class="track"></span>Option roles</label>
    <label class="switch"><input type="checkbox" id="model"><span class="track"></span>What a model receives</label>
    <span class="frame-ctl">Opening sentence <span class="seg" id="frame"><button type="button" data-v="1">1</button><button type="button" data-v="2">2</button><button type="button" data-v="3">3</button></span></span>
    <span class="count" id="count"></span>
    <button type="button" class="reset" id="reset">Clear filters</button>
  </div>
</div>
<button type="button" class="tofilters" id="tofilters">Filters</button>
<main class="wrap">
  <div id="sets"></div>
  <div class="empty" id="empty">No choice set matches these filters. <button type="button" class="reset" id="reset2">Clear filters</button></div>
</main>
<footer class="wrap">Values, names and descriptions are printed from the study's stimulus file by the code that writes the survey pages; the model text is composed by the code that sends the model requests.</footer>
<script type="application/json" id="stimulus-data">__DATA__</script>
<script>__JS__</script>
</body>
</html>
"""

INTERNAL = re.compile(r"\block(ed|s)?\b|\bHF\b|\bHD\b|localhost|https?://|TODO|FIXME", re.I)


def strip_pictures(page_html):
    out, n = re.subn(r"data:image/png;base64,[A-Za-z0-9+/=]+", "data:image/png;base64,[PNG]", page_html)
    if n != 9:
        refuse(f"expected the 9 registered pictures embedded once each, found {n} picture payloads")
    return out


def build_explorer(sets, focal):
    data, keymap = explorer_data(sets, focal)
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page_html = (EXPLORER_HTML.replace("__CSS__", EXPLORER_CSS.strip()).replace("__JS__", EXPLORER_JS.strip())
                 .replace("__NSTIM__", str(data["n_stimuli"])).replace("__NSETS__", str(len(data["sets"])))
                 .replace("__DATA__", blob))
    # checks on the page itself: no em or en dash, no code name, link or unfinished marker in the text
    probs = []
    if EM in page_html or EN in page_html:
        probs.append("em or en dash")
    text_only = strip_pictures(page_html)       # picture bytes are not text; words are scanned everywhere else
    for m in INTERNAL.finditer(text_only):
        probs.append(f"code name or link {m.group(0)!r} near {text_only[max(0, m.start() - 30):m.end() + 30]!r}")
    if re.search(r"/\*|<!--|(^|[^:\"'\\])//", EXPLORER_JS + EXPLORER_CSS + EXPLORER_HTML):
        probs.append("a code comment in the page source")
    if probs:
        refuse("explorer:\n  " + "\n  ".join(probs[:20]))
    os.makedirs(OFFLINE_DIR, exist_ok=True)
    extra = []
    if extra:
        refuse(f"the offline folder must hold only the explorer; it also holds {extra}")
    with open(EXPLORER, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page_html)
    return data, page_html, keymap


EXPLORER_EXTRACT_JS = r"""
() => {
  const out = [];
  document.querySelectorAll('.set').forEach(c => {
    c.querySelectorAll('.owrap').forEach((w, i) => {
      const card = w.querySelector('.ocard');
      const badge = w.querySelector('.cfx-badge');
      const behind = w.querySelector('.behind');
      out.push({set: c.dataset.k, idx: i, tab: w.querySelector('.rtab').innerText,
        lines: [...w.querySelectorAll('.obody .cfx-attr')].map(e => e.innerText),
        un: card.classList.contains('un'), badge: badge ? badge.innerText : null,
        behind: behind ? behind.innerText : null});
    });
  });
  return out;
}
"""


def test_explorer(sets, focal, data, keymap):
    """Open the file as a reviewer would (file://, network blocked and recorded), then prove: every set and
    option is printed as stimuli.json says, the composed model text equals the runner's for every frame and
    order, the filters and toggles work, nothing scrolls sideways on a phone; save screenshots."""
    from playwright.sync_api import sync_playwright
    os.makedirs(SHOTS_DIR, exist_ok=True)
    url = "file:///" + EXPLORER.replace("\\", "/")
    by_key = {k: next(d for d in sets if d["key"] == v) for k, v in keymap.items()}
    rev = {v: k for k, v in keymap.items()}
    report = {}
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        ctx = br.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
        requests = []
        ctx.route("**/*", lambda route: route.continue_() if route.request.url.startswith(("file:", "data:"))
                  else route.abort())
        pg = ctx.new_page()
        pg.on("request", lambda r: requests.append(r.url))
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.goto(url)
        pg.wait_for_load_state("load")
        external = [u for u in requests if not u.startswith(("file:", "data:"))]
        if external or errors:
            refuse(f"explorer: network requests {external[:3]} or page errors {errors[:3]}")
        n_sets = pg.evaluate("document.querySelectorAll('.set').length")
        if n_sets != 203:
            refuse(f"explorer shows {n_sets} sets, not 203")
        recs = pg.evaluate(EXPLORER_EXTRACT_JS)
        errs, printed = [], {}
        for r in recs:
            d = by_key[r["set"]]
            opt = d["options"][r["idx"]]
            errs += check_option_record(d, opt, r["idx"], r, focal)
            printed[r["set"]] = printed.get(r["set"], 0) + 1
        for d in sets:
            if printed.get(rev[d["key"]]) != len(d["options"]):
                errs.append(f"{d['key']}: {printed.get(rev[d['key']])} options printed for {len(d['options'])}")
        # the composed model text, every set, frame and order, against the runner
        texts = pg.evaluate("""() => { const X = window.stimulusExplorer, out = {};
            X.keys().forEach(k => { out[k] = []; for (let f = 1; f <= 3; f++) for (let i = 0; i < X.orders(k); i++)
              out[k].push(X.promptText(k, f, i)); }); return out; }""")
        n_prompts = 0
        for k, got in texts.items():
            d = by_key[k]
            orders = RUN.orders_for_delivery(d["fmt"], len(d["options"]), d["stim"]["id"])
            want = [RUN.build_prompt(d["stim"], d["cat"], o, f, d["fmt"], d["options"], d["words"])[0]
                    for f in (1, 2, 3) for o in orders]
            n_prompts += len(want)
            if got != want:
                errs.append(f"{k}: composed model text differs from the runner's")
        if errs:
            br.close()
            refuse("explorer:\n  " + "\n  ".join(errs[:20]))
        report["prompts_checked"] = n_prompts
        report["options_checked"] = len(recs)
        # the visible model pane equals the runner's text
        pg.goto(url + "#cat=bluetooth_speakers&str=FRQ&tier=2&fmt=numbers&roles=1&model=1&frame=2")
        pg.reload()
        pg.wait_for_load_state("load")
        vis = pg.evaluate("[...document.querySelectorAll('.set')].filter(c => !c.hidden).map(c => c.dataset.k)")
        if [keymap[v] for v in vis] != ["FRQ_bluetooth_speakers_t2|numbers|"]:
            refuse(f"explorer: filters show {[keymap[v] for v in vis]}")
        # every filter value shows exactly the sets it names
        for field, values in (("cat", APPENDIX_ORDER), ("str", STRUCT_ORDER), ("tier", ["1", "2", "3"]),
                              ("fmt", ["numbers", "words", "pictures"])):
            for v in values:
                h = {"cat": "all", "str": "all", "tier": "all", "fmt": "all"}
                h[field] = v
                pg.goto(url + "#" + "&".join(f"{a}={b}" for a, b in h.items()))
                pg.reload()
                pg.wait_for_load_state("load")
                got = sorted(keymap[x] for x in pg.evaluate(
                    "[...document.querySelectorAll('.set')].filter(c => !c.hidden).map(c => c.dataset.k)"))
                want = sorted(d["key"] for d in sets if {"cat": d["cat"]["id"], "str": d["stim"]["structure"],
                                                          "tier": str(d["stim"]["memorization_tier"]),
                                                          "fmt": d["fmt"]}[field] == v)
                if got != want:
                    refuse(f"explorer: filter {field}={v} shows {len(got)} sets, expected {len(want)}")
        report["filters_checked"] = len(APPENDIX_ORDER) + len(STRUCT_ORDER) + 6
        pg.goto(url + "#cat=bluetooth_speakers&str=FRQ&tier=2&fmt=numbers&roles=1&model=1&frame=2")
        pg.reload()
        pg.wait_for_load_state("load")
        vis = pg.evaluate("[...document.querySelectorAll('.set')].filter(c => !c.hidden).map(c => c.dataset.k)")
        d = by_key[vis[0]]
        pg.click(".set:not([hidden]) .stepper button[aria-label='Next option order']")
        shown = pg.inner_text(".set:not([hidden]) .pbox pre")
        want = RUN.build_prompt(d["stim"], d["cat"], RUN.orders_for_delivery("numbers", 3, d["stim"]["id"])[1], 2, "numbers",
                                d["options"], None)[0]
        if shown != want:
            refuse(f"explorer: the visible model text differs from the runner's:\n{shown}\n---\n{want}")
        pg.screenshot(path=os.path.join(SHOTS_DIR, "explorer_desktop_model_text.png"), full_page=False)
        # the visible pane where the opening carries the participants' explanatory sentence (frame 3: two lines),
        # for a text set and for a picture set (opening, then the picture, then the option lines)
        for h, want_key in (("#cat=earbuds&str=SIM&tier=2&fmt=numbers&roles=1&model=1&frame=3",
                             "SIM_earbuds_t2|numbers|clone_HF"),
                            ("#cat=televisions&str=FRQ&tier=2&fmt=pictures&roles=1&model=1&frame=3",
                             "FRQ_televisions_t2|pictures|")):
            pg.goto(url + h)
            pg.reload()
            pg.wait_for_load_state("load")
            card = next(c for c in pg.query_selector_all(".set:not([hidden])")
                        if keymap[c.get_attribute("data-k")] == want_key)
            pres = [e.inner_text() for e in card.query_selector_all(".pbox pre")]
            d = by_key[rev[want_key]]
            order = RUN.orders_for_delivery(d["fmt"], len(d["options"]), d["stim"]["id"])[0]
            want = RUN.build_prompt(d["stim"], d["cat"], order, 3, d["fmt"], d["options"], d["words"])[0]
            head, rest = RUN.split_head(want)
            if RUN.stem_explanation(d["stim"]) not in want:
                refuse(f"explorer check: {want_key} was expected to carry an explanatory sentence")
            got = pres if d["fmt"] == "pictures" else ["\n".join(pres)]
            exp = [head, rest] if d["fmt"] == "pictures" else [want]
            if got != exp or (d["fmt"] == "pictures" and not card.query_selector(".pbox img.mimg")):
                refuse(f"explorer: visible model text for {want_key} differs from the runner's:\n{got}\n---\n{exp}")
        report["visible_explanation_checks"] = 2
        shots = [
            ("explorer_desktop_top.png", "", 1280, 900, False),
            ("explorer_desktop_pictures_model.png", "#cat=televisions&str=SOT&tier=2&fmt=pictures&roles=1&model=1&frame=1", 1280, 900, False),
            ("explorer_desktop_extremity.png", "#cat=backpacks&str=MOT&tier=1&fmt=all&roles=1&model=0&frame=1", 1280, 900, True),
            ("explorer_desktop_phantom_words.png", "#cat=bluetooth_speakers&str=all&tier=2&fmt=words&roles=1&model=0&frame=1", 1280, 900, False),
        ]
        for name, h, w, hgt, full in shots:
            pg.set_viewport_size({"width": w, "height": hgt})
            pg.goto(url + h)
            pg.reload()
            pg.wait_for_load_state("load")
            if name == "explorer_desktop_top.png":
                pass
            elif "extremity" in name:
                pg.evaluate("window.scrollTo(0, document.querySelector('.set:not([hidden])').offsetTop - 180)")
            else:
                pg.evaluate("window.scrollTo(0, document.querySelector('.set:not([hidden])').offsetTop - 150)")
            pg.screenshot(path=os.path.join(SHOTS_DIR, name), full_page=full)
        ctx.close()
        # phone width
        ph = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
        ph.route("**/*", lambda route: route.continue_() if route.request.url.startswith(("file:", "data:")) else route.abort())
        pp = ph.new_page()
        wide = {}
        for name, h in [("explorer_phone_top.png", ""),
                        ("explorer_phone_model.png", "#cat=earbuds&str=SIM&tier=2&fmt=numbers&roles=1&model=1&frame=1"),
                        ("explorer_phone_pictures.png", "#cat=bluetooth_speakers&str=FRQ&tier=2&fmt=pictures&roles=1&model=1&frame=1"),
                        ("explorer_phone_phantom.png", "#cat=standing_desks&str=PHT&tier=all&fmt=all&roles=1&model=0&frame=1"),
                        ("explorer_phone_extremity.png", "#cat=robot_vacuums&str=MOT&tier=all&fmt=all&roles=1&model=0&frame=1")]:
            pp.goto(url + h)
            pp.reload()
            pp.wait_for_load_state("load")
            sw = pp.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
            wide[name] = sw
            if sw[0] > sw[1]:
                br.close()
                refuse(f"explorer scrolls sideways at phone width ({sw}) on {name}")
            if h:
                pp.evaluate("window.scrollTo(0, document.querySelector('.set:not([hidden])').offsetTop - 120)")
            pp.screenshot(path=os.path.join(SHOTS_DIR, name), full_page=False)
        # all sets rendered at phone width: no card wider than the screen
        pp.goto(url)
        pp.reload()
        pp.wait_for_load_state("load")
        pp.check("#model", force=True)
        over = pp.evaluate("""() => [...document.querySelectorAll('.set, .ocard, .prompt, .screen')]
            .filter(e => e.getBoundingClientRect().right > window.innerWidth + 0.5).length""")
        sw = pp.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        if over or sw[0] > sw[1]:
            br.close()
            refuse(f"explorer: {over} boxes wider than a phone screen with every set and the model text shown ({sw})")
        cut = pp.evaluate("""() => [...document.querySelectorAll('.rtab')]
            .filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.textContent)""")
        if cut:
            br.close()
            refuse(f"explorer: role tabs cut off at phone width: {cut[:4]}")
        report["phone_widths"] = wide
        br.close()
    return report


# ---------------------------------------------------------------------------------------------------
# selftest: the checks must refuse planted errors
# ---------------------------------------------------------------------------------------------------
def selftest(sets, focal):
    from playwright.sync_api import sync_playwright
    import copy
    plan = figure_plan(sets)
    f = next(x for x in plan if x["kind"] == "tier" and x["cid"] == "bluetooth_speakers" and x["tier"] == 2)
    f5 = next(x for x in plan if x["kind"] == "formats1" and x["cid"] == "bluetooth_speakers")
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        pg = br.new_page(viewport={"width": FIG_W_PX + 40, "height": 1200})
        page_html, used = build_figure_html(f, sets, focal)
        pg.set_content(page_html)
        clean = pg.evaluate(EXTRACT_JS, ".fig")
        page5, used5 = build_figure_html(f5, sets, focal)
        pg.set_content(page5)
        clean5 = pg.evaluate(EXTRACT_JS, ".fig")
        # a page whose text is too small and whose tab spills out of its card
        bad_css = page_html.replace(".cfx-attr{font-size:9px", ".cfx-attr{font-size:7.5px").replace(
            "white-space:nowrap}", "white-space:nowrap;width:400px}")
        pg.set_content(bad_css)
        small = pg.evaluate(EXTRACT_JS, ".fig")
        tall = page_html.replace("<div class='key'>", "<div class='key' style='margin-bottom:300px'>")
        pg.set_content(tall)
        tall_rec = pg.evaluate(EXTRACT_JS, ".fig")
        br.close()

    def mutate(rec, fn):
        r = copy.deepcopy(rec)
        fn(r)
        return r

    def opt_of(r, key, code):
        return next(o for o in r["opts"] if o["set"] == key and o["code"] == code)

    k_frq = "FRQ_bluetooth_speakers_t2|numbers|"
    k_sot = "SOT_bluetooth_speakers_t2|numbers|"
    k_pht = "PHT_bluetooth_speakers_t2|numbers|"
    k_words = "FRQ_bluetooth_speakers_t2|words|"
    k_pic = "BIN_bluetooth_speakers_t2|pictures|"
    cases = [
        ("a price one cent off", clean, used, lambda r: opt_of(r, k_frq, "HF")["lines"].__setitem__(2, opt_of(r, k_frq, "HF")["lines"][2].replace("$44.99", "$44.98"))),
        ("a rating changed", clean, used, lambda r: opt_of(r, k_sot, "HD")["lines"].__setitem__(1, opt_of(r, k_sot, "HD")["lines"][1].replace("4.7", "4.8"))),
        ("a description swapped", clean, used, lambda r: opt_of(r, k_frq, "DECOY")["lines"].__setitem__(1, "4.1 stars - a favorite among reviewers")),
        ("a product name changed", clean, used, lambda r: opt_of(r, k_frq, "HD")["lines"].__setitem__(0, "NimbusSound Speaker")),
        ("target and competitor tabs swapped", clean, used, lambda r: (opt_of(r, k_frq, "HF").__setitem__("tab", "COMPETITOR \u00b7 BUDGET"), opt_of(r, k_frq, "HD").__setitem__("tab", "TARGET \u00b7 PREMIUM"))),
        ("the compromise target not called the middle", clean, used, lambda r: opt_of(r, k_sot, "HD").__setitem__("tab", "TARGET \u00b7 PREMIUM")),
        ("a decoy called a range decoy", clean, used, lambda r: opt_of(r, k_frq, "DECOY").__setitem__("tab", "RANGE DECOY")),
        ("the budget card under the premium column", clean, used, lambda r: opt_of(r, k_frq, "HF").__setitem__("col", "PREMIUM OPTION")),
        ("an option dropped", clean, used, lambda r: r["opts"].remove(opt_of(r, k_frq, "DECOY"))),
        ("the phantom shown as available", clean, used, lambda r: opt_of(r, k_pht, "PHANTOM").__setitem__("un", False)),
        ("the unavailable tag missing", clean, used, lambda r: opt_of(r, k_pht, "PHANTOM").__setitem__("badge", None)),
        ("an em dash printed", clean, used, lambda r: r.__setitem__("text", r["text"] + " \u2014 ")),
        ("a spelled price one cent off", clean5, used5, lambda r: opt_of(r, k_words, "HF")["lines"].__setitem__(2, opt_of(r, k_words, "HF")["lines"][2].replace("ninety-nine cents", "ninety-eight cents"))),
        ("a spelled rating changed", clean5, used5, lambda r: opt_of(r, k_words, "HD")["lines"].__setitem__(1, opt_of(r, k_words, "HD")["lines"][1].replace("seven", "six"))),
        ("a value behind the bars changed", clean5, used5, lambda r: opt_of(r, k_pic, "HF").__setitem__("behind", "Values behind the bars: 4.2 stars, $44.99")),
        ("the text under 6 pt and a tab wider than its card", small, used, lambda r: None),
        ("the figure taller than 9 inches", tall_rec, used, lambda r: None),
    ]
    ok = True
    base_errs = check_page_record(clean, used, focal) + check_page_record(clean5, used5, focal)
    print(f"  clean pages: {len(base_errs)} failures (must be 0)")
    ok &= not base_errs
    for name, rec, u, fn in cases:
        errs = check_page_record(mutate(rec, fn), u, focal)
        print(f"  planted: {name:<48} refused: {'yes' if errs else 'NO'}" + (f"  ({errs[0][:90]})" if errs else ""))
        ok &= bool(errs)
    # a design error: the decoy placed so the competitor, not the target, dominates it
    d = copy.deepcopy(next(x for x in sets if x["key"] == k_frq))
    d["target"], d["competitor"] = d["competitor"], d["target"]
    g = check_geometry(d)
    print(f"  planted: {'target and competitor swapped in the design':<48} refused: {'yes' if g else 'NO'}")
    ok &= bool(g)
    # the words reader and the price reader are independent of the writers
    probes = [("forty-four dollars and ninety-nine cents", 44.99), ("one hundred nine dollars", 109.0),
              ("four point two stars", 4.2), ("seventy-eight out of 100", 78.0), ("one thousand one hundred four", 1104.0),
              ("one hundred sixty-six dollars and sixty cents", 166.6)]
    rd = all(abs(spelled_value(t) - v) < 1e-9 for t, v in probes)
    rd &= printed_value("$1,099.98 - a step up") == 1099.98 and printed_value("11,076 reviews") == 11076.0
    print(f"  value readers read known strings correctly: {'yes' if rd else 'NO'}")
    ok &= rd
    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return 0 if ok else 1


# ---------------------------------------------------------------------------------------------------
DATA, CATS, FIG_NO = None, None, {}


def main(argv):
    global DATA, CATS
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--figures-only", action="store_true")
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--draft", action="store_true", help="save figures with their errors to a scratch folder")
    a = ap.parse_args(argv[1:])
    DATA, CATS = load()
    focal = focal_words(DATA, CATS)
    sets = build_sets(DATA, CATS)
    geo = [e for d in sets for e in check_geometry(d)]
    if geo:
        refuse("design geometry:\n  " + "\n  ".join(geo[:20]))
    if a.selftest:
        return selftest(sets, focal)
    print(f"{len(sets)} choice sets from {len({d['stim']['id'] for d in sets})} stimuli; design geometry holds for all")
    print("Figures:")
    results = render_figures(sets, focal, only=a.only, draft=a.draft)
    if a.figures_only or a.only or a.draft:
        return 0
    print("Explorer:")
    data, page_html, keymap = build_explorer(sets, focal)
    print(f"  wrote {EXPLORER} ({len(page_html.encode('utf-8')) / 1e6:.2f} MB, {len(data['sets'])} sets)")
    rep = test_explorer(sets, focal, data, keymap)
    print(f"  opened offline with the network blocked: 0 requests beyond the file; {rep['options_checked']} "
          f"printed options checked against stimuli.json; {rep['prompts_checked']} composed model texts equal "
          f"the runner's; {rep['filters_checked']} filter values show exactly their sets; no sideways "
          f"scrolling and no cut-off role tab at 390 px")
    os.makedirs(READY, exist_ok=True)
    json.dump([{k: v for k, v in r.items() if k != "pages"} | {"sets": r["pages"]} for r in results],
              open(os.path.join(READY, "figure_manifest.json"), "w", encoding="utf-8"), indent=1)
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Refused as e:
        print("REFUSED: " + str(e))
        sys.exit(1)
