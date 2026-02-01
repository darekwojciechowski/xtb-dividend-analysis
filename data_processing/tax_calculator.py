"""
Tax Calculator Module

This module contains all logic related to calculating tax amounts (Tax Amount PLN)
for dividend income according to Polish Belka tax rules (19% flat tax).

The TaxCalculator class handles:
- Validation of required columns in DataFrame
- Parsing of formatted values (amounts with currency)
- Calculation of tax to pay in Poland based on tax already collected at source
"""

from __future__ import annotations

import pandas as pd
from loguru import logger


class TaxCalculator:
    """Calculate tax amounts in PLN to pay in Poland according to Belka tax (19%)."""

    # Polish Belka tax rate (19% flat tax on capital gains)
    POLISH_TAX_RATE = 0.19

    def __init__(self, df: pd.DataFrame):
        """
        Initialize TaxCalculator with a DataFrame.

        Args:
            df (pd.DataFrame): DataFrame containing dividend data with required columns.
        """
        self.df = df

    def _validate_required_columns(self, required_columns: list[str]) -> None:
        """
        Validate that required columns exist in DataFrame for tax calculations.

        Args:
            required_columns (list[str]): List of column names that must exist.

        Raises:
            ValueError: If any required column is missing.
        """
        missing_columns = [
            col for col in required_columns if col not in self.df.columns
        ]
        if missing_columns:
            raise ValueError(
                f"Required columns missing: {', '.join(missing_columns)}. "
                f"Please ensure all helper columns are created before calling this method."
            )

    def _parse_value_with_currency(
        self, value_str: str, column_name: str, ticker: str, date: str
    ) -> tuple[float, str]:
        """
        Parse numeric value and currency from formatted string.

        Args:
            value_str (str): String in format "6.84 USD" or "28.22 PLN"
            column_name (str): Name of the column being parsed (for error messages)
            ticker (str): Ticker symbol (for error messages)
            date (str): Date value (for error messages)

        Returns:
            tuple[float, str]: (numeric_value, currency_code)

        Raises:
            ValueError: If format is invalid or value cannot be parsed.
        """
        if pd.isna(value_str) or value_str == "" or value_str == "nan":
            raise ValueError(
                f"Missing '{column_name}' value for ticker '{ticker}' on date '{date}'."
            )

        parts = value_str.split()
        if len(parts) != 2:
            raise ValueError(
                f"Invalid '{column_name}' format for ticker '{ticker}' on date '{date}': '{value_str}'. "
                f"Expected format: '6.84 USD' or '28.22 PLN'."
            )

        try:
            numeric_value = float(parts[0])
            currency = parts[1]
            return numeric_value, currency
        except ValueError:
            raise ValueError(
                f"Invalid numeric value in '{column_name}' for ticker '{ticker}' on date '{date}': '{parts[0]}'"
            )

    def _parse_tax_collected_amount(
        self, value_str: str, ticker: str, date: str
    ) -> float:
        """
        Parse Tax Collected Amount which can be a value with currency or '-' for zero.

        Args:
            value_str (str): String in format "1.03 USD" or "-"
            ticker (str): Ticker symbol (for error messages)
            date (str): Date value (for error messages)

        Returns:
            float: Tax collected amount (0.0 if value is "-")

        Raises:
            ValueError: If format is invalid or value cannot be parsed.
        """
        if value_str == "-" or pd.isna(value_str) or value_str == "nan":
            return 0.0

        parts = value_str.split()
        if len(parts) != 2:
            raise ValueError(
                f"Invalid 'Tax Collected Amount' format for ticker '{ticker}' on date '{date}': '{value_str}'. "
                f"Expected format: '1.03 USD' or '-'."
            )

        try:
            return float(parts[0])
        except ValueError:
            raise ValueError(
                f"Invalid numeric value in 'Tax Collected Amount' for ticker '{ticker}' on date '{date}': '{parts[0]}'"
            )

    def _parse_exchange_rate(self, value_str: str, ticker: str, date: str) -> float:
        """
        Parse Exchange Rate D-1 which can be a value with PLN or '-' for 1.0.

        Args:
            value_str (str): String in format "4.1512 PLN" or "-"
            ticker (str): Ticker symbol (for error messages)
            date (str): Date value (for error messages)

        Returns:
            float: Exchange rate (1.0 if value is "-" indicating PLN)

        Raises:
            ValueError: If format is invalid or value cannot be parsed.
        """
        if value_str == "-" or pd.isna(value_str) or value_str == "nan":
            return 1.0

        parts = value_str.split()
        if len(parts) != 2:
            raise ValueError(
                f"Invalid 'Exchange Rate D-1' format for ticker '{ticker}' on date '{date}': '{value_str}'. "
                f"Expected format: '4.1512 PLN' or '-'."
            )

        try:
            return float(parts[0])
        except ValueError:
            raise ValueError(
                f"Invalid numeric value in 'Exchange Rate D-1' for ticker '{ticker}' on date '{date}': '{parts[0]}'"
            )

    def calculate_tax_for_pln_statement(self, statement_currency: str) -> pd.DataFrame:
        """
        Calculate tax amount in PLN to pay in Poland for PLN statement currency.
        Adds 'Tax Amount PLN' column to the DataFrame.

        Polish tax logic (Belka tax = 19%):
        - If Tax Collected >= 19%: Tax Amount PLN = "-" (tax already paid at source)
        - If Tax Collected < 19%: Tax Amount PLN = (Net Dividend * 19% - Tax Collected Amount) * Exchange Rate D-1

        This function uses the helper columns:
        - Tax Collected Amount: actual tax paid at source with currency
        - Exchange Rate D-1: exchange rate for currency on D-1 date

        Args:
            statement_currency (str): The currency of the statement from cell F6 (e.g., 'PLN').

        Returns:
            pd.DataFrame: DataFrame with added 'Tax Amount PLN' column.

        Raises:
            ValueError: If required columns are missing or if any row has missing data.
        """
        # Validate required columns exist
        required_columns = [
            "Net Dividend",
            "Tax Collected",
            "Tax Collected Amount",
            "Exchange Rate D-1",
        ]
        self._validate_required_columns(required_columns)

        # Add Tax Amount PLN column if it doesn't exist
        if "Tax Amount PLN" not in self.df.columns:
            self.df["Tax Amount PLN"] = 0.0

        def calculate_tax_pln(row):
            """Calculate tax amount in PLN for a single row."""
            # Get required values
            net_dividend_str = str(row.get("Net Dividend", ""))
            tax_percentage = row.get("Tax Collected", None)
            tax_collected_amount_str = str(row.get("Tax Collected Amount", ""))
            exchange_rate_str = str(row.get("Exchange Rate D-1", ""))

            # Validate that none of the critical values are missing
            if pd.isna(tax_percentage):
                ticker = row.get("Ticker", "Unknown")
                date = row.get("Date", "Unknown")
                raise ValueError(
                    f"Missing 'Tax Collected' value for ticker '{ticker}' on date '{date}'. "
                    f"All rows must have valid tax percentage values."
                )

            # Convert tax percentage to float
            try:
                tax_percentage = float(tax_percentage)
            except (ValueError, TypeError):
                ticker = row.get("Ticker", "Unknown")
                date = row.get("Date", "Unknown")
                raise ValueError(
                    f"Invalid 'Tax Collected' value for ticker '{ticker}' on date '{date}': {tax_percentage}"
                )

            # First condition: If tax already paid at source is >= 19%, no additional tax in Poland
            if tax_percentage >= self.POLISH_TAX_RATE:
                return "-"

            # Second condition: Calculate tax to pay in Poland
            ticker = row.get("Ticker", "Unknown")
            date = str(row.get("Date", "Unknown"))

            # Parse values using helper methods
            net_dividend, _ = self._parse_value_with_currency(
                net_dividend_str, "Net Dividend", ticker, date
            )
            tax_collected_amount = self._parse_tax_collected_amount(
                tax_collected_amount_str, ticker, date
            )
            exchange_rate = self._parse_exchange_rate(exchange_rate_str, ticker, date)

            # Calculate tax amount to pay in PLN
            # Formula: (Net Dividend * 19% - Tax Collected Amount) * Exchange Rate D-1
            tax_to_collect_in_currency = (
                net_dividend * self.POLISH_TAX_RATE
            ) - tax_collected_amount
            tax_amount_pln = tax_to_collect_in_currency * exchange_rate

            return round(tax_amount_pln, 2)

        # Apply calculation to all rows
        self.df["Tax Amount PLN"] = self.df.apply(calculate_tax_pln, axis=1)

        # Replace 0 with "-" for better readability
        self.df["Tax Amount PLN"] = self.df["Tax Amount PLN"].replace(0.0, "-")

        logger.info(
            f"Step 7 - Calculated tax amounts in PLN based on Polish tax rules (19% Belka tax) for {statement_currency} statement."
        )

        return self.df

    def calculate_tax_for_usd_statement(
        self, statement_currency: str
    ) -> pd.DataFrame:
        """
        Calculate tax amount in PLN to pay in Poland for USD statement currency.
        Adds 'Tax Amount PLN' column to the DataFrame.

        This is a placeholder for future implementation.

        Args:
            statement_currency (str): The currency of the statement from cell F6 (e.g., 'USD').

        Returns:
            pd.DataFrame: DataFrame with added 'Tax Amount PLN' column.
        """
        # TODO: Implement USD statement tax calculation logic
        logger.info(
            f"USD statement tax calculation not yet implemented for {statement_currency} statement."
        )
        return self.df
