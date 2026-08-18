"""Currency conversion and exchange rate lookups.

This module handles currency identification, exchange rate retrieval,
and currency-related calculations for dividend processing.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

import numpy as np
import pandas as pd
from loguru import logger

from .constants import (
    MAX_EXCHANGE_RATE_LOOKBACK_DAYS,
    WEEKEND_DAYS,
    ColumnName,
    Currency,
    TickerSuffix,
)
from .date_converter import to_date


def _round_shares_half_up(shares: float) -> float:
    """Round a share count to the nearest whole share, halves going up.

    Built-in :func:`round` applies banker's rounding, so an exact .5 share count
    lands on the nearest even integer -- 2.5 becomes 2, not 3. Share counts are
    back-solved from an amount and a per-share figure, so ties are reachable and
    a downward tie propagates into the reconstructed dividend amount.

    Args:
        shares: Unrounded share count.

    Returns:
        The share count rounded half-up, as a float.
    """
    return float(Decimal(repr(shares)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class ExchangeRateUnavailableError(ValueError):
    """Raised when no NBP exchange rate can be resolved for a requested currency/date.

    Inherits from ``ValueError`` so existing callers that catch ``ValueError``
    continue to handle the failure; new callers can catch this specific class
    to distinguish missing-data failures from generic validation errors.

    Attributes:
        currency: Currency code that was requested.
        target_date: ISO date string the lookup was anchored on.
        searched_files: NBP CSV paths that were consulted.
    """

    def __init__(
        self, currency: str, target_date: str, searched_files: list[str]
    ) -> None:
        self.currency = currency
        self.target_date = target_date
        self.searched_files = list(searched_files)
        message = (
            f"No exchange rate data found for {currency} on date "
            f"'{target_date}' or previous {MAX_EXCHANGE_RATE_LOOKBACK_DAYS} "
            f"business days. Searched files: {self.searched_files or '[]'}. "
            f"Download the matching 'archiwum_tab_a_XXXX.csv' for that date."
        )
        super().__init__(message)


class CurrencyConverter:
    """Handles currency operations including exchange rate lookups and conversions.

    Provides methods for determining dividend currencies based on tickers,
    retrieving exchange rates from NBP data, and performing currency conversions.
    """

    # Map of supported currency codes to the NBP CSV column that holds the rate.
    #
    # Only per-1-unit columns belong here. The NBP file also carries per-100
    # columns (100HUF, 100JPY, 100KRW, 100INR, 100CLP, 100ISK) and 10000IDR;
    # adding any of those without applying the divisor yields a silent 100x
    # (or 10000x) error, so they are deliberately absent.
    _CURRENCY_COLUMN_MAP = {
        Currency.USD.value: "1USD",
        Currency.EUR.value: "1EUR",
        Currency.GBP.value: "1GBP",
        Currency.DKK.value: "1DKK",
        Currency.CHF.value: "1CHF",
        Currency.NOK.value: "1NOK",
        Currency.SEK.value: "1SEK",
        Currency.CAD.value: "1CAD",
    }

    def __init__(self, df: pd.DataFrame):
        """Initialize CurrencyConverter with a DataFrame.

        Args:
            df: DataFrame containing dividend data.
        """
        self.df = df
        # Cached (currency, date) -> rate lookups, keyed by the tuple of NBP
        # CSV paths supplied to get_exchange_rate(). Built lazily on first
        # lookup so callers that never touch FX (PLN-only tests) pay nothing.
        self._rate_lookup_cache: dict[
            tuple[str, ...], dict[tuple[str, datetime], float]
        ] = {}

    def _build_rate_lookup(
        self, courses_paths: list[str]
    ) -> dict[tuple[str, datetime], float]:
        """Read each NBP CSV once and index every (currency, date) -> rate.

        First-file-wins on duplicate keys, matching the original linear scan.

        Args:
            courses_paths: NBP CSV paths to ingest.

        Returns:
            A dict keyed by ``(currency_code, datetime)`` mapping to the rate.
        """
        cache_key = tuple(courses_paths)
        cached = self._rate_lookup_cache.get(cache_key)
        if cached is not None:
            return cached

        lookup: dict[tuple[str, datetime], float] = {}
        for csv_file in courses_paths:
            try:
                df = pd.read_csv(
                    csv_file, sep=";", encoding="ISO-8859-1"
                )  # pragma: no mutate
            except FileNotFoundError:
                logger.warning(
                    f"Exchange rate file '{csv_file}' was not found."
                )  # pragma: no mutate
                continue
            except Exception as e:
                logger.warning(
                    f"An error occurred while processing '{csv_file}': {e}"
                )  # pragma: no mutate
                continue

            if "data" not in df.columns:
                continue

            dates = df["data"].astype(str)
            for currency_code, column in self._CURRENCY_COLUMN_MAP.items():
                if column not in df.columns:
                    continue
                for raw_date, raw_rate in zip(dates, df[column]):
                    if pd.isna(raw_rate):
                        continue
                    try:
                        d = datetime.strptime(raw_date, "%Y%m%d")
                    except (ValueError, TypeError):
                        continue
                    try:
                        rate = float(str(raw_rate).replace(",", "."))
                    except (ValueError, TypeError):
                        continue
                    key = (currency_code, d)
                    if key not in lookup:  # preserve first-file-wins ordering
                        lookup[key] = rate

        self._rate_lookup_cache[cache_key] = lookup
        return lookup

    def _currency_for_ticker(self, ticker: str) -> str:
        """Infer currency from ticker suffix (single source of truth).

        Args:
            ticker: The stock ticker.

        Returns:
            Inferred currency code.
        """
        # ASBIS pays its dividend in USD despite the .PL listing. Matched by
        # exact ticker, not substring, so "XASB.PL" does not inherit it.
        if ticker == "ASB.PL":  # pragma: no mutate
            return Currency.USD.value  # pragma: no mutate
        if ticker.endswith(TickerSuffix.US.value):  # pragma: no mutate
            return Currency.USD.value  # pragma: no mutate
        elif ticker.endswith(TickerSuffix.PL.value):  # pragma: no mutate
            return Currency.PLN.value  # pragma: no mutate
        elif ticker.endswith(TickerSuffix.DK.value):  # pragma: no mutate
            return Currency.DKK.value  # pragma: no mutate
        elif ticker.endswith(TickerSuffix.UK.value):  # pragma: no mutate
            return Currency.GBP.value  # pragma: no mutate
        elif any(  # pragma: no mutate
            ticker.endswith(suffix.value) for suffix in TickerSuffix.eurozone_suffixes()
        ):
            return Currency.EUR.value  # pragma: no mutate
        return Currency.USD.value  # pragma: no mutate

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
        return self._currency_for_ticker(ticker)

    def extract_dividend_from_comment(
        self, comment: str
    ) -> tuple[float | None, str | None]:
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

    def get_exchange_rate(
        self, courses_paths: list[str], target_date_str: str, currency: str
    ) -> float:
        """Retrieve the exchange rate for a specific currency on a specific date from CSV files.

        If the date is not found (e.g., weekend or holiday), searches backwards for the previous business day.

        Args:
            courses_paths: List of CSV file paths containing exchange rates.
            target_date_str: The date in 'YYYY-MM-DD' format to search for.
            currency: Currency code ('USD', 'EUR', 'DKK', 'GBP', etc.)

        Returns:
            The exchange rate for the specified currency on the specified date.
            Returns 1.0 for PLN (base currency).

        Raises:
            ExchangeRateUnavailableError: If no NBP rate can be resolved for the
                requested currency on the target date or any business day within
                the configured look-back window. Also raised for currencies not
                in the supported NBP column map.
        """
        # PLN is the base currency, so exchange rate is always 1.0
        if currency == Currency.PLN.value:
            return 1.0

        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")

        if currency not in self._CURRENCY_COLUMN_MAP:
            raise ExchangeRateUnavailableError(
                currency, target_date_str, list(courses_paths)
            )

        lookup = self._build_rate_lookup(list(courses_paths))
        current_date = target_date

        for attempt in range(MAX_EXCHANGE_RATE_LOOKBACK_DAYS):
            rate = lookup.get((currency, current_date))
            if rate is not None:
                if attempt > 0:
                    logger.info(
                        f"Exchange rate for {currency} not found for {target_date_str}, "  # pragma: no mutate
                        f"using rate from {current_date.strftime('%Y-%m-%d')}: {rate}"  # pragma: no mutate
                    )
                return rate

            current_date = current_date - timedelta(days=1)
            while current_date.weekday() in WEEKEND_DAYS:
                current_date = current_date - timedelta(days=1)

        error = ExchangeRateUnavailableError(
            currency, target_date_str, list(courses_paths)
        )
        logger.error(str(error))  # pragma: no mutate
        raise error

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
                f"Column '{date_d1_col}' is required but not found in DataFrame. "  # pragma: no mutate
                "Please run create_date_d_minus_1_column() before calling this method."  # pragma: no mutate
            )

        if shares_col not in self.df.columns:
            self.df[shares_col] = np.nan

        if currency_col not in self.df.columns:
            self.df[currency_col] = None

        date_col = ColumnName.DATE.value

        # Fail fast on rows that have data to process but lack a Date D-1
        # (the loop below relies on it for the FX lookup).
        candidates = self.df[
            self.df[date_col].notna()
            & self.df[amount_col].notna()
            & self.df[comment_col].notna()
        ]
        missing_d1 = candidates[candidates[date_d1_col].isna()]
        if not missing_d1.empty:
            raise ValueError(
                f"'{date_d1_col}' value is missing for row {missing_d1.index[0]}. "  # pragma: no mutate
                "All rows must have valid 'Date D-1' values."  # pragma: no mutate
            )

        _COMPUTED = "_computed"  # pragma: no mutate
        _SKIPPED = pd.Series(
            {
                _COMPUTED: False,
                shares_col: np.nan,
                currency_col: None,
                amount_col: np.nan,
            }
        )
        # Aggregate counter for division-by-zero events so we emit a single
        # log line instead of one per offending row.
        zero_denominator_rows: list[tuple[str, str]] = []

        def _compute_row(row: pd.Series) -> pd.Series:
            if (
                pd.isna(row.get(date_col))
                or pd.isna(row.get(amount_col))
                or pd.isna(row.get(comment_col))
            ):
                return _SKIPPED

            extracted_value, extracted_currency = self.extract_dividend_from_comment(
                row[comment_col]
            )
            if extracted_value is None or extracted_value <= 0:
                return _SKIPPED

            dividend_per_share = extracted_value
            ticker = row[ticker_col]
            currency = self.determine_currency(ticker, extracted_currency)

            exchange_rate = 1.0
            if (
                statement_currency == Currency.PLN.value
                and currency != Currency.PLN.value
            ):
                target_date_str = row[date_d1_col].strftime("%Y-%m-%d")
                exchange_rate = self.get_exchange_rate(
                    courses_paths, target_date_str, currency
                )

            denom = dividend_per_share * exchange_rate
            if denom == 0:
                zero_denominator_rows.append(
                    (ticker, row[date_d1_col].strftime("%Y-%m-%d"))  # pragma: no mutate
                )
                shares = 0.0
            else:
                shares = float(row[amount_col]) / denom

            rounded_shares = _round_shares_half_up(shares)
            return pd.Series(
                {
                    _COMPUTED: True,
                    shares_col: rounded_shares,
                    currency_col: currency,
                    # Total dividend = shares × per-share (was a 2-pass calc).
                    amount_col: rounded_shares * dividend_per_share,
                }
            )

        updates = self.df.apply(_compute_row, axis=1)
        computed = updates[_COMPUTED].astype(bool)
        if computed.any():
            self.df.loc[computed, shares_col] = updates.loc[
                computed, shares_col
            ].astype(float)
            self.df.loc[computed, currency_col] = updates.loc[computed, currency_col]
            self.df.loc[computed, amount_col] = updates.loc[
                computed, amount_col
            ].astype(float)

        if zero_denominator_rows:
            sample = zero_denominator_rows[:3]  # pragma: no mutate
            sample_str = ", ".join(
                f"{tkr} on {dt}" for tkr, dt in sample
            )  # pragma: no mutate
            logger.warning(
                f"Division by zero encountered in shares calculation for "  # pragma: no mutate
                f"{len(zero_denominator_rows)} row(s). Examples: {sample_str}."  # pragma: no mutate
            )

        logger.info(
            "Step 5 - Calculated dividends and updated shares using exchange rates."  # pragma: no mutate
        )
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
            currency_code = self._currency_for_ticker(ticker)
            return f"{dividend} {currency_code}"

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
        date_value = to_date(date_value)

        # Start with D-1 (previous day)
        previous_day = date_value - timedelta(days=1)

        # Skip backwards while it's a weekend
        while previous_day.weekday() in WEEKEND_DAYS:
            previous_day -= timedelta(days=1)

        return previous_day
