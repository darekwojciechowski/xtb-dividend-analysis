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

from decimal import Decimal

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from config.settings import settings
from data_processing.constants import Currency
from data_processing.currency_converter import CurrencyConverter
from data_processing.date_converter import DateConverter, convert_date
from data_processing.tax_calculator import TaxCalculator
from tests.metamorphic.conftest import dividend_rows

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
        alphabet=st.characters(
            blacklist_categories=("Cc", "Cs"), blacklist_characters=".,!?"
        ),
        min_size=1,
        max_size=5,
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
    generated = draw(
        st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=3, max_size=3)
    )
    return draw(st.sampled_from(common_currencies + [generated]))


@st.composite
def dividend_comments(draw) -> str:
    """Generate realistic dividend payment comments.

    Returns:
        str: Comment string with dividend information
    """
    amount = draw(
        st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000"), places=4)
    )
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
        (
            f"{day:02d}.{month:02d}.{year} {hour:02d}:{minute:02d}:{second:02d}",
            "%d.%m.%Y %H:%M:%S",
        ),
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
    return draw(
        st.floats(
            min_value=min_value,
            max_value=max_value,
            allow_nan=False,
            allow_infinity=False,
        )
    )


# ============================================================================
# CurrencyConverter Property-Based Tests
# ============================================================================


class TestCurrencyConverterProperties:
    """Property-based tests for CurrencyConverter."""

    @given(st.text(min_size=1, max_size=20))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_determine_currency_returns_supported_currency_enum_value(
        self, ticker: str
    ) -> None:
        """Invariant: every ticker resolves to a value declared in ``Currency``.

        Domain rule: the pipeline can only price assets in currencies it has
        NBP rates for. Any ticker the parser accepts must therefore map to a
        ``Currency`` enum member — never to a fabricated or unsupported code.
        """
        # Arrange
        df = pd.DataFrame({"Ticker": [ticker]})
        converter = CurrencyConverter(df)
        supported = {c.value for c in Currency}

        # Act
        result = converter.determine_currency(ticker, None)

        # Assert
        assert result in supported

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
    def test_determine_currency_returns_currency_enum_value_for_known_suffixes(
        self, ticker: str
    ) -> None:
        """Invariant: a ticker drawn from realistic suffixes maps to a ``Currency`` value.

        Stronger than the generic-text variant above because the strategy
        only produces suffixes the pipeline actually claims to support.
        """
        # Arrange
        df = pd.DataFrame({"Ticker": [ticker]})
        converter = CurrencyConverter(df)
        supported = {c.value for c in Currency}

        # Act
        result = converter.determine_currency(ticker, None)

        # Assert
        assert result in supported

    @given(st.lists(dividend_comments(), min_size=1, max_size=20, unique=True))
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
            assert currency is None or (
                isinstance(currency, str) and len(currency) == 3
            )

    @given(
        dividend_comments(),
        st.just(None),  # No extracted currency
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

    @given(
        st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.lists(st.integers()),
            st.none(),
        )
    )
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
        assert hasattr(result, "year")
        assert hasattr(result, "month")
        assert hasattr(result, "day")

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

    @given(
        st.dates(
            min_value=pd.Timestamp("2000-01-01").date(),
            max_value=pd.Timestamp("2099-12-31").date(),
        )
    )
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_convert_date_iso_roundtrip_is_idempotent(self, d) -> None:
        """Invariant: ``convert_date(d.isoformat(), "%Y-%m-%d")`` returns ``d``.

        The function is documented as a parser, not a transform. Round-tripping
        through ISO formatting must recover the original date for any valid
        date — otherwise downstream date arithmetic silently drifts.
        """
        # Arrange
        iso = d.isoformat()

        # Act
        first = convert_date(iso, format="%Y-%m-%d")
        second = convert_date(first.isoformat(), format="%Y-%m-%d")

        # Assert
        assert first == d
        assert second == first

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
            assert result is None or hasattr(result, "year")
        except Exception as e:
            pytest.fail(f"convert_to_date raised {type(e).__name__}: {e}")


# ============================================================================
# TaxCalculator Property-Based Tests
# ============================================================================


