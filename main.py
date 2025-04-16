import os
from data_processing.dataframe_processor import DataFrameProcessor
from data_processing.exporter import GoogleSpreadsheetExporter
from data_processing.import_data_xlsx import import_and_process_data
from tabulate import tabulate

def main():
    """
    Main function to read data, process it, and export it to a Google Spreadsheet format.
    """

    # Define file paths
    file_path = 'data/demo_XTB_broker_statement.xlsx'

    # Dynamically find all files starting with "archiwum_tab_a_" in the data folder
    data_folder = 'data'
    courses_paths = [
        os.path.join(data_folder, f) for f in os.listdir(data_folder)
        if f.startswith('archiwum_tab_a_') and f.endswith('.csv')
    ]
    
    # Check if the main file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist. Please check the path.")

    # Check if each course file exists
    for course_path in courses_paths:
        if not os.path.exists(course_path):
            raise FileNotFoundError(f"The file '{course_path}' does not exist. Please check the path.")

    # Load data from XLSX file
    df = import_and_process_data(file_path)

    # Initialize the DataFrameProcessor with the DataFrame
    processor = DataFrameProcessor(df)

    # Detect language before renaming columns
    language = processor.detect_language()
    print(f"Detected language: {language}")  # Debugging statement

    # Drop unnecessary columns
    processor.drop_columns(['ID'])

    # Rename columns based on detected language
    processor.rename_columns({
        processor.get_column_name('Time', 'Czas'): 'Date',
        processor.get_column_name('Symbol', 'Ticker'): 'Ticker',
        processor.get_column_name('Comment', 'Komentarz'): 'Comment',
        processor.get_column_name('Amount', 'Kwota'): 'Amount',
        processor.get_column_name('Type', 'Typ'): 'Type'
    })

    # Continue with processing
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

   # Display processed data
    print(tabulate(processor.get_processed_df(), headers='keys', tablefmt='pretty', showindex=False))

    # Retrieve processed DataFrame
    df_processed = processor.get_processed_df()
    
    # Export data to a CSV file for Google Spreadsheet
    exporter = GoogleSpreadsheetExporter(df_processed) # df with removed ANSI sequences from 'Ticker'
    exporter.export_to_google('for_google_spreadsheet.csv')
    
    return df_processed  # Ensure that the DataFrame is returned

if __name__ == "__main__":
    main()