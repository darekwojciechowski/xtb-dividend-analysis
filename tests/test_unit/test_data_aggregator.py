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
    """Arrange: DataFrame without the target column.
    Act: call `add_empty_column` with `col_name='Tax Collected'`.
    Assert: `'Tax Collected'` column exists in the result.
    """
    df = pd.DataFrame({"A": [1, 2]})
    agg = DataAggregator(df)
    result = agg.add_empty_column(col_name="Tax Collected", position=0)

    assert "Tax Collected" in result.columns


def test_add_empty_column_skips_insert_when_already_present():
    """Arrange: DataFrame with `'Tax Collected'` already present and a known value.
    Act: call `add_empty_column` with `col_name='Tax Collected'`.
    Assert: the column is unchanged and the existing value is preserved.
    """
    df = pd.DataFrame({"Tax Collected": [99.0], "A": [1]})
    agg = DataAggregator(df)
    result = agg.add_empty_column(col_name="Tax Collected", position=0)

    # Column still there, value unchanged
    assert list(result["Tax Collected"]) == [99.0]


# ---------------------------------------------------------------------------
# merge_rows_and_reorder — Tax Collected branch (lines 117-118)
# ---------------------------------------------------------------------------


def test_merge_rows_and_reorder_aggregates_tax_collected(basic_df):
    """Arrange: two rows sharing the same Date and Ticker, each with `'Tax Collected'`.
    Act: call `merge_rows_and_reorder`.
    Assert: rows merge into one and `'Tax Collected'` column is present.
    """
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
    """Arrange: two matching rows each with a `'Tax Collected Raw'` value.
    Act: call `merge_rows_and_reorder`.
    Assert: `'Tax Collected Raw'` equals the sum of both rows.
    """
    basic_df["Tax Collected"] = [-1.5, -1.5]
    basic_df["Tax Collected Raw"] = [0.5, 0.5]
    agg = DataAggregator(basic_df)
    result = agg.merge_rows_and_reorder()

    assert "Tax Collected Raw" in result.columns
    assert result["Tax Collected Raw"].iloc[0] == pytest.approx(1.0)


