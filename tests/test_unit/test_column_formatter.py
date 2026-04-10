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


def _stub_get_previous_business_day(_date):
    return _FAKE_D_MINUS_1


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
        new=_stub_get_previous_business_day,
    )
    def test_date_d_minus_1_no_tax_col_returns_real_date(self) -> None:
        """When 'Tax Collected' column is absent the mask is skipped and a real date is returned.

        Covers the early step-'4a' call before tax extraction has run.
        """
        df = _make_df(tax_collected=None, include_tax_col=False)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("4a")

        assert result["Date D-1"].iloc[0] == _FAKE_D_MINUS_1

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=_stub_get_previous_business_day,
    )
    def test_date_d_minus_1_tax_below_threshold_returns_real_date(self) -> None:
        """When Tax Collected < polish_tax_rate the real D-1 date is kept."""
        df = _make_df(tax_collected=0.15)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("8")

        assert result["Date D-1"].iloc[0] == _FAKE_D_MINUS_1

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=_stub_get_previous_business_day,
    )
    def test_date_d_minus_1_tax_equal_to_threshold_returns_dash(self) -> None:
        """When Tax Collected == polish_tax_rate (>= boundary) 'Date D-1' must show '-'."""
        df = _make_df(tax_collected=0.19)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("8")

        assert result["Date D-1"].iloc[0] == "-"

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=_stub_get_previous_business_day,
    )
    def test_date_d_minus_1_tax_above_threshold_returns_dash(self) -> None:
        """When Tax Collected > polish_tax_rate (e.g. ASB.PL 25.5% WHT) 'Date D-1' must show '-'."""
        df = _make_df(tax_collected=0.255)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("8")

        assert result["Date D-1"].iloc[0] == "-"

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=_stub_get_previous_business_day,
    )
    def test_date_d_minus_1_tax_nan_returns_real_date(self) -> None:
        """When Tax Collected is NaN (no WHT row merged) the real D-1 date is kept."""
        df = _make_df(tax_collected=None)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("8")

        assert result["Date D-1"].iloc[0] == _FAKE_D_MINUS_1


# ---------------------------------------------------------------------------
# TestCreateExchangeRateDMinus1Column
# ---------------------------------------------------------------------------


def _make_exchange_rate_df(
    net_dividend: str,
    tax_collected: float | None,
    date_d_minus_1=pd.Timestamp("2025-05-28"),
) -> pd.DataFrame:
    """Build a minimal single-row DataFrame for exchange rate tests."""
    return pd.DataFrame(
        {
            "Net Dividend": [net_dividend],
            "Tax Collected": [tax_collected],
            "Date D-1": [date_d_minus_1],
        }
    )


@pytest.mark.unit
class TestCreateExchangeRateDMinus1Column:
    """Tests for ColumnFormatter.create_exchange_rate_d_minus_1_column branches."""

    def test_exchange_rate_tax_above_threshold_returns_dash(self) -> None:
        """When Tax Collected >= polish_tax_rate the row returns '-' immediately (lines 162-166)."""
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.19)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 4.0
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "-"

    def test_exchange_rate_invalid_net_dividend_format_returns_dash(self) -> None:
        """When Net Dividend cannot be split into exactly 2 parts returns '-' (line 172)."""
        df = _make_exchange_rate_df("INVALID", tax_collected=0.10)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 4.0
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "-"

    def test_exchange_rate_nan_date_d_minus_1_returns_dash(self) -> None:
        """When Date D-1 is NaN/None returns '-' (line 178)."""
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10, date_d_minus_1=None)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 4.0
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "-"

    def test_exchange_rate_zero_rate_returns_dash(self) -> None:
        """When the looked-up exchange rate is 0.0 returns '-' (line 188)."""
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 0.0
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "-"

    def test_exchange_rate_pln_currency_returns_dash(self) -> None:
        """When currency is PLN and rate is 1.0 returns '-' (line 190)."""
        df = _make_exchange_rate_df("28.22 PLN", tax_collected=0.10)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 1.0
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "-"

    def test_exchange_rate_usd_valid_returns_formatted_rate(self) -> None:
        """Happy path: valid USD row returns formatted rate string."""
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 3.8512
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "3.8512 PLN"


# ---------------------------------------------------------------------------
# TestAddTaxCollectedAmount
# ---------------------------------------------------------------------------


def _make_tax_amount_df(
    net_dividend: str,
    tax_collected: float | None,
    tax_collected_raw: float | None = None,
    include_raw_col: bool = False,
) -> pd.DataFrame:
    """Build a minimal single-row DataFrame for tax collected amount tests."""
    data: dict = {
        "Net Dividend": [net_dividend],
        "Tax Collected": [tax_collected],
    }
    if include_raw_col:
        data["Tax Collected Raw"] = [tax_collected_raw]
    return pd.DataFrame(data)


@pytest.mark.unit
class TestAddTaxCollectedAmount:
    """Tests for ColumnFormatter.add_tax_collected_amount branches."""

    def test_tax_amount_invalid_net_dividend_returns_dash(self) -> None:
        """When Net Dividend has != 2 parts returns '-' (line 227)."""
        df = _make_tax_amount_df("INVALID", tax_collected=0.15)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        assert result["Tax Collected Amount"].iloc[0] == "-"

    def test_tax_amount_non_numeric_dividend_value_returns_dash(self) -> None:
        """When Net Dividend amount cannot be cast to float returns '-' (lines 232-233)."""
        df = _make_tax_amount_df("abc USD", tax_collected=0.15)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        assert result["Tax Collected Amount"].iloc[0] == "-"

    def test_tax_amount_zero_tax_percentage_returns_dash(self) -> None:
        """When Tax Collected is 0 returns '-'."""
        df = _make_tax_amount_df("6.84 USD", tax_collected=0)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        assert result["Tax Collected Amount"].iloc[0] == "-"

    def test_tax_amount_nan_tax_percentage_returns_dash(self) -> None:
        """When Tax Collected is NaN returns '-'."""
        df = _make_tax_amount_df("6.84 USD", tax_collected=None)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        assert result["Tax Collected Amount"].iloc[0] == "-"

    def test_tax_amount_usd_statement_uses_raw_column(self) -> None:
        """For USD statement with Tax Collected Raw column, uses abs(raw) value (lines 241-246)."""
        df = _make_tax_amount_df(
            "6.84 USD",
            tax_collected=0.15,
            tax_collected_raw=-1.21,
            include_raw_col=True,
        )
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="USD")

        assert result["Tax Collected Amount"].iloc[0] == "1.21 USD"

    def test_tax_amount_pln_statement_calculates_from_percentage(self) -> None:
        """For PLN statement, calculates tax amount from net dividend and percentage."""
        df = _make_tax_amount_df("28.22 PLN", tax_collected=0.19)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="PLN")

        # gross = 28.22 / (1 - 0.19) = 34.8395..., tax = gross * 0.19 = 6.6195...
        assert result["Tax Collected Amount"].iloc[0] == "6.62 PLN"
