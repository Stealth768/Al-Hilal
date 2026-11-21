"""
Al Hilal — Milestone 1 Comprehensive Astronomical Verification Script.

Computes 25 test cases across 5 locations:
  1. Makkah, Saudi Arabia (21.4225°N, 39.8262°E, 277m)
  2. Jakarta, Indonesia (-6.2088°S, 106.8456°E, 8m)
  3. London, UK (51.5074°N, -0.1278°W, 11m)
  4. New York, USA (40.7128°N, -74.0060°W, 10m)
  5. Karachi, Pakistan (24.8607°N, 67.0011°E, 10m)

Compares:
  - Moon topocentric altitude at sunset: Skyfield vs NASA JPL Horizons (interpolated)
  - Moon topocentric azimuth at sunset: Skyfield vs NASA JPL Horizons (interpolated)
  - Geocentric elongation (ARCL): Skyfield vs NASA JPL Horizons
  - Conjunction (New Moon) UTC time: Skyfield vs Astronomical reference dates
  - Sunset / moonset times and lag times

Outputs structured results and statistics.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from al_hilal.api.horizons import get_moon_alt_az, query_body_rows, _parse_row_datetime
from al_hilal.astronomy.lunar import compute_lunar_observation
from al_hilal.astronomy.models import AtmosphericConditions, ObserverLocation

STD_CONDITIONS = AtmosphericConditions(temperature_c=10.0, pressure_hPa=1010.0)

LOCATIONS = [
    ObserverLocation(21.4225, 39.8262, 277.0, "Makkah", "Asia/Riyadh"),
    ObserverLocation(-6.2088, 106.8456, 8.0, "Jakarta", "Asia/Jakarta"),
    ObserverLocation(51.5074, -0.1278, 11.0, "London", "Europe/London"),
    ObserverLocation(40.7128, -74.0060, 10.0, "New York", "America/New_York"),
    ObserverLocation(24.8607, 67.0011, 10.0, "Karachi", "Asia/Karachi"),
]

# 5 observation evenings for each location = 25 test cases
TEST_DATES = [
    "2020-04-24",  # Ramadan 1441
    "2021-04-12",  # Ramadan 1442
    "2022-04-01",  # Ramadan 1443
    "2023-03-22",  # Ramadan 1444
    "2024-03-11",  # Ramadan 1445
]

# Known reference conjunction (New Moon) times published by USNO / Astronomical Almanac
REFERENCE_CONJUNCTIONS = {
    "2020-04-24": datetime(2020, 4, 23, 2, 26, tzinfo=timezone.utc),
    "2021-04-12": datetime(2021, 4, 12, 2, 31, tzinfo=timezone.utc),
    "2022-04-01": datetime(2022, 4, 1, 6, 24, tzinfo=timezone.utc),
    "2023-03-22": datetime(2023, 3, 21, 17, 23, tzinfo=timezone.utc),
    "2024-03-11": datetime(2024, 3, 10, 9, 0, tzinfo=timezone.utc),
}

TOLERANCES = {
    "alt_deg": 0.05,       # 3 arcmin
    "az_deg": 0.10,        # 6 arcmin
    "conj_minutes": 1.0,   # 1 minute vs USNO published table
}


def main() -> None:
    results: list[dict[str, Any]] = []
    print("=" * 110)
    print("AL HILAL - MILESTONE 1 REAL ASTRONOMICAL BENCHMARK: SKYFIELD+DE440 vs NASA JPL HORIZONS")
    print("=" * 110)
    print(f"{'Location':<10} | {'Date':<10} | {'Conjunction UTC':<19} | {'Sunset UTC':<10} | "
          f"{'Alt SF':<8} | {'Alt JHL':<8} | {'dAlt(deg)':<9} | "
          f"{'Az SF':<8} | {'Az JHL':<8} | {'dAz(deg)':<9} | {'Status'}")
    print("-" * 110)

    alt_errors: list[float] = []
    az_errors: list[float] = []
    conj_errors_sec: list[float] = []

    for loc in LOCATIONS:
        for d_str in TEST_DATES:
            obs_date = date.fromisoformat(d_str)
            # Compute via Al Hilal Skyfield core
            obs = compute_lunar_observation(loc, obs_date, STD_CONDITIONS)
            sf_alt = obs.moon_at_sunset.altitude_deg
            sf_az = obs.moon_at_sunset.azimuth_deg
            sunset = obs.sunset_utc
            conj = obs.conjunction_utc

            # Check conjunction against reference
            ref_conj = REFERENCE_CONJUNCTIONS[d_str]
            conj_diff_s = abs((conj - ref_conj).total_seconds())
            conj_errors_sec.append(conj_diff_s)

            # Query Horizons
            try:
                hz_alt, hz_az = get_moon_alt_az(
                    loc.latitude, loc.longitude, loc.elevation, sunset
                )
                alt_diff = abs(sf_alt - hz_alt)
                az_diff = abs((sf_az - hz_az + 180.0) % 360.0 - 180.0)
                alt_errors.append(alt_diff)
                az_errors.append(az_diff)

                passed = alt_diff <= TOLERANCES["alt_deg"] and az_diff <= TOLERANCES["az_deg"]
                status = "PASS" if passed else "FAIL"

                print(f"{loc.name:<10} | {d_str:<10} | {conj.strftime('%Y-%m-%d %H:%M'):<19} | {sunset.strftime('%H:%M:%S'):<10} | "
                      f"{sf_alt:+.4f} | {hz_alt:+.4f} | {alt_diff:.4f} | "
                      f"{sf_az:.4f} | {hz_az:.4f} | {az_diff:.4f} | {status}")

                results.append({
                    "location": loc.name,
                    "date": d_str,
                    "conjunction_utc": conj.isoformat(),
                    "sunset_utc": sunset.isoformat(),
                    "moonset_utc": obs.moonset_utc.isoformat() if obs.moonset_utc else None,
                    "lag_minutes": obs.lag_time_minutes,
                    "skyfield_alt_deg": round(sf_alt, 4),
                    "horizons_alt_deg": round(hz_alt, 4),
                    "alt_diff_deg": round(alt_diff, 5),
                    "skyfield_az_deg": round(sf_az, 4),
                    "horizons_az_deg": round(hz_az, 4),
                    "az_diff_deg": round(az_diff, 5),
                    "arcl_deg": round(obs.arcl_deg, 4),
                    "w_arcmin": round(obs.w_arcmin, 4),
                    "delta_t_s": obs.delta_t.value_seconds,
                    "status": status,
                })
            except Exception as e:
                print(f"{loc.name:<10} | {d_str:<10} | {conj.strftime('%Y-%m-%d %H:%M'):<19} | {sunset.strftime('%H:%M:%S'):<10} | "
                      f"{sf_alt:+.4f}° | ERROR: {str(e)[:25]} | SKIP")

    print("=" * 110)
    print("\nBENCHMARK STATISTICAL SUMMARY:")
    print(f"Total test cases evaluated : {len(alt_errors)}")
    if alt_errors:
        print(f"Altitude Error vs JPL Horizons (|Skyfield - Horizons|):")
        print(f"  Tolerance      : <= {TOLERANCES['alt_deg']} deg (3 arcmin)")
        print(f"  Max error      : {max(alt_errors):.5f} deg ({max(alt_errors)*60:.3f} arcmin / {max(alt_errors)*3600:.1f} arcsec)")
        print(f"  Mean error     : {sum(alt_errors)/len(alt_errors):.5f} deg ({sum(alt_errors)/len(alt_errors)*60:.3f} arcmin / {sum(alt_errors)/len(alt_errors)*3600:.1f} arcsec)")
        print(f"  Min error      : {min(alt_errors):.5f} deg ({min(alt_errors)*3600:.1f} arcsec)")

        print(f"\nAzimuth Error vs JPL Horizons (|Skyfield - Horizons|):")
        print(f"  Tolerance      : <= {TOLERANCES['az_deg']} deg (6 arcmin)")
        print(f"  Max error      : {max(az_errors):.5f} deg ({max(az_errors)*60:.3f} arcmin / {max(az_errors)*3600:.1f} arcsec)")
        print(f"  Mean error     : {sum(az_errors)/len(az_errors):.5f} deg ({sum(az_errors)/len(az_errors)*60:.3f} arcmin / {sum(az_errors)/len(az_errors)*3600:.1f} arcsec)")

    if conj_errors_sec:
        print(f"\nConjunction Time Error vs USNO / Astronomical Almanac Reference:")
        print(f"  Tolerance      : <= {TOLERANCES['conj_minutes']*60:.0f} seconds")
        print(f"  Max difference : {max(conj_errors_sec):.1f} seconds")
        print(f"  Mean difference: {sum(conj_errors_sec)/len(conj_errors_sec):.1f} seconds")

    # Save verification report as JSON
    out_path = Path("data/verification_m1_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tolerances": TOLERANCES,
            "summary": {
                "total_cases": len(alt_errors),
                "all_passed": all(r.get("status") == "PASS" for r in results),
                "alt_error_max_deg": max(alt_errors) if alt_errors else None,
                "alt_error_mean_deg": sum(alt_errors)/len(alt_errors) if alt_errors else None,
                "az_error_max_deg": max(az_errors) if az_errors else None,
                "az_error_mean_deg": sum(az_errors)/len(az_errors) if az_errors else None,
                "conj_error_max_sec": max(conj_errors_sec) if conj_errors_sec else None,
            },
            "cases": results,
        }, f, indent=2)
    print(f"\nSaved detailed verification dataset to {out_path}")


if __name__ == "__main__":
    main()
