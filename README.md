# 💼 Financial Data Processing Pipeline

![CI/CD](https://img.shields.io/github/actions/workflow/status/darekwojciechowski/xtb-dividend-analysis/ci.yml?branch=main&style=flat-square&logo=github-actions&logoColor=white&label=CI/CD)
![Python Version](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)
![Playwright](https://img.shields.io/pypi/v/playwright?label=Playwright&style=flat-square&logo=playwright&logoColor=white&color=2EAD33)
![Pandas](https://img.shields.io/pypi/v/pandas?label=Pandas&style=flat-square&logo=pandas&logoColor=white&color=150458)
![NumPy](https://img.shields.io/pypi/v/numpy?label=NumPy&style=flat-square&logo=numpy&logoColor=white&color=013243)
![Matplotlib](https://img.shields.io/pypi/v/matplotlib?label=Matplotlib&style=flat-square&color=11557c)
![Pytest](https://img.shields.io/pypi/v/pytest?label=Pytest&style=flat-square&logo=pytest&logoColor=white&color=0A9EDC)
![Poetry](https://img.shields.io/badge/Poetry-1.8+-60A5FA?style=flat-square&logo=poetry&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

## 📋 Overview

A data processing pipeline designed for financial data analysis, specifically for extracting and processing XTB broker statements for Google Sheets integration. This project demonstrates expertise in data extraction, transformation, and visualization techniques essential for financial data analysis.

![Terminal](assets/xtb-dividend-analysis-terminal.gif)

## ✨ Key Features

- **Automated Condition Extraction**: Intelligent parsing of financial data
- **Date Standardization**: Converts various date formats to a consistent standard
- **Advanced DataFrame Processing**: Comprehensive data manipulation capabilities
- **Google Sheets Integration**: Seamless export functionality for collaborative analysis
- **Web Automation with Playwright**: Automates the download of currency exchange rate data for streamlined data acquisition
- **Automated Testing Infrastructure**: Comprehensive testing setup with pytest, tox, and GitHub Actions CI/CD pipeline

## 🧪 Testing & Development

### Automated Testing Infrastructure

This project implements a robust testing infrastructure with comprehensive CI/CD pipeline:

#### 🔧 Testing Framework
- **pytest**: Main testing framework with coverage reporting
- **tox**: Multi-environment testing across Python 3.9-3.13
- **GitHub Actions**: Automated CI/CD with matrix testing across Ubuntu, Windows, and macOS
- **act**: Local workflow testing with Docker (see `docs/act-local-testing.md`)

#### 🚀 CI/CD Pipeline Features
- **Multi-platform testing**: Tests run on Ubuntu, Windows, and macOS
- **Multi-version support**: Requires Python ≥3.12; CI tests across 3.9-3.13 via tox
- **Code quality checks**: Automated linting (flake8), formatting (black), import sorting (isort), and type checking (mypy)
- **Security scanning**: Automated vulnerability detection with bandit and safety
- **Coverage reporting**: Comprehensive test coverage with Codecov integration
- **Optimized caching**: Uses SHA256-based dependency cache keys for reliable artifact management

## 📖 Usage Guide

### 1. 📥 Data Acquisition

#### Using Playwright to Download Currency Archive

The `playwright_download_currency_archive.py` script automates the download of currency exchange rate data from the NBP Exchange Rates Archive. This script uses Playwright to interact with the website and download the required CSV files.

To run the script, execute the following command:
```bash
python playwright_download_currency_archive.py
```

This script will download files for the last 3 years, such as `archiwum_tab_a_<YYYY>.csv` (e.g., `archiwum_tab_a_2026.csv`, `archiwum_tab_a_2025.csv`, `archiwum_tab_a_2024.csv`). These files are necessary for the data processing pipeline.

### 2. ⚙️ Data Processing

Execute the main processing script:
```bash
python main.py
```

### 3. 📊 Google Sheets Integration

#### Automated Export

Use `GoogleSpreadsheetExporter` to export processed data to Google Sheets.

### 4. 📈 Visualization (External Repository)

To visualize the exported data, use the [Streamlit Dividend Dashboard](https://github.com/darekwojciechowski/Streamlit-Dividend-Dashboard) repository, which I created specifically for visualizing this data and is ready to use.  
Simply take the exported CSV file from this project and use it as input in the Streamlit dashboard for interactive data visualization.

![Dashboard Demo](assets/streamlit-dashboard-demo.gif)

## 🗺️ System Architecture

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://mermaid.ink/svg/JSV7aW5pdDogeyd0aGVtZSc6ICdkYXJrJywgJ3RoZW1lVmFyaWFibGVzJzogeyAncHJpbWFyeUNvbG9yJzogJyMxZjI5MzcnLCAnbWFpbkJrZyc6ICcjMWYyOTM3JywgJ2NsdXN0ZXJCa2cnOiAnIzExMTgyNycsICdjbHVzdGVyQm9yZGVyJzogJyMzNzQxNTEnLCAnbGluZUNvbG9yJzogJyM5Y2EzYWYnLCAnZm9udEZhbWlseSc6ICdTZWdvZSBVSSwgc2Fucy1zZXJpZicsICdlZGdlTGFiZWxCYWNrZ3JvdW5kJzogJyMxMTE4MjcnIH19fSUlCmdyYXBoIExSCiAgICBzdWJncmFwaCBEYXRhIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7RGF0YSBTY3VyY2VzJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Il0KICAgICAgICBkaXJlY3Rpb24gVEIKICAgICAgICBBW1hUQiBTdGF0ZW1lbnRzXTo6OmRhdGEKICAgICAgICBCW05CUCBBcmNoaXZlXTo6OmRhdGEKICAgIGVuZAoKICAgIHN1YmdyYXBoIExvZ2ljIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7UHJvY2Vzc2luZyBQaXBlbGluZSZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgQyhQbGF5d3JpZ2h0IERMKTo6OnByb2MKICAgICAgICBEe0RhdGEgRXh0cmFjdG9yfTo6OnByb2MKICAgICAgICBFW0RhdGVDb252ZXJ0ZXJdOjo6cHJvYwogICAgICAgIEZbREYgUHJvY2Vzc29yXTo6OnByb2MKICAgIGVuZAoKICAgIHN1YmdyYXBoIFVJIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7T3V0cHV0ICYgVmlzdWFsaXphdGlvbiZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgR1tHb29nbGUgU2hlZXRzXTo6OnVpCiAgICAgICAgSFtWaXN1YWxpemF0aW9uc106Ojp1aQogICAgICAgIElbU3RyZWFtbGl0IERhc2hib2FyZF06Ojp1aQogICAgZW5kCgogICAgQiAtLT58RG93bmxvYWR8IEMKICAgIEMgLS0-fENTVnwgRAogICAgQSAtLT58UGFyc2V8IEQKICAgIEQgLS0-fE5vcm1hbGl6ZXwgRQogICAgRSAtLT58VHJhbnNmb3JtfCBGCiAgICBGIC0tPnxFeHBvcnR8IEcKICAgIEYgLS0-fFBsb3R8IEgKICAgIEcgLS0-fFN0cmVhbXwgSQogICAgSCAtLT58RW5oYW5jZXwgSQoKICAgIGNsYXNzRGVmIGRhdGEgZmlsbDojMTcyNTU0LHN0cm9rZTojNjBhNWZhLHN0cm9rZS13aWR0aDoycHgsY29sb3I6I2RiZWFmZSxyeDo4LHJ5Ojg7CiAgICBjbGFzc0RlZiBwcm9jIGZpbGw6IzJlMTA2NSxzdHJva2U6I2E3OGJmYSxzdHJva2Utd2lkdGg6MnB4LGNvbG9yOiNmM2U4ZmYscng6OCxyeTo4OwogICAgY2xhc3NEZWYgdWkgZmlsbDojMDY0ZTNiLHN0cm9rZTojMzRkMzk5LHN0cm9rZS13aWR0aDoycHgsY29sb3I6I2QxZmFlNSxyeDo4LHJ5Ojg7CiAgICBzdHlsZSBEYXRhIGZpbGw6IzExMTgyNyxzdHJva2U6IzM3NDE1MSxzdHJva2Utd2lkdGg6MXB4LHJ4OjEwLHJ5OjEwCiAgICBzdHlsZSBMb2dpYyBmaWxsOiMxMTE4Mjcsc3Ryb2tlOiMzNzQxNTEsc3Ryb2tlLXdpZHRoOjFweCxyeDoxMCxyeToxMAogICAgc3R5bGUgVUkgZmlsbDojMTExODI3LHN0cm9rZTojMzc0MTUxLHN0cm9rZS13aWR0aDoxcHgscng6MTAscnk6MTAK">
  <img alt="System Architecture" src="https://mermaid.ink/svg/JSV7aW5pdDogeyd0aGVtZSc6ICdiYXNlJywgJ3RoZW1lVmFyaWFibGVzJzogeyAncHJpbWFyeUNvbG9yJzogJyNmZmYnLCAnbWFpbkJrZyc6ICcjZmZmJywgJ2NsdXN0ZXJCa2cnOiAnI2Y5ZmFmYicsICdjbHVzdGVyQm9yZGVyJzogJyNlNWU3ZWInLCAnbGluZUNvbG9yJzogJyM2YjcyODAnLCAnZm9udEZhbWlseSc6ICdTZWdvZSBVSSwgc2Fucy1zZXJpZicsICdlZGdlTGFiZWxCYWNrZ3JvdW5kJzogJyNmOWZhZmInIH19fSUlCmdyYXBoIExSCiAgICBzdWJncmFwaCBEYXRhIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7RGF0YSBTY3VyY2VzJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Il0KICAgICAgICBkaXJlY3Rpb24gVEIKICAgICAgICBBW1hUQiBTdGF0ZW1lbnRzXTo6OmRhdGEKICAgICAgICBCW05CUCBBcmNoaXZlXTo6OmRhdGEKICAgIGVuZAoKICAgIHN1YmdyYXBoIExvZ2ljIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7UHJvY2Vzc2luZyBQaXBlbGluZSZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgQyhQbGF5d3JpZ2h0IERMKTo6OnByb2MKICAgICAgICBEe0RhdGEgRXh0cmFjdG9yfTo6OnByb2MKICAgICAgICBFW0RhdGVDb252ZXJ0ZXJdOjo6cHJvYwogICAgICAgIEZbREYgUHJvY2Vzc29yXTo6OnByb2MKICAgIGVuZAoKICAgIHN1YmdyYXBoIFVJIFsiJm5ic3A7Jm5ic3A7Jm5ic3A7Jm5ic3A7T3V0cHV0ICYgVmlzdWFsaXphdGlvbiZuYnNwOyZuYnNwOyZuYnNwOyZuYnNwOyJdCiAgICAgICAgZGlyZWN0aW9uIFRCCiAgICAgICAgR1tHb29nbGUgU2hlZXRzXTo6OnVpCiAgICAgICAgSFtWaXN1YWxpemF0aW9uc106Ojp1aQogICAgICAgIElbU3RyZWFtbGl0IERhc2hib2FyZF06Ojp1aQogICAgZW5kCgogICAgQiAtLT58RG93bmxvYWR8IEMKICAgIEMgLS0-fENTVnwgRAogICAgQSAtLT58UGFyc2V8IEQKICAgIEQgLS0-fE5vcm1hbGl6ZXwgRQogICAgRSAtLT58VHJhbnNmb3JtfCBGCiAgICBGIC0tPnxFeHBvcnR8IEcKICAgIEYgLS0-fFBsb3R8IEgKICAgIEcgLS0-fFN0cmVhbXwgSQogICAgSCAtLT58RW5oYW5jZXwgSQoKICAgIGNsYXNzRGVmIGRhdGEgZmlsbDojZWZmNmZmLHN0cm9rZTojM2I4MmY2LHN0cm9rZS13aWR0aDoycHgsY29sb3I6IzFlM2E4YSxyeDo4LHJ5Ojg7CiAgICBjbGFzc0RlZiBwcm9jIGZpbGw6I2Y1ZjNmZixzdHJva2U6IzhiNWNmNixzdHJva2Utd2lkdGg6MnB4LGNvbG9yOiM0YzFkOTUscng6OCxyeTo4OwogICAgY2xhc3NEZWYgdWkgZmlsbDojZWNmZGY1LHN0cm9rZTojMTBiOTgxLHN0cm9rZS13aWR0aDoycHgsY29sb3I6IzA2NGUzYixyeDo4LHJ5Ojg7CiAgICBzdHlsZSBEYXRhIGZpbGw6I2Y5ZmFmYixzdHJva2U6I2U1ZTdlYixzdHJva2Utd2lkdGg6MXB4LHJ4OjEwLHJ5OjEwCiAgICBzdHlsZSBMb2dpYyBmaWxsOiNmOWZhZmIsc3Ryb2tlOiNlNWU3ZWIsc3Ryb2tlLXdpZHRoOjFweCxyeDoxMCxyeToxMAogICAgc3R5bGUgVUkgZmlsbDojZjlmYWZiLHN0cm9rZTojZTVlN2ViLHN0cm9rZS13aWR0aDoxcHgscng6MTAscnk6MTAK">
</picture>

## 🔧 Core Components

- **Data Extraction**: Utilizes `MultiConditionExtractor` for parsing financial transaction descriptions using pattern matching and regular expressions.

- **Date Conversion**: Employs `DateConverter` to standardize date formats and perform date-related calculations.

- **Data Processing**: Uses `DataFrameProcessor` for filtering, grouping, and analyzing financial data.

- **Data Export**: Facilitates Google Sheets integration via `GoogleSpreadsheetExporter`, preserving formatting and supporting multiple sheets.

- **Visualization**: Leverages `matplotlib` and `seaborn` for creating financial-specific plots and interactive visualizations.

- **Web Automation**: Uses `Playwright` for automated browser interactions to download currency exchange rate data.
