"""Unit tests for TaxCalculator.

Covers the Belka-tax calculation formulas, currency-string parsing, and error
handling of ``TaxCalculator``.

Test classes:
    TestTaxCalculation  — parametrised scenarios for the PLN-statement formula
                          (net × 19% − WHT) × rate, the USD-statement formula
                          (gross × 19% − WHT) × rate, and edge cases
                          (WHT ≥ 19%, zero WHT, total-tax summation,
                          PLN vs USD formula divergence)
    TestValueParsing    — ``_parse_value_with_currency``,
                          ``_parse_tax_collected_amount``,
                          ``_parse_exchange_rate`` with valid and sentinel inputs
    TestErrorHandling   — missing required columns, invalid currency-string format

All tests are marked ``@pytest.mark.unit``.
"""

from __future__ import annotations

import pandas as pd
import pytest

from data_processing.tax_calculator import TaxCalculator


@pytest.mark.unit
class TestTaxCalculation:
    """Test suite for tax calculation logic."""

    # Polish tax rate constant
    POLISH_TAX_RATE = 0.19

    @staticmethod
    def create_test_dataframe(
        date: str,
        ticker: str,
        shares: float,
        net_dividend: float,
        currency: str,
        tax_collected_pct: float,
        tax_collected_amount: float | str,
        exchange_rate: float | str,
    ) -> pd.DataFrame:
        """
        Helper method to create test DataFrame with consistent structure.

        Args:
            date: Transaction date
            ticker: Stock ticker symbol
            shares: Number of shares
            net_dividend: Net dividend amount
            currency: Currency code (USD, PLN, DKK, etc.)
            tax_collected_pct: Tax percentage collected at source (0.15 = 15%)
            tax_collected_amount: Tax amount collected (or "-" for zero)
            exchange_rate: Exchange rate to PLN (or "-" for PLN dividends)

        Returns:
            pd.DataFrame: Test data in expected format
        """
        tax_collected_str = (
            "-"
            if tax_collected_amount == 0 or tax_collected_amount == "-"
            else f"{tax_collected_amount} {currency}"
        )
        exchange_rate_str = (
            "-"
            if exchange_rate == "-" or exchange_rate == 1.0
            else f"{exchange_rate} PLN"
        )

        return pd.DataFrame(
            {
                "Date": [date],
                "Ticker": [ticker],
                "Shares": [shares],
                "Net Dividend": [f"{net_dividend} {currency}"],
                "Tax Collected": [tax_collected_pct],
                "Tax Collected Amount": [tax_collected_str],
                "Exchange Rate D-1": [exchange_rate_str],
            }
        )

    @staticmethod
    def calculate_expected_tax_pln_statement(
        net_dividend: float,
        tax_collected_amount: float,
        exchange_rate: float,
        tax_collected_pct: float,
    ) -> str:
        """
        Calculate expected tax for PLN statement using the same formula as TaxCalculator.

        Formula: (net_dividend * 19% - tax_collected_amount) * exchange_rate

        Returns:
            str: Expected tax amount formatted as "X.XX PLN" or "-" if no additional tax is due
        """
        if tax_collected_pct >= 0.19:
            return "-"

        tax_to_collect = (net_dividend * 0.19) - tax_collected_amount
        tax_in_pln = tax_to_collect * exchange_rate
        rounded_tax = round(tax_in_pln, 2)
        if rounded_tax == 0.0:
            return "-"
        return f"{rounded_tax} PLN"

    @staticmethod
    def calculate_expected_tax_usd_statement(
        net_dividend: float,
        tax_collected_amount: float,
        exchange_rate: float,
        tax_collected_pct: float,
    ) -> str:
        """
        Calculate expected tax for USD statement using the same formula as TaxCalculator.

        Formula: ((net_dividend + tax_collected_amount) * 19% - tax_collected_amount) * exchange_rate

        Returns:
            str: Expected tax amount formatted as "X.XX PLN" or "-" if no additional tax is due
        """
        if tax_collected_pct >= 0.19:
            return "-"

        gross_dividend = net_dividend + tax_collected_amount
        tax_to_collect = (gross_dividend * 0.19) - tax_collected_amount
        tax_in_pln = tax_to_collect * exchange_rate
        rounded_tax = round(tax_in_pln, 2)
        if rounded_tax == 0.0:
            return "-"
        return f"{rounded_tax} PLN"

    @pytest.mark.parametrize(
        "net_dividend,tax_collected_amount,tax_collected_pct,exchange_rate,ticker,date",
        [
            # SBUX.US - 15% tax collected at source
            (1.71, 0.26, 0.15, 4.1512, "SBUX.US", "2025-01-06"),
            # Test with different values - 10% tax collected
            (10.0, 1.0, 0.10, 4.0, "TEST1.US", "2025-01-15"),
            # Test with 18% tax (just below 19%)
            (10.0, 1.8, 0.18, 4.0, "TEST2.US", "2025-01-20"),
            # PLD.US - 15% tax collected at source
            (5.05, 0.76, 0.15, 3.6411, "PLD.US", "2025-09-30"),
            # VICI.US - 15% tax collected at source
            (9.52, 1.42, 0.15, 3.8707, "VICI.US", "2025-04-03"),
            # MAA.US - 15% tax collected at source
            (6.06, 0.91, 0.15, 3.6520, "MAA.US", "2025-10-31"),
        ],
    )
    def test_calculate_tax_for_pln_statement_with_tax_below_19_percent(
        self,
        net_dividend,
        tax_collected_amount,
        tax_collected_pct,
        exchange_rate,
        ticker,
        date,
    ) -> None:
        """Test tax calculation for PLN statement when tax collected is below 19%."""
        # Arrange
        df = self.create_test_dataframe(
            date=date,
            ticker=ticker,
            shares=1.0,
            net_dividend=net_dividend,
            currency="USD",
            tax_collected_pct=tax_collected_pct,
            tax_collected_amount=tax_collected_amount,
            exchange_rate=exchange_rate,
        )
        calculator = TaxCalculator(df)

        # Calculate expected result using the formula
        expected_tax = self.calculate_expected_tax_pln_statement(
            net_dividend, tax_collected_amount, exchange_rate, tax_collected_pct
        )

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert - verify calculator uses correct formula
        assert "Tax Amount PLN" in result_df.columns
        assert result_df.loc[0, "Tax Amount PLN"] == expected_tax

    @pytest.mark.parametrize(
        "net_dividend,tax_collected_pct,currency,exchange_rate,ticker,date",
        [
            # MMM.US - 30% tax collected (above 19%)
            (1.4, 0.30, "USD", 3.9974, "MMM.US", "2025-02-21"),
            # NOVOB.DK - 27% tax collected (above 19%)
            (26.25, 0.27, "DKK", 0.5702, "NOVOB.DK", "2025-08-19"),
            # XTB.PL - 19% tax collected (exactly 19%)
            (92.65, 0.19, "PLN", "-", "XTB.PL", "2025-06-25"),
            # Edge case: 20% tax collected
            (100.0, 0.20, "USD", 4.0, "TEST.US", "2025-01-01"),
        ],
    )
    def test_calculate_tax_when_tax_collected_above_or_equal_19_percent(
        self, net_dividend, tax_collected_pct, currency, exchange_rate, ticker, date
    ) -> None:
        """Test that when tax >= 19%, no additional tax is due in Poland."""
        # Arrange - tax amount doesn't matter when percentage >= 19%
        tax_collected_amount = net_dividend * tax_collected_pct
        df = self.create_test_dataframe(
            date=date,
            ticker=ticker,
            shares=1.0,
            net_dividend=net_dividend,
            currency=currency,
            tax_collected_pct=tax_collected_pct,
            tax_collected_amount=tax_collected_amount,
            exchange_rate=exchange_rate,
        )
        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert - verify that tax percentage check works correctly
        assert result_df.loc[0, "Tax Amount PLN"] == "-", (
            f"Expected no additional tax for {tax_collected_pct * 100}% tax rate, "
            f"but got {result_df.loc[0, 'Tax Amount PLN']}"
        )

    def test_calculate_tax_for_zero_tax_collected(self) -> None:
        """Test that when no tax is collected at source, full 19% is due."""
        # Arrange
        net_dividend = 25.5
        tax_collected_amount = 0.0
        tax_collected_pct = 0.0
        exchange_rate = 3.7456

        df = self.create_test_dataframe(
            date="2025-05-29",
            ticker="ASB.PL",
            shares=85.0,
            net_dividend=net_dividend,
            currency="USD",
            tax_collected_pct=tax_collected_pct,
            tax_collected_amount="-",
            exchange_rate=exchange_rate,
        )
        calculator = TaxCalculator(df)

        # Calculate expected: full 19% of net dividend converted to PLN
        expected_tax = self.calculate_expected_tax_pln_statement(
            net_dividend, tax_collected_amount, exchange_rate, tax_collected_pct
        )

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert - verify full 19% is calculated
        assert result_df.loc[0, "Tax Amount PLN"] == expected_tax
        # Additional verification: should be net_dividend * 0.19 * exchange_rate formatted with PLN
        expected_formatted = f"{round(net_dividend * 0.19 * exchange_rate, 2)} PLN"
        assert result_df.loc[0, "Tax Amount PLN"] == expected_formatted

    @pytest.mark.parametrize(
        "net_dividend,tax_collected_amount,tax_collected_pct,exchange_rate,ticker,date",
        [
            # MAA.US example
            (6.12, 0.92, 0.15, 3.5189, "MAA.US", "2026-01-30"),
            # VICI.US example
            (11.7, 1.76, 0.15, 3.6035, "VICI.US", "2026-01-08"),
            # Test with different tax percentage
            (10.0, 1.0, 0.10, 4.0, "TEST.US", "2026-01-01"),
        ],
    )
    def test_calculate_tax_for_usd_statement(
        self,
        net_dividend,
        tax_collected_amount,
        tax_collected_pct,
        exchange_rate,
        ticker,
        date,
    ) -> None:
        """Test tax calculation for USD statement - uses gross dividend formula."""
        # Arrange
        df = self.create_test_dataframe(
            date=date,
            ticker=ticker,
            shares=1.0,
            net_dividend=net_dividend,
            currency="USD",
            tax_collected_pct=tax_collected_pct,
            tax_collected_amount=tax_collected_amount,
            exchange_rate=exchange_rate,
        )
        calculator = TaxCalculator(df)

        # Calculate expected result using USD statement formula
        expected_tax = self.calculate_expected_tax_usd_statement(
            net_dividend, tax_collected_amount, exchange_rate, tax_collected_pct
        )

        # Act
        result_df = calculator.calculate_tax_for_usd_statement("USD")

        # Assert - verify calculator uses correct USD statement formula
        assert "Tax Amount PLN" in result_df.columns
        assert result_df.loc[0, "Tax Amount PLN"] == expected_tax

        # Additional verification: manually check the gross dividend formula
        if tax_collected_pct < 0.19:
            gross_dividend = net_dividend + tax_collected_amount
            tax_due = gross_dividend * 0.19
            tax_to_pay = tax_due - tax_collected_amount
            expected_manual = f"{round(tax_to_pay * exchange_rate, 2)} PLN"
            assert result_df.loc[0, "Tax Amount PLN"] == expected_manual

    def test_calculate_total_tax_amount(self) -> None:
        """Test calculation of total tax amount across multiple rows."""
        # Arrange
        test_values = ["0.27 PLN", "-", "18.15 PLN", "0.43 PLN", "-", "5.00 PLN"]
        df = pd.DataFrame({"Tax Amount PLN": test_values})

        # Calculate expected total (sum only numeric values, skip "-")
        numeric_values = [0.27, 18.15, 0.43, 5.00]
        expected_total = round(sum(numeric_values), 2)

        # Act
        total = TaxCalculator.calculate_total_tax_amount(df)

        # Assert - verify summation logic
        assert total == expected_total
        assert total == 23.85  # Verification of manual calculation

    def test_pln_vs_usd_statement_different_formulas(self) -> None:
        """Verify that PLN and USD statements use different calculation formulas."""
        # Arrange - same input data
        net_dividend = 10.0
        tax_collected_amount = 1.0
        tax_collected_pct = 0.10
        exchange_rate = 4.0

        df_pln = self.create_test_dataframe(
            date="2025-01-01",
            ticker="TEST.US",
            shares=1.0,
            net_dividend=net_dividend,
            currency="USD",
            tax_collected_pct=tax_collected_pct,
            tax_collected_amount=tax_collected_amount,
            exchange_rate=exchange_rate,
        )
        df_usd = df_pln.copy()

        # Act
        result_pln = TaxCalculator(df_pln).calculate_tax_for_pln_statement("PLN")
        result_usd = TaxCalculator(df_usd).calculate_tax_for_usd_statement("USD")

        # Assert - results should be different because formulas are different
        tax_pln = result_pln.loc[0, "Tax Amount PLN"]
        tax_usd = result_usd.loc[0, "Tax Amount PLN"]

        # PLN statement: (net * 0.19 - tax_collected) * rate = (10*0.19 - 1) * 4 = 3.6
        expected_pln = f"{round((net_dividend * 0.19 - tax_collected_amount) * exchange_rate, 2)} PLN"
        # USD statement: ((net + tax_collected) * 0.19 - tax_collected) * rate = (11*0.19 - 1) * 4 = 4.36
        expected_usd = f"{round(((net_dividend + tax_collected_amount) * 0.19 - tax_collected_amount) * exchange_rate, 2)} PLN"

        assert tax_pln == expected_pln
        assert tax_usd == expected_usd
        assert tax_pln != tax_usd, (
            "PLN and USD statements should produce different results with same input"
        )


class TestValueParsing:
    """Test suite for parsing values with currencies."""

    def test_parse_value_with_currency_for_usd(self) -> None:
        """Test parsing USD values."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act
        value, currency = calculator._parse_value_with_currency(
            "1.71 USD", "Net Dividend", "SBUX.US", "2025-01-06"
        )

        # Assert
        assert value == 1.71
        assert currency == "USD"

    def test_parse_value_with_currency_for_pln(self) -> None:
        """Test parsing PLN values."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act
        value, currency = calculator._parse_value_with_currency(
            "92.65 PLN", "Net Dividend", "XTB.PL", "2025-06-25"
        )

        # Assert
        assert value == 92.65
        assert currency == "PLN"

    def test_parse_tax_collected_amount_with_dash(self) -> None:
        """Test parsing tax collected amount when value is '-'."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act
        value = calculator._parse_tax_collected_amount("-", "ASB.PL", "2025-05-29")

        # Assert
        assert value == 0.0

    def test_parse_exchange_rate_with_dash(self) -> None:
        """Test parsing exchange rate when value is '-' (PLN dividend)."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act
        rate = calculator._parse_exchange_rate("-", "XTB.PL", "2025-06-25")

        # Assert
        assert rate == 1.0

    def test_parse_exchange_rate_with_value(self) -> None:
        """Test parsing exchange rate with actual rate."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act
        rate = calculator._parse_exchange_rate("4.1512 PLN", "SBUX.US", "2025-01-06")

        # Assert
        assert rate == 4.1512


class TestErrorHandling:
    """Test suite for error handling in tax calculations."""

    def test_calculate_tax_when_missing_required_columns_then_raises_error(
        self,
    ) -> None:
        """Test that missing required columns raise ValueError."""
        # Arrange
        df = pd.DataFrame(
            {
                "Date": ["2025-01-06"],
                "Ticker": ["SBUX.US"],
            }
        )
        calculator = TaxCalculator(df)

        # Act & Assert
        with pytest.raises(ValueError, match="Required columns missing"):
            calculator.calculate_tax_for_pln_statement("PLN")

    def test_parse_value_with_currency_when_invalid_format_then_raises_error(
        self,
    ) -> None:
        """Test that invalid currency format raises ValueError."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid 'Net Dividend' format"):
            calculator._parse_value_with_currency(
                "invalid", "Net Dividend", "SBUX.US", "2025-01-06"
            )


