"""Currency conversion integration tests.

Tests the integration of currency detection, exchange rate loading,
and currency conversion across the complete pipeline.

Uses ``data/demo_XTB_broker_statement_currency_PLN.xlsx`` as the
reference fixture — a PLN-denominated account statement containing
dividends in PLN (TXT.PL, XTB.PL), USD (SBUX.US, MMM.US, ASB.PL),
and DKK (NOVOB.DK).

Test Coverage:
    - Currency detection from XLSX cell F6
    - NBP exchange rate loading from archiwum_tab_a CSV files
    - Conversion accuracy for a known USD rate on a specific date
    - Multiple currencies present in one statement
    - Missing exchange rate raises ValueError (not silent failure)
"""

from __future__ import annotations

import pytest

from data_processing.constants import Currency
from data_processing.currency_converter import CurrencyConverter

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_currency_detection_and_conversion(
    pln_statement: tuple,
) -> None:
    """Test that F6 of the PLN statement is detected as PLN.

    Given: demo_XTB_broker_statement_currency_PLN.xlsx
    When:  import_and_process_data() reads cell F6
    Then:  returned currency equals 'PLN'
    """
    # Arrange / Act
    _, detected_currency = pln_statement

    # Assert
    assert detected_currency == Currency.PLN.value


@pytest.mark.integration
def test_nbp_exchange_rate_loading(
    currency_converter: CurrencyConverter,
    nbp_courses: list[str],
) -> None:
    """Test that the 2025 NBP archive CSV provides USD and DKK rates.

    Given: archiwum_tab_a_2025.csv with daily mid-rates
    When:  get_exchange_rate() is called for known business days
    Then:  USD rate on 2025-01-03 and DKK rate on 2025-08-18 are positive floats
    """
    # Act
    usd_rate = currency_converter.get_exchange_rate(
        nbp_courses, "2025-01-03", Currency.USD.value
    )
    dkk_rate = currency_converter.get_exchange_rate(
        nbp_courses, "2025-08-18", Currency.DKK.value
    )

    # Assert
    assert usd_rate > 0, "USD rate must be a positive float"
    assert dkk_rate > 0, "DKK rate must be a positive float"


@pytest.mark.integration
def test_currency_conversion_accuracy(
    currency_converter: CurrencyConverter,
    nbp_courses: list[str],
) -> None:
    """Test that the NBP USD rate for a specific D-1 date matches the published value.

    SBUX.US dividend on 2025-01-06 → D-1 = 2025-01-03 (previous business day).
    NBP published mid-rate for USD on that date: 4.1512.

    Given: archiwum_tab_a_2025.csv
    When:  get_exchange_rate() is called for '2025-01-03', USD
    Then:  rate == 4.1512 (within 0.0001 tolerance)
    """
    # Act
    rate = currency_converter.get_exchange_rate(
        nbp_courses, "2025-01-03", Currency.USD.value
    )

    # Assert
    assert rate == pytest.approx(4.1512, abs=1e-4)


@pytest.mark.integration
def test_multiple_currencies_same_statement(
    pln_statement: tuple,
) -> None:
    """Test that all three dividend currencies appear in the PLN statement.

    The demo file contains:
      - TXT.PL  → PLN
      - SBUX.US → USD
      - MMM.US  → USD
      - ASB.PL  → USD (special case: Polish listing, USD dividend)
      - NOVOB.DK → DKK
      - XTB.PL  → PLN

    Given: demo_XTB_broker_statement_currency_PLN.xlsx
    When:  import_and_process_data() loads all rows
    Then:  Comment column contains entries for PLN, USD, and DKK dividends
    """
    # Arrange
    df, currency = pln_statement
    assert currency == Currency.PLN.value

    comments = df["Comment"].fillna("").astype(str)

    # Act – detect which currency labels appear in comments
    has_pln_dividend = comments.str.contains(r"PLN.*/ SHR", regex=True).any()
    has_usd_dividend = comments.str.contains(r"USD.*/ SHR", regex=True).any()
    has_dkk_dividend = comments.str.contains(r"DKK.*/ SHR", regex=True).any()

    # Assert
    assert has_pln_dividend, "Expected PLN dividend rows in the statement"
    assert has_usd_dividend, "Expected USD dividend rows in the statement"
    assert has_dkk_dividend, "Expected DKK dividend rows in the statement"


@pytest.mark.integration
def test_missing_exchange_rate_handling(
    currency_converter: CurrencyConverter,
    nbp_courses: list[str],
) -> None:
    """Test that a date with no NBP data raises ValueError.

    Given: archiwum_tab_a_2025.csv (covers calendar year 2025)
    When:  get_exchange_rate() is called for a date outside any available CSV
    Then:  ValueError is raised — no silent failure or 0.0 fallback
    """
    # Arrange
    date_not_in_any_csv = "1990-01-01"

    # Act / Assert
    with pytest.raises(ValueError, match="No exchange rate data found"):
        currency_converter.get_exchange_rate(
            nbp_courses, date_not_in_any_csv, Currency.USD.value
        )
