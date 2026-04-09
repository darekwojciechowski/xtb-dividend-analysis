"""Structural interfaces (Protocols) for data_processing specialists.

All classes are ``@runtime_checkable`` so callers can use ``isinstance``
checks in tests or guards without importing the concrete implementations.
No existing class needs to change — these are purely additive.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class DataTransformer(Protocol):
    """Base protocol for specialists that own and mutate a DataFrame."""

    df: pd.DataFrame


class CurrencyConverterProtocol(DataTransformer, Protocol):
    def determine_currency(self, ticker: str, extracted_currency: str | None) -> str: ...
    def add_currency_to_dividends(self) -> pd.DataFrame: ...
    def calculate_dividend(
        self,
        courses_paths: list[str],
        statement_currency: str,
        comment_col: str,
        amount_col: str,
    ) -> pd.DataFrame: ...


class ColumnNormalizerProtocol(DataTransformer, Protocol):
    def get_column_name(self, english_name: str, polish_name: str) -> str: ...
    def drop_columns(self, columns: list[str]) -> pd.DataFrame: ...
    def normalize_column_names(self) -> pd.DataFrame: ...


class DividendFilterProtocol(DataTransformer, Protocol):
    def filter_dividends(self) -> pd.DataFrame: ...
    def group_by_dividends(self) -> pd.DataFrame: ...


class TaxCalculatorProtocol(Protocol):
    def calculate_tax_for_pln_statement(self, statement_currency: str) -> pd.DataFrame: ...
    def calculate_tax_for_usd_statement(self, statement_currency: str) -> pd.DataFrame: ...
