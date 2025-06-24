# Scripts Guide

This guide documents all utility scripts for testing, development, and project maintenance in the XTB Dividend Analysis project.

## Available Scripts

### Testing Scripts

#### `run_tests.py`
Cross-platform Python script to run the complete test suite.

**Usage:**
```bash
python scripts/run_tests.py
```

**Features:**
- Runs all tests with coverage reporting
- Validates module imports
- Provides detailed test summary
- Works on Windows, macOS, and Linux

#### `run_tests.ps1`
PowerShell script optimized for Windows environments.

**Usage:**
```powershell
.\scripts\run_tests.ps1
```

**Features:**
- Windows-optimized test execution
- Colored output for better readability
- Error handling and reporting
- Coverage analysis

### Development Scripts

#### `pre-commit-hook-example.sh`
Example git pre-commit hook that runs tests before allowing commits.

**Installation:**
```bash
# Option 1: Copy to git hooks (manual)
cp scripts/pre-commit-hook-example.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Option 2: Use pre-commit framework (recommended)
pip install pre-commit
pre-commit install
```

**Features:**
- Runs tests before each commit
- Prevents commits if tests fail
- Fast feedback for developers
- Integrates with git workflow

## Quick Commands

```bash
# Run all tests
python scripts/run_tests.py

# Run tests on Windows
.\scripts\run_tests.ps1

# Run specific test file
python -m pytest tests/test_dataframe_processor.py

# Run with coverage
python -m pytest --cov=data_processing --cov-report=html

# Install pre-commit hooks
pre-commit install
```

## Script Locations

- **Root level configs**: `tox.ini`, `.pre-commit-config.yaml`, `pyproject.toml`
- **Test files**: `tests/`
- **Documentation**: `docs/`
- **Utility scripts**: `scripts/` (this directory)

## Integration with IDEs

These scripts can be integrated with various IDEs:

### VS Code
Add to your `tasks.json`:
```json
{
    "label": "Run Tests",
    "type": "shell",
    "command": "python",
    "args": ["scripts/run_tests.py"],
    "group": "test"
}
```

### PyCharm
Configure external tools:
- Tool: `Run Tests`
- Command: `python`
- Arguments: `scripts/run_tests.py`
- Working directory: `$ProjectFileDir$`
