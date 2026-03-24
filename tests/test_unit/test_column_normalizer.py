"""Unit tests for ColumnNormalizer.

Covers column-name resolution (English vs. Polish), full DataFrame
normalization from Polish to English column names, and column dropping.

Test classes:
    TestGetColumnName        — English present, Polish present, neither → ValueError
    TestNormalizeColumnNames — Polish input, English input, missing columns → KeyError
    TestDropColumns          — happy path, empty DataFrame, missing column → ValueError

All tests are marked ``@pytest.mark.unit``.
"""

from __future__ import annotations

import pandas as pd
import pytest

from data_processing.column_normalizer import ColumnNormalizer
from data_processing.constants import ColumnName

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _english_df() -> pd.DataFrame:
    """Return a DataFrame with standard English column names."""
    return pd.DataFrame(
        {
            "Time": ["2024-01-15"],
            "Symbol": ["SBUX.US"],
            "Comment": ["USD 0.57/ SHR"],
            "Amount": [10.0],
            "Type": ["Dividend"],
            "ID": [1],
        }
    )


def _polish_df() -> pd.DataFrame:
    """Return a DataFrame with Polish column names (XTB PL statement)."""
    return pd.DataFrame(
        {
            "Czas": ["2024-01-15"],
            "Ticker": ["SBUX.US"],
            "Komentarz": ["USD 0.57/ SHR"],
            "Kwota": [10.0],
            "Typ": ["Dividend"],
            "ID": [1],
        }
    )


# ---------------------------------------------------------------------------
# TestGetColumnName
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetColumnName:
    """Tests for ColumnNormalizer.get_column_name."""

    def test_get_column_name_when_english_present_then_returns_english(self) -> None:
        """Returns English name when the English column exists in the DataFrame."""
        # Arrange
        df = pd.DataFrame({"Time": [], "Czas": []})
        normalizer = ColumnNormalizer(df)

        # Act
        result = normalizer.get_column_name("Time", "Czas")

        # Assert
        assert result == "Time"

    def test_get_column_name_when_only_polish_present_then_returns_polish(
        self,
    ) -> None:
        """Returns Polish name when only the Polish column is in the DataFrame."""
        # Arrange
        df = pd.DataFrame({"Czas": []})
        normalizer = ColumnNormalizer(df)

        # Act
        result = normalizer.get_column_name("Time", "Czas")

        # Assert
        assert result == "Czas"

    def test_get_column_name_when_neither_present_then_raises_value_error(
        self,
    ) -> None:
        """Raises ValueError when neither column name is found."""
        # Arrange
        df = pd.DataFrame({"UnrelatedCol": []})
        normalizer = ColumnNormalizer(df)

        # Act / Assert
        with pytest.raises(ValueError, match="Time"):
            normalizer.get_column_name("Time", "Czas")

    def test_get_column_name_error_message_mentions_both_names(self) -> None:
        """ValueError message includes both the English and Polish names."""
        # Arrange
        df = pd.DataFrame({"Unrelated": []})
        normalizer = ColumnNormalizer(df)

        # Act / Assert
        with pytest.raises(ValueError, match="Czas"):
            normalizer.get_column_name("Time", "Czas")


