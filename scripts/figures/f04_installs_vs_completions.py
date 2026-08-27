#!/usr/bin/env python3
"""
04_hamburg_installs_vs_completions.py — Hamburg: private solar installations
vs. new residential buildings completed, 2015–2025. (Renamed from
D12_hamburg_solar_vs_completions_bar.py 2026-08-09 to narrative order;
content unchanged.)

Grouped bar chart, Hamburg only, Panel C (C_bundesland_panel_monthly.csv).
Operator type: private only (recommended default, matches the convention
used across the rest of the Descriptive series). Both series are annual
counts on a shared axis — comparable orders of magnitude, which is what
makes the crossover visible: completions and installs run roughly level
through 2022, then installs overtake completions once the mandate applies
from 2023.

This replaces the orphaned legacy figure `solar_gap_hamburg_2015_2025.png`
(script no longer exists) with a fresh build from the current panel.

Output: Auswertung/Descriptive Results/02_Hamburg/04_hamburg_installs_vs_completions.png
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SRC  = BASE / "data" / "panels" / "C_bundesland_panel_monthly.csv"
OUT  = BASE / "output" / "figures" / "f04_installs_vs_completions.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

C_SOLAR = "#D94F3D"
C_BUILD = "#8C8C8C"
C_VLINE = "#444444"

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#E5E5E5",
    "grid.linewidth": 0.6, "axes.axisbelow": True,
})

# ── Load and aggregate to annual, Hamburg only ────────────────────────────────
df = pd.read_csv(SRC)
df = df[df["bundesland"] == "Hamburg"].copy()
df["year"] = df["year_month"].str[:4].astype(int)
df = df[df["year"].between(2015, 2025)]

annual = df.groupby("year").agg(
    solar_privat=("solar_privat", "sum"),
    completions=("completions_wohngebaeude", "mean"),
).reset_index()

YEARS = annual["year"].tolist()
x = np.arange(len(YEARS))
w = 0.38

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 6.5))

b1 = ax.bar(x - w/2, annual["solar_privat"], width=w, color=C_SOLAR,
            label="Private solar installations", zorder=3)
b2 = ax.bar(x + w/2, annual["completions"], width=w, color=C_BUILD,
            label="New residential buildings completed", zorder=3)

for xyr, lbl in [(2023, "First mandate\nstep"), (2024, "Second mandate\nstep")]:
    xi = YEARS.index(xyr) - 0.5
    ax.axvline(xi, color=C_VLINE, lw=1.2, linestyle=":", zorder=2)
    ax.text(xi + 0.05, ax.get_ylim()[1], lbl, va="top", fontsize=8, color=C_VLINE)

ax.set_xticks(x)
ax.set_xticklabels(YEARS, fontsize=9)
ax.set_ylabel("Annual count", fontsize=10)
ax.set_xlabel("Year", fontsize=10)
ax.set_title(
    "Hamburg — Private Solar Installations vs. New Residential Buildings Completed (2015–2025)",
    fontsize=11, fontweight="bold", pad=10,
)
ax.legend(fontsize=9, framealpha=0.95, loc="upper left")

fig.text(0.5, 0.01,
         "Source: MaStR (Bundesnetzagentur), private (natürliche Person) installations only; "
         "Destatis Baufertigstellungen Wohngebäude. 2025 completions: latest available Destatis figure.",
         ha="center", fontsize=8, color="#777777", style="italic")

fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
print(annual)
