"""Pandera schemas describing the input XTB XLSX and output Google-Sheets CSV.

Single source of truth for the expected structure and types of our data at
each pipeline boundary. Used by contract tests to detect silent drift in
either the broker's export format or our own exporter.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera import Check, Column, DataFrameSchema

# ---------------------------------------------------------------------------
# Input: raw "CASH OPERATION HISTORY" sheet as produced by XTB and loaded by
# ``data_processing.import_data_xlsx.import_and_process_data``.
# ---------------------------------------------------------------------------

# Dividend-related Type values we actively care about. The raw sheet may
# contain many other transaction types (Free-funds Interest, Zakup akcji/ETF,
# ...); the input schema validates structure only and the subset schema
# validates the dividend-only rows the pipeline actually processes.
DIVIDEND_TYPES: frozenset[str] = frozenset(
    {
        "Dividend",
        "Dywidenda",
        "DIVIDENT",
        "Withholding Tax",
        "Podatek od dywidend",
    }
)


# Structural schema: column names, dtypes, strict column set. Catches XTB
# renaming/reordering/dropping/adding columns.
INPUT_XLSX_SCHEMA: DataFrameSchema = DataFrameSchema(
    columns={
        "ID": Column(object, nullable=False),
        "Type": Column(pa.String, nullable=False),
        "Time": Column(pa.DateTime, nullable=True),
        "Comment": Column(pa.String, nullable=True),
        "Symbol": Column(pa.String, nullable=True),
        "Amount": Column(object, nullable=True),
    },
    strict=True,
    coerce=False,
)


# Stricter schema applied after filtering rows to dividend-related types only.
# Every dividend row must have a Symbol and a Comment we can parse.
DIVIDEND_ROWS_SCHEMA: DataFrameSchema = DataFrameSchema(
    columns={
        "Type": Column(
            pa.String,
            checks=Check.isin(sorted(DIVIDEND_TYPES)),
            nullable=False,
        ),
        "Symbol": Column(
            pa.String,
            checks=Check.str_matches(r"^[A-Z0-9.\-]+$"),
            nullable=False,
        ),
        "Comment": Column(pa.String, nullable=False),
    },
    strict=False,
    coerce=False,
)


# ---------------------------------------------------------------------------
# Output: tab-separated CSV produced by ``GoogleSpreadsheetExporter`` and read
# back with ``pd.read_csv(..., sep="\t")``.
# ---------------------------------------------------------------------------

OUTPUT_CSV_SCHEMA: DataFrameSchema = DataFrameSchema(
    columns={
        "Date": Column(pa.String, nullable=False),
        "Ticker": Column(
            pa.String,
            checks=Check.str_matches(r"^[A-Z0-9.\-]+$"),
            nullable=False,
        ),
        "Shares": Column(float, checks=Check.ge(0), nullable=False),
        "Net Dividend": Column(pa.String, nullable=False),
    },
    strict=False,
    coerce=False,
)
