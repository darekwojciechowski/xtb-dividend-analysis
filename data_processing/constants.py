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
    CHF = "CHF"
    NOK = "NOK"
    SEK = "SEK"
    CAD = "CAD"


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


# Issuer tax residence used for PIT-38 classification.
#
# These are ratified double-taxation-treaty facts, not deployment configuration,
# so they live here rather than in ``config/settings.py``.
DOMESTIC_ISSUER_COUNTRY: str = "PL"

# Ticker suffix -> issuer tax residence. The suffix is normally the listing
# venue, which usually coincides with tax residence; where it does not, add an
# entry to ``TICKER_COUNTRY_OVERRIDES`` instead of bending this map.
SUFFIX_TO_ISSUER_COUNTRY: dict[str, str] = {
    TickerSuffix.US.value: "US",
    TickerSuffix.PL.value: "PL",
    TickerSuffix.UK.value: "UK",
    TickerSuffix.DK.value: "DK",
    TickerSuffix.FR.value: "FR",
    TickerSuffix.DE.value: "DE",
    TickerSuffix.IE.value: "IE",
    TickerSuffix.NL.value: "NL",
    TickerSuffix.ES.value: "ES",
    TickerSuffix.IT.value: "IT",
    TickerSuffix.BE.value: "BE",
    TickerSuffix.AT.value: "AT",
    TickerSuffix.FI.value: "FI",
    TickerSuffix.PT.value: "PT",
}

# Tickers whose listing venue differs from the issuer's tax residence.
# ASBIS (ASB.PL) is a Cypriot company listed on the WSE: nothing is withheld at
# source, so the full Polish 19% is owed on it.
TICKER_COUNTRY_OVERRIDES: dict[str, str] = {
    "ASB.PL": "CY",
}

# Withholding actually levied at source, keyed by the ticker's listing venue.
#
# Distinct from ``TREATY_DIVIDEND_RATES`` below, and the two must not be merged:
# this table is what the broker deducts (Denmark takes 27%), while the treaty
# table is the *cap* Poland allows as a PIT-38 deduction, keyed by the issuer's
# tax residence (Denmark's cap is 15%). Conflating them either overstates the
# deduction or understates the tax withheld.
#
# Note: the US default assumes a filed W-8BEN. Without one the broker withholds
# 30%, which reaches the pipeline from the statement comment rather than here.
SUFFIX_WITHHOLDING_RATES: dict[str, float] = {
    TickerSuffix.US.value: 0.15,
    TickerSuffix.PL.value: 0.19,  # Belka, withheld by the Polish payer
    TickerSuffix.DK.value: 0.15,
    TickerSuffix.UK.value: 0.0,  # no UK withholding on non-residents
    TickerSuffix.IE.value: 0.15,
    TickerSuffix.FR.value: 0.0,
}

# Tickers whose withholding differs from their listing venue's default.
# Keys must match ``TICKER_COUNTRY_OVERRIDES`` exactly -- a ticker whose issuer
# sits in another country is precisely a ticker whose withholding is not its
# venue's. A contract test pins the two key sets together.
TICKER_WITHHOLDING_OVERRIDES: dict[str, float] = {
    "ASB.PL": 0.0,
}

# Maximum dividend withholding rate Poland's double-taxation treaties allow the
# source state to levy. Used as the "wariant A" cap on the PIT-38 poz. 48
# deduction. Poland is absent by design: domestic issuers are settled by the
# payer and are excluded from the declaration block entirely.
TREATY_DIVIDEND_RATES: dict[str, float] = {
    "US": 0.15,
    "UK": 0.10,
    "IT": 0.10,
    "BE": 0.10,
    "DE": 0.15,
    "FR": 0.15,
    "IE": 0.15,
    "NL": 0.15,
    "ES": 0.15,
    "AT": 0.15,
    "FI": 0.15,
    "PT": 0.15,
    "DK": 0.15,
    "CY": 0.05,
}


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
