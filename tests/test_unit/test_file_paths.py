"""Tests for get_file_paths."""

from __future__ import annotations

import re
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
        """Arrange: a data directory containing two archive CSVs and a valid xlsx file.
        Act: call get_file_paths with the xlsx path.
        Assert: the function returns the xlsx path and a list of two CSV paths.
        """
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
        """Arrange: a data directory exists but the main xlsx file is absent from disk.
        Act: call get_file_paths with the missing xlsx path.
        Assert: FileNotFoundError is raised with a message containing "does not exist".
        """
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        missing = str(tmp_path / "nonexistent.xlsx")

        with pytest.raises(FileNotFoundError, match="does not exist"):
            get_file_paths(missing)

    def test_raises_when_course_file_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arrange: a valid xlsx file and a glob that reports a CSV not present on disk.
        Act: call get_file_paths with the xlsx path.
        Assert: FileNotFoundError is raised with a message containing "does not exist".
        """
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()
        ghost = tmp_path / "data" / "archiwum_tab_a_ghost.csv"  # never created

        with patch.object(Path, "glob", return_value=[ghost]):
            with pytest.raises(FileNotFoundError, match="does not exist"):
                get_file_paths(str(xlsx))

    def test_returns_empty_courses_list_when_no_archive_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arrange: a data directory with no archive CSVs and a valid xlsx file.
        Act: call get_file_paths with the xlsx path.
        Assert: the function returns the xlsx path and an empty list.
        """
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()

        result_path, result_courses = get_file_paths(str(xlsx))

        assert result_path == str(xlsx)
        assert result_courses == []


@pytest.mark.unit
class TestGetFilePathsGuardLogic:
    """Mutation-killing tests for the two guard conditions."""

    def test_returns_tuple_without_raising_when_main_file_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arrange: a valid xlsx file and a data directory with no archive CSVs.
        Act: call get_file_paths with the xlsx path.
        Assert: the function returns the xlsx path and an empty list without raising.
        """
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()

        path, courses = get_file_paths(str(xlsx))

        assert path == str(xlsx)  # kills mutant: return changed
        assert courses == []  # kills mutant: list changed

    def test_does_not_raise_for_existing_course_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arrange: two archive CSV files and a valid xlsx file in the expected directories.
        Act: call get_file_paths with the xlsx path.
        Assert: the function returns both CSV paths in the courses list.
        """
        monkeypatch.chdir(tmp_path)
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        csv1 = data_dir / "archiwum_tab_a_2022.csv"
        csv2 = data_dir / "archiwum_tab_a_2023.csv"
        csv1.touch()
        csv2.touch()
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()

        path, courses = get_file_paths(str(xlsx))

        assert path == str(xlsx)
        assert len(courses) == 2  # kills mutant: loop guard inverted
        assert "data/archiwum_tab_a_2022.csv" in courses
        assert "data/archiwum_tab_a_2023.csv" in courses


@pytest.mark.unit
class TestGetFilePathsGlobBehavior:
    """Kills mutations to 'data' folder name and 'archiwum_tab_a_*.csv' pattern."""

    def test_ignores_csv_with_different_prefix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arrange: one archive CSV matching the expected prefix and one with a different name.
        Act: call get_file_paths with the xlsx path.
        Assert: only the matching CSV appears in the returned courses list.
        """
        monkeypatch.chdir(tmp_path)
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "archiwum_tab_a_2023.csv").touch()
        (data_dir / "other_file.csv").touch()
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()

        _, courses = get_file_paths(str(xlsx))

        assert len(courses) == 1  # kills mutant: glob pattern changed

    def test_resolves_paths_inside_data_folder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arrange: one archive CSV inside the data directory and a valid xlsx file.
        Act: call get_file_paths with the xlsx path.
        Assert: the returned course path starts with the "data/" prefix.
        """
        monkeypatch.chdir(tmp_path)
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "archiwum_tab_a_2024.csv").touch()
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()

        _, courses = get_file_paths(str(xlsx))

        assert courses[0].startswith("data/")  # kills mutant: Path("data") changed


@pytest.mark.unit
class TestGetFilePathsErrorMessages:
    """Kills string-literal mutations in FileNotFoundError messages."""

    def test_main_file_error_contains_file_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arrange: a path to a main xlsx file that does not exist on disk.
        Act: call get_file_paths with that path.
        Assert: FileNotFoundError message contains the exact missing file path.
        """
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        missing = str(tmp_path / "missing.xlsx")

        with pytest.raises(FileNotFoundError, match=re.escape(missing)):
            get_file_paths(missing)

    def test_course_file_error_contains_course_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Arrange: a valid xlsx file and a glob that reports a CSV not present on disk.
        Act: call get_file_paths with the xlsx path.
        Assert: FileNotFoundError message contains the missing CSV filename.
        """
        monkeypatch.chdir(tmp_path)
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        xlsx = tmp_path / "statement.xlsx"
        xlsx.touch()
        ghost = data_dir / "archiwum_tab_a_ghost.csv"

        with patch.object(Path, "glob", return_value=[ghost]):
            with pytest.raises(FileNotFoundError, match="archiwum_tab_a_ghost"):
                get_file_paths(str(xlsx))
