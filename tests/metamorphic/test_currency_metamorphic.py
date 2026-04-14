"""Metamorphic relations for ``CurrencyConverter``.

No oracle — instead we assert logical invariants:

* **Idempotence of currency inference**: calling ``_currency_for_ticker`` twice
  on the same ticker yields the same currency. Bug signal: hidden mutable
  state in the converter.
* **Business-day round-trip**: for any weekday date, applying
  ``get_previous_business_day`` lands on another weekday (never a weekend).
* **Comment parsing whitespace invariance**: extracted dividend/currency must
  not change when the comment is padded with surrounding whitespace.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from data_processing.currency_converter import CurrencyConverter

pytestmark = pytest.mark.metamorphic


@given(
    ticker=st.sampled_from(
        ["TXT.PL", "KGH.PL", "AAPL.US", "SAN.DE", "BNP.FR", "NOVO.DK", "LLOY.UK"]
    )
)
def test_currency_inference_is_idempotent(ticker: str) -> None:
    """Given a known ticker symbol,
    when _currency_for_ticker is called twice on the same CurrencyConverter,
    then both calls return the same currency — no hidden mutable state.
    """
    conv = CurrencyConverter(pd.DataFrame())
    assert conv._currency_for_ticker(ticker) == conv._currency_for_ticker(ticker)


@given(base=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)))
def test_previous_business_day_never_weekend(base: date) -> None:
    """Given any calendar date between 2020 and 2030,
    when get_previous_business_day is applied,
    then the result is a weekday (Monday–Friday) strictly before the next
    calendar day.
    """
    prev = CurrencyConverter.get_previous_business_day(base)
    assert prev.weekday() < 5
    assert prev < base + timedelta(days=1)


@given(
    pre=st.text(alphabet=" \t", max_size=4),
    post=st.text(alphabet=" \t", max_size=4),
)
def test_comment_extraction_whitespace_invariant(pre: str, post: str) -> None:
    """Given a canonical broker comment and a whitespace-padded variant,
    when extract_dividend_from_comment processes each,
    then both calls return the same (value, currency) pair.
    """
    conv = CurrencyConverter(pd.DataFrame())
    canonical = "TXT.PL PLN 1.6600/ SHR"
    padded = f"{pre}{canonical}{post}"

    assert conv.extract_dividend_from_comment(
        canonical
    ) == conv.extract_dividend_from_comment(padded)
