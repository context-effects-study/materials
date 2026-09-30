"""Rebuild this wave's report from its de-identified export and compare every table row with the report of
record (results/calibration_report_wave2.md). Output of record: Web Appendix F, Table WA-F4 and the wave-2 column of Table WA-F7.

Run from the repository root:  python calibration/wave2/reproduce.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import study_check  # noqa: E402

sys.exit(study_check.reproduce_wave("wave2", "calibration_wave2_MAPPING.json"))
