#!/usr/bin/env python
"""
Populate Storm Photos Script

Run this script to automatically fetch and store social media photos
for all storm events that are missing photos.

Usage:
    python scripts/populate_storm_photos.py [--days 90] [--storms 25]

Options:
    --days      Number of days back to look for storms (default: 90)
    --storms    Maximum storms to process (default: 25)
"""

import sys
import os
import argparse

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def main():
    parser = argparse.ArgumentParser(description='Populate storm photos from social media')
    parser.add_argument('--days', type=int, default=90, help='Days back to look for storms')
    parser.add_argument('--storms', type=int, default=25, help='Maximum storms to process')
    args = parser.parse_args()

    # Configure encoding for Windows
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    from src.social.storm_verification_pipeline import StormVerificationPipeline
    from src.db.database import Database
    from datetime import datetime, timedelta

    print(f"=" * 60)
    print(f"Storm Photo Population Script")
    print(f"=" * 60)
    print()

    # Check current status
    db_path = os.path.join(PROJECT_ROOT, 'data', 'hailtracker_crm.db')
    db = Database(db_path)

    cutoff = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    storms = db.execute('''
        SELECT e.id, e.event_name,
               COALESCE(photo_counts.photo_count, 0) as photo_count
        FROM hail_events e
        LEFT JOIN (
            SELECT hail_event_id, COUNT(*) as photo_count
            FROM storm_verifications
            WHERE photo_url IS NOT NULL
            GROUP BY hail_event_id
        ) photo_counts ON e.id = photo_counts.hail_event_id
        WHERE e.event_date >= ?
    ''', (cutoff,))

    need_photos = sum(1 for s in storms if s['photo_count'] < 5)
    have_photos = sum(1 for s in storms if s['photo_count'] >= 5)

    print(f"Storms in last {args.days} days: {len(storms)}")
    print(f"  - With 5+ photos: {have_photos}")
    print(f"  - Need more photos: {need_photos}")
    print()

    if need_photos == 0:
        print("All storms have photos! Nothing to do.")
        return

    print(f"Processing up to {args.storms} storms...")
    print("This may take a few minutes due to rate limiting...")
    print()

    # Run pipeline
    pipeline = StormVerificationPipeline()
    result = pipeline.process_active_storms(
        days_back=args.days,
        max_storms=args.storms,
        auto_analyze=False
    )

    print()
    print(f"=" * 60)
    print(f"RESULTS")
    print(f"=" * 60)
    print(f"Storms processed: {result['storms_processed']}")
    print(f"Storms skipped (already had 5+ photos): {sum(1 for r in result['storm_results'] if r.get('skipped'))}")
    print(f"Total posts found: {result['total_posts_found']}")
    print(f"Total photos added: {result['total_verifications']}")
    print()

    # Show per-storm breakdown
    print("Per-storm breakdown:")
    for r in result['storm_results']:
        storm_id = r.get('storm_id')
        if r.get('skipped'):
            print(f"  Storm {storm_id}: Skipped (has {r.get('existing_photos', 0)} photos)")
        else:
            print(f"  Storm {storm_id}: {r.get('verifications_added', 0)} photos added")


if __name__ == '__main__':
    main()
