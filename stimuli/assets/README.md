# The pictures

This folder holds one SVG file for each choice set shown as pictures. Every attribute is a bar whose length is
proportional to its value (amber bars for price and green bars for quality), and no numerals appear. `../render.py`
draws the files, and `../stimuli.json` records the name and the SHA-256 hash of each file under `format_variants`.
The PNG files that participants see and that the models that accept images receive are in `../../surveys/png/`
(made by `../../surveys/rasterize.py`).
