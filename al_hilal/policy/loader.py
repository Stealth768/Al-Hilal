"""
YAML loader and validator for authority profiles.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
import yaml

from al_hilal.astronomy.models import ObserverLocation
from al_hilal.policy.models import (
    AuthorityDecisionType,
    AuthorityProfile,
    DhulHijjahRule,
    Sect,
)

log = logging.getLogger(__name__)

DEFAULT_AUTHORITIES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "authorities"
_PROFILE_CACHE: dict[str, AuthorityProfile] = {}


def load_authority_profile_from_file(file_path: Path | str) -> AuthorityProfile:
    """Parse a single authority YAML file into an AuthorityProfile instance."""
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    ref_locs = []
    for loc_dict in data.get("reference_locations", []):
        ref_locs.append(
            ObserverLocation(
                latitude=float(loc_dict["latitude"]),
                longitude=float(loc_dict["longitude"]),
                elevation=float(loc_dict.get("elevation", 0.0)),
                name=loc_dict.get("name", ""),
                timezone=loc_dict.get("timezone_str", loc_dict.get("timezone", "UTC")),
            )
        )

    profile = AuthorityProfile(
        id=str(data["id"]).strip().lower(),
        name=str(data["name"]),
        country_code=str(data.get("country_code", "XX")).upper(),
        body_name=str(data.get("body_name", "")),
        decision_type=AuthorityDecisionType(data.get("decision_type", "local_sighting")),
        primary_criterion=str(data.get("primary_criterion", "odeh")),
        reference_locations=ref_locs,
        dhul_hijjah_rule=DhulHijjahRule(data.get("dhul_hijjah_rule", "local_sighting")),
        sect=Sect(data.get("sect", "general")),
        requires_naked_eye=bool(data.get("requires_naked_eye", True)),
        optical_aid_allowed=bool(data.get("optical_aid_allowed", False)),
        min_confidence_for_sighting=float(data.get("min_confidence_for_sighting", 0.5)),
        description=str(data.get("description", "")).strip(),
        official_sources=list(data.get("official_sources", [])),
    )
    return profile


def load_all_authority_profiles(
    directory: Optional[Path | str] = None, force_reload: bool = False
) -> dict[str, AuthorityProfile]:
    """Load all authority YAML profiles from the authorities directory."""
    global _PROFILE_CACHE
    if _PROFILE_CACHE and not force_reload:
        return _PROFILE_CACHE

    target_dir = Path(directory) if directory is not None else DEFAULT_AUTHORITIES_DIR
    if not target_dir.exists():
        log.warning("Authorities directory not found: %s", target_dir)
        return {}

    profiles: dict[str, AuthorityProfile] = {}
    for p in target_dir.glob("*.yaml"):
        try:
            profile = load_authority_profile_from_file(p)
            profiles[profile.id] = profile
        except Exception as e:
            log.error("Failed to load authority profile from %s: %s", p, e)

    _PROFILE_CACHE = profiles
    return _PROFILE_CACHE


def get_authority_profile(authority_id: str) -> AuthorityProfile:
    """Retrieve an authority profile by ID."""
    profiles = load_all_authority_profiles()
    key = authority_id.strip().lower()
    if key not in profiles:
        available = ", ".join(sorted(profiles.keys()))
        raise KeyError(f"Unknown authority '{authority_id}'. Available: {available}")
    return profiles[key]
