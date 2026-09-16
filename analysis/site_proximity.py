#!/usr/bin/env python3
"""Screen a site for nearby housing (the CAA/BMFA separation question) and draw
an annotated proximity map.

We only have the site's centroid + area from the survey, not its surveyed
boundary, so the site extent is APPROXIMATED as a compact square of the recorded
area. Building footprints are real, from OpenStreetMap (Overpass API, no key).
Distances are measured from that approximate edge to the nearest building.

Outputs (per site):
  - a Markdown assessment block (embedded in the site's issue)
  - outputs/proximity/<code>_<slug>.jpg — satellite view with the approx site
    extent, the required-gap line, and building footprints (homes highlighted)

Usage:
  python3 analysis/site_proximity.py --code <SVDLS_site_code> [--gap 50] [--print]

IMPORTANT: the required separation is a BMFA/CAA question. The default 50 m is the
figure the club was told; the standard Open-category A3 distance from residential
areas is 150 m, and a BMFA Article-16 authorisation may set something different.
Confirm the number that applies, then pass --gap.
"""

import argparse
import csv
import math
import os

import requests
from PIL import ImageDraw

from basemap import Basemap, font, ATTRIB

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "outputs", "proximity")
SCORED = os.path.join(HERE, "..", "outputs", "all_scored_sites.csv")

OVERPASS = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "glasgow-fpv-land-search/1.0 (site scouting)"}

REQUIRED_GAP_M = 50   # default; see the module docstring — confirm with BMFA/CAA
ZOOM = 18             # ~0.33 m/px -> ~335 m across a 1000 px frame
SIZE = 1000
R_EARTH = 6371000.0

# OSM building= values that indicate a dwelling.
RESIDENTIAL = {
    "house", "detached", "semidetached_house", "semi", "terrace", "terraced",
    "residential", "apartments", "bungalow", "dwelling", "maisonette",
    "houseboat", "static_caravan", "cabin",
}


# ---- geometry (local metres, equirectangular around the centroid) -----------

def to_local(lat, lon, lat0, lon0):
    x = math.radians(lon - lon0) * math.cos(math.radians(lat0)) * R_EARTH
    y = math.radians(lat - lat0) * R_EARTH
    return x, y


