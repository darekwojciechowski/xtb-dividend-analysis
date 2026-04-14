"""Contract test: the raw XTB XLSX export still matches our expected schema.

Red signal: XTB has renamed, dropped, reordered or retyped a column in the
``CASH OPERATION HISTORY`` sheet. The downstream pipeline would still run but
silently corrupt numbers — this test is the tripwire.
"""

from __future__ import annotations

from pathlib import Path

import pandera.pandas as pa
import pytest

from data_processing.import_data_xlsx import import_and_process_data

from .schemas import DIVIDEND_ROWS_SCHEMA, DIVIDEND_TYPES, INPUT_XLSX_SCHEMA

pytestmark = pytest.mark.contract


class TestInputXlsxSchema:
    def test_raw_xlsx_matches_structural_schema(self, demo_xlsx_path: Path) -> None:
        """Arrange: the demo XLSX fixture from the test suite.
        Act: load it through import_and_process_data.
        Assert: the resulting DataFrame satisfies INPUT_XLSX_SCHEMA and the
        detected currency is "PLN".
        """
        df, currency = import_and_process_data(demo_xlsx_path)

        assert df is not None
        assert currency == "PLN"
        INPUT_XLSX_SCHEMA.validate(df, lazy=True)

    def test_dividend_subset_matches_dividend_schema(
        self, demo_xlsx_path: Path
    ) -> None:
        """Arrange: the demo XLSX loaded into a DataFrame.
        Act: filter to dividend-type rows.
        Assert: the subset satisfies DIVIDEND_ROWS_SCHEMA and is non-empty.
        """
        df, _ = import_and_process_data(demo_xlsx_path)
        assert df is not None

        dividends = df[df["Type"].isin(DIVIDEND_TYPES)].reset_index(drop=True)
        assert len(dividends) > 0
        DIVIDEND_ROWS_SCHEMA.validate(dividends, lazy=True)

    def test_structural_schema_rejects_missing_column(
        self, demo_xlsx_path: Path
    ) -> None:
        """Given a valid DataFrame with the ``Symbol`` column removed,
        when INPUT_XLSX_SCHEMA validates it,
        then SchemaErrors is raised.
        """
        df, _ = import_and_process_data(demo_xlsx_path)
        assert df is not None

        broken = df.drop(columns=["Symbol"])

        with pytest.raises(pa.errors.SchemaErrors):
            INPUT_XLSX_SCHEMA.validate(broken, lazy=True)

    def test_dividend_schema_rejects_unknown_transaction_type(
        self, demo_xlsx_path: Path
    ) -> None:
        """Given a dividend DataFrame whose first row has an unrecognised Type value,
        when DIVIDEND_ROWS_SCHEMA validates it,
        then SchemaErrors is raised.
        """
        df, _ = import_and_process_data(demo_xlsx_path)
        assert df is not None

        dividends = df[df["Type"].isin(DIVIDEND_TYPES)].reset_index(drop=True).copy()
        dividends.loc[0, "Type"] = "TotallyNewBrokerEventType"

        with pytest.raises(pa.errors.SchemaErrors):
            DIVIDEND_ROWS_SCHEMA.validate(dividends, lazy=True)
