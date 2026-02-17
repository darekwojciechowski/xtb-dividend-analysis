from __future__ import annotations

import os
import re
from pathlib import Path

from loguru import logger
from playwright.sync_api import sync_playwright

from config.settings import settings


def find_and_download_latest_files() -> None:
    logger.info("Starting the Playwright script.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to NBP currency archive page
        page.goto(settings.nbp_archive_url)

        # Initialize a list to store file elements and their names
        file_elements = []

        # Iterate over potential child elements within the specified parent div
        logger.info("Searching for file elements on the page.")
        for i in range(0, 50):  # Adjust the range as needed
            selector = f".wp-block-buttons.is-layout-flex.wp-block-buttons-is-layout-flex div:nth-child({i})"
            element = page.query_selector(selector)

            if element:
                file_name = element.inner_text()
                logger.debug(f"Found element with text: {file_name}")
                # Extract the year or version number using regex
                match = re.search(r"\d{4}", file_name)
                if match:
                    year = int(match.group())
                    file_elements.append((year, file_name, element))

        # Sort the files by year in descending order
        logger.info("Sorting files by year in descending order.")
        file_elements.sort(reverse=True, key=lambda x: x[0])

        # Download the largest file and the next two largest files by decrementing the year
        downloaded_years = set()
        for year, file_name, element in file_elements:
            if year not in downloaded_years and len(downloaded_years) < 3:
                logger.info(f"Downloading file: {file_name}")

                # Set up download listener
                with page.expect_download() as download_info:
                    element.click()  # Click on the element to initiate download

                # Wait for the download to complete
                download = download_info.value
                # Save to project root 'data' directory
                project_root = Path(__file__).parent.parent
                data_dir = project_root / "data"
                data_dir.mkdir(exist_ok=True)
                download_path = data_dir / download.suggested_filename
                download.save_as(str(download_path))
                logger.info(f"File downloaded to: {download_path}")

                # Add the year to the set of downloaded years
                downloaded_years.add(year)

        logger.info("Closing the browser.")
        browser.close()


if __name__ == "__main__":
    logger.info("Script started.")
    find_and_download_latest_files()
    logger.info("Script finished.")
