"""Metamorphic relations for ``TaxCalculator`` on PLN statements.

Each test runs the tax calculation twice — once on the base DataFrame and
once on a transformed copy — and asserts a mathematical invariant between
the two totals. This catches bugs (lost rows, wrong accumulator reset,
rounding drift) without needing a pre-computed oracle.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings

from data_processing.tax_calculator import TaxCalculator

from .conftest import dividend_rows

pytestmark = pytest.mark.metamorphic


_SETTINGS = settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)


def _total_tax(df: pd.DataFrame) -> float:
    calc = TaxCalculator(df.copy(), polish_tax_rate=0.19)
    out = calc.calculate_tax_for_pln_statement("PLN")
    return TaxCalculator.calculate_total_tax_amount(out)


@_SETTINGS
@given(df=dividend_rows())
def test_permutation_invariance(df: pd.DataFrame) -> None:
    """Given a generated dividend DataFrame and a row-shuffled copy of it,
    when the total tax is calculated for each,
    then both totals are equal within floating-point tolerance.
    """
    shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)
    assert math.isclose(_total_tax(df), _total_tax(shuffled), abs_tol=0.01)


@_SETTINGS
@given(df=dividend_rows(max_rows=4))
def test_additivity_under_split(df: pd.DataFrame) -> None:
    """Given a dividend DataFrame split into two halves,
    when the total tax is calculated for the full set and for each half,
    then the full total equals the sum of the two partial totals within
    per-row rounding tolerance.
    """
    if len(df) < 2:
        return
    midpoint = len(df) // 2
    left = df.iloc[:midpoint].reset_index(drop=True)
    right = df.iloc[midpoint:].reset_index(drop=True)

    combined = _total_tax(df)
    split_sum = _total_tax(left) + _total_tax(right)

    # Per-row rounding of +/- 0.005 PLN can accumulate; bound it by row count.
    assert math.isclose(combined, split_sum, abs_tol=0.01 * len(df))


@_SETTINGS
@given(df=dividend_rows())
def test_duplication_doubles_tax(df: pd.DataFrame) -> None:
    """Given a dividend DataFrame and a copy with every row duplicated,
    when the total tax is calculated for each,
    then the doubled DataFrame's total is exactly twice the base total
    within per-row rounding tolerance.
    """
    doubled = pd.concat([df, df], ignore_index=True)

    base = _total_tax(df)
    twice = _total_tax(doubled)

    assert math.isclose(twice, 2 * base, abs_tol=0.01 * len(df) + 0.01)


@_SETTINGS
@given(df=dividend_rows())
def test_zero_tax_row_insertion_does_not_change_total(df: pd.DataFrame) -> None:
    """Given a dividend DataFrame augmented with a row whose withholding
    already meets the Belka rate (contributing "-" to PLN tax),
    when the total tax is calculated for both,
    then the totals are equal — the extra row contributes nothing.
    """
    # A row whose withholding already meets/exceeds Belka rate contributes
    # ``"-"`` and must not move the PLN total.
    extra = pd.DataFrame(
        [
            {
                "Date": "2025-02-21",
                "Ticker": "FULLY.TAXED",
                "Net Dividend": "100.00 PLN",
                "Tax Collected": 0.19,
                "Tax Collected Amount": "19.00 PLN",
                "Exchange Rate D-1": "-",
            }
        ]
    )
    augmented = pd.concat([df, extra], ignore_index=True)

    assert math.isclose(_total_tax(df), _total_tax(augmented), abs_tol=0.01)


@_SETTINGS
@given(df=dividend_rows())
def test_linear_scaling_of_dividends(df: pd.DataFrame) -> None:
    """Given a dividend DataFrame and a scaled copy where all amounts are
    multiplied by 2,
    when the total tax is calculated for each,
    then the scaled total equals 2× the base total within accumulated
    per-row rounding tolerance.
    """
    k = 2.0

    scaled = df.copy()

    def _scale_amount(s: str, factor: float) -> str:
        value, currency = s.split()
        return f"{float(value) * factor:.2f} {currency}"

    scaled["Net Dividend"] = scaled["Net Dividend"].apply(lambda s: _scale_amount(s, k))
    scaled["Tax Collected Amount"] = scaled["Tax Collected Amount"].apply(
        lambda s: _scale_amount(s, k)
    )

    base = _total_tax(df)
    scaled_total = _total_tax(scaled)

    # Tolerance grows with row count because each row re-rounds to 2 d.p.
    assert math.isclose(scaled_total, k * base, abs_tol=0.02 * len(df) + 0.01)
