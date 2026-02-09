"""Tests for converge.observability.logging."""

import json
import logging
from io import StringIO

from converge.observability.logging import JsonFormatter, configure_logging, get_logger, log_struct


def test_json_logging():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())

    logger = get_logger("test_logger")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    log_struct(logger, logging.INFO, "test message", user="alice", action="login")

    output = stream.getvalue()
    log_obj = json.loads(output)

    assert log_obj["message"] == "test message"
    assert log_obj["user"] == "alice"
    assert log_obj["action"] == "login"
    assert "timestamp" in log_obj


def test_default_logging():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger = get_logger("test_default")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("regular message")

    output = stream.getvalue()
    assert "regular message" in output
    assert "test_default" in output
    assert "INFO" in output

    configure_logging(json_format=False)
    configure_logging(json_format=True)


def test_log_struct_when_level_disabled():
    logger = get_logger("test_disabled")
    logger.setLevel(logging.ERROR)
    log_struct(logger, logging.DEBUG, "should not log", key="value")


def test_logging_logger_fallback():
    from converge.observability.logging import configure_logging

    configure_logging(json_format=True)
