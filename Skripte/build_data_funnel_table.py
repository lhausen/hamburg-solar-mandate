#!/usr/bin/env python3
"""
build_data_funnel_table.py — Methodology-section data funnel table: raw
BNetzA registry -> filter cascade -> the two analysis panels (SCM: Bundesland
x year, DiD: PLZ x year, first ring).

Every number is computed fresh:
  Block 1 (rows 1-5) — the four-filter cascade, applied step by step directly
    to the raw MaStR export, one row per step, showing records remaining
    and records removed at that step. Order: In Betrieb (already true of
    every row in the export) -> drop balcony systems -> drop
    ground-mounted/other non-roof structures -> drop <=0.8 kW -> restrict
    to commissioned 2015-2025. Filter codes themselves are not repeated
    here; Section 4.1 gives them.
  Block 2 — the two panels as columns, their attributes (units, of which
    treated, years, observations, private installations) as rows. SCM
    column: read directly from the main SCM spec's own output
    (17__.../Data/scm_panel_annual.csv), so this table can never drift from
    what SCM_30 actually ran on. DiD column: read directly from the DiD
    main spec's own analysis panel (02_DiD_PLZ/05__.../base/Data), same
    reasoning.

Deliberately does NOT read Panel A: cross-checked 2026-08-10 and found Panel
A on disk (dated 2026-07-10) predates a dropna=False fix in rebuild_panels.py
(dated 2026-07-29) that keeps the ~15 nationwide rows with a missing
Landkreis; Panel A is stale by exactly those 15 rows. Computing the cascade
straight from the raw export sidesteps that staleness. Panel A itself has
not been touched by this script.

Run after: SCM_30_rate_neubau_privat_annual.py (SCM panel) and did_analysis.py
(05__per_km2__privat__start2015 base spec, DiD panel). Does not require
rebuild_panels.py / Panel A.

Outputs:
  Thesis-Overleaf/tables/data_funnel_table.tex
  Auswertung/Berichte/04_data_funnel.csv
"""

from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent.parent

RAW_MASTR   = BASE / "Daten" / "Solardaten" / "mastr_solar_deutschland.csv"
SCM_ANNUAL  = (BASE / "Auswertung" / "Causal inference" / "01_SCM_Bundesebene" /
               "17__rate_neubau_privat_annual__2015-2022__vollerPool" /
               "Data" / "scm_panel_annual.csv")
DID_BASE    = (BASE / "Auswertung" / "Causal inference" / "02_DiD_PLZ" /
               "05__per_km2__privat__start2015" / "base" / "Data" / "panel_2015_base.csv")

TEX_OUT = BASE / "Thesis-Overleaf" / "tables" / "data_funnel_table.tex"
CSV_OUT = BASE / "Auswertung" / "Berichte" / "04_data_funnel.csv"
TEX_OUT.parent.mkdir(parents=True, exist_ok=True)
CSV_OUT.parent.mkdir(parents=True, exist_ok=True)

CODE_STECKER     = 2961
CODE_FREIFLAECHE = 852
CODE_UNKNOWN     = 2484
BALKON_KW        = 0.8

# ── Block 1: filter cascade, applied directly to the raw export ──────────────
n_status = n_balkon = n_nonroof = n_kw = n_window = 0

for chunk in pd.read_csv(
        RAW_MASTR, chunksize=500_000, low_memory=False,
        parse_dates=["Inbetriebnahmedatum"],
    ):
    c0 = chunk[chunk["EinheitBetriebsstatus"] == 35]
    n_status += len(c0)

    c1 = c0[c0["ArtDerSolaranlage"] != CODE_STECKER]
    n_balkon += len(c1)

    c2 = c1[~c1["ArtDerSolaranlage"].isin([CODE_FREIFLAECHE, CODE_UNKNOWN])]
    n_nonroof += len(c2)

    c3 = c2[c2["Nettonennleistung"] > BALKON_KW]
    n_kw += len(c3)

    c4 = c3[c3["Inbetriebnahmedatum"].between("2015-01-01", "2025-12-31")]
    n_window += len(c4)

cascade_rows = [
    ("In register (status \"In Betrieb\", all years)", n_status),
    ("after balcony-system filter", n_balkon),
    ("after non-roof structure filter", n_nonroof),
    ("after capacity filter (> 0.8 kW)", n_kw),
    ("after analysis window filter (2015\u20132025)", n_window),
]

# ── Block 2: SCM panel (Bundesland x year) — read from the main spec's own output ──
scm = pd.read_csv(SCM_ANNUAL)
n_scm_states   = scm["bundesland"].nunique()
n_scm_years    = scm["year"].nunique()
n_scm_obs      = len(scm)
scm_installs   = int(scm["solar_privat_y"].sum())
assert (n_scm_states, n_scm_years, n_scm_obs) == (14, 11, 154), \
    f"SCM panel dimensions changed: {(n_scm_states, n_scm_years, n_scm_obs)}"

