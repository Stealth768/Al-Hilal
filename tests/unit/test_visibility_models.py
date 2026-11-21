"""
Unit tests for crescent visibility models and criteria.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import pytest

from al_hilal.astronomy.models import (
    AtmosphericConditions,
    BodyPosition,
    DeltaTRecord,
    LunarObservationData,
    ObserverLocation,
)
from al_hilal.visibility import (
    ConjunctionBeforeMiddayUtcModel,
    ConjunctionBeforeSunsetModel,
    DanjonModel,
    FotheringhamModel,
    IlyasModel,
    Istanbul2015Model,
    Mabims2021Model,
    MabimsLegacyModel,
    MaunderModel,
    MoonAgeThresholdModel,
    OdehModel,
    OdehZone,
    ProbabilisticEnsembleModel,
    SchaeferModel,
    UmmAlQuraModel,
    VisibilityCategory,
    YallopModel,
    evaluate_all_models,
    get_model,
    list_available_models,
)


def _make_dummy_observation(
    arcl_deg: float = 12.0,
    arcv_deg: float = 10.0,
    w_arcmin: float = 0.5,
    altitude_deg: float = 6.0,
    daz_deg: float = 5.0,
    lag_minutes: float = 45.0,
    moon_age_hours: float = 20.0,
) -> LunarObservationData:
    """Construct a synthetic observation data object for unit testing."""
    sunset = datetime(2024, 3, 11, 15, 30, tzinfo=timezone.utc)
    conjunction = datetime(2024, 3, 10, 19, 30, tzinfo=timezone.utc)
    moonset = datetime(2024, 3, 11, 16, 15, tzinfo=timezone.utc)

    return LunarObservationData(
        observer=ObserverLocation(21.4225, 39.8262, 277.0, "Makkah"),
        observation_date_utc=sunset,
        conditions=AtmosphericConditions(10.0, 1010.0),
        sunset_utc=sunset,
        conjunction_utc=conjunction,
        moon_age_at_sunset_hours=moon_age_hours,
        moon_at_sunset=BodyPosition(altitude_deg, 270.0, 384400.0),
        sun_at_sunset=BodyPosition(-0.833, 265.0, 149597870.0),
        moonset_utc=moonset,
        lag_time_minutes=lag_minutes,
        arcl_deg=arcl_deg,
        arcv_deg=arcv_deg,
        daz_deg=daz_deg,
        w_arcmin=w_arcmin,
        illumination_pct=1.5,
        best_time_utc=None,
        best_time_altitude_deg=None,
        best_time_azimuth_deg=None,
        delta_t=DeltaTRecord(69.2, "IERS", 0.1),
        ephemeris_name="de440s.bsp",
        computed_at_utc=datetime.now(timezone.utc),
        skyfield_version="1.55",
    )


class TestYallopModel:
    """Test Bernard D. Yallop (1997) q-value and classification."""

    def test_q_calculation_formula(self) -> None:
        """Verify Yallop polynomial calculation arithmetic."""
        # For w = 0.5':
        # poly = 11.8371 - 6.3226(0.5) + 0.7319(0.25) - 0.1018(0.125) = 8.8461
        # q = (12.0 - 8.8461) / 10 = 0.3154
        q = YallopModel.calculate_q(arcv_deg=12.0, w_arcmin=0.5)
        assert abs(q - 0.3154) < 0.001

    def test_category_a_easily_visible(self) -> None:
        """q > +0.216 -> Category A."""
        obs = _make_dummy_observation(arcl_deg=15.0, arcv_deg=14.0, w_arcmin=0.6)
        res = YallopModel().evaluate(obs)
        assert res.category == VisibilityCategory.A.value
        assert res.is_visible is True
        assert res.probability >= 0.95

    def test_category_b_perfect_conditions(self) -> None:
        """+0.216 >= q > -0.014 -> Category B."""
        # Choose arcv so q is ~ 0.10
        # poly at w=0.3 is ~ 10.0, so arcv=11.0 -> q = 0.10
        obs = _make_dummy_observation(arcl_deg=10.0, arcv_deg=11.0, w_arcmin=0.3)
        res = YallopModel().evaluate(obs)
        assert res.category == VisibilityCategory.B.value
        assert res.is_visible is True

    def test_category_f_danjon_limit(self) -> None:
        """ARCL < 7.0° -> Category F regardless of ARCV."""
        obs = _make_dummy_observation(arcl_deg=6.5, arcv_deg=10.0, w_arcmin=0.1)
        res = YallopModel().evaluate(obs)
        assert res.category == VisibilityCategory.F.value
        assert res.is_visible is False
        assert res.probability == 0.0


class TestOdehModel:
    """Test Mohammad Sh. Odeh (2004) V-value and zone classification."""

    def test_v_calculation_formula(self) -> None:
        """Verify Odeh polynomial arithmetic."""
        # For w = 0.5':
        # poly = -0.1018(0.125) + 0.7319(0.25) - 6.3226(0.5) + 7.1651 = 4.1741
        # V = 10.0 - 4.1741 = 5.8259
        v = OdehModel.calculate_v(arcv_deg=10.0, w_arcmin=0.5)
        assert abs(v - 5.8259) < 0.002

    def test_zone_a_easily_visible(self) -> None:
        """V >= 5.65 -> Zone A (Naked eye)."""
        obs = _make_dummy_observation(arcl_deg=15.0, arcv_deg=12.0, w_arcmin=0.5)
        res = OdehModel().evaluate(obs)
        assert res.category == OdehZone.ZONE_A.value
        assert res.is_visible is True

    def test_zone_d_below_danjon(self) -> None:
        """ARCL < 6.4° -> Zone D."""
        obs = _make_dummy_observation(arcl_deg=6.2, arcv_deg=8.0, w_arcmin=0.1)
        res = OdehModel().evaluate(obs)
        assert res.category == OdehZone.ZONE_D.value
        assert res.is_visible is False


class TestClassicalModels:
    """Test Danjon, Maunder, Fotheringham, and Ilyas criteria."""

    def test_danjon_limit(self) -> None:
        model = DanjonModel(limit_deg=7.0)
        assert model.evaluate(_make_dummy_observation(arcl_deg=7.5)).criterion_met is True
        assert model.evaluate(_make_dummy_observation(arcl_deg=6.8)).criterion_met is False

    def test_maunder_curve(self) -> None:
        model = MaunderModel()
        # At DAZ=0°, req ARCV is 11.0°
        assert model.evaluate(_make_dummy_observation(daz_deg=0.0, arcv_deg=11.5)).criterion_met is True
        assert model.evaluate(_make_dummy_observation(daz_deg=0.0, arcv_deg=10.5)).criterion_met is False

    def test_fotheringham_curve(self) -> None:
        model = FotheringhamModel()
        # At DAZ=0°, req ARCV is 12.0°
        assert model.evaluate(_make_dummy_observation(daz_deg=0.0, arcv_deg=12.5)).criterion_met is True
        assert model.evaluate(_make_dummy_observation(daz_deg=0.0, arcv_deg=11.5)).criterion_met is False

    def test_ilyas_composite(self) -> None:
        model = IlyasModel()
        # All conditions met
        obs_good = _make_dummy_observation(arcl_deg=11.0, altitude_deg=5.0, lag_minutes=45.0)
        assert model.evaluate(obs_good).criterion_met is True

        # Failed on lag time
        obs_short_lag = _make_dummy_observation(arcl_deg=11.0, altitude_deg=5.0, lag_minutes=30.0)
        assert model.evaluate(obs_short_lag).criterion_met is False


class TestRegionalAndCalendarModels:
    """Test MABIMS, Istanbul 2015, and Umm al-Qura criteria."""

    def test_mabims_2021(self) -> None:
        model = Mabims2021Model()
        # Passing: alt >= 3.0° and elong >= 6.4°
        assert model.evaluate(_make_dummy_observation(altitude_deg=3.5, arcl_deg=7.0)).criterion_met is True
        # Failing on altitude
        assert model.evaluate(_make_dummy_observation(altitude_deg=2.5, arcl_deg=7.0)).criterion_met is False
        # Failing on elongation
        assert model.evaluate(_make_dummy_observation(altitude_deg=4.0, arcl_deg=6.0)).criterion_met is False

    def test_mabims_legacy(self) -> None:
        model = MabimsLegacyModel()
        assert model.evaluate(_make_dummy_observation(altitude_deg=2.2, arcl_deg=3.5, moon_age_hours=10.0)).criterion_met is True

    def test_istanbul_2015(self) -> None:
        model = Istanbul2015Model()
        # Passing: alt >= 5.0° and elong >= 8.0°
        assert model.evaluate(_make_dummy_observation(altitude_deg=5.5, arcl_deg=8.5)).criterion_met is True
        # Failing: alt < 5.0°
        assert model.evaluate(_make_dummy_observation(altitude_deg=4.5, arcl_deg=8.5)).criterion_met is False

    def test_umm_al_qura(self) -> None:
        model = UmmAlQuraModel()
        # Passing: conjunction before sunset (age > 0) and moonset after sunset (lag > 0)
        obs_pass = _make_dummy_observation(moon_age_hours=12.0, lag_minutes=30.0)
        assert model.evaluate(obs_pass).criterion_met is True

        # Failing: conjunction after sunset (age < 0)
        obs_fail_conj = _make_dummy_observation(moon_age_hours=-2.0, lag_minutes=30.0)
        assert model.evaluate(obs_fail_conj).criterion_met is False


class TestAstronomicalAndProbabilistic:
    """Test pure astronomical rules and probabilistic ensemble."""

    def test_conjunction_before_sunset(self) -> None:
        model = ConjunctionBeforeSunsetModel()
        assert model.evaluate(_make_dummy_observation(moon_age_hours=5.0)).criterion_met is True
        assert model.evaluate(_make_dummy_observation(moon_age_hours=-1.0)).criterion_met is False

    def test_moon_age_threshold(self) -> None:
        model = MoonAgeThresholdModel(min_age_hours=15.0)
        assert model.evaluate(_make_dummy_observation(moon_age_hours=16.0)).criterion_met is True
        assert model.evaluate(_make_dummy_observation(moon_age_hours=14.0)).criterion_met is False

    def test_probabilistic_ensemble(self) -> None:
        model = ProbabilisticEnsembleModel()
        obs = _make_dummy_observation(arcl_deg=14.0, arcv_deg=12.0, w_arcmin=0.5)
        res = model.evaluate(obs)
        assert 0.0 <= res.probability <= 1.0
        assert res.confidence_interval[0] <= res.probability <= res.confidence_interval[1]
        assert "Ensemble probability" in res.description

    def test_schaefer_stub_interface(self) -> None:
        model = SchaeferModel()
        res = model.evaluate(_make_dummy_observation(arcl_deg=10.0))
        assert "STUB_DEFERRED" in res.details["status"]


class TestModelRegistry:
    """Test registry discovery and multi-model evaluation."""

    def test_list_and_get_models(self) -> None:
        models = list_available_models()
        assert len(models) >= 12
        assert "yallop" in models
        assert "odeh" in models
        assert "mabims_2021" in models
        assert "ummalqura" in models

        m = get_model("yallop")
        assert isinstance(m, YallopModel)

    def test_evaluate_all_models(self) -> None:
        obs = _make_dummy_observation()
        results = evaluate_all_models(obs)
        assert len(results) >= 12
        assert "yallop" in results
        assert "odeh" in results
        assert "mabims_2021" in results
        assert "ummalqura" in results
        for k, res in results.items():
            assert res.model_name != ""
            d = res.to_dict()
            assert "model_name" in d
            assert "criterion_met" in d
