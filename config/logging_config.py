"""Loguru logging configuration for XTB Dividend Analysis.

Call ``setup_logging()`` once at application startup to configure
console and file handlers with consistent formatting.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_level: str = "INFO", log_file: str = "app.log"):
    """Configure loguru handlers for console and file output.

    Removes the default loguru handler and adds a colorized stderr
    handler and a plain-text rotating file handler under ``logs/``.
    The file is overwritten on each run (``mode="w"``).

    Args:
        log_level: Minimum log level to emit (for example, ``"DEBUG"``
            or ``"INFO"``).
        log_file: Filename for the log file inside the ``logs/``
            directory.

    Returns:
        The configured ``loguru.logger`` instance.
    """
    # Remove default handler
    logger.remove()

    # Configure custom colors for levels
    logger.level("DEBUG", color="<cyan>")
    logger.level("INFO", color="<white>")
    logger.level("SUCCESS", color="<green>")
    logger.level("WARNING", color="<yellow>")
    logger.level("ERROR", color="<red>")
    logger.level("CRITICAL", color="<RED><bold>")

    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Ensure the log file is saved in the logs folder, overwrite on each run (no history)
    log_file_path = logs_dir / log_file

    format_string = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Console handler with custom colors
    logger.add(
        sys.stderr,
        format=format_string,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # File handler without colors
    logger.add(
        log_file_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=log_level,
        mode="w",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )

    return logger
