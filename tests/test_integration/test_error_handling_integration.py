"""Error handling integration tests.

Tests the system's graceful handling of errors and edge cases
across the complete pipeline.

Test Coverage:
    - Missing input file errors
    - Missing exchange rate errors
    - Invalid file format errors
    - Corrupted CSV exchange rate data
    - Partial data recovery from DataFrames with missing values
    - Error logging verification via loguru sink capture
"""

from __future__ import annotations

import textwrap
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import pytest
from loguru import logger

from data_processing.currency_converter import CurrencyConverter
from data_processing.file_paths import get_file_paths
from data_processing.import_data_xlsx import import_and_process_data
from data_processing.tax_calculator import TaxCalculator

if TYPE_CHECKING:
    from collections.abc import Generator

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_NONEXISTENT_PATH = "/tmp/does_not_exist_ever_12345.xlsx"
_FUTURE_DATE_WITH_NO_RATE = "2099-01-01"
_USD = "USD"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def log_capture() -> Generator[StringIO, None, None]:
    """Capture loguru log output into an in-memory buffer.

    Adds a temporary loguru sink for the duration of one test, then removes
    it so other tests are not affected.

    Yields:
        StringIO buffer containing all log messages emitted during the test.
    """
    buffer = StringIO()
    sink_id = logger.add(buffer, format="{level} | {message}", level="DEBUG")
    yield buffer
    logger.remove(sink_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_missing_input_file_graceful_return() -> None:
    """Test that import_and_process_data returns (None, None) for a missing XLSX.

    Given: A path that does not point to any file on disk
    When:  import_and_process_data() is called with that path
    Then:  The function suppresses FileNotFoundError and returns (None, None)
           so callers can distinguish a missing file from a processing failure
           without catching raw exceptions themselves.
    """
    # Arrange
    missing_path = Path(_NONEXISTENT_PATH)

    # Act
    result_df, result_currency = import_and_process_data(missing_path)

    # Assert
    assert result_df is None, (
        f"Expected df=None for a missing file, got: {type(result_df)}"
    )
    assert result_currency is None, (
        f"Expected currency=None for a missing file, got: {result_currency!r}"
    )


@pytest.mark.integration
def test_missing_input_file_raises_in_file_paths() -> None:
    """Test that get_file_paths raises FileNotFoundError for a missing XLSX.

    Given: A path that does not point to any file on disk
    When:  get_file_paths() validates the path
    Then:  FileNotFoundError is raised and its message contains the path so
           users receive an actionable diagnostic.
    """
    # Arrange
    missing_path = _NONEXISTENT_PATH

    # Act / Assert
    with pytest.raises(FileNotFoundError) as exc_info:
        get_file_paths(missing_path)

    assert missing_path in str(exc_info.value), (
        "Expected the error message to include the missing path for diagnostics"
    )


@pytest.mark.integration
def test_missing_exchange_rates_raises_value_error(
    currency_converter: CurrencyConverter,
) -> None:
    """Test that get_exchange_rate raises ValueError when no NBP files contain the date.

    Given: A CurrencyConverter and an empty list of NBP course files
    When:  get_exchange_rate() exhausts all fallback attempts
    Then:  ValueError is raised with a message that names the currency and
           date so the operator knows which archive CSV is missing.

    Args:
        currency_converter: Module-scoped fixture providing a CurrencyConverter
            instance with an empty DataFrame.
    """
    # Arrange
    empty_courses: list[str] = []

    # Act / Assert
    with pytest.raises(ValueError) as exc_info:
        currency_converter.get_exchange_rate(
            empty_courses,
            "2025-03-15",
            _USD,
        )

    error_message = str(exc_info.value)
    assert _USD in error_message, (
        "ValueError message should name the currency that could not be resolved"
    )
    assert "archiwum_tab_a_XXXX.csv" in error_message or "2025-03-15" in error_message, (
        "ValueError message should include the target date for actionable diagnostics"
    )


@pytest.mark.integration
def test_invalid_xlsx_format_graceful_return(tmp_path: Path) -> None:
    """Test that import_and_process_data handles a non-XLSX binary gracefully.

    Given: A file ending in .xlsx but containing arbitrary text (not a valid
           OOXML workbook)
    When:  import_and_process_data() tries to open it
    Then:  The function suppresses the exception and returns (None, None),
           preventing an unhandled crash in the pipeline entry point.

    Args:
        tmp_path: pytest built-in temporary directory fixture (function scope).
    """
    # Arrange
    fake_xlsx = tmp_path / "invalid.xlsx"
    fake_xlsx.write_text("THIS IS NOT A VALID XLSX FILE\nbinary garbage\n\x00\x01")

    # Act
    result_df, result_currency = import_and_process_data(fake_xlsx)

    # Assert
    assert result_df is None, (
        "Expected df=None when the XLSX is corrupted or has wrong format"
    )
    assert result_currency is None, (
        "Expected currency=None when the XLSX is corrupted or has wrong format"
    )


@pytest.mark.integration
def test_corrupted_csv_exchange_rates_skipped_gracefully(
    currency_converter: CurrencyConverter,
    tmp_path: Path,
) -> None:
    """Test that get_exchange_rate skips a CSV without the expected currency column.

    Given: A CSV file that is structurally valid but lacks the ``1USD`` column
           (e.g., an incomplete or differently-formatted archive)
    When:  get_exchange_rate() reads the file
    Then:  The missing column is silently skipped; a ValueError is raised only
           after all files and look-back attempts are exhausted, meaning no
           unhandled exception escapes before the controlled error path fires.

    Args:
        currency_converter: Module-scoped CurrencyConverter fixture.
        tmp_path: pytest built-in temporary directory fixture.
    """
    # Arrange — CSV has a ``data`` column but no ``1USD`` column
    corrupted_csv = tmp_path / "corrupted_rates.csv"
    corrupted_csv.write_text(
        textwrap.dedent("""\
            data;1EUR;1GBP
            20250315;4,2500;5,1000
            20250314;4,2400;5,0900
        """),
        encoding="ISO-8859-1",
    )

    # Act / Assert — must raise ValueError (controlled), not KeyError or AttributeError
    with pytest.raises(ValueError):
        currency_converter.get_exchange_rate(
            [str(corrupted_csv)],
            "2025-03-15",
            _USD,
        )


@pytest.mark.integration
def test_partial_data_recovery_tax_calculator(
    dataframe_with_missing_values: pd.DataFrame,
) -> None:
    """Test that TaxCalculator raises ValueError for missing required columns.

    Given: A DataFrame that is missing the columns required by tax calculation
           (e.g., loaded from partial/broken import)
    When:  calculate_tax_for_pln_statement() validates required columns up front
    Then:  ValueError is raised immediately with a message listing which
           columns are absent, enabling fast failure and clear diagnosis.

    Args:
        dataframe_with_missing_values: Session-scoped fixture from
            tests/conftest.py providing a DataFrame with NaN values and
            no tax-related columns.
    """
    # Arrange — the fixture has no tax-related columns, so validation must fail
    calculator = TaxCalculator(dataframe_with_missing_values)
    # These are the columns that calculate_tax_for_pln_statement requires
    expected_missing = ["Net Dividend", "Tax Collected",
                        "Tax Collected Amount", "Exchange Rate D-1"]

    # Act / Assert — test via the public interface, not the private helper
    with pytest.raises(ValueError) as exc_info:
        calculator.calculate_tax_for_pln_statement("PLN")

    error_message = str(exc_info.value)
    for column in expected_missing:
        assert column in error_message, (
            f"Expected missing column '{column}' to appear in the error message"
        )


@pytest.mark.integration
def test_error_logging_missing_file_writes_to_sink(log_capture: StringIO) -> None:
    """Test that a missing XLSX path is written to the loguru sink at ERROR level.

    Given: A configured loguru sink capturing all log output
    When:  import_and_process_data() is called with a non-existent path
    Then:  At least one ERROR-level log record is emitted and its text
           references the missing file path, confirming observability is intact
           for operator alerting and post-mortem analysis.

    Args:
        log_capture: Function-scoped fixture providing an in-memory StringIO
            loguru sink.
    """
    # Arrange
    missing_path = Path(_NONEXISTENT_PATH)

    # Act
    import_and_process_data(missing_path)
    log_output = log_capture.getvalue()

    # Assert
    assert "ERROR" in log_output, (
        "Expected at least one ERROR-level log entry when the XLSX is missing"
    )
    assert str(missing_path) in log_output, (
        "Expected the missing file path to appear in the ERROR log for diagnostics"
    )


@pytest.mark.integration
def test_error_logging_missing_exchange_rate_file_writes_to_sink(
    log_capture: StringIO,
    currency_converter: CurrencyConverter,
) -> None:
    """Test that a missing NBP CSV path is written to the loguru sink at WARNING level.

    Given: A configured loguru sink and a course path pointing to a non-existent file
    When:  get_exchange_rate() attempts to read the file and fails
    Then:  A WARNING-level log record is emitted naming the missing file,
           so the missing archive can be identified without examining the full stack.

    Args:
        log_capture: Function-scoped fixture providing an in-memory StringIO
            loguru sink.
        currency_converter: Module-scoped CurrencyConverter fixture.
    """
    # Arrange
    ghost_csv = "/tmp/ghost_nbp_archive_99999.csv"

    # Act — get_exchange_rate will eventually raise ValueError after exhausting
    # all look-back attempts; we suppress it here because the assertion target
    # is only the WARNING log emitted per missing file.
    with pytest.raises(ValueError):
        currency_converter.get_exchange_rate([ghost_csv], "2025-06-01", _USD)

    log_output = log_capture.getvalue()

    # Assert
    assert "WARNING" in log_output, (
        "Expected at least one WARNING-level log entry for the missing NBP CSV"
    )
    assert ghost_csv in log_output, (
        "Expected the missing NBP CSV path to appear in the WARNING log"
    )
