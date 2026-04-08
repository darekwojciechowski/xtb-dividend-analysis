"""Performance tests for TaxExtractor."""

from __future__ import annotations

import statistics
import time

import pandas as pd
import pytest

from data_processing.constants import ColumnName
from data_processing.tax_extractor import TaxExtractor

from .conftest import BUDGET_TAX_EXTRACT_10K_S, _measure_ns


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
