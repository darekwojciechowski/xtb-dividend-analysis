# import_data_xlsx.py

from __future__ import annotations

import openpyxl
import pandas as pd
from loguru import logger


def import_and_process_data(file_path: str, sheet_name: str = "CASH OPERATION HISTORY") -> tuple[pd.DataFrame | None, str | None]:
    """
    Import and process data from XTB broker statement.

    Args:
        file_path: Path to the XLSX file
        sheet_name: Name of the sheet to read

    Returns:
        tuple: (DataFrame with transaction data, currency code from cell F6)
               Returns (None, None) if an error occurs
    """
    try:
        # First, extract currency from cell F6 using openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb[sheet_name]
        currency = ws['F6'].value
        wb.close()

        # Load the entire sheet
        all_data = pd.read_excel(file_path, sheet_name=sheet_name, header=None)

        # Find the row containing "ID"
        header_row_index = all_data[all_data.isin(["ID"]).any(axis=1)].index[0]

        # Load data from the row with headers
        data = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row_index)

        # Remove columns 'Unnamed: 0' and 'Unnamed: 7' (if they exist)
        data = data.drop(columns=["Unnamed: 0", "Unnamed: 7"], errors="ignore")

        # Remove rows containing "Total" in any column
        data = data[
            ~data.apply(lambda row: row.astype(str).str.contains("Total").any(), axis=1)
        ]

        logger.info(f"Detected currency from cell F6: {currency}")

        return data, currency

    except FileNotFoundError:
        logger.error(f"The file '{file_path}' was not found.")
    except pd.errors.EmptyDataError:
        logger.error("No data found in the file.")
    except Exception as e:
        logger.error(f"An error occurred while importing the data: {e}")

    return None, None
