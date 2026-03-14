"""Tax calculation integration tests.

Tests the integration of tax calculation logic with currency conversion
and data aggregation, ensuring correct Belka tax (19%) application.

Test Coverage:
    - 19% tax calculation on dividends
    - Tax calculation with converted currencies
    - Tax aggregation by multiple dimensions
    - Rounding consistency
"""

from __future__ import annotations

import pandas as pd
import pytest

from data_processing.tax_calculator import TaxCalculator

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def valid_pln_df() -> pd.DataFrame:
    """Single-row PLN DataFrame with all columns valid for TaxCalculator.

    Used as a baseline in error-condition tests — remove or corrupt one
    column per test to isolate the specific validation branch.

    Returns:
        DataFrame with one AAPL.US row, 0% WHT, exchange rate 1.0.
    """
    return pd.DataFrame(
        [_make_tax_row("AAPL.US", "100.0 PLN", 0.0, "-", "-", "2024-09-01")]
    )


def _make_tax_row(
    ticker: str,
    net_dividend_str: str,
    tax_collected_pct: float,
    tax_collected_amount_str: str,
    exchange_rate_str: str,
    date: str,
) -> dict:
    """Build a single row dict in the format TaxCalculator expects.

    Args:
        ticker: Stock ticker symbol.
        net_dividend_str: Net dividend string, e.g. ``"100.0 PLN"``.
        tax_collected_pct: WHT rate as a decimal, e.g. ``0.15``.
        tax_collected_amount_str: WHT amount string, e.g. ``"15.0 USD"`` or ``"-"``.
        exchange_rate_str: NBP D-1 rate string, e.g. ``"4.0 PLN"`` or ``"-"``.
        date: Dividend date string, e.g. ``"2024-03-15"``.

    Returns:
        Dictionary with all columns required by TaxCalculator.
    """
    return {
        "Date": date,
        "Ticker": ticker,
        "Net Dividend": net_dividend_str,
        "Tax Collected": tax_collected_pct,
        "Tax Collected Amount": tax_collected_amount_str,
        "Exchange Rate D-1": exchange_rate_str,
    }


@pytest.mark.integration
def test_tax_19_percent_calculation() -> None:
    """Test basic 19% Belka tax applied to a PLN dividend with no WHT at source.

    Given: Dividend of 100 PLN, 0% WHT, exchange rate 1.0 (PLN statement)
    When: calculate_tax_for_pln_statement() executes
    Then: Tax Amount PLN = 19.0 PLN; total tax = 19.0
    """
    # Arrange
    df = pd.DataFrame(
        [_make_tax_row("CDPROJEKT.PL", "100.0 PLN", 0.0, "-", "-", "2024-03-15")]
    )
    calculator = TaxCalculator(df)

    # Act
    result = calculator.calculate_tax_for_pln_statement("PLN")

    # Assert
    assert result["Tax Amount PLN"].iloc[0] == "19.0 PLN"
    assert TaxCalculator.calculate_total_tax_amount(result) == 19.0


@pytest.mark.integration
def test_tax_from_usd_dividend() -> None:
    """Test Belka tax calculation on a USD-denominated dividend converted to PLN.

    Given: Net 85.0 USD, WHT 15% (15.0 USD already paid), NBP rate 4.0 PLN
    When: calculate_tax_for_usd_statement() executes
    Then: Gross = 85+15 = 100 USD; Tax = (100×0.19 − 15) × 4.0 = 16.0 PLN
    """
    # Arrange
    df = pd.DataFrame(
        [
            _make_tax_row(
                "AAPL.US", "85.0 USD", 0.15, "15.0 USD", "4.0 PLN", "2024-04-15"
            )
        ]
    )
    calculator = TaxCalculator(df)

    # Act
    result = calculator.calculate_tax_for_usd_statement("USD")

    # Assert
    assert result["Tax Amount PLN"].iloc[0] == "16.0 PLN"
    assert TaxCalculator.calculate_total_tax_amount(result) == 16.0