def pt_seg_dist(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def poly_min_dist(square, poly):
    """Min distance between two polygons (assumes they don't overlap)."""
    best = float("inf")
    for a in square:
        for i in range(len(poly)):
            best = min(best, pt_seg_dist(a, poly[i], poly[(i + 1) % len(poly)]))
    for p in poly:
        for i in range(len(square)):
            best = min(best, pt_seg_dist(p, square[i], square[(i + 1) % len(square)]))
    return best


# ---- data ------------------------------------------------------------------

def site_row(code):
    with open(SCORED, newline="") as f:
        for r in csv.DictReader(f):
            if r["site_code"] == code:
                return r
    raise SystemExit(f"Site code {code!r} not found in {os.path.relpath(SCORED)}.")


def image_path(r):
    """Deterministic output path for a site's proximity image."""
    name = r["site_name"].strip() or r["address"].strip() or r["site_code"]
    slug = "".join(c for c in name.lower().split(",")[0].replace(" ", "-")
                   if c.isalnum() or c == "-")
    return os.path.join(OUT, f"{r['site_code']}_{slug}.jpg")


def fetch_buildings(lat, lon, radius_m):
    q = (f"[out:json][timeout:40];"
         f'(way["building"](around:{radius_m},{lat},{lon});'
         f'relation["building"](around:{radius_m},{lat},{lon}););out geom tags;')
    r = requests.post(OVERPASS, data={"data": q}, headers=HEADERS, timeout=90)
    r.raise_for_status()
    out = []
    for e in r.json().get("elements", []):
        geom = e.get("geometry")
        if not geom:
            continue
        btype = e.get("tags", {}).get("building", "yes")
        out.append({"btype": btype, "geom": [(g["lat"], g["lon"]) for g in geom]})
    return out


def assess(code, gap=REQUIRED_GAP_M, make_image=True):
    r = site_row(code)
    lat, lon = float(r["lat"]), float(r["lon"])
    area_m2 = float(r["size_ha"]) * 10000.0
    half = math.sqrt(area_m2) / 2.0            # half-side of the approx square (m)
    radius = int(half + gap + 150)             # search a bit beyond the gap line

    buildings = fetch_buildings(lat, lon, radius)

    # Square site polygon in local metres, centred on the centroid.
    square = [(-half, -half), (half, -half), (half, half), (-half, half)]

    nearest_res = nearest_other = None
    homes_in_gap = others_in_gap = 0
    for b in buildings:
        poly = [to_local(la, lo, lat, lon) for la, lo in b["geom"]]
        d = poly_min_dist(square, poly)
        b["dist"] = d
        b["is_home"] = b["btype"] in RESIDENTIAL
        if b["is_home"]:
            nearest_res = d if nearest_res is None else min(nearest_res, d)
            if d < gap:
                homes_in_gap += 1
        else:
            nearest_other = d if nearest_other is None else min(nearest_other, d)
            if d < gap:
                others_in_gap += 1

    md = _markdown(r, gap, half, radius, nearest_res, nearest_other,
                   homes_in_gap, others_in_gap)
    img_path = image_path(r)
    if make_image:
        _draw(img_path, r, lat, lon, half, gap, buildings)
    return {"markdown": md, "image": img_path, "nearest_res": nearest_res,
            "homes_in_gap": homes_in_gap}


def _markdown(r, gap, half, radius, nearest_res, nearest_other, homes_in_gap, others_in_gap):
    lines = [f"### Housing proximity (CAA/BMFA separation)", "",
             f"Screening for buildings near the site (OpenStreetMap footprints). "
             f"Required gap: **{gap} m** — *confirm with BMFA/CAA; the standard A3 "
             f"distance from residential areas is 150 m.*", ""]
    if nearest_res is None:
        lines.append(f"- **No homes found within {radius} m** of the site.")
    else:
        verdict = ("**within the gap — likely can't fly here without moving the "
                   "flight line in or getting permissions**" if nearest_res < gap
                   else f"beyond the {gap} m gap")
        lines.append(f"- **Nearest home: ~{nearest_res:.0f} m** from the site's "
                     f"approximate edge — {verdict}.")
        if homes_in_gap:
            lines.append(f"- {homes_in_gap} home(s) within the {gap} m gap.")
    if others_in_gap:
        lines.append(f"- {others_in_gap} non-residential/unclassified building(s) "
                     f"within the gap — check they aren't dwellings.")
    lines += ["",
              f"*Extent is approximate: a {2*half:.0f} m square of the recorded area, "
              f"**not a surveyed boundary**. Verify against a site plan / on the ground.*"]
    return "\n".join(lines)


def _draw(path, r, lat, lon, half, gap, buildings):
    code = r["site_code"]
    os.makedirs(OUT, exist_ok=True)
    bm = Basemap(lat, lon, ZOOM, SIZE)
    base = bm.image.convert("RGBA")
    overlay = ImageDraw.Draw(base, "RGBA")
    mid = SIZE // 2
    half_px = bm.m2px(half)
    gap_px = bm.m2px(gap)

    # Required-gap line (rounded buffer of the square) then the approx extent.
    overlay.rounded_rectangle(
        [mid - half_px - gap_px, mid - half_px - gap_px,
         mid + half_px + gap_px, mid + half_px + gap_px],
        radius=gap_px, outline=(255, 140, 0, 255), width=3)
    overlay.rectangle([mid - half_px, mid - half_px, mid + half_px, mid + half_px],
                      outline=(255, 235, 0, 255), width=3)

    # Buildings: homes red (filled if within the gap), others cyan.
    for b in buildings:
        pts = [bm.px(la, lo) for la, lo in b["geom"]]
        if b["is_home"]:
            fill = (255, 0, 0, 110) if b["dist"] < gap else (255, 0, 0, 0)
            overlay.polygon(pts, outline=(255, 0, 0, 255), fill=fill, width=2)
        else:
            overlay.polygon(pts, outline=(0, 200, 255, 200))

    canvas = base.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    draw.line([(mid - 16, mid), (mid + 16, mid)], fill=(255, 60, 60), width=2)
    draw.line([(mid, mid - 16), (mid, mid + 16)], fill=(255, 60, 60), width=2)

    # Scale bar (100 m)
    bar = int(bm.m2px(100))
    bx, by = 20, SIZE - 28
    draw.rectangle([bx - 6, by - 20, bx + bar + 6, by + 12], fill=(0, 0, 0))
    draw.line([(bx, by), (bx + bar, by)], fill=(255, 255, 255), width=3)
    draw.text((bx, by - 18), "100 m", fill=(255, 255, 255), font=font(13))

    # Caption + legend
    name = r["site_name"].strip() or r["address"].strip() or code
    draw.rectangle([0, 0, SIZE, 34], fill=(0, 0, 0))
    draw.text((10, 7), name[:60], fill=(255, 255, 255), font=font(19))
    legend = [("approx site extent", (255, 235, 0)),
              (f"{gap} m line", (255, 140, 0)),
              ("home", (255, 60, 60)),
              ("other building", (0, 200, 255))]
    ly = 42
    for text, col in legend:
        draw.rectangle([10, ly + 2, 26, ly + 14], fill=col)
        draw.text((32, ly), text, fill=(255, 255, 255), font=font(13))
        ly += 20

    attrib = ATTRIB + " · Buildings (c) OpenStreetMap"
    f_small = font(12)
    w = draw.textlength(attrib, font=f_small)
    draw.rectangle([SIZE - w - 12, SIZE - 20, SIZE, SIZE], fill=(0, 0, 0))
    draw.text((SIZE - w - 6, SIZE - 18), attrib, fill=(220, 220, 220), font=f_small)

    canvas.save(path, "JPEG", quality=85)
    return path


def main():
    ap = argparse.ArgumentParser(description="Screen a site for nearby housing.")
    ap.add_argument("--code", required=True, help="SVDLS site_code")
    ap.add_argument("--gap", type=float, default=REQUIRED_GAP_M,
                    help=f"required separation in metres (default {REQUIRED_GAP_M})")
    ap.add_argument("--print", action="store_true", help="print the assessment markdown")
    args = ap.parse_args()

    res = assess(args.code, args.gap)
    if args.print:
        print(res["markdown"])
    else:
        print(os.path.relpath(res["image"], os.path.join(HERE, "..")))


if __name__ == "__main__":
    main()
