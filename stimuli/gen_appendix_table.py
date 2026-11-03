"""gen_appendix_table.py: write the stimulus tables of Web Appendix B from stimuli/stimuli.json.

One table per product category lists every option once: one row per option (the budget and premium options,
each added option, the middle tier of the extremity menu) and one group of columns per stimulus tier, with the
product name in its own column at tiers 2 and 3, then the premium option's share in the pre-test. The price-free
categories and the pictures values of Bluetooth speakers and televisions have their own small tables. A cell
holding only "<" joins the cell on its left in the Word document. Every value is read from the stimulus file
the surveys and the model prompts use, and then read back from the printed tables option by option, so the
appendix cannot disagree with what participants and models see. The script stops when one table row would need
two values, when a printed value, name, target mark or share differs from the stimulus file, or when an option
of the stimulus file has no row.

Output: stimuli/STIMULUS_APPENDIX.md, the stimulus tables exactly as Web Appendix B prints them.

Run: python stimuli/gen_appendix_table.py
     python stimuli/gen_appendix_table.py --selftest   (shows the checks stop planted errors)
"""
import argparse
import copy
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
STIM = os.path.join(HERE, "stimuli.json")
OUT = os.path.join(HERE, "STIMULUS_APPENDIX.md")
WEB_APPENDIX = os.path.normpath(os.path.join(HERE, "..", "..", "web_appendices", "web_appendix.md"))

MERGE = "<"
TIER_HEAD = {1: "Tier 1: published values", 2: "Tier 2: new values", 3: "Tier 3: invented category"}
DECOYS = ("FRQ", "RNG", "PHT")              # the structures whose target is counterbalanced
# one row per option role, in this order; HF and HD are labeled per category (budget/premium, or the attribute
# each leads on in a price-free category)
ROWS = [("HF", None), ("HD", None), ("DECOY", "Frequency decoy"), ("RANGE_DECOY", "Range decoy"),
        ("PHANTOM", "Phantom (shown as unavailable)"), ("EXTREME", "New extreme (compromise)"),
        ("SYM_DECOY", "Symmetric decoy (upscaling)"), ("CLONE_HF", "Clone of the budget option"),
        ("CLONE_HD", "Clone of the premium option"), ("MIDDLE", "Extremity menu, middle tier")]
# the extremity menu and its control: the high and low tiers must have the premium and budget options' values
TIER_ROLE = {"High": "HD", "Middle": "MIDDLE", "Low": "HF"}
# the short unit printed after an attribute's name in the column heading (None: no unit is printed)
UNIT_SHORT = {"liters (L)": "L", "stars (Amazon, out of 5)": "stars", "number of customer reviews": None,
              "watts": "W", "TB": "TB", "MB/s": "MB/s", "0-100 overall rating (Consumer Reports)": "of 100",
              "0-100": "of 100", "0-100 expert scale": "of 100", "Pa": "Pa", "lbs": "lbs", "oz": "oz"}
STATUS = {"LOCK": "final", "RUN_WITH_DEVIATION": "retained", "EXIT": "removed", "CHECK_ONLY": "checked only"}
SHARE_LABEL = {"numbers": "Premium option's share in the pre-test",
               "words": "Premium option's share in the pre-test, words version",
               "pictures": "Premium option's share in the pre-test, pictures version"}


class Refused(Exception):
    pass


def refuse(msg):
    raise Refused(msg)


# ---------------------------------------------------------------------------------------------------
# reading the stimulus file
# ---------------------------------------------------------------------------------------------------
def is_price(a):
    return a["name"] == "price"


def attr_head(a):
    if is_price(a):
        return "Price"
    if a["unit"] not in UNIT_SHORT:
        refuse(f"no short unit for {a['name']} ({a['unit']!r}); add it to UNIT_SHORT")
    u = UNIT_SHORT[a["unit"]]
    name = a["name"].replace("_", " ")
    return name[0].upper() + name[1:] + (f" ({u})" if u else "")


def fmt_value(a, v):
    if is_price(a):
        return f"${float(v):,.2f}"
    f = float(v)
    return f"{int(f):,}" if f == int(f) else f"{f:g}"


def read_value(cell):
    """A printed value read back to a number, without the writer's code."""
    m = re.fullmatch(r"\$?([0-9][0-9,]*(?:\.[0-9]+)?)", cell.strip())
    if not m:
        raise ValueError(cell)
    return float(m.group(1).replace(",", ""))


def role_key(s, o):
    if s["structure"] in ("MOT", "EXC"):
        return TIER_ROLE[o["tier"]]
    return ("CLONE_" + o["clone_of"]) if o["code"] == "CLONE" else o["code"]


