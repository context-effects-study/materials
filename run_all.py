#!/usr/bin/env python3
"""run_all.py: regenerate every reproducible output of this repository and check each one against the deposited
copy.

Run from the repository root:

    python run_all.py                        # everything below except the long checks (about 7 minutes)
    python run_all.py --part calibration     # one part only: stimuli, calibration, surveys, models, power,
                                             # analysis or figures (the option can be repeated)
    python run_all.py --quick                # skip the slowest steps (clustered power, first-choice rule
                                             # simulation, analysis tests)
    python run_all.py --full                 # also the four long checks, about 80 minutes in all: the
                                             # routing stability of the planted model profiles, the
                                             # resolution statement, the faithful profile at larger samples,
                                             # and mutation testing of the analysis

Each step runs one of the repository's own scripts with the same Python interpreter, then compares what it
wrote with the file deposited here. Files regenerated in place must come out identical (images pixel for
pixel); the calibration reports are written to reproduction/ and compared row by row with the reports of
record. Every script that draws random numbers uses a fixed seed, named in its header. Files that the checks
write besides the deposited ones (check records, a synthetic export, the assignment service's bundle) are
moved into reproduction/ at the end, so the deposited folders stay as they were. The summary lists every step;
the exit code is 0 only when every step that ran reproduced.

Nothing here reads the network or changes the data in calibration/*/data/raw/.
"""
import argparse
import csv
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
REPRO = os.path.join(ROOT, "reproduction")
RESULTS = []
PARTS = ("stimuli", "calibration", "surveys", "models", "power", "analysis", "figures")


def path(*parts):
    return os.path.join(ROOT, *parts)


