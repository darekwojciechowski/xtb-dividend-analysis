#!/usr/bin/env python3
"""Generate security scan summary for GitHub Actions."""

import json
import sys
from pathlib import Path


def generate_security_summary(bandit_json_path: str) -> None:
    """Generate a security summary from bandit JSON output."""
    try:
        if not Path(bandit_json_path).exists():
            print("- **Bandit scan**: No report file found")
            return

        with open(bandit_json_path) as f:
            data = json.load(f)

        metrics = data.get('metrics', {}).get('_totals', {})
        total_lines = metrics.get('loc', 0)
        total_issues = len(data.get('results', []))
        high_severity = metrics.get('SEVERITY.HIGH', 0)
        medium_severity = metrics.get('SEVERITY.MEDIUM', 0)
        low_severity = metrics.get('SEVERITY.LOW', 0)

        print(f"- **Lines of Code Scanned**: {total_lines:,}")
        print(f"- **Total Security Issues**: {total_issues}")

        if total_issues > 0:
            print(f"- **High Severity**: {high_severity}")
            print(f"- **Medium Severity**: {medium_severity}")
            print(f"- **Low Severity**: {low_severity}")

            # Show most common issues
            issue_types = {}
            for result in data.get('results', []):
                test_id = result.get('test_id', 'unknown')
                issue_types[test_id] = issue_types.get(test_id, 0) + 1

            if issue_types:
                print("- **Most Common Issues**:")
                for test_id, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:3]:
                    print(f"  - {test_id}: {count}")
        else:
            print("- **Result**: No security issues found! 🎉")

    except Exception as e:
        print(f"- **Error**: Could not parse bandit report: {e}")


if __name__ == "__main__":
    bandit_json_path = sys.argv[1] if len(sys.argv) > 1 else "bandit-report.json"
    generate_security_summary(bandit_json_path)
