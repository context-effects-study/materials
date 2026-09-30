# Correction of the wave-1 range-question answer key (July 2, 2026)

This note records a correction made after wave 1 and before wave 2. It changes no stimulus value and no
choice share.

## What was wrong

The wave-1 comprehension item for the range decoy asked "On which feature do the options differ by the
widest amount?" and scored answer 1, "The first feature" (capacity), as correct. That key was written before
the range decoy was rebuilt on July 1 to the registered form. In the stimulus as fielded
(RNG_backpacks_t2: budget option 25 L at $34.99, premium option 50 L at $59.99, range decoy 50 L at $101.98)
the decoy matches the premium option's capacity, so the capacity gap stays 25 L, and it stretches the price
range to $67. The correct answer for the stimulus as built is therefore answer 2, "The second feature"
(price). The survey generator's answer key had not been updated when the decoy changed.

## What was done

- The answer key in `surveys/generate_calibration.py` was corrected from 1 to 2. The item's wording did
  not change, so wave 2 carried it unchanged as a re-check.
- Wave 1 was re-scored from its existing export against the corrected key, using
  `wave1/survey/calibration_wave1_MAPPING_rng_corrected.json` (the wave-1 design key with only this answer
  key changed). The key as fielded is kept unchanged in `wave1/survey/calibration_wave1_MAPPING.json`.
- The wave-1 report of record (`wave1/results/calibration_report_wave1.md`) was regenerated with the
  corrected key. Only the range-question row and the note on the instrument changed; every share, interval,
  verdict and adjustment row is the same.

## The two scorings

| Scoring | Respondents asked | Correct | Rate | Benchmark (70 percent) |
|---|---|---|---|---|
| As fielded ("The first feature") | 57 | 16 | 28.1% | missed |
| **Corrected ("The second feature")** | **57** | **29** | **50.9%** | **missed** |
| Corrected, kept respondents only | 57 | 29 | 50.9% | missed (all 57 were kept) |

All answers: "The second feature" 29, "The first feature" 16, "about the same" 7, "I cannot tell" 5.

The verdict does not change: even with the correct key the item misses the 70 percent benchmark (it asks
respondents to compare gaps measured in different units). Wave 2 re-checked the corrected item; the
decision rule written after wave 1 (`CALIBRATION_DESIGN.md`, the wave-2 amendment, item 3) applied if it
missed again.
