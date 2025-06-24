import logging
from config.logging_config import setup_logging
from data_processing.file_paths import get_file_paths
from data_processing.dataframe_processor import DataFrameProcessor
from data_processing.exporter import GoogleSpreadsheetExporter
from data_processing.import_data_xlsx import import_and_process_data
from tabulate import tabulate


def process_data(file_path, courses_paths):
    """
    Process the data using DataFrameProcessor and return the processed DataFrame.
    """
    # Load data from XLSX file
    df = import_and_process_data(file_path)

    # Initialize the DataFrameProcessor with the DataFrame
    processor = DataFrameProcessor(df)

    # Detect language before renaming columns
    language = processor.detect_language()

    # Perform data processing steps
    processor.drop_columns(["ID"])
    processor.rename_columns(
        {
            processor.get_column_name("Time", "Czas"): "Date",
            processor.get_column_name("Symbol", "Ticker"): "Ticker",
            processor.get_column_name("Comment", "Komentarz"): "Comment",
            processor.get_column_name("Amount", "Kwota"): "Amount",
            processor.get_column_name("Type", "Typ"): "Type",
        }
    )
    processor.apply_colorize_ticker()
    processor.apply_extractor()
    processor.apply_date_converter()
    processor.filter_dividends()
    processor.group_by_dividends()
    processor.add_empty_column()
    processor.move_negative_values()
    processor.calculate_dividend(courses_paths, language=language)
    processor.replace_tax_with_percentage()
    processor.merge_rows_and_reorder()
    processor.add_currency_to_dividends()

    # Log processed data
    logging.info(
        "\n" + tabulate(
            processor.get_processed_df(),
            headers="keys",
            tablefmt="pretty",
            showindex=False,
        )
    )

    return processor.get_processed_df()


def main():
    """
    Main function to orchestrate the workflow.
    """
    # Set up logging
    setup_logging(log_level=logging.INFO)

    # Define the main file path here
    file_path = "data/demo_XTB_broker_statement.xlsx"

    # Get file paths and validate them
    file_path, courses_paths = get_file_paths(file_path)

    # Process data
    df_processed = process_data(file_path, courses_paths)

    # Export data to a CSV file for Google Spreadsheet
    exporter = GoogleSpreadsheetExporter(df_processed)
    exporter.export_to_google("for_google_spreadsheet.csv")


if __name__ == "__main__":
    main()
