# Tests for Security and CI/CD Scripts

This directory contains comprehensive test coverage for security scanning and CI/CD utility scripts following pytest best practices and 2026 standards.

## Test Structure

```
tests/
├── test_unit/               # Unit tests for business logic
└── test_security/           # Security script tests (this directory)
    ├── __init__.py
    ├── test_bandit_to_sarif.py      # Tests for Bandit→SARIF converter
    └── test_security_summary.py      # Tests for security summary generator
```

## What's Being Tested

### 1. Bandit to SARIF Converter (`test_bandit_to_sarif.py`)
Tests for `scripts/bandit_to_sarif.py` - converts Bandit security scan results to SARIF 2.1.0 format for GitHub Security integration.

**Test Coverage:**
- ✅ Severity mapping (HIGH→error, MEDIUM→warning, LOW→note)
- ✅ SARIF structure validation
- ✅ Result conversion accuracy
- ✅ Windows path handling (backslash to forward slash)
- ✅ Missing field handling with sensible defaults
- ✅ Error handling (missing files, invalid JSON)
- ✅ Empty results handling

**Test Classes:**
- `TestSeverityMapping` - Verify severity level conversions
- `TestSARIFStructure` - Validate SARIF 2.1.0 schema compliance
- `TestResultConversion` - Test individual result transformation
- `TestFullConversion` - End-to-end conversion workflow
- `TestErrorHandling` - Edge cases and error scenarios

### 2. Security Summary Generator (`test_security_summary.py`)
Tests for `scripts/security_summary.py` - generates human-readable security summaries for CI/CD pipelines.

**Test Coverage:**
- ✅ Severity statistics formatting
- ✅ Common issue type counting and display
- ✅ Lines of code scanned reporting
- ✅ Top N issues limiting
- ✅ Empty results handling
- ✅ Missing file handling
- ✅ Malformed JSON handling
- ✅ Integration with actual Bandit report structure

**Test Classes:**
- `TestSeverityFormatting` - Severity breakdown display
- `TestCommonIssuesFormatting` - Issue frequency reporting
- `TestSecuritySummaryGeneration` - Complete summary generation
- `TestEdgeCases` - Error handling and edge cases
- `TestIntegrationWithBandit` - Real-world Bandit report parsing

## Running Tests

### Run All Security Tests
```bash
# All security tests
pytest tests/test_security/ -v

# Or using the marker
pytest -m security -v
```

### Run Specific Test Files
```bash
# Test Bandit to SARIF converter
pytest tests/test_security/test_bandit_to_sarif.py -v

# Test security summary generator
pytest tests/test_security/test_security_summary.py -v
```

### Run Specific Test Classes
```bash
# Test severity mapping
pytest tests/test_security/test_bandit_to_sarif.py::TestSeverityMapping -v

# Test error handling
pytest tests/test_security/test_security_summary.py::TestEdgeCases -v
```

### Run with Coverage
```bash
# Security scripts coverage
pytest tests/test_security/ --cov=scripts --cov-report=term-missing -v

# Coverage with HTML report
pytest tests/test_security/ --cov=scripts --cov-report=html -v
```

## Test Fixtures

### Shared Fixtures
Fixtures are defined within each test file for maximum clarity:

**`test_bandit_to_sarif.py`:**
- `sample_bandit_result` - Single Bandit finding
- `sample_bandit_report` - Complete Bandit JSON report
- `temp_bandit_json` - Temporary JSON file for testing

**`test_security_summary.py`:**
- `sample_bandit_metrics` - Severity statistics
- `sample_bandit_results` - List of findings
- `complete_bandit_report` - Full report structure
- `temp_bandit_report` - Temporary report file

## Test Markers

All tests in this directory use the `@pytest.mark.security` marker:

```python
@pytest.mark.security
class TestSeverityMapping:
    """Tests are automatically categorized as security tests."""
    pass
```

Filter by marker:
```bash
pytest -m security          # Run only security tests
pytest -m "not security"    # Skip security tests
```

## Test Patterns Used

### 1. Parametrized Testing
Test multiple scenarios efficiently:
```python
@pytest.mark.parametrize("bandit_severity,expected_sarif_level", [
    ("HIGH", "error"),
    ("MEDIUM", "warning"),
    ("LOW", "note"),
])
def test_map_severity_returns_correct_level(
    bandit_severity: str, expected_sarif_level: str
):
    assert _map_severity(bandit_severity) == expected_sarif_level
```

### 2. Temporary Files Testing
Use `tmp_path` fixture for file operations:
```python
def test_convert_creates_valid_file(temp_bandit_json: Path, tmp_path: Path):
    sarif_output = tmp_path / "results.sarif"
    convert_bandit_to_sarif(str(temp_bandit_json), str(sarif_output))
    assert sarif_output.exists()
```

### 3. Exception Testing
Validate error handling:
```python
def test_convert_raises_error_for_missing_file(tmp_path: Path):
    nonexistent = tmp_path / "nonexistent.json"
    with pytest.raises(FileNotFoundError):
        convert_bandit_to_sarif(str(nonexistent), str(output))
```

### 4. Output Capture Testing
Test console output with `capsys`:
```python
def test_format_severity_stats_shows_correct_counts(
    sample_bandit_metrics: dict, capsys
):
    _format_severity_stats(sample_bandit_metrics)
    captured = capsys.readouterr()
    assert "**High Severity**: 3" in captured.out
```

## Coverage Goals

Target: **100% coverage** for security scripts
Current: **100% coverage** ✅

```
scripts\bandit_to_sarif.py      30      0   100%
scripts\security_summary.py     35      0   100%
```

## Best Practices Followed

✅ **AAA Pattern** - Arrange, Act, Assert structure  
✅ **Descriptive Names** - Test names explain what and why  
✅ **Fixture Composition** - Build complex fixtures from simple ones  
✅ **One Behavior Per Test** - Each test validates one thing  
✅ **Test Error Paths** - Both happy paths and failure scenarios  
✅ **Type Hints** - Full type annotations for clarity  
✅ **Docstrings** - Clear documentation for each test  
✅ **Isolation** - Each test is independent  
✅ **Cleanup** - Automatic cleanup with tmp_path and fixtures  

## CI/CD Integration

These tests run automatically in GitHub Actions CI pipeline:

```yaml
# .github/workflows/ci.yml
- name: Run security script tests
  run: poetry run pytest tests/test_security/ -v --cov=scripts
```

## Adding New Tests

When adding new security scripts:

1. Create test file: `test_<script_name>.py`
2. Add `@pytest.mark.security` marker to test classes
3. Follow AAA pattern in test functions
4. Use parametrization for multiple scenarios
5. Test both success and error cases
6. Add fixtures in the test file or conftest.py
7. Update this README with new test coverage

Example template:
```python
"""Tests for new_security_script.py"""
import pytest

@pytest.mark.security
class TestNewFeature:
    def test_feature_when_valid_input_then_succeeds(self):
        # Arrange
        data = setup_data()
        
        # Act
        result = new_function(data)
        
        # Assert
        assert result == expected
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [SARIF 2.1.0 Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)
- [Bandit Security Linter](https://bandit.readthedocs.io/)
- [GitHub Code Scanning](https://docs.github.com/en/code-security/code-scanning)
