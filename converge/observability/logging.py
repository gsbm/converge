import json
import logging
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings for structured logging.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
        }

        # Add extra fields if present
        if hasattr(record, "props"):
            log_obj.update(record.props) # type: ignore

        return json.dumps(log_obj)

def configure_logging(level: int = logging.INFO, *, json_format: bool = False) -> None:
    """
    Configure the root logger with stream handlers and formatting.

    Removes existing handlers to avoid duplication.

    Args:
        level (int): The logging level to set (e.g. logging.INFO).
        json_format (bool): If True, use structured JSON logging. If False, use text format.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        ))

    root_logger.addHandler(handler)

def get_logger(name: str) -> logging.Logger:
    """
    Retrieve a named logger instance.

    Args:
        name (str): The name of the logger (typically __name__).

    Returns:
        logging.Logger: The configured logger instance.
    """
    return logging.getLogger(name)

def log_struct(logger: logging.Logger, level: int, message: str, **kwargs: Any) -> None:
    """
    Log a message with structured data as extra fields.

    This ensures that when JSON formatting is enabled, the kwargs appear
    as top-level keys in the JSON output.

    Args:
        logger (logging.Logger): The logger instance to use.
        level (int): The severity level of the log message.
        message (str): The primary log message.
        **kwargs: Arbitrary key-value pairs to attach to the log context.
    """
    if logger.isEnabledFor(level):
        logger._log(level, message, (), extra={"props": kwargs})
