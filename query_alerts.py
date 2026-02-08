"""
HailTracker Pro - Alert Database Query Tool

Query and export alert history from the database.

Usage:
    python query_alerts.py                      # Show recent alerts
    python query_alerts.py --stats              # Show statistics
    python query_alerts.py --level CRITICAL     # Filter by level
    python query_alerts.py --export alerts.csv  # Export to CSV
"""

import argparse
import sys
import os
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.alerts.database import AlertDatabase
from src.alerts.alert_manager import AlertLevel


def main():
    parser = argparse.ArgumentParser(
        description='HailTracker Pro - Query Alert Database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python query_alerts.py                         # Show recent alerts
  python query_alerts.py --stats                 # Show statistics
  python query_alerts.py --stats --days 7        # Stats for last 7 days
  python query_alerts.py --level CRITICAL        # Only CRITICAL alerts
  python query_alerts.py --radar KFWS            # Alerts from KFWS radar
  python query_alerts.py --min-pdr 70            # High PDR score alerts
  python query_alerts.py --export alerts.csv     # Export to CSV
  python query_alerts.py --export alerts.json    # Export to JSON
  python query_alerts.py --cleanup 90            # Delete alerts older than 90 days
        """
    )

    parser.add_argument(
        '--database', '-d',
        type=str,
        default='sqlite:///data/alerts/alerts.db',
        help='Database URL'
    )

    parser.add_argument(
        '--stats', '-s',
        action='store_true',
        help='Show statistics'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days for statistics/queries (default: 30)'
    )

    parser.add_argument(
        '--level', '-l',
        type=str,
        choices=['INFO', 'WATCH', 'WARNING', 'CRITICAL'],
        help='Filter by alert level'
    )

    parser.add_argument(
        '--radar', '-r',
        type=str,
        help='Filter by radar ID'
    )

    parser.add_argument(
        '--min-pdr',
        type=float,
        help='Filter by minimum PDR score'
    )

    parser.add_argument(
        '--limit', '-n',
        type=int,
        default=20,
        help='Maximum number of alerts to show (default: 20)'
    )

    parser.add_argument(
        '--export', '-e',
        type=str,
        metavar='FILE',
        help='Export to file (CSV or JSON based on extension)'
    )

    parser.add_argument(
        '--cleanup',
        type=int,
        metavar='DAYS',
        help='Delete alerts older than N days'
    )

    parser.add_argument(
        '--count',
        action='store_true',
        help='Show total count only'
    )

    args = parser.parse_args()

    # Connect to database
    try:
        db = AlertDatabase(args.database)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

    # Handle different modes
    if args.cleanup:
        cleanup_alerts(db, args.cleanup)
    elif args.stats:
        show_statistics(db, args.days)
    elif args.export:
        export_alerts(db, args)
    elif args.count:
        show_count(db)
    else:
        show_alerts(db, args)


def show_alerts(db: AlertDatabase, args):
    """Show recent alerts."""
    # Build query parameters
    query_params = {
        'limit': args.limit,
        'order_desc': True
    }

    if args.days:
        query_params['start_time'] = datetime.now() - timedelta(days=args.days)

    if args.level:
        query_params['level'] = AlertLevel[args.level]

    if args.radar:
        query_params['radar_id'] = args.radar

    if args.min_pdr:
        query_params['min_pdr_score'] = args.min_pdr

    # Get alerts
    alerts = db.get_alerts(**query_params)

    if not alerts:
        print("No alerts found matching criteria")
        return

    print(f"\nFound {len(alerts)} alerts")
    print("=" * 90)

    for alert in alerts:
        level_colors = {
            'CRITICAL': '\033[91m',
            'WARNING': '\033[93m',
            'WATCH': '\033[94m',
            'INFO': '\033[92m'
        }
        reset = '\033[0m'
        color = level_colors.get(alert.level.name, '')

        print(f"\n{color}[{alert.level.name}]{reset} {alert.event_name}")
        print(f"  ID: {alert.id}")
        print(f"  Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Location: ({alert.location[0]:.4f}, {alert.location[1]:.4f})")
        print(f"  Radar: {alert.radar_id}")
        print(f"  Hail: {alert.hail_size_mm:.0f}mm | PDR: {alert.pdr_score:.0f}/100 | Prob: {alert.hail_probability:.0f}%")

    print("\n" + "=" * 90)


def show_statistics(db: AlertDatabase, days: int):
    """Show database statistics."""
    stats = db.get_statistics(days)

    print(f"\n{'=' * 60}")
    print(f"ALERT STATISTICS - Last {days} days")
    print(f"{'=' * 60}")

    print(f"\nTotal Alerts: {stats['total_alerts']}")
    print(f"\nBy Level:")
    print(f"  CRITICAL: {stats['by_level']['critical']}")
    print(f"  WARNING:  {stats['by_level']['warning']}")
    print(f"  WATCH:    {stats['by_level']['watch']}")
    print(f"  INFO:     {stats['by_level']['info']}")

    print(f"\nHail Statistics:")
    print(f"  Max Size:     {stats['max_hail_size_mm']}mm ({stats['max_hail_size_mm']/25.4:.2f}\")")
    print(f"  Average Size: {stats['avg_hail_size_mm']}mm")
    print(f"  Average PDR:  {stats['avg_pdr_score']}/100")

    print(f"\nCoverage:")
    print(f"  Unique Radars: {stats['unique_radars']}")
    print(f"  Days w/Alerts: {stats['days_with_alerts']}")

    if stats.get('top_radars'):
        print(f"\nTop Radars:")
        for r in stats['top_radars']:
            print(f"  {r['radar']}: {r['count']} alerts")

    if stats.get('daily_trend'):
        print(f"\nDaily Trend (last {min(7, len(stats['daily_trend']))} days):")
        for day in stats['daily_trend'][-7:]:
            bar = '#' * min(day['count'], 50)
            print(f"  {day['date']}: {bar} ({day['count']})")

    print(f"\n{'=' * 60}")


def show_count(db: AlertDatabase):
    """Show total alert count."""
    count = db.get_count()
    print(f"Total alerts in database: {count}")


def export_alerts(db: AlertDatabase, args):
    """Export alerts to file."""
    filepath = args.export

    # Build query params
    query_params = {'limit': 10000}  # High limit for export

    if args.days:
        query_params['start_time'] = datetime.now() - timedelta(days=args.days)

    if args.level:
        query_params['level'] = AlertLevel[args.level]

    if args.radar:
        query_params['radar_id'] = args.radar

    if args.min_pdr:
        query_params['min_pdr_score'] = args.min_pdr

    # Export based on file extension
    if filepath.endswith('.csv'):
        count = db.export_to_csv(filepath, **query_params)
    elif filepath.endswith('.json'):
        count = db.export_to_json(filepath, **query_params)
    else:
        print("Unknown file format. Use .csv or .json extension")
        sys.exit(1)

    print(f"Exported {count} alerts to {filepath}")


def cleanup_alerts(db: AlertDatabase, days: int):
    """Delete old alerts."""
    print(f"Deleting alerts older than {days} days...")

    # Confirm
    count_before = db.get_count()
    alerts_to_delete = len(db.get_alerts(
        end_time=datetime.now() - timedelta(days=days),
        limit=100000
    ))

    if alerts_to_delete == 0:
        print("No alerts to delete")
        return

    print(f"Found {alerts_to_delete} alerts to delete out of {count_before} total")

    response = input("Continue? [y/N] ")
    if response.lower() != 'y':
        print("Cancelled")
        return

    deleted = db.delete_old_alerts(days)
    print(f"Deleted {deleted} alerts")
    print(f"Remaining: {db.get_count()} alerts")


if __name__ == '__main__':
    main()
