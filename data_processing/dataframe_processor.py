"""XTB Dividend Data Processor - Orchestrator.

This module provides the main DataFrameProcessor class that orchestrates
the complete dividend processing pipeline by delegating to specialized classes.

Refactored to follow SOLID principles with proper separation of concerns.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from .column_formatter import ColumnFormatter
from .column_normalizer import ColumnNormalizer
from .constants import Currency, TickerSuffix, ColumnName
from .currency_converter import CurrencyConverter
from .data_aggregator import DataAggregator
from .dividend_filter import DividendFilter
from .tax_calculator import TaxCalculator
from .tax_extractor import TaxExtractor


class DataFrameProcessor:
    """Orchestrates XTB broker statement data processing for dividend analysis.

    This class coordinates the complete pipeline for processing dividend data from XTB broker
    statements, delegating specific responsibilities to specialized classes.
    Supports both PLN and USD statement currencies with multilingual column names.

    Architecture:
        - Uses specialized classes for different concerns (S in SOLID)
        - Maintains backward compatibility with existing API
        - Delegates to: ColumnNormalizer, DividendFilter, TaxExtractor,
          CurrencyConverter, DataAggregator, ColumnFormatter, TaxCalculator

    Attributes:
        df: pandas DataFrame containing the processed dividend data.
    """

    def __init__(self, df: pd.DataFrame | None = None):
        """Initialize the DataFrameProcessor with a DataFrame.

        Args:
            df: The DataFrame to be processed.

        Raises:
            ValueError: If df is None or invalid.
        """
        if df is None:
            raise ValueError(
                "The DataFrame 'df' cannot be None. Please provide a valid DataFrame."
            )
        self.df = df.copy()
        logger.info("Step 1 - Initialized DataFrameProcessor with a DataFrame.")

    def detect_statement_currency(self, currency: str) -> str:
        """Detect the currency of the statement from cell F6 in the XTB broker statement.

        The currency in cell F6 defines:
        1. The currency of all amounts in the 'Amount' column
        2. The statement interface language (PLN = Polish, others = English)

        Args:
            currency: Currency code from cell F6 (e.g., 'USD', 'PLN', 'EUR')

        Returns:
            Currency code (e.g., 'USD', 'PLN', 'EUR')
        """
        return currency

    def get_column_name(self, english_name: str, polish_name: str) -> str:
        """Get the correct column name based on available columns in the DataFrame.

        Args:
            english_name: The English name of the column.
            polish_name: The Polish name of the column.

        Returns:
            The column name present in the DataFrame.
        """
        normalizer = ColumnNormalizer(self.df)
        return normalizer.get_column_name(english_name, polish_name)

    def drop_columns(self, columns: list[str]) -> None:
        """Drop specified columns from the DataFrame.

        Args:
            columns: A list of column names to be dropped.

        Raises:
            ValueError: If DataFrame is empty or columns are missing.
        """
        normalizer = ColumnNormalizer(self.df)
        self.df = normalizer.drop_columns(columns)

    def rename_columns(self, columns_dict: dict[str, str]) -> None:
        """Rename columns in the DataFrame based on a dictionary mapping.

        Args:
            columns_dict: A dictionary where keys are current column names and values are new column names.

        Raises:
            KeyError: If any source column is missing in the DataFrame.
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
        """Normalize column names to English standard names based on detected language.

        Maps Polish or English column names to standardized English names.
        """
        normalizer = ColumnNormalizer(self.df)
        self.df = normalizer.normalize_column_names()

    def convert_dates(self, date_col: str | None = None) -> None:
        """Convert date strings in the specified column to datetime objects.

        Args:
            date_col: The name of the column containing date strings.
                     If None, tries to find 'Date' or 'Data' column.
        """
        if date_col is None:
            date_col = self.get_column_name("Date", "Data")

        self.df[date_col] = pd.to_datetime(self.df[date_col], errors="coerce")

    def apply_colorize_ticker(self) -> None:
        """Apply random color formatting to the 'Ticker' column.

        Creates a new 'Colored Ticker' column without modifying the original 'Ticker' column.
        """
        formatter = ColumnFormatter(self.df)
        self.df = formatter.apply_colorize_ticker()

    def apply_extractor(self) -> None:
        """Apply the MultiConditionExtractor to the 'Comment' column."""
        formatter = ColumnFormatter(self.df)
        self.df = formatter.apply_extractor()

    def apply_date_converter(self) -> None:
        """Convert date strings in the 'Date' column to datetime objects."""
        formatter = ColumnFormatter(self.df)
        self.df = formatter.apply_date_converter()

    def filter_dividends(self) -> None:
        """Filter the DataFrame to include only dividend-related transactions."""
        dividend_filter = DividendFilter(self.df)
        self.df = dividend_filter.filter_dividends()

    def group_by_dividends(self) -> None:
        """Group the DataFrame by Date, Ticker, and Type, aggregating Amount."""
        dividend_filter = DividendFilter(self.df)
        self.df = dividend_filter.group_by_dividends()

    def add_empty_column(
        self, col_name: str = "Tax Collected", position: int = 4
    ) -> None:
        """Add an empty column to the DataFrame if it does not already exist.

        Args:
            col_name: The name of the column to be added. Defaults to 'Tax Collected'.
            position: The position to insert the column. Defaults to 4.
        """
        aggregator = DataAggregator(self.df)
        self.df = aggregator.add_empty_column(col_name, position)

    def prepare_columns(self) -> None:
        """Ensure that 'Tax Collected' and 'Net Dividend' columns exist in the DataFrame."""
        aggregator = DataAggregator(self.df)
        self.df = aggregator.prepare_columns()

    def convert_columns_to_numeric(self) -> None:
        """Convert 'Net Dividend' and 'Tax Collected' columns to numeric types."""
        aggregator = DataAggregator(self.df)
        self.df = aggregator.convert_columns_to_numeric()

    def move_negative_values(self) -> None:
        """Move negative values from 'Net Dividend' to 'Tax Collected'."""
        aggregator = DataAggregator(self.df)
        self.df = aggregator.move_negative_values()

    def merge_and_sum(self) -> None:
        """Merge rows with the same 'Date' and 'Ticker', summing amounts.

        DEPRECATED: Use merge_rows_and_reorder() instead.
        """
        self.merge_rows_and_reorder()

    def extract_tax_percentage_from_comment(self, statement_currency: str = "PLN") -> None:
        """Extract tax percentage from Comment column and store in 'Tax Collected' column.

        Args:
            statement_currency: Currency of the statement ('USD' or 'PLN')
        """
        tax_extractor = TaxExtractor(self.df)
        self.df = tax_extractor.extract_tax_percentage_from_comment(statement_currency)

    def merge_rows_and_reorder(
        self, drop_columns: list[str] = ["Type", "Comment"]
    ) -> None:
        """Merge rows with the same 'Date' and 'Ticker' and reorder columns.

        Args:
            drop_columns: A list of columns to drop after merging.
        """
        aggregator = DataAggregator(self.df)
        self.df = aggregator.merge_rows_and_reorder(drop_columns)

    # ------------------------------------------------------------------
    # Lazy specialist cache helpers
    # ------------------------------------------------------------------

    def _get_currency_converter(self) -> CurrencyConverter:
        """Return a CurrencyConverter bound to the current DataFrame.

        The instance is reused as long as ``self.df`` has not been replaced
        by a new object, avoiding repeated instantiation inside per-row loops.

        Returns:
            Cached ``CurrencyConverter`` for the current ``self.df``.
        """
        current_df = self.df
        if (
            getattr(self, "_cached_currency_converter", None) is None
            or getattr(self, "_cached_currency_converter_df", None) is not current_df
        ):
            self._cached_currency_converter: CurrencyConverter = CurrencyConverter(
                current_df)
            self._cached_currency_converter_df = current_df
        return self._cached_currency_converter

    def _get_tax_extractor(self) -> TaxExtractor:
        """Return a TaxExtractor bound to the current DataFrame.

        The instance is reused as long as ``self.df`` has not been replaced
        by a new object, avoiding repeated instantiation inside per-row loops.

        Returns:
            Cached ``TaxExtractor`` for the current ``self.df``.
        """
        current_df = self.df
        if (
            getattr(self, "_cached_tax_extractor", None) is None
            or getattr(self, "_cached_tax_extractor_df", None) is not current_df
        ):
            self._cached_tax_extractor: TaxExtractor = TaxExtractor(current_df)
            self._cached_tax_extractor_df = current_df
        return self._cached_tax_extractor

    # ------------------------------------------------------------------
    # Private forwarding delegates (use cached specialists)
    # ------------------------------------------------------------------

    def _extract_dividend_from_comment(self, comment: str) -> tuple[float | None, str | None]:
        """Extract dividend per share and currency from the comment string.

        Args:
            comment: The comment containing dividend details.

        Returns:
            Tuple of (dividend_per_share, currency) or (None, None) if not found.
        """
        return self._get_currency_converter().extract_dividend_from_comment(comment)

    def _determine_currency(self, ticker: str, extracted_currency: str | None) -> str:
        """Determine the currency based on ticker and extracted currency.

        Args:
            ticker: The stock ticker.
            extracted_currency: Currency extracted from comment.

        Returns:
            Determined currency ('USD', 'PLN', 'EUR', 'DKK', 'GBP')
        """
        return self._get_currency_converter().determine_currency(ticker, extracted_currency)

    def _extract_tax_rate_from_comment(self, comment: str) -> float | None:
        """Extract tax rate from comment string (e.g., 'WHT 27%' or '19%').

        Args:
            comment: Comment string potentially containing tax rate.

        Returns:
            Tax rate as decimal (e.g., 0.27 for 27%) or None if not found.
        """
        return self._get_tax_extractor().extract_tax_rate_from_comment(comment)

    def _get_default_tax_rate(self, ticker: str) -> float:
        """Get default withholding tax rate based on ticker suffix.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Default tax rate as decimal.
        """
        return self._get_tax_extractor().get_default_tax_rate(ticker)

    def _get_exchange_rate(self, courses_paths: list[str], target_date_str: str, currency: str) -> float:
        """Retrieve the exchange rate for a specific currency on a specific date.

        Args:
            courses_paths: List of CSV file paths containing exchange rates.
            target_date_str: The date in 'YYYY-MM-DD' format to search for.
            currency: Currency code ('USD', 'EUR', 'DKK', 'GBP', etc.)

        Returns:
            The exchange rate for the specified currency on the specified date.
        """
        return self._get_currency_converter().get_exchange_rate(courses_paths, target_date_str, currency)

    def add_currency_to_dividends(self) -> None:
        """Append currency symbols to the 'Net Dividend' column based on the ticker."""
        converter = CurrencyConverter(self.df)
        self.df = converter.add_currency_to_dividends()

    def calculate_dividend(
        self,
        courses_paths: list[str],
        statement_currency: str,
        comment_col: str | None = None,
        amount_col: str | None = None,
        date_col: str | None = None,
    ) -> pd.DataFrame:
        """Modify the Net Dividend column and calculate shares based on dividend per share.

        Delegates all business logic to ``CurrencyConverter.calculate_dividend``.

        Args:
            courses_paths: A list of CSV file paths for retrieving exchange rates.
            statement_currency: The currency of the statement from cell F6 (e.g., 'PLN', 'USD').
            comment_col: Column containing per-share dividend comments. Resolved from
                the DataFrame language if not provided.
            amount_col: Column to update with total dividend amounts. Defaults to
                ``ColumnName.NET_DIVIDEND``.
            date_col: Unused; kept for backward compatibility.

        Returns:
            Processed DataFrame with calculated shares and dividends.
        """
        comment_col = comment_col or self.get_column_name("Comment", "Komentarz")
        amount_col = amount_col or ColumnName.NET_DIVIDEND.value
        converter = CurrencyConverter(self.df)
        self.df = converter.calculate_dividend(
            courses_paths, statement_currency, comment_col, amount_col
        )
        return self.df

    def replace_tax_values(
        self, ticker_col: str | None = None, amount_col: str | None = None, tax_col: str = ColumnName.TAX_COLLECTED.value
    ) -> pd.DataFrame:
        """Update the 'Tax Collected' column based on the 'Net Dividend' column and ticker type.

        DEPRECATED: Tax extraction is now handled by extract_tax_percentage_from_comment().

        Args:
            ticker_col: The name of the column containing the ticker information.
            amount_col: The name of the column (Net Dividend) to base the calculation on.
            tax_col: The name of the column to update with the tax values.

        Returns:
            DataFrame with tax values updated.
        """
        ticker_col = ticker_col or self.get_column_name("Ticker", "Symbol")
        amount_col = amount_col or ColumnName.NET_DIVIDEND.value

        tax_extractor = TaxExtractor(self.df)

        def calculate_tax(row):
            """Calculate tax for a single row."""
            comment = row.get(ColumnName.COMMENT.value, "")

            # First, try to extract the tax rate from the comment
            tax_rate = tax_extractor.extract_tax_rate_from_comment(comment)

            # If not found in comment, use default rate based on ticker
            if tax_rate is None:
                tax_rate = tax_extractor.get_default_tax_rate(row[ticker_col])

            # Calculate tax amount
            return row[amount_col] * tax_rate

        # Apply calculation to all rows using vectorized operation
        self.df[tax_col] = self.df.apply(calculate_tax, axis=1)

        return self.df

    def replace_tax_with_percentage(self, tax_col: str = "Tax Collected", amount_col: str = "Net Dividend") -> pd.DataFrame:
        """Validate Tax Collected column and warn about high US tax rates.

        Args:
            tax_col: The name of the column containing tax percentages.
            amount_col: The name of the column containing net dividend amounts.

        Returns:
            DataFrame with validated tax data.
        """
        tax_extractor = TaxExtractor(self.df)
        self.df = tax_extractor.validate_tax_collected()
        return self.df

    def calculate_tax_in_pln_for_detected_usd(
        self, courses_paths: list[str], statement_currency: str
    ) -> pd.DataFrame:
        """Calculate tax amount in PLN for USD statement currency.

        Args:
            courses_paths: Not used, kept for backward compatibility.
            statement_currency: The currency of the statement from cell F6.

        Returns:
            DataFrame with added 'Tax Amount PLN' column.
        """
        calculator = TaxCalculator(self.df)
        self.df = calculator.calculate_tax_for_usd_statement(statement_currency)
        return self.df

    def calculate_tax_in_pln_for_detected_pln(
        self, statement_currency: str
    ) -> pd.DataFrame:
        """Calculate tax amount in PLN for PLN statement currency.

        Args:
            statement_currency: The currency of the statement from cell F6.

        Returns:
            DataFrame with added 'Tax Amount PLN' column.
        """
        calculator = TaxCalculator(self.df)
        self.df = calculator.calculate_tax_for_pln_statement(statement_currency)
        return self.df

    def add_tax_percentage_display(self) -> pd.DataFrame:
        """Create a display-friendly 'Tax Collected %' column with percentage formatting.

        Returns:
            DataFrame with added 'Tax Collected %' column.
        """
        formatter = ColumnFormatter(self.df)
        self.df = formatter.add_tax_percentage_display()
        return self.df

    @staticmethod
    def _get_previous_business_day(date_value):
        """Calculate the previous business day (D-1) from a given date.

        Args:
            date_value: A datetime.date, pandas Timestamp, or datetime object.

        Returns:
            The previous business day.
        """
        return CurrencyConverter.get_previous_business_day(date_value)

    def create_date_d_minus_1_column(self, step_number: str = "8") -> pd.DataFrame:
        """Create 'Date D-1' column showing the previous business day from the dividend date.

        Args:
            step_number: The step number to display in logs (default: "8").

        Returns:
            DataFrame with added 'Date D-1' column.
        """
        formatter = ColumnFormatter(self.df)
        self.df = formatter.create_date_d_minus_1_column(step_number)
        return self.df

    def create_exchange_rate_d_minus_1_column(self, courses_paths: list[str]) -> pd.DataFrame:
        """Create 'Exchange Rate D-1' column showing exchange rate for currency on D-1 date.

        Args:
            courses_paths: List of paths to exchange rate CSV files.

        Returns:
            DataFrame with added 'Exchange Rate D-1' column.
        """
        formatter = ColumnFormatter(self.df)
        self.df = formatter.create_exchange_rate_d_minus_1_column(courses_paths)
        return self.df

    def add_tax_collected_amount(self, statement_currency: str = "PLN") -> pd.DataFrame:
        """Create 'Tax Collected Amount' column showing actual tax amount collected.

        Args:
            statement_currency: Currency of the statement ('USD' or 'PLN')

        Returns:
            DataFrame with added 'Tax Collected Amount' column.
        """
        formatter = ColumnFormatter(self.df)
        self.df = formatter.add_tax_collected_amount(statement_currency)
        return self.df

    def reorder_columns(self) -> pd.DataFrame:
        """Reorder the DataFrame columns to the desired sequence.

        Returns:
            DataFrame with reordered columns.
        """
        aggregator = DataAggregator(self.df)
        self.df = aggregator.reorder_columns()
        return self.df

    def get_processed_df(self) -> pd.DataFrame:
        """Return the processed DataFrame with all transformations applied.

        Returns:
            The fully processed DataFrame ready for export or analysis.
        """
        logger.info("Step 13 - Returning the processed DataFrame.")
        return self.df

    @staticmethod
    def parse_dividend_to_pln(row) -> float:
        """Parse Net Dividend and convert to PLN using Exchange Rate D-1.

        Args:
            row: DataFrame row containing 'Net Dividend' and 'Exchange Rate D-1' columns.

        Returns:
            Dividend amount converted to PLN.
        """
        try:
            # Extract numeric value from "Net Dividend" (e.g., "5.05 USD" -> 5.05)
            net_div_str = str(row[ColumnName.NET_DIVIDEND.value])
            net_div_value = float(net_div_str.split()[0])

            # Get exchange rate (handle "-" for PLN)
            exchange_rate_str = str(row[ColumnName.EXCHANGE_RATE_D_MINUS_1.value])
            if exchange_rate_str == "-":
                exchange_rate = 1.0
            else:
                exchange_rate = float(exchange_rate_str.split()[0])

            return net_div_value * exchange_rate
        except (ValueError, IndexError, KeyError):
            return 0.0

    def log_table_with_tax_summary(self, statement_currency: str = "PLN") -> None:
        """Log the processed DataFrame as a formatted table with comprehensive tax summary.

        Args:
            statement_currency: Currency of the statement ('USD' or 'PLN').
        """
        from tabulate import tabulate

        # Prepare DataFrame for display (remove numeric Tax Collected column)
        df_display = self.df.copy()
        if ColumnName.TAX_COLLECTED.value in df_display.columns:
            df_display = df_display.drop(columns=[ColumnName.TAX_COLLECTED.value])

        # Calculate total dividends in PLN
        total_dividends_pln = df_display.apply(self.parse_dividend_to_pln, axis=1).sum()

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
        """Process the DataFrame by applying a standard sequence of transformations.

        Returns:
            The processed DataFrame.
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
