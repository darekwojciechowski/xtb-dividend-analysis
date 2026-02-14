"""
Unit tests for TaxCalculator class.

This module contains tests for tax calculation logic including:
- Calculation of tax amounts in PLN
- Parsing of values with currencies
- Handling of different tax scenarios
"""

import pandas as pd
import pytest

from data_processing.tax_calculator import TaxCalculator


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
        tax_collected_str = "-" if tax_collected_amount == 0 or tax_collected_amount == "-" else f"{tax_collected_amount} {currency}"
        exchange_rate_str = "-" if exchange_rate == "-" or exchange_rate == 1.0 else f"{exchange_rate} PLN"

        return pd.DataFrame({
            "Date": [date],
            "Ticker": [ticker],
            "Shares": [shares],
            "Net Dividend": [f"{net_dividend} {currency}"],
            "Tax Collected": [tax_collected_pct],
            "Tax Collected Amount": [tax_collected_str],
            "Exchange Rate D-1": [exchange_rate_str],
        })

    @staticmethod
    def calculate_expected_tax_pln_statement(
        net_dividend: float,
        tax_collected_amount: float,
        exchange_rate: float,
        tax_collected_pct: float
    ) -> float | str:
        """
        Calculate expected tax for PLN statement using the same formula as TaxCalculator.

        Formula: (net_dividend * 19% - tax_collected_amount) * exchange_rate

        Returns:
            float: Expected tax amount in PLN (rounded to 2 decimals)
            str: "-" if no additional tax is due
        """
        if tax_collected_pct >= 0.19:
            return "-"

        tax_to_collect = (net_dividend * 0.19) - tax_collected_amount
        tax_in_pln = tax_to_collect * exchange_rate
        return round(tax_in_pln, 2)

    @staticmethod
    def calculate_expected_tax_usd_statement(
        net_dividend: float,
        tax_collected_amount: float,
        exchange_rate: float,
        tax_collected_pct: float
    ) -> float | str:
        """
        Calculate expected tax for USD statement using the same formula as TaxCalculator.

        Formula: ((net_dividend + tax_collected_amount) * 19% - tax_collected_amount) * exchange_rate

        Returns:
            float: Expected tax amount in PLN (rounded to 2 decimals)
            str: "-" if no additional tax is due
        """
        if tax_collected_pct >= 0.19:
            return "-"

        gross_dividend = net_dividend + tax_collected_amount
        tax_to_collect = (gross_dividend * 0.19) - tax_collected_amount
        tax_in_pln = tax_to_collect * exchange_rate
        return round(tax_in_pln, 2)

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
        self, net_dividend, tax_collected_amount, tax_collected_pct, exchange_rate, ticker, date
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
            f"Expected no additional tax for {tax_collected_pct*100}% tax rate, "
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
        # Additional verification: should be net_dividend * 0.19 * exchange_rate
        assert result_df.loc[0, "Tax Amount PLN"] == round(
            net_dividend * 0.19 * exchange_rate, 2)

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
        self, net_dividend, tax_collected_amount, tax_collected_pct, exchange_rate, ticker, date
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
            expected_manual = round(tax_to_pay * exchange_rate, 2)
            assert result_df.loc[0, "Tax Amount PLN"] == expected_manual

    def test_calculate_total_tax_amount(self) -> None:
        """Test calculation of total tax amount across multiple rows."""
        # Arrange
        test_values = [0.27, "-", 18.15, 0.43, "-", 5.00]
        df = pd.DataFrame({"Tax Amount PLN": test_values})

        # Calculate expected total (sum only numeric values, skip "-")
        expected_total = round(sum(v for v in test_values if v != "-"), 2)

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
        expected_pln = round(
            (net_dividend * 0.19 - tax_collected_amount) * exchange_rate, 2)
        # USD statement: ((net + tax_collected) * 0.19 - tax_collected) * rate = (11*0.19 - 1) * 4 = 4.36
        expected_usd = round(((net_dividend + tax_collected_amount)
                             * 0.19 - tax_collected_amount) * exchange_rate, 2)

        assert tax_pln == expected_pln
        assert tax_usd == expected_usd
        assert tax_pln != tax_usd, "PLN and USD statements should produce different results with same input"


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

    def test_calculate_tax_when_missing_required_columns_then_raises_error(self) -> None:
        """Test that missing required columns raise ValueError."""
        # Arrange
        df = pd.DataFrame({
            "Date": ["2025-01-06"],
            "Ticker": ["SBUX.US"],
        })
        calculator = TaxCalculator(df)

        # Act & Assert
        with pytest.raises(ValueError, match="Required columns missing"):
            calculator.calculate_tax_for_pln_statement("PLN")

    def test_parse_value_with_currency_when_invalid_format_then_raises_error(self) -> None:
        """Test that invalid currency format raises ValueError."""
        # Arrange
        df = pd.DataFrame({"dummy": [1]})
        calculator = TaxCalculator(df)

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid 'Net Dividend' format"):
            calculator._parse_value_with_currency(
                "invalid", "Net Dividend", "SBUX.US", "2025-01-06"
            )
