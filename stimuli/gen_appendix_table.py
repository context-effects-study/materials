"""gen_appendix_table.py: write the stimulus appendix tables from stimuli/stimuli.json.

Every value in the appendix is read from the stimulus file the surveys and the model prompts use, so the
appendix cannot disagree with what participants and models see.

Output: stimuli/STIMULUS_APPENDIX.md, the source of the stimulus tables in Web Appendix B.

Run: python stimuli/gen_appendix_table.py
"""
import json, os, re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
TIER_NAME = {1: "Tier 1 - exact published focal values (constructed structures rebuilt to the registered geometry)",
             2: "Tier 2 - new values (same category)",
             3: "Tier 3 - invented (never-published) category"}
ORDER = ["BIN", "FRQ", "RNG", "PHT", "SOT", "MOT", "EXC", "SYM", "SIM"]   # EXC = extremity control (path a)

def fmt_val(v):
    return f"{v:g}"

def clean_source(src):
    """Reviewer-facing hygiene for source strings surfaced in the appendix: carry the manuscript's
    evangelidis2023a year suffix, and state the price-free arm's purpose in plain words instead of the
    internal decision-letter point number."""
    src = re.sub(r"(Evangelidis, Levav, and Simonson 2023)(?!a)", r"\1a", src)
    src = src.replace("(AE 8a robustness arm)", "(price-free robustness arm)")
    return src

def options_table(st, attrs, options=None, target=None):
    """Render one option table. The role column reads the stimulus's own registered `target`
    (the decoy target is HD in five categories and HF in five, fixed at the stimulus-design
    stage), never a hard-coded HD; `options`/`target` overrides let a SIM placement variant
    render with its own option set and uncloned focal."""
    names = [a["name"] for a in attrs]
    head = "| Option | role | available | " + " | ".join(n.replace("_", " ") for n in names) + " |"
    sep = "|" + "---|" * (3 + len(names))
    rows = [head, sep]
    opts = options if options is not None else st["options"]
    tgt = target if target is not None else st.get("target")
    for o in opts:
        code = o.get("code", "")
        role = (code + ("/target" if code == tgt else "")) if code in ("HF", "HD") else code
        if o.get("clone_of"):
            role += f" (clone of {o['clone_of']})"
        if o.get("tier"):
            role = o.get("tier") + " tier"
        av = "yes" if o.get("available", True) else "NO (phantom)"
        vals = " | ".join(fmt_val(o["attrs"][n]) for n in names)
        rows.append(f"| {code} | {role} | {av} | {vals} |")
    return "\n".join(rows)

