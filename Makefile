.PHONY: help install test test-fast test-cov lint format clean setup-dev

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install all dependencies
	python -m pip install --upgrade pip
	pip install poetry
	poetry install

test:  ## Run all tests
	poetry run pytest tests/ -v

test-fast:  ## Run tests without coverage
	poetry run pytest tests/ -v --tb=short

test-cov:  ## Run tests with coverage reporting
	poetry run pytest tests/ -v --cov=data_processing --cov=data_acquisition --cov=visualization --cov=config --cov-report=term-missing --cov-report=html

test-script:  ## Run tests using the Python test runner script
	python scripts/run_tests.py

test-script-ps:  ## Run tests using the PowerShell script (Windows)
	powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1

lint:  ## Run all linting tools
	poetry run flake8 data_processing data_acquisition visualization config tests --max-line-length=88 --extend-ignore=E203,W503,E501
	poetry run black --check data_processing data_acquisition visualization config tests
	poetry run isort --check-only data_processing data_acquisition visualization config tests --profile black
	poetry run mypy data_processing data_acquisition visualization config --ignore-missing-imports

format:  ## Format code with black and isort
	poetry run black data_processing data_acquisition visualization config tests
	poetry run isort data_processing data_acquisition visualization config tests --profile black

security:  ## Run security scans
	poetry run safety scan
	poetry run bandit -r data_processing data_acquisition visualization config

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
