.PHONY: help install test test-fast test-cov lint format clean setup-dev

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install all dependencies
	python -m pip install --upgrade pip
	pip install -r requirements.txt

test:  ## Run all tests
	pytest tests/ -v

test-fast:  ## Run tests without coverage
	pytest tests/ -v --tb=short

test-cov:  ## Run tests with coverage reporting
	pytest tests/ -v --cov=data_processing --cov=data_acquisition --cov=visualization --cov=config --cov-report=term-missing --cov-report=html

test-script:  ## Run tests using the Python test runner script
	python scripts/run_tests.py

test-script-ps:  ## Run tests using the PowerShell script (Windows)
	powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1

lint:  ## Run all linting tools
	flake8 data_processing data_acquisition visualization config tests --max-line-length=88 --extend-ignore=E203,W503
	black --check data_processing data_acquisition visualization config tests
	isort --check-only data_processing data_acquisition visualization config tests --profile black
	mypy data_processing data_acquisition visualization config --ignore-missing-imports

format:  ## Format code with black and isort
	black data_processing data_acquisition visualization config tests
	isort data_processing data_acquisition visualization config tests --profile black

security:  ## Run security scans
	safety check --file requirements.txt
	bandit -r data_processing data_acquisition visualization config

tox-test:  ## Run tests with tox (multiple Python versions)
	tox

clean:  ## Clean up cache files and test artifacts
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .tox
	rm -rf *.egg-info

setup-dev:  ## Set up development environment
	pip install pre-commit
	pre-commit install
	@echo "Development environment set up successfully!"

ci-local:  ## Run the same checks as CI locally
	$(MAKE) lint
	$(MAKE) test-cov
	$(MAKE) security

all:  ## Run all checks (lint, test, security)
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test-cov
	$(MAKE) security
