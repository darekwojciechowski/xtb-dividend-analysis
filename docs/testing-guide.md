# 🧪 Comprehensive Testing Guide

A practical guide to maintaining code quality and reliability.

## ⚡ Quick Start

Get your testing environment up and running in seconds.

```bash
# 1. Install Dependencies
poetry install

# 2. Run All Tests
poetry run pytest

# 3. Run with Coverage Report
poetry run pytest --cov --cov-report=term-missing
```

## 📂 Test Suite Architecture

Our tests are structured to mirror the application logic, ensuring intuitive navigation.

```text
tests/
├── __init__.py
├── test_main.py                # Integration tests for the main entry point
├── test_dataframe_processor.py # Unit tests for data transformation logic
├── test_date_converter.py      # Unit tests for date handling utilities
└── test_exporter.py            # Unit tests for file I/O and export
```

## 📊 Coverage & Quality Standards

We strive for high confidence in our code through rigorous metrics.

| Metric | Command | Target |
| :--- | :--- | :--- |
| **Unit Tests** | `poetry run pytest` | 100% Pass |
| **Coverage** | `poetry run pytest --cov` | >85% |
| **Linting** | `poetry run flake8 .` | 0 Errors |
| **Formatting** | `poetry run black .` | PEP 8 Compliant |

### Generating HTML Reports
For a visual deep-dive into coverage:
```bash
poetry run pytest --cov --cov-report=html
open htmlcov/index.html
```

## ✍️ Writing Effective Tests

We use `pytest` fixtures to create clean, maintainable test code.

**Example Pattern:**

```python
import pytest
from my_module import process_data

@pytest.fixture
def sample_dataset():
    """Provides a standardized dataset for testing."""
    return {"id": 1, "value": 100}

def test_data_processing_logic(sample_dataset):
    """
    GIVEN a valid sample dataset
    WHEN processed by the engine
    THEN the result should be normalized
    """
    result = process_data(sample_dataset)
    assert result["normalized_value"] == 1.0
```

## 🔧 Troubleshooting & Debugging

Common issues and how to resolve them.

| Issue | Solution |
| :--- | :--- |
| **Missing Dependencies** | Run `poetry install` to sync environment. |
| **Browser Errors** | Run `poetry run playwright install chromium` for scraper tests. |
| **Test Failures** | Use `poetry run pytest --pdb` to drop into debugger on failure. |
| **Verbose Output** | Use `poetry run pytest -vv` for detailed logs. |

---
*Quality is not an act, it is a habit.*