@pytest.mark.integration
def test_tax_calculation_with_multiple_tickers() -> None:
    """Test Belka tax calculation across three tickers with different WHT rates.

    Given: Three stocks — AAPL.US (15% WHT), CDPROJEKT.PL (19% WHT), NOVO.DK (15% WHT)
    When: calculate_tax_for_pln_statement() processes all rows
    Then:
        - AAPL.US: (68×0.19 − 12) × 4.0 = 3.68 PLN
        - CDPROJEKT.PL: WHT >= 19% → "-" (already fully paid)
        - NOVO.DK: (50×0.19 − 9) × 0.6 = 0.30 PLN
        - Total = 3.98 PLN
    """
    # Arrange
    df = pd.DataFrame(
        [
            _make_tax_row(
                "AAPL.US", "68.0 USD", 0.15, "12.0 USD", "4.0 PLN", "2024-03-01"
            ),
            _make_tax_row(
                "CDPROJEKT.PL", "200.0 PLN", 0.19, "38.0 PLN", "-", "2024-03-05"
            ),
            _make_tax_row(
                "NOVO.DK", "50.0 DKK", 0.15, "9.0 DKK", "0.6 PLN", "2024-03-10"
            ),
        ]
    )
    calculator = TaxCalculator(df)

    # Act
    result = calculator.calculate_tax_for_pln_statement("PLN")

    # Assert
    assert (
        result.loc[result["Ticker"] == "AAPL.US", "Tax Amount PLN"].iloc[0]
        == "3.68 PLN"
    )
    assert (
        result.loc[result["Ticker"] == "CDPROJEKT.PL", "Tax Amount PLN"].iloc[0] == "-"
    )
    assert (
        result.loc[result["Ticker"] == "NOVO.DK", "Tax Amount PLN"].iloc[0] == "0.3 PLN"
    )
    assert TaxCalculator.calculate_total_tax_amount(result) == 3.98


@pytest.mark.integration
def test_tax_aggregation_by_month() -> None:
    """Test monthly aggregation of Belka tax amounts across three months.

    Given: 6 dividends — 2 per month (Jan, Feb, Mar 2024), each 100 PLN with 0% WHT
    When: calculate_tax_for_pln_statement() runs and results grouped by month
    Then: Each month tax total = 38.0 PLN; grand total = 114.0 PLN
    """
    # Arrange
    rows = [
        _make_tax_row("AAPL.US", "100.0 PLN", 0.0, "-", "-", "2024-01-10"),
        _make_tax_row("MSFT.US", "100.0 PLN", 0.0, "-", "-", "2024-01-20"),
        _make_tax_row("AAPL.US", "100.0 PLN", 0.0, "-", "-", "2024-02-10"),
        _make_tax_row("MSFT.US", "100.0 PLN", 0.0, "-", "-", "2024-02-20"),
        _make_tax_row("AAPL.US", "100.0 PLN", 0.0, "-", "-", "2024-03-10"),
        _make_tax_row("MSFT.US", "100.0 PLN", 0.0, "-", "-", "2024-03-20"),
    ]
    df = pd.DataFrame(rows)
    calculator = TaxCalculator(df)

    # Act
    result = calculator.calculate_tax_for_pln_statement("PLN")
    result["Month"] = result["Date"].str[:7]
    monthly_totals = {
        month: TaxCalculator.calculate_total_tax_amount(group)
        for month, group in result.groupby("Month")
    }

    # Assert
    assert monthly_totals["2024-01"] == 38.0
    assert monthly_totals["2024-02"] == 38.0
    assert monthly_totals["2024-03"] == 38.0
    assert TaxCalculator.calculate_total_tax_amount(result) == 114.0


