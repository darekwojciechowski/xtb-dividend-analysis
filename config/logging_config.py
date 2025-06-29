import logging
import os


def setup_logging(log_level=logging.INFO, log_file="app.log"):
    """
    Set up logging configuration for the application.
    """
    handlers = [logging.StreamHandler()]

    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)

    # Ensure the log file is saved in the logs folder, overwrite on each run (no history)
    log_file_path = os.path.join(logs_dir, log_file)
    handlers.append(logging.FileHandler(log_file_path, encoding="utf-8", mode="w"))

    logging.basicConfig(
        level=log_level,
        format="[%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )
