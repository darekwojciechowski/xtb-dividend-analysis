"""Contract test: the exporter CSV still matches the Google-Sheets schema.

Red signal: ``GoogleSpreadsheetExporter`` has dropped a required column, or
reintroduced non-numeric junk in ``Shares``. This test runs the exporter on a
tiny synthetic DataFrame and validates the resulting file back through pandera.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_processing.exporter import GoogleSpreadsheetExporter

from .schemas import OUTPUT_CSV_SCHEMA

pytestmark = pytest.mark.contract


class TestOutputCsvSchema:
    def test_exported_csv_matches_output_schema(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arrange: a synthetic two-row DataFrame covering PLN and USD dividends.
        Act: export via GoogleSpreadsheetExporter and reload the written CSV.
        Assert: the file satisfies OUTPUT_CSV_SCHEMA and omits the raw
        ``Tax Collected`` column.
        """
        monkeypatch.chdir(tmp_path)

        df = pd.DataFrame(
            {
                "Date": ["2025-02-21", "2025-03-15"],
                "Ticker": ["TXT.PL", "AAPL.US"],
                "Shares": [7.0, 12.0],
                "Net Dividend": ["11.62 PLN", "4.80 USD"],
                "Tax Collected": [0.19, 0.15],
                "Tax Collected %": ["19%", "15%"],
                "Tax Amount PLN": ["-", "1.10 PLN"],
            }
        )

        GoogleSpreadsheetExporter(df.copy()).export_to_google()

        written = tmp_path / "output" / "for_google_spreadsheet.csv"
        assert written.exists()

        loaded = pd.read_csv(written, sep="\t")
        OUTPUT_CSV_SCHEMA.validate(loaded, lazy=True)
        assert "Tax Collected" not in loaded.columns

    def test_output_csv_when_pit38_enabled_then_row_count_equals_dataframe_row_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arrange: a synthetic DataFrame carrying foreign rows a PIT-38 block covers.
        Act: export via GoogleSpreadsheetExporter and reload the written CSV.
        Assert: the CSV holds exactly one row per DataFrame row.

        The PIT-38 declaration figures are terminal/log output only. Appending
        them to the CSV as a footer row would break OUTPUT_CSV_SCHEMA, which
        requires non-null Date/Ticker and a float Shares with ``coerce=False``.
        This test fails loudly if anyone wires the block into the export.
        """
        monkeypatch.chdir(tmp_path)

        df = pd.DataFrame(
            {
                "Date": ["2025-02-21", "2025-05-29", "2025-08-19"],
                "Ticker": ["TXT.PL", "ASB.PL", "NOVOB.DK"],
                "Shares": [17.0, 85.0, 13.0],
                "Net Dividend": ["28.22 PLN", "25.50 USD", "48.75 DKK"],
                "Tax Collected %": ["19%", "-", "27%"],
                "Tax Amount PLN": ["-", "18.15 PLN", "-"],
            }
        )

        GoogleSpreadsheetExporter(df.copy()).export_to_google()

        loaded = pd.read_csv(
            tmp_path / "output" / "for_google_spreadsheet.csv", sep="\t"
        )

        assert len(loaded) == len(df)
        OUTPUT_CSV_SCHEMA.validate(loaded, lazy=True)
