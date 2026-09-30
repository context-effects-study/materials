# The calibration pre-test: design and changes between waves

This is the design of the stimulus calibration pre-test, followed by every change in the order it was made.
This copy is written for readers: working notes (file names of the authors' working materials, budget planning) are left out,
and every rule, threshold and number is kept as it was stated.

## Why the pre-test exists

The associate editor: "I would suggest running a small pre-test to calibrate some of your stimuli before
registering the report to avoid extreme share in the binary condition." The editor: "substantial
pre-testing would be needed, to identify the stimuli and degree of tradeoff that results in context
effects." The published record shows why: the upscaling effect reverses at an 87 percent binary baseline
(p = .003), and the compromise effect reverses for advantaged targets. Extreme baselines do not only weaken
effects; they flip them.

## What is calibrated: 25 two-option pairs

Every choice set is built on a two-option pair (a premium option and a budget option).

| Block | Pairs | Rule |
|---|---|---|
| Published categories, tier 1 (exact published values) | 7 | checked only: the values are fixed by fidelity to the published source; a tier-1 pair outside the band is reported, never adjusted (changing it would break the premise of the memorization tier) |
| Published categories, tier 2 (new values) | 7 | adjustable |
| Invented categories, tier 3 | 3 | adjustable (realism checked first, below) |
| Format module, tier 2, words | 4 | adjustable wording, the same values as the numbers version where possible |
| Format module, tier 2, pictures | 4 | adjustable rendering, the same values |
| **Total** | **25** | |

## The target band

Each two-option pair is the shared baseline of six effect tests at once, including the compromise test,
whose target must start behind. The single band that satisfies all six: **the compromise target chosen by
40 to 45 percent, its rival by 55 to 60 percent.** This sits inside the general rule against extreme
baselines (40 to 60) and gives the compromise target its required disadvantage. Hard limits: a pair outside
25 to 75 percent after the final wave goes to the decision tree's stimulus-defect branch. Which option is
the compromise target (and so the direction in which the compromise set's new extreme extends) is fixed
per category at stimulus design and recorded in the stimulus file.

## The procedure

1. **Realism check first (invented categories only).** About 60 raters judge the three invented
   categories' product descriptions ("does this read like a real product page?", 7 points, plus open
   comments). Threshold: a mean of 5.0 or higher and no recurring confusion in the comments; otherwise
   revise the wording and check again.
2. **Wave 1.** Every pair to about 100 respondents (one binary choice each). At 100 a true 50 percent
   share is estimated within about 10 points (95 percent interval), enough to sort pairs into in band,
   adjust, and far off.
3. **Adjustment.** For each pair outside the band, change the price of the too-popular option (the
   intervention that keeps the quality attribute's published or designed value). The rule is mechanical
   and logged: shift the price by 10 percent of its value per 10 share points of imbalance, rounded to a
   realistic price point.
4. **Wave 2.** Re-test the adjusted pairs at about 100 each.
5. **Stop rule.** Stop when every adjustable pair is in the band, or after wave 3, whichever comes first.
   Tier-1 pairs are never adjusted (reported as measured). Pairs that three waves do not settle go to the
   stimulus-defect contingency (drop the category, promote a spare).

**Comprehension checks of the structures.** Calibrating the baseline is necessary but not enough: a decoy
whose dominance cannot be seen, a range that is not visibly extended, or menu tiers that do not read as
distinct would remove the effect even at a perfect baseline. So each structure gets a small check that it
is a valid instance of its structure, never a search for values that produce the effect (that would
manufacture the human result the study tests). Per structure:

- frequency and range decoys: "is any option clearly worse than another on every attribute?" and "which
  option has the widest range on attribute X?", passed by a planned share (70 percent detect the
  dominance, following the detection literature), with the decoy's own share near zero;
- phantom: recognized as unavailable and as better on one attribute, own share zero;
- compromise: the new extreme is seen as more extreme than the target ("which is the most premium?"), so
  the target reads as the middle option;
- upscaling: the symmetric decoy is seen as worse than both focal options;
- extremity: the three quality tiers of the menu are seen as distinct, the options within a tier as nearly
  equivalent;
- similarity: the clone is seen as a near-copy of its focal option.

**Protection of tier 3.** If an invented category fails its structure check or its baseline after the
third wave, a spare invented category is swapped in and calibrated (the stimulus stage builds five
invented candidates and keeps the best three); the tier-3 cell is not dropped. Only if the spares run out
does a tier-3 cell leave the design, and that is reported prominently.

**Re-deriving the extremity control.** The extremity control (EXC) is built from the extremity menu's
(MOT) own tier values, so the two menus share their tiers by construction. Calibration can move the MOT
tier values, so EXC must be rebuilt from MOT after the values are locked: `stimuli/build_stimuli.py`
re-derives EXC from the calibrated MOT tier centers and `stimuli/validate_stimuli.py` must then pass its
EXC checks (one option per tier, three distinct tiers, EXC tiers equal to the matched MOT tier centers).

**What the calibration data may touch.** Calibration responses never enter a confirmatory analysis; they
set attribute values before registration. The Stage 1 protocol reports every wave, every adjustment and
every final share.

**Outputs.** (1) A report per wave written by the analysis script from the export: per pair, the share,
the interval, the verdict and the adjustment. (2) The final values written into the stimulus file, with
`calibration_locked: true` on every stimulus. (3) The calibration survey, generated from the same stimulus
definitions.

## Change before wave 1

**Several choices per respondent.** The planned form gave each respondent one binary choice (about
3,500 respondents across the waves). The amended form bundles the choices: each respondent makes one
binary choice in each of the ten product categories that carry a pair, in one short survey. The precision
per pair is the same or better, the cost falls by more than half, and the baselines are measured in the
same multi-choice format the confirmatory surveys use (the confirmatory backbone asks seven choices per
person). Everything else (the 25 pairs, the band, the adjustment rule, tier-1 check only, the comprehension
checks, the EXC step, the stop rule, the hygiene rules) stays as planned.

**The constraint.** A respondent never judges the same product category twice, in any format: the tier-1
and tier-2 pairs of a category are near-identical trade-offs and the words and pictures pairs carry the
numbers pair's values, so a repeat would anchor the second answer on the first. Each respondent therefore
makes exactly ten choices, one per category; within a category the pair shown is dealt evenly, and the
order of the ten choices is randomized per respondent. One comprehension-check item follows the choices,
one structure per respondent.

**Size.** Four categories carry four pairs each, so they set the size: responses per pair on those
categories = participants / 4. Wave 1: **400 respondents, ten choices each** (about 3 minutes, $0.75 each,
about $15 per hour). The four-pair categories get 100 responses per pair (the planned precision), the
two-pair categories 200, and the single-pair invented categories 400; 4,000 binary responses in all.

**Analysis.** Shares are computed per pair over all responses to it. A respondent contributes at most one
choice per pair, but responses are clustered within respondents across pairs, so the analysis reports a
cluster-robust standard error per pair (respondent = cluster) beside the interval; for a single pair's
share it equals the usual binomial error.

## Changes after wave 1 (before wave 2)

Wave 1 ran on July 2 (400 approved). Seventeen adjustable pairs were outside the band, so wave 2 re-tests
them. The decisions:

1. **Shared values across formats.** Each category's wave-2 adjustment comes from the numbers pair's
   wave-1 share (the planned rule), and the words and pictures pairs carry those same values: the format
   module's premise ("adjustable wording and rendering, the same values as numbers") takes precedence over
   adjusting each format separately. The values are in `wave2/survey/wave2_pairs.json`. A pictures pair
   still at a ceiling at the shared values is handled by the planned no-room and stimulus-defect rules
   after the final wave. The water-bottles numbers pair is in the band, so its words and pictures pairs are
   re-tested at unchanged values.
2. **The stimulus file stays untouched in this wave.** The wave-2 survey applies the adjusted values in
   memory; values are written into the stimulus file once, at the final lock, followed by the EXC step.
3. **Clarified comprehension items, unchanged stimuli.** The wave-1 misses on the frequency (61 percent)
   and compromise (60 percent) checks are treated first as wording problems. Wave 2 labels the options
   Option A, B, C and asks concrete questions (frequency: "is any option clearly worse than another on every
   feature, and which one?"; compromise: "which option is the most premium?"), with the correct letter
   computed from the built stimulus. **Decision rule stated in advance: if the clarified items still miss
   70 percent in wave 2, one final strengthening of the stimulus geometry follows (a wider dominance margin
   for the frequency decoy, a more distant extreme for the compromise set), with a small wave-3 re-check of
   the affected items.**
4. **Range answer key corrected** from "The first feature" to "The second feature", to match the range
   decoy as built (`RNG_KEY_CORRECTION_2026-07-02.md`). Re-scored, wave 1 gives 29 of 57, 51 percent, still
   below 70. The corrected item rides unchanged in wave 2; a second miss falls under the rule in item 3. The
   other four items (phantom, upscaling, extremity, similarity), all passed in wave 1, ride again unchanged.
5. **Realism rides in wave 2.** The planned realism check had not run before wave 1, an ordering
   deviation that is reported. Every wave-2 respondent rates the three invented categories' pages, shown at
   the values they saw, on the planned 7-point question, with one optional comment box. The threshold is
   unchanged (a mean of 5.0 or higher and no recurring confusion). The invented categories' values lock only
   after both their wave-2 shares and their realism verdicts are in. About 300 ratings per category.
6. **Size and pay.** The categories with the most pairs now carry three, so responses per pair =
   participants / 3. Wave 1's 2.5 percent exclusion rate would leave about 97 kept per pair at 300, so the
   size is **312** (about 101 kept per pair on those categories). The realism block lengthens the survey
   (wave 1's median was 192 seconds; about 4.2 minutes expected), so pay rises to **$1.00** (about $14 per
   hour). Cost about $416 including fees.

## Changes after wave 2 (before wave 3): the final wave

Wave 3 is the final calibration wave. After it the values lock, and every pair that does not lock goes to
its planned stimulus-defect contingency and is reported.

**(a) The final-wave decision rule (fixed before any wave-3 data).** A pair locks at its wave-3 values
when (1) its share falls in the planned 40 to 45 percent band, or (2) its 95 percent interval overlaps
40 to 45 **and** the share keeps the compromise target behind and not extreme: **share between 33 and 50
percent** (at or below 50, the target stays the minority option, as the compromise test requires; at or
above 33, well inside the 25 to 75 limits). A pair that meets neither goes to the stimulus-defect
contingency and is reported prominently. Reason: the two water-bottles format pairs, re-tested at identical
values between waves, moved by 5.7 points (words) and 3.4 points (pictures), so the between-wave noise at
identical stimuli is about 4 to 6 points, and a rule requiring the share itself inside a 5-point band is
partly a coin flip at any affordable size (at about 154 responses and a true share of 42.5 percent, the
share lands inside 40 to 45 only about 46 percent of the time). The two-route rule tests the requirements
directly (compatible with the band, target behind, not extreme); at the same size and true share it locks
about 96 percent of the time, while a true share at or above about 55 percent still fails it.

**(b) Quality instead of price where price failed, and values per format where shared values could not
work.** In wave 2, on four numbers pairs (bluetooth speakers, earbuds, hard drives, televisions) the
target's share went up after its price was raised (each move within noise, but four of four in the wrong
direction), and the most common realism comment named the sparseness of the two-line displays. The reading
recorded then: in sparse displays price partly works as a quality cue, so the price rule is a weak or even
reversed lever on those pairs. Wave 3 therefore:

- keeps the price lever only where the two waves gave a usable price response (four solves: backpacks,
  premium option to $61.99; restaurants, to $60.99; televisions pictures, to $429; bluetooth speakers
  pictures, to $84.99), aimed at the band's midpoint (42.5 percent) by linear interpolation;
- moves the category's quality attribute instead on the pairs where price moved the wrong way (bluetooth
  speakers, earbuds, hard drives and televisions numbers) and on the pairs with only extrapolated or flat
  price responses (electric kettles, standing desks, bluetooth speakers words, hard drives words,
  televisions words, hard drives pictures): one conservative step per pair that lowers the too-popular
  option's relative quality, at realistic attribute values (star ratings in steps of 0.1, specifications at
  market steps), aimed at 42.5 percent. The direction is clear in every case; the steps are small because
  the interval route of the decision rule absorbs the remaining error. Each step and its reason are in
  `wave3/survey/wave3_pairs.json` and the wave-3 mapping;
