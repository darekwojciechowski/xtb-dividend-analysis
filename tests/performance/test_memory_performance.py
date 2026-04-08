"""Memory behaviour tests for the XTB dividend analysis pipeline."""

from __future__ import annotations

import tracemalloc

import numpy as np
import pandas as pd
import pytest

from data_processing.dataframe_processor import DataFrameProcessor
from data_processing.dividend_filter import DividendFilter

from .conftest import (
    BUDGET_MEMORY_FILTER_100K_BYTES,
    BUDGET_MEMORY_PIPELINE_1K_BYTES,
    _make_raw_transaction_df,
)


@pytest.mark.performance
class TestMemoryBehaviour:
    """Peak RSS and leak-detection tests using ``tracemalloc``."""

    @pytest.mark.slow
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
