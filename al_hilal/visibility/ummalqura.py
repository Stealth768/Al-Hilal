"""
Umm al-Qura Calendar Criteria (Kingdom of Saudi Arabia).

References
----------
Al-Mustafa, Z. A. (2000). "The Astronomical Aspects of the Umm al-Qura Calendar."
KACST (King Abdulaziz City for Science and Technology).
Hashim, A. (2005). "The Saudi Umm al-Qura Calendar: History and Rules."

Deterministic Rules (Post-1423 AH / 2002 CE)
---------------------------------------------
Evaluated at the Ka'bah / Makkah al-Mukarramah (21.4225°N, 39.8262°E):
On the 29th of each Hijri month:
    1. Geocentric conjunction (New Moon) occurs strictly BEFORE sunset at Makkah.
    2. Moonset occurs strictly AFTER sunset at Makkah (lag time > 0 minutes).

If both conditions are met, the next day is the 1st of the new Hijri month.
If either condition fails, the current month completes 30 days (istikmal).
"""

from __future__ import annotations

from typing import Any
from al_hilal.astronomy.models import LunarObservationData
from al_hilal.visibility.base import VisibilityModel
from al_hilal.visibility.models import VisibilityAssessment


class UmmAlQuraModel(VisibilityModel):
    """Saudi Arabia Umm al-Qura official calendar rule."""

    name = "Umm al-Qura (Saudi Arabia)"
    citation = "KACST (1423 AH / 2002 CE). Rules of the Official Umm al-Qura Calendar."

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        # Rule 1: Conjunction before sunset
        conjunction_before_sunset = obs.moon_age_at_sunset_hours > 0

        # Rule 2: Moonset after sunset (positive lag time)
        moonset_after_sunset = (
            obs.moonset_utc is not None
            and obs.sunset_utc is not None
            and obs.moonset_utc > obs.sunset_utc
        )
        lag_min = obs.lag_time_minutes if obs.lag_time_minutes is not None else 0.0

        met = conjunction_before_sunset and moonset_after_sunset

        desc = (
            f"Umm al-Qura rule satisfied: Conjunction was {obs.moon_age_at_sunset_hours:.2f}h before sunset, "
            f"and Moon sets {lag_min:.1f}m after sunset in {obs.observer.name or 'Makkah'}."
            if met
            else (
                f"Umm al-Qura rule NOT satisfied: "
                f"{'Conjunction is after sunset (' + str(round(obs.moon_age_at_sunset_hours, 2)) + 'h); ' if not conjunction_before_sunset else ''}"
                f"{'Moon sets before or at sunset (lag=' + str(round(lag_min, 1)) + 'm);' if not moonset_after_sunset else ''}"
            )
        )

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=met,  # In calculation calendar, meeting criteria begins the month
            criterion_met=met,
            numeric_value=round(lag_min, 2),
            description=desc,
            details={
                "conjunction_before_sunset": conjunction_before_sunset,
                "moonset_after_sunset": moonset_after_sunset,
                "moon_age_at_sunset_hours": round(obs.moon_age_at_sunset_hours, 2),
                "lag_time_minutes": round(lag_min, 1) if obs.lag_time_minutes is not None else None,
                "conjunction_utc": obs.conjunction_utc.isoformat(),
                "sunset_utc": obs.sunset_utc.isoformat(),
                "moonset_utc": obs.moonset_utc.isoformat() if obs.moonset_utc else None,
            },
            citation=self.citation,
        )
