#!/usr/bin/env python3
"""
Yearly DiD analysis — Hamburg Solardachpflicht.
Config-driven: each entry in SPECS produces a self-contained output folder.

Robustness specs included:
  base          — main specification
  placebo_t2021 — fake treatment at 2021, sample 2015/19–2022
  asinh         — main spec with asinh-transformed outcome (robustness against
                  the multiplicative EEG-2023 boom coinciding with treatment)

sh_control_matched / ni_control_matched / second_ring used to also be
generated here; they now live under _Additional/ (outside the main pipeline)
with their own standalone Script/run_did.py, since they're secondary
robustness checks, not part of the main spec set. See
_Additional/Auswertung/Causal inference/02_DiD_PLZ/05__per_km2__privat__start2015/.

Each spec writes to:
  Auswertung/Causal inference/02_DiD_PLZ/{spec}/{subfolder}/
    Tables/  00_pretrend_ftest.txt  01_basic_did.txt  02_twostep_did.txt
             03_event_study.txt     04_wild_bootstrap.txt
    Figures/ parallel_trends.png    event_study.png
    Data/    panel snapshot
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from scipy import stats
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from linearmodels.panel import PanelOLS

from plz_groups import SECOND_RING, FIRST_RING_SH, FIRST_RING_NI

BASE     = Path(__file__).resolve().parents[1]
IN_PATH  = BASE / "data/panels/B_did_panel_yearly.csv"
ROOT_OUT = BASE / "output/did"

# Group membership imported from plz_groups.py (single source of truth) --
# also used by build_did_panel.py and every Descriptive/ border figure.
# SECOND_RING is excluded from every spec below (first ring only).
SH_PLZS = FIRST_RING_SH
NI_PLZS = FIRST_RING_NI


@dataclass
class Cfg:
    start:    int         # first year in sample
    end:      int         # last year in sample  (2024 → drop 2025)
    lag:      int         # years to shift mandate onset (0 or 1)
    op:       str         # "privat" | "organisation"
    ctrl:     str | None  # None=all control, "SH"=SH only, "NI"=NI only
    placebo:  int | None  # None=real mandate; else fake onset year
    ref:      int         # reference year for event study
    per_km2:  bool = False    # if True, outcome = outcome_var / flaeche_km2
    outcome_var: str = "anzahl_anlagen"  # "anzahl_anlagen" | "netto_kw"
    transform: str | None = None  # None | "asinh" — applied to the outcome.
    # Rationale for asinh: the EEG-2023 boom was multiplicative (~3× nationally);
    # TWFE in levels only absorbs additive common shocks, so a levels DiD can be
    # inflated by a common multiplicative shock if baseline levels differ.
    # asinh approximates log but handles zero PLZ-years.


SPECS: list[tuple[str, str, Cfg]] = [
    # ── start 2015 ────────────────────────────────────────────────────────────
    ("01__count_anlagen__privat__start2015", "base",
     Cfg(2015, 2025, 0, "privat",       None, None, 2022)),
    ("01__count_anlagen__privat__start2015", "placebo_t2021",
     Cfg(2015, 2022, 0, "privat",       None, 2021, 2020)),
    # ── per km² start 2015 (main spec family) ────────────────────────────────
    ("05__per_km2__privat__start2015", "base",
     Cfg(2015, 2025, 0, "privat",       None, None, 2022, per_km2=True)),
    ("05__per_km2__privat__start2015", "placebo_t2021",
     Cfg(2015, 2022, 0, "privat",       None, 2021, 2020, per_km2=True)),
    ("05__per_km2__privat__start2015", "asinh",
     Cfg(2015, 2025, 0, "privat",       None, None, 2022, per_km2=True, transform="asinh")),
    # ── capacity (netto_kw) per km² start 2015 ───────────────────────────────
    ("09__capacity_per_km2__privat__start2015", "base",
     Cfg(2015, 2025, 0, "privat",       None, None, 2022, per_km2=True, outcome_var="netto_kw")),
    ("09__capacity_per_km2__privat__start2015", "placebo_t2021",
     Cfg(2015, 2022, 0, "privat",       None, 2021, 2020, per_km2=True, outcome_var="netto_kw")),
]


# ── Load ──────────────────────────────────────────────────────────────────────

def load(cfg: Cfg) -> tuple[pd.DataFrame, list[int]]:
    df = pd.read_csv(IN_PATH, dtype={"Postleitzahl": str})

    # Operator filter
    df = df[df["operator_type"] == cfg.op].copy()

    # Control group filter
    if cfg.ctrl == "SH":
        df = df[df["treated"].eq(1) | df["Postleitzahl"].isin(SH_PLZS)]
    elif cfg.ctrl == "NI":
        df = df[df["treated"].eq(1) | df["Postleitzahl"].isin(NI_PLZS)]

    # Exclude second-ring PLZs (every spec here uses the first ring only).
    df = df[~df["Postleitzahl"].isin(SECOND_RING)]

    # Time filter
    df = df[(df["year"] >= cfg.start) & (df["year"] <= cfg.end)]

    # Treatment dummies
    # T1 = new-construction mandate (2023+), T2 = roof-renovation extension
    # (2024+). NOT separately identified in practice — see CLAUDE.md /
    # LEVELS OF ANALYSIS and the note attached to the two-step table output:
    # registration lag makes the delayed T1 effect coincide with T2 onset.
    if cfg.placebo is not None:
        # Fake onset: t1 = placebo year, t2 = placebo + 1
        df["post_t1"] = (df["year"] >= cfg.placebo).astype(int)
        df["post_t2"] = (df["year"] >= cfg.placebo + 1).astype(int)
    else:
        df["post_t1"] = (df["year"] >= 2023 + cfg.lag).astype(int)
        df["post_t2"] = (df["year"] >= 2024 + cfg.lag).astype(int)

    df["treat_x_t1"] = df["treated"] * df["post_t1"]
    df["treat_x_t2"] = df["treated"] * df["post_t2"]

    # Outcome: raw variable or per km²
    if cfg.per_km2:
        df["outcome"] = df[cfg.outcome_var] / df["flaeche_km2"]
    else:
        df["outcome"] = df[cfg.outcome_var]

    # Optional transform (see Cfg.transform)
    if cfg.transform == "asinh":
        df["outcome"] = np.arcsinh(df["outcome"])

    # Event study dummies (all years except reference)
    years = sorted(df["year"].unique())
    for yr in years:
        if yr != cfg.ref:
            df[f"treat_x_{yr}"] = df["treated"] * (df["year"] == yr).astype(int)

    return df.set_index(["Postleitzahl", "year"]), years


# ── Regressions ───────────────────────────────────────────────────────────────

def fit(df: pd.DataFrame, cols: list[str]):
    return PanelOLS(
        df["outcome"], df[cols],
        entity_effects=True, time_effects=True,
    ).fit(cov_type="clustered", cluster_entity=True)

def run_basic(df):    return fit(df, ["treat_x_t1"])
def run_twostep(df):  return fit(df, ["treat_x_t1", "treat_x_t2"])
def run_event(df, years, ref): return fit(df, [f"treat_x_{y}" for y in years if y != ref])


# ── Pre-trend F-test ──────────────────────────────────────────────────────────

def pretrend_ftest(res, pre_cols: list[str]) -> dict:
    """Joint Wald test (χ² and F) on all pre-period event-study coefficients.

    With cluster-robust covariance the conventional F denominator df is
    G − 1 (number of clusters minus one), not the residual df — using
    df_resid would overstate precision (Cameron & Miller 2015)."""
    b = res.params[pre_cols].values
    V = res.cov.loc[pre_cols, pre_cols].values
    k = len(b)
    try:
        W = float(b @ np.linalg.inv(V) @ b)
    except np.linalg.LinAlgError:
        W = float(b @ np.linalg.pinv(V) @ b)
    F    = W / k
    dfd  = int(res.entity_info.total) - 1   # G − 1 clusters (cluster = PLZ)
    p_x = float(1 - stats.chi2.cdf(W, df=k))
    p_f = float(1 - stats.f.cdf(F, dfn=k, dfd=dfd))
    return {"chi2": W, "F": F, "df": k, "dfd": dfd, "p_chi2": p_x, "p_F": p_f}


# ── Linear combination test (tau1 + tau2) ──────────────────────────────────────

def lincom_sum(res, col1: str, col2: str) -> dict:
    """Test H0: coef[col1] + coef[col2] = 0 via the delta method, using the
    two-step model's clustered covariance matrix."""
    b1 = res.params[col1]; b2 = res.params[col2]
    v1 = res.cov.loc[col1, col1]
    v2 = res.cov.loc[col2, col2]
    cov12 = res.cov.loc[col1, col2]
    est = b1 + b2
    se  = float(np.sqrt(v1 + v2 + 2 * cov12))
    df  = int(res.df_resid)
    t   = est / se
    p   = float(2 * (1 - stats.t.cdf(abs(t), df=df)))
    tcrit = stats.t.ppf(0.975, df=df)
    return {"est": float(est), "se": se, "t": float(t), "p": p, "df": df,
            "lo": float(est - tcrit * se), "hi": float(est + tcrit * se)}


