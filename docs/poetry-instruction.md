# Poetry Instructions for Project Setup

Poetry is a dependency management and packaging tool for Python. It helps manage your project's dependencies, virtual environments, and packaging. Follow these steps to get started with Poetry:

## Step 1: Install Poetry

**MacOS** Install Poetry: Use Homebrew to install Poetry by running the following command:

```bash
brew install poetry
```

Alternatively, if you're on **Windows**, you can use:

```bash
pip install poetry
```

## Step 2: Navigate to Project Directory

Navigate to your project directory:

```bash
cd xtb-dividend-analysis
```

## Step 3: Install Project Dependencies

Install all dependencies defined in `pyproject.toml`:

```bash
poetry install
```

This will create a virtual environment and install:
- **Core dependencies**: `pandas`, `numpy`, `matplotlib`, `openpyxl`, `playwright`, `tabulate`, `loguru`
- **Dev dependencies**: `pytest`, `pytest-cov`, `black`, `isort`, `flake8`, `mypy`, `safety`, `bandit`, `tox`, `pre-commit`

## Step 4: Work with the Virtual Environment

You can work with Poetry in two ways:

Run commands with `poetry run`:
```bash
poetry run python main.py
poetry run pytest
```


## Step 5: Run Your Project

Process your transaction data:

```bash
poetry run python main.py
```

## Step 6: Run Tests

Execute the test suite:

```bash
poetry run pytest
```

## Additional Poetry Commands

Here are some other useful Poetry commands:

- **Add a new dependency**: `poetry add package-name`
- **Add a dev dependency**: `poetry add --group dev package-name`
- **Update dependencies**: `poetry update`
- **List all dependencies**: `poetry show`
- **Remove a dependency**: `poetry remove package-name`
- **Check for outdated packages**: `poetry show --outdated`
