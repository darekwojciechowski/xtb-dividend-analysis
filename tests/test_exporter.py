"""Tests for GoogleSpreadsheetExporter module."""

from pathlib import Path

import pandas as pd
import pytest

from data_processing.exporter import GoogleSpreadsheetExporter


@pytest.mark.unit
class TestAnsiRemoval:
    """Test suite for ANSI escape sequence removal functionality."""

    def test_remove_ansi_method(
        self, sample_dataframe_with_ansi: pd.DataFrame
    ) -> None:
        """Tests that the remove_ansi method correctly removes ANSI escape sequences."""
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)
        cleaned_text = exporter.remove_ansi("\x1b[31mMSFT\x1b[0m")
        assert cleaned_text == "MSFT"

    def test_export_removes_ansi_from_ticker(
        self, sample_dataframe_with_ansi: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Tests that export_to_google removes ANSI sequences from the Ticker column."""
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)
        output_file = tmp_path / "test_output.csv"
        exporter.export_to_google(filename=str(output_file))

        exported_df = pd.read_csv(output_file, sep="\t")
        assert "MSFT" in exported_df["Ticker"].values


@pytest.mark.unit
class TestDataTransformation:
    """Test suite for data transformation operations during export."""

    def test_replaces_nan_with_zero(
        self, sample_dataframe_with_ansi: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Tests that export_to_google replaces NaN values with 0."""
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)
        output_file = tmp_path / "test_output.csv"
        exporter.export_to_google(filename=str(output_file))

        exported_df = pd.read_csv(output_file, sep="\t")
        exported_df["Comment"] = exported_df["Comment"].astype(str)
        assert exported_df["Comment"].isnull().sum() == 0
        assert "0" in exported_df["Comment"].values

    def test_rounds_numeric_columns(
        self, sample_dataframe_with_ansi: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Tests that export_to_google rounds numeric columns to two decimal places."""
        exporter = GoogleSpreadsheetExporter(sample_dataframe_with_ansi)
        output_file = tmp_path / "test_output.csv"
        exporter.export_to_google(filename=str(output_file))

        exported_df = pd.read_csv(output_file, sep="\t")
        assert all(
            exported_df["Amount"].apply(lambda x: len(str(x).split(".")[1]) <= 2)
        )


@pytest.mark.unit
class TestExportValidation:
    """Test suite for export validation and error handling."""

    def test_validates_ticker_column_exists(self, tmp_path: Path) -> None:
        """Tests that export raises ValueError if the Ticker column is missing."""
        invalid_df = pd.DataFrame({"Amount": [10.0, 20.0]})
        exporter = GoogleSpreadsheetExporter(invalid_df)

        with pytest.raises(
            ValueError, match="The DataFrame must contain a 'Ticker' column."
        ):
            exporter.export_to_google(filename=str(tmp_path / "test_output.csv"))
