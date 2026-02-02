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

    def test_calculate_tax_for_sbux_example(self) -> None:
        """
        Test tax calculation for SBUX example from 2025-01-06.

        Example calculation:
        - Net Dividend: 1.71 USD
        - Tax Collected Amount: 0.26 USD
        - Tax Collected %: 15%
        - Exchange Rate D-1: 4.1512 PLN

        Expected calculation:
        - Tax due in USD: 1.71 × 19% = 0.3249 USD
        - Tax to pay in USD: 0.3249 - 0.26 = 0.0649 USD
        - Tax in PLN: 0.0649 × 4.1512 = 0.269413 PLN
        - Rounded: 0.27 PLN
        """
        # Arrange
        df = pd.DataFrame({
            "Date": ["2025-01-06"],
            "Ticker": ["SBUX.US"],
            "Shares": [3.0],
            "Net Dividend": ["1.71 USD"],
            "Tax Collected": [0.15],  # 15%
            "Tax Collected Amount": ["0.26 USD"],
            "Exchange Rate D-1": ["4.1512 PLN"],
        })

        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        assert "Tax Amount PLN" in result_df.columns
        assert result_df.loc[0, "Tax Amount PLN"] == 0.27

    def test_calculate_tax_when_tax_collected_above_19_percent_then_no_additional_tax(self) -> None:
        """
        Test that when tax collected at source is >= 19%, no additional tax is due in Poland.

        Example: MMM.US with 30% tax collected.
        """
        # Arrange
        df = pd.DataFrame({
            "Date": ["2025-02-21"],
            "Ticker": ["MMM.US"],
            "Shares": [2.0],
            "Net Dividend": ["1.4 USD"],
            "Tax Collected": [0.30],  # 30%
            "Tax Collected Amount": ["0.42 USD"],
            "Exchange Rate D-1": ["3.9974 PLN"],
        })

        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        assert result_df.loc[0, "Tax Amount PLN"] == "-"

    def test_calculate_tax_for_danish_dividend_with_27_percent_tax(self) -> None:
        """
        Test that when tax collected at source is 27%, no additional tax is due in Poland.

        Example: NOVOB.DK with 27% tax collected from 2025-08-19.

        Expected calculation:
        - Net Dividend: 26.25 DKK
        - Tax Collected Amount: 7.09 DKK
        - Tax Collected %: 27%
        - Exchange Rate D-1: 0.5702 PLN

        Since 27% >= 19%, no additional tax is due in Poland.
        Expected result: "-"
        """
        # Arrange
        df = pd.DataFrame({
            "Date": ["2025-08-19"],
            "Ticker": ["NOVOB.DK"],
            "Shares": [7.0],
            "Net Dividend": ["26.25 DKK"],
            "Tax Collected": [0.27],  # 27%
            "Tax Collected Amount": ["7.09 DKK"],
            "Exchange Rate D-1": ["0.5702 PLN"],
        })

        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        assert result_df.loc[0, "Tax Amount PLN"] == "-"

    def test_calculate_tax_for_pln_dividend_then_no_additional_tax(self) -> None:
        """
        Test that PLN dividends with 19% tax collected have no additional tax due.

        Example: XTB.PL with 19% tax collected.
        """
        # Arrange
        df = pd.DataFrame({
            "Date": ["2025-06-25"],
            "Ticker": ["XTB.PL"],
            "Shares": [17.0],
            "Net Dividend": ["92.65 PLN"],
            "Tax Collected": [0.19],  # 19%
            "Tax Collected Amount": ["17.60 PLN"],
            "Exchange Rate D-1": ["-"],
        })

        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        assert result_df.loc[0, "Tax Amount PLN"] == "-"

    def test_calculate_tax_for_zero_tax_collected_then_full_19_percent_due(self) -> None:
        """
        Test that when no tax is collected at source, full 19% is due in Poland.

        Example: ASB.PL with 0% tax collected from 2025-05-29.

        Expected calculation:
        - Net Dividend: 25.5 USD
        - Tax Collected Amount: 0 USD (no tax at source)
        - Tax Collected %: 0%
        - Exchange Rate D-1: 3.7456 PLN

        Calculation:
        - Tax due in USD: 25.5 × 19% = 4.845 USD
        - Tax to pay in USD: 4.845 - 0 = 4.845 USD
        - Tax in PLN: 4.845 × 3.7456 = 18.1476 PLN
        - Rounded: 18.15 PLN
        """
        # Arrange
        df = pd.DataFrame({
            "Date": ["2025-05-29"],
            "Ticker": ["ASB.PL"],
            "Shares": [85.0],
            "Net Dividend": ["25.5 USD"],
            "Tax Collected": [0.0],  # 0%
            "Tax Collected Amount": ["-"],
            "Exchange Rate D-1": ["3.7456 PLN"],
        })

        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        assert result_df.loc[0, "Tax Amount PLN"] == 18.15

    def test_calculate_tax_when_exactly_19_percent_then_no_additional_tax(self) -> None:
        """
        Test edge case: when tax collected is exactly 19%, no additional tax is due.

        This is a critical boundary condition - at exactly 19%, the condition
        tax_percentage >= POLISH_TAX_RATE should return "-".

        Example calculation:
        - Net Dividend: 10.0 USD
        - Tax Collected Amount: 1.9 USD (exactly 19%)
        - Tax Collected %: 19%
        - Exchange Rate D-1: 4.0 PLN

        Expected: No additional tax ("-") because 19% >= 19%
        """
        # Arrange
        df = pd.DataFrame({
            "Date": ["2025-01-15"],
            "Ticker": ["TEST.US"],
            "Shares": [10.0],
            "Net Dividend": ["10.0 USD"],
            "Tax Collected": [0.19],  # Exactly 19%
            "Tax Collected Amount": ["1.9 USD"],
            "Exchange Rate D-1": ["4.0 PLN"],
        })

        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        assert result_df.loc[0, "Tax Amount PLN"] == "-"

    def test_calculate_tax_when_just_below_19_percent_then_small_additional_tax(self) -> None:
        """
        Test edge case: when tax collected is just below 19%, small additional tax is due.

        Example calculation:
        - Net Dividend: 10.0 USD
        - Tax Collected Amount: 1.8 USD (18%)
        - Tax Collected %: 18%
        - Exchange Rate D-1: 4.0 PLN

        Expected calculation:
        - Tax due: 10.0 × 19% = 1.9 USD
        - Tax to pay: 1.9 - 1.8 = 0.1 USD
        - Tax in PLN: 0.1 × 4.0 = 0.4 PLN
        """
        # Arrange
        df = pd.DataFrame({
            "Date": ["2025-01-15"],
            "Ticker": ["TEST.US"],
            "Shares": [10.0],
            "Net Dividend": ["10.0 USD"],
            "Tax Collected": [0.18],  # Just below 19%
            "Tax Collected Amount": ["1.8 USD"],
            "Exchange Rate D-1": ["4.0 PLN"],
        })

        calculator = TaxCalculator(df)

        # Act
        result_df = calculator.calculate_tax_for_pln_statement("PLN")

        # Assert
        assert result_df.loc[0, "Tax Amount PLN"] == 0.4

    def test_calculate_total_tax_amount(self) -> None:
        """Test calculation of total tax amount across multiple rows."""
        # Arrange
        df = pd.DataFrame({
            "Tax Amount PLN": [0.27, "-", 18.15, 0.43, "-"]
        })

        # Act
        total = TaxCalculator.calculate_total_tax_amount(df)

        # Assert
        # 0.27 + 18.15 + 0.43 = 18.85
        assert total == 18.85


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
