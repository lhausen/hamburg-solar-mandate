#!/usr/bin/env python3
"""
SCM_30_rate_neubau_privat_annual.py -- MAIN SCM SPEC (as of 2026-08-10)
Annual SCM -- outcome: private PV installations per new residential building
  rate_privat_y = solar_privat_y / completions_wohngebaeude_y

Annual resolution, not quarterly like the retired SCM_20/21_rate_neubau_privat.R.
Rationale: completions_wohngebaeude (Daten/Neubaudaten/
completions_bundesland_annual.csv, Destatis 31121-0100) is genuine annual
data, broadcast to all 12 months of its year by build_panel_e.py. The
quarterly spec's "quarterly" denominator was therefore that same annual
figure divided by 4 -- one real observation copied four times with a scaling
factor, not four independent measurements. This spec uses the completions
data at its true resolution instead.

Uses the pysyncon package (Python port of R's Synth), not R -- consistent
with the rest of this pipeline, which is Python throughout except the
did_main_spec.R cross-check.

Single spec, donor pool: 13 BL (excl. BW, Berlin). No no-Bremen robustness
variant (dropped 2026-08-10, user decision): Bremen's own mandate only binds
from Jul 2024 (Bestand) / Jul 2025 (Neubau), and its raw installation series
shows no discontinuity at either date beyond the same post-2022 EEG-driven
boom every state shows -- excluding it from the donor pool has no basis in
the installations data. Bremen still receives ~100% of the donor weight;
that is reported as a limitation, not addressed by dropping it from the pool.

Spec mirrors SCM_20 as closely as annual resolution allows:
  Pre-period: 2015-2022 (8 years) | T0: 2023 (time_id = 9)
  Special predictors: 4 x 2-year sub-periods (2015-16, 17-18, 19-20, 21-22)
    -- same sub-period definition as the quarterly spec, just now each block
    is 2 annual points instead of 8 quarterly ones spanning the same years.

Output:
  Auswertung/Causal inference/01_SCM_Bundesebene/
    17__rate_neubau_privat_annual__2015-2022__vollerPool/
"""

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pysyncon import Dataprep, Synth

BASE      = pathlib.Path(__file__).resolve().parents[1]
BASE_SCM  = BASE / "output"
BASE_SPEC = BASE_SCM / "scm"
for sub in ("Data", "Tables", "Figures"):
    (BASE_SPEC / sub).mkdir(parents=True, exist_ok=True)

PANEL_C = BASE / "data" / "panels" / "C_bundesland_panel_monthly.csv"

TREATMENT = "Hamburg"
BL_EXCL   = ["Baden-Württemberg", "Berlin"]

PRE = list(range(1, 9))    # 2015-2022, time_id 1-8
ALL = list(range(1, 12))   # 2015-2025, time_id 1-11
T0  = 9                    # 2023

C_HAMBURG = "#B22222"
C_SYNTH   = "#2060A0"

# ── 1. Build annual panel ─────────────────────────────────────────────────────
print("Building annual panel …")
raw = pd.read_csv(PANEL_C)
raw["year"] = raw["year_month"].str[:4].astype(int)

annual = (
    raw.groupby(["bundesland", "year"])
    .agg(
        solar_privat_y=("solar_privat", "sum"),
        # completions_wohngebaeude is the same annual figure repeated across
        # all 12 months of its year (build_panel_e.py); mean() over the year
        # just collapses those 12 identical values back to the one real number.
        completions_y=("completions_wohngebaeude", "mean"),
    )
    .reset_index()
)
annual["rate_privat_y"] = annual["solar_privat_y"] / annual["completions_y"]
annual["time_id"] = annual["year"] - 2015 + 1
annual = annual.sort_values(["bundesland", "year"]).reset_index(drop=True)

counts = annual.groupby("bundesland").size()
assert (counts == 11).all(), f"Unbalanced annual panel: {counts[counts != 11]}"

print("Per-Neubau validation (Hamburg, Bremen, Niedersachsen, 2021-2025):")
print(
    annual[annual["bundesland"].isin(["Hamburg", "Bremen", "Niedersachsen"]) & annual["year"].between(2021, 2025)]
    [["bundesland", "year", "solar_privat_y", "completions_y", "rate_privat_y"]]
    .to_string(index=False)
)
print()

# ── 2. Donor pool ──────────────────────────────────────────────────────────────
donor_pool = sorted(set(annual["bundesland"]) - {TREATMENT} - set(BL_EXCL))
annual = annual[annual["bundesland"].isin([TREATMENT] + donor_pool)]

