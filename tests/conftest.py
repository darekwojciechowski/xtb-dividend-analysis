"""
Shared pytest configuration and fixtures for all test modules.

This module provides common test fixtures and configuration for the entire test suite,
following pytest best practices and 2026 standards.

Test Structure:
    tests/
    ├── conftest.py              # Shared fixtures (this file)
    ├── test_unit/               # Unit tests for business logic
    │   ├── test_dataframe_processor.py
    │   ├── test_date_converter.py
    │   ├── test_exporter.py
    │   ├── test_tax_calculator.py
    │   └── test_main.py
    ├── test_integration/        # Integration tests (multiple components)
    │   ├── conftest.py          # Integration-specific fixtures
    │   ├── test_data_pipeline.py
    │   ├── test_data_import_processing.py
    │   └── ... (see tests/test_integration/README.md)
    └── test_security/           # Tests for security/CI scripts
        ├── test_bandit_to_sarif.py
        └── test_security_summary.py

Usage:
    # Run all tests
    pytest
    
    # Run only unit tests
    pytest tests/test_unit/
    
    # Run only security tests
    pytest tests/test_security/ -m security
    
    # Run with coverage
    pytest --cov=data_processing --cov=scripts
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import pytest
from hypothesis import HealthCheck, settings
from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Generator

# ---------------------------------------------------------------------------
# Hypothesis global profile
# Registered here so every @given test picks it up without per-test @settings.
# max_examples=50 keeps the CI run fast while still exercising edge cases;
# suppress HealthCheck.too_slow to avoid flaky timeouts on slow runners.
# ---------------------------------------------------------------------------
settings.register_profile(
    "default",
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("default")


@pytest.fixture(scope="session")
def _base_sample_dataframe() -> pd.DataFrame:
    """
    Session-level, private source-of-truth DataFrame. Never mutated directly.

    Scope: session - Created once; consumed only through the function-scoped
    public wrapper ``sample_dataframe`` which returns a per-test copy.

    Returns:
        pd.DataFrame with typical transaction data including Date, Ticker, Amount, etc.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-02"],
            "Ticker": ["AAPL", "MSFT"],
            "Amount": [10.12345, 20.6789],
            "Type": ["Cash", "Cash"],
            "Comment": ["Dividend", "Dividend"],
            "Net Dividend": [8.4, 16.5],
            "Shares": [1, 2],
            "Tax Collected": [2.5, 4.9],
            "Currency": ["USD", "USD"],
        }
    )
    df["Date"] = pd.to_datetime(df["Date"])
    return df


@pytest.fixture(scope="function")
def sample_dataframe(_base_sample_dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Provides a per-test copy of the standard sample DataFrame.

    Scope: function - Each test receives an independent copy so mutations
    (e.g. column assignments) cannot leak between tests.

    Args:
        _base_sample_dataframe: Session-level source DataFrame.

    Returns:
        pd.DataFrame copy safe for mutation within a single test.
    """
    return _base_sample_dataframe.copy()


@pytest.fixture(scope="session")
def _base_sample_dataframe_with_ansi() -> pd.DataFrame:
    """
    Session-level, private source-of-truth DataFrame containing ANSI sequences.

    Scope: session - Created once; consumed only through the function-scoped
    public wrapper ``sample_dataframe_with_ansi``.

    Returns:
        pd.DataFrame containing ANSI-colored ticker symbols.
    """
    return pd.DataFrame(
        {
            "Ticker": ["AAPL", "\x1b[31mMSFT\x1b[0m"],
            "Amount": [10.12345, 20.6789],
            "Type": ["Cash", "Cash"],
            "Comment": ["Dividend", None],
        }
    )


@pytest.fixture(scope="function")
def sample_dataframe_with_ansi(
    _base_sample_dataframe_with_ansi: pd.DataFrame,
) -> pd.DataFrame:
    """
    Provides a per-test copy of the ANSI-decorated DataFrame.

    Scope: function - Each test receives an independent copy so mutations
    cannot leak between tests.

    Args:
        _base_sample_dataframe_with_ansi: Session-level source DataFrame.

    Returns:
        pd.DataFrame copy safe for mutation within a single test.
    """
    return _base_sample_dataframe_with_ansi.copy()


@pytest.fixture(scope="session")
def empty_dataframe() -> pd.DataFrame:
    """
    Provides an empty DataFrame for testing edge cases.

    Scope: session - Empty DataFrame is immutable.

    Returns:
        Empty pd.DataFrame.
    """
    return pd.DataFrame()


@pytest.fixture(scope="session")
def _base_dataframe_with_missing_values() -> pd.DataFrame:
    """
    Session-level, private source-of-truth DataFrame containing NaN values.

    Scope: session - Created once; consumed only through the function-scoped
    public wrapper ``dataframe_with_missing_values``.

    Returns:
        pd.DataFrame containing None/NaN values.
    """
    return pd.DataFrame(
        {
            "Date": ["2024-01-01", None],
            "Ticker": ["AAPL", None],
            "Amount": [10.0, None],
            "Type": ["Cash", None],
            "Comment": ["Dividend", None],
        }
    )


@pytest.fixture(scope="function")
def dataframe_with_missing_values(
    _base_dataframe_with_missing_values: pd.DataFrame,
) -> pd.DataFrame:
    """
    Provides a per-test copy of the DataFrame containing NaN values.

    Scope: function - Each test receives an independent copy so mutations
    cannot leak between tests.

    Args:
        _base_dataframe_with_missing_values: Session-level source DataFrame.

    Returns:
        pd.DataFrame copy safe for mutation within a single test.
    """
    return _base_dataframe_with_missing_values.copy()


@pytest.fixture(scope="session")
def large_dataframe() -> pd.DataFrame:
    """
    Provides a large DataFrame for performance testing.

    Scope: session - Large dataset creation is expensive; share across tests.

    Returns:
        pd.DataFrame with 10,000 rows.
    """
    size = 10000
    return pd.DataFrame(
        {
            "Date": pd.date_range(start="2024-01-01", periods=size, freq="D"),
            "Ticker": ["AAPL"] * size,
            "Amount": [10.0] * size,
            "Type": ["Cash"] * size,
            "Comment": ["Dividend"] * size,
        }
    )


@pytest.fixture(scope="function")
def temp_output_dir(tmp_path: Path) -> Path:
    """
    Provides a temporary directory for test output files.

    Scope: function - Each test gets its own isolated temporary directory.

    Args:
        tmp_path: pytest built-in temporary directory fixture.

    Returns:
        Path object pointing to a temporary test output directory.
    """
    output_dir = tmp_path / "test_output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture(scope="session", autouse=True)
def configure_test_logging() -> Generator[None, None, None]:
    """
    Configure loguru logger for test environment.

    Scope: session - Configure once for all tests.
    Autouse: True - Automatically applied to all tests.

    Yields:
        None - Cleanup happens after all tests complete.
    """
    # Remove default handler and configure for tests
    logger.remove()
    logger.add(
        lambda msg: None,  # Suppress output during tests
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    yield

    # Cleanup after all tests
    logger.remove()


# Marker definitions live exclusively in pyproject.toml [tool.pytest.ini_options].
# Duplicating them here with addinivalue_line caused warnings under --strict-markers
# (pytest 9+). The pytest_configure hook has been removed.
