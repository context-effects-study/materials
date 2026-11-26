"""Rebuild this wave's report from its de-identified export and compare every table row with the report of
record (results/calibration_report_wave1.md). Output of record: Web Appendix F, Tables WA-F2 and WA-F3 and the wave-1 column of Table WA-F7.

Run from the repository root:  python calibration/wave1/reproduce.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import study_check  # noqa: E402

sys.exit(study_check.reproduce_wave("wave1", "calibration_wave1_MAPPING_rng_corrected.json"))
