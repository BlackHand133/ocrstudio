# modules/logger.py

import json as _json
import os
import logging
import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

from modules.constants import (
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_FILE_NAME,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
)


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line — useful for Docker/headless log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        obj = {
            "ts":      datetime.datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return _json.dumps(obj, ensure_ascii=False)


def setup_logging(
    root_dir: str,
    level: str = "DEBUG",
    log_format: Optional[str] = None,
) -> logging.Logger:
    """
    Configure application logging with rotation.

    Creates the log directory, attaches a RotatingFileHandler (capped at
    LOG_MAX_BYTES with LOG_BACKUP_COUNT backups) and a StreamHandler.
    Both constants come from modules.constants so they stay in sync with
    the rest of the configuration.

    Args:
        root_dir:   Project root directory — logs go to <root_dir>/output/logs/
        level:      Log level string ("DEBUG", "INFO", "WARNING", "ERROR").
                    Callers can pass config.get('logging.level', 'INFO') here.
        log_format: ``"json"`` to emit one JSON object per line (ideal for Docker
                    headless / log aggregators).  Any other value (or ``None``)
                    falls back to the human-readable ``LOG_FORMAT`` constant.

    Returns:
        The "TextDetGUI" logger instance.
    """
    log_dir = os.path.join(root_dir, "output", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, LOG_FILE_NAME)

    # Remove any handlers attached in a previous call (e.g., during testing)
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    numeric_level = getattr(logging, level.upper(), logging.DEBUG)

    # Choose formatter: JSON for headless/Docker, plain text otherwise
    if log_format == "json":
        formatter: logging.Formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Rotating file handler — uses constants defined in modules/constants.py
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger.setLevel(numeric_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger = logging.getLogger("TextDetGUI")
    logger.info(
        "Logging initialised — level=%s format=%s, file=%s (max %dMB × %d backups)",
        level.upper(),
        log_format or "text",
        log_file,
        LOG_MAX_BYTES // (1024 * 1024),
        LOG_BACKUP_COUNT,
    )
    return logger