# ---------------------------------------------------------------------------
# TestNormalizeColumnNames
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeColumnNames:
    """Tests for ColumnNormalizer.normalize_column_names."""

    def test_normalize_when_english_columns_then_retains_standard_names(
        self,
    ) -> None:
        """English-input DataFrame keeps its columns renamed to ColumnName enum values."""
        # Arrange
        normalizer = ColumnNormalizer(_english_df())

        # Act
        result = normalizer.normalize_column_names()

        # Assert
        assert ColumnName.DATE.value in result.columns
        assert ColumnName.TICKER.value in result.columns
        assert ColumnName.COMMENT.value in result.columns
        assert ColumnName.AMOUNT.value in result.columns
        assert ColumnName.TYPE.value in result.columns

    def test_normalize_when_polish_columns_then_maps_to_english_names(self) -> None:
        """Polish-column DataFrame is fully remapped to English ColumnName enum values."""
        # Arrange
        normalizer = ColumnNormalizer(_polish_df())

        # Act
        result = normalizer.normalize_column_names()

        # Assert
        assert ColumnName.DATE.value in result.columns
        assert ColumnName.TICKER.value in result.columns
        assert ColumnName.COMMENT.value in result.columns
        assert ColumnName.AMOUNT.value in result.columns
        assert ColumnName.TYPE.value in result.columns

    def test_normalize_when_polish_columns_then_polish_names_removed(self) -> None:
        """After normalization, original Polish column names are gone."""
        # Arrange
        normalizer = ColumnNormalizer(_polish_df())

        # Act
        result = normalizer.normalize_column_names()

        # Assert
        assert "Czas" not in result.columns
        assert "Komentarz" not in result.columns
        assert "Kwota" not in result.columns
        assert "Typ" not in result.columns

    def test_normalize_when_missing_column_then_raises_value_error(self) -> None:
        """Missing required column raises ValueError."""
        # Arrange
        df = pd.DataFrame({"Time": [], "Symbol": [], "Comment": [], "Amount": []})
        # 'Type' column is intentionally absent
        normalizer = ColumnNormalizer(df)

        # Act / Assert
        with pytest.raises(ValueError):
            normalizer.normalize_column_names()

    def test_normalize_returns_dataframe(self) -> None:
        """Return value is always a DataFrame."""
        # Arrange
        normalizer = ColumnNormalizer(_english_df())

        # Act
        result = normalizer.normalize_column_names()

        # Assert
        assert isinstance(result, pd.DataFrame)

    def test_normalize_preserves_row_count(self) -> None:
        """Number of rows is unchanged after normalization."""
        # Arrange
        df = _english_df()
        normalizer = ColumnNormalizer(df)

        # Act
        result = normalizer.normalize_column_names()

        # Assert
        assert len(result) == len(df)


# ---------------------------------------------------------------------------
# TestDropColumns
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDropColumns:
    """Tests for ColumnNormalizer.drop_columns."""

    def test_drop_when_columns_present_then_removed(self) -> None:
        """Specified columns are absent from the returned DataFrame."""
        # Arrange
        df = pd.DataFrame({"ID": [1, 2], "Comment": ["a", "b"], "Amount": [1.0, 2.0]})
        normalizer = ColumnNormalizer(df)

        # Act
        result = normalizer.drop_columns(["ID", "Comment"])

        # Assert
        assert "ID" not in result.columns
        assert "Comment" not in result.columns

    def test_drop_when_columns_present_then_other_columns_retained(self) -> None:
        """Columns not listed are kept intact."""
        # Arrange
        df = pd.DataFrame({"ID": [1], "Comment": ["x"], "Amount": [5.0]})
        normalizer = ColumnNormalizer(df)

        # Act
        result = normalizer.drop_columns(["ID"])

        # Assert
        assert "Amount" in result.columns

    def test_drop_when_empty_dataframe_then_raises_value_error(self) -> None:
        """Raises ValueError on an empty DataFrame."""
        # Arrange
        normalizer = ColumnNormalizer(pd.DataFrame())

        # Act / Assert
        with pytest.raises(ValueError, match="empty"):
            normalizer.drop_columns(["ID"])

    def test_drop_when_column_missing_then_raises_value_error(self) -> None:
        """Raises ValueError listing the missing column name."""
        # Arrange
        df = pd.DataFrame({"Amount": [1.0]})
        normalizer = ColumnNormalizer(df)

        # Act / Assert
        with pytest.raises(ValueError, match="NonExistentCol"):
            normalizer.drop_columns(["NonExistentCol"])

    def test_drop_returns_dataframe(self) -> None:
        """Return type is always pd.DataFrame."""
        # Arrange
        df = pd.DataFrame({"ID": [1], "Amount": [1.0]})
        normalizer = ColumnNormalizer(df)

        # Act
        result = normalizer.drop_columns(["ID"])

        # Assert
        assert isinstance(result, pd.DataFrame)
