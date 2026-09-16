# Glasgow FPV Drone Racing — Land Search

Finding a new home for our FPV drone racing club by mining Scotland's open land data.

We're a registered charity and a recognised sport, with full [BMFA](https://bmfa.org)
membership and public liability insurance. We currently fly on a football-pitch-sized
plot at Craufurdland Castle near Fenwick (East Ayrshire), and we're looking for a
site in and around Glasgow that the club can grow into.

This repo takes the **[Scottish Vacant and Derelict Land Survey (SVDLS)](https://www.data.gov.uk/dataset/8a4f7b4c-2a3f-4f92-9d1e-svdls)**
— a national record of vacant and derelict land — and filters it down to realistic,
council-owned candidate sites, then ranks them for how well they'd suit a drone
racing course.

## Why council-owned land?

As a registered charity and recognised sport, we can make a credible case to a
local authority for recreational use of land they're not developing. So we filter
to **council-owned** sites and favour land the council has **no active plans to
build on** — that means both more secure tenure for us and an easier ask of them.

## What we're looking for

A good FPV racing site is:

- **About the size of a football pitch** (~0.7 ha) or a bit larger — we filter to 0.4–3.0 ha.
- **Open, flat, vacant ground** — not derelict rubble or land with buildings on it.
- **Clear of airport flight-restriction zones (FRZ)** — we flag proximity to Glasgow and Cumbernauld airports.
- **Away from dense housing** — for line-of-sight, and to keep separation from uninvolved people (a BMFA/CAA consideration) and minimise noise objections.
- **Low contamination risk** — former recreation grounds, pitches and amenity land beat ex-industrial sites.

## The results

- **[REPORT.md](REPORT.md)** — the shortlist of standout sites, with map links, reasoning, and what to avoid. **Start here.**
- **[outputs/all_scored_sites.csv](outputs/all_scored_sites.csv)** — every council-owned in-region site (289 of them), scored, with lat/long, map links and airport distances.
- **[outputs/ranked_table.md](outputs/ranked_table.md)** — the full ranked table (FRZ sites excluded).
- **[outputs/satellite/](outputs/satellite/)** — annotated satellite views of each shortlisted site (crosshair on the centroid, 100 m scale bar).

## Tracking outreach

We use **GitHub Issues** to track which sites we've approached and where each
conversation stands — one issue per site. Each issue carries the site's satellite
view, its **member-travel report** (how far each of us drives to it vs the castle
now, and the average), and the **Community Asset Transfer** contact for the
relevant council — the statutory route for a charity to take on council land. See
**[docs/outreach-tracking.md](docs/outreach-tracking.md)** for how it works.

### Member travel

Add your postcode to **[data/members.md](data/members.md)** (postcode only — no
names). We geocode it (postcodes.io) and get real driving distance/time (OSRM),
both free and keyless, comparing every site against the current base at
Craufurdland Castle. After adding members, refresh the issues with
`./scripts/backfill_issues.sh`.

## Reproducing the analysis

Pure Python 3, no dependencies to install.

```bash
python3 analysis/find_sites.py
```

This reads `data/Vacant_and_Derelict_Land_-_Scotland.csv` and regenerates
everything in `outputs/`.

| File | What it does |
|---|---|
| `analysis/find_sites.py` | Filters, scores and ranks the sites. All the tunable knobs (region, size band, scoring weights) are at the top. |
| `analysis/osgb.py` | Converts the survey's OS grid references to WGS84 lat/long for map links. |
| `analysis/fetch_satellite.py` | Downloads & annotates a satellite view per shortlisted site. Needs `requests` + `Pillow` (`pip install -r requirements.txt`). |
| `analysis/members.py` | Member-travel report for a site (geocoding + driving times). Needs `requests`. |
| `analysis/issue_body.py` | Assembles a site issue's full Markdown body (single source of truth). |

### How the score works

Each site gets a score from four factors — site type, the council's development
intentions, the previous use, and size. The exact weights live at the top of
`analysis/find_sites.py`; edit them and re-run to re-rank. Higher is better.

## Caveats

- **The survey is a snapshot.** Some sites may since have been built on or reallocated — always verify current status with the council.
- **Always check airspace** in a drone app (e.g. Drone Assist) before flying anywhere — our FRZ flag only covers the two nearest airports.
- **A site visit is essential.** The data doesn't capture surface condition, access, fencing or contamination.

## Data source & licence

Source data: Scottish Vacant and Derelict Land Survey, published under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
Our analysis code in this repo is released under the MIT Licence (see [LICENSE](LICENSE)).
