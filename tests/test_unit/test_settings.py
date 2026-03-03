"""Unit tests for config/settings.py.

Covers:
- Default field values on a freshly constructed ``Settings`` instance.
- ``validate_tax_rate`` raising ``ValidationError`` for out-of-range values.
- ``validate_tax_rate`` accepting all values in the valid ``[0, 1]`` range.
- ``get_input_file_path()`` returning the correct ``Path``.
- ``get_data_directory_path()`` returning the correct ``Path``.
- Environment variable overrides via ``monkeypatch``.
- Property-based invariant: any float in ``[0, 1]`` is accepted.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from config.settings import Settings

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSettingsDefaults:
    """Settings default values are correct out of the box."""

    def test_settings_default_tax_rate(self) -> None:
        """Default polish_tax_rate is 0.19."""
        # Arrange / Act
        s = Settings()

        # Assert
        assert s.polish_tax_rate == pytest.approx(0.19)

    def test_settings_default_data_directory(self) -> None:
        """Default data_directory is 'data'."""
        # Arrange / Act
        s = Settings()

        # Assert
        assert s.data_directory == "data"

    def test_settings_default_input_file_ends_with_xlsx(self) -> None:
        """Default input file has an .xlsx extension."""
        # Arrange / Act
        s = Settings()

        # Assert
        assert s.default_input_file.endswith(".xlsx")

    def test_settings_default_output_file(self) -> None:
        """Default output file is 'for_google_spreadsheet.csv'."""
        # Arrange / Act
        s = Settings()

        # Assert
        assert s.default_output_file == "for_google_spreadsheet.csv"

    def test_settings_default_nbp_archive_url_contains_nbp(self) -> None:
        """Default nbp_archive_url points to the NBP domain."""
        # Arrange / Act
        s = Settings()

        # Assert
        assert "nbp.pl" in s.nbp_archive_url

    def test_settings_default_nbp_archive_url_is_https(self) -> None:
        """Default nbp_archive_url uses HTTPS."""
        # Arrange / Act
        s = Settings()

        # Assert
        assert s.nbp_archive_url.startswith("https://")


# ---------------------------------------------------------------------------
# validate_tax_rate — invalid values
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateTaxRateInvalid:
    """validate_tax_rate rejects values strictly outside [0, 1]."""

    @pytest.mark.parametrize(
        "invalid_rate",
        [
            1.01,
            1.5,
            2.0,
            100.0,
            -0.01,
            -0.19,
            -1.0,
        ],
    )
    def test_validate_tax_rate_raises_for_out_of_range_value(
        self, invalid_rate: float
    ) -> None:
        """Tax rate outside [0, 1] must raise ValidationError."""
        # Arrange / Act / Assert
        with pytest.raises(ValidationError):
            Settings(POLISH_TAX_RATE=invalid_rate)


# ---------------------------------------------------------------------------
# validate_tax_rate — valid boundary and typical values
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateTaxRateValid:
    """validate_tax_rate accepts all values inside [0, 1]."""

    @pytest.mark.parametrize(
        "valid_rate",
        [
            0.0,
            0.19,
            0.5,
            1.0,
        ],
    )
    def test_validate_tax_rate_accepts_valid_value(self, valid_rate: float) -> None:
        """Tax rate in [0, 1] must be stored unchanged."""
        # Arrange / Act
        s = Settings(POLISH_TAX_RATE=valid_rate)

        # Assert
        assert s.polish_tax_rate == pytest.approx(valid_rate)


# ---------------------------------------------------------------------------
# validate_tax_rate — property-based
# ---------------------------------------------------------------------------


@pytest.mark.property_based
class TestValidateTaxRateProperty:
    """Property: every float in [0, 1] is accepted; everything outside is rejected."""

    @given(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    def test_any_rate_in_unit_interval_is_valid(self, rate: float) -> None:
        """Any float in [0.0, 1.0] must not raise."""
        # Arrange / Act
        s = Settings(POLISH_TAX_RATE=rate)

        # Assert
        assert 0.0 <= s.polish_tax_rate <= 1.0

    @given(
        st.one_of(
            st.floats(max_value=-1e-9, allow_nan=False, allow_infinity=False),
            st.floats(
                min_value=1.0 + 1e-9,
                max_value=1e6,
                allow_nan=False,
                allow_infinity=False,
            ),
        )
    )
    def test_any_rate_outside_unit_interval_is_invalid(self, rate: float) -> None:
        """Any float strictly outside [0.0, 1.0] must raise ValidationError."""
        # Arrange / Act / Assert
        with pytest.raises(ValidationError):
            Settings(POLISH_TAX_RATE=rate)


# ---------------------------------------------------------------------------
# get_input_file_path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetInputFilePath:
    """get_input_file_path() returns a Path built from default_input_file."""

    def test_get_input_file_path_returns_path_instance(self) -> None:
        """Return type is pathlib.Path."""
        # Arrange
        s = Settings()

        # Act
        result = s.get_input_file_path()

        # Assert
        assert isinstance(result, Path)

    def test_get_input_file_path_matches_default_input_file(self) -> None:
        """Returned path matches the default_input_file string."""
        # Arrange
        s = Settings()

        # Act
        result = s.get_input_file_path()

        # Assert
        assert result == Path(s.default_input_file)

    @pytest.mark.parametrize(
        "custom_path",
        [
            "data/my_statement.xlsx",
            "reports/2025_statement.xlsx",
            "input/xtb_export.xlsx",
        ],
    )
    def test_get_input_file_path_reflects_custom_value(self, custom_path: str) -> None:
        """Returned path reflects a custom DEFAULT_INPUT_FILE value."""
        # Arrange
        s = Settings(DEFAULT_INPUT_FILE=custom_path)

        # Act
        result = s.get_input_file_path()

        # Assert
        assert result == Path(custom_path)


# ---------------------------------------------------------------------------
# get_data_directory_path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetDataDirectoryPath:
    """get_data_directory_path() returns a Path built from data_directory."""

    def test_get_data_directory_path_returns_path_instance(self) -> None:
        """Return type is pathlib.Path."""
        # Arrange
        s = Settings()

        # Act
        result = s.get_data_directory_path()

        # Assert
        assert isinstance(result, Path)

    def test_get_data_directory_path_matches_data_directory(self) -> None:
        """Returned path matches the data_directory string."""
        # Arrange
        s = Settings()

        # Act
        result = s.get_data_directory_path()

        # Assert
        assert result == Path(s.data_directory)

    @pytest.mark.parametrize(
        "custom_dir",
        [
            "custom_data",
            "archive/2025",
            "tmp/nbp",
        ],
    )
    def test_get_data_directory_path_reflects_custom_value(
        self, custom_dir: str
    ) -> None:
        """Returned path reflects a custom DATA_DIRECTORY value."""
        # Arrange
        s = Settings(DATA_DIRECTORY=custom_dir)

        # Act
        result = s.get_data_directory_path()

        # Assert
        assert result == Path(custom_dir)


# ---------------------------------------------------------------------------
# Environment variable overrides via monkeypatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSettingsEnvOverrides:
    """Settings fields are overridden by environment variables."""

    def test_polish_tax_rate_overridden_by_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POLISH_TAX_RATE env var overrides the default tax rate."""
        # Arrange
        monkeypatch.setenv("POLISH_TAX_RATE", "0.25")

        # Act
        s = Settings()

        # Assert
        assert s.polish_tax_rate == pytest.approx(0.25)

    def test_data_directory_overridden_by_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DATA_DIRECTORY env var overrides the default directory name."""
        # Arrange
        monkeypatch.setenv("DATA_DIRECTORY", "overridden_data")

        # Act
        s = Settings()

        # Assert
        assert s.data_directory == "overridden_data"

    def test_nbp_archive_url_overridden_by_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NBP_ARCHIVE_URL env var overrides the default URL."""
        # Arrange
        custom_url = "https://custom.nbp.example/archive/"
        monkeypatch.setenv("NBP_ARCHIVE_URL", custom_url)

        # Act
        s = Settings()

        # Assert
        assert s.nbp_archive_url == custom_url

    def test_default_output_file_overridden_by_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DEFAULT_OUTPUT_FILE env var overrides the default output filename."""
        # Arrange
        monkeypatch.setenv("DEFAULT_OUTPUT_FILE", "my_output.csv")

        # Act
        s = Settings()

        # Assert
        assert s.default_output_file == "my_output.csv"