# ── Wild cluster bootstrap (Rademacher, manual) ───────────────────────────────

def wild_bootstrap_basic(df_raw: pd.DataFrame, cfg: Cfg,
                          B: int = 999, seed: int = 42) -> dict:
    """
    Restricted wild cluster bootstrap (WCR, Rademacher weights) p-value for
    the basic DiD coefficient (treat_x_t1). Clusters = PLZ.

    Scheme (Cameron, Gelbach & Miller 2008; MacKinnon & Webb 2018):
      1. Two-way within transformation of Y and X (absorbs PLZ + year FE).
      2. Under H0 (beta = 0) the restricted model has no regressors after
         demeaning, so the restricted residuals are simply the demeaned Y.
      3. Each replication: Y* = w_g · Y  with cluster-level Rademacher w_g,
         re-estimate beta and its cluster t-stat on (Y*, X), compare |t*|
         to |t_obs|.

    Note: the cluster SE formula omits small-sample corrections
    (G/(G−1) etc.); this cancels because t_obs and every t* are computed
    with the identical formula. t_obs may therefore differ slightly from
    the PanelOLS t-stat in 01_basic_did.txt (which applies corrections).
    """
    rng = np.random.default_rng(seed)

    data = df_raw.reset_index()[
        ["Postleitzahl", "year", "outcome", "treat_x_t1"]
    ].dropna().copy()

    # Two-way within transformation (iterative, ~20 iterations is sufficient)
    for col in ["outcome", "treat_x_t1"]:
        for _ in range(25):
            data[col] -= data.groupby("Postleitzahl")[col].transform("mean")
            data[col] -= data.groupby("year")[col].transform("mean")
            data[col] += data[col].mean()   # re-centre

    Y = data["outcome"].values
    X = data["treat_x_t1"].values
    cidx = pd.factorize(data["Postleitzahl"])[0]     # cluster index 0..G-1
    G    = int(cidx.max()) + 1

    denom = (X ** 2).sum()
    if denom == 0:
        return {"t_obs": np.nan, "p_boot": np.nan, "B": B}

    def cluster_t(Y_) -> float:
        """OLS slope of Y_ on X with cluster-robust t-stat."""
        b = (X * Y_).sum() / denom
        r = Y_ - b * X
        s = np.bincount(cidx, weights=X * r, minlength=G)
        se = np.sqrt((s ** 2).sum()) / denom
        return b / se if se > 0 else 0.0

    t_obs = cluster_t(Y)

    # Bootstrap distribution under H0: Y* = w_g · (restricted residuals) = w_g · Y
    t_boot = np.empty(B)
    for b in range(B):
        w = rng.choice([-1.0, 1.0], size=G)[cidx]
        t_boot[b] = cluster_t(Y * w)

    p_boot = float((np.abs(t_boot) >= np.abs(t_obs)).mean())
    return {"t_obs": round(float(t_obs), 4), "p_boot": round(p_boot, 4), "B": B}


