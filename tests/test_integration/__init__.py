"""Integration tests for XTB Dividend Analysis.

This package contains integration tests that verify the correct interaction
between multiple components of the application. Unlike unit tests that mock
dependencies, integration tests use real implementations to verify the system
works correctly end-to-end.

Test Organization:
    test_data_pipeline.py: Full end-to-end pipeline tests
    test_data_import_processing.py: Import + processing chain tests
    test_currency_conversion_integration.py: Currency handling tests
    test_tax_calculation_integration.py: Tax calculation tests
    test_export_functionality.py: Export pipeline tests
    test_error_handling_integration.py: Error handling tests
"""
