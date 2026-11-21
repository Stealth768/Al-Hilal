"""
Unit tests: atmospheric refraction and crescent width.

All tests are offline (no network, no ephemeris download).
Reference values are computed from the Bennett (1982) formula
and cross-checked against Table 16.a in Meeus (1998).

Tolerances
----------
- Refraction values: ±0.05 arcminutes
- Crescent width: ±0.001 arcminutes
"""

from __future__ import annotations

import math

import pytest

from al_hilal.astronomy.topocentric import (
    apparent_to_geometric_altitude,
    crescent_width_yallop,
    geometric_to_apparent_altitude,
    moon_horizontal_parallax_deg,
    moon_semi_diameter_arcmin,
    refraction_bennett,
    refraction_saemundsson,
)


class TestBennettRefraction:
    """Verify Bennett (1982) refraction formula against reference values.

    Formula: R = cot(h_app + 7.31 / (h_app + 4.4)) [arcminutes]
    Reference: Meeus (1998) Table 16.a (standard atmosphere 10°C / 1010 hPa).
    """

    # (apparent_alt_deg, expected_R_arcmin, tolerance)
    REFERENCE_CASES = [
        (90.0, 0.0,    0.01),   # zenith — negligible
        (45.0, 0.995,  0.02),   # cot(45.148°) ≈ 0.995'
        (20.0, 2.705,  0.05),   # cot(20.300°) ≈ 2.705'
        (10.0, 5.39,   0.05),   # cot(10.508°) ≈ 5.39'
        (5.0,  9.88,   0.10),   # cot(5.778°)  ≈ 9.88'
        (1.0,  24.33,  0.20),   # cot(2.354°)  ≈ 24.33'
        (0.0,  34.48,  0.20),   # horizon: cot(1.661°) ≈ 34.48' (Meeus 16.a: 34.5')
    ]

    @pytest.mark.parametrize("h_app, expected, tol", REFERENCE_CASES)
    def test_refraction_standard_atmosphere(self, h_app: float, expected: float, tol: float) -> None:
        """Bennett formula matches Meeus Table 16.a within tolerance."""
        R = refraction_bennett(h_app)
        assert abs(R - expected) <= tol, (
            f"alt={h_app}°: got R={R:.3f}', expected {expected}' ±{tol}'"
        )

    def test_refraction_below_horizon_clipped(self) -> None:
        """Bodies well below the horizon return 0."""
        assert refraction_bennett(-5.0) == 0.0

    def test_temperature_pressure_correction(self) -> None:
        """Warmer, lower-pressure air → less refraction."""
        R_std = refraction_bennett(20.0, 10.0, 1010.0)
        R_warm = refraction_bennett(20.0, 30.0, 1010.0)
        R_low_p = refraction_bennett(20.0, 10.0, 900.0)
        assert R_warm < R_std, "Warmer air should refract less"
        assert R_low_p < R_std, "Lower pressure should refract less"

    def test_roundtrip_apparent_geometric(self) -> None:
        """Apparent → geometric → apparent roundtrip within 0.005°."""
        for h_app in [5.0, 10.0, 20.0, 45.0]:
            h_geo = apparent_to_geometric_altitude(h_app)
            h_app2 = geometric_to_apparent_altitude(h_geo)
            assert abs(h_app2 - h_app) < 0.005, (
                f"Roundtrip failed at h_app={h_app}°: got {h_app2:.5f}°"
            )


class TestMoonParallaxAndSemiDiameter:
    """Moon horizontal parallax and semi-diameter from distance."""

    def test_mean_distance_parallax(self) -> None:
        """At mean distance ~384,400 km, HP ≈ 57.0' (0.9507°)."""
        hp = moon_horizontal_parallax_deg(384_400.0)
        assert 0.935 <= hp <= 0.960, f"HP at mean distance = {hp:.4f}°"

    def test_mean_distance_semi_diameter(self) -> None:
        """At mean distance ~384,400 km, SD ≈ 15.53 arcminutes."""
        sd = moon_semi_diameter_arcmin(384_400.0)
        assert 15.4 <= sd <= 15.7, f"SD at mean distance = {sd:.2f}'"

    def test_perigee(self) -> None:
        """At perigee ~356,400 km, HP and SD are larger."""
        hp_perigee = moon_horizontal_parallax_deg(356_400.0)
        hp_mean = moon_horizontal_parallax_deg(384_400.0)
        assert hp_perigee > hp_mean

        sd_perigee = moon_semi_diameter_arcmin(356_400.0)
        sd_mean = moon_semi_diameter_arcmin(384_400.0)
        assert sd_perigee > sd_mean

    def test_apogee(self) -> None:
        """At apogee ~406,700 km, HP and SD are smaller."""
        hp_apogee = moon_horizontal_parallax_deg(406_700.0)
        hp_mean = moon_horizontal_parallax_deg(384_400.0)
        assert hp_apogee < hp_mean


class TestCrescentWidth:
    """Yallop (1997) crescent width W = SD × (1 − cos(ARCL))."""

    def test_zero_elongation(self) -> None:
        """At ARCL=0° (exact conjunction), W = 0."""
        w = crescent_width_yallop(0.0, sd_arcmin=15.5)
        assert abs(w) < 1e-6

    def test_danjon_elongation(self) -> None:
        """At ARCL=7° (Danjon limit), crescent width is ~0.115'."""
        w = crescent_width_yallop(7.0, sd_arcmin=15.5)
        expected = 15.5 * (1.0 - math.cos(math.radians(7.0)))
        assert abs(w - expected) < 1e-4
        assert 0.10 < w < 0.15

    def test_larger_elongation(self) -> None:
        """Wider elongation → wider crescent."""
        w10 = crescent_width_yallop(10.0, sd_arcmin=15.5)
        w20 = crescent_width_yallop(20.0, sd_arcmin=15.5)
        assert w20 > w10
        assert 0.20 < w10 < 0.26  # ~0.235'
        assert 0.85 < w20 < 1.00  # ~0.935'
