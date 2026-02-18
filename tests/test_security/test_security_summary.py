"""
Tests for security summary generator script.

This module tests the security_summary.py script following pytest best practices
and ensuring proper generation of security scan summaries for CI/CD pipelines.
"""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

# Add scripts directory to path before importing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from security_summary import (
    _format_severity_stats,
    _format_common_issues,
    generate_security_summary,
)


if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def sample_bandit_metrics() -> dict:
    """Provide sample Bandit metrics for testing.

    Returns:
        Dictionary with severity statistics
    """
    return {
        "loc": 1250,
        "SEVERITY.HIGH": 3,
        "SEVERITY.MEDIUM": 12,
        "SEVERITY.LOW": 5,
    }


@pytest.fixture
def sample_bandit_results() -> list[dict]:
    """Provide sample Bandit results for testing.

    Returns:
        List of Bandit findings
    """
    return [
        {"test_id": "B101", "issue_text": "Assert used"},
        {"test_id": "B105", "issue_text": "Hardcoded password"},
        {"test_id": "B101", "issue_text": "Assert used"},
        {"test_id": "B105", "issue_text": "Hardcoded password"},
        {"test_id": "B105", "issue_text": "Hardcoded password"},
        {"test_id": "B201", "issue_text": "Flask debug mode"},
    ]


@pytest.fixture
def complete_bandit_report(
    sample_bandit_metrics: dict, sample_bandit_results: list[dict]
) -> dict:
    """Provide a complete Bandit report.

    Args:
        sample_bandit_metrics: Metrics fixture
        sample_bandit_results: Results fixture

    Returns:
        Complete Bandit JSON report structure
    """
    return {
        "metrics": {"_totals": sample_bandit_metrics},
        "results": sample_bandit_results,
    }


@pytest.fixture
def temp_bandit_report(tmp_path: Path, complete_bandit_report: dict) -> Path:
    """Create temporary Bandit JSON report file.

    Args:
        tmp_path: pytest temporary directory
        complete_bandit_report: Complete report data

    Returns:
        Path to temporary report file
    """
    report_file = tmp_path / "bandit-report.json"
    report_file.write_text(json.dumps(complete_bandit_report, indent=2))
    return report_file


@pytest.mark.security
class TestSeverityFormatting:
    """Test severity statistics formatting."""

    def test_format_severity_stats_prints_all_levels(
        self, sample_bandit_metrics: dict, capsys
    ) -> None:
        """Test that all severity levels are printed.

        Args:
            sample_bandit_metrics: Sample metrics data
            capsys: pytest capture fixture
        """
        _format_severity_stats(sample_bandit_metrics)

        captured = capsys.readouterr()
        assert "High Severity" in captured.out
        assert "Medium Severity" in captured.out
        assert "Low Severity" in captured.out

    def test_format_severity_stats_shows_correct_counts(
        self, sample_bandit_metrics: dict, capsys
    ) -> None:
        """Test that correct counts are displayed.

        Args:
            sample_bandit_metrics: Sample metrics data
            capsys: pytest capture fixture
        """
        _format_severity_stats(sample_bandit_metrics)

        captured = capsys.readouterr()
        assert "**High Severity**: 3" in captured.out
        assert "**Medium Severity**: 12" in captured.out
        assert "**Low Severity**: 5" in captured.out

    def test_format_severity_stats_handles_missing_severities(self, capsys) -> None:
        """Test that missing severity levels default to 0."""
        metrics = {}  # Empty metrics

        _format_severity_stats(metrics)

        captured = capsys.readouterr()
        assert "**High Severity**: 0" in captured.out
        assert "**Medium Severity**: 0" in captured.out
        assert "**Low Severity**: 0" in captured.out


@pytest.mark.security
class TestCommonIssuesFormatting:
    """Test common issues formatting."""

    def test_format_common_issues_shows_top_issues(
        self, sample_bandit_results: list[dict], capsys
    ) -> None:
        """Test that most common issues are displayed.

        Args:
            sample_bandit_results: Sample results
            capsys: pytest capture fixture
        """
        _format_common_issues(sample_bandit_results, top_n=3)

        captured = capsys.readouterr()
        assert "Most Common Issues" in captured.out
        assert "B105" in captured.out  # 3 occurrences
        assert "B101" in captured.out  # 2 occurrences

    def test_format_common_issues_shows_counts(
        self, sample_bandit_results: list[dict], capsys
    ) -> None:
        """Test that issue counts are displayed.

        Args:
            sample_bandit_results: Sample results
            capsys: pytest capture fixture
        """
        _format_common_issues(sample_bandit_results, top_n=3)

        captured = capsys.readouterr()
        assert "B105: 3" in captured.out
        assert "B101: 2" in captured.out
        assert "B201: 1" in captured.out

    def test_format_common_issues_limits_to_top_n(
        self, sample_bandit_results: list[dict], capsys
    ) -> None:
        """Test that only top N issues are shown.

        Args:
            sample_bandit_results: Sample results
            capsys: pytest capture fixture
        """
        _format_common_issues(sample_bandit_results, top_n=2)

        captured = capsys.readouterr()
        lines = [line for line in captured.out.split(
            '\n') if line.strip().startswith('- B')]

        # Should show only top 2 issues
        assert len(lines) == 2

    def test_format_common_issues_handles_empty_results(self, capsys) -> None:
        """Test formatting with empty results."""
        _format_common_issues([], top_n=3)

        captured = capsys.readouterr()
        # Should not print anything for empty results
        assert "Most Common Issues" not in captured.out

    def test_format_common_issues_handles_missing_test_id(self, capsys) -> None:
        """Test handling of results without test_id."""
        results = [{"issue_text": "Some issue"}]

        _format_common_issues(results, top_n=3)

        captured = capsys.readouterr()
        assert "unknown" in captured.out


