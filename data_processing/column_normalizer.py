"""Column normalization and multilingual support for XTB statements.

This module handles column name normalization and language detection
for both Polish and English XTB broker statements.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from .constants import ColumnName


class ColumnNormalizer:
    """Handles column name normalization and multilingual column management.

    Supports both Polish and English XTB broker statement formats,
    normalizing column names to a standard English format.
    """

    def __init__(self, df: pd.DataFrame):
        """Initialize ColumnNormalizer with a DataFrame.

        Args:
            df: DataFrame to normalize.
        """
        self.df = df

    def get_column_name(self, english_name: str, polish_name: str) -> str:
        """Get the correct column name based on available columns in the DataFrame.

        Args:
            english_name: The English name of the column.
            polish_name: The Polish name of the column.

        Returns:
            The column name present in the DataFrame.

        Raises:
            ValueError: If neither column name is found.
        """
        if english_name in self.df.columns:
            return english_name
        elif polish_name in self.df.columns:
            return polish_name
        else:
            raise ValueError(
                f"Neither '{english_name}' nor '{polish_name}' column found in the DataFrame."
            )

    def normalize_column_names(self) -> pd.DataFrame:
        """Normalize column names to English standard names based on detected language.

        Maps Polish or English column names to standardized English names.

        Returns:
            DataFrame with normalized column names.
        """
        column_mapping = {
            self.get_column_name("Time", "Czas"): ColumnName.DATE.value,
            self.get_column_name("Symbol", "Ticker"): ColumnName.TICKER.value,
            self.get_column_name("Comment", "Komentarz"): ColumnName.COMMENT.value,
            self.get_column_name("Amount", "Kwota"): ColumnName.AMOUNT.value,
            self.get_column_name("Type", "Typ"): ColumnName.TYPE.value,
        }

        missing_columns = [
            col for col in column_mapping.keys() if col not in self.df.columns
        ]
        if missing_columns:
            raise KeyError(
                f"The following columns are missing in the DataFrame: {', '.join(missing_columns)}"
            )

        self.df = self.df.rename(columns=column_mapping)
        logger.info("Step 2 - Normalized column names to English standard.")

        return self.df

    def drop_columns(self, columns: list[str]) -> pd.DataFrame:
        """Drop specified columns from the DataFrame.

        Args:
            columns: List of column names to be dropped.

        Returns:
            DataFrame with specified columns removed.

        Raises:
            ValueError: If DataFrame is empty or columns are missing.
        """
        if self.df is None or self.df.empty:
            raise ValueError("Error: The DataFrame is empty or has not been loaded.")

        missing_columns = [col for col in columns if col not in self.df.columns]
        if missing_columns:
            raise ValueError(f"Error: Missing columns: {', '.join(missing_columns)}")

        self.df = self.df.drop(columns=columns)
        return self.df
