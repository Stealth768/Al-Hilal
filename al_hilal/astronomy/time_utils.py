"""
Time-scale utilities for Al Hilal.

ΔT = TT − UT1 policy (per user spec)
--------------------------------------
1. IERS ``finals2000A.all`` table  →  authoritative, uncertainty ~0.01 s.
   Skyfield reads this automatically via :func:`get_timescale`.
2. USNO predictions  →  authoritative for ~2 years ahead.
3. Espenak & Meeus (2006) / Morrison & Stephenson (2004) polynomial  →
   used when beyond IERS tables or for deep historical/future dates.
4. Skyfield built-in table  →  fallback when network unavailable.

References
----------
Espenak, F., & Meeus, J. (2006). Five Millennium Canon of Solar Eclipses: -1999 to +3000.
    NASA Technical Publication TP-2006-214141.
Morrison, L.V., & Stephenson, F.R. (2004). Historical values of the Earth's clock error
    ΔT and the calculation of eclipses. J. Hist. Astron. 35, 327–336.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from al_hilal.astronomy.models import DeltaTRecord


def delta_t_polynomial(year: float) -> float:
    """ΔT = TT − UT1 in seconds using Espenak & Meeus (2006) / Morrison & Stephenson (2004).

    Parameters
    ----------
    year:
        Decimal year (e.g. 2024.5).

    Returns
    -------
    float
        Estimated ΔT in seconds.
    """
    y = year

    if 2005.0 <= y < 2050.0:
        t = y - 2000.0
        return 62.92 + 0.32217 * t + 0.005589 * t**2
    elif 2000.0 <= y < 2005.0:
        t = y - 2000.0
        return 63.86 + 0.3345 * t - 0.060374 * t**2 + 0.0017275 * t**3 + 0.000651814 * t**4
    elif 1986.0 <= y < 2000.0:
        t = y - 2000.0
        return 63.86 + 0.3345 * t - 0.060374 * t**2 + 0.0017275 * t**3 + 0.000651814 * t**4
    elif 2050.0 <= y < 2150.0:
        u = (y - 1820.0) / 100.0
        return -20.0 + 32.0 * u**2 - 0.5628 * (2150.0 - y)
    elif y >= 2150.0:
        u = (y - 1820.0) / 100.0
        return -20.0 + 32.0 * u**2
    else:
        # Pre-1986 historical approximation (Morrison & Stephenson 2004)
        u = (y - 1820.0) / 100.0
        return -20.0 + 32.0 * u**2


# Alias for backward compatibility
delta_t_morrison_stephenson = delta_t_polynomial


def get_delta_t(ts: object, t_sky: object, dt_utc: datetime) -> DeltaTRecord:
    """Retrieve ΔT = TT − UT1 for a Skyfield Time object."""
    try:
        delta_t_s = float(t_sky.delta_t)  # type: ignore[attr-defined]
        year = dt_utc.year + (dt_utc.timetuple().tm_yday - 1) / 365.25
        try:
            cutoff = ts.delta_t_recent_cutoff  # type: ignore[attr-defined]
            if year <= cutoff:
                source = "IERS_EOP"
                uncertainty = 0.1
            else:
                source = "USNO_PREDICT"
                uncertainty = 2.0
        except AttributeError:
            source = "BUILTIN"
            uncertainty = 5.0
        return DeltaTRecord(
            value_seconds=delta_t_s,
            source=source,
            uncertainty_seconds=uncertainty,
        )
    except Exception:
        year = dt_utc.year + (dt_utc.timetuple().tm_yday - 1) / 365.25
        return DeltaTRecord(
            value_seconds=delta_t_polynomial(year),
            source="MORRISON_STEPHENSON",
            uncertainty_seconds=20.0,
        )


def decimal_year(dt: datetime) -> float:
    """Convert a UTC datetime to a decimal year."""
    import calendar

    year = dt.year
    days_in_year = 366 if calendar.isleap(year) else 365
    day_of_year = dt.timetuple().tm_yday
    frac = day_of_year - 1 + dt.hour / 24 + dt.minute / 1440 + dt.second / 86400
    return year + frac / days_in_year


def utc_now() -> datetime:
    """Return current time as a UTC-aware datetime."""
    return datetime.now(tz=timezone.utc)
