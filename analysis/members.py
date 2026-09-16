#!/usr/bin/env python3
"""Work out how far each club member would travel to a site, and the average.

Reads member postcodes from data/members.md, geocodes them (postcodes.io — free,
no key), and gets real driving distance/time via OSRM (free, no key). Compares
each site against the club's current base at Craufurdland Castle so we can see
whether a site is actually closer for people.

Usage:
  python3 analysis/members.py --code <SVDLS_site_code>   # report for one site
  python3 analysis/members.py --lat <lat> --lon <lon>    # report for a coordinate
  python3 analysis/members.py --dump                     # geocode members -> JSON
                                                         # (feeds the scorer)

Prints a Markdown travel report (the block embedded in each site issue).
"""

import argparse
import csv
import json
import math
import os
import re
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
MEMBERS_MD = os.path.join(HERE, "..", "data", "members.md")
SCORED = os.path.join(HERE, "..", "outputs", "all_scored_sites.csv")
CACHE = os.path.join(HERE, "..", "outputs", ".geocode_cache.json")
LOCATIONS = os.path.join(HERE, "..", "outputs", "member_locations.json")

# The club's current home — Craufurdland Castle, near Fenwick (East Ayrshire).
CASTLE_POSTCODE = "KA3 6BS"
COMMUTE_THRESHOLD_MIN = 30  # "far" — the bar the castle currently fails for most

HEADERS = {"User-Agent": "glasgow-fpv-land-search/1.0 (club site scouting)"}


def load_cache():
    try:
        with open(CACHE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w") as f:
        json.dump(cache, f, indent=0, sort_keys=True)


def geocode(postcode, cache):
    """Postcode or outcode -> (lat, lon) via postcodes.io, cached."""
    key = postcode.upper().strip()
    if key in cache:
        return tuple(cache[key])
    compact = key.replace(" ", "")
    # A full postcode has an inward part (digit + 2 letters); an outcode doesn't.
    is_full = bool(re.search(r"\d[A-Z]{2}$", compact))
    if is_full:
        url = f"https://api.postcodes.io/postcodes/{requests.utils.quote(key)}"
    else:
        url = f"https://api.postcodes.io/outcodes/{requests.utils.quote(compact)}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    res = r.json().get("result")
    if not res:
        raise SystemExit(f"Could not geocode postcode {postcode!r}.")
    latlon = (res["latitude"], res["longitude"])
    cache[key] = list(latlon)
    save_cache(cache)
    time.sleep(0.1)
    return latlon


def haversine_km(a, b):
    R = 6371.0
    dlat = math.radians(b[0] - a[0])
    dlon = math.radians(b[1] - a[1])
    x = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(x))


def drive(origin, dest):
    """Return (km, minutes, method). Falls back to straight-line if OSRM fails."""
    url = (f"http://router.project-osrm.org/route/v1/driving/"
           f"{origin[1]},{origin[0]};{dest[1]},{dest[0]}?overview=false")
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        route = r.json()["routes"][0]
        time.sleep(0.1)
        return round(route["distance"] / 1000, 1), round(route["duration"] / 60), "drive"
    except (requests.RequestException, KeyError, IndexError):
        km = haversine_km(origin, dest)
        return round(km, 1), None, "straight-line"


def load_members():
    members = []
    with open(MEMBERS_MD) as f:
        for line in f:
            m = re.match(r"\|\s*(\d+)\s*\|\s*([A-Za-z0-9 ]+?)\s*\|", line)
            if m and m.group(2).strip().lower() != "postcode":
                members.append((m.group(1), m.group(2).strip().upper()))
    return members


def site_from_code(code):
    with open(SCORED, newline="") as f:
        for r in csv.DictReader(f):
            if r["site_code"] == code:
                if not r["lat"] or not r["lon"]:
                    raise SystemExit(f"Site {code} has no coordinates.")
                return float(r["lat"]), float(r["lon"])
    raise SystemExit(f"Site code {code!r} not found in {os.path.relpath(SCORED)}.")


def build_report(site):
    cache = load_cache()
    castle = geocode(CASTLE_POSTCODE, cache)
    members = load_members()
    if not members:
        return "_No members listed in data/members.md yet._"

    rows = []
    site_mins, castle_mins, any_straight = [], [], False
    for mid, pc in members:
        home = geocode(pc, cache)
        s_km, s_min, method = drive(home, site)
        c_km, c_min, _ = drive(home, castle)
        if method == "straight-line":
            any_straight = True
        if s_min is not None:
            site_mins.append(s_min)
        if c_min is not None:
            castle_mins.append(c_min)
        rows.append((mid, pc, s_km, s_min, c_km, c_min))

    def fmt_min(m):
        return f"{m} min" if m is not None else "—"

    lines = ["### Member travel", "",
             f"Driving distance/time from each member, vs the current base "
             f"(Craufurdland Castle, {CASTLE_POSTCODE}).", "",
             "| Member | Postcode | To site | To castle now | Change |",
             "|---|---|---|---|---|"]
    for mid, pc, s_km, s_min, c_km, c_min in rows:
        if s_min is not None and c_min is not None:
            delta = s_min - c_min
            change = f"{'▼' if delta < 0 else '▲' if delta > 0 else '='} {abs(delta)} min"
        else:
            change = "—"
        lines.append(f"| {mid} | {pc} | {s_km} km / {fmt_min(s_min)} "
                     f"| {c_km} km / {fmt_min(c_min)} | {change} |")

    if site_mins:
        mean_site = round(sum(site_mins) / len(site_mins))
        far = sum(1 for m in site_mins if m > COMMUTE_THRESHOLD_MIN)
        summary = (f"**Average to this site: {mean_site} min** "
                   f"({far} of {len(site_mins)} members over {COMMUTE_THRESHOLD_MIN} min).")
        if castle_mins:
            mean_castle = round(sum(castle_mins) / len(castle_mins))
            d = mean_site - mean_castle
            verb = "closer" if d < 0 else "further" if d > 0 else "the same"
            summary += (f" Average to the castle now: {mean_castle} min — "
                        f"this site is **{abs(d)} min {verb}** on average.")
        lines += ["", summary]
    if any_straight:
        lines += ["", "_Some legs used straight-line distance (routing service "
                  "unavailable); times shown as —._"]
    return "\n".join(lines)


def dump_locations():
    """Geocode all members + the castle to outputs/member_locations.json.

    The scorer (analysis/find_sites.py) reads this so it stays fast and offline —
    re-run this whenever data/members.md changes.
    """
    cache = load_cache()
    data = {
        "castle": {"postcode": CASTLE_POSTCODE, "latlon": list(geocode(CASTLE_POSTCODE, cache))},
        "members": [{"id": mid, "postcode": pc, "latlon": list(geocode(pc, cache))}
                    for mid, pc in load_members()],
    }
    with open(LOCATIONS, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {len(data['members'])} member locations to "
          f"{os.path.relpath(LOCATIONS, os.path.join(HERE, '..'))}")


def main():
    ap = argparse.ArgumentParser(description="Member travel report for a site.")
    ap.add_argument("--code", help="SVDLS site_code (coords looked up in the scored CSV).")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    ap.add_argument("--dump", action="store_true",
                    help="Geocode members to outputs/member_locations.json (for the scorer).")
    args = ap.parse_args()

    if args.dump:
        dump_locations()
        return

    if args.code:
        site = site_from_code(args.code)
    elif args.lat is not None and args.lon is not None:
        site = (args.lat, args.lon)
    else:
        ap.error("give --code, or both --lat and --lon")

    print(build_report(site))


if __name__ == "__main__":
    main()
