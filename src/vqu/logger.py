import logging
import os
import sys


OUTPUT_LOGGER_NAME = "vqu.cli.output"


def _setup_output_logger() -> logging.Logger:
    """Configures and returns the output logger."""
    logger = logging.getLogger(OUTPUT_LOGGER_NAME)

    logger.setLevel(logging.INFO)
    logger.propagate = "PYTEST_CURRENT_TEST" in os.environ

    # Check if the exact handler is already configured. Pytest capsys creates its own stdout stream,
    # so a new handler will be added in that case.
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler) and h.stream == sys.stdout:
            return logger

    # Clear all handlers and add a new one
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    return logger


output_logger = _setup_output_logger()
