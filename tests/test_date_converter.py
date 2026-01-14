"""Tests for DateConverter module."""

import pytest

from data_processing.date_converter import DateConverter


@pytest.mark.unit
class TestValidDateConversion:
    """Test suite for valid date conversion operations."""

    def test_converts_standard_format(self) -> None:
        """Tests that a valid date string is correctly converted to a date object."""
        converter = DateConverter("01.01.2024 12:00:00")
        converter.convert_to_date()
        assert converter.get_date().strftime("%Y-%m-%d") == "2024-01-01"

    def test_converts_custom_format(self) -> None:
        """Tests that a valid date string with a custom format is correctly converted."""
        converter = DateConverter("2024/01/01")
        converter.convert_to_date(format="%Y/%m/%d")
        assert converter.get_date().strftime("%Y-%m-%d") == "2024-01-01"


@pytest.mark.unit
@pytest.mark.edge_case
class TestInvalidDateHandling:
    """Test suite for invalid date handling and edge cases."""

    def test_invalid_format_returns_none(self) -> None:
        """Tests that an invalid date string format results in None."""
        converter = DateConverter("invalid-date")
        converter.convert_to_date()
        assert converter.get_date() is None

    def test_empty_string_returns_none(self) -> None:
        """Tests that an empty date string results in None."""
        converter = DateConverter("")
        converter.convert_to_date()
        assert converter.get_date() is None

    def test_none_value_returns_none(self) -> None:
        """Tests that initializing with None results in None for the converted date."""
        converter = DateConverter(None)
        converter.convert_to_date()
        assert converter.get_date() is None

    def test_non_leap_year_feb_29_returns_none(self) -> None:
        """Tests that an invalid leap year date results in None."""
        converter = DateConverter("29.02.2023 00:00:00")
        converter.convert_to_date()
        assert converter.get_date() is None


@pytest.mark.unit
@pytest.mark.edge_case
class TestLeapYearHandling:
    """Test suite for leap year date handling."""

    def test_leap_year_feb_29_converts_correctly(self) -> None:
        """Tests that a leap year date is correctly converted."""
        converter = DateConverter("29.02.2024 00:00:00")
        converter.convert_to_date()
        assert converter.get_date().strftime("%Y-%m-%d") == "2024-02-29"
