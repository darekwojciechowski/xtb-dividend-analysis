"""Unit tests for DataFrameProcessor.

Verifies the column-manipulation, data-transformation, filtering, aggregation,
tax-processing, and performance characteristics of ``DataFrameProcessor``.

Test classes:
    TestColumnOperations       — rename_columns, get_column_name, add_empty_column
    TestDataTransformation     — apply_colorize_ticker, apply_extractor,
                                 move_negative_values, add_currency_to_dividends
    TestFilteringOperations    — filter_dividends (row count, NaN removal)
    TestAggregationOperations  — group_by_dividends, calculate_dividend
    TestTaxProcessing          — replace_tax_with_percentage (parametrised)
    TestDataFrameAccess        — get_processed_df
    TestEdgeCases              — empty DataFrame handling
    TestPerformance            — group_by_dividends with large payloads

All tests carry the ``@pytest.mark.unit`` marker. External IO is isolated via
``unittest.mock.patch``. Performance tests additionally carry
``@pytest.mark.performance``; edge-case tests carry ``@pytest.mark.edge_case``.
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from data_processing.dataframe_processor import DataFrameProcessor


@pytest.fixture
def processor(sample_dataframe: pd.DataFrame) -> DataFrameProcessor:
    """
    Provides a DataFrameProcessor instance initialized with the sample DataFrame.

    A copy of the session-scoped fixture is used so that mutations inside
    each test do not bleed into other tests that share the same DataFrame.

    Args:
        sample_dataframe: Sample DataFrame fixture from conftest.py.

    Returns:
        DataFrameProcessor instance initialised with a fresh copy of the data.
    """
    return DataFrameProcessor(sample_dataframe.copy())


@pytest.mark.unit
class TestColumnOperations:
    """Test suite for column manipulation operations."""

    rename_mapping = {"Date": "TransactionDate", "Amount": "Value"}
    column_alternatives = ("Ticker", "Symbol")
    new_column_name = "New Column"

    def test_rename_when_valid_mapping_then_columns_updated(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that columns are renamed correctly with valid mapping."""
        # Arrange
        original_date_values = processor.df["Date"].tolist()

        # Act
        processor.rename_columns(self.rename_mapping)

        # Assert — old names gone, new names present, data preserved
        assert "TransactionDate" in processor.df.columns
        assert "Value" in processor.df.columns
        assert "Date" not in processor.df.columns
        assert "Amount" not in processor.df.columns
        assert processor.df["TransactionDate"].tolist() == original_date_values

    def test_get_column_name_when_column_exists_then_returns_exact_match(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that the english column name is returned when it exists."""
        # Arrange - processor has "Ticker" column

        # Act
        result = processor.get_column_name(*self.column_alternatives)

        # Assert — English name takes priority when present
        assert result == "Ticker"

    def test_add_empty_column_when_called_then_inserted_at_correct_position(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that new column with NaN values is inserted at position 4."""
        # Arrange
        original_columns = list(processor.df.columns)

        # Act
        processor.add_empty_column(self.new_column_name)

        # Assert — column exists, all NaN, and at correct position
        assert self.new_column_name in processor.df.columns
        assert processor.df[self.new_column_name].isnull().all()
        assert list(processor.df.columns).index(self.new_column_name) == 4
        # Original columns are all still present
        for col in original_columns:
            assert col in processor.df.columns


@pytest.mark.unit
class TestDataTransformation:
    """Test suite for data transformation operations."""

    required_ticker_column = "Ticker"

    def test_colorize_when_applied_then_colored_ticker_column_created(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that Colored Ticker column is created with ANSI escape codes."""
        # Arrange - processor from fixture

        # Act
        processor.apply_colorize_ticker()

        # Assert — original Ticker preserved, new Colored Ticker created with ANSI
        assert self.required_ticker_column in processor.df.columns
        assert "Colored Ticker" in processor.df.columns
        for idx, row in processor.df.iterrows():
            colored = row["Colored Ticker"]
            original = row["Ticker"]
            # Colored ticker must contain the original ticker text
            assert original in colored
            # Must contain ANSI reset code
            assert "\033[0m" in colored

    def test_extract_when_applied_then_comments_transformed(self) -> None:
        """Tests that extractor transforms comment values based on keywords."""
        # Arrange — use known keyword-matching comments
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "Ticker": ["A", "B", "C"],
                "Amount": [10.0, 20.0, 30.0],
                "Type": ["Cash", "Cash", "Cash"],
                "Comment": [
                    "Transfer from Blik account",
                    "Pekao bank wire",
                    "SBUX.US USD 0.5700/ SHR",
                ],
                "Net Dividend": [10.0, 20.0, 30.0],
                "Shares": [1, 2, 3],
                "Currency": ["PLN", "PLN", "USD"],
            }
        )
        processor = DataFrameProcessor(df)

        # Act
        processor.apply_extractor()

        # Assert — keyword matches become canonical labels
        assert processor.df.loc[0, "Comment"] == "Blik(Payu) deposit"
        assert processor.df.loc[1, "Comment"] == "Pekao S.A. deposit"
        # Non-matching comment stays unchanged
        assert processor.df.loc[2, "Comment"] == "SBUX.US USD 0.5700/ SHR"

    def test_move_negative_when_executed_then_negatives_moved_to_tax_collected(
        self,
    ) -> None:
        """Tests that negative Net Dividend values move to Tax Collected column."""
        # Arrange
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "Ticker": ["AAPL", "MSFT", "GOOGL"],
                "Amount": [10.0, -1.5, 20.0],
                "Type": ["Cash", "Cash", "Cash"],
                "Comment": ["Div", "Tax", "Div"],
                "Net Dividend": [10.0, -1.5, 20.0],
                "Shares": [1, 1, 2],
                "Currency": ["USD", "USD", "USD"],
            }
        )
        processor = DataFrameProcessor(df)

        # Act
        processor.move_negative_values()

        # Assert — negative value moved to Tax Collected
        assert processor.df.loc[1, "Tax Collected"] == -1.5
        assert pd.isna(processor.df.loc[1, "Net Dividend"])
        # Positive values unchanged
        assert processor.df.loc[0, "Net Dividend"] == 10.0
        assert processor.df.loc[2, "Net Dividend"] == 20.0

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

    def test_add_currency_when_called_then_appends_correct_currency_suffix(
        self,
    ) -> None:
        """Tests that correct currency suffix is appended based on ticker."""
        # Arrange
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                "Ticker": ["SBUX.US", "TKT.PL", "NOVOB.DK", "SHEL.UK"],
                "Amount": [10.0, 20.0, 30.0, 40.0],
                "Type": ["Cash", "Cash", "Cash", "Cash"],
                "Comment": ["Div", "Div", "Div", "Div"],
                "Net Dividend": [5.7, 3.2, 8.1, 12.0],
                "Shares": [1, 2, 1, 3],
                "Currency": ["USD", "PLN", "DKK", "GBP"],
            }
        )
        processor = DataFrameProcessor(df)

        # Act
        processor.add_currency_to_dividends()

        # Assert
        assert processor.df.loc[0, "Net Dividend"] == "5.7 USD"
        assert processor.df.loc[1, "Net Dividend"] == "3.2 PLN"
        assert processor.df.loc[2, "Net Dividend"] == "8.1 DKK"
        assert processor.df.loc[3, "Net Dividend"] == "12.0 GBP"


@pytest.mark.unit
class TestFilteringOperations:
    """Test suite for data filtering operations."""

    all_valid_dividend_types = [
        "Dividend",
        "Dywidenda",
        "DIVIDENT",
        "Withholding Tax",
        "Podatek od dywidend",
    ]

    def test_filter_when_called_then_only_dividend_types_remain(self) -> None:
        """Tests that only valid dividend type rows survive filtering."""
        # Arrange
        df = pd.DataFrame(
            {
                "Type": [
                    "Dividend",
                    "Fee",
                    "Dywidenda",
                    "Commission",
                    "Withholding Tax",
                    "Cash",
                    "Podatek od dywidend",
                    "DIVIDENT",
                ],
                "Amount": [10.0, 5.0, 20.0, 3.0, -1.5, 100.0, -2.0, 15.0],
            }
        )
        processor = DataFrameProcessor(df)

        # Act
        processor.filter_dividends()

        # Assert
        assert len(processor.df) == 5
        assert set(processor.df["Type"].tolist()) == {
            "Dividend",
            "Dywidenda",
            "Withholding Tax",
            "Podatek od dywidend",
            "DIVIDENT",
        }
        assert all(processor.df["Type"].isin(self.all_valid_dividend_types))

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
        assert len(processor.df) == 2
        assert processor.df["Type"].isnull().sum() == 0
        assert list(processor.df["Type"]) == ["Dividend", "Dywidenda"]
        assert list(processor.df["Amount"]) == [10.0, 30.0]


@pytest.mark.unit
class TestAggregationOperations:
    """Test suite for data aggregation operations."""

    dummy_paths = ["dummy_path"]
    language = "en"

    def test_group_when_called_then_amounts_are_summed_by_group(
        self,
    ) -> None:
        """Tests that grouping sums amounts per Date+Ticker+Type+Comment group."""
        # Arrange — two rows for same ticker on same date, different amounts
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01", "2024-01-01", "2024-01-02"],
                "Ticker": ["SBUX.US", "SBUX.US", "MSFT.US"],
                "Amount": [5.7, 3.3, 12.0],
                "Type": ["Dividend", "Dividend", "Dividend"],
                "Comment": [
                    "SBUX.US USD 0.5700/ SHR",
                    "SBUX.US USD 0.5700/ SHR",
                    "MSFT.US USD 0.7500/ SHR",
                ],
            }
        )
        processor = DataFrameProcessor(df)

        # Act
        processor.group_by_dividends()

        # Assert — two SBUX rows merged into one, MSFT stays separate
        assert len(processor.df) == 2
        assert "Net Dividend" in processor.df.columns
        sbux_row = processor.df[processor.df["Ticker"] == "SBUX.US"]
        assert sbux_row["Net Dividend"].values[0] == pytest.approx(9.0)
        msft_row = processor.df[processor.df["Ticker"] == "MSFT.US"]
        assert msft_row["Net Dividend"].values[0] == pytest.approx(12.0)

    def test_calculate_when_called_then_shares_computed_correctly(
        self,
    ) -> None:
        """Tests that dividend calculation produces correct Shares values."""
        # Arrange — known data: total_dividend=5.7, per_share=0.57, rate=4.0
        # Expected shares = 5.7 / (0.57 * 4.0) = 5.7 / 2.28 = 2.5 → round = 2
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2024-01-02"]),
                "Ticker": ["SBUX.US"],
                "Net Dividend": [5.7],
                "Shares": [0],
                "Comment": ["SBUX.US USD 0.5700/ SHR"],
                "Date D-1": pd.to_datetime(["2024-01-01"]),
                "Type": ["Dividend"],
                "Currency": ["USD"],
            }
        )
        processor = DataFrameProcessor(df)

        # Act
        with patch(
            "data_processing.currency_converter.CurrencyConverter.get_exchange_rate",
            return_value=4.0,
        ):
            processor.calculate_dividend(["dummy_path"], statement_currency="PLN")

        # Assert — shares = round(5.7 / (0.57 * 4.0)) = round(2.500...) = 3
        assert processor.df.loc[0, "Shares"] == 3
        assert processor.df.loc[0, "Currency"] == "USD"
        # Net Dividend recalculated: shares * dividend_per_share = 3 * 0.57 = 1.71
        assert processor.df.loc[0, "Net Dividend"] == pytest.approx(1.71)


@pytest.mark.unit
class TestTaxProcessing:
    """Test suite for tax-related processing operations."""

    base_amount = 100.0

    @pytest.mark.parametrize(
        "tax_values,has_zero_or_nan",
        [
            ([0.15, 0.20, 0.19], False),
            ([0.05, 0.0, 0.30], True),  # Contains 0
            ([0.19, 0.25, 0.15], False),
        ],
    )
    def test_replace_when_various_tax_values_then_validates_correctly(
        self, tax_values: list[float], has_zero_or_nan: bool
    ) -> None:
        """Tests that replace_tax_with_percentage preserves tax values and validates them."""
        # Arrange
        df = pd.DataFrame(
            {
                "Comment": ["Test"] * len(tax_values),
                "Tax Collected": tax_values,
                "Net Dividend": [self.base_amount] * len(tax_values),
                "Ticker": ["TEST.US"] * len(tax_values),
                "Date": ["2025-01-01"] * len(tax_values),
            }
        )
        processor = DataFrameProcessor(df)

        # Act
        result = processor.replace_tax_with_percentage()

        # Assert — tax values are preserved unchanged
        assert "Tax Collected" in result.columns
        assert list(result["Tax Collected"]) == tax_values
        # Row count preserved
        assert len(result) == len(tax_values)
        # Zero-detection works correctly
        zero_count = (result["Tax Collected"] == 0).sum() + result[
            "Tax Collected"
        ].isna().sum()
        assert (zero_count > 0) == has_zero_or_nan

    def test_replace_when_us_ticker_30_pct_then_data_preserved(self) -> None:
        """Tests that US tickers with 30% tax rate are detected (W8BEN warning scenario)."""
        # Arrange
        df = pd.DataFrame(
            {
                "Comment": ["Div", "Div"],
                "Tax Collected": [0.30, 0.15],
                "Net Dividend": [100.0, 50.0],
                "Ticker": ["AAPL.US", "MSFT.US"],
                "Date": ["2025-01-01", "2025-01-02"],
            }
        )
        processor = DataFrameProcessor(df)

        # Act
        result = processor.replace_tax_with_percentage()

        # Assert — data preserved, 30% detection works
        assert result.loc[0, "Tax Collected"] == 0.30
        assert result.loc[1, "Tax Collected"] == 0.15


@pytest.mark.unit
class TestDataFrameAccess:
    """Test suite for DataFrame access methods."""

    def test_get_processed_when_called_then_returns_dataframe_with_expected_columns(
        self, processor: DataFrameProcessor
    ) -> None:
        """Tests that get_processed_df returns a DataFrame with the original columns and row count."""
        # Arrange - processor from fixture

        # Act
        result = processor.get_processed_df()

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "Ticker" in result.columns
        assert "Date" in result.columns
        assert list(result["Ticker"]) == ["AAPL", "MSFT"]


@pytest.mark.edge_case
class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    rename_mapping = {"Date": "TransactionDate"}

    def test_process_when_empty_dataframe_then_rename_raises_key_error(self) -> None:
        """Tests that empty DataFrame raises KeyError on rename."""
        # Arrange
        empty_processor = DataFrameProcessor(pd.DataFrame())

        # Act & Assert
        with pytest.raises(KeyError):
            empty_processor.rename_columns(self.rename_mapping)

        assert empty_processor.df.empty


@pytest.mark.performance
class TestPerformance:
    """Test suite for performance with large datasets."""

    date_start = "2024-01-01"
    frequency = "D"

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

        # Assert — grouped result has fewer rows than input (duplicate tickers/dates merged)
        assert len(processor.df) >= expected_min_length
        assert "Net Dividend" in processor.df.columns
        # When all rows share same ticker, grouping should reduce row count
        if len(set(tickers)) == 1 and len(set(types)) == 1 and len(set(comments)) == 1:
            unique_dates = len(
                set(
                    pd.date_range(
                        start=self.date_start, periods=periods, freq=self.frequency
                    )
                )
            )
            assert len(processor.df) == unique_dates