def test_merge_rows_and_reorder_with_both_tax_columns(basic_df):
    """Arrange: two matching rows containing both `'Tax Collected'` and `'Tax Collected Raw'`.
    Act: call `merge_rows_and_reorder`.
    Assert: both tax columns are present in the merged result.
    """
    basic_df["Tax Collected"] = [-1.5, -1.5]
    basic_df["Tax Collected Raw"] = [0.3, 0.7]
    agg = DataAggregator(basic_df)
    result = agg.merge_rows_and_reorder()

    assert "Tax Collected" in result.columns
    assert "Tax Collected Raw" in result.columns
    assert result["Tax Collected Raw"].iloc[0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# merge_rows_and_reorder — Aggregation dict mutations
# ---------------------------------------------------------------------------


def test_merge_rows_and_reorder_net_dividend_summed_not_first():
    """Arrange: two rows with the same Date and Ticker and different Net Dividend values.
    Act: call `merge_rows_and_reorder`.
    Assert: Net Dividend equals the sum of both rows, not the first value alone.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01"],
            "Ticker": ["AAPL", "AAPL"],
            "Net Dividend": [10.5, 20.3],
            "Shares": [1.0, 1.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if agg_dict[NET_DIVIDEND] = "first" instead of "sum"
    assert len(result) == 1
    assert result["Net Dividend"].iloc[0] == pytest.approx(30.8)


def test_merge_rows_and_reorder_shares_summed_not_first():
    """Arrange: two rows with the same Date and Ticker and different Shares values.
    Act: call `merge_rows_and_reorder`.
    Assert: Shares equals the sum of both rows, not the first value alone.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01"],
            "Ticker": ["AAPL", "AAPL"],
            "Net Dividend": [10.0, 10.0],
            "Shares": [5.0, 3.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if agg_dict[SHARES] = "first" or "last" instead of "sum"
    assert result["Shares"].iloc[0] == pytest.approx(8.0)


def test_merge_rows_and_reorder_tax_collected_first_not_sum():
    """Arrange: two rows with the same Date and Ticker and different Tax Collected values.
    Act: call `merge_rows_and_reorder`.
    Assert: Tax Collected equals the first row's value, not the sum.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01"],
            "Ticker": ["AAPL", "AAPL"],
            "Net Dividend": [10.0, 10.0],
            "Shares": [1.0, 1.0],
            "Tax Collected": [1.5, 2.5],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if agg_dict[TAX_COLLECTED] = "sum" instead of "first"
    assert result["Tax Collected"].iloc[0] == pytest.approx(1.5)


def test_merge_rows_and_reorder_tax_collected_raw_summed_not_first():
    """Arrange: two rows with the same Date and Ticker and different Tax Collected Raw values.
    Act: call `merge_rows_and_reorder`.
    Assert: Tax Collected Raw equals the sum of both rows, not the first value alone.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01"],
            "Ticker": ["AAPL", "AAPL"],
            "Net Dividend": [10.0, 10.0],
            "Shares": [1.0, 1.0],
            "Tax Collected Raw": [2.0, 3.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if agg_dict[TAX_COLLECTED_RAW] = "first" instead of "sum"
    assert result["Tax Collected Raw"].iloc[0] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# merge_rows_and_reorder — Groupby mutations
# ---------------------------------------------------------------------------


def test_merge_rows_and_reorder_groups_by_date_and_ticker():
    """Arrange: multiple rows with different Date and Ticker combinations.
    Act: call `merge_rows_and_reorder`.
    Assert: rows are grouped only by matching Date and Ticker pairs, not collapsed.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "Ticker": ["AAPL", "MSFT", "AAPL"],
            "Net Dividend": [10.0, 5.0, 7.0],
            "Shares": [1.0, 1.0, 1.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if groupby uses only Date or only Ticker
    assert len(result) == 3


def test_merge_rows_and_reorder_multiple_tickers_same_date():
    """Arrange: two rows with the same Date but different Tickers.
    Act: call `merge_rows_and_reorder`.
    Assert: each ticker creates a separate row, not merged together.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01"],
            "Ticker": ["AAPL", "MSFT"],
            "Net Dividend": [10.0, 5.0],
            "Shares": [1.0, 1.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if groupby ignores Ticker
    assert len(result) == 2
    assert list(result["Ticker"]) == ["AAPL", "MSFT"]


def test_merge_rows_and_reorder_multiple_dates_same_ticker():
    """Arrange: two rows with the same Ticker but different Dates.
    Act: call `merge_rows_and_reorder`.
    Assert: each date creates a separate row, not merged together.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-02"],
            "Ticker": ["AAPL", "AAPL"],
            "Net Dividend": [10.0, 5.0],
            "Shares": [1.0, 1.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if groupby ignores Date
    assert len(result) == 2
    assert list(result["Date"]) == ["2024-01-01", "2024-01-02"]


# ---------------------------------------------------------------------------
# merge_rows_and_reorder — Column drops and ordering
# ---------------------------------------------------------------------------


def test_merge_rows_and_reorder_drops_type_column():
    """Arrange: DataFrame with a Type column present.
    Act: call `merge_rows_and_reorder`.
    Assert: Type column is removed from the result.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.0],
            "Shares": [1.0],
            "Type": ["DIV"],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if "Type" not in drop_columns
    assert "Type" not in result.columns


def test_merge_rows_and_reorder_drops_comment_column():
    """Arrange: DataFrame with a Comment column present.
    Act: call `merge_rows_and_reorder`.
    Assert: Comment column is removed from the result.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.0],
            "Shares": [1.0],
            "Comment": ["test comment"],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if "Comment" not in drop_columns
    assert "Comment" not in result.columns


def test_merge_rows_and_reorder_drops_both_type_and_comment():
    """Arrange: DataFrame with both Type and Comment columns present.
    Act: call `merge_rows_and_reorder`.
    Assert: both Type and Comment columns are removed from the result.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.0],
            "Shares": [1.0],
            "Type": ["DIV"],
            "Comment": ["test"],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if drop doesn't include both columns
    assert "Type" not in result.columns
    assert "Comment" not in result.columns


def test_merge_rows_and_reorder_custom_drop_columns():
    """Arrange: DataFrame with Type and Comment columns and an empty drop_columns list.
    Act: call `merge_rows_and_reorder` with `drop_columns=[]`.
    Assert: the custom parameter is used, overriding default drop behavior.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.0],
            "Shares": [1.0],
            "Type": ["DIV"],
            "Comment": ["test"],
        }
    )
    agg = DataAggregator(df)
    # When passing custom drop_columns, it replaces the default ["Type", "Comment"]
    result = agg.merge_rows_and_reorder(drop_columns=[])

    # Mutation: if drop_columns parameter not used
    # Since we didn't drop anything, but Type/Comment aren't in agg_dict,
    # they're already removed by groupby
    assert "Type" not in result.columns
    assert "Comment" not in result.columns


def test_merge_rows_and_reorder_shares_moved_to_end():
    """Arrange: DataFrame with Shares in the middle position.
    Act: call `merge_rows_and_reorder`.
    Assert: Shares column is at the end of the result.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.0],
            "Shares": [1.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if Shares not moved, or moved to wrong position
    assert result.columns[-1] == "Shares"


def test_merge_rows_and_reorder_shares_order_with_other_columns():
    """Arrange: DataFrame with multiple columns including Tax Collected and Shares.
    Act: call `merge_rows_and_reorder`.
    Assert: Shares is at the end and Tax Collected precedes it.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.0],
            "Tax Collected": [1.5],
            "Shares": [5.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if Shares moved to wrong position
    assert result.columns[-1] == "Shares"
    assert result.columns[-2] == "Tax Collected"


# ---------------------------------------------------------------------------
# merge_rows_and_reorder — Rounding mutations
# ---------------------------------------------------------------------------


def test_merge_rows_and_reorder_rounds_net_dividend_to_two_decimals():
    """Arrange: DataFrame with Net Dividend having many decimal places.
    Act: call `merge_rows_and_reorder`.
    Assert: Net Dividend is rounded to 2 decimal places.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.33333],
            "Shares": [1.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if round(n) not in code, or rounds to 1/3 decimals
    assert result["Net Dividend"].iloc[0] == pytest.approx(10.33)


def test_merge_rows_and_reorder_rounds_shares_to_two_decimals():
    """Arrange: DataFrame with Shares having many decimal places.
    Act: call `merge_rows_and_reorder`.
    Assert: Shares is rounded to 2 decimal places.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.0],
            "Shares": [5.55555],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if round(n) not in code, or rounds to 1/3 decimals
    assert result["Shares"].iloc[0] == pytest.approx(5.56)


def test_merge_rows_and_reorder_rounds_tax_collected_to_two_decimals():
    """Arrange: DataFrame with Tax Collected having many decimal places.
    Act: call `merge_rows_and_reorder`.
    Assert: Tax Collected is rounded to 2 decimal places.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.0],
            "Shares": [1.0],
            "Tax Collected": [1.77777],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if round(n) not in code, or rounds to 1/3 decimals
    assert result["Tax Collected"].iloc[0] == pytest.approx(1.78)


def test_merge_rows_and_reorder_rounding_preserves_zero():
    """Arrange: DataFrame with zero values for Net Dividend and Shares.
    Act: call `merge_rows_and_reorder`.
    Assert: rounding does not change zero values.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [0.0],
            "Shares": [0.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    assert result["Net Dividend"].iloc[0] == pytest.approx(0.0)
    assert result["Shares"].iloc[0] == pytest.approx(0.0)


def test_merge_rows_and_reorder_rounding_with_negative_values():
    """Arrange: DataFrame with negative Tax Collected having many decimal places.
    Act: call `merge_rows_and_reorder`.
    Assert: rounding works correctly with negative values.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.0],
            "Shares": [1.0],
            "Tax Collected": [-1.99999],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if rounding doesn't handle negatives properly
    assert result["Tax Collected"].iloc[0] == pytest.approx(-2.0)