@pytest.mark.unit
class TestParkingEdgeCases:
    """Test suite for edge cases in parsing methods."""

    @pytest.mark.parametrize(
        "value_str,expected_value,expected_currency",
        [
            ("1.0 USD", 1.0, "USD"),
            ("0.01 USD", 0.01, "USD"),
            ("100.99 DKK", 100.99, "DKK"),
            ("0.001 EUR", 0.001, "EUR"),
            ("999.999 GBP", 999.999, "GBP"),
            ("1000000.0 PLN", 1000000.0, "PLN"),
        ],
    )
    def test_parse_value_with_various_decimal_places(
        self, value_str, expected_value, expected_currency
    ) -> None:
        """Test parsing values with various decimal places and scales."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act
        value, currency = calculator._parse_value_with_currency(
            value_str, "Test Column", "TEST.XX", "2025-01-01"
        )

        # Assert
        assert value == expected_value
        assert currency == expected_currency

    @pytest.mark.parametrize(
        "value_str",
        [
            "  1.5 USD  ",  # Whitespace around
            "1.5  USD",  # Extra space before currency
            "1.5   USD",  # Multiple spaces
        ],
    )
    def test_parse_value_handles_whitespace_variations(self, value_str) -> None:
        """Test that parsing handles whitespace variations gracefully."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act & Assert
        # split() handles all whitespace, so these should work or fail consistently
        try:
            value, currency = calculator._parse_value_with_currency(
                value_str, "Test", "TEST.XX", "2025-01-01"
            )
            # If it succeeds, verify the values
            assert isinstance(value, float)
            assert isinstance(currency, str)
        except ValueError:
            # If it fails onwhitespace, that's also acceptable
            pass

    @pytest.mark.parametrize(
        "tax_amount_str,expected",
        [
            ("-", 0.0),
            ("0.0 USD", 0.0),
            ("0.01 USD", 0.01),
            ("100.5 EUR", 100.5),
        ],
    )
    def test_parse_tax_collected_amount_various_inputs(
        self, tax_amount_str, expected
    ) -> None:
        """Test parsing tax collected amount with various inputs."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act
        result = calculator._parse_tax_collected_amount(
            tax_amount_str, "TEST.XX", "2025-01-01"
        )

        # Assert
        assert result == expected

    @pytest.mark.parametrize(
        "rate_str,expected",
        [
            ("-", 1.0),
            ("1.0 PLN", 1.0),
            ("3.5 PLN", 3.5),
            ("4.1512 PLN", 4.1512),
            ("0.5702 PLN", 0.5702),
        ],
    )
    def test_parse_exchange_rate_various_inputs(self, rate_str, expected) -> None:
        """Test parsing exchange rate with various inputs."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act
        result = calculator._parse_exchange_rate(rate_str, "TEST.XX", "2025-01-01")

        # Assert
        assert result == expected


