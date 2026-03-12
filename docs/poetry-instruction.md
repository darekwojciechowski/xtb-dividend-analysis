# Poetry project setup

Poetry manages project dependencies, virtual environments, and packaging for
Python. This guide covers installation, dependency setup, and common commands
for `xtb-dividend-analysis`.

## Step 1: Install Poetry

On **macOS**, install Poetry with Homebrew:

```bash
brew install poetry
```

On **Windows**, install with pip:

```bash
pip install poetry
```

## Step 2: Navigate to project directory

```bash
cd xtb-dividend-analysis
```

## Step 3: Install project dependencies

Install all dependencies defined in `pyproject.toml`:

```bash
poetry install
```

This creates a virtual environment and installs:

- **Core dependencies**: `pandas`, `numpy`, `matplotlib`, `openpyxl`,
  `playwright`, `tabulate`, `loguru`
- **Dev dependencies**: `pytest`, `pytest-cov`, `black`, `isort`, `flake8`,
  `mypy`, `safety`, `bandit`, `tox`, `pre-commit`

## Step 4: Install Playwright browsers

`poetry install` installs the `playwright` Python package, but Chromium
(~170 MB) must be downloaded separately:

```bash
poetry run playwright install chromium
```

> **Note:** This is a one-time step. Browser files are stored in
> `~/.cache/ms-playwright` on macOS/Linux and `%LOCALAPPDATA%\ms-playwright`
> on Windows, outside Poetry's management.

## Step 5: Download currency exchange rates

Download the required NBP exchange rate files before running the pipeline:

```bash
poetry run python -m data_acquisition.playwright_download_currency_archive
```

This downloads the last 3 years of exchange rate data to the `data/`
directory. Run this once during initial setup, then periodically to keep
rates current.

## Step 6: Run the pipeline

```bash
poetry run python main.py
```

## Step 7: Run tests

```bash
poetry run pytest
```

## Step 8: Check test coverage

Run tests with a terminal coverage summary (shows missing lines):

```bash
poetry run pytest --cov=app --cov-report=term-missing
```

Generate an HTML report (saved to `htmlcov/index.html`):

```bash
poetry run pytest --cov=app --cov-report=html
```

## Updating dependencies to latest versions

Poetry's built-in `poetry update` respects the version constraints in
`pyproject.toml` (e.g. `^1.0.0`) and will not bump major versions. To upgrade
all dependencies to their **latest available versions** and rewrite the
constraints in `pyproject.toml`, use the `poetry-plugin-up` plugin.

### Install the plugin (one-time)

```bash
poetry self add poetry-plugin-up
```

### Upgrade all dependencies (runtime + dev)

```bash
poetry up --latest
```

### Upgrade only dev dependencies

```bash
poetry up --latest --only dev
```

### Check what is outdated before upgrading

```bash
poetry show --outdated
```

> **Note:** `poetry up --latest` modifies `pyproject.toml` and regenerates
> `poetry.lock`. Review the diff and run `make all` afterwards to confirm
> nothing is broken.

### Alternative: upgrade without the plugin

If you prefer not to install the plugin, pass `@latest` to `poetry add` directly:

```bash
poetry add --group dev \
  pytest@latest \
  pytest-cov@latest \
  pytest-timeout@latest \
  hypothesis@latest \
  ruff@latest \
  mypy@latest \
  types-tabulate@latest \
  safety@latest \
  bandit@latest \
  tox@latest \
  pre-commit@latest
```

This rewrites the constraints in `pyproject.toml` and updates `poetry.lock` in
one step, without requiring any plugin.

---

## Common Poetry commands

| Command | Description |
|---|---|
| `poetry add package-name` | Add a runtime dependency |
| `poetry add --group dev package-name` | Add a dev dependency |
| `poetry update` | Update dependencies within existing constraints |
| `poetry up --latest` | Upgrade all deps to latest and rewrite constraints |
| `poetry show` | List installed packages |
| `poetry remove package-name` | Remove a dependency |
| `poetry show --outdated` | List outdated packages |

## Code quality

Run linting with auto-fix and formatting using Ruff:

```bash
poetry run ruff check --fix .
poetry run ruff format --check .
```