import logging
import sys

from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from vqu.logger import _setup_output_logger


class TestSetupOutputLogger:
    """Unit tests for the _setup_output_logger function."""

    def test_logger_configuration(self) -> None:
        """Should return a logger with the correct name and INFO level."""
        logger = _setup_output_logger()
        assert logger.name == "vqu.cli.output"
        assert logger.level == logging.INFO

    def test_handler_and_formatter(self) -> None:
        """Should add a StreamHandler pointing to stdout with the correct format."""
        logger = _setup_output_logger()

        # Get the last handler added by the function
        handler = logger.handlers[-1]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream == sys.stdout
        assert handler.formatter is not None
        assert handler.formatter._fmt == "%(message)s"

    def test_propagate_in_pytest(self, mocker: MockerFixture) -> None:
        """Should have propagate set to True when running under pytest."""
        # Since we are currently running pytest, "PYTEST_CURRENT_TEST" is in os.environ
        logger = _setup_output_logger()
        assert logger.propagate is True

    def test_propagate_outside_pytest(self, monkeypatch: MonkeyPatch) -> None:
        """Should have propagate set to False when not running under pytest."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        logger = _setup_output_logger()
        assert logger.propagate is False

    def test_idempotency(self) -> None:
        """Should not add duplicate handlers if one already exists for stdout."""
        # Ensure a clean state first
        logger = logging.getLogger("vqu.cli.output")
        logger.handlers.clear()

        # First setup
        _setup_output_logger()
        assert len(logger.handlers) == 1
        first_handler = logger.handlers[0]

        # Second setup
        _setup_output_logger()
        assert len(logger.handlers) == 1
        assert logger.handlers[0] is first_handler

    def test_clears_existing_non_stdout_handlers(self) -> None:
        """Should clear existing handlers if no stdout handler is present."""
        logger = logging.getLogger("vqu.cli.output")
        logger.handlers.clear()

        # Add a non-stdout handler (e.g., NullHandler)
        dummy_handler = logging.NullHandler()
        logger.addHandler(dummy_handler)
        assert dummy_handler in logger.handlers

        # Act
        _setup_output_logger()

        # Assert: dummy_handler should be cleared, and only the stdout handler should remain
        assert dummy_handler not in logger.handlers
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        assert logger.handlers[0].stream == sys.stdout
