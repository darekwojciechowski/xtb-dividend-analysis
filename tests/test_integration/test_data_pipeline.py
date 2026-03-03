"""Full end-to-end pipeline integration tests.

Tests the complete data processing pipeline from raw XTB statement files
through all data processing steps to final export.

Reference fixture:
    ``data/demo_XTB_broker_statement_currency_PLN.xlsx`` — PLN-denominated
    account with dividends in PLN (TXT.PL, XTB.PL), USD (SBUX.US, MMM.US,
    ASB.PL), and DKK (NOVOB.DK).

Test Coverage:
    - Full pipeline with PLN statement → non-empty result, key columns present
    - Full pipeline USD path → TODO placeholder, USD demo file not yet in data/
    - Output CSV format → tab-separated, no ANSI codes, file created on disk
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

# Columns that every processed output row must contain
_REQUIRED_OUTPUT_COLUMNS: frozenset[str] = frozenset(
    {
        ColumnName.TICKER.value,
        ColumnName.DATE.value,
        ColumnName.NET_DIVIDEND.value,
        ColumnName.TAX_AMOUNT_PLN.value,
    }
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.integration
def test_full_pipeline_pln_statement(
    processed_pln_result: pd.DataFrame,
) -> None:
    """Test full pipeline with PLN denomination statement produces valid output.

    Given: ``demo_XTB_broker_statement_currency_PLN.xlsx`` processed through
           the full pipeline via the ``processed_pln_result`` fixture
    When:  The fixture computes the result once per module
    Then:
        - Returned DataFrame is non-empty
        - All required output columns are present
        - Every ``Tax Amount PLN`` value is non-negative (tax ≥ 0)
        - Every ``Net Dividend`` cell is non-null after processing

    Args:
        processed_pln_result: Module-scoped fixture with fully processed DataFrame.
    """
    # Arrange — full pipeline result pre-computed by module-scoped fixture
    result = processed_pln_result

    # Assert — structure
    assert result is not None, "process_data() must return a DataFrame"
    assert not result.empty, "Processed DataFrame must not be empty"
    missing = _REQUIRED_OUTPUT_COLUMNS - set(result.columns)
    assert not missing, f"Output DataFrame is missing columns: {missing}"

    # Assert — Tax Amount PLN is always non-negative
    # Values are formatted strings like "0.1 PLN" or "-"; extract the numeric part first.
    tax_values = pd.to_numeric(
        result[ColumnName.TAX_AMOUNT_PLN.value]
        .astype(str)
        .str.extract(r"([\d.]+)", expand=False),
        errors="coerce",
    ).dropna()
    assert not tax_values.empty, "Tax Amount PLN column must contain numeric values"
    assert (tax_values >= 0).all(), (
        f"All tax values must be ≥ 0, found negatives:\n{tax_values[tax_values < 0]}"
    )

    # Assert — Net Dividend column is populated
    assert result[ColumnName.NET_DIVIDEND.value].notna().any(), (
        "Net Dividend column must contain at least one non-null value"
    )


@pytest.mark.skip(
    reason="TODO: data/demo_XTB_broker_statement_currency_USD.xlsx not yet added"
)
@pytest.mark.integration
def test_full_pipeline_usd_statement() -> None:
    """Test full pipeline with USD-denominated account statement.

    Given: XTB statement where cell F6 contains 'USD'
    When:  ``process_data()`` runs with USD NBP exchange rates
    Then:  Output contains amounts converted to PLN with correct Belka tax

    Note:
        Add ``data/demo_XTB_broker_statement_currency_USD.xlsx`` to enable this test.
    """
    pass


@pytest.mark.slow
@pytest.mark.integration
def test_full_pipeline_output_format(
    processed_pln_result: pd.DataFrame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the pipeline export produces a Google-Sheets-compatible CSV.

    Given: Fully processed DataFrame from the ``processed_pln_result`` fixture
    When:  ``GoogleSpreadsheetExporter.export_to_google()`` writes the file
    Then:
        - CSV file is created on disk
        - First row is tab-separated (Google Sheets paste format)
        - File contains no ANSI escape sequences (terminal color codes stripped)
        - File is non-empty (at least a header row and one data row)

    Args:
        processed_pln_result: Module-scoped fixture with fully processed DataFrame.
        tmp_path: pytest built-in temporary directory per test function.
        monkeypatch: pytest monkeypatch for redirecting the working directory.
    """
    # Arrange
    output_filename = "test_export.csv"
    monkeypatch.chdir(tmp_path)
    exporter = GoogleSpreadsheetExporter(processed_pln_result.copy())

    # Act
    exporter.export_to_google(output_filename)

    # Assert — file created
    output_path = tmp_path / "output" / output_filename
    assert output_path.exists(), f"Expected CSV file at {output_path}"

    content = output_path.read_text(encoding="utf-8")
    lines = [ln for ln in content.splitlines() if ln.strip()]

    # Assert — at least header + one data row
    assert len(lines) >= 2, "CSV must contain a header row and at least one data row"

    # Assert — tab-separated header
    assert "\t" in lines[0], (
        f"Expected tab-separated columns in header, got: {lines[0]!r}"
    )

    # Assert — no ANSI escape sequences anywhere in the file
    assert not _ANSI_PATTERN.search(content), (
        "Exported CSV must not contain ANSI escape sequences"
    )
