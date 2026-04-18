"""Hypothesis profile registration and shared fixtures for fuzz tests."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from hypothesis import HealthCheck, settings

from data_processing.currency_converter import CurrencyConverter
from data_processing.tax_calculator import TaxCalculator

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


@pytest.fixture(autouse=True)
def _fuzz_profile() -> Generator[None, None, None]:
    settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "fuzz-local"))
    yield
    settings.load_profile("default")


@pytest.fixture(scope="session")
def tax_calc() -> TaxCalculator:
    """Uninitialized TaxCalculator — parse methods don't touch self."""
    return TaxCalculator.__new__(TaxCalculator)


@pytest.fixture(scope="session")
def currency_conv() -> CurrencyConverter:
    """Uninitialized CurrencyConverter — extract method doesn't touch self."""
    return CurrencyConverter.__new__(CurrencyConverter)
