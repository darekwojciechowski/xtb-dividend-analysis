"""Export functionality integration tests.

Tests the export pipeline that converts processed DataFrame into
Google Sheets compatible CSV format.

Uses the ``processed_pln_result`` module-scoped fixture from conftest so the
full pipeline runs only once per module — individual tests then inspect the
exported artefact.

Test Coverage:
    - CSV file is created with tab separator and UTF-8 encoding
    - Google Sheets compatibility (tab separator, no ANSI codes)
    - Numeric columns are rounded to two decimal places
    - Column order matches the processed DataFrame
    - No NaN / empty cells in exported file (replaced with 0)
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from data_processing.constants import ColumnName
from data_processing.exporter import GoogleSpreadsheetExporter

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_ANSI_PATTERN: re.Pattern[str] = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
_OUTPUT_FILENAME: str = "test_export_output.csv"

# Required columns that must survive the export trip.
# Currency is not emitted by the pipeline for PLN statements.
_REQUIRED_EXPORT_COLUMNS: frozenset[str] = frozenset(
    {
        ColumnName.TICKER.value,
        ColumnName.DATE.value,
        ColumnName.NET_DIVIDEND.value,
        ColumnName.TAX_AMOUNT_PLN.value,
    }
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run_export_to_tempdir(
    processed_pln_result: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    """Run GoogleSpreadsheetExporter and return the path to the generated file.

    Changes the working directory to ``tmp_path`` so ``output/`` is created
    inside the temporary directory, leaving the real workspace clean.

    Args:
        processed_pln_result: Fully processed DataFrame from the pipeline.
        monkeypatch: pytest monkeypatch fixture for cwd override.
        tmp_path: pytest built-in temporary directory.

    Returns:
        ``Path`` pointing to the written CSV file.
    """
    monkeypatch.chdir(tmp_path)
    exporter = GoogleSpreadsheetExporter(processed_pln_result.copy())
    exporter.export_to_google(_OUTPUT_FILENAME)
    return tmp_path / "output" / _OUTPUT_FILENAME


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.integration
def test_export_creates_tab_separated_utf8_csv(
    processed_pln_result: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that export_to_google() produces a tab-separated UTF-8 file on disk.

    Given: Fully processed PLN statement DataFrame from the pipeline
    When:  ``GoogleSpreadsheetExporter.export_to_google()`` is called
    Then:
        - The output file exists on disk
        - First line (header) contains tab characters
        - File is readable as UTF-8 without errors
        - File contains at least one data row beyond the header

    Args:
        processed_pln_result: Module-scoped fixture with fully processed DataFrame.
        monkeypatch: pytest fixture to override the working directory.
        tmp_path: pytest built-in temporary directory fixture.
    """
    # Arrange
    csv_path = _run_export_to_tempdir(processed_pln_result, monkeypatch, tmp_path)

    # Act
    raw_content = csv_path.read_text(encoding="utf-8")
    lines = [line for line in raw_content.splitlines() if line.strip()]

    # Assert
    assert csv_path.exists(), "Export must create the output CSV file"
    assert "\t" in lines[0], "Header row must use tab as column separator"
    assert len(lines) > 1, "CSV must contain at least one data row beyond the header"


