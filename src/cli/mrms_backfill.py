"""
MRMS MESH Historical Backfill CLI
==================================

Fills the 90-day gap between NOAA Storm Events and real-time radar
by fetching historical MRMS MESH data from Iowa State Mesonet archive,
extracting hail events, and persisting them as MRMS_BACKFILL records.

Usage:
    python -m src.cli.mrms_backfill --days 90
    python -m src.cli.mrms_backfill --start-date 2025-12-01 --end-date 2026-02-01
    python -m src.cli.mrms_backfill --days 30 --min-mesh-mm 25 --dry-run
    python -m src.cli.mrms_backfill --days 7 --workers 4 --tick-minutes 15
"""

import argparse
import logging
import os
import sys
from datetime import date, timedelta

# Ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.radar.backfill.mrms_backfill import run_backfill  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="MRMS MESH Historical Backfill — fills the 90-day hail data gap",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Date range
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument(
        "--days", type=int,
        help="Number of days to backfill from today (default 90)",
    )
    date_group.add_argument(
        "--start-date", type=str,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date", type=str, default=None,
        help="End date (YYYY-MM-DD), default today",
    )

    # Algorithm parameters
    parser.add_argument(
        "--min-mesh-mm", type=float, default=15.0,
        help="Minimum MESH threshold in mm (default: 15)",
    )
    parser.add_argument(
        "--min-core-km2", type=float, default=5.0,
        help="Minimum blob area in km² (default: 5)",
    )
    parser.add_argument(
        "--tick-minutes", type=int, default=10,
        help="Time step between MRMS fetches in minutes (default: 10)",
    )
    parser.add_argument(
        "--workers", type=int, default=6,
        help="Number of parallel fetch workers (default: 6)",
    )

    # De-duplication
    parser.add_argument(
        "--no-dedupe", action="store_true",
        help="Skip de-duplication against existing events",
    )
    parser.add_argument(
        "--dedupe-distance-km", type=float, default=30.0,
        help="Centroid distance threshold for dedup in km (default: 30)",
    )
    parser.add_argument(
        "--dedupe-overlap", type=float, default=0.25,
        help="Minimum polygon IOU for dedup match (default: 0.25)",
    )

    # Output control
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Extract and track but do not write to DB",
    )
    parser.add_argument(
        "--cache-dir", type=str, default="data/mrms_cache",
        help="Directory for cached grib2 files (default: data/mrms_cache)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose (DEBUG) logging",
    )

    args = parser.parse_args()

    # Resolve dates
    end_dt = date.fromisoformat(args.end_date) if args.end_date else date.today()
    if args.days is not None:
        start_dt = end_dt - timedelta(days=args.days)
    else:
        start_dt = date.fromisoformat(args.start_date)

    if start_dt >= end_dt:
        parser.error("start-date must be before end-date")

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    print(f"MRMS Backfill: {start_dt} → {end_dt} ({(end_dt - start_dt).days} days)")
    print(f"  min_mesh_mm={args.min_mesh_mm}  tick={args.tick_minutes}min  "
          f"workers={args.workers}  dedupe={'off' if args.no_dedupe else 'on'}")
    if args.dry_run:
        print("  *** DRY RUN — no database writes ***")
    print()

    result = run_backfill(
        start_date=start_dt,
        end_date=end_dt,
        min_mesh_mm=args.min_mesh_mm,
        min_core_km2=args.min_core_km2,
        tick_minutes=args.tick_minutes,
        workers=args.workers,
        dedupe=not args.no_dedupe,
        dedupe_distance_km=args.dedupe_distance_km,
        dedupe_overlap=args.dedupe_overlap,
        dry_run=args.dry_run,
        cache_dir=args.cache_dir,
    )

    # Print summary
    print()
    print("=" * 60)
    print("MRMS Backfill Complete")
    print("=" * 60)
    print(f"  Date range:      {start_dt} → {end_dt}")
    print(f"  Days processed:  {result['days_processed']}")
    print(f"  Days with hail:  {result['days_with_hail']}")
    print(f"  Days skipped:    {result['days_skipped']}")
    print(f"  Ticks fetched:   {result['ticks_fetched']}")
    print(f"  Ticks with data: {result['ticks_with_data']}")
    print(f"  Blobs found:     {result['total_blobs']}")
    print(f"  Tracks formed:   {result['tracks_formed']}")
    print(f"  Tracks deduped:  {result['tracks_deduped']}")
    print(f"  Events written:  {result['events_written']}")
    print(f"  Wall time:       {result['wall_seconds']:.1f}s")
    if args.dry_run:
        print("  *** DRY RUN — no database writes ***")
    print()


if __name__ == "__main__":
    main()
