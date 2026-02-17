"""Data aggregation and row merging operations.

This module handles grouping, merging, and aggregation of dividend data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger


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
        if "Tax Collected" not in self.df.columns:
            self.df["Tax Collected"] = np.nan

        if "Net Dividend" not in self.df.columns:
            self.df["Net Dividend"] = np.nan

        return self.df

    def add_empty_column(self, col_name: str = "Tax Collected", position: int = 4) -> pd.DataFrame:
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
        self.df["Net Dividend"] = pd.to_numeric(
            self.df["Net Dividend"], errors="coerce"
        )
        self.df["Tax Collected"] = pd.to_numeric(
            self.df["Tax Collected"], errors="coerce"
        )

        return self.df

    def move_negative_values(self) -> pd.DataFrame:
        """Move negative values from 'Net Dividend' to 'Tax Collected'.

        Sets the original 'Net Dividend' to NaN after moving.

        Returns:
            DataFrame with negative values moved.
        """
        self.prepare_columns()
        self.df.loc[self.df["Net Dividend"] < 0, "Tax Collected"] = self.df[
            "Net Dividend"
        ]
        self.df.loc[self.df["Net Dividend"] < 0, "Net Dividend"] = np.nan

        return self.df

    def merge_rows_and_reorder(self, drop_columns: list[str] = ["Type", "Comment"]) -> pd.DataFrame:
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
            "Net Dividend": "sum",
            "Shares": "sum",
        }

        # If Tax Collected exists, take first value (they should all be same after extract_tax_percentage_from_comment)
        if "Tax Collected" in self.df.columns:
            agg_dict["Tax Collected"] = "first"

        # If Tax Collected Raw exists (for USD statement), sum the values
        if "Tax Collected Raw" in self.df.columns:
            agg_dict["Tax Collected Raw"] = "sum"

        # Merge rows with the same 'Date' and 'Ticker'
        self.df = self.df.groupby(["Date", "Ticker"], as_index=False).agg(agg_dict)

        # Drop specified columns (if they exist in the DataFrame)
        self.df.drop(columns=drop_columns, errors="ignore", inplace=True)

        # Round the numeric columns to 2 decimal places
        self.df["Net Dividend"] = pd.to_numeric(
            self.df["Net Dividend"], errors='coerce').round(2)
        self.df["Tax Collected"] = pd.to_numeric(
            self.df["Tax Collected"], errors='coerce').round(2)
        # If Shares column exists and needs rounding
        self.df["Shares"] = pd.to_numeric(self.df["Shares"], errors='coerce').round(2)

        # Move 'Shares' column to the end
        shares_col = self.df.pop("Shares")
        self.df["Shares"] = shares_col

        return self.df

    def reorder_columns(self) -> pd.DataFrame:
        """Reorder the DataFrame columns to the desired sequence.

        Order: Date, Ticker, Shares, Net Dividend, Tax Collected Amount, 
               Tax Collected %, Tax Amount PLN

        Returns:
            DataFrame with reordered columns.
        """
        desired_order = [
            "Date",
            "Ticker",
            "Shares",
            "Net Dividend",
            "Tax Collected Amount",
            "Tax Collected %",
            "Date D-1",
            "Exchange Rate D-1",
            "Tax Amount PLN"
        ]

        # Filter to only include columns that exist in the DataFrame
        existing_columns = [col for col in desired_order if col in self.df.columns]

        # Reorder the DataFrame columns
        self.df = self.df[existing_columns]

        logger.info(
            f"Step 12 - Reordered columns to: {', '.join(existing_columns)}"
        )

        return self.df
