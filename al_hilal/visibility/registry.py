"""
Registry and multi-model evaluator for crescent visibility criteria.
"""

from __future__ import annotations

from typing import Any, Optional
from al_hilal.astronomy.models import LunarObservationData
from al_hilal.visibility.astronomical import (
    ConjunctionBeforeMiddayUtcModel,
    ConjunctionBeforeSunsetModel,
    MoonAgeThresholdModel,
)
from al_hilal.visibility.base import VisibilityModel
from al_hilal.visibility.classical import DanjonModel, FotheringhamModel, IlyasModel, MaunderModel
from al_hilal.visibility.istanbul import Istanbul2015Model
from al_hilal.visibility.mabims import Mabims2021Model, MabimsLegacyModel
from al_hilal.visibility.models import VisibilityAssessment
from al_hilal.visibility.odeh import OdehModel
from al_hilal.visibility.probabilistic import ProbabilisticEnsembleModel
from al_hilal.visibility.schaefer import SchaeferModel
from al_hilal.visibility.ummalqura import UmmAlQuraModel
from al_hilal.visibility.yallop import YallopModel

# Standard registry of all implemented models
_MODEL_REGISTRY: dict[str, type[VisibilityModel]] = {
    "yallop": YallopModel,
    "odeh": OdehModel,
    "danjon": DanjonModel,
    "maunder": MaunderModel,
    "fotheringham": FotheringhamModel,
    "ilyas": IlyasModel,
    "mabims_2021": Mabims2021Model,
    "mabims_legacy": MabimsLegacyModel,
    "istanbul_2015": Istanbul2015Model,
    "ummalqura": UmmAlQuraModel,
    "conjunction_sunset": ConjunctionBeforeSunsetModel,
    "conjunction_midday": ConjunctionBeforeMiddayUtcModel,
    "moon_age_15h": lambda: MoonAgeThresholdModel(15.0),  # type: ignore[dict-item]
    "schaefer": SchaeferModel,
    "probabilistic": ProbabilisticEnsembleModel,
}


def list_available_models() -> list[str]:
    """Return keys of all registered visibility and calendar models."""
    return list(_MODEL_REGISTRY.keys())


def get_model(name: str) -> VisibilityModel:
    """Retrieve an instantiated visibility model by name or key.

    Parameters
    ----------
    name:
        Model identifier (e.g. 'yallop', 'odeh', 'mabims_2021', 'ummalqura').
    """
    key = name.lower().strip()
    if key not in _MODEL_REGISTRY:
        available = ", ".join(list_available_models())
        raise KeyError(f"Unknown visibility model '{name}'. Available: {available}")
    factory = _MODEL_REGISTRY[key]
    return factory()


def evaluate_all_models(
    obs: LunarObservationData,
    model_keys: Optional[list[str]] = None,
) -> dict[str, VisibilityAssessment]:
    """Evaluate an observation across all or selected visibility models.

    Parameters
    ----------
    obs:
        The computed lunar observation data.
    model_keys:
        Optional list of model keys to evaluate. If None, evaluates all.

    Returns
    -------
    dict[str, VisibilityAssessment]
        Mapping from model key to the evaluation assessment.
    """
    keys = model_keys if model_keys is not None else list_available_models()
    results: dict[str, VisibilityAssessment] = {}
    for k in keys:
        model = get_model(k)
        results[k] = model.evaluate(obs)
    return results
