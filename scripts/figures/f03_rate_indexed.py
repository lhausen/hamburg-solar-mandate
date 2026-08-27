#!/usr/bin/env python3
"""
03_rate_hamburg_vs_germany_indexed.py — Hamburg vs. Germany-average,
installs per 1,000 new residential buildings, indexed to 2019 = 100.
(Renamed from D11_hamburg_vs_germany_avg_rate_index2019.py 2026-08-09 to
narrative order; content unchanged.)

Same underlying rate as D10 (private installs / residential completions *
1,000, Panel C, Bundesland-level), but each series — Hamburg, every
individual state, and the Germany average — is indexed to its own 2019
value = 100 before plotting, so slope (relative growth) rather than level is
what's compared. Window restricted to 2019–2025 (index requires a 2019
baseline).

Germany average = simple (unweighted) mean of the per-state *rate* across
all 16 Bundesländer each year, indexed to its own 2019 value afterwards —
i.e. treated as one more series, indexed the same way as every state, per
user decision 2026-08-08.

Output: Auswertung/Descriptive Results/01_Statewide_Comparison/03_rate_hamburg_vs_germany_indexed.png
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SRC  = BASE / "data" / "panels" / "C_bundesland_panel_monthly.csv"
OUT  = BASE / "output" / "figures" / "f03_rate_indexed.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

BASE_YEAR = 2019

C_HH    = "#D94F3D"
C_AVG   = "#2166AC"
C_GREY  = "#CCCCCC"
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

# ── Index every series to its own 2019 value = 100 ─────────────────────────────
def _to_index(group):
    base = group.loc[group["year"] == BASE_YEAR, "rate"]
    group = group.copy()
    group["idx"] = group["rate"] / base.iloc[0] * 100 if len(base) and base.iloc[0] else float("nan")
    return group

idx_parts = [_to_index(g) for _, g in annual.groupby("bundesland")]
annual = pd.concat(idx_parts, ignore_index=True)
germany_avg_idx = germany_avg / germany_avg.loc[BASE_YEAR] * 100

YEARS = [y for y in sorted(annual["year"].unique()) if y >= BASE_YEAR]

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 6.5))

for state in annual["bundesland"].unique():
    if state == "Hamburg":
        continue
    s = annual[(annual["bundesland"] == state) & (annual["year"] >= BASE_YEAR)].set_index("year")["idx"]
    ax.plot(s.index, s.values, color=C_GREY, lw=0.9, alpha=0.7, zorder=1)

hh = annual[(annual["bundesland"] == "Hamburg") & (annual["year"] >= BASE_YEAR)].set_index("year")["idx"]
l_hh, = ax.plot(hh.index, hh.values, color=C_HH, lw=2.8, zorder=10, label="Hamburg")
germany_avg_idx_win = germany_avg_idx[germany_avg_idx.index >= BASE_YEAR]
l_avg, = ax.plot(germany_avg_idx_win.index, germany_avg_idx_win.values, color=C_AVG, lw=2.2,
                  linestyle="--", zorder=9, label=f"Germany average (simple mean, {n_states} states)")

ax.axhline(100, color="#999999", lw=1.0, ls=":", zorder=2)

for xyr, lbl in [(2023, "HH Neubau\nmandate"), (2024, "HH Bestand\nmandate")]:
    ax.axvline(xyr, color=C_VLINE, lw=1.2, linestyle=":", zorder=3)
    ax.text(xyr + 0.05, ax.get_ylim()[1] * 0.99, lbl,
            ha="left", va="top", fontsize=7.5, color=C_VLINE)

legend_handles = [l_hh, l_avg,
                   plt.Line2D([0], [0], color=C_GREY, lw=1.5, label="Other Bundesländer")]

ax.set_xticks(YEARS)
ax.set_xticklabels(YEARS, fontsize=9)
ax.set_ylabel(f"Index ({BASE_YEAR} = 100)", fontsize=10)
ax.set_xlabel("Year", fontsize=10)
ax.set_title(
    "Hamburg vs. Germany Average, Indexed — Installs per 1,000 Residential Completions "
    f"({BASE_YEAR} = 100)",
    fontsize=11, fontweight="bold", pad=10,
)
ax.legend(handles=legend_handles, loc="upper left", fontsize=9, framealpha=0.95)

fig.text(0.5, 0.02,
         "Source: MaStR (Bundesnetzagentur); Destatis (Baufertigstellungen Wohngebäude). "
         f"Each series (incl. Germany average) indexed to its own {BASE_YEAR} value = 100.",
         ha="center", fontsize=8, color="#777777", style="italic")
fig.text(0.5, -0.005,
         "Germany average = unweighted mean of the per-state rate across all 16 Bundesländer.",
         ha="center", fontsize=8, color="#777777", style="italic")

fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
