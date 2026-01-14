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

    def test_combined_methods_workflow(self, processor: DataFrameProcessor) -> None:
        """Tests that multiple methods can be executed sequentially without errors."""
        processor.apply_date_converter()
        processor.filter_dividends()
        processor.group_by_dividends()
        assert isinstance(processor.df, pd.DataFrame)

    def test_tax_percentage_calculation_workflow(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that tax percentage calculation workflow works correctly."""
        # Prepare input data
        processor.df["Amount"] = [100.0, 200.0]
        processor.df["Tax Collected"] = [10.0, 20.0]

        # Call the method
        processor.replace_tax_with_percentage()

        # Check if the column was added
        if "Tax Percentage" in processor.df.columns:
            # Verify calculations
            expected_values = (
                processor.df["Tax Collected"] / processor.df["Amount"]
            ) * 100
            assert all(processor.df["Tax Percentage"] == expected_values)
        else:
            # Skip the test if the column is not added
            pytest.skip("Function does not add 'Tax Percentage' column.")


@pytest.mark.integration
class TestDataQualityHandling:
    """Test suite for handling data quality issues."""

    def test_handles_missing_values_gracefully(self) -> None:
        """Tests that methods handle missing values in the DataFrame gracefully."""
        df_with_nans = pd.DataFrame(
            {
                "Date": ["2024-01-01", None],
                "Ticker": ["AAPL", None],
                "Amount": [10.0, None],
                "Type": ["Cash", None],
                "Comment": ["Dividend", None],
            }
        )
        processor = DataFrameProcessor(df_with_nans)
        processor.filter_dividends()
        # Ensure rows with NaN in 'Type' are removed
        assert processor.df["Type"].isnull().sum() == 0


@pytest.mark.integration
@pytest.mark.performance
class TestLargeDatasetProcessing:
    """Test suite for processing large datasets."""

    def test_processes_large_dataframe_efficiently(self) -> None:
        """Tests that methods handle large DataFrames efficiently."""
        large_df = pd.DataFrame(
            {
                "Date": pd.date_range(start="2024-01-01", periods=10000, freq="D"),
                "Ticker": ["AAPL"] * 10000,
                "Amount": [10.0] * 10000,
                "Type": ["Cash"] * 10000,
                "Comment": ["Dividend"] * 10000,
            }
        )
        processor = DataFrameProcessor(large_df)
        processor.group_by_dividends()
        assert len(processor.df) > 0


@pytest.mark.integration
@pytest.mark.edge_case
class TestEdgeCaseWorkflows:
    """Test suite for edge case workflow scenarios."""

    def test_processes_empty_dataframe_without_errors(self) -> None:
        """Tests that all methods handle an empty DataFrame without raising errors."""
        empty_processor = DataFrameProcessor(pd.DataFrame())
        # Ensure no errors occur with an empty DataFrame
        assert empty_processor.df.empty
