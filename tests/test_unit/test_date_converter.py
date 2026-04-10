"""Tests for DateConverter module."""

from __future__ import annotations

from datetime import date, datetime

import pytest

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
