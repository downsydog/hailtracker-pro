#!/usr/bin/env python3
"""
Offline test for the central DB engine (HARDEN-1).

Verifies:
  - Import succeeds
  - SQLite backend works (default)
  - WAL mode is enabled
  - Context manager commits/rollbacks correctly
  - get_engine_info() returns expected fields
  - placeholder() returns '?'
  - is_postgres() returns False
  - close_engine() is safe to call

Does NOT require PostgreSQL or network.

Usage:
    python scripts/test_db_engine.py
"""

import sys
import os
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("DB ENGINE OFFLINE TEST (HARDEN-1)")
    print("=" * 60)

    # --- 1) Import check ---
    print("\n[1] Import check...")
    from src.db.engine import (
        get_connection, get_engine_info, close_engine,
        placeholder, is_postgres, _parse_url,
    )
    print("    OK: All engine functions imported")

    # --- 2) URL parsing ---
    print("\n[2] URL parsing...")
    p1 = _parse_url('sqlite:///database/hailtracker_pro.db')
    assert p1['backend'] == 'sqlite'
    assert p1['path'] == 'database/hailtracker_pro.db'

    p2 = _parse_url('postgresql://user:pass@localhost:5432/hailtracker')
    assert p2['backend'] == 'postgresql'
    assert 'user:pass' in p2['dsn']

    p3 = _parse_url('postgres://user:pass@host/db')
    assert p3['backend'] == 'postgresql'
    print("    OK: URL parsing works for sqlite, postgresql, postgres")

    # --- 3) SQLite connection via temp file ---
    print("\n[3] SQLite connection...")
    tmp = tempfile.mktemp(suffix='.db', prefix='hailtracker_test_')
    url = f'sqlite:///{tmp}'

    with get_connection(database_url=url) as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE test_tbl (id INTEGER PRIMARY KEY, val TEXT)')
        cur.execute("INSERT INTO test_tbl (val) VALUES ('hello')")

    # Verify data persisted (commit worked)
    with get_connection(database_url=url) as conn:
        cur = conn.cursor()
        cur.execute('SELECT val FROM test_tbl WHERE id = 1')
        row = cur.fetchone()
        assert row is not None
        assert row[0] == 'hello' or row['val'] == 'hello'
    print(f"    OK: SQLite read/write works ({tmp})")

    # --- 4) WAL mode ---
    print("\n[4] WAL mode check...")
    with get_connection(database_url=url) as conn:
        cur = conn.cursor()
        cur.execute('PRAGMA journal_mode')
        mode = cur.fetchone()[0]
        assert mode.lower() == 'wal', f"Expected WAL, got {mode}"
    print("    OK: WAL mode enabled")

    # --- 5) Rollback on error ---
    print("\n[5] Rollback on error...")
    try:
        with get_connection(database_url=url) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO test_tbl (val) VALUES ('should_rollback')")
            raise ValueError("intentional error")
    except ValueError:
        pass

    with get_connection(database_url=url) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM test_tbl WHERE val = 'should_rollback'")
        count = cur.fetchone()[0]
        assert count == 0, f"Expected 0 (rolled back), got {count}"
    print("    OK: Rollback on exception works")

    # --- 6) Engine info ---
    print("\n[6] Engine info (default SQLite)...")
    info = get_engine_info()
    assert info['backend'] == 'sqlite', f"Expected sqlite, got {info['backend']}"
    assert 'wal_mode' in info
    print(f"    OK: {info}")

    # --- 7) Placeholder ---
    print("\n[7] Placeholder...")
    ph = placeholder()
    assert ph == '?', f"Expected '?', got '{ph}'"
    print(f"    OK: placeholder() = '{ph}'")

    # --- 8) is_postgres ---
    print("\n[8] is_postgres()...")
    assert is_postgres() is False
    print("    OK: is_postgres() = False (SQLite mode)")

    # --- 9) close_engine ---
    print("\n[9] close_engine()...")
    close_engine()  # Should be safe even with no PG pool
    close_engine()  # Double-call should be safe
    print("    OK: close_engine() safe to call")

    # Cleanup
    try:
        os.remove(tmp)
    except OSError:
        pass

    print("\n" + "=" * 60)
    print("ALL DB ENGINE TESTS PASSED (HARDEN-1)")
    print("=" * 60)


if __name__ == '__main__':
    main()
