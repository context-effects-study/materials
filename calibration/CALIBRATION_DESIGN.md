# The calibration pre-test: design and changes between waves

This document gives the design of the calibration pre-test and then every change to it, in the order in which we
made the changes. We wrote this copy for readers. It leaves out working notes, such as the names of the authors'
working files and the planning of the budget, and it keeps every rule, threshold and number as we stated it at
the time. The last section says how each pair ended.

## Why we ran the pre-test

The associate editor wrote: "I would suggest running a small pre-test to calibrate some of your stimuli before
registering the report to avoid extreme share in the binary condition." The editor wrote: "substantial
pre-testing would be needed, to identify the stimuli and degree of tradeoff that results in context effects."
Published studies show why. The upscaling effect reversed when 87 percent of participants chose the premium
option in the two-option set (p = .003), and the compromise effect reversed when the target started ahead of its
rival. A share near the floor or the ceiling therefore does not only make an effect smaller; it can reverse it.

## What we calibrated: 25 two-option pairs

Every choice set starts from a two-option pair, a premium option and a budget option.

| Group | Pairs | Rule |
|---|---|---|
| Published categories, tier 1 (the exact published values) | 7 | Measured only. The values must stay as published, so we report a tier-1 pair outside the band and never adjust it. Adjusted values would no longer be the published values that the memorization test compares with new values |
| Published categories, tier 2 (new values) | 7 | Adjustable |
| Invented categories, tier 3 | 3 | Adjustable (realism checked first, as below) |
| Format module, tier 2, words | 4 | Adjustable wording, with the same values as the numbers version where possible |
| Format module, tier 2, pictures | 4 | Adjustable drawing, with the same values |
| **Total** | **25** | |

## The target band

Each two-option pair is the shared control of six effect tests at once. One of them is the compromise test, whose
target must start behind its rival. One band works for all six: **the compromise target chosen by 40 to 45
percent, and its rival by 55 to 60 percent.** This band lies inside the general rule against extreme shares (40 to
60 percent), and it keeps the compromise target behind, as the compromise test requires. The outer limits are 25
and 75 percent: a pair outside them after the final wave was to be treated as a defective stimulus. For each
category, we fixed at the design stage which option is the compromise target, and so the side on which the new
extreme option of the compromise set lies. The stimulus file records it.

## The procedure

1. **Realism first (invented categories only).** About 60 raters judge the product descriptions of the three
   invented categories on a 7-point question ("does this read like a real product page?") and can add comments.
   A category passes with a mean of 5.0 or higher and no confusion that recurs in the comments. Otherwise, we
   revise the wording and check again.
2. **Wave 1.** About 100 respondents choose in every pair, one choice each. With 100 respondents, a true share of
   50 percent is estimated to within about 10 points (95 percent interval). That is enough to sort the pairs into
   three groups: in the band, to adjust, and far off.
3. **Adjustment.** For each pair outside the band, we change the price of the option that is chosen too often,
   because this change keeps the quality attribute at its published or designed value. The rule is fixed and every
   step is logged: we shift the price by 10 percent of its value for every 10 points of imbalance in the share,
   and we round it to a realistic price.
4. **Wave 2.** About 100 respondents choose in each adjusted pair.
5. **When to stop.** We stop when every adjustable pair is in the band, or after wave 3, whichever comes first. We
   never adjust a tier-1 pair, and we report its share as measured. A pair that three waves do not place in the
   band is treated as a defective stimulus: we drop its category and use a spare category in its place.

**Comprehension checks of the structures.** A baseline in the band is necessary, but it is not enough. If
participants cannot see that a decoy is worse than the target, that a range is extended, or that the tiers of a
menu differ, the effect can vanish even at a perfect baseline. So each structure gets a short check that it reads
as intended. The check is never a search for values that produce the effect. Such a search would make people show
the effect by construction, and the study tests whether they show it. The checks are as follows:

