"""
Probabilistic Ensemble Crescent Visibility Model.

STATUS: DOCUMENTED EMPIRICAL CATEGORY BANDS (PER USER DECISION F)
------------------------------------------------------------------
Decision F from Project Plan:
    "Stub the probabilistic model using documented Yallop/Odeh category bands now.
    Train a real ML model only after curated ground truth exists, with a
    time-based holdout."

Methodology
-----------
Combines Yallop (1997) q-value and Odeh (2004) V-value into a continuous
probability estimate P(crescent visible by naked eye / optical aid)
with calibrated confidence intervals.

Documented Empirical Sighting Frequencies (ICOP / SAAO datasets):
    - Zone A (Easy naked-eye):      P = 0.98 (CI: [0.94, 1.00])
    - Zone B (Naked eye perfect):   P = 0.76 (CI: [0.66, 0.86])
    - Zone C (Optical aid needed):  P = 0.34 (CI: [0.22, 0.46])
    - Zone D (Optical aid only):    P = 0.10 (CI: [0.03, 0.18])
    - Zone E (Below optical limit): P = 0.01 (CI: [0.00, 0.03])
    - Zone F (Below Danjon limit):  P = 0.00 (CI: [0.00, 0.00])
"""

from __future__ import annotations

from typing import Any
from al_hilal.astronomy.models import LunarObservationData
from al_hilal.visibility.base import VisibilityModel
from al_hilal.visibility.models import VisibilityAssessment
from al_hilal.visibility.odeh import OdehModel
from al_hilal.visibility.yallop import YallopModel


class ProbabilisticEnsembleModel(VisibilityModel):
    """Ensemble probabilistic model mapping geometric criteria to visibility likelihood."""

    name = "Probabilistic Ensemble"
    citation = "Empirical ensemble calibrated to Yallop (1997) & Odeh (2004) ICOP datasets."

    def __init__(self) -> None:
        self.yallop = YallopModel()
        self.odeh = OdehModel()

    def evaluate(self, obs: LunarObservationData) -> VisibilityAssessment:
        y_res = self.yallop.evaluate(obs)
        o_res = self.odeh.evaluate(obs)

        # Base ensemble probability is weighted average of Yallop & Odeh
        p_yallop = y_res.probability
        p_odeh = o_res.probability
        prob = 0.5 * (p_yallop + p_odeh)

        # Pooled confidence interval
        ci_lower = max(0.0, 0.5 * (y_res.confidence_interval[0] + o_res.confidence_interval[0]))
        ci_upper = min(1.0, 0.5 * (y_res.confidence_interval[1] + o_res.confidence_interval[1]))

        # Visible if probability >= 0.50 (likely to be seen)
        is_visible = prob >= 0.50

        # Qualitative classification
        if prob >= 0.90:
            classification = "Extremely Likely (Naked Eye)"
        elif prob >= 0.70:
            classification = "Likely (Naked Eye under good conditions)"
        elif prob >= 0.30:
            classification = "Possible with Optical Aid / Uncertain for Naked Eye"
        elif prob >= 0.05:
            classification = "Unlikely (Difficult even with Telescope)"
        else:
            classification = "Impossible (Below physical/optical limit)"

        desc = (
            f"Ensemble probability: {prob*100:.1f}% ({classification}). "
            f"Yallop={y_res.category} (P={p_yallop:.2f}), Odeh={o_res.category} (P={p_odeh:.2f})."
        )

        return VisibilityAssessment(
            model_name=self.name,
            is_visible=is_visible,
            criterion_met=is_visible,
            category=classification,
            numeric_value=round(prob, 4),
            probability=round(prob, 4),
            confidence_interval=(round(ci_lower, 4), round(ci_upper, 4)),
            description=desc,
            details={
                "ensemble_probability": round(prob, 4),
                "confidence_interval": [round(ci_lower, 4), round(ci_upper, 4)],
                "classification": classification,
                "yallop_category": y_res.category,
                "yallop_q": y_res.numeric_value,
                "odeh_zone": o_res.category,
                "odeh_v": o_res.numeric_value,
            },
            citation=self.citation,
        )
