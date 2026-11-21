"""
Classical crescent visibility criteria.

Includes:
1. Danjon Limit (1932, 1936)
2. Fotheringham (1910)
3. Maunder (1911)
4. Ilyas (1988)

References
----------
Danjon, A. (1932). "Croissant de Lune et lumière cendrée." L'Astronomie 46, 57–66.
Danjon, A. (1936). "Le croissant de Lune." L'Astronomie 50, 443–448.
Fotheringham, J. K. (1910). "On the Smallest Visible Phase of the Moon." MNRAS 70, 527–531.
Maunder, E. W. (1911). "On the Smallest Visible Phase of the Moon." J. Br. Astron. Assoc. 21, 355–362.
Ilyas, M. (1988). "Limiting Altitude Separation in the New Moon's First Visibility Criterion."
Astron. Astrophys. 206, 133–135.
"""

from __future__ import annotations

import math
from typing import Any
from al_hilal.astronomy.models import LunarObservationData
from al_hilal.visibility.base import VisibilityModel
from al_hilal.visibility.models import VisibilityAssessment


class DanjonModel(VisibilityModel):
    """Danjon limit: minimum elongation ARCL for physical crescent existence."""

    name = "Danjon Limit"
    citation = "Danjon, A. (1936). L'Astronomie 50, 443–448."

    def __init__(self, limit_deg: float = 7.0) -> None:
        self.limit_deg = limit_deg

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        arcl = obs.arcl_deg
        met = arcl >= self.limit_deg and obs.moon_age_at_sunset_hours > 0

        desc = (
            f"Elongation {arcl:.2f}° >= {self.limit_deg:.1f}° (crescent physically forms)."
            if met
            else f"Elongation {arcl:.2f}° < {self.limit_deg:.1f}° (lunar mountains shadow crescent; zero cusp length)."
        )

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=met,
            criterion_met=met,
            numeric_value=round(arcl, 4),
            description=desc,
            details={"arcl_deg": round(arcl, 4), "limit_deg": self.limit_deg},
            citation=self.citation,
        )


class MaunderModel(VisibilityModel):
    """Maunder (1911) ARCV-DAZ visibility curve."""

    name = "Maunder (1911)"
    citation = "Maunder, E. W. (1911). J. Br. Astron. Assoc. 21, 355–362."

    DANJON_LIMIT_DEG = 7.0

    @classmethod
    def min_arcv(cls, daz_deg: float) -> float:
        """Minimum required ARCV for a given relative azimuth DAZ."""
        daz = abs(daz_deg)
        # Empirical quadratic fit to Maunder 1911 table (0°->11°, 10°->9.5°, 20°->6.0°)
        return max(5.0, 11.0 - 0.05 * daz - 0.01 * (daz**2))

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        daz = abs(obs.daz_deg)
        arcv = obs.arcv_deg
        arcl = obs.arcl_deg
        arcv_req = self.min_arcv(daz)

        met = (
            arcl >= self.DANJON_LIMIT_DEG
            and obs.moon_age_at_sunset_hours > 0
            and arcv >= arcv_req
            and obs.moon_at_sunset.altitude_deg > 0
        )

        diff = arcv - arcv_req
        desc = (
            f"ARCV ({arcv:.2f}°) >= Maunder threshold ({arcv_req:.2f}°) at DAZ={daz:.2f}°."
            if met
            else f"ARCV ({arcv:.2f}°) < Maunder threshold ({arcv_req:.2f}°) at DAZ={daz:.2f}°."
        )

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=met,
            criterion_met=met,
            numeric_value=round(diff, 4),
            description=desc,
            details={
                "arcv_deg": round(arcv, 4),
                "daz_deg": round(daz, 4),
                "min_arcv_deg": round(arcv_req, 4),
                "arcv_margin_deg": round(diff, 4),
            },
            citation=self.citation,
        )


class FotheringhamModel(VisibilityModel):
    """Fotheringham (1910) ARCV-DAZ visibility curve."""

    name = "Fotheringham (1910)"
    citation = "Fotheringham, J. K. (1910). MNRAS 70, 527–531."

    @classmethod
    def min_arcv(cls, daz_deg: float) -> float:
        daz = min(23.0, abs(daz_deg))
        return max(7.0, 12.0 - 0.008 * (daz**2))

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        daz = abs(obs.daz_deg)
        arcv = obs.arcv_deg
        arcl = obs.arcl_deg
        arcv_req = self.min_arcv(daz)

        met = (
            arcl >= 7.0
            and obs.moon_age_at_sunset_hours > 0
            and arcv >= arcv_req
            and obs.moon_at_sunset.altitude_deg > 0
        )

        diff = arcv - arcv_req
        desc = (
            f"ARCV ({arcv:.2f}°) >= Fotheringham threshold ({arcv_req:.2f}°) at DAZ={daz:.2f}°."
            if met
            else f"ARCV ({arcv:.2f}°) < Fotheringham threshold ({arcv_req:.2f}°) at DAZ={daz:.2f}°."
        )

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=met,
            criterion_met=met,
            numeric_value=round(diff, 4),
            description=desc,
            details={
                "arcv_deg": round(arcv, 4),
                "daz_deg": round(daz, 4),
                "min_arcv_deg": round(arcv_req, 4),
                "arcv_margin_deg": round(diff, 4),
            },
            citation=self.citation,
        )


class IlyasModel(VisibilityModel):
    """Ilyas (1988) composite crescent visibility criterion."""

    name = "Ilyas (1988)"
    citation = "Ilyas, M. (1988). Astron. Astrophys. 206, 133–135."

    MIN_ELONGATION_DEG = 10.5
    MIN_ALTITUDE_DEG = 4.0
    MIN_LAG_MINUTES = 40.0

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        arcl = obs.arcl_deg
        alt = obs.moon_at_sunset.altitude_deg
        lag = obs.lag_time_minutes if obs.lag_time_minutes is not None else -999.0

        cond_elong = arcl >= self.MIN_ELONGATION_DEG
        cond_alt = alt >= self.MIN_ALTITUDE_DEG
        cond_lag = lag >= self.MIN_LAG_MINUTES

        met = cond_elong and cond_alt and cond_lag and obs.moon_age_at_sunset_hours > 0

        desc = (
            f"Ilyas conditions satisfied (Elong {arcl:.1f}°>=10.5°, Alt {alt:.1f}°>=4.0°, Lag {lag:.0f}m>=40m)."
            if met
            else f"Ilyas conditions not met (Elong={arcl:.1f}°, Alt={alt:.1f}°, Lag={lag:.0f}m)."
        )

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=met,
            criterion_met=met,
            description=desc,
            details={
                "arcl_deg": round(arcl, 4),
                "altitude_deg": round(alt, 4),
                "lag_time_minutes": round(lag, 1) if lag > -900 else None,
                "elongation_ok": cond_elong,
                "altitude_ok": cond_alt,
                "lag_ok": cond_lag,
            },
            citation=self.citation,
        )
