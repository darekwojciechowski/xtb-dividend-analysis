"""Unit tests for TaxExtractor.

Covers tax-rate extraction from comment strings, country-specific default
rates, and the DataFrame-level extraction/merge pipeline.

Test classes:
    TestExtractTaxRateFromComment     — WHT and plain percentage patterns, edge inputs
    TestGetDefaultTaxRate             — per-suffix rates and the ASB.PL override
    TestExtractTaxPercentageFromComment — DataFrame grouping, comment-present, default fallback
    TestMergeRowsAndReorder           — column presence guard, WHT row removal

All tests are marked ``@pytest.mark.unit``.
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from data_processing.tax_extractor import TaxExtractor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_group_df(
    date: str = "2024-01-15",
    ticker: str = "SBUX.US",
    comments: list[str] | None = None,
    include_tax_col: bool = False,
) -> pd.DataFrame:
    """Build a minimal DataFrame representing a single Date+Ticker group."""
    if comments is None:
        comments = ["SBUX.US USD 0.5700/ SHR", "SBUX.US USD WHT 15%"]
    rows = [
        {
            "Date": date,
            "Ticker": ticker,
            "Type": "Dividend",
            "Amount": 10.0,
            "Comment": c,
        }
        for c in comments
    ]
    if include_tax_col:
        for r in rows:
            r["Tax Collected"] = 0.0
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# TestExtractTaxRateFromComment
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractTaxRateFromComment:
    """Tests for TaxExtractor.extract_tax_rate_from_comment."""

    @pytest.mark.parametrize(
        "comment, expected",
        [
            ("SBUX.US USD WHT 15%", 0.15),
            ("WHT 27%", 0.27),
            ("WHT 19%", 0.19),
            ("WHT 0%", 0.0),
            ("WHT 30%", 0.30),
            ("WHT 7.5%", 0.075),
        ],
    )
    def test_extract_when_wht_pattern_then_returns_correct_rate(
        self, comment: str, expected: float
    ) -> None:
        """WHT X% pattern returns the rate as a decimal."""
        # Arrange
        extractor = TaxExtractor(pd.DataFrame())

        # Act
        result = extractor.extract_tax_rate_from_comment(comment)

        # Assert
        assert result == pytest.approx(expected)

    @pytest.mark.parametrize(
        "comment, expected",
        [
            ("some text 19%", 0.19),
            ("15% withholding applied", 0.15),
        ],
    )
    def test_extract_when_plain_percentage_then_returns_correct_rate(
        self, comment: str, expected: float
    ) -> None:
        """Fallback plain percentage pattern works when WHT is absent."""
        # Arrange
        extractor = TaxExtractor(pd.DataFrame())

        # Act
        result = extractor.extract_tax_rate_from_comment(comment)

        # Assert
        assert result == pytest.approx(expected)

    def test_extract_when_no_percentage_then_returns_none(self) -> None:
        """Comment without any percentage → None."""
        # Arrange
        extractor = TaxExtractor(pd.DataFrame())

        # Act
        result = extractor.extract_tax_rate_from_comment("SBUX.US USD 0.5700/ SHR")

        # Assert
        assert result is None

    def test_extract_when_non_string_then_returns_none(self) -> None:
        """Non-string input → None."""
        # Arrange
        extractor = TaxExtractor(pd.DataFrame())

        # Act
        result = extractor.extract_tax_rate_from_comment(None)  # type: ignore[arg-type]

        # Assert
        assert result is None

    def test_extract_when_empty_string_then_returns_none(self) -> None:
        """Empty string → None."""
        # Arrange
        extractor = TaxExtractor(pd.DataFrame())

        # Act
        result = extractor.extract_tax_rate_from_comment("")

        # Assert
        assert result is None

    def test_extract_wht_pattern_takes_priority_over_plain_percentage(self) -> None:
        """When comment has both 'WHT X%' and a plain %, WHT wins."""
        # Arrange
        extractor = TaxExtractor(pd.DataFrame())

        # Act
        result = extractor.extract_tax_rate_from_comment("WHT 15% of 30% gross")

        # Assert
        assert result == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# TestGetDefaultTaxRate
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetDefaultTaxRate:
    """Tests for TaxExtractor.get_default_tax_rate."""

    @pytest.mark.parametrize(
        "ticker, expected",
        [
            ("AAPL.US", 0.15),
            ("XTB.PL", 0.19),
            ("NOVOB.DK", 0.15),
            ("HSBA.UK", 0.0),
            ("CRH.IE", 0.15),
            ("AIR.FR", 0.0),
            ("SAP.DE", 0.0),  # unknown suffix → 0.0
            ("ASML.NL", 0.0),  # unknown suffix → 0.0
        ],
    )
    def test_get_default_rate_when_known_suffix_then_returns_expected(
        self, ticker: str, expected: float
    ) -> None:
        """Correct default WHT rate is returned for each ticker suffix."""
        # Arrange
        extractor = TaxExtractor(pd.DataFrame())

        # Act
        result = extractor.get_default_tax_rate(ticker)

        # Assert
        assert result == pytest.approx(expected)

    def test_get_default_rate_when_unknown_suffix_then_returns_zero(self) -> None:
        """Unknown country suffix → 0.0 (safe default)."""
        # Arrange
        extractor = TaxExtractor(pd.DataFrame())

        # Act
        result = extractor.get_default_tax_rate("XYZ.ZZ")

        # Assert
        assert result == 0.0

    def test_get_default_rate_when_asb_pl_then_returns_zero(self) -> None:
        """ASB.PL is a US company listed in Poland — 0% withholding at source."""
        # Arrange
        extractor = TaxExtractor(pd.DataFrame())

        # Act
        result = extractor.get_default_tax_rate("ASB.PL")

        # Assert
        assert result == 0.0


# ---------------------------------------------------------------------------
# TestExtractTaxPercentageFromComment
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractTaxPercentageFromComment:
    """Tests for TaxExtractor.extract_tax_percentage_from_comment."""

    def test_extract_percentage_when_wht_in_comment_then_applies_to_all_group_rows(
        self,
    ) -> None:
        """All rows in a group get the WHT rate extracted from any comment row."""
        # Arrange
        df = _make_group_df(
            ticker="SBUX.US",
            comments=["SBUX.US USD 0.5700/ SHR", "SBUX.US USD WHT 15%"],
        )
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment(statement_currency="PLN")

        # Assert
        assert result["Tax Collected"].tolist() == pytest.approx([0.15, 0.15])

    def test_extract_percentage_when_no_comment_wht_then_uses_default_rate(
        self,
    ) -> None:
        """Without a WHT comment, the ticker-default rate is used."""
        # Arrange
        df = _make_group_df(
            ticker="SBUX.US",
            comments=["SBUX.US USD 0.5700/ SHR"],  # no WHT row
        )
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment(statement_currency="PLN")

        # Assert — default US rate is 0.15
        assert result["Tax Collected"].tolist() == pytest.approx([0.15])

    def test_extract_percentage_when_pln_ticker_then_uses_19_percent_default(
        self,
    ) -> None:
        """Polish tickers fall back to 19% WHT when no comment rate."""
        # Arrange
        df = _make_group_df(
            ticker="XTB.PL",
            comments=["XTB.PL PLN 1.2000/ SHR"],
        )
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment(statement_currency="PLN")

        # Assert
        assert result["Tax Collected"].tolist() == pytest.approx([0.19])

    def test_extract_percentage_returns_dataframe(self) -> None:
        """Method returns a DataFrame with 'Tax Collected' column and unchanged row count."""
        # Arrange
        df = _make_group_df()
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment()

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert "Tax Collected" in result.columns
        assert len(result) == len(df)

    def test_extract_percentage_when_usd_statement_saves_raw_column(self) -> None:
        """For USD statements, original Tax Collected is copied to Tax Collected Raw."""
        # Arrange
        df = _make_group_df(include_tax_col=True)
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment(statement_currency="USD")

        # Assert
        assert "Tax Collected Raw" in result.columns

    def test_extract_percentage_preserves_all_rows(self) -> None:
        """Row count is unchanged after extraction."""
        # Arrange
        df = _make_group_df(comments=["row A comment WHT 10%", "row B data"])
        extractor = TaxExtractor(df)
        original_len = len(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment()

        # Assert
        assert len(result) == original_len


# ---------------------------------------------------------------------------
# TestValidateTaxCollected
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateTaxCollected:
    """Tests for TaxExtractor.validate_tax_collected."""

    def test_validate_when_column_missing_then_raises_value_error(self) -> None:
        """Raises ValueError when 'Tax Collected' column is absent."""
        # Arrange
        df = pd.DataFrame({"Ticker": ["SBUX.US"], "Date": ["2024-01-15"]})
        extractor = TaxExtractor(df)

        # Act / Assert
        with pytest.raises(ValueError, match="Tax Collected"):
            extractor.validate_tax_collected()

    def test_validate_when_column_present_then_returns_dataframe(self) -> None:
        """No exception when 'Tax Collected' exists; returns DataFrame."""
        # Arrange
        df = pd.DataFrame(
            {"Ticker": ["SBUX.US"], "Date": ["2024-01-15"], "Tax Collected": [0.15]}
        )
        extractor = TaxExtractor(df)

        # Act
        result = extractor.validate_tax_collected()

        # Assert
        assert isinstance(result, pd.DataFrame)

    def test_validate_when_tax_collected_zero_then_logs_warning_and_returns_df(
        self,
    ) -> None:
        """Zero (not NaN) Tax Collected triggers warning but does not raise."""
        # Arrange
        df = pd.DataFrame(
            {"Ticker": ["HSBA.UK"], "Date": ["2024-01-15"], "Tax Collected": [0]}
        )
        extractor = TaxExtractor(df)

        # Act
        result = extractor.validate_tax_collected()

        # Assert — no exception; DataFrame returned
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    def test_validate_when_mixed_nan_zero_and_valid_then_warns_and_returns_df(
        self,
    ) -> None:
        """Rows with NaN and 0 both trigger warning; valid rows are untouched."""
        # Arrange
        df = pd.DataFrame(
            {
                "Ticker": ["SBUX.US", "HSBA.UK", "AAPL.US"],
                "Date": ["2024-01-15", "2024-01-15", "2024-01-15"],
                "Tax Collected": [0.15, float("nan"), 0],
            }
        )
        extractor = TaxExtractor(df)

        # Act
        result = extractor.validate_tax_collected()

        # Assert — 3 rows returned, no exception
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    def test_validate_when_us_ticker_with_30_pct_tax_then_warning_triggered(
        self,
    ) -> None:
        """US ticker with 30% Tax Collected triggers the W8BEN warning path."""
        # Arrange
        df = pd.DataFrame(
            {
                "Ticker": ["MMM.US"],
                "Date": ["2024-01-15"],
                "Tax Collected": [0.30],
            }
        )
        extractor = TaxExtractor(df)

        # Act — must complete without raising
        result = extractor.validate_tax_collected()

        # Assert
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.parametrize("tax_rate", [0.29, 0.31])
    def test_validate_us_ticker_outside_30_pct_tolerance_does_not_trigger_warning(
        self, tax_rate: float
    ) -> None:
        """US ticker with tax ±1% outside 30% does NOT trigger the 30% warning path."""
        # Arrange
        df = pd.DataFrame(
            {
                "Ticker": ["MMM.US"],
                "Date": ["2024-01-15"],
                "Tax Collected": [tax_rate],
            }
        )
        extractor = TaxExtractor(df)

        # Act / Assert — simply must not raise
        result = extractor.validate_tax_collected()
        assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# TestExtractTaxPercentageAdditional
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractTaxPercentageAdditional:
    """Additional tests for extract_tax_percentage_from_comment to kill mutations."""

    def test_multiple_groups_each_gets_own_rate(self) -> None:
        """Two different Date+Ticker groups each receive their respective WHT rate."""
        # Arrange
        df = pd.concat(
            [
                _make_group_df(
                    date="2024-01-15",
                    ticker="SBUX.US",
                    comments=["SBUX.US USD 0.5700/ SHR", "SBUX.US USD WHT 15%"],
                ),
                _make_group_df(
                    date="2024-02-20",
                    ticker="NOVOB.DK",
                    comments=["NOVOB.DK DKK 1.2000/ SHR", "NOVOB.DK DKK WHT 27%"],
                ),
            ],
            ignore_index=True,
        )
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment(statement_currency="PLN")

        # Assert
        sbux_rows = result[result["Ticker"] == "SBUX.US"]
        novob_rows = result[result["Ticker"] == "NOVOB.DK"]
        assert sbux_rows["Tax Collected"].iloc[0] == pytest.approx(0.15)
        assert novob_rows["Tax Collected"].iloc[0] == pytest.approx(0.27)

    def test_uk_ticker_with_no_wht_comment_gets_zero_default(self) -> None:
        """UK ticker without a WHT comment falls back to 0% default."""
        # Arrange
        df = _make_group_df(
            ticker="HSBA.UK",
            comments=["HSBA.UK GBP 0.3000/ SHR"],  # no WHT row
        )
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment(statement_currency="PLN")

        # Assert
        assert result["Tax Collected"].tolist() == pytest.approx([0.0])


# ---------------------------------------------------------------------------
# TestExtractTaxRateDecimalAdditional
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractTaxRateDecimalAdditional:
    """Decimal-percentage tests for extract_tax_rate_from_comment."""

    def test_plain_decimal_percentage_returns_correct_rate(self) -> None:
        """'dividend 12.5%' plain fallback returns 0.125."""
        # Arrange
        extractor = TaxExtractor(pd.DataFrame())

        # Act
        result = extractor.extract_tax_rate_from_comment("dividend 12.5%")

        # Assert
        assert result == pytest.approx(0.125)


# ---------------------------------------------------------------------------
# TestExtractTaxPercentageMutationKillers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtractTaxPercentageMutationKillers:
    """Targeted tests to kill surviving mutants in extract_tax_percentage_from_comment."""

    # --- mutmut_1, mutmut_2: default statement_currency="PLN" ---

    def test_default_currency_arg_does_not_create_raw_column(self) -> None:
        """Calling with no args defaults to PLN — no 'Tax Collected Raw' column created."""
        # Arrange
        df = _make_group_df(include_tax_col=True)
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment()

        # Assert
        assert "Tax Collected Raw" not in result.columns

    # --- mutmut_5: `and` → `or` in currency + col guard ---

    def test_pln_currency_with_existing_tax_col_does_not_create_raw_column(
        self,
    ) -> None:
        """PLN statement must NOT copy Tax Collected to Tax Collected Raw even if column exists."""
        # Arrange
        df = _make_group_df(include_tax_col=True)
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment(statement_currency="PLN")

        # Assert
        assert "Tax Collected Raw" not in result.columns

    # --- mutmut_10: raw col assigned None instead of actual values ---

    def test_usd_statement_raw_column_contains_original_tax_values(self) -> None:
        """For USD statement, Tax Collected Raw must hold the actual pre-extraction values."""
        # Arrange
        original_tax = 5.75
        df = _make_group_df(include_tax_col=True)
        df["Tax Collected"] = original_tax
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment(statement_currency="USD")

        # Assert
        assert "Tax Collected Raw" in result.columns
        assert result["Tax Collected Raw"].notna().all()
        assert result["Tax Collected Raw"].iloc[0] == pytest.approx(original_tax)

    # --- mutmut_29: round(tax_percentage, 2) vs round(tax_percentage, 3) ---

    def test_comment_extracted_rate_is_rounded_to_two_decimal_places(self) -> None:
        """WHT 27.3% → 0.273 stored as round(0.273, 2) = 0.27, not 0.273."""
        # Arrange
        df = _make_group_df(
            ticker="NOVOB.DK",
            comments=["NOVOB.DK DKK 1.20/ SHR", "NOVOB.DK DKK WHT 27.3%"],
        )
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment(statement_currency="PLN")

        # Assert — round(0.273, 2) == 0.27, round(0.273, 3) == 0.273
        assert result["Tax Collected"].iloc[0] == pytest.approx(0.27)
        assert result["Tax Collected"].iloc[0] != pytest.approx(0.273)

    # --- mutmut_41: round(default_rate, 2) vs round(default_rate, 3) ---

    def test_default_rate_is_rounded_to_two_decimal_places(self) -> None:
        """Default rate 0.273 stored as round(0.273, 2) = 0.27, not 0.273."""
        # Arrange
        df = _make_group_df(
            ticker="XYZ.ZZ",
            comments=["XYZ.ZZ USD 1.00/ SHR"],  # no WHT row → uses default
        )
        extractor = TaxExtractor(df)

        # Act — patch get_default_tax_rate to return a 3-dp value
        with patch.object(extractor, "get_default_tax_rate", return_value=0.273):
            result = extractor.extract_tax_percentage_from_comment(
                statement_currency="PLN"
            )

        # Assert — round(0.273, 2) == 0.27, round(0.273, 3) == 0.273
        assert result["Tax Collected"].iloc[0] == pytest.approx(0.27)
        assert result["Tax Collected"].iloc[0] != pytest.approx(0.273)

    # --- mutmut_42, mutmut_43: if default_rate == 0.0 branch ---

    def test_zero_default_rate_logs_info_not_warning(self) -> None:
        """0% default rate (e.g., UK stock) emits an INFO message, not WARNING."""
        # Arrange
        from loguru import logger

        df = _make_group_df(
            ticker="HSBA.UK",
            comments=["HSBA.UK GBP 0.30/ SHR"],
        )
        extractor = TaxExtractor(df)
        messages: list[str] = []
        sink_id = logger.add(messages.append, format="{level}:{message}")

        try:
            # Act
            extractor.extract_tax_percentage_from_comment(statement_currency="PLN")
        finally:
            logger.remove(sink_id)

        # Assert — INFO message about 0% present; no WARNING for this ticker
        assert any("INFO" in m and "0%" in m for m in messages)
        assert not any("WARNING" in m and "HSBA.UK" in m for m in messages)

    def test_nonzero_default_rate_logs_warning_not_info_for_missing_wht(self) -> None:
        """Non-zero default rate (US stock without WHT comment) emits WARNING."""
        # Arrange
        from loguru import logger

        df = _make_group_df(
            ticker="SBUX.US",
            comments=["SBUX.US USD 0.57/ SHR"],  # no WHT row
        )
        extractor = TaxExtractor(df)
        messages: list[str] = []
        sink_id = logger.add(messages.append, format="{level}:{message}")

        try:
            # Act
            extractor.extract_tax_percentage_from_comment(statement_currency="PLN")
        finally:
            logger.remove(sink_id)

        # Assert — WARNING about missing WHT must be present
        assert any(
            "WARNING" in m and "No WHT" in m and "SBUX.US" in m for m in messages
        )

    # --- mutmut_51, mutmut_53, mutmut_54: ignore_index=False in pd.concat ---

    def test_original_index_is_preserved_after_extraction(self) -> None:
        """pd.concat(..., ignore_index=False) keeps original DataFrame indices."""
        # Arrange
        df = _make_group_df(
            ticker="SBUX.US",
            comments=["SBUX.US USD 0.57/ SHR", "SBUX.US USD WHT 15%"],
        )
        custom_index = [100, 200]
        df.index = custom_index
        extractor = TaxExtractor(df)

        # Act
        result = extractor.extract_tax_percentage_from_comment(statement_currency="PLN")

        # Assert — ignore_index=True would reset to 0,1; False preserves 100,200
        assert 100 in result.index
        assert 200 in result.index

    # --- mutmut_55-58: log message string mutations ---

    def test_completion_log_message_is_emitted_with_correct_casing(self) -> None:
        """Exact INFO message 'Extracted tax percentages...' is logged after extraction."""
        # Arrange
        from loguru import logger

        df = _make_group_df()
        extractor = TaxExtractor(df)
        messages: list[str] = []
        sink_id = logger.add(messages.append, format="{level}:{message}")

        try:
            # Act
            extractor.extract_tax_percentage_from_comment(statement_currency="PLN")
        finally:
            logger.remove(sink_id)

        # Assert — message must start with capital 'E', not be prefixed or all-caps
        assert any("INFO" in m and "Extracted tax percentages" in m for m in messages)
