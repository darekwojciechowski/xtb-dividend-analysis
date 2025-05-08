import pytest
import pandas as pd
from unittest.mock import MagicMock

# Import the class to test
from data_processing.dataframe_processor import DataFrameProcessor


@pytest.fixture
def sample_dataframe():
    """
    Fixture providing a simple DataFrame for testing DataFrameProcessor methods.
    Includes all columns required by tested methods.
    """
    df = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "Ticker": ["AAPL", "MSFT"],
        "Amount": [10.0, 20.0],
        "Type": ["Cash", "Cash"],
        "Comment": ["Dividend", "Dividend"],
        "Net Dividend": [8.0, 16.0],
        "Shares": [1, 2],
        "Tax Collected": [2.0, 4.0],
        "Currency": ["USD", "USD"]
    })
    df["Date"] = pd.to_datetime(df["Date"])
    return df


@pytest.fixture
def processor(sample_dataframe):
    """
    Fixture providing a DataFrameProcessor instance initialized with sample data.
    """
    return DataFrameProcessor(sample_dataframe)


def test_rename_columns(processor):
    """
    Test that renaming columns updates DataFrame columns as expected.
    """
    processor.rename_columns({"Date": "TransactionDate", "Amount": "Value"})
    assert "TransactionDate" in processor.df.columns
    assert "Value" in processor.df.columns


def test_get_column_name(processor):
    """
    Test that get_column_name returns the correct column name if present.
    """
    result = processor.get_column_name("Ticker", "Symbol")
    assert result in ["Ticker", "Symbol"]


def test_apply_colorize_ticker(processor):
    """
    Test that apply_colorize_ticker executes without error and keeps 'Ticker' column.
    """
    processor.apply_colorize_ticker()
    assert "Ticker" in processor.df.columns


def test_apply_extractor(processor):
    """
    Test that apply_extractor executes without error and returns a DataFrame.
    """
    processor.apply_extractor()
    assert isinstance(processor.df, pd.DataFrame)


def test_apply_date_converter(processor):
    """
    Test that apply_date_converter converts the 'Date' column to datetime type.
    If conversion fails, show the actual dtype for easier debugging.
    """
    processor.apply_date_converter()
    dtype = processor.df["Date"].dtype
    assert pd.api.types.is_datetime64_any_dtype(
        dtype), f"'Date' column dtype is {dtype}, expected datetime64"


def test_filter_dividends(processor):
    """
    Test that filter_dividends does not increase the number of rows.
    """
    original_len = len(processor.df)
    processor.filter_dividends()
    assert len(processor.df) <= original_len


def test_group_by_dividends(processor):
    """
    Test that group_by_dividends executes without error and returns a DataFrame.
    """
    processor.group_by_dividends()
    assert isinstance(processor.df, pd.DataFrame)


def test_add_empty_column(processor):
    """
    Test that add_empty_column adds a new column with NaN values.
    """
    processor.add_empty_column()
    # Check if any column contains only NaN values (newly added column)
    assert any(processor.df.isnull().all())


def test_move_negative_values(processor):
    """
    Test that move_negative_values executes without error and returns a DataFrame.
    """
    processor.move_negative_values()
    assert isinstance(processor.df, pd.DataFrame)


def test_calculate_dividend(processor):
    """
    Test that calculate_dividend executes without error and returns a DataFrame.
    """
    processor.calculate_dividend(["dummy_path"], language="en")
    assert isinstance(processor.df, pd.DataFrame)


def test_replace_tax_with_percentage(processor):
    """
    Test that replace_tax_with_percentage executes without error and returns a DataFrame.
    """
    processor.replace_tax_with_percentage()
    assert isinstance(processor.df, pd.DataFrame)


def test_add_currency_to_dividends(processor):
    """
    Test that add_currency_to_dividends executes without error and returns a DataFrame.
    """
    processor.add_currency_to_dividends()
    assert isinstance(processor.df, pd.DataFrame)


def test_get_processed_df(processor):
    """
    Test that get_processed_df returns a DataFrame.
    """
    result = processor.get_processed_df()
    assert isinstance(result, pd.DataFrame)


def test_rename_columns_invalid_column(processor):
    """
    Test that renaming a non-existent column raises a KeyError.
    """
    with pytest.raises(KeyError):
        processor.rename_columns({"NonExistentColumn": "NewName"})


def test_methods_on_empty_dataframe():
    """
    Test that methods handle an empty DataFrame without errors.
    """
    empty_processor = DataFrameProcessor(pd.DataFrame())
    empty_processor.rename_columns(
        {"Date": "TransactionDate"})  # Should not raise
    assert empty_processor.df.empty


def test_move_negative_values_with_no_negatives(processor):
    """
    Test that move_negative_values does not modify the DataFrame if no negative values exist.
    """
    original_df = processor.df.copy()
    processor.move_negative_values()
    pd.testing.assert_frame_equal(processor.df, original_df)


def test_calculate_dividend_correctness(processor):
    """
    Test that calculate_dividend computes the correct values.
    """
    processor.calculate_dividend(["dummy_path"], language="en")
    assert "Net Dividend" in processor.df.columns
    assert all(processor.df["Net Dividend"] ==
               processor.df["Amount"] - processor.df["Tax Collected"])


def test_combined_methods(processor):
    """
    Test that multiple methods work together without errors.
    """
    processor.apply_date_converter()
    processor.filter_dividends()
    processor.group_by_dividends()
    assert isinstance(processor.df, pd.DataFrame)


def test_methods_with_missing_values():
    """
    Test that methods handle missing values gracefully.
    """
    df_with_nans = pd.DataFrame({
        "Date": ["2024-01-01", None],
        "Ticker": ["AAPL", None],
        "Amount": [10.0, None],
        "Type": ["Cash", None],
        "Comment": ["Dividend", None]
    })
    processor = DataFrameProcessor(df_with_nans)
    processor.filter_dividends()  # Should not raise
    assert processor.df.isnull().any().any()  # Ensure NaNs are still present


def test_large_dataframe():
    """
    Test that methods handle large DataFrames efficiently.
    """
    large_df = pd.DataFrame({
        "Date": pd.date_range(start="2024-01-01", periods=100000, freq="D"),
        "Ticker": ["AAPL"] * 100000,
        "Amount": [10.0] * 100000,
        "Type": ["Cash"] * 100000,
        "Comment": ["Dividend"] * 100000
    })
    processor = DataFrameProcessor(large_df)
    processor.group_by_dividends()  # Should not raise
    assert len(processor.df) > 0


def test_replace_tax_with_percentage_logic(processor):
    """
    Test that replace_tax_with_percentage correctly calculates tax as a percentage.
    """
    processor.replace_tax_with_percentage()
    assert "Tax Percentage" in processor.df.columns
    assert all(processor.df["Tax Percentage"] == (
        processor.df["Tax Collected"] / processor.df["Amount"]) * 100)