- frequency and range decoys: "is any option clearly worse than another on every attribute?" and "which option has
  the widest range on attribute X?". The benchmark is 70 percent correct, following the published studies of how
  often people detect that one option is worse on every attribute, and the decoy itself should be chosen by
  almost nobody;
- phantom: respondents should see that it is unavailable and that it is better than the target on one attribute,
  and nobody can choose it;
- compromise: respondents should see the new extreme option as more extreme than the target ("which is the most
  premium?"), so that the target reads as the middle option;
- upscaling: respondents should see the symmetric decoy as worse than both focal options;
- extremity: respondents should see the three quality tiers of the menu as distinct and the options within one
  tier as nearly the same;
- similarity: respondents should see the clone as a near-copy of the focal option that it copies.

**Protecting tier 3.** If an invented category fails its comprehension check or its baseline after the third
wave, we put a spare invented category in its place and calibrate it. The stimulus stage builds five invented
candidates and keeps the best three, so the tier-3 cell is not dropped. A tier-3 cell leaves the design only if no
spare remains, and we would report that prominently.

**Rebuilding the extremity control.** The extremity control (EXC) is built from the tier values of the extremity
menu (MOT), so that the two menus share their tiers. Calibration can move the tier values of the menu, so we
rebuild EXC from MOT after the values are final. `stimuli/build_stimuli.py` rebuilds EXC from the calibrated
centers of the menu's tiers. `stimuli/validate_stimuli.py` must then pass its checks of EXC: one option at each
tier, three distinct tiers, and each EXC tier equal to the center of the matched MOT tier.

**What the calibration data may change.** Calibration responses never enter a confirmatory analysis. They set
attribute values before registration. The Stage 1 protocol reports every wave, every adjustment and every final
share.

**Outputs.** The pre-test has three outputs. (1) For each wave, the analysis script writes a report from the
export, which gives the share, the interval, the result and the adjustment of each pair. (2) We write the final
values into the stimulus file, with `calibration_locked: true` on every stimulus. (3) The calibration survey is
generated from the same definitions of the stimuli.

## Change before wave 1

**Several choices per respondent.** In the planned form, each respondent made one choice between two options, and
the waves would have needed about 3,500 respondents. In the changed form, each respondent makes one choice in each
of the ten product categories that have a pair, in one short survey. The precision for each pair is the same or
better, the cost falls by more than half, and we measure the baselines with several choices per person, as in the
confirmatory survey of the core design, where each person makes seven choices. Everything else stays as planned:
the 25 pairs, the band, the adjustment rule, the rule that tier-1 pairs are only measured, the comprehension
checks, the rebuilding of the extremity control, the rule for stopping, and the rules for handling the data.

**The constraint.** A respondent never judges the same product category twice, in any format. The tier-1 and tier-2
pairs of a category offer nearly the same trade-off, and the words and pictures pairs have the values of the
numbers pair, so a second judgment in the same category would be anchored on the first. Each respondent
therefore makes exactly ten choices, one in each category. Within a category, the pairs are assigned evenly to
respondents, and the order of the ten choices is random for each respondent. One comprehension question follows
the choices, about one structure for each respondent.

**Size.** Four categories have four pairs each, so these categories set the size: each of their pairs receives
one quarter of the participants. Wave 1 has **400 respondents with ten choices each**, about 3 minutes, paid $0.75
(about $15 an hour). Each pair of the four-pair categories receives 100 responses, the planned precision, each pair
of the two-pair categories receives 200, and each single-pair invented category receives 400, for 4,000 choices in
all.

**Analysis.** We compute the share of each pair over all the responses to it. A respondent gives at most one
choice in each pair, but each respondent answers several pairs. The analysis therefore reports, beside the
interval, a standard error that treats each respondent as a cluster. For the share of a single pair, this error
equals the usual binomial error.

## Changes after wave 1 (before wave 2)

Wave 1 ran on July 2, with 400 approved respondents. Seventeen adjustable pairs were outside the band, so wave 2
tests them again. We made six decisions:

1. **The same values in every format.** We set each category's wave-2 values from the share of the numbers pair in
   wave 1, by the planned rule, and the words and pictures pairs show those same values. The format module is
   built on the rule that the words and pictures versions show the same values as the numbers version, and we
   kept that rule in preference to adjusting each format on its own. `wave2/survey/wave2_pairs.json` holds the
   values. If a pictures pair stays near the floor or the ceiling at the shared values, the planned rules for such
   cases apply after the final wave. The numbers pair of the water bottles is in the band, so we test its words and
   pictures pairs again at unchanged values.
2. **The stimulus file stays unchanged in this wave.** The wave-2 survey applies the adjusted values in memory. We
   write values into the stimulus file once, when the final values are fixed, and then rebuild the extremity
   control.
3. **Clearer comprehension questions, with the stimuli unchanged.** In wave 1, the checks of the frequency decoy
   (61 percent correct) and of the compromise set (60 percent) missed the benchmark, and we first treat these misses
   as problems of wording. Wave 2 labels the options Option A, B and C and asks concrete questions (frequency: "is
   any option clearly worse than another on every feature, and which one?"; compromise: "which option is the most
   premium?"). The correct letter is computed from the built stimulus. **We stated a rule in advance: if a clearer
   question still misses 70 percent in wave 2, we strengthen the geometry of the stimulus once (a decoy that is
   worse by a wider margin, or a new extreme option that lies further out), and we check the affected questions
   again, on a small scale, in wave 3.**
4. **The answer key of the range question is corrected** from "The first feature" to "The second feature", to match
   the range decoy as built (`RNG_KEY_CORRECTION_2026-07-02.md`). Scored with the corrected key, wave 1 gives 29 of
   57 correct, 51 percent, which is still below 70 percent. Wave 2 asks the corrected question again, unchanged, and
   a second miss falls under the rule in item 3. The other four questions (phantom, upscaling, extremity and
   similarity) all passed in wave 1, and wave 2 asks them again unchanged.
5. **Realism is measured in wave 2.** The planned realism check did not run before wave 1, and we report this change
   of order. Every wave-2 respondent rates the pages of the three invented categories, at the values that the
   respondent saw, on the planned 7-point question, with one optional comment box. The threshold is unchanged: a
   mean of 5.0 or higher and no confusion that recurs in the comments. We fix the values of the invented categories
   only after we know both their wave-2 shares and whether their pages met the realism threshold. Each category
   receives about 300 ratings.
6. **Size and pay.** The categories with the most pairs now have three, so each of their pairs receives one third of
   the participants. At wave 1's exclusion rate of 2.5 percent, 300 participants would leave about 97 kept
   responses for each such pair, so the size is **312**, which leaves about 101. The realism questions make the
   survey longer (the median time in wave 1 was 192 seconds, and we expect about 4.2 minutes), so the pay rises to
   **$1.00** (about $14 an hour). The cost is about $416 including fees.

## Changes after wave 2 (before wave 3, the final wave)

Wave 3 is the final calibration wave. After it, the values are fixed, and every pair that does not meet the rule
below is handled as planned for stimuli that fail to calibrate and is reported.

**(a) The decision rule of the final wave, fixed before any wave-3 data existed.** A pair keeps its wave-3 values
when (1) its share falls in the planned band of 40 to 45 percent, or (2) its 95 percent interval overlaps 40 to 45
**and** its share keeps the compromise target behind and away from the extremes: **a share between 33 and 50
percent.** At or below 50 percent, the target stays the less popular option, as the compromise test requires; at
or above 33 percent, the share is well inside the limits of 25 and 75 percent. A pair that meets neither condition
is handled as a stimulus that failed to calibrate and is reported prominently. We added the second condition
because the two water-bottles format pairs, tested twice at identical values, moved by 5.7 points (words) and 3.4
points (pictures) between waves. At unchanged stimuli, shares therefore differ by about 4 to 6 points from wave to
wave. A rule that requires the share itself to fall inside a band 5 points wide is then partly a matter of chance
at any sample that we can afford. With about 154 responses and a true share of 42.5 percent, the share falls
inside 40 to 45 only about 46 percent of the time. The rule with two conditions tests what the design needs: a
share compatible with the band, a target that starts behind, and no extreme share. At the same size and true
share, a pair meets it about 96 percent of the time, and a pair with a true share of about 55 percent or more still
fails it. (These two numbers came from an approximation. An exact binomial calculation gives about 49 and 97
percent, the values that Web Appendix F reports.)

**(b) Quality in place of price where price failed, and values for each format where shared values could not
work.** In wave 2, on four numbers pairs (Bluetooth speakers, earbuds, hard drives and televisions), the target's
share went up after we raised its price. Each change was within the noise between waves, but all four went in the
wrong direction. The most common realism comment said that the two-line pages were sparse. We concluded then that
on such sparse pages, respondents partly read the price as a sign of quality, so that a change of price moves the
share weakly or even in the wrong direction. For wave 3, we therefore made four changes:

- We keep the price rule only where the two waves gave a usable response of the share to the price. There are four
  such pairs: the backpacks (premium option to $61.99), the restaurants (to $60.99), the televisions in pictures
  (to $429) and the Bluetooth speakers in pictures (to $84.99). We aim each at the middle of the band (42.5
  percent) by linear interpolation between the two measured points.
- On the pairs where the price moved the share the wrong way (Bluetooth speakers, earbuds, hard drives and
  televisions, in numbers), and on the pairs whose response to price was flat or measured at one price only
  (electric kettles, standing desks, Bluetooth speakers in words, hard drives in words, televisions in words, hard
  drives in pictures), we change the category's quality attribute. Each pair takes one cautious step that lowers
  the relative quality of the option that is chosen too often. The new values are realistic: star ratings in steps
  of 0.1, and specifications in the steps that products on the market use. We aim each step at 42.5 percent. The
  direction of each step is clear, and we keep the steps small, because the interval condition of the decision rule
  accepts the remaining error. `wave3/survey/wave3_pairs.json` and the wave-3 design key give each step and its
  reason.
- **We depart from the rule of the same values in every format.** At the same values, the shares of one category's
  formats differed widely (hard drives: 74.5 percent in numbers, 61.8 in words and 84.8 in pictures), so no single
  set of values could put all of a category's formats in the band. In wave 3, we set values for each format where
  the data require it: each pictures pair follows its own measured response to price, and each words pair takes
  its category's step in quality. The format module then compares formats within the same category and with the
  same attributes, at values calibrated for each format, and we report it that way.
- We test the water-bottles pairs in words and in pictures again at unchanged values. Their changes from wave 1 to
  wave 2 lay within or near the noise between waves, and the numbers pair is in the band at these values. The new
  test also measures, at fixed values, the effect of the fuller descriptions and of the new legend.

**(c) Fuller product descriptions, the planned remedy for realism ("revise the wording and check again").** All
three invented categories missed the realism threshold with 309 respondents (means of 4.53 to 4.77). The most
common comment said that the two-line pages were sparse. Comments on units named suction in pascals, the wattage of
a kettle above 2,000 W, and weight capacity as the first feature of a standing desk. For the adjustable tiers only
(tiers 2 and 3), each option becomes a short entry like one on a product page: a model name without numerals and
without a real brand, and the two attributes in their usual display form. Each attribute has one plain qualifier,
with no numerals and no comparison, that says what the value means in use ("strong enough for carpets and pet
hair"). One source of content (`stimuli/enrich.py` and the file of values of the wave) feeds all three formats.
In numbers, an option shows the name, the value and the qualifier. In words, it shows the name, the value spelled
out and the qualifier. In pictures, it shows the name, a bar for each magnitude and the qualifier, still without
numerals. The legend of the pictures now names the attribute, which fixes the confusion about the legend of the
water bottles in wave 2. The tier-1 text stays exactly as published. As a result, the comparison of tier 1 with
tier 2 now also compares sparse published pages with fuller pages, and the protocol says so. In wave 3, the realism
questions check all three invented categories again on the fuller pages. The robot vacuums, final since wave 2 and
not shown as a choice in wave 3, are checked on a fixed page at their final values.

**(d) Comprehension checks with enough respondents, and the one strengthening of the stimuli.** In wave 2, each
question had about 44 or 45 respondents, which gives intervals about 14 points wide. That is enough to confirm a
clear pass, but not to judge a rate near 70 percent. In wave 3, each respondent answers **two questions, about two
different structures, and never in a category in which the respondent made a calibration choice.** We rebuilt the
check stimuli of all seven structures on the robot vacuums, which were final in wave 2 and so were shown to nobody
as a choice in wave 3, from their final pair (budget option 2,000 Pa at $159.00; premium option 6,000 Pa at
$499.99). The 42 ordered pairs of structures are assigned evenly, so that each structure reaches 2N/7 respondents
and appears equally often in each position. With N = 462, that gives 132 respondents for each structure (about 129
kept). We would have preferred 150 kept respondents for each structure, but that would have needed about 539
respondents and about $812, over the $700 limit for this wave, so the limit stated in advance applies: at least
120 respondents for each question. At a rate of 70 percent, the Wilson interval is 7.9 points wide at 130
respondents and 7.3 points wide at 150, and both are far narrower than the 14 points of wave 2.

The frequency question missed again (61 percent in wave 1, and 44 percent after the rewording in wave 2). This
miss triggers the rule stated after wave 1: **the one final strengthening of the geometry of the stimulus.** The
frequency decoy now falls short of the target by 25 percent of the range of the strong attribute and is 25 percent
more expensive, where it was 12 percent short and 8 percent more expensive before. The decoy is 5,000 Pa at
$624.99, against the target's 6,000 Pa at $499.99, and so it is visibly worse on both attributes. The range question
also missed again (51 percent with the corrected key, then 59 percent), and it takes the same kind of step on its
own attribute: the price of the range decoy grows from 1.7 to 2.2 times the target's price (6,000 Pa at
$1,099.98), which widens the gap in price that the question asks about. `stimuli/geometry.py` takes these
parameters as explicit arguments. The confirmatory stimuli adopt them only when the final values are fixed: this
wave changes only the check stimuli and leaves the stimulus file unchanged. We do not change the compromise stimulus,
because its wave-2 miss was two answers short and its interval included 70 percent. Its clearer question is asked
again with more respondents, as are the questions about the phantom, upscaling, extremity and similarity. The
wording of the questions and the lettered options stay fixed, so that the new check measures only the change of
margin. The answer keys are computed from the built stimuli.

**(e) The comprehension question about the pictures.** One required question follows the comprehension pages, and
only respondents who received at least one pictures pair see it (about 85 percent of respondents under the wave-3
assignment). The question shows the respondent's first pictures image again and asks which option has more of the
quality feature (the green bar). The correct answer is computed from the pair's values: it is Option B in the
standard order, the same for all four pictures stimuli. The question describes how respondents read the pictures,
and we report its result with the other results. We had not planned it, so it is not a criterion.

**(f) Size, length and pay, from the timings measured in wave 2.** Nine categories have open pairs (the robot
vacuums are final), so each respondent makes nine choices. The categories with the most open pairs have three, and
the water bottles have two. **N = 462**, a number that 2, 3, 6, 7 and 42 divide evenly. It gives 154 responses for
each pair in the three-pair categories (150 or more kept, at the exclusion rates of 1.0 to 2.5 percent that we
observed), 231 for each water-bottles pair, 462 for each single pair and 132 for each comprehension structure. We
built the expected median length from the medians measured in wave 2, which totaled 255 seconds (choice pages 9.6
seconds each, the comprehension page 33.8 seconds, and the realism pages 17, 9 and 8 seconds). Wave 3 has one choice
fewer (minus 10 seconds), fuller pages (about 4 seconds more on each of nine pages), a second comprehension page
(about 24 seconds) and the pictures question (about 13 seconds, weighted by the share of respondents who see it).
The expected median is therefore **about 5.0 to 5.3 minutes**. The pay is **$1.13**, which costs $696.11 including
fees at the fee rate that we observed (within the $700 limit) and pays $12.70 to $14.10 an hour across that range
of lengths.

**(g) The rules for handling the data, stated again for the final wave.** This wave's survey leaves the stimulus
file unchanged, and it applies all wave-3 values in memory. We fixed the decision rule above before any wave-3 data
existed. Calibration responses never enter a confirmatory analysis. We record the fuller descriptions, the new
margins of the check stimuli and the full history of the values of every pair (wave 1 to wave 2 to wave 3, with
the attribute changed in each wave and the reason) in `wave3/survey/wave3_pairs.json`, in the wave-3 design key and
in the Stage 1 protocol. When the final values are fixed, we write them and the fuller descriptions into the
stimulus file once, rebuild the extremity control, and adopt the new margins of the decoys.

## After the final wave (decided after the wave-3 data, and recorded here for completeness)

- **The final values.** On July 2, 2026, we wrote the final values into `stimuli/stimuli.json`.
  `stimuli/calibration_lock.py` records what we did with each pair, and `FINAL_LOCK_LIST_2026-07-02.json` gives the
  values, shares and intervals.
- **Pairs that met the decision rule.** As the calibration software read the wave-3 shares, twelve adjustable pairs
  met the decision rule. Later, we recomputed every share from the deposited data as the share of the compromise
  target itself, which is the share that the rule refers to. In the two invented categories whose attraction decoys
  favor the budget option, the electric kettles and the standing desks, the software had applied the band to the
  budget option's share. In the electric kettles, the compromise target started at 55.3 percent, so the pair fails
  the rule. Eleven of the eighteen adjustable pairs therefore met the rule.
- **The published pairs.** We measured the seven tier-1 pairs and reported their shares. One of them, the water
  bottles at 80.0 percent, lies outside the limits of 25 and 75 percent. It stays in the design with its measured
  baseline, and the pre-registered sensitivity analysis leaves it out.
- **Pairs kept although they failed the rule.** Six adjustable pairs failed the rule and stay in the design with
  their measured baselines: the backpacks (28.5 percent) and the restaurants (31.2 percent), both at new values,
  whose targets stay the less popular option; the earbuds at new values (61.0 percent) and the water bottles in
  pictures (59.1 percent), whose targets start ahead; the standing desks, whose compromise target started at 33.3
  percent and whose interval does not reach the band; and the electric kettles, whose compromise target started at
  55.3 percent. Where the compromise target starts ahead, the compromise test of that cell is only described. The
  plan was to drop such a category and use a spare one. After seeing the wave-3 data, we decided to keep the first
  five pairs, because each stayed inside the limits of 25 and 75 percent, and no spare invented category had been
  built. We kept the electric kettles because we read them as final at the time, and when the recount showed that
  they failed the rule, we kept them on the same terms as the other five. The pre-registered sensitivity analysis
  repeats every confirmatory test without these six pairs and without the published water bottles.
- **The pair removed.** The hard drives in pictures stayed above 75 percent in all three waves, and their three
  pictures cells left the design.
- **The realism comparison study** (`realism_study/`). We added this study after the invented categories missed the
  realism threshold in waves 2 and 3. It changes how we interpret the realism ratings, and it changes no value.
