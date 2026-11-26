# The source files of each category

Each category has one `<category>.json` file (the published values, or the values of an invented category), a
`<category>_t2.json` file (the new values) or a `<category>_pf.json` file (a price-free category). Beside
each, a `<category>_receipts.md` file gives the source of every published value: the paper, the section of the web
appendix of the first submission from which we took the value, and the value itself.

`../build_stimuli.py` merges these files into `../stimuli.json`. At the published values, the source files contain the
two original options as printed, and the frequency decoys, the symmetric decoys and the extremity menus with the
values of the first submission. Four added options have no published form that fits the design: the phantom, the
near-copy, the new extreme option of the compromise set, and the range decoy, which the target must beat.
`../geometry.py` builds these options for every cell from the cell's two-option pair, so that every category and
stimulus set uses the same geometry. The receipts files also give the values that these options had in the first
submission. Do not edit `stimuli.json`; change a source file and build the file again.
