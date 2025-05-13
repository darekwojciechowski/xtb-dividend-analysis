import logging
import os


def setup_logging(log_level=logging.INFO, log_file="app.log"):
    """
    Set up logging configuration for the application.
    """
    handlers = [logging.StreamHandler()]

    # Ensure the log file is always used, overwrite on each run (no history)
    log_file_path = os.path.join(os.getcwd(), log_file)
    handlers.append(logging.FileHandler(
        log_file_path, encoding='utf-8', mode='w'))

    logging.basicConfig(
        level=log_level,
        format="[%(levelname)s] %(name)s: %(message)s",
        handlers=handlers
    )
