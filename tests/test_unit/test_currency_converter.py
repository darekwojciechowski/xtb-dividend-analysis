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

from pathlib import Path

import pandas as pd
import pytest

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
        """Extracted currency always takes priority over ticker inference."""
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("SBUX.US", "EUR")

        # Assert
        assert result == "EUR"

    def test_determine_currency_when_us_ticker_then_returns_usd(self) -> None:
        """Tickers ending in .US resolve to USD."""
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("AAPL.US", None)

        # Assert
        assert result == "USD"

    def test_determine_currency_when_pl_ticker_then_returns_pln(self) -> None:
        """Tickers ending in .PL resolve to PLN (except ASB.PL special case)."""
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("XTB.PL", None)

        # Assert
        assert result == "PLN"

    def test_determine_currency_when_dk_ticker_then_returns_dkk(self) -> None:
        """Tickers ending in .DK resolve to DKK."""
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("NOVOB.DK", None)

        # Assert
        assert result == "DKK"

    def test_determine_currency_when_uk_ticker_then_returns_gbp(self) -> None:
        """Tickers ending in .UK resolve to GBP."""
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
        """Eurozone tickers resolve to EUR."""
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency(ticker, None)

        # Assert
        assert result == "EUR"

    def test_determine_currency_when_asb_pl_ticker_then_returns_usd(self) -> None:
        """ASB.PL is a US company listed in Poland — must resolve to USD."""
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("ASB.PL", None)

        # Assert
        assert result == "USD"

    def test_determine_currency_when_unknown_ticker_then_returns_usd(self) -> None:
        """Unknown tickers fall back to USD."""
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("XYZ.UNKNOWN", None)

        # Assert
        assert result == "USD"

    def test_determine_currency_never_returns_empty_string(self) -> None:
        """Result is always a non-empty string regardless of ticker."""
        # Arrange
        converter = _converter()

        # Act
        result = converter.determine_currency("ANYTHING.ZZ", None)

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0


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
        """Pattern 'XXX WHT' with '/SHR' → returns (amount, currency)."""
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
        """Pattern 'XXX WHT' with no '/SHR' → (None, currency)."""
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
        """Pattern 'XXX X.XX/ SHR' → (float, currency)."""
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
        """Pattern 'X.XX XXX/SHR' → (float, currency)."""
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
        """Fallback numeric match → (float, None)."""
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
        """Non-string input → (None, None)."""
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment(None)  # type: ignore[arg-type]

        # Assert
        assert amount is None
        assert currency is None

    def test_extract_when_empty_string_then_returns_none_tuple(self) -> None:
        """Empty string → (None, None)."""
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment("")

        # Assert
        assert amount is None
        assert currency is None

    def test_extract_when_dot_only_then_returns_none_tuple(self) -> None:
        """A lone '.' is not a valid number → (None, None)."""
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment(".")

        # Assert
        assert amount is None
        assert currency is None

    def test_extract_when_no_number_in_string_then_returns_none_tuple(self) -> None:
        """Pure text with no digits → (None, None)."""
        # Arrange
        converter = _converter()

        # Act
        amount, currency = converter.extract_dividend_from_comment("no digits here")

        # Assert
        assert amount is None
        assert currency is None

    def test_extract_when_pln_wht_pattern_then_returns_pln_currency(self) -> None:
        """PLN WHT pattern should return PLN currency."""
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
        """Return value is always a 2-tuple regardless of input."""
        # Arrange
        converter = _converter()

        # Act
        result = converter.extract_dividend_from_comment("random input 99")

        # Assert
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# TestGetExchangeRate
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetExchangeRate:
    """Tests for CurrencyConverter.get_exchange_rate."""

    def test_get_exchange_rate_when_pln_then_returns_one(self) -> None:
        """PLN is always 1.0 — no CSV lookup needed."""
        # Arrange
        converter = _converter()

        # Act
        rate = converter.get_exchange_rate([], "2024-01-15", "PLN")

        # Assert
        assert rate == pytest.approx(1.0)

    def test_get_exchange_rate_when_date_present_then_returns_correct_rate(
        self, tmp_path: Path
    ) -> None:
        """Returns the USD rate from CSV when target date is present."""
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
        """Weekend date triggers look-back and returns the Friday rate."""
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
        """Unsupported currency code (e.g. CHF) returns 1.0 instead of raising."""
        # Arrange
        csv_file = _nbp_csv(tmp_path, "20240115", 3.95)
        converter = _converter()

        # Act
        rate = converter.get_exchange_rate([str(csv_file)], "2024-01-15", "CHF")

        # Assert
        assert rate == pytest.approx(1.0)

    def test_get_exchange_rate_when_no_csv_files_and_nonpln_then_raises(self) -> None:
        """With no CSV files and a non-PLN currency, raises ValueError after exhausting look-back."""
        # Arrange
        converter = _converter()

        # Act / Assert
        with pytest.raises(ValueError, match="No exchange rate data found"):
            converter.get_exchange_rate([], "2024-01-15", "USD")

    def test_get_exchange_rate_when_multiple_csv_files_then_finds_rate(
        self, tmp_path: Path
    ) -> None:
        """Rate is found even when it lives in the second of several CSV files."""
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
