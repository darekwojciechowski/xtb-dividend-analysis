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