# ---------------------------------------------------------------------------
# merge_rows_and_reorder — Conditional branch coverage
# ---------------------------------------------------------------------------


def test_merge_rows_and_reorder_without_tax_collected_column():
    """Arrange: two rows matching on Date and Ticker with no Tax Collected column.
    Act: call `merge_rows_and_reorder`.
    Assert: aggregation succeeds and Tax Collected column is not added to the result.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01"],
            "Ticker": ["AAPL", "AAPL"],
            "Net Dividend": [10.0, 5.0],
            "Shares": [1.0, 1.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if condition removed, code crashes when Tax Collected missing
    assert len(result) == 1
    assert "Tax Collected" not in result.columns


def test_merge_rows_and_reorder_without_tax_collected_raw_column():
    """Arrange: two rows matching on Date and Ticker with no Tax Collected Raw column.
    Act: call `merge_rows_and_reorder`.
    Assert: aggregation succeeds and Tax Collected Raw column is not added to the result.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01"],
            "Ticker": ["AAPL", "AAPL"],
            "Net Dividend": [10.0, 5.0],
            "Shares": [1.0, 1.0],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if condition removed, code crashes when Tax Collected Raw missing
    assert len(result) == 1
    assert "Tax Collected Raw" not in result.columns


def test_merge_rows_and_reorder_tax_collected_first_with_nan():
    """Arrange: two rows with the same Date and Ticker, Tax Collected has one NaN value.
    Act: call `merge_rows_and_reorder`.
    Assert: Tax Collected first aggregation correctly uses the non-NaN value.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01"],
            "Ticker": ["AAPL", "AAPL"],
            "Net Dividend": [10.0, 5.0],
            "Shares": [1.0, 1.0],
            "Tax Collected": [1.5, float("nan")],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if agg_dict[TAX_COLLECTED] uses wrong function
    assert result["Tax Collected"].iloc[0] == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# merge_rows_and_reorder — Edge cases and integration
# ---------------------------------------------------------------------------


def test_merge_rows_and_reorder_single_row_no_merge():
    """Arrange: DataFrame with a single row including Type and Comment columns.
    Act: call `merge_rows_and_reorder`.
    Assert: single row passes through with Type and Comment dropped.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.0],
            "Shares": [5.0],
            "Type": ["DIV"],
            "Comment": ["test"],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    assert len(result) == 1
    assert result["Net Dividend"].iloc[0] == pytest.approx(10.0)
    assert "Type" not in result.columns


