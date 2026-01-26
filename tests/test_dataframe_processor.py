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

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        self.rename_mapping = {"Date": "TransactionDate", "Amount": "Value"}
        self.column_alternatives = ("Ticker", "Symbol")
        self.new_column_name = "New Column"

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        pass

    def test_rename_when_valid_mapping_then_columns_updated(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that columns are renamed correctly with valid mapping."""
        # Arrange - processor from fixture

        # Act
        processor.rename_columns(self.rename_mapping)

        # Assert
        assert "TransactionDate" in processor.df.columns
        assert "Value" in processor.df.columns

    def test_get_column_name_when_column_exists_then_returns_correct_name(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that correct column name is returned when it exists."""
        # Arrange - processor from fixture

        # Act
        result = processor.get_column_name(*self.column_alternatives)

        # Assert
        assert result in self.column_alternatives

    def test_add_empty_column_when_called_then_column_with_nans_added(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that new column with NaN values is added."""
        # Arrange - processor from fixture

        # Act
        processor.add_empty_column(self.new_column_name)

        # Assert
        assert self.new_column_name in processor.df.columns
        assert processor.df[self.new_column_name].isnull().all()


@pytest.mark.unit
class TestDataTransformation:
    """Test suite for data transformation operations."""

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        self.required_ticker_column = "Ticker"

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        pass

    def test_colorize_when_applied_then_ticker_column_retained(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that Ticker column is retained after colorization."""
        # Arrange - processor from fixture

        # Act
        processor.apply_colorize_ticker()

        # Assert
        assert self.required_ticker_column in processor.df.columns

    def test_extract_when_applied_then_returns_valid_dataframe(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that extractor returns a valid DataFrame."""
        # Arrange - processor from fixture

        # Act
        processor.apply_extractor()

        # Assert
        assert isinstance(processor.df, pd.DataFrame)

    def test_move_negative_when_executed_then_returns_dataframe(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that move_negative_values executes successfully."""
        # Arrange - processor from fixture

        # Act
        processor.move_negative_values()

        # Assert
        assert isinstance(processor.df, pd.DataFrame)

    def test_move_negative_when_no_negatives_then_dataframe_unchanged(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that DataFrame remains unchanged when no negative values exist."""
        # Arrange
        original_df = processor.df.copy()

        # Act
        processor.move_negative_values()

        # Assert
        pd.testing.assert_frame_equal(processor.df, original_df)

    def test_add_currency_when_called_then_executes_without_error(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that currency addition executes without errors."""
        # Arrange - processor from fixture

        # Act
        processor.add_currency_to_dividends()

        # Assert
        assert isinstance(processor.df, pd.DataFrame)


@pytest.mark.unit
class TestFilteringOperations:
    """Test suite for data filtering operations."""

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        self.valid_dividend_types = ["Dividend", "Dywidenda"]

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        pass

    def test_filter_when_called_then_row_count_not_increased(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that filtering does not increase row count."""
        # Arrange
        original_len = len(processor.df)

        # Act
        processor.filter_dividends()

        # Assert
        assert len(processor.df) <= original_len

    def test_filter_when_missing_values_then_removes_invalid_rows(self) -> None:
        """Tests that filtering removes rows with missing Type values."""
        # Arrange
        df_with_nans = pd.DataFrame(
            {
                "Type": ["Dividend", None, "Dywidenda", "Invalid", None],
                "Amount": [10.0, 20.0, 30.0, 40.0, 50.0],
            }
        )
        processor = DataFrameProcessor(df_with_nans)

        # Act
        processor.filter_dividends()

        # Assert
        assert processor.df["Type"].isnull().sum() == 0
        assert all(processor.df["Type"].isin(self.valid_dividend_types))


@pytest.mark.unit
class TestAggregationOperations:
    """Test suite for data aggregation operations."""

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        self.dummy_paths = ["dummy_path"]
        self.language = "en"

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        pass

    def test_group_when_called_then_returns_grouped_dataframe(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that grouping returns a valid grouped DataFrame."""
        # Arrange - processor from fixture

        # Act
        processor.group_by_dividends()

        # Assert
        assert isinstance(processor.df, pd.DataFrame)

    def test_calculate_when_called_then_executes_without_error(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that dividend calculation executes successfully."""
        # Arrange - processor from fixture

        # Act
        processor.calculate_dividend(self.dummy_paths, language=self.language)

        # Assert
        assert isinstance(processor.df, pd.DataFrame)


@pytest.mark.unit
class TestTaxProcessing:
    """Test suite for tax-related processing operations."""

    @classmethod
    def setup_class(cls) -> None:
        """Setup class-level fixtures before all tests."""
        cls.base_amount = 100.0

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup class-level fixtures after all tests."""
        pass

    @pytest.mark.parametrize(
        "comments,expected",
        [
            (["15%", "20%", "No tax info"], [0.15, 0.20, 0.0]),
            (["5%", "0%", "30%"], [0.05, 0.0, 0.30]),
            (["No info", "25%", ""], [0.0, 0.25, 0.0]),
        ],
    )
    def test_replace_when_various_formats_then_extracts_percentage_correctly(
        self, comments: list[str], expected: list[float]
    ) -> None:
        """Tests tax percentage extraction from various comment formats."""
        # Arrange
        df = pd.DataFrame(
            {
                "Comment": comments,
                "Tax Collected": [0.0] * len(comments),
                "Net Dividend": [self.base_amount] * len(comments),
                "Ticker": ["TEST.US"] * len(comments),
            }
        )
        processor = DataFrameProcessor(df)

        # Act
        processor.replace_tax_with_percentage()

        # Assert
        assert list(processor.df["Tax Collected"]) == expected


@pytest.mark.unit
class TestDataFrameAccess:
    """Test suite for DataFrame access methods."""

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        pass

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        pass

    def test_get_processed_when_called_then_returns_valid_dataframe(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that get_processed_df returns a valid DataFrame."""
        # Arrange - processor from fixture

        # Act
        result = processor.get_processed_df()

        # Assert
        assert isinstance(result, pd.DataFrame)


@pytest.mark.edge_case
class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        self.rename_mapping = {"Date": "TransactionDate"}

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        pass

    def test_process_when_empty_dataframe_then_handles_gracefully(self) -> None:
        """Tests that empty DataFrame is handled without errors."""
        # Arrange
        empty_processor = DataFrameProcessor(pd.DataFrame())

        # Act & Assert - should handle gracefully
        try:
            empty_processor.rename_columns(self.rename_mapping)
        except KeyError:
            pass  # Expected behavior for empty DataFrame

        assert empty_processor.df.empty


@pytest.mark.performance
class TestPerformance:
    """Test suite for performance with large datasets."""

    @classmethod
    def setup_class(cls) -> None:
        """Setup class-level fixtures before all tests."""
        cls.date_start = "2024-01-01"
        cls.frequency = "D"

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup class-level fixtures after all tests."""
        pass

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
    def test_group_when_large_dataset_then_handles_efficiently(
        self,
        periods: int,
        tickers: list[str],
        amounts: list[float],
        types: list[str],
        comments: list[str],
        expected_min_length: int,
    ) -> None:
        """Tests that large DataFrames are processed efficiently."""
        # Arrange
        tickers = tickers[:periods]
        amounts = amounts[:periods]
        types = types[:periods]
        comments = comments[:periods]

        large_df = pd.DataFrame(
            {
                "Date": pd.date_range(
                    start=self.date_start, periods=periods, freq=self.frequency
                ),
                "Ticker": tickers,
                "Amount": amounts,
                "Type": types,
                "Comment": comments,
            }
        )
        processor = DataFrameProcessor(large_df)

        # Act
        processor.group_by_dividends()

        # Assert
        assert len(processor.df) >= expected_min_length