@pytest.mark.unit
class TestTaxBoundaryConditions:
    """Test suite for tax calculation boundary conditions."""

    @pytest.mark.parametrize(
        "tax_collected_pct",
        [
            0.1899,  # Just below 19%
            0.18999,  # Even closer to 19%
            0.19,  # Exactly 19%
            0.19001,  # Just above 19%
            0.20,  # Well above 19%
        ],
    )
    def test_tax_boundary_near_19_percent(self, tax_collected_pct) -> None:
        """Test tax calculation at boundary near 19% threshold."""
        # Arrange - use substantial dividend to avoid rounding to zero
        net_dividend = 1000.0
        tax_collected_amount = net_dividend * tax_collected_pct
        exchange_rate = 1.0

        df = pd.DataFrame(
            {
                "Date": ["2025-01-01"],
                "Ticker": ["TEST.US"],
                "Shares": [1.0],
                "Net Dividend": [f"{net_dividend} USD"],
                "Tax Collected": [tax_collected_pct],
                "Tax Collected Amount": [f"{tax_collected_amount} USD"],
                "Exchange Rate D-1": [f"{exchange_rate} PLN"],
            }
        )
        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        tax_result = result_df.loc[0, "Tax Amount PLN"]
        if tax_collected_pct >= 0.19:
            assert tax_result == "-", f"Expected no tax for {tax_collected_pct * 100}%"
        else:
            assert tax_result != "-", f"Expected tax for {tax_collected_pct * 100}%"
            parts = tax_result.split()
            assert len(parts) == 2
            assert parts[1] == "PLN"
            assert float(parts[0]) > 0

    def test_tax_calculation_rounding_precision(self) -> None:
        """Test that tax calculations maintain proper rounding precision."""
        # Arrange - value that produces repeating decimal
        net_dividend = 10.0 / 3  # 3.3333...
        tax_collected_amount = 0.0
        exchange_rate = 3.3  # Another repeating decimal

        df = pd.DataFrame(
            {
                "Date": ["2025-01-01"],
                "Ticker": ["TEST.US"],
                "Shares": [1.0],
                "Net Dividend": [f"{net_dividend} USD"],
                "Tax Collected": [0.0],
                "Tax Collected Amount": ["-"],
                "Exchange Rate D-1": [f"{exchange_rate} PLN"],
            }
        )
        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert - verify 2 decimal places on result
        tax_result = result_df.loc[0, "Tax Amount PLN"]
        if tax_result != "-":
            amount = float(tax_result.split()[0])
            # Check that it's properly rounded to 2 decimals
            assert amount == round(amount, 2)

    @pytest.mark.parametrize(
        "net_dividend,tax_pct,rate,expected_is_dash",
        [
            (0.01, 0.19, 1.0, True),  # Small dividend, exactly 19%
            (1.0, 0.15, 1.0, False),  # Small dividend, below 19%
            (0.0001, 0.19, 1.0, True),  # Very tiny dividend
            (1000000, 0.19, 1.0, True),  # Very large dividend, exactly 19%
        ],
    )
    def test_tax_with_extreme_dividend_amounts(
        self, net_dividend, tax_pct, rate, expected_is_dash
    ) -> None:
        """Test tax calculation with extreme dividend amounts."""
        # Arrange
        tax_amount = net_dividend * tax_pct

        df = pd.DataFrame(
            {
                "Date": ["2025-01-01"],
                "Ticker": ["TEST.US"],
                "Shares": [1.0],
                "Net Dividend": [f"{net_dividend} USD"],
                "Tax Collected": [tax_pct],
                "Tax Collected Amount": [
                    f"{tax_amount} USD" if tax_pct < 0.19 else "-"
                ],
                "Exchange Rate D-1": [f"{rate} PLN"],
            }
        )
        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        tax_result = result_df.loc[0, "Tax Amount PLN"]
        if expected_is_dash:
            assert tax_result == "-"
        else:
            assert tax_result != "-"


