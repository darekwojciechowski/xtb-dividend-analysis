"""Download NBP currency exchange rate archives using Playwright.

Fetches the three most recent annual NBP Table A CSV files to the data/
directory.
"""

from __future__ import annotations

import re
from pathlib import Path

from loguru import logger
from playwright.sync_api import sync_playwright

from config.settings import settings


def find_and_download_latest_files() -> None:
    """Download three most recent NBP currency archive files.

    Launches Chromium, navigates to the NBP archive URL, extracts year
    numbers from button labels, and downloads files for the three most
    recent years to data/.
    """
    logger.info("Starting the Playwright script.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(settings.nbp_archive_url)

        try:
            cookie_button = page.get_by_text("Zostaw niezbędne pliki cookies")
            cookie_button.wait_for(timeout=5000)
            cookie_button.click()
            logger.info("Cookie consent dialog dismissed.")
        except Exception:
            logger.debug("No cookie consent dialog found, continuing.")

        file_elements = []
        logger.info("Searching for file elements on the page.")
        # Iterate up to 50 child elements; NBP page structure may vary
        for i in range(0, 50):
            selector = f".wp-block-buttons.is-layout-flex.wp-block-buttons-is-layout-flex div:nth-child({i})"
            element = page.query_selector(selector)

            if element:
                file_name = element.inner_text()
                logger.debug(f"Found element with text: {file_name}")
                # Extract four-digit year to sort by recency
                match = re.search(r"\d{4}", file_name)
                if match:
                    year = int(match.group())
                    file_elements.append((year, file_name, element))

        logger.info("Sorting files by year in descending order.")
        file_elements.sort(reverse=True, key=lambda x: x[0])

        downloaded_years: set[int] = set()
        for year, file_name, element in file_elements:
            if year not in downloaded_years and len(downloaded_years) < 3:
                logger.info(f"Downloading file: {file_name}")
                # Wait for download to complete before saving
                with page.expect_download() as download_info:
                    element.click()  # Click on the element to initiate download

                download = download_info.value
                project_root = Path(__file__).parent.parent
                data_dir = project_root / "data"
                data_dir.mkdir(exist_ok=True)
                download_path = data_dir / download.suggested_filename
                download.save_as(str(download_path))
                logger.info(f"File downloaded to: {download_path}")
                downloaded_years.add(year)

        browser.close()


if __name__ == "__main__":
    logger.info("Script started.")
    find_and_download_latest_files()
    logger.info("Script finished.")
