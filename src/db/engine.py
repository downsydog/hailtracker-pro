"""
Central Database Engine for HailTracker Pro

Provides a unified connection factory supporting:
  - SQLite (default, zero-config for dev)
  - PostgreSQL (production, via DATABASE_URL)

Usage:
    from src.db.engine import get_connection, get_engine_info

    # Context-managed connection (auto-commit on success, rollback on error)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")

    # Engine info for health checks
    info = get_engine_info()
    # {'backend': 'sqlite', 'database': 'database/hailtracker_pro.db', ...}

Environment:
    DATABASE_URL  - Connection string. Defaults to sqlite:///database/hailtracker_pro.db
                    Examples:
                      sqlite:///database/hailtracker_pro.db
                      postgresql://user:pass@localhost:5432/hailtracker
    DB_POOL_MIN   - Min pool size for Postgres (default: 2)
    DB_POOL_MAX   - Max pool size for Postgres (default: 10)
"""

import os
import sqlite3
import threading
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state (thread-safe via _lock)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_pg_pool = None  # psycopg2 SimpleConnectionPool (lazy)
_initialized = False

# ---------------------------------------------------------------------------
# Configuration (read once from env)
# ---------------------------------------------------------------------------
_DEFAULT_SQLITE_URL = 'sqlite:///database/hailtracker_pro.db'


def _get_database_url() -> str:
    return os.environ.get('DATABASE_URL', _DEFAULT_SQLITE_URL)


def _parse_url(url: str) -> Dict[str, Any]:
    """Parse DATABASE_URL into backend + connection params."""
    if url.startswith('sqlite'):
        path = url.replace('sqlite:///', '').replace('sqlite://', '')
        if not path:
            path = 'database/hailtracker_pro.db'
        return {'backend': 'sqlite', 'path': path}
    elif url.startswith('postgresql') or url.startswith('postgres'):
        return {'backend': 'postgresql', 'dsn': url}
    else:
        raise ValueError(f"Unsupported DATABASE_URL scheme: {url}")


# ---------------------------------------------------------------------------
# SQLite helpers
# ---------------------------------------------------------------------------

def _sqlite_connect(path: str) -> sqlite3.Connection:
    """Create a SQLite connection with recommended pragmas."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL mode for concurrent readers + single writer
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


# ---------------------------------------------------------------------------
# PostgreSQL helpers
# ---------------------------------------------------------------------------

def _get_pg_pool():
    """Lazy-init PostgreSQL connection pool (thread-safe)."""
    global _pg_pool
    if _pg_pool is not None:
        return _pg_pool

    with _lock:
        if _pg_pool is not None:
            return _pg_pool

        try:
            from psycopg2 import pool as pg_pool
            import psycopg2.extras
        except ImportError:
            raise ImportError(
                "psycopg2 not installed. "
                "Install with: pip install psycopg2-binary"
            )

        parsed = _parse_url(_get_database_url())
        min_conns = int(os.environ.get('DB_POOL_MIN', '2'))
        max_conns = int(os.environ.get('DB_POOL_MAX', '10'))

        _pg_pool = pg_pool.ThreadedConnectionPool(
            min_conns, max_conns,
            parsed['dsn'],
        )
        logger.info(
            "PostgreSQL pool created: min=%d max=%d",
            min_conns, max_conns,
        )
        return _pg_pool


def _pg_connect():
    """Get a connection from the PostgreSQL pool."""
    pool = _get_pg_pool()
    conn = pool.getconn()
    return conn


def _pg_release(conn):
    """Return a PostgreSQL connection to the pool."""
    pool = _get_pg_pool()
    pool.putconn(conn)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@contextmanager
def get_connection(database_url: Optional[str] = None):
    """
    Context-managed database connection.

    Yields a connection that auto-commits on clean exit,
    rolls back on exception.

    Args:
        database_url: Override DATABASE_URL for this call.
                      If None, reads from env / default.

    Usage:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM hail_events LIMIT 10")
            rows = cur.fetchall()
    """
    url = database_url or _get_database_url()
    parsed = _parse_url(url)

    if parsed['backend'] == 'sqlite':
        conn = _sqlite_connect(parsed['path'])
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = _pg_connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _pg_release(conn)


def get_engine_info() -> Dict[str, Any]:
    """
    Return engine metadata for health checks and diagnostics.

    Returns dict with:
        backend: 'sqlite' or 'postgresql'
        database: path or DSN (password masked)
        pool_min / pool_max: pool size (postgres only)
        wal_mode: True/False (sqlite only)
    """
    url = _get_database_url()
    parsed = _parse_url(url)
    info: Dict[str, Any] = {'backend': parsed['backend']}

    if parsed['backend'] == 'sqlite':
        info['database'] = parsed['path']
        # Check if WAL mode is active
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute('PRAGMA journal_mode')
                mode = cur.fetchone()[0]
                info['wal_mode'] = mode.lower() == 'wal'
        except Exception:
            info['wal_mode'] = False
    else:
        # Mask password in DSN for display
        dsn = parsed['dsn']
        import re
        masked = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', dsn)
        info['database'] = masked
        info['pool_min'] = int(os.environ.get('DB_POOL_MIN', '2'))
        info['pool_max'] = int(os.environ.get('DB_POOL_MAX', '10'))

    return info


def close_engine():
    """Close the connection pool (call on shutdown)."""
    global _pg_pool
    with _lock:
        if _pg_pool is not None:
            try:
                _pg_pool.closeall()
            except Exception as e:
                logger.warning("Error closing PG pool: %s", e)
            _pg_pool = None
            logger.info("PostgreSQL pool closed")


def placeholder() -> str:
    """Return the parameter placeholder for the active backend.

    Returns '?' for SQLite, '%s' for PostgreSQL.
    """
    parsed = _parse_url(_get_database_url())
    return '?' if parsed['backend'] == 'sqlite' else '%s'


def is_postgres() -> bool:
    """True if the active backend is PostgreSQL."""
    return _parse_url(_get_database_url())['backend'] == 'postgresql'
