"""Constants and Enumerations for XTB Dividend Analysis.

This module provides type-safe enumerations for currencies, ticker suffixes,
and column names used throughout the application.
"""

from __future__ import annotations

from enum import Enum

WEEKEND_DAYS: frozenset[int] = frozenset(
    {5, 6}
)  # Saturday=5, Sunday=6 (Python weekday)
MAX_EXCHANGE_RATE_LOOKBACK_DAYS: int = 10


class Currency(str, Enum):
    """Currency codes used in the application.

    Defines standard ISO 4217 currency codes for all supported currencies
    in the XTB dividend analysis system.
    """

    USD = "USD"
    PLN = "PLN"
    EUR = "EUR"
    DKK = "DKK"
    GBP = "GBP"


class TickerSuffix(str, Enum):
    """Stock exchange suffixes for ticker symbols.

    Defines ticker suffixes for different stock exchanges to determine
    currency, tax rates, and other country-specific parameters.
    """

    US = ".US"
    PL = ".PL"
    UK = ".UK"
    DK = ".DK"
    FR = ".FR"
    DE = ".DE"
    IE = ".IE"
    NL = ".NL"
    ES = ".ES"
    IT = ".IT"
    BE = ".BE"
    AT = ".AT"
    FI = ".FI"
    PT = ".PT"

    @classmethod
    def eurozone_suffixes(cls) -> list[TickerSuffix]:
        """Return all Eurozone country ticker suffixes used for EUR currency determination.

        Returns:
            List of ``TickerSuffix`` values representing Eurozone countries.
        """
        return [
            cls.FR,
            cls.DE,
            cls.IE,
            cls.NL,
            cls.ES,
            cls.IT,
            cls.BE,
            cls.AT,
            cls.FI,
            cls.PT,
        ]


class ColumnName(str, Enum):
    """Standard column names used throughout processing.

    Centralized definition of all DataFrame column names to ensure consistency
    across the application and eliminate magic strings.
    """

    DATE = "Date"
    TICKER = "Ticker"
    SHARES = "Shares"
    NET_DIVIDEND = "Net Dividend"
    TAX_COLLECTED = "Tax Collected"
    TAX_COLLECTED_RAW = "Tax Collected Raw"
    TAX_COLLECTED_PCT = "Tax Collected %"
    TAX_AMOUNT_PLN = "Tax Amount PLN"
    DATE_D_MINUS_1 = "Date D-1"
    EXCHANGE_RATE_D_MINUS_1 = "Exchange Rate D-1"
    TAX_COLLECTED_AMOUNT = "Tax Collected Amount"
    COMMENT = "Comment"
    TYPE = "Type"
    AMOUNT = "Amount"
    COLORED_TICKER = "Colored Ticker"
    CURRENCY = "Currency"


class TransactionType(str, Enum):
    """Transaction type labels used to filter dividend-related rows."""

    DIVIDEND_EN = "Dividend"
    DIVIDEND_PL = "Dywidenda"
    DIVIDEND_ALT = "DIVIDENT"
    WITHHOLDING_TAX = "Withholding Tax"
    WITHHOLDING_TAX_PL = "Podatek od dywidend"

    @classmethod
    def dividend_types(cls) -> list[str]:
        """Return all dividend-related transaction type values."""
        return [t.value for t in cls]
