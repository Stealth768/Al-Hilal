"""
Schaefer (1988, 1993, 1996) Physiological Crescent Visibility Model.

STATUS: STUB INTERFACE ONLY (DEFERRED PER USER DECISION C)
-----------------------------------------------------------
Decision C from Project Plan:
    "Defer Schaefer. No planned profile requires it, so keep only a stub
    interface for now."

Reference
---------
Schaefer, B. E. (1988). "Visibility of the Lunar Crescent." Q. J. R. Astron. Soc. 29, 511–523.
Schaefer, B. E. (1993). "Astronomy and the limits of vision." Vistas in Astronomy 36, 311–361.
Schaefer, B. E. (1996). "Lunar Crescent Visibility." Q. J. R. Astron. Soc. 37, 759–768.

When fully implemented in a future milestone, this model will incorporate
detailed atmospheric radiative transfer, physiological contrast thresholds
of the human eye (Hecht-Stiles-Verriest curves), and extinction coefficients.
"""

from __future__ import annotations

from typing import Any
from al_hilal.astronomy.models import LunarObservationData
from al_hilal.visibility.base import VisibilityModel
from al_hilal.visibility.models import VisibilityAssessment


class SchaeferModel(VisibilityModel):
    """Schaefer physiological vision model (stubbed per Decision C)."""

    name = "Schaefer (Physiological - Stub)"
    citation = "Schaefer, B. E. (1988, 1996). Q. J. R. Astron. Soc. [STUB INTERFACE - DEFERRED]"

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        # Fall back to Danjon check for basic validity
        arcl = obs.arcl_deg
        met = arcl >= 7.0 and obs.moon_age_at_sunset_hours > 0

        desc = (
            "Schaefer physiological model is deferred per project plan Decision C. "
            "Stub evaluation performed based on preliminary geometric elongation."
        )

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=met,
            criterion_met=met,
            numeric_value=round(arcl, 2),
            description=desc,
            details={
                "status": "STUB_DEFERRED",
                "arcl_deg": round(arcl, 4),
                "decision": "Decision C - Deferred until post-backtesting",
            },
            citation=self.citation,
        )
