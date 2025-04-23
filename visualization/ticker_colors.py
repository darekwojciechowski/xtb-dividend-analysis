# ticker_colors.py

import random

ticker_colors = {
    '': '\033[92m',  # Green
    '': '\033[91m',  # Red
    '': '\033[90m',  # Dark Gray
    '': '\033[97m',  # Light Gray
    '': '\033[33m',  # Yellow
    '': '\033[34m',  # Blue
    '': '\033[35m',  # Magenta
    '': '\033[36m',  # Cyan
    '': '\033[33m',  # Orange
    '': '\033[37m',  # White
    '': '\033[32m',  # Light Green
    '': '\033[31m',  # Light Red
    '': '\033[30m',  # Black
    '': '\033[95m',  # Purple
    '': '\033[96m',  # Light Cyan
    '': '\033[94m',  # Light Blue
    '': '\033[92m',  # Light Yellow
    '': '\033[91m',  # Light Magenta
    '': '\033[0m',   # Reset color
}

# Function to get a random color from ticker_colors


def get_random_color():
    """Return a randomly selected color from the ticker_colors dictionary."""
    return random.choice(list(ticker_colors.values()))
