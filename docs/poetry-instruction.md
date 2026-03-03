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

## Step 4: Install Playwright Browsers

`poetry install` installs the `playwright` Python package, but the browser binaries (Chromium, ~170 MB) are managed separately and must be downloaded once:

```bash
poetry run playwright install chromium
```

> **Note:** This is a one-time setup step. The browser files are stored in your user profile (`~/.cache/ms-playwright` on macOS/Linux, `%LOCALAPPDATA%\ms-playwright` on Windows) and are not managed by Poetry.

## Step 5: Work with the Virtual Environment

You can work with Poetry in two ways:

Run commands with `poetry run`:
```bash
poetry run python main.py
poetry run pytest
```


## Step 6: Download Currency Exchange Rates (First Time Setup)

Before running the main project, download the required NBP currency exchange rate files:

```bash
poetry run python -m data_acquisition.playwright_download_currency_archive
```

This downloads the last 3 years of exchange rate data from NBP to the `data/` directory. You only need to run this once, or periodically to update the rates.

## Step 7: Run Your Project

Process your transaction data:

```bash
poetry run python main.py
```

## Step 8: Run Tests

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


## Code Quality: Lint and Format with Ruff

Run linting with auto-fix and formatting using Ruff:

```bash
poetry run ruff check --fix .
poetry run ruff format .