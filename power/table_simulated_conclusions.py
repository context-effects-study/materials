"""table_simulated_conclusions.py: Table WA-E6, how often the analysis reached each conclusion for each of the
thirteen simulated models.

It reads power/model_noise_stability_runs.csv and counts, in the runs in which both positive controls held, the
conclusion reached for each model (S1 to S7, two failures at once, and the conclusions that name a pattern
that the model was not built to show). Standard library only.

Output: power/TABLE_SIMULATED_CONCLUSIONS.md.
Manuscript: Analysis Plan (Tests of the Three Accounts) and Web Appendix E.

Run: python power/table_simulated_conclusions.py      (after power/model_noise_stability.py)
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "analysis")))
import analyze  # noqa: E402
import synth  # noqa: E402

# the simulated models, in the order of the conclusions they were built to show, with a plain description
ROWS = [
    ("FAITHFUL", "Matches people everywhere"),
    ("DIVIDED_A", "Matches people (a second family)"),
    ("CONVERGE_NEW", "Matches people and names the attraction and compromise decoys"),
    ("WALK1_PARROT", "Matches people at the published values only (example 1)"),
    ("PARROT", "Published values only, and names the upscaling decoy it does not follow"),
    ("REASONER", "Falls short where the set gives no reason"),
    ("OVERRIDER", "Names every decoy and chooses against it"),
    ("WALK2_MIXED", "Reverses compromise and names its decoy (example 2)"),
    ("R4_ARGUABLE_OVERRIDE", "Misses attraction and compromise and names their decoys (example 3)"),
    ("DIVIDED_B", "Reverses every effect without naming a decoy"),
    ("CONVERGE_OLD", "Falls short on every effect"),
    ("R4_ARGUABLE_NORECOG", "Misses attraction and compromise without naming a decoy"),
    ("OVERSHOOT_T1", "Three times the human effect at the published values"),
]
SINGLE = ["S1", "S2", "S3", "S4", "S5", "S6", analyze.NOT_RESOLVED_SCENARIO]


def main():
    with open(os.path.join(HERE, "model_noise_stability_runs.csv"), encoding="utf-8") as f:
        every = [r for r in csv.DictReader(f) if r["noise"] == "independent"]
    # the runs in which both positive controls held (on the synthetic lattice the frequency-decoy control has one
    # calibrated premium-target cell, against three in the design, and a failed control leaves two tests not run)
    runs = [r for r in every if not r.get("controls_failed")]
    n = len(runs)
    head = "| Simulated model | Built to show | " + " | ".join(SINGLE) + " | Two failures | Wrong |"
    lines = ["**TABLE WA-E6.** CONCLUSIONS FOR THE SIMULATED MODELS", "", head,
             "|" + "---|" * (len(SINGLE) + 4)]
    total_wrong = 0
    for m, desc in ROWS:
        want = synth.MODEL_ARCHETYPES[m]["scenario"]
        got = [r[f"route_{m}"] for r in runs]
        cells = [str(sum(1 for g in got if g == s)) for s in SINGLE]
        joint = sum(1 for g in got if analyze.JOINT in g)
        wrong = sum(1 for r in runs if r[f"out_{m}"] == "wrong")
        total_wrong += wrong
        lines.append(f"| {desc} | {want.replace(analyze.JOINT, ' and ')} | " + " | ".join(cells)
                     + f" | {joint} | {wrong} |")
    share = total_wrong / (n * len(ROWS)) if n else 0.0
    lines += ["", f"*Note.* Each row counts the conclusions reached in the {n} of {len(every)} runs of the full analysis at "
              "the planned sizes in which both positive controls held, "
              "with every model call an independent draw at the share that we built into the model and every result "
              "judged against its 95% interval. S1 to S7 are the conclusions of the manuscript's Table 5; S7 is "
              "inconclusive. A conclusion with two failures present is counted under two failures. A conclusion is "
              "wrong when it names a pattern that the model was not built to show; an inconclusive result that "
              "leaves the built pattern possible is not wrong. Across the thirteen models, "
              f"{total_wrong} of {n * len(ROWS):,} runs ({share * 100:.1f}%) reached a wrong conclusion.", ""]
    text = "\n".join(lines)
    open(os.path.join(HERE, "TABLE_SIMULATED_CONCLUSIONS.md"), "w", encoding="utf-8", newline="\n").write(text)
    print(text)


if __name__ == "__main__":
    main()
