"""PIT-38 declaration figures for foreign dividend income.

XTB sends clients a "Raport Dodatkowy do PIT-38" PDF containing the handful of
numbers that are actually typed into the Polish tax form. This module derives
the same figures from the processed dividend DataFrame:

- **poz. 47** - flat 19% Polish tax on gross foreign dividend income
- **poz. 48** - foreign tax available for deduction, capped so that
  ``poz. 48 <= poz. 47``

Tax authorities hold two conflicting positions on poz. 48 and XTB documents
both, so both are computed:

- **Wariant A (limit UPO)** - ``min(paid, gross x treaty_rate, gross x 19%)``
- **Wariant B (limit 19%)** - ``min(paid, gross x 19%)``

Rows issued by Polish companies are excluded from the declaration entirely:
the withholding agent has already settled them. They still contribute to
``total_gross_all_pln``, which feeds the terminal summary.

Unlike the ``DataFrameProcessor`` specialists, nothing here mutates a
DataFrame - ``build_pit38_summary`` is a fold that returns a value.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

from .constants import (
    DOMESTIC_ISSUER_COUNTRY,
    SUFFIX_TO_ISSUER_COUNTRY,
    TICKER_COUNTRY_OVERRIDES,
    TREATY_DIVIDEND_RATES,
    ColumnName,
    Currency,
)
from .currency_converter import CurrencyConverter
from .tax_calculator import TaxCalculator

# Terminal color codes survive in the 'Colored Ticker' column and can leak into
# any ticker string handed to this module; strip them before matching suffixes.
_ANSI_PATTERN: re.Pattern[str] = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

# Sentinel written by ColumnFormatter for rows that need no FX lookup.
_NO_VALUE = "-"


def _round_2dp(value: float) -> float:
    """Round to two decimals half-up, as Ordynacja podatkowa art. 63 requires.

    Built-in ``round()`` is banker's rounding and would round 0.125 down.

    Args:
        value: Amount to round.

    Returns:
        The amount rounded to two decimal places.
    """
    return float(Decimal(repr(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def round_to_full_zloty(amount: float) -> int:
    """Round an amount to full złoty half-up, as the tax form requires.

    Ordynacja podatkowa art. 63 §1 mandates half-up rounding, so built-in
    ``round()`` must not be used here: it is banker's rounding and would
    turn 42.50 into 42.

    Args:
        amount: Amount in PLN.

    Returns:
        The amount rounded to a whole number of złoty.
    """
    return int(Decimal(repr(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def resolve_issuer_country(ticker: str) -> str | None:
    """Resolve the issuer's tax residence from a ticker symbol.

    Explicit overrides win over the suffix, because the suffix is the listing
    venue and the two can diverge (ASB.PL is Cypriot, listed on the WSE).

    Args:
        ticker: Ticker symbol, optionally wrapped in ANSI color codes.

    Returns:
        Two-letter country code, or ``None`` when the ticker matches no known
        override or suffix.
    """
    if not isinstance(ticker, str):
        return None

    clean = _ANSI_PATTERN.sub("", ticker).strip()

    override = TICKER_COUNTRY_OVERRIDES.get(clean)
    if override is not None:
        return override

    for suffix, country in SUFFIX_TO_ISSUER_COUNTRY.items():
        if clean.endswith(suffix):
            return country

    return None


def _net_dividend(row) -> tuple[float, str]:
    """Parse the gross dividend amount and its currency from a row.

    Despite the column's name, 'Net Dividend' holds the gross dividend.

    Args:
        row: DataFrame row with a 'Net Dividend' column.

    Returns:
        Tuple of ``(amount, currency_code)``.

    Raises:
        ValueError: If the value is missing or malformed.
    """
    # ticker and date feed error-message text only.
    ticker = str(row.get(ColumnName.TICKER.value, "Unknown"))  # pragma: no mutate
    date = str(row.get(ColumnName.DATE.value, "Unknown"))  # pragma: no mutate
    return TaxCalculator._parse_value_with_currency(
        str(row.get(ColumnName.NET_DIVIDEND.value, "")),
        ColumnName.NET_DIVIDEND.value,  # pragma: no mutate
        ticker,  # pragma: no mutate
        date,  # pragma: no mutate
    )


def gross_dividend_pln(
    row, converter: CurrencyConverter, courses_paths: list[str]
) -> tuple[float, float]:
    """Convert a row's gross dividend to PLN using the NBP D-1 rate.

    The displayed 'Exchange Rate D-1' is preferred so that the PIT-38 block
    stays consistent with the table printed directly above it. That column is
    blanked to ``"-"`` for every row whose withholding already meets the Polish
    19%, so foreign rows land there too; those are re-resolved from the NBP
    archive rather than silently treated as PLN.

    Args:
        row: DataFrame row with 'Net Dividend', 'Exchange Rate D-1', 'Date'.
        converter: Converter used for the fallback NBP lookup. Its rate cache
            is shared with the rest of the pipeline.
        courses_paths: NBP CSV paths for the fallback lookup.

    Returns:
        Tuple of ``(gross_amount_pln, exchange_rate)``.

    Raises:
        ValueError: If 'Net Dividend' is missing or malformed.
        ExchangeRateUnavailableError: If a foreign row needs an NBP rate that
            cannot be resolved.
    """
    amount, currency = _net_dividend(row)

    if currency == Currency.PLN.value:
        return amount, 1.0

    # ticker and date feed error-message text only.
    ticker = str(row.get(ColumnName.TICKER.value, "Unknown"))  # pragma: no mutate
    date = str(row.get(ColumnName.DATE.value, "Unknown"))  # pragma: no mutate

    displayed_rate = str(
        row.get(
            ColumnName.EXCHANGE_RATE_D_MINUS_1.value, _NO_VALUE
        )  # pragma: no mutate
    )
    if displayed_rate != _NO_VALUE and displayed_rate != "nan":  # pragma: no mutate
        rate, _ = TaxCalculator._parse_value_with_currency(
            displayed_rate,
            ColumnName.EXCHANGE_RATE_D_MINUS_1.value,  # pragma: no mutate
            ticker,  # pragma: no mutate
            date,  # pragma: no mutate
        )
        return amount * rate, rate

    previous_business_day = CurrencyConverter.get_previous_business_day(
        row[ColumnName.DATE.value]
    )
    rate = converter.get_exchange_rate(
        courses_paths, previous_business_day.strftime("%Y-%m-%d"), currency
    )
    return amount * rate, rate


def withholding_rate(row) -> float:
    """Read the withholding rate from the displayed 'Tax Collected %' column.

    This is the single source for the rate. The numeric 'Tax Collected' column
    is not an alternative: ``DataAggregator.reorder_columns`` drops it one step
    before the summary is rendered, so a fallback tier could only ever fire
    from a unit test.

    'Tax Collected %' is written as ``f"{int(value * 100)}%"``, which
    truncates. Every rate XTB states in its WHT comments is a whole percent, so
    this is lossless today; a fractional rate would understate the deduction,
    which is the safe direction.

    Args:
        row: DataFrame row with a 'Tax Collected %' column.

    Returns:
        Withholding rate as a decimal, or ``0.0`` when absent or ``"-"``.
    """
    raw = row.get(ColumnName.TAX_COLLECTED_PCT.value)

    # Stringifying first collapses every non-percentage case onto one branch:
    # a missing column, NaN and the "-" sentinel all fail the suffix check.
    text = str(raw).strip()
    if not text.endswith("%"):
        return 0.0

    try:
        return float(text[:-1]) / 100
    except ValueError:
        return 0.0


@dataclass(frozen=True)
class Pit38Row:
    """One foreign dividend row's contribution to the declaration.

    All monetary fields are PLN, rounded to two decimals for display. The
    summary totals are accumulated at full precision and rounded once, so they
    do not necessarily equal the sum of these fields.

    Attributes:
        ticker: Ticker symbol with ANSI codes stripped.
        country: Resolved issuer tax residence, or ``None`` when unknown.
        gross_pln: Gross dividend converted to PLN.
        rate: Withholding rate actually applied at source.
        foreign_tax_paid_pln: Withholding tax paid abroad, in PLN.
        tax_19_pct_pln: Polish 19% tax on ``gross_pln``.
        deductible_treaty_pln: poz. 48 under wariant A (treaty-rate cap).
        deductible_full_pln: poz. 48 under wariant B (19% cap).
    """

    ticker: str
    country: str | None
    gross_pln: float
    rate: float
    foreign_tax_paid_pln: float
    tax_19_pct_pln: float
    deductible_treaty_pln: float
    deductible_full_pln: float


@dataclass(frozen=True)
class Pit38Summary:
    """Declaration-level PIT-38 figures for a whole statement.

    Attributes:
        gross_foreign_pln: Total gross foreign dividend income (PLN).
        foreign_tax_paid_pln: Total withholding tax paid abroad (PLN).
        tax_19_pct_pln: poz. 47 - 19% of ``gross_foreign_pln``.
        deductible_treaty_pln: poz. 48 under wariant A.
        deductible_full_pln: poz. 48 under wariant B.
        payable_treaty_pln: Tax still due in Poland under wariant A.
        payable_full_pln: Tax still due in Poland under wariant B.
        total_gross_all_pln: Gross dividends across all rows, Polish included.
        rows: Per-row breakdown of the foreign rows only.
        unknown_country_tickers: Tickers whose issuer country or treaty rate
            could not be resolved; their wariant A cap degrades to 19%.
    """

    gross_foreign_pln: float
    foreign_tax_paid_pln: float
    tax_19_pct_pln: float
    deductible_treaty_pln: float
    deductible_full_pln: float
    payable_treaty_pln: float
    payable_full_pln: float
    total_gross_all_pln: float
    rows: tuple[Pit38Row, ...]
    unknown_country_tickers: tuple[str, ...]


def build_pit38_summary(
    df: pd.DataFrame,
    converter: CurrencyConverter,
    courses_paths: list[str],
    polish_tax_rate: float,
) -> Pit38Summary:
    """Fold a processed dividend DataFrame into PIT-38 declaration figures.

    poz. 47 applies the 19% to the *summed* foreign gross rather than summing
    per-row taxes, so a future per-row cap cannot silently change the basis.
    Everything accumulates at full float precision and is rounded once.

    Args:
        df: Processed DataFrame with 'Ticker', 'Date', 'Net Dividend',
            'Tax Collected %' and 'Exchange Rate D-1' columns.
        converter: Converter used for NBP fallback lookups.
        courses_paths: NBP CSV paths for fallback lookups.
        polish_tax_rate: Polish Belka rate (0.19).

    Returns:
        A populated ``Pit38Summary``.

    Raises:
        ValueError: If a row's 'Net Dividend' is missing or malformed.
        ExchangeRateUnavailableError: If a foreign row's NBP rate is missing.
    """
    rows: list[Pit38Row] = []
    unknown_country: list[str] = []

    total_gross_all = 0.0
    gross_foreign = 0.0
    tax_paid_total = 0.0
    deductible_treaty_total = 0.0
    deductible_full_total = 0.0

    for _, row in df.iterrows():
        gross_pln, _rate = gross_dividend_pln(row, converter, courses_paths)
        total_gross_all += gross_pln

        ticker = _ANSI_PATTERN.sub(
            "", str(row.get(ColumnName.TICKER.value, ""))
        ).strip()
        country = resolve_issuer_country(ticker)

        if country == DOMESTIC_ISSUER_COUNTRY:
            continue

        # One degradation path, two triggers: an unresolved country and a
        # country with no treaty entry both fall back to the 19% cap, which
        # collapses wariant A onto wariant B. Understating the deduction is the
        # safe direction; silently treating a foreign issuer as Polish is not.
        treaty_rate = TREATY_DIVIDEND_RATES.get(country) if country else None
        if treaty_rate is None:
            treaty_rate = polish_tax_rate
            unknown_country.append(ticker)

        rate = withholding_rate(row)
        tax_paid = gross_pln * rate
        tax_19_pct = gross_pln * polish_tax_rate
        # The tax_19_pct term is belt-and-braces: no rate in
        # TREATY_DIVIDEND_RATES currently exceeds 19%, so it never binds today.
        # It keeps poz. 48 <= poz. 47 holding if one ever is added.
        deductible_treaty = min(
            tax_paid,
            gross_pln * treaty_rate,
            tax_19_pct,  # pragma: no mutate
        )
        deductible_full = min(tax_paid, tax_19_pct)

        gross_foreign += gross_pln
        tax_paid_total += tax_paid
        deductible_treaty_total += deductible_treaty
        deductible_full_total += deductible_full

        rows.append(
            Pit38Row(
                ticker=ticker,
                country=country,
                gross_pln=_round_2dp(gross_pln),
                rate=rate,
                foreign_tax_paid_pln=_round_2dp(tax_paid),
                tax_19_pct_pln=_round_2dp(tax_19_pct),
                deductible_treaty_pln=_round_2dp(deductible_treaty),
                deductible_full_pln=_round_2dp(deductible_full),
            )
        )

    tax_19_pct_total = gross_foreign * polish_tax_rate

    return Pit38Summary(
        gross_foreign_pln=_round_2dp(gross_foreign),
        foreign_tax_paid_pln=_round_2dp(tax_paid_total),
        tax_19_pct_pln=_round_2dp(tax_19_pct_total),
        deductible_treaty_pln=_round_2dp(deductible_treaty_total),
        deductible_full_pln=_round_2dp(deductible_full_total),
        payable_treaty_pln=_round_2dp(tax_19_pct_total - deductible_treaty_total),
        payable_full_pln=_round_2dp(tax_19_pct_total - deductible_full_total),
        total_gross_all_pln=_round_2dp(total_gross_all),
        rows=tuple(rows),
        unknown_country_tickers=tuple(dict.fromkeys(unknown_country)),
    )


_TITLE = "RAPORT PODATKOWY PIT-38 - DYWIDENDY ZAGRANICZNE"
# Display labels. Pure presentation text, so mutating them cannot change a
# declaration figure; pragma-marked to keep them out of the mutation budget.
_LABEL_GROSS = "Przychod brutto z dywidend zagranicznych (w PLN)"  # pragma: no mutate
_LABEL_PAID = "Podatek zaplacony za granica (w PLN)"  # pragma: no mutate
_LABEL_POZ_47 = (
    "poz. 47 - Zryczaltowany podatek wg stawki 19% (w PLN)"  # pragma: no mutate
)
_LABEL_VARIANT_A = "Wariant A - limit UPO (stawki traktatowe)"  # pragma: no mutate
_LABEL_VARIANT_B = "Wariant B - limit 19%"  # pragma: no mutate
_LABEL_POZ_48_A = "  poz. 48 - Podatek do odliczenia"  # pragma: no mutate
_LABEL_POZ_48_B = "  poz. 48"  # pragma: no mutate
_LABEL_PAYABLE = "  Do zaplaty w Polsce"  # pragma: no mutate
_DOMESTIC_NOTE = "Pominieto pozycje polskich emitentow - podatek pobrany przez platnika."  # pragma: no mutate
_UNKNOWN_COUNTRY_NOTE = "(!) {ticker}: nieznany kraj emitenta - limit UPO zastapiony limitem 19%."  # pragma: no mutate
_UNAVAILABLE_NOTES = (
    "Brak kursu NBP - nie mozna obliczyc pozycji PIT-38.",  # pragma: no mutate
    "Szczegoly w logu bledow.",  # pragma: no mutate
)

# Marker row: rendered as a horizontal rule rather than a label/value pair.
_RULE = ("", "")


def _pad_row(label: str, value: str, width: int) -> str:
    """Render one boxed line with the label left-aligned and value right-aligned.

    Args:
        label: Left-hand text.
        value: Right-hand text; empty for label-only lines.
        width: Total line width including both border characters.

    Returns:
        A single ``"| ... |"`` line exactly ``width`` characters wide when the
        content fits, and one space wider than the content when it does not.
    """
    padding = max(width - 4 - len(label) - len(value), 1)
    return "| " + label + " " * padding + value + " |"


def _center_row(text: str, width: int) -> str:
    """Render one boxed line with the text centered.

    Padding is clamped at zero so over-long text degrades into a slightly wide
    line rather than a silently mangled one.

    Args:
        text: Text to center.
        width: Total line width including both border characters.

    Returns:
        A single ``"| ... |"`` line.
    """
    # Callers always widen the block past the longest line, so the clamps are
    # defence against a future caller rather than a live branch.
    left = max((width - 2 - len(text)) // 2, 0)  # pragma: no mutate
    right = max(width - 2 - len(text) - left, 0)  # pragma: no mutate
    return "|" + " " * left + text + " " * right + "|"


def _money(amount: float) -> str:
    """Format a PLN amount with two decimals and a full-złoty figure.

    Args:
        amount: Amount in PLN.

    Returns:
        A string such as ``"24.62 PLN  (25 zl)"``.
    """
    return f"{amount:.2f} PLN  ({round_to_full_zloty(amount)} zl)"


def format_pit38_block(summary: Pit38Summary, width: int) -> list[str]:
    """Render the PIT-38 summary as boxed, equal-width ASCII lines.

    ASCII only, so the block renders identically in a Windows console and a
    UTF-8 log file.

    Args:
        summary: Figures to render.
        width: Minimum line width, normally the width of the table above. The
            block widens beyond it when a line would not otherwise fit.

    Returns:
        List of lines, separators included, ready to join with newlines.
    """
    body: list[tuple[str, str]] = [
        (_LABEL_GROSS, f"{summary.gross_foreign_pln:.2f} PLN"),
        (_LABEL_PAID, f"{summary.foreign_tax_paid_pln:.2f} PLN"),
        _RULE,
        (_LABEL_POZ_47, _money(summary.tax_19_pct_pln)),
        _RULE,
        (_LABEL_VARIANT_A, ""),
        (_LABEL_POZ_48_A, _money(summary.deductible_treaty_pln)),
        (_LABEL_PAYABLE, _money(summary.payable_treaty_pln)),
        _RULE,
        (_LABEL_VARIANT_B, ""),
        (_LABEL_POZ_48_B, _money(summary.deductible_full_pln)),
        (_LABEL_PAYABLE, _money(summary.payable_full_pln)),
        _RULE,
        (_DOMESTIC_NOTE, ""),
    ]

    for ticker in summary.unknown_country_tickers:
        body.append((_UNKNOWN_COUNTRY_NOTE.format(ticker=ticker), ""))

    longest = max(
        [len(_TITLE)] + [len(label) + len(value) + 1 for label, value in body if label]
    )
    block_width = max(width, longest + 4)

    separator = "+" + "-" * (block_width - 2) + "+"
    lines = [separator, _center_row(_TITLE, block_width), separator]
    for label, value in body:
        if not label:
            lines.append(separator)
        else:
            lines.append(_pad_row(label, value, block_width))
    lines.append(separator)

    return lines


def format_pit38_unavailable_block(width: int) -> list[str]:
    """Render a degraded block for when NBP rates are missing.

    Args:
        width: Minimum line width, normally the width of the table above.

    Returns:
        List of lines, separators included.
    """
    messages = list(_UNAVAILABLE_NOTES)
    block_width = max(width, max(len(m) for m in [_TITLE] + messages) + 4)
    separator = "+" + "-" * (block_width - 2) + "+"

    return [
        separator,
        _center_row(_TITLE, block_width),
        separator,
        *[_pad_row(message, "", block_width) for message in messages],
        separator,
    ]