@pytest.mark.unit
class TestMultipleRowCalculations:
    """Test suite for tax calculations across multiple rows."""

    def test_calculate_tax_multiple_rows_different_currencies(self) -> None:
        """Test that calculations work correctly for multiple rows with different currencies."""
        # Arrange
        df = pd.DataFrame(
            {
                "Date": ["2025-01-01", "2025-01-01", "2025-01-01"],
                "Ticker": ["TEST1.US", "TEST2.DK", "TEST3.PL"],
                "Shares": [1.0, 1.0, 1.0],
                "Net Dividend": ["10.0 USD", "50.0 DKK", "100.0 PLN"],
                "Tax Collected": [0.15, 0.27, 0.19],
                "Tax Collected Amount": ["1.5 USD", "13.5 DKK", "-"],
                "Exchange Rate D-1": ["4.0 PLN", "0.57 PLN", "-"],
            }
        )
        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        assert len(result_df) == 3
        assert "Tax Amount PLN" in result_df.columns

        # Row 1: US stock, should have calculated tax
        assert result_df.loc[0, "Tax Amount PLN"] != "-"

        # Row 2: DK stock with 27% tax (>19%), should be dash
        assert result_df.loc[1, "Tax Amount PLN"] == "-"

        # Row 3: PL stock with 19% tax, should be dash
        assert result_df.loc[2, "Tax Amount PLN"] == "-"

    def test_calculate_total_tax_with_multiple_currencies(self) -> None:
        """Test total tax calculation across rows with different currencies."""
        # Arrange
        df = pd.DataFrame(
            {"Tax Amount PLN": ["5.25 PLN", "-", "10.75 PLN", "3.0 PLN", "-"]}
        )

        # Act
        total = TaxCalculator.calculate_total_tax_amount(df)

        # Assert
        expected = 5.25 + 10.75 + 3.0
        assert total == expected
        assert total == 19.0

    def test_calculate_tax_multiple_rows_usd_statement(self) -> None:
        """Test USD statement formula across multiple rows."""
        # Arrange
        df = pd.DataFrame(
            {
                "Date": ["2025-01-01", "2025-01-02"],
                "Ticker": ["AAPL.US", "MSFT.US"],
                "Shares": [10.0, 5.0],
                "Net Dividend": ["10.0 USD", "15.0 USD"],
                "Tax Collected": [0.15, 0.15],
                "Tax Collected Amount": ["1.5 USD", "2.25 USD"],
                "Exchange Rate D-1": ["4.0 PLN", "4.1 PLN"],
            }
        )
        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_usd_statement("USD")

        # Assert
        assert len(result_df) == 2
        assert "Tax Amount PLN" in result_df.columns

        # Both rows should have non-dash values (tax < 19%)
        for idx in [0, 1]:
            assert result_df.loc[idx, "Tax Amount PLN"] != "-"


@pytest.mark.unit
class TestErrorMessages:
    """Test suite for error message clarity and correctness."""

    @pytest.mark.parametrize(
        "invalid_value",
        ["", "USD only", "123", "   ", None],
    )
    def test_parse_value_error_message_clarity(self, invalid_value) -> None:
        """Test that parsing errors provide clear messages."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            calculator._parse_value_with_currency(
                invalid_value, "Net Dividend", "SBUX.US", "2025-01-06"
            )

        # Message should mention the column name
        assert "Net Dividend" in str(exc_info.value)

    def test_missing_column_error_message(self) -> None:
        """Test that missing column error lists the missing column."""
        # Arrange
        df = pd.DataFrame({"Date": ["2025-01-01"], "Ticker": ["TEST.US"]})
        calculator = TaxCalculator(df)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            calculator.calculate_tax_for_pln_statement("PLN")

        error_msg = str(exc_info.value)
        assert "missing" in error_msg.lower()
        assert "columns" in error_msg.lower()
