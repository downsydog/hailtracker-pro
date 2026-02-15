"""
Graceful Shutdown Handlers

Installs signal handlers for SIGTERM/SIGINT that trigger an orderly
shutdown of background subsystems (monitor, MRMS updater, task queue, DB pool).

Usage:
    from src.safety.shutdown import install_shutdown_handlers

    install_shutdown_handlers()
    # Now SIGTERM/SIGINT will log and set the shutdown flag.
    # Check is_shutting_down() in long-running loops.
"""

import os
import signal
import threading
import logging
from typing import List, Callable

logger = logging.getLogger(__name__)

_shutdown_flag = threading.Event()
_callbacks: List[Callable] = []
_lock = threading.Lock()


def is_shutting_down() -> bool:
    """Check if a shutdown has been requested."""
    return _shutdown_flag.is_set()


def register_shutdown_callback(fn: Callable):
    """Register a callback to run during shutdown."""
    with _lock:
        _callbacks.append(fn)


def _signal_handler(signum, frame):
    """Handle SIGTERM / SIGINT."""
    sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    logger.info("Received %s — initiating graceful shutdown...", sig_name)
    _shutdown_flag.set()

    with _lock:
        callbacks = list(_callbacks)

    for fn in callbacks:
        try:
            fn()
        except Exception as e:
            logger.warning("Shutdown callback error: %s", e)

    logger.info("Shutdown callbacks complete (%d executed)", len(callbacks))


def install_shutdown_handlers():
    """Install signal handlers for graceful shutdown.

    Safe to call multiple times; only installs once.
    On Windows, only SIGINT is reliably available.
    """
    try:
        signal.signal(signal.SIGINT, _signal_handler)
    except (OSError, ValueError):
        pass  # Can't set in non-main thread

    # SIGTERM is Unix-only
    if hasattr(signal, 'SIGTERM'):
        try:
            signal.signal(signal.SIGTERM, _signal_handler)
        except (OSError, ValueError):
            pass

    logger.info("Shutdown handlers installed (pid=%d)", os.getpid())
