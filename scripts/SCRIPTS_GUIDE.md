# Scripts Guide

This guide documents utility scripts for CI/CD and security scanning in the XTB Dividend Analysis project.

## Available Scripts

### Security & CI Scripts

#### `bandit_to_sarif.py`
Converts Bandit JSON security reports to SARIF 2.1.0 format for GitHub Security integration.

**Usage:**
```bash
poetry run python scripts/bandit_to_sarif.py <bandit_json> <sarif_output>
```

**Features:**
- Modern Python 3.9+ with full type hints
- Modular architecture with helper functions
- Converts Bandit JSON to SARIF 2.1.0 format
- Maps severity levels (HIGH→error, MEDIUM→warning, LOW→note)
- Creates valid SARIF even on parsing errors
- Proper error handling with specific exceptions

**Implementation:**
- Uses `pathlib.Path` for file operations
- Type-annotated with `dict[str, Any]` patterns
- Structured docstrings (Args/Returns/Raises)
- Updates Bandit version metadata to 1.9.1

#### `security_summary.py`
Generates human-readable security scan summaries for GitHub Actions workflows.

**Usage:**
```bash
python scripts/security_summary.py <bandit_json>
```

**Features:**
- Modern Python with type hints and `Counter` from collections
- Displays scanned LOC and total issues
- Shows severity breakdown (High/Medium/Low)
- Lists top 3 most common issue types
- Graceful handling of missing/malformed reports
- Outputs to stderr for errors

## Quick Commands

```bash
# Run all tests locally
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=data_processing --cov=data_acquisition --cov=visualization --cov=config

# Run security scan and convert to SARIF
poetry run bandit -r data_processing data_acquisition visualization config -f json -o bandit-report.json
poetry run python scripts/bandit_to_sarif.py bandit-report.json bandit-results.sarif

# Generate security summary
python scripts/security_summary.py bandit-report.json

# Install pre-commit hooks
pre-commit install
```

## Technical Details


### Code Quality Standards
- Full type annotations using modern syntax (`dict[str, Any]`, not `Dict[str, Any]`)
- Structured docstrings with Args/Returns/Raises sections
- Specific exception handling (avoid bare `except Exception`)
- Prefer `pathlib.Path` over `open()`
- Use `collections.Counter` for frequency counting
- Error output to `sys.stderr`, normal output to `sys.stdout`

## Script Locations

- **Root level configs**: `tox.ini`, `.pre-commit-config.yaml`, `pyproject.toml`
- **Test files**: `tests/`
- **Documentation**: `docs/`
- **CI/Security scripts**: `scripts/`

## CI/CD Integration

These scripts are used automatically in the GitHub Actions CI pipeline (`.github/workflows/ci.yml`):

- `bandit_to_sarif.py` – converts security scan results for GitHub Security tab
- `security_summary.py` – generates workflow summary with security metrics

For local testing, use `poetry run pytest` directly or configure pre-commit hooks via `.pre-commit-config.yaml`.

