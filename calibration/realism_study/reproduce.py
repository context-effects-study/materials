"""Rebuild the realism comparison from the study's de-identified export and compare it with the deposited
results (results/realism_results.json). Output of record: Web Appendix F, the realism comparison.

Run from the repository root:  python calibration/realism_study/reproduce.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import study_check  # noqa: E402

sys.exit(study_check.reproduce_realism())
