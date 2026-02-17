#!/usr/bin/env python3
"""
Data Migration: SQLite -> PostgreSQL

Reads from the local SQLite databases and batch-inserts into PostgreSQL
(whose schema was already created by ensure_schema / migration files).

Usage:
    # Dry run (report only, no writes)
    python scripts/migrate_sqlite_to_pg.py --dry-run

    # Migrate first 100 rows per table
    python scripts/migrate_sqlite_to_pg.py --limit 100

    # Full migration
    python scripts/migrate_sqlite_to_pg.py

    # Verify only (compare row counts)
    python scripts/migrate_sqlite_to_pg.py --verify

    # Specific tables only
    python scripts/migrate_sqlite_to_pg.py --tables hail_events,fleet_locations

Environment:
    DATABASE_URL  — PostgreSQL connection string (required)
    SQLITE_CRM_PATH — Path to hailtracker_crm.db (default: data/hailtracker_crm.db)
    SQLITE_MAIN_PATH — Path to hailtracker_pro.db (default: database/hailtracker_pro.db)
"""

import os
import sys
import json
import argparse
import sqlite3
import time
import logging
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BATCH_SIZE = 500

# Tables and their source SQLite database
# Format: (table_name, sqlite_db_key, columns_to_skip, on_conflict_column)
TABLE_REGISTRY = [
    # --- Radar pipeline tables (from hailtracker_pro.db) ---
    {
        'table': 'hail_events',
        'source': 'main',
        'conflict_col': None,  # No upsert, INSERT only
        'skip_cols': {'center_geom', 'swath_geom'},  # Generated/trigger columns
    },
    {
        'table': 'hail_detections',
        'source': 'main',
        'conflict_col': None,
        'skip_cols': {'geom'},
    },
    {
        'table': 'hail_swaths',
        'source': 'main',
        'conflict_col': 'swath_id',
        'skip_cols': {'centroid_geom', 'swath_geom'},
    },
    {
        'table': 'affected_locations',
        'source': 'main',
        'conflict_col': None,
        'skip_cols': set(),
    },
    # --- Fleet tables (from hailtracker_pro.db) ---
    {
        'table': 'fleet_locations',
        'source': 'main',
        'conflict_col': None,
        'skip_cols': {'geom'},  # Generated column
    },
    {
        'table': 'fleet_categories',
        'source': 'main',
        'conflict_col': 'category',
        'skip_cols': set(),
    },
    {
        'table': 'hail_event_locations',
        'source': 'main',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'watch_list',
        'source': 'main',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'planned_routes',
        'source': 'main',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'route_stops',
        'source': 'main',
        'conflict_col': None,
        'skip_cols': set(),
    },
    # --- CRM tables (from hailtracker_crm.db) ---
    {
        'table': 'users',
        'source': 'crm',
        'conflict_col': 'email',
        'skip_cols': set(),
    },
    {
        'table': 'interactions',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'deals',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'tasks',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'notes',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'email_campaigns',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'email_sends',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'sms_campaigns',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'sms_sends',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'performance_metrics',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    # --- CRM core tables (from hailtracker_crm.db, migration 003) ---
    # FK ordering: parents before children
    {
        'table': 'locations',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'customers',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'vehicles',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'technicians',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'insurance_claims',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'leads',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'jobs',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'job_status_history',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'estimates',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'estimate_items',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'invoices',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'payments',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'communications',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
    {
        'table': 'documents',
        'source': 'crm',
        'conflict_col': None,
        'skip_cols': set(),
    },
]


def get_sqlite_conn(db_key: str, paths: Dict[str, str]) -> Optional[sqlite3.Connection]:
    """Get SQLite connection for the given db key."""
    path = paths.get(db_key)
    if not path or not os.path.exists(path):
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_pg_conn():
    """Get PostgreSQL connection from engine pool."""
    from src.db.engine import get_raw_connection
    return get_raw_connection()


def table_exists_sqlite(conn: sqlite3.Connection, table: str) -> bool:
    """Check if a table exists in SQLite."""
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def get_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    """Get column names from a SQLite table."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def get_pg_columns(pg_conn, table: str) -> set:
    """Get column names that exist in the PostgreSQL table."""
    cur = pg_conn.cursor()
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s",
        (table,),
    )
    return {row['column_name'] for row in cur.fetchall()}


def table_row_count(conn, table: str, is_pg: bool = False) -> int:
    """Get row count for a table."""
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        row = cur.fetchone()
        if row is None:
            return 0
        if isinstance(row, dict):
            return row.get('count', 0)
        return row[0]
    except Exception:
        return 0


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    table_config: dict,
    limit: int = 0,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """
    Migrate one table from SQLite to PostgreSQL.

    Returns (rows_migrated, errors).
    """
    table = table_config['table']
    conflict_col = table_config.get('conflict_col')
    skip_cols = table_config.get('skip_cols', set())

    if not table_exists_sqlite(sqlite_conn, table):
        logger.info("  [SKIP] Table '%s' not found in SQLite", table)
        return 0, 0

    # Get columns from SQLite, filter out PG-only generated columns
    all_cols = get_columns(sqlite_conn, table)
    cols = [c for c in all_cols if c not in skip_cols]

    # Dynamic column skip: drop any SQLite columns missing from PG
    pg_cols = get_pg_columns(pg_conn, table)
    if pg_cols:
        dropped = [c for c in cols if c not in pg_cols]
        if dropped:
            logger.info("  Dropping SQLite-only columns not in PG: %s", dropped)
            cols = [c for c in cols if c in pg_cols]

    # Read source data
    query = f"SELECT {', '.join(cols)} FROM {table} ORDER BY id"
    if limit > 0:
        query += f" LIMIT {limit}"

    try:
        rows = sqlite_conn.execute(query).fetchall()
    except Exception as e:
        # Table might not have 'id' column
        query = f"SELECT {', '.join(cols)} FROM {table}"
        if limit > 0:
            query += f" LIMIT {limit}"
        rows = sqlite_conn.execute(query).fetchall()

    if not rows:
        logger.info("  [SKIP] Table '%s' is empty in SQLite", table)
        return 0, 0

    total = len(rows)
    logger.info("  Migrating '%s': %d rows ...", table, total)

    if dry_run:
        return total, 0

    # Build INSERT SQL
    placeholders = ', '.join(['%s'] * len(cols))
    col_list = ', '.join(cols)

    if conflict_col:
        insert_sql = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_col}) DO NOTHING"
        )
    else:
        insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    pg_cur = pg_conn.cursor()
    migrated = 0
    errors = 0

    for i in range(0, total, BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        for row_idx, row in enumerate(batch):
            values = []
            for j, col in enumerate(cols):
                val = row[j]
                # Convert sqlite booleans (0/1) for boolean-like columns
                if isinstance(val, int) and col in {
                    'luxury_vehicles', 'requires_appointment', 'has_security_gate',
                    'security_guard', 'can_canvas_lot', 'parking_fee', 'worked_before',
                    'verified', 'hail_detected', 'bounced', 'active', 'email_verified',
                    'in_swath', 'contacted', 'deal_created', 'alert_on_hail',
                }:
                    val = bool(val)
                values.append(val)
            # Use SAVEPOINT per row so a single-row error doesn't wipe
            # every prior row in the batch (the old rollback() bug).
            sp_name = f"sp_{i}_{row_idx}"
            try:
                pg_cur.execute(f"SAVEPOINT {sp_name}")
                pg_cur.execute(insert_sql, values)
                pg_cur.execute(f"RELEASE SAVEPOINT {sp_name}")
                migrated += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    logger.warning("    Row error in '%s': %s", table, str(e)[:120])
                pg_cur.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
                continue

        pg_conn.commit()
        if i + BATCH_SIZE < total:
            logger.info("    ... %d / %d", min(i + BATCH_SIZE, total), total)

    # Reset sequences so new inserts get correct IDs
    if migrated > 0 and 'id' in cols:
        try:
            pg_cur.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"(SELECT COALESCE(MAX(id), 1) FROM {table}))"
            )
            pg_conn.commit()
        except Exception:
            pg_conn.rollback()

    return migrated, errors


def run_migration(args):
    """Run the full migration."""
    # Resolve SQLite paths
    crm_path = os.environ.get('SQLITE_CRM_PATH', 'data/hailtracker_crm.db')
    main_path = os.environ.get('SQLITE_MAIN_PATH', 'database/hailtracker_pro.db')

    paths = {'crm': crm_path, 'main': main_path}

    # Ensure PG schema exists
    logger.info("Ensuring PostgreSQL schema is up to date ...")
    from src.db.engine import ensure_schema, is_postgres
    if not is_postgres():
        logger.error("DATABASE_URL is not PostgreSQL. Set DATABASE_URL to a postgresql:// URL.")
        sys.exit(1)
    ensure_schema()

    # Filter tables if --tables specified
    tables = TABLE_REGISTRY
    if args.tables:
        requested = {t.strip() for t in args.tables.split(',')}
        tables = [t for t in tables if t['table'] in requested]
        if not tables:
            logger.error("No matching tables found for: %s", args.tables)
            sys.exit(1)

    # Migrate each table (reuse a single PG connection to avoid pool exhaustion)
    report = []
    total_migrated = 0
    total_errors = 0
    t0 = time.monotonic()
    pg_conn = get_pg_conn()

    for tbl_config in tables:
        source_key = tbl_config['source']
        sqlite_conn = get_sqlite_conn(source_key, paths)
        if sqlite_conn is None:
            logger.warning("SQLite file not found for '%s': %s",
                           tbl_config['table'], paths.get(source_key))
            report.append((tbl_config['table'], 0, 0, 'SKIPPED'))
            continue

        try:
            migrated, errs = migrate_table(
                sqlite_conn, pg_conn,
                tbl_config,
                limit=args.limit,
                dry_run=args.dry_run,
            )
            total_migrated += migrated
            total_errors += errs
            status = 'OK' if errs == 0 else f'{errs} errors'
            report.append((tbl_config['table'], migrated, errs, status))
        except Exception as e:
            logger.error("Failed on table '%s': %s", tbl_config['table'], e)
            report.append((tbl_config['table'], 0, 0, f'FAILED: {e}'))
            # Reset connection state after error
            try:
                pg_conn.rollback()
            except Exception:
                pass
        finally:
            sqlite_conn.close()

    pg_conn.close()

    elapsed = time.monotonic() - t0

    # Print report
    print("\n" + "=" * 70)
    print("MIGRATION REPORT")
    print("=" * 70)
    print(f"{'Table':<30} {'Rows':<10} {'Errors':<10} Status")
    print("-" * 70)
    for table, rows, errs, status in report:
        print(f"{table:<30} {rows:<10} {errs:<10} {status}")
    print("-" * 70)
    print(f"{'TOTAL':<30} {total_migrated:<10} {total_errors:<10}")
    print(f"\nElapsed: {elapsed:.1f}s")
    if args.dry_run:
        print("\n[DRY RUN] No data was written to PostgreSQL.")
    print()


def run_verify():
    """Compare row counts between SQLite and PostgreSQL."""
    crm_path = os.environ.get('SQLITE_CRM_PATH', 'data/hailtracker_crm.db')
    main_path = os.environ.get('SQLITE_MAIN_PATH', 'database/hailtracker_pro.db')
    paths = {'crm': crm_path, 'main': main_path}

    pg_conn = get_pg_conn()

    print("\n" + "=" * 70)
    print("VERIFICATION REPORT")
    print("=" * 70)
    print(f"{'Table':<30} {'SQLite':<12} {'PostgreSQL':<12} Match")
    print("-" * 70)

    all_match = True
    for tbl_config in TABLE_REGISTRY:
        table = tbl_config['table']
        source_key = tbl_config['source']

        # SQLite count
        try:
            sqlite_conn = get_sqlite_conn(source_key, paths)
            if sqlite_conn and table_exists_sqlite(sqlite_conn, table):
                sqlite_count = table_row_count(sqlite_conn, table)
                sqlite_conn.close()
            else:
                sqlite_count = '-'
        except Exception as e:
            sqlite_count = f'ERR'
            logger.warning("SQLite read error for '%s': %s", table, str(e)[:80])

        # PG count
        try:
            pg_count = table_row_count(pg_conn, table, is_pg=True)
        except Exception:
            pg_count = '-'

        if isinstance(sqlite_count, int) and isinstance(pg_count, int):
            match = 'OK' if sqlite_count == pg_count else 'MISMATCH'
            if match == 'MISMATCH':
                all_match = False
        else:
            match = 'N/A'

        print(f"{table:<30} {str(sqlite_count):<12} {str(pg_count):<12} {match}")

    print("-" * 70)
    if all_match:
        print("All counts match.")
    else:
        print("WARNING: Some counts do not match.")
    print()
    pg_conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Migrate HailTracker SQLite data to PostgreSQL'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would be migrated without writing')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit rows per table (0 = no limit)')
    parser.add_argument('--verify', action='store_true',
                        help='Only verify row counts (no migration)')
    parser.add_argument('--tables', type=str, default='',
                        help='Comma-separated list of tables to migrate')

    args = parser.parse_args()

    print("=" * 70)
    print("HailTracker Data Migration: SQLite -> PostgreSQL")
    print("=" * 70)

    if args.verify:
        run_verify()
    else:
        run_migration(args)
        if not args.dry_run:
            run_verify()


if __name__ == '__main__':
    main()
