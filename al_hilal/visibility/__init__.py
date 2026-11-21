"""
Crescent visibility and Islamic calendar models sub-package.
"""

from al_hilal.visibility.astronomical import (
    ConjunctionBeforeMiddayUtcModel,
    ConjunctionBeforeSunsetModel,
    MoonAgeThresholdModel,
)
from al_hilal.visibility.base import VisibilityModel
from al_hilal.visibility.classical import DanjonModel, FotheringhamModel, IlyasModel, MaunderModel
from al_hilal.visibility.istanbul import Istanbul2015Model
from al_hilal.visibility.mabims import Mabims2021Model, MabimsLegacyModel
from al_hilal.visibility.models import OdehZone, VisibilityAssessment, VisibilityCategory
from al_hilal.visibility.odeh import OdehModel
from al_hilal.visibility.probabilistic import ProbabilisticEnsembleModel
from al_hilal.visibility.registry import evaluate_all_models, get_model, list_available_models
from al_hilal.visibility.schaefer import SchaeferModel
from al_hilal.visibility.ummalqura import UmmAlQuraModel
from al_hilal.visibility.yallop import YallopModel

__all__ = [
    "VisibilityModel",
    "VisibilityAssessment",
    "VisibilityCategory",
    "OdehZone",
    "YallopModel",
    "OdehModel",
    "DanjonModel",
    "MaunderModel",
    "FotheringhamModel",
    "IlyasModel",
    "Mabims2021Model",
    "MabimsLegacyModel",
    "Istanbul2015Model",
    "UmmAlQuraModel",
    "ConjunctionBeforeSunsetModel",
    "ConjunctionBeforeMiddayUtcModel",
    "MoonAgeThresholdModel",
    "SchaeferModel",
    "ProbabilisticEnsembleModel",
    "list_available_models",
    "get_model",
    "evaluate_all_models",
]
