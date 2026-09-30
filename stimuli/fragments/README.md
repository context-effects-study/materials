# Per-category source files

One `<category>.json` per category (tier 1, published values, or tier 3 for the invented categories),
`<category>_t2.json` (tier 2, new values) and `<category>_pf.json` (the price-free categories), with a
`<category>_receipts.md` beside each giving the source of every published value: the paper, the section of
the first-round web appendix where the value was taken from, and the value itself.

`../build_stimuli.py` merges these files into `../stimuli.json`. The structures that have no faithful
published form (the phantom, the near-copy, the compromise extreme and, since the range decoy was rebuilt
to the registered dominated form, the range decoy) are constructed for every cell from the cell's
two-option pair by `../geometry.py`, so every category and tier uses the same geometry; the original
first-submission values of those structures stay in the receipts files. Do not edit `stimuli.json`; change
a source file and rebuild.
