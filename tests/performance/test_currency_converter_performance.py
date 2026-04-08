"""Performance tests for CurrencyConverter."""

from __future__ import annotations

import statistics

import numpy as np
import pandas as pd
import pytest

from data_processing.constants import ColumnName
from data_processing.currency_converter import CurrencyConverter

from .conftest import (
    BUDGET_CURRENCY_DETERMINE_10K_S,
    BUDGET_EXTRACT_COMMENT_10K_S,
    _measure_ns,
)


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
