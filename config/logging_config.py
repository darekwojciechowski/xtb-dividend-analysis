import os
import sys
from loguru import logger


def setup_logging(log_level="INFO", log_file="app.log"):
    """
    Set up logging configuration for the application using loguru.
    Applies modern 2026 color trends: deep teal, warm coral, sage green, and muted purple.
    """
    # Remove default handler
    logger.remove()

    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)

    # Ensure the log file is saved in the logs folder, overwrite on each run (no history)
    log_file_path = os.path.join(logs_dir, log_file)

    # Modern 2026 color palette - trendy, sophisticated colors
    # Deep Teal (#2C7A7B) for DEBUG
    # Sage Green (#68A691) for INFO
    # Warm Coral (#E8927C) for WARNING
    # Muted Purple (#8B7BA8) for ERROR
    # Deep Burgundy (#6B2C3E) for CRITICAL

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

    # Configure custom colors for log levels (2026 trends)
    logger.level("DEBUG", color="<fg #2C7A7B>")      # Deep Teal
    logger.level("INFO", color="<fg #68A691>")       # Sage Green
    logger.level("WARNING", color="<fg #E8927C>")    # Warm Coral
    logger.level("ERROR", color="<fg #8B7BA8>")      # Muted Purple
    logger.level("CRITICAL", color="<fg #6B2C3E>")   # Deep Burgundy

    return logger
