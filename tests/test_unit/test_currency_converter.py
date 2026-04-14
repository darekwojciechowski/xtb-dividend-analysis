"""Unit tests for CurrencyConverter.

Covers currency determination, per-comment dividend extraction, and
exchange-rate retrieval from NBP archive CSV files.

Test classes:
    TestDetermineCurrency        — ticker-suffix routing, extracted_currency priority, ASB.PL edge case
    TestExtractDividendFromComment — all regex branches, sentinel and edge inputs
    TestGetExchangeRate           — PLN shortcut, D-1 lookback, unsupported currency, missing date

All tests are marked ``@pytest.mark.unit``.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from data_processing.constants import ColumnName
from data_processing.currency_converter import CurrencyConverter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _converter() -> CurrencyConverter:
    return CurrencyConverter(pd.DataFrame())


def _nbp_csv(tmp_path: Path, date_str: str, rate: float) -> Path:
    """Write a minimal NBP-style CSV file matching the real NBP archive format.

    The real archiwum_tab_a_*.csv has a description row AFTER the header that
    forces the ``data`` column to be parsed as object (string) dtype by pandas,
    which is required for the string comparison inside ``get_exchange_rate``.
    """
    content = (
        "data;1USD;1EUR;1GBP;1DKK\n"
        "nazwa;US dollar;euro;pound sterling;Danish krone\n"  # description row — keeps data col as str
        f"{date_str};{str(rate).replace('.', ',')};4,2500;5,1200;0,5700\n"
    )
    csv_file = tmp_path / f"archiwum_tab_a_{date_str[:4]}.csv"
    csv_file.write_text(content, encoding="ISO-8859-1")
    return csv_file


# ---------------------------------------------------------------------------
# TestDetermineCurrency
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDetermineCurrency:
    """Tests for CurrencyConverter.determine_currency."""

    def test_determine_currency_when_extracted_then_returns_extracted(self) -> None:
        """Arrange: extracted_currency is 'EUR', ticker is 'SBUX.US'.
        Act: determine the currency.
        Assert: Extracted currency takes priority; returns 'EUR'.
        """
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("SBUX.US", "EUR")

        # Assert
        assert result == "EUR"

    def test_determine_currency_when_us_ticker_then_returns_usd(self) -> None:
        """Arrange: Ticker is 'AAPL.US', extracted_currency is None.
        Act: determine the currency.
        Assert: Returns 'USD' based on ticker suffix.
        """
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("AAPL.US", None)

        # Assert
        assert result == "USD"

    def test_determine_currency_when_pl_ticker_then_returns_pln(self) -> None:
        """Arrange: Ticker is 'XTB.PL', extracted_currency is None.
        Act: determine the currency.
        Assert: Returns 'PLN' based on ticker suffix.
        """
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("XTB.PL", None)

        # Assert
        assert result == "PLN"

    def test_determine_currency_when_dk_ticker_then_returns_dkk(self) -> None:
        """Arrange: Ticker is 'NOVOB.DK', extracted_currency is None.
        Act: determine the currency.
        Assert: Returns 'DKK' based on ticker suffix.
        """
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("NOVOB.DK", None)

        # Assert
        assert result == "DKK"

    def test_determine_currency_when_uk_ticker_then_returns_gbp(self) -> None:
        """Arrange: Ticker is 'HSBA.UK', extracted_currency is None.
        Act: determine the currency.
        Assert: Returns 'GBP' based on ticker suffix.
        """
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("HSBA.UK", None)

        # Assert
        assert result == "GBP"

    @pytest.mark.parametrize(
        "ticker", ["AIR.FR", "SAP.DE", "CRH.IE", "ASML.NL", "ITX.ES", "ENEL.IT"]
    )
    def test_determine_currency_when_eurozone_ticker_then_returns_eur(
        self, ticker: str
    ) -> None:
        """Arrange: Ticker is from Eurozone (.FR, .DE, etc.), extracted_currency is None.
        Act: determine the currency.
        Assert: Returns 'EUR' based on ticker suffix.
        """
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency(ticker, None)

        # Assert
        assert result == "EUR"

    def test_determine_currency_when_asb_pl_ticker_then_returns_usd(self) -> None:
        """Arrange: Ticker is 'ASB.PL' (US company listed in Poland).
        Act: determine the currency.
        Assert: Returns 'USD' as a special case.
        """
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("ASB.PL", None)

        # Assert
        assert result == "USD"

    def test_determine_currency_when_unknown_ticker_then_returns_usd(self) -> None:
        """Arrange: Ticker is 'XYZ.UNKNOWN', extracted_currency is None.
        Act: determine the currency.
        Assert: Unknown ticker falls back to 'USD'.
        """
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("XYZ.UNKNOWN", None)

        # Assert
        assert result == "USD"

    def test_determine_currency_never_returns_empty_string(self) -> None:
        """Arrange: Ticker is unrecognized, extracted_currency is None.
        Act: determine the currency.
        Assert: Never returns empty string; always returns a concrete value.
        """
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("ANYTHING.ZZ", None)

        # Assert
        assert result == "USD"

    def test_determine_currency_repeated_calls_are_idempotent(self) -> None:
        """Arrange: determine_currency is called 10 times with the same arguments.
        Act: call determine_currency repeatedly.
        Assert: All results are identical; no side-effect drift occurs.
        """
        # Arrange
        converter = _converter()
        ticker = "AAPL.US"

        # Act
        results = [converter.determine_currency(ticker, None) for _ in range(10)]

        # Assert
        assert len(set(results)) == 1, "determine_currency is not deterministic"
        assert results[0] == "USD"


# ---------------------------------------------------------------------------
# TestExtractDividendFromComment
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractDividendFromComment:
    """Tests for CurrencyConverter.extract_dividend_from_comment."""

    # --- happy-path regex branches ---

    def test_extract_when_usd_wht_with_amount_then_returns_amount_and_currency(
        self,
    ) -> None:
        """Arrange: Comment string contains a WHT pattern with a per-share amount.
        Act: extract dividend from the comment.
        Assert: Returns (amount, currency) where amount equals the per-share value.
        """
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment(
            "SBUX.US USD WHT 15% 0.3000/ SHR"
        )

        # Assert
        assert amount == pytest.approx(0.3)
        assert currency == "USD"

    def test_extract_when_usd_wht_without_amount_then_returns_none_amount(
        self,
    ) -> None:
        """Arrange: Comment contains WHT pattern but no per-share amount.
        Act: extract dividend from the comment.
        Assert: Returns (None, currency).
        """
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment(
            "SBUX.US USD WHT 15%"
        )

        # Assert
        assert amount is None
        assert currency == "USD"

    def test_extract_when_currency_amount_shr_pattern_then_returns_correct_values(
        self,
    ) -> None:
        """Arrange: Comment matches 'XXX X.XX/ SHR' pattern.
        Act: extract dividend from the comment.
        Assert: Returns (float, currency).
        """
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment(
            "MSFT.US USD 0.7500/ SHR"
        )

        # Assert
        assert amount == pytest.approx(0.75)
        assert currency == "USD"

    def test_extract_when_amount_currency_shr_pattern_then_returns_correct_values(
        self,
    ) -> None:
        """Arrange: Comment matches 'X.XX XXX/SHR' pattern.
        Act: extract dividend from the comment.
        Assert: Returns (float, currency).
        """
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment("1.2300 EUR/SHR")

        # Assert
        assert amount == pytest.approx(1.23)
        assert currency == "EUR"

    def test_extract_when_numeric_only_pattern_then_returns_float_and_none_currency(
        self,
    ) -> None:
        """Arrange: Comment contains a number but no recognized currency pattern.
        Act: extract dividend from the comment.
        Assert: Fallback numeric match returns (float, None).
        """
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment(
            "some text 2.50 more text"
        )

        # Assert
        assert amount == pytest.approx(2.50)
        assert currency is None

    # --- edge / sentinel cases ---

    def test_extract_when_none_input_then_returns_none_tuple(self) -> None:
        """Arrange: Input is None (non-string).
        Act: extract dividend from the comment.
        Assert: Returns (None, None).
        """
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment(None)  # type: ignore[arg-type]

        # Assert
        assert amount is None
        assert currency is None

    def test_extract_when_empty_string_then_returns_none_tuple(self) -> None:
        """Arrange: Comment is an empty string.
        Act: extract dividend from the comment.
        Assert: Returns (None, None).
        """
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment("")

        # Assert
        assert amount is None
        assert currency is None

    def test_extract_when_dot_only_then_returns_none_tuple(self) -> None:
        """Arrange: Comment is a lone period '.'.
        Act: extract dividend from the comment.
        Assert: Invalid number returns (None, None).
        """
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment(".")

        # Assert
        assert amount is None
        assert currency is None

    def test_extract_when_no_number_in_string_then_returns_none_tuple(self) -> None:
        """Arrange: Comment contains only text with no digits.
        Act: extract dividend from the comment.
        Assert: Returns (None, None).
        """
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment("no digits here")

        # Assert
        assert amount is None
        assert currency is None

    def test_extract_when_pln_wht_pattern_then_returns_pln_currency(self) -> None:
        """Arrange: Comment contains a PLN WHT pattern.
        Act: extract dividend from the comment.
        Assert: Returns PLN currency.
        """
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment(
            "TXT.PL PLN WHT 19% 1.2000/ SHR"
        )

        # Assert
        assert currency == "PLN"
        assert amount == pytest.approx(1.2)

    def test_extract_always_returns_tuple(self) -> None:
        """Arrange: Comment contains text and a number with no currency.
        Act: extract dividend from the comment.
        Assert: Numeric fallback returns (99.0, None).
        """
        # Arrange
        converter = _converter()

        # Act
        value, currency = converter.extract_dividend_from_comment("random input 99")

        # Assert
        assert value == pytest.approx(99.0)
        assert currency is None


# ---------------------------------------------------------------------------
# TestGetExchangeRate
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetExchangeRate:
    """Tests for CurrencyConverter.get_exchange_rate."""

    def test_get_exchange_rate_when_pln_then_returns_one(self) -> None:
        """Arrange: Currency is 'PLN'.
        Act: get the exchange rate.
        Assert: Returns 1.0 without CSV lookup.
        """
        # Arrange
        converter = _converter()

        # Act
        rate = converter.get_exchange_rate([], "2024-01-15", "PLN")

        # Assert
        assert rate == pytest.approx(1.0)

    def test_get_exchange_rate_when_date_present_then_returns_correct_rate(
        self, tmp_path: Path
    ) -> None:
        """Arrange: NBP CSV file contains the target date.
        Act: get the exchange rate.
        Assert: Correct rate is returned from CSV.
        """
        # Arrange
        csv_file = _nbp_csv(tmp_path, "20240115", 3.9500)
        converter = _converter()

        # Act
        rate = converter.get_exchange_rate([str(csv_file)], "2024-01-15", "USD")

        # Assert
        assert rate == pytest.approx(3.95)

    def test_get_exchange_rate_when_date_is_weekend_then_uses_previous_business_day(
        self, tmp_path: Path
    ) -> None:
        """Arrange: Target date is a weekend; Friday rate is in the CSV.
        Act: get the exchange rate.
        Assert: Look-back mechanism returns the previous business day's rate.
        """
        # Arrange — 2024-01-13 is Saturday; Friday is 2024-01-12
        csv_file = _nbp_csv(tmp_path, "20240112", 4.0100)
        converter = _converter()

        # Act
        rate = converter.get_exchange_rate([str(csv_file)], "2024-01-13", "USD")

        # Assert
        assert rate == pytest.approx(4.01)

    def test_get_exchange_rate_when_unsupported_currency_then_returns_one(
        self, tmp_path: Path
    ) -> None:
        """Arrange: Currency is unsupported (e.g., CHF).
        Act: get the exchange rate.
        Assert: Returns 1.0 instead of raising an exception.
        """
        # Arrange
        csv_file = _nbp_csv(tmp_path, "20240115", 3.95)
        converter = _converter()

        # Act
        rate = converter.get_exchange_rate([str(csv_file)], "2024-01-15", "CHF")

        # Assert
        assert rate == pytest.approx(1.0)

    def test_get_exchange_rate_when_no_csv_files_and_nonpln_then_raises(self) -> None:
        """Arrange: No CSV files available, currency is non-PLN.
        Act: get the exchange rate.
        Assert: Raises ValueError after exhausting look-back.
        """
        # Arrange
        converter = _converter()

        # Act / Assert
        with pytest.raises(ValueError, match="No exchange rate data found"):
            converter.get_exchange_rate([], "2024-01-15", "USD")

    def test_get_exchange_rate_when_multiple_csv_files_then_finds_rate(
        self, tmp_path: Path
    ) -> None:
        """Arrange: Multiple CSV files exist; target date is in the second file.
        Act: get the exchange rate.
        Assert: Rate is found across all CSV files.
        """
        # Arrange
        csv_no_data = tmp_path / "archiwum_tab_a_2023.csv"
        csv_no_data.write_text(
            "data;1USD;1EUR;1GBP;1DKK\nnazwa;US dollar;euro;pound sterling;Danish krone\n",
            encoding="ISO-8859-1",
        )
        csv_with_data = _nbp_csv(tmp_path, "20240115", 3.9800)
        converter = _converter()

        # Act
        rate = converter.get_exchange_rate(
            [str(csv_no_data), str(csv_with_data)], "2024-01-15", "USD"
        )

        # Assert
        assert rate == pytest.approx(3.98)


# ---------------------------------------------------------------------------
# Helpers shared by TestCalculateDividendMutations
# ---------------------------------------------------------------------------

_DATE = "Date"
_DATE_D1 = ColumnName.DATE_D_MINUS_1.value  # "Date D-1"
_TICKER = ColumnName.TICKER.value  # "Ticker"
_SHARES = ColumnName.SHARES.value  # "Shares"
_CURRENCY = ColumnName.CURRENCY.value  # "Currency"
_COMMENT = "Comment"
_AMOUNT = "Net Dividend"


def _valid_row(
    *,
    ticker: str = "AAPL.US",
    amount: float = 4.0,
    comment: str = "AAPL.US USD 1.0/ SHR",
    date: object = pd.Timestamp("2024-01-15"),
    date_d1: object = pd.Timestamp("2024-01-12"),
) -> dict:
    """Return a single-row dict ready for pd.DataFrame({...})."""
    return {
        _DATE: [date],
        _TICKER: [ticker],
        _AMOUNT: [amount],
        _COMMENT: [comment],
        _DATE_D1: [date_d1],
    }


# ---------------------------------------------------------------------------
# TestCalculateDividendMutations
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCalculateDividendMutations:
    """Targeted tests for CurrencyConverter.calculate_dividend.

    Each test is designed to kill one or more specific survived mutations
    from the mutmut run.
    """

    # ------------------------------------------------------------------
    # mutmut_3: currency_col = None
    # ------------------------------------------------------------------

    def test_currency_col_name_is_currency_not_none(self) -> None:
        """Arrange: calculate_dividend is called with valid dividend data.
        Act: calculate the dividend.
        Assert: Currency column is created with correct key name.
        """
        # Arrange
        df = pd.DataFrame(_valid_row())
        converter = CurrencyConverter(df)

        # Act
        with patch.object(converter, "get_exchange_rate", return_value=4.0):
            result = converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert
        assert _CURRENCY in result.columns
        assert result.loc[0, _CURRENCY] is not None
        assert result.loc[0, _CURRENCY] == "USD"

    # ------------------------------------------------------------------
    # mutmut_6, 7, 8, 9: error message for missing Date D-1 column
    # ------------------------------------------------------------------

    def test_missing_date_d1_column_raises_with_full_message(self) -> None:
        """Arrange: DataFrame lacks the Date D-1 column.
        Act: calculate the dividend.
        Assert: ValueError contains the column name and remediation hint.
        """
        # Arrange
        df = pd.DataFrame(
            {
                _DATE: [pd.Timestamp("2024-01-15")],
                _TICKER: ["AAPL.US"],
                _AMOUNT: [4.0],
                _COMMENT: ["AAPL.US USD 1.0/ SHR"],
                # _DATE_D1 intentionally absent
            }
        )
        converter = CurrencyConverter(df)

        # Act / Assert
        with pytest.raises(ValueError) as exc_info:
            converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        message = str(exc_info.value)
        assert "Date D-1" in message
        assert "create_date_d_minus_1_column" in message

    # ------------------------------------------------------------------
    # mutmut_11: self.df[shares_col] = None  (should be np.nan)
    # ------------------------------------------------------------------

    def test_shares_col_initialised_as_float_not_object(self) -> None:
        """Arrange: DataFrame with rows that have NaN dates (loop never enters).
        Act: calculate the dividend.
        Assert: Shares column is initialized with float dtype, using np.nan.
        """
        # Arrange — all rows have NaN Date so the loop body is never entered
        df = pd.DataFrame(
            {
                _DATE: [pd.NaT],
                _TICKER: ["AAPL.US"],
                _AMOUNT: [4.0],
                _COMMENT: ["AAPL.US USD 1.0/ SHR"],
                _DATE_D1: [pd.Timestamp("2024-01-12")],
                # _SHARES intentionally absent
            }
        )
        converter = CurrencyConverter(df)

        # Act
        result = converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert
        assert result[_SHARES].dtype == float

    # ------------------------------------------------------------------
    # mutmut_12, 13: currency_col condition flipped / initialised to ""
    # ------------------------------------------------------------------

    def test_currency_col_absent_initialised_to_none_not_empty_string(self) -> None:
        """Arrange: DataFrame lacks the Currency column.
        Act: calculate the dividend.
        Assert: Currency column is created with None values, not empty strings.
        """
        # Arrange — all rows have NaN Date so no rows are processed
        df = pd.DataFrame(
            {
                _DATE: [pd.NaT],
                _TICKER: ["AAPL.US"],
                _AMOUNT: [4.0],
                _COMMENT: ["AAPL.US USD 1.0/ SHR"],
                _DATE_D1: [pd.Timestamp("2024-01-12")],
                # _CURRENCY intentionally absent
            }
        )
        converter = CurrencyConverter(df)

        # Act
        result = converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert
        assert _CURRENCY in result.columns
        assert result.loc[0, _CURRENCY] is None

    # ------------------------------------------------------------------
    # mutmut_14: OR → AND for comment NaN check
    # ------------------------------------------------------------------

    def test_row_with_nan_comment_is_skipped_but_next_row_is_processed(self) -> None:
        """Arrange: First row has NaN Comment; second row is valid.
        Act: calculate the dividend.
        Assert: Invalid row is skipped; valid rows are processed.
        """
        # Arrange
        df = pd.DataFrame(
            {
                _DATE: [pd.Timestamp("2024-01-15"), pd.Timestamp("2024-01-15")],
                _TICKER: ["AAPL.US", "AAPL.US"],
                _AMOUNT: [4.0, 4.0],
                _COMMENT: [float("nan"), "AAPL.US USD 1.0/ SHR"],
                _DATE_D1: [pd.Timestamp("2024-01-12"), pd.Timestamp("2024-01-12")],
            }
        )
        converter = CurrencyConverter(df)

        # Act
        with patch.object(converter, "get_exchange_rate", return_value=4.0):
            result = converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert — row 0 skipped, row 1 processed
        assert pd.isna(result.loc[0, _SHARES])
        assert not pd.isna(result.loc[1, _SHARES])

    # ------------------------------------------------------------------
    # mutmut_15: OR → AND for amount NaN check
    # ------------------------------------------------------------------

    def test_row_with_nan_amount_is_skipped_but_next_row_is_processed(self) -> None:
        """Arrange: First row has NaN amount; second row is valid.
        Act: calculate the dividend.
        Assert: Row with NaN amount is skipped; valid rows are processed.
        """
        # Arrange
        df = pd.DataFrame(
            {
                _DATE: [pd.Timestamp("2024-01-15"), pd.Timestamp("2024-01-15")],
                _TICKER: ["AAPL.US", "AAPL.US"],
                _AMOUNT: [float("nan"), 4.0],
                _COMMENT: ["AAPL.US USD 1.0/ SHR", "AAPL.US USD 1.0/ SHR"],
                _DATE_D1: [pd.Timestamp("2024-01-12"), pd.Timestamp("2024-01-12")],
            }
        )
        converter = CurrencyConverter(df)

        # Act
        with patch.object(converter, "get_exchange_rate", return_value=4.0):
            result = converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert — row 0 skipped, row 1 processed
        assert pd.isna(result.loc[0, _SHARES])
        assert not pd.isna(result.loc[1, _SHARES])

    def test_row_with_nan_date_is_skipped_but_next_row_is_processed(self) -> None:
        """Arrange: First row has NaN Date; second row is valid.
        Act: calculate the dividend.
        Assert: Row with NaN date is skipped; valid rows are processed.
        """
        # Arrange
        df = pd.DataFrame(
            {
                _DATE: [pd.NaT, pd.Timestamp("2024-01-15")],
                _TICKER: ["AAPL.US", "AAPL.US"],
                _AMOUNT: [4.0, 4.0],
                _COMMENT: ["AAPL.US USD 1.0/ SHR", "AAPL.US USD 1.0/ SHR"],
                _DATE_D1: [pd.Timestamp("2024-01-12"), pd.Timestamp("2024-01-12")],
            }
        )
        converter = CurrencyConverter(df)

        # Act
        with patch.object(converter, "get_exchange_rate", return_value=4.0):
            result = converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert
        assert pd.isna(result.loc[0, _SHARES])
        assert not pd.isna(result.loc[1, _SHARES])

    # ------------------------------------------------------------------
    # mutmut_22: continue → break
    # ------------------------------------------------------------------

    def test_continue_not_break_on_skipped_row(self) -> None:
        """Arrange: First row has NaN Date; rows 2 and 3 are valid.
        Act: calculate the dividend.
        Assert: Loop continues after skip; all subsequent valid rows are processed.
        """
        # Arrange — row 0 has NaN Date (skipped); rows 1 and 2 are valid
        df = pd.DataFrame(
            {
                _DATE: [pd.NaT, pd.Timestamp("2024-01-15"), pd.Timestamp("2024-01-15")],
                _TICKER: ["AAPL.US", "AAPL.US", "AAPL.US"],
                _AMOUNT: [4.0, 4.0, 4.0],
                _COMMENT: [
                    "AAPL.US USD 1.0/ SHR",
                    "AAPL.US USD 1.0/ SHR",
                    "AAPL.US USD 1.0/ SHR",
                ],
                _DATE_D1: [
                    pd.Timestamp("2024-01-12"),
                    pd.Timestamp("2024-01-12"),
                    pd.Timestamp("2024-01-12"),
                ],
            }
        )
        converter = CurrencyConverter(df)

        # Act
        with patch.object(converter, "get_exchange_rate", return_value=4.0):
            result = converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert — rows 1 and 2 must both be processed
        assert pd.isna(result.loc[0, _SHARES])
        assert not pd.isna(result.loc[1, _SHARES])
        assert not pd.isna(result.loc[2, _SHARES])

    # ------------------------------------------------------------------
    # mutmut_26, 27, 28: Date D-1 NaN error message content / casing
    # ------------------------------------------------------------------

    def test_nan_date_d1_on_valid_row_raises_with_correct_message(self) -> None:
        """Arrange: Valid row with NaN Date D-1.
        Act: calculate the dividend.
        Assert: ValueError contains expected literal substrings.
        """
        # Arrange
        df = pd.DataFrame(
            {
                _DATE: [pd.Timestamp("2024-01-15")],
                _TICKER: ["AAPL.US"],
                _AMOUNT: [4.0],
                _COMMENT: ["AAPL.US USD 1.0/ SHR"],
                _DATE_D1: [pd.NaT],
            }
        )
        converter = CurrencyConverter(df)

        # Act / Assert
        with pytest.raises(ValueError) as exc_info:
            converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        message = str(exc_info.value)
        assert "Date D-1" in message
        assert "All rows must have valid" in message

    # ------------------------------------------------------------------
    # mutmut_30, 32, 33, 34: strftime format for target_date_str
    # ------------------------------------------------------------------

    def test_date_passed_to_get_exchange_rate_is_iso_format(self) -> None:
        """Arrange: Valid dividend row with Date D-1.
        Act: calculate the dividend.
        Assert: get_exchange_rate receives date in 'YYYY-MM-DD' format.
        """
        # Arrange
        df = pd.DataFrame(_valid_row(date_d1=pd.Timestamp("2024-01-12")))
        converter = CurrencyConverter(df)
        mock_rate = MagicMock(return_value=4.0)

        # Act
        with patch.object(converter, "get_exchange_rate", mock_rate):
            converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert — second positional arg to get_exchange_rate is the date string
        call_args = mock_rate.call_args
        date_arg = call_args[0][1]  # positional arg index 1
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_arg), (
            f"Expected ISO date YYYY-MM-DD, got: {date_arg!r}"
        )
        assert date_arg == "2024-01-12"

    # ------------------------------------------------------------------
    # mutmut_37, 46, 47: ticker and extracted_currency passed correctly
    # ------------------------------------------------------------------

    def test_determine_currency_called_with_correct_ticker_and_extracted_currency(
        self,
    ) -> None:
        """Arrange: Dividend comment with extracted currency.
        Act: calculate the dividend.
        Assert: determine_currency receives correct ticker and extracted currency.
        """
        # Arrange — comment "AAPL.US USD 1.0/ SHR" extracts ("USD", 1.0)
        df = pd.DataFrame(_valid_row(ticker="AAPL.US", comment="AAPL.US USD 1.0/ SHR"))
        converter = CurrencyConverter(df)
        mock_determine = MagicMock(return_value="USD")

        # Act
        with (
            patch.object(converter, "determine_currency", mock_determine),
            patch.object(converter, "get_exchange_rate", return_value=4.0),
        ):
            converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert
        mock_determine.assert_called_once_with("AAPL.US", "USD")

    # ------------------------------------------------------------------
    # mutmut_51, 52, 53: exchange_rate stays 1.0 for PLN/PLN rows
    # ------------------------------------------------------------------

    def test_pln_dividend_with_pln_statement_uses_exchange_rate_one(self) -> None:
        """Arrange: PLN dividend with PLN statement.
        Act: calculate the dividend.
        Assert: get_exchange_rate is never called; exchange_rate remains 1.0.
        """
        # Arrange — total_dividend=10.0, dividend_per_share=2.0 → shares=5
        df = pd.DataFrame(
            _valid_row(
                ticker="XTB.PL",
                amount=10.0,
                comment="XTB.PL PLN 2.0/ SHR",
            )
        )
        converter = CurrencyConverter(df)
        exploding_rate = MagicMock(
            side_effect=AssertionError("get_exchange_rate must not be called for PLN")
        )

        # Act
        with patch.object(converter, "get_exchange_rate", exploding_rate):
            result = converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert — no exception raised; shares = round(10 / (2 * 1.0)) = 5
        assert result.loc[0, _SHARES] == 5

    # ------------------------------------------------------------------
    # mutmut_57–62: get_exchange_rate called with correct positional args
    # ------------------------------------------------------------------

    def test_get_exchange_rate_called_with_correct_positional_args(self) -> None:
        """Arrange: Valid dividend row with courses paths.
        Act: calculate the dividend.
        Assert: get_exchange_rate receives (courses_paths, date_str, currency).
        """
        # Arrange
        courses = ["/some/path/archiwum_tab_a_2024.csv"]
        df = pd.DataFrame(
            _valid_row(
                ticker="AAPL.US",
                amount=4.0,
                comment="AAPL.US USD 1.0/ SHR",
                date_d1=pd.Timestamp("2024-01-12"),
            )
        )
        converter = CurrencyConverter(df)
        mock_rate = MagicMock(return_value=3.95)

        # Act
        with patch.object(converter, "get_exchange_rate", mock_rate):
            converter.calculate_dividend(courses, "PLN", _COMMENT, _AMOUNT)

        # Assert — exactly one call with correct positional arguments
        mock_rate.assert_called_once_with(courses, "2024-01-12", "USD")

    # ------------------------------------------------------------------
    # mutmut_63, 65, 70, 71: zero-dividend guard and shares = 0.0
    # ------------------------------------------------------------------

    def test_zero_exchange_rate_produces_shares_zero_float(self) -> None:
        """Arrange: exchange_rate is 0.0.
        Act: calculate the dividend.
        Assert: Shares is 0.0 as float.
        """
        # Arrange — exchange_rate=0 triggers the guard
        df = pd.DataFrame(
            _valid_row(ticker="AAPL.US", amount=4.0, comment="AAPL.US USD 1.0/ SHR")
        )
        converter = CurrencyConverter(df)

        # Act
        with patch.object(converter, "get_exchange_rate", return_value=0.0):
            result = converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        shares_val = result.loc[0, _SHARES]
        assert shares_val == pytest.approx(0.0)
        assert isinstance(shares_val, float)

    def test_nonzero_exchange_rate_computes_shares_correctly(self) -> None:
        """Arrange: total=8.0, per_share=1.0, exchange_rate=4.0.
        Act: calculate the dividend.
        Assert: Shares = round(total / (per_share * rate)) = 2.
        """
        # Arrange — total=8.0, per_share=1.0, rate=4.0 → shares=round(8/4)=2
        df = pd.DataFrame(
            _valid_row(ticker="AAPL.US", amount=8.0, comment="AAPL.US USD 1.0/ SHR")
        )
        converter = CurrencyConverter(df)

        # Act
        with patch.object(converter, "get_exchange_rate", return_value=4.0):
            result = converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        assert result.loc[0, _SHARES] == 2

    # ------------------------------------------------------------------
    # mutmut_66–69: warning message for division-by-zero case
    # ------------------------------------------------------------------

    def test_zero_exchange_rate_logs_warning_with_correct_content(self, capfd) -> None:
        """Arrange: exchange_rate is 0.0.
        Act: calculate the dividend.
        Assert: Warning is logged with 'Division by zero' and ticker.
        """
        # Arrange
        df = pd.DataFrame(
            _valid_row(ticker="AAPL.US", amount=4.0, comment="AAPL.US USD 1.0/ SHR")
        )
        converter = CurrencyConverter(df)
        captured_warnings: list[str] = []

        with patch("data_processing.currency_converter.logger") as mock_logger:
            mock_logger.warning = MagicMock(
                side_effect=lambda msg: captured_warnings.append(msg)
            )
            mock_logger.info = MagicMock()

            with patch.object(converter, "get_exchange_rate", return_value=0.0):
                converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert — at least one warning containing the expected substrings
        assert captured_warnings, "Expected at least one logger.warning call"
        combined = " ".join(captured_warnings)
        assert "Division by zero" in combined
        assert "AAPL.US" in combined

    # ------------------------------------------------------------------
    # mutmut_88–91: logger.info step-5 message
    # ------------------------------------------------------------------

    def test_logger_info_contains_step5_and_exchange_rates(self) -> None:
        """Arrange: Valid dividend row.
        Act: calculate the dividend.
        Assert: logger.info is called with 'Step 5' and 'exchange rates'.
        """
        # Arrange
        df = pd.DataFrame(_valid_row())
        converter = CurrencyConverter(df)
        info_calls: list[str] = []

        with patch("data_processing.currency_converter.logger") as mock_logger:
            mock_logger.info = MagicMock(side_effect=lambda msg: info_calls.append(msg))
            mock_logger.warning = MagicMock()

            with patch.object(converter, "get_exchange_rate", return_value=4.0):
                converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert
        assert info_calls, "Expected at least one logger.info call"
        combined = " ".join(info_calls)
        assert "Step 5" in combined
        assert "exchange rates" in combined

    # ------------------------------------------------------------------
    # Baseline: happy-path sanity check (extracted_value == 0 skips row)
    # ------------------------------------------------------------------

    def test_extracted_value_zero_skips_row(self) -> None:
        """Arrange: Comment extracts to 0.0 dividend per share.
        Act: calculate the dividend.
        Assert: Row is skipped; Shares remains NaN.
        """
        # Arrange — bare '0' comment → numeric fallback → 0.0
        df = pd.DataFrame(_valid_row(comment="0", amount=10.0))
        converter = CurrencyConverter(df)

        # Act
        result = converter.calculate_dividend([], "PLN", _COMMENT, _AMOUNT)

        # Assert
        assert pd.isna(result.loc[0, _SHARES])


# ---------------------------------------------------------------------------
# TestAddCurrencyToDividends
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAddCurrencyToDividends:
    """Tests for CurrencyConverter.add_currency_to_dividends."""

    @pytest.mark.parametrize(
        "ticker, expected_suffix",
        [
            ("HSBA.UK", "GBP"),
            ("NOVOB.DK", "DKK"),
            ("AAPL.US", "USD"),
            ("AIR.FR", "EUR"),
        ],
    )
    def test_add_currency_appends_correct_suffix(
        self, ticker: str, expected_suffix: str
    ) -> None:
        """Arrange: DataFrame with ticker and Net Dividend amount.
        Act: add currency to dividends.
        Assert: Currency code matching ticker suffix is appended to Net Dividend.
        """
        # Arrange
        df = pd.DataFrame(
            {
                "Ticker": [ticker],
                "Net Dividend": [1.23],
            }
        )
        converter = CurrencyConverter(df)

        # Act
        result = converter.add_currency_to_dividends()

        # Assert
        assert result.loc[0, "Net Dividend"].endswith(f" {expected_suffix}")
