#!/usr/bin/env python3
"""
06_border_groups_map.py — Zoomed map: Hamburg treatment vs. control PLZs.
(Renamed from D7_border_plz_map.py 2026-08-09 to narrative order; content
unchanged.)

Categories mirror the DiD panel exactly (Auswertung/Panels/D_did_panel_yearly.csv
and the shared Skripte/plz_groups.py FIRST_RING_* / SECOND_RING definitions,
also used by did_analysis.py and every other border-comparison descriptive
script):
  Treated (main spec, n=31)   | Treated (2nd ring, robustness only, n=6)
  Control SH (main spec, n=17)| Control SH (2nd ring, robustness only, n=5)
  Control NI (main spec, n=7) | Control NI (2nd ring, robustness only, n=1)

3 PLZ straddling the Hamburg/SH administrative border (21039, 22113, 22145)
are not part of the DiD panel at all and are shown as excluded background.
21509 (Glinde) touches the Hamburg border at a single point only (not a
shared edge), so it is excluded from the first ring — but it borders
first-ring SH PLZs 21465 and 22885 by a real shared edge, so it qualifies
for the second ring (plz_groups.py SECOND_RING_SH, added 2026-08-07) and
renders as Control – SH (2nd ring) here.

Output: Auswertung/Descriptive Results/03_Border_DiD_Comparison/06_border_groups_map.png
"""

import pathlib, warnings, sys
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from shapely.ops import unary_union
from shapely.geometry import box as _box

warnings.filterwarnings("ignore")

BASE = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE / "Skripte"))
from plz_groups import (
    FIRST_RING_HH, FIRST_RING_SH, FIRST_RING_NI,
    SECOND_RING_HH, SECOND_RING_SH, SECOND_RING_NI,
)

GEO_HH     = BASE / "Daten/postleitzahlen_json/de_hh_up_postleitzahlen_EPSG_4326.json"
GEO_SH     = BASE / "Daten/postleitzahlen_json/schleswigholstein.geojson"
GEO_NI     = BASE / "Daten/postleitzahlen_json/niedersachsen.geojson"
# Official Kreis-level admin boundaries (AGS state prefix) — same source D8 uses
# to dissolve Bundesland polygons. Used here only for the true Hamburg state
# outline: PLZ polygons split some PLZ across the HH/SH and HH/NI border, so a
# union of postal-code geometry (the old approach) does not trace the actual
# administrative border. Already in EPSG:25832, no reprojection needed.
GEO_KREISE = BASE / "Daten/postleitzahlen_json/K-2024-AI-S-03--AI2001--2026-06-02.geojson"
OUT     = BASE / "Auswertung/Descriptive Results/03_Border_DiD_Comparison/06_border_groups_map.png"
OUT.parent.mkdir(parents=True, exist_ok=True)
CRS = "EPSG:25832"

# ── Classification — first-ring (main spec) sets and second-ring subsets,
# both imported from plz_groups.py (single source of truth, not duplicated
# here) ────────────────────────────────────────────────────────────────────
TREAT_MAIN = set(FIRST_RING_HH)
TREAT_2ND  = SECOND_RING_HH
SH_MAIN    = set(FIRST_RING_SH)
SH_2ND     = SECOND_RING_SH
NI_MAIN    = set(FIRST_RING_NI)
NI_2ND     = SECOND_RING_NI
EXCLUDED   = {"21039","22113","22145"}   # split PLZ, not in D_did_panel_yearly.csv

ALL_CLASSIFIED = (TREAT_MAIN | TREAT_2ND | SH_MAIN | SH_2ND |
                  NI_MAIN | NI_2ND | EXCLUDED)

# PLZs that appear in HH geojson but are primarily SH/NI territory (tiny slivers)
HH_SLIVERS = {"22869", "22885", "21217"}

# ── Load geodata ───────────────────────────────────────────────────────────────
print("Loading geodata …")

gdf_hh = gpd.read_file(GEO_HH)
gdf_hh["plz"] = gdf_hh["plz"].astype(str).str.zfill(5)
gdf_hh = gdf_hh[["plz","geometry"]].dissolve(by="plz", as_index=False).to_crs(CRS)

gdf_sh_raw = gpd.read_file(GEO_SH)
gdf_sh_raw["plz"] = gdf_sh_raw["plz_code"].astype(str).str.zfill(5)
gdf_sh_all = gdf_sh_raw[["plz","geometry"]].dissolve(by="plz", as_index=False).to_crs(CRS)

