"""Google Sheets CSV export for dividend analysis results.

This module serializes the processed dividend DataFrame to a
tab-separated CSV file ready to paste into Google Sheets.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


class GoogleSpreadsheetExporter:
    """Exports the processed dividend DataFrame to a Google Sheets-compatible CSV.

    Strips ANSI color codes, drops intermediate calculation columns, and
    writes a tab-separated file to the ``output/`` directory.
    """

    def __init__(self, df: pd.DataFrame):
        """Initialize GoogleSpreadsheetExporter with a DataFrame.

        Args:
            df: The DataFrame to process and export.
        """
        self.df = df

    def remove_ansi(self, text: str) -> str:
        """Remove ANSI escape sequences from a string.

        Args:
            text: The string potentially containing ANSI escape sequences.

        Returns:
            The string with all ANSI sequences removed.
        """
        ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        return ansi_escape.sub("", text)

    def export_to_google(self, filename: str = "for_google_spreadsheet.csv") -> None:
        """Export the DataFrame to a tab-separated CSV file for Google Sheets.

        Saves the file to the ``output/`` directory, creating it if needed.
        Removes ANSI sequences from ``Ticker``, drops the numeric
        ``Tax Collected`` column when the display column is present, fills
        ``NaN`` with ``0``, and rounds numeric columns to two decimal places.

        Args:
            filename: Name of the output file.

        Raises:
            ValueError: If the DataFrame does not contain a ``Ticker`` column.
        """
        # Validate that the DataFrame has a 'Ticker' column
        if "Ticker" not in self.df.columns:
            raise ValueError("The DataFrame must contain a 'Ticker' column.")

        # Remove ANSI sequences from 'Ticker'
        self.df["Ticker"] = self.df["Ticker"].apply(self.remove_ansi)

        # Drop numeric 'Tax Collected' column (keep only 'Tax Collected %' for display)
        if "Tax Collected" in self.df.columns and "Tax Collected %" in self.df.columns:
            self.df = self.df.drop(columns=["Tax Collected"])

        # Replace NaN values with 0
        self.df = self.df.fillna(0)

        # Round numeric columns to two decimal places
        numeric_cols = self.df.select_dtypes(include=["number"]).columns
        self.df[numeric_cols] = self.df[numeric_cols].round(2)

        # Create output directory if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create full file path
        file_path = output_dir / filename

        # Export to CSV with tab as separator
        self.df.to_csv(file_path, sep="\t", index=False)
