"""Shared satellite-basemap utilities.

Fetches and stitches free Esri World Imagery tiles (no API key) centred on a
coordinate, and maps between lat/lon and image pixels. Used by
fetch_satellite.py (annotated site views) and site_proximity.py (housing check).

Imagery © Esri, Maxar, Earthstar Geographics.
"""

import io
import math
import os
import re
import subprocess
import time

import requests
from PIL import Image, ImageFont

TILE_URL = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}")
HEADERS = {"User-Agent": "glasgow-fpv-land-search/1.0 (site scouting)"}
ATTRIB = "Imagery (c) Esri, Maxar, Earthstar Geographics"


def global_px(lat, lon, z):
    """Global Web-Mercator pixel coordinates (256 px tiles)."""
    s = math.sin(math.radians(lat))
    x = (lon + 180.0) / 360.0 * 256 * 2 ** z
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * 256 * 2 ** z
    return x, y


def ground_res(lat, z):
    """Metres per pixel at this latitude and zoom."""
    return 156543.03392 * math.cos(math.radians(lat)) / (2 ** z)


def font(size):
    for path in ("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


class Basemap:
    """A stitched square satellite image centred on (lat, lon)."""

    def __init__(self, lat, lon, zoom, size):
        self.lat, self.lon, self.zoom, self.size = lat, lon, zoom, size
        self.mpp = ground_res(lat, zoom)
        cx, cy = global_px(lat, lon, zoom)
        self.left, self.top = cx - size / 2, cy - size / 2
        self.image = self._stitch()

    def _stitch(self):
        canvas = Image.new("RGB", (self.size, self.size))
        tx0, tx1 = int(self.left // 256), int((self.left + self.size) // 256)
        ty0, ty1 = int(self.top // 256), int((self.top + self.size) // 256)
        for tx in range(tx0, tx1 + 1):
            for ty in range(ty0, ty1 + 1):
                r = requests.get(TILE_URL.format(z=self.zoom, x=tx, y=ty),
                                 headers=HEADERS, timeout=30)
                r.raise_for_status()
                tile = Image.open(io.BytesIO(r.content)).convert("RGB")
                canvas.paste(tile, (int(tx * 256 - self.left), int(ty * 256 - self.top)))
                time.sleep(0.05)
        return canvas

    def px(self, lat, lon):
        """lat/lon -> (x, y) pixel within this image."""
        gx, gy = global_px(lat, lon, self.zoom)
        return gx - self.left, gy - self.top

    def m2px(self, metres):
        return metres / self.mpp


def raw_base():
    """Base raw.githubusercontent.com URL for the current repo + branch, or None.

    Used to build image URLs that render inside GitHub issues.
    """
    try:
        url = subprocess.check_output(["git", "remote", "get-url", "origin"],
                                      text=True, stderr=subprocess.DEVNULL).strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                         text=True, stderr=subprocess.DEVNULL).strip()
        m = re.search(r"github\.com[:/]+([^/]+)/(.+?)(?:\.git)?$", url)
        if not m:
            return None
        return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{branch}"
    except (subprocess.CalledProcessError, OSError):
        return None
