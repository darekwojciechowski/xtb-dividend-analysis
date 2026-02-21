"""Belka tax (19%) calculation for foreign dividend income.

This module calculates the Polish ``Tax Amount PLN`` owed on dividend
income, accounting for withholding tax already deducted at source.

The ``TaxCalculator`` class handles:

- Validation of required DataFrame columns before calculation
- Parsing of formatted amount-with-currency strings
- Per-row tax calculation for both PLN and USD statement variants
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from config.settings import settings


class TaxCalculator:
    """Calculate tax amounts in PLN to pay in Poland according to Belka tax (19%)."""

    def __init__(self, df: pd.DataFrame, polish_tax_rate: float | None = None):
        """Initialize TaxCalculator with a DataFrame.

        Args:
            df: DataFrame containing dividend data with required columns.
            polish_tax_rate: Polish Belka tax rate. If ``None``, reads the
                rate from ``settings.polish_tax_rate``.
        """
        self.df = df
        self.polish_tax_rate = polish_tax_rate if polish_tax_rate is not None else settings.polish_tax_rate

    def _validate_required_columns(self, required_columns: list[str]) -> None:
        """Validate that required columns exist in the DataFrame.

        Args:
            required_columns: Column names that must all be present.

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
        """Parse a numeric value and currency from a formatted string.

        Args:
            value_str: String in the format ``"6.84 USD"`` or ``"28.22 PLN"``.
            column_name: Column name being parsed, used in error messages.
            ticker: Ticker symbol, used in error messages.
            date: Date value, used in error messages.

        Returns:
            A tuple ``(numeric_value, currency_code)``.

        Raises:
            ValueError: If the format is invalid or the value cannot be
                parsed.
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
        """Parse the Tax Collected Amount, accepting ``"-"`` as zero.

        Args:
            value_str: String in the format ``"1.03 USD"`` or ``"-"``.
            ticker: Ticker symbol, used in error messages.
            date: Date value, used in error messages.

        Returns:
            Tax collected amount as a float, or ``0.0`` when the value
            is ``"-"``.

        Raises:
            ValueError: If the format is invalid or the value cannot be
                parsed.
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
        """Parse the Exchange Rate D-1, accepting ``"-"`` as ``1.0`` (PLN).

        Args:
            value_str: String in the format ``"4.1512 PLN"`` or ``"-"``.
            ticker: Ticker symbol, used in error messages.
            date: Date value, used in error messages.

        Returns:
            Exchange rate as a float, or ``1.0`` when the value is
            ``"-"`` (indicating PLN base currency).

        Raises:
            ValueError: If the format is invalid or the value cannot be
                parsed.
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
        """Calculate Belka tax in PLN for a PLN-denominated statement.

        Adds a ``Tax Amount PLN`` column using the following logic:

        - If ``Tax Collected >= 19%``: sets ``Tax Amount PLN`` to ``"-"``
          (tax already fully paid at source).
        - Otherwise: ``Tax Amount PLN =
          (Net Dividend * 19% - Tax Collected Amount) * Exchange Rate D-1``.

        Requires the helper columns ``Tax Collected Amount`` and
        ``Exchange Rate D-1`` to exist before calling.

        Args:
            statement_currency: Currency code from cell F6 (for example,
                ``"PLN"``).

        Returns:
            DataFrame with the ``Tax Amount PLN`` column added.

        Raises:
            ValueError: If required columns are missing or any row has
                missing data.
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
            if tax_percentage >= self.polish_tax_rate:
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
                net_dividend * self.polish_tax_rate
            ) - tax_collected_amount
            tax_amount_pln = tax_to_collect_in_currency * exchange_rate

            # Format with PLN currency suffix
            rounded_tax = round(tax_amount_pln, 2)
            if rounded_tax == 0.0:
                return "-"
            return f"{rounded_tax} PLN"

        # Apply calculation to all rows
        self.df["Tax Amount PLN"] = self.df.apply(calculate_tax_pln, axis=1)

        logger.info(
            f"Step 11 - Calculated tax amounts in PLN based on Polish tax rules (19% Belka tax) for {statement_currency} statement."
        )

        return self.df

    def calculate_tax_for_usd_statement(
        self, statement_currency: str
    ) -> pd.DataFrame:
        """Calculate Belka tax in PLN for a USD-denominated statement.

        Adds a ``Tax Amount PLN`` column. Because the USD statement
        already contains gross amounts, the formula differs from the PLN
        variant:

        - If ``Tax Collected >= 19%``: sets ``Tax Amount PLN`` to ``"-"``.
        - Otherwise: ``Tax Amount PLN =
          (Gross Dividend * 19% - Tax Collected Amount) * Exchange Rate D-1``
          where ``Gross Dividend = Net Dividend + Tax Collected Amount``.

        Args:
            statement_currency: Currency code from cell F6 (for example,
                ``"USD"``).

        Returns:
            DataFrame with the ``Tax Amount PLN`` column added.

        Raises:
            ValueError: If required columns are missing or any row has
                missing data.
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
            if tax_percentage >= self.polish_tax_rate:
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
            # For USD statement: Tax Collected Amount is the actual amount from file
            # Formula: (Gross Dividend * 19% - Tax Collected Amount) * Exchange Rate D-1
            # Gross Dividend = Net Dividend + Tax Collected Amount (actual values from file)
            gross_dividend = net_dividend + tax_collected_amount
            tax_to_collect_in_currency = (
                gross_dividend * self.polish_tax_rate
            ) - tax_collected_amount
            tax_amount_pln = tax_to_collect_in_currency * exchange_rate

            # Format with PLN currency suffix
            rounded_tax = round(tax_amount_pln, 2)
            if rounded_tax == 0.0:
                return "-"
            return f"{rounded_tax} PLN"

        # Apply calculation to all rows
        self.df["Tax Amount PLN"] = self.df.apply(calculate_tax_pln, axis=1)

        logger.info(
            f"Step 11 - Calculated tax amounts in PLN based on Polish tax rules (19% Belka tax) for {statement_currency} statement."
        )

        return self.df

    @staticmethod
    def calculate_total_tax_amount(df: pd.DataFrame) -> float:
        """Sum all ``Tax Amount PLN`` values, ignoring ``"-"`` markers.

        Args:
            df: DataFrame containing a ``Tax Amount PLN`` column.

        Returns:
            Total tax amount in PLN rounded to two decimal places.
        """
        if "Tax Amount PLN" not in df.columns:
            return 0.0

        total = 0.0
        for value in df["Tax Amount PLN"]:
            # Skip "-" values and parse numeric values with " PLN" suffix
            if value != "-" and value != 0:
                try:
                    # Handle format: "18.15 PLN" or numeric values
                    if isinstance(value, str) and " PLN" in value:
                        numeric_value = float(value.replace(" PLN", "").strip())
                        total += numeric_value
                    else:
                        total += float(value)
                except (ValueError, TypeError):
                    pass

        return round(total, 2)
