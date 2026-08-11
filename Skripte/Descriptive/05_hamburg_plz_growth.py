#!/usr/bin/env python3
"""
05_hamburg_plz_growth.py — Hamburg PLZ choropleth: growth in solar
installations, 2019–22 baseline vs. 2023–25 (post-mandate). (Renamed from
D13_hamburg_plz_growth_heatmap.py 2026-08-09 to narrative order.)

Private operators (natürliche Person) only, full Hamburg (all PLZs), built
fresh from A_deutschland_plz_monat_operatortyp.csv — NOT from the retired
B_plz_monat_operatortyp.csv panel the legacy versions of this figure used.
Restricted to operator_type == "privat" 2026-08-09, consistent with every
other thesis-facing figure and with the causal analysis (previously included
all operator types).

Metric: absolute growth in installs/year (annualized post-period mean minus
annualized pre-period mean), not % growth. Changed 2026-08-09 (user: one map,
count growth for all PLZs, not %) after an earlier %-based version needed a
minimum-sample threshold that blanked out ~40 low-volume inner-city PLZs
gray, and a since-rejected two-metric/hatching fallback attempt. Absolute
counts don't have the divide-by-near-zero instability % has, so no threshold
or exclusion is needed — every PLZ gets a real value.

This is a whole-Hamburg map (not restricted to the DiD border PLZs) and
carries no Landkreis breakdown or labeling anywhere — geometry comes from
the same Hamburg PLZ geojson D7 uses, Bundesland-level filter only.

Output: Auswertung/Descriptive Results/02_Hamburg/05_hamburg_plz_growth.png
"""

import pathlib, warnings
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

warnings.filterwarnings("ignore")

BASE = pathlib.Path(__file__).parent.parent.parent
SRC_A = BASE / "Auswertung" / "Panels" / "A_deutschland_plz_monat_operatortyp.csv"
GEO_HH = BASE / "Daten/postleitzahlen_json/de_hh_up_postleitzahlen_EPSG_4326.json"
OUT = BASE / "Auswertung" / "Descriptive Results" / "02_Hamburg" / "05_hamburg_plz_growth.png"
OUT.parent.mkdir(parents=True, exist_ok=True)
CRS = "EPSG:25832"

PRE_YEARS, POST_YEARS = (2019, 2022), (2023, 2025)
# Same slivers D7 excludes from the Hamburg PLZ geojson (PLZ that appear in
# the HH file but are primarily SH/NI territory).
HH_SLIVERS = {"22869", "22885", "21217"}

# ── Load and aggregate Panel A, Hamburg, private operators only ──────────────
df = pd.read_csv(SRC_A, usecols=["Postleitzahl", "Bundesland", "operator_type", "jahr_monat", "anzahl_anlagen"])
df = df[(df["Bundesland"] == "Hamburg") & (df["operator_type"] == "privat")].copy()
df["plz"] = df["Postleitzahl"].astype(str).str.zfill(5)
df["year"] = df["jahr_monat"].str[:4].astype(int)

pre_total = df[df["year"].between(*PRE_YEARS)].groupby("plz")["anzahl_anlagen"].sum()
post_total = df[df["year"].between(*POST_YEARS)].groupby("plz")["anzahl_anlagen"].sum()
pre = pre_total / (PRE_YEARS[1] - PRE_YEARS[0] + 1)
post = post_total / (POST_YEARS[1] - POST_YEARS[0] + 1)

growth = pd.DataFrame({"pre": pre, "post": post}).fillna(0.0)
growth["abs_growth"] = growth["post"] - growth["pre"]

print(f"Hamburg PLZs: {len(growth)}")
print(growth["abs_growth"].describe())

# ── Geometry ───────────────────────────────────────────────────────────────────
gdf = gpd.read_file(GEO_HH)
gdf["plz"] = gdf["plz"].astype(str).str.zfill(5)
gdf = gdf[["plz", "geometry"]].dissolve(by="plz", as_index=False).to_crs(CRS)
gdf = gdf[~gdf["plz"].isin(HH_SLIVERS | {"27499"})]

gdf_map = gdf.merge(growth, on="plz", how="left")

# ── Colour scale ───────────────────────────────────────────────────────────────
vmax = np.nanpercentile(gdf_map["abs_growth"], 98)  # clip extreme outliers for readability
cmap = plt.get_cmap("YlOrRd")
norm = mcolors.Normalize(vmin=0, vmax=vmax)

# ── Plot ────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 10))
ax.set_facecolor("#D6E8F4")

gdf_map.plot(ax=ax, column="abs_growth", cmap=cmap, norm=norm,
             edgecolor="#555555", linewidth=0.3, zorder=2)

ax.set_axis_off()

sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.02)
cbar.set_label(f"Absolute growth, installs/year added ({PRE_YEARS[0]}–{PRE_YEARS[1]} → {POST_YEARS[0]}–{POST_YEARS[1]})",
               fontsize=9)

fig.suptitle(
    "Hamburg — Growth in Solar Installations by PLZ, Pre- vs. Post-Mandate\n"
    f"Annualized {PRE_YEARS[0]}–{PRE_YEARS[1]} baseline vs. {POST_YEARS[0]}–{POST_YEARS[1]}, private operators only",
    fontsize=12, fontweight="bold", y=0.98,
)
fig.text(0.5, 0.02,
         "Source: MaStR (Bundesnetzagentur), private (natürliche Person) operators only, all Hamburg PLZs. "
         "Growth = annualized post-period mean "
         "minus annualized pre-period mean, both averaged over unequal-length windows "
         f"({PRE_YEARS[1]-PRE_YEARS[0]+1} vs. {POST_YEARS[1]-POST_YEARS[0]+1} years).",
         ha="center", fontsize=7.5, color="#777777", style="italic")
fig.text(0.5, -0.005,
         f"Color scale clipped at the 98th percentile ({vmax:.0f} installs/year) to limit outlier distortion.",
         ha="center", fontsize=7.5, color="#777777", style="italic")

fig.subplots_adjust(top=0.90, bottom=0.05, left=0.02, right=0.98)
fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"\nSaved → {OUT}")
