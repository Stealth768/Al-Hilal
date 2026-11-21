"""
Abstract base class for all crescent visibility and calendar criteria models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from al_hilal.astronomy.models import LunarObservationData
from al_hilal.visibility.models import VisibilityAssessment


class VisibilityModel(ABC):
    """Abstract base class for a crescent visibility model or calendar rule."""

    name: str = "BaseModel"
    citation: str = ""

    @abstractmethod
    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        """Evaluate crescent visibility or month-start condition for an observation."""
        raise NotImplementedError
