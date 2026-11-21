"""
Milestone 2 Crescent Visibility Models Verification Script.

Evaluates an astronomical observation through all registered visibility models:
  - Yallop (1997)
  - Odeh (2004)
  - Danjon Limit (1936)
  - Maunder (1911)
  - Fotheringham (1910)
  - Ilyas (1988)
  - MABIMS 2021 (Neo-criteria)
  - MABIMS Legacy (1992)
  - Istanbul 2015 Consensus
  - Saudi Umm al-Qura Calendar Rule
  - Pure Conjunction Before Local Sunset
  - Conjunction Before 12:00 UTC
  - Moon Age Threshold (15h)
  - Schaefer (Stub)
  - Probabilistic Ensemble

Outputs a clear comparative matrix.
"""

from __future__ import annotations

from datetime import date
from al_hilal.astronomy.lunar import compute_lunar_observation
from al_hilal.astronomy.models import AtmosphericConditions, ObserverLocation
from al_hilal.visibility import evaluate_all_models


def main() -> None:
    # Key test case: Makkah Ramadan 1445H observation evening (2024-03-11)
    loc = ObserverLocation(21.4225, 39.8262, 277.0, "Makkah", "Asia/Riyadh")
    obs_date = date(2024, 3, 11)
    conditions = AtmosphericConditions(10.0, 1010.0)

    print("=" * 105)
    print("AL HILAL - MILESTONE 2: MULTI-MODEL VISIBILITY EVALUATION BENCHMARK")
    print(f"Location: {loc.name} ({loc.latitude}N, {loc.longitude}E) | Date: {obs_date}")
    print("=" * 105)

    obs = compute_lunar_observation(loc, obs_date, conditions)

    print(f"Astronomical Snapshot at Sunset ({obs.sunset_utc.strftime('%H:%M:%S')} UTC):")
    print(f"  Moon Altitude : {obs.moon_at_sunset.altitude_deg:+.4f} deg")
    print(f"  Elongation (ARCL) : {obs.arcl_deg:.4f} deg")
    print(f"  Arc of Vision (ARCV): {obs.arcv_deg:.4f} deg")
    print(f"  Crescent Width (W)  : {obs.w_arcmin:.4f} arcmin")
    print(f"  Lag Time      : {obs.lag_time_minutes:.1f} minutes")
    print(f"  Moon Age      : {obs.moon_age_at_sunset_hours:.2f} hours")
    print("-" * 105)
    print(f"{'Model Name':<28} | {'Met?':<5} | {'Category/Zone':<28} | {'Value':<8} | {'P(Vis)':<6} | {'Description'}")
    print("-" * 105)

    evaluations = evaluate_all_models(obs)
    for key, res in evaluations.items():
        met_str = "YES" if res.criterion_met else "NO"
        cat_str = res.category if res.category else "-"
        val_str = f"{res.numeric_value:+.3f}" if res.numeric_value is not None else "-"
        prob_str = f"{res.probability*100:.0f}%" if res.probability > 0 else "0%"
        print(f"{res.model_name:<28} | {met_str:<5} | {cat_str:<28} | {val_str:<8} | {prob_str:<6} | {res.description[:55]}...")

    print("=" * 105)


if __name__ == "__main__":
    main()