def test_merge_rows_and_reorder_large_aggregation():
    """Arrange: five rows sharing the same Date and Ticker with various dividend and share amounts.
    Act: call `merge_rows_and_reorder`.
    Assert: rows merge correctly and aggregated values match expected sums.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"] * 5,
            "Ticker": ["AAPL"] * 5,
            "Net Dividend": [10.0, 20.0, 30.0, 15.5, 24.5],
            "Shares": [1.0, 2.0, 3.0, 1.5, 2.5],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    assert len(result) == 1
    assert result["Net Dividend"].iloc[0] == pytest.approx(100.0)
    assert result["Shares"].iloc[0] == pytest.approx(10.0)


def test_merge_rows_and_reorder_all_columns_together():
    """Arrange: two rows with all possible columns including Type, Comment, and both tax columns.
    Act: call `merge_rows_and_reorder`.
    Assert: all aggregation, rounding, dropping, and ordering operations execute correctly together.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01"],
            "Ticker": ["AAPL", "AAPL"],
            "Net Dividend": [10.123, 5.456],
            "Shares": [2.999, 3.001],
            "Tax Collected": [1.5, 1.5],
            "Tax Collected Raw": [0.5, 0.5],
            "Type": ["DIV", "DIV"],
            "Comment": ["a", "b"],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    assert len(result) == 1
    assert result["Net Dividend"].iloc[0] == pytest.approx(15.58)
    assert result["Shares"].iloc[0] == pytest.approx(6.0)
    assert result["Tax Collected"].iloc[0] == pytest.approx(1.5)
    assert result["Tax Collected Raw"].iloc[0] == pytest.approx(1.0)
    assert "Type" not in result.columns
    assert "Comment" not in result.columns
    assert result.columns[-1] == "Shares"


