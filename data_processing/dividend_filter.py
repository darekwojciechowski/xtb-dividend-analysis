"""Dividend data filtering and aggregation.

This module handles filtering dividend-related transactions
and grouping dividend data.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from .constants import ColumnName


class DividendFilter:
    """Filters and groups dividend-related transactions from XTB statements.

    Handles filtering of dividend and withholding tax transactions,
    and groups data by date, ticker, and type.
    """

    def __init__(self, df: pd.DataFrame):
        """Initialize DividendFilter with a DataFrame.

        Args:
            df: DataFrame containing transaction data.
        """
        self.df = df

    def filter_dividends(self) -> pd.DataFrame:
        """Filter DataFrame to include only dividend-related transactions.

        Includes rows where Type is 'Dividend', 'Dywidenda', 'DIVIDENT',
        'Withholding Tax', or 'Podatek od dywidend'.

        Returns:
            Filtered DataFrame with only dividend data.
        """
        type_col = ColumnName.TYPE.value

        self.df = self.df[self.df[type_col].notna()]
        self.df = self.df[
            self.df[type_col].isin(
                [
                    "Dividend",
                    "Dywidenda",
                    "DIVIDENT",
                    "Withholding Tax",
                    "Podatek od dywidend",
                ]
            )
        ]
        logger.info("Step 3 - Filtered rows to include only dividend-related data.")

        return self.df

    def group_by_dividends(self) -> pd.DataFrame:
        """Group DataFrame by Date, Ticker, and Type, aggregating Amount.

        Groups dividend transactions and sums amounts for each unique
        combination of date, ticker, type, and comment.

        Returns:
            Grouped DataFrame with aggregated amounts.
        """
        self.df = (
            self.df.groupby([
                ColumnName.DATE.value,
                ColumnName.TICKER.value,
                ColumnName.TYPE.value,
                ColumnName.COMMENT.value,
            ])
            .agg({ColumnName.AMOUNT.value: "sum"})
            .reset_index()
        )
        self.df.rename(
            columns={ColumnName.AMOUNT.value: ColumnName.NET_DIVIDEND.value}, inplace=True)
        logger.info(
            "Step 4 - Grouped data by date, ticker, and type; aggregated amounts."
        )

        return self.df
