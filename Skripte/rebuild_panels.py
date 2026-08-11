#!/usr/bin/env python3
"""
Build Panel A: Germany-wide PLZ × month × operator_type panel.

Source: Daten/Solardaten/mastr_solar_deutschland.csv
Output: Auswertung/Panels/A_deutschland_plz_monat_operatortyp.csv

Filters applied:
  - EinheitBetriebsstatus == 35  (In Betrieb)
  - ArtDerSolaranlage not in {2961 (Balkon), 852 (Freifläche), 2484 (Sonstige)}
  - Nettonennleistung > 0.8 kW
  - Inbetriebnahmedatum >= 2015-01-01
"""

import pandas as pd
import numpy as np
from pathlib import Path

BASE        = Path(__file__).parent.parent
SRC         = BASE / "Daten" / "Solardaten" / "mastr_solar_deutschland.csv"
OUT_PANELS  = BASE / "Auswertung" / "Panels"
OUT_BERICHT = BASE / "Auswertung" / "Berichte"

CHUNK_SIZE    = 500_000
CODE_STECKER  = 2961
CODE_FREIFLÄCHE = 852
CODE_UNKNOWN  = 2484
BALKON_KW     = 0.8
PRE_MASTR_DATE = pd.Timestamp("2019-01-01")
PRE_2015_DATE  = pd.Timestamp("2015-01-01")

def emit(msg=""):
    print(msg)

emit("=" * 72)
emit("  Panel A — Germany-wide PLZ × month × operator_type")
emit("=" * 72)
emit(f"\nFiltering {SRC.name} in chunks of {CHUNK_SIZE:,}...")

filtered_chunks: list[pd.DataFrame] = []

for chunk in pd.read_csv(
        SRC,
        chunksize=CHUNK_SIZE,
        low_memory=False,
        parse_dates=["Inbetriebnahmedatum"],
    ):
    chunk = chunk[chunk["EinheitBetriebsstatus"] == 35]
    chunk = chunk[chunk["ArtDerSolaranlage"] != CODE_STECKER]
    chunk = chunk[chunk["Nettonennleistung"] > BALKON_KW]
    chunk = chunk[chunk["ArtDerSolaranlage"] != CODE_FREIFLÄCHE]
    chunk = chunk[chunk["ArtDerSolaranlage"] != CODE_UNKNOWN]
    # NaT dates drop out here (NaT >= date is False)
    chunk = chunk[chunk["Inbetriebnahmedatum"] >= PRE_2015_DATE]
    filtered_chunks.append(chunk)

emit("Concatenating...")
df = pd.concat(filtered_chunks, ignore_index=True)
del filtered_chunks
emit(f"Filtered dataset: {len(df):,} rows")

# Classify
df["pre_mastr"]  = df["Inbetriebnahmedatum"] < PRE_MASTR_DATE
df["jahr_monat"] = df["Inbetriebnahmedatum"].dt.strftime("%Y-%m")
df["Postleitzahl"] = df["Postleitzahl"].astype(str).str.zfill(5)

# Aggregate: PLZ × Landkreis × Bundesland × operator_type × month
emit("\nAggregating Panel A (PLZ × Landkreis × Bundesland × operator_type × month)...")

pa = (
    # dropna=False: keep rows with missing Landkreis (a handful nationwide) --
    # groupby's default dropna=True would silently discard them.
    df.groupby(
        ["Postleitzahl", "Landkreis", "Bundesland", "operator_type", "jahr_monat"],
        observed=True, sort=True, dropna=False,
    )
    .agg(
        anzahl_anlagen  = ("EinheitMastrNummer", "count"),
        netto_kw        = ("Nettonennleistung",  "sum"  ),
        brutto_kw       = ("Bruttoleistung",     "sum"  ),
        pre_mastr_share = ("pre_mastr",          "mean" ),
    )
    .reset_index()
)

path_pa = OUT_PANELS / "A_deutschland_plz_monat_operatortyp.csv"
pa.to_csv(path_pa, index=False, encoding="utf-8-sig")

emit(f"\nSaved: {path_pa.name}")
emit(f"  Rows:              {len(pa):,}")
emit(f"  Columns:           {list(pa.columns)}")
emit(f"  Date range:        {pa['jahr_monat'].min()}  →  {pa['jahr_monat'].max()}")
emit(f"  Unique PLZs:       {pa['Postleitzahl'].nunique():,}")
emit(f"  Unique Landkreise: {pa['Landkreis'].nunique():,}")
emit(f"  Unique Bundesländer: {pa['Bundesland'].nunique():,}")


# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
emit()
emit("=" * 72)
emit("  FINAL PANEL INVENTORY")
emit("=" * 72)

for path in sorted(OUT_PANELS.glob("*.csv")):
    df_check = pd.read_csv(path, nrows=0)
    size_kb = path.stat().st_size // 1024
    # count rows cheaply
    with open(path) as fh:
        nrows = sum(1 for _ in fh) - 1
    emit(f"\n  {path.name}")
    emit(f"    Rows:    {nrows:,}")
    emit(f"    Columns: {list(df_check.columns)}")
    emit(f"    Size:    {size_kb:,} KB")

emit()
emit("Done.")