print(f"Donor pool (n={len(donor_pool)}): {', '.join(donor_pool)}")
print(f"PRE: 1-8 (2015-2022)  |  T0: 9 (2023)  |  ALL: 1-11 (2015-2025)\n")

# ── 3. Dataprep + Synth ────────────────────────────────────────────────────────
print("dataprep …")
dataprep = Dataprep(
    foo=annual,
    predictors=["rate_privat_y"],
    predictors_op="mean",
    special_predictors=[
        ("rate_privat_y", [1, 2], "mean"),   # 2015-2016
        ("rate_privat_y", [3, 4], "mean"),   # 2017-2018
        ("rate_privat_y", [5, 6], "mean"),   # 2019-2020
        ("rate_privat_y", [7, 8], "mean"),   # 2021-2022
    ],
    dependent="rate_privat_y",
    unit_variable="bundesland",
    time_variable="time_id",
    treatment_identifier=TREATMENT,
    controls_identifier=donor_pool,
    time_predictors_prior=PRE,
    time_optimize_ssr=PRE,
)
print("dataprep: OK\n")

print("Estimating SCM …")
synth = Synth()
synth.fit(dataprep=dataprep, optim_method="Nelder-Mead", optim_initial="equal")
print("synth: OK\n")

# ── 4. Weights + balance ──────────────────────────────────────────────────────
donor_weights = (
    synth.weights(round=10)
    .rename("weight")
    .to_frame()
    .reset_index()
    .rename(columns={"index": "bundesland"})
)
donor_weights["weight_pct"] = (donor_weights["weight"] * 100).round(2)
donor_weights = donor_weights.sort_values("weight", ascending=False).reset_index(drop=True)

print("=== Donor Weights ===")
print(donor_weights.to_string(index=False))

bal_pred = synth.summary(round=6).reset_index().rename(
    columns={"index": "predictor", "treated": "hamburg", "synthetic": "synthetic", "sample mean": "sample_mean"}
)
print("\n=== Predictor Balance ===")
print(bal_pred.to_string(index=False))

# ── 5. Full-period path (observed vs. synthetic), pre/post RMSPE ─────────────
Z0_all, Z1_all = dataprep.make_outcome_mats(time_period=ALL)
Y_synth = (Z0_all[donor_pool] * synth.W).sum(axis=1)
Y_treat = Z1_all

gap = pd.DataFrame({
    "time_id":   ALL,
    "year":      [2014 + t for t in ALL],
    "Y_hamburg": Y_treat.reindex(ALL).to_numpy(),
    "Y_synth":   Y_synth.reindex(ALL).to_numpy(),
})
gap["gap"]  = gap["Y_hamburg"] - gap["Y_synth"]
gap["post"] = gap["time_id"] >= T0

pre_gap  = gap.loc[~gap["post"], "gap"].to_numpy()
post_gap = gap.loc[gap["post"], "gap"].to_numpy()
pre_rmspe  = float(np.sqrt(np.mean(pre_gap ** 2)))
post_rmspe = float(np.sqrt(np.mean(post_gap ** 2)))
ratio      = post_rmspe / pre_rmspe
mean_post_gap = float(np.mean(post_gap))

print(f"\nPre-RMSPE:  {pre_rmspe:.6f} installations/building/year")
print(f"Post-RMSPE: {post_rmspe:.6f} installations/building/year")
print(f"Ratio:      {ratio:.2f}x")
print(f"Mean post-treatment gap: {mean_post_gap:+.6f} installations/building/year\n")

# ── 6. Save tables ─────────────────────────────────────────────────────────────
annual.to_csv(BASE_SPEC / "Data" / "scm_panel_annual.csv", index=False)
gap.to_csv(BASE_SPEC / "Data" / "gap_series.csv", index=False)
donor_weights.to_csv(BASE_SPEC / "Tables" / "donor_weights.csv", index=False)
bal_pred.to_csv(BASE_SPEC / "Tables" / "predictor_balance.csv", index=False)

rmspe_summary = pd.DataFrame([{
    "Spec": "baseline_annual",
    "Label": "Annual, baseline (T0 = 2023)",
    "T0 (time_id)": T0,
    "T0 Year": 2023,
    "Pre-RMSPE": round(pre_rmspe, 6),
    "Post-RMSPE": round(post_rmspe, 6),
    "Ratio": round(ratio, 2),
    "Mean Post-Gap": round(mean_post_gap, 6),
}])
rmspe_summary.to_csv(BASE_SPEC / "Tables" / "rmspe_summary.csv", index=False)

