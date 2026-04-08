"""Scalability (linear-growth) performance tests."""

from __future__ import annotations

import statistics

import numpy as np
import pandas as pd
import pytest

from data_processing.constants import ColumnName
from data_processing.currency_converter import CurrencyConverter
from data_processing.dividend_filter import DividendFilter
from data_processing.tax_extractor import TaxExtractor

from .conftest import (
    SCALABILITY_LINEAR_MULTIPLIER,
    _make_raw_transaction_df,
    _measure_ns,
)


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
