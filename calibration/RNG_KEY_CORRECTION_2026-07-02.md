# Correction of the answer key of the wave-1 question about the range decoy (July 2, 2026)

This note records a correction that we made after wave 1 and before wave 2. It changes no stimulus value and no
choice share.

## What was wrong

The wave-1 comprehension question about the range decoy asked "On which feature do the options differ by the
widest amount?", and the answer key scored answer 1, "The first feature" (capacity), as correct. We had written that
key before July 1, when we rebuilt the range decoy in the form that the design requires. In the stimulus as
fielded (RNG_backpacks_t2), the budget option holds 25 L at $34.99, the premium option holds 50 L at $59.99, and the
range decoy holds 50 L at $101.98. The decoy has the same capacity as the premium option, so the gap in capacity
stays 25 L, while the decoy widens the range of prices to $67. The correct answer for the stimulus as built is
therefore answer 2, "The second feature" (price). We had not updated the answer key in the survey generator when
we changed the decoy.

## What we did

- We corrected the answer key in `surveys/generate_calibration.py` from 1 to 2. The wording of the question did not
  change, so wave 2 asked the same question again as a second check.
- We scored wave 1 again, from its existing export, against the corrected key. The scoring uses
  `wave1/survey/calibration_wave1_MAPPING_rng_corrected.json`, which is the wave-1 design key with only this answer
  key changed. The key as fielded stays unchanged in `wave1/survey/calibration_wave1_MAPPING.json`.
- We wrote the original wave-1 report (`wave1/results/calibration_report_wave1.md`) again with the corrected key.
  Only the row of the range question and the note on the survey changed. Every share, interval, result and
  adjustment is the same.

## The two scorings

| Scoring | Respondents asked | Correct | Rate | Benchmark (70 percent) |
|---|---|---|---|---|
| As fielded ("The first feature") | 57 | 16 | 28.1% | missed |
| **Corrected ("The second feature")** | **57** | **29** | **50.9%** | **missed** |
| Corrected, kept respondents only | 57 | 29 | 50.9% | missed (all 57 were kept) |

The 57 respondents gave these answers: "The second feature" 29, "The first feature" 16, "about the same" 7, and "I
cannot tell" 5.

The result does not change. Even with the correct key, the question misses the 70 percent benchmark. One reason may
be that the question asks respondents to compare gaps measured in different units. Wave 2 asked the corrected
question again. If it missed again, the rule that we wrote after wave 1 applied (`CALIBRATION_DESIGN.md`, the
changes after wave 1, item 3).
