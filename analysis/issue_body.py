#!/usr/bin/env python3
"""Assemble the full Markdown body of a site's outreach issue.

Single source of truth for what a site issue contains: satellite image, site
details, the Community Asset Transfer contact for its council, the member-travel
report, and the outreach checklist. Used by both scripts/elevate_site.sh (new
issues) and scripts/backfill_issues.sh (existing ones).

Usage:
  python3 analysis/issue_body.py --code <SVDLS_site_code> [--image-url <raw_url>]
"""

import argparse
import csv
import os
import re

import members          # build_report() — member-travel section
import site_proximity   # assess() — housing-proximity section
from basemap import raw_base

HERE = os.path.dirname(os.path.abspath(__file__))
SCORED = os.path.join(HERE, "..", "outputs", "all_scored_sites.csv")
CONTACTS_MD = os.path.join(HERE, "..", "data", "council_contacts.md")


def site_row(code):
    with open(SCORED, newline="") as f:
        for r in csv.DictReader(f):
            if r["site_code"] == code:
                return r
    raise SystemExit(f"Site code {code!r} not found in {os.path.relpath(SCORED)}.")


def council_contact(council):
    """Return (url, contact) for a council from council_contacts.md, or (None, None)."""
    with open(CONTACTS_MD) as f:
        for line in f:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 3 and cells[0] == council:
                return cells[1], cells[2]
    return None, None


def build(code, image_url=None):
    r = site_row(code)
    name = r["site_name"].strip() or r["address"].strip() or code
    site = (float(r["lat"]), float(r["lon"]))

    parts = []
    if image_url:
        parts.append(f"![Satellite view]({image_url})\n"
                     "*Red crosshair = site centroid · 100 m scale bar · imagery © Esri/Maxar.*\n\n---\n")

    details = [
        f"**Council:** {r['council']} · **Size:** {r['size_ha']} ha · Score {r['score']}",
        f"**SVDLS code:** {code}",
        f"**Type / potential / former use:** {r['site_type']} · {r['development_potential']} · {r['previous_use']}",
        f"**Map:** {r['map_url']}",
    ]
    if r.get("in_airport_frz") == "True":
        details.append("\n**Warning: inside an airport flight-restriction zone — "
                       "likely unflyable. Confirm before pursuing.**")
    parts.append("\n".join(details))

    # Housing-proximity screen (needs OpenStreetMap via Overpass — degrade gracefully).
    try:
        res = site_proximity.assess(code, make_image=False)
        block = res["markdown"]
        base = raw_base()
        rel = os.path.relpath(res["image"], os.path.join(HERE, ".."))
        if base and os.path.exists(res["image"]):
            block += (f"\n\n![Housing proximity]({base}/{rel})\n"
                      "*Yellow = approx site extent (from area, not a surveyed boundary) · "
                      "orange = separation line · red = homes · "
                      "imagery © Esri, buildings © OpenStreetMap.*")
        parts.append(block)
    except Exception as e:  # network/Overpass hiccup shouldn't block issue creation
        parts.append(f"### Housing proximity (CAA/BMFA separation)\n\n"
                     f"_Screen unavailable ({e}). Re-run `analysis/site_proximity.py "
                     f"--code {code}`._")

    url, contact = council_contact(r["council"])
    if url:
        line = (f"### How to approach the council\n\n"
                f"Route: **Community Asset Transfer** (Community Empowerment (Scotland) Act 2015).\n"
                f"- **{r['council']} CAT page:** {url}")
        if contact and contact != "via enquiry form":
            line += f"\n- **Contact:** {contact}"
        parts.append(line)

    parts.append(members.build_report(site))

    parts.append("- [ ] Satellite view checked\n"
                 "- [ ] Airspace checked in a drone app\n"
                 "- [ ] First contact made\n"
                 "- [ ] Site visit")

    return "\n\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description="Build a site issue's Markdown body.")
    ap.add_argument("--code", required=True, help="SVDLS site_code")
    ap.add_argument("--image-url", help="Raw URL of the satellite image, if already pushed")
    args = ap.parse_args()
    print(build(args.code, args.image_url))


if __name__ == "__main__":
    main()
