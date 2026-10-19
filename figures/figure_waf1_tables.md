# The calibration tables behind Figure WA-F1

Tables WA-F3, WA-F4 and WA-F5 of Web Appendix F, copied exactly. Each row's n, target share and 95 percent
interval is the row of the same pair in the report of record of that wave (calibration/<wave>/results/),
which `run_all.py` reproduces from the deposited data. `figures/build_figure_waf1.py` reads this file.

**TABLE WA-F3.** WAVE 1: THE EIGHTEEN ADJUSTABLE PAIRS AND THE ADJUSTMENT EACH RECEIVED

| Pair | n | Target share (%) | 95% CI | Result | Adjustment for wave 2 |
|---|---|---|---|---|---|
| Backpacks, new values | 196 | 49.5 | [42.6, 56.4] | Adjust | Premium price 59.99 to 62.99 |
| Bluetooth speakers, new values | 97 | 61.9 | [51.9, 70.9] | Adjust | Premium price 89.99 to 109.00 |
| Earbuds, new values | 195 | 53.8 | [46.8, 60.7] | Adjust | Premium price 29.99 to 32.99 |
| Hard drives, new values | 98 | 69.4 | [59.7, 77.6] | Adjust | Premium price 99.99 to 119.00 |
| Restaurants, new values | 197 | 51.8 | [44.8, 58.7] | Adjust | Premium price 58.00 to 61.99 |
| Televisions, new values | 99 | 60.6 | [50.8, 69.7] | Adjust | Premium price 399.99 to 459.00 |
| Water bottles, new values | 96 | 41.7 | [32.3, 51.7] | In the band | None; values kept as final |
| Electric kettles (invented) | 392 | 72.2 | [67.6, 76.4] | Adjust | Budget price 24.99 to 31.99 |
| Robot vacuums (invented) | 392 | 33.7 | [29.2, 38.5] | Adjust | Budget price 149.99 to 159.00 |
| Standing desks (invented) | 392 | 80.1 | [75.9, 83.8] | Adjust (outside 25-75; the limits apply only after the final wave) | Budget price 199.99 to 269.00 |
| Bluetooth speakers, words | 97 | 61.9 | [51.9, 70.9] | Adjust | Same values as the numbers pair |
| Hard drives, words | 97 | 67.0 | [57.2, 75.6] | Adjust | Same values as the numbers pair |
| Televisions, words | 99 | 63.6 | [53.8, 72.4] | Adjust | Same values as the numbers pair |
| Water bottles, words | 97 | 32.0 | [23.5, 41.8] | Adjust | Values unchanged (re-tested) |
| Bluetooth speakers, pictures | 100 | 39.0 | [30.0, 48.8] | Adjust | Same values as the numbers pair |
| Hard drives, pictures | 99 | 91.9 | [84.9, 95.8] | Adjust (outside 25-75) | Same values as the numbers pair |
| Televisions, pictures | 99 | 50.5 | [40.8, 60.1] | Adjust | Same values as the numbers pair |
| Water bottles, pictures | 99 | 56.6 | [46.7, 65.9] | Adjust | Values unchanged (re-tested) |

**TABLE WA-F4.** WAVE 2: SEVENTEEN PAIRS AT SHARED VALUES, WITH THE WAVE-3 ADJUSTMENT

