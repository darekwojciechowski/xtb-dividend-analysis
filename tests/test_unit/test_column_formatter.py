"""Unit tests for ColumnFormatter.create_date_d_minus_1_column.

Verifies that 'Date D-1' shows '-' when Tax Collected >= polish_tax_rate
and a real date otherwise, mirroring the behaviour of 'Exchange Rate D-1'.
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from data_processing.column_formatter import ColumnFormatter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_D_MINUS_1 = pd.Timestamp("2025-05-28")


def _make_df(tax_collected: float | None, include_tax_col: bool = True) -> pd.DataFrame:
    """Build a minimal single-row DataFrame for testing.

    Args:
        tax_collected: Value to place in the 'Tax Collected' column,
            or ``None`` to represent a NaN entry.
        include_tax_col: When ``False`` the 'Tax Collected' column is
            omitted entirely (simulates the early step-"4a" call).

    Returns:
        DataFrame with a 'Date' column (and optionally 'Tax Collected').
    """
    data: dict = {"Date": [pd.Timestamp("2025-05-29")]}
    if include_tax_col:
        data["Tax Collected"] = [tax_collected]
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateDateDMinus1Column:
    """Tests for ColumnFormatter.create_date_d_minus_1_column tax-rate mask."""

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=lambda _: _FAKE_D_MINUS_1,
    )
    def test_date_d_minus_1_no_tax_col_returns_real_date(self):
        """When 'Tax Collected' column is absent the mask is skipped and a real date is returned.

        Covers the early step-'4a' call before tax extraction has run.
        """
        df = _make_df(tax_collected=None, include_tax_col=False)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("4a")

        assert result["Date D-1"].iloc[0] == _FAKE_D_MINUS_1

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=lambda _: _FAKE_D_MINUS_1,
    )
    def test_date_d_minus_1_tax_below_threshold_returns_real_date(self):
        """When Tax Collected < polish_tax_rate the real D-1 date is kept."""
        df = _make_df(tax_collected=0.15)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("8")

        assert result["Date D-1"].iloc[0] == _FAKE_D_MINUS_1

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=lambda _: _FAKE_D_MINUS_1,
    )
    def test_date_d_minus_1_tax_equal_to_threshold_returns_dash(self):
        """When Tax Collected == polish_tax_rate (>= boundary) 'Date D-1' must show '-'."""
        df = _make_df(tax_collected=0.19)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("8")

        assert result["Date D-1"].iloc[0] == "-"

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=lambda _: _FAKE_D_MINUS_1,
    )
    def test_date_d_minus_1_tax_above_threshold_returns_dash(self):
        """When Tax Collected > polish_tax_rate (e.g. ASB.PL 25.5% WHT) 'Date D-1' must show '-'."""
        df = _make_df(tax_collected=0.255)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("8")

        assert result["Date D-1"].iloc[0] == "-"

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=lambda _: _FAKE_D_MINUS_1,
    )
    def test_date_d_minus_1_tax_nan_returns_real_date(self):
        """When Tax Collected is NaN (no WHT row merged) the real D-1 date is kept."""
        df = _make_df(tax_collected=None)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("8")

        assert result["Date D-1"].iloc[0] == _FAKE_D_MINUS_1
