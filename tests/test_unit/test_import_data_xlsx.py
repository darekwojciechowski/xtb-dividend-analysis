"""Tests for import_and_process_data."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from data_processing.import_data_xlsx import import_and_process_data


@pytest.mark.unit
class TestImportAndProcessData:
    """Tests for import_and_process_data."""

    def test_returns_none_tuple_when_file_not_found(self, tmp_path: Path) -> None:
        missing = tmp_path / "ghost.xlsx"

        df, currency = import_and_process_data(missing)

        assert df is None
        assert currency is None

    def test_returns_none_tuple_when_empty_data_error(self, tmp_path: Path) -> None:
        # Covers line 65: pd.errors.EmptyDataError branch
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()

        with (
            patch("data_processing.import_data_xlsx.openpyxl.load_workbook") as mock_wb,
            patch(
                "data_processing.import_data_xlsx.pd.read_excel",
                side_effect=pd.errors.EmptyDataError,
            ),
        ):
            mock_ws = MagicMock()
            mock_ws.__getitem__.return_value.value = "USD"
            mock_wb.return_value.__getitem__.return_value = mock_ws

            df, currency = import_and_process_data(xlsx)

        assert df is None
        assert currency is None

    def test_returns_none_tuple_on_generic_exception(self, tmp_path: Path) -> None:
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()

        with patch(
            "data_processing.import_data_xlsx.openpyxl.load_workbook",
            side_effect=RuntimeError("unexpected"),
        ):
            df, currency = import_and_process_data(xlsx)

        assert df is None
        assert currency is None
