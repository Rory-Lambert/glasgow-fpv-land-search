#!/usr/bin/env python3
"""Screen every candidate site for homes near it, so the scorer can omit any site
with housing inside the required separation.

Queries OpenStreetMap (Overpass) once per site and caches the nearest-home
distance in outputs/housing_screen.json. Re-runs only screen sites not already
cached, so the ~260-query sweep is a one-time cost; pass --refresh to redo all.
The cached distance is measured out to ~175 m beyond the site edge, so the score
can later re-threshold at a larger gap (e.g. 150 m) without re-querying.

Usage:
  python3 analysis/housing.py --build [--refresh]   # screen all candidates
  python3 analysis/housing.py --code <SVDLS_code>    # just print one site's result

Site extent is approximated as a compact square of the recorded area (the survey
gives no boundary) — see site_proximity.py. Homes = OSM building types in
site_proximity.RESIDENTIAL.
"""

import argparse
import csv
import json
import math
import os
import time

import math

import requests

from site_proximity import (OVERPASS_ENDPOINTS, HEADERS, fetch_buildings,
                            to_local, poly_min_dist, RESIDENTIAL)

HERE = os.path.dirname(os.path.abspath(__file__))
SCORED = os.path.join(HERE, "..", "outputs", "all_scored_sites.csv")
SCREEN = os.path.join(HERE, "..", "outputs", "housing_screen.json")

MARGIN_M = 175   # measure homes out to edge + this (covers a later 150 m threshold)
BATCH = 12       # sites per Overpass query — small enough to keep responses light
DELAY_S = 4.0    # gap between batch requests; gentle on the public servers


def haversine_m(a, b):
    R = 6371000.0
    dlat = math.radians(b[0] - a[0])
    dlon = math.radians(b[1] - a[1])
    x = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(x))


# Overpass regex of residential building= values (mirrors RESIDENTIAL) — filtering
# in the query keeps responses small and fast.
_RES_RE = "^(" + "|".join(sorted(RESIDENTIAL)) + ")$"


def fetch_buildings_batch(sites):
    """One Overpass query for many sites. `sites` = list of (lat, lon, radius_m).
    Returns residential building polygons as (lat, lon) vertex lists."""
    clauses = "".join(f'way["building"~"{_RES_RE}"](around:{r},{lat},{lon});'
                      for lat, lon, r in sites)
    q = f"[out:json][timeout:40];({clauses});out geom tags;"
    # lz4 has been the responsive mirror; try it first. Short timeout so a hung
    # endpoint fails fast (45 s) instead of stalling the whole batch.
    endpoints = ["https://lz4.overpass-api.de/api/interpreter"] + \
                [e for e in OVERPASS_ENDPOINTS if "lz4" not in e]
    last = None
    for attempt in range(5):
        endpoint = endpoints[attempt % len(endpoints)]
        try:
            r = requests.post(endpoint, data={"data": q}, headers=HEADERS, timeout=45)
            r.raise_for_status()
            homes = []
            for e in r.json().get("elements", []):
                g = e.get("geometry")
                if g and e.get("tags", {}).get("building", "yes") in RESIDENTIAL:
                    homes.append([(p["lat"], p["lon"]) for p in g])
            return homes
        except requests.RequestException as e:
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Overpass unavailable after retries: {last}")


def nearest_home_m(lat, lon, area_ha):
    """Nearest residential building to the site's approx square edge, in metres.

    Returns (distance_or_None, n_homes_within_radius, radius_m). None distance
    means no home within the searched radius.
    """
    half = math.sqrt(area_ha * 10000.0) / 2.0
    radius = int(half + MARGIN_M)
    square = [(-half, -half), (half, -half), (half, half), (-half, half)]

    nearest, n_homes = None, 0
    for b in fetch_buildings(lat, lon, radius):
        if b["btype"] not in RESIDENTIAL:
            continue
        poly = [to_local(la, lo, lat, lon) for la, lo in b["geom"]]
        d = poly_min_dist(square, poly)
        nearest = d if nearest is None else min(nearest, d)
        n_homes += 1
    return (round(nearest, 1) if nearest is not None else None), n_homes, radius


