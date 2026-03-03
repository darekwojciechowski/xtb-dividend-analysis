"""Unit tests for the Playwright-based NBP currency archive downloader.

Tests cover all key behaviours of ``find_and_download_latest_files``:

- Navigates to the URL from ``settings.nbp_archive_url``.
- Extracts four-digit year numbers from element text via regex.
- Ignores elements whose text contains no four-digit year.
- Sorts found years descending and downloads only the three most recent.
- Skips duplicate year entries so each year is downloaded at most once.
- Saves each file to the ``data/`` directory under the project root.
- Creates the ``data/`` directory if it does not already exist.
- Performs no downloads when no matching elements are found on the page.

All external dependencies (``sync_playwright``, filesystem) are mocked so the
tests run without a real browser or network connection.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from data_acquisition.playwright_download_currency_archive import (
    find_and_download_latest_files,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_element(year_label: str) -> MagicMock:
    """Return a mock page element whose inner_text returns *year_label*.

    Args:
        year_label: Text the mock element should return from ``inner_text()``.

    Returns:
        MagicMock configured as a Playwright element handle.
    """
    el = MagicMock()
    el.inner_text.return_value = year_label
    return el


def _make_download_context_manager(suggested_filename: str) -> MagicMock:
    """Return a mock ``expect_download()`` context manager.

    Args:
        suggested_filename: The filename the mock download should report.

    Returns:
        MagicMock that behaves like ``playwright.expect_download()``
        context manager, exposing ``value.suggested_filename``.
    """
    mock_download = MagicMock()
    mock_download.suggested_filename = suggested_filename

    mock_download_info = MagicMock()
    mock_download_info.value = mock_download

    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_download_info)
    mock_cm.__exit__ = MagicMock(return_value=False)
    return mock_cm


def _build_playwright_mocks(
    elements_by_index: dict[int, MagicMock],
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Build a hierarchy of Playwright mocks wired to the given elements.

    Args:
        elements_by_index: Mapping of ``range(0, 50)`` child index → mock
            element.  Indices not present return ``None`` from
            ``query_selector``.

    Returns:
        Tuple of (mock_sync_playwright_cm, mock_browser, mock_page).
    """
    mock_page = MagicMock()

    def _query_selector(selector: str) -> MagicMock | None:
        for idx, el in elements_by_index.items():
            if f"nth-child({idx})" in selector:
                return el
        return None

    mock_page.query_selector.side_effect = _query_selector

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_playwright = MagicMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    mock_sync_pw_cm = MagicMock()
    mock_sync_pw_cm.__enter__ = MagicMock(return_value=mock_playwright)
    mock_sync_pw_cm.__exit__ = MagicMock(return_value=False)

    return mock_sync_pw_cm, mock_browser, mock_page


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFindAndDownloadLatestFiles:
    """Unit tests for ``find_and_download_latest_files``."""

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def test_find_and_download_latest_files_navigates_to_configured_url(self) -> None:
        """Browser must open the URL stored in ``settings.nbp_archive_url``."""
        # Arrange
        mock_sync_pw_cm, _, mock_page = _build_playwright_mocks({})
        mock_page.expect_download.return_value = _make_download_context_manager(
            "dummy.csv"
        )

        with (
            patch(
                "data_acquisition.playwright_download_currency_archive.sync_playwright",
                return_value=mock_sync_pw_cm,
            ),
            patch(
                "data_acquisition.playwright_download_currency_archive.settings"
            ) as mock_settings,
        ):
            mock_settings.nbp_archive_url = "https://example.com/archive"

            # Act
            find_and_download_latest_files()

        # Assert
        mock_page.goto.assert_called_once_with("https://example.com/archive")

    # ------------------------------------------------------------------
    # Year extraction
    # ------------------------------------------------------------------

    def test_find_and_download_latest_files_ignores_elements_without_year(self) -> None:
        """Elements whose text contains no four-digit number must be skipped."""
        # Arrange
        element_no_year = _make_element("Tabela A – inne pliki")
        mock_sync_pw_cm, _, mock_page = _build_playwright_mocks({1: element_no_year})

        with patch(
            "data_acquisition.playwright_download_currency_archive.sync_playwright",
            return_value=mock_sync_pw_cm,
        ):
            # Act
            find_and_download_latest_files()

        # Assert – no download was triggered
        mock_page.expect_download.assert_not_called()

    def test_find_and_download_latest_files_extracts_year_from_element_text(
        self,
    ) -> None:
        """A four-digit year present in element text must trigger a download."""
        # Arrange
        el_2025 = _make_element("Archiwum 2025")
        mock_sync_pw_cm, _, mock_page = _build_playwright_mocks({1: el_2025})
        mock_page.expect_download.return_value = _make_download_context_manager(
            "archiwum_tab_a_2025.csv"
        )

        with patch(
            "data_acquisition.playwright_download_currency_archive.sync_playwright",
            return_value=mock_sync_pw_cm,
        ):
            # Act
            find_and_download_latest_files()

        # Assert
        mock_page.expect_download.assert_called_once()

    # ------------------------------------------------------------------
    # Limit to three most recent years
    # ------------------------------------------------------------------

    def test_find_and_download_latest_files_downloads_only_three_most_recent_years(
        self,
    ) -> None:
        """When four elements are present exactly three most recent must be downloaded."""
        # Arrange
        elements = {
            1: _make_element("Archiwum 2026"),
            2: _make_element("Archiwum 2025"),
            3: _make_element("Archiwum 2024"),
            4: _make_element("Archiwum 2023"),
        }
        mock_sync_pw_cm, _, mock_page = _build_playwright_mocks(elements)
        mock_page.expect_download.side_effect = [
            _make_download_context_manager("archiwum_tab_a_2026.csv"),
            _make_download_context_manager("archiwum_tab_a_2025.csv"),
            _make_download_context_manager("archiwum_tab_a_2024.csv"),
        ]

        with patch(
            "data_acquisition.playwright_download_currency_archive.sync_playwright",
            return_value=mock_sync_pw_cm,
        ):
            # Act
            find_and_download_latest_files()

        # Assert – exactly three downloads
        assert mock_page.expect_download.call_count == 3

    def test_find_and_download_latest_files_skips_oldest_year_when_four_found(
        self,
    ) -> None:
        """The oldest year must not be clicked when four years are available."""
        # Arrange
        el_2023 = _make_element("Archiwum 2023")
        elements = {
            1: _make_element("Archiwum 2026"),
            2: _make_element("Archiwum 2025"),
            3: _make_element("Archiwum 2024"),
            4: el_2023,
        }
        mock_sync_pw_cm, _, mock_page = _build_playwright_mocks(elements)
        mock_page.expect_download.side_effect = [
            _make_download_context_manager("archiwum_tab_a_2026.csv"),
            _make_download_context_manager("archiwum_tab_a_2025.csv"),
            _make_download_context_manager("archiwum_tab_a_2024.csv"),
        ]

        with patch(
            "data_acquisition.playwright_download_currency_archive.sync_playwright",
            return_value=mock_sync_pw_cm,
        ):
            # Act
            find_and_download_latest_files()

        # Assert – the 2023 element was never clicked
        el_2023.click.assert_not_called()

    # ------------------------------------------------------------------
    # Duplicate years
    # ------------------------------------------------------------------

    def test_find_and_download_latest_files_downloads_duplicate_year_only_once(
        self,
    ) -> None:
        """Duplicate year entries on the page must produce a single download."""
        # Arrange
        elements = {
            1: _make_element("Archiwum 2025 (wersja 1)"),
            2: _make_element("Archiwum 2025 (wersja 2)"),
        }
        mock_sync_pw_cm, _, mock_page = _build_playwright_mocks(elements)
        mock_page.expect_download.return_value = _make_download_context_manager(
            "archiwum_tab_a_2025.csv"
        )

        with patch(
            "data_acquisition.playwright_download_currency_archive.sync_playwright",
            return_value=mock_sync_pw_cm,
        ):
            # Act
            find_and_download_latest_files()

        # Assert – year 2025 downloaded exactly once despite two elements
        assert mock_page.expect_download.call_count == 1

    # ------------------------------------------------------------------
    # No elements found
    # ------------------------------------------------------------------

    def test_find_and_download_latest_files_does_nothing_when_no_elements_found(
        self,
    ) -> None:
        """No downloads should be attempted when no page elements are matched."""
        # Arrange
        mock_sync_pw_cm, _, mock_page = _build_playwright_mocks({})

        with patch(
            "data_acquisition.playwright_download_currency_archive.sync_playwright",
            return_value=mock_sync_pw_cm,
        ):
            # Act
            find_and_download_latest_files()

        # Assert
        mock_page.expect_download.assert_not_called()

    # ------------------------------------------------------------------
    # File save path
    # ------------------------------------------------------------------

    def test_find_and_download_latest_files_saves_file_inside_data_directory(
        self,
    ) -> None:
        """Downloaded file must be saved inside a path that contains a ``data`` segment."""
        # Arrange
        el_2025 = _make_element("Archiwum 2025")
        mock_sync_pw_cm, _, mock_page = _build_playwright_mocks({1: el_2025})
        mock_page.expect_download.return_value = _make_download_context_manager(
            "archiwum_tab_a_2025.csv"
        )

        with patch(
            "data_acquisition.playwright_download_currency_archive.sync_playwright",
            return_value=mock_sync_pw_cm,
        ):
            # Act
            find_and_download_latest_files()

        # Assert – save_as called with a path that contains the 'data' directory
        download_mock = (
            mock_page.expect_download.return_value.__enter__.return_value.value
        )
        call_args = download_mock.save_as.call_args
        assert call_args is not None
        saved_path = Path(call_args[0][0])
        assert "data" in saved_path.parts
        assert saved_path.name == "archiwum_tab_a_2025.csv"

    def test_find_and_download_latest_files_uses_suggested_filename(self) -> None:
        """``download.suggested_filename`` must be used as the saved file name."""
        # Arrange
        el_2026 = _make_element("Archiwum 2026")
        mock_sync_pw_cm, _, mock_page = _build_playwright_mocks({1: el_2026})
        expected_name = "archiwum_tab_a_2026.csv"
        mock_page.expect_download.return_value = _make_download_context_manager(
            expected_name
        )

        with patch(
            "data_acquisition.playwright_download_currency_archive.sync_playwright",
            return_value=mock_sync_pw_cm,
        ):
            # Act
            find_and_download_latest_files()

        # Assert
        download_mock = (
            mock_page.expect_download.return_value.__enter__.return_value.value
        )
        saved_path: str = download_mock.save_as.call_args[0][0]
        assert saved_path.endswith(expected_name)

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    def test_find_and_download_latest_files_launches_browser_headless_false(
        self,
    ) -> None:
        """Chromium must be launched with ``headless=False``."""
        # Arrange
        mock_sync_pw_cm, mock_browser, _ = _build_playwright_mocks({})

        with patch(
            "data_acquisition.playwright_download_currency_archive.sync_playwright",
            return_value=mock_sync_pw_cm,
        ):
            # Act
            find_and_download_latest_files()

        # Assert
        mock_playwright = mock_sync_pw_cm.__enter__.return_value
        mock_playwright.chromium.launch.assert_called_once_with(headless=False)

    def test_find_and_download_latest_files_closes_browser_after_completion(
        self,
    ) -> None:
        """Browser must be closed even when no files are downloaded."""
        # Arrange
        mock_sync_pw_cm, mock_browser, _ = _build_playwright_mocks({})

        with patch(
            "data_acquisition.playwright_download_currency_archive.sync_playwright",
            return_value=mock_sync_pw_cm,
        ):
            # Act
            find_and_download_latest_files()

        # Assert
        mock_browser.close.assert_called_once()

    # ------------------------------------------------------------------
    # Click behaviour
    # ------------------------------------------------------------------

    def test_find_and_download_latest_files_clicks_element_to_trigger_download(
        self,
    ) -> None:
        """Each downloaded year must be initiated by clicking its element."""
        # Arrange
        el_2025 = _make_element("Archiwum 2025")
        mock_sync_pw_cm, _, mock_page = _build_playwright_mocks({1: el_2025})
        mock_page.expect_download.return_value = _make_download_context_manager(
            "archiwum_tab_a_2025.csv"
        )

        with patch(
            "data_acquisition.playwright_download_currency_archive.sync_playwright",
            return_value=mock_sync_pw_cm,
        ):
            # Act
            find_and_download_latest_files()

        # Assert
        el_2025.click.assert_called_once()
