#!/usr/bin/env python3
"""Run every script behind a thesis figure or table in this directory."""
import subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPTS = [
    "01_mandate_timeline_states.py",
    "02_rate_hamburg_vs_germany.py",
    "03_rate_hamburg_vs_germany_indexed.py",
    "04_hamburg_installs_vs_completions.py",
    "05_hamburg_plz_growth.py",
    "06_border_groups_map.py",
    "07_border_parallel_trends.py",
    "D4_summary_statistics.py",
]

failed = []
for script in SCRIPTS:
    print(f"--- {script}")
    if subprocess.run([sys.executable, str(HERE / script)]).returncode != 0:
        failed.append(script)

print(f"\nDone: {len(SCRIPTS) - len(failed)}/{len(SCRIPTS)} scripts succeeded.")
if failed:
    print("Failed:", ", ".join(failed))
    sys.exit(1)
