# The human exclusion rules (registered)

In a Registered Report the data-quality checks must be stated in advance, must not depend on the outcome,
and must be applied the same way in every condition, so they can never be tuned to help a hypothesis.
These are those checks. Every value below is a fixed number, decided before any data, applied identically
across all cells, tiers, formats and conditions. `analysis/ingest.py` applies them.

## The four rules

1. **Attention check.** Each participant sees one required multiple-choice item with a single correct
   answer ("To show you are reading carefully, please select 'Strongly agree'"), export column
   `attention_1`. A participant who does not select the correct option is excluded from every analysis.
   The correct option is recorded in each survey's mapping file.

2. **Fast responses.** Each choice page records how long it was on screen before the participant moved on
   (the Page Submit timer). A participant is excluded if the median of these times over their choice pages
   is below a fixed floor of 3 seconds: a choice made faster than the options can be read is not a
   considered choice. The floor is a fixed number, not a percentile of the collected data, so it cannot
   move with the sample.

3. **Duplicate, preview and incomplete responses.** Excluded: any response with
   `DistributionChannel = preview`; any response with `Finished = 0` (abandoned before the last choice);
   and a second response from the same Prolific id or `ResponseId` (the first complete one is kept).
   Prolific's allowlist prevents re-entry, and calibration participants are on the confirmatory studies'
   exclusion list, so no one appears in both.

4. **Symmetry.** The rules above are applied identically across every cell, structure, tier and format. No
   rule refers to the option a participant chose: exclusions depend only on attention, speed and
   completeness.

`analysis/ingest.py` also records, as an exclusion reason, any choice of an option that could not be chosen
(the unavailable phantom), which the survey's choice widget prevents, and any repeat of a product category
within one participant, which the scripts prevent by construction; both are checks that the survey worked,
not additional screening.

## Replacement

Excluded participants are replaced by the script-level top-up rule (`../docs/HUMAN_PROTOCOL.md`, section 4):
the scripts whose cells fall short are dealt again until each cell reaches its target (700, with the 350 and
350 tier split and the first-choice subsample preserved). Exclusion therefore does not unbalance the design.

## Reporting

The Stage 1 protocol states these rules. The Stage 2 results report the number excluded by each rule in each
cell, as evidence that the rules were applied symmetrically; the counts are written to the results pack
(`analysis/results_pack/numbers.json`).
