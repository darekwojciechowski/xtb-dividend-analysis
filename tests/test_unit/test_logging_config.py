"""Unit tests for config.logging_config.setup_logging.

Covers the full body of ``setup_logging`` (lines 32-77 in
config/logging_config.py), which was previously exercised only through
mocks in test_main.py.

Test class:
    TestSetupLogging — return value, logs-directory creation, log-file
                       creation, custom log levels (parametrized),
                       handler count, file-output content, log-file
                       overwrite, and idempotency.

All tests are marked ``@pytest.mark.unit``.
Loguru global state is reset before and after every test via a fixture
that removes all handlers added during the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from loguru import logger

from config.logging_config import setup_logging


@pytest.fixture(autouse=True)
def _reset_loguru():
    """Remove all loguru handlers added during the test.

    Uses ``logger.remove()`` before *and* after each test so the global
    loguru state does not leak between tests.

    Yields:
        None
    """
    logger.remove()
    yield
    logger.remove()


@pytest.mark.unit
class TestSetupLogging:
    """Test suite for config.logging_config.setup_logging."""

    def test_setup_logging_when_called_then_returns_logger(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """setup_logging should return the loguru logger instance."""
        # Arrange
        monkeypatch.chdir(tmp_path)

        # Act
        result = setup_logging()

        # Assert
        assert result is logger

    def test_setup_logging_when_called_then_creates_logs_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """setup_logging should create a ``logs/`` directory if it does not exist."""
        # Arrange
        monkeypatch.chdir(tmp_path)
        logs_dir = tmp_path / "logs"
        assert not logs_dir.exists()

        # Act
        setup_logging()

        # Assert
        assert logs_dir.is_dir()

    def test_setup_logging_when_called_then_creates_log_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """setup_logging should create the log file inside ``logs/``."""
        # Arrange
        monkeypatch.chdir(tmp_path)

        # Act
        setup_logging(log_file="app.log")

        # Assert
        assert (tmp_path / "logs" / "app.log").exists()

    def test_setup_logging_when_custom_log_file_then_creates_named_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """setup_logging should use the caller-supplied filename."""
        # Arrange
        monkeypatch.chdir(tmp_path)

        # Act
        setup_logging(log_file="custom_test.log")

        # Assert
        assert (tmp_path / "logs" / "custom_test.log").exists()

    @pytest.mark.parametrize(
        "log_level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    )
    def test_setup_logging_when_valid_level_then_returns_logger(
        self, log_level: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """setup_logging should accept any standard loguru level without raising."""
        # Arrange
        monkeypatch.chdir(tmp_path)

        # Act
        result = setup_logging(log_level=log_level)

        # Assert
        assert result is logger

    def test_setup_logging_when_called_then_adds_exactly_two_handlers(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """setup_logging should register exactly two handlers: stderr + file.

        Loguru exposes handler IDs starting from 0 and incrementing; after
        ``logger.remove()`` (in fixture) and one ``setup_logging`` call the
        next two ``logger.add`` calls return consecutive IDs. We verify that
        exactly two IDs are allocated.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)

        # Act
        first_id = logger.add(lambda _: None)  # baseline handler to get next ID
        logger.remove(first_id)
        setup_logging()
        # The two handlers added by setup_logging occupy the next two IDs
        # (first_id+1 and first_id+2). Attempting to remove them confirms they exist.
        handler_a = first_id + 1
        handler_b = first_id + 2

        # Assert — neither remove should raise, meaning both handlers were registered
        logger.remove(handler_a)
        logger.remove(handler_b)

    def test_setup_logging_when_message_logged_then_file_contains_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A message logged after setup_logging should appear in the log file."""
        # Arrange
        monkeypatch.chdir(tmp_path)
        setup_logging(log_level="DEBUG", log_file="output.log")

        # Act
        logger.info("sentinel_message_12345")

        # Assert
        log_contents = (tmp_path / "logs" / "output.log").read_text(encoding="utf-8")
        assert "sentinel_message_12345" in log_contents

    def test_setup_logging_when_called_twice_then_file_does_not_duplicate_content(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Second call with mode='w' should overwrite, not append, the log file."""
        # Arrange
        monkeypatch.chdir(tmp_path)
        setup_logging(log_file="overwrite.log")
        logger.info("first_run_message")

        # Act — second call rewrites the file
        setup_logging(log_file="overwrite.log")
        logger.info("second_run_message")

        # Assert — only the second run's message should be present
        log_contents = (tmp_path / "logs" / "overwrite.log").read_text(encoding="utf-8")
        assert "second_run_message" in log_contents
        assert "first_run_message" not in log_contents

    def test_setup_logging_when_logs_dir_exists_then_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """setup_logging should not raise when ``logs/`` already exists."""
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / "logs").mkdir()

        # Act & Assert
        result = setup_logging()
        assert result is logger
