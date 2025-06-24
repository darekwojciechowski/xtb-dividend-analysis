# Project Structure

```
xtb-dividend-analysis/
│
├── assets/                         # Static files, sample exports, documentation assets
│   ├── for_google_spreadsheet.csv  # Sample export file
│   ├── Net_Dividend_Chart.png      # Sample chart output
│   └── ...
│
├── config/                         # Configuration files
│   └── logging_config.py           # Centralized logging configuration
│
├── data/                           # Input data files (XLSX, CSV)
│   ├── demo_XTB_broker_statement.xlsx
│   ├── archiwum_tab_a_2025.csv
│   └── ...
│
├── data_acquisition/               # Data acquisition scripts
│   └── playwright_download_currency_archive.py  # Currency data download automation
│
├── data_processing/                # Core data processing modules
│   ├── dataframe_processor.py      # Main DataFrame processing logic
│   ├── exporter.py                 # Export logic (e.g., to Google Sheets/CSV)
│   ├── file_paths.py               # File path and validation utilities
│   ├── import_data_xlsx.py         # XLSX import and preprocessing
│   ├── extractor.py                # Condition extraction logic
│   └── date_converter.py           # Date parsing and conversion
│
├── docs/                           # Project documentation
│   ├── PROJECT_STRUCTURE.md        # This file - project structure documentation
│   ├── TESTING.md                  # Comprehensive testing guide
│   └── AUTOMATED_TESTING_SUMMARY.md # Testing setup summary
│
├── logs/                           # Application log files (auto-created)
│   └── app.log                     # Main application log
│
├── output/                         # Generated files and exports (auto-created)
│   └── for_google_spreadsheet.csv  # Generated CSV for Google Sheets import
│
├── scripts/                        # Utility scripts for development and testing
│   ├── run_tests.py                # Cross-platform test runner (Python)
│   ├── run_tests.ps1               # PowerShell test runner (Windows)
│   ├── pre-commit-hook-example.sh  # Git pre-commit hook example
│   └── SCRIPTS_GUIDE.md            # Scripts documentation and usage guide
│
├── tests/                          # Unit tests and test utilities
│   ├── test_dataframe_processor.py # Tests for DataFrame processing logic
│   ├── test_date_converter.py      # Tests for date conversion
│   ├── test_exporter.py            # Tests for export functionality
│   └── test_main.py                # Integration tests
│
├── visualization/                  # Visualization utilities
│   ├── chart_net_dividend.py       # Chart generation logic
│   ├── plot_style.py               # Plotting style configuration
│   └── ticker_colors.py            # Ticker color mapping and helpers
│
├── main.py                         # Main entry point for the pipeline
│
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Project configuration and dependencies (Poetry)
├── poetry.lock                     # Locked dependency versions
├── tox.ini                         # Multi-version testing configuration
├── Makefile                        # Development commands and shortcuts
│
├── .gitignore                      # Git ignore rules
├── .pre-commit-config.yaml         # Pre-commit hooks configuration
├── README.md                       # Project documentation and usage
│
└── LICENSE                         # License file
```

**Notes for this project:**
- `assets/` contains static files, sample exports, and documentation assets.
- `config/` centralizes all configuration files (logging, settings, future configurations).
- `data/` is for raw input files, not to be versioned if they are large or sensitive.
- `data_acquisition/` contains scripts for automated data collection and downloads.
- `data_processing/` is the main package for all ETL (Extract, Transform, Load) logic.
- `docs/` contains project documentation, testing guides, and specifications.
- `logs/` stores application log files (auto-created, should be in .gitignore).
- `output/` contains generated files and exports (auto-created, consider .gitignore for large files).
- `scripts/` contains utility scripts for testing, development, and project maintenance.
- `tests/` contains unit tests with parametrized test cases for comprehensive coverage.
- `visualization/` handles plotting, charting, and visual styling utilities.
- `main.py` is the only script that should be run directly for the main workflow.
- Configuration files (`tox.ini`, `.pre-commit-config.yaml`) remain in root for tool discovery.
- Poetry is used for dependency management (`pyproject.toml`, `poetry.lock`).
- All configuration, credentials, and sensitive data should be excluded via `.gitignore`.
- Folders `logs/` and `output/` are automatically created by the application if they don't exist.
