"""Hypothesis profile registration for fuzz tests."""

from __future__ import annotations

import os

from hypothesis import HealthCheck, settings

settings.register_profile(
    "fuzz-local",
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
settings.register_profile(
    "fuzz-ci",
    max_examples=500,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "fuzz-local"))
