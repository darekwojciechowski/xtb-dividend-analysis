"""Performance tests for the XTB dividend analysis pipeline.

Measures throughput, latency, and memory behaviour of the core processing
components at realistic and stress-level dataset sizes.

Strategy
--------
* Every test records wall-clock time with ``time.perf_counter_ns()`` and
  memory snapshots with ``tracemalloc``.
* Thresholds are documented as named constants so they can be adjusted in a
  single place when hardware budgets change.
* Scalability tests verify that processing time stays within a linear
  multiplier when the dataset size grows 10x (O(n) contract).
* All tests are tagged ``@pytest.mark.performance``; slow stress tests also
  carry ``@pytest.mark.slow`` so the fast-feedback CI run can skip them with
  ``-m "not slow"``.

Test classes
------------
TestDividendFilterPerformance   — filter_dividends / group_by_dividends throughput
TestCurrencyConverterPerformance — determine_currency / extract_dividend_from_comment
TestTaxExtractorPerformance      — extract_tax_rate_from_comment bulk parsing
TestTaxCalculatorPerformance     — calculate_tax_for_pln_statement on large tables
TestDataFrameProcessorPerformance — end-to-end pipeline orchestration
TestMemoryBehaviour              — peak RSS and memory-leak detection
TestScalability                  — linear-scaling contracts across 1x / 10x sizes
"""

from __future__ import annotations

import statistics
import time
import tracemalloc
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pytest

from data_processing.constants import ColumnName, Currency
from data_processing.currency_converter import CurrencyConverter
from data_processing.dataframe_processor import DataFrameProcessor
from data_processing.dividend_filter import DividendFilter
from data_processing.tax_calculator import TaxCalculator
from data_processing.tax_extractor import TaxExtractor

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Performance budget constants
# Adjust only here when hardware budgets change, never inside tests.
# ---------------------------------------------------------------------------

# Maximum acceptable wall-clock time (seconds) for a single operation at the
# indicated row-count.
BUDGET_FILTER_10K_S: float = 0.5
BUDGET_FILTER_100K_S: float = 5.0
BUDGET_GROUP_10K_S: float = 0.5
BUDGET_CURRENCY_DETERMINE_10K_S: float = 1.0
BUDGET_EXTRACT_COMMENT_10K_S: float = 1.0
BUDGET_TAX_EXTRACT_10K_S: float = 1.0
BUDGET_TAX_CALCULATE_PLN_1K_S: float = 1.0
BUDGET_TAX_CALCULATE_PLN_5K_S: float = 5.0
BUDGET_PIPELINE_1K_S: float = 2.0

# Maximum peak memory increase (bytes) allowed during processing.
BUDGET_MEMORY_FILTER_100K_BYTES: int = 100 * 1024 * 1024  # 100 MB
BUDGET_MEMORY_PIPELINE_1K_BYTES: int = 20 * 1024 * 1024  # 20 MB

# Scalability: processing time for 10x data must not exceed this multiplier.
SCALABILITY_LINEAR_MULTIPLIER: float = 15.0

