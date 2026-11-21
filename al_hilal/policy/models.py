"""
Data structures for authority profiles, policies, and calendar predictions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional

from al_hilal.astronomy.models import ObserverLocation


class AuthorityDecisionType(str, Enum):
    """Methodology by which an Islamic authority determines month start."""

    CALCULATION = "calculation"                    # Deterministic astronomical algorithm (e.g. Umm al-Qura, Diyanet, FCNA)
    LOCAL_SIGHTING = "local_sighting"              # Physical sighting within national / regional territory (e.g. Morocco, Oman, Pakistan)
    REGIONAL_SIGHTING = "regional_sighting"        # Sighting shared within neighboring region (e.g. MABIMS)
    GLOBAL_SIGHTING = "global_sighting"            # Any credible sighting anywhere in the world (e.g. Wifaqul Ulama option)
    FOLLOW_SAUDI = "follow_saudi"                  # Follows Saudi Supreme Court announcements directly


class Sect(str, Enum):
    """Denomination for event calendar calculations."""

    SUNNI = "sunni"
    SHIA = "shia"
    GENERAL = "general"


class DhulHijjahRule(str, Enum):
    """Specific policy for determining the 1st of Dhul Hijjah, Arafah, and Eid al-Adha."""

    FOLLOW_MAKKAH = "follow_makkah"        # Align Day of Arafah (9th) and Eid al-Adha (10th) with Hajj at Makkah
    LOCAL_SIGHTING = "local_sighting"      # Apply independent local sighting for Dhul Hijjah as with other months


@dataclass(frozen=True)
class AuthorityProfile:
    """Configuration profile for a national, regional, or international Islamic body."""

    id: str
    name: str
    country_code: str
    body_name: str
    decision_type: AuthorityDecisionType
    primary_criterion: str                 # Key matching visibility model (e.g. 'ummalqura', 'odeh', 'mabims_2021')
    reference_locations: list[ObserverLocation]
    dhul_hijjah_rule: DhulHijjahRule = DhulHijjahRule.LOCAL_SIGHTING
    sect: Sect = Sect.GENERAL
    requires_naked_eye: bool = True
    optical_aid_allowed: bool = False
    min_confidence_for_sighting: float = 0.50
    description: str = ""
    official_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "country_code": self.country_code,
            "body_name": self.body_name,
            "decision_type": self.decision_type.value,
            "primary_criterion": self.primary_criterion,
            "reference_locations": [
                {
                    "name": loc.name,
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "elevation": loc.elevation,
                    "timezone": loc.timezone,
                }
                for loc in self.reference_locations
            ],
            "dhul_hijjah_rule": self.dhul_hijjah_rule.value,
            "sect": self.sect.value,
            "requires_naked_eye": self.requires_naked_eye,
            "optical_aid_allowed": self.optical_aid_allowed,
            "min_confidence_for_sighting": self.min_confidence_for_sighting,
            "description": self.description,
            "official_sources": self.official_sources,
        }


@dataclass(frozen=True)
class MonthStartPrediction:
    """Result of predicting the start of a Hijri month for an authority."""

    authority_id: str
    authority_name: str
    hijri_year: int
    hijri_month: int
    search_evening_gregorian: date        # The 29th evening of preceding month
    calculated_start_date: date           # Pure astronomical / criteria-driven 1st of month
    likely_announced_date: date           # Realistic predicted declaration accounting for authority practices
    month_length_preceding: int           # 29 or 30 days
    is_sighting_possible: bool            # True if visible according to authority's criteria
    sighting_probability: float           # 0.0 to 1.0
    confidence: float                     # Confidence in the predicted outcome (0.0 to 1.0)
    driving_factor: str                   # Which criterion or rule drove the decision
    criteria_used: str
    alternative_date: Optional[date] = None
    alternative_reason: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_id": self.authority_id,
            "authority_name": self.authority_name,
            "hijri_year": self.hijri_year,
            "hijri_month": self.hijri_month,
            "search_evening_gregorian": self.search_evening_gregorian.isoformat(),
            "calculated_start_date": self.calculated_start_date.isoformat(),
            "likely_announced_date": self.likely_announced_date.isoformat(),
            "month_length_preceding": self.month_length_preceding,
            "is_sighting_possible": self.is_sighting_possible,
            "sighting_probability": round(self.sighting_probability, 4),
            "confidence": round(self.confidence, 4),
            "driving_factor": self.driving_factor,
            "criteria_used": self.criteria_used,
            "alternative_date": self.alternative_date.isoformat() if self.alternative_date else None,
            "alternative_reason": self.alternative_reason,
            "details": self.details,
        }


@dataclass(frozen=True)
class IslamicEventPrediction:
    """Predicted Gregorian date and metadata for an Islamic event."""

    event_key: str
    name_en: str
    name_ar: str
    hijri_year: int
    hijri_month: int
    hijri_day: int
    gregorian_date: date
    authority_id: str
    authority_name: str
    confidence: float
    note: Optional[str] = None
    sect: Sect = Sect.GENERAL