- **records a departure from the wave-2 shared-values rule**: the same values landed at 24.8 to 84.8
  percent across one category's formats (hard drives: numbers 74.5, words 61.8, pictures 84.8), so no single
  value could put all of a category's formats in the band. Wave-3 values are set per format where the
  evidence requires (the pictures pairs follow their own solves; the words pairs share their category's
  quality step). The format module's premise becomes "same category, same attribute structure, values
  calibrated per format", reported as such;
- re-tests the water-bottles words and pictures pairs at unchanged values (their wave-2 deviations sit
  within or near the between-wave noise, and the numbers pair is in the band at these values), which also
  measures the effect of the enriched descriptions and the new legend at fixed values.

**(c) Enriched descriptions (the planned realism remedy: "revise the wording and check again").** All
three invented categories missed the realism threshold at 309 respondents (means 4.53 to 4.77), and the most
common comment named the sparse two-line pages; comments on units named suction in pascals, a kettle's
wattage above 2,000 W, and weight capacity as the lead feature of a standing desk. For the adjustable tiers
only (tiers 2 and 3), each option becomes a short product-page entry: a brand-neutral model name without
numerals, plus the two attributes in their usual display form, each with one plain-language qualifier that
contains no numerals and no comparison and says what the value means in use ("strong enough for carpets and
pet hair"). One content source (`stimuli/enrich.py` and the wave's value file) feeds all three formats:
numbers (name, value, qualifier), words (name, spelled value, qualifier) and pictures (name, magnitude bar,
qualifier, still without numerals, and a legend that now names the attribute, which fixes the wave-2
water-bottles legend confusion). Tier-1 text stays exactly as published; as a consequence the tier-1 versus
tier-2 contrast now also carries sparse published pages against enriched ones, which the protocol
discloses. The wave-3 realism items re-check all three invented categories on the enriched pages (robot
vacuums, final since wave 2 and not dealt as a choice, is re-checked on a static page at its final values).

**(d) Comprehension checks at a useful size, and the one strengthening of the stimuli.** Wave 2's items ran
at about 44 to 45 respondents each (intervals of about 14 points): enough to confirm passes, not to judge
70 percent. In wave 3 each respondent answers **two items, from different structures, never from a category
in which the respondent made a calibration choice.** The seven structures' check stimuli are rebuilt on
robot vacuums (final in wave 2, so dealt to no one as a choice in wave 3) from its final pair (budget
2,000 Pa at $159.00; premium 6,000 Pa at $499.99) and dealt as the 42 ordered pairs of structures with even
presentation, so each structure reaches 2N/7 respondents with position balanced. At N = 462 that is 132
(about 129 kept) per structure. (The preferred 150 kept per structure would need about 539 respondents,
about $812, over the $700 limit set for this wave, so the limit stated in advance applies: at least 120 per
item. A 70 percent rate carries a 7.9-point Wilson interval at 130 against 7.3 points at 150, both far
narrower than wave 2's 14.)

The frequency item missed again (61 percent in wave 1, 44 percent after clarification in wave 2), which
triggers the rule stated after wave 1: **the one final strengthening of the stimulus geometry.** The
frequency decoy's dominance margin grows from (12 percent of the strong attribute's span, 8 percent worse on
price) to (25 percent, 25 percent): decoy 5,000 Pa at $624.99 against the target's 6,000 Pa at $499.99,
visibly worse on both attributes. The range item missed again (51 percent at the corrected key, then 59
percent) and takes the same step on its own lever: the price extension grows from 1.7 to 2.2 times the
target's price (decoy 6,000 Pa at $1,099.98), widening the price gap the item asks about. These parameters
enter `stimuli/geometry.py` as explicit arguments; the confirmatory stimuli adopt them only at the final
lock (this wave changes the check stimuli only; the stimulus file is untouched). The compromise stimulus is
not changed (its wave-2 miss was two answers short, with the interval straddling 70 percent); its clarified
item rides as a re-check at the larger size, as do the phantom, upscaling, extremity and similarity items.
Item wording and the lettered presentation are held fixed so the re-check isolates the change of margin;
answer keys are computed from the built stimuli.

**(e) The picture comprehension item.** One required item after the comprehension pages, shown only to
respondents who received at least one pictures pair (about 85 percent under the wave-3 deal): their first
pictures image is shown again, and the item asks which option has more of the quality feature (the green
bar). The correct answer is computed from the pair's values (Option B in the standard order, the same for
all four pictures stimuli). It is a descriptive indicator of how the pictures were read, reported with the
results; it was never planned, so it is not a criterion.

