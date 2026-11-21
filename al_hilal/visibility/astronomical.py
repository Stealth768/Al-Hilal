"""
Pure astronomical conjunction and moon-age criteria.

Used by calculation-based bodies, astronomical societies, and specific jurisdictions:
1. Conjunction before local sunset
2. Conjunction before 12:00 UTC (or midnight UTC)
3. Moon age at sunset threshold (e.g., age >= 12h, 15h, or 18h)
"""

from __future__ import annotations

from typing import Any
from al_hilal.astronomy.models import LunarObservationData
from al_hilal.visibility.base import VisibilityModel
from al_hilal.visibility.models import VisibilityAssessment


class ConjunctionBeforeSunsetModel(VisibilityModel):
    """Start of month if geocentric conjunction occurs before local sunset."""

    name = "Conjunction Before Local Sunset"
    citation = "Standard astronomical calendar convention (Conjunction < Sunset)."

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        met = obs.moon_age_at_sunset_hours > 0
        desc = (
            f"Conjunction occurred {obs.moon_age_at_sunset_hours:.2f}h before local sunset."
            if met
            else f"Conjunction occurs after local sunset (Moon age: {obs.moon_age_at_sunset_hours:.2f}h)."
        )

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=met,
            criterion_met=met,
            numeric_value=round(obs.moon_age_at_sunset_hours, 2),
            description=desc,
            details={
                "moon_age_at_sunset_hours": round(obs.moon_age_at_sunset_hours, 2),
                "conjunction_utc": obs.conjunction_utc.isoformat(),
                "sunset_utc": obs.sunset_utc.isoformat(),
            },
            citation=self.citation,
        )


class ConjunctionBeforeMiddayUtcModel(VisibilityModel):
    """Start of month if conjunction occurs before 12:00 UTC on the observation date."""

    name = "Conjunction Before 12:00 UTC"
    citation = "Global astronomical standard (Conjunction < 12:00 UTC)."

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        conj = obs.conjunction_utc
        # Check if conjunction was on observation date before 12:00 UTC
        obs_d = obs.sunset_utc.date()
        conj_d = conj.date()
        met = (conj_d == obs_d and conj.hour < 12) or (conj_d < obs_d)

        desc = (
            f"Conjunction at {conj.strftime('%H:%M:%S')} UTC meets the before-12:00 UTC rule."
            if met
            else f"Conjunction at {conj.strftime('%H:%M:%S')} UTC occurs after 12:00 UTC."
        )

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=met,
            criterion_met=met,
            description=desc,
            details={
                "conjunction_utc": conj.isoformat(),
                "hour_utc": conj.hour + conj.minute / 60.0,
            },
            citation=self.citation,
        )


class MoonAgeThresholdModel(VisibilityModel):
    """Start of month if Moon age at sunset exceeds minimum threshold (e.g. 15 hours)."""

    name = "Moon Age Threshold"
    citation = "Empirical age limit (Moon age at sunset >= threshold)."

    def __init__(self, min_age_hours: float = 15.0) -> None:
        self.min_age_hours = min_age_hours

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        age = obs.moon_age_at_sunset_hours
        met = age >= self.min_age_hours

        desc = (
            f"Moon age at sunset ({age:.2f}h) >= threshold ({self.min_age_hours:.1f}h)."
            if met
            else f"Moon age at sunset ({age:.2f}h) < threshold ({self.min_age_hours:.1f}h)."
        )

        return VisibilityAssessment(
            model_name=f"{self.name} ({self.min_age_hours:.0f}h)",
            is_visible=met,
            criterion_met=met,
            numeric_value=round(age, 2),
            description=desc,
            details={
                "moon_age_hours": round(age, 2),
                "min_age_hours": self.min_age_hours,
            },
            citation=self.citation,
        )
