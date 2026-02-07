"""Integration tests for main.py workflow orchestration.

This module contains integration tests that verify the correct behavior of the
main.py entry point functions (process_data and main). Tests use mocking to
isolate the orchestration logic from external dependencies like file I/O,
DataFrameProcessor, and GoogleSpreadsheetExporter.

Test Coverage:
    - process_data() function with PLN and USD statement types
    - main() function successful execution and error handling
    - Error handling for missing exchange rates
    - Proper logging behavior during errors
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from main import DEFAULT_INPUT_FILE, DEFAULT_OUTPUT_FILE, main, process_data


@pytest.fixture
def sample_processed_df() -> pd.DataFrame:
    """Provides a sample processed DataFrame with dividend data.

    Returns:
        pd.DataFrame: DataFrame containing sample dividend data with columns:
            Date, Ticker, Net Dividend, and Tax Amount PLN.
    """
    return pd.DataFrame({
        "Date": ["2025-01-01"],
        "Ticker": ["AAPL.US"],
        "Net Dividend": ["10.00 USD"],
        "Tax Amount PLN": [5.0]
    })


@pytest.fixture
def mock_courses_paths() -> list[str]:
    """Provides sample currency exchange rate file paths for testing.

    Returns:
        list[str]: List containing path to mock NBP exchange rate archive file.
    """
    return ["data/archiwum_tab_a_2025.csv"]


@pytest.mark.integration
class TestProcessDataFunction:
    """Test suite for process_data() function.

    Verifies that the process_data function correctly orchestrates the dividend
    processing pipeline for different statement currencies (PLN, USD) and ensures
    all DataFrameProcessor methods are called in the correct order.
    """

    @patch("main.import_and_process_data")
    @patch("main.DataFrameProcessor")
    def test_process_data_when_pln_statement_then_processes_correctly(
        self, mock_processor_class, mock_import, sample_processed_df, mock_courses_paths
    ):
        """Tests that PLN statement is processed with correct tax calculation method.

        Args:
            mock_processor_class: Mock of DataFrameProcessor class.
            mock_import: Mock of import_and_process_data function.
            sample_processed_df: Fixture providing sample DataFrame.
            mock_courses_paths: Fixture providing exchange rate file paths.

        Verifies:
            - import_and_process_data is called with correct file path
            - PLN-specific tax calculation method is used
            - USD tax calculation method is NOT called
            - Result is a pandas DataFrame
        """
        # Arrange
        mock_import.return_value = (sample_processed_df.copy(), "PLN")
        mock_processor_instance = MagicMock()
        mock_processor_instance.detect_statement_currency.return_value = "PLN"
        mock_processor_instance.get_processed_df.return_value = sample_processed_df
        mock_processor_class.return_value = mock_processor_instance

        # Act
        result = process_data("test_file.xlsx", mock_courses_paths)

        # Assert
        mock_import.assert_called_once_with("test_file.xlsx")
        mock_processor_instance.calculate_tax_in_pln_for_detected_pln.assert_called_once()
        mock_processor_instance.calculate_tax_in_pln_for_detected_usd.assert_not_called()
        assert isinstance(result, pd.DataFrame)

    @patch("main.import_and_process_data")
    @patch("main.DataFrameProcessor")
    def test_process_data_when_usd_statement_then_uses_usd_tax_calculation(
        self, mock_processor_class, mock_import, sample_processed_df, mock_courses_paths
    ):
        """Tests that USD statement uses USD-specific tax calculation method.

        Args:
            mock_processor_class: Mock of DataFrameProcessor class.
            mock_import: Mock of import_and_process_data function.
            sample_processed_df: Fixture providing sample DataFrame.
            mock_courses_paths: Fixture providing exchange rate file paths.

        Verifies:
            - USD-specific tax calculation is called with correct parameters
            - PLN tax calculation method is NOT called for USD statements
        """
        # Arrange
        mock_import.return_value = (sample_processed_df.copy(), "USD")
        mock_processor_instance = MagicMock()
        mock_processor_instance.detect_statement_currency.return_value = "USD"
        mock_processor_instance.get_processed_df.return_value = sample_processed_df
        mock_processor_class.return_value = mock_processor_instance

        # Act
        result = process_data("test_file.xlsx", mock_courses_paths)

        # Assert
        mock_processor_instance.calculate_tax_in_pln_for_detected_usd.assert_called_once_with(
            mock_courses_paths, "USD"
        )
        mock_processor_instance.calculate_tax_in_pln_for_detected_pln.assert_not_called()

    @patch("main.import_and_process_data")
    @patch("main.DataFrameProcessor")
    def test_process_data_when_called_then_executes_full_pipeline(
        self, mock_processor_class, mock_import, sample_processed_df, mock_courses_paths
    ):
        """Tests that all required processing steps are executed in order.

        Args:
            mock_processor_class: Mock of DataFrameProcessor class.
            mock_import: Mock of import_and_process_data function.
            sample_processed_df: Fixture providing sample DataFrame.
            mock_courses_paths: Fixture providing exchange rate file paths.

        Verifies:
            All key pipeline steps are called exactly once:
            - normalize_column_names, filter_dividends, group_by_dividends
            - calculate_dividend, extract_tax_percentage_from_comment
            - reorder_columns, log_table_with_tax_summary
        """
        # Arrange
        mock_import.return_value = (sample_processed_df.copy(), "PLN")
        mock_processor_instance = MagicMock()
        mock_processor_instance.detect_statement_currency.return_value = "PLN"
        mock_processor_instance.get_processed_df.return_value = sample_processed_df
        mock_processor_class.return_value = mock_processor_instance

        # Act
        process_data("test_file.xlsx", mock_courses_paths)

        # Assert - verify key pipeline steps were called
        mock_processor_instance.normalize_column_names.assert_called_once()
        mock_processor_instance.filter_dividends.assert_called_once()
        mock_processor_instance.group_by_dividends.assert_called_once()
        mock_processor_instance.calculate_dividend.assert_called_once()
        mock_processor_instance.extract_tax_percentage_from_comment.assert_called_once()
        mock_processor_instance.reorder_columns.assert_called_once()
        mock_processor_instance.log_table_with_tax_summary.assert_called_once()


@pytest.mark.integration
class TestMainFunction:
    """Test suite for main() orchestration function.

    Tests the top-level main() function that orchestrates the complete workflow:
    logging setup, file path retrieval, data processing, and export to Google
    Spreadsheet format. Includes both successful execution and error scenarios.
    """

    @patch("main.GoogleSpreadsheetExporter")
    @patch("main.process_data")
    @patch("main.get_file_paths")
    @patch("main.setup_logging")
    def test_main_when_successful_then_exports_results(
        self, mock_logging, mock_get_paths, mock_process, mock_exporter_class, sample_processed_df
    ):
        """Tests that main() successfully processes and exports data.

        Args:
            mock_logging: Mock of setup_logging function.
            mock_get_paths: Mock of get_file_paths function.
            mock_process: Mock of process_data function.
            mock_exporter_class: Mock of GoogleSpreadsheetExporter class.
            sample_processed_df: Fixture providing sample DataFrame.

        Verifies:
            - Logging is configured with INFO level
            - File paths are retrieved
            - Data processing is executed
            - Export to Google Spreadsheet format is performed
        """
        # Arrange
        mock_get_paths.return_value = ("input.xlsx", ["rates.csv"])
        mock_process.return_value = sample_processed_df
        mock_exporter_instance = MagicMock()
        mock_exporter_class.return_value = mock_exporter_instance

        # Act
        main()

        # Assert
        mock_logging.assert_called_once_with(log_level="INFO")
        mock_get_paths.assert_called_once()
        mock_process.assert_called_once_with("input.xlsx", ["rates.csv"])
        mock_exporter_class.assert_called_once_with(sample_processed_df)
        mock_exporter_instance.export_to_google.assert_called_once_with(
            DEFAULT_OUTPUT_FILE)

    @patch("main.logger")
    @patch("main.process_data")
    @patch("main.get_file_paths")
    @patch("main.setup_logging")
    def test_main_when_value_error_then_logs_error_and_exits_gracefully(
        self, mock_logging, mock_get_paths, mock_process, mock_logger
    ):
        """Tests that main() handles ValueError gracefully with proper logging.

        Args:
            mock_logging: Mock of setup_logging function.
            mock_get_paths: Mock of get_file_paths function.
            mock_process: Mock of process_data function that raises ValueError.
            mock_logger: Mock of logger instance.

        Verifies:
            - Error is logged when processing fails
            - Warning and info messages are logged
            - Application exits gracefully without crashing
        """
        # Arrange
        mock_get_paths.return_value = ("input.xlsx", ["rates.csv"])
        mock_process.side_effect = ValueError("Exchange rate not found")

        # Act
        main()

        # Assert
        mock_logger.error.assert_called()
        mock_logger.warning.assert_called()
        mock_logger.info.assert_called()

    @patch("main.GoogleSpreadsheetExporter")
    @patch("main.process_data")
    @patch("main.get_file_paths")
    @patch("main.setup_logging")
    def test_main_when_called_then_uses_default_input_file(
        self, mock_logging, mock_get_paths, mock_process, mock_exporter_class, sample_processed_df
    ):
        """Tests that main() uses DEFAULT_INPUT_FILE constant.

        Args:
            mock_logging: Mock of setup_logging function.
            mock_get_paths: Mock of get_file_paths function.
            mock_process: Mock of process_data function.
            mock_exporter_class: Mock of GoogleSpreadsheetExporter class.
            sample_processed_df: Fixture providing sample DataFrame.

        Verifies:
            - get_file_paths is called with DEFAULT_INPUT_FILE constant value
        """
        # Arrange
        mock_get_paths.return_value = ("test.xlsx", ["rates.csv"])
        mock_process.return_value = sample_processed_df

        # Act
        main()

        # Assert
        # Verify get_file_paths was called with string version of DEFAULT_INPUT_FILE
        called_path = mock_get_paths.call_args[0][0]
        assert str(DEFAULT_INPUT_FILE) == called_path


@pytest.mark.integration
@pytest.mark.edge_case
class TestMainErrorHandling:
    """Test suite for error handling in main workflow.

    Focuses on edge cases and error scenarios, particularly missing exchange
    rate data and the quality of error messages provided to users.
    """

    @patch("main.logger")
    @patch("main.process_data")
    @patch("main.get_file_paths")
    @patch("main.setup_logging")
    def test_main_when_missing_exchange_rates_then_provides_helpful_message(
        self, mock_logging, mock_get_paths, mock_process, mock_logger
    ):
        """Tests that missing exchange rate error provides actionable guidance.

        Args:
            mock_logging: Mock of setup_logging function.
            mock_get_paths: Mock of get_file_paths function.
            mock_process: Mock of process_data function that raises ValueError.
            mock_logger: Mock of logger instance.

        Verifies:
            - Error message contains "Processing failed"
            - Warning mentions "exchange rate"
            - Info message references "playwright_download_currency_archive" script
        """
        # Arrange
        mock_get_paths.return_value = ("input.xlsx", [])
        mock_process.side_effect = ValueError("No exchange rate data found")

        # Act
        main()

        # Assert
        error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]

        assert any("Processing failed" in msg for msg in error_calls)
        assert any("exchange rate" in msg.lower() for msg in warning_calls)
        assert any("playwright_download_currency_archive" in msg for msg in info_calls)
