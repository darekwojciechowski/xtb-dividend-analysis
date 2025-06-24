import os
import re
import pandas as pd
from typing import Optional


class GoogleSpreadsheetExporter:
    def __init__(self, df: pd.DataFrame):
        """
        Initializes the GoogleSpreadsheetExporter with a DataFrame.

        :param df: The DataFrame to be processed and exported.
        """
        self.df = df

    def remove_ansi(self, text: str) -> str:
        """
        Removes ANSI escape sequences from a string.

        :param text: The string containing ANSI escape sequences.
        :return: The string with ANSI sequences removed.
        """
        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        return ansi_escape.sub('', text)

    def export_to_google(self, filename: str = 'for_google_spreadsheet.csv') -> None:
        """
        Processes the DataFrame and exports it to a CSV file formatted for Google Sheets.
        The file is saved in the 'output' directory.

        :param filename: The name of the file to which the DataFrame will be exported.
        """
        # Validate that the DataFrame has a 'Ticker' column
        if 'Ticker' not in self.df.columns:
            raise ValueError("The DataFrame must contain a 'Ticker' column.")

        # Remove ANSI sequences from 'Ticker'
        self.df['Ticker'] = self.df['Ticker'].apply(self.remove_ansi)

        # Replace NaN values with 0
        self.df.fillna(0, inplace=True)

        # Round numeric columns to two decimal places
        numeric_cols = self.df.select_dtypes(include=['number']).columns
        self.df[numeric_cols] = self.df[numeric_cols].round(2)

        # Create output directory if it doesn't exist
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)

        # Create full file path
        file_path = os.path.join(output_dir, filename)

        # Export to CSV with tab as separator
        self.df.to_csv(file_path, sep='\t', index=False)
