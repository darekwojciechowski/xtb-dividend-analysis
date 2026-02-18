"""Currency conversion integration tests.

Tests the integration of currency detection, exchange rate loading,
and currency conversion across the complete pipeline.

Test Coverage:
    - Currency detection and conversion
    - NBP exchange rate loading
    - Conversion accuracy
    - Multiple currencies in single statement
    - Missing exchange rate error handling
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_currency_detection_and_conversion() -> None:
    """Test currency detection followed by conversion.

    Given: XTB file with USD denomination
    When: detect_statement_currency() → currency_converter
    Then: NBP rates fetched, conversion executed
    """
    # TODO: Implement currency detection and conversion test
    pytest.skip("Implementation in progress")


@pytest.mark.integration
def test_nbp_exchange_rate_loading() -> None:
    """Test loading of NBP exchange rates.

    Given: CSV file with NBP exchange rates
    When: Exchange rates loaded
    Then: Rates available for all transaction dates
    """
    # TODO: Implement exchange rate loading test
    pytest.skip("Implementation in progress")


@pytest.mark.integration
def test_currency_conversion_accuracy() -> None:
    """Test accuracy of currency conversion calculations.

    Given: 100 USD × rate 4.0 = 400 PLN expected
    When: process_data() with USD data
    Then: Amount in PLN = 400.00 (with rounding tolerance)
    """
    # TODO: Implement conversion accuracy test
    pytest.skip("Implementation in progress")


@pytest.mark.integration
def test_multiple_currencies_same_statement() -> None:
    """Test handling of multiple currencies in one statement.

    Given: File with transactions in USD, EUR, GBP
    When: convert_currencies() executes
    Then: Each currency converted with correct rate
    """
    # TODO: Implement multiple currency handling test
    pytest.skip("Implementation in progress")


@pytest.mark.integration
def test_missing_exchange_rate_handling() -> None:
    """Test error handling for missing exchange rates.

    Given: Missing exchange rate for USD
    When: convert_currencies() attempts conversion
    Then: Appropriate error raised (not silent failure)
    """
    # TODO: Implement missing rate error handling test
    pytest.skip("Implementation in progress")
