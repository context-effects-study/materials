# The exclusion rules for the human data (pre-registered)

In a Registered Report, the checks of data quality must be stated in advance, must not depend on the outcome, and
must apply in the same way in every condition, so that nobody can tune them to favor a hypothesis. This document
states those checks. Every value below is a fixed number that we set before collecting any data, and each rule
applies in the same way to all cells, tiers, formats and conditions. `analysis/ingest.py` applies the rules.

## The four rules

1. **Attention check.** Each participant answers one required multiple-choice question with one correct answer ("To
   show you are reading carefully, please select 'Strongly agree'"), in the export column `attention_1`. We exclude
   from every analysis a participant who does not select the correct option. The design key of each survey records
   the correct option.

2. **Fast responses.** For each choice page, the survey records how long the page was on screen before the
   participant moved on (the Page Submit timer). We exclude a participant whose median time across the choice pages
   is below a fixed floor of 3 seconds, because nobody can read the options and make a considered choice that fast.
   The floor is a fixed number, not a percentile of the collected data, so it cannot move with the sample.

3. **Duplicate, preview and incomplete responses.** We exclude any response with `DistributionChannel = preview`,
   any response with `Finished = 0` (the participant stopped before the last choice), and any second response with
   the same Prolific id or `ResponseId` (we keep the first complete one). Prolific's allowlist prevents a second
   entry, and the participants of the calibration studies are on the exclusion list of the confirmatory studies, so
   nobody takes part in both.

4. **The same rules in every condition.** The rules above apply in the same way to every cell, structure, tier and
   format. No rule refers to the option that a participant chose. An exclusion depends only on attention, speed and
   completion.

`analysis/ingest.py` also records two further reasons for exclusion: a choice of an option that cannot be chosen (the
unavailable phantom), which the survey's choice widget prevents, and a second choice in the same product category
by one participant, which the scripts prevent by design. Both are checks that the survey worked, not further rules
for screening participants.

## Replacement

We replace excluded participants under the rule for recruiting more participants, which works by script
(`../docs/HUMAN_PROTOCOL.md`, section 4). We open new places for the scripts whose cells are short, until each cell
reaches its target: 700 choices, split 350 and 350 between the tiers, with the first choices of each cell kept.
Exclusions therefore do not unbalance the design.

## Reporting

The Stage 1 protocol states these rules. In the Stage 2 results, we will report the number of participants that
each rule excluded in each cell, to show that the rules applied in the same way everywhere. The analysis writes
these counts to the results files (`analysis/results_pack/numbers.json`).
