"""
NASA JPL Horizons REST API wrapper for Al Hilal.

Used **only** as a cross-check against Skyfield results, not as a
primary computation source.

API documentation: https://ssd.jpl.nasa.gov/doc/horizons_api.html
No API key required.  Rate limit: approximately 1 request/second.

Quantities requested
--------------------
4   — Apparent altitude and azimuth (refracted, topocentric)
10  — Illuminated fraction
24  — Sun-target elongation (geocentric)
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

log = logging.getLogger(__name__)

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
_LAST_REQUEST_TIME: float = 0.0
_MIN_INTERVAL_S: float = 1.1  # honour rate limit


def _rate_limit() -> None:
    global _LAST_REQUEST_TIME
    elapsed = time.monotonic() - _LAST_REQUEST_TIME
    if elapsed < _MIN_INTERVAL_S:
        time.sleep(_MIN_INTERVAL_S - elapsed)
    _LAST_REQUEST_TIME = time.monotonic()


def query_body_at_time(
    body_id: str,
    lat_deg: float,
    lon_deg: float,
    elevation_km: float,
    time_utc: datetime,
    quantities: str = "4,10,24",
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    """Query JPL Horizons for topocentric quantities at a single UTC instant.

    Parameters
    ----------
    body_id:
        Horizons target body ID string: ``"301"`` (Moon), ``"10"`` (Sun).
    lat_deg, lon_deg, elevation_km:
        Observer geodetic position.  Longitude: positive East.
    time_utc:
        Observation epoch (UTC-aware datetime).
    quantities:
        Comma-separated Horizons quantity codes.
    timeout_s:
        HTTP request timeout.

    Returns
    -------
    dict
        Parsed CSV rows as ``{column_name: value}`` for the single epoch,
        plus ``_raw`` key with the full API response text.

    Raises
    ------
    httpx.HTTPError
        On network or HTTP error.
    RuntimeError
        If the Horizons response cannot be parsed.
    """
    # Horizons wants a 1-minute window around the target time
    t_start = time_utc - timedelta(minutes=1)
    t_stop = time_utc + timedelta(minutes=1)

    def _fmt(dt: datetime) -> str:
        return dt.strftime("%Y-%b-%d %H:%M:%S")

    # Build SITE_COORD: "lon,lat,elevation_km" (Horizons convention: lon first)
    site_coord = f"{lon_deg:.4f},{lat_deg:.4f},{elevation_km:.3f}"

    params = {
        "format": "json",
        "COMMAND": f"'{body_id}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "coord@399",
        "SITE_COORD": f"'{site_coord}'",
        "START_TIME": f"'{_fmt(t_start)}'",
        "STOP_TIME": f"'{_fmt(t_stop)}'",
        "STEP_SIZE": "'1 m'",
        "QUANTITIES": f"'{quantities}'",
        "CAL_FORMAT": "CAL",
        "TIME_DIGITS": "SECONDS",
        "ANG_FORMAT": "DEG",
        "APPARENT": "REFRACTED",
        "CSV_FORMAT": "YES",
        "SKIP_DAYLT": "NO",
    }

    _rate_limit()
    log.debug("Querying Horizons: body=%s loc=(%.4f,%.4f) t=%s", body_id, lat_deg, lon_deg, _fmt(time_utc))

    with httpx.Client(timeout=timeout_s) as client:
        resp = client.get(HORIZONS_URL, params=params)
        resp.raise_for_status()

    data = resp.json()
    raw_text: str = data.get("result", "")

    if "$$SOE" not in raw_text or "$$EOE" not in raw_text:
        raise RuntimeError(
            f"Horizons response has no ephemeris block ($$SOE/$$EOE). "
            f"Body={body_id}. Raw snippet: {raw_text[:300]}"
        )

    return _parse_horizons_csv(raw_text, time_utc)


def _parse_horizons_csv(raw: str, target_utc: datetime) -> dict[str, Any]:
    """Extract the row closest to *target_utc* from a Horizons CSV block."""
    # Extract the block between $$SOE and $$EOE
    soe = raw.index("$$SOE")
    eoe = raw.index("$$EOE")
    block = raw[soe + 5 : eoe].strip()

    # The header line is before $$SOE, skipping any separator lines of asterisks
    pre_soe = raw[:soe].rstrip()
    header_candidates = [
        l.strip()
        for l in pre_soe.splitlines()
        if l.strip() and not l.strip().startswith("*") and not l.strip().startswith("$")
    ]
    if not header_candidates:
        raise RuntimeError("Could not find CSV header line before $$SOE in Horizons response.")
    header_line = header_candidates[-1]
    headers = [h.strip() for h in header_line.split(",")]

    rows = []
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < len(headers):
            continue
        rows.append(dict(zip(headers, parts)))

    if not rows:
        raise RuntimeError("No data rows found in Horizons response.")

    # Pick the row whose timestamp is closest to target_utc
    def _parse_row_time(row: dict[str, str]) -> datetime:
        # Check all possible date column names
        for k in ("Date__(UT)__HR:MN:SC.fff", "Date__(UT)__HR:MN:SC", "Date__(UT)__HR:MN", "Date_(UT)_HR:MN"):
            val = row.get(k)
            if val:
                for fmt in ("%Y-%b-%d %H:%M:%S.%f", "%Y-%b-%d %H:%M:%S", "%Y-%b-%d %H:%M"):
                    try:
                        return datetime.strptime(val.strip(), fmt).replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass
        return target_utc

    best = min(rows, key=lambda r: abs((_parse_row_time(r) - target_utc).total_seconds()))
    best["_raw_response_snippet"] = raw[:200]
    return best


def query_body_rows(
    body_id: str,
    lat_deg: float,
    lon_deg: float,
    elevation_km: float,
    time_utc: datetime,
    quantities: str = "4,10,24",
    timeout_s: float = 30.0,
) -> list[dict[str, Any]]:
    """Query JPL Horizons and return parsed CSV rows for the minute window around time_utc."""
    t_start = time_utc - timedelta(minutes=1)
    t_stop = time_utc + timedelta(minutes=1)

    def _fmt(dt: datetime) -> str:
        return dt.strftime("%Y-%b-%d %H:%M:%S")

    site_coord = f"{lon_deg:.4f},{lat_deg:.4f},{elevation_km:.3f}"

    params = {
        "format": "json",
        "COMMAND": f"'{body_id}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "coord@399",
        "SITE_COORD": f"'{site_coord}'",
        "START_TIME": f"'{_fmt(t_start)}'",
        "STOP_TIME": f"'{_fmt(t_stop)}'",
        "STEP_SIZE": "'1 m'",
        "QUANTITIES": f"'{quantities}'",
        "CAL_FORMAT": "CAL",
        "TIME_DIGITS": "SECONDS",
        "ANG_FORMAT": "DEG",
        "APPARENT": "REFRACTED",
        "CSV_FORMAT": "YES",
        "SKIP_DAYLT": "NO",
    }

    _rate_limit()
    log.debug("Querying Horizons: body=%s loc=(%.4f,%.4f) t=%s", body_id, lat_deg, lon_deg, _fmt(time_utc))

    with httpx.Client(timeout=timeout_s) as client:
        resp = client.get(HORIZONS_URL, params=params)
        resp.raise_for_status()

    data = resp.json()
    raw_text: str = data.get("result", "")

    if "$$SOE" not in raw_text or "$$EOE" not in raw_text:
        raise RuntimeError(
            f"Horizons response has no ephemeris block ($$SOE/$$EOE). "
            f"Body={body_id}. Raw snippet: {raw_text[:300]}"
        )

    soe = raw.index("$$SOE") if (raw := raw_text) else 0
    eoe = raw_text.index("$$EOE")
    block = raw_text[soe + 5 : eoe].strip()

    pre_soe = raw_text[:soe].rstrip()
    header_candidates = [
        l.strip()
        for l in pre_soe.splitlines()
        if l.strip() and not l.strip().startswith("*") and not l.strip().startswith("$")
    ]
    if not header_candidates:
        raise RuntimeError("Could not find CSV header line before $$SOE in Horizons response.")
    header_line = header_candidates[-1]
    headers = [h.strip() for h in header_line.split(",")]

    rows: list[dict[str, Any]] = []
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < len(headers):
            continue
        row_dict = dict(zip(headers, parts))
        rows.append(row_dict)

    if not rows:
        raise RuntimeError("No data rows found in Horizons response.")
    return rows


def _parse_row_datetime(row: dict[str, Any]) -> datetime:
    for k, val in row.items():
        if "date" in k.lower() and val:
            for fmt in ("%Y-%b-%d %H:%M:%S.%f", "%Y-%b-%d %H:%M:%S", "%Y-%b-%d %H:%M"):
                try:
                    return datetime.strptime(str(val).strip(), fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
    raise ValueError(f"Could not parse datetime from row: {row}")


def query_body_at_time(
    body_id: str,
    lat_deg: float,
    lon_deg: float,
    elevation_km: float,
    time_utc: datetime,
    quantities: str = "4,10,24",
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    """Query JPL Horizons for topocentric quantities at a single UTC instant."""
    rows = query_body_rows(
        body_id, lat_deg, lon_deg, elevation_km, time_utc, quantities, timeout_s
    )
    return min(rows, key=lambda r: abs((_parse_row_datetime(r) - time_utc).total_seconds()))


def get_moon_alt_az(
    lat_deg: float,
    lon_deg: float,
    elevation_m: float,
    time_utc: datetime,
) -> tuple[float, float]:
    """Convenience wrapper: return (altitude_deg, azimuth_deg) for the Moon.

    Linearly interpolated to the exact second of ``time_utc`` from Horizons minute rows.
    """
    rows = query_body_rows(
        "301",
        lat_deg,
        lon_deg,
        elevation_m / 1000.0,
        time_utc,
        quantities="4,10,24",
    )

    def _extract_alt_az(row: dict[str, Any]) -> tuple[float, float]:
        alt, az = None, None
        for key, val in row.items():
            k = key.lower()
            if "elev" in k or "alt" in k:
                try:
                    alt = float(val)
                except (ValueError, TypeError):
                    pass
            if "azi" in k or "az" in k:
                try:
                    az = float(val)
                except (ValueError, TypeError):
                    pass
        if alt is None or az is None:
            raise RuntimeError(f"Could not parse alt/az from Horizons row: {row}")
        return alt, az

    # Sort rows by parsed timestamp
    timed_rows = sorted(((_parse_row_datetime(r), r) for r in rows), key=lambda x: x[0])

    # Find the bounding interval [r0, r1] containing time_utc
    r0, r1 = timed_rows[0], timed_rows[-1]
    for i in range(len(timed_rows) - 1):
        if timed_rows[i][0] <= time_utc <= timed_rows[i + 1][0]:
            r0 = timed_rows[i]
            r1 = timed_rows[i + 1]
            break

    dt0 = (time_utc - r0[0]).total_seconds()
    span = (r1[0] - r0[0]).total_seconds()
    alt0, az0 = _extract_alt_az(r0[1])
    alt1, az1 = _extract_alt_az(r1[1])

    if span <= 0 or dt0 <= 0:
        return alt0, az0
    if dt0 >= span:
        return alt1, az1

    frac = dt0 / span
    # Altitude linear interpolation
    alt_interp = alt0 + frac * (alt1 - alt0)
    # Azimuth interpolation with circular wrap
    d_az = (az1 - az0) % 360.0
    if d_az > 180.0:
        d_az -= 360.0
    az_interp = (az0 + frac * d_az) % 360.0

    return alt_interp, az_interp
