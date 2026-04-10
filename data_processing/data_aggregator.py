"""Data aggregation and row merging operations.

This module handles grouping, merging, and aggregation of dividend data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from .constants import ColumnName


class DataAggregator:
    """Handles data aggregation, grouping, and row merging operations.

    Provides methods for preparing columns, merging rows with same date/ticker,
    and aggregating dividend amounts.
    """

    def __init__(self, df: pd.DataFrame):
        """Initialize DataAggregator with a DataFrame.

        Args:
            df: DataFrame to aggregate.
        """
        self.df = df

    def prepare_columns(self) -> pd.DataFrame:
        """Ensure that 'Tax Collected' and 'Net Dividend' columns exist in the DataFrame.

        Returns:
            DataFrame with required columns added if missing.
        """
        if ColumnName.TAX_COLLECTED.value not in self.df.columns:
            self.df[ColumnName.TAX_COLLECTED.value] = np.nan

        if ColumnName.NET_DIVIDEND.value not in self.df.columns:
            self.df[ColumnName.NET_DIVIDEND.value] = np.nan

        return self.df

    def add_empty_column(
        self, col_name: str = "Tax Collected", position: int = 4
    ) -> pd.DataFrame:
        """Add an empty column to the DataFrame if it does not already exist.

        Args:
            col_name: The name of the column to be added. Defaults to 'Tax Collected'.
            position: The position to insert the column. Defaults to 4.

        Returns:
            DataFrame with new column added.
        """
        if col_name not in self.df.columns:
            self.df.insert(position, col_name, pd.NA)

        return self.df

    def convert_columns_to_numeric(self) -> pd.DataFrame:
        """Convert 'Net Dividend' and 'Tax Collected' columns to numeric types.

        Coerces errors to NaN.

        Returns:
            DataFrame with numeric columns.
        """
        self.df[ColumnName.NET_DIVIDEND.value] = pd.to_numeric(
            self.df[ColumnName.NET_DIVIDEND.value], errors="coerce"
        )
        self.df[ColumnName.TAX_COLLECTED.value] = pd.to_numeric(
            self.df[ColumnName.TAX_COLLECTED.value], errors="coerce"
        )

        return self.df

    def move_negative_values(self) -> pd.DataFrame:
        """Move negative values from 'Net Dividend' to 'Tax Collected'.

        Sets the original 'Net Dividend' to NaN after moving.

        Returns:
            DataFrame with negative values moved.
        """
        self.prepare_columns()
        net_div = ColumnName.NET_DIVIDEND.value
        tax_col = ColumnName.TAX_COLLECTED.value
        self.df.loc[self.df[net_div] < 0, tax_col] = self.df[net_div]
        self.df.loc[self.df[net_div] < 0, net_div] = np.nan

        return self.df

    def merge_rows_and_reorder(
        self, drop_columns: list[str] = ["Type", "Comment"]
    ) -> pd.DataFrame:
        """Merge rows in the DataFrame with the same 'Date' and 'Ticker'.

        Removes the specified columns ('Type', 'Comment' by default),
        moves 'Shares' column to the end, and rounds numeric values to 2 decimal places.

        Args:
            drop_columns: A list of columns to drop after merging. Defaults to ['Type', 'Comment'].

        Returns:
            DataFrame with merged rows.

        Note:
            This method should be called after extract_tax_percentage_from_comment() to preserve
            tax percentage values during aggregation.
        """
        # Build aggregation dictionary dynamically based on available columns
        agg_dict = {
            ColumnName.NET_DIVIDEND.value: "sum",
            ColumnName.SHARES.value: "sum",
        }

        # If Tax Collected exists, take first value (they should all be same after extract_tax_percentage_from_comment)
        if ColumnName.TAX_COLLECTED.value in self.df.columns:
            agg_dict[ColumnName.TAX_COLLECTED.value] = "first"

        # If Tax Collected Raw exists (for USD statement), sum the values
        if ColumnName.TAX_COLLECTED_RAW.value in self.df.columns:
            agg_dict[ColumnName.TAX_COLLECTED_RAW.value] = "sum"

        # Merge rows with the same 'Date' and 'Ticker'
        self.df = self.df.groupby(
            [ColumnName.DATE.value, ColumnName.TICKER.value], as_index=False
        ).agg(agg_dict)

        # Drop specified columns (if they exist in the DataFrame)
        self.df.drop(columns=drop_columns, errors="ignore", inplace=True)

        # Round the numeric columns to 2 decimal places
        self.df[ColumnName.NET_DIVIDEND.value] = pd.to_numeric(
            self.df[ColumnName.NET_DIVIDEND.value], errors="coerce"
        ).round(2)
        self.df[ColumnName.TAX_COLLECTED.value] = pd.to_numeric(
            self.df[ColumnName.TAX_COLLECTED.value], errors="coerce"
        ).round(2)
        # If Shares column exists and needs rounding
        self.df[ColumnName.SHARES.value] = pd.to_numeric(
            self.df[ColumnName.SHARES.value], errors="coerce"
        ).round(2)

        # Move 'Shares' column to the end
        shares_col = self.df.pop(ColumnName.SHARES.value)
        self.df[ColumnName.SHARES.value] = shares_col

        return self.df

    def reorder_columns(self) -> pd.DataFrame:
        """Reorder the DataFrame columns to the desired sequence.

        Order: Date, Ticker, Shares, Net Dividend, Tax Collected Amount,
               Tax Collected %, Tax Amount PLN

        Returns:
            DataFrame with reordered columns.
        """
        desired_order = [
            ColumnName.DATE.value,
            ColumnName.TICKER.value,
            ColumnName.SHARES.value,
            ColumnName.NET_DIVIDEND.value,
            ColumnName.TAX_COLLECTED_AMOUNT.value,
            ColumnName.TAX_COLLECTED_PCT.value,
            ColumnName.DATE_D_MINUS_1.value,
            ColumnName.EXCHANGE_RATE_D_MINUS_1.value,
            ColumnName.TAX_AMOUNT_PLN.value,
        ]

        # Filter to only include columns that exist in the DataFrame
        existing_columns = [col for col in desired_order if col in self.df.columns]

        # Reorder the DataFrame columns
        self.df = self.df[existing_columns]

        existing_cols_str = ", ".join(existing_columns)
        logger.info(f"Step 12 - Reordered columns to: {existing_cols_str}")

        return self.df
