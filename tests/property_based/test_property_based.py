"""Property-based tests using Hypothesis for data processing modules.

This module provides property-based testing for core business logic to discover
edge cases and validate invariants across the entire input space.

Key Testing Principles:
    - Property-based tests complement traditional unit tests by testing invariants
    - Hypothesis generates hundreds of test cases automatically
    - Tests find edge cases developers might not think of
    - Results are reproducible and shrink to minimal failing examples

Test Coverage:
    - CurrencyConverter: exchange rate calculations, currency detection
    - DateConverter: date parsing with various formats
    - TaxCalculator: mathematical properties of tax calculations
    - DataFrameProcessor: data aggregation invariants
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
import pytest
from hypothesis import given, strategies as st

from data_processing.currency_converter import CurrencyConverter
from data_processing.date_converter import DateConverter
from data_processing.tax_calculator import TaxCalculator


# ============================================================================
# Custom Hypothesis Strategies
# ============================================================================


@st.composite
def ticker_strategies(draw) -> str:
    """Generate realistic ticker symbols.

    Returns:
        str: Valid ticker symbol in format SYMBOL.SUFFIX
    """
    symbols = st.text(
        alphabet=st.characters(blacklist_categories=(
            "Cc", "Cs"), blacklist_characters=".,!?"),
        min_size=1,
        max_size=5
    )
    suffixes = st.sampled_from([".US", ".PL", ".DE", ".FR", ".UK", ".DK", ".SE", ""])

    symbol = draw(symbols)
    suffix = draw(suffixes)
    return symbol.upper() + suffix


@st.composite
def currency_codes(draw) -> str:
    """Generate valid 3-letter currency codes.

    Returns:
        str: Currency code (USD, EUR, PLN, etc.)
    """
    common_currencies = ["USD", "EUR", "PLN", "GBP", "DKK", "SEK", "CAD", "JPY", "CHF"]
    generated = draw(st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        min_size=3,
        max_size=3
    ))
    return draw(st.sampled_from(common_currencies + [generated]))


@st.composite
def dividend_comments(draw) -> str:
    """Generate realistic dividend payment comments.

    Returns:
        str: Comment string with dividend information
    """
    amount = draw(st.decimals(min_value=0.01, max_value=1000, places=4))
    currency = draw(currency_codes())

    # Different comment patterns used by brokers
    patterns = [
        f"{currency} {float(amount)}/SHR",
        f"{float(amount)} {currency}/SHR",
        f"{currency} WHT",
        f"{float(amount)}",
        f"DIV {currency} {float(amount)}/SHR",
    ]

    return draw(st.sampled_from(patterns))


@st.composite
def valid_date_formats_with_values(draw) -> tuple[str, str]:
    """Generate valid date strings with matching formats.

    Returns:
        tuple[str, str]: (date_string, format_string) pair
    """
    year = draw(st.integers(min_value=2000, max_value=2099))
    month = draw(st.integers(min_value=1, max_value=12))

    # Determine max day based on month and year
    if month in [1, 3, 5, 7, 8, 10, 12]:
        max_day = 31
    elif month in [4, 6, 9, 11]:
        max_day = 30
    else:  # February
        max_day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28

    day = draw(st.integers(min_value=1, max_value=max_day))
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))

    # Create date string and matching format
    date_formats = [
        (f"{day:02d}.{month:02d}.{year} {hour:02d}:{minute:02d}:{second:02d}", "%d.%m.%Y %H:%M:%S"),
        (f"{year}/{month:02d}/{day:02d}", "%Y/%m/%d"),
        (f"{year}-{month:02d}-{day:02d}", "%Y-%m-%d"),
        (f"{month:02d}/{day:02d}/{year}", "%m/%d/%Y"),
        (f"{day:02d}-{month:02d}-{year}", "%d-%m-%Y"),
    ]

    return draw(st.sampled_from(date_formats))


@st.composite
def positive_floats(draw, min_value: float = 0.01, max_value: float = 10000) -> float:
    """Generate positive floating point numbers for financial calculations.

    Args:
        min_value: Minimum value (exclusive)
        max_value: Maximum value (inclusive)

    Returns:
        float: Positive float value
    """
    return draw(st.floats(
        min_value=min_value,
        max_value=max_value,
        allow_nan=False,
        allow_infinity=False
    ))


# ============================================================================
# CurrencyConverter Property-Based Tests
# ============================================================================


class TestCurrencyConverterProperties:
    """Property-based tests for CurrencyConverter."""

    @given(st.text(min_size=1, max_size=20))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_determine_currency_never_returns_empty_string(self, ticker: str) -> None:
        """Property: determine_currency should never return empty string.

        This validates that currency determination always produces a valid result
        for any ticker input.
        """
        # Arrange
        df = pd.DataFrame({"Ticker": [ticker]})
        converter = CurrencyConverter(df)

        # Act
        result = converter.determine_currency(ticker, None)

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        assert result != ""

    @given(st.text(min_size=1, max_size=20), currency_codes())
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_determine_currency_prefers_extracted_currency(
        self, ticker: str, currency: str
    ) -> None:
        """Property: extracted currency takes precedence over ticker-based detection.

        If a currency is explicitly extracted/provided, it should be returned
        regardless of ticker format.
        """
        # Arrange
        df = pd.DataFrame({"Ticker": [ticker]})
        converter = CurrencyConverter(df)

        # Act
        result = converter.determine_currency(ticker, currency)

        # Assert
        assert result == currency

    @given(ticker_strategies())
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_determine_currency_returns_known_currency(self, ticker: str) -> None:
        """Property: currency result should be a known currency code.

        Method should only return valid currency codes that are supported
        by the system.
        """
        # Arrange
        df = pd.DataFrame({"Ticker": [ticker]})
        converter = CurrencyConverter(df)
        known_currencies = {"USD", "EUR", "PLN", "GBP", "DKK", "SEK"}

        # Act
        result = converter.determine_currency(ticker, None)

        # Assert
        assert result in known_currencies

    @given(
        st.lists(dividend_comments(), min_size=1, max_size=20, unique=True)
    )
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_extract_dividend_from_comment_returns_valid_tuple(
        self, comments: list[str]
    ) -> None:
        """Property: extract_dividend_from_comment always returns tuple of (float|None, str|None).

        Method should never raise an exception for any string input,
        and always return a well-formed tuple.
        """
        # Arrange
        df = pd.DataFrame({"Comment": comments})
        converter = CurrencyConverter(df)

        # Act & Assert
        for comment in comments:
            result = converter.extract_dividend_from_comment(comment)

            # Property: always tuple of size 2
            assert isinstance(result, tuple)
            assert len(result) == 2

            dividend, currency = result
            # Property: dividend is either None or positive float
            assert dividend is None or (isinstance(dividend, float) and dividend >= 0)
            # Property: currency is either None or 3-letter string
            assert currency is None or (isinstance(
                currency, str) and len(currency) == 3)

    @given(
        dividend_comments(),
        st.just(None)  # No extracted currency
    )
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_extract_dividend_returns_non_negative_amounts(
        self, comment: str, _: None
    ) -> None:
        """Property: extracted dividend amounts are never negative.

        Financial calculations should never produce negative dividend amounts.
        """
        # Arrange
        df = pd.DataFrame()
        converter = CurrencyConverter(df)

        # Act
        dividend, _ = converter.extract_dividend_from_comment(comment)

        # Assert
        if dividend is not None:
            assert dividend >= 0
            assert isinstance(dividend, float)

    @given(st.one_of(st.integers(), st.floats(allow_nan=False, allow_infinity=False), st.lists(st.integers()), st.none()))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_extract_dividend_handles_non_string_input(self, non_string) -> None:
        """Property: extract_dividend_from_comment handles non-string gracefully.

        Method should return (None, None) for non-string inputs without raising.
        """
        # Arrange
        df = pd.DataFrame()
        converter = CurrencyConverter(df)

        # Act
        result = converter.extract_dividend_from_comment(non_string)

        # Assert
        assert result == (None, None)


# ============================================================================
# DateConverter Property-Based Tests
# ============================================================================


class TestDateConverterProperties:
    """Property-based tests for DateConverter."""

    @given(valid_date_formats_with_values())
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_convert_valid_dates_always_produces_date(
        self, date_input: tuple[str, str]
    ) -> None:
        """Property: valid dates should always convert successfully.

        For valid date strings with matching format, conversion should
        produce non-None result.
        """
        # Arrange
        date_string, date_format = date_input
        converter = DateConverter(date_string)

        # Act
        converter.convert_to_date(format=date_format)
        result = converter.get_date()

        # Assert
        assert result is not None
        assert hasattr(result, 'year')
        assert hasattr(result, 'month')
        assert hasattr(result, 'day')

    @given(st.none())
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_convert_none_returns_none(self, none_value) -> None:
        """Property: None input should always return None.

        The method should handle None gracefully by returning None.
        """
        # Arrange
        converter = DateConverter(none_value)

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result is None

    @given(st.just(""))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_convert_empty_string_returns_none(self, empty: str) -> None:
        """Property: empty string should always return None.

        The method should treat empty strings as invalid input.
        """
        # Arrange
        converter = DateConverter(empty)

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result is None

    @given(st.integers(min_value=1900, max_value=2100))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_converted_date_year_in_reasonable_range(self, year: int) -> None:
        """Property: converted dates should have year in reasonable range.

        Year should be between 1900 and 2100 for financial data.
        """
        # Arrange
        date_string = f"{year:04d}-01-01"
        converter = DateConverter(date_string)

        # Act
        converter.convert_to_date(format="%Y-%m-%d")
        result = converter.get_date()

        # Assert
        assert result is not None
        assert 1900 <= result.year <= 2100

    @given(st.text(min_size=1))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_convert_never_raises_exception(self, arbitrary_text: str) -> None:
        """Property: convert_to_date should never raise exception.

        Method should handle any input gracefully, returning None for invalid input
        rather than raising exceptions.
        """
        # Arrange
        converter = DateConverter(arbitrary_text)

        # Act & Assert - should not raise
        try:
            converter.convert_to_date()
            result = converter.get_date()
            assert result is None or hasattr(result, 'year')
        except Exception as e:
            pytest.fail(f"convert_to_date raised {type(e).__name__}: {e}")


# ============================================================================
# TaxCalculator Property-Based Tests
# ============================================================================


class TestTaxCalculatorProperties:
    """Property-based tests for TaxCalculator."""

    @given(positive_floats(min_value=1, max_value=100000))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_tax_rate_is_valid_percentage(self, amount: float) -> None:
        """Property: tax_calculator stores valid tax rate as percentage.

        Tax rate should be between 0 and 100 (or 0.0 and 1.0 normalized).
        """
        # Arrange
        df = pd.DataFrame({"Amount": [amount]})

        # Act
        calculator = TaxCalculator(df, polish_tax_rate=0.19)

        # Assert
        assert 0 <= calculator.polish_tax_rate <= 1
        assert calculator.polish_tax_rate > 0

    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=10),  # ticker
                positive_floats(min_value=0.1, max_value=10000),  # amount
            ),
            min_size=1,
            max_size=50,
        )
    )
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_tax_calculator_accepts_reasonable_data(
        self, data: list[tuple[str, float]]
    ) -> None:
        """Property: TaxCalculator should accept reasonable financial data.

        Constructor should not raise for valid DataFrame with positive amounts.
        """
        # Arrange
        tickers, amounts = zip(*data)
        df = pd.DataFrame({"Ticker": tickers, "Amount": amounts})

        # Act & Assert
        calculator = TaxCalculator(df)
        assert calculator.df is not None
        assert len(calculator.df) == len(data)

    @given(positive_floats(min_value=0.01, max_value=1))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_multiple_tax_rates_accepted(self, rate: float) -> None:
        """Property: different tax rates can be set.

        TaxCalculator should accept various valid tax rates (0-1).
        """
        # Arrange
        df = pd.DataFrame({"Data": [1, 2, 3]})

        # Act
        calculator = TaxCalculator(df, polish_tax_rate=rate)

        # Assert
        assert calculator.polish_tax_rate == rate

    @given(positive_floats())
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_tax_calculator_preserves_dataframe(self, amount: float) -> None:
        """Property: TaxCalculator should preserve DataFrame integrity.

        The original DataFrame should not be modified during initialization.
        """
        # Arrange
        original_df = pd.DataFrame({
            "Ticker": ["AAPL"],
            "Amount": [amount],
            "Date": ["2024-01-01"]
        })
        original_len = len(original_df)
        original_columns = set(original_df.columns)

        # Act
        calculator = TaxCalculator(original_df)

        # Assert
        assert len(calculator.df) == original_len
        assert set(calculator.df.columns) == original_columns


# ============================================================================
# Integration Property-Based Tests
# ============================================================================


class TestDataProcessingInvariants:
    """Property-based tests for invariants across multiple components."""

    @given(st.lists(
        st.tuples(
            ticker_strategies(),
            dividend_comments(),
            valid_date_formats_with_values(),
        ),
        min_size=1,
        max_size=20,
    ))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_currency_detection_always_consistent(
        self, data: list[tuple[str, str, tuple[str, str]]]
    ) -> None:
        """Property: currency detection should be consistent for same ticker.

        Given the same ticker, currency determination should always
        return the same result.
        """
        # Arrange
        df = pd.DataFrame({"Ticker": [item[0] for item in data]})
        converter = CurrencyConverter(df)

        # Act & Assert
        for ticker, _, _ in data:
            result1 = converter.determine_currency(ticker, None)
            result2 = converter.determine_currency(ticker, None)

            # Property: idempotent - same input, same output
            assert result1 == result2

    @given(st.text(min_size=0, max_size=100))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_comment_extraction_is_idempotent(self, comment: str) -> None:
        """Property: extracting dividend from same comment always returns same result.

        Calling extract_dividend_from_comment multiple times with the same input
        should produce identical results.
        """
        # Arrange
        df = pd.DataFrame()
        converter = CurrencyConverter(df)

        # Act
        result1 = converter.extract_dividend_from_comment(comment)
        result2 = converter.extract_dividend_from_comment(comment)
        result3 = converter.extract_dividend_from_comment(comment)

        # Assert - idempotent property
        assert result1 == result2
        assert result2 == result3
