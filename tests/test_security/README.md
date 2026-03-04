# Security tests

Tests for scripts in `scripts/` that process security scan results.

**Test files:**
- `test_bandit_to_sarif.py` — SARIF conversion
- `test_security_summary.py` — summary formatting

## Running

Run all security tests:

```bash
make test
poetry run pytest -m security -v
```

Run with coverage:

```bash
poetry run pytest -m security --cov=scripts --cov-report=term-missing -v
```

## Test marker

All tests use `@pytest.mark.security`:

```bash
poetry run pytest -m security          # Run only security tests
poetry run pytest -m "not security"    # Skip security tests
```

## CI/CD

Tests run in the `test-security` job in `.github/workflows/ci.yml`:

```yaml
- name: Run security tests
  run: |
    poetry run pytest tests/ \
      -m "security" \
      --junitxml=test-results-security.xml \
      --no-cov \
      -v
```

## Adding new tests

When adding a new security script:

1. Create `tests/test_security/test_<script_name>.py`.
2. Add `@pytest.mark.security` to all test classes.
3. Follow the AAA pattern.
4. Use parametrization for multiple input scenarios.
5. Test both success paths and failure paths.
6. Add fixtures in the test file or in `conftest.py`.

Example template:

```python
"""Tests for new_security_script.py."""

from __future__ import annotations

import pytest


@pytest.mark.security
class TestNewFeature:
    def test_feature_when_valid_input_then_succeeds(self) -> None:
        # Arrange
        data = setup_data()

        # Act
        result = new_function(data)

        # Assert
        assert result == expected
```
