"""Unit tests for the PIT-38 declaration report module.

Test Coverage:
    - Issuer country resolution (overrides, suffixes, ANSI, unknown)
    - Gross dividend conversion to PLN, including the NBP fallback lookup
    - Withholding rate parsing from the displayed 'Tax Collected %' column
    - Half-up rounding to full złoty
    - Declaration-level folding, both variants and the exclusions
    - Block rendering (equal widths, ASCII only)
"""

from __future__ import annotations

import pandas as pd
import pytest

from data_processing.currency_converter import (
    CurrencyConverter,
    ExchangeRateUnavailableError,
)
from data_processing.pit38_report import (
    Pit38Summary,
    build_pit38_summary,
    format_pit38_block,
    format_pit38_unavailable_block,
    gross_dividend_pln,
    resolve_issuer_country,
    round_to_full_zloty,
    withholding_rate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_POLISH_TAX_RATE = 0.19


def _make_row(
    ticker: str,
    net_dividend: str,
    tax_pct: str = "-",
    exchange_rate: str = "-",
    date: str = "2025-05-29",
) -> dict[str, object]:
    """Build one processed-pipeline row as a plain dict.

    Args:
        ticker: Ticker symbol.
        net_dividend: Formatted gross amount, e.g. ``"6.84 USD"``.
        tax_pct: Displayed withholding percentage, e.g. ``"15%"`` or ``"-"``.
        exchange_rate: Displayed D-1 rate, e.g. ``"4.1512 PLN"`` or ``"-"``.
        date: Dividend payment date.

    Returns:
        Dict with the columns ``pit38_report`` reads.
    """
    return {
        "Date": pd.Timestamp(date),
        "Ticker": ticker,
        "Net Dividend": net_dividend,
        "Tax Collected %": tax_pct,
        "Exchange Rate D-1": exchange_rate,
    }


def _summary(rows: list[dict[str, object]], courses: list[str] | None = None):
    """Fold rows into a Pit38Summary with an empty-DataFrame converter.

    Args:
        rows: Row dicts built by ``_make_row``.
        courses: NBP CSV paths for fallback lookups.

    Returns:
        The resulting ``Pit38Summary``.
    """
    df = pd.DataFrame(rows)
    return build_pit38_summary(
        df, CurrencyConverter(df), list(courses or []), _POLISH_TAX_RATE
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveIssuerCountry:
    """Tests for resolve_issuer_country."""

    def test_resolve_when_us_suffix_then_returns_us(self) -> None:
        assert resolve_issuer_country("SBUX.US") == "US"

    def test_resolve_when_pl_suffix_then_returns_pl(self) -> None:
        assert resolve_issuer_country("XTB.PL") == "PL"

    def test_resolve_when_dk_suffix_then_returns_dk(self) -> None:
        assert resolve_issuer_country("NOVOB.DK") == "DK"

    def test_resolve_when_override_ticker_then_beats_suffix(self) -> None:
        """ASBIS lists on the WSE but is tax-resident in Cyprus."""
        assert resolve_issuer_country("ASB.PL") == "CY"

    def test_resolve_when_ansi_wrapped_then_strips_color_codes(self) -> None:
        colored = "\x1b[38;5;208mSBUX.US\x1b[0m"

        assert resolve_issuer_country(colored) == "US"

    def test_resolve_when_ansi_wrapped_override_then_beats_suffix(self) -> None:
        colored = "\x1b[31mASB.PL\x1b[0m"

        assert resolve_issuer_country(colored) == "CY"

    def test_resolve_when_ticker_merely_contains_an_override_then_no_match(
        self,
    ) -> None:
        """An override applies to its exact ticker, not anything containing it.

        Substring matching resolved "ASB.PLUS" to Cyprus, silently moving a
        real position onto ASBIS's 5% treaty cap.
        """
        assert resolve_issuer_country("ASB.PLUS") is None

    def test_resolve_when_unknown_suffix_then_returns_none(self) -> None:
        assert resolve_issuer_country("FOO.ZZ") is None

    def test_resolve_when_no_suffix_then_returns_none(self) -> None:
        assert resolve_issuer_country("AAPL") is None

    def test_resolve_when_not_a_string_then_returns_none(self) -> None:
        assert resolve_issuer_country(None) is None  # type: ignore[arg-type]


@pytest.mark.unit
class TestGrossDividendPln:
    """Tests for gross_dividend_pln."""

    def test_gross_when_pln_row_then_rate_is_one(self) -> None:
        """A PLN row needs no conversion regardless of the displayed rate."""
        row = pd.Series(_make_row("XTB.PL", "92.65 PLN", "19%", "-"))

        amount, rate = gross_dividend_pln(row, CurrencyConverter(pd.DataFrame()), [])

        assert amount == pytest.approx(92.65)
        assert rate == pytest.approx(1.0)

    def test_gross_when_displayed_rate_present_then_multiplies_by_it(self) -> None:
        row = pd.Series(_make_row("SBUX.US", "5.0 USD", "15%", "4.0 PLN"))

        amount, rate = gross_dividend_pln(row, CurrencyConverter(pd.DataFrame()), [])

        assert amount == pytest.approx(20.0)
        assert rate == pytest.approx(4.0)

    def test_gross_when_rate_blank_then_looks_up_previous_business_day(
        self, tmp_path
    ) -> None:
        """A blanked rate must trigger an NBP lookup, not a silent 1:1 fallback.

        ColumnFormatter blanks 'Exchange Rate D-1' for every row whose
        withholding already meets 19%, which includes foreign rows.
        """
        # Arrange — 2025-02-24 is a Monday, so D-1 is Friday 2025-02-21.
        csv = tmp_path / "rates.csv"
        csv.write_text("data;1USD\n20250221;3,9974\n", encoding="ISO-8859-1")
        row = pd.Series(_make_row("MMM.US", "1.4 USD", "30%", "-", date="2025-02-24"))

        # Act
        amount, rate = gross_dividend_pln(
            row, CurrencyConverter(pd.DataFrame()), [str(csv)]
        )

        # Assert
        assert rate == pytest.approx(3.9974)
        assert amount == pytest.approx(1.4 * 3.9974)

    def test_gross_when_rate_unavailable_then_raises(self) -> None:
        """Missing NBP data must fail loudly rather than degrade to 1:1."""
        row = pd.Series(_make_row("MMM.US", "1.4 USD", "30%", "-"))

        with pytest.raises(ExchangeRateUnavailableError):
            gross_dividend_pln(row, CurrencyConverter(pd.DataFrame()), [])

    def test_gross_when_net_dividend_malformed_then_raises(self) -> None:
        """The replaced helper swallowed this into 0.0; it now propagates."""
        row = pd.Series(_make_row("SBUX.US", "N/A", "15%", "4.0 PLN"))

        with pytest.raises(ValueError, match="Net Dividend"):
            gross_dividend_pln(row, CurrencyConverter(pd.DataFrame()), [])


@pytest.mark.unit
class TestWithholdingRate:
    """Tests for withholding_rate."""

    def test_rate_when_percentage_string_then_returns_decimal(self) -> None:
        assert withholding_rate(pd.Series({"Tax Collected %": "27%"})) == pytest.approx(
            0.27
        )

    def test_rate_when_dash_then_returns_zero(self) -> None:
        assert withholding_rate(pd.Series({"Tax Collected %": "-"})) == 0.0

    def test_rate_when_column_missing_then_returns_zero(self) -> None:
        assert withholding_rate(pd.Series({"Ticker": "AAPL.US"})) == 0.0

    def test_rate_when_nan_then_returns_zero(self) -> None:
        assert withholding_rate(pd.Series({"Tax Collected %": float("nan")})) == 0.0

    def test_rate_when_not_a_percentage_then_returns_zero(self) -> None:
        assert withholding_rate(pd.Series({"Tax Collected %": "abc"})) == 0.0

    def test_rate_when_percent_sign_without_number_then_returns_zero(self) -> None:
        """Trailing '%' is not enough: the prefix must parse as a number."""
        assert withholding_rate(pd.Series({"Tax Collected %": "abc%"})) == 0.0


@pytest.mark.unit
class TestRoundToFullZloty:
    """Tests for round_to_full_zloty."""

    def test_round_when_half_above_even_then_rounds_up(self) -> None:
        assert round_to_full_zloty(42.50) == 43

    def test_round_when_half_below_even_then_still_rounds_up(self) -> None:
        """Paired with the case above: banker's rounding would give 42 for both."""
        assert round_to_full_zloty(41.50) == 42

    def test_round_when_below_half_then_rounds_down(self) -> None:
        assert round_to_full_zloty(24.62) == 25
        assert round_to_full_zloty(18.69) == 19
        assert round_to_full_zloty(5.11) == 5

    def test_round_when_zero_then_returns_zero(self) -> None:
        assert round_to_full_zloty(0.0) == 0


@pytest.mark.unit
class TestBuildPit38Summary:
    """Tests for build_pit38_summary."""

    def test_summary_when_treaty_rate_below_paid_then_variants_diverge(self) -> None:
        """MMM.US: 30% withheld without a W-8BEN, US treaty caps at 15%.

        Wariant A caps at the treaty rate, wariant B at the Polish 19%, so the
        two deductions differ for this row.
        """
        summary = _summary([_make_row("MMM.US", "1.4 USD", "30%", "3.9974 PLN")])

        # gross 5.5964; paid 1.6789; 19% cap 1.0633; treaty cap 0.8395
        assert summary.gross_foreign_pln == pytest.approx(5.60)
        assert summary.deductible_treaty_pln == pytest.approx(0.84)
        assert summary.deductible_full_pln == pytest.approx(1.06)

    def test_summary_when_paid_below_both_caps_then_variants_agree(self) -> None:
        """SBUX.US is withheld at exactly the US treaty rate, so no cap bites."""
        summary = _summary([_make_row("SBUX.US", "1.71 USD", "15%", "4.1512 PLN")])

        assert summary.deductible_treaty_pln == pytest.approx(1.06)
        assert summary.deductible_full_pln == pytest.approx(1.06)

    def test_summary_when_zero_withholding_then_no_deduction(self) -> None:
        """ASB.PL is Cypriot with nothing withheld: the full 19% is owed here."""
        summary = _summary([_make_row("ASB.PL", "25.5 USD", "-", "3.7456 PLN")])

        assert summary.rows[0].country == "CY"
        assert summary.foreign_tax_paid_pln == pytest.approx(0.0)
        assert summary.deductible_treaty_pln == pytest.approx(0.0)
        assert summary.tax_19_pct_pln == pytest.approx(18.15)
        assert summary.payable_full_pln == pytest.approx(18.15)

    def test_summary_when_polish_issuer_then_excluded_from_foreign_gross(self) -> None:
        """Polish rows are settled by the payer, so they never reach poz. 47."""
        summary = _summary(
            [
                _make_row("XTB.PL", "92.65 PLN", "19%", "-"),
                _make_row("SBUX.US", "1.71 USD", "15%", "4.1512 PLN"),
            ]
        )

        assert [r.ticker for r in summary.rows] == ["SBUX.US"]
        assert summary.gross_foreign_pln == pytest.approx(7.10)
        assert summary.total_gross_all_pln == pytest.approx(99.75)

    def test_summary_when_unknown_country_then_degrades_to_19_pct_cap(self) -> None:
        """Misclassifying a foreign issuer as Polish would drop a real liability."""
        summary = _summary([_make_row("FOO.ZZ", "100.0 PLN", "30%", "-")])

        assert summary.unknown_country_tickers == ("FOO.ZZ",)
        assert summary.rows[0].country is None
        # Wariant A collapses onto wariant B: both capped at 19%.
        assert summary.deductible_treaty_pln == pytest.approx(19.0)
        assert summary.deductible_full_pln == pytest.approx(19.0)

    def test_summary_when_multiple_rows_then_accumulates_tax_paid(self) -> None:
        """Foreign tax paid must accumulate across rows, not overwrite."""
        summary = _summary(
            [
                _make_row("SBUX.US", "100.0 PLN", "15%", "-"),
                _make_row("KO.US", "200.0 PLN", "15%", "-"),
            ]
        )

        assert summary.foreign_tax_paid_pln == pytest.approx(45.0)
        assert summary.gross_foreign_pln == pytest.approx(300.0)

    def test_summary_when_row_built_then_carries_full_breakdown(self) -> None:
        """Every Pit38Row field is populated, not left unset."""
        summary = _summary([_make_row("MMM.US", "100.0 PLN", "30%", "-")])

        row = summary.rows[0]

        assert row.ticker == "MMM.US"
        assert row.country == "US"
        assert row.gross_pln == pytest.approx(100.0)
        assert row.rate == pytest.approx(0.30)
        assert row.foreign_tax_paid_pln == pytest.approx(30.0)
        assert row.tax_19_pct_pln == pytest.approx(19.0)
        assert row.deductible_treaty_pln == pytest.approx(15.0)
        assert row.deductible_full_pln == pytest.approx(19.0)

    def test_summary_when_ticker_is_colorized_then_reports_it_stripped(self) -> None:
        """Colored tickers must not leak escape codes into the report."""
        summary = _summary(
            [_make_row("\x1b[31mFOO.ZZ\x1b[0m", "100.0 PLN", "30%", "-")]
        )

        assert summary.rows[0].ticker == "FOO.ZZ"
        assert summary.unknown_country_tickers == ("FOO.ZZ",)

    def test_summary_when_multiple_rows_then_payable_is_47_minus_48(self) -> None:
        summary = _summary(
            [
                _make_row("SBUX.US", "1.71 USD", "15%", "4.1512 PLN"),
                _make_row("MMM.US", "1.4 USD", "30%", "3.9974 PLN"),
            ]
        )

        assert summary.payable_treaty_pln == pytest.approx(
            summary.tax_19_pct_pln - summary.deductible_treaty_pln, abs=0.01
        )
        assert summary.payable_full_pln == pytest.approx(
            summary.tax_19_pct_pln - summary.deductible_full_pln, abs=0.01
        )

    def test_summary_when_empty_dataframe_then_all_totals_zero(self) -> None:
        """Every accumulator must start at zero, not carry a seeded value."""
        df = pd.DataFrame(
            columns=[
                "Date",
                "Ticker",
                "Net Dividend",
                "Tax Collected %",
                "Exchange Rate D-1",
            ]
        )

        summary = build_pit38_summary(df, CurrencyConverter(df), [], _POLISH_TAX_RATE)

        assert summary.gross_foreign_pln == 0.0
        assert summary.foreign_tax_paid_pln == 0.0
        assert summary.tax_19_pct_pln == 0.0
        assert summary.deductible_treaty_pln == 0.0
        assert summary.deductible_full_pln == 0.0
        assert summary.payable_treaty_pln == 0.0
        assert summary.payable_full_pln == 0.0
        assert summary.total_gross_all_pln == 0.0
        assert summary.rows == ()
        assert summary.unknown_country_tickers == ()

    def test_summary_when_total_ties_at_half_grosz_then_rounds_up(self) -> None:
        """Totals round half-up, not banker's: 12.345 must become 12.35.

        Ordynacja podatkowa art. 63 mandates half-up, so the module must not
        fall back to the decimal context default, which is half-even.
        """
        summary = _summary([_make_row("AAA.US", "12.345 PLN", "-", "-")])

        assert summary.gross_foreign_pln == 12.35

    def test_summary_when_19_pct_applied_then_uses_summed_gross_not_per_row(
        self,
    ) -> None:
        """poz. 47 is 19% of the summed gross, not the sum of per-row taxes.

        Two 0.50 PLN rows make the two formulations disagree: rounding each
        row's tax first gives 0.10 + 0.10 = 0.20, taxing the sum gives 0.19.
        """
        summary = _summary(
            [
                _make_row("AAA.US", "0.50 USD", "-", "1.0 PLN"),
                _make_row("BBB.US", "0.50 USD", "-", "1.0 PLN"),
            ]
        )

        assert summary.tax_19_pct_pln == pytest.approx(0.19)


@pytest.mark.unit
class TestFormatPit38Block:
    """Tests for format_pit38_block."""

    @staticmethod
    def _block(summary: Pit38Summary, width: int = 80) -> list[str]:
        return format_pit38_block(summary, width)

    def test_block_when_rendered_then_all_lines_equal_width(self) -> None:
        summary = _summary([_make_row("MMM.US", "1.4 USD", "30%", "3.9974 PLN")])

        lines = self._block(summary, width=120)

        assert len({len(line) for line in lines}) == 1, (
            f"Ragged block: {sorted({len(line) for line in lines})}"
        )

    def test_block_when_content_exceeds_width_then_widens_instead_of_overflowing(
        self,
    ) -> None:
        summary = _summary([_make_row("MMM.US", "1.4 USD", "30%", "3.9974 PLN")])

        lines = self._block(summary, width=20)

        assert len({len(line) for line in lines}) == 1
        assert len(lines[0]) > 20

    def test_block_when_auto_widened_then_fits_longest_line_exactly(self) -> None:
        """The block widens to exactly fit its content, with no slack column.

        Guards the ``longest + 4`` width arithmetic: a wider or narrower
        constant still yields equal-width lines, so only the tightness of the
        fit distinguishes them. Longest content here is the poz. 47 label (53
        chars) plus one separating space plus "19.00 PLN  (19 zl)" (18 chars),
        and the "| " / " |" borders add 4 more.
        """
        summary = _summary([_make_row("MMM.US", "100.0 PLN", "30%", "-")])

        lines = self._block(summary, width=1)

        assert len(lines[0]) == 53 + 1 + 18 + 4

    def test_block_when_label_only_row_then_no_stray_value_is_rendered(self) -> None:
        """Section headers and footnotes carry a label and nothing else."""
        summary = _summary([_make_row("SBUX.US", "1.71 USD", "15%", "4.1512 PLN")])

        lines = self._block(summary, width=140)
        label_only = [
            line
            for line in lines
            if "Wariant A - limit UPO (stawki traktatowe)" in line
        ]

        assert len(label_only) == 1
        assert label_only[0].rstrip("| ").strip().endswith("(stawki traktatowe)")

    def test_block_when_rendered_then_title_is_centered(self) -> None:
        """Equal line widths alone do not prove the title sits in the middle."""
        summary = _summary([_make_row("MMM.US", "1.4 USD", "30%", "3.9974 PLN")])

        title_line = self._block(summary, width=140)[1]
        interior = title_line[1:-1]
        left_padding = len(interior) - len(interior.lstrip())
        right_padding = len(interior) - len(interior.rstrip())

        assert abs(left_padding - right_padding) <= 1, (
            f"Title off-center by {left_padding - right_padding} characters"
        )

    def test_block_when_rendered_then_contains_no_ansi_codes(self) -> None:
        summary = _summary([_make_row("MMM.US", "1.4 USD", "30%", "3.9974 PLN")])

        lines = self._block(summary)

        assert not any("\x1b[" in line for line in lines)

    def test_block_when_rendered_then_is_ascii_only(self) -> None:
        """ASCII keeps the box aligned in a Windows console."""
        summary = _summary([_make_row("MMM.US", "1.4 USD", "30%", "3.9974 PLN")])

        lines = self._block(summary)

        assert all(line.isascii() for line in lines)

    def test_block_when_rendered_then_shows_both_variants_and_full_zloty(self) -> None:
        summary = _summary([_make_row("ASB.PL", "25.5 USD", "-", "3.7456 PLN")])

        text = "\n".join(self._block(summary, width=140))

        assert "Wariant A - limit UPO (stawki traktatowe)" in text
        assert "Wariant B - limit 19%" in text
        assert "18.15 PLN  (18 zl)" in text

    def test_block_when_unknown_country_then_renders_footnote(self) -> None:
        """The degradation must be visible in the output the user reads."""
        summary = _summary([_make_row("FOO.ZZ", "100.0 PLN", "30%", "-")])

        text = "\n".join(self._block(summary, width=140))

        assert "(!) FOO.ZZ: nieznany kraj emitenta" in text


@pytest.mark.unit
class TestFormatPit38UnavailableBlock:
    """Tests for the degraded block rendered when NBP data is missing."""

    def test_unavailable_block_when_rendered_then_all_lines_equal_width(self) -> None:
        lines = format_pit38_unavailable_block(120)

        assert len({len(line) for line in lines}) == 1

    def test_unavailable_block_when_rendered_then_states_the_cause(self) -> None:
        text = "\n".join(format_pit38_unavailable_block(80))

        assert "Brak kursu NBP" in text

    def test_unavailable_block_when_auto_widened_then_fits_title_exactly(self) -> None:
        """Width is driven by the longest line plus the borders and padding.

        Here that is the 51-character "Brak kursu NBP ..." message rather than
        the 47-character title.
        """
        lines = format_pit38_unavailable_block(1)

        assert len(lines[0]) == 51 + 4

    def test_unavailable_block_when_rendered_then_message_lines_carry_no_value(
        self,
    ) -> None:
        """The degraded block has no right-hand column to fill."""
        lines = format_pit38_unavailable_block(80)
        message_lines = [line for line in lines if "Brak kursu NBP" in line]

        assert len(message_lines) == 1
        assert message_lines[0].rstrip("| ").endswith("pozycji PIT-38.")
