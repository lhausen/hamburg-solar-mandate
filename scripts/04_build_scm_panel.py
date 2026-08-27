#!/usr/bin/env python3
"""
Build Panel C: Bundesland × month panel for SCM and descriptive analysis.

Inputs (all derived from mastr_solar_deutschland.csv or static sources):
  Panel A      — Auswertung/Panels/A_deutschland_plz_monat_operatortyp.csv
  Mandate index — Auswertung/Panels/mandate_index_monthly.csv (coded legal
               input, not an analysis panel -- carries no panel letter)
  Completions — Daten/Neubaudaten/completions_bundesland_annual.csv
              (Destatis 31121-0100: Baufertigstellungen Wohn- und Nichtwohngebäude
               by Bundesland and year; annual values broadcast to all 12 months)

Output:
  Auswertung/Panels/C_bundesland_panel_monthly.csv

Columns:
  bundesland, year_month,
  solar_organisation, solar_privat, netto_kw_organisation, netto_kw_privat,
  solar_total, netto_kw_total,
  mandate_commercial, mandate_private, mandate_score,
  completions_wohngebaeude, completions_nichtwohn, completions_gesamt
"""

from pathlib import Path
import pandas as pd

BASE         = Path(__file__).resolve().parents[1]
PANEL_A      = BASE / "data/panels/A_deutschland_plz_monat_operatortyp.csv"
PANEL_A = PANEL_A if PANEL_A.exists() else PANEL_A.with_suffix(".csv.gz")
MANDATE_IDX  = BASE / "data/panels/mandate_index_monthly.csv"
COMPLETIONS  = BASE / "data/aux/completions_bundesland_annual.csv"
OUT          = BASE / "data/panels/C_bundesland_panel_monthly.csv"

# ── 1. Solar: aggregate Panel A (PLZ × month × operator) → Bundesland × month ─

print("Reading Panel A …")
pa = pd.read_csv(PANEL_A, dtype={"Postleitzahl": str})

solar = (
    pa.groupby(["Bundesland", "jahr_monat", "operator_type"], observed=True)
    .agg(anzahl=("anzahl_anlagen", "sum"), kw=("netto_kw", "sum"))
    .reset_index()
)

# Pivot operator_type → columns
solar_wide = solar.pivot_table(
    index=["Bundesland", "jahr_monat"],
    columns="operator_type",
    values=["anzahl", "kw"],
    aggfunc="sum",
    fill_value=0,
).reset_index()

solar_wide.columns = [
    "_".join(c).strip("_") if c[1] else c[0]
    for c in solar_wide.columns
]

solar_wide = solar_wide.rename(columns={
    "Bundesland":          "bundesland",
    "jahr_monat":          "year_month",
    "anzahl_organisation": "solar_organisation",
    "anzahl_privat":       "solar_privat",
    "kw_organisation":     "netto_kw_organisation",
    "kw_privat":           "netto_kw_privat",
})

for col in ["solar_organisation", "solar_privat", "netto_kw_organisation", "netto_kw_privat"]:
    if col not in solar_wide.columns:
        solar_wide[col] = 0

solar_wide["solar_total"]   = solar_wide["solar_organisation"]   + solar_wide["solar_privat"]
solar_wide["netto_kw_total"]= solar_wide["netto_kw_organisation"] + solar_wide["netto_kw_privat"]

# ── 2. Mandate: merge the mandate index ────────────────────────────────────────

print("Merging the mandate index …")
mandate_idx = pd.read_csv(MANDATE_IDX).rename(columns={"Bundesland": "bundesland"})
mandate_idx = mandate_idx[["bundesland", "year_month", "mandate_commercial", "mandate_private", "mandate_score"]]

panel = solar_wide.merge(mandate_idx, on=["bundesland", "year_month"], how="left")

# ── 3. Completions: merge Destatis annual data ─────────────────────────────────

print("Merging Baufertigstellungen …")
comp = pd.read_csv(COMPLETIONS)
comp["year"] = comp["year"].astype(str)

panel["year"] = panel["year_month"].str[:4]
panel = panel.merge(comp, on=["bundesland", "year"], how="left")
panel = panel.drop(columns="year")

# ── 4. Drop months with missing completions (caps at last year with Destatis data)

panel = panel[panel["completions_wohngebaeude"].notna()]

# ── 5. Sort and save ───────────────────────────────────────────────────────────

col_order = [
    "bundesland", "year_month",
    "solar_organisation", "solar_privat",
    "netto_kw_organisation", "netto_kw_privat",
    "solar_total", "netto_kw_total",
    "mandate_commercial", "mandate_private", "mandate_score",
    "completions_wohngebaeude", "completions_nichtwohn", "completions_gesamt",
]
panel = panel[col_order].sort_values(["bundesland", "year_month"]).reset_index(drop=True)

panel.to_csv(OUT, index=False)
print(f"Saved: {OUT.name}  ({len(panel):,} rows, {panel['bundesland'].nunique()} Bundesländer)")

# ── 5. Spot-check against known values ────────────────────────────────────────

print("\nSpot-check — Hamburg 2023:")
hh23 = panel[(panel["bundesland"] == "Hamburg") & (panel["year_month"].str.startswith("2023"))]
print(hh23[["year_month", "solar_privat", "mandate_private", "completions_wohngebaeude"]].to_string(index=False))

missing_mandate = panel["mandate_commercial"].isna().sum()
missing_comp    = panel["completions_wohngebaeude"].isna().sum()
print(f"\nMissing mandate values:      {missing_mandate}")
print(f"Missing completions values:  {missing_comp}")
