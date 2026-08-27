#!/usr/bin/env python3
"""
data_quality_audit.py — Re-derive the numerical data-quality claims in
CLAUDE.md ("Verified Findings & Data Quality") directly from the single
authoritative solar source, mastr_solar_deutschland.csv, plus the SH
completions file for item (f).

Computes:
  a) Balkonkraftwerk filter — count and share of ArtDerSolaranlage == 2961
  e) EEG-2023 boom — private installations 2023 vs. 2022 growth factor,
     computed twice:
       (i)  first-ring DiD sample (Panel B PLZs minus SECOND_RING from
            plz_groups.py), treated vs. control
       (ii) statewide Hamburg vs. Schleswig-Holstein + Niedersachsen
  f) SH completions source — identify the Kreis-level series in
     "Baufertigstellungen Gebäude SH Gemeinden 2000-2024.csv" with the
     anomalously low 2019 value

NOT computed — (b) registration lag, (c) negative lags, (d) decommissioned
counts — because mastr_solar_deutschland.csv structurally cannot support
them: parse_mastr_bulk.py never extracts Registrierungsdatum, and hard-
filters to EinheitBetriebsstatus == "35" ("In Betrieb") at parse time, so
decommissioned units never enter this file. See CLAUDE.md Verified
Findings 2/3/6 for the number-free methodological notes that replace the
old unverified claims.

Output: Auswertung/Berichte/01_data_quality_audit.txt
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "scripts"))
from plz_groups import SECOND_RING

SRC_MASTR = BASE / "data" / "raw" / "mastr_solar_deutschland.csv"
SRC_B     = BASE / "data" / "panels" / "B_did_panel_yearly.csv"
SRC_SH    = BASE / "data" / "aux" / "Baufertigstellungen Gebäude SH Gemeinden 2000-2024.csv"
OUT       = BASE / "output" / "reports" / "01_data_quality_audit.txt"
OUT.parent.mkdir(parents=True, exist_ok=True)

lines: list[str] = []
def log(s: str = "") -> None:
    lines.append(s)
    print(s)


log("=" * 70)
log("Data Quality Audit — Hamburg Solardachpflicht")
log(f"Script: Skripte/data_quality_audit.py")
log(f"Run date: {date.today().isoformat()}")
log("=" * 70)
log()
log("Source: Daten/Solardaten/mastr_solar_deutschland.csv (single authoritative")
log("solar source; already filtered to EinheitBetriebsstatus == 'In Betrieb' and")
log("Registrierungsdatum was never extracted — see note at bottom of this file.")
log()

print("Loading mastr_solar_deutschland.csv …")
df = pd.read_csv(
    SRC_MASTR,
    usecols=["Postleitzahl", "Bundesland", "Inbetriebnahmedatum",
             "ArtDerSolaranlage", "operator_type"],
    dtype={"Postleitzahl": str},
)
df["year"] = pd.to_datetime(df["Inbetriebnahmedatum"], errors="coerce").dt.year
total_rows = len(df)

# ── (a) Balkonkraftwerk filter ────────────────────────────────────────────────
log("-" * 70)
log("(a) Balkonkraftwerk filter — ArtDerSolaranlage == 2961")
log("-" * 70)
n_balkon = int((df["ArtDerSolaranlage"] == 2961).sum())
share_balkon = n_balkon / total_rows * 100
log(f"  Total rows in source:      {total_rows:,}")
log(f"  ArtDerSolaranlage == 2961: {n_balkon:,}")
log(f"  Share:                     {share_balkon:.1f}%")
log()

# ── (e) EEG-2023 boom — growth factor, two ways ───────────────────────────────
log("-" * 70)
log("(e) EEG-2023 boom — private installations, 2023 vs. 2022 growth factor")
log("-" * 70)

priv = df[df["operator_type"] == "privat"]

# (i) first-ring DiD sample: Panel B PLZs minus SECOND_RING, treated vs. control
plz_d = (pd.read_csv(SRC_B, usecols=["Postleitzahl", "treated"], dtype={"Postleitzahl": str})
           .drop_duplicates("Postleitzahl"))
plz_d = plz_d[~plz_d["Postleitzahl"].isin(SECOND_RING)]
treated_plz = set(plz_d.loc[plz_d["treated"] == 1, "Postleitzahl"])
control_plz = set(plz_d.loc[plz_d["treated"] == 0, "Postleitzahl"])

t = priv[priv["Postleitzahl"].isin(treated_plz)]
c = priv[priv["Postleitzahl"].isin(control_plz)]
t22, t23 = int((t["year"] == 2022).sum()), int((t["year"] == 2023).sum())
c22, c23 = int((c["year"] == 2022).sum()), int((c["year"] == 2023).sum())

log(f"  (i) First-ring DiD sample (n=31 treated / n=25 control, SECOND_RING excluded):")
log(f"      Hamburg border PLZs (treated): {t22:,} (2022) -> {t23:,} (2023)  "
    f"= {t23/t22:.2f}x")
log(f"      Control border PLZs:           {c22:,} (2022) -> {c23:,} (2023)  "
    f"= {c23/c22:.2f}x")
log()

# (ii) statewide Hamburg vs. SH + NI
hh   = priv[priv["Bundesland"] == "Hamburg"]
shni = priv[priv["Bundesland"].isin(["Schleswig-Holstein", "Niedersachsen"])]
hh22, hh23 = int((hh["year"] == 2022).sum()), int((hh["year"] == 2023).sum())
sn22, sn23 = int((shni["year"] == 2022).sum()), int((shni["year"] == 2023).sum())

log(f"  (ii) Statewide:")
log(f"      Hamburg (full state):        {hh22:,} (2022) -> {hh23:,} (2023)  "
    f"= {hh23/hh22:.2f}x")
log(f"      Schleswig-Holstein + Niedersachsen: {sn22:,} (2022) -> {sn23:,} (2023)  "
    f"= {sn23/sn22:.2f}x")
log()

# ── (f) SH completions source — anomalous 2019 series ─────────────────────────
log("-" * 70)
log("(f) SH completions source — anomalous 2019 value")
log("-" * 70)

YEAR_COLS = [str(y) for y in range(2010, 2025)]
sh = pd.read_csv(SRC_SH, sep=";", encoding="utf-8-sig", skiprows=8, header=0, dtype=str)
sh.columns = ["Kreis", "Gemeinde"] + YEAR_COLS
sh = sh[sh["Kreis"].notna() & (sh["Kreis"].str.strip() != "")]
for y in YEAR_COLS:
    sh[y] = pd.to_numeric(sh[y].str.strip(), errors="coerce")

totals = sh[sh["Gemeinde"].str.strip() == "Gesamtsumme"].copy()
totals["ratio_2019_vs_neighbors"] = totals["2019"] / totals[["2018", "2020"]].mean(axis=1)
anomaly = totals.sort_values("ratio_2019_vs_neighbors").iloc[0]

log(f"  Checked {len(totals)} Kreis-level Gesamtsumme series for a 2019 value that")
log(f"  is anomalously low relative to its own 2018/2020 neighbors.")
log(f"  Most anomalous series: \"{anomaly['Kreis']}\" (data label only, NOT an")
log(f"  analysis unit — this project never uses Landkreise as an analysis level)")
log(f"    2018: {anomaly['2018']:.0f}   2019: {anomaly['2019']:.0f}   2020: {anomaly['2020']:.0f}")
log(f"    2019 is {anomaly['ratio_2019_vs_neighbors']*100:.0f}% of the 2018/2020 average"
    f" (i.e. a {100 - anomaly['ratio_2019_vs_neighbors']*100:.0f}% drop) — likely partial-year"
    f" reporting in the source.")
log()

# ── Not computed ──────────────────────────────────────────────────────────────
log("-" * 70)
log("(b), (c), (d) — NOT COMPUTED")
log("-" * 70)
log("  mastr_solar_deutschland.csv cannot support these:")
log("    - Registrierungsdatum is never extracted by parse_mastr_bulk.py")
log("      (not in SOLAR_FIELDS, not in the CSV header) -> (b) and (c) are")
log("      not derivable from this source.")
log("    - parse_mastr_bulk.py hard-filters to EinheitBetriebsstatus == \"35\"")
log("      (\"In Betrieb\") at parse time -> decommissioned units never enter")
log("      this file, so (d) is not derivable from this source.")
log("  Per user decision 2026-07-22: not re-deriving from the raw bulk ZIP or")
log("  the superseded per-region CSVs. CLAUDE.md Findings 2/3/6 were rewritten")
log("  as number-free methodological notes instead.")
log()
log("=" * 70)
log("End of audit.")
log("=" * 70)

OUT.write_text("\n".join(lines) + "\n")
print(f"\nSaved: {OUT}")
