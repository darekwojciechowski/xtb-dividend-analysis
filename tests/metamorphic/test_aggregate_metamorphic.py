"""Metamorphic relations for ``DataAggregator.merge_rows_and_reorder``.

These guard the `groupby` path that merges multiple transaction rows for the
same ``(Date, Ticker)`` pair. The relations encode claims that are easy to
break with an accidental change in aggregation strategy.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from data_processing.data_aggregator import DataAggregator

pytestmark = pytest.mark.metamorphic


_SETTINGS = settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)


@st.composite
def raw_rows(draw) -> pd.DataFrame:
    n = draw(st.integers(min_value=2, max_value=8))
    tickers = draw(
        st.lists(
            st.sampled_from(["TXT.PL", "KGH.PL", "AAPL.US"]),
            min_size=n,
            max_size=n,
        )
    )
    dates = draw(
        st.lists(
            st.sampled_from(["2025-01-15", "2025-02-21", "2025-03-10"]),
            min_size=n,
            max_size=n,
        )
    )
    net = draw(
        st.lists(
            st.floats(
                min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False
            ),
            min_size=n,
            max_size=n,
        )
    )
    shares = draw(
        st.lists(
            st.integers(min_value=1, max_value=1000),
            min_size=n,
            max_size=n,
        )
    )
    return pd.DataFrame(
        {
            "Date": dates,
            "Ticker": tickers,
            "Net Dividend": net,
            "Shares": shares,
            "Tax Collected": [0.15] * n,
            "Type": ["Dywidenda"] * n,
            "Comment": ["x"] * n,
        }
    )


def _net_sum(df: pd.DataFrame) -> float:
    agg = DataAggregator(df.copy()).merge_rows_and_reorder()
    return float(pd.to_numeric(agg["Net Dividend"], errors="coerce").fillna(0).sum())


@_SETTINGS
@given(df=raw_rows())
def test_permutation_invariance_of_net_sum(df: pd.DataFrame) -> None:
    """Given a generated transaction DataFrame and a row-shuffled copy,
    when merge_rows_and_reorder is applied to each,
    then the net dividend sums are equal within floating-point tolerance.
    """
    shuffled = df.sample(frac=1, random_state=7).reset_index(drop=True)
    assert math.isclose(_net_sum(df), _net_sum(shuffled), abs_tol=0.01)


@_SETTINGS
@given(df=raw_rows())
def test_duplication_doubles_net_sum(df: pd.DataFrame) -> None:
    """Given a transaction DataFrame and a copy with every row duplicated,
    when merge_rows_and_reorder is applied to each,
    then the doubled net sum equals 2× the base net sum within tolerance.
    """
    doubled = pd.concat([df, df], ignore_index=True)
    assert math.isclose(
        _net_sum(doubled), 2 * _net_sum(df), abs_tol=0.02 * len(df) + 0.01
    )


@_SETTINGS
@given(df=raw_rows())
def test_unique_ticker_count_preserved_under_duplication(df: pd.DataFrame) -> None:
    """Given a transaction DataFrame and a copy with every row duplicated,
    when merge_rows_and_reorder is applied to each,
    then both results contain exactly the same set of tickers.
    """
    doubled = pd.concat([df, df], ignore_index=True)
    base_agg = DataAggregator(df.copy()).merge_rows_and_reorder()
    doubled_agg = DataAggregator(doubled.copy()).merge_rows_and_reorder()
    assert set(base_agg["Ticker"]) == set(doubled_agg["Ticker"])
