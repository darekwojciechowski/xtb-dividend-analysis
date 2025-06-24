#!/bin/sh
# Pre-commit hook that runs tests automatically
# To install: copy this file to .git/hooks/pre-commit and make it executable
# Or use: pre-commit install (recommended)

echo "Running pre-commit tests..."

# Change to the project directory
cd "$(git rev-parse --show-toplevel)"

# Run quick tests
python -m pytest tests/ -v --tb=short -x

# Check the exit status
if [ $? -ne 0 ]; then
    echo "❌ Tests failed! Commit aborted."
    echo "Fix the failing tests before committing."
    exit 1
fi

echo "✅ All tests passed! Proceeding with commit."
exit 0
