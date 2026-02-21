# GitHub Copilot — Project Instructions

Automatically injected into every Copilot Chat session and all custom agents.
Behavioral rules for specific agents live in `.github/agents/*.agent.md` — do not duplicate them here.

---

## Language

All responses, code comments, docstrings, commit messages, variable names, and generated documentation must be in English only. Never use Polish or any other language in generated output, even if the user writes in Polish.

---

## Project Overview

`xtb-dividend-analysis` is a financial data processing pipeline for Polish retail investors using the XTB brokerage platform. It:

- Parses XTB broker trading statements exported as `.xlsx` files (Polish and English variants)
- Extracts dividend and withholding tax (WHT) records from those statements
- Looks up historical NBP (National Bank of Poland) exchange rates to convert foreign dividends to PLN
- Calculates Belka tax (19% Polish capital gains tax) owed on foreign dividends, deducting WHT already paid at source
- Exports a tab-separated CSV ready to paste into Google Sheets

---

## Domain Vocabulary

- **Belka tax** — Polish 19% flat capital gains tax (`polish_tax_rate = 0.19` in `settings.py`)
- **WHT (Withholding Tax)** — tax deducted at source by the paying country; appears as a negative row in the XTB statement
- **NBP archive** — annual CSV files from the National Bank of Poland containing daily mid-rates (`archiwum_tab_a_*.csv`) downloaded via Playwright
- **D-1 rate** — the NBP exchange rate from the business day before the dividend payment date, used for PLN conversion
- **Statement currency** — the account currency detected from cell F6 of the XTB XLSX (USD or PLN)
- **Gross dividend** — total dividend before WHT
- **Net dividend** — dividend after deducting WHT

---

## Architecture

The system is a sequential processing pipeline with a Facade orchestrator pattern, decomposed following SOLID principles.

```
main.py
  └── process_data()
        └── DataFrameProcessor (Facade/Orchestrator)
              Delegates each step to a single-responsibility specialist class:
              ColumnNormalizer, DividendFilter, DataAggregator,
              CurrencyConverter, TaxExtractor, TaxCalculator, ColumnFormatter
        └── GoogleSpreadsheetExporter.export_to_google()
```

Key architectural rules:
- `DataFrameProcessor` owns the pipeline state (`self.df`); it never implements business logic itself
- Delegate-then-assign pattern: `specialist = SpecialistClass(self.df); self.df = specialist.method()`
- All specialist helpers are stateless beyond their constructor; they receive `df`, operate, and return `df`
- ~20 named sequential steps in `main.py`; each step logs `"Step N - ..."` via loguru

---

## Module Map

```
main.py                                                    Pipeline entry point; chains all processing steps
config/settings.py                                         Settings(BaseSettings) singleton; reads from .env
config/logging_config.py                                   Loguru setup (console + file); call setup_logging()
data_processing/constants.py                               Enums: Currency, TickerSuffix, ColumnName
data_processing/dataframe_processor.py                     DataFrameProcessor — Facade orchestrator (~25 methods)
data_processing/column_normalizer.py                       Normalizes bilingual (PL/EN) column names to English
data_processing/column_formatter.py                        Ticker colorization, D-1 date, display formatting
data_processing/dividend_filter.py                         Filters dividend and WHT rows; groups by key fields
data_processing/data_aggregator.py                         Merges rows, moves negative values, reorders columns
data_processing/currency_converter.py                      NBP exchange rate lookup; currency detection from ticker
data_processing/tax_extractor.py                           Parses WHT percentage from comment strings
data_processing/tax_calculator.py                          Belka tax calculation in PLN (gross * 19% - WHT paid)
data_processing/extractor.py                               MultiConditionExtractor — keyword-based comment parser
data_processing/date_converter.py                          Standardizes date formats across statement variants
data_processing/exporter.py                                GoogleSpreadsheetExporter — tab-separated CSV output
data_processing/file_paths.py                              Validates and resolves input XLSX and NBP CSV paths
data_processing/import_data_xlsx.py                        Reads XTB XLSX via openpyxl; detects currency from F6
data_acquisition/playwright_download_currency_archive.py   Downloads NBP annual CSVs via Playwright/Chromium
visualization/chart_net_dividend.py                        Matplotlib bar chart of net dividends by ticker
visualization/plot_style.py                                Shared chart styling
visualization/ticker_colors.py                             Per-ticker color assignments
tests/conftest.py                                          Shared pytest fixtures
tests/test_unit/                                           Unit tests (AAA pattern, mocked dependencies)
tests/test_integration/                                    Integration tests with real DataFrames and file fixtures
tests/property_based/                                      Hypothesis generative tests
tests/test_security/                                       Bandit SARIF conversion and security summary tests
scripts/                                                   CI helper scripts (bandit_to_sarif, security_summary)
```

