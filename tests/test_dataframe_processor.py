"""Tests for DataFrameProcessor module."""

import pandas as pd
import pytest

from data_processing.dataframe_processor import DataFrameProcessor


@pytest.fixture
def processor(sample_dataframe: pd.DataFrame) -> DataFrameProcessor:
    """
    Provides a DataFrameProcessor instance initialized with the sample DataFrame.

    Args:
        sample_dataframe: Sample DataFrame fixture from conftest.py.

    Returns:
        DataFrameProcessor instance.
    """
    return DataFrameProcessor(sample_dataframe)


@pytest.mark.unit
class TestColumnOperations:
    """Test suite for column manipulation operations."""

    def test_rename_columns(self, processor: DataFrameProcessor) -> None:
        """Tests that the rename_columns method correctly updates column names."""
        processor.rename_columns({"Date": "TransactionDate", "Amount": "Value"})
        assert "TransactionDate" in processor.df.columns
        assert "Value" in processor.df.columns

    def test_get_column_name(self, processor: DataFrameProcessor) -> None:
        """Tests that the get_column_name method returns the correct column name."""
        result = processor.get_column_name("Ticker", "Symbol")
        assert result in ["Ticker", "Symbol"]

    def test_add_empty_column(self, processor: DataFrameProcessor) -> None:
        """Tests that the add_empty_column method adds a new column with NaN values."""
        processor.add_empty_column("New Column")
        assert "New Column" in processor.df.columns
        assert processor.df["New Column"].isnull().all()


@pytest.mark.unit
class TestDataTransformation:
    """Test suite for data transformation operations."""

    def test_apply_colorize_ticker(self, processor: DataFrameProcessor) -> None:
        """Tests that the apply_colorize_ticker method retains the Ticker column."""
        processor.apply_colorize_ticker()
        assert "Ticker" in processor.df.columns

    def test_apply_extractor(self, processor: DataFrameProcessor) -> None:
        """Tests that the apply_extractor method returns a valid DataFrame."""
        processor.apply_extractor()
        assert isinstance(processor.df, pd.DataFrame)

    def test_move_negative_values(self, processor: DataFrameProcessor) -> None:
        """Tests that the move_negative_values method executes without errors."""
        processor.move_negative_values()
        assert isinstance(processor.df, pd.DataFrame)

    def test_move_negative_values_with_no_negatives(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that move_negative_values does not modify DataFrame without negatives."""
        original_df = processor.df.copy()
        processor.move_negative_values()
        pd.testing.assert_frame_equal(processor.df, original_df)

    def test_add_currency_to_dividends(self, processor: DataFrameProcessor) -> None:
        """Tests that add_currency_to_dividends executes without errors."""
        processor.add_currency_to_dividends()
        assert isinstance(processor.df, pd.DataFrame)


@pytest.mark.unit
class TestFilteringOperations:
    """Test suite for data filtering operations."""

    def test_filter_dividends(self, processor: DataFrameProcessor) -> None:
        """Tests that filter_dividends filters rows correctly."""
        original_len = len(processor.df)
        processor.filter_dividends()
        assert len(processor.df) <= original_len

    def test_filter_dividends_with_missing_values(self) -> None:
        """Tests that filter_dividends handles missing values correctly."""
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


@pytest.mark.unit
class TestAggregationOperations:
    """Test suite for data aggregation operations."""

    def test_group_by_dividends(self, processor: DataFrameProcessor) -> None:
        """Tests that group_by_dividends returns a grouped DataFrame."""
        processor.group_by_dividends()
        assert isinstance(processor.df, pd.DataFrame)

    def test_calculate_dividend(self, processor: DataFrameProcessor) -> None:
        """Tests that calculate_dividend executes without errors."""
        processor.calculate_dividend(["dummy_path"], language="en")
        assert isinstance(processor.df, pd.DataFrame)


@pytest.mark.unit
class TestTaxProcessing:
    """Test suite for tax-related processing operations."""

    @pytest.mark.parametrize(
        "comments,expected",
        [
            (["15%", "20%", "No tax info"], [0.15, 0.20, 0.0]),
            (["5%", "0%", "30%"], [0.05, 0.0, 0.30]),
            (["No info", "25%", ""], [0.0, 0.25, 0.0]),
        ],
    )
    def test_replace_tax_with_percentage_parametrized(
        self, comments: list[str], expected: list[float]
    ) -> None:
        """Tests tax percentage extraction from comments with various formats."""
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


@pytest.mark.unit
class TestDataFrameAccess:
    """Test suite for DataFrame access methods."""

    def test_get_processed_df(self, processor: DataFrameProcessor) -> None:
        """Tests that get_processed_df returns a valid DataFrame."""
        result = processor.get_processed_df()
        assert isinstance(result, pd.DataFrame)


@pytest.mark.edge_case
class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_methods_on_empty_dataframe(self) -> None:
        """Tests that all methods handle an empty DataFrame without raising errors."""
        empty_processor = DataFrameProcessor(pd.DataFrame())

        # Ensure no errors occur when renaming columns in an empty DataFrame
        try:
            empty_processor.rename_columns({"Date": "TransactionDate"})
        except KeyError:
            pass  # Expected behavior for an empty DataFrame

        # Ensure the DataFrame remains empty
        assert empty_processor.df.empty


@pytest.mark.performance
class TestPerformance:
    """Test suite for performance with large datasets."""

    @pytest.mark.parametrize(
        "periods,tickers,amounts,types,comments,expected_min_length",
        [
            # Small dataset
            (
                100,
                ["AAPL"] * 100,
                [10.0] * 100,
                ["Cash"] * 100,
                ["Dividend"] * 100,
                1,
            ),
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
        self,
        periods: int,
        tickers: list[str],
        amounts: list[float],
        types: list[str],
        comments: list[str],
        expected_min_length: int,
    ) -> None:
        """Tests that methods handle large DataFrames efficiently."""
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
