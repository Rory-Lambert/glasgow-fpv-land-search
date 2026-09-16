#!/usr/bin/env python3
"""Find candidate sites for an FPV drone racing club from the Scottish Vacant
and Derelict Land Survey (SVDLS).

Pipeline
--------
1. Filter the national dataset to council-owned land in the Glasgow travel-to-work
   area, roughly football-pitch sized.
2. Score each site on how well it suits an FPV racing course (open ground, low
   development pressure, flat/uncontaminated former use, sensible size) AND how
   close it is to the club's members.
3. Flag proximity to airport flight-restriction zones (FRZ).
4. Write ranked outputs to ../outputs/ (CSV + a Markdown table).

Run:  python3 analysis/find_sites.py     (from the repo root)

Member proximity is read from outputs/member_locations.json — regenerate it with
`python3 analysis/members.py --dump` after editing data/members.md, then re-run
this. If that file is absent the proximity component is simply 0.

Pure standard library — no dependencies to install.
"""

import csv
import json
import math
import os

from osgb import osgb36_to_wgs84

# --------------------------------------------------------------------------
# Configuration — tweak these to re-scope the search
# --------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "Vacant_and_Derelict_Land_-_Scotland.csv")
OUT = os.path.join(HERE, "..", "outputs")

# Glasgow + surrounding councils (incl. East Ayrshire, the club's home patch)
REGION = {
    "Glasgow City", "East Dunbartonshire", "West Dunbartonshire",
    "East Renfrewshire", "Renfrewshire", "North Lanarkshire",
    "South Lanarkshire", "Inverclyde", "East Ayrshire",
}

OWNER = "Local Authority"     # the club wants land it can appeal to the council for
SIZE_MIN, SIZE_MAX = 0.4, 3.0  # hectares; a football pitch is ~0.7 ha

# Member proximity — a site everyone can actually reach scores higher.
# Scored on the mean straight-line distance from members (from
# outputs/member_locations.json, written by `analysis/members.py --dump`).
# Road distance/time is ~1.3-1.5x this and is shown per-member in each issue.
PROXIMITY_BANDS = [(8, 4), (15, 3), (25, 2), (40, 1)]  # (max mean km, points); else 0

# Reference points in OSGB36 easting/northing for distance flags
GLASGOW_CENTRE = (258906, 665004)   # George Square
GLASGOW_AIRPORT = (247800, 666300)  # EGPF
CUMBERNAULD_AIRPORT = (276300, 674600)  # EGPG
FRZ_KM = 5.0  # sites inside this radius of an airport are flagged

# Scoring weights ----------------------------------------------------------
# Open, flat vacant land beats derelict rubble beats land with buildings.
TYPE_SCORE = {"Vacant Land": 3, "Derelict": 0, "Vacant Land and Buildings": -3}

# Land the council will NOT develop is both safer tenure and an easier "ask".
DEV_SCORE = {
    "Uneconomic to Develop/Soft End Use": 4,
    "Developable - Undetermined": 2,
    "Unknown (uncertain/insufficient information)": 1,
    "Developable - Medium Term": 0,
    "Developable - Short Term": -2,
}

# Former use hints at surface condition, obstacles and contamination risk.
PREV_SCORE = {
    "Recreation & Leisure": 3, "Passive Open Space": 3, "Agriculture": 2,
    "Prepared Ground": 2, "Forestry/Woodland": 1, "Education": 1,
    "Residential - Housing": 1, "Unknown": 0, "Other": 0, "Community & Health": 0,
    "Residential - Hotels, Hostels etc": 0, "Offices": -1, "Retailing": -1,
    "Storage": -1, "Wholesale Distribution": -1, "Transport": -2,
    "Mineral Activity": -2, "Utility Services": -2, "Manufacturing": -3,
    "Other General Industry": -3,
}


def size_score(ha):
    """Reward sizes near a football pitch, taper towards the band edges."""
    if 0.7 <= ha <= 2.0:
        return 3
    if 0.5 <= ha < 0.7 or 2.0 < ha <= 3.0:
        return 1
    return 0


def to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def km(e, n, ref):
    return math.hypot(e - ref[0], n - ref[1]) / 1000.0


def haversine_km(a, b):
    R = 6371.0
    dlat = math.radians(b[0] - a[0])
    dlon = math.radians(b[1] - a[1])
    x = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(x))


