#!/usr/bin/env python3
"""
A1_completions_bundeslaender.py — Appendix figure: residential building
completions by federal state, 2015-2025. Supports Chapter 6.1's claim that
the post-2022 drop in completions is nationwide, not Hamburg-specific.

New 2026-08-17 (user decision): no prior script/figure for this comparison
was found under _Additional/ (searched by content, not just filename), so
this is a new build, not a restyle of an existing one.

Data: Daten/Neubaudaten/completions_bundesland_annual.csv (Destatis
31121-0100), all 16 Bundesländer, 2015-2025 — the same source
build_panel_e.py reads for Panel C, at its native Bundesland x year
resolution (no monthly broadcast, unlike Panel C).

Log y-axis, not indexed to 2015=100: the 16 states span roughly two orders
of magnitude in completions (Nordrhein-Westfalen ~20,000/year vs. Bremen/
Saarland ~500-1,000/year), so a linear axis would flatten every small state
to a line near zero. Considered indexing every series to its own 2015 value
(the approach used in 03_rate_hamburg_vs_germany_indexed.py) but chose log
scale instead: it keeps each state's actual completions count on the axis
(so the reader can still see NRW is ~20x Bremen), and on a log axis equal
*percentage* changes produce equal vertical drops — which is exactly the
"shared post-2022 decline" comparison this figure exists to make, without
adding a second normalization step on top of the raw Destatis figures used
everywhere else in the thesis.

Only Hamburg is color-highlighted; the other 15 states are drawn as thin
grey ("dezent") lines with a single "Other federal states" legend entry —
same convention as 02/03_rate_hamburg_vs_germany*.py.

Output:
  Auswertung/Descriptive Results/01_Statewide_Comparison/A1_completions_bundeslaender.png
  Thesis-Overleaf/figures/A1_completions_bundeslaender.png (copy)
"""


import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SRC  = BASE / "data" / "aux" / "completions_bundesland_annual.csv"
OUT  = BASE / "output" / "figures" / "f08_completions_states.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

C_HH    = "#D94F3D"
C_GREY  = "#CCCCCC"
C_VLINE = "#444444"

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#E5E5E5",
    "grid.linewidth": 0.6, "axes.axisbelow": True,
})

# ── Load ────────────────────────────────────────────────────────────────────
df = pd.read_csv(SRC)
df = df[df["year"].between(2015, 2025)]

# Plausibility check: Germany-wide totals should match Destatis 31121-0100
# 2022-2025 (103,525 / 96,827 / 76,073 / 58,885).
germany_totals = df.groupby("year")["completions_wohngebaeude"].sum()
print("Germany-wide completions_wohngebaeude, 2022-2025:")
print(germany_totals.loc[2022:2025].to_string())

YEARS = sorted(df["year"].unique())

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 6.5))

for state in df["bundesland"].unique():
    if state == "Hamburg":
        continue
    s = df[df["bundesland"] == state].set_index("year")["completions_wohngebaeude"]
    ax.plot(s.index, s.values, color=C_GREY, lw=0.9, alpha=0.7, zorder=1)

hh = df[df["bundesland"] == "Hamburg"].set_index("year")["completions_wohngebaeude"]
l_hh, = ax.plot(hh.index, hh.values, color=C_HH, lw=2.8, zorder=10, label="Hamburg")

for xyr, lbl in [(2023, "HH Neubau\nmandate"), (2024, "HH Bestand\nmandate")]:
    ax.axvline(xyr, color=C_VLINE, lw=1.2, linestyle=":", zorder=3)
    ax.text(xyr + 0.05, ax.get_ylim()[1], lbl,
            ha="left", va="top", fontsize=7.5, color=C_VLINE)

ax.set_yscale("log")

legend_handles = [l_hh,
                   plt.Line2D([0], [0], color=C_GREY, lw=1.5, label="Other federal states")]

ax.set_xticks(YEARS)
ax.set_xticklabels(YEARS, rotation=30, ha="right", fontsize=9)
ax.set_ylabel("Completed residential buildings (log scale)", fontsize=10)
ax.set_xlabel("Year", fontsize=10)
ax.set_title(
    "Residential Building Completions by Federal State, 2015–2025",
    fontsize=11, fontweight="bold", pad=10,
)
ax.legend(handles=legend_handles, loc="upper left", fontsize=9, framealpha=0.95)

fig.text(0.5, 0.02,
         "Source: Destatis 31121-0100, own calculation.",
         ha="center", fontsize=8, color="#777777", style="italic")

fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")

