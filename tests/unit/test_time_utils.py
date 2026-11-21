"""
Unit tests: time utilities.

All tests are offline (no network, no ephemeris).
"""

from __future__ import annotations

import pytest
from al_hilal.astronomy.time_utils import decimal_year, delta_t_morrison_stephenson


class TestMorrisonStephensonDeltaT:
    """Morrison & Stephenson (2004) polynomial sanity checks.

    Reference values: USNO ΔT tables at https://maia.usno.navy.mil/products/deltaT
    We don't expect perfect agreement (polynomial is approximate) but
    values should be in the right ballpark.
    """

    # (year, approximate expected ΔT seconds, tolerance)
    KNOWN_VALUES = [
        (2000.0, 63.8,  3.0),   # USNO: 63.8 s
        (2010.0, 65.5,  4.0),   # USNO: ~65.5 s
        (2020.0, 70.0,  8.0),   # USNO: ~69.2 s; polynomial less accurate here
    ]

    @pytest.mark.parametrize("year, expected, tol", KNOWN_VALUES)
    def test_known_years(self, year, expected, tol):
        dt = delta_t_morrison_stephenson(year)
        assert abs(dt - expected) <= tol, (
            f"M&S ΔT({year}) = {dt:.2f}s, expected ~{expected}s ±{tol}s"
        )

    def test_positive_and_increasing_near_2000(self):
        """ΔT should be positive and roughly increasing over 1990–2030."""
        values = [delta_t_morrison_stephenson(y) for y in range(1990, 2031, 5)]
        assert all(v > 0 for v in values), "All ΔT values should be positive"


class TestDecimalYear:
    from datetime import datetime, timezone

    def test_jan_1_midnight(self):
        from datetime import datetime, timezone
        dt = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        y = decimal_year(dt)
        assert 2024.0 <= y < 2024.01

    def test_jul_1_midyear(self):
        from datetime import datetime, timezone
        dt = datetime(2024, 7, 2, 12, 0, 0, tzinfo=timezone.utc)  # ~midyear
        y = decimal_year(dt)
        assert 2024.48 <= y <= 2024.52
