"""Tax rate extraction and calculation.

This module handles extraction of tax rates from comment fields
and provides default tax rates based on ticker suffixes.
"""

from __future__ import annotations

import re

import pandas as pd
from loguru import logger

from .constants import Currency, TickerSuffix


class TaxExtractor:
    """Extracts tax information from comments and provides default tax rates.

    Handles extraction of withholding tax rates from broker statement comments
    and provides country-specific default tax rates based on ticker suffixes.
    """

    def __init__(self, df: pd.DataFrame):
        """Initialize TaxExtractor with a DataFrame.

        Args:
            df: DataFrame containing dividend data.
        """
        self.df = df

    def extract_tax_rate_from_comment(self, comment: str) -> float | None:
        """Extract tax rate from comment string (e.g., 'WHT 27%' or '19%').

        Args:
            comment: Comment string potentially containing tax rate.

        Returns:
            Tax rate as decimal (e.g., 0.27 for 27%) or None if not found.
        """
        if not isinstance(comment, str):
            return None

        # Try to match WHT pattern first (more specific)
        match = re.search(r"WHT\s*(\d+(?:\.\d+)?)%", comment)
        if match:
            return float(match.group(1)) / 100

        # Try to match any percentage pattern
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', comment)
        if match:
            return float(match.group(1)) / 100

        return None

    def get_default_tax_rate(self, ticker: str) -> float:
        """Get default withholding tax rate based on ticker suffix.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Default tax rate as decimal.
        """
        # Special case: ASB.PL is a US company listed in Poland with 0% withholding at source
        if "ASB.PL" in ticker:
            return 0.0

        # Define the withholding tax rates at source
        # Note: US default is 15% with W8BEN form. Without W8BEN, the rate is 30%.
        tax_rates = {
            # 15% withholding tax for US stocks (with W8BEN form)
            TickerSuffix.US.value: 0.15,
            # 19% withholding tax for PL stocks (Belka tax)
            TickerSuffix.PL.value: 0.19,
            TickerSuffix.DK.value: 0.15,  # 15% withholding tax for DK stocks (Denmark)
            # 0% withholding tax for UK stocks (no UK withholding tax for non-residents)
            TickerSuffix.UK.value: 0.0,
            # 15% withholding tax for IE stocks (Ireland, reduced rate for Polish residents)
            TickerSuffix.IE.value: 0.15,
            # 0% withholding tax for FR stocks (France, under Poland-France tax treaty)
            TickerSuffix.FR.value: 0.0,
        }

        for suffix, rate in tax_rates.items():
            if suffix in ticker:
                return rate

        return 0.0  # Default to 0% if country not recognized

    def extract_tax_percentage_from_comment(self, statement_currency: str = "PLN") -> pd.DataFrame:
        """Extract tax percentage from Comment column and store in 'Tax Collected' column.

        This should be called BEFORE merge_rows_and_reorder() to preserve tax percentage values.

        For USD statement: preserves the actual tax amount from file in 'Tax Collected Raw' column
        before converting 'Tax Collected' to percentage.

        Each dividend has two rows in Excel:
        1. Row with amount: "SBUX.US USD 0.5700/ SHR"
        2. Row with tax: "SBUX.US USD WHT 15%"

        This method finds the tax percentage for each Date+Ticker group by searching
        all rows in that group.

        Special cases (0% withholding tax at source):
        - ASB.PL: US company listed in Poland, no withholding tax in Excel
        - UK stocks: No withholding tax for non-residents
        - FR stocks: 0% withholding under Poland-France tax treaty

        Args:
            statement_currency: Currency of the statement ('USD' or 'PLN')

        Returns:
            DataFrame with tax percentages extracted.
        """
        # For USD statement, save the actual tax amount before converting to percentage
        if statement_currency == "USD" and "Tax Collected" in self.df.columns:
            self.df["Tax Collected Raw"] = self.df["Tax Collected"].copy()

        # Group by Date and Ticker, then extract tax percentage for each group
        grouped = self.df.groupby(["Date", "Ticker"], group_keys=False)

        # Process each group to extract tax percentage
        results = []
        for (date, ticker), group in grouped:
            group_copy = group.copy()

            # Try to extract tax percentage from each row in the group
            tax_found = False
            for comment in group_copy["Comment"]:
                tax_percentage = self.extract_tax_rate_from_comment(comment)
                if tax_percentage is not None:
                    # Found a valid tax percentage, apply to all rows in group
                    group_copy["Tax Collected"] = round(tax_percentage, 2)
                    tax_found = True
                    break

            if not tax_found:
                # If no tax percentage found, use default rate for ticker
                default_rate = self.get_default_tax_rate(ticker)
                group_copy["Tax Collected"] = round(default_rate, 2)

                if default_rate == 0.0:
                    logger.info(
                        f"Using 0% tax rate for {ticker} (no withholding tax at source).")
                else:
                    logger.warning(
                        f"No WHT information in Comment for {ticker} on {date}. "
                        f"Using default rate {default_rate*100:.0f}% (common for small dividend amounts)."
                    )

            results.append(group_copy)

        self.df = pd.concat(results, ignore_index=False)
        logger.info(
            "Extracted tax percentages from Comment column for each Date+Ticker group.")

        return self.df

    def validate_tax_collected(self) -> pd.DataFrame:
        """Validate Tax Collected column and warn about high US tax rates.

        This method validates that the Tax Collected column exists and contains valid values.
        It also checks for US dividends with 30% tax rate and suggests filing W8BEN form.

        Returns:
            DataFrame with validated tax data.

        Raises:
            ValueError: If Tax Collected column is not found.
        """
        tax_col = "Tax Collected"

        # Validate that Tax Collected column exists and has values
        if tax_col not in self.df.columns:
            raise ValueError(
                f"Column '{tax_col}' not found. "
                f"Please call extract_tax_percentage_from_comment() before merge_rows_and_reorder()."
            )

        # Check for any missing or invalid tax percentages
        invalid_rows = self.df[self.df[tax_col].isna() | (self.df[tax_col] == 0)]
        if not invalid_rows.empty:
            logger.warning(
                f"Found {len(invalid_rows)} rows with missing or zero tax percentages. "
                f"Tickers: {invalid_rows['Ticker'].tolist()}"
            )

        logger.info("Tax Collected column validated.")

        # Check for US tickers with 30% tax rate
        us_tickers_with_30_tax = self.df[
            (self.df["Ticker"].str.contains("US", na=False)) &
            (abs(self.df[tax_col] - 0.30) < 0.01)
        ]

        if not us_tickers_with_30_tax.empty:
            ticker_examples = us_tickers_with_30_tax["Ticker"].head(3).tolist()
            logger.warning(
                f"⚠️  WARNING: 30% tax rate detected for US dividend(s): {', '.join(ticker_examples)}. "
                f"In Poland, you can file a W8BEN form with your broker, "
                f"which reduces the withholding tax from 30% to 15% according to the double taxation treaty."
            )

        logger.info(
            "Step 6 - Updated 'Tax Collected' column with calculated tax percentages."
        )

        return self.df
