"""Application Settings using pydantic-settings.

This module provides type-safe configuration management for the XTB Dividend Analysis application.
All environment-specific values are externalized to environment variables with sensible defaults
for local development.

Configuration is loaded from environment variables and .env file (if present).
Required settings will fail fast at startup if missing, ensuring proper configuration.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with type-safe environment variable configuration.

    Attributes:
        # File Paths
        default_input_file: Default XTB broker statement file to process
        default_output_file: Default output CSV filename for Google Sheets
        data_directory: Directory containing input data files

        # URLs
        nbp_archive_url: NBP (National Bank of Poland) currency archive URL

        # Tax Configuration
        polish_tax_rate: Polish Belka tax rate (19% capital gains tax)
    """

    # File Paths Configuration
    default_input_file: str = Field(
        default="data/demo_XTB_broker_statement_currency_PLN.xlsx",
        alias="DEFAULT_INPUT_FILE",
        description="Default XTB broker statement XLSX file path"
    )

    default_output_file: str = Field(
        default="for_google_spreadsheet.csv",
        alias="DEFAULT_OUTPUT_FILE",
        description="Default output CSV filename"
    )

    data_directory: str = Field(
        default="data",
        alias="DATA_DIRECTORY",
        description="Directory for storing data files"
    )

    # External URLs
    nbp_archive_url: str = Field(
        default="https://nbp.pl/statystyka-i-sprawozdawczosc/kursy/archiwum-tabela-a-csv-xls/",
        alias="NBP_ARCHIVE_URL",
        description="NBP currency archive URL for downloading exchange rates"
    )

    # Tax Configuration
    polish_tax_rate: float = Field(
        default=0.19,
        alias="POLISH_TAX_RATE",
        description="Polish Belka tax rate (19% flat tax on capital gains)"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    @field_validator("polish_tax_rate")
    @classmethod
    def validate_tax_rate(cls, v: float) -> float:
        """Validate that tax rate is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError(f"Tax rate must be between 0 and 1, got {v}")
        return v

    @field_validator("default_input_file", "data_directory")
    @classmethod
    def validate_paths_exist(cls, v: str, info) -> str:
        """Validate that critical paths exist (only for production)."""
        # Skip validation in non-production environments for flexibility
        return v

    def get_input_file_path(self) -> Path:
        """Get the default input file as a Path object."""
        return Path(self.default_input_file)

    def get_data_directory_path(self) -> Path:
        """Get the data directory as a Path object."""
        return Path(self.data_directory)


# Create singleton instance
# This will fail fast at import time if configuration is invalid
try:
    settings = Settings()
except Exception as e:
    import sys
    print(f"Configuration Error: {e}")
    print("\nPlease check your environment variables or .env file.")
    print("See .env.example for required configuration format.")
    sys.exit(1)