def load_member_locations():
    try:
        with open(os.path.join(OUT, "member_locations.json")) as f:
            return [tuple(m["latlon"]) for m in json.load(f)["members"]]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return []


def proximity_score(mean_km):
    if mean_km is None:
        return 0
    for max_km, pts in PROXIMITY_BANDS:
        if mean_km <= max_km:
            return pts
    return 0


def main():
    members = load_member_locations()

    with open(DATA, newline="") as f:
        rows = list(csv.DictReader(f))

    sites = []
    for r in rows:
        if r["local_authority"] not in REGION:
            continue
        if r["owner_1"] != OWNER:
            continue
        size = to_float(r["site_size"])
        if size is None or not (SIZE_MIN <= size <= SIZE_MAX):
            continue

        e, n = to_float(r["east"]), to_float(r["north"])
        lat = lon = d_centre = d_gla = d_cum = None
        in_frz = False
        if e is not None and n is not None:
            lat, lon = osgb36_to_wgs84(e, n)
            d_centre = round(km(e, n, GLASGOW_CENTRE), 1)
            d_gla = round(km(e, n, GLASGOW_AIRPORT), 1)
            d_cum = round(km(e, n, CUMBERNAULD_AIRPORT), 1)
            in_frz = d_gla < FRZ_KM or d_cum < FRZ_KM

        mean_member_km = None
        if members and lat is not None:
            mean_member_km = round(
                sum(haversine_km((lat, lon), m) for m in members) / len(members), 1)
        prox = proximity_score(mean_member_km)

        score = (
            TYPE_SCORE.get(r["site_type"], 0)
            + DEV_SCORE.get(r["development_potential"], 0)
            + PREV_SCORE.get(r["previous_use"], 0)
            + size_score(size)
            + prox
        )

        sites.append({
            "score": score,
            "proximity_score": prox,
            "mean_member_km": mean_member_km if mean_member_km is not None else "",
            "site_code": r["site_code"],
            "site_name": r["site_name"].strip(),
            "council": r["local_authority"],
            "address": r["address"].strip(),
            "size_ha": size,
            "site_type": r["site_type"],
            "development_potential": r["development_potential"],
            "previous_use": r["previous_use"],
            "lat": round(lat, 6) if lat else "",
            "lon": round(lon, 6) if lon else "",
            "km_from_glasgow_centre": d_centre if d_centre is not None else "",
            "km_from_glasgow_airport": d_gla if d_gla is not None else "",
            "km_from_cumbernauld_airport": d_cum if d_cum is not None else "",
            "in_airport_frz": in_frz,
            "map_url": (
                f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}"
                if lat else ""
            ),
        })

    # Sort best-first; within a score, nearest to Glasgow first.
    sites.sort(key=lambda s: (-s["score"], s["km_from_glasgow_centre"] or 999))

    os.makedirs(OUT, exist_ok=True)

    # 1) Full scored table as CSV
    cols = list(sites[0].keys())
    with open(os.path.join(OUT, "all_scored_sites.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(sites)

    # 2) A ready-to-paste Markdown table of the top sites (FRZ sites excluded)
    clear = [s for s in sites if not s["in_airport_frz"]]
    with open(os.path.join(OUT, "ranked_table.md"), "w") as f:
        f.write("| Rank | Score | Site | Council | Size (ha) | Type | Dev. potential | Former use | Avg member km | Map |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for i, s in enumerate(clear[:30], 1):
            name = s["site_name"] or s["address"][:40] or "(unnamed)"
            f.write(
                f"| {i} | {s['score']:+d} | {name} | {s['council']} | {s['size_ha']} "
                f"| {s['site_type']} | {s['development_potential']} | {s['previous_use']} "
                f"| {s['mean_member_km']} | [map]({s['map_url']}) |\n"
            )

    print(f"Scored {len(sites)} council-owned sites in region "
          f"({len(clear)} clear of airport FRZ).")
    if members:
        print(f"Member proximity included for {len(members)} member(s).")
    else:
        print("No member_locations.json — run `python3 analysis/members.py --dump` "
              "to include member proximity in the score.")
    print(f"Wrote {OUT}/all_scored_sites.csv and {OUT}/ranked_table.md")


if __name__ == "__main__":
    main()
