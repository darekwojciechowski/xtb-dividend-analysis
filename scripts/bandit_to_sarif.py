#!/usr/bin/env python3
"""Convert bandit JSON output to SARIF format for GitHub Security."""

import json
import sys
from pathlib import Path


def convert_bandit_to_sarif(bandit_json_path: str, sarif_output_path: str) -> None:
    """Convert bandit JSON report to SARIF format."""
    try:
        with open(bandit_json_path) as f:
            bandit_data = json.load(f)

        # Create SARIF structure
        sarif = {
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "bandit",
                        "version": "1.8.5",
                        "informationUri": "https://bandit.readthedocs.io/",
                        "shortDescription": {"text": "Security linter for Python"},
                        "fullDescription": {"text": "Bandit is a tool designed to find common security issues in Python code."}
                    }
                },
                "results": []
            }]
        }

        # Convert bandit results to SARIF format
        for result in bandit_data.get("results", []):
            severity_map = {
                "LOW": "note",
                "MEDIUM": "warning",
                "HIGH": "error"
            }

            sarif_result = {
                "ruleId": result.get("test_id", "unknown"),
                "ruleIndex": 0,
                "message": {
                    "text": result.get("issue_text", "Security issue detected")
                },
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": result.get("filename", "unknown").replace("\\", "/")
                        },
                        "region": {
                            "startLine": result.get("line_number", 1),
                            "startColumn": 1
                        }
                    }
                }],
                "level": severity_map.get(result.get("issue_severity", "LOW"), "note"),
                "partialFingerprints": {
                    "primaryLocationLineHash": f"{result.get('filename', '')}:{result.get('line_number', 0)}"
                }
            }
            sarif["runs"][0]["results"].append(sarif_result)

        # Write SARIF file
        with open(sarif_output_path, "w") as f:
            json.dump(sarif, f, indent=2)

        print(
            f"Successfully converted {len(sarif['runs'][0]['results'])} issues to SARIF format")

    except Exception as e:
        print(f"Error converting bandit to SARIF: {e}")
        # Create minimal valid SARIF file
        minimal_sarif = {
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "bandit"
                    }
                },
                "results": []
            }]
        }
        with open(sarif_output_path, "w") as f:
            json.dump(minimal_sarif, f, indent=2)


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