@pytest.mark.integration
def test_tax_rounding_consistency() -> None:
    """Test that fractional tax amounts are rounded consistently across multiple runs.

    Given: Dividend of 33.33 PLN with 0% WHT (produces 6.3327 before rounding)
    When: calculate_tax_for_pln_statement() called 3 times on independent copies
    Then: All runs produce "6.33 PLN"; no floating-point drift between invocations
    """
    # Arrange
    base_df = pd.DataFrame(
        [_make_tax_row("AAPL.US", "33.33 PLN", 0.0, "-", "-", "2024-05-15")]
    )

    # Act — three independent calculator instances
    results = [
        TaxCalculator(base_df.copy())
        .calculate_tax_for_pln_statement("PLN")["Tax Amount PLN"]
        .iloc[0]
        for _ in range(3)
    ]

    # Assert
    assert results[0] == "6.33 PLN"
    assert results[0] == results[1] == results[2]


# ---------------------------------------------------------------------------
# Parameterized tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    "ticker,net_str,wht_pct,wht_amount_str,rate_str,expected",
    [
        pytest.param(
            "CDPROJEKT.PL",
            "100.0 PLN",
            0.0,
            "-",
            "-",
            "19.0 PLN",
            id="0pct_wht_full_belka",
        ),
        pytest.param(
            "AAPL.US",
            "100.0 PLN",
            0.15,
            "15.0 PLN",
            "-",
            "4.0 PLN",
            id="15pct_wht_partial_belka",
        ),
        pytest.param(
            "AAPL.US",
            "100.0 PLN",
            0.18,
            "18.0 PLN",
            "-",
            "1.0 PLN",
            id="18pct_wht_near_boundary",
        ),
        pytest.param(
            "CDPROJEKT.PL",
            "100.0 PLN",
            0.19,
            "19.0 PLN",
            "-",
            "-",
            id="19pct_wht_exactly_paid",
        ),
        pytest.param(
            "AAPL.US",
            "100.0 PLN",
            0.25,
            "25.0 PLN",
            "-",
            "-",
            id="25pct_wht_overpaid",
        ),
        pytest.param(
            "AAPL.US",
            "50.0 USD",
            0.0,
            "-",
            "4.0 PLN",
            "38.0 PLN",
            id="0pct_wht_with_fx_rate",
        ),
    ],
)
def test_tax_pln_statement_parametrized(
    ticker: str,
    net_str: str,
    wht_pct: float,
    wht_amount_str: str,
    rate_str: str,
    expected: str,
) -> None:
    """Parameterized: PLN statement tax across WHT rate boundaries and exchange rates.

    Verifies the early-exit branch (WHT >= 19% → "-") and the standard
    formula for all cases below the Belka threshold.

    Args:
        ticker: Stock ticker symbol.
        net_str: Net dividend string including currency, e.g. ``"100.0 PLN"``.
        wht_pct: WHT rate as a decimal.
        wht_amount_str: WHT amount string or ``"-"``.
        rate_str: NBP D-1 exchange rate string or ``"-"``.
        expected: Expected ``Tax Amount PLN`` cell value.
    """
    # Arrange
    df = pd.DataFrame(
        [
            _make_tax_row(
                ticker, net_str, wht_pct, wht_amount_str, rate_str, "2024-06-01"
            )
        ]
    )

    # Act
    result = TaxCalculator(df).calculate_tax_for_pln_statement("PLN")

    # Assert
    assert result["Tax Amount PLN"].iloc[0] == expected


