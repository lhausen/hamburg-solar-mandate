#!/usr/bin/env python3
"""
D4_summary_statistics.py — Summary statistics table, border DiD group.

Unit: PLZ × year from B_did_panel_yearly.csv, first-ring sample — identical to
the main did_analysis.py specification. PLZ counts are the first-ring groups
as defined in Skripte/plz_groups.py (FIRST_RING_HH / FIRST_RING_SH /
FIRST_RING_NI). Second-ring PLZs (Skripte/plz_groups.py SECOND_RING)
are excluded. PLZ-level area (flaeche_km2) is already in the DiD panel, so no
separate PLZ-area file is needed.

Groups: Hamburg border PLZs (treated) | Control border PLZs
Period: Pre-mandate (2015–2022) | Post-mandate (2023–2025)

Output: _Additional/Auswertung/Descriptive Results/D4_summary_statistics.png / .csv
(moved out of the thesis-facing folder 2026-08-08, see D1_parallel_trends.py.)
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
import sys

BASE  = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "scripts"))
from plz_groups import SECOND_RING, FIRST_RING_HH, FIRST_RING_SH, FIRST_RING_NI

N_HH, N_SH, N_NI = len(FIRST_RING_HH), len(FIRST_RING_SH), len(FIRST_RING_NI)
N_CTRL = N_SH + N_NI

SRC_D = BASE / "data" / "panels" / "B_did_panel_yearly.csv"
OUT   = BASE / "output" / "tables" / "summary_statistics.png"
OUTC  = BASE / "output" / "tables" / "summary_statistics.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

CUTOFF = 2023

# ── Load DiD panel, first ring only ───────────────────────────────────────────
print("Loading Panel B …")
d = pd.read_csv(SRC_D)
d = d[~d["Postleitzahl"].astype(str).isin(SECOND_RING)]
d = d[d["year"].between(2015, 2025)]
d["group"] = d["treated"].map({1: "Hamburg border PLZs", 0: "Control border PLZs"})

wide = d.pivot_table(index=["Postleitzahl", "group", "year", "flaeche_km2"],
                      columns="operator_type",
                      values="anzahl_anlagen", fill_value=0).reset_index()
wide = wide.rename(columns={"privat": "anlagen_privat", "organisation": "anlagen_organisation"})

kw = d.pivot_table(index=["Postleitzahl", "year"],
                    columns="operator_type",
                    values="netto_kw", fill_value=0).reset_index()
kw = kw.rename(columns={"privat": "kw_privat", "organisation": "kw_organisation"})
wide = wide.merge(kw, on=["Postleitzahl", "year"], how="left")

for suffix in ["privat", "organisation"]:
    for col in [f"anlagen_{suffix}", f"kw_{suffix}"]:
        if col not in wide.columns:
            wide[col] = 0

wide["anlagen_total"] = wide["anlagen_privat"] + wide["anlagen_organisation"]
wide["private_share"] = np.where(
    wide["anlagen_total"] > 0,
    wide["anlagen_privat"] / wide["anlagen_total"] * 100,
    np.nan,
)
wide["avg_kw_privat"] = np.where(
    wide["anlagen_privat"] > 0,
    wide["kw_privat"] / wide["anlagen_privat"],
    np.nan,
)
wide["density_privat"] = np.where(
    wide["flaeche_km2"] > 0, wide["anlagen_privat"] / wide["flaeche_km2"], np.nan
)

wide["period"] = wide["year"].apply(
    lambda y: "Pre-mandate (2015–2022)" if y < CUTOFF else "Post-mandate (2023–2025)"
)

# ── Summary statistics ────────────────────────────────────────────────────────
# Compact "Table 1" layout: one row per variable, one column per Group × Period
# cell. N is reported inside each cell since it differs by variable (avg. system
# size and private share are only defined for PLZ-years with ≥1 private install).
VARIABLES = {
    "anlagen_privat": "Private installations / PLZ-year",
    "density_privat": "Private installations per km²",
    "avg_kw_privat":  "Avg. system size, private (kW)",
    "private_share":  "Private share of installations (%)",
}
GROUPS  = ["Hamburg border PLZs", "Control border PLZs"]
PERIODS = ["Pre-mandate (2015–2022)", "Post-mandate (2023–2025)"]
COLS    = [(g, p) for g in GROUPS for p in PERIODS]

# Avg. system size and private share are installation-weighted (matches the
# thesis table): total kW / total installations, and total private / total
# installations, summed over the whole group x period cell -- not the mean
# of per-PLZ-year values, which the rest of this script still uses for
# anlagen_privat and density_privat.
WEIGHTED_MEAN = {
    "avg_kw_privat": lambda sub: sub["kw_privat"].sum() / sub["anlagen_privat"].sum(),
    "private_share": lambda sub: sub["anlagen_privat"].sum() / sub["anlagen_total"].sum() * 100,
}

rows_csv = []
cell_grid = []
for var, label in VARIABLES.items():
    row_cells = []
    for grp, period in COLS:
        sub = wide[(wide["group"] == grp) & (wide["period"] == period)]
        col = sub[var].dropna()
        n, sd = len(col), col.std()
        mean = WEIGHTED_MEAN[var](sub) if var in WEIGHTED_MEAN else col.mean()
        row_cells.append(f"{mean:,.2f}\n({sd:,.2f})\nn={n:,}" if n else "—")
        rows_csv.append({"Variable": label, "Group": grp, "Period": period,
                          "N": n, "Mean": mean, "SD": sd})
    cell_grid.append([label] + row_cells)

pd.DataFrame(rows_csv).to_csv(OUTC, index=False)
print(f"Saved CSV: {OUTC}")

# ── PNG table ─────────────────────────────────────────────────────────────────
col_labels = ["Variable"] + [f"{g}\n{p.split('(')[1].rstrip(')')}" for g, p in COLS]

fig, ax = plt.subplots(figsize=(11, 3.2))
ax.axis("off")

table = ax.table(cellText=cell_grid, colLabels=col_labels, cellLoc="center", loc="center")
table.auto_set_font_size(False)
table.set_fontsize(9)
table.auto_set_column_width(list(range(len(col_labels))))
table.scale(1, 2.6)

for j in range(len(col_labels)):
    table[(0, j)].set_facecolor("#2C3E50")
    table[(0, j)].set_text_props(color="white", fontweight="bold")
    table[(0, j)].set_height(0.16)

GROUP_SHADE = {"Hamburg border PLZs": "#FDE8E3", "Control border PLZs": "#EAF2FB"}
for i in range(1, len(cell_grid) + 1):
    table[(i, 0)].set_text_props(ha="left", fontweight="bold")
    table[(i, 0)].PAD = 0.03
    for j, (grp, _) in enumerate(COLS, start=1):
        table[(i, j)].set_facecolor(GROUP_SHADE[grp])

fig.suptitle(
    "Summary Statistics — Private Solar Installations (PLZ × year)\n"
    "31 Hamburg border PLZs (treated) vs. 25 control border PLZs "
    "(first ring, identical to the main DiD specification)",
    fontsize=11, fontweight="bold", y=1.04,
)
fig.text(0.5, -0.06,
         "Source: MaStR (Bundesnetzagentur). Unit: PLZ × calendar year, 2015–2025 — the "
         "first-ring DiD panel (B_did_panel_yearly.csv, SECOND_RING excluded). Cells show "
         "mean, (SD), and n. Avg. system size and private share are installation-weighted "
         "(total kW / total installations; total private / total installations) and exclude "
         "PLZ-years with zero private installations.",
         ha="center", fontsize=7.5, color="#777777", style="italic")

fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
print(f"Saved: {OUT}")
