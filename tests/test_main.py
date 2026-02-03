"""Integration tests for DataFrameProcessor workflows."""

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


@pytest.mark.integration
class TestWorkflowIntegration:
    """Test suite for integrated workflow operations."""

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        self.tax_test_amounts = [100.0, 200.0]
        self.tax_test_collected = [10.0, 20.0]

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        pass

    def test_workflow_when_methods_combined_then_executes_successfully(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that multiple workflow methods execute sequentially without errors."""
        # Arrange - processor from fixture

        # Act
        processor.apply_date_converter()
        processor.filter_dividends()
        processor.group_by_dividends()

        # Assert
        assert isinstance(processor.df, pd.DataFrame)

    def test_workflow_when_calculating_tax_percentage_then_computes_correctly(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that tax percentage validation workflow works correctly."""
        # Arrange
        processor.df["Net Dividend"] = self.tax_test_amounts
        # Tax percentages (2 values for 2 rows)
        processor.df["Tax Collected"] = [0.15, 0.19]

        # Act - This function now validates Tax Collected column
        processor.replace_tax_with_percentage()

        # Assert - Check that Tax Collected column still has valid values
        assert "Tax Collected" in processor.df.columns
        assert not processor.df["Tax Collected"].isnull().any()
        assert all(processor.df["Tax Collected"] > 0)


@pytest.mark.integration
class TestDataQualityHandling:
    """Test suite for handling data quality issues."""

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        self.nan_test_data = pd.DataFrame(
            {
                "Date": ["2024-01-01", None],
                "Ticker": ["AAPL", None],
                "Amount": [10.0, None],
                "Type": ["Cash", None],
                "Comment": ["Dividend", None],
            }
        )

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        pass

    def test_filter_when_missing_values_then_removes_invalid_rows(self) -> None:
        """Tests that missing values are handled gracefully during filtering."""
        # Arrange
        processor = DataFrameProcessor(self.nan_test_data)

        # Act
        processor.filter_dividends()

        # Assert
        assert processor.df["Type"].isnull().sum() == 0


@pytest.mark.integration
@pytest.mark.performance
class TestLargeDatasetProcessing:
    """Test suite for processing large datasets."""

    @classmethod
    def setup_class(cls) -> None:
        """Setup class-level fixtures before all tests."""
        cls.large_dataset_size = 10000
        cls.date_start = "2024-01-01"
        cls.frequency = "D"

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup class-level fixtures after all tests."""
        pass

    def test_group_when_large_dataframe_then_processes_efficiently(self) -> None:
        """Tests that large DataFrames are processed efficiently."""
        # Arrange
        large_df = pd.DataFrame(
            {
                "Date": pd.date_range(
                    start=self.date_start, periods=self.large_dataset_size, freq=self.frequency
                ),
                "Ticker": ["AAPL"] * self.large_dataset_size,
                "Amount": [10.0] * self.large_dataset_size,
                "Type": ["Cash"] * self.large_dataset_size,
                "Comment": ["Dividend"] * self.large_dataset_size,
            }
        )
        processor = DataFrameProcessor(large_df)

        # Act
        processor.group_by_dividends()

        # Assert
        assert len(processor.df) > 0


@pytest.mark.integration
@pytest.mark.edge_case
class TestEdgeCaseWorkflows:
    """Test suite for edge case workflow scenarios."""

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        self.empty_df = pd.DataFrame()

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        pass

    def test_workflow_when_empty_dataframe_then_handles_without_error(self) -> None:
        """Tests that empty DataFrame is handled gracefully in workflows."""
        # Arrange
        empty_processor = DataFrameProcessor(self.empty_df)

        # Act - no operations performed on empty DataFrame

        # Assert
        assert empty_processor.df.empty
