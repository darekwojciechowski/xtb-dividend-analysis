"""Date string conversion utilities for XTB statement processing.

This module provides date parsing and normalization for the date formats
found in both Polish and English XTB broker statement exports.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger


class DateConverter:
    """Converts date strings from XTB statements to Python date objects.

    Handles the ``dd.mm.YYYY HH:MM:SS`` format used in XTB exports and
    returns ``None`` safely when the input is missing or unparseable.
    """

    def __init__(self, date_string: str):
        """Initialize DateConverter with a date string.

        Args:
            date_string: The date string to convert.
        """
        self.date_string = date_string
        self.date_only: pd.Timestamp | None = None

    def convert_to_date(self, format: str = "%d.%m.%Y %H:%M:%S") -> None:
        """Convert the date string to a date object using the provided format.

        Sets ``self.date_only`` to ``None`` when the input is empty or
        the conversion fails.

        Args:
            format: strptime format string for the input date.
        """
        if not self.date_string:  # Check for None or empty string
            self.date_only = None
            return
        try:
            self.date_only = pd.to_datetime(self.date_string, format=format).date()
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting date: {e}")
            self.date_only = None

    def get_date(self) -> pd.Timestamp | None:
        """Return the converted date object.

        Returns:
            The converted date object, or ``None`` if conversion failed.
        """
        return self.date_only