@pytest.mark.integration
@pytest.mark.parametrize(
    "net_str,wht_pct,wht_amount_str,rate_str,expected",
    [
        pytest.param(
            "100.0 USD",
            0.0,
            "-",
            "4.0 PLN",
            "76.0 PLN",
            id="0pct_wht_full_belka_usd",
        ),
        pytest.param(
            "85.0 USD",
            0.15,
            "15.0 USD",
            "4.0 PLN",
            "16.0 PLN",
            id="15pct_wht_partial_belka_usd",
        ),
        pytest.param(
            "81.0 USD",
            0.19,
            "19.0 USD",
            "4.0 PLN",
            "-",
            id="19pct_wht_exactly_paid_usd",
        ),
        pytest.param(
            "70.0 USD",
            0.30,
            "30.0 USD",
            "4.0 PLN",
            "-",
            id="30pct_wht_no_w8ben_usd",
        ),
    ],
)
def test_tax_usd_statement_parametrized(
    net_str: str,
    wht_pct: float,
    wht_amount_str: str,
    rate_str: str,
    expected: str,
) -> None:
    """Parameterized: USD statement tax across WHT scenarios including 30% (no W8BEN).

    Verifies that the USD gross-up formula (Gross = Net + WHT Amount) is applied
    and that rates >= 19% return ``"-"`` (tax already covered at source).

    Args:
        net_str: Net dividend string, e.g. ``"85.0 USD"``.
        wht_pct: WHT rate as a decimal.
        wht_amount_str: WHT amount already deducted, e.g. ``"15.0 USD"`` or ``"-"``.
        rate_str: NBP D-1 exchange rate string.
        expected: Expected ``Tax Amount PLN`` cell value.
    """
    # Arrange
    df = pd.DataFrame(
        [
            _make_tax_row(
                "AAPL.US", net_str, wht_pct, wht_amount_str, rate_str, "2024-07-01"
            )
        ]
    )

    # Act
    result = TaxCalculator(df).calculate_tax_for_usd_statement("USD")

    # Assert
    assert result["Tax Amount PLN"].iloc[0] == expected


@pytest.mark.integration
@pytest.mark.parametrize(
    "net_str,wht_pct,expected_tax,expected_total",
    [
        pytest.param(
            "33.33 PLN",
            0.0,
            "6.33 PLN",
            6.33,
            id="fractional_rounds_down",
        ),
        pytest.param(
            "10.53 PLN",
            0.0,
            "2.0 PLN",
            2.0,
            id="decimal_rounds_to_one_place",
        ),
        pytest.param(
            "0.01 PLN",
            0.0,
            "-",
            0.0,
            id="tiny_dividend_rounds_to_zero",
        ),
        pytest.param(
            "1000.0 PLN",
            0.0,
            "190.0 PLN",
            190.0,
            id="large_dividend_exact",
        ),
    ],
)
def test_tax_rounding_parametrized(
    net_str: str,
    wht_pct: float,
    expected_tax: str,
    expected_total: float,
) -> None:
    """Parameterized: rounding behaviour for fractional, tiny, and large dividend amounts.

    Verifies that ``round(..., 2)`` is applied correctly and that the
    ``0.0`` → ``"-"`` guard fires for amounts that round to nothing.

    Args:
        net_str: Net dividend string including currency, e.g. ``"33.33 PLN"``.
        wht_pct: WHT rate as a decimal (0.0 isolates the rounding path).
        expected_tax: Expected ``Tax Amount PLN`` cell string.
        expected_total: Expected value from ``calculate_total_tax_amount``.
    """
    # Arrange
    df = pd.DataFrame(
        [_make_tax_row("AAPL.US", net_str, wht_pct, "-", "-", "2024-08-01")]
    )

    # Act
    result = TaxCalculator(df).calculate_tax_for_pln_statement("PLN")

    # Assert
    assert result["Tax Amount PLN"].iloc[0] == expected_tax
    assert TaxCalculator.calculate_total_tax_amount(result) == expected_total


