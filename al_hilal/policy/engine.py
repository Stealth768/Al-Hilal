"""
Policy engine: implements authority-specific rules, istikmal logic,
and event date generation.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional
import yaml

from al_hilal.astronomy.lunar import compute_lunar_observation
from al_hilal.astronomy.models import AtmosphericConditions
from al_hilal.policy.loader import get_authority_profile, load_all_authority_profiles
from al_hilal.policy.models import (
    AuthorityDecisionType,
    AuthorityProfile,
    DhulHijjahRule,
    IslamicEventPrediction,
    MonthStartPrediction,
    Sect,
)
from al_hilal.visibility import evaluate_all_models, get_model
from al_hilal.visibility.probabilistic import ProbabilisticEnsembleModel

NAMES_YAML_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "i18n" / "names.yaml"


class PolicyEngine:
    """Evaluates astronomical observations against national and regional authority policies."""

    def __init__(self, conditions: Optional[AtmosphericConditions] = None) -> None:
        self.conditions = conditions or AtmosphericConditions(10.0, 1010.0)
        self.prob_model = ProbabilisticEnsembleModel()
        self._load_i18n_names()

    def _load_i18n_names(self) -> None:
        if NAMES_YAML_PATH.exists():
            with open(NAMES_YAML_PATH, "r", encoding="utf-8") as f:
                self.i18n_data = yaml.safe_load(f)
        else:
            self.i18n_data = {"hijri_months": {}, "islamic_events": {}}

    def predict_month_start(
        self,
        authority: AuthorityProfile | str,
        hijri_year: int,
        hijri_month: int,
        search_evening_gregorian: date,
    ) -> MonthStartPrediction:
        """Predict the start date of a Hijri month for a given authority.

        Parameters
        ----------
        authority:
            AuthorityProfile or string ID (e.g. 'saudi_ummalqura', 'morocco_habous').
        hijri_year:
            Target Hijri year.
        hijri_month:
            Target Hijri month (1 to 12).
        search_evening_gregorian:
            Gregorian date of the 29th day of the preceding month (observation evening).
        """
        if isinstance(authority, str):
            profile = get_authority_profile(authority)
        else:
            profile = authority

        # Evaluate across authority reference locations
        primary_loc = profile.reference_locations[0]
        obs = compute_lunar_observation(primary_loc, search_evening_gregorian, self.conditions)

        # Evaluate primary model
        primary_model = get_model(profile.primary_criterion)
        assessment = primary_model.evaluate(obs)

        # Evaluate probabilistic model for likelihood
        prob_assessment = self.prob_model.evaluate(obs)
        prob = prob_assessment.probability
        confidence = abs(prob - 0.5) * 2.0  # High confidence near 0.0 and 1.0

        criterion_met = assessment.criterion_met

        # ── 1. Calculated Start Date (Pure rule application) ──────────────
        if criterion_met:
            # 29 days in preceding month -> starts day after search evening
            calc_start = search_evening_gregorian + timedelta(days=1)
            month_len = 29
            driving_factor = f"Criteria '{profile.primary_criterion}' satisfied at {primary_loc.name}."
        else:
            # Istikmal: 30 days in preceding month -> starts 2 days after search evening
            calc_start = search_evening_gregorian + timedelta(days=2)
            month_len = 30
            driving_factor = (
                f"Istikmal (30 days): Criteria '{profile.primary_criterion}' not met at {primary_loc.name}."
            )

        # ── 2. Likely Announced Date (Practice / Sighting reality) ────────
        alt_date: Optional[date] = None
        alt_reason: Optional[str] = None

        if profile.decision_type == AuthorityDecisionType.CALCULATION:
            # Calculation authorities follow calculated date directly
            likely_announced = calc_start
        elif profile.id == "saudi_supreme_court":
            # Saudi Supreme Court historically accepts sightings when lag > 0
            # even if optical models consider it Category E or marginal
            lag = obs.lag_time_minutes or 0.0
            if obs.moon_age_at_sunset_hours > 0 and lag > 0:
                likely_announced = search_evening_gregorian + timedelta(days=1)
                month_len = 29
                driving_factor = "Saudi Supreme Court accepts witness testimony (lag > 0m)."
            else:
                likely_announced = search_evening_gregorian + timedelta(days=2)
                month_len = 30
                driving_factor = "Istikmal: Moon set before sunset or conjunction after sunset."
        else:
            # Sighting-based bodies require credible visibility probability
            if prob >= profile.min_confidence_for_sighting:
                likely_announced = search_evening_gregorian + timedelta(days=1)
                month_len = 29
            else:
                likely_announced = search_evening_gregorian + timedelta(days=2)
                month_len = 30
                if criterion_met:
                    alt_date = calc_start
                    alt_reason = "Astronomical criterion met, but high risk of optical sighting failure / weather."

        # Special check for Dhul Hijjah Makkah-following rule
        if hijri_month == 12 and profile.dhul_hijjah_rule == DhulHijjahRule.FOLLOW_MAKKAH:
            driving_factor += " (Aligned with Hajj/Makkah declaration)."

        return MonthStartPrediction(
            authority_id=profile.id,
            authority_name=profile.name,
            hijri_year=hijri_year,
            hijri_month=hijri_month,
            search_evening_gregorian=search_evening_gregorian,
            calculated_start_date=calc_start,
            likely_announced_date=likely_announced,
            month_length_preceding=month_len,
            is_sighting_possible=assessment.is_visible,
            sighting_probability=prob,
            confidence=round(confidence, 4),
            driving_factor=driving_factor,
            criteria_used=profile.primary_criterion,
            alternative_date=alt_date,
            alternative_reason=alt_reason,
            details={
                "primary_assessment": assessment.to_dict(),
                "probabilistic_assessment": prob_assessment.to_dict(),
                "decision_type": profile.decision_type.value,
                "dhul_hijjah_rule": profile.dhul_hijjah_rule.value,
                "observer_location": primary_loc.name,
                "lag_time_minutes": obs.lag_time_minutes,
                "moon_altitude_sunset": obs.moon_at_sunset.altitude_deg,
                "elongation_arcl": obs.arcl_deg,
            },
        )

    def predict_event_date(
        self,
        event_key: str,
        hijri_year: int,
        month_1st_gregorian: date,
        authority: AuthorityProfile | str,
    ) -> Optional[IslamicEventPrediction]:
        """Compute the Gregorian date of an Islamic event given the 1st of its month."""
        if isinstance(authority, str):
            profile = get_authority_profile(authority)
        else:
            profile = authority

        events_dict = self.i18n_data.get("islamic_events", {})
        if event_key not in events_dict:
            return None

        evt = events_dict[event_key]
        evt_sect = evt.get("sect", "general")
        profile_sect = profile.sect.value

        # Filter out Shia-only events for Sunni authorities and vice-versa
        if evt_sect != "general" and profile_sect != "general" and evt_sect != profile_sect:
            return None

        h_month = evt.get("hijri_month", 1)
        # Single day event or window start
        h_day = evt.get("hijri_day", 1)
        if "hijri_days" in evt:
            h_day = evt["hijri_days"][0]

        # Calculate Gregorian date: 1st of month + (day - 1) days
        evt_greg = month_1st_gregorian + timedelta(days=h_day - 1)

        return IslamicEventPrediction(
            event_key=event_key,
            name_en=evt.get("en", event_key),
            name_ar=evt.get("ar", ""),
            hijri_year=hijri_year,
            hijri_month=h_month,
            hijri_day=h_day,
            gregorian_date=evt_greg,
            authority_id=profile.id,
            authority_name=profile.name,
            confidence=0.90,
            note=evt.get("note"),
            sect=Sect(evt_sect),
        )
