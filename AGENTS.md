# Agent guide

Repo purpose and structure: see [README.md](README.md). This file is the runbook
for the two tasks that have a right way and several wrong ones.

## Elevating a site to a tracked issue

When a site is chosen for outreach, create its issue with **one command** — do not
hand-roll the steps:

```bash
./scripts/elevate_site.sh <SVDLS_site_code>
```

Find the `site_code` in `outputs/all_scored_sites.csv` or `REPORT.md`. The script
reads the site's details, generates its satellite view and housing-proximity map,
commits and **pushes** both images, then opens a labelled issue embedding them. It
refuses to create a duplicate if an issue already references that code.

The ordering matters and is why this is a script, not a checklist: an issue
embeds its images by **raw GitHub URL**, which only resolves after they are
pushed. Creating the issue first gives broken images. `elevate_site.sh` pushes
before it references. If you must debug the pieces, they are `analysis/fetch_satellite.py --code <code>`
(satellite), `analysis/site_proximity.py --code <code>` (housing map), and
`analysis/issue_body.py --code <code>` (body) — but reach for the script first.

`analysis/issue_body.py` is the **single source of truth** for what an issue
contains: site details, the housing-proximity screen (from OpenStreetMap, via
`site_proximity.py`), the council's Community Asset Transfer contact (from
`data/council_contacts.md`), and the member-travel report (from `data/members.md`).
Edit the body there, not in the bash scripts.

Outreach tracking conventions (status/council labels, closing issues): see
[docs/outreach-tracking.md](docs/outreach-tracking.md).

## Refreshing issues after data changes

Member travel numbers are baked into each issue body at creation. After editing
`data/members.md` (or `data/council_contacts.md`), re-run the body for affected
issues — one issue, or all the originally-seeded ones:

```bash
./scripts/refresh_issue.sh <issue_number> <site_code>   # one issue
./scripts/backfill_issues.sh                            # the 7 seeded issues
```

`refresh_issue.sh` preserves the existing satellite image and rebuilds everything
else from current data.

## Re-running the analysis

```bash
python3 analysis/members.py --dump      # geocode members -> member_locations.json
python3 analysis/housing.py --build      # screen candidates for nearby homes (cached)
python3 analysis/find_sites.py          # regenerates everything in outputs/
python3 analysis/fetch_satellite.py     # rebuilds the 7 shortlist images
```

`find_sites.py` needs only Python 3; it reads two generated inputs:
`outputs/member_locations.json` (member-proximity score) and
`outputs/housing_screen.json` (the **hard filter** that omits any site with a home
within `HOUSING_GAP_M` — default 50 m). Run `members.py --dump` after editing
`data/members.md`, and `housing.py --build` to screen sites (it only queries sites
not already cached, so it's cheap after the first sweep; distances are stored out
to ~175 m so you can raise `HOUSING_GAP_M` to 150 and just re-run `find_sites.py`).
The `members.py`, `housing.py` and satellite scripts need `requests` (+ `Pillow`) —
`pip install -r requirements.txt`. Re-scope by editing the config block at the top
of `find_sites.py`, then re-run.

## Conventions

- Satellite imagery is free Esri World Imagery, no API key — used with the
  attribution burned into each image. Keep that attribution.
- `data/` holds the source survey verbatim; treat it as read-only input.
- `outputs/` is generated — regenerate it, don't hand-edit it.
