# Testing Guide

This project uses comprehensive automated testing with pytest, tox, and GitHub Actions.

## Quick Start

### Installing Dependencies

First, ensure Poetry is installed and dependencies are ready:
```bash
pip install poetry
poetry install --with dev
```

### Running Tests Locally

**Option 1: Using the test runner script**
```bash
# Python script (cross-platform)
poetry run python scripts/run_tests.py

# PowerShell script (Windows)
.\scripts\run_tests.ps1
```

**Option 2: Direct pytest commands**
```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=data_processing --cov=data_acquisition --cov=visualization --cov=config --cov-report=term-missing

# Run specific test file
poetry run pytest tests/test_dataframe_processor.py -v

# Run tests in verbose mode
poetry run pytest -v
```

**Option 3: Using Make (if available)**
```bash
make test          # Run all tests
make test-cov      # Run tests with coverage
make test-fast     # Run tests without coverage
make lint          # Run code quality checks
make format        # Format code
make all           # Run everything
```

## Testing Framework

### Pytest Configuration
- Configuration in `pyproject.toml`
- Test discovery: `tests/test_*.py`
- Coverage reporting for all main modules
- HTML and XML coverage reports generated

### Test Structure
```
tests/
├── __init__.py
├── test_main.py                    # Main functionality tests
├── test_dataframe_processor.py     # DataFrame processing tests
├── test_date_converter.py          # Date conversion tests
└── test_exporter.py               # Export functionality tests
```

### Tox Testing
Run tests across multiple Python versions:
```bash
# Install tox
pip install tox

# Run tests on all Python versions
tox

# Run tests on specific Python version
tox -e py312

# Run linting only
tox -e lint

# Run coverage only
tox -e coverage
```

## Continuous Integration

### GitHub Actions Workflows

**1. Fast Tests (`fast-tests.yml`)**
- Triggered on every push and PR
- Runs basic tests on Python 3.12
- Quick feedback for developers

**2. Full CI Pipeline (`ci.yml`)**
- Runs on main branches and PRs
- Tests multiple Python versions (3.9-3.13)
- Tests multiple operating systems (Ubuntu, Windows, macOS)
- Includes linting, security scans, and coverage reporting

### Automated Checks
Every commit triggers:
- ✅ Unit tests across multiple Python versions
- ✅ Code quality checks (flake8, black, isort)
- ✅ Type checking (mypy)
- ✅ Security scanning (safety, bandit)
- ✅ Coverage reporting

## Pre-commit Hooks

Set up pre-commit hooks to run tests before each commit:

```bash
# Install pre-commit
pip install pre-commit

# Set up the git hook scripts
pre-commit install

# Run against all files (optional)
pre-commit run --all-files
```

This will automatically run:
- Code formatting (black, isort)
- Linting (flake8)
- Basic file checks
- Tests (pytest)

## Code Coverage

### Viewing Coverage Reports

**Terminal output:**
```bash
pytest --cov=data_processing --cov-report=term-missing
```

**HTML report:**
```bash
pytest --cov=data_processing --cov-report=html
# Open htmlcov/index.html in browser
```

**XML report (for CI):**
```bash
pytest --cov=data_processing --cov-report=xml
```

### Coverage Configuration
- Minimum coverage thresholds can be set in `pyproject.toml`
- Excludes test files and cache directories
- Reports missing lines for easy identification

## Writing Tests

### Test Conventions
- Test files: `test_*.py`
- Test functions: `test_*`
- Use fixtures for common test data
- Mock external dependencies
- Test both success and failure cases

### Example Test Structure
```python
import pytest
from unittest.mock import MagicMock
from your_module import YourClass

@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_your_function(sample_data):
    # Arrange
    expected = "expected_result"
    
    # Act
    result = your_function(sample_data)
    
    # Assert
    assert result == expected
```

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Make sure you're in the project root
cd /path/to/xtb-dividend-analysis

# Check Python path
python -c "import sys; print(sys.path)"
```

**2. Missing Dependencies**
```bash
# Install all dependencies
poetry install --with dev
```

**3. Playwright Issues**
```bash
# Install Playwright browsers
playwright install
```

### Debug Mode
Run tests in debug mode:
```bash
pytest --pdb  # Drop into debugger on failures
pytest -s     # Don't capture output
pytest -v     # Verbose output
```

## Integration with IDEs

### VS Code
Add to `.vscode/settings.json`:
```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.testing.autoTestDiscoverOnSaveEnabled": true
}
```

### PyCharm
- Right-click on `tests` folder → "Run 'pytest in tests'"
- Configure run configuration for pytest
- Enable coverage in run configuration

## Performance Testing

For large datasets or performance-critical code:
```bash
# Run with timing
pytest --durations=10

# Profile test execution
pip install pytest-profiling
pytest --profile
```
