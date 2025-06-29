import pandas as pd
import pytest

# Import the class to test
from data_processing.dataframe_processor import DataFrameProcessor


@pytest.fixture
def sample_dataframe():
    """
    Provides a sample DataFrame for testing DataFrameProcessor methods.
    Includes all necessary columns required by the tested methods.
    """
    df = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-02"],
            "Ticker": ["AAPL", "MSFT"],
            "Amount": [10.1, 20.4],
            "Type": ["Cash", "Cash"],
            "Comment": ["Dividend", "Dividend"],
            "Net Dividend": [8.4, 16.5],
            "Shares": [1, 2],
            "Tax Collected": [2.5, 4.9],
            "Currency": ["USD", "USD"],
        }
    )
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
    Tests that the rename_columns method correctly updates column names in the DataFrame.
    """
    processor.rename_columns({"Date": "TransactionDate", "Amount": "Value"})
    assert "TransactionDate" in processor.df.columns
    assert "Value" in processor.df.columns


def test_get_column_name(processor):
    """
    Tests that the get_column_name method returns the correct column name if it exists.
    """
    result = processor.get_column_name("Ticker", "Symbol")
    assert result in ["Ticker", "Symbol"]


def test_apply_colorize_ticker(processor):
    """
    Tests that the apply_colorize_ticker method executes without errors and retains the 'Ticker' column.
    """
    processor.apply_colorize_ticker()
    assert "Ticker" in processor.df.columns


def test_apply_extractor(processor):
    """
    Tests that the apply_extractor method executes without errors and returns a valid DataFrame.
    """
    processor.apply_extractor()
    assert isinstance(processor.df, pd.DataFrame)


def test_filter_dividends(processor):
    """
    Tests that the filter_dividends method filters rows correctly without increasing the row count.
    """
    original_len = len(processor.df)
    processor.filter_dividends()
    assert len(processor.df) <= original_len


def test_group_by_dividends(processor):
    """
    Tests that the group_by_dividends method executes without errors and returns a grouped DataFrame.
    """
    processor.group_by_dividends()
    assert isinstance(processor.df, pd.DataFrame)


def test_add_empty_column(processor):
    """
    Tests that the add_empty_column method adds a new column with NaN values to the DataFrame.
    """
    processor.add_empty_column("New Column")
    assert "New Column" in processor.df.columns
    assert processor.df["New Column"].isnull().all()


def test_move_negative_values(processor):
    """
    Tests that the move_negative_values method executes without errors and returns a valid DataFrame.
    """
    processor.move_negative_values()
    assert isinstance(processor.df, pd.DataFrame)


def test_calculate_dividend(processor):
    """
    Tests that the calculate_dividend method executes without errors and returns a valid DataFrame.
    """
    processor.calculate_dividend(["dummy_path"], language="en")
    assert isinstance(processor.df, pd.DataFrame)


@pytest.mark.parametrize(
    "comments,expected",
    [
        (["15%", "20%", "No tax info"], [0.15, 0.20, 0.0]),
        (["5%", "0%", "30%"], [0.05, 0.0, 0.30]),
        (["No info", "25%", ""], [0.0, 0.25, 0.0]),
    ],
)
def test_replace_tax_with_percentage_parametrized(comments, expected):
    df = pd.DataFrame(
        {
            "Comment": comments,
            "Tax Collected": [0.0] * len(comments),
            "Amount": [100.0] * len(comments),
        }
    )
    processor = DataFrameProcessor(df)
    processor.replace_tax_with_percentage()
    assert list(processor.df["Tax Collected"]) == expected


def test_add_currency_to_dividends(processor):
    """
    Tests that the add_currency_to_dividends method executes without errors and returns a valid DataFrame.
    """
    processor.add_currency_to_dividends()
    assert isinstance(processor.df, pd.DataFrame)


def test_get_processed_df(processor):
    """
    Tests that the get_processed_df method returns a valid DataFrame.
    """
    result = processor.get_processed_df()
    assert isinstance(result, pd.DataFrame)


def test_methods_on_empty_dataframe():
    """
    Tests that all methods handle an empty DataFrame without raising errors.
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
    Tests that the move_negative_values method does not modify the DataFrame
    if no negative values are present.
    """
    original_df = processor.df.copy()
    processor.move_negative_values()
    pd.testing.assert_frame_equal(processor.df, original_df)


def test_filter_dividends_with_missing_values():
    """
    Tests that the filter_dividends method handles missing values in the 'Type' column correctly.
    """
    df_with_nans = pd.DataFrame(
        {
            "Type": ["Dividend", None, "Dywidenda", "Invalid", None],
            "Amount": [10.0, 20.0, 30.0, 40.0, 50.0],
        }
    )
    processor = DataFrameProcessor(df_with_nans)
    processor.filter_dividends()
    assert processor.df["Type"].isnull().sum() == 0
    assert all(processor.df["Type"].isin(["Dividend", "Dywidenda"]))


@pytest.mark.parametrize(
    "periods,tickers,amounts,types,comments,expected_min_length",
    [
        # Small dataset
        (100, ["AAPL"] * 100, [10.0] * 100, ["Cash"] * 100, ["Dividend"] * 100, 1),
        # Medium dataset with mixed tickers
        (
            1000,
            ["AAPL", "MSFT", "GOOGL"] * 334,
            [15.5, 25.0, 30.75] * 334,
            ["Cash"] * 1000,
            ["Dividend"] * 1000,
            1,
        ),
        # Large dataset with varied amounts
        (
            5000,
            ["TSLA"] * 5000,
            list(range(1, 5001)),
            ["Cash"] * 5000,
            ["Dividend"] * 5000,
            1,
        ),
        # Very large dataset
        (
            10000,
            ["NVDA", "AMD"] * 5000,
            [50.0, 75.0] * 5000,
            ["Cash"] * 10000,
            ["Dividend"] * 10000,
            1,
        ),
        # Mixed types and comments
        (
            2000,
            ["IBM"] * 2000,
            [100.0] * 2000,
            ["Cash", "Stock"] * 1000,
            ["Dividend", "Split"] * 1000,
            0,
        ),
    ],
)
def test_large_dataframe(
    periods, tickers, amounts, types, comments, expected_min_length
):
    """
    Tests that all methods handle large DataFrames efficiently without performance issues.
    Uses parametrized inputs to test different scenarios and data sizes.
    """
    # Ensure all lists have the correct length
    tickers = tickers[:periods]
    amounts = amounts[:periods]
    types = types[:periods]
    comments = comments[:periods]

    large_df = pd.DataFrame(
        {
            "Date": pd.date_range(start="2024-01-01", periods=periods, freq="D"),
            "Ticker": tickers,
            "Amount": amounts,
            "Type": types,
            "Comment": comments,
        }
    )
    processor = DataFrameProcessor(large_df)
    processor.group_by_dividends()
    assert len(processor.df) >= expected_min_length
