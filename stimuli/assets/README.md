# Pictures-format images

One SVG per pictures-format choice set: every attribute is a proportional bar (price bars amber, quality
bars green) and no numerals appear. They are drawn by `../render.py`, and `../stimuli.json` records the
file name and SHA-256 of each under `format_variants`. The PNG files served to participants and sent to
vision models are in `../../surveys/png/` (made by `../../surveys/rasterize.py`).
