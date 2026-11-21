"""
Milestone 3 Policy Engine Multi-Authority Verification Script.

Demonstrates how real Islamic authorities decide differently on the exact same moon:
  1. Ramadan 1445H Start (Search Eve: 2024-03-10)
  2. Shawwal 1445H / Eid al-Fitr (Search Eve: 2024-04-08)
  3. Dhul Hijjah 1444H / Arafah & Eid al-Adha (Search Eve: 2023-06-18)
  4. Sectarian event date resolutions (Sunni vs Shia Mawlid)
"""

from __future__ import annotations

from datetime import date
from al_hilal.policy import PolicyEngine, load_all_authority_profiles


def main() -> None:
    engine = PolicyEngine()
    profiles = load_all_authority_profiles()

    print("=" * 115)
    print("AL HILAL - MILESTONE 3: MULTI-AUTHORITY POLICY ENGINE BENCHMARK")
    print(f"Loaded {len(profiles)} Official Authority Profiles from data/authorities/")
    print("=" * 115)

    # ── CASE 1: Ramadan 1445H (Eve of 10 March 2024) ──────────────────────
    search_date_ramadan = date(2024, 3, 10)
    print(f"\n[CASE 1] RAMADAN 1445H OBSERVATION EVENING: {search_date_ramadan} (29 Sha'ban in KSA)")
    print("-" * 115)
    print(f"{'Authority':<35} | {'Decision Type':<16} | {'Calc Date':<10} | {'Announced':<10} | {'Len':<4} | {'Driving Factor'}")
    print("-" * 115)

    for pid in [
        "saudi_ummalqura",
        "saudi_supreme_court",
        "turkey_diyanet",
        "indonesia_kemenag",
        "morocco_habous",
        "egypt_dar_al_ifta",
        "pakistan_ruet",
        "oman_mara",
        "usa_fcna",
        "uk_wifaqul_ulama",
        "shia_najaf_sistani",
    ]:
        pred = engine.predict_month_start(pid, hijri_year=1445, hijri_month=9, search_evening_gregorian=search_date_ramadan)
        print(
            f"{pred.authority_name[:35]:<35} | "
            f"{pred.details['decision_type']:<16} | "
            f"{pred.calculated_start_date.isoformat():<10} | "
            f"{pred.likely_announced_date.isoformat():<10} | "
            f"{pred.month_length_preceding:<4} | "
            f"{pred.driving_factor[:40]}"
        )

    # ── CASE 2: Dhul Hijjah 1444H / Day of Arafah & Eid al-Adha ───────────
    search_date_dh = date(2023, 6, 18)
    print(f"\n[CASE 2] DHUL HIJJAH 1444H (HAJJ & EID AL-ADHA) SEARCH EVE: {search_date_dh}")
    print("-" * 115)
    print(f"{'Authority':<35} | {'Dhul Hijjah 1st':<15} | {'Day of Arafah (9th)':<20} | {'Eid al-Adha (10th)':<20}")
    print("-" * 115)

    for pid in ["saudi_ummalqura", "turkey_diyanet", "morocco_habous", "pakistan_ruet", "indonesia_kemenag"]:
        pred = engine.predict_month_start(pid, hijri_year=1444, hijri_month=12, search_evening_gregorian=search_date_dh)
        start_1st = pred.likely_announced_date
        arafah = engine.predict_event_date("day_of_arafah", 1444, start_1st, pid)
        eid = engine.predict_event_date("eid_al_adha", 1444, start_1st, pid)
        print(
            f"{pred.authority_name[:35]:<35} | "
            f"{start_1st.isoformat():<15} | "
            f"{arafah.gregorian_date.isoformat() if arafah else 'N/A':<20} | "
            f"{eid.gregorian_date.isoformat() if eid else 'N/A':<20}"
        )

    # ── CASE 3: Sectarian Event Divergence (Decision D) ───────────────────
    print(f"\n[CASE 3] SECTARIAN EVENT RESOLUTION (DECISION D): MAWLID AL-NABI 1446H")
    print("-" * 115)
    rabi_1st = date(2024, 9, 5)
    for pid in ["saudi_supreme_court", "shia_najaf_sistani"]:
        p = profiles[pid]
        sunni_m = engine.predict_event_date("mawlid_sunni", 1446, rabi_1st, p)
        shia_m = engine.predict_event_date("mawlid_shia", 1446, rabi_1st, p)
        print(f"Profile: {p.name} (Sect: {p.sect.value.upper()})")
        if sunni_m:
            print(f"  -> Sunni Mawlid (12th Rabi' al-Awwal): {sunni_m.gregorian_date.isoformat()} ({sunni_m.name_ar})")
        if shia_m:
            print(f"  -> Shia Mawlid  (17th Rabi' al-Awwal): {shia_m.gregorian_date.isoformat()} ({shia_m.name_ar})")

    print("=" * 115)


if __name__ == "__main__":
    main()