def load_screen():
    try:
        with open(SCREEN) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _screen_site(r, homes):
    """Nearest residential building to r's approx square edge, given batch homes."""
    lat, lon = float(r["lat"]), float(r["lon"])
    half = math.sqrt(float(r["size_ha"]) * 10000.0) / 2.0
    radius = half + MARGIN_M
    square = [(-half, -half), (half, -half), (half, half), (-half, half)]
    nearest, n = None, 0
    for poly_ll in homes:
        # Cheap prune: skip homes whose first vertex is well outside this site's radius.
        if haversine_m((lat, lon), poly_ll[0]) > radius + 60:
            continue
        poly = [to_local(la, lo, lat, lon) for la, lo in poly_ll]
        d = poly_min_dist(square, poly)
        nearest = d if nearest is None else min(nearest, d)
        n += 1
    return ({"nearest_home_m": round(nearest, 1) if nearest is not None else None,
             "n_homes": n, "radius_m": int(radius)})


def build(refresh=False, max_batches=None):
    with open(SCORED, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["lat"] and r["lon"]]

    screen = {} if refresh else load_screen()
    todo = [r for r in rows if r["site_code"] not in screen
            or "error" in screen[r["site_code"]]]
    n_batches = (len(todo) + BATCH - 1) // BATCH
    if max_batches:
        n_batches = min(n_batches, max_batches)
        todo = todo[:n_batches * BATCH]     # bound this run so it exits cleanly
    print(f"{len(rows)} candidates; {len(todo)} to screen in {n_batches} batch(es) "
          f"({len(rows) - len(todo)} not touched this run).")

    for bi in range(n_batches):
        batch = todo[bi * BATCH:(bi + 1) * BATCH]
        sites = [(float(r["lat"]), float(r["lon"]),
                  int(math.sqrt(float(r["size_ha"]) * 10000.0) / 2 + MARGIN_M)) for r in batch]
        try:
            homes = fetch_buildings_batch(sites)
            for r in batch:
                screen[r["site_code"]] = _screen_site(r, homes)
        except Exception as e:            # whole batch failed — mark for retry
            for r in batch:
                screen[r["site_code"]] = {"error": str(e)[:120]}
        with open(SCREEN, "w") as f:
            json.dump(screen, f, indent=0, sort_keys=True)
        print(f"  batch {bi + 1}/{n_batches} done ({(bi + 1) * BATCH} sites)")
        if bi < n_batches - 1:
            time.sleep(DELAY_S)

    errs = sum(1 for v in screen.values() if "error" in v)
    print(f"Done. {len(screen)} sites in {os.path.relpath(SCREEN)} "
          f"({errs} errored — re-run to retry).")


def main():
    ap = argparse.ArgumentParser(description="Screen candidate sites for nearby homes.")
    ap.add_argument("--build", action="store_true", help="screen all candidates -> JSON")
    ap.add_argument("--refresh", action="store_true", help="re-screen even cached sites")
    ap.add_argument("--max-batches", type=int, help="cap batches this run (for clean short runs)")
    ap.add_argument("--code", help="screen just one site by SVDLS code and print it")
    args = ap.parse_args()

    if args.code:
        with open(SCORED, newline="") as f:
            r = next((x for x in csv.DictReader(f) if x["site_code"] == args.code), None)
        if not r:
            raise SystemExit(f"Site {args.code} not found.")
        dist, n, radius = nearest_home_m(float(r["lat"]), float(r["lon"]), float(r["size_ha"]))
        print(f"{args.code}: nearest home {dist} m (searched {radius} m, {n} homes)")
    elif args.build:
        build(refresh=args.refresh, max_batches=args.max_batches)
    else:
        ap.error("give --build or --code")


if __name__ == "__main__":
    main()
