"""Pytest configuration and shared fixtures."""

import pytest
from hypothesis import settings, Verbosity

# Configure hypothesis for property-based testing
settings.register_profile("default", max_examples=100, verbosity=Verbosity.normal)
settings.register_profile("ci", max_examples=1000, verbosity=Verbosity.verbose)
settings.register_profile("dev", max_examples=10, verbosity=Verbosity.verbose)
settings.load_profile("default")


@pytest.fixture
def sample_timestamp() -> int:
    """Return a sample timestamp."""
    return 1704067200000  # 2024-01-01 00:00:00 UTC
