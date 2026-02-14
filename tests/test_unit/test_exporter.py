"""Tests for GoogleSpreadsheetExporter module."""

from pathlib import Path

import pandas as pd
import pytest

from data_processing.exporter import GoogleSpreadsheetExporter


@pytest.mark.unit
class TestAnsiRemoval:
    """Test suite for ANSI escape sequence removal functionality."""

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        self.ansi_text = "\x1b[31mMSFT\x1b[0m"
        self.expected_clean_text = "MSFT"

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        # Clean up any resources if needed
        pass

    def test_remove_ansi_when_text_contains_escape_codes_then_returns_clean_text(
        self, sample_dataframe_with_ansi: pd.DataFrame
    ) -> None:
        """Tests ANSI removal from text containing escape sequences."""
        # Arrange
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)

        # Act
        cleaned_text = exporter.remove_ansi(self.ansi_text)

        # Assert
        assert cleaned_text == self.expected_clean_text

    def test_export_when_dataframe_has_ansi_then_ticker_column_is_cleaned(
        self, sample_dataframe_with_ansi: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Tests that export removes ANSI sequences from the Ticker column."""
        # Arrange
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)
        output_file = tmp_path / "test_output.csv"

        # Act
        exporter.export_to_google(filename=str(output_file))
        exported_df = pd.read_csv(output_file, sep="\t")

        # Assert
        assert self.expected_clean_text in exported_df["Ticker"].values


@pytest.mark.unit
class TestDataTransformation:
    """Test suite for data transformation operations during export."""

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        self.decimal_places = 2
        self.replacement_value = "0"

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        pass

    def test_export_when_nan_present_then_replaces_with_zero(
        self, sample_dataframe_with_ansi: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Tests that NaN values are replaced with 0 during export."""
        # Arrange
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)
        output_file = tmp_path / "test_output.csv"

        # Act
        exporter.export_to_google(filename=str(output_file))
        exported_df = pd.read_csv(output_file, sep="\t")
        exported_df["Comment"] = exported_df["Comment"].astype(str)

        # Assert
        assert exported_df["Comment"].isnull().sum() == 0
        assert self.replacement_value in exported_df["Comment"].values

    def test_export_when_numeric_columns_then_rounds_to_two_decimals(
        self, sample_dataframe_with_ansi: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Tests that numeric columns are rounded to two decimal places."""
        # Arrange
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)
        output_file = tmp_path / "test_output.csv"

        # Act
        exporter.export_to_google(filename=str(output_file))
        exported_df = pd.read_csv(output_file, sep="\t")

        # Assert
        assert all(
            exported_df["Amount"].apply(
                lambda x: len(str(x).split(".")[1]) <= self.decimal_places
            )
        )


@pytest.mark.unit
class TestExportValidation:
    """Test suite for export validation and error handling."""

    def setup_method(self) -> None:
        """Setup test fixtures before each test method."""
        self.expected_error_message = "The DataFrame must contain a 'Ticker' column."

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        pass

    def test_export_when_ticker_column_missing_then_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        """Tests that export raises ValueError when Ticker column is missing."""
        # Arrange
        invalid_df = pd.DataFrame({"Amount": [10.0, 20.0]})
        exporter = GoogleSpreadsheetExporter(invalid_df)
        output_file = tmp_path / "test_output.csv"

        # Act & Assert
        with pytest.raises(ValueError, match=self.expected_error_message):
            exporter.export_to_google(filename=str(output_file))
