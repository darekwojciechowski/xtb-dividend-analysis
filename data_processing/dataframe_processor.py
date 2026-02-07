from __future__ import annotations

import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from loguru import logger

from visualization.ticker_colors import get_random_color

from .date_converter import DateConverter
from .extractor import MultiConditionExtractor
from .tax_calculator import TaxCalculator
from .tax_calculator import TaxCalculator


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

    def detect_statement_currency(self, currency: str) -> str:
        """
        Detects the currency of the statement from cell F6 in the XTB broker statement.

        The currency in cell F6 defines:
        1. The currency of all amounts in the 'Amount' column
        2. The statement interface language (PLN = Polish, others = English)

        Args:
            currency: Currency code from cell F6 (e.g., 'USD', 'PLN', 'EUR')

        Returns:
            str: Currency code (e.g., 'USD', 'PLN', 'EUR')
        """
        return currency

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
        logger.info("Step 2 - Normalized column names to English standard.")

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

    def extract_tax_percentage_from_comment(self, statement_currency: str = "PLN") -> None:
        """
        Extract tax percentage from Comment column and store in 'Tax Collected' column.
        This should be called BEFORE merge_rows_and_reorder() to preserve tax percentage values.

        For USD statement: preserves the actual tax amount from file in 'Tax Collected Raw' column
        before converting 'Tax Collected' to percentage.

        Each dividend has two rows in Excel:
        1. Row with amount: "SBUX.US USD 0.5700/ SHR"
        2. Row with tax: "SBUX.US USD WHT 15%"

        This method finds the tax percentage for each Date+Ticker group by searching
        all rows in that group.

        Special cases (0% withholding tax at source):
        - ASB.PL: US company listed in Poland, no withholding tax in Excel
        - UK stocks: No withholding tax for non-residents
        - FR stocks: 0% withholding under Poland-France tax treaty

        Args:
            statement_currency (str): Currency of the statement ('USD' or 'PLN')

        Raises:
            ValueError: If tax percentage cannot be extracted from any Comment in the group
                       and default rate is not 0%.
        """
        # For USD statement, save the actual tax amount before converting to percentage
        if statement_currency == "USD" and "Tax Collected" in self.df.columns:
            self.df["Tax Collected Raw"] = self.df["Tax Collected"].copy()

        # Group by Date and Ticker, then extract tax percentage for each group
        grouped = self.df.groupby(["Date", "Ticker"], group_keys=False)

        def find_tax_for_group(group_data):
            """Find tax percentage for a group of rows with same Date and Ticker."""
            # Get ticker and date from the group's name (index)
            ticker = group_data.name[1] if hasattr(
                group_data, 'name') else group_data["Ticker"].iloc[0]
            date = group_data.name[0] if hasattr(
                group_data, 'name') else group_data["Date"].iloc[0]

            group = group_data if isinstance(
                group_data, pd.DataFrame) else self.df.loc[group_data.index]

            # Try to extract tax percentage from each row in the group
            for comment in group["Comment"]:
                tax_percentage = self._extract_tax_rate_from_comment(comment)
                if tax_percentage is not None:
                    # Found a valid tax percentage, apply to all rows in group
                    group.loc[:, "Tax Collected"] = round(tax_percentage, 2)
                    return group

            # If no tax percentage found, use default rate for ticker
            default_rate = self._get_default_tax_rate(ticker)
            group.loc[:, "Tax Collected"] = round(default_rate, 2)

            if default_rate == 0.0:
                logger.info(
                    f"Using 0% tax rate for {ticker} (no withholding tax at source).")
            else:
                logger.warning(
                    f"No WHT information in Comment for {ticker} on {date}. "
                    f"Using default rate {default_rate*100:.0f}% (common for small dividend amounts).")
            return group

        # Apply function to each group without including grouping columns in the operation
        results = []
        for (date, ticker), group in grouped:
            group_copy = group.copy()

            # Try to extract tax percentage from each row in the group
            tax_found = False
            for comment in group_copy["Comment"]:
                tax_percentage = self._extract_tax_rate_from_comment(comment)
                if tax_percentage is not None:
                    # Found a valid tax percentage, apply to all rows in group
                    group_copy["Tax Collected"] = round(tax_percentage, 2)
                    tax_found = True
                    break

            if not tax_found:
                # If no tax percentage found, use default rate for ticker
                default_rate = self._get_default_tax_rate(ticker)
                group_copy["Tax Collected"] = round(default_rate, 2)

                if default_rate == 0.0:
                    logger.info(
                        f"Using 0% tax rate for {ticker} (no withholding tax at source).")
                else:
                    logger.warning(
                        f"No WHT information in Comment for {ticker} on {date}. "
                        f"Using default rate {default_rate*100:.0f}% (common for small dividend amounts)."
                    )

            results.append(group_copy)

        self.df = pd.concat(results, ignore_index=False)
        logger.info(
            "Extracted tax percentages from Comment column for each Date+Ticker group.")

    def merge_rows_and_reorder(
        self, drop_columns: list[str] = ["Type", "Comment"]
    ) -> None:
        """
        Merges rows in the DataFrame with the same 'Date' and 'Ticker',
        removes the specified columns ('Type', 'Comment' by default),
        moves 'Shares' column to the end, and rounds numeric values to 2 decimal places.

        :param drop_columns: A list of columns to drop after merging. Defaults to ['Type', 'Comment'].
        """
        # Build aggregation dictionary dynamically based on available columns
        agg_dict = {
            "Net Dividend": "sum",
            "Shares": "sum",
        }

        # If Tax Collected exists, take first value (they should all be same after extract_tax_percentage_from_comment)
        if "Tax Collected" in self.df.columns:
            agg_dict["Tax Collected"] = "first"

        # If Tax Collected Raw exists (for USD statement), sum the values
        if "Tax Collected Raw" in self.df.columns:
            agg_dict["Tax Collected Raw"] = "sum"

        # Merge rows with the same 'Date' and 'Ticker'
        self.df = self.df.groupby(["Date", "Ticker"], as_index=False).agg(agg_dict)

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
        # Special case: ASB.PL is a US company listed in Poland with 0% withholding at source
        if "ASB.PL" in ticker:
            return 0.0

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
        If the date is not found (e.g., weekend or holiday), searches backwards for the previous business day.

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

        # Try to find exchange rate for target date or previous business days
        max_attempts = 10  # Maximum number of days to search backwards
        current_date = target_date

        for attempt in range(max_attempts):
            current_date_str_formatted = current_date.strftime("%Y%m%d")

            for csv_file in courses_paths:
                try:
                    df = pd.read_csv(csv_file, sep=";", encoding="ISO-8859-1")

                    # Check if the column exists
                    if column_name not in df.columns:
                        continue

                    currency_value = df[df["data"] ==
                                        current_date_str_formatted][column_name].values

                    if len(currency_value) > 0:
                        rate = float(currency_value[0].replace(",", "."))
                        if attempt > 0:
                            logger.info(
                                f"Exchange rate for {currency} not found for {target_date_str}, "
                                f"using rate from {current_date.strftime('%Y-%m-%d')}: {rate}"
                            )
                        return rate
                except FileNotFoundError:
                    logger.warning(f"Exchange rate file '{csv_file}' was not found.")
                except Exception as e:
                    logger.warning(
                        f"An error occurred while processing '{csv_file}': {e}")

            # Move to previous day
            current_date = current_date - timedelta(days=1)

            # Skip weekends (Saturday=5, Sunday=6)
            while current_date.weekday() in [5, 6]:
                current_date = current_date - timedelta(days=1)

        error_msg = (
            f"No exchange rate data found for {currency} on date '{target_date_str}' or previous {max_attempts} business days. "
            f"Check if you have downloaded the file 'archiwum_tab_a_XXXX.csv' for the date '{target_date_str}'."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

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
        self, courses_paths: list[str], statement_currency: str, comment_col: str | None = None, amount_col: str | None = None, date_col: str | None = None
    ) -> pd.DataFrame:
        """
        Modify the Net Dividend column based on the number extracted from the Comment column
        and calculate shares based on the extracted dividend amount and the retrieved exchange rate
        for the specific date in each row.

        Args:
            courses_paths (list): A list of CSV file paths for retrieving exchange rates.
            statement_currency (str): The currency of the statement from cell F6 (e.g., 'PLN', 'USD').
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

            # Use Date D-1 for exchange rate lookup - it must be available
            if "Date D-1" not in self.df.columns:
                raise ValueError(
                    "Column 'Date D-1' is required but not found in DataFrame. "
                    "Please run create_date_d_minus_1_column() before calling this method."
                )

            if pd.isna(row.get("Date D-1")):
                raise ValueError(
                    f"Date D-1 value is missing for row {index}. "
                    f"All rows must have valid 'Date D-1' values."
                )

            target_date = row["Date D-1"]
            if isinstance(target_date, pd.Timestamp):
                target_date_str = target_date.strftime("%Y-%m-%d")
            else:
                target_date_str = target_date.strftime("%Y-%m-%d")

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

                # Apply exchange rate based on statement currency and dividend currency
                exchange_rate = 1.0  # Default exchange rate

                # Only apply exchange rate conversion for Polish statements (PLN) with USD dividends
                if statement_currency == "PLN" and currency == "USD":
                    exchange_rate = self._get_exchange_rate(
                        courses_paths, target_date_str, currency
                    )
                    # No need to check for 0 as exception will be raised if not found

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
        This method is deprecated. Tax percentage extraction is now done by
        extract_tax_percentage_from_comment() before merging.

        This method now just validates that Tax Collected column exists and contains valid values.

        Args:
            tax_col (str): The name of the column containing tax percentages.
            amount_col (str): The name of the column containing net dividend amounts.
        """
        # Validate that Tax Collected column exists and has values
        if tax_col not in self.df.columns:
            raise ValueError(
                f"Column '{tax_col}' not found. "
                f"Please call extract_tax_percentage_from_comment() before merge_rows_and_reorder()."
            )

        # Check for any missing or invalid tax percentages
        invalid_rows = self.df[self.df[tax_col].isna() | (self.df[tax_col] == 0)]
        if not invalid_rows.empty:
            logger.warning(
                f"Found {len(invalid_rows)} rows with missing or zero tax percentages. "
                f"Tickers: {invalid_rows['Ticker'].tolist()}"
            )

        logger.info("Tax Collected column validated.")
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

    def calculate_tax_in_pln_for_detected_usd(
        self, courses_paths: list[str], statement_currency: str
    ) -> pd.DataFrame:
        """Calculate tax amount in PLN for USD statement currency.

        Delegates to TaxCalculator class.

        Args:
            courses_paths (list[str]): Not used, kept for backward compatibility.
            statement_currency (str): The currency of the statement from cell F6.

        Returns:
            pd.DataFrame: DataFrame with added 'Tax Amount PLN' column.
        """
        calculator = TaxCalculator(self.df)
        self.df = calculator.calculate_tax_for_usd_statement(statement_currency)
        return self.df

    def calculate_tax_in_pln_for_detected_pln(
        self, statement_currency: str
    ) -> pd.DataFrame:
        """Calculate tax amount in PLN for PLN statement currency.

        Delegates to TaxCalculator class.

        Args:
            statement_currency (str): The currency of the statement from cell F6.

        Returns:
            pd.DataFrame: DataFrame with added 'Tax Amount PLN' column.
        """
        calculator = TaxCalculator(self.df)
        self.df = calculator.calculate_tax_for_pln_statement(statement_currency)
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
            "Step 7 - Created 'Tax Collected %' display column with percentage formatting."
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

    def create_date_d_minus_1_column(self, step_number: str = "8") -> pd.DataFrame:
        """
        Creates 'Date D-1' column showing the previous business day from the dividend date.
        If D-1 falls on a weekend, uses the last weekday (typically Friday).

        Args:
            step_number (str): The step number to display in logs (default: "8").

        Returns:
            pd.DataFrame: DataFrame with added 'Date D-1' column.
        """
        self.df["Date D-1"] = self.df["Date"].apply(self._get_previous_business_day)

        logger.info(
            f"Step {step_number} - Created 'Date D-1' column with previous business day dates."
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
                return f"{rate:.4f} PLN"

        # Create Exchange Rate D-1 column
        self.df["Exchange Rate D-1"] = self.df.apply(get_exchange_rate_for_row, axis=1)

        logger.info(
            "Step 9 - Created 'Exchange Rate D-1' column with exchange rates for D-1 dates."
        )

        return self.df

    def add_tax_collected_amount(self, statement_currency: str = "PLN") -> pd.DataFrame:
        """
        Creates 'Tax Collected Amount' column showing the actual tax amount collected
        in the same currency as the dividend (not as percentage).

        For USD statement: uses the raw tax amount from file (Tax Collected Raw column)
        For PLN statement: calculates from Net Dividend and tax percentage

        Args:
            statement_currency (str): Currency of the statement ('USD' or 'PLN')

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

            # For USD statement: use raw tax amount from file if available
            if statement_currency == "USD" and "Tax Collected Raw" in self.df.columns:
                tax_raw = row.get("Tax Collected Raw", None)
                if not pd.isna(tax_raw) and tax_raw != 0:
                    # Tax Collected Raw contains negative value, take absolute
                    tax_amount = abs(float(tax_raw))
                    return f"{tax_amount:.2f} {currency}"

            # For PLN statement or if raw amount not available: calculate from percentage
            # Net Dividend = Gross Dividend * (1 - tax_percentage)
            # Therefore: Gross Dividend = Net Dividend / (1 - tax_percentage)
            # Tax Amount = Gross Dividend * tax_percentage
            gross_dividend = dividend_amount / (1 - tax_percentage)
            tax_amount = gross_dividend * tax_percentage

            # Format with currency
            return f"{tax_amount:.2f} {currency}"

        # Create Tax Collected Amount column
        self.df["Tax Collected Amount"] = self.df.apply(calculate_tax_amount, axis=1)

        logger.info(
            "Step 10 - Created 'Tax Collected Amount' column with actual tax amounts in respective currencies."
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
            f"Step 12 - Reordered columns to: {', '.join(existing_columns)}"
        )

        return self.df

    def get_processed_df(self) -> pd.DataFrame:
        """
        Returns the processed DataFrame.

        :return: The processed DataFrame.
        """
        logger.info("Step 13 - Returning the processed DataFrame.")  # Log here
        return self.df

    def log_table_with_tax_summary(self) -> None:
        """
        Log the processed DataFrame as a formatted table with tax summary.
        Removes the numeric 'Tax Collected' column before display and adds
        a summary footer showing total dividends received and total tax due in PLN.

        :return: None
        """
        from tabulate import tabulate
        from data_processing.tax_calculator import TaxCalculator

        # Prepare DataFrame for display (remove numeric Tax Collected column)
        df_display = self.df.copy()
        if "Tax Collected" in df_display.columns:
            df_display = df_display.drop(columns=["Tax Collected"])

        # Calculate total dividends in PLN
        def parse_dividend_to_pln(row):
            """Parse Net Dividend and convert to PLN using Exchange Rate D-1."""
            try:
                # Extract numeric value from "Net Dividend" (e.g., "5.05 USD" -> 5.05)
                net_div_str = str(row["Net Dividend"])
                net_div_value = float(net_div_str.split()[0])

                # Get exchange rate (handle "-" for PLN)
                exchange_rate_str = str(row["Exchange Rate D-1"])
                if exchange_rate_str == "-":
                    exchange_rate = 1.0
                else:
                    exchange_rate = float(exchange_rate_str.split()[0])

                return net_div_value * exchange_rate
            except (ValueError, IndexError, KeyError):
                return 0.0

        total_dividends_pln = df_display.apply(parse_dividend_to_pln, axis=1).sum()

        # Calculate total tax to pay in PLN
        total_tax = TaxCalculator.calculate_total_tax_amount(df_display)

        # Calculate net dividends after tax
        net_after_tax = total_dividends_pln - total_tax

        # Create table with data
        table = tabulate(
            df_display,
            headers="keys",
            tablefmt="pretty",
            showindex=False,
        )

        # Format table with tax summary footer
        table_lines = table.split('\n')
        table_width = len(table_lines[0]) if table_lines else 80

        # Create separator line
        separator = "+" + "-" * (table_width - 2) + "+"

        # Create summary texts
        dividends_text = f"Total dividends received (gross): {total_dividends_pln:.2f} PLN"
        tax_text = f"Total tax due in PLN: {total_tax:.2f} PLN"
        net_text = f"Net dividends after tax: {net_after_tax:.2f} PLN"

        # Center the summary texts
        def center_text(text, width):
            padding = (width - len(text) - 2) // 2
            return "|" + " " * padding + text + " " * (width - len(text) - padding - 2) + "|"

        dividends_line = center_text(dividends_text, table_width)
        tax_line = center_text(tax_text, table_width)
        net_line = center_text(net_text, table_width)

        # Combine table with summary
        table_with_summary = f"{table}\n{separator}\n{dividends_line}\n{separator}\n{tax_line}\n{separator}\n{net_line}\n{separator}"

        # Log processed data with summary
        logger.info("\n" + table_with_summary)

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
