"""Advanced property-based tests for complex data transformations.

This module extends property-based testing to cover more complex scenarios
including data aggregation, column formatting, and multi-step transformations.
"""

from __future__ import annotations

import pandas as pd
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from data_processing.currency_converter import CurrencyConverter

# Documented ticker-suffix → currency mapping that ``_currency_for_ticker``
# claims to implement. Tests verify the SUT against this table rather than
# trivial set-membership, so a mis-mapped suffix fails loudly.
SUFFIX_CURRENCY = {
    ".US": "USD",
    ".PL": "PLN",
    ".DK": "DKK",
    ".UK": "GBP",
    ".FR": "EUR",
    ".DE": "EUR",
    ".IE": "EUR",
    ".NL": "EUR",
    ".ES": "EUR",
    ".IT": "EUR",
    ".BE": "EUR",
    ".AT": "EUR",
    ".FI": "EUR",
    ".PT": "EUR",
}

# ============================================================================
# Custom Strategies for Complex Data Structures
# ============================================================================


@st.composite
def numeric_strings(draw, min_value: float = 0, max_value: float = 100000) -> str:
    """Generate strings representing numeric values.

    Patterns: "123.45", "1,234.56", "1 234,56", etc.
    """
    value = draw(
        st.floats(
            min_value=min_value,
            max_value=max_value,
            allow_nan=False,
            allow_infinity=False,
        )
    )

    # Different numeric formats
    formats = [
        str(abs(value)),  # Standard decimal
        f"{abs(value):.2f}",  # With 2 decimal places
        f"{abs(value):,.2f}",  # With thousand separator
        f"{abs(value):,.0f}",  # Integer format
    ]

    return draw(st.sampled_from(formats))


@st.composite
def currency_amount_strings(draw) -> str:
    """Generate strings in format 'AMOUNT CURRENCY'.

    Examples: "123.45 USD", "1234,56 EUR", "999.99 PLN"
    """
    amount = draw(numeric_strings(min_value=0.01, max_value=100000))
    currencies = ["USD", "EUR", "PLN", "GBP", "DKK", "JPY", "CAD"]
    currency = draw(st.sampled_from(currencies))

    return f"{amount} {currency}"


@st.composite
def date_strings_various_formats(draw) -> str:
    """Generate date strings in different formats.

    Examples: "2024-01-15", "01/15/2024", "2024.01.15", "15.01.2024"
    """

    year = draw(st.integers(min_value=2000, max_value=2050))

    month = draw(st.integers(min_value=1, max_value=12))

    # Determine max day
    if month in [1, 3, 5, 7, 8, 10, 12]:
        max_day = 31
    elif month in [4, 6, 9, 11]:
        max_day = 30
    else:
        max_day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28

    day = draw(st.integers(min_value=1, max_value=max_day))

    formats = [
        f"{year}-{month:02d}-{day:02d}",
        f"{day:02d}/{month:02d}/{year}",
        f"{year}.{month:02d}.{day:02d}",
        f"{day:02d}.{month:02d}.{year}",
    ]

    return draw(st.sampled_from(formats))


@st.composite
def dividend_dataframes(draw, min_rows: int = 1, max_rows: int = 20) -> pd.DataFrame:
    """Generate realistic dividend DataFrames for testing.

    Args:
        min_rows: Minimum number of rows
        max_rows: Maximum number of rows

    Returns:
        pd.DataFrame with dividend data
    """
    num_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))

    tickers = draw(
        st.lists(
            st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=6),
            min_size=num_rows,
            max_size=num_rows,
        )
    )

    amounts = draw(
        st.lists(
            st.floats(
                min_value=0.01, max_value=10000, allow_nan=False, allow_infinity=False
            ),
            min_size=num_rows,
            max_size=num_rows,
        )
    )

    dates = draw(
        st.lists(
            date_strings_various_formats(),
            min_size=num_rows,
            max_size=num_rows,
        )
    )

    return pd.DataFrame(
        {
            "Ticker": [t.upper() for t in tickers],
            "Amount": amounts,
            "Date": dates,
        }
    )


