#!/usr/bin/env python3
"""
Parse MaStR Gesamtdatenexport ZIP → clean solar CSV for Germany.

Sources used from ZIP:
  EinheitenSolar_*.xml   — core unit data (60 files)
  Marktakteure_*.xml     — operator type: private vs. organisation (53 files)

Output:
  Daten/Solardaten/mastr_solar_deutschland.csv
"""

import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
import re

# Paths derive from the repo location; the bulk ZIP is not tracked in the repo,
# so its location can be overridden via the MASTR_ZIP environment variable.
import os
BASE     = Path(__file__).resolve().parents[1]
ZIP_PATH = Path(os.environ.get(
    "MASTR_ZIP", BASE / "data" / "raw" / "Gesamtdatenexport_20260401_25.2.zip"))
OUT_PATH = BASE / "data" / "raw" / "mastr_solar_deutschland.csv"

# ── Catalog decodings ──────────────────────────────────────────────────────
BUNDESLAND = {
    "1400": "Brandenburg",
    "1401": "Berlin",
    "1402": "Baden-Württemberg",
    "1403": "Bayern",
    "1404": "Bremen",
    "1405": "Hessen",
    "1406": "Hamburg",
    "1407": "Mecklenburg-Vorpommern",
    "1408": "Niedersachsen",
    "1409": "Nordrhein-Westfalen",
    "1410": "Rheinland-Pfalz",
    "1411": "Schleswig-Holstein",
    "1412": "Saarland",
    "1413": "Sachsen",
    "1414": "Sachsen-Anhalt",
    "1415": "Thüringen",
}

STATUS_IN_BETRIEB = "35"

# ArtDerSolaranlage: 853 = Aufdachanlage (rooftop), 852 = Freiflächenanlage
# Nutzungsbereich:   1453 = Bauliche Anlage (Hausdach etc.), 1455 = Freifläche

SOLAR_FIELDS = [
    "EinheitMastrNummer",
    "AnlagenbetreiberMastrNummer",
    "Bundesland",
    "Landkreis",
    "Gemeinde",
    "Gemeindeschluessel",
    "Postleitzahl",
    "Ort",
    "Inbetriebnahmedatum",
    "EinheitBetriebsstatus",
    "Bruttoleistung",
    "Nettonennleistung",
    "ArtDerSolaranlage",
    "Nutzungsbereich",
]


def parse_marktakteure(z: zipfile.ZipFile) -> dict[str, bool]:
    """Build lookup: MastrNummer → is_private (True = natürliche Person)."""
    files = sorted(n for n in z.namelist() if re.match(r"Marktakteure_\d+\.xml", n))
    lookup: dict[str, bool] = {}
    print(f"Parsing {len(files)} Marktakteure files …")
    for i, fname in enumerate(files, 1):
        with z.open(fname) as f:
            for _, elem in ET.iterparse(f, events=("end",)):
                if elem.tag == "Marktakteur":
                    nr  = (elem.findtext("MastrNummer") or "").strip()
                    art = (elem.findtext("Personenart") or "").strip()
                    if nr:
                        # Personenart catalog value 518 = "natürliche Person"
                        # (MaStR Katalogwerte, Katalogkategorie "Personenart";
                        # verify against Katalogwerte.xml in the bulk export).
                        lookup[nr] = (art == "518")
                    elem.clear()
        print(f"  [{i}/{len(files)}] {fname}  —  {len(lookup):,} operators so far")
    print(f"\n  Done. {len(lookup):,} operators loaded.")
    return lookup


def parse_solar(z: zipfile.ZipFile, betreiber_lookup: dict[str, bool]) -> pd.DataFrame:
    """Parse all EinheitenSolar XML files and return a DataFrame."""
    files = sorted(n for n in z.namelist() if re.match(r"EinheitenSolar_\d+\.xml", n))
    print(f"\nParsing {len(files)} EinheitenSolar files …")
    rows = []
    total = 0

    for i, fname in enumerate(files, 1):
        file_rows = 0
        with z.open(fname) as f:
            for _, elem in ET.iterparse(f, events=("end",)):
                if elem.tag == "EinheitSolar":
                    status = (elem.findtext("EinheitBetriebsstatus") or "").strip()
                    bl     = (elem.findtext("Bundesland") or "").strip()

                    # Keep only active systems in Germany
                    if status != STATUS_IN_BETRIEB or bl not in BUNDESLAND:
                        elem.clear()
                        continue

                    row = {field: (elem.findtext(field) or "").strip()
                           for field in SOLAR_FIELDS}

                    # Decode Bundesland
                    row["Bundesland"] = BUNDESLAND[bl]

                    # Resolve operator type. Units whose operator ID is not
                    # found in Marktakteure default to "organisation"; the
                    # unmatched share is reported in the sanity check below.
                    betreiber_nr = row.get("AnlagenbetreiberMastrNummer", "")
                    row["operator_matched"] = betreiber_nr in betreiber_lookup
                    row["is_private"] = betreiber_lookup.get(betreiber_nr, False)
                    row["operator_type"] = "privat" if row["is_private"] else "organisation"

                    rows.append(row)
                    file_rows += 1
                    elem.clear()

        total += file_rows
        print(f"  [{i}/{len(files)}] {fname}  —  +{file_rows:,} Anlagen  (gesamt: {total:,})")

    print(f"\n  Done. {total:,} active solar systems parsed.")
    return pd.DataFrame(rows)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df["Inbetriebnahmedatum"] = pd.to_datetime(df["Inbetriebnahmedatum"], errors="coerce")
    df["Nettonennleistung"]   = pd.to_numeric(df["Nettonennleistung"].str.replace(",", "."), errors="coerce")
    df["Bruttoleistung"]      = pd.to_numeric(df["Bruttoleistung"].str.replace(",", "."),   errors="coerce")
    df["Postleitzahl"]        = df["Postleitzahl"].str.zfill(5)

    # Drop rows with missing key fields
    before = len(df)
    df = df.dropna(subset=["Inbetriebnahmedatum", "Nettonennleistung"])
    print(f"  Dropped {before - len(df):,} rows with missing date or capacity.")
    return df


# ── Main ───────────────────────────────────────────────────────────────────
print(f"Opening ZIP: {ZIP_PATH.name}")
with zipfile.ZipFile(ZIP_PATH) as z:
    betreiber = parse_marktakteure(z)
    df = parse_solar(z, betreiber)

print("\nCleaning …")
df = clean(df)

print(f"\nSaving to {OUT_PATH} …")
df.to_csv(OUT_PATH, index=False)
print(f"Done! {len(df):,} rows, {OUT_PATH.stat().st_size / 1e6:.0f} MB")

# Quick sanity check
print("\n── Bundesland counts ──")
print(df["Bundesland"].value_counts().to_string())
print(f"\n── operator_type ──")
print(df["operator_type"].value_counts().to_string())
n_unmatched = int((~df["operator_matched"]).sum())
print(f"\n── operator match rate ──")
print(f"  Units with operator ID not found in Marktakteure "
      f"(defaulted to 'organisation'): {n_unmatched:,} "
      f"({100 * n_unmatched / len(df):.2f}%)")
print(f"\n── date range ──")
print(f"  {df['Inbetriebnahmedatum'].min().date()} → {df['Inbetriebnahmedatum'].max().date()}")
