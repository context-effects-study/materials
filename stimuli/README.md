# stimuli/

The single stimulus file and the code that builds and checks it. Every survey, model prompt and appendix
table reads `stimuli.json`; nothing else holds a stimulus value.

| File | What it is |
|---|---|
| `stimuli.json` | The stimulus file: 165 stimuli (13 product categories, 9 choice-set structures, 3 memorization tiers, and the words and pictures variants of the format module), with the calibrated values locked in and a calibration record on every calibrated pair. Built by `build_stimuli.py`; never edited by hand |
| `stimuli_prelock.json` | The stimulus file as it stood when the calibration surveys were built and fielded (before the final calibration lock), kept so the calibration waves can be checked against their true source. `calibration/calibration_analysis.py` reads it |
| `build_stimuli.py` | Builds `stimuli.json` from `fragments/` and checks every calibrated value against `../calibration/FINAL_LOCK_LIST_2026-07-02.json` |
| `calibration_lock.py` | The decisions of the final calibration lock: the routing of every pair, the values calibrated per format, the enriched descriptions and the strengthened decoy margins |
| `geometry.py` | Constructs every structure (decoys, phantom, extreme, extremity menu and control, near-copy) from a category's two-option pair by fixed rules |
| `enrich.py` | The enriched product descriptions (model names and qualifiers) for the numbers, words and pictures formats |
| `generate_tier2.py`, `generate_tier3.py`, `generate_pricefree.py`, `generate_formats.py` | The generators of tier 2, tier 3, the price-free categories and the format variants |
| `render.py`, `render_shared.py` | The picture renderer (magnitude bars, no numerals) and the one function that turns a value into display text for both surveys and model prompts |
| `validate_stimuli.py` | Recomputes the geometry of every stimulus and checks 640 properties; must end `640 PASS, 0 WARN, 0 FAIL` |
| `gen_appendix_table.py`, `STIMULUS_APPENDIX.md` | The stimulus tables of Web Appendix B, generated from `stimuli.json` |
| `fragments/` | The per-category source files and, for every published value, its source (`*_receipts.md`) |
| `assets/` | The pictures-format images (SVG); the PNG files served to participants are in `../surveys/png/` |

## Rebuild and check

```
python stimuli/build_stimuli.py         # rewrites stimuli.json; the result is identical to the deposited file
python stimuli/validate_stimuli.py      # 640 PASS, 0 WARN, 0 FAIL
python stimuli/gen_appendix_table.py    # rewrites STIMULUS_APPENDIX.md
```

## Where the published values come from

The tier-1 values are the exact values of the published studies each effect comes from; every value is
listed with its source (author, year, journal, DOI) in `fragments/<category>_receipts.md`. Tier-2 values
are new values for the same categories; tier-3 categories (electric kettles, robot vacuums, standing desks)
never appeared in a context-effects study. All calibrated values come from the calibration pre-test
(`../calibration/`).
