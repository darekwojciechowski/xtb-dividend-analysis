"""Integration test specific fixtures.

Provides test data paths and temporary directories specific to integration
testing. Global fixtures are inherited from tests/conftest.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def sample_xtb_statement_path() -> Path:
    """Return path to sample XTB statement XLSX file.

    Scope: module - Same file used across all tests in module.

    Returns:
        Path to sample XTB statement in fixtures directory.
    """
    return (
        Path(__file__).parent /
        "fixtures" /
        "sample_xtb_statements" /
        "xtb_statement_sample.xlsx"
    )


@pytest.fixture(scope="function")
def integration_temp_output_dir(tmp_path: Path) -> Path:
    """Provide temporary output directory for integration tests.

    Scope: function - Fresh directory for each test.

    Args:
        tmp_path: pytest built-in temporary directory fixture.

    Returns:
        Path to temporary directory for test outputs.
    """
    output_dir = tmp_path / "integration_output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture(scope="module")
def sample_exchange_rates_path() -> Path:
    """Return path to sample NBP exchange rates CSV file.

    Scope: module - Same rates used across module.

    Returns:
        Path to sample exchange rates CSV in fixtures directory.
    """
    return (
        Path(__file__).parent /
        "fixtures" /
        "exchange_rates" /
        "nbp_rates_sample.csv"
    )
