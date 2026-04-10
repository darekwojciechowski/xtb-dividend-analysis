"""Tests for get_file_paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from data_processing.file_paths import get_file_paths


@pytest.mark.unit
class TestGetFilePaths:
    """Tests for the get_file_paths function."""

    def test_returns_file_path_and_courses_when_all_exist(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange: build real data/ folder with CSVs inside tmp_path
        monkeypatch.chdir(tmp_path)
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "archiwum_tab_a_2023.csv").touch()
        (data_dir / "archiwum_tab_a_2024.csv").touch()
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()

        result_path, result_courses = get_file_paths(str(xlsx))

        assert result_path == str(xlsx)
        assert len(result_courses) == 2

    def test_raises_when_main_file_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        missing = str(tmp_path / "nonexistent.xlsx")

        with pytest.raises(FileNotFoundError, match="does not exist"):
            get_file_paths(missing)

    def test_raises_when_course_file_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Covers lines 42-52: glob reports a CSV that does not exist on disk
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()
        ghost = tmp_path / "data" / "archiwum_tab_a_ghost.csv"  # never created

        # Patch Path.glob so it yields the ghost path without it existing
        with patch.object(Path, "glob", return_value=[ghost]):
            with pytest.raises(FileNotFoundError, match="does not exist"):
                get_file_paths(str(xlsx))

    def test_returns_empty_courses_list_when_no_archive_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()

        result_path, result_courses = get_file_paths(str(xlsx))

        assert result_path == str(xlsx)
        assert result_courses == []
