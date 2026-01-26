#!/usr/bin/env python3
"""Convert bandit JSON output to SARIF format for GitHub Security.

This script converts Bandit security scan results to the SARIF 2.1.0 format,
enabling integration with GitHub Security Code Scanning alerts.
"""

import json
import sys
from pathlib import Path
from typing import Any


def _map_severity(severity: str) -> str:
    """Map bandit severity to SARIF level.

    Args:
        severity: Bandit severity level (LOW, MEDIUM, HIGH)

    Returns:
        SARIF level (note, warning, error)
    """
    severity_map = {"HIGH": "error", "MEDIUM": "warning", "LOW": "note"}
    return severity_map.get(severity, "note")


def _create_sarif_structure() -> dict[str, Any]:
    """Create base SARIF 2.1.0 structure.

    Returns:
        Base SARIF dictionary with tool metadata
    """
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "bandit",
                    "version": "1.9.1",
                    "informationUri": "https://bandit.readthedocs.io/",
                    "shortDescription": {"text": "Security linter for Python"},
                    "fullDescription": {
                        "text": "Bandit is a tool designed to find common security issues in Python code."
                    }
                }
            },
            "results": []
        }]
    }


def _convert_result(result: dict[str, Any]) -> dict[str, Any]:
    """Convert a single bandit result to SARIF format.

    Args:
        result: Bandit result dictionary

    Returns:
        SARIF-formatted result
    """
    filename = result.get("filename", "unknown").replace("\\", "/")
    line_number = result.get("line_number", 1)

    return {
        "ruleId": result.get("test_id", "unknown"),
        "ruleIndex": 0,
        "message": {
            "text": result.get("issue_text", "Security issue detected")
        },
        "locations": [{
            "physicalLocation": {
                "artifactLocation": {"uri": filename},
                "region": {
                    "startLine": line_number,
                    "startColumn": 1
                }
            }
        }],
        "level": _map_severity(result.get("issue_severity", "LOW")),
        "partialFingerprints": {
            "primaryLocationLineHash": f"{filename}:{line_number}"
        }
    }


def convert_bandit_to_sarif(bandit_json_path: str, sarif_output_path: str) -> None:
    """Convert bandit JSON report to SARIF format.

    Args:
        bandit_json_path: Path to bandit JSON report
        sarif_output_path: Path where SARIF file will be written

    Raises:
        FileNotFoundError: If bandit JSON file doesn't exist
        json.JSONDecodeError: If bandit JSON is malformed
    """
    try:
        with Path(bandit_json_path).open() as f:
            bandit_data = json.load(f)

        sarif = _create_sarif_structure()

        # Convert all bandit results
        for result in bandit_data.get("results", []):
            sarif["runs"][0]["results"].append(_convert_result(result))

        # Write SARIF file
        with Path(sarif_output_path).open("w") as f:
            json.dump(sarif, f, indent=2)

        issue_count = len(sarif["runs"][0]["results"])
        print(
            f"Successfully converted {issue_count} issue{'s' if issue_count != 1 else ''} to SARIF format")

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error converting bandit to SARIF: {e}", file=sys.stderr)
        # Create minimal valid SARIF file
        minimal_sarif = _create_sarif_structure()
        with Path(sarif_output_path).open("w") as f:
            json.dump(minimal_sarif, f, indent=2)
        raise


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python bandit_to_sarif.py <bandit_json> <sarif_output>")
        sys.exit(1)

    bandit_json_path = sys.argv[1]
    sarif_output_path = sys.argv[2]

    if not Path(bandit_json_path).exists():
        print(f"Error: Bandit JSON file not found: {bandit_json_path}")
        sys.exit(1)

    convert_bandit_to_sarif(bandit_json_path, sarif_output_path)