@pytest.mark.slow
@pytest.mark.integration
def test_export_csv_contains_no_ansi_codes(
    processed_pln_result: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that the exported CSV contains no ANSI terminal escape sequences.

    Google Sheets cannot handle ANSI color codes; they must be stripped
    from the ``Ticker`` column before export.

    Given: Fully processed PLN statement DataFrame (Ticker column may have ANSI codes)
    When:  ``GoogleSpreadsheetExporter.export_to_google()`` is called
    Then:  No ANSI escape sequences appear anywhere in the output file

    Args:
        processed_pln_result: Module-scoped fixture with fully processed DataFrame.
        monkeypatch: pytest fixture to override the working directory.
        tmp_path: pytest built-in temporary directory fixture.
    """
    # Arrange
    csv_path = _run_export_to_tempdir(processed_pln_result, monkeypatch, tmp_path)

    # Act
    raw_content = csv_path.read_text(encoding="utf-8")

    # Assert
    assert not _ANSI_PATTERN.search(raw_content), (
        "Exported CSV must not contain ANSI escape sequences"
    )


@pytest.mark.slow
@pytest.mark.integration
def test_export_required_columns_present(
    processed_pln_result: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that all required columns survive the export round-trip.

    Given: Fully processed PLN statement DataFrame
    When:  CSV is written and read back via pandas
    Then:  All columns from ``_REQUIRED_EXPORT_COLUMNS`` are present in the CSV

    Args:
        processed_pln_result: Module-scoped fixture with fully processed DataFrame.
        monkeypatch: pytest fixture to override the working directory.
        tmp_path: pytest built-in temporary directory fixture.
    """
    # Arrange
    csv_path = _run_export_to_tempdir(processed_pln_result, monkeypatch, tmp_path)

    # Act
    df_exported = pd.read_csv(csv_path, sep="\t", encoding="utf-8")

    # Assert
    missing = _REQUIRED_EXPORT_COLUMNS - set(df_exported.columns)
    assert not missing, f"Exported CSV is missing required columns: {missing}"


@pytest.mark.slow
@pytest.mark.integration
def test_export_numeric_columns_rounded_to_two_decimal_places(
    processed_pln_result: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that numeric columns are rounded to exactly two decimal places on export.

    Given: Fully processed PLN statement DataFrame with floating-point values
    When:  ``GoogleSpreadsheetExporter.export_to_google()`` is called
    Then:  Every numeric cell in the CSV has at most two decimal places

    Args:
        processed_pln_result: Module-scoped fixture with fully processed DataFrame.
        monkeypatch: pytest fixture to override the working directory.
        tmp_path: pytest built-in temporary directory fixture.
    """
    # Arrange
    csv_path = _run_export_to_tempdir(processed_pln_result, monkeypatch, tmp_path)

    # Act
    df_exported = pd.read_csv(csv_path, sep="\t", encoding="utf-8")
    numeric_cols = df_exported.select_dtypes(include=["number"]).columns

    # Assert
    for col in numeric_cols:
        values = df_exported[col].dropna()
        decimal_counts = values.apply(
            lambda v: len(str(v).split(".")[-1]) if "." in str(v) else 0
        )
        assert (decimal_counts <= 2).all(), (
            f"Column '{col}' contains values with more than 2 decimal places:\n"
            f"{values[decimal_counts > 2]}"
        )


@pytest.mark.slow
@pytest.mark.integration
def test_export_no_nan_values_in_output(
    processed_pln_result: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that no NaN values appear in the exported CSV (replaced with 0).

    ``GoogleSpreadsheetExporter`` calls ``fillna(0)`` before writing; pasting
    empty cells into Google Sheets causes formula errors.

    Given: Fully processed PLN statement DataFrame
    When:  CSV is written and read back via pandas
    Then:  No NaN values exist in any column of the exported CSV

    Args:
        processed_pln_result: Module-scoped fixture with fully processed DataFrame.
        monkeypatch: pytest fixture to override the working directory.
        tmp_path: pytest built-in temporary directory fixture.
    """
    # Arrange
    csv_path = _run_export_to_tempdir(processed_pln_result, monkeypatch, tmp_path)

    # Act
    df_exported = pd.read_csv(csv_path, sep="\t", encoding="utf-8")

    # Assert
    nan_summary = df_exported.isna().sum()
    cols_with_nans = nan_summary[nan_summary > 0]
    assert cols_with_nans.empty, (
        f"Exported CSV must not contain NaN values, found:\n{cols_with_nans}"
    )


@pytest.mark.slow
@pytest.mark.integration
def test_export_column_order_matches_dataframe(
    processed_pln_result: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that the column order in the exported CSV matches the processed DataFrame.

    Given: Fully processed PLN statement DataFrame with defined column sequence
    When:  CSV is written and read back via pandas
    Then:
        - CSV column list matches the DataFrame column list (after ``Tax Collected``
          is dropped when ``Tax Collected %`` is present — same as exporter logic)
        - ``Date`` appears as the first column

    Args:
        processed_pln_result: Module-scoped fixture with fully processed DataFrame.
        monkeypatch: pytest fixture to override the working directory.
        tmp_path: pytest built-in temporary directory fixture.
    """
    # Arrange
    source_df = processed_pln_result.copy()

    # Replicate the exporter's column-drop logic to derive expected columns
    if (
        ColumnName.TAX_COLLECTED.value in source_df.columns
        and ColumnName.TAX_COLLECTED_PCT.value in source_df.columns
    ):
        source_df = source_df.drop(columns=[ColumnName.TAX_COLLECTED.value])

    expected_columns = list(source_df.columns)
    csv_path = _run_export_to_tempdir(processed_pln_result, monkeypatch, tmp_path)

    # Act
    df_exported = pd.read_csv(csv_path, sep="\t", encoding="utf-8")

    # Assert
    assert list(df_exported.columns) == expected_columns, (
        f"Exported column order does not match.\n"
        f"Expected: {expected_columns}\n"
        f"Got:      {list(df_exported.columns)}"
    )
    assert df_exported.columns[0] == ColumnName.DATE.value, (
        f"First column must be '{ColumnName.DATE.value}', "
        f"got '{df_exported.columns[0]}'"
    )