def main():
    d = json.load(open(os.path.join(HERE, "stimuli.json"), encoding="utf-8"))
    cats = {c["id"]: c for c in d["categories"]}
    by_cat = defaultdict(list)
    for s in d["stimuli"]:
        by_cat[s["category"]].append(s)
    # 2026-09-29: which option each calibration share belongs to. cal_focal is the option
    # the calibration records count (the first decoy target listed for the category, as in
    # ingest.load_stimuli); comp_target is the category's compromise target (the SOT cells' target).
    cal_focal, comp_target = {}, {}
    for s in d["stimuli"]:
        if s["structure"] != "BIN" and s.get("target"):
            cal_focal.setdefault(s["category"], s["target"])
        if s["structure"] == "SOT":
            assert comp_target.setdefault(s["category"], s["target"]) == s["target"], \
                f"{s['category']}: compromise targets differ across tiers"
    ROLE = {"HD": "premium option", "HF": "budget option"}

    def who(opt, comp):
        return f"{ROLE[opt]} ({opt}{', the compromise target' if opt == comp else ''})"

    def share_label(cat, w):
        """'<option> share X percent [lo, hi], n = N'; when the recorded option is not the
        compromise target, the compromise target's share and interval are given beside it."""
        f, comp = cal_focal[cat], comp_target.get(cat)
        share, ci, n = w.get("target_share_pct"), w.get("wilson95") or ["", ""], w.get("n")
        if comp is None or f == comp:
            return f"{who(f, comp)} share {share} percent [{ci[0]}, {ci[1]}], n = {n}"
        k = w.get("k_target")
        cpct = 100.0 * (n - k) / n if k is not None else 100.0 - share
        assert abs(cpct - (100.0 - share)) < 0.051, f"{cat}: complement share disagrees"
        return (f"{who(f, comp)} share {share} percent [{ci[0]}, {ci[1]}]; compromise target "
                f"({comp}, the {ROLE[comp]}) share {cpct:.1f} percent "
                f"[{100 - ci[1]:.1f}, {100 - ci[0]:.1f}], n = {n}")

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
           f"**Scope:** {d['meta']['n_categories']} product categories, {d['meta']['n_stimuli']} "
           "stimuli across three memorization tiers, nine choice structures (the eight effect and "
           "control structures plus the matched single-option-per-tier extremity control), plus a "
           "words/pictures format module on four categories.",
           "",
           "## Structure codes",
           "BIN = binary baseline; FRQ = frequency decoy (slightly worse than the target on both "
           "attributes); RNG = range decoy (matches the target on its strong attribute and extends "
           "the attribute range past the target on its weak attribute, so the target dominates it); "
           "PHT = phantom (unavailable, superior on the strong attribute only); SOT = compromise "
           "(two binary options plus a new extreme, so the former premium becomes the middle); MOT = "
           "multiple-options-per-tier (the extremity treatment menu); EXC = the matched extremity "
           "control (one option at each of the treatment menu's three quality tiers, so the two menus "
           "share their tiers and differ only in options per tier); SYM = symmetric decoy (upscaling); "
           "SIM = similarity (a non-dominated near-duplicate of one option, placed at about twelve "
           "percent of the focal gap from its original and floored at one distinguishable unit of the "
           "attribute, so on coarse integer attributes such as storage sizes the clone's step is a "
           "larger fraction of the gap).",
           "",
           "The published categories carry the exact published focal (binary) values at tier 1. The "
           "constructed structures (PHT, SIM, SOT, RNG) are rebuilt around those focal values to the "
           "registered geometry at every tier, because the corresponding prior variants violated it "
           "(a phantom superior on both attributes, an added middle for compromise, a non-dominated "
           "range decoy); the same correction applies to the one frequency decoy whose prior variant "
           "tied the target on an attribute (external hard drives, tier 1, rebuilt to the registered "
           "worse-on-both form); the prior values are preserved in the deposited materials. For the three "
           "categories drawn from Evangelidis, Levav, and Simonson 2023a (backpacks, Bluetooth "
           "speakers, external hard drives), the published studies provide binary focal values only, "
           "so the extremity menu's High and Low tiers carry those published focals and its "
           "middle-tier values are documented midpoint constructions between them, recorded in the "
           "per-category source notes of the deposited materials.",
           "",
           "## Status after the completed calibration pre-test (2026-07-02)",
           "- **Hotels dropped, backpacks restored.** Hotels' 5-star rating ceiling left no "
           "room for a range decoy or compromise extreme, so the category was dropped at the "
           "stimulus-design stage and backpacks (no ceiling) restored. Roster = 13 categories "
           "(10 main + 3 price-free variants).",
           "- **Values are final.** Three calibration waves (1,174 participants) set "
           "the binary baselines; every stimulus carries `calibration_locked: true` in the "
           "deposited stimulus file, and each calibrated binary cell carries its measured share, "
           "interval, and routing record. Pairs that ended outside the registered band carry "
           "their documented-deviation flags (including the compromise-precondition flags on the "
           "affected compromise cells).",
           "- **The pictures hard-drives cells were removed from the design.** That pair stayed "
           "beyond the 25-75 percent hard limits in all three waves (the registered "
           "stimulus-defect contingency); its three pictures-format cells left the confirmatory "
           "inventory, while the numbers and words hard-drives pairs ended inside the band and "
           "stay in the design.",
           "- **Two pictures pairs carry per-format final values** (Bluetooth speakers, "
           "televisions): the calibration found no single value set that placed all of a "
           "category's formats in band, so their pictures variants carry their own values "
           "(shown in their own option tables below).",
           "- **Enriched product-page text is canonical for the adjustable tiers** (tiers 2 and "
           "3, the structures sharing the calibrated binary control): every option carries a "
           "brand-neutral, numeral-free model name and one plain-language qualifier per "
           "attribute (the table at the end of this appendix). Tier-1 text stays exactly as "
           "published; the extremity menus and their matched controls stay sparse (the "
           "extremity comparison is internal to that matched pair).",
           "- **Price-free robustness arm present** (the three `_pf` categories): two quality "
           "attributes, no price, attraction family only - answers the AE's price-as-signal point (AE 8a).",
           "",
           "## Product categories",
           "",
           "| # | Category | Attributes | Source | Tier(s) | Price-free |",
           "|---|---|---|---|---|---|"]
    for i, c in enumerate(d["categories"], 1):
        attrs = ", ".join(f"{a['name'].replace('_',' ')} ({a['unit']}, {a['direction'].replace('_',' ')})"
                          for a in c["attributes"])
        tiers = sorted({s["memorization_tier"] for s in by_cat[c["id"]]})
        src = clean_source(c.get("source", ""))
        out.append(f"| {i} | {c['label']} | {attrs} | {src} | {','.join(map(str,tiers))} | "
                   f"{'yes' if c.get('price_free') else 'no'} |")

    for c in d["categories"]:
        out += ["", f"## {c['label']}", ""]
        stims = sorted(by_cat[c["id"]], key=lambda s: (s["memorization_tier"], ORDER.index(s["structure"])))
        cur_tier = None
        for s in stims:
            if s["memorization_tier"] != cur_tier:
                cur_tier = s["memorization_tier"]
                out += ["", f"### {TIER_NAME[cur_tier]}", ""]
            stat = s.get("statistic") or "-"
            out.append(f"**{s['structure']}** (stem: \"{s['stem']}\"; statistic: {stat})")
            out.append("")
            if s.get("placement_variants"):
                # SIM: the registered design tests BOTH clone placements, so the appendix shows both.
                prim = s.get("sim_placement", "primary")
                prim_lab = "clone of the budget option (HF)" if prim == "clone_HF" else \
                           "clone of the premium option (HD)"
                out.append(f"*Placement {prim} ({prim_lab}; uncloned focal = {s.get('target','')}):*")
                out.append("")
                out.append(options_table(s, c["attributes"]))
                for pname, pv in sorted(s["placement_variants"].items()):
                    pv_lab = "clone of the premium option (HD)" if pname == "clone_HD" else \
                             "clone of the budget option (HF)"
                    pv_stat = pv.get("statistic") or "-"
                    out.append("")
                    out.append(f"*Placement {pname} ({pv_lab}; uncloned focal = {pv.get('target','')}; "
                               f"statistic: {pv_stat}):*")
                    out.append("")
                    out.append(options_table(s, c["attributes"], options=pv["options"],
                                             target=pv.get("target")))
            else:
                out.append(options_table(s, c["attributes"]))
            if s.get("format_variants"):
                fv = s["format_variants"]
                ex = fv["words"][0]
                wpair = ", ".join(f"{k} = {v}" for k, v in ex["words"].items())
                out.append("")
                if fv.get("pictures"):
                    pic = fv["pictures"]
                    out.append(f"*Format module:* WORDS (e.g. Option {ex['code']}: {wpair}) and "
                               f"PICTURES (`{pic['image_ref']}`, quantitative-magnitude SVG, "
                               f"rendered from the final calibrated values, "
                               f"sha256 {pic['image_sha256'][:12]}...).")
                    if pic.get("per_format_values"):
                        out.append("")
                        out.append("*Pictures column, per-format final values (the calibration's "
                                   "recorded per-format departure):*")
                        out.append("")
                        out.append(options_table(s, c["attributes"], options=pic["options"]))
                else:
                    out.append(f"*Format module:* WORDS only (e.g. Option {ex['code']}: {wpair}). "
                               "The pictures cells of this category were removed from the design "
                               "at the final calibration wave (registered stimulus-defect "
                               "contingency; three waves beyond the 25-75 percent hard limits).")
            if s.get("calibration"):
                # Reviewer-facing display of the recorded status codes (the data keeps LOCK /
                # EXIT / RUN_WITH_DEVIATION / CHECK_ONLY; the appendix prints the plain words
                # Web Appendix F's final-status table uses). Display hygiene only - the
                # stimulus file is untouched.
                STATUS_DISPLAY = {"LOCK": "final",
                                  "EXIT": "removed",
                                  "RUN_WITH_DEVIATION": "retained, baseline reported",
                                  "CHECK_ONLY": "published values, checked only"}
                def clean_disposition(txt):
                    txt = txt.replace("LOCK at these values at final calibration lock (with the enrichment content)",
                                      "Final at these values (with the fuller product-page "
                                      "descriptions)")
                    txt = txt.replace("LOCK at", "Final at")
                    txt = txt.replace("DEFECT-ROUTED", "Removed")
                    txt = txt.replace("(terminal wave)", "(final wave)")
                    return txt
                for fmt in ("numbers", "words", "pictures"):
                    rec = s["calibration"]["arms"].get(fmt)
                    if not rec:
                        continue
                    w = rec.get("wave3") or rec.get("wave1") or {}
                    ci = w.get("wilson95") or ["", ""]
                    share = w.get("target_share_pct")
                    stat = rec.get("status")
                    stat_disp = STATUS_DISPLAY.get(stat, stat)
                    if share is not None:
                        out.append("")
                        out.append(f"*Calibration ({fmt} pair):* {share_label(s['category'], w)}; "
                                   f"{stat_disp}.")
                    else:
                        # the share sits inside the disposition text; label it in the heading
                        f_, comp_ = cal_focal[s["category"]], comp_target.get(s["category"])
                        assert comp_ is None or f_ == comp_, \
                            f"{s['id']}: unlabeled disposition share needs a compromise share"
                        out.append("")
                        out.append(f"*Calibration ({fmt} pair; the share quoted belongs to the "
                                   f"{who(f_, comp_)}):* {stat_disp}; "
                                   f"{clean_disposition((rec.get('disposition') or '').split(';')[0])}.")
            out.append("")
    enr = d.get("enrichment")
    if enr:
        out += ["", "## Enriched product-page text (adjustable tiers; canonical as of the "
                "completed calibration)",
                "",
                enr.get("note", ""),
                "",
                "Each option in scope renders as: the model name, then each attribute's canonical "
                "value string followed by its qualifier. The same content feeds the human cards, "
                "the spelled-out words cards, the picture renders, and the model prompts.",
                ""]
        role_note = {"HF": "budget focal", "HD": "premium focal", "DECOY": "frequency decoy",
                     "RANGE_DECOY": "range decoy", "PHANTOM": "phantom (unavailable)",
                     "EXTREME": "compromise extreme", "SYM_DECOY": "symmetric decoy",
                     "CLONE_HF": "clone of the budget focal", "CLONE_HD": "clone of the premium focal"}
        for cid in sorted(enr.get("by_category", {})):
            entries = enr["by_category"][cid]
            out += [f"### {cats[cid]['label']}", "",
                    "| Option role | Model name | Qualifiers |", "|---|---|---|"]
            for key in ("HF", "HD", "DECOY", "RANGE_DECOY", "PHANTOM", "EXTREME", "SYM_DECOY",
                        "CLONE_HF", "CLONE_HD"):
                e = entries.get(key)
                if not e:
                    continue
                quals = "; ".join(f"{a.replace('_', ' ')}: {q}" for a, q in e["qualifiers"].items())
                out.append(f"| {role_note[key]} | {e['name']} | {quals} |")
            out.append("")
    path = os.path.join(HERE, "STIMULUS_APPENDIX.md")
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print(f"wrote {os.path.relpath(path, HERE)} ({len(out)} lines) from stimuli.json "
          f"({d['meta']['n_categories']} categories, {d['meta']['n_stimuli']} stimuli)")

if __name__ == "__main__":
    main()
