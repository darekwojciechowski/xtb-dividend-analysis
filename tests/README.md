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
- `metamorphic/` — Metamorphic relation tests: no oracle needed — tests assert invariants that must hold between a base run and a transformed run (e.g. permuted, scaled, split input). Run with `-m metamorphic`.

## Test conventions

Follow these conventions when writing new tests:

- **Naming**: `test_<unit>_<scenario>_<expected_outcome>`
- **Structure**: AAA pattern with blank lines between each section:
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

## Mutation testing

Mutation tests use [mutmut](https://mutmut.readthedocs.io/) to verify that the test suite actually catches logic errors. Mutmut introduces small code changes (mutations) and checks whether at least one test fails for each one.

Run mutation testing:

```bash
poetry run mutmut run
```

View results after the run completes:

```bash
poetry run mutmut results                # All results
poetry run mutmut show 1                 # Diff for a specific mutant
```

Run mutations against a single file to speed things up:

```bash
poetry run mutmut run --paths-to-mutate data_processing/tax_calculator.py
```

Configuration in `pyproject.toml` (`[tool.mutmut]`):
- **Mutates:** `data_processing/` (excluding `import_data_xlsx.py`, `data_aggregator.py`, `constants.py`, `file_paths.py`)
- **Tests used:** `tests/test_unit/`
- Property-based and slow tests are excluded from each mutation run for speed

Results are cached in `.mutmut-cache` (SQLite). Delete this file to force a full re-run.
