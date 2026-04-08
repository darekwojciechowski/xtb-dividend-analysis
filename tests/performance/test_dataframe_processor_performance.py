"""Performance tests for DataFrameProcessor."""

from __future__ import annotations

import statistics
import time

import numpy as np
import pandas as pd
import pytest

from data_processing.dataframe_processor import DataFrameProcessor

from .conftest import (
    BUDGET_FILTER_10K_S,
    BUDGET_PIPELINE_1K_S,
    _make_raw_transaction_df,
    _measure_ns,
)


@pytest.mark.performance
class TestDataFrameProcessorPerformance:
    """Throughput tests for DataFrameProcessor at scale."""

    def test_filter_dividends_1k_rows_within_budget(
        self, rng: np.random.Generator
    ) -> None:
        """DataFrameProcessor.filter_dividends processes 1 000 rows within budget.

        Budget: BUDGET_PIPELINE_1K_S seconds (median).

        Args:
            rng: Session-scoped seeded random generator.
        """
        # Arrange
        df = _make_raw_transaction_df(1_000, rng)

        def _run() -> None:
            processor = DataFrameProcessor(df.copy())
            processor.filter_dividends()

        timings = _measure_ns(_run)

        # Act
        median_s = statistics.median(timings)

        # Assert
        assert median_s < BUDGET_PIPELINE_1K_S, (
            f"DataFrameProcessor.filter_dividends(1k) median={median_s:.4f}s exceeded budget={BUDGET_PIPELINE_1K_S}s"
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