def numbers_options(s):
    """Every option a numbers-format set of this stimulus shows (the second similarity placement included)."""
    out = list(s["options"])
    for pv in (s.get("placement_variants") or {}).values():
        out += pv["options"]
    return out


def model(d):
    """Everything the tables print, per category, collected row by row; refuses when one row cannot hold a
    role because the role has two different values within one tier."""
    enr = d["enrichment"]
    by = defaultdict(list)
    for s in d["stimuli"]:
        by[s["category"]].append(s)
    # which option each recorded calibration share belongs to (as ingest.load_stimuli reads it)
    cal_focal = {}
    for s in d["stimuli"]:
        if s["structure"] != "BIN" and s.get("target"):
            cal_focal.setdefault(s["category"], s["target"])
    cats = []
    for c in d["categories"]:
        stims = by[c["id"]]
        tiers = sorted({s["memorization_tier"] for s in stims})
        stems = {s["stem"] for s in stims}
        if len(stems) != 1:
            refuse(f"{c['id']}: the sets carry {len(stems)} different questions; one table prints one")
        values = {t: {} for t in tiers}
        for s in stims:
            for o in numbers_options(s):
                k, t = role_key(s, o), s["memorization_tier"]
                old = values[t].setdefault(k, o["attrs"])
                if old != o["attrs"]:
                    refuse(f"{s['id']}: {k} has the values {o['attrs']} here and {old} elsewhere at tier {t}; "
                           "one row cannot hold both")
                if (k == "PHANTOM") == o.get("available", True):
                    refuse(f"{s['id']}: option {o['code']} is {'available' if o.get('available', True) else 'unavailable'}, "
                           "and only the phantom is shown as unavailable")
        # the targets the row labels claim
        target = {}
        for t in tiers:
            ts = {s["target"] for s in stims if s["memorization_tier"] == t and s["structure"] in DECOYS}
            if len(ts) != 1:
                refuse(f"{c['id']} tier {t}: the decoys target {sorted(ts)}; one label cannot say which")
            target[t] = ts.pop()
            for s in stims:
                if s["memorization_tier"] == t and s["structure"] in ("SOT", "SYM") and s["target"] != "HD":
                    refuse(f"{s['id']}: the target is {s['target']}; the table assumes the premium option")
                if s["memorization_tier"] == t and s["structure"] == "SIM":
                    variants = [(s["target"], s["options"])] + [(pv["target"], pv["options"])
                                                                for pv in (s.get("placement_variants") or {}).values()]
                    for tg, opts in variants:
                        if any(o.get("clone_of") == tg for o in opts):
                            refuse(f"{s['id']}: the cloned option is the target; the note says the target has no clone")
        named = [t for t in tiers if t in enr["scope"]["tiers"] and c["id"] in enr["by_category"]]
        # shares in the pre-test, per format and tier
        shares = {}
        for s in stims:
            if s["structure"] == "BIN" and s.get("calibration"):
                for fmt, rec in s["calibration"]["arms"].items():
                    shares[(fmt, s["memorization_tier"])] = share_text(c["id"], cal_focal.get(c["id"]), rec, s["id"])
        # format versions (tier 2 only, baseline, frequency decoy, compromise)
        words = [s for s in stims if "words" in (s.get("format_variants") or {})]
        pics = [s for s in stims if "pictures" in (s.get("format_variants") or {})]
        fmt = None
        if words:
            if {s["structure"] for s in words} != {"BIN", "FRQ", "SOT"} or {s["memorization_tier"] for s in words} != {2}:
                refuse(f"{c['id']}: the words version is not the tier-2 baseline, frequency decoy and compromise")
            for s in words:
                if [w["code"] for w in s["format_variants"]["words"]] != [o["code"] for o in s["options"]]:
                    refuse(f"{s['id']}: the words version shows other options than the numbers version")
            pic_values = {}
            for s in pics:
                for o in s["format_variants"]["pictures"]["options"]:
                    old = pic_values.setdefault(o["code"], o["attrs"])
                    if old != o["attrs"]:
                        refuse(f"{s['id']}: pictures option {o['code']} differs between sets")
            if pics and {s["id"] for s in pics} != {s["id"] for s in words}:
                refuse(f"{c['id']}: the pictures sets are not the words sets")
            own = any(s["format_variants"]["pictures"].get("per_format_values") for s in pics)
            if pics and not own and any(pic_values[k] != values[2][k] for k in pic_values):
                refuse(f"{c['id']}: the pictures values differ from tier 2 but are not marked as their own")
            if not pics and ("pictures", 2) in shares and not shares[("pictures", 2)].endswith("removed"):
                refuse(f"{c['id']}: no pictures sets, but the pictures pair was not removed")
            bin_words = next(s for s in words if s["structure"] == "BIN")["format_variants"]["words"]
            hf_words = next(w for w in bin_words if w["code"] == "HF")["words"]
            spelled = [v for w in bin_words for v in w["words"].values()]
            digits = sorted({x for v in spelled for x in re.findall(r"\d+", v)})
            if digits not in ([], ["100"]) or any(re.search(r"\d", v) and not v.endswith("out of 100") for v in spelled):
                refuse(f"{c['id']}: the words version prints digits other than the 100 of 'out of 100': {digits}")
            example = hf_words[c["attributes"][0]["name"]]
            fmt = dict(example=example, keeps_100=bool(digits), pictures=bool(pics), own=own,
                       pic_values=pic_values)
        cats.append(dict(cat=c, tiers=tiers, stem=stems.pop(), values=values, target=target, named=named,
                         shares=shares, fmt=fmt, stims=stims, cal_focal=cal_focal.get(c["id"])))
    return cats


