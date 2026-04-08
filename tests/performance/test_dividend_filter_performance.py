"""Performance tests for DividendFilter."""

from __future__ import annotations

import statistics

import pandas as pd
import pytest

from data_processing.dividend_filter import DividendFilter

from .conftest import (
    BUDGET_FILTER_10K_S,
    BUDGET_FILTER_100K_S,
    BUDGET_GROUP_10K_S,
    _measure_ns,
)


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