gdf_ni_raw = gpd.read_file(GEO_NI)
gdf_ni_raw["plz"] = gdf_ni_raw["plz_code"].astype(str).str.zfill(5)
gdf_ni_all = gdf_ni_raw[["plz","geometry"]].dissolve(by="plz", as_index=False).to_crs(CRS)


def _get_geom(plz, *gdfs):
    for gdf in gdfs:
        r = gdf[gdf["plz"] == plz]
        if len(r):
            return r.geometry.iloc[0]
    return None

# ── Build rows ─────────────────────────────────────────────────────────────────
rows = []

hh_plz_set = set(gdf_hh["plz"]) - HH_SLIVERS - {"27499"}
for plz in hh_plz_set:
    geom = _get_geom(plz, gdf_hh)
    if geom is None:
        continue
    if plz in EXCLUDED:
        sh_part = _get_geom(plz, gdf_sh_all)
        if sh_part:
            geom = unary_union([geom, sh_part])
        cat = "Excluded"
    elif plz in TREAT_MAIN:
        cat = "Treated (main)"
    elif plz in TREAT_2ND:
        cat = "Treated (2nd ring)"
    else:
        cat = "HH interior"
    rows.append({"plz": plz, "cat": cat, "geometry": geom})

SH_LK = {"01053","01056","01060","01062"}
gdf_sh4 = gdf_sh_raw[gdf_sh_raw["krs_code"].isin(SH_LK)][["plz","geometry"]].dissolve(by="plz", as_index=False).to_crs(CRS)
sh_bg_plz = set(gdf_sh4["plz"]) - ALL_CLASSIFIED

for plz in (SH_MAIN | SH_2ND | sh_bg_plz):
    if plz in EXCLUDED:
        continue
    geom = _get_geom(plz, gdf_sh_all)
    if geom is None:
        continue
    if plz in SH_MAIN:
        cat = "Control – SH (main)"
    elif plz in SH_2ND:
        cat = "Control – SH (2nd ring)"
    else:
        cat = "SH background"
    rows.append({"plz": plz, "cat": cat, "geometry": geom})

NI_LK = {"03353","03359"}
gdf_ni2 = gdf_ni_raw[gdf_ni_raw["krs_code"].isin(NI_LK)][["plz","geometry"]].dissolve(by="plz", as_index=False).to_crs(CRS)
ni_bg_plz = set(gdf_ni2["plz"]) - ALL_CLASSIFIED

for plz in (NI_MAIN | NI_2ND | ni_bg_plz):
    geom = _get_geom(plz, gdf_ni_all)
    if geom is None:
        continue
    if plz in NI_MAIN:
        cat = "Control – NI (main)"
    elif plz in NI_2ND:
        cat = "Control – NI (2nd ring)"
    else:
        cat = "NI background"
    rows.append({"plz": plz, "cat": cat, "geometry": geom})

gdf_map = gpd.GeoDataFrame(rows, crs=CRS).drop_duplicates(subset="plz")
print(f"Total PLZs in map: {len(gdf_map)}")
for cat, n in gdf_map["cat"].value_counts().items():
    print(f"  {cat}: {n}")

# ── Clip to display area ───────────────────────────────────────────────────────
focus_cats = {"Treated (main)","Treated (2nd ring)","Control – SH (main)",
              "Control – SH (2nd ring)","Control – NI (main)","Control – NI (2nd ring)",
              "Excluded","HH interior"}
focus = gdf_map[gdf_map["cat"].isin(focus_cats)]
cx, cy = focus.geometry.centroid.x, focus.geometry.centroid.y
x_min, x_max = cx.min() - 15_000, cx.max() + 15_000
y_min, y_max = cy.min() - 15_000, cy.max() + 17_000
clip_box = gpd.GeoDataFrame(geometry=[_box(x_min, y_min, x_max, y_max)], crs=CRS)
gdf_plot = gpd.clip(gdf_map, clip_box).reset_index(drop=True)

# ── Colours (consistent with C_HH / C_CTRL used across the Descriptive series) ─
COLORS = {
    "Treated (main)":          "#D94F3D",
    "Treated (2nd ring)":      "#F0B8AC",
    "Control – SH (main)":     "#2166AC",
    "Control – SH (2nd ring)": "#AFC9E3",
    "Control – NI (main)":     "#4A7C3F",
    "Control – NI (2nd ring)": "#BFDAB5",
    "HH interior":             "#C8C8C8",
    "Excluded":                "#B8A0A0",
    "SH background":           "#DDE8DD",
    "NI background":           "#E8DED0",
}
CAT_ORDER = list(COLORS)

