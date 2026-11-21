"""
Data models for the Al Hilal astronomy engine.

Design rules:
- All angles in degrees unless a name ends in _rad or doc says otherwise.
- All times are UTC datetime objects (timezone-aware) unless named *_tt or *_ut1.
- All distances in km unless named otherwise.
- Frozen dataclasses are used for inputs (safe to cache/hash).
  Mutable dataclass for output (LunarObservationData) has a ``warnings`` list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ObserverLocation:
    """Geodetic position of an observer on WGS-84.

    Parameters
    ----------
    latitude:
        Decimal degrees, positive = North, negative = South.
    longitude:
        Decimal degrees, positive = East, negative = West.
    elevation:
        Metres above the WGS-84 ellipsoid (not mean sea level).
    name:
        Human-readable label, used in reports.
    timezone:
        IANA timezone string (e.g. ``"Asia/Riyadh"``).  Used only for
        display; all internal computation uses UTC.
    """

    latitude: float
    longitude: float
    elevation: float = 0.0
    name: str = ""
    timezone: str = "UTC"

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"latitude must be in [-90, 90], got {self.latitude}")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"longitude must be in [-180, 180], got {self.longitude}")
        if self.elevation < -500:
            raise ValueError(f"elevation {self.elevation} m is implausibly low")


@dataclass(frozen=True)
class AtmosphericConditions:
    """Standard atmospheric conditions for refraction correction.

    **Default values (10 °C, 1010 hPa) are fixed for reproducible backtests.**
    Live weather values (Open-Meteo) are used only in sensitivity-test mode
    and must not alter the deterministic backtest baseline.

    References
    ----------
    Bennett (1982) — refraction formula used throughout.
    Yallop (1997) NAO TN 69 — states "standard atmosphere" without specifying;
    10 °C / 1010 hPa is the widely-adopted convention in the crescent literature.
    """

    temperature_c: float = 10.0    # degrees Celsius
    pressure_hPa: float = 1010.0   # hectopascals (= millibars)
    humidity_pct: float = 50.0     # relative humidity, 0–100

    def __post_init__(self) -> None:
        if not (-90 <= self.temperature_c <= 60):
            raise ValueError(f"temperature {self.temperature_c} °C out of range")
        if not (800 <= self.pressure_hPa <= 1100):
            raise ValueError(f"pressure {self.pressure_hPa} hPa out of range")


DEFAULT_CONDITIONS = AtmosphericConditions()


# ---------------------------------------------------------------------------
# Output sub-records
# ---------------------------------------------------------------------------


@dataclass
class BodyPosition:
    """Topocentric, refraction-corrected altitude and azimuth of a body."""

    altitude_deg: float    # positive = above horizon
    azimuth_deg: float     # degrees from North, clockwise (0–360)
    distance_km: float     # topocentric distance


@dataclass
class DeltaTRecord:
    """Recorded ΔT = TT − UT1 at a specific epoch.

    Sources (in priority order):
    1. ``IERS_EOP``: IERS finals2000A.all table — authoritative to ~±0.01 s.
    2. ``USNO_PREDICT``: USNO short-term predictions — authoritative ~2 yr ahead.
    3. ``MORRISON_STEPHENSON``: polynomial extrapolation (Morrison & Stephenson
       2004) — used beyond IERS tables or for deep history (pre-1700).
    4. ``BUILTIN``: Skyfield built-in value (fallback).
    """

    value_seconds: float
    source: str  # one of the four strings above
    uncertainty_seconds: float  # estimated 1-sigma


# ---------------------------------------------------------------------------
# Primary output
# ---------------------------------------------------------------------------


@dataclass
class LunarObservationData:
    """Complete crescent-observation dataset for one observer on one evening.

    'Evening' means the sunset that immediately follows (or coincides with)
    the astronomical new moon.  All quantities are evaluated **at the moment
    of sunset** unless the field name indicates otherwise.

    Angles: degrees.  Times: UTC-aware datetime.  Crescent width: arcminutes.
    """

    # ── Inputs (echoed for provenance) ────────────────────────────────────
    observer: ObserverLocation
    observation_date_utc: datetime       # date of the observation evening (UTC)
    conditions: AtmosphericConditions

    # ── Conjunction ───────────────────────────────────────────────────────
    conjunction_utc: datetime            # Exact new moon (geocentric ecliptic lon equal)
    moon_age_at_sunset_hours: float      # Hours elapsed since conjunction at sunset

    # ── Event times (UTC, timezone-aware) ────────────────────────────────
    sunset_utc: datetime
    moonset_utc: Optional[datetime]      # None when moon sets before sunset
    lag_time_minutes: Optional[float]   # moonset − sunset; negative means before sunset

    # ── Positions at sunset (topocentric, refraction-corrected) ───────────
    moon_at_sunset: BodyPosition
    sun_at_sunset: BodyPosition

    # ── Crescent parameters (at sunset) ──────────────────────────────────
    arcl_deg: float          # Geocentric elongation Sun–Moon (great-circle degrees)
    arcv_deg: float          # Arc of Vision = moon alt − sun alt at sunset (topocentric)
    daz_deg: float           # Relative azimuth = moon az − sun az at sunset
    w_arcmin: float          # Crescent width (Yallop approximation, arc-minutes)
    illumination_pct: float  # Illuminated fraction 0–100 %

    # ── Best-time (midpoint sunset–moonset) ──────────────────────────────
    best_time_utc: Optional[datetime]
    best_time_altitude_deg: Optional[float]
    best_time_azimuth_deg: Optional[float]

    # ── Time-system metadata ──────────────────────────────────────────────
    delta_t: DeltaTRecord            # ΔT = TT − UT1 at sunset

    # ── Provenance ────────────────────────────────────────────────────────
    ephemeris_name: str              # e.g. "de440s.bsp"
    computed_at_utc: datetime        # Wall-clock time this object was created
    skyfield_version: str
    warnings: list[str] = field(default_factory=list)

    # ── Derived convenience properties ────────────────────────────────────

    @property
    def crescent_visible_geometrically(self) -> bool:
        """True if lag time > 0 and elongation above Danjon limit (7°)."""
        return (
            self.lag_time_minutes is not None
            and self.lag_time_minutes > 0
            and self.arcl_deg >= 7.0
        )
