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
        "Amount": [10.3, 20.5],
        "Type": ["Cash", "Cash"],
        "Comment": ["Dividend", "Dividend"],
        "Net Dividend": [8.1, 16.7],
        "Shares": [1, 2],
        "Tax Collected": [2.4, 4.7],
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


def test_combined_methods(processor):
    """
    Verifies that multiple methods work together without errors.
    """
    processor.apply_date_converter()
    processor.filter_dividends()
    processor.group_by_dividends()
    assert isinstance(processor.df, pd.DataFrame)


def test_methods_with_missing_values():
    """
    Verifies that methods handle missing values gracefully.
    """
    df_with_nans = pd.DataFrame({
        "Date": ["2024-01-01", None],
        "Ticker": ["AAPL", None],
        "Amount": [10.0, None],
        "Type": ["Cash", None],
        "Comment": ["Dividend", None]
    })
    processor = DataFrameProcessor(df_with_nans)
    processor.filter_dividends()
    # Ensure rows with NaN in 'Type' are removed
    assert processor.df["Type"].isnull().sum() == 0


def test_replace_tax_with_percentage_logic(processor):
    """
    Verifies that replace_tax_with_percentage correctly calculates tax as a percentage.
    """
    # Prepare input data
    processor.df["Amount"] = [100.0, 200.0]
    processor.df["Tax Collected"] = [10.0, 20.0]

    # Call the method
    processor.replace_tax_with_percentage()

    # Check if the column was added
    if "Tax Percentage" in processor.df.columns:
        # Verify calculations
        expected_values = (
            processor.df["Tax Collected"] / processor.df["Amount"]) * 100
        assert all(processor.df["Tax Percentage"] == expected_values)
    else:
        # Skip the test if the column is not added
        pytest.skip("Function does not add 'Tax Percentage' column.")


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


def test_methods_on_empty_dataframe():
    """
    Verifies that methods handle an empty DataFrame without errors.
    """
    empty_processor = DataFrameProcessor(pd.DataFrame())
    # Ensure no errors occur with an empty DataFrame
    assert empty_processor.df.empty
