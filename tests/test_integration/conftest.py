"""Integration test specific fixtures.

Provides test data paths and temporary directories specific to integration
testing. Global fixtures are inherited from tests/conftest.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_processing.currency_converter import CurrencyConverter
from data_processing.import_data_xlsx import import_and_process_data


@pytest.fixture(scope="module")
def pln_statement() -> tuple[pd.DataFrame, str]:
    """Return imported PLN statement DataFrame and detected currency.

    Reads ``demo_XTB_broker_statement_currency_PLN.xlsx`` once per module
    so the expensive openpyxl + pandas import is not repeated per test.

    Scope: module — shared across all tests in the module.

    Returns:
        Tuple of ``(df, currency_code)`` from ``import_and_process_data()``.
    """
    _pln_path = (
        Path(__file__).parent.parent.parent
        / "data"
        / "demo_XTB_broker_statement_currency_PLN.xlsx"
    )
    df, currency = import_and_process_data(_pln_path)
    assert df is not None, "Failed to import PLN demo statement"
    return df, currency


@pytest.fixture(scope="module")
def nbp_courses() -> list[str]:
    """Return list of NBP CSV paths for 2025 exchange rate lookups.

    Scope: module — shared across all tests in the module.

    Returns:
        List of string paths to the 2025 NBP archive CSV.
    """
    return [
        str(
            Path(__file__).parent.parent.parent
            / "data"
            / "archiwum_tab_a_2025.csv"
        )
    ]


@pytest.fixture(scope="module")
def currency_converter() -> CurrencyConverter:
    """Return a CurrencyConverter instance with an empty DataFrame.

    Scope: module — shared across all tests in the module.

    Returns:
        CurrencyConverter ready for exchange rate lookups.
    """
    return CurrencyConverter(pd.DataFrame())


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