def test_merge_rows_and_reorder_preserves_column_order():
    """Arrange: DataFrame with multiple columns including Tax Collected and Shares.
    Act: call `merge_rows_and_reorder`.
    Assert: Shares is at the end and other columns maintain their relative order.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["AAPL"],
            "Net Dividend": [10.0],
            "Shares": [5.0],
            "Tax Collected": [1.5],
        }
    )
    agg = DataAggregator(df)
    result = agg.merge_rows_and_reorder()

    # Mutation: if pop/assignment doesn't actually move Shares
    cols = list(result.columns)
    assert cols[-1] == "Shares"
    assert cols[-2] != "Shares"


# ---------------------------------------------------------------------------
# Mutation killers — add_empty_column defaults
# ---------------------------------------------------------------------------


def test_add_empty_column_default_args_create_tax_collected_at_position_four():
    """Arrange: DataFrame with 5 non-tax columns.
    Act: call add_empty_column() with NO arguments (default col + default pos).
    Assert: column is named exactly 'Tax Collected' AND lives at index 4
    (kills col_name default-string mutations and position default 4 → 5).
    """
    df = pd.DataFrame(
        {
            "Date": [1],
            "Ticker": ["A"],
            "Net Dividend": [1.0],
            "Shares": [1.0],
            "Comment": ["x"],
        }
    )
    agg = DataAggregator(df)

    result = agg.add_empty_column()

    cols = list(result.columns)
    assert "Tax Collected" in cols
    assert cols.index("Tax Collected") == 4


def test_add_empty_column_inserts_pd_na_not_python_none():
    """Arrange: empty DataFrame with one row.
    Act: call add_empty_column.
    Assert: the new column contains pd.NA (na-detected), not the Python None
    sentinel (kills `pd.NA` → `None` mutation; both look 'null' but pd.NA
    preserves nullable extension dtypes whereas None coerces to object).
    """
    df = pd.DataFrame({"A": [1, 2]})
    agg = DataAggregator(df)

    result = agg.add_empty_column(col_name="X", position=0)

    # pd.isna treats both as NA, so the distinguishing fact is the *value type*.
    # Inserting pd.NA produces pd.NA in the column; inserting None produces None.
    assert all(v is pd.NA for v in result["X"])


# ---------------------------------------------------------------------------
# Mutation killers — move_negative_values boundary semantics
# ---------------------------------------------------------------------------


def test_move_negative_values_zero_net_dividend_is_kept_not_moved():
    """Arrange: a row whose Net Dividend is exactly 0.
    Act: move_negative_values.
    Assert: Net Dividend stays 0; Tax Collected is NOT populated from it
    (kills `< 0` → `<= 0` and `< 0` → `< 1` mutations which would erroneously
    treat zero/positive small values as 'negative').
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["A"],
            "Net Dividend": [0.0],
            "Shares": [1.0],
        }
    )
    agg = DataAggregator(df)

    result = agg.move_negative_values()

    assert result.loc[0, "Net Dividend"] == 0.0
    assert (
        pd.isna(result.loc[0, "Tax Collected"]) or result.loc[0, "Tax Collected"] != 0.0
    )


