# Survey 2, 3, 4 deals - construction and balance proof
(deal.py, 2026-06-13. Greedy balanced deals for the non-backbone surveys; the backbone keeps
its proven 180-script set. Consumed by generate_survey.py.)

## Survey 4 - price-free arm (3 cats x 4 structures, tier-2, 2,800 participants x 3)
- 12 cells each exactly 700: PASS (min 700/max 700, 12 cells)
- no repeated category within a participant (all 3 distinct): PASS ()
- every participant has 3 trials: PASS (2800 participants)
- all price-free cells tier-2 (HD-target arm): PASS ()

## Survey 2 - SIM two-placement top-up (10 cats x 2 placements, 1,000 participants x 7)
- no repeated category within a participant (7 distinct): PASS ()
- every participant has 7 SIM trials: PASS (1000 participants)
- each category appears ~700 times (10 cats): PASS (min 700/max 700)
- published (cat,placement,tier) cells ~175 each: PASS (min 175/max 175 over 28 cells)
- invented (cat,placement,tier=3) cells ~350 each: PASS (min 350/max 350 over 6 cells)
- each (category, placement) ~350 (20 cells): PASS (min 350/max 350)

## Survey 3 (words) - format module (4 cats x 3 structures, tier-2, 2,800 participants x 3)
- no repeated category within a participant (3 distinct of 4): PASS ()
- every participant has 3 trials: PASS (2800 participants)
- all cells format=words: PASS ()
- all categories in the words roster ['bluetooth_speakers', 'water_bottles', 'hard_drives', 'televisions']: PASS ()
- 12 cells ~700 each (4 cat x 3 struct): PASS (min 700/max 700, 12 cells)
- each of 4 categories ~2,100 appearances: PASS (min 2100/max 2100)

## Survey 3 (pictures) - separate participants; final roster (3 categories after the hard-drives pictures exit), 2,100 participants x 3
- no repeated category within a participant (3 distinct of 3): PASS ()
- every participant has 3 trials: PASS (2100 participants)
- all cells format=pictures: PASS ()
- all categories in the pictures roster ['bluetooth_speakers', 'water_bottles', 'televisions']: PASS ()
- 9 cells ~700 each (3 cat x 3 struct): PASS (min 700/max 700, 9 cells)
- each of 3 categories ~2,100 appearances: PASS (min 2100/max 2100)

## OVERALL: ALL DEALS BALANCED
