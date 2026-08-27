#!/usr/bin/env python3
"""
mandate_data.py — Shared solar mandate dataset for the Descriptive mandate
visualizations (D6 and its 2026-08-09 alternative-visualization candidates).

SINGLE SOURCE OF TRUTH for MANDATE_DATA — do not duplicate a second copy in
any D6* script. Extracted from D6_mandate_timeline.py so the original Gantt
chart and the three alternative-visualization candidates it inspired
(row-timeline, scope-over-time step chart, state×type heatmap) all draw from
the identical dataset instead of risking silently-diverging transcriptions.

Source: BSW, Übersicht Solarpflichten Bundesländer (June 2024) + CLAUDE.md
(Baden-Württemberg dates cross-checked against primary sources, see CLAUDE.md
footnote 1).

Each entry: (state, type, start_year, start_month, note)
  type: "commercial" | "private" | "bestand"
  note: None, or a short scope-limitation tag ("weak", "Nichtwohn", "public",
        "Landeseigene", "commercial" [=Bestand mandate covers commercial
        buildings only], "pending/unclear", "ext. source")
"""

MANDATE_DATA = [
    # Hamburg — most comprehensive (treatment)
    ("Hamburg",             "commercial", 2023, 1,  None),
    ("Hamburg",             "private",    2023, 1,  None),
    ("Hamburg",             "bestand",    2024, 1,  None),
    # Berlin — also private Neubau from Jan 2023
    ("Berlin",              "commercial", 2023, 1,  None),
    ("Berlin",              "private",    2023, 1,  None),
    ("Berlin",              "bestand",    2023, 1,  None),
    # Bremen — private Neubau but late (Jul 2025)
    ("Bremen",              "commercial", 2025, 7,  None),
    ("Bremen",              "private",    2025, 7,  None),
    ("Bremen",              "bestand",    2024, 7,  None),
    # NRW
    ("Nordrhein-Westfalen", "commercial", 2024, 1,  None),
    ("Nordrhein-Westfalen", "private",    2025, 1,  None),
    ("Nordrhein-Westfalen", "bestand",    2026, 1,  None),
    # Niedersachsen (weak private 2025)
    ("Niedersachsen",       "commercial", 2023, 1,  None),
    ("Niedersachsen",       "private",    2025, 1,  "weak"),
    # Schleswig-Holstein (commercial Neubau + Bestand Nichtwohn only)
    ("Schleswig-Holstein",  "commercial", 2023, 1,  None),
    ("Schleswig-Holstein",  "bestand",    2023, 1,  "Nichtwohn"),
    # Rheinland-Pfalz
    ("Rheinland-Pfalz",     "commercial", 2023, 1,  None),
    ("Rheinland-Pfalz",     "bestand",    2024, 1,  "public"),
    # Hessen
    ("Hessen",              "commercial", 2023, 11, None),
    ("Hessen",              "bestand",    2024, 11, "Landeseigene"),
    # Bayern
    ("Bayern",              "commercial", 2023, 3,  None),
    ("Bayern",              "bestand",    2025, 1,  "Nichtwohn"),
    # Brandenburg
    ("Brandenburg",         "commercial", 2024, 6,  None),
    ("Brandenburg",         "bestand",    2024, 6,  "commercial"),
    # Baden-Württemberg (external source)
    ("Baden-Württemberg",   "commercial", 2022, 5,  "ext. source"),
    ("Baden-Württemberg",   "bestand",    2023, 1,  "ext. source"),
    # States with no or only future mandates — commercial Neubau where applicable
    ("Saarland",            "commercial", 2024, 1,  "pending/unclear"),
    ("Sachsen",             "commercial", 2024, 1,  "pending/unclear"),
    ("Sachsen-Anhalt",      "commercial", 2024, 1,  "pending/unclear"),
    ("Thüringen",           "commercial", 2024, 1,  "pending/unclear"),
    ("Mecklenburg-Vorpommern", "commercial", 2024, 1, "pending/unclear"),
]

TYPE_COLORS = {
    "commercial": "#2166AC",   # blue
    "private":    "#D94F3D",   # red
    "bestand":    "#1B7837",   # green
}
TYPE_LABELS = {
    "commercial": "Commercial Neubau",
    "private":    "Private/Wohn Neubau",
    "bestand":    "Bestandsgebäude",
}

# Notes that mark a scope-limited (not full) mandate — used by every
# visualization to dim/flag these rather than showing them at full strength.
SCOPE_LIMITED_NOTES = {
    "weak", "Nichtwohn", "public", "Landeseigene", "commercial",
    "pending/unclear",
}
