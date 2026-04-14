"""Shared fixtures for contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_XLSX = REPO_ROOT / "data" / "demo_XTB_broker_statement_currency_PLN.xlsx"


@pytest.fixture(scope="module")
def demo_xlsx_path() -> Path:
    if not DEMO_XLSX.exists():
        pytest.skip(f"Demo XTB statement not present at {DEMO_XLSX}")
    return DEMO_XLSX