# ── Format regression table ───────────────────────────────────────────────────

def fmt_table(res, title: str, outcome_label: str = "anzahl_anlagen (raw count)",
              extra_note: str | None = None) -> str:
    lines = [title, "=" * 66,
             f"  N obs:         {int(res.nobs):,}",
             f"  N entities:    {res.entity_info.total:,}",
             f"  R² (within):   {res.rsquared:.4f}",
             f"  Outcome:       {outcome_label}",
             ""]
    lines.append(f"  {'Variable':<24} {'Coef':>8}  {'SE':>8}  {'t':>7}  {'p':>7}  95% CI")
    lines.append("  " + "-" * 72)
    ci = res.conf_int()
    for name in res.params.index:
        c  = res.params[name];  se = res.std_errors[name]
        t  = res.tstats[name];  p  = res.pvalues[name]
        lo = ci["lower"][name]; hi = ci["upper"][name]
        s  = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
        lines.append(
            f"  {name:<24} {c:>8.3f}  {se:>8.3f}  {t:>7.2f}  {p:>7.4f}"
            f"  [{lo:.3f}, {hi:.3f}] {s}")
    lines += ["", "  *** p<0.01  ** p<0.05  * p<0.1",
              "  SE clustered at PLZ level. PLZ + year two-way FE."]
    if extra_note:
        lines += ["", f"  {extra_note}"]
    return "\n".join(lines)


