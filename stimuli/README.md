# stimuli/

This folder contains the file of all stimuli and the code that builds and checks it. Every survey, every model prompt and
every table of Web Appendix B reads its values from `stimuli.json`, and no other file contains a stimulus value.

| File | What it is |
|---|---|
| `stimuli.json` | The file of all stimuli: 165 stimuli in 13 product categories, 9 kinds of choice set and 3 stimulus sets (the field `memorization_tier`: 1, the published values; 2, the new values; 3, the new categories), with the words and pictures versions of the formats part. It contains the final calibrated values and, on every calibrated pair, the record of its calibration. `build_stimuli.py` builds it, and nobody edits it by hand |
| `stimuli_prelock.json` | The file of stimuli as it stood when we built and fielded the calibration surveys, before we fixed the final values. It is deposited so that the calibration waves can be checked against the file that they were built from, and `calibration/calibration_analysis.py` reads it |
| `build_stimuli.py` | Builds `stimuli.json` from `fragments/` and checks every calibrated value against `../calibration/FINAL_LOCK_LIST_2026-07-02.json` |
| `calibration_lock.py` | Records what we did with each pair when we fixed the final values: the values calibrated for each format, the fuller descriptions and the wider margins of the decoys |
| `geometry.py` | Builds the added options of every choice set (the decoys, the phantom, the new extreme option, the extremity menu and its control, and the near-copy) from a category's two-option pair, by fixed rules |
| `enrich.py` | The fuller product descriptions (model names and qualifiers) for the numbers, words and pictures formats |
| `generate_tier2.py`, `generate_tier3.py`, `generate_pricefree.py`, `generate_formats.py` | Write the new values, the new categories, the price-free categories and the words and pictures versions |
| `render.py`, `render_shared.py` | `render.py` draws the pictures (bars for each magnitude, with no numerals). `render_shared.py` is the one function that turns a value into the text that both the surveys and the model prompts show |
| `validate_stimuli.py` | Recomputes the geometry of every stimulus and checks 640 properties. It must end with `640 PASS, 0 WARN, 0 FAIL` |
| `gen_appendix_table.py`, `STIMULUS_APPENDIX.md` | Tables WA-B1 to WA-B15 of Web Appendix B, written from `stimuli.json`: every option of each product category, with the published and the new values side by side |
| `fragments/` | The source files of each category and, for every published value, its source (`*_receipts.md`) |
| `assets/` | The pictures as SVG files. The PNG files that participants and models see are in `../surveys/png/` |

## Commands

```
python stimuli/build_stimuli.py         # rewrites stimuli.json; the result is identical to the deposited file
python stimuli/validate_stimuli.py      # 640 PASS, 0 WARN, 0 FAIL
python stimuli/gen_appendix_table.py    # rewrites STIMULUS_APPENDIX.md
```

## Sources of the values

We built the stimuli at the published values from two published papers, one on upscaling and one on extremity.
The two original options are as the two papers printed them, and the authors of each paper reported only
their own effect, upscaling or extremity, on these options; every added option follows our design.
`fragments/<category>_receipts.md` lists every published value with its source (authors, year, journal and DOI).
The new values, which no paper printed, are for the same categories. The new categories (electric kettles, robot
vacuums and standing desks) have never appeared in a study of context effects. All the calibrated values come from
the calibration pre-test (`../calibration/`).
