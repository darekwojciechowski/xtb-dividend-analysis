"""Unit tests for DataAggregator."""

from __future__ import annotations

import pandas as pd
import pytest

from data_processing.data_aggregator import DataAggregator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01"],
            "Ticker": ["AAPL", "AAPL"],
            "Net Dividend": [10.0, 5.0],
            "Shares": [2.0, 2.0],
            "Type": ["DIV", "DIV"],
            "Comment": ["x", "y"],
        }
    )


# ---------------------------------------------------------------------------
# add_empty_column
# ---------------------------------------------------------------------------


def test_add_empty_column_inserts_when_missing():
    df = pd.DataFrame({"A": [1, 2]})
    agg = DataAggregator(df)
    result = agg.add_empty_column(col_name="Tax Collected", position=0)

    assert "Tax Collected" in result.columns


def test_add_empty_column_skips_insert_when_already_present():
    df = pd.DataFrame({"Tax Collected": [99.0], "A": [1]})
    agg = DataAggregator(df)
    result = agg.add_empty_column(col_name="Tax Collected", position=0)

    # Column still there, value unchanged
    assert list(result["Tax Collected"]) == [99.0]


# ---------------------------------------------------------------------------
# merge_rows_and_reorder — Tax Collected branch (lines 117-118)
# ---------------------------------------------------------------------------


def test_merge_rows_and_reorder_aggregates_tax_collected(basic_df):
    basic_df["Tax Collected"] = [-1.5, -1.5]
    agg = DataAggregator(basic_df)
    result = agg.merge_rows_and_reorder()

    assert "Tax Collected" in result.columns
    assert len(result) == 1
    assert result["Net Dividend"].iloc[0] == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# merge_rows_and_reorder — Tax Collected Raw branch (lines 121-122)
# ---------------------------------------------------------------------------


def test_merge_rows_and_reorder_sums_tax_collected_raw(basic_df):
    basic_df["Tax Collected"] = [-1.5, -1.5]
    basic_df["Tax Collected Raw"] = [0.5, 0.5]
    agg = DataAggregator(basic_df)
    result = agg.merge_rows_and_reorder()

    assert "Tax Collected Raw" in result.columns
    assert result["Tax Collected Raw"].iloc[0] == pytest.approx(1.0)


def test_merge_rows_and_reorder_with_both_tax_columns(basic_df):
    basic_df["Tax Collected"] = [-1.5, -1.5]
    basic_df["Tax Collected Raw"] = [0.3, 0.7]
    agg = DataAggregator(basic_df)
    result = agg.merge_rows_and_reorder()

    assert "Tax Collected" in result.columns
    assert "Tax Collected Raw" in result.columns
    assert result["Tax Collected Raw"].iloc[0] == pytest.approx(1.0)
