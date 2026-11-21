"""
Data models and enumeration types for crescent visibility models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class VisibilityCategory(str, Enum):
    """Yallop (1997) visibility categories."""

    A = "A"  # Easily visible to the naked eye
    B = "B"  # Visible under perfect conditions
    C = "C"  # May need optical aid to find the crescent
    D = "D"  # Will need optical aid to find and see the crescent
    E = "E"  # Not visible with conventional telescopes (below limit)
    F = "F"  # Below Danjon limit / physically impossible


class OdehZone(str, Enum):
    """Odeh (2004) visibility zones."""

    ZONE_A = "Zone A"  # Easily visible by naked eye
    ZONE_B = "Zone B"  # Visible by optical aid, could be seen by naked eye
    ZONE_C = "Zone C"  # Visible by optical aid only
    ZONE_D = "Zone D"  # Not visible even with optical aid


@dataclass(frozen=True)
class VisibilityAssessment:
    """Standard assessment output for any crescent visibility or calendar model."""

    model_name: str
    is_visible: bool
    criterion_met: bool
    description: str
    category: Optional[str] = None
    numeric_value: Optional[float] = None  # e.g., Yallop q, Odeh V
    probability: float = 0.0               # Estimated P(crescent visible) [0.0, 1.0]
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    details: dict[str, Any] = field(default_factory=dict)
    citation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert assessment to JSON-serializable dictionary."""
        return {
            "model_name": self.model_name,
            "is_visible": self.is_visible,
            "criterion_met": self.criterion_met,
            "category": self.category,
            "numeric_value": self.numeric_value,
            "probability": round(self.probability, 4),
            "confidence_interval": [round(self.confidence_interval[0], 4), round(self.confidence_interval[1], 4)],
            "description": self.description,
            "details": self.details,
            "citation": self.citation,
        }
