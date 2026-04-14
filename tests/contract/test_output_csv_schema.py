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