def share_text(cid, focal, rec, sid):
    """The premium option's share in the pre-test, its interval, the sample and the outcome. A share recorded for
    the budget option (the electric kettles and the standing desks) is printed as its complement, with the
    complementary interval, which is exact."""
    w = rec.get("wave3") or rec.get("wave1") or {}
    if w.get("target_share_pct") is not None:
        share, (lo, hi), n, k = w["target_share_pct"], w["wilson95"], w["n"], w.get("k_target")
    else:
        m = re.search(r"\((\d+(?:\.\d+)?)% \[(\d+(?:\.\d+)?), (\d+(?:\.\d+)?)\], n=(\d+), wave \d", rec.get("disposition") or "")
        if not m:
            refuse(f"{sid}: no recorded share in the calibration record")
        share, lo, hi, n, k = float(m.group(1)), float(m.group(2)), float(m.group(3)), int(m.group(4)), None
    if focal != "HD":
        if focal != "HF":
            refuse(f"{sid}: the recorded share belongs to {focal!r}")
        comp = 100.0 * (n - k) / n if k is not None else 100.0 - share
        if abs(comp - (100.0 - share)) > 0.051:
            refuse(f"{sid}: the complement of the recorded share disagrees with its count")
        share, lo, hi = 100.0 - share, 100.0 - hi, 100.0 - lo
    if rec.get("status") not in STATUS:
        refuse(f"{sid}: unknown calibration status {rec.get('status')!r}")
    return f"{share:.1f}% [{lo:.1f}, {hi:.1f}], n = {n}; {STATUS[rec['status']]}"


# ---------------------------------------------------------------------------------------------------
# writing the tables
# ---------------------------------------------------------------------------------------------------
def focal_label(m, code, tiers=None):
    cat = m["cat"]
    if cat["price_free"]:
        a = cat["attributes"][0 if code == "HD" else 1]
        base = "Option with the higher " + a["name"].replace("_", " ")
    else:
        base = "Budget option" if code == "HF" else "Premium option"
    tiers = tiers or m["tiers"]
    on = [t for t in tiers if m["target"][t] == code]
    if not on:
        return base
    if len(on) == len(tiers):
        return base + " (target of the decoys)"
    return base + " (target of the decoys at tier " + " and ".join(str(t) for t in on) + ")"


def row(cells):
    return "| " + " | ".join(cells) + " |"


def main_table(m, n_table):
    cat, attrs = m["cat"], m["cat"]["attributes"]
    head, sub, groups = ["Option"], [""], []
    for t in m["tiers"]:
        cols = (["Name"] if t in m["named"] else []) + [attr_head(a) for a in attrs]
        head += [TIER_HEAD[t]] + [MERGE] * (len(cols) - 1)
        sub += cols
        groups.append((t, len(cols)))
    if cat["price_free"]:
        title = f"{cat['label'].split(' (')[0].upper()} WITHOUT PRICES: EVERY OPTION"
    elif len(m["tiers"]) == 2:
        title = f"{cat['label'].upper()}: EVERY OPTION, BOTH TIERS"
    else:
        title = f"{cat['label'].upper()}: EVERY OPTION"
    lines = [f"**TABLE WA-B{n_table}.** {title}", "", f"*Question above every set:* \"{m['stem']}\"", "",
             row(head), "|" + "---|" * len(head), row(sub)]
    enr = DATA["enrichment"]["by_category"].get(cat["id"], {})
    for key, label in ROWS:
        if not any(key in m["values"][t] for t in m["tiers"]):
            continue
        cells = [label or focal_label(m, key)]
        for t, _ in groups:
            v = m["values"][t].get(key)
            if t in m["named"]:
                cells.append(enr[key]["name"] if (v is not None and key != "MIDDLE") else "")
            cells += [fmt_value(a, v[a["name"]]) if v is not None else "" for a in attrs]
        lines.append(row(cells))
    for fmt in ("numbers", "words", "pictures"):
        if not any((fmt, t) in m["shares"] for t in m["tiers"]):
            continue
        cells = [SHARE_LABEL[fmt]]
        for t, width in groups:
            cells += [m["shares"].get((fmt, t), "")] + [MERGE] * (width - 1)
        lines.append(row(cells))
    return "\n".join(lines)


