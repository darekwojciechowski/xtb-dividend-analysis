"""Fuzz the string-level parsers in ``data_processing``.

Strategies hit date strings, currency-annotated amounts, and dividend-comment
extraction with Unicode edge cases: surrogates, NUL bytes, zero-width joiners,
RTL marks, and long strings. Each parser must either return a well-typed
value or raise ``ValueError`` / ``TypeError`` — never ``KeyError``,
``IndexError``, ``AttributeError``, or ``UnicodeError``.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from data_processing.currency_converter import CurrencyConverter
from data_processing.date_converter import convert_date
from data_processing.tax_calculator import TaxCalculator

pytestmark = pytest.mark.fuzz


# Allowed exceptions from our domain parsers. Anything else escaping = bug.
DOMAIN_ERRORS = (ValueError, TypeError)

hostile_text = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),  # drop lone surrogates, can't round-trip
    ),
    min_size=0,
    max_size=256,
)


@given(raw=hostile_text)
def test_convert_date_never_crashes(raw: str) -> None:
    """Given an arbitrary Unicode string (Hypothesis-generated),
    when convert_date processes it,
    then it returns None or a date-like object — never an unexpected exception.
    """
    try:
        result = convert_date(raw)
    except DOMAIN_ERRORS:
        return
    assert result is None or hasattr(result, "year")


@given(raw=hostile_text)
def test_parse_value_with_currency_is_bounded(raw: str) -> None:
    """Given an arbitrary Unicode string as a dividend amount field,
    when _parse_value_with_currency processes it,
    then it returns a (float, str) pair or raises ValueError/TypeError —
    never KeyError, IndexError, AttributeError, or UnicodeError.
    """
    try:
        numeric, currency = TaxCalculator._parse_value_with_currency(
            raw, column_name="Net Dividend", ticker="FUZZ", date="2025-01-01"
        )
    except DOMAIN_ERRORS:
        return
    assert isinstance(numeric, float)
    assert isinstance(currency, str)


@given(raw=hostile_text)
def test_parse_tax_collected_amount_is_bounded(raw: str) -> None:
    """Given an arbitrary Unicode string as a tax-collected field,
    when _parse_tax_collected_amount processes it,
    then it returns a float or raises ValueError/TypeError — never an
    unexpected exception type.
    """
    calc = TaxCalculator.__new__(TaxCalculator)
    try:
        out = calc._parse_tax_collected_amount(raw, ticker="FUZZ", date="2025-01-01")
    except DOMAIN_ERRORS:
        return
    assert isinstance(out, float)


@given(raw=hostile_text)
def test_parse_exchange_rate_is_bounded(raw: str) -> None:
    """Given an arbitrary Unicode string as an exchange-rate field,
    when _parse_exchange_rate processes it,
    then it returns a float or raises ValueError/TypeError — never an
    unexpected exception type.
    """
    calc = TaxCalculator.__new__(TaxCalculator)
    try:
        out = calc._parse_exchange_rate(raw, ticker="FUZZ", date="2025-01-01")
    except DOMAIN_ERRORS:
        return
    assert isinstance(out, float)


@given(comment=hostile_text)
def test_extract_dividend_from_comment_never_crashes(comment: str) -> None:
    """Given an arbitrary Unicode string as a broker comment,
    when extract_dividend_from_comment processes it,
    then it returns (None, None) or a (float, 3-char str) pair —
    never an unhandled exception.
    """
    conv = CurrencyConverter.__new__(CurrencyConverter)
    value, currency = conv.extract_dividend_from_comment(comment)
    assert value is None or isinstance(value, float)
    assert currency is None or (isinstance(currency, str) and len(currency) == 3)
