#!/usr/bin/env python3
"""Fetch an annotated satellite view for each shortlisted site.

Centred on the site centroid, with a crosshair marker, a scale bar and a caption.
Saves to ../outputs/satellite/. Tile fetching and pixel maths live in basemap.py.

Usage:
  python3 analysis/fetch_satellite.py                 # (re)build the 7 shortlist images
  python3 analysis/fetch_satellite.py --code <CODE>   # build ONE image for a site by
                                                      # its SVDLS site_code (from the
                                                      # scored CSV). Prints the saved
                                                      # path (used by elevate_site.sh).

Imagery © Esri, Maxar, Earthstar Geographics.
"""

import argparse
import csv
import os

from basemap import Basemap, font, ATTRIB

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "outputs", "satellite")
SCORED = os.path.join(HERE, "..", "outputs", "all_scored_sites.csv")

ZOOM = 17          # ~0.7 m/px at this latitude -> ~670 m across a 1000 px frame
SIZE = 1000        # output width/height in pixels

# The shortlist from REPORT.md — (rank/label, name, lat, lon).
SITES = [
    ("1", "Former Blaes Pitch, Cambuslang", 55.820998, -4.151503),
    ("2", "Former Recreation Ground, Glenmavis", 55.883586, -4.002923),
    ("3", "Wheatholme Park North, Airdrie", 55.874173, -3.970852),
    ("4", "East of Lochgoin Avenue, Nitshill", 55.917933, -4.372224),
    ("5", "Rear of Gardenside Crescent, Cambuslang", 55.827945, -4.161786),
    ("6", "Northern Site, Alexandria", 55.996137, -4.574884),
    ("7", "Stoner Crescent, Auchinleck", 55.474799, -4.292637),
]


def build_image(name, lat, lon):
    bm = Basemap(lat, lon, ZOOM, SIZE)
    canvas = bm.image
    from PIL import ImageDraw
    draw = ImageDraw.Draw(canvas)
    mid = SIZE // 2

    # Crosshair on the exact site centroid
    draw.line([(mid - 22, mid), (mid - 7, mid)], fill=(255, 60, 60), width=3)
    draw.line([(mid + 7, mid), (mid + 22, mid)], fill=(255, 60, 60), width=3)
    draw.line([(mid, mid - 22), (mid, mid - 7)], fill=(255, 60, 60), width=3)
    draw.line([(mid, mid + 7), (mid, mid + 22)], fill=(255, 60, 60), width=3)
    draw.ellipse([mid - 4, mid - 4, mid + 4, mid + 4], outline=(255, 60, 60), width=2)

    # Scale bar (100 m)
    bar_px = int(bm.m2px(100))
    bx, by = 20, SIZE - 30
    draw.rectangle([bx - 6, by - 20, bx + bar_px + 6, by + 12], fill=(0, 0, 0))
    draw.line([(bx, by), (bx + bar_px, by)], fill=(255, 255, 255), width=3)
    draw.line([(bx, by - 5), (bx, by + 5)], fill=(255, 255, 255), width=3)
    draw.line([(bx + bar_px, by - 5), (bx + bar_px, by + 5)], fill=(255, 255, 255), width=3)
    draw.text((bx, by - 18), "100 m", fill=(255, 255, 255), font=font(13))

    # Caption bar — name on the left, coordinates right-aligned
    draw.rectangle([0, 0, SIZE, 34], fill=(0, 0, 0))
    draw.text((10, 7), f"#{name}", fill=(255, 255, 255), font=font(20))
    coord = f"{lat:.5f}, {lon:.5f}"
    f_coord = font(14)
    draw.text((SIZE - draw.textlength(coord, font=f_coord) - 10, 10),
              coord, fill=(200, 200, 200), font=f_coord)

    # Attribution (required)
    f_small = font(12)
    w = draw.textlength(ATTRIB, font=f_small)
    draw.rectangle([SIZE - w - 12, SIZE - 20, SIZE, SIZE], fill=(0, 0, 0))
    draw.text((SIZE - w - 6, SIZE - 18), ATTRIB, fill=(220, 220, 220), font=f_small)
    return canvas


def _nameslug(name):
    s = name.lower().split(",")[0].replace(" ", "-")
    return "".join(c for c in s if c.isalnum() or c == "-")


def slug(label, name):
    return f"{int(label):02d}_{_nameslug(name)}"


def lookup_by_code(code):
    """Return (name, lat, lon) for a site_code from all_scored_sites.csv."""
    with open(SCORED, newline="") as f:
        for r in csv.DictReader(f):
            if r["site_code"] == code:
                name = r["site_name"].strip() or r["address"].strip() or code
                if not r["lat"] or not r["lon"]:
                    raise SystemExit(f"Site {code} has no coordinates in the survey.")
                return name, float(r["lat"]), float(r["lon"])
    raise SystemExit(f"Site code {code!r} not found in {os.path.relpath(SCORED)}. "
                     "Run analysis/find_sites.py first, or check the code.")


def render(label, name, lat, lon, filename):
    os.makedirs(OUT, exist_ok=True)
    img = build_image(f"{label}  {name}", lat, lon)
    path = os.path.join(OUT, filename)
    img.save(path, "JPEG", quality=85)
    return path


def main():
    ap = argparse.ArgumentParser(description="Fetch annotated satellite views of sites.")
    ap.add_argument("--code", help="SVDLS site_code — render just this one site.")
    args = ap.parse_args()

    if args.code:
        name, lat, lon = lookup_by_code(args.code)
        path = render(args.code, name, lat, lon, f"{args.code}_{_nameslug(name)}.jpg")
        print(os.path.relpath(path, os.path.join(HERE, "..")))
        return

    for label, name, lat, lon in SITES:
        path = render(label, name, lat, lon, slug(label, name) + ".jpg")
        print(f"  saved {os.path.relpath(path, os.path.join(HERE, '..'))}")
    print(f"Done — {len(SITES)} images in outputs/satellite/")


if __name__ == "__main__":
    main()