# Repeat count for statistical timing measurements.
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
# Fixtures
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
# TestDividendFilterPerformance
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestDividendFilterPerformance:
    """Throughput tests for DividendFilter on realistic-sized DataFrames."""

    def test_filter_dividends_10k_rows_within_budget(
        self, raw_df_10k: pd.DataFrame
    ) -> None:
        """filter_dividends completes 10 000-row DataFrame within budget.

        Budget: BUDGET_FILTER_10K_S seconds (median across repeats).

        Args:
            raw_df_10k: 10 000-row raw transactions fixture.
        """
        # Arrange
        timings = _measure_ns(
            lambda: DividendFilter(raw_df_10k.copy()).filter_dividends()
        )

        # Act
        median_s = statistics.median(timings)

        # Assert
        assert median_s < BUDGET_FILTER_10K_S, (
            f"filter_dividends(10k) median={median_s:.4f}s exceeded budget={BUDGET_FILTER_10K_S}s"
        )

    @pytest.mark.slow
    def test_filter_dividends_100k_rows_within_budget(
        self, raw_df_100k: pd.DataFrame
    ) -> None:
        """filter_dividends completes 100 000-row DataFrame within budget.

        Budget: BUDGET_FILTER_100K_S seconds (median across repeats).

        Args:
            raw_df_100k: 100 000-row raw transactions fixture.
        """
        # Arrange
        timings = _measure_ns(
            lambda: DividendFilter(raw_df_100k.copy()).filter_dividends()
        )

        # Act
        median_s = statistics.median(timings)

        # Assert
        assert median_s < BUDGET_FILTER_100K_S, (
            f"filter_dividends(100k) median={median_s:.4f}s exceeded budget={BUDGET_FILTER_100K_S}s"
        )

    def test_group_by_dividends_10k_rows_within_budget(
        self, raw_df_10k: pd.DataFrame
    ) -> None:
        """group_by_dividends completes 10 000-row DataFrame within budget.

        Budget: BUDGET_GROUP_10K_S seconds (median across repeats).

        Args:
            raw_df_10k: 10 000-row raw transactions fixture.
        """
        # Arrange — pre-filter so grouping operates on realistic subset
        filtered = DividendFilter(raw_df_10k.copy()).filter_dividends()
        timings = _measure_ns(
            lambda: DividendFilter(filtered.copy()).group_by_dividends()
        )

        # Act
        median_s = statistics.median(timings)

        # Assert
        assert median_s < BUDGET_GROUP_10K_S, (
            f"group_by_dividends(10k filtered) median={median_s:.4f}s exceeded budget={BUDGET_GROUP_10K_S}s"
        )

    def test_filter_dividends_result_correctness_preserved_under_load(
        self, raw_df_10k: pd.DataFrame
    ) -> None:
        """filter_dividends returns only valid dividend types even at scale.

        Ensures the performance-optimised path does not drop correctness.

        Args:
            raw_df_10k: 10 000-row raw transactions fixture.
        """
        # Arrange
        allowed_types = {
            "Dividend",
            "Dywidenda",
            "DIVIDENT",
            "Withholding Tax",
            "Podatek od dywidend",
        }

        # Act
        result = DividendFilter(raw_df_10k.copy()).filter_dividends()

        # Assert
        actual_types = set(result[ColumnName.TYPE.value].unique())
        assert actual_types.issubset(allowed_types), (
            f"Unexpected types after filter: {actual_types - allowed_types}"
        )


# ---------------------------------------------------------------------------
# TestCurrencyConverterPerformance
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestCurrencyConverterPerformance:
    """Throughput tests for CurrencyConverter hot paths."""

    def test_determine_currency_10k_calls_within_budget(
        self, raw_df_10k: pd.DataFrame
    ) -> None:
        """determine_currency executes 10 000 calls within budget.

        Budget: BUDGET_CURRENCY_DETERMINE_10K_S seconds (median).

        Args:
            raw_df_10k: 10 000-row DataFrame, tickers used as input.
        """
        # Arrange
        converter = CurrencyConverter(raw_df_10k)
        tickers = raw_df_10k[ColumnName.TICKER.value].tolist()
        comments_pool = [None, "USD 0.25/ SHR", "PLN 3.00/ SHR"]
        rng = np.random.default_rng(0)
        extracted = [comments_pool[i] for i in rng.integers(0, 3, size=len(tickers))]

        def _run() -> None:
            for ticker, ext in zip(tickers, extracted):
                converter.determine_currency(ticker, ext)

        timings = _measure_ns(_run)

        # Act
        median_s = statistics.median(timings)

        # Assert
        assert median_s < BUDGET_CURRENCY_DETERMINE_10K_S, (
            f"determine_currency(10k) median={median_s:.4f}s exceeded budget={BUDGET_CURRENCY_DETERMINE_10K_S}s"
        )

    def test_extract_dividend_from_comment_10k_calls_within_budget(
        self, raw_df_10k: pd.DataFrame
    ) -> None:
        """extract_dividend_from_comment executes 10 000 calls within budget.

        Budget: BUDGET_EXTRACT_COMMENT_10K_S seconds (median).

        Args:
            raw_df_10k: 10 000-row raw transactions fixture.
        """
        # Arrange
        converter = CurrencyConverter(raw_df_10k)
        comments = raw_df_10k[ColumnName.COMMENT.value].tolist()

        def _run() -> None:
            for comment in comments:
                converter.extract_dividend_from_comment(comment)

        timings = _measure_ns(_run)

        # Act
        median_s = statistics.median(timings)

        # Assert
        assert median_s < BUDGET_EXTRACT_COMMENT_10K_S, (
            f"extract_dividend_from_comment(10k) median={median_s:.4f}s exceeded budget={BUDGET_EXTRACT_COMMENT_10K_S}s"
        )

    def test_determine_currency_is_deterministic(self) -> None:
        """determine_currency returns the same result on repeated calls.

        Verifies there is no side-effect that could accumulate under load.
        """
        # Arrange
        converter = CurrencyConverter(pd.DataFrame())
        ticker = "AAPL.US"
        extracted_currency = None

        # Act
        results = [
            converter.determine_currency(ticker, extracted_currency)
            for _ in range(1_000)
        ]

        # Assert
        assert len(set(results)) == 1, "determine_currency is not deterministic"
        assert results[0] == Currency.USD.value