def format_line(m, pic_table):
    f = m["fmt"]
    spelled = ("every number written out except the 100 of a rating out of 100" if f["keeps_100"]
               else "every number written out")
    if not f["pictures"]:
        pics = "; the pictures version was removed after the pre-test"
    elif f["own"]:
        pics = f", and in pictures, with values of their own (Table WA-B{pic_table})"
    else:
        pics = ", and in pictures, at the values of tier 2"
    return (f"*Format module:* the baseline, frequency-decoy and compromise sets are also shown in words, with the "
            f"names, descriptions and values of tier 2 and {spelled} (\"{f['example']}\"){pics}.")


def pictures_table(m, n_table):
    cat, attrs, f = m["cat"], m["cat"]["attributes"], m["fmt"]
    head = ["Option", "Pictures version"] + [MERGE] * (len(attrs) - 1)
    lines = [f"**TABLE WA-B{n_table}.** {cat['label'].upper()}: THE VALUES BEHIND THE PICTURES", "",
             row(head), "|" + "---|" * len(head), row([""] + [attr_head(a) for a in attrs])]
    for key, label in ROWS:
        v = f["pic_values"].get(key)
        if v is not None:
            lines.append(row([label or focal_label(m, key, tiers=[2])] + [fmt_value(a, v[a["name"]]) for a in attrs]))
    return "\n".join(lines)


def blocks(cats):
    """[(category id, kind, text)] in the order the web appendix prints them."""
    out, n = [], 0
    for m in cats:
        n += 1
        out.append((m["cat"]["id"], "table", main_table(m, n)))
        if m["fmt"]:
            pic_n = n + 1 if (m["fmt"]["pictures"] and m["fmt"]["own"]) else None
            out.append((m["cat"]["id"], "format", format_line(m, pic_n)))
            if pic_n:
                n += 1
                out.append((m["cat"]["id"], "pictures", pictures_table(m, n)))
    return out


def enrichment_section(d):
    """The list of names and descriptions at the end of Web Appendix B (unchanged since 2026-07-02)."""
    enr = d.get("enrichment")
    cats = {c["id"]: c for c in d["categories"]}
    out = ["## Enriched product-page text (adjustable tiers; canonical as of the completed calibration)", "",
           enr.get("note", ""), "",
           "Each option in scope renders as: the model name, then each attribute's canonical "
           "value string followed by its qualifier. The same content feeds the human cards, "
           "the spelled-out words cards, the picture renders, and the model prompts.", ""]
    role_note = {"HF": "budget focal", "HD": "premium focal", "DECOY": "frequency decoy",
                 "RANGE_DECOY": "range decoy", "PHANTOM": "phantom (unavailable)",
                 "EXTREME": "compromise extreme", "SYM_DECOY": "symmetric decoy",
                 "CLONE_HF": "clone of the budget focal", "CLONE_HD": "clone of the premium focal"}
    for cid in sorted(enr.get("by_category", {})):
        entries = enr["by_category"][cid]
        out += [f"### {cats[cid]['label']}", "", "| Option role | Model name | Qualifiers |", "|---|---|---|"]
        for key in role_note:
            e = entries.get(key)
            if e:
                quals = "; ".join(f"{a.replace('_', ' ')}: {q}" for a, q in e["qualifiers"].items())
                out.append(f"| {role_note[key]} | {e['name']} | {quals} |")
        out.append("")
    return out


