````instructions
# GitHub Copilot — Project Instructions

Automatically injected into every Copilot Chat session and all custom agents.
Behavioral rules for specific agents live in `.github/agents/*.agent.md` — do not duplicate them here.

> **Keep this file short.** One code example beats three paragraphs of prose. Add detail only when an agent makes a mistake. Prefer delegating specifics to the relevant `.github/agents/*.agent.md` file instead.

---

## Language

All responses, code comments, docstrings, commit messages, variable names, and generated documentation must be in English only. Never use Polish or any other language in generated output, even if the user writes in Polish.

---

## Commands

Run these before pushing. Always use the full command with flags, not just the tool name.

| Command | What it does |
|---|---|
| `make test` | `poetry run pytest tests/ -v` — full test suite |
| `make test-cov` | Tests + HTML/XML/terminal coverage report |
| `make format` | `black` + `isort` auto-fix |
| `make lint` | `flake8` + `black --check` + `isort --check` + `mypy --ignore-missing-imports` |
| `make security` | `safety scan` + `bandit -r` on all source dirs |
| `make all` | format → lint → test-cov → security (full pre-push gate) |
| `make mutmut` | `poetry run mutmut run` — mutation testing on `data_processing/` |
| `make mutmut-results` | Show surviving/killed mutants summary |
| `make mutmut-browse` | Browse mutation results interactively (TUI) |
| `python main.py` | Run the full dividend analysis pipeline |

---

## Project Overview

`xtb-dividend-analysis` is a financial data processing pipeline for Polish retail investors using the XTB brokerage platform. It parses XTB `.xlsx` broker statements, looks up NBP exchange rates, calculates Belka tax (19% on foreign dividends minus WHT already paid at source), and exports a tab-separated CSV for Google Sheets.

**Key domain terms:** Belka tax (19% Polish capital gains tax) · WHT (Withholding Tax, negative row in statement) · NBP archive (`archiwum_tab_a_*.csv`) · D-1 rate (NBP mid-rate the business day before the dividend date) · Gross/Net dividend · Statement currency (detected from cell F6 of the XTB XLSX)

---

## Architecture

Sequential processing pipeline with a Facade orchestrator. `DataFrameProcessor` delegates every step to a single-responsibility specialist and never implements business logic itself.

```
main.py → DataFrameProcessor → ColumnNormalizer, DividendFilter, DataAggregator,
                                CurrencyConverter, TaxExtractor, TaxCalculator, ColumnFormatter
        → GoogleSpreadsheetExporter.export_to_google()
```

Key entry points: `main.py` (pipeline runner) · `data_processing/dataframe_processor.py` (orchestrator, ~25 methods) · `data_processing/constants.py` (`ColumnName`, `Currency`, `TickerSuffix` enums). Full module inventory: `data_processing/`, `data_acquisition/`, `visualization/`, `config/`.

**Tech stack:** Python ≥3.12 · pandas ≥2.3 · numpy ≥2.3 · openpyxl ≥3.1.5 · playwright ≥1.56 · loguru ≥0.7 · pydantic-settings ≥2.0 · matplotlib ≥3.10 · Poetry (package-mode = false) · pytest ≥9.0 + hypothesis ≥6.0 · tox ≥4.0 (py39–py313)

---

## Coding Conventions

The code example below is the canonical reference — follow it exactly.

```python
from __future__ import annotations          # required in every module

import pandas as pd
from loguru import logger                   # never use print()

from config.settings import settings        # all configurable values live here
from data_processing.constants import ColumnName  # always use enums, never raw strings


class TaxCalculator:
    """Calculate Belka tax (19%) owed on foreign dividend income in PLN."""

    def __init__(self, df: pd.DataFrame, polish_tax_rate: float | None = None) -> None:
        """Initialize TaxCalculator.

        Args:
            df: DataFrame with required dividend columns.
            polish_tax_rate: Override for the Belka rate; defaults to
                ``settings.polish_tax_rate``.
        """
        self.df = df
        self.polish_tax_rate = (
            polish_tax_rate if polish_tax_rate is not None else settings.polish_tax_rate
        )

    def calculate(self) -> pd.DataFrame:
        """Append Tax Amount PLN column and return the modified DataFrame.

        Returns:
            DataFrame with the ``ColumnName.TAX_AMOUNT_PLN`` column added.
        """
        logger.info("Step 11 - Calculating Belka tax in PLN")
        result = self.df.copy()             # never mutate self.df in-place
        # access columns via ColumnName enum, e.g. result[ColumnName.GROSS_DIVIDEND]
        return result
```

Additional rules: Google-style docstrings (`Args:`, `Returns:`, `Raises:`) on all public methods · full type hints on all public signatures · delegate-then-assign in `DataFrameProcessor` (`specialist = Foo(self.df); self.df = specialist.method()`) · composition over inheritance.

---

## Testing

- AAA pattern: Arrange / Act / Assert, blank line between each section
- Test names: `test_<unit>_<scenario>_<expected_outcome>`
- Markers: `@pytest.mark.unit` · `@pytest.mark.integration` · `@pytest.mark.property_based` · `@pytest.mark.security`
- Mock all external IO with `unittest.mock.patch` or `MagicMock`
- Property-based tests use `@given` (Hypothesis) in `tests/property_based/`
- Fixtures: shared → `tests/conftest.py`; integration-specific → `tests/test_integration/conftest.py`

---

## Git Workflow

- Commit format: `type(scope): description` — types: `feat` · `fix` · `refactor` · `test` · `chore` · `docs`
- Feature branches off `main`; PR required to merge
- `make setup-dev` installs pre-commit hooks (runs format + lint automatically on every commit)
- Never commit: `.env`, `data/archiwum_*.csv`, `logs/`, `output/`, `htmlcov/`

---

## CI/CD

Run `make all` locally before pushing. CI mirrors the same sequence across 3 OS × 5 Python versions via `tox`. See `.github/workflows/ci.yml` (full matrix + Codecov) and `fast-tests.yml` (smoke test, ubuntu-latest / Python 3.12).

---

## Boundaries

**Always do:** `from __future__ import annotations` · `ColumnName`/`Currency`/`TickerSuffix` enums for all column/currency access · Google docstrings · `loguru` for all output · delegate-then-assign in `DataFrameProcessor` · run `make format` before committing

**Ask first:** adding new `pyproject.toml` dependencies · renaming `settings.py` fields · modifying CI workflow files · changing `DataFrameProcessor` public method signatures

**Never do:** `print()` in source modules · raw string literals for column names or currency codes · hardcoded paths, rates, or URLs · in-place DataFrame mutation returned from specialists · new inheritance hierarchies · Polish or emoji in output · commit `.env` or secrets

````
