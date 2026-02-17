"""
Thread-local log context for structured logging with correlation IDs.

Usage:
    from src.observability.log_context import set_log_context, clear_log_context

    set_log_context(trace_id='abc123', tick_id=42, radar_id='KTLX')
    logger.info("Processing radar")   # trace_id, tick_id, radar_id injected

    clear_log_context()

The ContextFilter automatically attaches all stored fields to every
LogRecord so that JSONFormatter (or any formatter) can include them.
"""

import logging
import threading
import uuid
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Thread-local storage
# ---------------------------------------------------------------------------
_ctx = threading.local()


def set_log_context(**fields: Any) -> None:
    """
    Merge *fields* into the current thread's log context.

    Subsequent log records on this thread will include these fields
    (via ContextFilter).  Call ``clear_log_context`` at the end of
    the unit of work.
    """
    if not hasattr(_ctx, 'fields'):
        _ctx.fields = {}
    _ctx.fields.update(fields)


def clear_log_context() -> None:
    """Remove all context fields for the current thread."""
    _ctx.fields = {}


def get_log_context() -> Dict[str, Any]:
    """Return a copy of the current thread's log context."""
    return dict(getattr(_ctx, 'fields', {}))


def new_trace_id() -> str:
    """Generate a short trace ID (12 hex chars)."""
    return uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Logging Filter — injects context fields into every LogRecord
# ---------------------------------------------------------------------------

class ContextFilter(logging.Filter):
    """
    Logging filter that copies thread-local context fields onto LogRecord.

    Attach to a handler or the root logger:

        logging.getLogger().addFilter(ContextFilter())

    After that, any formatter can reference the fields as record attributes.
    """

    # Fields the filter will inject (and their defaults if not in context).
    KNOWN_FIELDS = (
        'trace_id', 'tick_id', 'job_id',
        'radar_id', 'scan_key',
        'event_id', 'swath_id',
        'duration_ms', 'status',
    )

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = getattr(_ctx, 'fields', {})
        for key in self.KNOWN_FIELDS:
            if not hasattr(record, key):
                val = ctx.get(key)
                if val is not None:
                    setattr(record, key, val)
        return True


# ---------------------------------------------------------------------------
# Install helper — call once at startup
# ---------------------------------------------------------------------------

def install_context_filter() -> None:
    """
    Add ContextFilter to the root logger so all loggers inherit it.

    Safe to call multiple times (idempotent).
    """
    root = logging.getLogger()
    for f in root.filters:
        if isinstance(f, ContextFilter):
            return
    root.addFilter(ContextFilter())
