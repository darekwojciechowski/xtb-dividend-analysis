#!/usr/bin/env python3
"""Generate security scan summary for GitHub Actions.

This script parses Bandit JSON reports and generates human-readable
summaries suitable for GitHub Actions workflow summaries.
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger


def _format_severity_stats(metrics: dict[str, Any]) -> None:
    """Print severity breakdown.

    Args:
        metrics: Bandit metrics dictionary with severity counts
    """
    severities = [
        ("High", metrics.get('SEVERITY.HIGH', 0)),
        ("Medium", metrics.get('SEVERITY.MEDIUM', 0)),
        ("Low", metrics.get('SEVERITY.LOW', 0))
    ]

    for name, count in severities:
        logger.info(f"- **{name} Severity**: {count}")


def _format_common_issues(results: list[dict[str, Any]], top_n: int = 3) -> None:
    """Print most common issue types.

    Args:
        results: List of bandit results
        top_n: Number of top issues to display
    """
    issue_types = Counter(
        result.get('test_id', 'unknown')
        for result in results
    )

    if issue_types:
        logger.info("- **Most Common Issues**:")
        for test_id, count in issue_types.most_common(top_n):
            logger.info(f"  - {test_id}: {count}")


def generate_security_summary(bandit_json_path: str) -> None:
    """Generate a security summary from bandit JSON output.

    Args:
        bandit_json_path: Path to bandit JSON report

    Prints:
        Markdown-formatted summary to stdout
    """
    report_path = Path(bandit_json_path)

    if not report_path.exists():
        logger.info("- **Bandit scan**: No report file found")
        return

    try:
        with report_path.open() as f:
            data = json.load(f)

        metrics = data.get('metrics', {}).get('_totals', {})
        results = data.get('results', [])

        total_lines = metrics.get('loc', 0)
        total_issues = len(results)

        logger.info(f"- **Lines of Code Scanned**: {total_lines:,}")
        logger.info(f"- **Total Security Issues**: {total_issues}")

        if total_issues > 0:
            _format_severity_stats(metrics)
            _format_common_issues(results)
        else:
            logger.info("- **Result**: No security issues found! 🎉")

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"- **Error**: Could not parse bandit report: {e}")


if __name__ == "__main__":
    bandit_json_path = sys.argv[1] if len(sys.argv) > 1 else "bandit-report.json"
    generate_security_summary(bandit_json_path)
