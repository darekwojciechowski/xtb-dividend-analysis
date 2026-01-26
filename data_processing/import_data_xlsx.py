# import_data_xlsx.py

from __future__ import annotations

import pandas as pd
from loguru import logger


def import_and_process_data(file_path: str, sheet_name: str = "CASH OPERATION HISTORY") -> pd.DataFrame | None:
    try:
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

        return data

    except FileNotFoundError:
        logger.error(f"The file '{file_path}' was not found.")
    except pd.errors.EmptyDataError:
        logger.error("No data found in the file.")
    except Exception as e:
        logger.error(f"An error occurred while importing the data: {e}")

    return None