| Pair | n | Share (%) | 95% CI | Wave-1 share | Adjustment for wave 3 |
|---|---|---|---|---|---|
| Backpacks, new values | 309 | 39.8 | [34.5, 45.4] | 49.5 | Premium price 62.99 to 61.99 (from the measured slope) |
| Bluetooth speakers, new values | 104 | 64.4 | [54.9, 73.0] | 61.9 | Budget rating 3.8 to 4.2 stars; price kept |
| Earbuds, new values | 309 | 56.0 | [50.4, 61.4] | 53.8 | Budget review count 2,500 to 4,000; price kept |
| Hard drives, new values | 102 | 74.5 | [65.3, 82.0] | 69.4 | Budget capacity 1 TB to 2 TB; price kept |
| Restaurants, new values | 309 | 39.8 | [34.5, 45.4] | 51.8 | Premium price 61.99 to 60.99 (from the measured slope) |
| Televisions, new values | 103 | 61.2 | [51.5, 70.0] | 60.6 | Budget picture-quality score 70 to 78; price kept |
| Electric kettles (invented) | 309 | 68.0 | [62.6, 72.9] | 72.2 | Budget wattage 1,500 to 1,000 W; price kept |
| Robot vacuums (invented) | 309 | 42.1 | [36.7, 47.6] | 33.7 | None; in the band, values kept as final |
| Standing desks (invented) | 309 | 69.6 | [64.2, 74.4] | 80.1 | Budget weight capacity 150 to 110 lbs; price kept |
| Bluetooth speakers, words | 100 | 59.0 | [49.2, 68.1] | 61.9 | Same values as the numbers pair |
| Hard drives, words | 102 | 61.8 | [52.1, 70.6] | 67.0 | Same values as the numbers pair |
| Televisions, words | 103 | 53.4 | [43.8, 62.7] | 63.6 | Same values as the numbers pair |
| Water bottles, words | 154 | 37.7 | [30.4, 45.5] | 32.0 | Values unchanged (re-tested) |
| Bluetooth speakers, pictures | 105 | 24.8 | [17.5, 33.8] | 39.0 | Premium price 109.00 to 84.99 (own slope) |
| Hard drives, pictures | 105 | 84.8 | [76.7, 90.4] | 91.9 | Same values as the numbers pair |
| Televisions, pictures | 103 | 36.9 | [28.2, 46.5] | 50.5 | Premium price 459.00 to 429.00 (own slope) |
| Water bottles, pictures | 155 | 60.0 | [52.1, 67.4] | 56.6 | Values unchanged (re-tested) |

**TABLE WA-F5.** WAVE 3: SIXTEEN PAIRS UNDER THE FINAL DECISION RULE

| Pair | n | Share (%) | 95% CI | Course (waves 1, 2, 3) | Outcome |
|---|---|---|---|---|---|
| Backpacks, new values | 459 | 28.5 | [24.6, 32.8] | 49.5, 39.8, 28.5 | Did not calibrate (below 33) |
| Bluetooth speakers, new values | 153 | 35.9 | [28.8, 43.8] | 61.9, 64.4, 35.9 | Final (interval overlaps the band) |
| Earbuds, new values | 459 | 61.0 | [56.5, 65.4] | 53.8, 56.0, 61.0 | Did not calibrate (above 50) |
| Hard drives, new values | 151 | 47.0 | [39.2, 55.0] | 69.4, 74.5, 47.0 | Final (interval overlaps the band) |
| Restaurants, new values | 459 | 31.2 | [27.1, 35.5] | 51.8, 39.8, 31.2 | Did not calibrate (below 33) |
| Televisions, new values | 153 | 49.0 | [41.2, 56.9] | 60.6, 61.2, 49.0 | Final (interval overlaps the band) |
| Electric kettles (invented) | 459 | 44.7 | [40.2, 49.2] | 72.2, 68.0, 44.7 | Read as final (budget share in the band); fails by option identity (compromise target 55.3) |
| Standing desks (invented) | 459 | 66.7 | [62.2, 70.8] | 80.1, 69.6, 66.7 | Did not calibrate (budget share above 50; compromise target 33.3) |
| Bluetooth speakers, words | 153 | 34.0 | [27.0, 41.8] | 61.9, 59.0, 34.0 | Final (interval overlaps the band) |
| Hard drives, words | 155 | 40.0 | [32.6, 47.9] | 67.0, 61.8, 40.0 | Final (share in the band) |
| Televisions, words | 156 | 49.4 | [41.6, 57.1] | 63.6, 53.4, 49.4 | Final (interval overlaps the band) |
| Water bottles, words | 229 | 44.1 | [37.8, 50.6] | 32.0, 37.7, 44.1 | Final (share in the band) |
| Bluetooth speakers, pictures | 153 | 37.3 | [30.0, 45.1] | 39.0, 24.8, 37.3 | Final (interval overlaps the band) |
| Hard drives, pictures | 153 | 79.1 | [72.0, 84.8] | 91.9, 84.8, 79.1 | Did not calibrate (outside 25-75 in all three waves) |
| Televisions, pictures | 150 | 38.7 | [31.2, 46.7] | 50.5, 36.9, 38.7 | Final (interval overlaps the band) |
| Water bottles, pictures | 230 | 59.1 | [52.7, 65.3] | 56.6, 60.0, 59.1 (same values all three waves) | Did not calibrate (above 50) |
