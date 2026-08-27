#!/usr/bin/env python3
"""
07_border_parallel_trends.py — Pre-period parallel trends (2015–2025), border
DiD group. (Renamed from D1_parallel_trends.py 2026-08-09 to narrative order;
content unchanged.)

Hamburg (treated) vs. Control — the first-ring DiD sample, identical to the main
did_analysis.py specification. PLZ counts are the first-ring groups as defined
in Skripte/plz_groups.py (FIRST_RING_HH / FIRST_RING_SH / FIRST_RING_NI).
Second-ring PLZs (Skripte/plz_groups.py SECOND_RING) are excluded,
matching the main spec exactly. Monthly resolution comes from
A_deutschland_plz_monat_operatortyp.csv filtered to that same PLZ set.

Single-panel figure: quarterly private installations per km², group-level
(sum of installs / sum of each PLZ's own area within the group) — the same
outcome definition did_analysis.py uses for the main DiD spec (05__per_km2),
not an arbitrary index. Area (flaeche_km2) comes from B_did_panel_yearly.csv,
merged onto the quarterly Panel A counts (area is time-invariant per PLZ, so
one merge covers all quarters). Kept at quarterly resolution rather than the
DiD panel's annual frequency — 8 pre-period annual points would make a weak
visual trends check; quarterly Panel A data gives ~32.

Changed 2026-08-09 (user: use the DiD spec's per-km² outcome instead of an
indexed baseline) from an earlier version that indexed both groups to their
own 2019-2022 mean = 1.0. A separate raw-counts, dual-axis panel that used to
sit below this one was dropped the same day ("I only want one plot not the
one that shows two different ones") — it showed levels, not trends, and
wasn't the point of this figure.

Output: Auswertung/Descriptive Results/03_Border_DiD_Comparison/07_border_parallel_trends.png
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import sys

BASE     = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "scripts"))
from plz_groups import SECOND_RING, FIRST_RING_HH, FIRST_RING_SH, FIRST_RING_NI

N_HH, N_SH, N_NI = len(FIRST_RING_HH), len(FIRST_RING_SH), len(FIRST_RING_NI)
N_CTRL = N_SH + N_NI

SRC_A    = BASE / "data" / "panels" / "A_deutschland_plz_monat_operatortyp.csv"
SRC_A = SRC_A if SRC_A.exists() else SRC_A.with_suffix(".csv.gz")
SRC_D    = BASE / "data" / "panels" / "B_did_panel_yearly.csv"
OUT      = BASE / "output" / "figures" / "f07_parallel_trends.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

C_HH   = "#D94F3D"
C_CTRL = "#2166AC"
C_VL   = "#444444"
C_PRE  = "#F7F7F7"

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#E5E5E5",
    "grid.linewidth": 0.6, "axes.axisbelow": True,
})

# ── PLZ → treated crosswalk + area from the DiD panel, first ring only ───────
plz_group = (pd.read_csv(SRC_D, usecols=["Postleitzahl", "treated", "flaeche_km2"])
               .drop_duplicates("Postleitzahl"))
plz_group = plz_group[~plz_group["Postleitzahl"].astype(str).isin(SECOND_RING)]
group_area = plz_group.groupby("treated")["flaeche_km2"].sum()  # combined km² per group

# ── Load Panel A, restrict to the first-ring DiD PLZs, label group, aggregate ─
df = pd.read_csv(SRC_A, usecols=["Postleitzahl", "operator_type", "jahr_monat", "anzahl_anlagen"])
df = df.merge(plz_group[["Postleitzahl", "treated"]], on="Postleitzahl", how="inner")
df = df[df["operator_type"] == "privat"]
df["date"] = pd.to_datetime(df["jahr_monat"] + "-01")
df = df[df["date"].dt.year.between(2015, 2025)]
df["group"] = df["treated"].map({1: "Hamburg border PLZs", 0: "Control border PLZs"})
df["quarter"] = df["date"].dt.to_period("Q")

q = (df.groupby(["group", "treated", "quarter"])["anzahl_anlagen"]
       .sum()
       .reset_index()
       .assign(date=lambda d: d["quarter"].dt.to_timestamp()))
q["km2"]     = q["treated"].map(group_area)
q["per_km2"] = q["anzahl_anlagen"] / q["km2"]

hh   = q[q["group"] == "Hamburg border PLZs"].set_index("date")["per_km2"].sort_index()
ctrl = q[q["group"] == "Control border PLZs"].set_index("date")["per_km2"].sort_index()

MANDATE1 = pd.Timestamp("2023-01-01")
MANDATE2 = pd.Timestamp("2024-01-01")

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax1 = plt.subplots(figsize=(13, 6.5))

ax1.axvspan(pd.Timestamp("2015-01-01"), MANDATE1, color=C_PRE, alpha=0.7, zorder=0)
ax1.plot(hh.index,   hh.values,   color=C_HH,   lw=2.4, label="Hamburg border PLZs")
ax1.plot(ctrl.index, ctrl.values, color=C_CTRL, lw=2.0, linestyle="--",
         label="Control border PLZs")

for xd, lbl in [(MANDATE1, "First mandate\nstep"), (MANDATE2, "Second mandate\nstep")]:
    ax1.axvline(xd, color=C_VL, lw=1.3, linestyle=":", zorder=2)
    ax1.text(xd + pd.Timedelta(days=50), ax1.get_ylim()[1] * 0.99,
             lbl, ha="left", va="top", fontsize=8, color=C_VL)

ax1.set_ylabel("Private solar installations per km²", fontsize=10)
ax1.set_xlabel("Quarter", fontsize=10)
ax1.set_title(
    "Pre-period Parallel Trends — Private Solar Installations per km², Quarterly (Border DiD PLZs)",
    fontsize=11, fontweight="bold",
)
ax1.legend(handles=[
    plt.Line2D([0],[0], color=C_HH,   lw=2.4,         label=f"Hamburg border PLZs (n={N_HH}, treated)"),
    plt.Line2D([0],[0], color=C_CTRL, lw=2.0, ls="--", label=f"Control border PLZs (n={N_CTRL})"),
    mpatches.Patch(color=C_PRE, alpha=0.9, label="Pre-mandate period"),
], loc="upper left", fontsize=9, framealpha=0.9)

ax1.set_xlim(pd.Timestamp("2015-01-01"), pd.Timestamp("2025-12-01"))

hh_km2   = group_area.get(1, float("nan"))
ctrl_km2 = group_area.get(0, float("nan"))
fig.text(0.5, 0.02,
         "Source: MaStR (Bundesnetzagentur). Private operators (natürliche Person) only. "
         f"{N_HH} Hamburg border PLZs vs. {N_CTRL} control border PLZs (first ring, identical to the "
         f"main DiD specification): {hh_km2:,.0f} km² vs. {ctrl_km2:,.0f} km² combined.",
         ha="center", fontsize=8, color="#777777", style="italic")
fig.text(0.5, -0.005,
         "Same per-km² outcome definition as did_analysis.py's main spec. "
         "Vertical lines: Hamburg Solardachpflicht (Jan 2023, Jan 2024).",
         ha="center", fontsize=8, color="#777777", style="italic")

fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
print(f"Saved: {OUT}")
