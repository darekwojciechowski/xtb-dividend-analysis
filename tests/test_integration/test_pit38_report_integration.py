"""PIT-38 declaration figures against the demo statement.

Pins every number the terminal block prints for
``data/demo_XTB_broker_statement_currency_PLN.xlsx``. The expected values were
derived from the raw statement and the NBP archive, not from the code:

===========  ========  =========  ========  ======  =========  =========
row          country   gross PLN  paid PLN  19%     wariant A  wariant B
===========  ========  =========  ========  ======  =========  =========
SBUX.US      US 15%    7.10       1.06      1.35    1.06       1.06
MMM.US       US 15%    5.60       1.68      1.06    0.84       1.06
ASB.PL       CY 5%     95.51      0.00      18.15   0.00       0.00
SBUX.US      US 15%    6.42       0.96      1.22    0.96       0.96
NOVOB.DK     DK 15%    14.97      4.04      2.84    2.25       2.84
===========  ========  =========  ========  ======  =========  =========

The totals are **not** the sum of those 2-decimal displays: accumulation runs
at full float precision and rounds once at the end. Adding the displayed
wariant-B column gives 5.92, while the unrounded terms give 5.93. Do not
"correct" a total to match its column.
"""

from __future__ import annotations

import pandas as pd
import pytest

from config.settings import settings
from data_processing.currency_converter import CurrencyConverter
from data_processing.pit38_report import Pit38Summary, build_pit38_summary
from data_processing.tax_calculator import TaxCalculator

pytestmark = [pytest.mark.slow, pytest.mark.integration]

# Polish issuers, excluded from poz. 47 (settled by the withholding agent).
_POLISH_GROSS_PLN = 28.22 + 92.65 + 38.15  # 159.02


@pytest.fixture(scope="module")
def pit38_summary(
    processed_pln_result: pd.DataFrame, nbp_courses: list[str]
) -> Pit38Summary:
    """Build the PIT-38 summary once for the whole module.

    Args:
        processed_pln_result: Module-scoped fully processed DataFrame.
        nbp_courses: Module-scoped NBP CSV paths.

    Returns:
        ``Pit38Summary`` for the demo statement.
    """
    df = processed_pln_result
    return build_pit38_summary(
        df, CurrencyConverter(df), nbp_courses, settings.polish_tax_rate
    )


def test_pit38_gross_foreign_excludes_polish_issuers(
    pit38_summary: Pit38Summary,
) -> None:
    """Test that Polish issuers stay out of the declaration's income base.

    Given: The demo statement, whose Polish rows total 159.02 PLN gross
    When:  The PIT-38 summary is folded
    Then:  Only the foreign rows reach ``gross_foreign_pln``, while
           ``total_gross_all_pln`` still counts every row

    Args:
        pit38_summary: Module-scoped summary fixture.
    """
    assert pit38_summary.gross_foreign_pln == pytest.approx(129.59)
    assert pit38_summary.total_gross_all_pln == pytest.approx(288.61)
    assert pit38_summary.total_gross_all_pln - pit38_summary.gross_foreign_pln == (
        pytest.approx(_POLISH_GROSS_PLN, abs=0.01)
    )
    assert not any(row.country == "PL" for row in pit38_summary.rows)


def test_pit38_declaration_figures_match_expected_demo_values(
    pit38_summary: Pit38Summary,
) -> None:
    """Test that every printed declaration figure matches the reference table.

    Given: The demo statement processed end to end
    When:  The PIT-38 summary is folded
    Then:  poz. 47, both poz. 48 variants and both payable figures match the
           values derived from the raw statement and the NBP archive

    Args:
        pit38_summary: Module-scoped summary fixture.
    """
    assert pit38_summary.foreign_tax_paid_pln == pytest.approx(7.75)
    assert pit38_summary.tax_19_pct_pln == pytest.approx(24.62)
    assert pit38_summary.deductible_treaty_pln == pytest.approx(5.11)
    assert pit38_summary.deductible_full_pln == pytest.approx(5.93)
    assert pit38_summary.payable_treaty_pln == pytest.approx(19.51)
    assert pit38_summary.payable_full_pln == pytest.approx(18.69)


