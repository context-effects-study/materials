"""enrich.py: the single renderer for the enriched product descriptions.

After the invented categories missed the realism threshold in wave 2, each option in the adjustable tiers
(tier 2 and tier 3) became a short product-page entry: a brand-neutral model name without numerals, plus,
for each attribute, the value (rendered by render_shared.render_value, unchanged) and one plain-language
qualifier saying what the value means in use. One content source feeds all three formats:

  numbers   the model name, then "<value> - <qualifier>" for each attribute
  words     the model name, then the spelled-out value and the qualifier
  pictures  the model name above the magnitude bars, the qualifier under each bar

The human survey cards and the model prompts both call entry_for() here, so both read the same text.
Tier-1 (published) values keep their published, sparse wording.
Manuscript: Method (stimulus descriptions) and Web Appendix F (the wave-3 amendment on descriptions).

Imported by build_stimuli.py, the survey generators and models/run.py; not run on its own.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "engines"))
from render_shared import render_value          # the canonical value strings (QSF-1)
import generate_formats as GF                   # attr_words: the spelled-out words idiom

# numeral-free rule: qualifiers/names must carry no digits and no spelled number words
_SPELLED_NUM = re.compile(
    r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|"
    r"fifty|sixty|seventy|eighty|ninety|hundred|thousand|dozen)\b", re.I)


def entry_for(enrichment_block, stim, opt):
    """Resolve one option's enrichment entry from the CANONICAL block in stimuli.json (written at
    the final calibration lock, 2026-07-02: {"scope": {tiers, structures}, "by_category": {cat: {key: entry}}}).
    Returns the {"name", "qualifiers"} entry, or None when the stimulus is out of scope (tier-1,
    MOT/EXC, price-free categories) - callers then render the sparse card, unchanged. The CLONE
    options resolve through their clone_of field (CLONE_HF / CLONE_HD). This is the ONE resolution
    rule, shared by the human QSF generators and the model runner (QSF-1 parity)."""
    if not enrichment_block:
        return None
    scope = enrichment_block.get("scope", {})
    if stim.get("memorization_tier") not in scope.get("tiers", []):
        return None
    if stim.get("structure") not in scope.get("structures", []):
        return None
    entries = (enrichment_block.get("by_category") or {}).get(stim.get("category"))
    if not entries:
        return None
    code = (opt.get("code") or "").upper()
    key = ("CLONE_" + (opt.get("clone_of") or "HF").upper()) if code == "CLONE" else code
    return entries.get(key)


def validate_enrichment(enrichment, cats):
    """Hard-assert the amendment-(c) content contract for every category/option in the kit block.
    Raises on any violation (a numeral in a name/qualifier would leak magnitude into the pictures
    format, whose whole manipulation is 'no numerals')."""
    for cat_id, by_code in enrichment.items():
        if cat_id == "note":
            continue
        attrs = [a["name"] for a in cats[cat_id]["attributes"]]
        for code, entry in by_code.items():
            name = entry["name"]
            assert not re.search(r"\d", name) and not _SPELLED_NUM.search(name), \
                f"enrichment {cat_id}.{code}: model name must be numeral-free: {name!r}"
            quals = entry["qualifiers"]
            assert set(quals) == set(attrs), \
                f"enrichment {cat_id}.{code}: qualifiers must cover exactly {sorted(attrs)}, got {sorted(quals)}"
            for a, q in quals.items():
                assert not re.search(r"\d", q) and not _SPELLED_NUM.search(q), \
                    f"enrichment {cat_id}.{code}.{a}: qualifier must be numeral-free: {q!r}"


def option_numbers_html(opt, cat_meta, entry):
    """The enriched NUMBERS card body: bold model name, then per attribute the canonical
    render_value string (verbatim - QSF-1) followed by its plain-language qualifier."""
    lines = [f"<div class='cfx-attr'><b>{entry['name']}</b></div>"]
    for a in cat_meta["attributes"]:
        n = a["name"]
        if n in opt["attrs"]:
            v = render_value(n, a.get("unit", ""), opt["attrs"][n])
            lines.append(f"<div class='cfx-attr'>{v} — {entry['qualifiers'][n]}</div>")
    return "".join(lines)


def option_words_html(opt, cat_meta, entry):
    """The enriched WORDS card body: same content, the numeric magnitudes spelled out via the SAME
    attr_words idiom the words module always used (computed fresh from the effective values, so
    per-arm overrides are honoured)."""
    lines = [f"<div class='cfx-attr'><b>{entry['name']}</b></div>"]
    for a in cat_meta["attributes"]:
        n = a["name"]
        if n in opt["attrs"]:
            v = GF.attr_words(n, a.get("unit", ""), float(opt["attrs"][n]))
            lines.append(f"<div class='cfx-attr'>{v} — {entry['qualifiers'][n]}</div>")
    return "".join(lines)
