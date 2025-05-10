import pytest
from data_processing.date_converter import DateConverter


def test_valid_date_conversion():
    """
    Tests that a valid date string is correctly converted to a date object.
    """
    converter = DateConverter("01.01.2024 12:00:00")
    converter.convert_to_date()
    assert converter.get_date().strftime("%Y-%m-%d") == "2024-01-01"


def test_invalid_date_format():
    """
    Tests that an invalid date string format results in None for the converted date.
    """
    converter = DateConverter("invalid-date")
    converter.convert_to_date()
    assert converter.get_date() is None


def test_custom_date_format():
    """
    Tests that a valid date string with a custom format is correctly converted.
    """
    converter = DateConverter("2024/01/01")
    converter.convert_to_date(format="%Y/%m/%d")
    assert converter.get_date().strftime("%Y-%m-%d") == "2024-01-01"


def test_empty_date_string():
    """
    Tests that an empty date string results in None for the converted date.
    """
    converter = DateConverter("")
    converter.convert_to_date()
    assert converter.get_date() is None


def test_none_date_string():
    """
    Tests that initializing with None as the date string results in None for the converted date.
    """
    converter = DateConverter(None)
    converter.convert_to_date()
    assert converter.get_date() is None


def test_edge_case_leap_year():
    """
    Tests that a leap year date is correctly converted.
    """
    converter = DateConverter("29.02.2024 00:00:00")
    converter.convert_to_date()
    assert converter.get_date().strftime("%Y-%m-%d") == "2024-02-29"


def test_edge_case_non_leap_year():
    """
    Tests that an invalid leap year date results in None for the converted date.
    """
    converter = DateConverter("29.02.2023 00:00:00")
    converter.convert_to_date()
    assert converter.get_date() is None
