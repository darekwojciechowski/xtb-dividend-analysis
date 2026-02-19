"""XTB Dividend Analysis Pipeline.

Main entry point for processing XTB broker statements and calculating dividend data
with tax calculations according to Polish tax regulations (Belka tax 19%).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from config.logging_config import setup_logging
from config.settings import settings
from data_processing.dataframe_processor import DataFrameProcessor
from data_processing.exporter import GoogleSpreadsheetExporter
from data_processing.file_paths import get_file_paths
from data_processing.import_data_xlsx import import_and_process_data


def process_data(file_path: str, courses_paths: list[str]) -> pd.DataFrame:
    """Process XTB broker statement data through complete transformation pipeline.

    Executes full data processing workflow including:
    - Data extraction and currency detection
    - Column normalization and filtering
    - Dividend calculations with exchange rates
    - Tax calculations according to Polish regulations
    - Data export preparation

    Args:
        file_path: Path to the XTB broker statement XLSX file.
        courses_paths: List of paths to NBP exchange rate CSV files.

    Returns:
        Processed DataFrame with calculated dividends and tax amounts.

    Raises:
        FileNotFoundError: If input file or exchange rate files are missing.
        ValueError: If data format is invalid or required columns are missing.
    """
    df, currency = import_and_process_data(file_path)

    processor = DataFrameProcessor(df)

    statement_currency = processor.detect_statement_currency(currency)

    # Perform data processing steps
    processor.drop_columns(["ID"])
    processor.normalize_column_names()
    processor.apply_colorize_ticker()
    processor.apply_extractor()
    processor.apply_date_converter()
    processor.filter_dividends()
    processor.group_by_dividends()
    processor.add_empty_column()
    processor.move_negative_values()
    processor.create_date_d_minus_1_column("4a")
    processor.calculate_dividend(courses_paths, statement_currency)
    processor.extract_tax_percentage_from_comment(statement_currency)
    processor.merge_rows_and_reorder()
    processor.replace_tax_with_percentage()
    processor.add_tax_percentage_display()
    processor.create_date_d_minus_1_column("8")
    processor.add_currency_to_dividends()
    processor.create_exchange_rate_d_minus_1_column(courses_paths)
    processor.add_tax_collected_amount(statement_currency)

    # Calculate tax in PLN based on detected statement currency
    if statement_currency == "USD":
        processor.calculate_tax_in_pln_for_detected_usd(
            courses_paths, statement_currency)
    else:
        processor.calculate_tax_in_pln_for_detected_pln(statement_currency)

    processor.reorder_columns()
    processor.log_table_with_tax_summary(statement_currency)

    return processor.get_processed_df()


def main() -> None:
    """Orchestrate the complete dividend analysis workflow.

    Sets up logging, validates file paths, processes XTB broker statement data,
    and exports results to CSV format suitable for Google Sheets import.
    """
    setup_logging()

    file_path = settings.get_input_file_path()

    file_path, courses_paths = get_file_paths(str(file_path))

    try:
        df_processed = process_data(file_path, courses_paths)
    except ValueError as e:
        logger.error(f"Processing failed: {e}")
        logger.warning(
            "No exchange rate data found. Please ensure that the NBP currency archive files "
            "(archiwum_tab_a_20XX.csv) are downloaded for the required dates."
        )
        logger.info(
            "To download missing currency data, run: python data_acquisition/playwright_download_currency_archive.py"
        )
        return

    exporter = GoogleSpreadsheetExporter(df_processed)
    exporter.export_to_google(settings.default_output_file)


if __name__ == "__main__":
    main()
