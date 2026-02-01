# main.py
# XTB Dividend Analysis Pipeline
# Main entry point for processing XTB broker statements and calculating dividend data

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger
from tabulate import tabulate

from config.logging_config import setup_logging
from data_processing.dataframe_processor import DataFrameProcessor
from data_processing.exporter import GoogleSpreadsheetExporter
from data_processing.file_paths import get_file_paths
from data_processing.import_data_xlsx import import_and_process_data

# Configuration constants
DEFAULT_INPUT_FILE = Path("data") / "demo_XTB_broker_statement.xlsx"
DEFAULT_OUTPUT_FILE = "for_google_spreadsheet.csv"


def process_data(file_path: str, courses_paths: list[str]) -> pd.DataFrame:
    """
    Process the data using DataFrameProcessor and return the processed DataFrame.
    """
    # Load data from XLSX file and extract currency
    df, currency = import_and_process_data(file_path)

    # Initialize the DataFrameProcessor with the DataFrame
    processor = DataFrameProcessor(df)

    # Detect statement currency from cell F6
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
    processor.calculate_dividend(courses_paths, statement_currency)
    processor.merge_rows_and_reorder()
    processor.replace_tax_with_percentage()  # Calculate percentage AFTER merging
    processor.calculate_tax_in_pln(courses_paths)  # Calculate tax amount in PLN
    processor.add_tax_percentage_display()  # Add display-friendly percentage column
    processor.create_date_d_minus_1_column()  # Add Date D-1 column
    processor.add_currency_to_dividends()
    processor.create_exchange_rate_d_minus_1_column(
        courses_paths)  # Add Exchange Rate D-1 column
    processor.add_tax_collected_amount()  # Add tax collected amount with currency
    processor.reorder_columns()  # Reorder columns to desired sequence

    # Prepare DataFrame for display (remove numeric Tax Collected column)
    df_display = processor.get_processed_df().copy()
    if "Tax Collected" in df_display.columns:
        df_display = df_display.drop(columns=["Tax Collected"])

    # Log processed data
    logger.info(
        "\n" + tabulate(
            df_display,
            headers="keys",
            tablefmt="pretty",
            showindex=False,
        )
    )

    return processor.get_processed_df()


def main() -> None:
    """
    Main function to orchestrate the workflow.
    """
    # Set up logging
    setup_logging(log_level="INFO")

    # Use default input file path
    file_path = DEFAULT_INPUT_FILE

    # Get file paths and validate them
    file_path, courses_paths = get_file_paths(str(file_path))

    # Process data
    df_processed = process_data(file_path, courses_paths)

    # Export data to a CSV file for Google Spreadsheet
    exporter = GoogleSpreadsheetExporter(df_processed)
    exporter.export_to_google(DEFAULT_OUTPUT_FILE)


if __name__ == "__main__":
    main()