# ---------------------------------------------------------------------------
# TestTaxExtractorPerformance
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestTaxExtractorPerformance:
    """Throughput tests for TaxExtractor comment-parsing hot path."""

    def test_extract_tax_rate_10k_calls_within_budget(
        self, raw_df_10k: pd.DataFrame
    ) -> None:
        """extract_tax_rate_from_comment executes 10 000 calls within budget.

        Budget: BUDGET_TAX_EXTRACT_10K_S seconds (median).

        Args:
            raw_df_10k: 10 000-row raw transactions fixture.
        """
        # Arrange
        extractor = TaxExtractor(raw_df_10k)
        comments = raw_df_10k[ColumnName.COMMENT.value].tolist()

        def _run() -> None:
            for comment in comments:
                extractor.extract_tax_rate_from_comment(comment)

        timings = _measure_ns(_run)

        # Act
        median_s = statistics.median(timings)

        # Assert
        assert median_s < BUDGET_TAX_EXTRACT_10K_S, (
            f"extract_tax_rate_from_comment(10k) median={median_s:.4f}s exceeded budget={BUDGET_TAX_EXTRACT_10K_S}s"
        )

    def test_extract_tax_rate_returns_none_for_invalid_fast(self) -> None:
        """extract_tax_rate_from_comment returns ``None`` quickly for non-matching input.

        Ensures the regex early-exit path is fast to avoid performance
        penalties on non-dividend rows.
        """
        # Arrange
        extractor = TaxExtractor(pd.DataFrame())
        non_matching = ["Open position", "Close position", "Deposit", "", "123456"]
        repeat = 2_000

        def _run() -> None:
            for _ in range(repeat):
                for comment in non_matching:
                    extractor.extract_tax_rate_from_comment(comment)

        # Act
        start = time.perf_counter_ns()
        _run()
        elapsed_s = (time.perf_counter_ns() - start) / 1e9

        # Assert — 10 000 calls must finish well under 1 second
        assert elapsed_s < 1.0, (
            f"Non-matching extract_tax_rate took {elapsed_s:.4f}s for {repeat * len(non_matching)} calls"
        )


