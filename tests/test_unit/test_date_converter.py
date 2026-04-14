"""Tests for DateConverter module."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from loguru import logger

from data_processing.date_converter import DateConverter, convert_date, to_date


@pytest.mark.unit
class TestValidDateConversion:
    """Test suite for valid date conversion operations."""

    standard_date_string = "01.01.2024 12:00:00"
    custom_date_string = "2024/01/01"
    custom_format = "%Y/%m/%d"
    expected_date = "2024-01-01"

    def test_convert_when_standard_format_provided_then_returns_correct_date(
        self,
    ) -> None:
        """Tests conversion of standard format date string."""
        # Arrange
        converter = DateConverter(self.standard_date_string)

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result.strftime("%Y-%m-%d") == self.expected_date

    def test_convert_when_custom_format_provided_then_returns_correct_date(
        self,
    ) -> None:
        """Tests conversion of custom format date string."""
        # Arrange
        converter = DateConverter(self.custom_date_string)

        # Act
        converter.convert_to_date(format=self.custom_format)
        result = converter.get_date()

        # Assert
        assert result.strftime("%Y-%m-%d") == self.expected_date


@pytest.mark.unit
@pytest.mark.edge_case
class TestInvalidDateHandling:
    """Test suite for invalid date handling and edge cases."""

    invalid_format_string = "invalid-date"
    empty_string = ""
    non_leap_year_date = "29.02.2023 00:00:00"

    def test_convert_when_invalid_format_then_returns_none(self) -> None:
        """Tests that invalid date format returns None."""
        # Arrange
        converter = DateConverter(self.invalid_format_string)

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result is None

    def test_convert_when_empty_string_then_returns_none(self) -> None:
        """Tests that empty string returns None."""
        # Arrange
        converter = DateConverter(self.empty_string)

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result is None

    def test_convert_when_none_value_then_returns_none(self) -> None:
        """Tests that None value returns None."""
        # Arrange
        converter = DateConverter(None)

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result is None

    def test_convert_when_non_leap_year_feb_29_then_returns_none(self) -> None:
        """Tests that invalid leap year date returns None."""
        # Arrange
        converter = DateConverter(self.non_leap_year_date)

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result is None


@pytest.mark.unit
@pytest.mark.edge_case
class TestInitialState:
    """Test suite for DateConverter initial state before conversion."""

    def test_init_when_created_then_date_only_is_none(self) -> None:
        """date_only attribute is None immediately after construction."""
        # Arrange / Act
        converter = DateConverter("01.01.2024 12:00:00")

        # Assert — without calling convert_to_date, the date must still be None
        assert converter.date_only is None

    def test_init_when_none_date_string_then_date_only_still_none(self) -> None:
        """Passing None as date_string leaves date_only as None before conversion."""
        # Arrange / Act
        converter = DateConverter(None)

        # Assert
        assert converter.date_only is None


@pytest.mark.unit
@pytest.mark.edge_case
class TestFormatSpecificity:
    """Test suite verifying format-string correctness (day vs. month disambiguation)."""

    # 15.01.2024 — day=15, month=1; wrong format would swap to day=1, month=15
    date_string = "15.01.2024 00:00:00"

    def test_convert_when_default_format_then_day_is_15_not_1(self) -> None:
        """Default %d.%m.%Y format maps first field to day, not month."""
        # Arrange
        converter = DateConverter(self.date_string)

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result.day == 15
        assert result.month == 1

    def test_convert_when_whitespace_only_then_returns_none(self) -> None:
        """A whitespace-only string is treated as empty and returns None."""
        # Arrange
        converter = DateConverter("   ")

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result is None


@pytest.mark.unit
@pytest.mark.edge_case
class TestLeapYearHandling:
    """Test suite for leap year date handling."""

    leap_year_date = "29.02.2024 00:00:00"
    expected_result = "2024-02-29"

    def test_convert_when_leap_year_feb_29_then_converts_correctly(self) -> None:
        """Tests that leap year February 29th is correctly converted."""
        # Arrange
        converter = DateConverter(self.leap_year_date)

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result.strftime("%Y-%m-%d") == self.expected_result


@pytest.mark.unit
class TestConvertDateFunction:
    """Tests for the module-level convert_date function."""

    def test_convert_date_when_valid_string_then_returns_date(self) -> None:
        result = convert_date("01.03.2024 10:00:00")

        assert result.strftime("%Y-%m-%d") == "2024-03-01"

    def test_convert_date_when_none_then_returns_none(self) -> None:
        assert convert_date(None) is None

    def test_convert_date_when_empty_string_then_returns_none(self) -> None:
        assert convert_date("") is None

    def test_convert_date_when_whitespace_only_then_returns_none(self) -> None:
        # Covers line 71: the strip() branch of the guard
        assert convert_date("   ") is None

    def test_convert_date_when_invalid_format_then_returns_none(self) -> None:
        # Covers lines 74-76: ValueError → logger.error → return None
        assert convert_date("not-a-date") is None

    def test_convert_date_when_custom_format_provided_then_parses_correctly(
        self,
    ) -> None:
        result = convert_date("2024/06/15", format="%Y/%m/%d")

        assert result.strftime("%Y-%m-%d") == "2024-06-15"

    def test_convert_date_when_default_format_then_day_field_is_25(self) -> None:
        # Kills mutmut_1/2/3: day=25 is unambiguous — any wrong format either
        # fails to parse (→ None) or maps the fields incorrectly.
        result = convert_date("25.06.2024 08:15:00")

        assert result is not None
        assert result.day == 25
        assert result.month == 6

    def test_convert_date_when_default_format_then_four_digit_year_is_preserved(
        self,
    ) -> None:
        # Kills mutmut_2: %y (2-digit) would misparse "2024" as year 20 or fail.
        result = convert_date("15.03.2024 00:00:00")

        assert result is not None
        assert result.year == 2024

    def test_convert_date_when_default_format_then_month_field_is_correct(self) -> None:
        # Kills mutmut_3: %D/%M swap — day=15 > 12 forces correct %d/%m ordering.
        result = convert_date("15.11.2024 00:00:00")

        assert result is not None
        assert result.day == 15
        assert result.month == 11


@pytest.mark.unit
class TestDateConverterFormatSpecificityMutation:
    """Mutation-targeted tests for DateConverter.convert_to_date format correctness.

    These tests kill mutmut_1/2/3 (corrupt default format strings) by asserting on
    unambiguous day/month values, and mutmut_8/10 (format=None / format dropped) by
    using an ambiguous date where day != month so that format=None would swap them.
    """

    def test_convert_when_unambiguous_date_then_day_and_month_are_correct(self) -> None:
        """day=15, month=11 — a corrupt format raises ValueError → None, killing mutmut_1/2/3."""
        # Arrange
        converter = DateConverter("15.11.2024 00:00:00")

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result is not None
        assert result.day == 15
        assert result.month == 11
        assert result.year == 2024

    def test_convert_when_ambiguous_date_then_format_controls_day_vs_month(
        self,
    ) -> None:
        """01.02.2024 — with correct %d.%m format day=1, month=2.

        Kills mutmut_8 (format=None) and mutmut_10 (format arg removed): pandas with
        inferred format may parse this as month=1, day=2 (US convention).
        """
        # Arrange
        converter = DateConverter("01.02.2024 00:00:00")

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result is not None
        assert result.day == 1
        assert result.month == 2

    def test_convert_when_custom_format_then_format_argument_is_used(self) -> None:
        """Custom format %Y/%m/%d — without format the default %d.%m.%Y raises ValueError.

        Kills mutmut_8/10: format=None or missing causes a parse failure for this input.
        """
        # Arrange
        converter = DateConverter("2024/09/20")

        # Act
        converter.convert_to_date(format="%Y/%m/%d")
        result = converter.get_date()

        # Assert
        assert result is not None
        assert result.day == 20
        assert result.month == 9
        assert result.year == 2024


@pytest.mark.unit
class TestDateConverterLogging:
    """Mutation-targeted logging tests for DateConverter.convert_to_date.

    Kills mutmut_11: logger.error(None) would not produce "Error converting date".
    """

    def test_convert_when_invalid_input_then_logs_error_with_exception_text(
        self,
    ) -> None:
        # Arrange
        captured: list[str] = []
        sink_id = logger.add(lambda msg: captured.append(msg), level="ERROR")
        converter = DateConverter("not-a-date")

        # Act
        try:
            converter.convert_to_date()
        finally:
            logger.remove(sink_id)

        # Assert
        assert len(captured) == 1
        assert "Error converting date" in captured[0]


@pytest.mark.unit
class TestConvertDateLogging:
    """Tests that verify error logging behaviour inside convert_date."""

    def test_convert_date_when_invalid_input_then_logs_error_with_exception_text(
        self,
    ) -> None:
        # Kills mutmut_12: logger.error(None) would not contain "Error converting date".
        # Arrange
        captured: list[str] = []
        sink_id = logger.add(lambda msg: captured.append(msg), level="ERROR")

        # Act
        try:
            convert_date("not-a-date")
        finally:
            logger.remove(sink_id)

        # Assert
        assert len(captured) == 1
        assert "Error converting date" in captured[0]


@pytest.mark.unit
class TestToDateFunction:
    """Tests for to_date normalisation helper."""

    def test_to_date_when_timestamp_then_returns_date(self) -> None:
        import pandas as pd

        ts = pd.Timestamp("2024-05-20")

        result = to_date(ts)

        assert result == date(2024, 5, 20)
        assert type(result) is date

    def test_to_date_when_datetime_then_returns_date(self) -> None:
        # Covers line 91: isinstance(value, datetime) branch
        dt = datetime(2024, 7, 4, 12, 0, 0)

        result = to_date(dt)

        assert result == date(2024, 7, 4)
        assert type(result) is date

    def test_to_date_when_date_then_returns_same_date(self) -> None:
        # Covers line 92: passthrough for already-date objects
        d = date(2024, 8, 1)

        result = to_date(d)

        assert result is d