def document(d, bl):
    frozen = (d.get("meta") or {}).get("frozen_at")
    out = ["# STIMULUS APPENDIX (generated from stimuli.json - do not hand-edit)",
           "",
           "*Every value below is read from "
           "`stimuli.json`, the single source of truth that the survey, the model runner, and the "
           "dashboard also read. Regenerated on every stimulus change, so the appendix can never "
           "drift from the delivered stimuli (the V1 defect this design eliminates)."
           + (f" Values are FINAL as of {frozen} (the calibration pre-test is complete; the "
              "full three-wave record, the final-values list, and the routing records are in the "
              "deposited calibration materials)." if frozen else
              " Values are not final until the calibration pre-test completes.") + "*",
           "",
           "These are the stimulus tables of Web Appendix B, as the web appendix prints them. Each table lists every "
           "option of one product category once, with one group of columns for each stimulus tier of the category. "
           "A cell holding only \"<\" joins the cell on its left in the Word document, so a tier heading spans "
           "its columns and a pre-test share spans its tier.",
           ""]
    labels = {c["id"]: c["label"] for c in d["categories"]}
    seen = set()
    for cid, kind, text in bl:
        if cid not in seen:
            out += [f"## {labels[cid]}", ""]
            seen.add(cid)
        out += [text, ""]
    out += enrichment_section(d)
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------------------------------
# the second route: every option of every set, read back from the printed tables
# ---------------------------------------------------------------------------------------------------
def parse_tables(text):
    """{caption: (header, subheader, {row label: cells})} for every TABLE WA-B in a text."""
    out = {}
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        mc = re.match(r"^\*\*TABLE (WA-B\d+)\.\*\* (.*)$", ln)
        if not mc:
            continue
        j = i + 1
        while j < len(lines) and not lines[j].startswith("|"):
            j += 1
        tab = []
        while j < len(lines) and lines[j].startswith("|"):
            tab.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
            j += 1
        if len(tab) < 3:
            continue
        rows_ = {}
        for r in tab[3:]:
            if r[0] in rows_:
                raise Refused(f"{mc.group(1)}: row {r[0]!r} printed twice")
            rows_[r[0]] = r[1:]
        out[mc.group(1)] = dict(title=mc.group(2), head=tab[0][1:], sub=tab[2][1:], rows=rows_)
    return out


def groups_of(head):
    """[(tier heading, first column, width)] from a header row with "<" merges."""
    gs = []
    for k, h in enumerate(head):
        if h == MERGE:
            if not gs:
                raise Refused("a table header starts with a merge mark")
            gs[-1][2] += 1
        else:
            gs.append([h, k, 1])
    return gs


def claims_target(label, tier):
    """True when a row label says that its option is the decoys' target at this tier."""
    m = re.search(r"\(target of the decoys(?: at tier ([0-9]+(?: and [0-9]+)*))?\)", label or "")
    return bool(m) and (m.group(1) is None or str(tier) in m.group(1).split(" and "))