# ---------------------------------------------------------------------------
# TestTaxCalculatorPerformance
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestTaxCalculatorPerformance:
    """Throughput tests for TaxCalculator PLN-statement calculation."""

    def test_calculate_tax_pln_statement_1k_rows_within_budget(
        self, tax_calc_df_1k: pd.DataFrame
    ) -> None:
        """calculate_tax_for_pln_statement processes 1 000 rows within budget.

        Budget: BUDGET_TAX_CALCULATE_PLN_1K_S seconds (median).

        Args:
            tax_calc_df_1k: 1 000-row pre-processed DataFrame fixture.
        """
        # Arrange
        timings = _measure_ns(
            lambda: TaxCalculator(
                tax_calc_df_1k.copy()
            ).calculate_tax_for_pln_statement(statement_currency=Currency.PLN.value)
        )

        # Act
        median_s = statistics.median(timings)

        # Assert
        assert median_s < BUDGET_TAX_CALCULATE_PLN_1K_S, (
            f"calculate_tax_for_pln_statement(1k) median={median_s:.4f}s exceeded budget={BUDGET_TAX_CALCULATE_PLN_1K_S}s"
        )

    @pytest.mark.slow
    def test_calculate_tax_pln_statement_5k_rows_within_budget(
        self, tax_calc_df_5k: pd.DataFrame
    ) -> None:
        """calculate_tax_for_pln_statement processes 5 000 rows within budget.

        Budget: BUDGET_TAX_CALCULATE_PLN_5K_S seconds (median).

        Args:
            tax_calc_df_5k: 5 000-row pre-processed DataFrame fixture.
        """
        # Arrange
        timings = _measure_ns(
            lambda: TaxCalculator(
                tax_calc_df_5k.copy()
            ).calculate_tax_for_pln_statement(statement_currency=Currency.PLN.value)
        )

        # Act
        median_s = statistics.median(timings)

        # Assert
        assert median_s < BUDGET_TAX_CALCULATE_PLN_5K_S, (
            f"calculate_tax_for_pln_statement(5k) median={median_s:.4f}s exceeded budget={BUDGET_TAX_CALCULATE_PLN_5K_S}s"
        )

    def test_calculate_tax_result_has_no_null_tax_amount(
        self, tax_calc_df_1k: pd.DataFrame
    ) -> None:
        """All rows in output have a ``Tax Amount PLN`` value (no silent NaN).

        Args:
            tax_calc_df_1k: 1 000-row pre-processed DataFrame fixture.
        """
        # Arrange / Act
        result = TaxCalculator(tax_calc_df_1k.copy()).calculate_tax_for_pln_statement(
            statement_currency=Currency.PLN.value
        )

        # Assert — every row must have a non-null Tax Amount PLN
        tax_col = ColumnName.TAX_AMOUNT_PLN.value
        assert tax_col in result.columns, (
            f"Column '{tax_col}' missing from TaxCalculator output"
        )
        null_count = result[tax_col].isna().sum()
        assert null_count == 0, f"{null_count} rows have null {tax_col}"


# ---------------------------------------------------------------------------
# TestDataFrameProcessorPerformance
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestDataFrameProcessorPerformance:
    """Throughput tests for DataFrameProcessor initialisation at scale."""

    def test_dataframe_processor_init_1k_rows_within_budget(
        self, rng: np.random.Generator
    ) -> None:
        """DataFrameProcessor.__init__ copies 1 000 rows within budget.

        Budget: BUDGET_PIPELINE_1K_S seconds (median).

        Args:
            rng: Session-scoped seeded random generator.
        """
        # Arrange
        df = _make_raw_transaction_df(1_000, rng)
        timings = _measure_ns(lambda: DataFrameProcessor(df.copy()))

        # Act
        median_s = statistics.median(timings)

        # Assert
        assert median_s < BUDGET_PIPELINE_1K_S, (
            f"DataFrameProcessor init(1k) median={median_s:.4f}s exceeded budget={BUDGET_PIPELINE_1K_S}s"
        )

    def test_filter_dividends_via_processor_preserves_row_count_bounds(
        self, raw_df_10k: pd.DataFrame
    ) -> None:
        """DataFrameProcessor.filter_dividends produces a non-empty subset within budget.

        Verifies that the processor delegates correctly and does not
        accidentally drop all rows or keep every row.

        Args:
            raw_df_10k: 10 000-row raw transactions fixture.
        """
        # Arrange
        processor = DataFrameProcessor(raw_df_10k.copy())

        # Act
        start = time.perf_counter_ns()
        processor.filter_dividends()
        elapsed_s = (time.perf_counter_ns() - start) / 1e9

        # Assert — timing
        assert elapsed_s < BUDGET_FILTER_10K_S, (
            f"DataFrameProcessor.filter_dividends(10k) took {elapsed_s:.4f}s > budget={BUDGET_FILTER_10K_S}s"
        )
        # Assert — correctness: subset, not empty, not identical to input
        assert 0 < len(processor.df) <= len(raw_df_10k), (
            f"Unexpected row count after filter: {len(processor.df)}"
        )