# ── 7. Figures ──────────────────────────────────────────────────────────────────
x_labels = [2014 + t for t in ALL]

# Path plot and gap plot are placed side by side in the thesis at
# 0.48\textwidth each (down from path_plot's previous 0.72\textwidth solo
# placement), so default matplotlib font sizes would render too small;
# explicit sizes below are scaled up accordingly. Titles and footer captions
# are omitted -- the shared LaTeX figure caption carries that information
# instead, and per Dr. Renner's guidance, code/column names (as the old
# footers had) don't belong in anything thesis-facing.
TICK_FS  = 12
LABEL_FS = 13
LEGEND_FS = 11
ANNOT_FS  = 11

# Path plot
fig, ax = plt.subplots(figsize=(10, 6))
ax.axvline(T0, color="grey", linestyle="--", linewidth=1.2)
ax.plot(gap["time_id"], gap["Y_hamburg"], color=C_HAMBURG, marker="o", markersize=4, label="Hamburg (observed)")
ax.plot(gap["time_id"], gap["Y_synth"], color=C_SYNTH, linestyle="--", marker="o", markersize=4, label="Synthetic Hamburg")
ax.set_xticks(ALL)
ax.set_xticklabels(x_labels)
ax.tick_params(labelsize=TICK_FS)
ax.set_ylabel("Private PV installations per new residential building", fontsize=LABEL_FS)
ax.legend(loc="upper left", framealpha=0.9, fontsize=LEGEND_FS)
ax.text(0.99, 0.02, f"Pre-RMSPE: {pre_rmspe:.3f}", transform=ax.transAxes,
        va="bottom", ha="right", fontsize=ANNOT_FS, color="#666666")
fig.tight_layout()
fig.savefig(BASE_SPEC / "Figures" / "path_plot.png", dpi=150)
plt.close(fig)

# Gap plot. Annotation no longer reports the post/pre-RMSPE ratio: dropped
# from the results table and body text (2026-08-10) as uninterpretable
# without a placebo distribution. Mean post-treatment gap stays, rounded to
# two decimals to match the text ($-3.75$).
fig, ax = plt.subplots(figsize=(10, 6))
ax.axvspan(gap["time_id"].min() - 0.5, T0, color="#EEEEEE", alpha=0.6, zorder=0)
ax.axvspan(T0, gap["time_id"].max() + 0.5, color="#FFEEEE", alpha=0.6, zorder=0)
ax.axhline(0, color="grey", linewidth=1)
ax.axvline(T0, color="grey", linestyle="--", linewidth=1.2)
ax.plot(gap["time_id"], gap["gap"], color=C_HAMBURG, marker="o", markersize=4)
ax.set_xticks(ALL)
ax.set_xticklabels(x_labels)
ax.tick_params(labelsize=TICK_FS)
ax.set_ylabel("Gap (Hamburg − Synthetic Hamburg)", fontsize=LABEL_FS)
ax.text(0.01, 0.98, f"Mean post-gap: {mean_post_gap:+.2f}",
        transform=ax.transAxes, va="top", fontsize=ANNOT_FS, color="#666666")
fig.tight_layout()
fig.savefig(BASE_SPEC / "Figures" / "gap_plot.png", dpi=150)
plt.close(fig)

# Donor weights plot
w_sorted = donor_weights.sort_values("weight_pct")
fig, ax = plt.subplots(figsize=(8, 5))
colors = ["#2060A0" if w > 5 else "#B8B8B8" for w in w_sorted["weight_pct"]]
ax.barh(w_sorted["bundesland"], w_sorted["weight_pct"], color=colors)
for y, w in enumerate(w_sorted["weight_pct"]):
    if w > 0.4:
        ax.text(w + 1, y, f"{w:.1f} %", va="center", fontsize=8.5)
ax.set_xlim(0, 100)
ax.set_xlabel("Weight (%)")
ax.set_title("Donor Weights (W*) — Neubau Rate Spec (Private, Annual)", fontweight="bold")
fig.tight_layout()
fig.savefig(BASE_SPEC / "Figures" / "weights_plot.png", dpi=150)
plt.close(fig)

print(f"Done. All outputs -> {BASE_SPEC.name}/")
