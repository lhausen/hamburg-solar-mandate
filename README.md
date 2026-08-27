# Hamburg Solar Mandate — Replication Material

Code and data for the bachelor's thesis *Evaluating Hamburg's Solar Mandate:
A Causal Analysis of Solar Expansion* (Universität Hamburg, 2026). The
repository reproduces every estimate, table and figure reported in the thesis.

## Layout

```
data/
  raw/      MaStR bulk export (not tracked -- see data/raw/README.md)
  panels/   the three analysis panels built from the raw export (shipped)
  aux/      building completions, postal-code geometries
scripts/
  00-04     data pipeline: raw export -> analysis file -> panels
  05-06     estimation: border DiD and synthetic control
  08-09     sample-construction table and data-quality audit (need raw data)
  figures/  one script per thesis figure, f01-f09
output/     everything the scripts produce (shipped, so results can be
            checked without running anything)
run_all.py  runs the full chain; see below
```

## Quickstart (no download needed)

The panels in `data/panels/` are the exact inputs behind the thesis results,
so the estimations and figures run as-is:

```
pip install -r requirements.txt
python3 run_all.py
```

This re-estimates the DiD models, the synthetic control, and rebuilds all
figures into `output/`. Expected headline results (thesis chapter 5):

| Quantity | Value |
|---|---|
| Main DiD coefficient (installations per km² and year) | 1.956 (SE 0.849, p = 0.022) |
| Effect relative to the counterfactual level | 39.4% |
| Two-step: post-2023 / additional post-2024 | 1.216 / 1.111 |
| Total post-2024 effect | 2.327 (p = 0.004) |
| Pre-trend joint test | F(7,54) = 1.12, p = 0.363 |
| Wild cluster bootstrap p (main coefficient) | 0.016 |
| Placebo (onset 2021) | 0.243 (p = 0.311) |
| Capacity outcome (kW per km² and year) | 14.290 (p = 0.031), 34.9% |
| Synthetic control | 100% Bremen, pre-RMSPE 0.370, mean post gap -3.91 |

## Full rebuild from the raw export

Download the export as described in `data/raw/README.md`, then:

```
python3 run_all.py --from-raw
```

This parses the bulk export, rebuilds the panels (they reproduce the shipped
ones), and reruns everything, including the two scripts that can only run on
the unfiltered export: the sample-construction table
(`08_make_funnel_table.py`) and the data-quality audit
(`09_data_quality_audit.py`).

## What produces what in the thesis

| Thesis item | Script | Output |
|---|---|---|
| Table 1 (sample construction) | `08_make_funnel_table.py` | `output/tables/data_funnel_table.tex` |
| Table 2 (summary statistics) | `figures/f09_summary_statistics.py` | `output/tables/summary_statistics.csv` |
| Tables 3-4, appendix table (DiD, robustness, event study) | `05_run_did.py` | `output/did/<spec>/Tables/` |
| Figure 1 (mandate timeline) | `figures/f01_mandate_timeline.py` | `output/figures/` |
| Figures 2-3 (Hamburg vs. Germany rate, indexed) | `figures/f02`, `f03` | `output/figures/` |
| Figure 4 (installations vs. completions) | `figures/f04` | `output/figures/` |
| Figure 5 (postal-code growth map, appendix) | `figures/f05` | `output/figures/` |
| Figure 6 (border groups map, appendix) | `figures/f06` | `output/figures/` |
| Figure 7 (pre-period parallel trends) | `figures/f07` | `output/figures/` |
| Figures 8-9 (synthetic control path and gap) | `06_run_scm.py` | `output/scm/Figures/` |
| Figure 10 (event study) | `05_run_did.py` | `output/did/05__per_km2__privat__start2015/base/Figures/` |
| Appendix figure (completions by state) | `figures/f08_completions_states.py` | `output/figures/` |
| Filter counts cited in chapter 4 | `09_data_quality_audit.py` | `output/reports/` |

## Specifications

`05_run_did.py` estimates exactly the models reported in the thesis: private
installations per km² (main model, plus a placebo with treatment onset moved
to 2021 and an asinh variant), installed capacity per km² (plus placebo), and
the unnormalised count model, which fails the pre-trend test and is reported
to motivate the normalised outcome. Standard errors are clustered at
postal-code level; the wild cluster bootstrap (Rademacher weights, 999
replications, seed 42) is run for the main coefficient.

`06_run_scm.py` estimates the synthetic control for Hamburg (donor pool: 13
Bundesländer, excluding Baden-Württemberg and Berlin) on private
installations per newly completed residential building, annual, pre-period
2015-2022.

## Data sources

Solar installations: Marktstammdatenregister (Bundesnetzagentur), bulk export
April 2026. Building completions: Destatis, table 31121-0100. Postal-code
geometries: Esri Deutschland / OpenStreetMap contributors; state geometries
in `data/aux/postleitzahlen_json/`. Mandate dates: coded from the state
climate protection acts (`scripts/mandate_data.py`); the legal texts are
cited in the thesis and not redistributed here.
