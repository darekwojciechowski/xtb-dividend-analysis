"""Performance tests for TaxCalculator."""

from __future__ import annotations

import statistics

import pandas as pd
import pytest

from data_processing.constants import Currency
from data_processing.tax_calculator import TaxCalculator

from .conftest import (
    BUDGET_TAX_CALCULATE_PLN_1K_S,
    BUDGET_TAX_CALCULATE_PLN_5K_S,
    _measure_ns,
)


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
