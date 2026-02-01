#!/usr/bin/env python3
"""
Migration script: SQLite hail_events -> PostgreSQL storms + swaths

Source: SQLite hailtracker_crm.db
Target: PostgreSQL hailtracker_master (Docker container: hailtracker_postgres)

This script migrates 147,280 hail events from SQLite to PostgreSQL.
"""

import sqlite3
import psycopg2
import json
import sys
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

# Configuration
SQLITE_PATH = "C:/Users/xtxll/Desktop/HailTracker/hailtracker-pro/data/hailtracker_crm.db"
PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "hailtracker_master",
    "user": "hailtracker",
    "password": "hailtracker_dev_2024"
}

BATCH_SIZE = 1000  # Commit every N records


def get_sqlite_connection() -> sqlite3.Connection:
    """Connect to SQLite database."""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_pg_connection() -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database."""
    return psycopg2.connect(**PG_CONFIG)


def extract_state_from_event_name(event_name: str) -> Optional[str]:
    """Extract state abbreviation from event name if present."""
    # Common patterns: "City, ST" or "City ST" or just state codes
    if not event_name:
        return None

    # List of US state abbreviations
    states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
              'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
              'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
              'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
              'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC']

    # Try to find state in the last part of the name
    parts = event_name.replace(',', ' ').split()
    for part in reversed(parts):
        if part.upper() in states:
            return part.upper()

    return None


def parse_polygon(swath_polygon: str) -> Optional[dict]:
    """Parse swath polygon from string to dict."""
    if not swath_polygon:
        return None
    try:
        return json.loads(swath_polygon)
    except (json.JSONDecodeError, TypeError):
        return None


def migrate_data(dry_run: bool = False) -> Tuple[int, int, int]:
    """
    Migrate data from SQLite to PostgreSQL.

    Returns:
        Tuple of (storms_migrated, swaths_migrated, errors)
    """
    sqlite_conn = get_sqlite_connection()
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()

    storms_migrated = 0
    swaths_migrated = 0
    errors = 0

    try:
        # Get total count
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT COUNT(*) FROM hail_events")
        total_count = sqlite_cursor.fetchone()[0]
        print(f"Total hail_events to migrate: {total_count:,}")

        if dry_run:
            print("\n[DRY RUN] No changes will be made.\n")

        # Check for existing data
        pg_cursor.execute("SELECT COUNT(*) FROM storms")
        existing_storms = pg_cursor.fetchone()[0]
        if existing_storms > 0:
            print(f"WARNING: PostgreSQL storms table already has {existing_storms} records.")
            response = input("Continue and add new records? (y/n): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                return (0, 0, 0)

        # Fetch all hail_events
        sqlite_cursor.execute("""
            SELECT
                id, event_name, event_date, start_time, end_time,
                center_lat, center_lon, swath_polygon, swath_area_sqmi,
                max_hail_size, avg_hail_size, max_reflectivity, avg_reflectivity,
                storm_motion_dir, storm_motion_speed, swath_method,
                num_detections, data_source, confidence_score,
                affected_locations, estimated_vehicles,
                created_at, updated_at, organization_id
            FROM hail_events
            ORDER BY id
        """)

        batch_count = 0

        for row in sqlite_cursor:
            try:
                # Generate a unique noaa_id from the SQLite id and event_name
                sqlite_id = row['id']
                event_name = row['event_name'] or f"Event_{sqlite_id}"
                noaa_id = f"SQLITE_{sqlite_id}"

                # Parse event_date
                event_date = row['event_date']
                if event_date:
                    try:
                        if isinstance(event_date, str):
                            event_date = datetime.strptime(event_date, '%Y-%m-%d')
                    except ValueError:
                        event_date = datetime.now()
                else:
                    event_date = datetime.now()

                # Extract state
                state = extract_state_from_event_name(event_name)

                # Parse created_at
                created_at = row['created_at']
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except ValueError:
                        created_at = datetime.now()

                if not dry_run:
                    # Insert into storms table
                    pg_cursor.execute("""
                        INSERT INTO storms (noaa_id, event_date, state, status, business_count, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        noaa_id,
                        event_date,
                        state,
                        'processed',
                        row['affected_locations'] or 0,
                        created_at
                    ))
                    storm_id = pg_cursor.fetchone()[0]
                else:
                    storm_id = sqlite_id  # For dry run, use placeholder

                storms_migrated += 1

                # Parse polygon
                polygon = parse_polygon(row['swath_polygon'])

                if not dry_run:
                    # Insert into swaths table
                    pg_cursor.execute("""
                        INSERT INTO swaths (
                            storm_id, city, state, county, max_hail_size,
                            polygon, center_lat, center_lon, area_sq_miles, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        storm_id,
                        event_name[:100] if event_name else None,  # Use event_name as city placeholder
                        state,
                        None,  # county not in source data
                        row['max_hail_size'],
                        json.dumps(polygon) if polygon else None,
                        row['center_lat'],
                        row['center_lon'],
                        row['swath_area_sqmi'],
                        created_at
                    ))

                swaths_migrated += 1
                batch_count += 1

                # Commit in batches
                if batch_count >= BATCH_SIZE:
                    if not dry_run:
                        pg_conn.commit()
                    print(f"  Processed {storms_migrated:,} / {total_count:,} ({100*storms_migrated/total_count:.1f}%)")
                    batch_count = 0

            except Exception as e:
                errors += 1
                if errors <= 10:  # Only print first 10 errors
                    print(f"  Error migrating event {row['id']}: {e}")
                elif errors == 11:
                    print("  ... (suppressing further error messages)")
                continue

        # Final commit
        if not dry_run:
            pg_conn.commit()

        print(f"\nMigration complete!")
        print(f"  Storms migrated: {storms_migrated:,}")
        print(f"  Swaths migrated: {swaths_migrated:,}")
        print(f"  Errors: {errors:,}")

    except Exception as e:
        print(f"Migration failed: {e}")
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_cursor.close()
        pg_conn.close()

    return (storms_migrated, swaths_migrated, errors)


def verify_migration() -> None:
    """Verify the migration was successful."""
    print("\n=== Verification ===")

    # SQLite counts
    sqlite_conn = get_sqlite_connection()
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM hail_events")
    sqlite_count = cursor.fetchone()[0]
    sqlite_conn.close()

    # PostgreSQL counts
    pg_conn = get_pg_connection()
    pg_cursor = pg_conn.cursor()

    pg_cursor.execute("SELECT COUNT(*) FROM storms")
    pg_storms_count = pg_cursor.fetchone()[0]

    pg_cursor.execute("SELECT COUNT(*) FROM swaths")
    pg_swaths_count = pg_cursor.fetchone()[0]

    pg_conn.close()

    print(f"SQLite hail_events: {sqlite_count:,}")
    print(f"PostgreSQL storms:  {pg_storms_count:,}")
    print(f"PostgreSQL swaths:  {pg_swaths_count:,}")

    if sqlite_count == pg_storms_count:
        print("\n[OK] Migration verified: counts match!")
    else:
        print(f"\n[WARNING] Count mismatch: {sqlite_count - pg_storms_count:,} records difference")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate SQLite hail_events to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Simulate migration without making changes')
    parser.add_argument('--verify', action='store_true', help='Only verify existing migration')
    args = parser.parse_args()

    print("=" * 60)
    print("HailTracker Data Migration: SQLite -> PostgreSQL")
    print("=" * 60)
    print(f"\nSource: {SQLITE_PATH}")
    print(f"Target: PostgreSQL {PG_CONFIG['database']}@{PG_CONFIG['host']}")
    print()

    if args.verify:
        verify_migration()
    else:
        migrate_data(dry_run=args.dry_run)
        if not args.dry_run:
            verify_migration()


if __name__ == "__main__":
    main()
