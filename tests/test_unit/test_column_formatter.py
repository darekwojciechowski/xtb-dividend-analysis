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
        """Arrange: 'Tax Collected' column is absent.
        Act: create the Date D-1 column at step '4a'.
        Assert: Date D-1 holds the real previous business day date.
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
        """Arrange: Tax Collected is 0.15, below the Polish 19% threshold.
        Act: create the Date D-1 column at step '8'.
        Assert: Date D-1 holds the real previous business day date.
        """
        df = _make_df(tax_collected=0.15)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("8")

        assert result["Date D-1"].iloc[0] == _FAKE_D_MINUS_1

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=_stub_get_previous_business_day,
    )
    def test_date_d_minus_1_tax_equal_to_threshold_returns_dash(self) -> None:
        """Arrange: Tax Collected is 0.19, at the Polish tax threshold.
        Act: create the Date D-1 column at step '8'.
        Assert: Date D-1 is '-'.
        """
        df = _make_df(tax_collected=0.19)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("8")

        assert result["Date D-1"].iloc[0] == "-"

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=_stub_get_previous_business_day,
    )
    def test_date_d_minus_1_tax_above_threshold_returns_dash(self) -> None:
        """Arrange: Tax Collected is 0.255, above the Polish tax threshold (ASB.PL case).
        Act: create the Date D-1 column at step '8'.
        Assert: Date D-1 is '-'.
        """
        df = _make_df(tax_collected=0.255)
        formatter = ColumnFormatter(df)

        result = formatter.create_date_d_minus_1_column("8")

        assert result["Date D-1"].iloc[0] == "-"

    @patch(
        "data_processing.column_formatter.CurrencyConverter.get_previous_business_day",
        new=_stub_get_previous_business_day,
    )
    def test_date_d_minus_1_tax_nan_returns_real_date(self) -> None:
        """Arrange: Tax Collected is NaN, indicating no WHT row was merged.
        Act: create the Date D-1 column at step '8'.
        Assert: Date D-1 holds the real previous business day date.
        """
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
        """Arrange: Tax Collected is 0.19, at the Polish tax threshold.
        Act: create the Exchange Rate D-1 column.
        Assert: Exchange Rate D-1 is '-'.
        """
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.19)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 4.0
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "-"

    def test_exchange_rate_invalid_net_dividend_format_returns_dash(self) -> None:
        """Arrange: Net Dividend cannot be split into exactly 2 parts.
        Act: create the Exchange Rate D-1 column.
        Assert: Exchange Rate D-1 is '-'.
        """
        df = _make_exchange_rate_df("INVALID", tax_collected=0.10)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 4.0
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "-"

    def test_exchange_rate_nan_date_d_minus_1_returns_dash(self) -> None:
        """Arrange: Date D-1 is NaN/None.
        Act: create the Exchange Rate D-1 column.
        Assert: Exchange Rate D-1 is '-'.
        """
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10, date_d_minus_1=None)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 4.0
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "-"

    def test_exchange_rate_zero_rate_returns_dash(self) -> None:
        """Arrange: Exchange rate lookup returns 0.0.
        Act: create the Exchange Rate D-1 column.
        Assert: Exchange Rate D-1 is '-'.
        """
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 0.0
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "-"

    def test_exchange_rate_pln_currency_returns_dash(self) -> None:
        """Arrange: Currency is PLN and rate is 1.0.
        Act: create the Exchange Rate D-1 column.
        Assert: Exchange Rate D-1 is '-'.
        """
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
        """Arrange: Exchange Rate D-1 column creation is requested.
        Act: create the Exchange Rate D-1 column.
        Assert: CurrencyConverter is instantiated with self.df.
        """
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 3.85
            formatter.create_exchange_rate_d_minus_1_column([])

        MockCC.assert_called_once_with(df)

    def test_exchange_rate_injected_converter_is_reused(self) -> None:
        """Arrange: CurrencyConverter is pre-injected via the converter parameter.
        Act: create the Exchange Rate D-1 column.
        Assert: The injected converter is used; no new CurrencyConverter is instantiated.
        """
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
        """Arrange: Exchange rate is 1.0 but currency is non-PLN (USD).
        Act: create the Exchange Rate D-1 column.
        Assert: Exchange Rate D-1 is formatted rate, not '-'.
        """
        df = _make_exchange_rate_df("6.84 USD", tax_collected=0.10)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 1.0
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "1.0000 PLN"

    def test_exchange_rate_get_exchange_rate_receives_correct_date_format(self) -> None:
        """Arrange: Date D-1 is a pandas Timestamp.
        Act: create the Exchange Rate D-1 column.
        Assert: get_exchange_rate receives the date as a 'YYYY-MM-DD' string.
        """
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
        """Arrange: courses_paths list and currency code are provided.
        Act: create the Exchange Rate D-1 column.
        Assert: get_exchange_rate receives courses_paths and extracted currency.
        """
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
        """Arrange: Row contains Ticker, Date, and Net Dividend.
        Act: create the Exchange Rate D-1 column.
        Assert: _parse_value_with_currency receives the row's Ticker and Date.
        """
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
        """Arrange: Row lacks the 'Tax Collected' column.
        Act: create the Exchange Rate D-1 column.
        Assert: Tax check is skipped and the exchange rate is returned.
        """
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
        """Arrange: Tax Collected is NaN.
        Act: create the Exchange Rate D-1 column.
        Assert: NaN Tax Collected does not trigger early '-' return.
        """
        df = _make_exchange_rate_df("6.84 USD", tax_collected=None)
        formatter = ColumnFormatter(df)

        with patch("data_processing.column_formatter.CurrencyConverter") as MockCC:
            MockCC.return_value.get_exchange_rate.return_value = 3.85
            result = formatter.create_exchange_rate_d_minus_1_column([])

        assert result["Exchange Rate D-1"].iloc[0] == "3.8500 PLN"

    def test_exchange_rate_step9_logged(self) -> None:
        """Arrange: Column creation is requested.
        Act: create the Exchange Rate D-1 column.
        Assert: Step 9 message is logged.
        """
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
        """Arrange: Net Dividend has != 2 parts.
        Act: add Tax Collected Amount column.
        Assert: Tax Collected Amount is '-'.
        """
        df = _make_tax_amount_df("INVALID", tax_collected=0.15)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        assert result["Tax Collected Amount"].iloc[0] == "-"

    def test_tax_amount_non_numeric_dividend_value_returns_dash(self) -> None:
        """Arrange: Net Dividend amount cannot be parsed as float.
        Act: add Tax Collected Amount column.
        Assert: Tax Collected Amount is '-'.
        """
        df = _make_tax_amount_df("abc USD", tax_collected=0.15)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        assert result["Tax Collected Amount"].iloc[0] == "-"

    def test_tax_amount_zero_tax_percentage_returns_dash(self) -> None:
        """Arrange: Tax Collected is 0.
        Act: add Tax Collected Amount column.
        Assert: Tax Collected Amount is '-'.
        """
        df = _make_tax_amount_df("6.84 USD", tax_collected=0)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        assert result["Tax Collected Amount"].iloc[0] == "-"

    def test_tax_amount_nan_tax_percentage_returns_dash(self) -> None:
        """Arrange: Tax Collected is NaN.
        Act: add Tax Collected Amount column.
        Assert: Tax Collected Amount is '-'.
        """
        df = _make_tax_amount_df("6.84 USD", tax_collected=None)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        assert result["Tax Collected Amount"].iloc[0] == "-"

    def test_tax_amount_usd_statement_uses_raw_column(self) -> None:
        """Arrange: USD statement with Tax Collected Raw column set to -1.21.
        Act: add Tax Collected Amount column.
        Assert: Tax Collected Amount uses absolute value of raw column.
        """
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
        """Arrange: PLN statement with 28.22 PLN dividend and 19% tax.
        Act: add Tax Collected Amount column.
        Assert: Tax amount is calculated as gross × 19%.
        """
        df = _make_tax_amount_df("28.22 PLN", tax_collected=0.19)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="PLN")

        # gross = 28.22 / (1 - 0.19) = 34.8395..., tax = gross * 0.19 = 6.6195...
        assert result["Tax Collected Amount"].iloc[0] == "6.62 PLN"

    def test_tax_amount_default_statement_currency_is_pln(self) -> None:
        """Arrange: add_tax_collected_amount called without statement_currency argument.
        Act: add Tax Collected Amount column with default currency.
        Assert: Default statement_currency is 'PLN'.
        """
        df = _make_tax_amount_df("28.22 PLN", tax_collected=0.19)
        formatter = ColumnFormatter(df)

        # Call without statement_currency to test default
        result = formatter.add_tax_collected_amount()

        # Should use PLN calculation
        assert result["Tax Collected Amount"].iloc[0] == "6.62 PLN"

    def test_tax_amount_tax_percentage_default_is_zero_not_one(self) -> None:
        """Arrange: Tax Collected is NaN (uses default value).
        Act: add Tax Collected Amount column.
        Assert: Default tax_percentage is 0, not 1.
        """
        df = _make_tax_amount_df("6.84 USD", tax_collected=None)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        # With default 0 (NaN check passes), should return "-"
        assert result["Tax Collected Amount"].iloc[0] == "-"

    def test_tax_amount_ticker_column_name_correct(self) -> None:
        """Arrange: Row contains Ticker, Net Dividend, Date, Tax Collected.
        Act: add Tax Collected Amount column.
        Assert: Ticker is extracted correctly from ColumnName.TICKER.value.
        """
        df = pd.DataFrame(
            {
                "Net Dividend": ["6.84 USD"],
                "Tax Collected": [0.15],
                "Ticker": ["AAPL"],
                "Date": [pd.Timestamp("2025-05-29")],
            }
        )
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        # Should successfully extract currency and return formatted amount
        assert result["Tax Collected Amount"].iloc[0] != "-"

    def test_tax_amount_date_column_name_correct(self) -> None:
        """Arrange: Row contains Date, Net Dividend, Ticker, Tax Collected.
        Act: add Tax Collected Amount column.
        Assert: Date is extracted correctly from ColumnName.DATE.value.
        """
        df = pd.DataFrame(
            {
                "Net Dividend": ["6.84 USD"],
                "Tax Collected": [0.15],
                "Ticker": ["AAPL"],
                "Date": [pd.Timestamp("2025-05-29")],
            }
        )
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        assert result["Tax Collected Amount"].iloc[0] != "-"

    def test_tax_amount_condition_logic_and_not_or(self) -> None:
        """Arrange: PLN statement with Tax Collected Raw column present.
        Act: add Tax Collected Amount column.
        Assert: Condition uses 'and' (not 'or'); raw column is not used.
        """
        df = pd.DataFrame(
            {
                "Net Dividend": ["6.84 USD"],
                "Tax Collected": [0.15],
                "Tax Collected Raw": [-1.21],
                "Ticker": ["AAPL"],
                "Date": [pd.Timestamp("2025-05-29")],
            }
        )
        formatter = ColumnFormatter(df)

        # Call with PLN (non-USD) statement - should NOT use raw column
        result = formatter.add_tax_collected_amount(statement_currency="PLN")

        # With PLN, should calculate from percentage, not use raw amount
        # gross = 6.84 / (1 - 0.15) = 8.047..., tax = gross * 0.15 = 1.207...
        expected = "1.21 USD"  # calculated, not "1.21 USD" from raw
        assert result["Tax Collected Amount"].iloc[0] == expected

    def test_tax_amount_condition_equality_not_inequality(self) -> None:
        """Arrange: USD statement with Tax Collected Raw column present.
        Act: add Tax Collected Amount column.
        Assert: Condition uses == 'USD'; raw column is used.
        """
        df = pd.DataFrame(
            {
                "Net Dividend": ["6.84 USD"],
                "Tax Collected": [0.15],
                "Tax Collected Raw": [-1.02],
                "Ticker": ["AAPL"],
                "Date": [pd.Timestamp("2025-05-29")],
            }
        )
        formatter = ColumnFormatter(df)

        # Call with USD statement - should use raw column
        result = formatter.add_tax_collected_amount(statement_currency="USD")

        # Should use raw amount (absolute value)
        assert result["Tax Collected Amount"].iloc[0] == "1.02 USD"

    def test_tax_amount_usd_raw_zero_not_used(self) -> None:
        """Arrange: USD statement with Tax Collected Raw = 0.
        Act: add Tax Collected Amount column.
        Assert: Raw value of 0 is not used; amount is calculated instead.
        """
        df = pd.DataFrame(
            {
                "Net Dividend": ["6.84 USD"],
                "Tax Collected": [0.15],
                "Tax Collected Raw": [0],
                "Ticker": ["AAPL"],
                "Date": [pd.Timestamp("2025-05-29")],
            }
        )
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="USD")

        # With raw = 0, should calculate from percentage instead
        expected = "1.21 USD"  # calculated
        assert result["Tax Collected Amount"].iloc[0] == expected

    def test_tax_amount_usd_raw_nan_not_used(self) -> None:
        """Arrange: USD statement with Tax Collected Raw = NaN.
        Act: add Tax Collected Amount column.
        Assert: Raw value of NaN is not used; amount is calculated instead.
        """
        df = pd.DataFrame(
            {
                "Net Dividend": ["6.84 USD"],
                "Tax Collected": [0.15],
                "Tax Collected Raw": [None],
                "Ticker": ["AAPL"],
                "Date": [pd.Timestamp("2025-05-29")],
            }
        )
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="USD")

        # With raw = NaN, should calculate from percentage instead
        expected = "1.21 USD"  # calculated
        assert result["Tax Collected Amount"].iloc[0] == expected

    def test_tax_amount_absolute_value_of_raw(self) -> None:
        """Arrange: USD statement with Tax Collected Raw = -1.21.
        Act: add Tax Collected Amount column.
        Assert: Absolute value of raw amount is used.
        """
        df = pd.DataFrame(
            {
                "Net Dividend": ["6.84 USD"],
                "Tax Collected": [0.15],
                "Tax Collected Raw": [-1.21],
                "Ticker": ["AAPL"],
                "Date": [pd.Timestamp("2025-05-29")],
            }
        )
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="USD")

        # Should take absolute value
        assert result["Tax Collected Amount"].iloc[0] == "1.21 USD"

    def test_tax_amount_formatting_two_decimals(self) -> None:
        """Arrange: Tax Collected Raw = -2.345.
        Act: add Tax Collected Amount column.
        Assert: Result is formatted with exactly 2 decimal places.
        """
        df = pd.DataFrame(
            {
                "Net Dividend": ["10.00 USD"],
                "Tax Collected": [0.19],
                "Tax Collected Raw": [-2.345],
                "Ticker": ["AAPL"],
                "Date": [pd.Timestamp("2025-05-29")],
            }
        )
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="USD")

        # Should format with .2f
        assert result["Tax Collected Amount"].iloc[0] == "2.35 USD"

    def test_tax_amount_currency_appended(self) -> None:
        """Arrange: USD statement with Tax Collected Raw column present.
        Act: add Tax Collected Amount column.
        Assert: Currency is appended with a space.
        """
        df = _make_tax_amount_df(
            "6.84 USD",
            tax_collected=0.15,
            tax_collected_raw=-1.21,
            include_raw_col=True,
        )
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="USD")

        # Must have space before currency
        assert " USD" in result["Tax Collected Amount"].iloc[0]
        assert result["Tax Collected Amount"].iloc[0] == "1.21 USD"

    def test_tax_amount_calculation_formula_correct(self) -> None:
        """Arrange: PLN statement with 100.00 PLN and 20% tax.
        Act: add Tax Collected Amount column.
        Assert: Calculation uses gross = net / (1 - tax%), tax = gross * tax%.
        """
        df = _make_tax_amount_df("100.00 PLN", tax_collected=0.20)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="PLN")

        # gross = 100 / (1 - 0.20) = 100 / 0.80 = 125
        # tax = 125 * 0.20 = 25.00
        assert result["Tax Collected Amount"].iloc[0] == "25.00 PLN"

    def test_tax_amount_formula_dividend_not_swapped(self) -> None:
        """Arrange: PLN statement with 100.00 PLN and 25% tax.
        Act: add Tax Collected Amount column.
        Assert: Calculation divides by (1 - tax%), not (1 + tax%).
        """
        df = _make_tax_amount_df("100.00 PLN", tax_collected=0.25)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="PLN")

        # With division by (1 - 0.25) = 0.75: gross = 133.33, tax = 33.33
        # With division by (1 + 0.25) = 1.25: gross = 80.00, tax = 20.00
        assert result["Tax Collected Amount"].iloc[0] == "33.33 PLN"

    def test_tax_amount_column_created(self) -> None:
        """Arrange: DataFrame with Net Dividend and Tax Collected.
        Act: add Tax Collected Amount column.
        Assert: Tax Collected Amount column is created.
        """
        df = _make_tax_amount_df("6.84 USD", tax_collected=0.15)
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount()

        assert "Tax Collected Amount" in result.columns

    def test_tax_amount_step10_logged(self) -> None:
        """Arrange: Column creation is requested.
        Act: add Tax Collected Amount column.
        Assert: Step 10 message is logged.
        """
        from unittest.mock import MagicMock

        import data_processing.column_formatter as mod

        df = _make_tax_amount_df("6.84 USD", tax_collected=0.15)
        formatter = ColumnFormatter(df)
        captured: list[str] = []

        mock_log = MagicMock(
            side_effect=lambda msg, *a, **kw: captured.append(str(msg))
        )

        with patch.object(mod.logger, "info", mock_log):
            formatter.add_tax_collected_amount()

        assert any("Step 10" in m and "Tax Collected Amount" in m for m in captured)

    def test_add_tax_collected_amount_missing_tax_collected_column_returns_dash(
        self,
    ) -> None:
        """Arrange: DataFrame with 'Net Dividend' but no 'Tax Collected' column.
        Act: add Tax Collected Amount column with statement_currency='PLN'.
        Assert: Tax Collected Amount is '-' (uses default 0, which triggers early return).
        """
        df = pd.DataFrame({"Net Dividend": ["10.00 USD"]})
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="PLN")

        assert result["Tax Collected Amount"].iloc[0] == "-"

    def test_add_tax_collected_amount_pln_with_raw_col_present_uses_formula(
        self,
    ) -> None:
        """Arrange: PLN statement with 'Tax Collected Raw' column present and non-zero.
        Act: add Tax Collected Amount column with statement_currency='PLN'.
        Assert: Uses formula path (gross * rate), not raw value path.
        """
        df = pd.DataFrame(
            {
                "Net Dividend": ["10.00 USD"],
                "Tax Collected": [0.30],
                "Tax Collected Raw": [-1.30],
                "Ticker": ["TEST"],
                "Date": [pd.Timestamp("2025-05-29")],
            }
        )
        formatter = ColumnFormatter(df)

        result = formatter.add_tax_collected_amount(statement_currency="PLN")

        # Formula path: gross = 10.00 / (1 - 0.30) ≈ 14.286, tax = 14.286 * 0.30 ≈ 4.286
        # Expected: "4.29 USD"
        # Raw path would give "1.30 USD"
        assert result["Tax Collected Amount"].iloc[0] == "4.29 USD"
