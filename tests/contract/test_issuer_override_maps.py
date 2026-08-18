"""Contract between the two per-ticker override tables.

``TICKER_COUNTRY_OVERRIDES`` and ``TICKER_WITHHOLDING_OVERRIDES`` describe the
same fact from two angles: a ticker whose issuer is tax-resident somewhere other
than its listing venue is exactly a ticker whose withholding is not its venue's
default. They are separate dicts only because routing ``tax_extractor`` through
``pit38_report`` would make a tax-extraction module depend on a reporting one.

The proper fix is a shared ``issuer_policy`` module owning both tables. Until
that exists, this test makes the duplication detectable rather than absent: add
a ticker to one map and forget the other, and it fails here instead of silently
taping a Cypriot issuer's country onto a Polish withholding rate.
"""

from __future__ import annotations

import pytest

from data_processing.constants import (
    TICKER_COUNTRY_OVERRIDES,
    TICKER_WITHHOLDING_OVERRIDES,
)

pytestmark = pytest.mark.contract


def test_override_maps_cover_exactly_the_same_tickers() -> None:
    """Test that neither override table carries a ticker the other lacks.

    Given: The two per-ticker override tables in ``constants``
    When:  Their key sets are compared
    Then:  They are identical, so no ticker is overridden on one axis only
    """
    assert set(TICKER_WITHHOLDING_OVERRIDES) == set(TICKER_COUNTRY_OVERRIDES)
