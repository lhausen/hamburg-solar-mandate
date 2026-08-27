#!/usr/bin/env python3
"""
02_rate_hamburg_vs_germany.py — Hamburg vs. Germany-average, solar
installations per 1,000 new residential buildings, 2015–2025. (Renamed from
D10_hamburg_vs_germany_avg_rate.py 2026-08-09 to narrative order; content
unchanged.)

Bundesland-level, Panel C (C_bundesland_panel_monthly.csv). Same rate
definition as D2a (private installs / residential completions * 1,000), but
a different comparison: Hamburg against a single "Germany average" line
rather than five individually highlighted states.

Germany average = simple (unweighted) mean of the per-state rate across all
16 Bundesländer each year — not weighted by completions or population, per
user decision 2026-08-08. Companion figure to D2a, not a replacement: D2a is
kept unchanged (five-state comparison); this isolates the single
Hamburg-vs.-average contrast the thesis narrative needs.

Output: Auswertung/Descriptive Results/01_Statewide_Comparison/02_rate_hamburg_vs_germany.png
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SRC  = BASE / "data" / "panels" / "C_bundesland_panel_monthly.csv"
OUT  = BASE / "output" / "figures" / "f02_rate_hh_vs_germany.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

C_HH   = "#D94F3D"
C_AVG  = "#2166AC"
C_GREY = "#CCCCCC"
C_VLINE = "#444444"

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#E5E5E5",
    "grid.linewidth": 0.6, "axes.axisbelow": True,
})

# ── Load and aggregate to annual rate per state ───────────────────────────────
df = pd.read_csv(SRC)
df["year"] = df["year_month"].str[:4].astype(int)
df = df[df["year"].between(2015, 2025)]

annual = df.groupby(["bundesland", "year"]).agg(
    solar_privat=("solar_privat", "sum"),
    completions=("completions_wohngebaeude", "mean"),
).reset_index()
annual["rate"] = annual["solar_privat"] / annual["completions"] * 1_000

n_states = annual["bundesland"].nunique()
germany_avg = annual.groupby("year")["rate"].mean()

YEARS = sorted(annual["year"].unique())

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 6.5))

for state in annual["bundesland"].unique():
    if state == "Hamburg":
        continue
    s = annual[annual["bundesland"] == state].set_index("year")["rate"]
    ax.plot(s.index, s.values, color=C_GREY, lw=0.9, alpha=0.7, zorder=1)

hh = annual[annual["bundesland"] == "Hamburg"].set_index("year")["rate"]
l_hh, = ax.plot(hh.index, hh.values, color=C_HH, lw=2.8, zorder=10, label="Hamburg")
l_avg, = ax.plot(germany_avg.index, germany_avg.values, color=C_AVG, lw=2.2,
                  linestyle="--", zorder=9, label=f"Germany average (simple mean, {n_states} states)")

for xyr, lbl in [(2023, "HH Neubau\nmandate"), (2024, "HH Bestand\nmandate")]:
    ax.axvline(xyr, color=C_VLINE, lw=1.2, linestyle=":", zorder=3)
    ax.text(xyr + 0.05, ax.get_ylim()[1] * 0.99, lbl,
            ha="left", va="top", fontsize=7.5, color=C_VLINE)

legend_handles = [l_hh, l_avg,
                   plt.Line2D([0], [0], color=C_GREY, lw=1.5, label="Other Bundesländer")]

ax.set_xticks(YEARS)
ax.set_xticklabels(YEARS, rotation=30, ha="right", fontsize=9)
ax.set_ylabel("Private solar installations per 1,000 new residential buildings", fontsize=10)
ax.set_xlabel("Year", fontsize=10)
ax.set_title(
    "Hamburg vs. Germany Average — Private Installations per 1,000 Residential Completions (2015–2025)",
    fontsize=11, fontweight="bold", pad=10,
)
ax.legend(handles=legend_handles, loc="upper left", fontsize=9, framealpha=0.95)

fig.text(0.5, 0.02,
         "Source: MaStR (Bundesnetzagentur); Destatis (Baufertigstellungen Wohngebäude). "
         "Germany average = unweighted mean of the per-state rate across all 16 Bundesländer.",
         ha="center", fontsize=8, color="#777777", style="italic")
fig.text(0.5, -0.005,
         "2025 completions: latest available Destatis figure.",
         ha="center", fontsize=8, color="#777777", style="italic")

fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
