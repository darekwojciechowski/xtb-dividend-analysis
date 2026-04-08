"""Shared fixtures, helpers, and budget constants for performance tests."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

from data_processing.constants import ColumnName

# ---------------------------------------------------------------------------
# Performance budget constants
# Adjust only here when hardware budgets change, never inside tests.
# ---------------------------------------------------------------------------

BUDGET_FILTER_10K_S: float = 0.5
BUDGET_FILTER_100K_S: float = 5.0
BUDGET_GROUP_10K_S: float = 0.5
BUDGET_CURRENCY_DETERMINE_10K_S: float = 1.0
BUDGET_EXTRACT_COMMENT_10K_S: float = 1.0
BUDGET_TAX_EXTRACT_10K_S: float = 1.0
BUDGET_TAX_CALCULATE_PLN_1K_S: float = 1.0
BUDGET_TAX_CALCULATE_PLN_5K_S: float = 5.0
BUDGET_PIPELINE_1K_S: float = 2.0

BUDGET_MEMORY_FILTER_100K_BYTES: int = 100 * 1024 * 1024  # 100 MB
BUDGET_MEMORY_PIPELINE_1K_BYTES: int = 20 * 1024 * 1024  # 20 MB

SCALABILITY_LINEAR_MULTIPLIER: float = 15.0

TIMING_REPEATS: int = 5

# ---------------------------------------------------------------------------
# Shared ticker / comment pools
# ---------------------------------------------------------------------------

_TICKERS_US = ["AAPL.US", "MSFT.US", "JNJ.US", "KO.US", "T.US"]
_TICKERS_PL = ["PKN.PL", "PKO.PL", "CDR.PL"]
_TICKERS_EU = ["AIR.FR", "ALV.DE", "PHIA.NL"]
_ALL_TICKERS = _TICKERS_US + _TICKERS_PL + _TICKERS_EU
_COMMENTS = [
    "USD 0.2500/ SHR WHT 15%",
    "USD 1.1000/ SHR WHT 15%",
    "PLN 3.0000/ SHR WHT 19%",
    "EUR 0.5000/ SHR WHT 15%",
    "Dividend reinvestment plan",
    "0.3000/ SHR",
]
_TYPES_DIV = [
    "Dividend",
    "Dywidenda",
    "DIVIDENT",
    "Withholding Tax",
    "Podatek od dywidend",
]
_TYPES_OTHER = ["Open", "Close", "Deposit", "Withdrawal"]


# ---------------------------------------------------------------------------
# Data builders
# ---------------------------------------------------------------------------


def _make_raw_transaction_df(n_rows: int, rng: np.random.Generator) -> pd.DataFrame:
    """Build a realistic raw transactions DataFrame of *n_rows* rows.

    Approximately 60 % of rows are dividend-related to simulate a real
    broker statement with mixed transaction types.

    Args:
        n_rows: Number of rows to generate.
        rng: Seeded NumPy random generator for reproducible data.

    Returns:
        DataFrame with columns Date, Ticker, Type, Amount, Comment.
    """
    n_div = int(n_rows * 0.6)
    n_other = n_rows - n_div

    div_types = rng.choice(_TYPES_DIV, size=n_div)
    other_types = rng.choice(_TYPES_OTHER, size=n_other)
    all_types = np.concatenate([div_types, other_types])
    rng.shuffle(all_types)

    return pd.DataFrame(
        {
            ColumnName.DATE.value: pd.date_range(
                "2024-01-01", periods=n_rows, freq="h"
            ),
            ColumnName.TICKER.value: rng.choice(_ALL_TICKERS, size=n_rows),
            ColumnName.TYPE.value: all_types,
            ColumnName.AMOUNT.value: rng.uniform(1.0, 500.0, size=n_rows).round(4),
            ColumnName.COMMENT.value: rng.choice(_COMMENTS, size=n_rows),
        }
    )


def _make_tax_calc_df(n_rows: int, rng: np.random.Generator) -> pd.DataFrame:
    """Build a pre-processed DataFrame suitable for TaxCalculator tests.

    Args:
        n_rows: Number of rows to generate.
        rng: Seeded NumPy random generator.

    Returns:
        DataFrame with all columns required by ``calculate_tax_for_pln_statement``.
    """
    net_vals = rng.uniform(5.0, 500.0, size=n_rows).round(4)
    currencies = rng.choice(["USD", "PLN", "EUR"], size=n_rows)
    wht_pcts = rng.choice([0.0, 0.15, 0.19, 0.27], size=n_rows)
    wht_amounts = (net_vals * wht_pcts).round(4)
    rates = np.where(
        currencies == "PLN", 1.0, rng.uniform(3.5, 4.5, size=n_rows).round(4)
    )

    def _fmt_net(v: float, c: str) -> str:
        return f"{v} {c}"

    def _fmt_wht(v: float, c: str, pct: float) -> str:
        return "-" if pct == 0.0 else f"{v} {c}"

    def _fmt_rate(r: float, c: str) -> str:
        return "-" if c == "PLN" else f"{r} PLN"

    return pd.DataFrame(
        {
            ColumnName.DATE.value: pd.date_range(
                "2024-01-01", periods=n_rows, freq="h"
            ).astype(str),
            ColumnName.TICKER.value: rng.choice(_ALL_TICKERS, size=n_rows),
            ColumnName.NET_DIVIDEND.value: [
                _fmt_net(v, c) for v, c in zip(net_vals, currencies)
            ],
            ColumnName.TAX_COLLECTED.value: wht_pcts,
            ColumnName.TAX_COLLECTED_AMOUNT.value: [
                _fmt_wht(v, c, p) for v, c, p in zip(wht_amounts, currencies, wht_pcts)
            ],
            ColumnName.EXCHANGE_RATE_D_MINUS_1.value: [
                _fmt_rate(r, c) for r, c in zip(rates, currencies)
            ],
        }
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _measure_ns(fn, repeat: int = TIMING_REPEATS) -> list[float]:
    """Run *fn* *repeat* times and return wall-clock durations in seconds.

    Args:
        fn: Zero-argument callable to benchmark.
        repeat: Number of repetitions.

    Returns:
        List of elapsed times in seconds.
    """
    results: list[float] = []
    for _ in range(repeat):
        start = time.perf_counter_ns()
        fn()
        elapsed = (time.perf_counter_ns() - start) / 1e9
        results.append(elapsed)
    return results


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def rng() -> np.random.Generator:
    """Session-scoped seeded random generator for reproducible data.

    Returns:
        Seeded NumPy Generator.
    """
    return np.random.default_rng(seed=42)


@pytest.fixture(scope="session")
def raw_df_10k(rng: np.random.Generator) -> pd.DataFrame:
    """Session-scoped 10 000-row raw transactions DataFrame.

    Returns:
        DataFrame with 10 000 rows.
    """
    return _make_raw_transaction_df(10_000, rng)


@pytest.fixture(scope="session")
def raw_df_100k(rng: np.random.Generator) -> pd.DataFrame:
    """Session-scoped 100 000-row raw transactions DataFrame.

    Returns:
        DataFrame with 100 000 rows.
    """
    return _make_raw_transaction_df(100_000, rng)


@pytest.fixture(scope="session")
def tax_calc_df_1k(rng: np.random.Generator) -> pd.DataFrame:
    """Session-scoped 1 000-row pre-processed DataFrame for TaxCalculator.

    Returns:
        DataFrame with 1 000 rows.
    """
    return _make_tax_calc_df(1_000, rng)


@pytest.fixture(scope="session")
def tax_calc_df_5k(rng: np.random.Generator) -> pd.DataFrame:
    """Session-scoped 5 000-row pre-processed DataFrame for TaxCalculator.

    Returns:
        DataFrame with 5 000 rows.
    """
    return _make_tax_calc_df(5_000, rng)
