"""XTB broker statement XLSX importer.

This module reads an XTB ``CASH OPERATION HISTORY`` sheet from an
``.xlsx`` file and detects the account currency from cell F6.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd
from loguru import logger


def import_and_process_data(
    file_path: Path,
    sheet_name: str = "CASH OPERATION HISTORY",
) -> tuple[pd.DataFrame | None, str | None]:
    """Import and process data from an XTB broker statement.

    Reads cell F6 for the account currency, locates the header row by
    searching for ``ID``, then loads the transaction table below it.

    Args:
        file_path: Path to the XLSX file.
        sheet_name: Name of the sheet to read.

    Returns:
        A tuple ``(df, currency)`` where ``df`` is a DataFrame of
        transaction rows and ``currency`` is the currency code from
        cell F6. Returns ``(None, None)`` if an error occurs.
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

        logger.info(f"Detected currency for this XTB spreadsheet: {currency}")

        return data, currency

    except FileNotFoundError:
        logger.error(f"The file '{file_path}' was not found.")
    except pd.errors.EmptyDataError:
        logger.error("No data found in the file.")
    except Exception as e:
        logger.error(f"An error occurred while importing the data: {e}")

    return None, None
