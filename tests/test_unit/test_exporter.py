"""Tests for GoogleSpreadsheetExporter module."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_processing.exporter import GoogleSpreadsheetExporter


@pytest.mark.unit
class TestAnsiRemoval:
    """Test suite for ANSI escape sequence removal functionality."""

    ansi_text = "\x1b[31mMSFT\x1b[0m"
    expected_clean_text = "MSFT"

    def test_remove_ansi_when_plain_text_then_returns_unchanged(
        self, sample_dataframe_with_ansi: pd.DataFrame
    ) -> None:
        """Tests that plain text without ANSI codes passes through unchanged."""
        # Arrange
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)
        plain_text = "MSFT"

        # Act
        result = exporter.remove_ansi(plain_text)

        # Assert
        assert result == plain_text

    def test_remove_ansi_when_empty_string_then_returns_empty(
        self, sample_dataframe_with_ansi: pd.DataFrame
    ) -> None:
        """Tests that empty string input returns empty string."""
        # Arrange
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)

        # Act
        result = exporter.remove_ansi("")

        # Assert
        assert result == ""

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

    decimal_places = 2
    replacement_value = "0"

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
        for idx, val in enumerate(exported_df["Amount"]):
            decimal_str = str(val).split(".")[1] if "." in str(val) else ""
            assert len(decimal_str) <= self.decimal_places, (
                f"Row {idx}: {val!r} has {len(decimal_str)} decimal places, expected ≤{self.decimal_places}"
            )


@pytest.mark.unit
class TestExportValidation:
    """Test suite for export validation and error handling."""

    EXPECTED_ERROR_MESSAGE = "The DataFrame must contain a 'Ticker' column."

    def test_export_when_ticker_column_missing_then_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        """Tests that export raises ValueError when Ticker column is missing."""
        # Arrange
        invalid_df = pd.DataFrame({"Amount": [10.0, 20.0]})
        exporter = GoogleSpreadsheetExporter(invalid_df)
        output_file = tmp_path / "test_output.csv"

        # Act & Assert
        with pytest.raises(ValueError, match=self.EXPECTED_ERROR_MESSAGE):
            exporter.export_to_google(filename=str(output_file))


@pytest.mark.unit
class TestTaxColumnDrop:
    """Test suite for the conditional Tax Collected column removal."""

    def test_export_when_both_tax_columns_present_then_drops_tax_collected(
        self, tmp_path: Path
    ) -> None:
        """Tests that 'Tax Collected' is dropped when 'Tax Collected %' also present."""
        # Arrange
        df = pd.DataFrame(
            {
                "Ticker": ["AAPL"],
                "Tax Collected": [2.5],
                "Tax Collected %": [0.15],
            }
        )
        exporter = GoogleSpreadsheetExporter(df)
        output_file = tmp_path / "output.csv"

        # Act
        exporter.export_to_google(filename=str(output_file))
        exported_df = pd.read_csv(output_file, sep="\t")

        # Assert
        assert "Tax Collected" not in exported_df.columns
        assert "Tax Collected %" in exported_df.columns

    def test_export_when_only_tax_collected_no_pct_column_then_kept(
        self, tmp_path: Path
    ) -> None:
        """Tests that 'Tax Collected' is kept when 'Tax Collected %' is absent."""
        # Arrange
        df = pd.DataFrame(
            {
                "Ticker": ["AAPL"],
                "Tax Collected": [2.5],
            }
        )
        exporter = GoogleSpreadsheetExporter(df)
        output_file = tmp_path / "output.csv"

        # Act
        exporter.export_to_google(filename=str(output_file))
        exported_df = pd.read_csv(output_file, sep="\t")

        # Assert
        assert "Tax Collected" in exported_df.columns


@pytest.mark.unit
class TestExportFileFormat:
    """Test suite for output file format correctness."""

    def test_export_when_written_then_file_is_tab_separated(
        self, sample_dataframe_with_ansi: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Tests that the output file uses tab as the field separator."""
        # Arrange
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)
        output_file = tmp_path / "output.csv"

        # Act
        exporter.export_to_google(filename=str(output_file))
        raw_content = output_file.read_text()

        # Assert: header contains tabs between column names
        header_line = raw_content.splitlines()[0]
        expected_columns = len(sample_dataframe_with_ansi.columns)
        assert header_line.count("\t") == expected_columns - 1
        assert "," not in header_line

    def test_export_creates_output_directory_if_missing(
        self,
        sample_dataframe_with_ansi: pd.DataFrame,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Tests that the output directory is created when it does not exist."""
        # Arrange
        monkeypatch.chdir(tmp_path)
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)

        # Act
        exporter.export_to_google(filename="result.csv")

        # Assert
        assert (tmp_path / "output" / "result.csv").exists()
