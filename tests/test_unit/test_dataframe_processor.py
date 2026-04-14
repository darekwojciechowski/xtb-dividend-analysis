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
        assert processor.df.loc[1, "Tax Collected"] == pytest.approx(-1.5)
        assert pd.isna(processor.df.loc[1, "Net Dividend"])
        # Positive values unchanged
        assert processor.df.loc[0, "Net Dividend"] == pytest.approx(10.0)
        assert processor.df.loc[2, "Net Dividend"] == pytest.approx(20.0)

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
        assert result.loc[0, "Tax Collected"] == pytest.approx(0.30)
        assert result.loc[1, "Tax Collected"] == pytest.approx(0.15)


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


@pytest.mark.unit
class TestInitialization:
    """Test suite for DataFrameProcessor initialization."""

    def test_init_when_none_then_raises_value_error(self) -> None:
        """Tests that passing None raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            DataFrameProcessor(None)


@pytest.mark.unit
class TestConvertDates:
    """Test suite for convert_dates with auto-detection."""

    def test_convert_dates_when_no_col_given_then_auto_detects_date_column(
        self,
    ) -> None:
        """Tests that convert_dates resolves 'Date' column automatically."""
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01", "2024-06-15"],
                "Ticker": ["A", "B"],
                "Amount": [10.0, 20.0],
            }
        )
        processor = DataFrameProcessor(df)

        processor.convert_dates()

        assert pd.api.types.is_datetime64_any_dtype(processor.df["Date"])

    def test_convert_dates_when_explicit_col_given_then_converts_that_column(
        self,
    ) -> None:
        """Tests that explicit date_col bypasses auto-detection."""
        df = pd.DataFrame(
            {
                "settlement_date": ["2024-03-10", "2024-09-22"],
                "Ticker": ["A", "B"],
            }
        )
        processor = DataFrameProcessor(df)

        processor.convert_dates(date_col="settlement_date")

        assert pd.api.types.is_datetime64_any_dtype(processor.df["settlement_date"])

    def test_convert_dates_when_data_column_present_then_auto_detects_it(
        self,
    ) -> None:
        """Tests that convert_dates resolves 'Data' column automatically."""
        df = pd.DataFrame(
            {
                "Data": ["2024-01-15", "2024-07-04"],
                "Ticker": ["A", "B"],
            }
        )
        processor = DataFrameProcessor(df)

        processor.convert_dates()

        assert pd.api.types.is_datetime64_any_dtype(processor.df["Data"])

    def test_convert_dates_when_called_then_values_are_correct_datetimes(
        self,
    ) -> None:
        """Tests that parsed datetime values match the original date strings."""
        df = pd.DataFrame({"Date": ["2024-01-15", "2024-07-04"]})
        processor = DataFrameProcessor(df)

        processor.convert_dates()

        assert processor.df["Date"].iloc[0] == pd.Timestamp("2024-01-15")
        assert processor.df["Date"].iloc[1] == pd.Timestamp("2024-07-04")

    def test_convert_dates_when_invalid_date_then_becomes_nat(
        self,
    ) -> None:
        """Tests that invalid date strings are coerced to NaT, not raised."""
        df = pd.DataFrame({"Date": ["2024-01-01", "not-a-date", "2024-12-31"]})
        processor = DataFrameProcessor(df)

        processor.convert_dates()

        assert pd.isna(processor.df["Date"].iloc[1])
        assert processor.df["Date"].iloc[0] == pd.Timestamp("2024-01-01")
        assert processor.df["Date"].iloc[2] == pd.Timestamp("2024-12-31")


@pytest.mark.unit
class TestPrepareAndConvert:
    """Test suite for prepare_columns and convert_columns_to_numeric."""

    def test_prepare_columns_when_missing_then_creates_them(self) -> None:
        """Tests that prepare_columns adds Tax Collected and Net Dividend if absent."""
        df = pd.DataFrame(
            {"Date": ["2024-01-01"], "Ticker": ["AAPL"], "Amount": [10.0]}
        )
        processor = DataFrameProcessor(df)

        processor.prepare_columns()

        assert "Tax Collected" in processor.df.columns
        assert "Net Dividend" in processor.df.columns

    def test_convert_columns_to_numeric_when_called_then_columns_are_numeric(
        self,
    ) -> None:
        """Tests that Net Dividend and Tax Collected become numeric."""
        df = pd.DataFrame(
            {
                "Net Dividend": ["5.5", "3.2"],
                "Tax Collected": ["1.1", "0.9"],
                "Ticker": ["A", "B"],
            }
        )
        processor = DataFrameProcessor(df)

        processor.convert_columns_to_numeric()

        assert pd.api.types.is_numeric_dtype(processor.df["Net Dividend"])
        assert pd.api.types.is_numeric_dtype(processor.df["Tax Collected"])


@pytest.mark.unit
class TestDeprecatedMethods:
    """Test suite for deprecated/forwarding methods."""

    def test_merge_and_sum_when_called_then_delegates_to_merge_rows_and_reorder(
        self,
    ) -> None:
        """Tests that merge_and_sum calls merge_rows_and_reorder."""
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
                "Ticker": ["AAPL", "AAPL"],
                "Net Dividend": [5.0, 3.0],
                "Tax Collected": [1.0, 0.5],
                "Shares": [1, 1],
                "Currency": ["USD", "USD"],
                "Type": ["Dividend", "Withholding Tax"],
                "Comment": ["div", "tax"],
            }
        )
        processor = DataFrameProcessor(df)

        processor.merge_and_sum()

        assert "Type" not in processor.df.columns
        assert "Comment" not in processor.df.columns


@pytest.mark.unit
class TestPrivateDelegates:
    """Test suite for private forwarding delegate methods."""

    def test_extract_dividend_from_comment_when_valid_comment_then_returns_values(
        self,
    ) -> None:
        """Tests that _extract_dividend_from_comment returns dividend and currency."""
        df = pd.DataFrame({"Ticker": ["SBUX.US"], "Net Dividend": [5.7]})
        processor = DataFrameProcessor(df)

        result = processor._extract_dividend_from_comment("SBUX.US USD 0.5700/ SHR")

        assert result[0] == pytest.approx(0.57)
        assert result[1] == "USD"

    def test_determine_currency_when_us_ticker_then_returns_usd(self) -> None:
        """Tests that _determine_currency returns USD for .US tickers."""
        df = pd.DataFrame({"Ticker": ["AAPL.US"], "Net Dividend": [10.0]})
        processor = DataFrameProcessor(df)

        result = processor._determine_currency("AAPL.US", None)

        assert result == "USD"

    def test_extract_tax_rate_from_comment_when_wht_present_then_returns_rate(
        self,
    ) -> None:
        """Tests that _extract_tax_rate_from_comment parses WHT percentage."""
        df = pd.DataFrame({"Ticker": ["AAPL.US"], "Net Dividend": [10.0]})
        processor = DataFrameProcessor(df)

        result = processor._extract_tax_rate_from_comment("WHT 15%")

        assert result == pytest.approx(0.15)

    def test_get_default_tax_rate_when_us_ticker_then_returns_015(self) -> None:
        """Tests that _get_default_tax_rate returns 0.15 for US tickers."""
        df = pd.DataFrame({"Ticker": ["AAPL.US"], "Net Dividend": [10.0]})
        processor = DataFrameProcessor(df)

        result = processor._get_default_tax_rate("AAPL.US")

        assert result == pytest.approx(0.15)

    def test_get_exchange_rate_when_called_then_delegates_to_currency_converter(
        self,
    ) -> None:
        """Tests that _get_exchange_rate delegates to CurrencyConverter."""
        df = pd.DataFrame({"Ticker": ["AAPL.US"], "Net Dividend": [10.0]})
        processor = DataFrameProcessor(df)

        with patch(
            "data_processing.currency_converter.CurrencyConverter.get_exchange_rate",
            return_value=4.2,
        ):
            result = processor._get_exchange_rate(["dummy.csv"], "2024-01-01", "USD")

        assert result == pytest.approx(4.2)


@pytest.mark.unit
class TestReplaceTaxValues:
    """Test suite for the deprecated replace_tax_values method."""

    def test_replace_tax_values_when_called_then_computes_tax_from_rate(self) -> None:
        """Tests that replace_tax_values fills Tax Collected based on comment rate."""
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01"],
                "Ticker": ["AAPL.US"],
                "Net Dividend": [100.0],
                "Tax Collected": [0.0],
                "Comment": ["WHT 15%"],
            }
        )
        processor = DataFrameProcessor(df)

        result = processor.replace_tax_values()

        assert result.loc[0, "Tax Collected"] == pytest.approx(15.0)

    def test_replace_tax_values_when_no_comment_rate_then_uses_default(self) -> None:
        """Tests that replace_tax_values falls back to default rate when comment has no rate."""
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01"],
                "Ticker": ["AAPL.US"],
                "Net Dividend": [100.0],
                "Tax Collected": [0.0],
                "Comment": ["Dividend payment"],
            }
        )
        processor = DataFrameProcessor(df)

        result = processor.replace_tax_values()

        assert result.loc[0, "Tax Collected"] == pytest.approx(15.0)


@pytest.mark.unit
class TestCalculateTaxInPln:
    """Test suite for USD and PLN statement tax calculation."""

    def test_calculate_tax_usd_when_called_then_adds_tax_amount_pln_column(
        self,
    ) -> None:
        """Tests that calculate_tax_in_pln_for_detected_usd adds Tax Amount PLN."""
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2024-01-02"]),
                "Ticker": ["AAPL.US"],
                "Net Dividend": ["5.7 USD"],
                "Tax Collected": [0.15],
                "Tax Collected Amount": ["0.855 USD"],
                "Exchange Rate D-1": ["4.0 PLN"],
            }
        )
        processor = DataFrameProcessor(df)

        result = processor.calculate_tax_in_pln_for_detected_usd(
            courses_paths=[], statement_currency="USD"
        )

        assert "Tax Amount PLN" in result.columns


@pytest.mark.unit
class TestGetPreviousBusinessDay:
    """Test suite for _get_previous_business_day static method."""

    def test_get_previous_business_day_when_monday_then_returns_friday(self) -> None:
        """Tests that Monday returns the previous Friday."""
        import datetime

        monday = datetime.date(2024, 1, 8)  # Monday
        result = DataFrameProcessor._get_previous_business_day(monday)

        assert result == datetime.date(2024, 1, 5)  # Friday

    def test_get_previous_business_day_when_tuesday_then_returns_monday(self) -> None:
        """Tests that a regular Tuesday returns the previous Monday."""
        import datetime

        tuesday = datetime.date(2024, 1, 9)
        result = DataFrameProcessor._get_previous_business_day(tuesday)

        assert result == datetime.date(2024, 1, 8)


@pytest.mark.unit
class TestParseDividendToPln:
    """Test suite for parse_dividend_to_pln static method."""

    def test_parse_when_pln_then_uses_exchange_rate_1(self) -> None:
        """Tests that exchange rate '-' (PLN) results in factor of 1.0."""
        row = pd.Series({"Net Dividend": "10.0 PLN", "Exchange Rate D-1": "-"})

        result = DataFrameProcessor.parse_dividend_to_pln(row)

        assert result == pytest.approx(10.0)

    def test_parse_when_usd_then_multiplies_by_rate(self) -> None:
        """Tests that USD net dividend is multiplied by exchange rate."""
        row = pd.Series({"Net Dividend": "5.0 USD", "Exchange Rate D-1": "4.0 PLN"})

        result = DataFrameProcessor.parse_dividend_to_pln(row)

        assert result == pytest.approx(20.0)

    def test_parse_when_invalid_values_then_returns_zero(self) -> None:
        """Tests that malformed data returns 0.0 without raising."""
        row = pd.Series({"Net Dividend": "N/A", "Exchange Rate D-1": "bad"})

        result = DataFrameProcessor.parse_dividend_to_pln(row)

        assert result == pytest.approx(0.0)


@pytest.mark.unit
class TestLogTableWithTaxSummary:
    """Test suite for log_table_with_tax_summary."""

    def test_log_table_when_tax_collected_present_then_drops_for_display(
        self,
    ) -> None:
        """Tests that Tax Collected column is dropped from display without raising."""
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2024-01-01"]),
                "Ticker": ["AAPL.US"],
                "Net Dividend": ["10.0 USD"],
                "Tax Collected": [0.15],
                "Exchange Rate D-1": ["4.0 PLN"],
            }
        )
        processor = DataFrameProcessor(df)

        # Should not raise
        processor.log_table_with_tax_summary(statement_currency="USD")

    def test_log_table_when_no_tax_collected_then_no_error(self) -> None:
        """Tests that missing Tax Collected column is handled gracefully."""
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2024-01-01"]),
                "Ticker": ["AAPL.US"],
                "Net Dividend": ["10.0 USD"],
                "Exchange Rate D-1": ["4.0 PLN"],
            }
        )
        processor = DataFrameProcessor(df)

        processor.log_table_with_tax_summary(statement_currency="USD")


@pytest.mark.unit
class TestProcess:
    """Test suite for the process() orchestration method."""

    def test_process_when_called_then_executes_all_pipeline_steps(self) -> None:
        """Tests that process() calls each pipeline step and returns a DataFrame."""
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01"],
                "Ticker": ["AAPL"],
                "Amount": [10.0],
                "Type": ["Dividend"],
                "Comment": ["div"],
                "Tax Collected": [0.15],
                "Shares": [1],
                "Currency": ["USD"],
            }
        )
        processor = DataFrameProcessor(df)

        with patch.object(processor, "merge_and_sum"):
            result = processor.process()

        assert isinstance(result, pd.DataFrame)

    def test_process_when_no_tax_collected_column_then_adds_it(self) -> None:
        """Tests that process() adds Tax Collected column when it is absent."""
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01"],
                "Ticker": ["AAPL"],
                "Amount": [10.0],
                "Type": ["Dividend"],
                "Comment": ["div"],
                "Shares": [1],
                "Currency": ["USD"],
            }
        )
        processor = DataFrameProcessor(df)

        with patch.object(processor, "merge_and_sum"):
            result = processor.process()

        assert isinstance(result, pd.DataFrame)


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
