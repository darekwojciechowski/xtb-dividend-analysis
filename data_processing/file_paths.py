from __future__ import annotations

from pathlib import Path

from loguru import logger


def get_file_paths(file_path: str) -> tuple[str, list[str]]:
    """
    Define file paths and validate their existence.
    Args:
        file_path: Path to the main file.
    Returns:
        tuple: file_path (str), courses_paths (list[str])
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
