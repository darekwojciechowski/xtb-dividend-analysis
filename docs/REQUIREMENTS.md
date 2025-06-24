# Requirements Files

This project uses multiple requirements files for different purposes:

## `requirements.txt` - Production Dependencies
Contains all dependencies needed to run the application, including:
- Core data processing libraries (pandas, numpy, matplotlib)
- Playwright for web automation
- All production dependencies

**Usage:**
```bash
pip install -r requirements.txt
```

## `requirements-test.txt` - Testing Dependencies
Contains dependencies needed for testing and development, excluding problematic packages like playwright that may have build issues on certain platforms:
- All core dependencies
- Testing frameworks (pytest, pytest-cov)
- Code quality tools (flake8, black, isort, mypy)
- Security scanning tools (safety, bandit)

**Usage:**
```bash
pip install -r requirements-test.txt
```

## When to Use Which

### Use `requirements.txt` for:
- Production deployments
- Local development when you need all features
- When playwright functionality is required

### Use `requirements-test.txt` for:
- CI/CD pipelines (more reliable)
- Testing environments
- Development when playwright is not needed
- Platforms with known build issues (e.g., macOS + Python 3.13)

## CI/CD Strategy

Our GitHub Actions workflows use `requirements-test.txt` to avoid build failures from optional dependencies like playwright, while still testing the core functionality thoroughly.

Playwright is installed separately with error handling to prevent CI failures on incompatible platform/Python version combinations.
