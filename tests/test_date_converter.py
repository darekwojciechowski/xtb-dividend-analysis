"""Tests for DateConverter module."""

import pytest

from data_processing.date_converter import DateConverter


@pytest.mark.unit
class TestValidDateConversion:
    """Test suite for valid date conversion operations."""

    @classmethod
    def setup_class(cls) -> None:
        """Setup class-level fixtures before all tests."""
        cls.standard_date_string = "01.01.2024 12:00:00"
        cls.custom_date_string = "2024/01/01"
        cls.custom_format = "%Y/%m/%d"
        cls.expected_date = "2024-01-01"

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup class-level fixtures after all tests."""
        pass

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

    @classmethod
    def setup_class(cls) -> None:
        """Setup class-level fixtures before all tests."""
        cls.invalid_format_string = "invalid-date"
        cls.empty_string = ""
        cls.non_leap_year_date = "29.02.2023 00:00:00"

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup class-level fixtures after all tests."""
        pass

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
class TestLeapYearHandling:
    """Test suite for leap year date handling."""

    @classmethod
    def setup_class(cls) -> None:
        """Setup class-level fixtures before all tests."""
        cls.leap_year_date = "29.02.2024 00:00:00"
        cls.expected_result = "2024-02-29"

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup class-level fixtures after all tests."""
        pass

    def test_convert_when_leap_year_feb_29_then_converts_correctly(self) -> None:
        """Tests that leap year February 29th is correctly converted."""
        # Arrange
        converter = DateConverter(self.leap_year_date)

        # Act
        converter.convert_to_date()
        result = converter.get_date()

        # Assert
        assert result.strftime("%Y-%m-%d") == self.expected_result