# ── Block 3: DiD panel (PLZ x year, first ring) — read from the DiD main spec ──
did = pd.read_csv(DID_BASE)
n_did_plz     = did["Postleitzahl"].nunique()
n_did_years   = did["year"].nunique()
n_did_obs     = len(did)
did_installs  = int(did["anzahl_anlagen"].sum())
n_did_treated = did.loc[did["treated"] == 1, "Postleitzahl"].nunique()
n_did_control = did.loc[did["treated"] == 0, "Postleitzahl"].nunique()
assert (n_did_plz, n_did_years, n_did_obs) == (55, 11, 605), \
    f"DiD panel dimensions changed: {(n_did_plz, n_did_years, n_did_obs)}"

# Panels as columns, attributes as rows. "of which treated" = the target
# unit for SCM (Hamburg, 1 of 14 states) vs. treated postal codes for DiD.
panel_header = ("", "Synthetic control", "Difference-in-differences")
panel_rows = [
    ("Units", f"{n_scm_states} Bundesl\u00e4nder", f"{n_did_plz} postal codes"),
    ("of which treated", "1", str(n_did_treated)),
    ("Years (2015\u20132025)", str(n_scm_years), str(n_did_years)),
    ("Observations", f"{n_scm_obs:,}", f"{n_did_obs:,}"),
    ("Private installations", f"{scm_installs:,}", f"{did_installs:,}"),
]

# Removed at each step = the drop from the previous row; first row has none.
cascade_removed = [None] + [cascade_rows[i-1][1] - cascade_rows[i][1] for i in range(1, len(cascade_rows))]

# ── CSV (backing data, plain text) ────────────────────────────────────────────
csv_rows = (
    [{"quantity": q, "value_scm": v, "value_did": r if r is not None else ""}
     for (q, v), r in zip(cascade_rows, cascade_removed)]
    + [{"quantity": q, "value_scm": v1, "value_did": v2} for q, v1, v2 in [panel_header] + panel_rows]
)
pd.DataFrame(csv_rows).to_csv(CSV_OUT, index=False)
print(f"Saved: {CSV_OUT}")

# ── LaTeX (booktabs/threeparttable/tabularx) ──────────────────────────────────
def _cascade_row(quantity, value, removed):
    rem = f"{removed:,}" if removed is not None else "---"
    return f"{quantity} & {value:,} & {rem} \\\\\n"

def _panel_row(quantity, v1, v2):
    return f"{quantity} & {v1} & {v2} \\\\\n"

tex = r"""% -----------------------------------------------------------------------
% Table: Data construction funnel — from BNetzA registry to analysis panels
% Requires: booktabs, threeparttable, tabularx (tabularx needed because the
% cascade labels are too long for a plain 'l' column to fit \textwidth --
% a bare tabular centres via glue and silently overflows the margins with
% no compiler warning; the X column wraps instead).
% Generated by Skripte/build_data_funnel_table.py — do not edit by hand.
% -----------------------------------------------------------------------

\begin{table}[!htbp]
\centering
\caption{From Registry to Analysis Panels: Sample Construction}
\label{tab:data_funnel}
\begin{threeparttable}
\small
\begin{tabularx}{\textwidth}{Xrr}
\toprule
& Records & Removed \\
\cmidrule(lr){2-3}
"""
for (q, v), r in zip(cascade_rows, cascade_removed):
    tex += _cascade_row(q, v, r)
tex += "\\midrule\n"
for q, v1, v2 in [panel_header] + panel_rows:
    tex += _panel_row(q, v1, v2)
tex += r"""\bottomrule
\end{tabularx}
\begin{tablenotes}
\small
\item \textit{Notes:} Source: MaStR bulk export
  (\texttt{mastr\_solar\_deutschland.csv}). Row 1 is not restricted by
  commissioning date and covers the full history of the register; row 5 and
  both panels below it are restricted to the 2015--2025 analysis window.
\end{tablenotes}
\end{threeparttable}
\end{table}
"""
TEX_OUT.write_text(tex)
print(f"Saved: {TEX_OUT}")

print("\nFunnel:")
for (q, v), r in zip(cascade_rows, cascade_removed):
    removed = f"({r:,})" if r is not None else ""
    print(f"  {q:<58} {v:>12,}  {removed}")
print()
for q, v1, v2 in [panel_header] + panel_rows:
    print(f"  {q:<25} {v1:>20} {v2:>25}")
