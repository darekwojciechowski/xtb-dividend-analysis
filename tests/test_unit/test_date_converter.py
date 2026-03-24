"""Tests for DateConverter module."""

from __future__ import annotations

import pytest

from data_processing.date_converter import DateConverter


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
