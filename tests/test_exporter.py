import pytest
import pandas as pd
import os
from data_processing.exporter import GoogleSpreadsheetExporter


@pytest.fixture
def sample_dataframe():
    """
    Provides a sample DataFrame for testing GoogleSpreadsheetExporter methods.
    """
    return pd.DataFrame({
        "Ticker": ["AAPL", "\x1B[31mMSFT\x1B[0m"],
        "Amount": [10.12345, 20.6789],
        "Type": ["Cash", "Cash"],
        "Comment": ["Dividend", None]
    })


def test_remove_ansi(sample_dataframe):
    """
    Tests that the remove_ansi method correctly removes ANSI escape sequences from strings.
    """
    exporter = GoogleSpreadsheetExporter(sample_dataframe)
    cleaned_text = exporter.remove_ansi("\x1B[31mMSFT\x1B[0m")
    assert cleaned_text == "MSFT"


def test_export_to_google_removes_ansi(sample_dataframe, tmp_path):
    """
    Tests that export_to_google removes ANSI sequences from the 'Ticker' column.
    """
    exporter = GoogleSpreadsheetExporter(sample_dataframe)
    output_file = tmp_path / "test_output.csv"
    exporter.export_to_google(filename=str(output_file))

    exported_df = pd.read_csv(output_file, sep='\t')
    assert "MSFT" in exported_df["Ticker"].values


def test_export_to_google_replaces_nan(sample_dataframe, tmp_path):
    """
    Tests that export_to_google replaces NaN values with 0.
    """
    exporter = GoogleSpreadsheetExporter(sample_dataframe)
    output_file = tmp_path / "test_output.csv"
    exporter.export_to_google(filename=str(output_file))

    exported_df = pd.read_csv(output_file, sep='\t')
    exported_df["Comment"] = exported_df["Comment"].astype(
        str)  # Ensure consistent type
    assert exported_df["Comment"].isnull().sum() == 0
    assert "0" in exported_df["Comment"].values


def test_export_to_google_rounds_numeric(sample_dataframe, tmp_path):
    """
    Tests that export_to_google rounds numeric columns to two decimal places.
    """
    exporter = GoogleSpreadsheetExporter(sample_dataframe)
    output_file = tmp_path / "test_output.csv"
    exporter.export_to_google(filename=str(output_file))

    exported_df = pd.read_csv(output_file, sep='\t')
    assert all(exported_df["Amount"].apply(
        lambda x: len(str(x).split(".")[1]) <= 2))


def test_export_to_google_validates_ticker_column(tmp_path):
    """
    Tests that export_to_google raises a ValueError if the 'Ticker' column is missing.
    """
    invalid_df = pd.DataFrame({"Amount": [10.0, 20.0]})
    exporter = GoogleSpreadsheetExporter(invalid_df)

    with pytest.raises(ValueError, match="The DataFrame must contain a 'Ticker' column."):
        exporter.export_to_google(filename=str(tmp_path / "test_output.csv"))
