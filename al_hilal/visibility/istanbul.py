"""
Istanbul 2015 Consensus Criterion (International Hijri Calendar Unity Congress).

Reference
---------
International Hijri Calendar Unity Congress (Istanbul, 2016 / proposed 2015).
Directorate of Religious Affairs (Diyanet), Turkey.

Criteria
--------
For the start of a lunar month under the unified global calendar proposal:
    1. Moon altitude at sunset >= 5.0°
    2. Elongation (ARCL) >= 8.0°
"""

from __future__ import annotations

from typing import Any
from al_hilal.astronomy.models import LunarObservationData
from al_hilal.visibility.base import VisibilityModel
from al_hilal.visibility.models import VisibilityAssessment


class Istanbul2015Model(VisibilityModel):
    """Istanbul 2015 consensus criterion (Alt >= 5°, Elong >= 8°)."""

    name = "Istanbul 2015"
    citation = "Istanbul 2015 Consensus (Diyanet, Turkey: Alt >= 5.0°, Elong >= 8.0°)."

    MIN_ALTITUDE_DEG = 5.0
    MIN_ELONGATION_DEG = 8.0

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        alt = obs.moon_at_sunset.altitude_deg
        arcl = obs.arcl_deg

        alt_ok = alt >= self.MIN_ALTITUDE_DEG
        elong_ok = arcl >= self.MIN_ELONGATION_DEG
        met = alt_ok and elong_ok and obs.moon_age_at_sunset_hours > 0

        desc = (
            f"Istanbul 2015 satisfied: Alt {alt:.2f}° >= 5.0° and Elongation {arcl:.2f}° >= 8.0°."
            if met
            else f"Istanbul 2015 not satisfied: Alt={alt:.2f}° (req >=5.0°), Elong={arcl:.2f}° (req >=8.0°)."
        )

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=met,
            criterion_met=met,
            description=desc,
            details={
                "altitude_deg": round(alt, 4),
                "arcl_deg": round(arcl, 4),
                "altitude_ok": alt_ok,
                "elongation_ok": elong_ok,
                "min_altitude_deg": self.MIN_ALTITUDE_DEG,
                "min_elongation_deg": self.MIN_ELONGATION_DEG,
            },
            citation=self.citation,
        )
