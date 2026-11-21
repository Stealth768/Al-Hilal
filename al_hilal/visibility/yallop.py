"""
Yallop (1997) Crescent Visibility Model.

Reference
---------
Yallop, B. D. (1997). "A Method for Predicting the First Sighting of the New
Crescent Moon." HM Nautical Almanac Office, Royal Greenwich Observatory,
NAO Technical Note No. 69.

Methodology
-----------
Yallop tested 295 historical observations (1859–1996) and derived a cubic
polynomial in crescent width W (in arcminutes) against topocentric arc of
vision ARCV (in degrees):

    f(W) = 11.8371 - 6.3226*W + 0.7319*W^2 - 0.1018*W^3
    q = (ARCV - f(W)) / 10

Categories:
    A: q > +0.216              -> Easily visible to the naked eye
    B: +0.216 >= q > -0.014    -> Visible under perfect conditions
    C: -0.014 >= q > -0.160    -> May need optical aid to find crescent
    D: -0.160 >= q > -0.232    -> Will need optical aid to find and see crescent
    E: q <= -0.232 (ARCL > 7°) -> Not visible with conventional telescope
    F: ARCL <= 7.0°            -> Below Danjon limit / physically impossible
"""

from __future__ import annotations

from typing import Any
from al_hilal.astronomy.models import LunarObservationData
from al_hilal.visibility.base import VisibilityModel
from al_hilal.visibility.models import VisibilityAssessment, VisibilityCategory


class YallopModel(VisibilityModel):
    """Yallop (1997) crescent moon visibility algorithm."""

    name = "Yallop (1997)"
    citation = "Yallop, B.D. (1997). NAO Technical Note No. 69, HM Nautical Almanac Office."

    DANJON_LIMIT_DEG = 7.0

    @classmethod
    def calculate_q(cls, arcv_deg: float, w_arcmin: float) -> float:
        """Calculate Yallop q-value given ARCV (degrees) and W (arcminutes)."""
        w = max(0.0, w_arcmin)
        poly = 11.8371 - 6.3226 * w + 0.7319 * (w**2) - 0.1018 * (w**3)
        return (arcv_deg - poly) / 10.0

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        arcl = obs.arcl_deg
        arcv = obs.arcv_deg
        w = obs.w_arcmin

        # Physical impossibility check (Danjon limit or Moon below horizon/conjunction)
        if arcl < self.DANJON_LIMIT_DEG or obs.moon_age_at_sunset_hours <= 0:
            category = VisibilityCategory.F
            q_val = self.calculate_q(arcv, w)
            is_visible = False
            prob = 0.0
            ci = (0.0, 0.0)
            desc = "Category F: Below Danjon limit (ARCL < 7.0°) or before conjunction; physically impossible."
        else:
            q_val = self.calculate_q(arcv, w)
            if q_val > 0.216:
                category = VisibilityCategory.A
                is_visible = True
                prob = 0.98
                ci = (0.94, 1.00)
                desc = "Category A: Easily visible to the naked eye."
            elif q_val > -0.014:
                category = VisibilityCategory.B
                is_visible = True
                prob = 0.75
                ci = (0.65, 0.85)
                desc = "Category B: Visible under perfect conditions."
            elif q_val > -0.160:
                category = VisibilityCategory.C
                is_visible = False  # May require telescope/binoculars
                prob = 0.35
                ci = (0.22, 0.48)
                desc = "Category C: May need optical aid to find crescent; visible with aid."
            elif q_val > -0.232:
                category = VisibilityCategory.D
                is_visible = False  # Requires optical aid
                prob = 0.10
                ci = (0.03, 0.18)
                desc = "Category D: Will need optical aid to find and see crescent."
            else:
                category = VisibilityCategory.E
                is_visible = False
                prob = 0.01
                ci = (0.00, 0.03)
                desc = "Category E: Not visible with conventional telescopes (below optical limit)."

        details: dict[str, Any] = {
            "q_value": round(q_val, 4),
            "arcv_deg": round(arcv, 4),
            "arcl_deg": round(arcl, 4),
            "w_arcmin": round(w, 4),
            "category": category.value,
        }

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=is_visible,
            criterion_met=is_visible,
            category=category.value,
            numeric_value=round(q_val, 4),
            probability=prob,
            confidence_interval=ci,
            description=desc,
            details=details,
            citation=self.citation,
        )
