"""
Odeh (2004) Crescent Visibility Model.

Reference
---------
Odeh, M. Sh. (2004). "New Criterion for Lunar Crescent Visibility."
Experimental Astronomy, 18(1), 1–11.

Methodology
-----------
Odeh analyzed an expanded database of 737 historical and modern observations
(including ICOP telescope observations) to establish a visibility parameter V
incorporating optical aid detection limits and a revised Danjon limit of 6.4°:

    ARCV_min(W) = -0.1018*W^3 + 0.7319*W^2 - 6.3226*W + 7.1651
    V = ARCV - ARCV_min(W)

Visibility Zones:
    Zone A (V >= 5.65):
        Easily visible to the naked eye.
    Zone B (2.00 <= V < 5.65):
        Visible by optical aid; can be seen by naked eye under excellent conditions.
    Zone C (-0.96 <= V < 2.00):
        Visible by optical aid only.
    Zone D (V < -0.96 or ARCL < 6.4°):
        Not visible even with optical aid.
"""

from __future__ import annotations

from typing import Any
from al_hilal.astronomy.models import LunarObservationData
from al_hilal.visibility.base import VisibilityModel
from al_hilal.visibility.models import OdehZone, VisibilityAssessment


class OdehModel(VisibilityModel):
    """Odeh (2004) empirical crescent visibility criterion."""

    name = "Odeh (2004)"
    citation = "Odeh, M. Sh. (2004). Experimental Astronomy 18(1), 1–11."

    DANJON_LIMIT_ODEH_DEG = 6.4

    @classmethod
    def calculate_v(cls, arcv_deg: float, w_arcmin: float) -> float:
        """Calculate Odeh V-value given ARCV (degrees) and W (arcminutes)."""
        w = max(0.0, w_arcmin)
        poly = -0.1018 * (w**3) + 0.7319 * (w**2) - 6.3226 * w + 7.1651
        return arcv_deg - poly

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        arcl = obs.arcl_deg
        arcv = obs.arcv_deg
        w = obs.w_arcmin

        v_val = self.calculate_v(arcv, w)

        if arcl < self.DANJON_LIMIT_ODEH_DEG or obs.moon_age_at_sunset_hours <= 0:
            zone = OdehZone.ZONE_D
            is_visible = False
            prob = 0.0
            ci = (0.0, 0.0)
            desc = "Zone D: Below Odeh Danjon limit (ARCL < 6.4°) or before conjunction; invisible."
        elif v_val >= 5.65:
            zone = OdehZone.ZONE_A
            is_visible = True
            prob = 0.97
            ci = (0.92, 1.00)
            desc = "Zone A: Easily visible to the naked eye."
        elif v_val >= 2.00:
            zone = OdehZone.ZONE_B
            is_visible = True
            prob = 0.78
            ci = (0.68, 0.88)
            desc = "Zone B: Visible by optical aid; can be seen by naked eye under pristine skies."
        elif v_val >= -0.96:
            zone = OdehZone.ZONE_C
            is_visible = False  # requires telescope
            prob = 0.32
            ci = (0.20, 0.44)
            desc = "Zone C: Visible by optical aid (telescope/binoculars) only."
        else:
            zone = OdehZone.ZONE_D
            is_visible = False
            prob = 0.01
            ci = (0.00, 0.02)
            desc = "Zone D: Not visible even with conventional optical aid."

        details: dict[str, Any] = {
            "v_value": round(v_val, 4),
            "arcv_deg": round(arcv, 4),
            "arcl_deg": round(arcl, 4),
            "w_arcmin": round(w, 4),
            "zone": zone.value,
        }

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=is_visible,
            criterion_met=is_visible,
            category=zone.value,
            numeric_value=round(v_val, 4),
            probability=prob,
            confidence_interval=ci,
            description=desc,
            details=details,
            citation=self.citation,
        )
