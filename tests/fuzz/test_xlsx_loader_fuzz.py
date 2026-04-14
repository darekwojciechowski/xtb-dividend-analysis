"""Fuzz the XLSX loader with random bytes.

Goal: no matter what garbage we hand the loader, it must return the well-typed
``(None, None)`` failure tuple OR a valid ``(DataFrame, currency)`` pair. It
must *never* escape with an unhandled exception — the whole point of the try/
except in ``import_and_process_data`` is to be a hard boundary.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from data_processing.import_data_xlsx import import_and_process_data

pytestmark = pytest.mark.fuzz


@given(payload=st.binary(min_size=0, max_size=8192))
def test_loader_never_raises_on_random_bytes(
    tmp_path_factory: pytest.TempPathFactory, payload: bytes
) -> None:
    """Given a file containing arbitrary random bytes (Hypothesis-generated),
    when import_and_process_data processes it,
    then the result is either (None, None) or a (DataFrame, str) pair —
    never an unhandled exception.
    """
    tmp_dir = tmp_path_factory.mktemp("fuzz_xlsx")
    target = tmp_dir / "fuzz.xlsx"
    target.write_bytes(payload)

    df, currency = import_and_process_data(target)

    assert df is None or isinstance(df, pd.DataFrame)
    assert currency is None or isinstance(currency, str)
    if df is None:
        assert currency is None


def test_loader_handles_missing_path(tmp_path: Path) -> None:
    """Given a path that does not exist on disk,
    when import_and_process_data is called,
    then both return values are None.
    """
    df, currency = import_and_process_data(tmp_path / "does-not-exist.xlsx")
    assert df is None
    assert currency is None
