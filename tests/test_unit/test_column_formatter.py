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

    def test_exchange_rate_converter_created_with_df(self) -> None:
        """CurrencyConverter is constructed with self.df, not None (kills mutmut_3)."""
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 3.85
            formatter.create_exchange_rate_d_minus_1_column([])

        MockCC.assert_called_once_with(df)

    def test_exchange_rate_injected_converter_is_reused(self) -> None:
        """When _converter is pre-injected it is used directly; no new CurrencyConverter (kills mutmut_3 via injection path)."""
        from unittest.mock import MagicMock

        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10)
        mock_converter = MagicMock()
        mock_converter.get_exchange_rate.return_value = 4.20
        formatter = ColumnFormatter(df, converter=mock_converter)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            result = formatter.create_exchange_rate_d_minus_1_column([])
            MockCC.assert_not_called()

        assert result["Exchange Rate D-1"].iloc[0] == "4.2000 PLN"

    def test_exchange_rate_rate_one_non_pln_returns_formatted_rate(self) -> None:
        """rate == 1.0 with non-PLN currency must return a formatted rate, not '-' (kills mutmut_80)."""
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 1.0
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "1.0000 PLN"

    def test_exchange_rate_get_exchange_rate_receives_correct_date_format(self) -> None:
        """get_exchange_rate must be called with a YYYY-MM-DD date string (kills mutmut_64, 67-69)."""
        d_minus_1 = pd.Timestamp("2025-05-28")
        df = _make_exchange_rate_df(
            "6.84 USD", tax_collected=0.10, date_d_minus_1=d_minus_1
        )
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 3.85
            formatter.create_exchange_rate_d_minus_1_column(["/some/path"])

        _args, _kwargs = MockCC.return_value.get_exchange_rate.call_args
        date_arg = _args[1]
        assert date_arg == "2025-05-28"

    def test_exchange_rate_get_exchange_rate_receives_courses_paths_and_currency(
        self,
    ) -> None:
        """get_exchange_rate must receive courses_paths[0] and extracted currency (kills mutmut_71-76)."""
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10)
        formatter = ColumnFormatter(df)
        courses_paths = ["/path/a", "/path/b"]

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 3.85
            formatter.create_exchange_rate_d_minus_1_column(courses_paths)

        _args, _kwargs = MockCC.return_value.get_exchange_rate.call_args
        assert _args[0] == courses_paths
        assert _args[2] == "USD"

    def test_exchange_rate_parse_receives_ticker_and_date_from_row(self) -> None:
        """_parse_value_with_currency must receive the row's Ticker and Date (kills mutmut_32-53)."""
        df = pd.DataFrame(
            {
                "Net Dividend": ["6.84 USD"],
                "Tax Collected": [0.10],
                "Date D-1": [pd.Timestamp("2025-05-28")],
                "Ticker": ["AAPL"],
                "Date": [pd.Timestamp("2025-05-29")],
            }
        )
        formatter = ColumnFormatter(df)

        with (
            patch("data_processing.column_formatter.CurrencyConverter") as MockCC,
            patch(
                "data_processing.column_formatter.TaxCalculator._parse_value_with_currency",
                return_value=(6.84, "USD"),
            ) as mock_parse,
        ):
            MockCC.return_value.get_exchange_rate.return_value = 3.85
            formatter.create_exchange_rate_d_minus_1_column([])

        mock_parse.assert_called_once()
        call_args = mock_parse.call_args[0]
        assert call_args[0] == "6.84 USD"  # net_dividend_str
        assert call_args[1] == "Net Dividend"  # label (kills mutmut_51-60)
        assert call_args[2] == "AAPL"  # ticker (kills mutmut_32-39)
        assert "2025-05-29" in call_args[3]  # date (kills mutmut_40-48)

    def test_exchange_rate_missing_tax_collected_key_proceeds_to_rate(self) -> None:
        """Row without 'Tax Collected' key skips the tax check and returns the rate (kills mutmut_7)."""
        df = pd.DataFrame(
            {
                "Net Dividend": ["6.84 USD"],
                "Date D-1": [pd.Timestamp("2025-05-28")],
            }
        )
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 3.85
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "3.8500 PLN"

    def test_exchange_rate_tax_nan_does_not_return_dash_early(self) -> None:
        """NaN Tax Collected must not trigger early '-' return (kills mutmut_11)."""
        df = _make_exchange_rate_df("6.84 USD", tax_collected=None)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 3.85
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "3.8500 PLN"

    def test_exchange_rate_step9_logged(self) -> None:
        """Step 9 message is emitted to the logger (kills mutmut_96-99)."""
        from unittest.mock import MagicMock

        import data_processing.column_formatter as mod

        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10)
        formatter = ColumnFormatter(df)
        captured: list[str] = []

        mock_log = MagicMock(
            side_effect=lambda msg, *a, **kw: captured.append(str(msg))
        )

        with (
            patch("data_processing.column_formatter.CurrencyConverter") as MockCC,
            patch.object(mod.logger, "info", mock_log),
        ):
            MockCC.return_value.get_exchange_rate.return_value = 3.85
            formatter.create_exchange_rate_d_minus_1_column([])

        assert any("Step 9" in m and "Exchange Rate D-1" in m for m in captured)


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
