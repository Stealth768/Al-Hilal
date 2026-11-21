"""
MABIMS Crescent Visibility Criteria (Brunei, Indonesia, Malaysia, Singapore).

References
----------
MABIMS (2021). "Kriteria Baru Imkanur Rukyah MABIMS 2021" (Adopted 2022).
Kementerian Agama Republik Indonesia (Kemenag).
"""

from __future__ import annotations

from typing import Any
from al_hilal.astronomy.models import LunarObservationData
from al_hilal.visibility.base import VisibilityModel
from al_hilal.visibility.models import VisibilityAssessment


class Mabims2021Model(VisibilityModel):
    """MABIMS 2021 Neo-criteria (Imkanur Rukyah):

    - Moon topocentric/apparent altitude at sunset >= 3.0°
    - Geocentric elongation (ARCL) >= 6.4°
    """

    name = "MABIMS 2021"
    citation = "MABIMS (2021). Kriteria Imkanur Rukyah Baru (Alt >= 3°, Elong >= 6.4°)."

    MIN_ALTITUDE_DEG = 3.0
    MIN_ELONGATION_DEG = 6.4

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        alt = obs.moon_at_sunset.altitude_deg
        arcl = obs.arcl_deg

        alt_ok = alt >= self.MIN_ALTITUDE_DEG
        elong_ok = arcl >= self.MIN_ELONGATION_DEG
        met = alt_ok and elong_ok and obs.moon_age_at_sunset_hours > 0

        desc = (
            f"MABIMS 2021 satisfied: Alt {alt:.2f}° >= 3.0° and Elongation {arcl:.2f}° >= 6.4°."
            if met
            else f"MABIMS 2021 not satisfied: Alt={alt:.2f}° (req >=3.0°), Elong={arcl:.2f}° (req >=6.4°)."
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


class MabimsLegacyModel(VisibilityModel):
    """MABIMS 1992 Legacy criteria (Imkanur Rukyah Lama):

    - Moon altitude at sunset >= 2.0° and elongation >= 3.0°, OR
    - Moon lag time >= 8 minutes (after sunset),
    - Moon age at sunset >= 8 hours.
    """

    name = "MABIMS Legacy (1992)"
    citation = "MABIMS (1992). Kriteria Imkanur Rukyah Klasik (Alt >= 2°, Elong >= 3° atau Lag >= 8m)."

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        alt = obs.moon_at_sunset.altitude_deg
        arcl = obs.arcl_deg
        lag = obs.lag_time_minutes if obs.lag_time_minutes is not None else -999.0
        age = obs.moon_age_at_sunset_hours

        cond1 = (alt >= 2.0 and arcl >= 3.0)
        cond2 = (lag >= 8.0)
        met = (cond1 or cond2) and (age >= 8.0)

        desc = (
            f"MABIMS Legacy met: Alt={alt:.2f}°, Elong={arcl:.2f}°, Lag={lag:.1f}m, Age={age:.1f}h."
            if met
            else f"MABIMS Legacy not met: Alt={alt:.2f}°, Elong={arcl:.2f}°, Lag={lag:.1f}m, Age={age:.1f}h."
        )

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=met,
            criterion_met=met,
            description=desc,
            details={
                "altitude_deg": round(alt, 4),
                "arcl_deg": round(arcl, 4),
                "lag_time_minutes": round(lag, 1) if lag > -900 else None,
                "moon_age_hours": round(age, 2),
            },
            citation=self.citation,
        )
