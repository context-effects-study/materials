# Figures

Every figure of the manuscript and the web appendix, with the script that draws it. Each script reads the
released stimulus file, surveys or tables, and stops if what it would print differs from them.

| File | Figure | Script |
|---|---|---|
| `figure1.png`, `figure1.svg` | Figure 1, the registered decision tree | `build_figure1.py` |
| `figure2.png` | Figure 2, one choice set in numbers, words and pictures | `build_figure2.py` |
| `figure_waf1.png` | Figure WA-F1, the three calibration waves | `build_figure_waf1.py`, from `figure_waf1_tables.md` |
| `stimulus_figures/figure_wab*.png` | Figures WA-B1 to WA-B28 of Web Appendix B, every choice set | `build_stimulus_figures.py` |
| `../stimulus-explorer.html` | the offline stimulus explorer (all 165 stimuli) | `build_stimulus_figures.py` |

`figure_waf1_tables.md` holds Tables WA-F3, WA-F4 and WA-F5 exactly as the web appendix prints them. Each row's
n, target share and interval is the row of the same pair in that wave's report of record
(`calibration/<wave>/results/`), which `run_all.py` reproduces from the deposited data.

## How to redraw them

The figure scripts need a browser engine (Playwright with Chromium) or matplotlib; `requirements.txt` pins both.
After `pip install -r requirements.txt`, install the browser once with `python -m playwright install chromium`.
Then, from the repository root:

```
python figures/build_figure1.py
python figures/build_figure2.py
python figures/build_figure_waf1.py
python figures/build_stimulus_figures.py
```

or `python run_all.py --figures`, which runs the four scripts and checks that every image comes out identical,
pixel for pixel, to the deposited one. The images were made on Windows 11 with the package versions in
`requirements.txt`; a different operating system or browser build can move text by a pixel, in which case the
scripts' own checks (values, words, text size, boxes) still apply and still pass.
