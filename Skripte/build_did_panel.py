#!/usr/bin/env python3
"""
Build the yearly DiD panel for the Hamburg Solardachpflicht analysis.

Treatment group  — HH_grenze (n=37: 31 first ring + 6 second ring)
Control group    — SH_grenze (n=22: 17+5) + NI_grenze (n=8: 7+1)
Excluded         — Beiderseits split PLZs (n=3): 21039, 22113, 22145
Group membership — imported from Skripte/plz_groups.py (single source of truth);
                   the first/second ring split used by the main DiD spec also
                   lives there (did_analysis.py filters on SECOND_RING)

Source: Auswertung/Panels/A_deutschland_plz_monat_operatortyp.csv
Output: Auswertung/Panels/D_did_panel_yearly.csv

Design notes:
  - Two treatment steps: post2023 (Neubau mandate) and post2024 (Dachsanierung)
  - Operator type kept as a dimension to allow private/org heterogeneity analysis
  - 2025 data included as-is: the MaStR export vintage (April 2026) closes the
    2015-2025 window with at least four months of registration buffer, so 2025
    is not materially incomplete (no year_incomplete flag; see CLAUDE.md)
  - pre_mastr_share > 0 in 2015-2018 rows reflects retrospective MaStR registrations;
    these are real installations but coverage is lower than post-2019 years
"""

from pathlib import Path
import pandas as pd

BASE     = Path(__file__).parent.parent
IN_PATH  = BASE / "Auswertung/Panels/A_deutschland_plz_monat_operatortyp.csv"
PLZ_GEO  = BASE / "Daten/PLZ_Gebiete_3575278427074611710.csv"
OUT_DIR  = BASE / "Auswertung/Panels"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── PLZ definitions — imported from the single source of truth ────────────────

from plz_groups import (
    TREATMENT, SH_CONTROL, NI_CONTROL,
    EXCLUDED_BEIDERSEITS as EXCLUDED,
)

ALL_PLZS = TREATMENT + SH_CONTROL + NI_CONTROL
YEAR_MIN, YEAR_MAX = 2015, 2025
OPERATOR_TYPES = ["privat", "organisation"]

# ── Load and filter ───────────────────────────────────────────────────────────

raw = pd.read_csv(IN_PATH, dtype={"Postleitzahl": str})
raw = raw[raw["Postleitzahl"].isin(ALL_PLZS)].copy()
raw["year"] = raw["jahr_monat"].str[:4].astype(int)
raw = raw[(raw["year"] >= YEAR_MIN) & (raw["year"] <= YEAR_MAX)]

# ── Aggregate monthly → yearly ────────────────────────────────────────────────

yearly = (
    raw.groupby(["Postleitzahl", "year", "operator_type"], observed=True)
    .agg(
        anzahl_anlagen=("anzahl_anlagen", "sum"),
        netto_kw=("netto_kw", "sum"),
        brutto_kw=("brutto_kw", "sum"),
    )
    .reset_index()
)

# ── Build balanced skeleton (all PLZ × year × operator_type combinations) ─────

idx = pd.MultiIndex.from_product(
    [ALL_PLZS, range(YEAR_MIN, YEAR_MAX + 1), OPERATOR_TYPES],
    names=["Postleitzahl", "year", "operator_type"],
)
skeleton = pd.DataFrame(index=idx).reset_index()

panel = skeleton.merge(yearly, on=["Postleitzahl", "year", "operator_type"], how="left")
panel[["anzahl_anlagen", "netto_kw", "brutto_kw"]] = (
    panel[["anzahl_anlagen", "netto_kw", "brutto_kw"]].fillna(0)
)

# ── Attach DiD indicator columns ──────────────────────────────────────────────

plz_meta = pd.concat([
    pd.DataFrame({"Postleitzahl": TREATMENT, "group": "HH_grenze",
                  "treated": 1, "bundesland": "Hamburg"}),
    pd.DataFrame({"Postleitzahl": SH_CONTROL, "group": "SH_grenze",
                  "treated": 0, "bundesland": "Schleswig-Holstein"}),
    pd.DataFrame({"Postleitzahl": NI_CONTROL, "group": "NI_grenze",
                  "treated": 0, "bundesland": "Niedersachsen"}),
])

panel = panel.merge(plz_meta, on="Postleitzahl", how="left")

# DiD post-period dummies
panel["post2023"] = (panel["year"] >= 2023).astype(int)
panel["post2024"] = (panel["year"] >= 2024).astype(int)

# ── Attach PLZ area ───────────────────────────────────────────────────────────

geo = (
    pd.read_csv(PLZ_GEO, dtype={"Postleitzahl": str})
    .assign(Postleitzahl=lambda d: d["Postleitzahl"].str.zfill(5))
    [["Postleitzahl", "Gebietgröße in km²"]]
    .rename(columns={"Gebietgröße in km²": "flaeche_km2"})
)
panel = panel.merge(geo, on="Postleitzahl", how="left")

# ── Sort and save ─────────────────────────────────────────────────────────────

col_order = [
    "Postleitzahl", "bundesland", "group", "treated",
    "year", "operator_type",
    "anzahl_anlagen", "netto_kw", "brutto_kw",
    "flaeche_km2", "post2023", "post2024",
]
panel = panel[col_order].sort_values(["Postleitzahl", "year", "operator_type"])

out_path = OUT_DIR / "D_did_panel_yearly.csv"
panel.to_csv(out_path, index=False)

# ── Summary ───────────────────────────────────────────────────────────────────

print("=" * 60)
print("DiD Panel — build complete")
print("=" * 60)
print(f"Output: {out_path}")
print(f"Rows:   {len(panel):,}")
print(f"  Expected: {len(ALL_PLZS)} PLZs × {YEAR_MAX - YEAR_MIN + 1} years × "
      f"{len(OPERATOR_TYPES)} operator types = "
      f"{len(ALL_PLZS) * (YEAR_MAX - YEAR_MIN + 1) * len(OPERATOR_TYPES):,}")
print()
print("PLZ counts:")
print(f"  Treatment (HH_grenze): {len(TREATMENT)}")
print(f"  Control   (SH_grenze): {len(SH_CONTROL)}")
print(f"  Control   (NI_grenze): {len(NI_CONTROL)}")
print(f"  Excluded  (Beiderseits): {sorted(EXCLUDED)}")
print()
print("Zero-fill summary (rows where anzahl_anlagen == 0):")
zeros = panel[panel["anzahl_anlagen"] == 0]
print(f"  {len(zeros):,} zero rows ({100*len(zeros)/len(panel):.1f}%)")
print()
print("Installations by year and group:")
pivot = (
    panel.groupby(["year", "group"])["anzahl_anlagen"]
    .sum()
    .unstack("group")
    .fillna(0)
    .astype(int)
)
print(pivot.to_string())
print("=" * 60)
