# Project Structure

```
xtb-dividend-analysis/
│
├── assets/                         # Static files, sample exports (e.g., for_google_spreadsheet.csv)
│
├── data/                           # Input data files (XLSX, CSV)
│   ├── demo_XTB_broker_statement.xlsx
│   ├── archiwum_tab_a_2025.csv
│   └── ...
│
├── data_processing/                # Core data processing modules
│   ├── dataframe_processor.py      # Main DataFrame processing logic
│   ├── exporter.py                 # Export logic (e.g., to Google Sheets/CSV)
│   ├── file_paths.py               # File path and validation utilities
│   ├── import_data_xlsx.py         # XLSX import and preprocessing
│   ├── extractor.py                # Condition extraction logic
│   └── date_converter.py           # Date parsing and conversion
│
├── visualization/                  # Visualization utilities
│   └── ticker_colors.py            # Ticker color mapping and helpers
│
├── playwright_download_currency_archive.py  # Script for downloading currency data using Playwright
│
├── logging_config.py               # Logging configuration
│
├── main.py                         # Main entry point for the pipeline
│
├── requirements.txt                # Python dependencies
│
├── .gitignore                      # Git ignore rules
│
├── README.md                       # Project documentation and usage
│
└── LICENSE                         # License file
```

**Notes for this project:**
- `assets/` contains only static or example output files, not code.
- `data/` is for raw input files, not to be versioned if they are large or sensitive.
- `data_processing/` is the main package for all ETL (Extract, Transform, Load) logic.
- `visualization/` is for any plotting or color utilities.
- `main.py` is the only script that should be run directly for the main workflow.
- `playwright_download_currency_archive.py` is a utility script for automated data acquisition.
- `logging_config.py` centralizes logging setup for consistency.
- All configuration, credentials, and sensitive data should be excluded via `.gitignore`.
- For larger projects, consider adding `tests/` and `docs/` directories.
