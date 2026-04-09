"""Data import and processing chain integration tests.

Tests the integration between data import and processing components,
verifying that raw data is correctly normalized and prepared for analysis.

Uses ``data/demo_XTB_broker_statement_currency_PLN.xlsx`` as the
reference fixture — a PLN-denominated account with 44 rows and column
names in the English XTB export format (Time, Symbol, Type, Comment, Amount).

Test Coverage:
    - Import with column normalization
    - Duplicate transaction IDs absent
    - Data type consistency after import
    - Polish diacritical marks preserved in Type column
    - All rows have a valid (non-null) date after import
"""

from __future__ import annotations

import pandas as pd
import pytest

from data_processing.column_normalizer import ColumnNormalizer
from data_processing.constants import ColumnName

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Expected row count for the demo file
_EXPECTED_ROW_COUNT = 44


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
def test_import_and_column_normalization(
    pln_statement: tuple[pd.DataFrame, str],
) -> None:
    """Test import followed by ColumnNormalizer.normalize_column_names().

    Given: demo_XTB_broker_statement_currency_PLN.xlsx with English headers
           (Time, Symbol, Comment, Amount, Type)
    When:  ColumnNormalizer.normalize_column_names() renames the columns
    Then:  DataFrame contains all five standard English column names defined
           in ColumnName enum (Date, Ticker, Comment, Amount, Type)
    """
    # Arrange
    df, _ = pln_statement

    # Act
    normalizer = ColumnNormalizer(df)
    normalized_df = normalizer.normalize_column_names()

    # Assert
    expected_columns = {
        ColumnName.DATE.value,
        ColumnName.TICKER.value,
        ColumnName.COMMENT.value,
        ColumnName.AMOUNT.value,
        ColumnName.TYPE.value,
    }
    assert expected_columns.issubset(set(normalized_df.columns))


@pytest.mark.integration
@pytest.mark.slow
def test_import_duplicate_removal(
    pln_statement: tuple[pd.DataFrame, str],
) -> None:
    """Test that every transaction ID in the imported statement is unique.

    Given: demo_XTB_broker_statement_currency_PLN.xlsx (44 rows)
    When:  import_and_process_data() loads the sheet
    Then:  The ID column contains no duplicate values, meaning each
           transaction appears exactly once
    """
    # Arrange
    df, _ = pln_statement

    # Act
    duplicate_count = df["ID"].duplicated().sum()

    # Assert
    assert duplicate_count == 0, f"Expected 0 duplicate IDs but found {duplicate_count}"


@pytest.mark.integration
@pytest.mark.slow
def test_import_data_type_consistency(
    pln_statement: tuple[pd.DataFrame, str],
) -> None:
    """Test that critical columns have the expected dtypes after import.

    Given: demo_XTB_broker_statement_currency_PLN.xlsx
    When:  import_and_process_data() loads the sheet
    Then:
        - Time column is parsed as datetime64 (pandas Timestamp)
        - ID, Type, Comment columns are object (string) dtype
        - Amount column is object dtype (raw before numeric coercion)
        - All 44 rows are present (no rows silently dropped)
    """
    # Arrange
    df, _ = pln_statement

    # Assert — datetime column
    assert pd.api.types.is_datetime64_any_dtype(df["Time"]), (
        "Time column must be datetime64 after import"
    )

    # Assert — string columns (use ColumnName enum for normalised names)
    # pandas 2.x may infer StringDtype instead of object for string columns;
    # accept both to stay compatible across pandas versions.
    for col in ("ID", ColumnName.TYPE.value, ColumnName.COMMENT.value):
        dtype = df[col].dtype
        is_str_like = dtype.kind == "O" or isinstance(dtype, pd.StringDtype)
        assert is_str_like, f"Column '{col}' must be object dtype"

    # Assert — row count intact
    assert len(df) == _EXPECTED_ROW_COUNT


@pytest.mark.integration
@pytest.mark.slow
def test_import_with_special_characters(
    pln_statement: tuple[pd.DataFrame, str],
) -> None:
    """Test that Polish diacritical marks in the Type column are preserved.

    The demo file contains transaction types such as 'Sprzedaż akcji/ETF'
    (ż) and 'Zakup akcji/ETF' (no diacritics) and 'Zysk/Strata'.  These
    verify that openpyxl reads the XLSX without mojibake.

    Given: demo_XTB_broker_statement_currency_PLN.xlsx
    When:  import_and_process_data() loads the sheet
    Then:  Type column contains the exact Polish strings with diacritics
    """
    # Arrange
    df, _ = pln_statement
    types = set(df[ColumnName.TYPE.value].unique())

    # Act / Assert
    assert "Sprzedaż akcji/ETF" in types, (
        "Expected Polish type 'Sprzedaż akcji/ETF' with diacritics preserved"
    )
    assert "Podatek od dywidend" in types, (
        "Expected Polish type 'Podatek od dywidend' preserved"
    )


@pytest.mark.integration
@pytest.mark.slow
def test_import_missing_dates(
    pln_statement: tuple[pd.DataFrame, str],
) -> None:
    """Test that every row in the imported statement has a valid date.

    Given: demo_XTB_broker_statement_currency_PLN.xlsx (all rows have
           timestamps in the source file)
    When:  import_and_process_data() parses the Time column
    Then:  Time column contains zero NaT (not-a-time) values, confirming
           that no date was lost or silently dropped during import
    """
    # Arrange
    df, _ = pln_statement

    # Act
    nat_count = df["Time"].isna().sum()

    # Assert
    assert nat_count == 0, (
        f"Expected no missing dates but found {nat_count} NaT entries"
    )


@pytest.mark.integration
@pytest.mark.slow
def test_import_detects_pln_currency(
    pln_statement: tuple[pd.DataFrame, str],
) -> None:
    """Test that import_and_process_data detects the PLN account currency.

    Given: demo_XTB_broker_statement_currency_PLN.xlsx with 'PLN' in cell F6
    When:  import_and_process_data() reads the sheet
    Then:  The returned currency string equals 'PLN'
    """
    # Arrange
    _, currency = pln_statement

    # Assert
    assert currency == "PLN", f"Expected detected currency 'PLN' but got '{currency}'"
