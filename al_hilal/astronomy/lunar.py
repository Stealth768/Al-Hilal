"""
Main lunar-observation computation for Al Hilal.

Entry point
-----------
``compute_lunar_observation(observer, date, conditions)``
    → :class:`~al_hilal.astronomy.models.LunarObservationData`

This function:
1. Finds the conjunction (new moon) before the observation evening.
2. Computes sunset time for the observer on *date*.
3. Evaluates all crescent parameters at the moment of sunset.
4. Finds moonset after sunset (if any).
5. Evaluates position at best-time (midpoint sunset–moonset).

All Skyfield calls use topocentric, refraction-corrected positions
(``apparent().altaz(temperature_C=..., pressure_mbar=...)``).

References
----------
Yallop (1997) NAO TN 69 — ARCL, ARCV, DAZ, W conventions.
Meeus (1998) Astronomical Algorithms Ch. 49 — illuminated fraction.
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from al_hilal.astronomy.ephemeris import (
    DEFAULT_EPHEMERIS,
    get_ephemeris,
    get_timescale,
    skyfield_version,
)
from al_hilal.astronomy.models import (
    AtmosphericConditions,
    BodyPosition,
    DEFAULT_CONDITIONS,
    DeltaTRecord,
    LunarObservationData,
    ObserverLocation,
)
from al_hilal.astronomy.time_utils import get_delta_t, utc_now

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _skyfield_topos(loc: ObserverLocation) -> object:
    """Build a Skyfield GeographicPosition (topos) from an :class:`ObserverLocation`."""
    from skyfield.api import wgs84  # type: ignore[import-untyped]

    return wgs84.latlon(loc.latitude, loc.longitude, loc.elevation)


def _skyfield_observer(eph: object, loc: ObserverLocation) -> object:
    """Build a Skyfield topocentric observer (earth + topos) from an :class:`ObserverLocation`."""
    earth = eph["Earth"]  # type: ignore[index]
    topos = _skyfield_topos(loc)
    return earth + topos


def _body_position(
    observer_sf: object,
    body: object,
    t_sky: object,
    conditions: AtmosphericConditions,
) -> BodyPosition:
    """Return topocentric, refraction-corrected alt/az/distance for a body."""
    astrometric = observer_sf.at(t_sky).observe(body)  # type: ignore[attr-defined]
    apparent = astrometric.apparent()
    alt, az, dist = apparent.altaz(  # type: ignore[attr-defined]
        temperature_C=conditions.temperature_c,
        pressure_mbar=conditions.pressure_hPa,
    )
    return BodyPosition(
        altitude_deg=float(alt.degrees),  # type: ignore[attr-defined]
        azimuth_deg=float(az.degrees),    # type: ignore[attr-defined]
        distance_km=float(dist.km),       # type: ignore[attr-defined]
    )


def _find_conjunction(ts: object, eph: object, before_utc: datetime) -> datetime:
    """Find the most recent new moon strictly before *before_utc* (UTC).

    Searches a 35-day window to guarantee at most one full lunation.

    Returns
    -------
    datetime
        UTC-aware datetime of the conjunction.

    Raises
    ------
    RuntimeError
        If no new moon is found in the search window.
    """
    from skyfield import almanac  # type: ignore[import-untyped]

    t1 = ts.from_datetime(before_utc)  # type: ignore[attr-defined]
    t0 = ts.from_datetime(before_utc - timedelta(days=35))  # type: ignore[attr-defined]

    times, phases = almanac.find_discrete(t0, t1, almanac.moon_phases(eph))
    # phase 0 = new moon
    new_moons = [t for t, p in zip(times, phases) if p == 0]

    if not new_moons:
        raise RuntimeError(
            f"No new moon found in the 35 days before {before_utc.isoformat()}"
        )
    return new_moons[-1].utc_datetime()  # type: ignore[attr-defined]


def _find_event_time(
    ts: object,
    eph: object,
    topos: object,
    body: object,
    date_utc: date,
    event_type: int,  # 1=rising, 0=setting
    search_hours_after_midnight: tuple[int, int] = (0, 23),
) -> Optional[datetime]:
    """Find the first rise (1) or set (0) of *body* on *date_utc* UTC.

    Parameters
    ----------
    search_hours_after_midnight:
        (start_hour, end_hour) of the UTC search window on *date_utc*.
        Default covers the whole day.

    Returns
    -------
    datetime or None
        UTC-aware datetime, or ``None`` if the body doesn't rise/set that day.
    """
    from skyfield import almanac  # type: ignore[import-untyped]

    h0, h1 = search_hours_after_midnight
    t0 = ts.utc(date_utc.year, date_utc.month, date_utc.day, h0)  # type: ignore[attr-defined]
    t1 = ts.utc(date_utc.year, date_utc.month, date_utc.day, h1, 59, 59)  # type: ignore[attr-defined]

    f = almanac.risings_and_settings(eph, body, topos)  # type: ignore[attr-defined]
    times, events = almanac.find_discrete(t0, t1, f)

    for t, e in zip(times, events):
        if int(e) == event_type:
            return t.utc_datetime()  # type: ignore[attr-defined]
    return None


def _geocentric_elongation(
    eph: object, ts: object, t_sky: object
) -> float:
    """Geocentric elongation Sun–Moon in degrees at Skyfield time *t_sky*."""
    earth = eph["Earth"]  # type: ignore[index]
    sun = eph["Sun"]      # type: ignore[index]
    moon = eph["Moon"]    # type: ignore[index]

    sun_astrometric = earth.at(t_sky).observe(sun).apparent()  # type: ignore[attr-defined]
    moon_astrometric = earth.at(t_sky).observe(moon).apparent()  # type: ignore[attr-defined]

    sep = sun_astrometric.separation_from(moon_astrometric)  # type: ignore[attr-defined]
    return float(sep.degrees)  # type: ignore[attr-defined]


def _illuminated_fraction(eph: object, ts: object, t_sky: object) -> float:
    """Illuminated fraction of the Moon (0–100 %) at Skyfield time *t_sky*.

    Uses the phase angle formula (Meeus, Ch. 48):
        k = (1 + cos(i)) / 2
    where i is the geocentric phase angle (supplement of elongation).
    """
    arcl_deg = _geocentric_elongation(eph, ts, t_sky)
    # Phase angle i = angular separation between observer-Moon-Sun
    # At elongation ARCL, phase angle ≈ 180° − ARCL (small parallax approx.)
    # For higher accuracy, compute from the actual geometry:
    earth = eph["Earth"]   # type: ignore[index]
    sun = eph["Sun"]       # type: ignore[index]
    moon = eph["Moon"]     # type: ignore[index]

    e_pos = earth.at(t_sky)  # type: ignore[attr-defined]
    sun_from_earth = e_pos.observe(sun).apparent()
    moon_from_earth = e_pos.observe(moon).apparent()

    # Phase angle = angle at Moon between Earth-direction and Sun-direction
    # We approximate via elongation (error < 0.01 %)
    i_deg = 180.0 - arcl_deg
    k = (1.0 + math.cos(math.radians(i_deg))) / 2.0
    return round(k * 100.0, 4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_lunar_observation(
    observer: ObserverLocation,
    observation_date: date,
    conditions: AtmosphericConditions = DEFAULT_CONDITIONS,
    ephemeris_name: str = DEFAULT_EPHEMERIS,
) -> LunarObservationData:
    """Compute all crescent-observation quantities for one observer on one evening.

    This is the primary entry point for Milestone 1.

    Parameters
    ----------
    observer:
        Geodetic observer position (WGS-84).
    observation_date:
        The **Gregorian calendar date** of the observation evening.
        The function looks for sunset on this date (UTC) and evaluates
        all crescent parameters at that sunset moment.
    conditions:
        Atmospheric conditions for refraction.  Default: 10 °C / 1010 hPa
        (fixed standard for reproducible backtests).
    ephemeris_name:
        Which JPL ephemeris to use.  Default: ``"de440s.bsp"``.

    Returns
    -------
    LunarObservationData
        All crescent parameters with provenance.

    Notes
    -----
    - ARCL is **geocentric** (standard Yallop/Odeh convention).
    - ARCV and DAZ are **topocentric**, refraction-corrected.
    - Moonset is the first moonset **after** sunset on *observation_date*.
      If none exists (moon sets before sunset), ``moonset_utc`` is None
      and ``lag_time_minutes`` is None.
    """
    warnings: list[str] = []
    ts = get_timescale()
    eph = get_ephemeris(ephemeris_name)

    earth = eph["Earth"]   # type: ignore[index]
    sun = eph["Sun"]       # type: ignore[index]
    moon = eph["Moon"]     # type: ignore[index]

    topos = _skyfield_topos(observer)
    observer_sf = earth + topos

    # ── 1. Sunset on observation_date ─────────────────────────────────────
    sunset_utc = _find_event_time(
        ts, eph, topos, sun, observation_date,
        event_type=0,          # 0 = setting
        search_hours_after_midnight=(6, 23),   # don't catch early-morning pseudo-sunsets
    )
    if sunset_utc is None:
        raise RuntimeError(
            f"No sunset found on {observation_date} for {observer.name or observer}"
        )

    # ── 2. Conjunction (new moon) before sunset ───────────────────────────
    conjunction_utc = _find_conjunction(ts, eph, sunset_utc)
    moon_age_hours = (sunset_utc - conjunction_utc).total_seconds() / 3600.0

    if moon_age_hours < 0:
        warnings.append(
            f"Moon age at sunset is negative ({moon_age_hours:.2f} h): "
            "conjunction is after sunset on this date."
        )

    # ── 3. Positions at sunset ────────────────────────────────────────────
    t_sunset = ts.from_datetime(sunset_utc)  # type: ignore[attr-defined]
    moon_pos = _body_position(observer_sf, moon, t_sunset, conditions)
    sun_pos = _body_position(observer_sf, sun, t_sunset, conditions)

    # ── 4. Crescent parameters ────────────────────────────────────────────
    arcl_deg = _geocentric_elongation(eph, ts, t_sunset)
    arcv_deg = moon_pos.altitude_deg - sun_pos.altitude_deg

    daz_deg = moon_pos.azimuth_deg - sun_pos.azimuth_deg
    # Normalise to (−180, +180]
    if daz_deg > 180.0:
        daz_deg -= 360.0
    elif daz_deg <= -180.0:
        daz_deg += 360.0

    # Crescent width (Yallop approximation — calibrated for the q-criterion)
    from al_hilal.astronomy.topocentric import crescent_width_yallop, moon_semi_diameter_arcmin
    sd_arcmin = moon_semi_diameter_arcmin(moon_pos.distance_km)
    w_arcmin = crescent_width_yallop(arcl_deg, sd_arcmin)

    illumination_pct = _illuminated_fraction(eph, ts, t_sunset)

    # ── 5. Moonset after sunset ───────────────────────────────────────────
    moonset_utc: Optional[datetime] = None
    lag_time_minutes: Optional[float] = None

    # Search from sunset hour onward to catch moonsets close to sunset
    sunset_hour = sunset_utc.hour
    moonset_candidate = _find_event_time(
        ts, eph, topos, moon, observation_date,
        event_type=0,
        search_hours_after_midnight=(sunset_hour, 23),
    )
    if moonset_candidate is None:
        # Try next day (moonset can be after midnight)
        next_day = observation_date + timedelta(days=1)
        moonset_candidate = _find_event_time(
            ts, eph, topos, moon, next_day,
            event_type=0,
            search_hours_after_midnight=(0, 8),
        )

    if moonset_candidate is not None and moonset_candidate > sunset_utc:
        moonset_utc = moonset_candidate
        lag_time_minutes = (moonset_utc - sunset_utc).total_seconds() / 60.0
    elif moonset_candidate is not None:
        # Moonset before sunset — not useful; record lag as negative
        lag_time_minutes = (moonset_candidate - sunset_utc).total_seconds() / 60.0
        warnings.append(
            f"Moonset ({moonset_candidate.isoformat()}) is before sunset "
            f"({sunset_utc.isoformat()}). Crescent not visible this evening."
        )

    # ── 6. Best-time position ─────────────────────────────────────────────
    best_time_utc: Optional[datetime] = None
    best_time_altitude_deg: Optional[float] = None
    best_time_azimuth_deg: Optional[float] = None

    if moonset_utc is not None:
        best_time_utc = sunset_utc + (moonset_utc - sunset_utc) / 2
        t_best = ts.from_datetime(best_time_utc)  # type: ignore[attr-defined]
        moon_best = _body_position(observer_sf, moon, t_best, conditions)
        best_time_altitude_deg = moon_best.altitude_deg
        best_time_azimuth_deg = moon_best.azimuth_deg

    # ── 7. ΔT record ──────────────────────────────────────────────────────
    delta_t_record = get_delta_t(ts, t_sunset, sunset_utc)

    if arcl_deg < 7.0:
        warnings.append(
            f"Elongation {arcl_deg:.2f}° is below the Danjon limit (7°). "
            "Crescent is geometrically impossible regardless of criteria."
        )

    return LunarObservationData(
        observer=observer,
        observation_date_utc=datetime(
            observation_date.year, observation_date.month, observation_date.day,
            tzinfo=timezone.utc,
        ),
        conditions=conditions,
        conjunction_utc=conjunction_utc,
        moon_age_at_sunset_hours=moon_age_hours,
        sunset_utc=sunset_utc,
        moonset_utc=moonset_utc,
        lag_time_minutes=lag_time_minutes,
        moon_at_sunset=moon_pos,
        sun_at_sunset=sun_pos,
        arcl_deg=arcl_deg,
        arcv_deg=arcv_deg,
        daz_deg=daz_deg,
        w_arcmin=w_arcmin,
        illumination_pct=illumination_pct,
        best_time_utc=best_time_utc,
        best_time_altitude_deg=best_time_altitude_deg,
        best_time_azimuth_deg=best_time_azimuth_deg,
        delta_t=delta_t_record,
        ephemeris_name=ephemeris_name,
        computed_at_utc=utc_now(),
        skyfield_version=skyfield_version(),
        warnings=warnings,
    )
