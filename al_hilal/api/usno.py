"""USNO Astronomical Applications API wrapper.

Used as a secondary cross-check for rise/set times.
API documentation: https://aa.usno.navy.mil/data/api
No API key required.

Endpoints used
--------------
/rstt/oneday   — Rise, Set, and Transit Times for the Sun and Moon
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

import httpx

log = logging.getLogger(__name__)

USNO_BASE = "https://aa.usno.navy.mil/api"
_TIMEOUT = 20.0


def get_riseset(
    obs_date: date,
    lat_deg: float,
    lon_deg: float,
    tz_offset_h: float = 0.0,
) -> dict[str, Any]:
    """Call USNO /rstt/oneday and return the parsed JSON body.

    Parameters
    ----------
    obs_date:
        Gregorian date of interest.
    lat_deg, lon_deg:
        Observer coordinates (decimal degrees).
    tz_offset_h:
        UTC offset in hours for the observer (USNO uses this for local time
        display only; does not affect UTC rise/set times).

    Returns
    -------
    dict
        Full USNO JSON response.

    Raises
    ------
    httpx.HTTPError
        On network or HTTP failure.
    RuntimeError
        If the USNO API returns an error field.
    """
    params = {
        "date": obs_date.strftime("%Y-%m-%d"),
        "coords": f"{lat_deg:.4f},{lon_deg:.4f}",
        "tz": f"{tz_offset_h:.1f}",
    }
    url = f"{USNO_BASE}/rstt/oneday"
    log.debug("Querying USNO: %s params=%s", url, params)

    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()

    payload = resp.json()
    if "error" in payload:
        raise RuntimeError(f"USNO API error: {payload['error']}")
    return payload


def extract_sunset_utc(
    usno_response: dict[str, Any],
    obs_date: date,
    tz_offset_h: float = 0.0,
) -> Optional[datetime]:
    """Extract sunset UTC time from a USNO /rstt/oneday response.

    The USNO API returns times in local time (with the given tz_offset_h).
    We convert back to UTC.

    Returns ``None`` if the sun does not set on that date (polar region).
    """
    return _extract_event_utc(usno_response, obs_date, tz_offset_h, "set", "Sun")


def extract_moonset_utc(
    usno_response: dict[str, Any],
    obs_date: date,
    tz_offset_h: float = 0.0,
) -> Optional[datetime]:
    """Extract moonset UTC time from a USNO /rstt/oneday response."""
    return _extract_event_utc(usno_response, obs_date, tz_offset_h, "set", "Moon")


def _extract_event_utc(
    payload: dict[str, Any],
    obs_date: date,
    tz_offset_h: float,
    event: str,
    body: str,
) -> Optional[datetime]:
    """Parse the USNO response structure to find the time of an event.

    USNO response structure (simplified)::

        {
          "sundata": [{"phen": "Set", "time": "17:35"}],
          "moondata": [{"phen": "Set", "time": "19:12"}],
          ...
        }
    """
    body_key = "sundata" if body == "Sun" else "moondata"
    events = payload.get(body_key, [])

    for ev in events:
        phen = str(ev.get("phen", "")).lower()
        if event.lower() in phen:
            time_str: str = ev.get("time", "")
            if not time_str:
                return None
            try:
                h, m = map(int, time_str.strip().split(":"))
            except ValueError:
                log.warning("Could not parse USNO time %r", time_str)
                return None

            # Local time → UTC
            local_minutes = h * 60 + m
            utc_minutes = local_minutes - int(tz_offset_h * 60)
            utc_h = utc_minutes // 60
            utc_m = utc_minutes % 60

            return datetime(
                obs_date.year, obs_date.month, obs_date.day,
                utc_h, utc_m, tzinfo=timezone.utc,
            )
    return None
