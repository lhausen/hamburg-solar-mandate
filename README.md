# Hamburg Solar Mandate — Replication Material

Code and data for the bachelor's thesis *Evaluating Hamburg's Solar Mandate:
A Causal Analysis of Solar Expansion* (Universität Hamburg, 2026).

This repository contains only what is needed to reproduce the figures, tables
and estimates that appear in the thesis.

## Data

**Solar installations.** Marktstammdatenregister (Bundesnetzagentur), bulk
export retrieved April 2026. The raw export is roughly 800 MB and is not
included here. It can be downloaded with the `open_mastr` package:

```python
from open_mastr import Mastr
Mastr().download(method="bulk")
```

`parse_mastr_bulk.py` turns that export into the single analysis file the
pipeline reads. Alternatively, start from `Auswertung/Panels/` — the panels
built from that file are included, so every step after parsing can be run
without downloading the export. Panel A is stored compressed; unpack it with
`gunzip` before running the scripts that read it.

**Building completions.** Destatis table 31121-0100, in `Daten/Neubaudaten/`.

**Postal code geometry and areas.** `Daten/postleitzahlen_json/` and
`Daten/PLZ_Gebiete_*.csv`.

**Mandate dates.** Coded from the state climate protection acts and the
overview published by the Bundesverband Solarwirtschaft. The legal texts
themselves are not redistributed here; sources are cited in the thesis.

## Running the analysis

```
gunzip -k Auswertung/Panels/A_deutschland_plz_monat_operatortyp.csv.gz

python3 parse_mastr_bulk.py                     # raw export → analysis file
python3 Skripte/rebuild_panels.py               # → Panel A
python3 Skripte/build_mandate_index.py          # → Panel C
python3 Skripte/build_did_panel.py              # → Panel D
python3 Skripte/build_panel_e.py                # → Panel E
python3 Skripte/did_analysis.py                 # DiD estimates, event study
python3 Skripte/SCM/07_rate_neubau/SCM_30_rate_neubau_privat_annual.py
python3 Skripte/Descriptive/run_all.py          # descriptive figures
python3 Skripte/build_data_funnel_table.py      # sample construction table
python3 Skripte/data_quality_audit.py           # filter counts cited in Ch. 4
```

The first five steps rebuild the panels from the raw export. If you start from
the panels included here, unpack Panel A and begin at `did_analysis.py`.

## What produces what in the thesis

| Thesis item | Produced by |
|---|---|
| Table: sample construction | `build_data_funnel_table.py` |
| Table: summary statistics | `Descriptive/D4_summary_statistics.py` |
| Table: DiD estimates, robustness, event-study appendix | `did_analysis.py` |
| Figures 1–7 | `Descriptive/01`–`07`, via `run_all.py` |
| Figures: synthetic control (both panels) | `SCM_30_rate_neubau_privat_annual.py` |
| Figure: event study | `did_analysis.py` |
| Filter counts in the data section | `data_quality_audit.py` |

## Specifications

`did_analysis.py` estimates the four models reported in the thesis and no
others: private installations per km² (the main model), the same model with
treatment onset moved to 2021 as a placebo, installed capacity per km², and
the unnormalised count model, which fails the parallel-trends test and is
reported only to show why the outcome is normalised.

## Requirements

Python 3.10 with `pandas`, `numpy`, `linearmodels`, `pysyncon`, `matplotlib`,
`geopandas`, `open_mastr`.
