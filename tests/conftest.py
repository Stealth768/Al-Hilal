"""
Shared pytest fixtures for Al Hilal tests.
"""

from __future__ import annotations

import pytest
from al_hilal.astronomy.models import AtmosphericConditions, ObserverLocation

# ---------------------------------------------------------------------------
# Reference locations (used across multiple test modules)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def loc_makkah() -> ObserverLocation:
    return ObserverLocation(21.4225, 39.8262, 277.0, "Makkah", "Asia/Riyadh")


@pytest.fixture(scope="session")
def loc_jakarta() -> ObserverLocation:
    return ObserverLocation(-6.2088, 106.8456, 8.0, "Jakarta", "Asia/Jakarta")


@pytest.fixture(scope="session")
def loc_london() -> ObserverLocation:
    return ObserverLocation(51.5074, -0.1278, 11.0, "London", "Europe/London")


@pytest.fixture(scope="session")
def loc_new_york() -> ObserverLocation:
    return ObserverLocation(40.7128, -74.0060, 10.0, "New York", "America/New_York")


@pytest.fixture(scope="session")
def loc_karachi() -> ObserverLocation:
    return ObserverLocation(24.8607, 67.0011, 10.0, "Karachi", "Asia/Karachi")


@pytest.fixture(scope="session")
def standard_conditions() -> AtmosphericConditions:
    return AtmosphericConditions(temperature_c=10.0, pressure_hPa=1010.0)