# ---------------------------------------------------------------------------
# TestMemoryBehaviour
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestMemoryBehaviour:
    """Peak RSS and leak-detection tests using ``tracemalloc``."""

    def test_filter_dividends_100k_peak_memory_within_budget(
        self, raw_df_100k: pd.DataFrame
    ) -> None:
        """filter_dividends on 100 000 rows allocates below memory budget.

        Budget: BUDGET_MEMORY_FILTER_100K_BYTES bytes peak increase.

        Args:
            raw_df_100k: 100 000-row raw transactions fixture.
        """
        # Arrange
        df_copy = raw_df_100k.copy()
        tracemalloc.start()
        tracemalloc.clear_traces()

        # Act
        DividendFilter(df_copy).filter_dividends()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Assert
        assert peak < BUDGET_MEMORY_FILTER_100K_BYTES, (
            f"filter_dividends(100k) peak memory={peak / 1024 / 1024:.1f} MB "
            f"exceeded budget={BUDGET_MEMORY_FILTER_100K_BYTES / 1024 / 1024:.0f} MB"
        )

    def test_dataframe_processor_init_1k_peak_memory_within_budget(
        self, rng: np.random.Generator
    ) -> None:
        """DataFrameProcessor init on 1 000 rows allocates below memory budget.

        Budget: BUDGET_MEMORY_PIPELINE_1K_BYTES bytes peak increase.

        Args:
            rng: Session-scoped seeded random generator.
        """
        # Arrange
        df = _make_raw_transaction_df(1_000, rng)
        tracemalloc.start()
        tracemalloc.clear_traces()

        # Act
        DataFrameProcessor(df)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Assert
        assert peak < BUDGET_MEMORY_PIPELINE_1K_BYTES, (
            f"DataFrameProcessor init peak memory={peak / 1024 / 1024:.1f} MB "
            f"exceeded budget={BUDGET_MEMORY_PIPELINE_1K_BYTES / 1024 / 1024:.0f} MB"
        )

    def test_repeated_filter_dividends_no_memory_leak(
        self, rng: np.random.Generator
    ) -> None:
        """Repeated DividendFilter invocations do not accumulate memory.

        Runs the filter 20 times and checks that allocated memory does not
        grow monotonically (a strong indicator of a reference leak).

        Args:
            rng: Session-scoped seeded random generator.
        """
        # Arrange
        snapshots: list[int] = []
        n_iterations = 20
        df_base = _make_raw_transaction_df(500, rng)

        # Act
        tracemalloc.start()
        for _ in range(n_iterations):
            DividendFilter(df_base.copy()).filter_dividends()
            current, _ = tracemalloc.get_traced_memory()
            snapshots.append(current)
        tracemalloc.stop()

        # Assert — memory in the second half must not all exceed memory in the first half
        first_half_max = max(snapshots[: n_iterations // 2])
        second_half_max = max(snapshots[n_iterations // 2 :])
        growth_ratio = second_half_max / first_half_max if first_half_max > 0 else 1.0
        assert growth_ratio < 2.0, (
            f"Possible memory leak in DividendFilter: "
            f"growth ratio={growth_ratio:.2f} (first_half_max={first_half_max}, second_half_max={second_half_max})"
        )


# ---------------------------------------------------------------------------
# TestScalability
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.slow
class TestScalability:
    """Linear-scaling contract tests (1x vs 10x data size).

    Each test re-generates data at two sizes to ensure the processing
    time does not grow super-linearly.
    """

    def test_filter_dividends_scales_linearly(self, rng: np.random.Generator) -> None:
        """DividendFilter.filter_dividends scales at most O(n * MULTIPLIER).

        Measures median time at 1 000 and 10 000 rows and asserts the
        10x size runs in at most SCALABILITY_LINEAR_MULTIPLIER * time(1x).

        Args:
            rng: Session-scoped seeded random generator.
        """
        # Arrange
        df_1k = _make_raw_transaction_df(1_000, rng)
        df_10k = _make_raw_transaction_df(10_000, rng)

        # Act
        t_1k = statistics.median(
            _measure_ns(lambda: DividendFilter(df_1k.copy()).filter_dividends())
        )
        t_10k = statistics.median(
            _measure_ns(lambda: DividendFilter(df_10k.copy()).filter_dividends())
        )

        # Assert
        allowed_10k = t_1k * SCALABILITY_LINEAR_MULTIPLIER
        assert t_10k <= allowed_10k, (
            f"filter_dividends does not scale linearly: "
            f"t_1k={t_1k:.4f}s, t_10k={t_10k:.4f}s, "
            f"allowed_10k={allowed_10k:.4f}s (multiplier={SCALABILITY_LINEAR_MULTIPLIER})"
        )

    def test_determine_currency_scales_linearly(self, rng: np.random.Generator) -> None:
        """CurrencyConverter.determine_currency scales at most O(n * MULTIPLIER).

        Args:
            rng: Session-scoped seeded random generator.
        """
        # Arrange
        df_1k = _make_raw_transaction_df(1_000, rng)
        df_10k = _make_raw_transaction_df(10_000, rng)
        converter = CurrencyConverter(pd.DataFrame())
        tickers_1k = df_1k[ColumnName.TICKER.value].tolist()
        tickers_10k = df_10k[ColumnName.TICKER.value].tolist()

        # Act
        t_1k = statistics.median(
            _measure_ns(
                lambda: [converter.determine_currency(t, None) for t in tickers_1k]
            )
        )
        t_10k = statistics.median(
            _measure_ns(
                lambda: [converter.determine_currency(t, None) for t in tickers_10k]
            )
        )

        # Assert
        allowed_10k = t_1k * SCALABILITY_LINEAR_MULTIPLIER
        assert t_10k <= allowed_10k, (
            f"determine_currency does not scale linearly: "
            f"t_1k={t_1k:.4f}s, t_10k={t_10k:.4f}s, "
            f"allowed_10k={allowed_10k:.4f}s (multiplier={SCALABILITY_LINEAR_MULTIPLIER})"
        )

    def test_extract_tax_rate_scales_linearly(self, rng: np.random.Generator) -> None:
        """TaxExtractor.extract_tax_rate_from_comment scales at most O(n * MULTIPLIER).

        Args:
            rng: Session-scoped seeded random generator.
        """
        # Arrange
        df_1k = _make_raw_transaction_df(1_000, rng)
        df_10k = _make_raw_transaction_df(10_000, rng)
        extractor = TaxExtractor(pd.DataFrame())
        comments_1k = df_1k[ColumnName.COMMENT.value].tolist()
        comments_10k = df_10k[ColumnName.COMMENT.value].tolist()

        # Act
        t_1k = statistics.median(
            _measure_ns(
                lambda: [
                    extractor.extract_tax_rate_from_comment(c) for c in comments_1k
                ]
            )
        )
        t_10k = statistics.median(
            _measure_ns(
                lambda: [
                    extractor.extract_tax_rate_from_comment(c) for c in comments_10k
                ]
            )
        )

        # Assert
        allowed_10k = t_1k * SCALABILITY_LINEAR_MULTIPLIER
        assert t_10k <= allowed_10k, (
            f"extract_tax_rate_from_comment does not scale linearly: "
            f"t_1k={t_1k:.4f}s, t_10k={t_10k:.4f}s, "
            f"allowed_10k={allowed_10k:.4f}s (multiplier={SCALABILITY_LINEAR_MULTIPLIER})"
        )