def verify(d, text):
    """Problems (empty = every check holds): each option of each set is printed on a row of its category's table,
    in the column group of its tier, with its own values and name; every label's target claim, every share and
    every format line agree with the stimulus file."""
    probs = []
    tables = parse_tables(text)
    enr = d["enrichment"]
    by_cat = defaultdict(list)
    for s in d["stimuli"]:
        by_cat[s["category"]].append(s)
    cal_focal = {}
    for s in d["stimuli"]:
        if s["structure"] != "BIN" and s.get("target"):
            cal_focal.setdefault(s["category"], s["target"])
    labels = dict((k, v) for k, v in ROWS if v)
    cap_of = {}
    for tid, tb in tables.items():
        cap_of.setdefault(tb["title"].split(":")[0].split(",")[0], []).append(tid)
    for c in d["categories"]:
        upper = c["label"].upper() if not c["price_free"] else c["label"].split(" (")[0].upper() + " WITHOUT PRICES"
        tids = [t for t in cap_of.get(upper, []) if "PICTURES" not in tables[t]["title"]]
        if len(tids) != 1:
            probs.append(f"{c['id']}: {len(tids)} tables titled {upper!r}")
            continue
        tb = tables[tids[0]]
        gs = groups_of(tb["head"])
        tier_col = {}
        for h, k, w in gs:
            m = re.match(r"Tier (\d):", h)
            if not m:
                probs.append(f"{c['id']}: column heading {h!r} names no tier")
                continue
            tier_col[int(m.group(1))] = (k, w)
        attrs = c["attributes"]

        def find_row(code):
            if code in labels:
                return labels[code]
            hits = [r for r in tb["rows"] if r.startswith("Budget option" if code == "HF" else "Premium option")
                    and "share" not in r] if not c["price_free"] else \
                   [r for r in tb["rows"] if r.startswith("Option with the higher "
                                                          + attrs[0 if code == "HD" else 1]["name"].replace("_", " "))]
            return hits[0] if len(hits) == 1 else None

        for s in by_cat[c["id"]]:
            t = s["memorization_tier"]
            if t not in tier_col:
                probs.append(f"{s['id']}: tier {t} has no columns in {tids[0]}")
                continue
            k0, w = tier_col[t]
            sub = tb["sub"][k0:k0 + w]
            named = sub[0] == "Name"
            if named != (t in enr["scope"]["tiers"] and c["id"] in enr["by_category"]):
                probs.append(f"{s['id']}: the name column is {'present' if named else 'missing'} at tier {t}")
            for o in numbers_options(s):
                key = role_key(s, o)
                lab = find_row(key)
                if lab is None or lab not in tb["rows"]:
                    probs.append(f"{s['id']} option {o['code']}: no row for it in {tids[0]}")
                    continue
                cells = tb["rows"][lab][k0:k0 + w]
                vals = cells[1:] if named else cells
                for a, cell in zip(attrs, vals):
                    try:
                        if abs(read_value(cell) - float(o["attrs"][a["name"]])) > 1e-9:
                            probs.append(f"{s['id']} option {o['code']}: {a['name']} printed {cell}, "
                                         f"stimuli.json has {o['attrs'][a['name']]}")
                    except ValueError:
                        probs.append(f"{s['id']} option {o['code']}: cannot read {a['name']} from {cell!r}")
                if named and s["structure"] in enr["scope"]["structures"]:
                    ekey = ("CLONE_" + o["clone_of"]) if o["code"] == "CLONE" else o["code"]
                    if cells[0] != enr["by_category"][c["id"]][ekey]["name"]:
                        probs.append(f"{s['id']} option {o['code']}: name printed {cells[0]!r}")
                if (key == "PHANTOM") == o.get("available", True) or ((key == "PHANTOM") != ("unavailable" in lab)):
                    probs.append(f"{s['id']} option {o['code']}: availability and label disagree")
            # the target claim of the two focal rows
            if s["structure"] in DECOYS:
                other = "HF" if s["target"] == "HD" else "HD"
                if not claims_target(find_row(s["target"]), t) or claims_target(find_row(other), t):
                    probs.append(f"{s['id']}: the table does not mark {s['target']} alone as the target at tier {t}")
            # shares
            if s["structure"] == "BIN" and s.get("calibration"):
                for fmt, rec in s["calibration"]["arms"].items():
                    lab = SHARE_LABEL[fmt]
                    want = share_text(c["id"], cal_focal.get(c["id"]), rec, s["id"])
                    got = tb["rows"].get(lab, [""] * (k0 + 1))[k0]
                    if got != want:
                        probs.append(f"{s['id']} {fmt} share: printed {got!r}, expected {want!r}")
            # the pictures values
            fv = s.get("format_variants") or {}
            if "pictures" in fv:
                pic = fv["pictures"]
                ptids = [x for x in cap_of.get(c["label"].upper(), []) if "PICTURES" in tables[x]["title"]]
                for o in pic["options"]:
                    if pic.get("per_format_values"):
                        if len(ptids) != 1:
                            probs.append(f"{s['id']}: {len(ptids)} pictures tables")
                            break
                        pt = tables[ptids[0]]
                        lab = labels.get(o["code"]) or next((r for r in pt["rows"] if r.startswith(
                            "Budget option" if o["code"] == "HF" else "Premium option")), None)
                        vals = pt["rows"].get(lab)
                    else:
                        lab = find_row(o["code"])
                        vals = tb["rows"].get(lab, [])[k0 + 1:k0 + w] if lab else None
                    if not vals or any(abs(read_value(v) - float(o["attrs"][a["name"]])) > 1e-9
                                       for v, a in zip(vals, attrs)):
                        probs.append(f"{s['id']} pictures option {o['code']}: printed {vals}, stimuli.json has "
                                     f"{o['attrs']}")
        # a row of the table that no option uses
        used = {find_row(role_key(s, o)) for s in by_cat[c["id"]] for o in numbers_options(s)}
        extra = [r for r in tb["rows"] if r not in used and r not in SHARE_LABEL.values()]
        if extra:
            probs.append(f"{c['id']}: rows that no option of the stimulus file uses: {extra}")
        # the extremity tiers: the menu's high and low tiers print as the premium and budget rows
        for s in by_cat[c["id"]]:
            if s["structure"] in ("MOT", "EXC"):
                for o in s["options"]:
                    if TIER_ROLE[o["tier"]] in ("HF", "HD"):
                        focal = next(x for x in by_cat[c["id"]] if x["structure"] == "BIN"
                                     and x["memorization_tier"] == s["memorization_tier"])
                        fo = next(x for x in focal["options"] if x["code"] == TIER_ROLE[o["tier"]])
                        if fo["attrs"] != o["attrs"]:
                            probs.append(f"{s['id']}: the {o['tier']} tier differs from the {fo['code']} option")
    return probs


def names_rows(d):
    """The rows of the list of names and descriptions (the tables under "Product-page descriptions")."""
    return [ln for ln in enrichment_section(d) if ln.startswith("| ") and not ln.startswith("| Option role")]