---

## Tech Stack

### Runtime
- `pandas >=2.3.0` — all DataFrame operations throughout the pipeline
- `numpy >=2.3.0` — numeric operations, NaN handling
- `matplotlib >=3.10.0` — dividend visualization charts
- `openpyxl >=3.1.5` — reading XTB `.xlsx` broker statement files
- `playwright >=1.56.0` — browser automation for downloading NBP CSV archives
- `tabulate >=0.9.0` — terminal table output for the tax summary log
- `loguru >=0.7.0` — structured logging to console and `logs/app.log`
- `pydantic-settings >=2.0.0` — type-safe configuration from environment / `.env`

### Development and Testing
- `pytest >=9.0` with `pytest-cov >=7.0` — test runner and coverage
- `hypothesis >=6.0` — property-based generative testing
- `flake8 >=7.0`, `black >=24.0`, `isort >=5.13` — linting and formatting
- `mypy >=1.0` with `types-tabulate` — static type checking
- `safety >=3.0` — dependency vulnerability scanning
- `bandit >=1.7` — static security analysis (SARIF output uploaded to GitHub Security tab)
- `tox >=4.0` — multi-environment test orchestration (Python 3.9–3.13)
- `pre-commit >=4.5` — Git pre-commit hooks

Python requirement: `>=3.12`
Package manager: Poetry (package-mode = false)

---

## Coding Conventions

Always follow these rules when generating or modifying code in this project:

- Add `from __future__ import annotations` at the top of every Python module
- Use Google-style docstrings with `Args:`, `Returns:`, and `Raises:` sections on all public methods
- Provide full type hints on all public method signatures, including return types
- Access column names exclusively via `ColumnName` enum; access currencies via `Currency` enum; access ticker suffixes via `TickerSuffix` enum — never use raw string literals for these
- Use the delegate-then-assign pattern inside `DataFrameProcessor`: `specialist = SpecialistClass(self.df); self.df = specialist.method()`
- Use `loguru` for all logging: `from loguru import logger`; never use `print()` for diagnostics or output
- Use the `settings` singleton from `config.settings` for all configurable values (paths, rates, URLs); never hardcode them
- Do not mutate `self.df` in-place and return the mutated object from specialist helpers — always return a new or modified DataFrame
- Use composition, not inheritance, for processing helpers

---

## Testing Rules

- Follow the AAA pattern: Arrange, Act, Assert — with a blank line between each section
- Name tests: `test_<unit>_<scenario>_<expected_outcome>`
- Mark tests with the appropriate pytest marker: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.property_based`, `@pytest.mark.security`
- Use `unittest.mock.patch` or `MagicMock` for all external IO (file reads, HTTP, Playwright)
- Use `hypothesis` with `@given` for property-based tests in `tests/property_based/`
- Each test must be fully independent — no shared mutable state between tests
- Place shared fixtures in `tests/conftest.py`; place integration-specific fixtures in `tests/test_integration/conftest.py`

---

## CI/CD

Two GitHub Actions workflows:
- `ci.yml` — full matrix (3 OS x 5 Python versions), lint, bandit security scan, Codecov upload, PR coverage comment, sticky summary comment; lint and security jobs are non-blocking (`continue-on-error: true`)
- `fast-tests.yml` — smoke test on ubuntu-latest / Python 3.12 only; runs on every push/PR

Cache keys are computed from `pyproject.toml` SHA256 hash inline in Python.
Test results published via `dorny/test-reporter` as JUnit XML.

---

## What NOT to Generate

- No `print()` calls anywhere in source modules
- No hardcoded file paths, exchange rates, tax rates, or URLs — use `settings`
- No raw string literals for column names or currency codes — use the enums
- No in-place DataFrame mutation returned from specialist helpers
- No new inheritance hierarchies — this project uses composition throughout
- No Polish, no emoji, no emoticons in any generated output
