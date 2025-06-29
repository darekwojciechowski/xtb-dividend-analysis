import re
from typing import Dict


class MultiConditionExtractor:
    def __init__(self, input_string: str):
        """
        Initializes the MultiConditionExtractor with an input string.

        :param input_string: The string from which to extract conditions based on keywords.
        """
        self.input_string = input_string

    def extract_condition(self) -> str:
        """
        Extracts a condition from the input string based on predefined keywords.

        :return: A string representing the extracted condition based on keywords, or the original input string if no match is found.
        """
        # Define a mapping of keywords to their corresponding conditions
        keyword_map: Dict[str, str] = {
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
