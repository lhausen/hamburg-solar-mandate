#!/usr/bin/env python3
"""
01_mandate_timeline_states.py — Solar mandate timeline, built on the
2-category regression index (mandate_commercial, mandate_private) instead of
the 3-dimension-plus-caveats dataset D6 used. (Renamed from
D6e_mandate_index_row_timeline.py 2026-08-09 to narrative order; content
unchanged.)

Second round of alternatives (2026-08-09), after the user rejected all three
first-round candidates and pointed at C_mandate_index_monthly.csv — the
actual mandate_commercial / mandate_private / mandate_score (0-2) index that
feeds Panel E and every DiD/SCM script downstream. Ambiguous/narrow-scope
cases (Bayern's Nichtwohn-only Bestand, Hessen's Landeseigene-only
obligation, etc.) are already resolved to a clean 0 by build_mandate_index.py
— no hatching or "scope-limited" notes needed here.

Chosen 2026-08-09 as the thesis-facing mandate timeline, superseding
D6_mandate_timeline.py (now retired to _Additional/, still valid/runnable).

Design: one row per state, color-coded by mandate_score (0 = no mandate,
1 = commercial new construction only, 2 = commercial + private new
construction). Dates read directly from C_mandate_index_monthly.csv (first
year_month where each flag turns 1), not re-transcribed.

Legal-text cross-check (2026-08-09): every state's coded date was checked
against a primary source (local PDF in Daten/Quellen/ where available, else
an official/professional-body web source) before trusting this chart. All
matched build_mandate_index.py exactly, with one exception found and applied
below: Brandenburg's § 32a BbgBO mandate (commercial Neubau, June 2024) was
REPEALED effective 30 June 2026 by the Vierte Änderung der Brandenburgischen
Bauordnung (confirmed via the Brandenburgische Ingenieurkammer, bbik.de) —
after C_mandate_index_monthly.csv was built, so the panel has no repeal
mechanism and still shows Brandenburg mandated indefinitely. Applied here as
a sourced override, not silently; not fed back into the panel itself (see
session notes — that's a separate decision since it doesn't touch the
2015-2025 analysis window).

Output: Auswertung/Descriptive Results/01_Statewide_Comparison/01_mandate_timeline_states.png
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
SRC  = BASE / "Auswertung" / "Panels" / "C_mandate_index_monthly.csv"
OUT  = BASE / "Auswertung" / "Descriptive Results" / "01_Statewide_Comparison" / "01_mandate_timeline_states.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

C_NONE = "#E5E5E5"
C_COMM = "#2166AC"
C_FULL = "#D94F3D"
C_HH_BORDER = "#1A1A1A"
XMIN, XMAX = 2021.7, 2026.75

# Repeals not reflected in C_mandate_index_monthly.csv (found 2026-08-09, see
# docstring): {state: (repeal_x, source_note)}. Reverts that state's segment
# to "no mandate" from repeal_x onward.
REPEALS = {
    "Brandenburg": (2026.0 + 6 / 12, "§ 32a BbgBO repealed 30.06.2026 (Vierte Änderung BbgBO)"),
}

df = pd.read_csv(SRC)
df["date"] = pd.to_datetime(df["year_month"] + "-01")
df["x"] = df["date"].dt.year + (df["date"].dt.month - 1) / 12

def first_date(bl, col):
    sub = df[(df["Bundesland"] == bl) & (df[col] == 1)]
    return sub["x"].min() if not sub.empty else None

STATES_ALL = sorted(df["Bundesland"].unique())
comm_date = {bl: first_date(bl, "mandate_commercial") for bl in STATES_ALL}
priv_date = {bl: first_date(bl, "mandate_private") for bl in STATES_ALL}

def sort_key(bl):
    p = priv_date[bl] if priv_date[bl] is not None else 9999
    c = comm_date[bl] if comm_date[bl] is not None else 9999
    return (p, c, bl)

STATES = sorted(STATES_ALL, key=sort_key)

def segments(bl):
    c, p = comm_date[bl], priv_date[bl]
    segs = []
    breakpoints = sorted(x for x in [c, p] if x is not None)
    if not breakpoints:
        return [(XMIN, XMAX, C_NONE)]
    if breakpoints[0] > XMIN:
        segs.append((XMIN, breakpoints[0], C_NONE))
    for i, bp in enumerate(breakpoints):
        score = int(c is not None and c <= bp) + int(p is not None and p <= bp)
        color = C_FULL if score == 2 else C_COMM
        x1 = breakpoints[i + 1] if i + 1 < len(breakpoints) else XMAX
        segs.append((bp, x1, color))

    if bl in REPEALS:
        repeal_x, _ = REPEALS[bl]
        clipped = []
        for x0, x1, color in segs:
            if x0 >= repeal_x:
                continue
            clipped.append((x0, min(x1, repeal_x), color))
        clipped.append((repeal_x, XMAX, C_NONE))
        segs = clipped
    return segs

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 6))
ax.set_facecolor("#FAFAFA")
for sp in ax.spines.values():
    sp.set_visible(False)

BAR_H = 0.62
for si, state in enumerate(STATES):
    y = len(STATES) - 1 - si
    for x0, x1, color in segments(state):
        rect = mpatches.FancyBboxPatch(
            (x0, y - BAR_H / 2), x1 - x0, BAR_H,
            boxstyle="square,pad=0", facecolor=color,
            edgecolor="white", linewidth=0.6, zorder=3,
        )
        ax.add_patch(rect)
    if state == "Hamburg":
        border = mpatches.FancyBboxPatch(
            (XMIN + 0.02, y - BAR_H / 2 - 0.06), XMAX - XMIN - 0.04, BAR_H + 0.12,
            boxstyle="round,pad=0.01", facecolor="none",
            edgecolor=C_HH_BORDER, linewidth=2.4, zorder=6,
        )
        ax.add_patch(border)

for yr in range(2022, 2027):
    ax.axvline(yr, color="#DDDDDD", lw=0.8, zorder=1)
    ax.text(yr, len(STATES) - 0.15, str(yr), ha="center", va="bottom",
             fontsize=9, color="#666666")

ax.set_xlim(XMIN, XMAX)
ax.set_ylim(-0.7, len(STATES))
ax.set_yticks(range(len(STATES)))
ax.set_yticklabels(
    [f"$\\bf{{Hamburg}}$" if s == "Hamburg" else s for s in reversed(STATES)],
    fontsize=9.5,
)
ax.tick_params(left=False, bottom=False)
ax.set_xticks([])

legend_handles = [
    mpatches.Patch(facecolor=C_NONE, label="No mandate (score 0)"),
    mpatches.Patch(facecolor=C_COMM, label="Commercial new construction only (score 1)"),
    mpatches.Patch(facecolor=C_FULL, label="Commercial + private new construction (score 2)"),
]
ax.legend(handles=legend_handles, loc="lower right", fontsize=9, framealpha=0.95,
          title="mandate_score", title_fontsize=9)

ax.set_title(
    "Solar Mandate Index by Bundesland, 2022–2026",
    fontsize=12, fontweight="bold", pad=12,
)

fig.text(0.5, 0.005,
         "Source: Auswertung/Panels/C_mandate_index_monthly.csv (Skripte/build_mandate_index.py) — the index "
         "used in Panel E and every DiD/SCM regression.",
         ha="center", fontsize=7.5, color="#777777", style="italic")
fig.text(0.5, -0.02,
         "Every date cross-checked against a primary legal text or official source, 2026-08-09. Brandenburg's "
         "mandate (repealed 30.06.2026) shown as a sourced override not yet reflected in the panel itself.",
         ha="center", fontsize=7.5, color="#777777", style="italic")

fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
print(f"Saved: {OUT}")
