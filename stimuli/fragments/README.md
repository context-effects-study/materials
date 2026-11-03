# The source files of each category

Each category has one `<category>.json` file (tier 1, the published values, or tier 3 for an invented category), a
`<category>_t2.json` file (tier 2, the new values) or a `<category>_pf.json` file (a price-free category). Beside
each, a `<category>_receipts.md` file gives the source of every published value: the paper, the section of the web
appendix of the first submission from which we took the value, and the value itself.

`../build_stimuli.py` merges these files into `../stimuli.json`. Some structures have no published form that fits the
design: the phantom, the near-copy and the new extreme option of the compromise set, and the range decoy, which we
rebuilt so that the target is better than it, as the design requires. `../geometry.py` builds these structures for
every cell from the cell's two-option pair, so that every category and tier uses the same geometry. The receipts
files keep the values of these structures in the first submission. Do not edit `stimuli.json`; change a source file
and build the stimulus file again.
