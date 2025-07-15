# 💼 Financial Data Processing Pipeline

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

#### 🚀 CI/CD Pipeline Features
- **Multi-platform testing**: Tests run on Ubuntu, Windows, and macOS
- **Multi-version support**: Compatible with Python 3.9, 3.10, 3.11, 3.12, and 3.13
- **Code quality checks**: Automated linting (flake8), formatting (black), import sorting (isort), and type checking (mypy)
- **Security scanning**: Automated vulnerability detection with bandit and safety
- **Coverage reporting**: Comprehensive test coverage with Codecov integration

#### ⚡ Development Tools
- **Pre-commit hooks**: Automated code quality checks before commits
- **Cross-platform scripts**: Testing utilities for different operating systems
- **Comprehensive documentation**: Detailed testing guides in `docs/TESTING.md`

## 📖 Usage Guide

### 1. 📥 Data Acquisition

#### Using Playwright to Download Currency Archive

The `playwright_download_currency_archive.py` script automates the download of currency exchange rate data from the NBP Exchange Rates Archive. This script uses Playwright to interact with the website and download the required CSV files.

To run the script, execute the following command:
```bash
python playwright_download_currency_archive.py
```

This script will download files for the last 3 years, such as `archiwum_tab_a_<YYYY>.csv` (e.g., `archiwum_tab_a_2025.csv`, `archiwum_tab_a_2024.csv`, `archiwum_tab_a_2023.csv`). These files are necessary for the data processing pipeline.

### 2. ⚙️ Data Processing

Execute the main processing script:
```bash
python main.py
```

### 3. 📊 Google Sheets Integration

#### Automated Export

Use `GoogleSpreadsheetExporter` to export processed data to Google Sheets. Ensure all dependencies are installed and API credentials are configured for seamless integration.

### 4. 📈 Visualization (External Repository)

To visualize the exported data, use the [Streamlit Dividend Dashboard](https://github.com/darekwojciechowski/Streamlit-Dividend-Dashboard) repository, which I created specifically for visualizing this data and is ready to use.  
Simply take the exported CSV file from this project and use it as input in the Streamlit dashboard for interactive data visualization.

![Dashboard Demo](assets/streamlit-dashboard-demo.gif)

## 🔧 Core Components

- **Data Extraction**: Utilizes `MultiConditionExtractor` for parsing financial transaction descriptions using pattern matching and regular expressions.

- **Date Conversion**: Employs `DateConverter` to standardize date formats and perform date-related calculations.

- **Data Processing**: Uses `DataFrameProcessor` for filtering, grouping, and analyzing financial data.

- **Data Export**: Facilitates Google Sheets integration via `GoogleSpreadsheetExporter`, preserving formatting and supporting multiple sheets.

- **Visualization**: Leverages `matplotlib` and `seaborn` for creating financial-specific plots and interactive visualizations.

- **Web Automation**: Uses Playwright for automated browser interactions to download currency exchange rate data.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