def test_move_negative_values_positive_below_one_is_kept():
    """Arrange: a row whose Net Dividend is +0.5 (positive but < 1).
    Act: move_negative_values.
    Assert: row is untouched (kills `< 0` → `< 1` which would treat 0.5 as
    negative and move it).
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["A"],
            "Net Dividend": [0.5],
            "Shares": [1.0],
        }
    )
    agg = DataAggregator(df)

    result = agg.move_negative_values()

    assert result.loc[0, "Net Dividend"] == pytest.approx(0.5)
    assert pd.isna(result.loc[0, "Tax Collected"])


def test_move_negative_values_negative_amount_is_moved_to_tax_collected():
    """Arrange: a row with Net Dividend = -3.
    Act: move_negative_values.
    Assert: Tax Collected = -3, Net Dividend = NaN (baseline behaviour).
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Ticker": ["A"],
            "Net Dividend": [-3.0],
            "Shares": [1.0],
        }
    )
    agg = DataAggregator(df)

    result = agg.move_negative_values()

    assert result.loc[0, "Tax Collected"] == pytest.approx(-3.0)
    assert pd.isna(result.loc[0, "Net Dividend"])


# ---------------------------------------------------------------------------
# reorder_columns
# ---------------------------------------------------------------------------


def _full_reorder_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Tax Amount PLN": ["1"],
            "Exchange Rate D-1": ["2"],
            "Date D-1": ["3"],
            "Tax Collected %": ["4"],
            "Tax Collected Amount": ["5"],
            "Net Dividend": ["6"],
            "Shares": ["7"],
            "Ticker": ["8"],
            "Date": ["9"],
        }
    )


@pytest.mark.unit
class TestReorderColumns:
    """Tests for DataAggregator.reorder_columns ordering and filtering."""

    def test_reorders_columns_to_canonical_order(self) -> None:
        agg = DataAggregator(_full_reorder_df())

        result = agg.reorder_columns()

        assert list(result.columns) == [
            "Date",
            "Ticker",
            "Shares",
            "Net Dividend",
            "Tax Collected Amount",
            "Tax Collected %",
            "Date D-1",
            "Exchange Rate D-1",
            "Tax Amount PLN",
        ]

    def test_drops_columns_not_in_desired_order(self) -> None:
        df = _full_reorder_df()
        df["Extra"] = ["x"]
        agg = DataAggregator(df)

        result = agg.reorder_columns()

        assert "Extra" not in result.columns

    def test_handles_subset_of_desired_columns(self) -> None:
        df = pd.DataFrame({"Ticker": ["AAPL"], "Date": ["2024-01-01"]})
        agg = DataAggregator(df)

        result = agg.reorder_columns()

        assert list(result.columns) == ["Date", "Ticker"]

    def test_places_date_first(self) -> None:
        agg = DataAggregator(_full_reorder_df())

        result = agg.reorder_columns()

        assert result.columns[0] == "Date"

    def test_places_tax_amount_pln_last(self) -> None:
        agg = DataAggregator(_full_reorder_df())

        result = agg.reorder_columns()

        assert result.columns[-1] == "Tax Amount PLN"

    def test_ticker_comes_before_shares(self) -> None:
        agg = DataAggregator(_full_reorder_df())

        result = agg.reorder_columns()

        cols = list(result.columns)
        assert cols.index("Ticker") < cols.index("Shares")

    def test_preserves_row_data(self) -> None:
        df = _full_reorder_df()
        agg = DataAggregator(df)

        result = agg.reorder_columns()

        assert result["Date"].iloc[0] == "9"
        assert result["Ticker"].iloc[0] == "8"

    def test_returns_empty_columns_when_no_canonical_column_present(self) -> None:
        df = pd.DataFrame({"Extra1": ["a"], "Extra2": ["b"]})
        agg = DataAggregator(df)

        result = agg.reorder_columns()

        assert list(result.columns) == []