# ── Plot ────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 10))
ax.set_facecolor("#D6E8F4")

for cat in reversed(CAT_ORDER):
    sub = gdf_plot[gdf_plot["cat"] == cat]
    if sub.empty:
        continue
    sub.plot(ax=ax, color=COLORS[cat], edgecolor="#555555", linewidth=0.3, zorder=2)

label_cats = {"Treated (main)","Treated (2nd ring)","Control – SH (main)",
              "Control – SH (2nd ring)","Control – NI (main)","Control – NI (2nd ring)"}
for _, row in gdf_plot[gdf_plot["cat"].isin(label_cats)].iterrows():
    c = row.geometry.centroid
    ax.text(c.x, c.y, row["plz"], fontsize=4.5, ha="center", va="center",
            color="#111111", fontweight="bold", zorder=5)

# Hamburg city outline — true administrative border, dissolved from the
# Kreis-level file via the official AGS state prefix "02" (Hamburg). PLZ
# geometry is NOT used here: several PLZ straddle the HH/SH and HH/NI border
# (21039, 22113, 22145) and some HH-file postal codes are mostly SH/NI
# territory (HH_SLIVERS), so unioning PLZ polygons traces postal-code edges,
# not the real state line.
gdf_kreise = gpd.read_file(GEO_KREISE)
gdf_kreise["bl_code"] = gdf_kreise["schluessel"].astype(str).apply(
    lambda s: s.zfill(5)[:2] if len(s) > 2 else s.zfill(2)
)
hh_admin = gdf_kreise[gdf_kreise["bl_code"] == "02"]
hh_outline = gpd.GeoDataFrame(geometry=[unary_union(hh_admin.geometry)], crs=gdf_kreise.crs).to_crs(CRS)
hh_outline.boundary.plot(ax=ax, color="white",   linewidth=4.0, zorder=6)
hh_outline.boundary.plot(ax=ax, color="#111111", linewidth=1.8, zorder=7)

ax.set_xlim(x_min, x_max)
ax.set_ylim(y_min, y_max)
ax.set_axis_off()

# ── Legend ──────────────────────────────────────────────────────────────────────
LEGEND_LABELS = {
    "Treated (main)":          f"Treated — Hamburg ({len(TREAT_MAIN)})",
    "Control – SH (main)":     f"Control — Schleswig-Holstein ({len(SH_MAIN)})",
    "Control – NI (main)":     f"Control — Niedersachsen ({len(NI_MAIN)})",
    "Treated (2nd ring)":      f"Treated, 2nd ring (robustness only, {len(TREAT_2ND)})",
    "Control – SH (2nd ring)": f"Control SH, 2nd ring (robustness only, {len(SH_2ND)})",
    "Control – NI (2nd ring)": f"Control NI, 2nd ring (robustness only, {len(NI_2ND)})",
    "HH interior":             "Hamburg interior (not in panel)",
    "Excluded":                f"Split PLZ, excluded ({len(EXCLUDED)})",
    "SH background":           "SH background",
    "NI background":           "NI background",
}
handles = [
    mpatches.Patch(facecolor=COLORS[c], edgecolor="#555555", linewidth=0.5,
                   label=LEGEND_LABELS[c])
    for c in CAT_ORDER
]
ax.legend(handles=handles, loc="upper left", fontsize=8.5,
          framealpha=0.9, edgecolor="#AAAAAA")

# ── Title ────────────────────────────────────────────────────────────────────────
n_main  = len(TREAT_MAIN) + len(SH_MAIN) + len(NI_MAIN)
n_total = n_main + len(TREAT_2ND) + len(SH_2ND) + len(NI_2ND)
fig.suptitle(
    "DiD Treatment and Control PLZs — Hamburg vs. Schleswig-Holstein / Niedersachsen\n"
    f"Main spec: {n_main} PLZ  |  Incl. 2nd-ring robustness: {n_total} PLZ",
    fontsize=13, fontweight="bold", y=0.98,
)

fig.subplots_adjust(top=0.93, bottom=0.02, left=0.02, right=0.98)
fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"\nSaved → {OUT}")
