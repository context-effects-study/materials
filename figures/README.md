# Figures

This folder holds every figure of the manuscript and the web appendix. Each figure that is computed from data comes
with the script that draws it. Each such script reads the stimulus file, the surveys or the tables of this
repository, and it stops if what it would print differs from them. Figures 1 to 3 and Figures WA-A1 and WA-E1 are
drawings of a stimulus or of the pre-registered rules, and we deposit them as the images that the manuscript and
the web appendix print.

| File | Figure | Script |
|---|---|---|
| `figure1.png` | Figure 1, whether a decoy shifts the choices of language models as much as the choices of people (the frequency-decoy set of backpacks at new values; the shares are illustrative) | a drawing |
| `figure2.png` | Figure 2, the pattern of fidelity that each account predicts across the design | a drawing |
| `figure3.png` | Figure 3, the decision tree: does the model match people, and if not, why not | a drawing |
| `figure_waa1.png` | Figure WA-A1, the seven context effects as choice sets of backpacks | a drawing |
| `figure_wae1.png` | Figure WA-E1, the five fidelity classes on the fidelity map | a drawing |
| `figure_waf1.png` | Figure WA-F1, the three calibration waves | `build_figure_waf1.py`, from `figure_waf1_tables.md` |
| `stimulus_figures/figure_wab*.png` | Figures WA-B1 to WA-B4 of Web Appendix B: one survey page as participants saw it (WA-B1), and the frequency-decoy picture of each of the three pictures categories (WA-B2 to WA-B4) | `build_stimulus_figures.py` |
| `../stimulus-explorer.html` | The stimulus explorer, which shows all 165 stimuli offline | `build_stimulus_figures.py` |

`figure_waf1_tables.md` holds Tables WA-F3, WA-F4 and WA-F5 exactly as the web appendix prints them. For each row,
the number of respondents, the target share and the interval equal the row of the same pair in the original report
of that wave (`calibration/<wave>/results/`), and `run_all.py` reproduces those reports from the deposited data.

`fonts/` holds the files of the IBM Plex Sans typeface, which `build_figure_waf1.py` and `build_stimulus_figures.py`
draw with, so that the figures do not depend on the fonts installed on a computer. We copied the files unchanged.
They are under the SIL Open Font License (`fonts/license.txt`).

## How to draw the figures again

`build_figure_waf1.py` needs matplotlib, and `build_stimulus_figures.py` needs a browser engine (Playwright with
Chromium) and Pillow. `requirements.txt` lists all three at the tested versions. After
`pip install -r requirements.txt`, install the browser once with `python -m playwright install chromium`. Then, from
the root of the repository, run:

```
python figures/build_figure_waf1.py
python figures/build_stimulus_figures.py
```

You can also run `python run_all.py --part figures`, which runs the two scripts and checks that every image comes out
identical, pixel by pixel, to the deposited one. We made the images on Windows 11 with the package versions in
`requirements.txt`. On another operating system or with another build of the browser, text can move by a pixel. In
that case, the scripts' own checks of values, words, text size and boxes still apply, and they still pass.
