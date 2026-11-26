# Calibration wave 3, the final wave: design, findings and the final status of every pair

In wave 3, we measured again the 16 pairs that were still open, at values adjusted pair by pair, on fuller product
pages. Each respondent answered two comprehension questions (about 130 answers for each kind of choice set), the
comprehension question about the pictures and the realism questions again. Prolific approved 462 participants, and
459 of them remained after the exclusions (4,131 choices). The numbers and the result of each pair are in the
original report (`results/calibration_report_wave3.md`), and the record of the study, with an account of every row
of the export, is in `README.md`. We fixed the decision rule of the final wave before collecting the data.

## Final status of the 25 pairs

Every pair is listed with its values in `../FINAL_LOCK_LIST_2026-07-02.json`, and we summarize them in Table WA-F6
of the web appendix.

- **Eleven of the pairs whose values we set met the decision rule.** Four had a share in the band: the water
  bottles at new values (41.7 percent, final after wave 1), the robot vacuums (42.1, final after wave 2), and the
  hard drives (40.0) and water bottles (44.1) in words. Seven met the interval condition: the Bluetooth speakers
  (35.9), hard drives (47.0) and televisions (49.0) at new values in numbers, the Bluetooth speakers (34.0) and
  televisions (49.4) in words, and the Bluetooth speakers (37.3) and televisions (38.7) in pictures.
- **The seven pairs with published values** were measured and reported and never changed. One of them, the water
  bottles at 80.0 percent, lies outside the limits of 25 and 75 percent. It stays in the design with its measured
  baseline, and we leave it out of the pre-registered sensitivity analysis.
- **Six of the pairs whose values we set failed the rule and stay in the design with their measured baselines.**
  The backpacks (28.5) and the restaurants (31.2), both at new values, ended below the band, with the target still
  the less popular option. The earbuds at new values (61.0) and the water bottles in pictures (59.1) ended with the
  target ahead. In the standing desks, the compromise target started at 33.3 percent, and its interval does not
  reach the band. In the electric kettles, the compromise target started at 55.3 percent. The calibration software
  had read the kettles as final, because it applied the band to the share of the budget option; when we recomputed
  every share as the share of the compromise target itself, the kettles failed the rule. Where the compromise target
  starts ahead, the compromise test of that cell is only described. In the sensitivity analysis, we repeat every
  confirmatory test without these six pairs.
- **We removed one pair from the design.** The hard drives in pictures stayed above the limit of 75 percent in all
  three waves (91.9, 84.8 and 79.1 percent), and we removed their three pictures cells from the confirmatory design.
  Without them, the design has 93,100 confirmatory choices in 123 cells.

## The comprehension checks

At wave 3, the questions about four kinds of choice set passed the benchmark of 70 percent correct: the phantom (87
percent), the new extreme option of the compromise set (88), the symmetric decoy of upscaling (71) and the quality
tiers of the extremity menu (93). Three failed it: the frequency decoy (34), the range decoy (46) and the near-copy of
the similarity set (33). The most common answer to the frequency question was that the cheapest option is worse than
another option on every attribute, which cannot be true by the question's own definition, because that option has
the lowest price. From the answers to this question, we therefore cannot tell whether respondents saw that the decoy
was worse on every attribute. We fixed a rule in advance for these failures: we compare a model with people on an
effect only when the confirmatory human data show that effect. Of the respondents who saw the question about the
pictures, 92 percent answered it correctly, so most respondents read the bars as intended.

## Realism

With 459 respondents, the invented categories scored 4.36, 4.53 and 4.68, again below the threshold of 5.0. We
therefore ran the realism comparison study (`../realism_study/REPORT.md`). On the same question, raters judged the
invented pages about as realistic as the pages of the published categories.
