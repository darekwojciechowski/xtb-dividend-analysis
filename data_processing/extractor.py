"""Comment extraction using keyword-based condition matching.

This module provides keyword-based extraction of structured conditions
from free-text comment strings found in XTB broker statements.
"""

from __future__ import annotations

import re


class MultiConditionExtractor:
    """Extracts structured conditions from free-text comment strings.

    Matches predefined keywords in the input string and maps them to
    canonical condition labels used elsewhere in the pipeline.
    """

    def __init__(self, input_string: str):
        """Initialize MultiConditionExtractor with a comment string.

        Args:
            input_string: The string from which to extract conditions
                based on keywords.
        """
        self.input_string = input_string

    def extract_condition(self) -> str:
        """Extract a condition from the input string based on predefined keywords.

        Returns:
            The canonical condition label matching a keyword, or the
            original input string if no keyword is found.
        """
        # Define a mapping of keywords to their corresponding conditions
        keyword_map: dict[str, str] = {
            "Blik": "Blik(Payu) deposit",
            "Pekao": "Pekao S.A. deposit",
        }

        # Convert the input string to lowercase for case-insensitive matching
        lower_input_string = self.input_string.lower()

        # Search for each keyword in the lowercase input string
        for keyword, condition in keyword_map.items():
            pattern = re.compile(
                r"\b" + re.escape(keyword.lower()) + r"\b", re.IGNORECASE
            )
            if pattern.search(lower_input_string):
                return condition

        # Return the original input string if no keywords are matched
        return self.input_string