def py(script, *args, check_text=None, timeout=7200):
    """Run one of the repository's scripts; return its printed output. Stops on a non-zero exit."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, script, *args], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=timeout)
    out = p.stdout + p.stderr
    if p.returncode != 0:
        raise RuntimeError(f"{script} {' '.join(args)} exited with {p.returncode}:\n{out[-2500:]}")
    if check_text and not re.search(check_text, out):
        raise RuntimeError(f"{script}: expected output /{check_text}/ not found:\n{out[-2500:]}")
    return out


def snapshot(*patterns):
    files = {}
    for pat in patterns:
        for f in glob.glob(path(*pat.split("/")), recursive=True):
            if os.path.isfile(f):
                files[f] = open(f, "rb").read()
    return files


def png_pixels(data):
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    return im.size, im.mode, im.tobytes()


def compare(before, ignore_lines=None):
    """Files in `before` must be identical now (a PNG pixel for pixel), apart from lines matching ignore_lines."""
    diffs = []
    for f, old in before.items():
        new = open(f, "rb").read() if os.path.exists(f) else b""
        if f.endswith(".png"):
            if new == old or (new and png_pixels(new) == png_pixels(old)):
                continue
            diffs.append(os.path.relpath(f, ROOT))
            continue
        # line endings are the operating system's business, not the content's
        new, old = new.replace(b"\r\n", b"\n"), old.replace(b"\r\n", b"\n")
        if new == old:
            continue
        if ignore_lines:
            rx = re.compile(ignore_lines)
            keep = lambda b: [l for l in b.decode("utf-8", "replace").splitlines() if not rx.search(l)]  # noqa: E731
            if keep(new) == keep(old):
                continue
        diffs.append(os.path.relpath(f, ROOT))
    return diffs


def step(name, output, fn):
    """Run one step and record its result. `output` names the manuscript output it reproduces."""
    t0 = time.time()
    try:
        verdict = fn() or "reproduced"
    except Exception as e:  # noqa: BLE001  (a failed step is reported, and the remaining steps still run)
        verdict = "FAILED: " + str(e).strip().splitlines()[0][:200]
        print(str(e)[-3000:])
    RESULTS.append((name, output, verdict, time.time() - t0))
    print(f"[{time.time() - t0:6.1f} s] {name}: {verdict}", flush=True)


def diffs_verdict(diffs, note="identical"):
    if diffs:
        raise RuntimeError("differs from the deposited copy: " + ", ".join(diffs))
    return note


def park(*relpaths):
    """Move files or folders the checks wrote outside reproduction/ into reproduction/ (the same relative path),
    so the deposited folders stay exactly as deposited. Nothing is deleted: an earlier parked copy is kept
    under a numbered name."""
    for rel in relpaths:
        src = path(*rel.split("/"))
        if not os.path.exists(src):
            continue
        dest = os.path.join(REPRO, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        n, target = 1, dest
        while os.path.exists(target):
            n += 1
            target = f"{dest}.{n}"
        shutil.move(src, target)


# ---------------------------------------------------------------------------------------------------------
# stimuli
# ---------------------------------------------------------------------------------------------------------
def stimuli_file():
    # Creates stimuli/stimuli.json: every stimulus value behind the Method, Table 2 and Web Appendix B,
    # and the final calibrated values of Web Appendix F (Table WA-F6), checked against the lock list.
    before = snapshot("stimuli/stimuli.json")
    py("stimuli/build_stimuli.py")
    return diffs_verdict(compare(before))


def stimuli_validator():
    # Checks the geometry of every stimulus (Web Appendix B definitions): must report no FAIL and no WARN.
    out = py("stimuli/validate_stimuli.py", check_text=r"TOTALS: \d+ PASS, 0 WARN, 0 FAIL")
    return re.search(r"TOTALS: (\d+) PASS", out).group(1) + " checks pass"


def appendix_tables():
    # Creates stimuli/STIMULUS_APPENDIX.md: the stimulus tables of Web Appendix B.
    before = snapshot("stimuli/STIMULUS_APPENDIX.md")
    py("stimuli/gen_appendix_table.py")
    return diffs_verdict(compare(before))


# ---------------------------------------------------------------------------------------------------------
# calibration
# ---------------------------------------------------------------------------------------------------------
def calibration_study(study):
    # Rebuilds one calibration study's reported numbers from its deposited export with the study's own
    # calibration/<study>/reproduce.py: Web Appendix F, Tables WA-F2 and WA-F3 (wave 1), WA-F4 (wave 2), WA-F5
    # (wave 3), the comprehension checks of Table WA-F7, and the realism comparison (published pages 4.17 to
    # 5.05; published minus invented +0.18, 95% interval -0.07 to +0.42).
    def run():
        out = py(f"calibration/{study}/reproduce.py")
        return out.strip().splitlines()[-1]
    return run


def survey_views():
    # Creates calibration/<study>/survey/<survey>.pdf: the printable view of each fielded calibration survey.
    before = snapshot("calibration/*/survey/*.pdf")
    py("surveys/print_survey.py")
    return diffs_verdict(compare(before), f"{len(before)} survey views identical")


def choice_files():
    # Creates calibration/*/data/processed/: the analysis-ready files (one row per kept choice or rating,
    # and the exclusion record of every export row).
    before = snapshot("calibration/*/data/processed/*.csv")
    py("calibration/make_choice_files.py")
    return diffs_verdict(compare(before))


def calibration_surveys():
    # Rebuilds the design of the three calibration surveys from the fielded files and checks them against the
    # value kits and the stimulus file they were built from.
    out = py("surveys/calibration_selftest.py", check_text=r"-- (\d+)/\1 checks pass --")
    m = re.search(r"-- (\d+)/(\d+) checks pass --", out)
    return f"{m.group(1)} of {m.group(2)} checks pass"


# ---------------------------------------------------------------------------------------------------------
# surveys
# ---------------------------------------------------------------------------------------------------------
def surveys():
    # Creates the five confirmatory surveys and their design keys (surveys/out/): the Human study section of
    # the Method and the cell counts of Table 2. The files must equal the deposited ones byte for byte.
    before = snapshot("surveys/out/*")
    py("surveys/generate_qsf.py")
    py("surveys/generate_survey.py")
    return diffs_verdict(compare(before), "five surveys and five mappings identical")


def survey_balance():
    # Creates the balance proofs of the participant scripts (surveys/DEAL_RESULTS.md,
    # surveys/SCRIPTSET_RESULTS.md) and the 180 backbone scripts (surveys/scriptset_180.csv).
    before = snapshot("surveys/DEAL_RESULTS.md", "surveys/SCRIPTSET_RESULTS.md", "surveys/scriptset_180.csv")
    py("surveys/deal.py")
    py("surveys/scriptset_sim.py")
    return diffs_verdict(compare(before))


def survey_checks():
    # Rebuilds the backbone design from its survey file and checks it; checks the export reader on a
    # synthetic export (the exclusion rules of surveys/SURVEY_SPEC.md).
    py("surveys/qsf_selftest.py")
    py("analysis/ingest.py", "--selftest", check_text="INGEST PIPELINE GREEN")
    return "backbone design and export reader pass"


def assignment_service():
    # Rebuilds the assignment service's script tables and checks that the deal hashes equal the ones recorded
    # in the survey mappings, then checks the three surveys that use the service against those tables.
    py("surveys/assign_worker/build_worker_data.py")
    manifest = json.load(open(path("surveys", "assign_worker", "src", "manifest.json"), encoding="utf-8"))
    recorded = set()
    for m in glob.glob(path("surveys", "out", "*_MAPPING.json")):
        recorded |= set(re.findall(r'"deal_sha256[^"]*"\s*:\s*"([0-9a-f]{8,})"', open(m, encoding="utf-8").read()))
    fresh = set(re.findall(r'"deal_sha256[^"]*"\s*:\s*"([0-9a-f]{8,})"', json.dumps(manifest)))
    if not fresh or not fresh <= recorded:
        raise RuntimeError(f"deal hashes {sorted(fresh)} not all recorded in the survey mappings")
    py("surveys/survey_selftest.py")
    return f"{len(fresh)} deal hashes match the survey mappings; surveys 3 and 4 pass their check"


def survey_package():
    # The survey package holds the same five surveys and mappings as surveys/out/, plus the walkthrough and
    # the pictures, and a checksum list.
    import hashlib
    pkg = path("survey_package")
    bad = []
    for line in open(os.path.join(pkg, "SHA256SUMS.txt"), encoding="utf-8"):
        if line.strip():
            h, name = line.strip().split(None, 1)
            f = os.path.join(pkg, *name.strip().split("/"))
            if not os.path.exists(f) or hashlib.sha256(open(f, "rb").read()).hexdigest() != h:
                bad.append(name)
    for f in glob.glob(path("surveys", "out", "*")):
        twin = os.path.join(pkg, os.path.basename(f))
        if os.path.exists(twin) and open(twin, "rb").read() != open(f, "rb").read():
            bad.append(os.path.basename(f) + " (differs from surveys/out)")
    if bad:
        raise RuntimeError("survey package: " + ", ".join(bad))
    return "every checksum verifies; the surveys equal surveys/out"


# ---------------------------------------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------------------------------------
def model_plan():
    # Creates models/MANIFEST.md, the exact call plan of the Model study section and Table 2, and checks the
    # runner's registry, prompt materials and requests without any network call.
    before = snapshot("models/MANIFEST.md")
    py("models/build_manifest.py")
    py("models/run.py", "--selftest")
    py("models/selftest_mutants.py")
    return diffs_verdict(compare(before), "call plan identical; runner checks pass")


def model_prompts():
    # Creates models/SAMPLE_CALLS.jsonl from the runner's dry run (synthetic replies, no network).
    before = snapshot("models/SAMPLE_CALLS.jsonl")
    n = 1
    while os.path.exists(os.path.join(REPRO, f"model_dry_run_{n}")):   # a fresh folder for every run
        n += 1
    out_dir = os.path.join(REPRO, f"model_dry_run_{n}")
    os.makedirs(out_dir)
    py("models/run.py", "--out-dir", out_dir)
    new = open(os.path.join(out_dir, "SAMPLE_CALLS.jsonl"), "rb").read()
    old = list(before.values())[0]
    if new != old:
        raise RuntimeError("the sample prompts differ from models/SAMPLE_CALLS.jsonl")
    return "identical"


# ---------------------------------------------------------------------------------------------------------
# power
# ---------------------------------------------------------------------------------------------------------
def power_levels():
    # Creates power/RESULTS.md and power/POWER_ADDED_CELLS.md: the power paragraph of the Method
    # (analytic and simulated power per category, pooled and first-choice; seed 11).
    before = snapshot("power/RESULTS.md", "power/POWER_ADDED_CELLS.md")
    py("power/power_sim.py")
    py("power/power_added_cells.py")
    return diffs_verdict(compare(before))


def power_registered_tests():
    # Creates power/POWER_FORMAT_INTERACTION.md (Table WA-E3) and power/POWER_COMPROMISE_POOLED.md: the power
    # of the format interaction tests and of the pooled compromise test (seed 20260929).
    before = snapshot("power/POWER_FORMAT_INTERACTION.md", "power/POWER_COMPROMISE_POOLED.md")
    py("power/power_format_interaction.py")
    py("power/power_compromise_pooled.py")
    return diffs_verdict(compare(before))


def first_trial_rule():
    # Creates power/FIRST_TRIAL_RULE_SIM.md (Table WA-E2): the false-alarm rate and power of the registered
    # first-choice check (seed 20260929).
    before = snapshot("power/FIRST_TRIAL_RULE_SIM.md")
    py("power/first_trial_rule_sim.py")
    return diffs_verdict(compare(before))


def power_clustered():
    # Creates power/CLUSTERED_POWER.md: the effect of within-participant correlation on the pooled tests
    # (Method, power paragraph; seed 7; needs numpy).
    before = snapshot("power/CLUSTERED_POWER.md")
    py("power/clustered_power.py")
    return diffs_verdict(compare(before))


def noise_stability():
    # Creates power/MODEL_NOISE_STABILITY.md and power/model_noise_stability_runs.csv: how often each planted
    # model profile routes to its intended scenario under the sampling noise of the repeated draws.
    before = snapshot("power/MODEL_NOISE_STABILITY.md", "power/model_noise_stability_runs.csv")
    py("power/model_noise_stability.py")
    return diffs_verdict(compare(before, ignore_lines=r"runs of the full pipeline|\d+ s\b"))


def resolution_statement():
    # Creates power/RESOLUTION_STATEMENT.md (Table WA-E4), power/resolution_statement_runs.csv and
    # power/resolution_statement_summary.json: the smallest true difference each pattern test and class boundary
    # resolves in 80 percent of runs at the planned sizes.
    before = snapshot("power/RESOLUTION_STATEMENT.md", "power/resolution_statement_runs.csv",
                      "power/resolution_statement_summary.json")
    py("power/resolution_statement.py", timeout=7200)
    return diffs_verdict(compare(before, ignore_lines=r"runs of the full pipeline|\d+ s\b"))


def faithful_by_sample():
    # Creates power/FAITHFUL_RESOLUTION_BY_SAMPLE.md: the sample the planted faithful profile needs to route to S1.
    before = snapshot("power/FAITHFUL_RESOLUTION_BY_SAMPLE.md")
    py("power/faithful_resolution_by_sample.py")
    return diffs_verdict(compare(before, ignore_lines=r"runs of the full pipeline|\d+ s\b"))


# ---------------------------------------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------------------------------------
def constants_table():
    # Creates analysis/REGISTERED_CONSTANTS.md: Table WA-E1, every registered cutoff, printed from the one
    # structure the analysis reads.
    before = snapshot("analysis/REGISTERED_CONSTANTS.md")
    py("analysis/print_constants.py")
    return diffs_verdict(compare(before))


def rehearsal():
    # Creates analysis/results_pack/ and analysis/RESULTS_PACK_SELFTEST.md: the analysis plan run end to end
    # on synthetic data (Steps 0 to 3, Table 4 routing, the two walk-throughs of Web Appendix C, the
    # secondary readings of Web Appendix E). Seed 20260613. Every data file must be identical; only the
    # recorded runtime and interpreter lines change between runs.
    before = snapshot("analysis/results_pack/**/*", "analysis/RESULTS_PACK_SELFTEST.md")
    py("analysis/analyze.py", check_text="ALL CHECKS PASS")
    park("analysis/results_pack/dashboard_data.json", "analysis/results_pack/figures")
    return diffs_verdict(compare(before, ignore_lines=r"runtime|python:|platform|seconds"),
                         "all checks pass; every results file identical")


def demo_data():
    # Creates analysis/demo_data/: the rehearsal's synthetic data in the registered formats (the demonstration
    # data file of the Stage 1 guidelines).
    before = snapshot("analysis/demo_data/*")
    py("analysis/write_demo_data.py")
    return diffs_verdict(compare(before), "human table and model log identical")


def analysis_tests():
    # Tests of every rule the analysis applies (each builds data in which one rule decides the outcome).
    out = py("analysis/test_analysis.py", "--no-write", check_text=r"OVERALL: ALL PASS")
    n = len(re.findall(r"^\| test_\w+ \| PASS \|", out, re.M))
    return f"{n} tests pass"


def mutation_testing():
    # Breaks one rule at a time in a scratch copy of the analysis and requires a test or the rehearsal to fail.
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "analysis/mutate_checks.py"], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    park("analysis/MUTATION_REPORT.md")
    m = re.search(r"(\d+) of (\d+) mutants killed", p.stdout + p.stderr)
    if not m:
        raise RuntimeError("no mutation summary:\n" + (p.stdout + p.stderr)[-2000:])
    return f"{m.group(1)} of {m.group(2)} mutants killed (report in reproduction/analysis/MUTATION_REPORT.md)"


# ---------------------------------------------------------------------------------------------------------
# figures (need Playwright with Chromium, Pillow and matplotlib)
# ---------------------------------------------------------------------------------------------------------
def figure(script, *files):
    def run():
        before = snapshot(*files)
        py(script)
        return diffs_verdict(compare(before))
    return run


def stimulus_figures():
    # Creates figures/stimulus_figures/ (Figures WA-B1 onward) and stimulus-explorer.html, with every check
    # of the builder (values, words and roles against stimuli.json, text size and boxes, the explorer opened
    # offline with the network blocked).
    before = snapshot("figures/stimulus_figures/*.png", "stimulus-explorer.html")
    py("figures/build_stimulus_figures.py", check_text="ALL CHECKS PASSED")
    return diffs_verdict(compare(before), f"{len(before) - 1} figures and the explorer identical")


STEPS = [
    ("stimuli", "Stimulus file", "Method; Table 2; Web Appendix B; Table WA-F6", stimuli_file, ""),
    ("stimuli", "Stimulus validator", "Web Appendix B", stimuli_validator, ""),
    ("stimuli", "Stimulus appendix tables", "Web Appendix B", appendix_tables, ""),
    ("calibration", "Calibration wave 1", "Tables WA-F2, WA-F3, WA-F7", calibration_study("wave1"), ""),
    ("calibration", "Calibration wave 2", "Tables WA-F4, WA-F7", calibration_study("wave2"), ""),
    ("calibration", "Calibration wave 3", "Tables WA-F5, WA-F7", calibration_study("wave3"), ""),
    ("calibration", "Realism comparison", "Web Appendix F, realism comparison", calibration_study("realism_study"), ""),
    ("calibration", "Calibration processed files", "calibration/*/data/processed", choice_files, ""),
    ("calibration", "Calibration survey checks", "Web Appendix F", calibration_surveys, ""),
    ("calibration", "Calibration survey views", "the four fielded surveys, printable", survey_views, ""),
    ("surveys", "Confirmatory surveys", "Method, Human study; Table 2", surveys, ""),
    ("surveys", "Script balance", "Method, Human study", survey_balance, ""),
    ("surveys", "Survey and reader checks", "Method, Human study; exclusion rules", survey_checks, ""),
    ("surveys", "Assignment service tables", "Method, Human study", assignment_service, ""),
    ("surveys", "Survey package", "the surveys ready to import", survey_package, ""),
    ("models", "Model call plan", "Method, Model study; Table 2; Table 3", model_plan, ""),
    ("models", "Sample prompts", "Method, Model study; Web Appendix D", model_prompts, ""),
    ("power", "Power", "Method, power paragraph", power_levels, ""),
    ("power", "Power of the format and compromise tests", "Web Appendix E, Table WA-E3", power_registered_tests, ""),
    ("power", "First-choice rule simulation", "Web Appendix E, Table WA-E2", first_trial_rule, "slow"),
    ("power", "Clustered power", "Method, power paragraph", power_clustered, "slow"),
    ("power", "Routing stability of the planted profiles", "Analysis Plan; Web Appendix E", noise_stability, "full"),
    ("power", "Resolution statement", "Analysis Plan; Web Appendix E, Table WA-E4", resolution_statement, "full"),
    ("power", "Faithful profile at larger samples", "Analysis Plan; Web Appendix E", faithful_by_sample, "full"),
    ("analysis", "Registered constants", "Web Appendix E, Table WA-E1", constants_table, ""),
    ("analysis", "Analysis dress rehearsal", "Analysis Plan; Table 4; Web Appendices C and E", rehearsal, ""),
    ("analysis", "Demonstration data", "analysis/demo_data", demo_data, ""),
    ("analysis", "Analysis explorer", "Analysis Plan; Figure 3; Table 4",
     figure("analysis/build_analysis_explorer.py", "analysis-explorer.html"), ""),
    ("analysis", "Analysis tests", "Analysis Plan", analysis_tests, "slow"),
    ("analysis", "Mutation testing", "Analysis Plan", mutation_testing, "full"),
    ("figures", "Figure WA-F1", "Web Appendix F, Figure WA-F1",
     figure("figures/build_figure_waf1.py", "figures/figure_waf1.png"), ""),
    ("figures", "Stimulus figures and explorer", "Web Appendix B figures; the stimulus explorer", stimulus_figures, ""),
]

# files the checks write outside reproduction/, moved there at the end
BY_PRODUCTS = ("analysis/out", "analysis/INGEST_CHECK.md", "analysis/SYNTH_CHECK.md", "analysis/ANALYSIS_TEST_REPORT.md",
               "surveys/SURVEY_CHECK.md", "surveys/assign_worker/src/scripts_data.js",
               "surveys/assign_worker/src/manifest.json", "stimuli/VALIDATION_REPORT.md")


def main():
    ap = argparse.ArgumentParser(description="Regenerate and check every reproducible output.")
    ap.add_argument("--part", action="append", choices=PARTS, help="run one part only (may be repeated)")
    ap.add_argument("--quick", action="store_true", help="skip the slow steps")
    ap.add_argument("--full", action="store_true", help="also run the two long checks")
    a = ap.parse_args()
    parts = set(a.part or PARTS)
    t0 = time.time()
    versions = []
    for mod in ("numpy", "matplotlib", "PIL", "playwright"):
        try:
            from importlib.metadata import version
            versions.append(f"{mod} {version({'PIL': 'pillow'}.get(mod, mod))}")
        except Exception:  # noqa: BLE001
            versions.append(f"{mod} not installed")
    print(f"Python {platform.python_version()} on {platform.system()} {platform.release()}; " + ", ".join(versions))

    for part, name, output, fn, speed in STEPS:
        if part not in parts:
            continue
        if speed == "full" and not a.full:
            RESULTS.append((name, output, "skipped (run with --full)", 0.0))
            continue
        if speed == "slow" and a.quick:
            RESULTS.append((name, output, "skipped (--quick)", 0.0))
            continue
        step(name, output, fn)
    park(*BY_PRODUCTS)

    print("\nSummary")
    width = max(len(r[0]) for r in RESULTS)
    for name, output, verdict, secs in RESULTS:
        print(f"  {name:<{width}}  {secs:6.1f} s  {verdict}   [{output}]")
    failed = [r for r in RESULTS if r[2].startswith("FAILED")]
    print(f"\n{len(RESULTS) - len(failed)} of {len(RESULTS)} steps reproduced or skipped; "
          f"{len(failed)} failed; total {time.time() - t0:.0f} s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