def fmt_pretrend(result: dict, pre_cols: list[str]) -> str:
    lines = [
        "Pre-trend Joint Wald Test",
        "=" * 50,
        f"  H0: all pre-period treat×year coefficients = 0",
        f"  Pre-period dummies tested: {len(pre_cols)}",
        f"  Variables: {', '.join(pre_cols)}",
        "",
        f"  Chi² ({result['df']} df):  {result['chi2']:.3f}   p = {result['p_chi2']:.4f}",
        f"  F    ({result['df']}, {result['dfd']}): {result['F']:.3f}   p = {result['p_F']:.4f}"
        f"   (denominator df = G−1 clusters)",
        "",
        "  Interpretation:",
        "    p > 0.1 → fail to reject parallel trends (desired)",
        "    p < 0.1 → evidence of pre-existing differential trends (concern)",
    ]
    return "\n".join(lines)


def fmt_lincom(result: dict, t1_lbl: str, t2_lbl: str, total_lbl: str,
               outcome_label: str) -> str:
    s = ("***" if result["p"] < 0.01 else "**" if result["p"] < 0.05
         else "*" if result["p"] < 0.1 else "")
    lines = [
        f"Linear Combination Test — {total_lbl}",
        "=" * 66,
        f"  H0: treat_x_t1 + treat_x_t2 = 0",
        f"  Outcome: {outcome_label}",
        f"  Combines: {t1_lbl}  +  {t2_lbl}",
        "",
        f"  Estimate:  {result['est']:.3f}",
        f"  SE:        {result['se']:.3f}",
        f"  t({result['df']}):   {result['t']:.2f}   p = {result['p']:.4f}  {s}",
        f"  95% CI:    [{result['lo']:.3f}, {result['hi']:.3f}]",
        "",
        "  Interpretation: combined treatment effect once both mandate steps",
        "  are active (from the two-step model in 02_twostep_did.txt).",
        "",
        "  *** p<0.01  ** p<0.05  * p<0.1",
        "  SE via delta method on the two-step model's clustered covariance.",
    ]
    return "\n".join(lines)