@pytest.mark.security
class TestSecuritySummaryGeneration:
    """Test complete security summary generation."""

    def test_generate_security_summary_shows_lines_scanned(
        self, temp_bandit_report: Path, capsys
    ) -> None:
        """Test that LOC scanned is displayed.

        Args:
            temp_bandit_report: Temporary report file
            capsys: pytest capture fixture
        """
        generate_security_summary(str(temp_bandit_report))

        captured = capsys.readouterr()
        assert "Lines of Code Scanned" in captured.out
        assert "1,250" in captured.out

    def test_generate_security_summary_shows_total_issues(
        self, temp_bandit_report: Path, capsys
    ) -> None:
        """Test that total issues count is displayed.

        Args:
            temp_bandit_report: Temporary report file
            capsys: pytest capture fixture
        """
        generate_security_summary(str(temp_bandit_report))

        captured = capsys.readouterr()
        assert "Total Security Issues" in captured.out
        assert "6" in captured.out  # 6 results in sample

    def test_generate_security_summary_shows_severity_breakdown(
        self, temp_bandit_report: Path, capsys
    ) -> None:
        """Test that severity breakdown is included.

        Args:
            temp_bandit_report: Temporary report file
            capsys: pytest capture fixture
        """
        generate_security_summary(str(temp_bandit_report))

        captured = capsys.readouterr()
        assert "High Severity" in captured.out
        assert "Medium Severity" in captured.out
        assert "Low Severity" in captured.out

    def test_generate_security_summary_shows_common_issues(
        self, temp_bandit_report: Path, capsys
    ) -> None:
        """Test that common issues are listed.

        Args:
            temp_bandit_report: Temporary report file
            capsys: pytest capture fixture
        """
        generate_security_summary(str(temp_bandit_report))

        captured = capsys.readouterr()
        assert "Most Common Issues" in captured.out
        assert "B105" in captured.out
        assert "B101" in captured.out


@pytest.mark.security
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_generate_security_summary_handles_missing_file(
        self, tmp_path: Path, capsys
    ) -> None:
        """Test handling when report file doesn't exist.

        Args:
            tmp_path: Temporary directory
            capsys: pytest capture fixture
        """
        nonexistent = tmp_path / "nonexistent.json"

        generate_security_summary(str(nonexistent))

        captured = capsys.readouterr()
        assert "No report file found" in captured.out

    def test_generate_security_summary_handles_invalid_json(
        self, tmp_path: Path, capsys
    ) -> None:
        """Test handling of malformed JSON.

        Args:
            tmp_path: Temporary directory
            capsys: pytest capture fixture
        """
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{ invalid json }")

        generate_security_summary(str(invalid_json))

        captured = capsys.readouterr()
        assert "Error" in captured.err or "Could not parse" in captured.out

    def test_generate_security_summary_handles_empty_results(
        self, tmp_path: Path, capsys
    ) -> None:
        """Test summary when no issues are found.

        Args:
            tmp_path: Temporary directory
            capsys: pytest capture fixture
        """
        clean_report = tmp_path / "clean.json"
        clean_report.write_text(json.dumps({
            "metrics": {"_totals": {"loc": 500}},
            "results": []
        }))

        generate_security_summary(str(clean_report))

        captured = capsys.readouterr()
        assert "Total Security Issues" in captured.out
        assert "0" in captured.out
        assert "No security issues found" in captured.out or "🎉" in captured.out

    def test_generate_security_summary_handles_missing_metrics(
        self, tmp_path: Path, capsys
    ) -> None:
        """Test handling when metrics are missing.

        Args:
            tmp_path: Temporary directory
            capsys: pytest capture fixture
        """
        minimal_report = tmp_path / "minimal.json"
        minimal_report.write_text(json.dumps({
            "results": []
        }))

        # Should not crash
        generate_security_summary(str(minimal_report))

        captured = capsys.readouterr()
        assert "Lines of Code Scanned" in captured.out


@pytest.mark.security
class TestIntegrationWithBandit:
    """Integration tests with actual Bandit report structure."""

    def test_summary_matches_bandit_report_structure(
        self, temp_bandit_report: Path, capsys
    ) -> None:
        """Test that summary correctly parses real Bandit report structure.

        Args:
            temp_bandit_report: Temporary report file
            capsys: pytest capture fixture
        """
        # Read the report to verify structure
        report_data = json.loads(temp_bandit_report.read_text())

        generate_security_summary(str(temp_bandit_report))

        captured = capsys.readouterr()

        # Verify metrics are correctly extracted
        expected_loc = report_data["metrics"]["_totals"]["loc"]
        assert str(expected_loc) in captured.out.replace(",", "")

        # Verify results count
        expected_issues = len(report_data["results"])
        assert str(expected_issues) in captured.out
