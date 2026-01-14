"""
Shared pytest configuration and fixtures for all test modules.

This module provides common test fixtures and configuration for the entire test suite,
following pytest best practices and 2026 standards.
"""

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """
    Provides a standard sample DataFrame for testing data processing operations.

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


@pytest.fixture
def sample_dataframe_with_ansi() -> pd.DataFrame:
    """
    Provides a DataFrame with ANSI escape sequences for testing cleanup operations.

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


@pytest.fixture
def empty_dataframe() -> pd.DataFrame:
    """
    Provides an empty DataFrame for testing edge cases.

    Returns:
        Empty pd.DataFrame.
    """
    return pd.DataFrame()


@pytest.fixture
def dataframe_with_missing_values() -> pd.DataFrame:
    """
    Provides a DataFrame with NaN values for testing data validation.

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


@pytest.fixture
def large_dataframe() -> pd.DataFrame:
    """
    Provides a large DataFrame for performance testing.

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


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """
    Provides a temporary directory for test output files.

    Args:
        tmp_path: pytest built-in temporary directory fixture.

    Returns:
        Path object pointing to a temporary test output directory.
    """
    output_dir = tmp_path / "test_output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


# Test markers configuration
def pytest_configure(config: pytest.Config) -> None:
    """
    Configure custom pytest markers for test categorization.

    Args:
        config: pytest configuration object.
    """
    config.addinivalue_line("markers", "unit: Unit tests for individual functions")
    config.addinivalue_line(
        "markers", "integration: Integration tests for multiple components")
    config.addinivalue_line("markers", "performance: Performance and stress tests")
    config.addinivalue_line("markers", "edge_case: Edge case and boundary tests")
