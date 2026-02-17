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

    # Legacy-style connection (must call .close() when done)
    conn = get_raw_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    conn.commit()
    conn.close()

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
import hashlib
import sqlite3
import threading
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

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
# PG Raw Connection Proxy (pool-safe drop-in for legacy code)
# ---------------------------------------------------------------------------

class _PGRawConnection:
    """
    Wraps a pooled PostgreSQL connection so that .close() returns it to the
    pool instead of destroying it.  Cursors use RealDictCursor by default so
    dict(row) works the same as sqlite3.Row.
    """

    def __init__(self, conn):
        self._conn = conn
        try:
            import psycopg2.extras
            self._cursor_factory = psycopg2.extras.RealDictCursor
        except ImportError:
            self._cursor_factory = None

    # -- connection API -------------------------------------------------------

    def cursor(self):
        if self._cursor_factory:
            return self._conn.cursor(cursor_factory=self._cursor_factory)
        return self._conn.cursor()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        _pg_release(self._conn)

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params or ())
        return cur

    def executescript(self, sql_text: str):
        """PG equivalent of sqlite3.Connection.executescript()."""
        cur = self._conn.cursor()
        for stmt in _split_sql(sql_text):
            if stmt.strip():
                cur.execute(stmt)
        return cur

    def fetchone(self):
        return self._conn.cursor().fetchone()

    # -- context manager (with conn: ...) ------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

    # -- sqlite3 compat stubs ------------------------------------------------

    @property
    def row_factory(self):
        return None

    @row_factory.setter
    def row_factory(self, val):
        pass  # PG uses cursor_factory; ignore sqlite row_factory


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


def get_raw_connection(database_url: Optional[str] = None):
    """
    Return a non-context-managed database connection.

    For SQLite, returns a standard sqlite3.Connection (with Row factory).
    For PostgreSQL, returns a _PGRawConnection whose .close() returns the
    underlying connection to the pool and whose cursors are RealDictCursor.

    Caller **must** call .close() when finished.

    For new code, prefer the context-managed ``get_connection()``.
    """
    url = database_url or _get_database_url()
    parsed = _parse_url(url)

    if parsed['backend'] == 'sqlite':
        return _sqlite_connect(parsed['path'])
    else:
        return _PGRawConnection(_pg_connect())


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


# ---------------------------------------------------------------------------
# Schema initialization (PostGIS) with version tracking
# ---------------------------------------------------------------------------

_schema_initialized = False


def ensure_schema() -> None:
    """
    Run numbered PostGIS migration files from ``migrations/`` if the backend
    is PostgreSQL.

    Creates a ``schema_migrations`` table to track which versions have been
    applied.  Each migration file is named ``NNN_description.sql`` where NNN
    is a zero-padded integer version.

    For SQLite, this is a no-op (schemas are loaded via .sql files or inline
    CREATE TABLE IF NOT EXISTS).

    Safe to call multiple times (idempotent).
    """
    global _schema_initialized
    if _schema_initialized:
        return

    if not is_postgres():
        _schema_initialized = True
        return

    with get_connection() as conn:
        cur = conn.cursor()

        # Ensure PostGIS extension
        cur.execute(
            "SELECT 1 FROM pg_extension WHERE extname = 'postgis'"
        )
        if cur.fetchone() is None:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")

        # Schema version tracking table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version   INTEGER PRIMARY KEY,
                filename  TEXT NOT NULL,
                applied_at TIMESTAMPTZ DEFAULT NOW(),
                checksum  TEXT
            )
        """)

        # Discover and apply migrations
        migrations_dir = os.path.join(
            os.path.dirname(__file__), '..', '..', 'migrations',
        )
        migrations_dir = os.path.normpath(migrations_dir)

        if not os.path.isdir(migrations_dir):
            logger.warning("Migrations directory not found: %s", migrations_dir)
            _schema_initialized = True
            return

        migration_files = sorted(
            f for f in os.listdir(migrations_dir) if f.endswith('.sql')
        )

        for filename in migration_files:
            # Extract version number: 001_description.sql -> 1
            try:
                version = int(filename.split('_')[0])
            except (ValueError, IndexError):
                logger.debug("Skipping non-versioned file: %s", filename)
                continue

            # Already applied?
            cur.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s",
                (version,),
            )
            if cur.fetchone():
                continue

            # Read and apply
            mig_path = os.path.join(migrations_dir, filename)
            with open(mig_path, 'r', encoding='utf-8') as f:
                ddl = f.read()

            checksum = hashlib.sha256(ddl.encode()).hexdigest()[:16]

            for stmt in _split_sql(ddl):
                if stmt.strip():
                    cur.execute(stmt)

            cur.execute(
                "INSERT INTO schema_migrations (version, filename, checksum) "
                "VALUES (%s, %s, %s)",
                (version, filename, checksum),
            )
            logger.info("Applied migration %03d: %s", version, filename)

    _schema_initialized = True


def get_schema_version() -> Optional[int]:
    """Return the highest applied migration version, or None."""
    if not is_postgres():
        return None
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'schema_migrations'
            """)
            if cur.fetchone() is None:
                return None
            cur.execute("SELECT MAX(version) FROM schema_migrations")
            row = cur.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def _split_sql(sql_text: str) -> List[str]:
    """
    Split a SQL file into individual statements.

    Handles dollar-quoted function bodies ($$...$$) correctly.
    """
    statements: List[str] = []
    current: List[str] = []
    in_dollar = False

    for line in sql_text.split('\n'):
        stripped = line.strip()
        # Skip pure comment lines
        if stripped.startswith('--') and not in_dollar:
            continue

        current.append(line)

        # Track $$ quoting for function bodies
        dollar_count = line.count('$$')
        if dollar_count % 2 == 1:
            in_dollar = not in_dollar

        # Statement boundary: semicolon at end of line, not inside $$
        if not in_dollar and stripped.endswith(';'):
            stmt = '\n'.join(current).strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt)
            current = []

    # Leftover (shouldn't happen with well-formed SQL)
    if current:
        stmt = '\n'.join(current).strip()
        if stmt and not stmt.startswith('--'):
            statements.append(stmt)

    return statements
