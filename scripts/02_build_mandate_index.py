#!/usr/bin/env python3
"""
build_mandate_index.py
Constructs a monthly solar mandate panel for all 16 German Bundesländer.

Source: 240611_BSW-Uebersicht_Solarpflichten_Bundeslaender_Langfassungen.pdf
        (Daten/Quellen/) + CLAUDE.md policy summary.

Two mandate dimensions encoded as binary indicators (1 = binding mandate
active, 0 = no binding mandate):

  mandate_commercial   PV obligation for commercial/Nichtwohngebäude new builds
  mandate_private      PV obligation for private/Wohngebäude new builds

  mandate_score        sum of the two (0–2); primary regression variable

Output: Auswertung/Panels/mandate_index_monthly.csv
        Auswertung/Berichte/02_mandate_index_protokoll.txt
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

BASE        = Path(__file__).resolve().parents[1]
OUT_PANELS  = BASE / "data" / "panels"
OUT_BERICHT = BASE / "output" / "reports"
OUT_PANELS.mkdir(parents=True, exist_ok=True)
OUT_BERICHT.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# MANDATE TABLE
# Each entry: (activation_date_or_None, note)
# None means "no binding mandate exists in this category"
# "soll" means Sollvorschrift (recommendation, not legally binding) → treated as None
#
# Sources per state:
#   Bayern, Berlin, Brandenburg, Bremen, Hamburg, Niedersachsen, Hessen,
#   NRW, Rheinland-Pfalz, Schleswig-Holstein:
#     BSW PDF (240611_BSW-Uebersicht_Solarpflichten_Bundeslaender_Langfassungen.pdf)
#   Baden-Württemberg:
#     § 8a Klimaschutz- und Klimawandelanpassungsgesetz BW (KSG BW) —
#     NOT in BSW PDF; dates from KSG BW legislative history (training knowledge).
#     Flag: source_bw_external = True.
#   Mecklenburg-Vorpommern, Saarland, Sachsen, Sachsen-Anhalt, Thüringen:
#     Absent from BSW PDF; no known binding solar mandate as of June 2024.
# ─────────────────────────────────────────────────────────────────────────────

MANDATES = {
    # ── Baden-Württemberg ─────────────────────────────────────────────────────
    # Umweltministerium BW flyer (primary source):
    #   Nichtwohnbereich Neubau + Parkplätze >35 Stellplätze: 01.01.2022
    #   Wohnbereich Neubau: 01.05.2022
    #   Grundlegende Dachsanierungen (Baubeginn ab): 01.01.2023
    # These predate § 23 KlimaG BW (GBl. 2023 S. 26, in force 11.02.2023),
    # which consolidated and extended the predecessor provisions.
    "Baden-Württemberg": dict(
        commercial_neubau = "2022-01-01",
        private_neubau    = "2022-05-01",
        bestand           = "2023-01-01",
        bestand_scope     = "all",
        source            = "Umweltministerium BW, Photovoltaikpflicht-barrierefrei.pdf (Daten/Quellen/BW/)",
        source_flag       = "pdf",
    ),

    # ── Bayern ────────────────────────────────────────────────────────────────
    # Art. 44a BayBO (text as of 01.05.2026, describing earlier activation dates).
    # § 44a(2): Nichtwohngebäude (excl. residential) Neubau from 2023-03-01 (purely
    #   commercial/industrial) and 2023-07-01 (other Nichtwohngebäude). Using earliest.
    # § 44a(4): Wohngebäude "sollen" — Sollvorschrift, not legally binding → None.
    # § 44a(2) Satz 2: Bestand Dacherneuerung Nichtwohngebäude from 2025-01-01.
    #   → Scope = commercial only → coded 0 per design choice (not relevant for private
    #     building owners).
    # § 44a(1): State-owned (Freistaat) buildings → Landeseigene only → coded 0.
    "Bayern": dict(
        commercial_neubau = "2023-03-01",
        private_neubau    = None,
        bestand           = None,             # Nichtwohngebäude only → 0 per design choice
        bestand_scope     = "commercial",
        source            = "Art. 44a BayBO, primary PDF (Daten/Quellen/Bayern/)",
        source_flag       = "pdf",
    ),

    # ── Berlin ────────────────────────────────────────────────────────────────
    # SolarG BE (GVBl. 77. Jg. Nr. 54, 15. Juli 2021, in force 01.01.2023).
    # § 3(1): applies to ALL nicht-öffentlichen Gebäuden (>50m² Nutzungsfläche).
    # Covers Neubau AND wesentliche Umbauten des Daches (= Bestand).
    # No commercial/private distinction — all private building owners included.
    "Berlin": dict(
        commercial_neubau = "2023-01-01",
        private_neubau    = "2023-01-01",
        bestand           = "2023-01-01",
        bestand_scope     = "all",
        source            = "SolarG BE § 3(1), GVBl. 2021 Nr. 54 (Daten/Quellen/Berlin/)",
        source_flag       = "pdf",
    ),

    # ── Brandenburg ──────────────────────────────────────────────────────────
    # BbgBO § 32a, in force 01.06.2024 (GVBl. I 2023 Nr. 18, 29.09.2023).
    # § 32a(1): "überwiegend öffentlich genutzt" OR "überwiegend gewerblich genutzt"
    #   from 2024-06-01. Wohngebäude explicitly excluded.
    # Bestand: "vollständige Erneuerung der Dachhaut" also from 2024-06-01 —
    #   but only for public/commercial buildings (same scope as Neubau).
    #   → Scope = commercial only → coded 0 per design choice.
    "Brandenburg": dict(
        commercial_neubau = "2024-06-01",
        private_neubau    = None,
        bestand           = None,             # commercial/public only → 0 per design choice
        bestand_scope     = "commercial",
        source            = "BbgBO § 32a, GVBl. I 2023 Nr. 18 (Daten/Quellen/Brandenburg/)",
        source_flag       = "pdf",
    ),

    # ── Bremen ────────────────────────────────────────────────────────────────
    # BremSolarG, consolidated version (Brem.GBl. 2024 S. 589, Inkrafttreten 25.07.2024).
    # § 2(1): Neubau ALL Gebäude (no commercial/private distinction).
    #   Exempt if Bauantrag filed before 2025-07-01 → mandate effective 2025-07-01.
    # § 2(2): Bestand (grundlegende Dachsanierung ≥ 80% Dachfläche) from 2024-07-01,
    #   ALL building owners (no distinction).
    "Bremen": dict(
        commercial_neubau = "2025-07-01",
        private_neubau    = "2025-07-01",
        bestand           = "2024-07-01",
        bestand_scope     = "all",
        source            = "BremSolarG § 2, Brem.GBl. 2024 S. 589 (Daten/Quellen/Bremen/)",
        source_flag       = "pdf",
    ),

    # ── Hamburg ───────────────────────────────────────────────────────────────
    # HmbKliSchG § 16 (Fassung 13.12.2023, Gültig ab 01.01.2024) + § 16a.
    # § 16(2): ALL Gebäude incl. private — Neubau mandate active from 01.01.2023
    #   (original HmbKliSchG 20.02.2020 transitional provisions set 01.01.2023).
    # § 16(2) Satz 2: wesentliche Umbauten des Daches (Bestand) — same provision,
    #   minimum size requirements (30% Brutto-/Nettodachfläche) from 01.01.2024
    #   per § 16(3). Basic Bestand obligation thus effective 01.01.2024.
    # This is the treatment state.
    "Hamburg": dict(
        commercial_neubau = "2023-01-01",
        private_neubau    = "2023-01-01",
        bestand           = "2024-01-01",
        bestand_scope     = "all",
        source            = "HmbKliSchG § 16 + § 16a, Fassung 13.12.2023 (Daten/Quellen/Hamburg/)",
        source_flag       = "pdf",
    ),

    # ── Hessen ────────────────────────────────────────────────────────────────
    # HEG § 9a (Gesamtausgabe, effective 02.08.2023–31.12.2029) + § 12.
    # § 9a: ONLY Landeseigene (state-owned) buildings — Neubau from 29.11.2023,
    #   Bestand from 29.11.2024.
    # § 12: ONLY non-state-owned parking lots (Stellplätze), NOT buildings.
    # No mandate for commercial or private buildings/private owners whatsoever.
    # → All three dimensions 0 per design choice (not relevant for private owners).
    "Hessen": dict(
        commercial_neubau = None,
        private_neubau    = None,
        bestand           = None,
        bestand_scope     = "public_only",
        source            = "HEG § 9a + § 12, GVBl. 2023 S. 582 (Daten/Quellen/Hessen/)",
        source_flag       = "pdf",
    ),

    # ── Mecklenburg-Vorpommern ────────────────────────────────────────────────
    "Mecklenburg-Vorpommern": dict(
        commercial_neubau = None,
        private_neubau    = None,
        bestand           = None,
        bestand_scope     = None,
        source            = "Not in BSW PDF; no known mandate as of 2024-06",
        source_flag       = "absent",
    ),

    # ── Niedersachsen ─────────────────────────────────────────────────────────
    # NBauO § 32a — 5 chronological versions confirmed by primary PDFs.
    # Version 1 (01.01.2022–05.07.2022): commercial Neubau from 2023-01-01.
    # Versions 2–4 (06.07.2022–31.12.2024): commercial from 2023-01-01;
    #   other Nichtwohn from 2024-01-01; Wohngebäude from 2025-01-01 (Neubau only).
    # Version 5 (ab 01.01.2025, current): ALL buildings Neubau (no distinction) from
    #   2025-01-01; § 32a(2) NEW: Bestand (Dacherneuerung bis zur wasserführenden
    #   Schicht) for ALL buildings from 2025-01-01. Scope = all.
    "Niedersachsen": dict(
        commercial_neubau = "2023-01-01",
        private_neubau    = "2025-01-01",
        bestand           = "2025-01-01",
        bestand_scope     = "all",
        source            = "NBauO § 32a, 5 versions (Daten/Quellen/Niedersachen/)",
        source_flag       = "pdf",
    ),

    # ── Nordrhein-Westfalen ───────────────────────────────────────────────────
    # BauO NRW § 42a + SAN-VO NRW (06.06.2024, Gültig ab 19.06.2024).
    # SAN-VO § 1(2) confirms:
    #   1. Nichtwohngebäude Neubau: Bauantrag after 2024-01-01.
    #   2. Kommunale Gebäude Bestand: Dacherneuerung after 2024-07-01 → narrow → 0.
    #   3. Wohngebäude Neubau: Bauantrag after 2025-01-01.
    #   4. All other buildings Bestand (incl. private): Dacherneuerung after 2026-01-01.
    # Bestand from 2026-01-01 applies broadly to ALL buildings → scope = all → 1.
    "Nordrhein-Westfalen": dict(
        commercial_neubau = "2024-01-01",
        private_neubau    = "2025-01-01",
        bestand           = "2026-01-01",
        bestand_scope     = "all",
        source            = "BauO NRW § 42a + SAN-VO NRW, GV.NRW 2024 (Daten/Quellen/NRW/)",
        source_flag       = "pdf",
    ),

    # ── Rheinland-Pfalz ───────────────────────────────────────────────────────
    # LSolarG (GVBl. 2021 S. 550), current version with 22.11.2023 amendment.
    # § 2(1): commercial Neubau from 2023-01-01; public buildings Neubau + Bestand.
    # § 2(2): ALL Neubauten must be "PV-ready" (structural preparation only, not
    #   installation) — NOT an installation mandate → private_neubau = None.
    # Bestand: ONLY for öffentliche Gebäude (public buildings) → narrow → 0 per
    #   design choice (not relevant for private building owners).
    "Rheinland-Pfalz": dict(
        commercial_neubau = "2023-01-01",
        private_neubau    = None,
        bestand           = None,             # public only → 0 per design choice
        bestand_scope     = "public_only",
        source            = "LSolarG § 2 + § 4, GVBl. 2021 S. 550 (Daten/Quellen/Rheinland-Pfalz/)",
        source_flag       = "pdf",
    ),

    # ── Saarland ──────────────────────────────────────────────────────────────
    "Saarland": dict(
        commercial_neubau = None,
        private_neubau    = None,
        bestand           = None,
        bestand_scope     = None,
        source            = "Not in BSW PDF; no known mandate as of 2024-06",
        source_flag       = "absent",
    ),

    # ── Sachsen ───────────────────────────────────────────────────────────────
    "Sachsen": dict(
        commercial_neubau = None,
        private_neubau    = None,
        bestand           = None,
        bestand_scope     = None,
        source            = "Not in BSW PDF; no known mandate as of 2024-06",
        source_flag       = "absent",
    ),

    # ── Sachsen-Anhalt ────────────────────────────────────────────────────────
    "Sachsen-Anhalt": dict(
        commercial_neubau = None,
        private_neubau    = None,
        bestand           = None,
        bestand_scope     = None,
        source            = "Not in BSW PDF; no known mandate as of 2024-06",
        source_flag       = "absent",
    ),

    # ── Schleswig-Holstein ────────────────────────────────────────────────────
    # EWKG § 26 + § 27 (Fassung 25.03.2025, Gültig ab 29.03.2025).
    # § 26(1): Neubau ALL Gebäude (Wohn- und Nichtwohngebäude) AND Renovierung >10%
    #   Dachfläche of Nichtwohngebäude — from 29.03.2025.
    # § 26(6): Wohngebäude EXEMPT if Bauantrag filed within 1 year of amendment
    #   (i.e. before 29.03.2026). Private Neubau mandate effectively from 29.03.2026.
    #   Using 2026-04-01 (first full month after transition window closes).
    # Bestand: § 26(1) "Renovierung... von Nichtwohngebäuden" only → commercial scope
    #   → coded 0 per design choice (not relevant for private building owners).
    # Before 29.03.2025: Nichtwohngebäude Neubau only from 2023-01-01 (old § 11 EWKG).
    "Schleswig-Holstein": dict(
        commercial_neubau = "2023-01-01",
        private_neubau    = "2026-04-01",   # § 26(6) 1-year transition expires 29.03.2026
        bestand           = None,             # Nichtwohngebäude only → 0 per design choice
        bestand_scope     = "commercial",
        source            = "EWKG § 26 + § 27, Fassung 25.03.2025 (Daten/Quellen/SH/)",
        source_flag       = "pdf",
    ),

    # ── Thüringen ─────────────────────────────────────────────────────────────
    "Thüringen": dict(
        commercial_neubau = None,
        private_neubau    = None,
        bestand           = None,
        bestand_scope     = None,
        source            = "Not in BSW PDF; no known mandate as of 2024-06",
        source_flag       = "absent",
    ),
}

EXPECTED_STATES = {
    "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen",
    "Hamburg", "Hessen", "Mecklenburg-Vorpommern", "Niedersachsen",
    "Nordrhein-Westfalen", "Rheinland-Pfalz", "Saarland", "Sachsen",
    "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen",
}
assert set(MANDATES.keys()) == EXPECTED_STATES, \
    f"Missing: {EXPECTED_STATES - set(MANDATES.keys())}"

# ─────────────────────────────────────────────────────────────────────────────
# BUILD MONTHLY PANEL: 2015-01 to 2026-12
# ─────────────────────────────────────────────────────────────────────────────
months = pd.period_range("2015-01", "2026-12", freq="M")

rows = []
for bl, m in MANDATES.items():
    for period in months:
        date = period.to_timestamp()
        rows.append({
            "Bundesland":        bl,
            "year_month":        str(period),
            "mandate_commercial": int(
                m["commercial_neubau"] is not None
                and date >= pd.Timestamp(m["commercial_neubau"])
            ),
            "mandate_private":   int(
                m["private_neubau"] is not None
                and date >= pd.Timestamp(m["private_neubau"])
            ),
            "source_flag":       m["source_flag"],
        })

panel = pd.DataFrame(rows)
panel["mandate_score"] = panel["mandate_commercial"] + panel["mandate_private"]

# ── Output ────────────────────────────────────────────────────────────────────
out_path = OUT_PANELS / "mandate_index_monthly.csv"
panel.to_csv(out_path, index=False, encoding="utf-8-sig")

# ── Terminal summary ──────────────────────────────────────────────────────────
print("=" * 72)
print("  MANDATE INDEX — SUMMARY")
print("=" * 72)

print(f"\nPanel shape: {panel.shape}  ({panel['Bundesland'].nunique()} states × {panel['year_month'].nunique()} months)")
print(f"Saved: {out_path.name}\n")

# Static table: mandate dimensions per state (as of 2024-01)
check_date = "2024-01"
snap = panel[panel["year_month"] == check_date].set_index("Bundesland")

print(f"{'State':<25} {'Comm':>5} {'Priv':>5} {'Score':>6}  {'Source'}")
print("-" * 75)
for bl in sorted(snap.index):
    r = snap.loc[bl]
    src = MANDATES[bl]["source"]
    print(f"  {bl:<23} {r.mandate_commercial:>5} {r.mandate_private:>5} "
          f"{r.mandate_score:>6}  {src}")

print("\nColumn meanings (as of 2024-01):")
print("  Comm  = mandate_commercial")
print("  Priv  = mandate_private")
print("  Score = sum (0–2)")
print("\nFlagged: States marked 'absent' have no confirmed mandate in the source document.")
print("         BaWü dates from Umweltministerium BW flyer (predecessor law, pre-KlimaG BW 2023).\n")

# ── Protocol file ─────────────────────────────────────────────────────────────
lines = ["=" * 72,
         "MANDATE INDEX PROTOCOL — mandate_index_monthly.csv",
         "=" * 72,
         f"",
         f"Generated:   {datetime.now().strftime('%Y-%m-%d %H:%M')}",
         f"Source:      Daten/Quellen/240611_BSW-Uebersicht_Solarpflichten_Bundeslaender_Langfassungen.pdf",
         f"Coverage:    All 16 Bundesländer, 2015-01 to 2026-12",
         f"",
         "Two binary mandate dimensions:",
         "  mandate_commercial   PV obligation for commercial/Nichtwohngebäude new builds",
         "  mandate_private      PV obligation for private/Wohngebäude new builds",
         "  mandate_score        Sum of the two (0–2)",
         "",
         "source_flag values:",
         "  'pdf'      — date verified in BSW PDF (June 2024 edition)",
         "  'external' — date from source external to BSW PDF",
         "  'absent'   — state not in BSW PDF; no known mandate encoded",
         "",
         "=" * 72,
         "STATE-BY-STATE MANDATE DATES",
         "=" * 72, ""]

for bl in sorted(MANDATES.keys()):
    m = MANDATES[bl]
    lines += [
        f"  {bl}",
        f"    commercial_neubau : {m['commercial_neubau'] or '—'}",
        f"    private_neubau    : {m['private_neubau'] or '—'}",
        f"    source            : {m['source']}",
        "",
    ]

lines += [
    "=" * 72,
    "IDENTIFICATION NOTES FOR THESIS",
    "=" * 72,
    "",
    "Hamburg is unique in mandating PRIVATE Wohngebäude from Jan 2023 AND",
    "imposing Bestand obligations (roof renovation) from Jan 2024.",
    "",
    "States with private_neubau mandate (treatment-like for private sector):",
]
priv_states = [bl for bl, m in MANDATES.items() if m["private_neubau"] is not None]
for bl in sorted(priv_states):
    lines.append(f"  {bl}  ({MANDATES[bl]['private_neubau']})")

lines += [
    "",
    "Control group states (SH, NI Landkreise surrounding Hamburg):",
    "  Schleswig-Holstein  commercial + bestand (Nichtwohn) from 2023-01-01",
    "                      NO private mandate — clean control for Hamburg private effect",
    "  Niedersachsen       commercial from 2023-01-01; private from 2025-01-01",
    "                      NO Bestand — clean control for Jan 2024 treatment date",
    "",
    "Berlin: co-treated (private mandate Jan 2023). Exclude from clean control group.",
    "Baden-Württemberg: private mandate May 2022, commercial Jan 2022 (pre-Hamburg).",
    "  Source: Umweltministerium BW flyer (confirmed primary source). Exclude or use",
    "  as treated comparison — pre-dates Hamburg treatment window.",
    "",
    "=" * 72,
]

protocol_text = "\n".join(lines)
protocol_path = OUT_BERICHT / "02_mandate_index_protokoll.txt"
protocol_path.write_text(protocol_text, encoding="utf-8")

print(f"Protocol saved: {protocol_path.name}")
print(f"\nPanel columns: {list(panel.columns)}")
print(f"Mandate score range: {panel['mandate_score'].min()}–{panel['mandate_score'].max()} (max possible: 2)")
print(f"\nDone.")
