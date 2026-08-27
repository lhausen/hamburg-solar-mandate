#!/usr/bin/env python3
"""
run_all.py -- reproduce every estimate, table and figure of the thesis.

Two entry points, depending on what is available locally:

  python3 run_all.py             Start from the panels shipped in data/panels/
                                 (the default; no raw download needed).
  python3 run_all.py --from-raw  Full rebuild: parse the MaStR bulk export,
                                 rebuild the panels, then run everything.
                                 Requires the export described in data/raw/.

Steps and what they produce are listed in README.md. Exits non-zero if any
step fails, so this doubles as the reproducibility check.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
FROM_RAW = "--from-raw" in sys.argv

RAW_STEPS = [
    "scripts/00_parse_mastr_bulk.py",
    "scripts/01_build_panel_a.py",
    "scripts/02_build_mandate_index.py",
    "scripts/03_build_did_panel.py",
    "scripts/04_build_scm_panel.py",
    "scripts/08_make_funnel_table.py",
    "scripts/09_data_quality_audit.py",
]

PANEL_STEPS = [
    "scripts/05_run_did.py",
    "scripts/06_run_scm.py",
    "scripts/figures/f01_mandate_timeline.py",
    "scripts/figures/f02_rate_hh_vs_germany.py",
    "scripts/figures/f03_rate_indexed.py",
    "scripts/figures/f04_installs_vs_completions.py",
    "scripts/figures/f05_plz_growth_map.py",
    "scripts/figures/f06_border_map.py",
    "scripts/figures/f07_parallel_trends.py",
    "scripts/figures/f08_completions_states.py",
    "scripts/figures/f09_summary_statistics.py",
]

steps = (RAW_STEPS + PANEL_STEPS) if FROM_RAW else PANEL_STEPS

failed = []
for step in steps:
    print(f"\n{'='*60}\nRunning {step} ...\n{'='*60}")
    result = subprocess.run([sys.executable, str(HERE / step)])
    if result.returncode != 0:
        failed.append(step)

print(f"\n{'='*60}")
print(f"Done: {len(steps) - len(failed)}/{len(steps)} steps succeeded.")
if failed:
    print("Failed: " + ", ".join(failed))
    sys.exit(1)
