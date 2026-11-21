"""
Atmospheric refraction and topocentric parallax helpers.

Refraction models
-----------------
Bennett (1982):
    R = cot(h_app + 7.31 / (h_app + 4.4))  [arcminutes]

where h_app is the **apparent** (observed) altitude in degrees.
This formula is accurate to ±0.07' for altitudes down to 0°.

Sæmundsson (1986):
    R = 1.02 × cot(h_true + 10.3 / (h_true + 5.11))  [arcminutes]

where h_true is the **geometric** (true) altitude in degrees.

Temperature and pressure corrections (Meeus Ch. 16):
    R_corrected = R × (P / 1010) × (283 / (273 + T))

where P is pressure in hPa and T is temperature in °C.

Crescent width
--------------
Yallop (1997) NAO TN 69:
    W = SD × (1 − cos(ARCL))  [arcminutes]

where SD is the Moon's semi-diameter in arcminutes (~15.5') and
ARCL is the geocentric elongation Sun–Moon in degrees.

References
----------
Bennett, G.G. (1982). "The Calculation of Astronomical Refraction in
    Marine Navigation." J. Navig. 35(2), 255–259.
Sæmundsson, Þ. (1986). "Astronomical Refraction." Sky & Telescope 72, 70.
Meeus, J. (1998). Astronomical Algorithms, 2nd ed. Ch. 16.
Yallop, B.D. (1997). NAO Technical Note No. 69.
"""

from __future__ import annotations

import math


def refraction_bennett(
    apparent_altitude_deg: float,
    temperature_c: float = 10.0,
    pressure_hPa: float = 1010.0,
) -> float:
    """Atmospheric refraction from APPARENT altitude using Bennett (1982).

    Parameters
    ----------
    apparent_altitude_deg:
        Apparent (observed) altitude of the body in degrees.
    temperature_c:
        Air temperature in °C. Default: 10 °C.
    pressure_hPa:
        Atmospheric pressure in hPa. Default: 1010 hPa.

    Returns
    -------
    float
        Refraction correction R in **arcminutes**.
        True altitude = apparent altitude − R / 60.
    """
    h = apparent_altitude_deg
    if h < -1.0:
        return 0.0

    arg_deg = h + 7.31 / (h + 4.4)
    if arg_deg >= 90.0:
        return 0.0

    arg_rad = math.radians(arg_deg)
    R_arcmin = 1.0 / math.tan(arg_rad)
    R_arcmin = max(0.0, min(R_arcmin, 40.0))

    # Temperature and pressure correction (Meeus Ch. 16)
    R_corrected = R_arcmin * (pressure_hPa / 1010.0) * (283.0 / (273.0 + temperature_c))
    return R_corrected


def refraction_saemundsson(
    true_altitude_deg: float,
    temperature_c: float = 10.0,
    pressure_hPa: float = 1010.0,
) -> float:
    """Atmospheric refraction from TRUE (geometric) altitude using Sæmundsson (1986).

    Parameters
    ----------
    true_altitude_deg:
        True (geometric) altitude of the body in degrees.
    temperature_c:
        Air temperature in °C. Default: 10 °C.
    pressure_hPa:
        Atmospheric pressure in hPa. Default: 1010 hPa.

    Returns
    -------
    float
        Refraction correction R in **arcminutes**.
        Apparent altitude = true altitude + R / 60.
    """
    h = true_altitude_deg
    if h < -5.0:
        return 0.0

    arg_deg = h + 10.3 / (h + 5.11)
    if arg_deg >= 90.0:
        return 0.0

    arg_rad = math.radians(arg_deg)
    R_arcmin = 1.02 / math.tan(arg_rad)
    R_arcmin = max(0.0, min(R_arcmin, 40.0))

    R_corrected = R_arcmin * (pressure_hPa / 1010.0) * (283.0 / (273.0 + temperature_c))
    return R_corrected


def apparent_to_geometric_altitude(
    apparent_alt_deg: float,
    temperature_c: float = 10.0,
    pressure_hPa: float = 1010.0,
) -> float:
    """Convert apparent altitude to geometric (true) altitude in degrees."""
    R_arcmin = refraction_bennett(apparent_alt_deg, temperature_c, pressure_hPa)
    return apparent_alt_deg - R_arcmin / 60.0


def geometric_to_apparent_altitude(
    geometric_alt_deg: float,
    temperature_c: float = 10.0,
    pressure_hPa: float = 1010.0,
) -> float:
    """Convert geometric (true) altitude to apparent altitude in degrees."""
    R_arcmin = refraction_saemundsson(geometric_alt_deg, temperature_c, pressure_hPa)
    return geometric_alt_deg + R_arcmin / 60.0


def moon_horizontal_parallax_deg(distance_km: float) -> float:
    """Moon's equatorial horizontal parallax in degrees.

    HP = arcsin(R_earth / distance)
    """
    R_EARTH_KM = 6378.137  # WGS-84 equatorial radius
    return math.degrees(math.asin(R_EARTH_KM / distance_km))


def moon_semi_diameter_arcmin(distance_km: float) -> float:
    """Moon's topocentric/geocentric semi-diameter in arcminutes.

    SD = arcsin(R_moon / distance) × (180 / π) × 60
    where R_moon = 1737.4 km (IAU defined mean radius).
    """
    R_MOON_KM = 1737.4
    return math.degrees(math.asin(R_MOON_KM / distance_km)) * 60.0


def crescent_width_yallop(arcl_deg: float, sd_arcmin: float = 15.5) -> float:
    """Crescent width (W) in arcminutes using Yallop (1997) NAO TN 69.

    W = SD × (1 − cos(ARCL))

    Parameters
    ----------
    arcl_deg:
        Geocentric elongation Sun–Moon in degrees (ARCL).
    sd_arcmin:
        Moon's semi-diameter in arcminutes (default 15.5').

    Returns
    -------
    float
        Crescent width W in **arcminutes**.
    """
    arcl_rad = math.radians(arcl_deg)
    return sd_arcmin * (1.0 - math.cos(arcl_rad))
