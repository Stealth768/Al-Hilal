"""
Unit tests for authority profiles, policy engine, and calendar events.
"""

from __future__ import annotations

from datetime import date
import pytest

from al_hilal.policy import (
    AuthorityDecisionType,
    DhulHijjahRule,
    PolicyEngine,
    Sect,
    get_authority_profile,
    load_all_authority_profiles,
)


class TestAuthorityProfiles:
    """Verify loading and structure of data-driven authority profiles."""

    def test_load_all_profiles(self) -> None:
        profiles = load_all_authority_profiles()
        assert len(profiles) >= 10

        expected_ids = [
            "saudi_ummalqura",
            "saudi_supreme_court",
            "indonesia_kemenag",
            "morocco_habous",
            "turkey_diyanet",
            "egypt_dar_al_ifta",
            "pakistan_ruet",
            "oman_mara",
            "usa_fcna",
            "uk_wifaqul_ulama",
            "europe_ecfr",
            "shia_najaf_sistani",
        ]
        for aid in expected_ids:
            assert aid in profiles, f"Missing expected authority profile '{aid}'"

    def test_profile_fields(self) -> None:
        p = get_authority_profile("morocco_habous")
        assert p.name == "Morocco (Habous / Awqaf)"
        assert p.country_code == "MA"
        assert p.decision_type == AuthorityDecisionType.LOCAL_SIGHTING
        assert p.requires_naked_eye is True
        assert len(p.reference_locations) >= 1

    def test_shia_profile_sect(self) -> None:
        """Verify Shia profile has sect set to Sect.SHIA per Decision D."""
        p = get_authority_profile("shia_najaf_sistani")
        assert p.sect == Sect.SHIA
        assert p.requires_naked_eye is True
        assert p.optical_aid_allowed is False


class TestPolicyEngineMonthPrediction:
    """Verify policy engine decisions on historical crescent search dates."""

    def test_ramadan_1445_saudi_vs_morocco(self) -> None:
        """On 2024-03-10 (29 Sha'ban 1445 in Saudi):

        - Saudi Umm al-Qura starts Ramadan on 2024-03-11 (conjunction before sunset, lag > 0).
        - Morocco (strict sighting) finds moon invisible (Danjon/optical limit),
          declares 30 days (istikmal), and starts Ramadan on 2024-03-12.
        """
        engine = PolicyEngine()
        search_date = date(2024, 3, 10)

        # 1. Saudi Umm al-Qura
        saudi_pred = engine.predict_month_start(
            "saudi_ummalqura", hijri_year=1445, hijri_month=9, search_evening_gregorian=search_date
        )
        assert saudi_pred.calculated_start_date == date(2024, 3, 11)
        assert saudi_pred.month_length_preceding == 29
        assert saudi_pred.likely_announced_date == date(2024, 3, 11)

        # 2. Morocco Habous
        morocco_pred = engine.predict_month_start(
            "morocco_habous", hijri_year=1445, hijri_month=9, search_evening_gregorian=search_date
        )
        # Sighting impossible on 10th -> Istikmal 30 days -> Month starts on 12th
        assert morocco_pred.calculated_start_date == date(2024, 3, 12)
        assert morocco_pred.month_length_preceding == 30
        assert morocco_pred.likely_announced_date == date(2024, 3, 12)

    def test_dual_output_calculation_vs_likely_announced(self) -> None:
        """Verify prediction includes both calculated and likely announced dates."""
        engine = PolicyEngine()
        pred = engine.predict_month_start(
            "morocco_habous", hijri_year=1445, hijri_month=9, search_evening_gregorian=date(2024, 3, 10)
        )
        assert pred.calculated_start_date is not None
        assert pred.likely_announced_date is not None
        assert pred.driving_factor != ""
        d = pred.to_dict()
        assert "calculated_start_date" in d
        assert "likely_announced_date" in d
        assert "month_length_preceding" in d


class TestEventDateCalculations:
    """Verify Islamic event date predictions and sect-specific handling."""

    def test_eid_al_fitr_calculation(self) -> None:
        """Eid al-Fitr is always 1st of Shawwal (month 10)."""
        engine = PolicyEngine()
        shawwal_1st = date(2024, 4, 10)
        evt = engine.predict_event_date("eid_al_fitr", 1445, shawwal_1st, "saudi_ummalqura")
        assert evt is not None
        assert evt.gregorian_date == date(2024, 4, 10)
        assert evt.hijri_month == 10
        assert evt.hijri_day == 1

    def test_day_of_arafah_and_eid_al_adha(self) -> None:
        """Day of Arafah is 9th Dhul Hijjah, Eid al-Adha is 10th Dhul Hijjah."""
        engine = PolicyEngine()
        dhul_hijjah_1st = date(2024, 6, 7)

        arafah = engine.predict_event_date("day_of_arafah", 1445, dhul_hijjah_1st, "saudi_ummalqura")
        assert arafah is not None
        assert arafah.gregorian_date == date(2024, 6, 15)  # 7 + 8 days = 15th

        eid_adha = engine.predict_event_date("eid_al_adha", 1445, dhul_hijjah_1st, "saudi_ummalqura")
        assert eid_adha is not None
        assert eid_adha.gregorian_date == date(2024, 6, 16)  # 7 + 9 days = 16th

    def test_sect_specific_mawlid_events(self) -> None:
        """Decision D: Sunni authorities receive Mawlid on 12th; Shia authorities on 17th."""
        engine = PolicyEngine()
        rabi_1st = date(2024, 9, 5)

        # Sunni authority (Saudi Supreme Court)
        sunni_mawlid = engine.predict_event_date("mawlid_sunni", 1446, rabi_1st, "saudi_supreme_court")
        assert sunni_mawlid is not None
        assert sunni_mawlid.gregorian_date == date(2024, 9, 16)  # 5 + 11 = 16th (12th Rabi')

        shia_mawlid_on_sunni = engine.predict_event_date("mawlid_shia", 1446, rabi_1st, "saudi_supreme_court")
        assert shia_mawlid_on_sunni is None  # filtered out

        # Shia authority (Sistani)
        shia_mawlid = engine.predict_event_date("mawlid_shia", 1446, rabi_1st, "shia_najaf_sistani")
        assert shia_mawlid is not None
        assert shia_mawlid.gregorian_date == date(2024, 9, 21)  # 5 + 16 = 21st (17th Rabi')

        sunni_mawlid_on_shia = engine.predict_event_date("mawlid_sunni", 1446, rabi_1st, "shia_najaf_sistani")
        assert sunni_mawlid_on_shia is None  # filtered out