# ---------------------------------------------------------------------------
# Error condition tests  (best practice: test edge cases and error paths)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    "missing_column",
    [
        pytest.param("Net Dividend", id="missing_net_dividend"),
        pytest.param("Tax Collected", id="missing_tax_collected"),
        pytest.param("Tax Collected Amount", id="missing_tax_collected_amount"),
        pytest.param("Exchange Rate D-1", id="missing_exchange_rate"),
    ],
)
def test_tax_pln_statement_raises_on_missing_column(
    valid_pln_df: pd.DataFrame, missing_column: str
) -> None:
    """Test that TaxCalculator raises ValueError when a required column is absent.

    Given: A valid PLN DataFrame with one required column dropped
    When: calculate_tax_for_pln_statement() executes
    Then: ValueError is raised and the missing column name appears in the message

    Args:
        valid_pln_df: Fixture providing a complete valid single-row DataFrame.
        missing_column: Name of the column to remove before calling the calculator.
    """
    # Arrange
    df = valid_pln_df.drop(columns=[missing_column])

    # Act / Assert
    with pytest.raises(ValueError, match=missing_column):
        TaxCalculator(df).calculate_tax_for_pln_statement("PLN")


@pytest.mark.integration
def test_tax_pln_statement_raises_on_nan_tax_collected(
    valid_pln_df: pd.DataFrame,
) -> None:
    """Test that a NaN in Tax Collected raises ValueError with ticker context.

    Given: A PLN DataFrame where Tax Collected is NaN for a known ticker
    When: calculate_tax_for_pln_statement() executes
    Then: ValueError is raised and the ticker symbol appears in the message
    """
    # Arrange
    valid_pln_df.loc[0, "Tax Collected"] = float("nan")

    # Act / Assert
    with pytest.raises(ValueError, match="AAPL.US"):
        TaxCalculator(valid_pln_df).calculate_tax_for_pln_statement("PLN")


@pytest.mark.integration
@pytest.mark.parametrize(
    "column,bad_value,expected_fragment",
    [
        pytest.param(
            "Net Dividend",
            "NO_SPACE",
            "Net Dividend",
            id="net_dividend_missing_currency_token",
        ),
        pytest.param(
            "Net Dividend",
            "abc PLN",
            "Net Dividend",
            id="net_dividend_non_numeric",
        ),
        pytest.param(
            "Tax Collected Amount",
            "NO_SPACE",
            "Tax Collected Amount",
            id="tax_collected_amount_missing_currency_token",
        ),
        pytest.param(
            "Exchange Rate D-1",
            "NO_SPACE",
            "Exchange Rate D-1",
            id="exchange_rate_missing_currency_token",
        ),
    ],
)
def test_tax_pln_statement_raises_on_malformed_value(
    valid_pln_df: pd.DataFrame,
    column: str,
    bad_value: str,
    expected_fragment: str,
) -> None:
    """Test that malformed column values raise ValueError with the column name in the message.

    Given: A valid PLN DataFrame with one cell replaced by a malformed string
    When: calculate_tax_for_pln_statement() processes that row
    Then: ValueError is raised and the column name appears in the error message

    Args:
        valid_pln_df: Fixture providing a complete valid single-row DataFrame.
        column: Column whose value will be replaced with a malformed string.
        bad_value: The invalid string to inject.
        expected_fragment: Substring expected to appear in the ValueError message.
    """
    # Arrange
    valid_pln_df.loc[0, column] = bad_value

    # Act / Assert
    with pytest.raises(ValueError, match=expected_fragment):
        TaxCalculator(valid_pln_df).calculate_tax_for_pln_statement("PLN")


@pytest.mark.integration
def test_tax_pln_statement_raises_on_missing_net_dividend_value(
    valid_pln_df: pd.DataFrame,
) -> None:
    """Test that an empty Net Dividend string raises ValueError.

    Given: A PLN DataFrame where Net Dividend cell is an empty string
    When: calculate_tax_for_pln_statement() executes
    Then: ValueError is raised referencing the Net Dividend column
    """
    # Arrange
    valid_pln_df.loc[0, "Net Dividend"] = ""

    # Act / Assert
    with pytest.raises(ValueError, match="Net Dividend"):
        TaxCalculator(valid_pln_df).calculate_tax_for_pln_statement("PLN")
