from __future__ import annotations

from pathlib import Path

from loguru import logger


def get_file_paths(file_path: str) -> tuple[str, list[str]]:
    """Resolve and validate the XLSX input path and all NBP archive CSV paths.

    Searches the ``data/`` directory for files matching
    ``archiwum_tab_a_*.csv`` and validates that the main input file and
    each archive file exist on disk.

    Args:
        file_path: Path to the XTB XLSX broker statement.

    Returns:
        A tuple ``(file_path, courses_paths)`` where ``file_path`` is
        the validated XLSX path and ``courses_paths`` is a list of
        matched NBP archive CSV paths.

    Raises:
        FileNotFoundError: If the XLSX file or any NBP archive CSV does
            not exist.
    """
    # Dynamically find all files starting with "archiwum_tab_a_" in the data folder
    data_folder = Path("data")
    courses_paths = [
        str(data_folder / f.name)
        for f in data_folder.glob("archiwum_tab_a_*.csv")
    ]

    # Check if the main file exists
    main_file = Path(file_path)
    if not main_file.exists():
        logger.error(f"The file '{file_path}' does not exist. Please check the path.")
        raise FileNotFoundError(
            f"The file '{file_path}' does not exist. Please check the path."
        )

    # Check if each course file exists
    for course_path in courses_paths:
        course_file = Path(course_path)
        if not course_file.exists():
            logger.error(
                f"The file '{course_path}' does not exist. Please check the path."
            )
            raise FileNotFoundError(
                f"The file '{course_path}' does not exist. Please check the path."
            )

    return file_path, courses_paths
