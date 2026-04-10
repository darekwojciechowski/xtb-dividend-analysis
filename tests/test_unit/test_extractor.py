"""Tests for MultiConditionExtractor and extract_condition."""

from __future__ import annotations

import pytest

from data_processing.extractor import MultiConditionExtractor, extract_condition


@pytest.mark.unit
class TestMultiConditionExtractor:
    """Tests for the MultiConditionExtractor class."""

    def test_init_stores_input_string(self) -> None:
        # Covers line 26
        extractor = MultiConditionExtractor("some comment")

        assert extractor.input_string == "some comment"

    def test_extract_condition_when_blik_keyword_then_returns_canonical_label(
        self,
    ) -> None:
        extractor = MultiConditionExtractor("Payment via Blik transfer")

        result = extractor.extract_condition()

        assert result == "Blik(Payu) deposit"

    def test_extract_condition_when_pekao_keyword_then_returns_canonical_label(
        self,
    ) -> None:
        extractor = MultiConditionExtractor("Deposit from Pekao account")

        result = extractor.extract_condition()

        assert result == "Pekao S.A. deposit"

    def test_extract_condition_when_no_keyword_then_returns_original_string(
        self,
    ) -> None:
        original = "Regular dividend payment"
        extractor = MultiConditionExtractor(original)

        result = extractor.extract_condition()

        assert result == original

    def test_extract_condition_case_insensitive_match(self) -> None:
        extractor = MultiConditionExtractor("BLIK payment")

        result = extractor.extract_condition()

        assert result == "Blik(Payu) deposit"

    def test_extract_condition_partial_word_does_not_match(self) -> None:
        # "Bliks" should not match "blik" due to word-boundary regex
        extractor = MultiConditionExtractor("Bliks transfer")

        result = extractor.extract_condition()

        assert result == "Bliks transfer"


@pytest.mark.unit
class TestExtractConditionFunction:
    """Tests for the module-level extract_condition function."""

    def test_when_blik_in_string_then_returns_blik_label(self) -> None:
        assert extract_condition("Blik payment") == "Blik(Payu) deposit"

    def test_when_pekao_in_string_then_returns_pekao_label(self) -> None:
        assert extract_condition("Pekao deposit") == "Pekao S.A. deposit"

    def test_when_no_keyword_then_returns_original(self) -> None:
        assert extract_condition("Unknown source") == "Unknown source"
