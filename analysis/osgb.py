"""Convert OSGB36 easting/northing (the grid used by the SVDLS dataset) to
WGS84 latitude/longitude (the system used by Google Maps, drone apps, etc.).

Uses the standard Ordnance Survey reverse projection followed by a Helmert
transformation. Accuracy is ~5 m, which is ample for eyeballing a site on a
satellite map. No third-party libraries required.
"""

import math


def _en_to_latlon(E, N, a, b):
    """Reverse Transverse Mercator projection onto the Airy 1830 ellipsoid."""
    F0 = 0.9996012717
    lat0 = math.radians(49)
    lon0 = math.radians(-2)
    N0, E0 = -100000.0, 400000.0
    e2 = 1 - (b * b) / (a * a)
    n = (a - b) / (a + b)

    lat = lat0
    M = 0.0
    while abs(N - N0 - M) >= 0.00001:
        lat = (N - N0 - M) / (a * F0) + lat
        Ma = (1 + n + (5 / 4) * n * n + (5 / 4) * n ** 3) * (lat - lat0)
        Mb = (3 * n + 3 * n * n + (21 / 8) * n ** 3) * math.sin(lat - lat0) * math.cos(lat + lat0)
        Mc = ((15 / 8) * n * n + (15 / 8) * n ** 3) * math.sin(2 * (lat - lat0)) * math.cos(2 * (lat + lat0))
        Md = (35 / 24) * n ** 3 * math.sin(3 * (lat - lat0)) * math.cos(3 * (lat + lat0))
        M = b * F0 * (Ma - Mb + Mc - Md)

    sl = math.sin(lat)
    nu = a * F0 / math.sqrt(1 - e2 * sl * sl)
    rho = a * F0 * (1 - e2) / (1 - e2 * sl * sl) ** 1.5
    eta2 = nu / rho - 1
    tl = math.tan(lat)
    sec = 1 / math.cos(lat)

    VII = tl / (2 * rho * nu)
    VIII = tl / (24 * rho * nu ** 3) * (5 + 3 * tl * tl + eta2 - 9 * tl * tl * eta2)
    IX = tl / (720 * rho * nu ** 5) * (61 + 90 * tl * tl + 45 * tl ** 4)
    X = sec / nu
    XI = sec / (6 * nu ** 3) * (nu / rho + 2 * tl * tl)
    XII = sec / (120 * nu ** 5) * (5 + 28 * tl * tl + 24 * tl ** 4)

    d = E - E0
    lat_ = lat - VII * d ** 2 + VIII * d ** 4 - IX * d ** 6
    lon_ = lon0 + X * d - XI * d ** 3 + XII * d ** 5
    return lat_, lon_


def _helmert_osgb36_to_wgs84(lat, lon):
    """Datum shift from OSGB36 (Airy 1830) to WGS84 (GRS80)."""
    a = 6377563.396
    b = 6356256.909
    e2 = 1 - (b * b) / (a * a)
    sl, cl = math.sin(lat), math.cos(lat)
    nu = a / math.sqrt(1 - e2 * sl * sl)

    x = nu * cl * math.cos(lon)
    y = nu * cl * math.sin(lon)
    z = (1 - e2) * nu * sl

    tx, ty, tz = 446.448, -125.157, 542.060
    rx = math.radians(0.1502 / 3600)
    ry = math.radians(0.2470 / 3600)
    rz = math.radians(0.8421 / 3600)
    s = -20.4894e-6

    x2 = tx + x * (1 + s) + (-rz) * y + ry * z
    y2 = ty + rz * x + y * (1 + s) + (-rx) * z
    z2 = tz + (-ry) * x + rx * y + z * (1 + s)

    a2, b2 = 6378137.0, 6356752.3142
    e22 = 1 - (b2 * b2) / (a2 * a2)
    p = math.sqrt(x2 * x2 + y2 * y2)
    latn = math.atan2(z2, p * (1 - e22))
    latold = 2 * math.pi
    while abs(latn - latold) > 1e-11:
        latold = latn
        nu2 = a2 / math.sqrt(1 - e22 * math.sin(latn) ** 2)
        latn = math.atan2(z2 + e22 * nu2 * math.sin(latn), p)
    lonn = math.atan2(y2, x2)
    return math.degrees(latn), math.degrees(lonn)


def osgb36_to_wgs84(easting, northing):
    """Return (lat, lon) in WGS84 decimal degrees for an OSGB36 E/N pair."""
    lat, lon = _en_to_latlon(easting, northing, 6377563.396, 6356256.909)
    return _helmert_osgb36_to_wgs84(lat, lon)
