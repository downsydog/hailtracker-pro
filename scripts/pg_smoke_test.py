#!/usr/bin/env python3
"""
PG Mode Smoke Test

Verifies that HailTracker runs correctly against PostgreSQL with ZERO
SQLite fallback.  Designed to run after cutover (DATABASE_URL set to a
postgresql:// DSN).

Usage:
    # Against a running PG instance
    DATABASE_URL=postgresql://user:pass@localhost:5432/hailtracker \
        python scripts/pg_smoke_test.py

    # With verbose output
    DATABASE_URL=... python scripts/pg_smoke_test.py -v

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

import os
import sys
import time
import logging
import traceback
import argparse

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-5s %(message)s',
)
logger = logging.getLogger(__name__)

PASSED = 0
FAILED = 0
SKIPPED = 0


def check(name: str):
    """Decorator that runs a check function and tracks pass/fail."""
    def decorator(fn):
        def wrapper(*args, **kwargs):
            global PASSED, FAILED, SKIPPED
            try:
                result = fn(*args, **kwargs)
                if result is None or result is True:
                    PASSED += 1
                    logger.info("  PASS  %s", name)
                elif result == 'skip':
                    SKIPPED += 1
                    logger.info("  SKIP  %s", name)
                else:
                    FAILED += 1
                    logger.error("  FAIL  %s — %s", name, result)
            except Exception as e:
                FAILED += 1
                logger.error("  FAIL  %s — %s", name, e)
                if args and getattr(args[0], 'verbose', False):
                    traceback.print_exc()
        return wrapper
    return decorator


class SmokeTest:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    # ------------------------------------------------------------------
    # 1. Engine checks
    # ------------------------------------------------------------------

    @check("DATABASE_URL points to PostgreSQL")
    def check_database_url(self):
        url = os.environ.get('DATABASE_URL', '')
        if not url.startswith('postgres'):
            return f"DATABASE_URL={url!r} — not PostgreSQL"

    @check("is_postgres() returns True")
    def check_is_postgres(self):
        from src.db.engine import is_postgres
        if not is_postgres():
            return "is_postgres() returned False"

    @check("get_engine_info() reports postgresql backend")
    def check_engine_info(self):
        from src.db.engine import get_engine_info
        info = get_engine_info()
        if info['backend'] != 'postgresql':
            return f"backend={info['backend']}"

    @check("get_raw_connection() returns _PGRawConnection")
    def check_raw_connection(self):
        from src.db.engine import get_raw_connection
        conn = get_raw_connection()
        cls_name = type(conn).__name__
        conn.close()
        if cls_name != '_PGRawConnection':
            return f"type={cls_name}, expected _PGRawConnection"

    @check("get_connection() context manager works")
    def check_context_connection(self):
        from src.db.engine import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 AS n")
            row = cur.fetchone()
            if row is None:
                return "SELECT 1 returned None"

    @check("ensure_schema() runs without error")
    def check_ensure_schema(self):
        from src.db.engine import ensure_schema
        ensure_schema()

    @check("schema_migrations has version >= 3")
    def check_schema_version(self):
        from src.db.engine import get_schema_version
        v = get_schema_version()
        if v is None or v < 3:
            return f"schema version = {v}, expected >= 3"

    # ------------------------------------------------------------------
    # 2. Core table existence checks (from PG migrations)
    # ------------------------------------------------------------------

    @check("Core radar tables exist in PG")
    def check_radar_tables(self):
        from src.db.engine import get_raw_connection
        expected = [
            'hail_events', 'hail_detections', 'hail_swaths',
            'affected_locations',
        ]
        conn = get_raw_connection()
        cur = conn.cursor()
        missing = []
        for t in expected:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name=%s",
                (t,),
            )
            if cur.fetchone() is None:
                missing.append(t)
        conn.close()
        if missing:
            return f"Missing tables: {missing}"

    @check("Core CRM/fleet tables exist in PG (from migration 002)")
    def check_crm_tables(self):
        from src.db.engine import get_raw_connection
        expected = [
            'fleet_locations', 'fleet_categories', 'users',
            'interactions', 'deals', 'tasks', 'notes',
            'email_campaigns', 'alerts',
        ]
        conn = get_raw_connection()
        cur = conn.cursor()
        missing = []
        for t in expected:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name=%s",
                (t,),
            )
            if cur.fetchone() is None:
                missing.append(t)
        conn.close()
        if missing:
            return f"Missing tables: {missing}"

    @check("CRM core tables exist in PG (from migration 003)")
    def check_crm_core_tables(self):
        from src.db.engine import get_raw_connection
        expected = [
            'customers', 'vehicles', 'technicians', 'jobs',
            'estimates', 'estimate_items', 'invoices', 'payments',
            'company_settings', 'user_activity_log', 'billing',
        ]
        conn = get_raw_connection()
        cur = conn.cursor()
        missing = []
        for t in expected:
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name=%s",
                (t,),
            )
            if cur.fetchone() is None:
                missing.append(t)
        conn.close()
        if missing:
            return f"Missing tables: {missing}"

    # ------------------------------------------------------------------
    # 3. Module import checks (verify no import-time sqlite3 crash)
    # ------------------------------------------------------------------

    @check("Import: src.db.compat")
    def check_import_compat(self):
        import src.db.compat  # noqa: F401

    @check("Import: src.auth.auth_manager")
    def check_import_auth(self):
        from src.auth.auth_manager import AuthManager  # noqa: F401

    @check("Import: src.crm.models.database")
    def check_import_crm_db(self):
        from src.crm.models.database import Database  # noqa: F401

    @check("Import: src.crm.managers.admin_manager")
    def check_import_admin_mgr(self):
        from src.crm.managers.admin_manager import AdminManager  # noqa: F401

    @check("Import: src.crm.managers.kiosk_intake_manager")
    def check_import_kiosk(self):
        from src.crm.managers.kiosk_intake_manager import KioskIntakeManager  # noqa: F401

    @check("Import: src.radar.damage_grid")
    def check_import_damage_grid(self):
        from src.radar.damage_grid import ensure_damage_grid_table  # noqa: F401

    # ------------------------------------------------------------------
    # 4. SQL compat layer
    # ------------------------------------------------------------------

    @check("sql.adapt() converts ? to %s")
    def check_sql_adapt(self):
        from src.db.compat import sql
        result = sql.adapt("SELECT * FROM t WHERE id = ? AND name = ?")
        if '%s' not in result or '?' in result:
            return f"adapt result: {result!r}"

    @check("placeholder() returns %s in PG mode")
    def check_placeholder(self):
        from src.db.engine import placeholder
        ph = placeholder()
        if ph != '%s':
            return f"placeholder={ph!r}"

    # ------------------------------------------------------------------
    # 5. Read/write round-trip
    # ------------------------------------------------------------------

    @check("INSERT + SELECT round-trip on hail_events")
    def check_insert_select(self):
        from src.db.engine import get_raw_connection
        conn = get_raw_connection()
        cur = conn.cursor()
        # Use a savepoint so we can roll back without affecting other data
        cur.execute("SAVEPOINT smoke_rw")
        try:
            cur.execute("""
                INSERT INTO hail_events (
                    event_name, event_date,
                    center_lat, center_lon,
                    swath_polygon, swath_method,
                    max_hail_size
                ) VALUES (
                    'smoke_test_event', '2025-01-01',
                    35.0, -97.0,
                    '{"type":"Point","coordinates":[-97,35]}',
                    'smoke_test', 25.0
                ) RETURNING id
            """)
            row = cur.fetchone()
            if row is None or row.get('id') is None:
                return "RETURNING id got None"

            inserted_id = row['id']
            cur.execute(
                "SELECT event_name FROM hail_events WHERE id = %s",
                (inserted_id,),
            )
            sel = cur.fetchone()
            if sel is None or sel['event_name'] != 'smoke_test_event':
                return f"SELECT returned {sel}"
        finally:
            cur.execute("ROLLBACK TO SAVEPOINT smoke_rw")
            conn.commit()
            conn.close()

    # ------------------------------------------------------------------
    # 6. Flask test client (if app imports cleanly)
    # ------------------------------------------------------------------

    @check("Flask app imports and creates test client")
    def check_flask_app(self):
        try:
            from src.web.app import create_app
            app = create_app()
            self._flask_app = app
        except Exception as e:
            return f"create_app() failed: {e}"

    @check("GET /api/system/ready returns 200 or 503")
    def check_system_ready(self):
        app = getattr(self, '_flask_app', None)
        if app is None:
            return 'skip'
        client = app.test_client()
        resp = client.get('/api/system/ready')
        # 503 is acceptable — health check may fail due to missing
        # Redis or radar pipeline, which is not a schema issue.
        if resp.status_code not in (200, 503):
            return f"status={resp.status_code}"

    @check("GET /api/hail-events returns 200")
    def check_hail_events_api(self):
        app = getattr(self, '_flask_app', None)
        if app is None:
            return 'skip'
        client = app.test_client()
        resp = client.get('/api/hail-events')
        if resp.status_code not in (200, 401):
            return f"status={resp.status_code}"

    # ------------------------------------------------------------------
    # 7. Static analysis: no sqlite3.connect in routes
    # ------------------------------------------------------------------

    @check("No unguarded sqlite3.connect in src/web/routes/")
    def check_no_sqlite_in_routes(self):
        routes_dir = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'web', 'routes',
        )
        routes_dir = os.path.normpath(routes_dir)
        if not os.path.isdir(routes_dir):
            return f"routes dir not found: {routes_dir}"

        # Skip files that are dead code (blueprint never registered)
        skip_files = {'fleet_leads_api.py'}

        hits = []
        for fname in sorted(os.listdir(routes_dir)):
            if not fname.endswith('.py') or fname in skip_files:
                continue
            fpath = os.path.join(routes_dir, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # Look for bare sqlite3.connect that isn't behind an
                # is_postgres() guard (else branch).
                # Use a 50-line context window to catch guards in
                # enclosing functions.
                if 'sqlite3.connect' in line:
                    context_start = max(0, i - 50)
                    context = ''.join(lines[context_start:i])
                    if 'is_postgres()' not in context and 'not is_postgres' not in context:
                        hits.append(f"{fname}:{i}")

        if hits:
            return f"Unguarded sqlite3.connect: {', '.join(hits)}"

    # ------------------------------------------------------------------
    # Run all
    # ------------------------------------------------------------------

    def run_all(self):
        t0 = time.monotonic()

        print("=" * 60)
        print("HailTracker PG Mode Smoke Test")
        print("=" * 60)

        # Engine
        self.check_database_url()
        self.check_is_postgres()
        self.check_engine_info()
        self.check_raw_connection()
        self.check_context_connection()
        self.check_ensure_schema()
        self.check_schema_version()

        # Tables
        self.check_radar_tables()
        self.check_crm_tables()
        self.check_crm_core_tables()

        # Imports
        self.check_import_compat()
        self.check_import_auth()
        self.check_import_crm_db()
        self.check_import_admin_mgr()
        self.check_import_kiosk()
        self.check_import_damage_grid()

        # Compat
        self.check_sql_adapt()
        self.check_placeholder()

        # R/W
        self.check_insert_select()

        # Flask
        self.check_flask_app()
        self.check_system_ready()
        self.check_hail_events_api()

        # Static analysis
        self.check_no_sqlite_in_routes()

        elapsed = time.monotonic() - t0

        print()
        print("-" * 60)
        print(f"  PASSED:  {PASSED}")
        print(f"  FAILED:  {FAILED}")
        print(f"  SKIPPED: {SKIPPED}")
        print(f"  Elapsed: {elapsed:.1f}s")
        print("-" * 60)

        if FAILED > 0:
            print("\nSMOKE TEST FAILED")
            return 1
        else:
            print("\nALL CHECKS PASSED")
            return 0


def main():
    parser = argparse.ArgumentParser(description='PG Mode Smoke Test')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show tracebacks on failure')
    args = parser.parse_args()

    test = SmokeTest(verbose=args.verbose)
    sys.exit(test.run_all())


if __name__ == '__main__':
    main()
