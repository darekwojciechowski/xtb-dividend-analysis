"""
Tests for Bandit to SARIF converter script.

This module tests the bandit_to_sarif.py script following pytest best practices
and ensuring proper conversion of security scan results to SARIF 2.1.0 format.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# Add scripts directory to path before importing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from bandit_to_sarif import (
    _map_severity,
    _create_sarif_structure,
    _convert_result,
    convert_bandit_to_sarif,
)


if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def sample_bandit_result() -> dict:
    """Provide a sample Bandit result for testing.

    Returns:
        Dictionary representing a typical Bandit finding
    """
    return {
        "filename": "test_file.py",
        "line_number": 42,
        "test_id": "B101",
        "issue_text": "Use of assert detected",
        "issue_severity": "HIGH",
    }


@pytest.fixture
def sample_bandit_report() -> dict:
    """Provide a complete sample Bandit JSON report.

    Returns:
        Dictionary representing a full Bandit scan report
    """
    return {
        "results": [
            {
                "filename": "app.py",
                "line_number": 10,
                "test_id": "B101",
                "issue_text": "Use of assert detected",
                "issue_severity": "HIGH",
            },
            {
                "filename": "config.py",
                "line_number": 25,
                "test_id": "B105",
                "issue_text": "Possible hardcoded password",
                "issue_severity": "MEDIUM",
            },
        ],
        "metrics": {"_totals": {"loc": 150, "nosec": 0}},
    }


@pytest.fixture
def temp_bandit_json(tmp_path: Path, sample_bandit_report: dict) -> Path:
    """Create a temporary Bandit JSON file.

    Args:
        tmp_path: pytest's temporary path fixture
        sample_bandit_report: Sample report data

    Returns:
        Path to the temporary JSON file
    """
    json_file = tmp_path / "bandit-report.json"
    json_file.write_text(json.dumps(sample_bandit_report, indent=2))
    return json_file


@pytest.mark.security
class TestSeverityMapping:
    """Test severity level mapping from Bandit to SARIF."""

    @pytest.mark.parametrize("bandit_severity,expected_sarif_level", [
        ("HIGH", "error"),
        ("MEDIUM", "warning"),
        ("LOW", "note"),
        ("UNKNOWN", "note"),  # Default case
    ])
    def test_map_severity_returns_correct_level(
        self, bandit_severity: str, expected_sarif_level: str
    ) -> None:
        """Test that Bandit severity maps to correct SARIF level.

        Args:
            bandit_severity: Bandit severity string
            expected_sarif_level: Expected SARIF level
        """
        assert _map_severity(bandit_severity) == expected_sarif_level


@pytest.mark.security
class TestSARIFStructure:
    """Test SARIF structure creation and validation."""

    def test_create_sarif_structure_returns_valid_schema(self) -> None:
        """Test that base SARIF structure has required fields."""
        sarif = _create_sarif_structure()

        # Verify SARIF 2.1.0 schema
        assert sarif["version"] == "2.1.0"
        assert "$schema" in sarif
        assert "runs" in sarif
        assert len(sarif["runs"]) == 1

    def test_create_sarif_structure_has_tool_metadata(self) -> None:
        """Test that SARIF structure includes tool information."""
        sarif = _create_sarif_structure()

        tool = sarif["runs"][0]["tool"]["driver"]
        assert tool["name"] == "bandit"
        assert "version" in tool
        assert "informationUri" in tool
        assert tool["informationUri"] == "https://bandit.readthedocs.io/"

    def test_create_sarif_structure_has_empty_results(self) -> None:
        """Test that SARIF structure initializes with empty results array."""
        sarif = _create_sarif_structure()

        assert sarif["runs"][0]["results"] == []


@pytest.mark.security
class TestResultConversion:
    """Test conversion of individual Bandit results to SARIF format."""

    def test_convert_result_creates_valid_sarif_result(
        self, sample_bandit_result: dict
    ) -> None:
        """Test that Bandit result converts to valid SARIF result.

        Args:
            sample_bandit_result: Sample Bandit finding
        """
        sarif_result = _convert_result(sample_bandit_result)

        # Verify required SARIF result fields
        assert sarif_result["ruleId"] == "B101"
        assert sarif_result["message"]["text"] == "Use of assert detected"
        assert sarif_result["level"] == "error"

    def test_convert_result_creates_location_info(
        self, sample_bandit_result: dict
    ) -> None:
        """Test that SARIF result includes location information.

        Args:
            sample_bandit_result: Sample Bandit finding
        """
        sarif_result = _convert_result(sample_bandit_result)

        location = sarif_result["locations"][0]["physicalLocation"]
        assert location["artifactLocation"]["uri"] == "test_file.py"
        assert location["region"]["startLine"] == 42
        assert location["region"]["startColumn"] == 1

    def test_convert_result_handles_windows_paths(self) -> None:
        """Test that Windows backslashes are converted to forward slashes."""
        windows_result = {
            "filename": "src\\app\\main.py",
            "line_number": 10,
            "test_id": "B101",
            "issue_text": "Issue",
            "issue_severity": "LOW",
        }

        sarif_result = _convert_result(windows_result)
        uri = sarif_result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]

        assert "\\" not in uri
        assert uri == "src/app/main.py"

    def test_convert_result_handles_missing_fields(self) -> None:
        """Test that converter handles missing optional fields gracefully."""
        minimal_result = {}

        sarif_result = _convert_result(minimal_result)

        # Should use default values
        assert sarif_result["ruleId"] == "unknown"
        assert sarif_result["message"]["text"] == "Security issue detected"
        assert sarif_result["level"] == "note"


@pytest.mark.security
class TestFullConversion:
    """Test complete Bandit to SARIF conversion workflow."""

    def test_convert_bandit_to_sarif_creates_valid_file(
        self, temp_bandit_json: Path, tmp_path: Path
    ) -> None:
        """Test that conversion creates valid SARIF file.

        Args:
            temp_bandit_json: Temporary Bandit JSON file
            tmp_path: Temporary directory
        """
        sarif_output = tmp_path / "results.sarif"

        convert_bandit_to_sarif(str(temp_bandit_json), str(sarif_output))

        # Verify file was created
        assert sarif_output.exists()

        # Verify content is valid JSON
        sarif_data = json.loads(sarif_output.read_text())
        assert sarif_data["version"] == "2.1.0"

    def test_convert_bandit_to_sarif_converts_all_results(
        self, temp_bandit_json: Path, tmp_path: Path
    ) -> None:
        """Test that all Bandit results are converted.

        Args:
            temp_bandit_json: Temporary Bandit JSON file
            tmp_path: Temporary directory
        """
        sarif_output = tmp_path / "results.sarif"

        convert_bandit_to_sarif(str(temp_bandit_json), str(sarif_output))

        sarif_data = json.loads(sarif_output.read_text())
        results = sarif_data["runs"][0]["results"]

        # Should have 2 results from sample report
        assert len(results) == 2
        assert results[0]["ruleId"] == "B101"
        assert results[1]["ruleId"] == "B105"

    def test_convert_bandit_to_sarif_maps_severity_correctly(
        self, temp_bandit_json: Path, tmp_path: Path
    ) -> None:
        """Test that severity levels are mapped correctly.

        Args:
            temp_bandit_json: Temporary Bandit JSON file
            tmp_path: Temporary directory
        """
        sarif_output = tmp_path / "results.sarif"

        convert_bandit_to_sarif(str(temp_bandit_json), str(sarif_output))

        sarif_data = json.loads(sarif_output.read_text())
        results = sarif_data["runs"][0]["results"]

        # First result: HIGH -> error
        assert results[0]["level"] == "error"
        # Second result: MEDIUM -> warning
        assert results[1]["level"] == "warning"


@pytest.mark.security
class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_convert_raises_error_for_missing_file(self, tmp_path: Path) -> None:
        """Test that converter raises FileNotFoundError for missing input."""
        nonexistent = tmp_path / "nonexistent.json"
        output = tmp_path / "output.sarif"

        with pytest.raises(FileNotFoundError):
            convert_bandit_to_sarif(str(nonexistent), str(output))

    def test_convert_raises_error_for_invalid_json(self, tmp_path: Path) -> None:
        """Test that converter raises JSONDecodeError for invalid JSON."""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{ invalid json }")
        output = tmp_path / "output.sarif"

        with pytest.raises(json.JSONDecodeError):
            convert_bandit_to_sarif(str(invalid_json), str(output))

    def test_convert_creates_minimal_sarif_on_error(self, tmp_path: Path) -> None:
        """Test that minimal valid SARIF is created even on error."""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{ invalid }")
        output = tmp_path / "output.sarif"

        try:
            convert_bandit_to_sarif(str(invalid_json), str(output))
        except json.JSONDecodeError:
            pass

        # Should still create valid minimal SARIF
        assert output.exists()
        sarif_data = json.loads(output.read_text())
        assert sarif_data["version"] == "2.1.0"
        assert sarif_data["runs"][0]["results"] == []

    def test_convert_handles_empty_results(self, tmp_path: Path) -> None:
        """Test conversion with empty results array."""
        empty_report = tmp_path / "empty.json"
        empty_report.write_text(json.dumps({"results": []}))
        output = tmp_path / "output.sarif"

        convert_bandit_to_sarif(str(empty_report), str(output))

        sarif_data = json.loads(output.read_text())
        assert sarif_data["runs"][0]["results"] == []
