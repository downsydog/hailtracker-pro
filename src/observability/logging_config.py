"""
Structured Logging Configuration

Environment:
    LOG_FORMAT - 'text' (default) or 'json'
    LOG_LEVEL  - DEBUG, INFO, WARNING, ERROR (default: INFO)
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        if record.exc_info and record.exc_info[1]:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Include extra fields if present
        for key in ('radar_id', 'event_id', 'task_name', 'duration_ms',
                     'status_code', 'method', 'path', 'request_id'):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        return json.dumps(log_entry, default=str)


def configure_logging(
    log_format: str = None,
    log_level: str = None,
):
    """
    Configure application logging.

    Args:
        log_format: 'text' or 'json'. If None, reads LOG_FORMAT env.
        log_level: 'DEBUG', 'INFO', etc. If None, reads LOG_LEVEL env.
    """
    fmt = log_format or os.environ.get('LOG_FORMAT', 'text')
    level_str = log_level or os.environ.get('LOG_LEVEL', 'INFO')
    level = getattr(logging, level_str.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if fmt.lower() == 'json':
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

    root.addHandler(handler)

    # Quiet down noisy third-party loggers
    for noisy in ('urllib3', 'botocore', 's3transfer', 'werkzeug'):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging configured: format=%s level=%s", fmt, level_str
    )
