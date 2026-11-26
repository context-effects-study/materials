"""render_shared.py: the one function that turns an attribute value into display text.

The human surveys (surveys/generate_qsf.py and the other generators) and the model prompts (models/run.py)
both call render_value() from here, so a person and a model always read the same words for the same
option, for example "65/100 rating", "$79.99", "1,147 reviews". The longer unit descriptions in
stimuli.json are kept for the appendix; render_value shortens them for display without losing the scale.

Imported by the survey generators, the model runner and enrich.py; not run on its own.
"""


def _num(v):
    """Number -> string with thousands separators; ints stay integer, floats keep their decimals."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"{int(f):,}" if f == int(f) else f"{f:,}"


def _price(v):
    """A price as a shop prints it: whole dollars stay whole ($109), anything else has two decimals ($41.50,
    never $41.5). Added 2026-09-29: the constructed options (decoys, phantoms, new extremes, menu tiers) had
    printed as "$41.5" and "$1,009.8" on the cards and in the prompts; no calibrated price changes."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"{int(f):,}" if f == int(f) else f"{f:,.2f}"


def _selftest():
    """Refuses unless prices print as a shop prints them and every other value is unchanged."""
    cases = [(("price", "USD", 41.5), "$41.50"), (("price", "USD", 1009.8), "$1,009.80"),
             (("price", "USD", 109), "$109"), (("price", "USD", 19.99), "$19.99"),
             (("price", "USD", 1299.0), "$1,299"), (("rating", "stars (Amazon, out of 5)", 4.5), "4.5 stars"),
             (("reviews", "number of customer reviews", 11076), "11,076 reviews")]
    bad = [(a, want, render_value(*a)) for a, want in cases if render_value(*a) != want]
    if bad:
        raise SystemExit(f"render_shared SELFTEST FAIL: {bad}")
    print(f"render_shared SELFTEST: PASS ({len(cases)} cases)")


def render_value(name, unit, v):
    """One attribute value as a realistic display string.
    $79.99 / 4.5 stars / 65/100 picture quality / 40 liters capacity / 1,147 reviews.
    Identical output on the human card and in the model prompt (that is the whole point)."""
    nl, ul = name.lower(), (unit or "").lower()
    s = _num(v)
    if "price" in nl or "cost" in nl or "$" in ul or "usd" in ul:
        return f"${_price(v)}"
    if "star" in ul or "star" in nl:
        return f"{s} stars"
    if "0-100" in ul or "100-point" in ul or "100 point" in ul:
        return f"{s}/100 {name.replace('_', ' ')}"
    if "review" in nl:
        return f"{s} reviews"
    tok = (unit or "").split()[0] if unit else ""
    return (f"{s} {tok} {name.replace('_', ' ')}".strip() if tok and not tok[0].isdigit()
            else f"{s} {name.replace('_', ' ')}")


if __name__ == "__main__":
    _selftest()
