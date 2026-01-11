from __future__ import annotations

import pandas as pd


class DateConverter:
    def __init__(self, date_string: str):
        """
        Initializes the DateConverter with a date string.

        :param date_string: The date string to be converted.
        """
        self.date_string = date_string
        self.date_only: pd.Timestamp | None = None

    def convert_to_date(self, format: str = "%d.%m.%Y %H:%M:%S") -> None:
        """
        Converts the date string to a date object based on the provided format.

        :param format: The format in which the date_string is provided.
        """
        if not self.date_string:  # Check for None or empty string
            self.date_only = None
            return
        try:
            self.date_only = pd.to_datetime(self.date_string, format=format).date()
        except (ValueError, TypeError) as e:
            print(f"Error converting date: {e}")
            self.date_only = None

    def get_date(self) -> pd.Timestamp | None:
        """
        Returns the converted date object.

        :return: The converted date object or None if conversion failed.
        """
        return self.date_only
