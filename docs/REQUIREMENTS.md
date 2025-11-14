# Dependency Management

Project uses **Poetry** for dependency management.

## Installation

```bash
# Install Poetry
pip install poetry

# Install all dependencies
poetry install

# Production only
poetry install --only main
```

## Usage

```bash
# Run script
poetry run python main.py

# Run tests
poetry run pytest

# Add package
poetry add pandas

# Add dev package
poetry add --group dev pytest
```

## Dependencies

**Production** (`[project.dependencies]`):
- pandas, numpy, matplotlib, openpyxl

**Development** (`[tool.poetry.group.dev.dependencies]`):
- pytest, pytest-cov, flake8, black, isort, mypy, safety, bandit, tox
