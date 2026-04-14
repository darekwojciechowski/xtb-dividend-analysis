# XTB dividend analysis

![CI/CD](https://img.shields.io/github/actions/workflow/status/darekwojciechowski/xtb-dividend-analysis/ci.yml?branch=main&style=flat-square&logo=github-actions&logoColor=white&label=CI/CD)
![Coverage](https://img.shields.io/badge/dynamic/json?url=https://raw.githubusercontent.com/darekwojciechowski/xtb-dividend-analysis/main/coverage.json&query=$.totals.percent_covered_display&label=Coverage&suffix=%25&style=flat-square&color=success)
![Python Version](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fdarekwojciechowski%2Fxtb-dividend-analysis%2Fmain%2Fpyproject.toml&style=flat-square&logo=python&logoColor=white&label=Python)
![Playwright](https://img.shields.io/pypi/v/playwright?label=Playwright&style=flat-square&logo=playwright&logoColor=white&color=2EAD33)
![Pandas](https://img.shields.io/pypi/v/pandas?label=Pandas&style=flat-square&logo=pandas&logoColor=white&color=150458)
![NumPy](https://img.shields.io/pypi/v/numpy?label=NumPy&style=flat-square&logo=numpy&logoColor=white&color=013243)
![Pytest](https://img.shields.io/pypi/v/pytest?label=Pytest&style=flat-square&logo=pytest&logoColor=white&color=0A9EDC)
![Poetry](https://img.shields.io/pypi/v/poetry?label=Poetry&style=flat-square&logo=poetry&logoColor=white&color=60A5FA)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

A Python data pipeline that parses XTB broker statements (`.xlsx`),
converts foreign dividends to PLN using NBP D-1 exchange rates, calculates
Polish Belka tax (19%) with WHT deduction, and exports a tab-separated CSV
ready to paste into Google Sheets.

![Terminal](assets/xtb-dividend-analysis-terminal.gif)

**Technical highlights**

- **Facade orchestrator pattern** — `DataFrameProcessor` owns pipeline state
  and delegates every transformation to a dedicated, stateless specialist
  class (single-responsibility principle throughout)
- **Delegate-then-assign** — each step follows `specialist = Class(df);
  df = specialist.method()`, keeping mutations explicit and traceable
- **Four-tier test suite** — unit, integration, property-based
  (`hypothesis`), and security tests; 3 OS × 5 Python versions in CI
- **Type-safe configuration** — `pydantic-settings` reads all settings from
  `.env`; no hardcoded paths, rates, or URLs anywhere in source code
- **Full static analysis** — `mypy` strict mode, `flake8`, `black`, `isort`,
  `bandit` SARIF upload to GitHub Security tab, `safety` dependency scan
- **Structured logging** — `loguru` throughout; no `print()` calls in source
- **`from __future__ import annotations`** and Google-style docstrings with
  `Args:`, `Returns:`, `Raises:` on every public method

## Architecture

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://mermaid.ink/svg/JSV7aW5pdDogeyd0aGVtZSc6ICdkYXJrJywgJ3RoZW1lVmFyaWFibGVzJzogeyAncHJpbWFyeUNvbG9yJzogJyMxZjI5MzcnLCAnbWFpbkJrZyc6ICcjMWYyOTM3JywgJ2NsdXN0ZXJCa2cnOiAnIzExMTgyNycsICdjbHVzdGVyQm9yZGVyJzogJyMzNzQxNTEnLCAnbGluZUNvbG9yJzogJyM5Y2EzYWYnLCAnZm9udEZhbWlseSc6ICdTZWdvZSBVSSwgc2Fucy1zZXJpZicsICdlZGdlTGFiZWxCYWNrZ3JvdW5kJzogJyMxMTE4MjcnIH19fSUlCmdyYXBoIExSCiAgICBzdWJncmFwaCBEYXRhIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7RGF0YSBTY3VyY2VzJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Il0KICAgICAgICBkaXJlY3Rpb24gVEIKICAgICAgICBBW1hUQiBTdGF0ZW1lbnRzXTo6OmRhdGEKICAgICAgICBCW05CUCBBcmNoaXZlXTo6OmRhdGEKICAgIGVuZAoKICAgIHN1YmdyYXBoIExvZ2ljIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7UHJvY2Vzc2luZyBQaXBlbGluZSZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgQyhQbGF5d3JpZ2h0IERMKTo6OnByb2MKICAgICAgICBEe0RhdGEgRXh0cmFjdG9yfTo6OnByb2MKICAgICAgICBFW0RhdGVDb252ZXJ0ZXJdOjo6cHJvYwogICAgICAgIEZbREYgUHJvY2Vzc29yXTo6OnByb2MKICAgIGVuZAoKICAgIHN1YmdyYXBoIFVJIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7T3V0cHV0ICYgVmlzdWFsaXphdGlvbiZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgR1tHb29nbGUgU2hlZXRzXTo6OnVpCiAgICAgICAgSFtWaXN1YWxpemF0aW9uc106Ojp1aQogICAgICAgIElbU3RyZWFtbGl0IERhc2hib2FyZF06Ojp1aQogICAgZW5kCgogICAgQiAtLT58RG93bmxvYWR8IEMKICAgIEMgLS0-fENTVnwgRAogICAgQSAtLT58UGFyc2V8IEQKICAgIEQgLS0-fE5vcm1hbGl6ZXwgRQogICAgRSAtLT58VHJhbnNmb3JtfCBGCiAgICBGIC0tPnxFeHBvcnR8IEcKICAgIEYgLS0-fFBsb3R8IEgKICAgIEcgLS0-fFN0cmVhbXwgSQogICAgSCAtLT58RW5oYW5jZXwgSQoKICAgIGNsYXNzRGVmIGRhdGEgZmlsbDojMTcyNTU0LHN0cm9rZTojNjBhNWZhLHN0cm9rZS13aWR0aDoycHgsY29sb3I6I2RiZWFmZSxyeDo4LHJ5Ojg7CiAgICBjbGFzc0RlZiBwcm9jIGZpbGw6IzJlMTA2NSxzdHJva2U6I2E3OGJmYSxzdHJva2Utd2lkdGg6MnB4LGNvbG9yOiNmM2U4ZmYscng6OCxyeTo4OwogICAgY2xhc3NEZWYgdWkgZmlsbDojMDY0ZTNiLHN0cm9rZTojMzRkMzk5LHN0cm9rZS13aWR0aDoycHgsY29sb3I6I2QxZmFlNSxyeDo4LHJ5Ojg7CiAgICBzdHlsZSBEYXRhIGZpbGw6IzExMTgyNyxzdHJva2U6IzM3NDE1MSxzdHJva2Utd2lkdGg6MXB4LHJ4OjEwLHJ5OjEwCiAgICBzdHlsZSBMb2dpYyBmaWxsOiMxMTE4Mjcsc3Ryb2tlOiMzNzQxNTEsc3Ryb2tlLXdpZHRoOjFweCxyeDoxMCxyeToxMAogICAgc3R5bGUgVUkgZmlsbDojMTExODI3LHN0cm9rZTojMzc0MTUxLHN0cm9rZS13aWR0aDoxcHgscng6MTAscnk6MTAK">
  <img alt="System architecture diagram" src="https://mermaid.ink/svg/JSV7aW5pdDogeyd0aGVtZSc6ICdiYXNlJywgJ3RoZW1lVmFyaWFibGVzJzogeyAncHJpbWFyeUNvbG9yJzogJyNmZmYnLCAnbWFpbkJrZyc6ICcjZmZmJywgJ2NsdXN0ZXJCa2cnOiAnI2Y5ZmFmYicsICdjbHVzdGVyQm9yZGVyJzogJyNlNWU3ZWInLCAnbGluZUNvbG9yJzogJyM2YjcyODAnLCAnZm9udEZhbWlseSc6ICdTZWdvZSBVSSwgc2Fucy1zZXJpZicsICdlZGdlTGFiZWxCYWNrZ3JvdW5kJzogJyNmOWZhZmInIH19fSUlCmdyYXBoIExSCiAgICBzdWJncmFwaCBEYXRhIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7RGF0YSBTY3VyY2VzJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Il0KICAgICAgICBkaXJlY3Rpb24gVEIKICAgICAgICBBW1hUQiBTdGF0ZW1lbnRzXTo6OmRhdGEKICAgICAgICBCW05CUCBBcmNoaXZlXTo6OmRhdGEKICAgIGVuZAoKICAgIHN1YmdyYXBoIExvZ2ljIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7UHJvY2Vzc2luZyBQaXBlbGluZSZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgQyhQbGF5d3JpZ2h0IERMKTo6OnByb2MKICAgICAgICBEe0RhdGEgRXh0cmFjdG9yfTo6OnByb2MKICAgICAgICBFW0RhdGVDb252ZXJ0ZXJdOjo6cHJvYwogICAgICAgIEZbREYgUHJvY2Vzc29yXTo6OnByb2MKICAgIGVuZAoKICAgIHN1YmdyYXBoIFVJIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7T3V0cHV0ICYgVmlzdWFsaXphdGlvbiZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgR1tHb29nbGUgU2hlZXRzXTo6OnVpCiAgICAgICAgSFtWaXN1YWxpemF0aW9uc106Ojp1aQogICAgICAgIElbU3RyZWFtbGl0IERhc2hib2FyZF06Ojp1aQogICAgZW5kCgogICAgQiAtLT58RG93bmxvYWR8IEMKICAgIEMgLS0-fENTVnwgRAogICAgQSAtLT58UGFyc2V8IEQKICAgIEQgLS0-fE5vcm1hbGl6ZXwgRQogICAgRSAtLT58VHJhbnNmb3JtfCBGCiAgICBGIC0tPnxFeHBvcnR8IEcKICAgIEYgLS0-fFBsb3R8IEgKICAgIEcgLS0-fFN0cmVhbXwgSQogICAgSCAtLT58RW5oYW5jZXwgSQoKICAgIGNsYXNzRGVmIGRhdGEgZmlsbDojZWZmNmZmLHN0cm9rZTojM2I4MmY2LHN0cm9rZS13aWR0aDoycHgsY29sb3I6IzFlM2E4YSxyeDo4LHJ5Ojg7CiAgICBjbGFzc0RlZiBwcm9jIGZpbGw6I2Y1ZjNmZixzdHJva2U6IzhiNWNmNixzdHJva2Utd2lkdGg6MnB4LGNvbG9yOiM0YzFkOTUscng6OCxyeTo4OwogICAgY2xhc3NEZWYgdWkgZmlsbDojZWNmZGY1LHN0cm9rZTojMTBiOTgxLHN0cm9rZS13aWR0aDoycHgsY29sb3I6IzA2NGUzYixyeDo4LHJ5Ojg7CiAgICBzdHlsZSBEYXRhIGZpbGw6I2Y5ZmFmYixzdHJva2U6I2U1ZTdlYixzdHJva2Utd2lkdGg6MXB4LHJ4OjEwLHJ5OjEwCiAgICBzdHlsZSBMb2dpYyBmaWxsOiNmOWZhZmIsc3Ryb2tlOiNlNWU3ZWIsc3Ryb2tlLXdpZHRoOjFweCxyeDoxMCxyeToxMAogICAgc3R5bGUgVUkgZmlsbDojZjlmYWZiLHN0cm9rZTojZTVlN2ViLHN0cm9rZS13aWR0aDoxcHgscng6MTAscnk6MTAK">
</picture>

### Pipeline steps

`DataFrameProcessor` is a facade that owns `self.df` and never implements
business logic itself. Each step uses the delegate-then-assign pattern:

```python
specialist = SpecialistClass(self.df)
self.df = specialist.method()
```

| Step | Specialist class | Responsibility |
|------|-----------------|----------------|
| 1 | `ColumnNormalizer` | Maps bilingual (PL/EN) column names to canonical English names via `ColumnName` enum |
| 2 | `DividendFilter` | Filters dividend and WHT rows; groups by ticker, date, and comment |
| 3 | `DataAggregator` | Merges split rows, moves negative WHT values to a dedicated column, reorders columns |
| 4 | `CurrencyConverter` | Detects account currency from XLSX cell F6; looks up NBP D-1 mid-rate for each payment date |
| 5 | `TaxExtractor` | Parses WHT percentage from free-text comment strings using `MultiConditionExtractor` |
| 6 | `TaxCalculator` | Computes Belka tax: `gross × 0.19 − WHT_paid` in PLN; handles both USD and PLN accounts |
| 7 | `ColumnFormatter` | Applies ANSI ticker colorization, formats display columns, appends currency labels |

All domain constants (`ColumnName`, `Currency`, `TickerSuffix`) are enums
in `data_processing/constants.py`. No raw string literals for column names
or currency codes appear anywhere in source.

## Testing

The test suite has seven tiers, each with a distinct scope and tooling:

| Tier | Files | Framework | What it covers |
|------|-------|-----------|----------------|
| Unit | 7 | `pytest` + `unittest.mock` | Each specialist class in isolation; all external I/O mocked |
| Integration | 6 | `pytest` + real DataFrames | End-to-end pipeline with actual XLSX fixtures and NBP CSV files |
| Property-based | 2 | `hypothesis` (100 examples/run) | Mathematical invariants in `TaxCalculator`, `CurrencyConverter`, `DateConverter`, and `DataFrameProcessor` |
| Security | 2 | `bandit` + custom SARIF parser | SARIF output structure, severity mapping, security summary generation |
| Contract | 2 | `pandera` | Schema tripwires on the raw XTB XLSX and the Google-Sheets CSV — catches silent broker format drift |
| Fuzz | 2 | `hypothesis` (binary & text strategies) | Robustness of the XLSX loader and string parsers against hostile input; whitelisted exceptions only |
| Metamorphic | 3 | `hypothesis` + relation assertions | Logical invariants of tax/currency/aggregate logic (permutation, duplication, additivity, linear scaling) without an oracle |

All tests follow the AAA pattern (Arrange / Act / Assert) with a blank line
between each section, and are named
`test_<unit>_<scenario>_<expected_outcome>`.

Run the full suite:

```bash
poetry run pytest
```

Run a specific tier:

```bash
poetry run pytest -m unit
poetry run pytest -m integration
poetry run pytest -m property_based
poetry run pytest -m security
poetry run pytest -m contract
poetry run pytest -m fuzz
poetry run pytest -m metamorphic
```

Run across Python 3.9–3.13 with tox:

```bash
poetry run tox
```

## CI/CD pipeline

### `ci.yml` — full matrix

- **Matrix:** 3 operating systems (Ubuntu, Windows, macOS) × 5 Python
  versions (3.9–3.13), with targeted exclusions to keep the matrix lean
- **Change detection:** `dorny/paths-filter@v3` skips the test job when no
  Python files changed
- **Dependency cache:** keyed on the SHA256 hash of `pyproject.toml` to
  invalidate reliably on any dependency change
- **Artifacts:** JUnit XML test results via `dorny/test-reporter`; Codecov
  coverage upload with PR comment; `bandit` SARIF report uploaded to the
  GitHub Security tab
- **Non-blocking jobs:** lint and security jobs run with
  `continue-on-error: true` so a style warning never blocks a merge

### `fast-tests.yml` — smoke test

- **Matrix:** Ubuntu + Python 3.12 only
- **Purpose:** sub-60-second feedback loop before the full matrix completes

## Prerequisites

- Python 3.12 or later
- [Poetry](https://python-poetry.org/) for dependency management
- Chromium (installed automatically by Playwright during setup)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/darekwojciechowski/xtb-dividend-analysis.git
   cd xtb-dividend-analysis
   ```

2. Install dependencies:

   ```bash
   poetry install
   ```

3. Install the Playwright browser:

   ```bash
   poetry run playwright install chromium
   ```

## Usage

### Step 1: Download NBP exchange rate archives

Run the following command to download NBP annual exchange rate CSV files
for the last three years. The files are saved to the `data/` directory as
`archiwum_tab_a_<YYYY>.csv`, for example `archiwum_tab_a_2025.csv`.

```bash
poetry run python data_acquisition/playwright_download_currency_archive.py
```

### Step 2: Process the broker statement

Place your XTB broker statement `.xlsx` file in the `data/` directory,
then run the pipeline:

```bash
poetry run python main.py
```

The processed output is written to `output/for_google_spreadsheet.csv`.

### Step 3: Import to Google Sheets

Open Google Sheets, then paste the contents of
`output/for_google_spreadsheet.csv` directly into a sheet. The file uses
tab separators, which Google Sheets recognizes automatically on paste.

### Step 4: Visualize (optional)

To explore the data interactively, use the
[Streamlit Dividend Dashboard](https://github.com/darekwojciechowski/Streamlit-Dividend-Dashboard).
Supply the exported CSV as the dashboard's input file.

![Dashboard Demo](assets/streamlit-dashboard-demo.gif)
