"""Comment extraction using keyword-based condition matching.

This module provides keyword-based extraction of structured conditions
from free-text comment strings found in XTB broker statements.
"""

from __future__ import annotations

import re

_KEYWORD_MAP: dict[str, str] = {
    "Blik": "Blik(Payu) deposit",  # pragma: no mutate
    "Pekao": "Pekao S.A. deposit",  # pragma: no mutate
}


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
        return extract_condition(self.input_string)


def extract_condition(input_string: str) -> str:
    """Extract a structured condition from a free-text comment string.

    Args:
        input_string: The string from which to extract a condition.

    Returns:
        The canonical condition label matching a keyword, or the original
        input string if no keyword is found.
    """
    lower = input_string.lower()
    for keyword, condition in _KEYWORD_MAP.items():
        if re.compile(r"\b" + re.escape(keyword.lower()) + r"\b").search(lower):
            return condition
    return input_string