def check_web_appendix(bl, wa_text, names=()):
    """Problems (empty = holds): Web Appendix B prints every generated block unchanged, in order, and no other
    stimulus table caption; its list of names and descriptions prints every generated row unchanged (a trailing
    HTML comment, such as a prose-lint mark, is allowed after a row)."""
    probs = []
    wa = wa_text.replace("\r\n", "\n")
    if "## Web Appendix B." not in wa or "## Web Appendix C." not in wa:
        return ["the web appendix has no section B followed by section C"]
    sec = wa.split("## Web Appendix B.", 1)[1].split("## Web Appendix C.", 1)[0]
    pos = -1
    for cid, kind, text in bl:
        i = sec.find(text)
        if i < 0:
            first = text.split("\n")[0]
            near = sec.find(first[:40])
            probs.append(f"Web Appendix B does not print the generated {kind} of {cid} unchanged "
                         f"({first[:70]!r}{', its first line is there' if near >= 0 else ''})")
        elif i < pos:
            probs.append(f"Web Appendix B prints the {kind} of {cid} out of order")
        else:
            pos = i
    gen_caps = {text.split("\n")[0] for _, kind, text in bl if kind != "format"}
    for cap in re.findall(r"^\*\*TABLE WA-B\d+\.\*\*.*$", sec, re.M):
        if cap not in gen_caps:
            probs.append(f"Web Appendix B prints a stimulus table that is not generated: {cap[:70]!r}")
    if names:
        printed = [re.sub(r"\s*<!--.*?-->\s*$", "", ln) for ln in sec.split("\n")
                   if ln.startswith("| ") and not ln.startswith("| Option role")]
        printed = printed[-len(names):]
        bad = [g for g, w in zip(names, printed) if g != w]
        if len(printed) != len(names) or bad:
            probs.append(f"the list of names and descriptions differs from stimuli.json, e.g. {(bad or ['(rows missing)'])[0][:90]!r}")
    return probs


# ---------------------------------------------------------------------------------------------------
DATA = None


def build(d):
    global DATA
    DATA = d
    cats = model(d)
    bl = blocks(cats)
    text = document(d, bl)
    probs = verify(d, text)
    return cats, bl, text, probs


