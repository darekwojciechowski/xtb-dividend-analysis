"""Shared Hypothesis strategies + helpers for metamorphic tests."""

from __future__ import annotations

import pandas as pd
from hypothesis import strategies as st


# A ``Net Dividend`` row as it exists right before TaxCalculator runs: the
# amount is stored as a "<value> <currency>" string, and tax columns are
# likewise pre-formatted by earlier pipeline stages.
def _amount_str(value: float, currency: str = "PLN") -> str:
    return f"{value:.2f} {currency}"


@st.composite
def dividend_rows(draw, *, max_rows: int = 8) -> pd.DataFrame:
    """Generate a small DataFrame shaped like the TaxCalculator input (PLN statement).

    Constrains values to realistic ranges so tax math stays numerically stable
    under the metamorphic transformations (scale, split, duplicate, permute).
    """
    n = draw(st.integers(min_value=1, max_value=max_rows))
    tickers = draw(
        st.lists(
            st.sampled_from(["TXT.PL", "KGH.PL", "PKN.PL", "CDR.PL"]),
            min_size=n,
            max_size=n,
        )
    )
    net_dividends = draw(
        st.lists(
            st.floats(
                min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False
            ),
            min_size=n,
            max_size=n,
        )
    )
    # Tax withheld at source — always *below* the Polish Belka rate so every
    # row contributes a non-zero tax to collect locally. Keeps the metamorphic
    # maths clean (no "-" masking).
    tax_pcts = draw(
        st.lists(
            st.floats(
                min_value=0.00, max_value=0.18, allow_nan=False, allow_infinity=False
            ),
            min_size=n,
            max_size=n,
        )
    )

    rows = []
    for ticker, net, pct in zip(tickers, net_dividends, tax_pcts):
        rows.append(
            {
                "Date": "2025-02-21",
                "Ticker": ticker,
                "Net Dividend": _amount_str(net, "PLN"),
                "Tax Collected": pct,
                "Tax Collected Amount": _amount_str(net * pct, "PLN"),
                "Exchange Rate D-1": "-",
            }
        )
    return pd.DataFrame(rows)


@st.composite
def pit38_rows(draw, *, max_rows: int = 8) -> pd.DataFrame:
    """Generate a DataFrame shaped like the ``build_pit38_summary`` input.

    Rows carry foreign (US) tickers so nothing is excluded as domestic, but
    are denominated in PLN so no NBP lookup is needed. Withholding rates are
    whole percents because the pipeline writes ``Tax Collected %`` through
    ``f"{int(value * 100)}%"``, and they straddle the US treaty rate (15%) and
    the Polish rate (19%) so both deduction caps get exercised.
    """
    n = draw(st.integers(min_value=1, max_value=max_rows))
    tickers = draw(
        st.lists(
            st.sampled_from(["SBUX.US", "MMM.US", "AAPL.US", "KO.US"]),
            min_size=n,
            max_size=n,
        )
    )
    gross_amounts = draw(
        st.lists(
            st.floats(
                min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False
            ),
            min_size=n,
            max_size=n,
        )
    )
    tax_pcts = draw(
        st.lists(st.integers(min_value=0, max_value=30), min_size=n, max_size=n)
    )

    return pd.DataFrame(
        [
            {
                "Date": pd.Timestamp("2025-02-21"),
                "Ticker": ticker,
                "Net Dividend": _amount_str(gross, "PLN"),
                "Tax Collected %": f"{pct}%" if pct else "-",
                "Exchange Rate D-1": "-",
            }
            for ticker, gross, pct in zip(tickers, gross_amounts, tax_pcts)
        ]
    )