def fmt_wildboot(result: dict, t1_lbl: str) -> str:
    lines = [
        f"Wild Cluster Bootstrap — Basic DiD coefficient ({t1_lbl})",
        "=" * 60,
        f"  Method:     Restricted wild cluster bootstrap (WCR),",
        f"              Rademacher weights, cluster = PLZ",
        f"  Replications: {result['B']}",
        "",
        f"  Observed t-stat:  {result['t_obs']}",
        f"  Bootstrap p-value (two-sided): {result['p_boot']}",
        "",
        "  Note: standard clustered SE p-value is in 01_basic_did.txt; its",
        "  t-stat differs slightly (small-sample corrections, see docstring).",
        "  Caveat: clustering treats PLZs as independent policy draws, but",
        "  treatment is assigned at the Bundesland level (1 treated state).",
        "  See thesis discussion of inference with few treated clusters.",
    ]
    return "\n".join(lines)


# ── Parallel trends plot ──────────────────────────────────────────────────────

def plot_pt(df: pd.DataFrame, cfg: Cfg, save_path: Path) -> None:
    # df is the already-filtered regression sample (same one fit() uses) --
    # NOT the raw master panel. Re-deriving the filter here previously drifted
    # out of sync with load()'s actual sample (missed the second-ring
    # exclusion and the *_matched control subsets), so the plotted means
    # didn't match the regression sitting right next to them.
    sub = df.reset_index()
    stats_df = sub.groupby(["year", "treated"])["outcome"].mean().reset_index()

    t1 = (cfg.placebo or 2023) + cfg.lag
    t2 = (cfg.placebo + 1 if cfg.placebo else 2024) + cfg.lag
    t1_word = "Fake mandate" if cfg.placebo else "mandate in force"
    t2_word = "Fake extended mandate" if cfg.placebo else "extended mandate"

    ctrl_label = {"SH": "SH Grenze (control)", "NI": "NI Grenze (control)"}.get(
        cfg.ctrl, "SH + NI Grenze (control)")
    op_label  = "private" if cfg.op == "privat" else "commercial (negative control)"
    metric_lbl = ("installed capacity (kW)" if cfg.outcome_var == "netto_kw"
                   else "new solar installations")
    y_label   = (f"Mean {op_label} {metric_lbl} per km² per PLZ"
                 if cfg.per_km2 else
                 f"Mean {op_label} {metric_lbl} per PLZ")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axvspan(t1 - 0.5, t2 - 0.5, color="#fee8c8", alpha=0.6,
               label=f"{t1}+: {t1_word}")
    ax.axvspan(t2 - 0.5, cfg.end + 0.5, color="#fdbb84", alpha=0.5,
               label=f"{t2}+: {t2_word}")
    ax.axvline(t1 - 0.5, color="grey", linewidth=0.8, linestyle=":")

    for val, label, color, fmt in [
        (1, "Hamburg Grenze (treated)", "#d73027", "o-"),
        (0, ctrl_label,                 "#2166ac", "s--"),
    ]:
        g = stats_df[stats_df["treated"] == val].sort_values("year")
        ax.plot(g["year"], g["outcome"], fmt, color=color,
                label=label, markersize=5, linewidth=1.8)

    years_avail = sorted(sub["year"].unique())
    ax.set_xticks(years_avail)
    ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.set_xlabel("Year")
    ax.set_ylabel(y_label)
    tag = f"  |  {cfg.ctrl} control" if cfg.ctrl else ""
    tag += "  |  1-yr lag" if cfg.lag else ""
    tag += "  |  placebo 2021" if cfg.placebo else ""
    tag += "  |  no 2025" if cfg.end == 2024 else ""
    ax.set_title(f"Parallel Trends — {op_label.title()} Solar\nStart: {cfg.start}{tag}",
                 fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(axis="y", linewidth=0.4, alpha=0.6)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


# ── Event study plot ──────────────────────────────────────────────────────────

def plot_es(res, years: list[int], cfg: Cfg, save_path: Path) -> None:
    event_years = [y for y in years if y != cfg.ref]
    coefs = {int(n.split("_")[-1]): res.params[n] for n in res.params.index}
    lo_d  = {int(n.split("_")[-1]): res.conf_int()["lower"][n] for n in res.params.index}
    hi_d  = {int(n.split("_")[-1]): res.conf_int()["upper"][n] for n in res.params.index}

    all_y = sorted(event_years + [cfg.ref])
    c   = [coefs.get(y, 0.0) for y in all_y]
    elo = [c[i] - lo_d.get(all_y[i], c[i]) for i in range(len(all_y))]
    ehi = [hi_d.get(all_y[i], c[i]) - c[i] for i in range(len(all_y))]

    t1 = (cfg.placebo or 2023) + cfg.lag
    t2 = (cfg.placebo + 1 if cfg.placebo else 2024) + cfg.lag
    t1_word = "Fake mandate" if cfg.placebo else "mandate in force"
    t2_word = "Fake extended mandate" if cfg.placebo else "extended mandate"

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axvspan(t1 - 0.5, t2 - 0.5, color="#fee8c8", alpha=0.6,
               label=f"{t1}+: {t1_word}")
    ax.axvspan(t2 - 0.5, max(all_y) + 0.5, color="#fdbb84", alpha=0.5,
               label=f"{t2}+: {t2_word}")
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.axvline(cfg.ref + 0.5, color="grey", linewidth=0.8, linestyle=":")

    for mask, color in [
        ([y <= cfg.ref for y in all_y], "#2166ac"),
        ([y >  cfg.ref for y in all_y], "#d73027"),
    ]:
        ys  = [all_y[i] for i in range(len(all_y)) if mask[i]]
        ax.errorbar(ys,
                    [c[i]   for i in range(len(all_y)) if mask[i]],
                    yerr=[[elo[i] for i in range(len(all_y)) if mask[i]],
                          [ehi[i] for i in range(len(all_y)) if mask[i]]],
                    fmt="o-", color=color, capsize=4, markersize=5, linewidth=1.5)

    ax.set_xticks(all_y); ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.set_xlabel("Year")
    ax.set_ylabel(f"Coeff. on Treated × Year  (rel. to {cfg.ref})")
    ax.set_title(f"Event Study  |  Start {cfg.start}", fontsize=11)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(axis="y", linewidth=0.4, alpha=0.6)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


# ── Run one spec ──────────────────────────────────────────────────────────────

def run_spec(spec_name: str, subfolder: str, cfg: Cfg) -> None:
    out = ROOT_OUT / spec_name / subfolder
    for sub in ["Data", "Figures", "Tables"]:
        (out / sub).mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*66}")
    print(f"  {spec_name} / {subfolder}")
    print(f"{'='*66}")

    df, years = load(cfg)

    n_trt  = df.reset_index().drop_duplicates("Postleitzahl")["treated"].sum()
    n_ctrl = df.reset_index().drop_duplicates("Postleitzahl")["treated"].eq(0).sum()
    print(f"  {n_trt} treated PLZs, {n_ctrl} control PLZs  |  {len(df):,} obs  |"
          f"  years {min(years)}–{max(years)}  |  op={cfg.op}"
          + (f"  ctrl={cfg.ctrl}" if cfg.ctrl else "")
          + (f"  placebo={cfg.placebo}" if cfg.placebo else ""))

    # Panel snapshot
    df.reset_index().to_csv(
        out / "Data" / f"panel_{cfg.start}_{subfolder}.csv", index=False)

    # Regressions
    res1 = run_basic(df)
    res2 = run_twostep(df)
    res3 = run_event(df, years, cfg.ref)

    # Identify pre-period cols for F-test
    pre_cols = [f"treat_x_{y}" for y in years if y < (cfg.placebo or 2023 + cfg.lag) and y != cfg.ref]

    # Pre-trend F-test
    ft = pretrend_ftest(res3, pre_cols) if pre_cols else None

    # Wild bootstrap on basic DiD
    wb = wild_bootstrap_basic(df, cfg)

    # Linear combination: total effect once both post-onset dummies are active
    lc = lincom_sum(res2, "treat_x_t1", "treat_x_t2")

    # Determine onset labels — neutral time-based wording only. T1 and T2 are
    # NOT separately identified (registration lag makes the delayed T1 effect
    # coincide with T2 onset), so labels must never imply a Neubau-specific vs.
    # Dachsanierung-specific effect. See CLAUDE.md / LEVELS OF ANALYSIS.
    t1_yr = (cfg.placebo or 2023) + cfg.lag
    t2_yr = (cfg.placebo + 1 if cfg.placebo else 2024) + cfg.lag
    fake  = "Fake " if cfg.placebo else ""
    t1_lbl    = f"{fake}Post-{t1_yr} effect"
    t2_lbl    = f"{fake}Additional post-{t2_yr} effect"
    total_lbl = f"{fake}Total post-{t2_yr} effect (Post-{t1_yr} + additional)"

    var_lbl = {"anzahl_anlagen": "anzahl_anlagen", "netto_kw": "netto_kw (kW)"}[cfg.outcome_var]
    outcome_lbl = f"{var_lbl} / flaeche_km2 (per km²)" if cfg.per_km2 else f"{var_lbl} (raw)"
    if cfg.transform == "asinh":
        outcome_lbl = f"asinh({outcome_lbl})"

    header = (
        f"DiD Analysis — {cfg.op} solar — {spec_name} / {subfolder}\n"
        f"Treatment: Hamburg Grenze  |  Control: "
        + (f"{cfg.ctrl} Grenze only" if cfg.ctrl else "SH + NI Grenze")
        + f"\nOutcome: {outcome_lbl}  |  Years: {cfg.start}–{cfg.end}"
        + (f"\nFake treatment onset: {cfg.placebo}/{cfg.placebo+1}" if cfg.placebo else "")
        + f"\nRef year (event study): {cfg.ref}\n\n"
    )

    twostep_note = (
        "Note: T1 (new construction, 2023) and T2 (roof renovation, 2024) are "
        "not separately identified — registration lag causes the delayed T1 "
        "effect to overlap the T2 onset. The second coefficient is a post-2024 "
        "increment, not a renovation-specific effect."
    )
    tables = {
        "01_basic_did.txt":   fmt_table(res1, f"Basic DiD  —  treated × {t1_lbl}", outcome_lbl),
        "02_twostep_did.txt": fmt_table(res2, f"Two-step DiD  —  {t1_lbl}  +  {t2_lbl}", outcome_lbl,
                                          extra_note=twostep_note),
        "02b_twostep_total_effect.txt": fmt_lincom(lc, t1_lbl, t2_lbl, total_lbl, outcome_lbl),
        "03_event_study.txt": fmt_table(res3,  "Event Study  —  treated × year dummies", outcome_lbl),
        "04_wild_bootstrap.txt": fmt_wildboot(wb, t1_lbl),
    }
    if ft:
        tables["00_pretrend_ftest.txt"] = fmt_pretrend(ft, pre_cols)

    for fname, content in tables.items():
        (out / "Tables" / fname).write_text(header + content)

    # Console summary
    c1 = res1.params["treat_x_t1"]; p1 = res1.pvalues["treat_x_t1"]
    print(f"  Basic DiD:    treat_x_t1 = {c1:+.2f}  p={p1:.4f}")
    print(f"  Total (t1+t2): {lc['est']:+.2f}  p={lc['p']:.4f}")
    if ft:
        print(f"  Pre-trend F:  F={ft['F']:.3f}  p={ft['p_F']:.4f}"
              + ("  ✓" if ft["p_F"] > 0.1 else "  ✗ concern"))
    print(f"  Wild boot p:  {wb['p_boot']}")

    # Figures
    plot_pt(df, cfg, out / "Figures" / "parallel_trends.png")
    plot_es(res3, years, cfg, out / "Figures" / "event_study.png")
    print(f"  → {out / 'Figures'}")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    for spec_name, subfolder, cfg in SPECS:
        run_spec(spec_name, subfolder, cfg)
    print(f"\nDone. {len(SPECS)} specs  →  {ROOT_OUT}")
