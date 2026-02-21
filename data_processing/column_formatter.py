"""Column formatting and display preparation.

This module handles formatting of columns for display and export,
including tax percentage display, currency annotations, and date calculations.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from loguru import logger

from config.settings import settings
from visualization.ticker_colors import get_random_color

from .constants import ColumnName
from .currency_converter import CurrencyConverter
from .date_converter import DateConverter
from .extractor import MultiConditionExtractor


class ColumnFormatter:
    """Formats DataFrame columns for display and export.

    Handles formatting of tax percentages, dates, currencies, and other
    display-oriented column transformations.
    """

    def __init__(self, df: pd.DataFrame):
        """Initialize ColumnFormatter with a DataFrame.

        Args:
            df: DataFrame to format.
        """
        self.df = df

    def apply_colorize_ticker(self) -> pd.DataFrame:
        """Apply random color formatting to the 'Ticker' column.

        Creates a new 'Colored Ticker' column without modifying the original 'Ticker' column.

        Returns:
            DataFrame with colored ticker column.
        """
        self.df["Colored Ticker"] = self.df["Ticker"].apply(
            lambda ticker: f"{get_random_color()}{ticker}\033[0m"
        )
        return self.df

    def apply_extractor(self) -> pd.DataFrame:
        """Apply the MultiConditionExtractor to the 'Comment' column.

        Returns:
            DataFrame with processed comments.
        """
        def apply_extractor_func(text: str) -> str:
            extractor = MultiConditionExtractor(text)
            return extractor.extract_condition()

        self.df["Comment"] = self.df["Comment"].apply(apply_extractor_func)
        return self.df

    def apply_date_converter(self) -> pd.DataFrame:
        """Convert date strings in the 'Date' column to datetime objects.

        Returns:
            DataFrame with converted dates.
        """
        def apply_converter(date_string: str) -> pd.Timestamp | None:
            converter = DateConverter(date_string)
            converter.convert_to_date()
            return converter.get_date()

        self.df["Date"] = self.df["Date"].apply(apply_converter)
        return self.df

    def add_tax_percentage_display(self) -> pd.DataFrame:
        """Create a display-friendly 'Tax Collected %' column with percentage formatting.

        Keeps the numeric 'Tax Collected' column for calculations.
        The 'Tax Collected %' column will be used for export/display,
        while 'Tax Collected' remains numeric for calculations.

        Returns:
            DataFrame with added 'Tax Collected %' column.
        """
        def format_tax_percentage(value):
            """Format tax percentage for display."""
            if pd.isna(value) or value == 0:
                return "-"
            # Convert decimal to percentage (e.g., 0.15 -> "15%")
            return f"{int(value * 100)}%"

        # Create display column from numeric column
        self.df["Tax Collected %"] = self.df["Tax Collected"].apply(
            format_tax_percentage)

        logger.info(
            "Step 7 - Created 'Tax Collected %' display column with percentage formatting."
        )

        return self.df

    def create_date_d_minus_1_column(self, step_number: str = "8") -> pd.DataFrame:
        """Create 'Date D-1' column showing the previous business day from the dividend date.

        If D-1 falls on a weekend, uses the last weekday (typically Friday).
        When Tax Collected >= polish_tax_rate, 'Date D-1' shows "-" since
        Polish tax obligations are already satisfied and no exchange-rate lookup is needed.
        The mask is applied only when the 'Tax Collected' column is already present
        (i.e. at step "8"); the early call at step "4a" is unaffected.

        Args:
            step_number: The step number to display in logs (default: "8").

        Returns:
            DataFrame with added 'Date D-1' column.
        """
        self.df["Date D-1"] = self.df["Date"].apply(
            CurrencyConverter.get_previous_business_day
        )

        # Mask rows where foreign WHT already satisfies Polish tax obligation.
        # 'Tax Collected' only exists after tax extraction (step "8" onwards).
        tax_col = ColumnName.TAX_COLLECTED.value
        if tax_col in self.df.columns:
            mask = self.df[tax_col].notna() & (
                self.df[tax_col] >= settings.polish_tax_rate)
            if mask.any():
                # Cast to object so a string sentinel "-" can coexist with Timestamps.
                self.df["Date D-1"] = self.df["Date D-1"].astype(object)
                self.df.loc[mask, "Date D-1"] = "-"

        logger.info(
            f"Step {step_number} - Created 'Date D-1' column with previous business day dates."
        )

        return self.df

    def create_exchange_rate_d_minus_1_column(self, courses_paths: list[str]) -> pd.DataFrame:
        """Create 'Exchange Rate D-1' column showing exchange rate for currency on D-1 date.

        Exchange rate is only shown when Tax Collected < 19% (polish_tax_rate).
        When foreign tax collected is >= 19%, Exchange Rate D-1 shows "-" since
        Polish tax obligations are already satisfied.

        Args:
            courses_paths: List of paths to exchange rate CSV files.

        Returns:
            DataFrame with added 'Exchange Rate D-1' column.
        """
        converter = CurrencyConverter(self.df)

        def get_exchange_rate_for_row(row):
            """Extract currency from Net Dividend and get exchange rate for D-1 date.

            Returns "-" if Tax Collected >= polish_tax_rate (19%), otherwise returns
            the exchange rate for the D-1 date.
            """
            # Check if foreign tax already satisfies Polish tax obligation
            tax_percentage = row.get("Tax Collected", None)
            if tax_percentage is not None and not pd.isna(tax_percentage):
                if tax_percentage >= settings.polish_tax_rate:
                    return "-"

            net_dividend_str = str(row.get("Net Dividend", ""))
            date_d_minus_1 = row.get("Date D-1")

            # Extract currency from Net Dividend (format: "6.84 USD" or "28.22 PLN")
            parts = net_dividend_str.split()
            if len(parts) != 2:
                return "-"

            currency = parts[1]

            # Convert date to string format for lookup
            if pd.isna(date_d_minus_1):
                return "-"

            # Convert date to YYYY-MM-DD format
            if isinstance(date_d_minus_1, pd.Timestamp):
                date_str = date_d_minus_1.strftime("%Y-%m-%d")
            elif isinstance(date_d_minus_1, datetime):
                date_str = date_d_minus_1.strftime("%Y-%m-%d")
            else:
                date_str = date_d_minus_1.strftime("%Y-%m-%d")

            # Get exchange rate
            rate = converter.get_exchange_rate(courses_paths, date_str, currency)

            # Return formatted rate or "-" if not found
            if rate == 0.0:
                return "-"
            elif rate == 1.0 and currency == "PLN":
                return "-"  # No need to show rate for PLN
            else:
                return f"{rate:.4f} PLN"

        # Create Exchange Rate D-1 column
        self.df["Exchange Rate D-1"] = self.df.apply(get_exchange_rate_for_row, axis=1)

        logger.info(
            "Step 9 - Created 'Exchange Rate D-1' column with exchange rates for D-1 dates."
        )

        return self.df

    def add_tax_collected_amount(self, statement_currency: str = "PLN") -> pd.DataFrame:
        """Create 'Tax Collected Amount' column showing actual tax amount collected.

        Shows the tax amount in the same currency as the dividend (not as percentage).

        For USD statement: uses the raw tax amount from file (Tax Collected Raw column)
        For PLN statement: calculates from Net Dividend and tax percentage

        Args:
            statement_currency: Currency of the statement ('USD' or 'PLN')

        Returns:
            DataFrame with added 'Tax Collected Amount' column.
        """
        def calculate_tax_amount(row):
            """Calculate actual tax amount collected with currency."""
            net_dividend_str = str(row.get("Net Dividend", ""))
            tax_percentage = row.get("Tax Collected", 0)

            # Extract numeric value and currency from Net Dividend
            # Format: "6.84 USD" or "28.22 PLN"
            parts = net_dividend_str.split()
            if len(parts) != 2:
                return "-"

            try:
                dividend_amount = float(parts[0])
                currency = parts[1]
            except (ValueError, IndexError):
                return "-"

            # Check if tax percentage is valid
            if pd.isna(tax_percentage) or tax_percentage == 0:
                return "-"

            # For USD statement: use raw tax amount from file if available
            if statement_currency == "USD" and "Tax Collected Raw" in self.df.columns:
                tax_raw = row.get("Tax Collected Raw", None)
                if not pd.isna(tax_raw) and tax_raw != 0:
                    # Tax Collected Raw contains negative value, take absolute
                    tax_amount = abs(float(tax_raw))
                    return f"{tax_amount:.2f} {currency}"

            # For PLN statement or if raw amount not available: calculate from percentage
            # Net Dividend = Gross Dividend * (1 - tax_percentage)
            # Therefore: Gross Dividend = Net Dividend / (1 - tax_percentage)
            # Tax Amount = Gross Dividend * tax_percentage
            gross_dividend = dividend_amount / (1 - tax_percentage)
            tax_amount = gross_dividend * tax_percentage

            # Format with currency
            return f"{tax_amount:.2f} {currency}"

        # Create Tax Collected Amount column
        self.df["Tax Collected Amount"] = self.df.apply(calculate_tax_amount, axis=1)

        logger.info(
            "Step 10 - Created 'Tax Collected Amount' column with actual tax amounts in respective currencies."
        )

        return self.df
