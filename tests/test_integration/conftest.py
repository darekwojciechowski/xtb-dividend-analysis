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
from main import process_data


@pytest.fixture(scope="module")
def pln_statement_path() -> Path:
    """Return path to the PLN demo XTB statement XLSX.

    Single source of truth for the PLN demo file path used by all
    integration tests that need to drive the full pipeline.

    Scope: module — path is constant across all tests in the module.

    Returns:
        Absolute ``Path`` to ``data/demo_XTB_broker_statement_currency_PLN.xlsx``.
    """
    return (
        Path(__file__).parent.parent.parent
        / "data"
        / "demo_XTB_broker_statement_currency_PLN.xlsx"
    )


@pytest.fixture(scope="module")
def pln_statement(pln_statement_path: Path) -> tuple[pd.DataFrame, str]:
    """Return imported PLN statement DataFrame and detected currency.

    Reads ``demo_XTB_broker_statement_currency_PLN.xlsx`` once per module
    so the expensive openpyxl + pandas import is not repeated per test.

    Scope: module — shared across all tests in the module.

    Returns:
        Tuple of ``(df, currency_code)`` from ``import_and_process_data()``.

    Args:
        pln_statement_path: Module-scoped fixture providing the XLSX path.
    """
    df, currency = import_and_process_data(pln_statement_path)
    if df is None:
        pytest.fail(
            f"Failed to import PLN demo statement from {pln_statement_path}. "
            "Check that the file exists and is a valid XTB XLSX export."
        )
    return df, currency


@pytest.fixture(scope="module")
def nbp_courses() -> list[str]:
    """Return list of NBP CSV paths for 2025 exchange rate lookups.

    Scope: module — shared across all tests in the module.

    Returns:
        List of string paths to the 2025 NBP archive CSV.
    """
    data_dir = Path(__file__).parent.parent.parent / "data"
    # Include all available annual CSVs so that dividend dates spanning
    # multiple calendar years (e.g. a D-1 falling in late December 2024)
    # can be resolved without a ValueError from the converter.
    years = ["2024", "2025", "2026"]
    return [
        str(data_dir / f"archiwum_tab_a_{y}.csv")
        for y in years
        if (data_dir / f"archiwum_tab_a_{y}.csv").exists()
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

    Raises:
        pytest.skip.Exception: When the fixture file has not yet been added
            to ``tests/test_integration/fixtures/sample_xtb_statements/``.
    """
    path = (
        Path(__file__).parent
        / "fixtures"
        / "sample_xtb_statements"
        / "xtb_statement_sample.xlsx"
    )
    if not path.exists():
        pytest.skip(f"Fixture file not found: {path} — add it to enable these tests.")
    return path


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

    Raises:
        pytest.skip.Exception: When the fixture file has not yet been added
            to ``tests/test_integration/fixtures/exchange_rates/``.
    """
    path = (
        Path(__file__).parent / "fixtures" / "exchange_rates" / "nbp_rates_sample.csv"
    )
    if not path.exists():
        pytest.skip(f"Fixture file not found: {path} — add it to enable these tests.")
    return path


@pytest.fixture(scope="module")
def processed_pln_result(
    pln_statement_path: Path,
    nbp_courses: list[str],
) -> pd.DataFrame:
    """Run the full pipeline once per module and share the result.

    Prevents each integration test from calling ``process_data()`` independently
    with identical inputs, which would waste CI time on repeated openpyxl and
    NBP CSV reads.

    Scope: module — computed once, shared read-only across all tests.

    Args:
        pln_statement_path: Module-scoped fixture providing the XLSX path.
        nbp_courses: Module-scoped fixture providing NBP CSV paths for 2024–2026.

    Returns:
        Processed DataFrame from ``process_data()``.
    """
    return process_data(str(pln_statement_path), nbp_courses)
