import logging
import os


def get_file_paths(file_path):
    """
    Define file paths and validate their existence.
    Args:
        file_path (str): Path to the main file.
    Returns:
        tuple: file_path (str), courses_paths (list)
    """
    # Dynamically find all files starting with "archiwum_tab_a_" in the data folder
    data_folder = "data"
    courses_paths = [
        os.path.join(data_folder, f)
        for f in os.listdir(data_folder)
        if f.startswith("archiwum_tab_a_") and f.endswith(".csv")
    ]

    # Check if the main file exists
    if not os.path.exists(file_path):
        logging.error(f"The file '{file_path}' does not exist. Please check the path.")
        raise FileNotFoundError(
            f"The file '{file_path}' does not exist. Please check the path."
        )

    # Check if each course file exists
    for course_path in courses_paths:
        if not os.path.exists(course_path):
            logging.error(
                f"The file '{course_path}' does not exist. Please check the path."
            )
            raise FileNotFoundError(
                f"The file '{course_path}' does not exist. Please check the path."
            )

    return file_path, courses_paths
