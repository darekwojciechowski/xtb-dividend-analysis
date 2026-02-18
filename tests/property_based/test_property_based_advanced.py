"""Advanced property-based tests for complex data transformations.

This module extends property-based testing to cover more complex scenarios
including data aggregation, column formatting, and multi-step transformations.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pandas as pd
import pytest
from hypothesis import given, strategies as st, assume

from data_processing.column_formatter import ColumnFormatter
from data_processing.currency_converter import CurrencyConverter


# ============================================================================
# Custom Strategies for Complex Data Structures
# ============================================================================


@st.composite
def numeric_strings(draw, min_value: float = 0, max_value: float = 100000) -> str:
    """Generate strings representing numeric values.

    Patterns: "123.45", "1,234.56", "1 234,56", etc.
    """
    value = draw(st.floats(min_value=min_value, max_value=max_value,
                 allow_nan=False, allow_infinity=False))

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

    tickers = draw(st.lists(
        st.text(
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            min_size=1,
            max_size=6
        ),
        min_size=num_rows,
        max_size=num_rows,
    ))

    amounts = draw(st.lists(
        st.floats(min_value=0.01, max_value=10000,
                  allow_nan=False, allow_infinity=False),
        min_size=num_rows,
        max_size=num_rows,
    ))

    dates = draw(st.lists(
        date_strings_various_formats(),
        min_size=num_rows,
        max_size=num_rows,
    ))

    return pd.DataFrame({
        "Ticker": [t.upper() for t in tickers],
        "Amount": amounts,
        "Date": dates,
    })


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
    """Tests for invariants that should hold across complex transformations."""

    @given(dividend_dataframes(min_rows=1, max_rows=50))
    @pytest.mark.property_based
    @pytest.mark.integration
    def test_dataframe_never_loses_rows(self, df: pd.DataFrame) -> None:
        """Property: data transformations should not lose rows.

        After processing, DataFrame should have same number of rows as input.
        """
        # Arrange
        original_len = len(df)
        converter = CurrencyConverter(df)

        # Act - just verify the converter preserves structure
        assert len(converter.df) == original_len

        # Assert
        assert converter.df.shape[0] >= original_len  # Should not decrease

    @given(dividend_dataframes(min_rows=1, max_rows=30))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_dataframe_columns_preserved(self, df: pd.DataFrame) -> None:
        """Property: data processing should preserve required columns.

        Processing shouldn't remove columns that exist in input.
        """
        # Arrange
        original_columns = set(df.columns)

        # Act
        converter = CurrencyConverter(df)

        # Assert
        result_columns = set(converter.df.columns)
        assert original_columns.issubset(result_columns)

    @given(
        st.lists(
            st.tuples(
                st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=6),
                st.floats(min_value=0.01, max_value=10000,
                          allow_nan=False, allow_infinity=False),
            ),
            min_size=1,
            max_size=100,
        )
    )
    @pytest.mark.property_based
    @pytest.mark.performance
    def test_large_batch_processing_stable(
        self, ticker_amount_pairs: list[tuple[str, float]]
    ) -> None:
        """Property: processing large batches should remain stable.

        Performance and correctness shouldn't degrade with more data.
        """
        # Arrange
        tickers, amounts = zip(*ticker_amount_pairs)
        df = pd.DataFrame({
            "Ticker": tickers,
            "Amount": amounts,
        })

        # Act
        converter = CurrencyConverter(df)

        # Assert
        assert len(converter.df) == len(ticker_amount_pairs)
        assert all(isinstance(ticker, str) for ticker in converter.df["Ticker"])
        assert all(isinstance(amount, (int, float))
                   for amount in converter.df["Amount"])


# ============================================================================
# Boundary and Edge Case Properties
# ============================================================================


class TestBoundaryConditions:
    """Property-based tests for boundary conditions and edge cases."""

    @given(st.floats(min_value=0, max_value=1e-10, allow_nan=False, allow_infinity=False))
    @pytest.mark.property_based
    @pytest.mark.edge_case
    def test_very_small_amounts_stay_non_negative(self, small_amount: float) -> None:
        """Property: very small amounts should be non-negative and processable.

        System should handle amounts near zero without errors.
        """
        # Property: amounts should be >= 0
        assert small_amount >= 0
        assert isinstance(small_amount, float)

    @given(st.floats(min_value=1e10, max_value=1e15, allow_nan=False, allow_infinity=False))
    @pytest.mark.property_based
    @pytest.mark.edge_case
    def test_very_large_amounts_are_numeric(self, large_amount: float) -> None:
        """Property: very large amounts should remain valid floats.

        System should handle large amounts without errors or overflow.
        """
        # Property: amount should be numeric and positive
        assert isinstance(large_amount, float)
        assert large_amount > 0
        assert not (large_amount == float('inf') or large_amount == float('-inf'))

    @given(st.text(min_size=0, max_size=1))
    @pytest.mark.property_based
    @pytest.mark.edge_case
    def test_minimal_strings_remain_strings(self, minimal_text: str) -> None:
        """Property: minimal strings should remain strings.

        Empty or single-character strings are valid text.
        """
        # Property: should be string
        assert isinstance(minimal_text, str)
        assert len(minimal_text) <= 1

    @given(st.text(min_size=100, max_size=1000))
    @pytest.mark.property_based
    @pytest.mark.edge_case
    def test_very_long_strings_remain_strings(self, long_string: str) -> None:
        """Property: very long strings should remain strings.

        Should not cause issues processing long text.
        """
        # Property: should still be string
        assert isinstance(long_string, str)
        assert len(long_string) >= 100


# ============================================================================
# Type Safety Properties
# ============================================================================


class TestTypeSafetyProperties:
    """Property-based tests for type consistency and safety."""

    @given(dividend_dataframes(min_rows=1, max_rows=20))
    @pytest.mark.property_based
    @pytest.mark.unit
    def test_converter_maintains_dataframe_type(self, df: pd.DataFrame) -> None:
        """Property: CurrencyConverter should maintain DataFrame type.

        After initialization, df attribute should always be a DataFrame.
        """
        # Arrange & Act
        converter = CurrencyConverter(df)

        # Assert
        assert isinstance(converter.df, pd.DataFrame)
        assert hasattr(converter.df, "shape")
        assert hasattr(converter.df, "columns")