def _tax_pln_amount(result_str: str) -> float:
    """Parse a ``Tax Amount PLN`` cell, treating ``"-"`` as zero."""
    if result_str == "-":
        return 0.0
    return float(result_str.replace(" PLN", "").strip())


class TestTaxCalculatorProperties:
    """Domain invariants for TaxCalculator on a PLN-denominated statement."""

    @given(dividend_rows())
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_tax_pln_never_exceeds_gross_times_belka_rate(
        self, df: pd.DataFrame
    ) -> None:
        """Invariant: per-row Tax Amount PLN ≤ Net Dividend × polish_tax_rate.

        The Belka top-up cannot be larger than the full Belka liability on the
        gross dividend (because it is reduced by tax already withheld at source).
        Anything beyond that means the formula is over-collecting.
        """
        # Arrange
        calculator = TaxCalculator(df.copy())
        rate = calculator.polish_tax_rate

        # Act
        result = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        for _, row in result.iterrows():
            gross = float(row["Net Dividend"].split()[0])
            tax_pln = _tax_pln_amount(row["Tax Amount PLN"])
            # Allow a tiny rounding slack since the formatted value is rounded
            # to 2 decimal places.
            assert tax_pln <= gross * rate + 0.01, (
                f"tax_pln={tax_pln} exceeds gross*rate={gross * rate} "
                f"for row {row.to_dict()}"
            )

    @given(
        st.floats(min_value=10.0, max_value=10000.0, allow_nan=False),
        st.floats(min_value=20.0, max_value=10000.0, allow_nan=False),
        st.floats(min_value=0.0, max_value=0.18, allow_nan=False),
    )
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_tax_pln_monotonic_in_gross_when_wht_held_constant(
        self, low: float, delta: float, wht_pct: float
    ) -> None:
        """Invariant: holding the WHT rate fixed, Tax Amount PLN is non-decreasing in gross.

        Tax = (gross × 19% − tax_collected_amount) × fx, with
        tax_collected_amount = gross × wht_pct. Both terms grow linearly with
        gross, so a larger gross must never produce a smaller Belka top-up.
        """
        # Arrange — same wht rate, two grosses (low and high = low + delta)
        high = low + delta

        def _row(net: float) -> dict:
            return {
                "Date": "2025-02-21",
                "Ticker": "TXT.PL",
                "Net Dividend": f"{net:.2f} PLN",
                "Tax Collected": wht_pct,
                "Tax Collected Amount": f"{net * wht_pct:.2f} PLN",
                "Exchange Rate D-1": "-",
            }

        df = pd.DataFrame([_row(low), _row(high)])
        calculator = TaxCalculator(df)

        # Act
        result = calculator.calculate_tax_for_pln_statement("PLN")
        tax_low = _tax_pln_amount(result.iloc[0]["Tax Amount PLN"])
        tax_high = _tax_pln_amount(result.iloc[1]["Tax Amount PLN"])

        # Assert — high gross must owe at least as much as low gross
        assert tax_high + 0.01 >= tax_low, (
            f"non-monotonic: gross {low}→{tax_low}, gross {high}→{tax_high}"
        )

    @given(dividend_rows())
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_tax_pln_zero_when_wht_meets_belka_rate(self, df: pd.DataFrame) -> None:
        """Invariant: any row where Tax Collected ≥ polish_tax_rate yields ``"-"``.

        The statute considers Belka satisfied at source; the pipeline must not
        compute an additional top-up in that case.
        """
        # Arrange — force every row to clear the Belka threshold.
        df = df.copy()
        df["Tax Collected"] = settings.polish_tax_rate
        calculator = TaxCalculator(df)

        # Act
        result = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        assert (result["Tax Amount PLN"] == "-").all()


# ============================================================================
# Integration Property-Based Tests
# ============================================================================


class TestDataProcessingInvariants:
    """Property-based tests for invariants across multiple components."""

    @given(
        st.lists(
            st.tuples(
                ticker_strategies(),
                dividend_comments(),
                valid_date_formats_with_values(),
            ),
            min_size=1,
            max_size=20,
        )
    )
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