**(f) Size, length and pay (from wave 2's measured timings).** Nine categories carry open pairs (robot
vacuums is final), so each respondent makes nine choices; the categories with the most open pairs carry
three, water bottles two. **N = 462** (divisible by 2, 3, 6, 7 and 42): 154 per pair in the three-pair
categories (150 or more kept at the observed exclusion rates of 1.0 to 2.5 percent), 231 per water-bottles
pair, 462 per single pair, 132 per comprehension structure. Expected median length, built from wave 2's
measured medians (255 seconds in total: choice pages 9.6 seconds, comprehension page 33.8 seconds, realism
pages 17, 9 and 8 seconds): one choice fewer (minus 10 seconds), enriched pages (about 4 seconds more on
each of nine), a second comprehension page (about 24 seconds) and the picture item (about 13 seconds,
weighted) give **about 5.0 to 5.3 minutes**. Pay **$1.13**: $696.11 including fees at the observed fee rate
(within the $700 limit), $12.70 to $14.10 per hour across that range of lengths.

**(g) The hygiene rules, restated for the final wave.** The stimulus file is untouched by this wave's
survey; all wave-3 values are applied in memory; the decision rule above was fixed before any wave-3 data
existed; calibration responses never enter a confirmatory analysis; the enrichment content, the geometry
margins and the full value history of every pair (wave 1 to wave 2 to wave 3, with each wave's lever and
reason) are recorded in `wave3/survey/wave3_pairs.json`, the wave-3 mapping and the Stage 1 protocol. At the
final lock the locked values and the enrichment content are written into the stimulus file once, followed
by the EXC step and the adoption of the geometry margins.

## After the final wave (recorded here for completeness; decided after the wave-3 data)

- **The final lock** (July 2, 2026) wrote the values into `stimuli/stimuli.json`; the routing of every pair
  is in `stimuli/calibration_lock.py` and the values, shares and intervals in
  `FINAL_LOCK_LIST_2026-07-02.json`. Twelve adjustable pairs met the decision rule, the seven tier-1 pairs
  were checked and reported, five pairs that met neither route were kept in the design with the deviation
  recorded on the stimuli (backpacks 28.5 and restaurants 31.2 percent, below the band with the target still
  the minority option; earbuds 61.0, standing desks 66.7 and water bottles pictures 59.1 percent, with the
  target ahead, where the compromise test is reported as descriptive), and one pair (hard drives pictures,
  above 75 percent in all three waves) left the design. Keeping the five pairs instead of the planned
  contingency (drop the category, promote a spare) was decided after the wave-3 data; no spare invented
  category had been built, so a swap was not available.
- **The realism comparison study** (`realism_study/`) was added after the invented categories missed the
  realism threshold in waves 2 and 3. It changes how the realism result is read, not any value.
