"""
Skyfield ephemeris loader and timescale factory for Al Hilal.

Ephemeris hierarchy
-------------------
de440s.bsp  — 1849–2150, ~17 MB  ← default (covers all practical crescent dates)
de440.bsp   — 1550–2650, ~114 MB
de441.bsp   — −13200–17191, ~3.1 GB (not needed for this project)

IERS EOP data
-------------
Skyfield automatically downloads ``finals2000A.all`` from the IERS data centre
on first use of ``loader.timescale()`` and caches it in the ephemeris directory.
This provides UT1−UTC (ΔT component) and polar-motion parameters.

If the IERS server is unavailable, Skyfield falls back to its built-in
short table.  This is logged as a WARNING so callers can see it.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

import skyfield  # type: ignore[import-untyped]
from skyfield.api import Loader  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Absolute path: repo-root/data/ephemeris/
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
EPHEMERIS_DIR: Final[Path] = _REPO_ROOT / "data" / "ephemeris"

DEFAULT_EPHEMERIS: Final[str] = "de440s.bsp"
SUPPORTED_EPHEMERIDES: Final[frozenset[str]] = frozenset(
    {"de440s.bsp", "de440.bsp", "de441.bsp"}
)

# Module-level caches to avoid re-loading on every call
_eph_cache: dict[str, object] = {}
_ts_cache: dict[str, object] = {}


def get_ephemeris(name: str = DEFAULT_EPHEMERIS) -> object:
    """Return a cached Skyfield ephemeris (Kernel) object.

    Downloads the BSP file from the JPL/NAIF server if not already cached
    on disk.  The file is stored in ``data/ephemeris/``.

    Parameters
    ----------
    name:
        Filename of the ephemeris, e.g. ``"de440s.bsp"``.

    Returns
    -------
    skyfield.data.mpc.SpiceKernel
        The loaded ephemeris object, ready for body lookup via ``eph['Moon']``.

    Raises
    ------
    ValueError
        If *name* is not in :data:`SUPPORTED_EPHEMERIDES`.
    OSError
        If the file cannot be downloaded and is not cached locally.
    """
    if name not in SUPPORTED_EPHEMERIDES:
        raise ValueError(
            f"Unsupported ephemeris {name!r}. "
            f"Choose from: {sorted(SUPPORTED_EPHEMERIDES)}"
        )

    if name not in _eph_cache:
        EPHEMERIS_DIR.mkdir(parents=True, exist_ok=True)
        loader = Loader(str(EPHEMERIS_DIR))
        logger.info("Loading ephemeris %s (may download ~17 MB on first run)", name)
        _eph_cache[name] = loader(name)
        logger.info("Ephemeris %s loaded successfully", name)

    return _eph_cache[name]


def get_timescale(ephemeris_dir: Path | None = None) -> object:
    """Return a Skyfield Timescale with IERS EOP corrections loaded.

    Skyfield fetches ``finals2000A.all`` from the IERS data centre on
    the first call and caches the file in the ephemeris directory.
    Subsequent calls use the cached version.

    The timescale provides:
    - UTC ↔ TT conversion (using IERS ΔAT = TAI − UTC tables)
    - UT1 ↔ UTC correction (from IERS finals2000A ΔUT1 column)
    - Polar motion parameters (xp, yp)

    Parameters
    ----------
    ephemeris_dir:
        Override the directory for IERS cache files.  Defaults to
        :data:`EPHEMERIS_DIR`.

    Returns
    -------
    skyfield.timelib.Timescale
    """
    dir_ = ephemeris_dir or EPHEMERIS_DIR
    key = str(dir_)
    if key not in _ts_cache:
        dir_.mkdir(parents=True, exist_ok=True)
        loader = Loader(str(dir_))
        try:
            ts = loader.timescale()
            logger.info("Timescale loaded with IERS EOP data from %s", dir_)
        except Exception as exc:
            logger.warning(
                "Could not load IERS EOP data (%s); using built-in ΔT table. "
                "ΔT accuracy may be reduced by up to ~1 s.",
                exc,
            )
            from skyfield.api import load as _load  # type: ignore[import-untyped]
            ts = _load.timescale(builtin=True)
        _ts_cache[key] = ts
    return _ts_cache[key]


def skyfield_version() -> str:
    """Return the installed Skyfield version string."""
    return str(skyfield.__version__)


def clear_cache() -> None:
    """Flush module-level caches (useful in testing)."""
    _eph_cache.clear()
    _ts_cache.clear()