def selftest(d):
    ok = True
    _, bl, text, probs = build(d)
    print(f"  clean tables: {len(probs)} problems (must be 0)")
    ok &= not probs
    names = names_rows(d)
    wa_clean = ("## Web Appendix B. x\n\n" + "\n\n".join(t for _, _, t in bl) + "\n\n### Names\n\n"
                + "\n".join(names) + "\n\n## Web Appendix C. y\n")
    clean_wa = check_web_appendix(bl, wa_clean, names)
    print(f"  clean web appendix copy: {len(clean_wa)} problems (must be 0)")
    ok &= not clean_wa

    def planted_text(name, fn):
        bad = fn(text)
        if bad == text:
            print(f"  planted: {name:<58} NOT PLANTED")
            return False
        p = verify(d, bad)
        print(f"  planted: {name:<58} refused: {'yes' if p else 'NO'}" + (f"  ({p[0][:80]})" if p else ""))
        return bool(p)

    def planted_data(name, fn):
        dd = copy.deepcopy(d)
        fn(dd)
        try:
            _, _, _, p = build(dd)
        except Refused as e:
            p = [str(e)]
        print(f"  planted: {name:<58} refused: {'yes' if p else 'NO'}" + (f"  ({p[0][:80]})" if p else ""))
        build(d)
        return bool(p)

    def stim(dd, sid):
        return next(s for s in dd["stimuli"] if s["id"] == sid)

    def opt(s, code):
        return next(o for o in s["options"] if o["code"] == code)

    ok &= planted_text("a price one cent off", lambda t: t.replace("| Frequency decoy | 38 | $42.99 |",
                                                                    "| Frequency decoy | 38 | $42.98 |"))
    ok &= planted_text("a capacity changed", lambda t: t.replace("| Range decoy | 40 | $87.98 |",
                                                                 "| Range decoy | 41 | $87.98 |"))
    ok &= planted_text("a product name changed", lambda t: t.replace("Ridgeline Daypack", "Ridgeline Pack", 1))
    ok &= planted_text("two rows swapped (decoy values under the range decoy)",
                       lambda t: t.replace("| Frequency decoy | 38 | $42.99 |", "| Frequency decoy | 40 | $87.98 |"))
    ok &= planted_text("an option's row dropped", lambda t: re.sub(r"\n\| Clone of the premium option \| 39 [^\n]*", "", t, count=1))
    ok &= planted_text("the target mark moved to the competitor",
                       lambda t: t.replace("| Budget option | 30 |", "| Budget option (target of the decoys) | 30 |", 1)
                       .replace("| Premium option (target of the decoys) | 40 |", "| Premium option | 40 |", 1))
    ok &= planted_text("a pre-test share changed", lambda t: t.replace("42.9% [36.1, 49.9]", "43.9% [36.1, 49.9]", 1))
    ok &= planted_text("a pre-test outcome changed", lambda t: t.replace("n = 459; retained", "n = 459; final", 1))
    ok &= planted_text("a pictures value changed", lambda t: t.replace("| Frequency decoy | 3.6 | $56.24 |",
                                                                       "| Frequency decoy | 3.6 | $56.25 |"))
    ok &= planted_text("the phantom not marked unavailable", lambda t: t.replace("Phantom (shown as unavailable)", "Phantom"))
    ok &= planted_data("the budget option priced differently in one set",
                       lambda dd: opt(stim(dd, "FRQ_backpacks_t2"), "HF")["attrs"].__setitem__("price", 35.49))
    ok &= planted_data("the extremity menu's high tier off the premium values",
                       lambda dd: next(o for o in stim(dd, "MOT_backpacks_t2")["options"] if o["tier"] == "High")
                       ["attrs"].__setitem__("capacity", 49))
    ok &= planted_data("the decoys of one tier with two targets",
                       lambda dd: stim(dd, "RNG_backpacks_t2").__setitem__("target", "HF"))
    ok &= planted_data("a second question in one category",
                       lambda dd: stim(dd, "SYM_backpacks_t1").__setitem__("stem", "Which backpack would you buy?"))
    ok &= planted_data("an available phantom", lambda dd: opt(stim(dd, "PHT_backpacks_t1"), "PHANTOM").__setitem__("available", True))
    wa_bad = wa_clean.replace("| Frequency decoy | 38 | $42.99 |", "| Frequency decoy | 38 | $42.98 |")
    p = check_web_appendix(bl, wa_bad)
    print(f"  planted: {'a cell edited in the web appendix':<58} refused: {'yes' if p else 'NO'}")
    ok &= bool(p)
    wa_bad = wa_clean.replace("## Web Appendix C.", "**TABLE WA-B99.** AN OLD TABLE\n\n## Web Appendix C.")
    p = check_web_appendix(bl, wa_bad)
    print(f"  planted: {'a stale stimulus table left in the web appendix':<58} refused: {'yes' if p else 'NO'}")
    ok &= bool(p)
    parts = wa_clean.split("\n\n")
    p = check_web_appendix(bl, "\n\n".join([parts[0], parts[3], parts[1], parts[2]] + parts[4:]))
    print(f"  planted: {'two tables in the wrong order':<58} refused: {'yes' if p else 'NO'}")
    ok &= bool(p)
    p = check_web_appendix(bl, wa_clean.replace("| Ridgeway Daypack | capacity:", "| Ridgeway Pack | capacity:"), names)
    print(f"  planted: {'a name changed in the list of names':<58} refused: {'yes' if p else 'NO'}")
    ok &= bool(p)
    p = check_web_appendix(bl, wa_clean.replace("Ridgeway Daypack | capacity: room for a laptop, lunch, and a light jacket |",
                                                "Ridgeway Daypack | capacity: room for a laptop, lunch, and a light jacket | <!-- note -->"), names)
    print(f"  clean control: a trailing comment after a row of the list: {len(p)} problems (must be 0)")
    ok &= not p
    rd = read_value("$1,099.98") == 1099.98 and read_value("11,076") == 11076.0 and read_value("4.5") == 4.5
    print(f"  the value reader reads known strings correctly: {'yes' if rd else 'NO'}")
    ok &= rd
    print("SELFTEST PASS" if ok else "SELFTEST FAIL")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv[1:])
    d = json.load(open(STIM, encoding="utf-8"))
    if a.selftest:
        return selftest(d)
    cats, bl, text, probs = build(d)
    if probs:
        refuse("the printed tables disagree with stimuli.json:\n  " + "\n  ".join(probs[:20]))
    n_tables = sum(1 for _, k, _ in bl if k != "format")
    if a.check:
        on_disk = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        errs = [] if on_disk == text else [f"{os.path.basename(OUT)} is not the generated text; run this script"]
        has_wa = os.path.exists(WEB_APPENDIX)
        if has_wa:
            errs += check_web_appendix(bl, open(WEB_APPENDIX, encoding="utf-8", newline="").read(), names_rows(d))
        if errs:
            refuse("\n  ".join(errs[:20]))
        print(f"check: {os.path.basename(OUT)}" + (" and Web Appendix B print" if has_wa else " prints") +
              f" the {n_tables} generated stimulus tables unchanged, and every value, name, target mark and pre-test "
              "share in them equals stimuli.json" + ("" if has_wa else " (no web appendix in this folder tree)"))
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote {os.path.relpath(OUT, HERE)} ({text.count(chr(10))} lines, {n_tables} tables) from stimuli.json "
          f"({d['meta']['n_categories']} categories, {d['meta']['n_stimuli']} stimuli); every option of every set "
          f"read back from the printed tables")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Refused as e:
        print("REFUSED: " + str(e))
        sys.exit(1)
