"""Unit tests for DividendFilter.

Covers dividend-type filtering and grouping/aggregation behaviour.

Test classes:
    TestFilterDividends   — keeps valid types, removes non-dividend rows, handles NaN
    TestGroupByDividends  — aggregates Amount sums, renames to Net Dividend, row count

All tests are marked ``@pytest.mark.unit``.
"""

from __future__ import annotations

import pandas as pd
import pytest

from data_processing.dividend_filter import DividendFilter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_TYPES = [
    "Dividend",
    "Dywidenda",
    "DIVIDENT",
    "Withholding Tax",
    "Podatek od dywidend",
]


def _make_df(
    types: list[str | None], amounts: list[float] | None = None
) -> pd.DataFrame:
    """Build a minimal DataFrame with Date, Ticker, Type, Amount, Comment columns."""
    n = len(types)
    if amounts is None:
        amounts = [1.0] * n
    return pd.DataFrame(
        {
            "Date": ["2024-01-15"] * n,
            "Ticker": ["SBUX.US"] * n,
            "Type": types,
            "Amount": amounts,
            "Comment": ["some comment"] * n,
        }
    )


# ---------------------------------------------------------------------------
# TestFilterDividends
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterDividends:
    """Tests for DividendFilter.filter_dividends."""

    @pytest.mark.parametrize("dividend_type", _VALID_TYPES)
    def test_filter_when_valid_type_then_row_is_kept(self, dividend_type: str) -> None:
        """Each of the five accepted Type values passes the filter."""
        # Arrange
        df = _make_df([dividend_type, "Transfer"])
        flt = DividendFilter(df)

        # Act
        result = flt.filter_dividends()

        # Assert
        assert len(result) == 1
        assert result.iloc[0]["Type"] == dividend_type

    def test_filter_when_non_dividend_types_present_then_removed(self) -> None:
        """Rows with types like 'Transfer' or 'Deposit' are dropped."""
        # Arrange
        df = _make_df(["Dividend", "Transfer", "Deposit", "Dywidenda"])
        flt = DividendFilter(df)

        # Act
        result = flt.filter_dividends()

        # Assert
        assert len(result) == 2
        assert set(result["Type"].tolist()) == {"Dividend", "Dywidenda"}

    def test_filter_when_all_five_valid_types_present_then_all_kept(self) -> None:
        """All five valid types survive the filter simultaneously."""
        # Arrange
        df = _make_df(_VALID_TYPES)
        flt = DividendFilter(df)

        # Act
        result = flt.filter_dividends()

        # Assert
        assert len(result) == len(_VALID_TYPES)

    def test_filter_when_nan_type_then_nan_rows_removed(self) -> None:
        """NaN Type values are dropped before type matching."""
        # Arrange
        df = _make_df(["Dividend", None, "Withholding Tax"])
        flt = DividendFilter(df)

        # Act
        result = flt.filter_dividends()

        # Assert
        assert result["Type"].isna().sum() == 0
        assert len(result) == 2

    def test_filter_returns_dataframe(self) -> None:
        """Return value is always a pd.DataFrame."""
        # Arrange
        flt = DividendFilter(_make_df(["Dividend"]))

        # Act
        result = flt.filter_dividends()

        # Assert
        assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# TestGroupByDividends
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGroupByDividends:
    """Tests for DividendFilter.group_by_dividends."""

    def test_group_when_duplicate_rows_then_amounts_are_summed(self) -> None:
        """Rows with identical Date/Ticker/Type/Comment have their Amount summed."""
        # Arrange
        df = pd.DataFrame(
            {
                "Date": ["2024-01-15", "2024-01-15"],
                "Ticker": ["SBUX.US", "SBUX.US"],
                "Type": ["Dividend", "Dividend"],
                "Comment": ["USD 0.57/ SHR", "USD 0.57/ SHR"],
                "Amount": [5.70, 3.00],
            }
        )
        flt = DividendFilter(df)

        # Act
        result = flt.group_by_dividends()

        # Assert
        assert len(result) == 1
        assert result.iloc[0]["Net Dividend"] == pytest.approx(8.70)

    def test_group_when_distinct_tickers_then_separate_rows(self) -> None:
        """Different tickers produce separate rows after grouping."""
        # Arrange
        df = pd.DataFrame(
            {
                "Date": ["2024-01-15", "2024-01-15"],
                "Ticker": ["SBUX.US", "MSFT.US"],
                "Type": ["Dividend", "Dividend"],
                "Comment": ["USD 0.57/ SHR", "USD 0.75/ SHR"],
                "Amount": [5.70, 7.50],
            }
        )
        flt = DividendFilter(df)

        # Act
        result = flt.group_by_dividends()

        # Assert
        assert len(result) == 2

    def test_group_renames_amount_to_net_dividend(self) -> None:
        """After grouping, the column is renamed from Amount to Net Dividend."""
        # Arrange
        df = _make_df(["Dividend"])
        flt = DividendFilter(df)

        # Act
        result = flt.group_by_dividends()

        # Assert
        assert "Net Dividend" in result.columns
        assert "Amount" not in result.columns

    def test_group_returns_dataframe(self) -> None:
        """Return value is always a pd.DataFrame."""
        # Arrange
        flt = DividendFilter(_make_df(["Dividend"]))

        # Act
        result = flt.group_by_dividends()

        # Assert
        assert isinstance(result, pd.DataFrame)

    def test_group_when_single_row_then_value_preserved(self) -> None:
        """Single row is unchanged after grouping (no aggregation needed)."""
        # Arrange
        df = _make_df(["Dividend"], amounts=[12.34])
        flt = DividendFilter(df)

        # Act
        result = flt.group_by_dividends()

        # Assert
        assert result.iloc[0]["Net Dividend"] == pytest.approx(12.34)
