from __future__ import annotations

import re
from datetime import datetime

import numpy as np
import pandas as pd
from loguru import logger

from visualization.ticker_colors import get_random_color

from .date_converter import DateConverter
from .extractor import MultiConditionExtractor


class DataFrameProcessor:
    def __init__(self, df: pd.DataFrame | None = None):
        """
        Initializes the DataFrameProcessor with a DataFrame.

        :param df: The DataFrame to be processed.
        """
        if df is None:
            raise ValueError(
                "The DataFrame 'df' cannot be None. Please provide a valid DataFrame."
            )
        self.df = df.copy()
        logger.info("Step 1 - Initialized DataFrameProcessor with a DataFrame.")

    def detect_language(self) -> str:
        """
        Detects the language of the DataFrame based on column names.

        Returns:
            str: 'PL' if Polish columns are detected, 'ENG' if English columns are detected.
        """
        polish_columns = {"Data", "Symbol", "Komentarz", "Kwota", "Typ"}
        english_columns = {"Date", "Ticker", "Comment", "Amount", "Type"}

        language = (
            "PL"
            if len(polish_columns.intersection(self.df.columns))
            > len(english_columns.intersection(self.df.columns))
            else "ENG"
        )
        logger.info(f"Step 2 - Detected language: {language}.")
        return language

    def get_column_name(self, english_name: str, polish_name: str) -> str:
        """
        Utility function to get the correct column name based on available columns in the DataFrame.

        Args:
            english_name (str): The English name of the column.
            polish_name (str): The Polish name of the column.

        Returns:
            str: The column name present in the DataFrame.
        """
        if english_name in self.df.columns:
            return english_name
        elif polish_name in self.df.columns:
            return polish_name
        else:
            raise ValueError(
                f"Neither '{english_name}' nor '{polish_name}' column found in the DataFrame."
            )

    def drop_columns(self, columns: list[str]) -> None:
        """
        Drops specified columns from the DataFrame.

        :param columns: A list of column names to be dropped.
        """
        if self.df is None or self.df.empty:
            raise ValueError("Error: The DataFrame is empty or has not been loaded.")

        missing_columns = [col for col in columns if col not in self.df.columns]
        if missing_columns:
            raise ValueError(f"Error: Missing columns: {', '.join(missing_columns)}")

        self.df.drop(columns=columns, inplace=True)

    def rename_columns(self, columns_dict: dict[str, str]) -> None:
        """
        Renames columns in the DataFrame based on a dictionary mapping.

        :param columns_dict: A dictionary where keys are current column names and values are new column names.
        """
        missing_columns = [
            col for col in columns_dict.keys() if col not in self.df.columns
        ]
        if missing_columns:
            raise KeyError(
                f"The following columns are missing in the DataFrame: {', '.join(missing_columns)}"
            )

        self.df.rename(columns=columns_dict, inplace=True)

    def normalize_column_names(self) -> None:
        """
        Normalizes column names to English standard names based on detected language.
        Maps Polish or English column names to standardized English names.
        """
        column_mapping = {
            self.get_column_name("Time", "Czas"): "Date",
            self.get_column_name("Symbol", "Ticker"): "Ticker",
            self.get_column_name("Comment", "Komentarz"): "Comment",
            self.get_column_name("Amount", "Kwota"): "Amount",
            self.get_column_name("Type", "Typ"): "Type",
        }
        self.rename_columns(column_mapping)
        logger.info("Normalized column names to English standard.")

    def convert_dates(self, date_col: str | None = None) -> None:
        """
        Converts date strings in the specified column to datetime objects.

        Args:
            date_col (str, optional): The name of the column containing date strings.
                                     If None, tries to find 'Date' or 'Data' column.
        """
        if date_col is None:
            date_col = self.get_column_name("Date", "Data")

        self.df[date_col] = pd.to_datetime(self.df[date_col], errors="coerce")

    def apply_colorize_ticker(self) -> None:
        """
        Applies random color formatting to the 'Ticker' column.
        Creates a new 'Colored Ticker' column without modifying the original 'Ticker' column.
        """
        self.df["Colored Ticker"] = self.df["Ticker"].apply(
            lambda ticker: f"{get_random_color()}{ticker}\033[0m"
        )

    def apply_extractor(self) -> None:
        """
        Applies the MultiConditionExtractor to the 'Comment' column.
        """

        def apply_extractor_func(text: str) -> str:
            extractor = MultiConditionExtractor(text)
            return extractor.extract_condition()

        self.df["Comment"] = self.df["Comment"].apply(apply_extractor_func)

    def apply_date_converter(self) -> None:
        """
        Converts date strings in the 'Date' column to datetime objects.
        """

        def apply_converter(date_string: str) -> pd.Timestamp | None:
            converter = DateConverter(date_string)
            converter.convert_to_date()
            return converter.get_date()

        self.df["Date"] = self.df["Date"].apply(apply_converter)

    def filter_dividends(self) -> None:
        """
        Filters the DataFrame to include only rows where 'Type'/'Typ' is either 'Dividend', 'Dywidenda', 'DIVIDENT',
        'Withholding Tax', 'Podatek od dywidend'. Handles missing values in the 'Type'/'Typ' column.
        """
        type_col = self.get_column_name("Type", "Typ")

        self.df = self.df[self.df[type_col].notna()]
        self.df = self.df[
            self.df[type_col].isin(
                [
                    "Dividend",
                    "Dywidenda",
                    "DIVIDENT",
                    "Withholding Tax",
                    "Podatek od dywidend",
                ]
            )
        ]
        logger.info("Step 3 - Filtered rows to include only dividend-related data.")

    def group_by_dividends(self) -> None:
        """
        Groups the DataFrame by 'Date'/'Data', 'Ticker'/'Symbol', and 'Type'/'Typ',
        then aggregates the 'Amount'/'Kwota' column.
        """
        date_col = self.get_column_name("Date", "Data")
        ticker_col = self.get_column_name("Ticker", "Symbol")
        type_col = self.get_column_name("Type", "Typ")
        comment_col = self.get_column_name("Comment", "Komentarz")
        amount_col = self.get_column_name("Amount", "Kwota")

        self.df = (
            self.df.groupby([date_col, ticker_col, type_col, comment_col])
            .agg({amount_col: "sum"})
            .reset_index()
        )
        self.df.rename(columns={amount_col: "Net Dividend"}, inplace=True)
        logger.info(
            "Step 4 - Grouped data by date, ticker, and type; aggregated amounts."
        )

    def add_empty_column(
        self, col_name: str = "Tax Collected", position: int = 4
    ) -> None:
        """
        Adds an empty column to the DataFrame if it does not already exist.

        :param col_name: The name of the column to be added. Defaults to 'Tax Collected'.
        :param position: The position to insert the column. Defaults to 4.
        """
        if col_name not in self.df.columns:
            self.df.insert(position, col_name, pd.NA)

    def prepare_columns(self) -> None:
        """
        Ensures that 'Tax Collected' and 'Net Dividend' columns exist in the DataFrame.
        """
        if "Tax Collected" not in self.df.columns:
            self.df["Tax Collected"] = np.nan

        if "Net Dividend" not in self.df.columns:
            self.df["Net Dividend"] = np.nan

    def convert_columns_to_numeric(self) -> None:
        """
        Converts 'Net Dividend' and 'Tax Collected' columns to numeric types, coercing errors to NaN.
        """
        self.df["Net Dividend"] = pd.to_numeric(
            self.df["Net Dividend"], errors="coerce"
        )
        self.df["Tax Collected"] = pd.to_numeric(
            self.df["Tax Collected"], errors="coerce"
        )

    def move_negative_values(self) -> None:
        """
        Moves negative values from 'Net Dividend' to 'Tax Collected' and sets the original 'Net Dividend' to NaN.
        """
        self.prepare_columns()
        self.df.loc[self.df["Net Dividend"] < 0, "Tax Collected"] = self.df[
            "Net Dividend"
        ]
        self.df.loc[self.df["Net Dividend"] < 0, "Net Dividend"] = np.nan

    def merge_and_sum(self) -> None:
        """
        Merges rows with the same 'Date' and 'Ticker', summing 'Net Dividend' and 'Tax Collected' columns.
        Updates the internal DataFrame.
        """
        self.prepare_columns()
        self.convert_columns_to_numeric()
        self.df.fillna(0, inplace=True)

        self.df = self.df.groupby(["Date", "Ticker"], as_index=False).agg(
            {"Net Dividend": "sum", "Tax Collected": "sum"}
        )

        self.df["Net Dividend"] = self.df["Net Dividend"].replace(0, np.nan)
        self.df["Tax Collected"] = self.df["Tax Collected"].replace(0, np.nan)

    def merge_rows_and_reorder(
        self, drop_columns: list[str] = ["Type", "Comment"]
    ) -> None:
        """
        Merges rows in the DataFrame with the same 'Date' and 'Ticker',
        removes the specified columns ('Type', 'Comment' by default),
        moves 'Shares' column to the end, and rounds numeric values to 2 decimal places.

        :param drop_columns: A list of columns to drop after merging. Defaults to ['Type', 'Comment'].
        """
        # Merge rows with the same 'Date' and 'Ticker'
        self.df = self.df.groupby(["Date", "Ticker"], as_index=False).agg(
            {
                "Net Dividend": "sum",
                "Tax Collected": "sum",
                "Shares": "sum",  # Assuming 'Shares' column exists and should also be summed
            }
        )

        # Drop specified columns (if they exist in the DataFrame)
        self.df.drop(columns=drop_columns, errors="ignore", inplace=True)

        # Round the numeric columns to 2 decimal places
        self.df["Net Dividend"] = pd.to_numeric(
            self.df["Net Dividend"], errors='coerce').round(2)
        self.df["Tax Collected"] = pd.to_numeric(
            self.df["Tax Collected"], errors='coerce').round(2)
        # If Shares column exists and needs rounding
        self.df["Shares"] = pd.to_numeric(self.df["Shares"], errors='coerce').round(2)

        # Move 'Shares' column to the end
        shares_col = self.df.pop("Shares")
        self.df["Shares"] = shares_col

    def _extract_dividend_from_comment(self, comment: str) -> tuple[float | None, str | None]:
        """
        Extract dividend per share and currency from the comment string.

        Args:
            comment (str): The comment containing dividend details.

        Returns:
            tuple: (dividend_per_share, currency) or (None, None) if not found.
        """
        if not isinstance(comment, str):
            return None, None

        # Try to match the pattern "USD X.XX/ SHR" or "PLN X.XX/ SHR"
        match = re.search(r"(USD|PLN) ([\d.]+)/ SHR", comment)
        if match:
            return float(match.group(2)), match.group(1)

        # Try alternative pattern "X.XX USD/SHR" or "X.XX PLN/SHR"
        match = re.search(r"([\d.]+) (USD|PLN)/SHR", comment)
        if match:
            return float(match.group(1)), match.group(2)

        # Try to match just a number (assume default currency based on ticker)
        match = re.search(r"([\d.]+)", comment)
        if match:
            return float(match.group(1)), None

        return None, None

    def _determine_currency(self, ticker: str, extracted_currency: str | None) -> str:
        """
        Determine the currency based on ticker and extracted currency.

        Args:
            ticker (str): The stock ticker.
            extracted_currency (str): Currency extracted from comment.

        Returns:
            str: Determined currency ('USD', 'PLN', 'EUR', 'DKK', 'GBP')
        """
        if extracted_currency:
            return extracted_currency

        # If no currency in comment, infer from ticker
        if ".US" in ticker:
            return "USD"
        elif ".PL" in ticker:
            # Special case for ASB.PL which uses USD
            if "ASB.PL" in ticker:
                return "USD"
            return "PLN"
        elif ".DK" in ticker:
            return "DKK"
        elif ".UK" in ticker:
            return "GBP"
        elif any(suffix in ticker for suffix in [".FR", ".DE", ".IE", ".NL", ".ES", ".IT", ".BE", ".AT", ".FI", ".PT"]):
            return "EUR"

        # Default to USD if can't determine
        return "USD"

    def add_currency_to_dividends(self) -> None:
        """
        Appends currency symbols to the 'Net Dividend' column based on the ticker:
        - USD for .US tickers
        - PLN for .PL tickers (except ASB.PL which uses USD)
        - EUR for eurozone tickers (.FR, .DE, .IE, .NL, .ES, .IT, .BE, .AT, .FI, .PT)
        - DKK for .DK tickers
        - GBP for .UK tickers
        """

        def append_currency(row):
            ticker = row["Ticker"]
            dividend = row["Net Dividend"]

            if ".US" in ticker:
                return f"{dividend} USD"
            elif "ASB.PL" in ticker:
                # Exception for ASB.PL (uses USD)
                return f"{dividend} USD"
            elif ".PL" in ticker:
                return f"{dividend} PLN"
            elif ".DK" in ticker:
                return f"{dividend} DKK"
            elif ".UK" in ticker:
                return f"{dividend} GBP"
            elif any(suffix in ticker for suffix in [".FR", ".DE", ".IE", ".NL", ".ES", ".IT", ".BE", ".AT", ".FI", ".PT"]):
                return f"{dividend} EUR"
            # No change if the condition doesn't match
            return dividend

        # Apply the currency formatting
        self.df["Net Dividend"] = self.df.apply(append_currency, axis=1)

    def calculate_dividend(
        self, courses_paths: list[str], language: str, comment_col: str | None = None, amount_col: str | None = None, date_col: str | None = None
    ) -> pd.DataFrame:
        """
        Modify the Net Dividend column based on the number extracted from the Comment column
        and calculate shares based on the extracted dividend amount and the retrieved exchange rate
        for the specific date in each row.

        Args:
            courses_paths (list): A list of CSV file paths for retrieving USD exchange rates.
            language (str): The detected language of the DataFrame ('PL' or 'ENG').
            comment_col (str, optional): The name of the column containing the comments to extract numbers from.
            amount_col (str, optional): The name of the column (Net Dividend) to update with the extracted values.
            date_col (str, optional): The name of the column containing the date for retrieving the exchange rate.
        """
        # Use get_column_name to handle multilingual column names
        comment_col = comment_col or self.get_column_name("Comment", "Komentarz")
        amount_col = amount_col or "Net Dividend"
        date_col = date_col or self.get_column_name("Date", "Data")

        def get_usd_exchange_rate(courses_paths, target_date_str):
            """
            Retrieve the exchange rate for 1 USD on a specific date from multiple CSV files.

            Args:
                courses_paths (list): List of CSV file paths.
                target_date_str (str): The date in 'YYYY-MM-DD' format to search for.

            Returns:
                float: The exchange rate for 1 USD on the specified date.
            """
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
            target_date_str_formatted = target_date.strftime("%Y%m%d")

            for csv_file in courses_paths:
                try:
                    df = pd.read_csv(csv_file, sep=";", encoding="ISO-8859-1")
                    usd_value = df[df["data"] == target_date_str_formatted][
                        "1USD"
                    ].values

                    if len(usd_value) > 0:
                        return float(usd_value[0].replace(",", "."))
                except FileNotFoundError:
                    print(f"Warning: The file '{csv_file}' was not found.")
                except Exception as e:
                    print(f"An error occurred while processing '{csv_file}': {e}")

            print(
                f"Error: No data found for the date '{target_date_str}'. Check if you have downloaded the file 'archiwum_tab_a_XXXX.csv' for the date '{target_date_str}'."
            )
            return 0.0

        def calculate_shares(total_dividend, dividend_per_share, exchange_rate):
            """
            Calculate the number of shares based on the total dividend value using the formula:
            Shares = Total Dividend / (Dividend per Share * Exchange Rate)

            Args:
                total_dividend (float): Total dividend value.
                dividend_per_share (float): Dividend per share.
                exchange_rate (float): Exchange rate for currency conversion.

            Returns:
                float: Number of shares, rounded to two decimal places.
            """
            if dividend_per_share * exchange_rate == 0:
                print("Warning: Division by zero encountered in shares calculation.")
                return 0.0

            shares = total_dividend / (dividend_per_share * exchange_rate)
            return round(shares, 2)

        # Add Shares column if it doesn't exist
        if "Shares" not in self.df.columns:
            self.df["Shares"] = np.nan

        # Add Currency column if it doesn't exist
        if "Currency" not in self.df.columns:
            self.df["Currency"] = None

        for index, row in self.df.iterrows():
            if (
                pd.isna(row[date_col])
                or pd.isna(row[amount_col])
                or pd.isna(row[comment_col])
            ):
                continue

            target_date_str = row[date_col].strftime("%Y-%m-%d")
            total_dividend = float(row[amount_col])
            ticker = row["Ticker"]

            extracted_value, extracted_currency = self._extract_dividend_from_comment(
                row[comment_col])

            if extracted_value is not None and extracted_value > 0:
                # Store the dividend per share
                dividend_per_share = extracted_value

                # Determine currency based on ticker and extracted info
                currency = self._determine_currency(ticker, extracted_currency)
                self.df.at[index, "Currency"] = currency

                # Apply exchange rate based on language and currency
                exchange_rate = 1.0  # Default exchange rate

                # Only apply exchange rate conversion for Polish interface with USD dividends
                if language == "PL" and currency == "USD":
                    exchange_rate = get_usd_exchange_rate(
                        courses_paths, target_date_str
                    )
                    if exchange_rate == 0:
                        continue  # Skip if we couldn't get a valid exchange rate

                # Calculate shares based on total dividend and dividend per share
                shares = calculate_shares(
                    total_dividend, dividend_per_share, exchange_rate
                )

                # Validate that shares is a whole number (not fractional)
                # Allow small tolerance for rounding errors (0.01)
                fractional_part = abs(shares - round(shares))
                if fractional_part > 0.01:
                    error_msg = (
                        f"Non-integer share count detected for {ticker} on {target_date_str}: "
                        f"{shares} shares (Total: {total_dividend} {currency}, Per share: {dividend_per_share} {currency}). "
                        f"Data inconsistency - expected whole number of shares. "
                        f"Please verify source data in the Excel file."
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # Round shares to the nearest integer
                self.df.at[index, "Shares"] = round(shares)

                # Keep the dividend per share value in the amount column
                self.df.at[index, amount_col] = dividend_per_share

        # Calculate the total dividend amount after processing
        self.df[amount_col] = self.df.apply(
            lambda row: (
                row["Shares"] * row[amount_col]
                if not pd.isna(row["Shares"])
                else row[amount_col]
            ),
            axis=1,
        )
        logger.info(
            "Step 5 - Calculated dividends and updated shares using exchange rates."
        )

        return self.df

    def replace_tax_values(
        self, ticker_col: str | None = None, amount_col: str | None = None, tax_col: str = "Tax Collected"
    ) -> pd.DataFrame:
        """
        Update the 'Tax Collected' column based on the 'Net Dividend' column and ticker type.
        Applies withholding tax rates at source: 15% for US stocks and 19% for Polish stocks.

        Args:
            ticker_col (str, optional): The name of the column containing the ticker information.
            amount_col (str, optional): The name of the column (Net Dividend) to base the calculation on.
            tax_col (str): The name of the column to update with the tax values.
        """
        # Use get_column_name to handle multilingual column names
        ticker_col = ticker_col or self.get_column_name("Ticker", "Symbol")
        amount_col = amount_col or "Net Dividend"
        # Define the withholding tax rates at source for US, PL, DK, UK, IE and FR
        # Note: US default is 15% with W8BEN form. Without W8BEN, the rate is 30%.
        tax_rates = {
            "US": 0.15,  # 15% withholding tax for US stocks (with W8BEN form)
            "PL": 0.19,  # 19% withholding tax for PL stocks (Belka tax)
            "DK": 0.15,  # 15% withholding tax for DK stocks (Denmark)
            # 0% withholding tax for UK stocks (no UK withholding tax for non-residents)
            "UK": 0.0,
            # 15% withholding tax for IE stocks (Ireland, reduced rate for Polish residents)
            "IE": 0.15,
            # 0% withholding tax for FR stocks (France, under Poland-France tax treaty)
            "FR": 0.0,
        }

        # Iterate over each row in the DataFrame
        for index, row in self.df.iterrows():
            ticker = row[ticker_col]  # Get the ticker for the current row
            # Get the value from 'Net Dividend'
            net_dividend = row[amount_col]

            # Determine the tax rate based on the ticker
            if "US" in ticker:
                tax_rate = tax_rates["US"]
            elif "PL" in ticker:
                tax_rate = tax_rates["PL"]
            elif "DK" in ticker:
                tax_rate = tax_rates["DK"]
            elif "UK" in ticker:
                tax_rate = tax_rates["UK"]
            elif "IE" in ticker:
                tax_rate = tax_rates["IE"]
            elif "FR" in ticker:
                tax_rate = tax_rates["FR"]
            else:
                tax_rate = 0.0  # No tax if ticker is not recognized

            # Calculate the tax based on 'Net Dividend'
            tax_collected = net_dividend * tax_rate

            # Update the 'Tax Collected' column
            self.df.at[index, tax_col] = tax_collected

        return self.df

    def replace_tax_with_percentage(self, tax_col: str = "Tax Collected", amount_col: str = "Net Dividend") -> pd.DataFrame:
        """
        Calculate tax percentage based on actual tax amount and net dividend amount.
        Replaces absolute tax values with percentages (Tax Collected / Net Dividend).

        Args:
            tax_col (str): The name of the column containing tax amounts.
            amount_col (str): The name of the column containing net dividend amounts.
        """
        us_tax_30_warning_shown = False

        # Iterate over each row to calculate percentage
        for index, row in self.df.iterrows():
            tax_amount = row[tax_col]
            net_dividend = row[amount_col]
            ticker = row.get("Ticker", "")

            # Calculate percentage if both values are valid
            if pd.notna(tax_amount) and pd.notna(net_dividend) and net_dividend != 0:
                # Tax amount should be negative or positive absolute value
                # Convert to percentage: abs(tax) / dividend
                tax_percentage = abs(tax_amount) / abs(net_dividend)
                # Round to 2 decimal places
                self.df.at[index, tax_col] = round(tax_percentage, 2)

                # Check if US dividend has 30% tax rate
                if "US" in ticker and abs(tax_percentage - 0.30) < 0.01 and not us_tax_30_warning_shown:
                    logger.warning(
                        f"⚠️  WARNING: 30% tax rate detected for US dividend {ticker}. "
                        f"In Poland, you can file a W8BEN form with your broker, "
                        f"which reduces the withholding tax from 30% to 15% according to the double taxation treaty."
                    )
                    us_tax_30_warning_shown = True
            else:
                # If cannot calculate, set to NaN
                self.df.at[index, tax_col] = np.nan

        logger.info(
            "Step 6 - Updated 'Tax Collected' column with calculated tax percentages."
        )

        return self.df

    def get_processed_df(self) -> pd.DataFrame:
        """
        Returns the processed DataFrame.

        :return: The processed DataFrame.
        """
        logger.info("Step 7 - Returning the processed DataFrame.")  # Log here
        return self.df

    def process(self) -> pd.DataFrame:
        """
        Processes the DataFrame by applying a standard sequence of transformations.

        Returns:
            pd.DataFrame: The processed DataFrame.
        """
        logger.info("Starting DataFrame processing.")
        # Convert dates if needed
        self.convert_dates()

        # Filter and group dividends
        self.filter_dividends()
        self.group_by_dividends()

        # Add tax column if needed
        if "Tax Collected" not in self.df.columns:
            self.add_empty_column("Tax Collected")

        # Process tax information
        self.replace_tax_with_percentage()

        # Merge and clean up
        self.merge_and_sum()
        logger.info("DataFrame processing completed.")

        return self.df