@st.composite
def shr_amount_strings(draw) -> str:
    """Generate plain decimal amount strings the SHR regexes can round-trip.

    Always of the form ``"<int>.<4 digits>"`` so it matches ``[\\d.]+`` and
    parses cleanly with ``float`` (no thousand separators or scientific
    notation that would defeat an exact round-trip).
    """
    whole = draw(st.integers(min_value=0, max_value=99999))
    frac = draw(st.integers(min_value=0, max_value=9999))
    return f"{whole}.{frac:04d}"


_SHR_CURRENCIES = ["USD", "EUR", "PLN", "GBP", "DKK", "JPY", "CAD"]


# ============================================================================
# Note: ColumnFormatter Property-Based Tests Skipped
# ============================================================================
# ColumnFormatter requires DataFrame initialization, which makes it difficult
# to test with property-based strategies for simple value formatting.
# See test_unit/test_column_formatter.py for unit tests of formatting operations.


# ============================================================================
# Complex Data Transformation Invariants
# ============================================================================


class TestDataTransformationInvariants:
    """Property-based invariants over real CurrencyConverter transformations.

    Each test exercises a distinct branch of the parsing/mapping logic and
    asserts a relation between input and output, so a mutation that breaks
    the branch produces a failing example.
    """

    @given(currency=st.sampled_from(_SHR_CURRENCIES), amount=shr_amount_strings())
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_extract_dividend_round_trips_currency_then_amount_format(
        self, currency: str, amount: str
    ) -> None:
        """Property: ``"<CUR> <amount>/ SHR"`` round-trips to (amount, CUR).

        Exercises the ``([A-Z]{3}) ([\\d.]+)/ SHR`` branch.
        """
        # Arrange
        converter = CurrencyConverter(pd.DataFrame())
        comment = f"{currency} {amount}/ SHR"

        # Act
        result_amount, result_currency = converter.extract_dividend_from_comment(
            comment
        )

        # Assert
        assert result_currency == currency
        assert result_amount == pytest.approx(float(amount))

    @given(currency=st.sampled_from(_SHR_CURRENCIES), amount=shr_amount_strings())
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_extract_dividend_round_trips_amount_then_currency_format(
        self, currency: str, amount: str
    ) -> None:
        """Property: ``"<amount> <CUR>/SHR"`` round-trips to (amount, CUR).

        Exercises the alternative ``([\\d.]+) ([A-Z]{3})/SHR`` branch.
        """
        # Arrange
        converter = CurrencyConverter(pd.DataFrame())
        comment = f"{amount} {currency}/SHR"

        # Act
        result_amount, result_currency = converter.extract_dividend_from_comment(
            comment
        )

        # Assert
        assert result_currency == currency
        assert result_amount == pytest.approx(float(amount))

    @given(amount=shr_amount_strings())
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_extract_dividend_bare_number_returns_amount_and_no_currency(
        self, amount: str
    ) -> None:
        """Property: a bare numeric comment yields (amount, None).

        Exercises the final number-only branch, where no currency is present.
        """
        # Arrange
        converter = CurrencyConverter(pd.DataFrame())

        # Act
        result_amount, result_currency = converter.extract_dividend_from_comment(amount)

        # Assert
        assert result_currency is None
        assert result_amount == pytest.approx(float(amount))

    @given(
        base=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=5),
        suffix=st.sampled_from(sorted(SUFFIX_CURRENCY)),
    )
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_determine_currency_maps_each_suffix_to_documented_currency(
        self, base: str, suffix: str
    ) -> None:
        """Property: every documented ticker suffix maps to its claimed currency.

        Verifies ``determine_currency`` (via ``_currency_for_ticker``) against
        the documented mapping, not mere ``Currency``-enum membership.
        """
        # Arrange
        ticker = base + suffix
        assume("ASB.PL" not in ticker)  # ASB.PL is a documented USD special case
        converter = CurrencyConverter(pd.DataFrame())

        # Act
        result = converter.determine_currency(ticker, None)

        # Assert
        assert result == SUFFIX_CURRENCY[suffix]
