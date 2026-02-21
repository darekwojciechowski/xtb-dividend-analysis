"""Currency conversion and exchange rate lookups.

This module handles currency identification, exchange rate retrieval,
and currency-related calculations for dividend processing.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from loguru import logger

from .constants import ColumnName, Currency, TickerSuffix


class CurrencyConverter:
    """Handles currency operations including exchange rate lookups and conversions.

    Provides methods for determining dividend currencies based on tickers,
    retrieving exchange rates from NBP data, and performing currency conversions.
    """

    def __init__(self, df: pd.DataFrame):
        """Initialize CurrencyConverter with a DataFrame.

        Args:
            df: DataFrame containing dividend data.
        """
        self.df = df

    def determine_currency(self, ticker: str, extracted_currency: str | None) -> str:
        """Determine the currency based on ticker and extracted currency.

        Args:
            ticker: The stock ticker.
            extracted_currency: Currency extracted from comment.

        Returns:
            Determined currency ('USD', 'PLN', 'EUR', 'DKK', 'GBP')
        """
        if extracted_currency:
            return extracted_currency

        # Special case: ASB.PL is a US company listed in Poland
        if "ASB.PL" in ticker:
            return Currency.USD.value

        # If no currency in comment, infer from ticker suffix
        if TickerSuffix.US.value in ticker:
            return Currency.USD.value
        elif TickerSuffix.PL.value in ticker:
            return Currency.PLN.value
        elif TickerSuffix.DK.value in ticker:
            return Currency.DKK.value
        elif TickerSuffix.UK.value in ticker:
            return Currency.GBP.value
        elif any(suffix.value in ticker for suffix in TickerSuffix.eurozone_suffixes()):
            return Currency.EUR.value

        # Default to USD if can't determine
        return Currency.USD.value

    def extract_dividend_from_comment(self, comment: str) -> tuple[float | None, str | None]:
        """Extract dividend per share and currency from the comment string.

        Args:
            comment: The comment containing dividend details.

        Returns:
            Tuple of (dividend_per_share, currency) or (None, None) if not found.
        """
        if not isinstance(comment, str):
            return None, None

        # Try to match the pattern "XXX WHT" (currency with withholding tax, e.g., "PLN WHT 19%")
        match = re.search(r"([A-Z]{3})\s+WHT", comment)
        if match:
            currency = match.group(1)
            # Try to find a dividend amount in the same comment (e.g., "0.3000/ SHR")
            dividend_match = re.search(r"([\d.]+)\s*/\s*SHR", comment)
            if dividend_match:
                return float(dividend_match.group(1)), currency
            # If no dividend amount found, return None for dividend but still return currency
            return None, currency

        # Try to match the pattern "XXX X.XX/ SHR" (any 3-letter currency)
        match = re.search(r"([A-Z]{3}) ([\d.]+)/ SHR", comment)
        if match:
            return float(match.group(2)), match.group(1)

        # Try alternative pattern "X.XX XXX/SHR" (any 3-letter currency)
        match = re.search(r"([\d.]+) ([A-Z]{3})/SHR", comment)
        if match:
            return float(match.group(1)), match.group(2)

        # Try to match just a number (assume default currency based on ticker)
        match = re.search(r"([\d.]+)", comment)
        if match:
            num_str = match.group(1)
            # Avoid matching a single '.' or multiple dots which are not valid numbers
            if num_str == "." or num_str.replace(".", "") == "":
                return None, None
            try:
                return float(num_str), None
            except ValueError:
                # If conversion fails, return None for this invalid input
                return None, None

        return None, None

    def get_exchange_rate(self, courses_paths: list[str], target_date_str: str, currency: str) -> float:
        """Retrieve the exchange rate for a specific currency on a specific date from CSV files.

        If the date is not found (e.g., weekend or holiday), searches backwards for the previous business day.

        Args:
            courses_paths: List of CSV file paths containing exchange rates.
            target_date_str: The date in 'YYYY-MM-DD' format to search for.
            currency: Currency code ('USD', 'EUR', 'DKK', 'GBP', etc.)

        Returns:
            The exchange rate for the specified currency on the specified date.
            Returns 1.0 for PLN. Returns 0.0 if rate not found.

        Raises:
            ValueError: If no exchange rate data found for the specified date.
        """
        # PLN is the base currency, so exchange rate is always 1.0
        if currency == Currency.PLN.value:
            return 1.0

        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")

        # Map currency to column name in NBP data
        currency_column_map = {
            Currency.USD.value: "1USD",
            Currency.EUR.value: "1EUR",
            Currency.GBP.value: "1GBP",
            Currency.DKK.value: "1DKK",
        }

        column_name = currency_column_map.get(currency)
        if not column_name:
            logger.warning(
                f"Currency '{currency}' not supported for exchange rate lookup. Using 1.0")
            return 1.0

        # Try to find exchange rate for target date or previous business days
        max_attempts = 10  # Maximum number of days to search backwards
        current_date = target_date

        for attempt in range(max_attempts):
            current_date_str_formatted = current_date.strftime("%Y%m%d")

            for csv_file in courses_paths:
                try:
                    df = pd.read_csv(csv_file, sep=";", encoding="ISO-8859-1")

                    # Check if the column exists
                    if column_name not in df.columns:
                        continue

                    currency_value = df[df["data"] ==
                                        current_date_str_formatted][column_name].values

                    if len(currency_value) > 0:
                        rate = float(currency_value[0].replace(",", "."))
                        if attempt > 0:
                            logger.info(
                                f"Exchange rate for {currency} not found for {target_date_str}, "
                                f"using rate from {current_date.strftime('%Y-%m-%d')}: {rate}"
                            )
                        return rate
                except FileNotFoundError:
                    logger.warning(f"Exchange rate file '{csv_file}' was not found.")
                except Exception as e:
                    logger.warning(
                        f"An error occurred while processing '{csv_file}': {e}")

            # Move to previous day
            current_date = current_date - timedelta(days=1)

            # Skip weekends (Saturday=5, Sunday=6)
            while current_date.weekday() in [5, 6]:
                current_date = current_date - timedelta(days=1)

        error_msg = (
            f"No exchange rate data found for {currency} on date '{target_date_str}' or previous {max_attempts} business days. "
            f"Check if you have downloaded the file 'archiwum_tab_a_XXXX.csv' for the date '{target_date_str}'."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    def calculate_dividend(
        self,
        courses_paths: list[str],
        statement_currency: str,
        comment_col: str,
        amount_col: str,
    ) -> pd.DataFrame:
        """Calculate shares and net dividends per row using per-share dividend and exchange rates.

        Populates the ``Shares`` and ``Currency`` columns and updates ``amount_col``
        with the total dividend (shares × dividend_per_share).

        Args:
            courses_paths: List of NBP CSV file paths for exchange-rate lookups.
            statement_currency: Currency of the XTB statement from cell F6 (e.g., 'PLN', 'USD').
            comment_col: Column name containing comment strings with dividend-per-share data.
            amount_col: Column name holding the total dividend amount to be updated.

        Returns:
            DataFrame with populated ``Shares``, ``Currency``, and updated amount column.

        Raises:
            ValueError: If ``Date D-1`` column is missing or contains NaN values.
        """
        date_d1_col = ColumnName.DATE_D_MINUS_1.value
        shares_col = ColumnName.SHARES.value
        currency_col = ColumnName.CURRENCY.value
        ticker_col = ColumnName.TICKER.value

        if date_d1_col not in self.df.columns:
            raise ValueError(
                f"Column '{date_d1_col}' is required but not found in DataFrame. "
                "Please run create_date_d_minus_1_column() before calling this method."
            )

        if shares_col not in self.df.columns:
            self.df[shares_col] = np.nan

        if currency_col not in self.df.columns:
            self.df[currency_col] = None

        for index, row in self.df.iterrows():
            if (
                pd.isna(row.get(ColumnName.DATE.value))
                or pd.isna(row.get(amount_col))
                or pd.isna(row.get(comment_col))
            ):
                continue

            if pd.isna(row.get(date_d1_col)):
                raise ValueError(
                    f"'{date_d1_col}' value is missing for row {index}. "
                    "All rows must have valid 'Date D-1' values."
                )

            target_date = row[date_d1_col]
            target_date_str = target_date.strftime("%Y-%m-%d")

            total_dividend = float(row[amount_col])
            ticker = row[ticker_col]

            extracted_value, extracted_currency = self.extract_dividend_from_comment(
                row[comment_col]
            )

            if extracted_value is not None and extracted_value > 0:
                dividend_per_share = extracted_value

                currency = self.determine_currency(ticker, extracted_currency)
                self.df.at[index, currency_col] = currency

                exchange_rate = 1.0
                if statement_currency == Currency.PLN.value and currency == Currency.USD.value:
                    exchange_rate = self.get_exchange_rate(
                        courses_paths, target_date_str, currency
                    )

                if dividend_per_share * exchange_rate == 0:
                    logger.warning(
                        "Division by zero encountered in shares calculation for "
                        f"ticker '{ticker}' on {target_date_str}."
                    )
                    shares = 0.0
                else:
                    shares = total_dividend / (dividend_per_share * exchange_rate)

                self.df.at[index, shares_col] = round(shares)
                self.df.at[index, amount_col] = dividend_per_share

        self.df[amount_col] = self.df.apply(
            lambda r: (
                r[shares_col] * r[amount_col]
                if not pd.isna(r[shares_col])
                else r[amount_col]
            ),
            axis=1,
        )
        logger.info(
            "Step 5 - Calculated dividends and updated shares using exchange rates.")
        return self.df

    def add_currency_to_dividends(self) -> pd.DataFrame:
        """Append currency symbols to the 'Net Dividend' column based on the ticker.

        Adds appropriate currency (USD, PLN, EUR, DKK, GBP) based on ticker suffix.

        Returns:
            DataFrame with currency-annotated dividends.
        """
        def append_currency(row):
            ticker = row["Ticker"]
            dividend = row["Net Dividend"]

            # Special case: ASB.PL uses USD
            if "ASB.PL" in ticker:
                return f"{dividend} {Currency.USD.value}"

            # Determine currency based on ticker suffix
            if TickerSuffix.US.value in ticker:
                return f"{dividend} {Currency.USD.value}"
            elif TickerSuffix.PL.value in ticker:
                return f"{dividend} {Currency.PLN.value}"
            elif TickerSuffix.DK.value in ticker:
                return f"{dividend} {Currency.DKK.value}"
            elif TickerSuffix.UK.value in ticker:
                return f"{dividend} {Currency.GBP.value}"
            elif any(suffix.value in ticker for suffix in TickerSuffix.eurozone_suffixes()):
                return f"{dividend} {Currency.EUR.value}"

            # No change if the condition doesn't match
            return dividend

        # Apply the currency formatting
        self.df["Net Dividend"] = self.df.apply(append_currency, axis=1)
        return self.df

    @staticmethod
    def get_previous_business_day(date_value) -> datetime:
        """Calculate the previous business day (D-1) from a given date.

        Skips weekends (Saturday, Sunday) by going backwards to the last weekday.

        Args:
            date_value: A datetime.date, pandas Timestamp, or datetime object.

        Returns:
            The previous business day.
        """
        # Convert to datetime.date if needed
        if isinstance(date_value, pd.Timestamp):
            date_value = date_value.date()
        elif isinstance(date_value, datetime):
            date_value = date_value.date()

        # Start with D-1 (previous day)
        previous_day = date_value - timedelta(days=1)

        # Skip backwards while it's a weekend (Saturday=5, Sunday=6)
        while previous_day.weekday() in [5, 6]:
            previous_day -= timedelta(days=1)

        return previous_day
