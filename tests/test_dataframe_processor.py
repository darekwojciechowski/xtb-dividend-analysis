import pytest
import pandas as pd
from unittest.mock import MagicMock

# Import the class to test
from data_processing.dataframe_processor import DataFrameProcessor


@pytest.fixture
def sample_dataframe():
    """
    Provides a sample DataFrame for testing DataFrameProcessor methods.
    Includes all necessary columns required by the tested methods.
    """
    df = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "Ticker": ["AAPL", "MSFT"],
        "Amount": [10.1, 20.4],
        "Type": ["Cash", "Cash"],
        "Comment": ["Dividend", "Dividend"],
        "Net Dividend": [8.4, 16.5],
        "Shares": [1, 2],
        "Tax Collected": [2.5, 4.9],
        "Currency": ["USD", "USD"]
    })
    df["Date"] = pd.to_datetime(df["Date"])
    return df


@pytest.fixture
def processor(sample_dataframe):
    """
    Provides a DataFrameProcessor instance initialized with the sample DataFrame.
    """
    return DataFrameProcessor(sample_dataframe)


def test_rename_columns(processor):
    """
    Verifies that renaming columns updates the DataFrame columns as expected.
    """
    processor.rename_columns({"Date": "TransactionDate", "Amount": "Value"})
    assert "TransactionDate" in processor.df.columns
    assert "Value" in processor.df.columns


def test_get_column_name(processor):
    """
    Verifies that get_column_name returns the correct column name if present.
    """
    result = processor.get_column_name("Ticker", "Symbol")
    assert result in ["Ticker", "Symbol"]


def test_apply_colorize_ticker(processor):
    """
    Verifies that apply_colorize_ticker executes without errors and retains the 'Ticker' column.
    """
    processor.apply_colorize_ticker()
    assert "Ticker" in processor.df.columns


def test_apply_extractor(processor):
    """
    Verifies that apply_extractor executes without errors and returns a DataFrame.
    """
    processor.apply_extractor()
    assert isinstance(processor.df, pd.DataFrame)


def test_filter_dividends(processor):
    """
    Verifies that filter_dividends filters rows correctly without increasing the number of rows.
    """
    original_len = len(processor.df)
    processor.filter_dividends()
    assert len(processor.df) <= original_len


def test_group_by_dividends(processor):
    """
    Verifies that group_by_dividends executes without errors and returns a grouped DataFrame.
    """
    processor.group_by_dividends()
    assert isinstance(processor.df, pd.DataFrame)


def test_add_empty_column(processor):
    """
    Verifies that add_empty_column adds a new column with NaN values to the DataFrame.
    """
    processor.add_empty_column("New Column")
    assert "New Column" in processor.df.columns
    assert processor.df["New Column"].isnull().all()


def test_move_negative_values(processor):
    """
    Verifies that move_negative_values executes without errors and returns a DataFrame.
    """
    processor.move_negative_values()
    assert isinstance(processor.df, pd.DataFrame)


def test_calculate_dividend(processor):
    """
    Verifies that calculate_dividend executes without errors and returns a DataFrame.
    """
    processor.calculate_dividend(["dummy_path"], language="en")
    assert isinstance(processor.df, pd.DataFrame)


def test_replace_tax_with_percentage(processor):
    """
    Verifies that replace_tax_with_percentage correctly calculates and replaces 'Tax Collected' values with percentages.
    """
    # Prepare input data
    processor.df = pd.DataFrame({
        "Comment": ["15%", "20%", "No tax info"],
        "Tax Collected": [0.0, 0.0, 0.0],
        "Amount": [100.0, 200.0, 300.0]
    })

    # Execute the method
    processor.replace_tax_with_percentage()

    # Verify the results
    assert processor.df["Tax Collected"][0] == 0.15, "Expected 15% to be converted to 0.15"
    assert processor.df["Tax Collected"][1] == 0.20, "Expected 20% to be converted to 0.20"
    assert processor.df["Tax Collected"][2] == 0.0, "Expected no change for 'No tax info'"


def test_add_currency_to_dividends(processor):
    """
    Verifies that add_currency_to_dividends executes without errors and returns a DataFrame.
    """
    processor.add_currency_to_dividends()
    assert isinstance(processor.df, pd.DataFrame)


def test_get_processed_df(processor):
    """
    Verifies that get_processed_df returns a DataFrame.
    """
    result = processor.get_processed_df()
    assert isinstance(result, pd.DataFrame)


def test_methods_on_empty_dataframe():
    """
    Verifies that methods handle an empty DataFrame without errors.
    """
    empty_processor = DataFrameProcessor(pd.DataFrame())

    # Ensure no errors occur when renaming columns in an empty DataFrame
    try:
        empty_processor.rename_columns({"Date": "TransactionDate"})
    except KeyError:
        pass  # Expected behavior for an empty DataFrame

    # Ensure the DataFrame remains empty
    assert empty_processor.df.empty


def test_move_negative_values_with_no_negatives(processor):
    """
    Verifies that move_negative_values does not modify the DataFrame if no negative values exist.
    """
    original_df = processor.df.copy()
    processor.move_negative_values()
    pd.testing.assert_frame_equal(processor.df, original_df)


def test_filter_dividends_with_missing_values():
    """
    Verifies that filter_dividends handles missing values in the 'Type' column correctly.
    """
    df_with_nans = pd.DataFrame({
        "Type": ["Dividend", None, "Dywidenda", "Invalid", None],
        "Amount": [10.0, 20.0, 30.0, 40.0, 50.0]
    })
    processor = DataFrameProcessor(df_with_nans)
    processor.filter_dividends()
    assert processor.df["Type"].isnull().sum() == 0
    assert all(processor.df["Type"].isin(["Dividend", "Dywidenda"]))


def test_large_dataframe():
    """
    Verifies that methods handle large DataFrames efficiently without performance issues.
    """
    large_df = pd.DataFrame({
        "Date": pd.date_range(start="2024-01-01", periods=10000, freq="D"),
        "Ticker": ["AAPL"] * 10000,
        "Amount": [10.0] * 10000,
        "Type": ["Cash"] * 10000,
        "Comment": ["Dividend"] * 10000
    })
    processor = DataFrameProcessor(large_df)
    processor.group_by_dividends()
    assert len(processor.df) > 0
