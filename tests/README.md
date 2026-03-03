# Tests

This directory contains all test suites for the dividend analysis pipeline. Tests follow the AAA pattern (Arrange, Act, Assert) and use pytest with multiple test markers for organization and selective execution.

## Quick start

Run all tests:

```bash
poetry run pytest
```

Run tests with coverage report:

```bash
poetry run pytest --cov=config --cov=data_processing --cov=data_acquisition --cov=visualization
```

Run tests by marker:

```bash
poetry run pytest -m unit          # Unit tests only
poetry run pytest -m integration   # Integration tests only
poetry run pytest -m property_based  # Property-based tests with Hypothesis
poetry run pytest -m security      # Security tests with Bandit
```

## Folder structure

- `conftest.py` — Shared pytest fixtures used across all test suites
- `test_unit/` — Unit tests with mocked external dependencies (file I/O, HTTP, Playwright)
- `test_integration/` — Integration tests using real DataFrames and file fixtures
- `test_security/` — Static security analysis tests (Bandit SARIF conversion, security summary)
- `property_based/` — Generative tests with Hypothesis for property verification

## Test conventions

Follow these conventions when writing new tests:

- **Naming**: `test_<unit>_<scenario>_<expected_outcome>`
- **Structure**: AAA pattern with blank lines between each section:
  ```python
  def test_column_normalizer_bilingual_columns_normalized_to_english():
      # Arrange
      df = pd.DataFrame({"Akcja PL": [1], "Akcja EN": [2]})

      # Act
      result = ColumnNormalizer(df).normalize_columns()

      # Assert
      assert list(result.columns) == ["Ticker"]
  ```
- **Markers**: Add appropriate pytest marker (`@pytest.mark.unit`, `@pytest.mark.integration`, etc.)
- **Mocking**: Use `unittest.mock.patch` or `MagicMock` for external I/O
- **Independence**: Each test must be fully independent; no shared mutable state
- **Fixtures**: Place shared fixtures in `conftest.py` or test-specific `conftest.py` files

## Running tests locally

Use make commands for common tasks:

```bash
make test              # Run full test suite
make test-cov          # Run with coverage report
make lint              # Run linters (flake8, black, isort, mypy)
make security          # Run bandit security scan
```

Or run individual test files:

```bash
poetry run pytest tests/test_unit/test_column_normalizer.py
poetry run pytest tests/test_integration/test_dataframe_processor.py -v
```

## Environment setup

Tests run in the configured Python environment (Python 3.12+). Install development dependencies:

```bash
poetry install
```

If you modify dependencies, regenerate the lock file:

```bash
poetry lock --no-update
```

## Coverage

Coverage reports are generated in `htmlcov/`. Open `htmlcov/index.html` in your browser to view detailed coverage by file and line.

Target coverage: 80%+ overall, enforced via CI/CD workflow.