def test_pit38_per_row_breakdown_matches_expected_demo_values(
    pit38_summary: Pit38Summary,
) -> None:
    """Test the per-row breakdown, including the two treaty-divergence cases.

    Given: The demo statement, containing a 30%-WHT US row (no W-8BEN), a
           27%-WHT Danish row and a zero-WHT Cypriot row
    When:  The PIT-38 summary is folded
    Then:  Each row's country, gross, and both deduction variants match

    Args:
        pit38_summary: Module-scoped summary fixture.
    """
    expected = [
        ("SBUX.US", "US", 7.10, 1.06, 1.06),
        ("MMM.US", "US", 5.60, 0.84, 1.06),
        ("ASB.PL", "CY", 95.51, 0.00, 0.00),
        ("SBUX.US", "US", 6.42, 0.96, 0.96),
        ("NOVOB.DK", "DK", 14.97, 2.25, 2.84),
    ]

    actual = [
        (
            row.ticker,
            row.country,
            row.gross_pln,
            row.deductible_treaty_pln,
            row.deductible_full_pln,
        )
        for row in pit38_summary.rows
    ]

    assert len(actual) == len(expected)
    for got, want in zip(actual, expected):
        assert got[0] == want[0]
        assert got[1] == want[1]
        assert got[2] == pytest.approx(want[2])
        assert got[3] == pytest.approx(want[3])
        assert got[4] == pytest.approx(want[4])


def test_pit38_flags_non_usd_foreign_row_as_unconverted(
    pit38_summary: Pit38Summary,
) -> None:
    """Test that the DKK row is flagged as not yet FX-converted.

    Given: NOVOB.DK, whose share count is computed without an FX rate
           (Bug C, deferred to plan 22) and whose gross is therefore understated
    When:  The PIT-38 summary is folded
    Then:  The ticker appears in ``unconverted_currency_tickers`` so the block
           can print an explicit warning, and no country is left unresolved

    Args:
        pit38_summary: Module-scoped summary fixture.
    """
    assert pit38_summary.unconverted_currency_tickers == ("NOVOB.DK",)
    assert pit38_summary.unknown_country_tickers == ()


def test_pit38_reconciles_with_calculated_total_tax(
    pit38_summary: Pit38Summary, processed_pln_result: pd.DataFrame
) -> None:
    """Test that poz. 47 minus wariant B poz. 48 reconciles with the Belka total.

    Given: The demo statement's per-row ``Tax Amount PLN`` column
    When:  ``poz. 47 - poz. 48 (wariant B)`` is compared against
           ``TaxCalculator.calculate_total_tax_amount``
    Then:  The two agree within accumulated double-rounding drift

    The tolerance is not slack for its own sake: ``_calculate_tax_pln_row``
    re-parses values that were already formatted to two decimals, so each row
    can drift by a few groszy. 24.6229 - 5.9348 = 18.688 vs 18.66 here.

    Precondition: ``calculate_total_tax_amount`` sums over *all* rows,
    including the Polish ones poz. 47 excludes. The relation holds only
    because every Polish row in the demo is withheld at exactly 19%, making its
    Belka amount ``gross x 0.19 - gross x 0.19 = 0``. A Polish row at any other
    rate breaks this by złoty, not groszy, and this tolerance will not absorb it.

    Args:
        pit38_summary: Module-scoped summary fixture.
        processed_pln_result: Module-scoped fully processed DataFrame.
    """
    belka_total = TaxCalculator.calculate_total_tax_amount(processed_pln_result)
    n_foreign_rows = len(pit38_summary.rows)

    reconciled = pit38_summary.tax_19_pct_pln - pit38_summary.deductible_full_pln

    assert reconciled == pytest.approx(belka_total, abs=0.01 * n_foreign_rows + 0.01)
