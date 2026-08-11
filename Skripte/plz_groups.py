#!/usr/bin/env python3
"""
plz_groups.py — Shared PLZ group definitions for the Hamburg Solardachpflicht
border comparison (Panel D / D_did_panel_yearly.csv).

SINGLE SOURCE OF TRUTH for all border-comparison group membership:
  - FIRST_RING_*  : the main DiD sample (31 treated vs. 24 control)
  - SECOND_RING_* : robustness-only outer PLZs
  - TREATMENT / SH_CONTROL / NI_CONTROL : full lists (first + second ring),
    used by build_did_panel.py to construct Panel D
  - EXCLUDED_BEIDERSEITS : PLZs straddling the Hamburg boundary, in no group

SECOND_RING PLZs are excluded from the main DiD specification (did_analysis.py
SPECS, other than a dedicated second-ring robustness spec) and from every
border-comparison descriptive figure (Descriptive/D1–D5, D7). The main spec and
all descriptive border figures use the identical first-ring sample: 31 Hamburg
border PLZs vs. 24 control border PLZs (17 SH + 7 NI).
"""

# ── First ring (main DiD sample) ─────────────────────────────────────────────

FIRST_RING_HH = [
    "22559", "22589", "22587", "22549", "22547", "22523", "22457", "22455",
    "22415", "22417", "22419", "22399", "22395", "22397", "22359", "22149",
    "22143", "22117", "22115", "21031", "21029", "21037", "21109", "21129",
    "21147", "21149", "21075", "21077", "21079", "22045", "22043",
]

# 21509 (Glinde) excluded from the FIRST ring only: touches the Hamburg
# border at a single point only, not a genuine shared edge like the other 17
# SH first-ring PLZs. It IS a genuine second-ring PLZ, though -- verified
# 2026-08-07 against the PLZ boundary files: Glinde shares a real edge with
# 21465 (6.5 km) and 22885 (3.7 km), both first-ring SH PLZs -- the same
# adjacency-to-first-ring criterion every other SECOND_RING_* member meets.
# See SECOND_RING_SH below.
FIRST_RING_SH = [
    "22880", "25469", "25462", "25474", "25421", "25482", "22869", "22848",
    "22850", "22851", "22889", "22885", "22941", "22926", "22949", "21465",
    "21502",
]

FIRST_RING_NI = [
    "21217", "21218", "21224", "21435", "21629", "21635", "21423",
]

# ── Second ring (robustness only) ────────────────────────────────────────────

SECOND_RING_HH = {"21073", "21033", "21035", "22119", "22147", "22453"}
# 21509 (Glinde) added 2026-08-07: excluded from FIRST_RING_SH (point contact
# with Hamburg only, see comment there) but borders first-ring SH PLZs 21465
# and 22885 by a real shared edge, meeting the same criterion as the other
# four SECOND_RING_SH members.
SECOND_RING_SH = {"25488", "23863", "22846", "22844", "21509"}
SECOND_RING_NI = {"21614"}

SECOND_RING = SECOND_RING_HH | SECOND_RING_SH | SECOND_RING_NI

# ── Full group lists (first + second ring) — Panel D construction ────────────

TREATMENT  = FIRST_RING_HH + sorted(SECOND_RING_HH)
SH_CONTROL = FIRST_RING_SH + sorted(SECOND_RING_SH)
NI_CONTROL = FIRST_RING_NI + sorted(SECOND_RING_NI)

# ── Special cases ────────────────────────────────────────────────────────────

# Straddle the Hamburg boundary (Beiderseits) — excluded from all groups.
EXCLUDED_BEIDERSEITS = {"21039", "22113", "22145"}

# NOTE on 21509 (Glinde): excluded from FIRST_RING_SH only (point contact with
# Hamburg, not a shared edge) -- reclassified into SECOND_RING_SH 2026-08-07
# once it was checked against the second-ring criterion (borders a first-ring
# PLZ) rather than the first-ring one. No longer excluded from every group.

# NOTE on 22457 / 21465: an earlier version of this file flagged these as
# "split" PLZs spanning a border, with a dedicated no_split robustness spec.
# Verified 2026-07-30 against the PLZ boundary files (Daten/postleitzahlen_json/):
# 22457 does not appear in the Schleswig-Holstein file at all (wholly within
# Hamburg -- the old "spans Hamburg/Pinneberg" claim was wrong), and 21465
# spans two Kreise (Stormarn / Herzogtum Lauenburg) that are BOTH inside
# Schleswig-Holstein -- never touches Hamburg. Neither PLZ crosses the actual
# treatment boundary, so neither is relevant to identification. Removed.


# ── Consistency checks (run on import; cheap) ────────────────────────────────

assert len(FIRST_RING_HH) == 31 and len(FIRST_RING_SH) == 17 and len(FIRST_RING_NI) == 7
assert len(SECOND_RING_SH) == 5 and len(SECOND_RING_HH) == 6 and len(SECOND_RING_NI) == 1
assert not (set(FIRST_RING_HH + FIRST_RING_SH + FIRST_RING_NI) & SECOND_RING)
assert not (set(TREATMENT + SH_CONTROL + NI_CONTROL) & EXCLUDED_BEIDERSEITS)
