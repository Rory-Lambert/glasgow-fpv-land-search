# Shortlist: flyable sites for the club

*Council-owned vacant/derelict land in the Glasgow area, football-pitch sized,
scored for site quality and member travel — and **hard-filtered to drop anything
with a home within 50 m** of the site, which for FPV is the make-or-break test.
Browse it all interactively in the **[Site Explorer](https://rory-lambert.github.io/glasgow-fpv-land-search/explorer.html)**
(tick "Clear of homes"); full data in [outputs/all_scored_sites.csv](outputs/all_scored_sites.csv).*

## The headline

Screening real building footprints (OpenStreetMap) against each site changed the
picture completely. **Most council sites in the Glasgow area have housing within
50 m** — including six of the seven sites we first shortlisted. Once those are
removed, a genuinely *flyable* leaderboard emerges: **138 sites** clear the
filters, and the best of them are open ground with **no home within ~175 m**.

**Top recommendation: the former Rugby Pitch off Cumbernauld Road (Glasgow).**
It's open, pitch-shaped recreational land with *no home within 175 m*, ~18 min
average drive for the current members (26 min closer than the castle), and it
tops the ranking. Second is **Glenconner Park** — former recreation land the
council itself has flagged "uneconomic to develop", which makes it an easy
Community Asset Transfer ask.

> **The 50 m figure is your member's; confirm it with BMFA.** The standard Open-
> category A3 distance from residential areas is **150 m**. If 150 m applies, the
> list shrinks further toward the "no home within 175 m" sites below — change
> `HOUSING_GAP_M` in `analysis/find_sites.py` and re-run to see it.

## How a site earns its place

1. **Council-owned** (so we can make a Community Asset Transfer case).
2. **~0.4–3.0 ha** (football pitch is ~0.7 ha).
3. **Clear of airport flight-restriction zones** (Glasgow & Cumbernauld).
4. **No home within 50 m** of the (approximate) edge — the hard filter.
5. Then scored on **openness, low development pressure, former use, size, and
   member proximity** (higher = better).

## The leaderboard — flyable, best first

| # | Score | Site | Council | Size | Former use | Nearest home | Avg member |
|---|---|---|---|---|---|---|---|
| 1 | +12 | **Rugby Pitch, Cumbernauld Rd** ⭐ | Glasgow | 1.38 ha | Recreation | none <175 m | 14.1 km |
| 2 | +12 | Wellfield St / Croftbank St | Glasgow | 0.95 ha | ex-housing | none <175 m | 13.3 km |
| 3 | +12 | Craigendmuir St | Glasgow | 0.87 ha | ex-housing | none <175 m | 13.3 km |
| 4 | +12 | West of 1159 Royston Rd (by M80) | Glasgow | 1.39 ha | ex-housing | 167 m | 13.5 km |
| 5 | +11 | **Glenconner Park**, Charles St ⭐ | Glasgow | 0.50 ha | Recreation | 105 m | 13.1 km |
| 6 | +11 | 4-10 Stonyhurst St | Glasgow | 1.40 ha | ex-housing | none <175 m | 13.4 km |
| 7 | +11 | Greenside Cres | Glasgow | 0.78 ha | ex-housing | none <175 m | 13.6 km |
| 8 | +11 | Opp 112-132 Strathmore Rd | Glasgow | 1.38 ha | — | 124 m | 14.0 km |

The two **former recreation grounds** (⭐) are the strongest for a drone course —
open, flat, already recreational. The rest are **cleared housing plots that are
now genuinely isolated** (no neighbouring homes within the gap): fine on the
separation test and openness, though a site visit matters more to confirm surface
and access.

### Still worth keeping: Northern Site, Alexandria
The one survivor from the original shortlist — **1.98 ha, nearest home 169 m,
clear** — but ~31 km from the members, so it ranks lower on travel. Kept as the
"room to grow" option if distance isn't a dealbreaker.

## What the filter removed

- **103+ sites with a home within 50 m** — including our old top picks (Blaes
  Pitch 11 m, Glenmavis 8 m, Wheatholme 1 m, Gardenside/Auchinleck ~0 m). Full
  list in [outputs/excluded_by_housing.csv](outputs/excluded_by_housing.csv).
- **Airport FRZ sites** (e.g. the Paisley/Ferguslie sites, ~2 km from Glasgow
  Airport) — excluded from the ranking entirely.

## Caveats

- **Site extent is approximate.** The survey gives a centroid + area, not a
  boundary, so the housing gap is measured from a square of the recorded area —
  a screen, not a survey. Verify against a site plan / on the ground.
- **Confirm the separation distance** with BMFA/CAA (50 m vs 150 m).
- **18 of 289 sites are not yet housing-screened** (an Overpass rate-limit cut
  the sweep short); they're flagged "not screened", never silently included.
  Re-run `python3 analysis/housing.py --build` to finish them.
- **Snapshot data** — verify current status with the council, and always check
  airspace in a drone app before flying.

## Next steps

1. **Site-visit the two recreation grounds** (Rugby Pitch, Glenconner Park).
2. **Confirm the 50 m vs 150 m rule** with BMFA.
3. **Open the council conversation** via Community Asset Transfer — each tracked
   [issue](../../issues) carries the CAT contact. See [docs/outreach-tracking.md](docs/outreach-tracking.md).
