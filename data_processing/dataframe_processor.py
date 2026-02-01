from __future__ import annotations

import re
from datetime import datetime, timedelta

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

        # Try to match the pattern "XXX WHT" (currency with withholding tax, e.g., "PLN WHT 19%")
        match = re.search(r"([A-Z]{3})\s+WHT", comment)
        if match:
            currency = match.group(1)
            # Try to find a dividend amount in the same comment (e.g., "0.3000/ SHR")
            dividend_match = re.search(r"([\d.]+)\s*/\s*SHR", comment)
            if dividend_match:
                return float(dividend_match.group(1)), currency
            # If no dividend amount found, return None for dividend but still return currency
            return None, currency

        # Try to match the pattern "XXX X.XX/ SHR" (any 3-letter currency)
        match = re.search(r"([A-Z]{3}) ([\d.]+)/ SHR", comment)
        if match:
            return float(match.group(2)), match.group(1)

        # Try alternative pattern "X.XX XXX/SHR" (any 3-letter currency)
        match = re.search(r"([\d.]+) ([A-Z]{3})/SHR", comment)
        if match:
            return float(match.group(1)), match.group(2)

        # Try to match just a number (assume default currency based on ticker)
        match = re.search(r"([\d.]+)", comment)
        if match:
            num_str = match.group(1)
            # Avoid matching a single '.' which is not a valid number
            if num_str == ".":
                return None, None
            return float(num_str), None

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

    def _extract_tax_rate_from_comment(self, comment: str) -> float | None:
        """
        Extract tax rate from comment string (e.g., 'WHT 27%' or '19%').

        Args:
            comment (str): Comment string potentially containing tax rate.

        Returns:
            float | None: Tax rate as decimal (e.g., 0.27 for 27%) or None if not found.
        """
        if not isinstance(comment, str):
            return None

        # Try to match WHT pattern first (more specific)
        match = re.search(r"WHT\s*(\d+(?:\.\d+)?)%", comment)
        if match:
            return float(match.group(1)) / 100

        # Try to match any percentage pattern
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', comment)
        if match:
            return float(match.group(1)) / 100

        return None

    def _get_default_tax_rate(self, ticker: str) -> float:
        """
        Get default withholding tax rate based on ticker suffix.

        Args:
            ticker (str): Stock ticker symbol.

        Returns:
            float: Default tax rate as decimal.
        """
        # Define the withholding tax rates at source
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

        for suffix, rate in tax_rates.items():
            if suffix in ticker:
                return rate

        return 0.0  # Default to 0% if country not recognized

    def _get_exchange_rate(self, courses_paths: list[str], target_date_str: str, currency: str) -> float:
        """
        Retrieve the exchange rate for a specific currency on a specific date from CSV files.

        Args:
            courses_paths (list): List of CSV file paths containing exchange rates.
            target_date_str (str): The date in 'YYYY-MM-DD' format to search for.
            currency (str): Currency code ('USD', 'EUR', 'DKK', 'GBP', etc.)

        Returns:
            float: The exchange rate for the specified currency on the specified date.
                   Returns 1.0 for PLN. Returns 0.0 if rate not found.
        """
        # PLN is the base currency, so exchange rate is always 1.0
        if currency == "PLN":
            return 1.0

        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        target_date_str_formatted = target_date.strftime("%Y%m%d")

        # Map currency to column name in NBP data
        currency_column_map = {
            "USD": "1USD",
            "EUR": "1EUR",
            "GBP": "1GBP",
            "DKK": "1DKK",
        }

        column_name = currency_column_map.get(currency)
        if not column_name:
            logger.warning(
                f"Currency '{currency}' not supported for exchange rate lookup. Using 1.0")
            return 1.0

        for csv_file in courses_paths:
            try:
                df = pd.read_csv(csv_file, sep=";", encoding="ISO-8859-1")

                # Check if the column exists
                if column_name not in df.columns:
                    continue

                currency_value = df[df["data"] ==
                                    target_date_str_formatted][column_name].values

                if len(currency_value) > 0:
                    return float(currency_value[0].replace(",", "."))
            except FileNotFoundError:
                logger.warning(f"Exchange rate file '{csv_file}' was not found.")
            except Exception as e:
                logger.warning(f"An error occurred while processing '{csv_file}': {e}")

        logger.error(
            f"No exchange rate data found for {currency} on date '{target_date_str}'. "
            f"Check if you have downloaded the file 'archiwum_tab_a_XXXX.csv' for the date '{target_date_str}'."
        )
        return 0.0

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
                    exchange_rate = self._get_exchange_rate(
                        courses_paths, target_date_str, currency
                    )
                    if exchange_rate == 0:
                        continue  # Skip if we couldn't get a valid exchange rate

                # Calculate shares based on total dividend and dividend per share
                shares = calculate_shares(
                    total_dividend, dividend_per_share, exchange_rate
                )

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
        First tries to extract tax rate from Comment column, then uses default rates.

        Args:
            ticker_col (str, optional): The name of the column containing the ticker information.
            amount_col (str, optional): The name of the column (Net Dividend) to base the calculation on.
            tax_col (str): The name of the column to update with the tax values.
        """
        # Use get_column_name to handle multilingual column names
        ticker_col = ticker_col or self.get_column_name("Ticker", "Symbol")
        amount_col = amount_col or "Net Dividend"

        def calculate_tax(row):
            """Calculate tax for a single row."""
            comment = row.get("Comment", "")

            # First, try to extract the tax rate from the comment
            tax_rate = self._extract_tax_rate_from_comment(comment)

            # If not found in comment, use default rate based on ticker
            if tax_rate is None:
                tax_rate = self._get_default_tax_rate(row[ticker_col])

            # Calculate tax amount
            return row[amount_col] * tax_rate

        # Apply calculation to all rows using vectorized operation
        self.df[tax_col] = self.df.apply(calculate_tax, axis=1)

        return self.df

    def replace_tax_with_percentage(self, tax_col: str = "Tax Collected", amount_col: str = "Net Dividend") -> pd.DataFrame:
        """
        Calculate tax percentage based on actual tax amount and net dividend amount.
        First tries to extract percentage from Comment column, then calculates from tax/dividend ratio.
        Replaces absolute tax values with percentages (Tax Collected / Net Dividend).

        Args:
            tax_col (str): The name of the column containing tax amounts.
            amount_col (str): The name of the column containing net dividend amounts.
        """
        def calculate_tax_percentage(row):
            """Calculate tax percentage for a single row."""
            comment = row.get("Comment", "")

            # First, try to extract percentage from Comment column
            tax_percentage = self._extract_tax_rate_from_comment(comment)

            # If no percentage found in comment, calculate from tax amount and dividend
            if tax_percentage is None:
                tax_amount = row[tax_col]
                net_dividend = row[amount_col]

                if pd.notna(tax_amount) and pd.notna(net_dividend) and net_dividend != 0:
                    # Convert to percentage: abs(tax) / dividend
                    tax_percentage = abs(tax_amount) / abs(net_dividend)

            # Return rounded percentage or 0.0 if not calculable
            return round(tax_percentage, 2) if tax_percentage is not None else 0.0

        # Apply calculation to all rows
        self.df[tax_col] = self.df.apply(calculate_tax_percentage, axis=1)

        # Check for 30% US tax and warn user (vectorized check)
        us_tickers_with_30_tax = self.df[
            (self.df["Ticker"].str.contains("US", na=False)) &
            (abs(self.df[tax_col] - 0.30) < 0.01)
        ]

        if not us_tickers_with_30_tax.empty:
            ticker_examples = us_tickers_with_30_tax["Ticker"].head(3).tolist()
            logger.warning(
                f"⚠️  WARNING: 30% tax rate detected for US dividend(s): {', '.join(ticker_examples)}. "
                f"In Poland, you can file a W8BEN form with your broker, "
                f"which reduces the withholding tax from 30% to 15% according to the double taxation treaty."
            )

        logger.info(
            "Step 6 - Updated 'Tax Collected' column with calculated tax percentages."
        )

        return self.df

    def calculate_tax_in_pln(
        self, courses_paths: list[str], date_col: str = "Date"
    ) -> pd.DataFrame:
        """
        Calculate tax amount in PLN based on net dividend, tax percentage, currency, and exchange rate.
        Adds 'Tax Amount PLN' column to the DataFrame.

        Polish tax logic (Belka tax = 19%):
        - If Tax Collected >= 19%: Tax Amount PLN = 0 (tax already paid at source)
        - If Tax Collected < 19%: Tax Amount PLN = Net Dividend * (19% - Tax Collected) * Exchange Rate

        Args:
            courses_paths (list): List of CSV file paths for retrieving exchange rates.
            date_col (str): The name of the column containing dates.

        Returns:
            pd.DataFrame: DataFrame with added 'Tax Amount PLN' column.
        """
        # Add Tax Amount PLN column if it doesn't exist
        if "Tax Amount PLN" not in self.df.columns:
            self.df["Tax Amount PLN"] = 0.0

        # Polish Belka tax rate
        POLISH_TAX_RATE = 0.19  # 19%

        def calculate_tax_pln(row):
            """Calculate tax amount in PLN for a single row."""
            # Get required values
            net_dividend = row.get("Net Dividend", 0)
            tax_percentage = row.get("Tax Collected", 0)
            currency = row.get("Currency", "PLN")
            date = row.get(date_col)

            # Validate data
            if pd.isna(net_dividend) or pd.isna(tax_percentage) or pd.isna(date):
                return 0.0

            # Convert to numeric if needed
            try:
                net_dividend = float(net_dividend)
                tax_percentage = float(tax_percentage)
            except (ValueError, TypeError):
                return 0.0

            # If tax already paid at source is >= 19%, no additional tax in Poland
            if tax_percentage >= POLISH_TAX_RATE:
                return 0.0

            # Get exchange rate for the currency
            if isinstance(date, pd.Timestamp):
                date_str = date.strftime("%Y-%m-%d")
            else:
                date_str = str(date)

            exchange_rate = self._get_exchange_rate(courses_paths, date_str, currency)

            if exchange_rate == 0:
                logger.warning(
                    f"Could not get exchange rate for {currency} on {date_str}. "
                    f"Tax amount in PLN will be 0 for this row."
                )
                return 0.0

            # Calculate tax amount to pay in PLN (difference between Polish rate and already paid)
            # Tax Amount PLN = Net Dividend * (19% - Tax Already Paid) * Exchange Rate
            tax_difference = POLISH_TAX_RATE - tax_percentage
            tax_amount_pln = net_dividend * tax_difference * exchange_rate

            return round(tax_amount_pln, 2)

        # Apply calculation to all rows
        self.df["Tax Amount PLN"] = self.df.apply(calculate_tax_pln, axis=1)

        # Replace 0 with "-" for better readability
        self.df["Tax Amount PLN"] = self.df["Tax Amount PLN"].replace(0.0, "-")

        logger.info(
            "Step 7 - Calculated tax amounts in PLN based on exchange rates and Polish tax rules (19% Belka tax)."
        )

        return self.df

    def add_tax_percentage_display(self) -> pd.DataFrame:
        """
        Creates a display-friendly 'Tax Collected %' column with percentage formatting.
        Keeps the numeric 'Tax Collected' column for calculations.

        The 'Tax Collected %' column will be used for export/display,
        while 'Tax Collected' remains numeric for calculations.

        Returns:
            pd.DataFrame: DataFrame with added 'Tax Collected %' column.
        """
        def format_tax_percentage(value):
            """Format tax percentage for display."""
            if pd.isna(value) or value == 0:
                return "-"
            # Convert decimal to percentage (e.g., 0.15 -> "15%")
            return f"{int(value * 100)}%"

        # Create display column from numeric column
        self.df["Tax Collected %"] = self.df["Tax Collected"].apply(
            format_tax_percentage)

        logger.info(
            "Step 8 - Created 'Tax Collected %' display column with percentage formatting."
        )

        return self.df

    @staticmethod
    def _get_previous_business_day(date_value) -> datetime:
        """
        Calculate the previous business day (D-1) from a given date.
        Skips weekends (Saturday, Sunday) by going backwards to the last weekday.

        Args:
            date_value: A datetime.date, pandas Timestamp, or datetime object.

        Returns:
            datetime.date: The previous business day.
        """
        # Convert to datetime.date if needed
        if isinstance(date_value, pd.Timestamp):
            date_value = date_value.date()
        elif isinstance(date_value, datetime):
            date_value = date_value.date()

        # Start with D-1 (previous day)
        previous_day = date_value - timedelta(days=1)

        # Skip backwards while it's a weekend (Saturday=5, Sunday=6)
        while previous_day.weekday() in [5, 6]:
            previous_day -= timedelta(days=1)

        return previous_day

    def create_date_d_minus_1_column(self) -> pd.DataFrame:
        """
        Creates 'Date D-1' column showing the previous business day from the dividend date.
        If D-1 falls on a weekend, uses the last weekday (typically Friday).

        Returns:
            pd.DataFrame: DataFrame with added 'Date D-1' column.
        """
        self.df["Date D-1"] = self.df["Date"].apply(self._get_previous_business_day)

        logger.info(
            "Step 8a - Created 'Date D-1' column with previous business day dates."
        )

        return self.df

    def create_exchange_rate_d_minus_1_column(self, courses_paths: list[str]) -> pd.DataFrame:
        """
        Creates 'Exchange Rate D-1' column showing the exchange rate for the currency
        from Net Dividend column on the D-1 date.

        Args:
            courses_paths (list[str]): List of paths to exchange rate CSV files.

        Returns:
            pd.DataFrame: DataFrame with added 'Exchange Rate D-1' column.
        """
        def get_exchange_rate_for_row(row):
            """Extract currency from Net Dividend and get exchange rate for D-1 date."""
            net_dividend_str = str(row.get("Net Dividend", ""))
            date_d_minus_1 = row.get("Date D-1")

            # Extract currency from Net Dividend (format: "6.84 USD" or "28.22 PLN")
            parts = net_dividend_str.split()
            if len(parts) != 2:
                return "-"

            currency = parts[1]

            # Convert date to string format for lookup
            if pd.isna(date_d_minus_1):
                return "-"

            # Convert date to YYYY-MM-DD format
            if isinstance(date_d_minus_1, pd.Timestamp):
                date_str = date_d_minus_1.strftime("%Y-%m-%d")
            elif isinstance(date_d_minus_1, datetime):
                date_str = date_d_minus_1.strftime("%Y-%m-%d")
            else:
                date_str = date_d_minus_1.strftime("%Y-%m-%d")

            # Get exchange rate
            rate = self._get_exchange_rate(courses_paths, date_str, currency)

            # Return formatted rate or "-" if not found
            if rate == 0.0:
                return "-"
            elif rate == 1.0 and currency == "PLN":
                return "-"  # No need to show rate for PLN
            else:
                return f"{rate:.4f}"

        # Create Exchange Rate D-1 column
        self.df["Exchange Rate D-1"] = self.df.apply(get_exchange_rate_for_row, axis=1)

        logger.info(
            "Step 8b - Created 'Exchange Rate D-1' column with exchange rates for D-1 dates."
        )

        return self.df

    def add_tax_collected_amount(self) -> pd.DataFrame:
        """
        Creates 'Tax Collected Amount' column showing the actual tax amount collected
        in the same currency as the dividend (not as percentage).
        This is calculated as: Net Dividend (numeric) * Tax Collected (percentage).

        Returns:
            pd.DataFrame: DataFrame with added 'Tax Collected Amount' column.
        """
        def calculate_tax_amount(row):
            """Calculate actual tax amount collected with currency."""
            net_dividend_str = str(row.get("Net Dividend", ""))
            tax_percentage = row.get("Tax Collected", 0)

            # Extract numeric value and currency from Net Dividend
            # Format: "6.84 USD" or "28.22 PLN"
            parts = net_dividend_str.split()
            if len(parts) != 2:
                return "-"

            try:
                dividend_amount = float(parts[0])
                currency = parts[1]
            except (ValueError, IndexError):
                return "-"

            # Check if tax percentage is valid
            if pd.isna(tax_percentage) or tax_percentage == 0:
                return "-"

            # Calculate tax amount
            tax_amount = dividend_amount * tax_percentage

            # Format with currency
            return f"{tax_amount:.2f} {currency}"

        # Create Tax Collected Amount column
        self.df["Tax Collected Amount"] = self.df.apply(calculate_tax_amount, axis=1)

        logger.info(
            "Step 9 - Created 'Tax Collected Amount' column with actual tax amounts in respective currencies."
        )

        return self.df

    def reorder_columns(self) -> pd.DataFrame:
        """
        Reorders the DataFrame columns to the desired sequence:
        Date, Ticker, Shares, Net Dividend, Tax Collected Amount, Tax Collected %, Tax Amount PLN

        Returns:
            pd.DataFrame: DataFrame with reordered columns.
        """
        desired_order = [
            "Date",
            "Ticker",
            "Shares",
            "Net Dividend",
            "Tax Collected Amount",
            "Tax Collected %",
            "Date D-1",
            "Exchange Rate D-1",
            "Tax Amount PLN"
        ]

        # Filter to only include columns that exist in the DataFrame
        existing_columns = [col for col in desired_order if col in self.df.columns]

        # Reorder the DataFrame columns
        self.df = self.df[existing_columns]

        logger.info(
            f"Step 10 - Reordered columns to: {', '.join(existing_columns)}"
        )

        return self.df

    def get_processed_df(self) -> pd.DataFrame:
        """
        Returns the processed DataFrame.

        :return: The processed DataFrame.
        """
        logger.info("Step 11 - Returning the processed DataFrame.")  # Log here
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
