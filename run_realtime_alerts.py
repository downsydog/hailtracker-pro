"""
Real-Time Storm Alert System

Monitor NEXRAD radar data in real-time and generate alerts for hail events.

Usage:
    python run_realtime_alerts.py                    # Monitor default radars
    python run_realtime_alerts.py --radars KFWS KTLX # Monitor specific radars
    python run_realtime_alerts.py --interval 60      # Check every 60 seconds
    python run_realtime_alerts.py --threshold 60     # Alert on PDR score >= 60
    python run_realtime_alerts.py --sms-env          # Enable SMS via env vars
"""

import argparse
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.alerts.storm_monitor import StormMonitor, MonitorConfig
from src.alerts.alert_manager import AlertManager, AlertLevel
from src.alerts.notifiers import ConsoleNotifier, WebhookNotifier, SoundNotifier
from src.alerts.geo_filter import GeoFilter, list_named_regions, get_suggested_radars
from src.alerts.config import (
    load_config,
    save_config,
    find_config_file,
    get_default_config,
    config_to_monitor_args,
    create_sample_config
)


def main():
    parser = argparse.ArgumentParser(
        description='HailTracker Pro - Real-Time Storm Alert System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_realtime_alerts.py
  python run_realtime_alerts.py --radars KFWS KTLX KAMA
  python run_realtime_alerts.py --interval 120 --threshold 70
  python run_realtime_alerts.py --webhook https://hooks.slack.com/xxx
  python run_realtime_alerts.py --sms-env  # Use env vars for Twilio

SMS Alerts (Twilio):
  Option 1: Use environment variables (--sms-env flag)
    export TWILIO_ACCOUNT_SID=ACxxxxx
    export TWILIO_AUTH_TOKEN=xxxxx
    export TWILIO_FROM_NUMBER=+15551234567
    export TWILIO_TO_NUMBERS=+15559876543,+15551112222

  Option 2: Pass credentials directly
    --sms-sid ACxxxxx --sms-token xxxxx --sms-from +15551234567 --sms-to +15559876543

Default radars monitored (Tornado Alley):
  KFWS, KDFW (Dallas-Fort Worth)
  KTLX, KVNX (Oklahoma)
  KICT, KDDC (Kansas)
  KOAX, KUEX (Nebraska)
  KAMA, KLBB (Texas Panhandle)
        """
    )

    parser.add_argument(
        '--radars', '-r',
        nargs='+',
        default=None,
        help='Radar IDs to monitor (e.g., KFWS KTLX KAMA)'
    )

    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=300,
        help='Scan interval in seconds (default: 300 = 5 minutes)'
    )

    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=40.0,
        help='Minimum PDR score to trigger alert (default: 40)'
    )

    parser.add_argument(
        '--min-reflectivity',
        type=float,
        default=50.0,
        help='Minimum reflectivity to analyze (dBZ, default: 50)'
    )

    parser.add_argument(
        '--min-mesh',
        type=float,
        default=15.0,
        help='Minimum MESH to alert (mm, default: 15)'
    )

    parser.add_argument(
        '--webhook',
        type=str,
        default=None,
        help='Webhook URL for Slack/Discord notifications'
    )

    parser.add_argument(
        '--webhook-platform',
        type=str,
        default='slack',
        choices=['slack', 'discord', 'custom'],
        help='Webhook platform (default: slack)'
    )

    parser.add_argument(
        '--no-sound',
        action='store_true',
        help='Disable sound alerts'
    )

    parser.add_argument(
        '--no-console',
        action='store_true',
        help='Disable console output (log to file only)'
    )

    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run a quick demo with simulated alerts'
    )

    # Config file arguments
    config_group = parser.add_argument_group('Configuration File')

    config_group.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        metavar='FILE',
        help='Load settings from config file (YAML or JSON)'
    )

    config_group.add_argument(
        '--create-config',
        type=str,
        nargs='?',
        const='hailtracker.yaml',
        metavar='FILE',
        help='Create sample config file and exit (default: hailtracker.yaml)'
    )

    config_group.add_argument(
        '--show-config',
        action='store_true',
        help='Show current configuration and exit'
    )

    # SMS/Twilio arguments
    sms_group = parser.add_argument_group('SMS Alerts (Twilio)')

    sms_group.add_argument(
        '--sms-env',
        action='store_true',
        help='Enable SMS using environment variables (TWILIO_ACCOUNT_SID, etc.)'
    )

    sms_group.add_argument(
        '--sms-sid',
        type=str,
        default=None,
        help='Twilio Account SID'
    )

    sms_group.add_argument(
        '--sms-token',
        type=str,
        default=None,
        help='Twilio Auth Token'
    )

    sms_group.add_argument(
        '--sms-from',
        type=str,
        default=None,
        help='Twilio phone number to send from (e.g., +15551234567)'
    )

    sms_group.add_argument(
        '--sms-to',
        type=str,
        nargs='+',
        default=None,
        help='Phone number(s) to send SMS to (e.g., +15559876543)'
    )

    sms_group.add_argument(
        '--sms-level',
        type=str,
        default='WARNING',
        choices=['INFO', 'WATCH', 'WARNING', 'CRITICAL'],
        help='Minimum alert level to send SMS (default: WARNING)'
    )

    # Push notification arguments
    push_group = parser.add_argument_group('Push Notifications')

    push_group.add_argument(
        '--ntfy',
        type=str,
        default=None,
        metavar='TOPIC',
        help='Enable ntfy.sh push notifications (provide topic name)'
    )

    push_group.add_argument(
        '--ntfy-server',
        type=str,
        default='https://ntfy.sh',
        help='ntfy server URL (default: https://ntfy.sh)'
    )

    push_group.add_argument(
        '--pushover-user',
        type=str,
        default=None,
        help='Pushover user key'
    )

    push_group.add_argument(
        '--pushover-token',
        type=str,
        default=None,
        help='Pushover API token'
    )

    push_group.add_argument(
        '--push-level',
        type=str,
        default='WARNING',
        choices=['INFO', 'WATCH', 'WARNING', 'CRITICAL'],
        help='Minimum alert level for push notifications (default: WARNING)'
    )

    # Email arguments
    email_group = parser.add_argument_group('Email Alerts')

    email_group.add_argument(
        '--email-env',
        action='store_true',
        help='Enable email using environment variables (EMAIL_SMTP_SERVER, etc.)'
    )

    email_group.add_argument(
        '--email-smtp',
        type=str,
        default=None,
        metavar='SERVER',
        help='SMTP server (e.g., smtp.gmail.com)'
    )

    email_group.add_argument(
        '--email-port',
        type=int,
        default=587,
        help='SMTP port (default: 587 for TLS, use 465 for SSL)'
    )

    email_group.add_argument(
        '--email-user',
        type=str,
        default=None,
        help='SMTP username (usually your email address)'
    )

    email_group.add_argument(
        '--email-password',
        type=str,
        default=None,
        help='SMTP password (for Gmail, use an App Password)'
    )

    email_group.add_argument(
        '--email-from',
        type=str,
        default=None,
        help='From address (defaults to --email-user)'
    )

    email_group.add_argument(
        '--email-to',
        type=str,
        nargs='+',
        default=None,
        help='Recipient email address(es)'
    )

    email_group.add_argument(
        '--email-level',
        type=str,
        default='WARNING',
        choices=['INFO', 'WATCH', 'WARNING', 'CRITICAL'],
        help='Minimum alert level to send email (default: WARNING)'
    )

    # Database arguments
    db_group = parser.add_argument_group('Database Storage')

    db_group.add_argument(
        '--database',
        type=str,
        default='sqlite:///data/alerts/alerts.db',
        metavar='URL',
        help='Database URL (default: sqlite:///data/alerts/alerts.db)'
    )

    db_group.add_argument(
        '--no-database',
        action='store_true',
        help='Disable database storage'
    )

    # Geographic coverage arguments
    geo_group = parser.add_argument_group('Geographic Coverage')

    geo_group.add_argument(
        '--coverage-region',
        type=str,
        default=None,
        metavar='NAME',
        help='Named coverage region (e.g., texas, dallas_fort_worth, hail_alley_core)'
    )

    geo_group.add_argument(
        '--coverage-regions',
        type=str,
        nargs='+',
        default=None,
        metavar='NAME',
        help='Multiple coverage regions (e.g., dallas_fort_worth oklahoma_city)'
    )

    geo_group.add_argument(
        '--coverage-center',
        type=str,
        default=None,
        metavar='LAT,LON',
        help='Center point for radius filter (e.g., 32.7767,-96.7970)'
    )

    geo_group.add_argument(
        '--coverage-radius',
        type=float,
        default=None,
        metavar='MILES',
        help='Radius in miles from center point (use with --coverage-center)'
    )

    geo_group.add_argument(
        '--coverage-bounds',
        type=str,
        default=None,
        metavar='LAT_MIN,LAT_MAX,LON_MIN,LON_MAX',
        help='Bounding box coordinates (e.g., 32.0,34.0,-98.0,-96.0)'
    )

    geo_group.add_argument(
        '--auto-radars',
        action='store_true',
        help='Automatically select radars based on coverage area'
    )

    geo_group.add_argument(
        '--list-regions',
        action='store_true',
        help='List all available named regions and exit'
    )

    args = parser.parse_args()

    # Handle --create-config
    if args.create_config:
        create_sample_config(args.create_config)
        return

    # Handle --list-regions
    if args.list_regions:
        print_regions()
        return

    # Load configuration from file
    file_config = {}
    config_path = args.config or find_config_file()

    if config_path:
        try:
            file_config = load_config(config_path)
            print(f"Loaded configuration from: {config_path}")
        except FileNotFoundError:
            if args.config:  # Only error if explicitly specified
                print(f"Error: Config file not found: {config_path}")
                sys.exit(1)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)

    # Handle --show-config
    if args.show_config:
        show_current_config(file_config, args)
        return

    # Parse coverage center coordinates
    coverage_center_lat = None
    coverage_center_lon = None
    if args.coverage_center:
        try:
            parts = args.coverage_center.split(',')
            coverage_center_lat = float(parts[0].strip())
            coverage_center_lon = float(parts[1].strip())
        except (ValueError, IndexError):
            print("Error: --coverage-center must be in format LAT,LON (e.g., 32.7767,-96.7970)")
            sys.exit(1)

    # Parse coverage bounds
    lat_min = lat_max = lon_min = lon_max = None
    if args.coverage_bounds:
        try:
            parts = args.coverage_bounds.split(',')
            lat_min = float(parts[0].strip())
            lat_max = float(parts[1].strip())
            lon_min = float(parts[2].strip())
            lon_max = float(parts[3].strip())
        except (ValueError, IndexError):
            print("Error: --coverage-bounds must be in format LAT_MIN,LAT_MAX,LON_MIN,LON_MAX")
            sys.exit(1)

    # Determine if SMS is enabled
    sms_enabled = args.sms_env or (args.sms_sid and args.sms_to)

    # Determine if email is enabled
    email_enabled = args.email_env or (args.email_smtp and args.email_to)

    # Demo mode
    if args.demo:
        # Build geo filter for demo if specified
        demo_geo_filter = None
        if args.coverage_region:
            try:
                demo_geo_filter = GeoFilter.from_named_region(args.coverage_region)
            except ValueError as e:
                print(f"Warning: {e}")
        elif coverage_center_lat and coverage_center_lon and args.coverage_radius:
            demo_geo_filter = GeoFilter.from_radius(
                coverage_center_lat, coverage_center_lon, args.coverage_radius
            )
        elif lat_min is not None:
            demo_geo_filter = GeoFilter.from_bounds(lat_min, lat_max, lon_min, lon_max)
        elif args.coverage_regions:
            filters = []
            for region in args.coverage_regions:
                try:
                    filters.append(GeoFilter.from_named_region(region.strip()))
                except ValueError as e:
                    print(f"Warning: {e}")
            if filters:
                demo_geo_filter = GeoFilter.composite(filters, operator='OR')

        run_demo(
            sms_enabled=sms_enabled,
            sms_use_env=args.sms_env,
            sms_sid=args.sms_sid,
            sms_token=args.sms_token,
            sms_from=args.sms_from,
            sms_to=args.sms_to,
            sms_level=args.sms_level,
            ntfy_topic=args.ntfy,
            ntfy_server=args.ntfy_server,
            pushover_user=args.pushover_user,
            pushover_token=args.pushover_token,
            push_level=args.push_level,
            email_enabled=email_enabled,
            email_use_env=args.email_env,
            email_smtp=args.email_smtp,
            email_port=args.email_port,
            email_user=args.email_user,
            email_password=args.email_password,
            email_from=args.email_from,
            email_to=args.email_to,
            email_level=args.email_level,
            database_enabled=not args.no_database,
            database_url=args.database,
            geo_filter=demo_geo_filter
        )
        return

    # Build configuration - start with file config, override with CLI args
    config_args = config_to_monitor_args(file_config) if file_config else {}

    # Override with CLI arguments (CLI takes precedence over file)
    cli_overrides = {
        'scan_interval_seconds': args.interval,
        'min_reflectivity_dbz': args.min_reflectivity,
        'min_mesh_mm': args.min_mesh,
        'min_pdr_score': args.threshold,
        'enable_sound': not args.no_sound,
        'enable_console': not args.no_console,
        'webhook_url': args.webhook,
        'webhook_platform': args.webhook_platform,
        # SMS settings
        'sms_enabled': sms_enabled or config_args.get('sms_enabled', False),
        'sms_use_env': args.sms_env or config_args.get('sms_use_env', False),
        'sms_account_sid': args.sms_sid or config_args.get('sms_account_sid'),
        'sms_auth_token': args.sms_token or config_args.get('sms_auth_token'),
        'sms_from_number': args.sms_from or config_args.get('sms_from_number'),
        'sms_to_numbers': args.sms_to or config_args.get('sms_to_numbers', []),
        'sms_min_level': args.sms_level,
        # Push notification settings
        'ntfy_topic': args.ntfy or config_args.get('ntfy_topic'),
        'ntfy_server': args.ntfy_server or config_args.get('ntfy_server', 'https://ntfy.sh'),
        'pushover_user': args.pushover_user or config_args.get('pushover_user'),
        'pushover_token': args.pushover_token or config_args.get('pushover_token'),
        'push_min_level': args.push_level,
        # Email settings
        'email_enabled': email_enabled or config_args.get('email_enabled', False),
        'email_use_env': args.email_env or config_args.get('email_use_env', False),
        'email_smtp_server': args.email_smtp or config_args.get('email_smtp_server'),
        'email_smtp_port': args.email_port or config_args.get('email_smtp_port', 587),
        'email_username': args.email_user or config_args.get('email_username'),
        'email_password': args.email_password or config_args.get('email_password'),
        'email_from': args.email_from or config_args.get('email_from'),
        'email_to': args.email_to or config_args.get('email_to', []),
        'email_min_level': args.email_level,
        # Database settings
        'database_enabled': not args.no_database,
        'database_url': args.database,
        # Geographic coverage settings (CLI overrides file config)
        'lat_min': lat_min or config_args.get('lat_min'),
        'lat_max': lat_max or config_args.get('lat_max'),
        'lon_min': lon_min or config_args.get('lon_min'),
        'lon_max': lon_max or config_args.get('lon_max'),
        'coverage_region': args.coverage_region or config_args.get('coverage_region'),
        'coverage_center_lat': coverage_center_lat or config_args.get('coverage_center_lat'),
        'coverage_center_lon': coverage_center_lon or config_args.get('coverage_center_lon'),
        'coverage_radius_miles': args.coverage_radius or config_args.get('coverage_radius_miles'),
        'coverage_regions': args.coverage_regions or config_args.get('coverage_regions', []),
        'auto_select_radars': args.auto_radars or config_args.get('auto_select_radars', False),
    }

    # Remove None values to use MonitorConfig defaults
    final_config = {k: v for k, v in cli_overrides.items() if v is not None}

    # Create MonitorConfig
    config = MonitorConfig(**final_config)

    # Set radars (CLI > file config > default)
    if args.radars:
        config.radar_ids = args.radars
    elif config_args.get('radar_ids'):
        config.radar_ids = config_args['radar_ids']

    # Print banner
    print_banner()

    # Create and start monitor
    try:
        monitor = StormMonitor(config)
        monitor.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


def print_banner():
    """Print startup banner."""
    banner = """
    +====================================================================+
    |                                                                    |
    |   ***  HAILTRACKER PRO - REAL-TIME STORM ALERTS  ***               |
    |                                                                    |
    |   Monitoring NEXRAD radar for hail events                          |
    |   ML-powered analysis with 85% accuracy                            |
    |                                                                    |
    +====================================================================+
    """
    print(banner)


def print_regions():
    """Print available named regions."""
    regions = list_named_regions()

    print("\n" + "=" * 70)
    print("AVAILABLE COVERAGE REGIONS")
    print("=" * 70)

    # Group by type
    states = []
    metros = []
    special = []

    for name, info in sorted(regions.items()):
        bounds = info['bounds']
        if name in ['hail_alley_core', 'tornado_alley', 'dixie_alley']:
            special.append((name, bounds))
        elif any(x in name for x in ['_city', 'dallas', 'denver', 'omaha', 'minneapolis',
                                      'san_antonio', 'austin', 'houston', 'tulsa', 'wichita',
                                      'des_moines', 'st_louis', 'atlanta', 'nashville',
                                      'memphis', 'chicago', 'indianapolis', 'detroit', 'columbus']):
            metros.append((name, bounds))
        else:
            states.append((name, bounds))

    print("\nSTATES:")
    print("-" * 60)
    for name, bounds in states:
        lat_range = f"{bounds['lat_min']:.1f}-{bounds['lat_max']:.1f}N"
        lon_range = f"{bounds['lon_min']:.1f}-{bounds['lon_max']:.1f}W"
        print(f"  {name:<20} {lat_range:<15} {lon_range}")

    print("\nMETRO AREAS:")
    print("-" * 60)
    for name, bounds in metros:
        lat_range = f"{bounds['lat_min']:.1f}-{bounds['lat_max']:.1f}N"
        lon_range = f"{bounds['lon_min']:.1f}-{bounds['lon_max']:.1f}W"
        print(f"  {name:<20} {lat_range:<15} {lon_range}")

    print("\nSPECIAL REGIONS:")
    print("-" * 60)
    for name, bounds in special:
        lat_range = f"{bounds['lat_min']:.1f}-{bounds['lat_max']:.1f}N"
        lon_range = f"{bounds['lon_min']:.1f}-{bounds['lon_max']:.1f}W"
        print(f"  {name:<20} {lat_range:<15} {lon_range}")

    print("\n" + "=" * 70)
    print("\nEXAMPLES:")
    print("  python run_realtime_alerts.py --coverage-region dallas_fort_worth")
    print("  python run_realtime_alerts.py --coverage-region texas --auto-radars")
    print("  python run_realtime_alerts.py --coverage-regions dallas_fort_worth oklahoma_city")
    print("  python run_realtime_alerts.py --coverage-center 32.7767,-96.7970 --coverage-radius 50")
    print()


def show_current_config(file_config, args):
    """Display current configuration from file and CLI."""
    import json

    print("\n" + "=" * 70)
    print("CURRENT CONFIGURATION")
    print("=" * 70)

    if file_config:
        print("\nFrom config file:")
        print("-" * 40)

        # Show key settings
        if file_config.get('radars'):
            print(f"  Radars: {', '.join(file_config['radars'])}")

        thresholds = file_config.get('thresholds', {})
        if thresholds:
            print(f"  Min PDR Score: {thresholds.get('min_pdr_score', 40)}")

        coverage = file_config.get('coverage', {})
        if coverage.get('region'):
            print(f"  Coverage Region: {coverage['region']}")
        if coverage.get('center'):
            print(f"  Coverage Center: {coverage['center']}")
            print(f"  Coverage Radius: {coverage.get('radius_miles')} miles")

        # Notifications
        sms = file_config.get('sms', {})
        if sms.get('enabled'):
            print(f"  SMS: Enabled (min level: {sms.get('min_level', 'WARNING')})")

        push = file_config.get('push', {})
        if push.get('ntfy', {}).get('enabled'):
            print(f"  ntfy: {push['ntfy'].get('topic')}")
        if push.get('pushover', {}).get('enabled'):
            print(f"  Pushover: Enabled")

        email = file_config.get('email', {})
        if email.get('enabled'):
            print(f"  Email: Enabled (min level: {email.get('min_level', 'WARNING')})")

        db = file_config.get('database', {})
        if db.get('enabled'):
            print(f"  Database: {db.get('url', 'sqlite:///data/alerts/alerts.db')}")
    else:
        print("\nNo config file loaded (using CLI arguments and defaults)")

    print("\n" + "=" * 70)
    print("\nTo create a config file, run:")
    print("  python run_realtime_alerts.py --create-config")
    print()


def run_demo(
    sms_enabled=False,
    sms_use_env=False,
    sms_sid=None,
    sms_token=None,
    sms_from=None,
    sms_to=None,
    sms_level='WARNING',
    ntfy_topic=None,
    ntfy_server='https://ntfy.sh',
    pushover_user=None,
    pushover_token=None,
    push_level='WARNING',
    email_enabled=False,
    email_use_env=False,
    email_smtp=None,
    email_port=587,
    email_user=None,
    email_password=None,
    email_from=None,
    email_to=None,
    email_level='WARNING',
    database_enabled=True,
    database_url='sqlite:///data/alerts/alerts.db',
    geo_filter=None
):
    """Run a demo with simulated alerts."""
    from datetime import datetime
    from src.alerts.alert_manager import Alert, AlertLevel, AlertManager
    from src.alerts.notifiers import ConsoleNotifier, SoundNotifier

    print_banner()
    print("\n" + "=" * 70)
    print("DEMO MODE - Simulated Alerts")
    print("=" * 70 + "\n")

    # Create alert manager with notifiers
    manager = AlertManager()
    manager.add_notifier(ConsoleNotifier(use_colors=True))
    manager.add_notifier(SoundNotifier())

    # Map level string to AlertLevel
    level_map = {
        'INFO': AlertLevel.INFO,
        'WATCH': AlertLevel.WATCH,
        'WARNING': AlertLevel.WARNING,
        'CRITICAL': AlertLevel.CRITICAL
    }

    # Add SMS notifier if configured
    if sms_enabled:
        print("SMS ALERTS ENABLED")
        print("-" * 40)

        min_level = level_map.get(sms_level, AlertLevel.WARNING)

        if sms_use_env:
            from src.alerts.notifiers import TwilioNotifierFromEnv
            sms_notifier = TwilioNotifierFromEnv(min_level=min_level)
            manager.add_notifier(sms_notifier)
            print(f"Using environment variables for Twilio")
        elif sms_sid and sms_to:
            from src.alerts.notifiers import TwilioNotifier
            sms_notifier = TwilioNotifier(
                account_sid=sms_sid,
                auth_token=sms_token,
                from_number=sms_from,
                to_numbers=sms_to,
                min_level=min_level
            )
            manager.add_notifier(sms_notifier)
            print(f"Sending SMS to: {', '.join(sms_to)}")

        print(f"Minimum SMS level: {sms_level}")
        print("-" * 40 + "\n")

    # Add push notification notifiers if configured
    push_enabled = ntfy_topic or (pushover_user and pushover_token)
    if push_enabled:
        print("PUSH NOTIFICATIONS ENABLED")
        print("-" * 40)

        push_min_level = level_map.get(push_level, AlertLevel.WARNING)

        if ntfy_topic:
            from src.alerts.notifiers import NtfyNotifier
            ntfy_notifier = NtfyNotifier(
                topic=ntfy_topic,
                server=ntfy_server,
                min_level=push_min_level
            )
            manager.add_notifier(ntfy_notifier)
            print(f"ntfy topic: {ntfy_topic}")
            print(f"ntfy server: {ntfy_server}")

        if pushover_user and pushover_token:
            from src.alerts.notifiers import PushoverNotifier
            pushover_notifier = PushoverNotifier(
                user_key=pushover_user,
                api_token=pushover_token,
                min_level=push_min_level
            )
            manager.add_notifier(pushover_notifier)
            print(f"Pushover: enabled")

        print(f"Minimum push level: {push_level}")
        print("-" * 40 + "\n")

    # Add email notifier if configured
    if email_enabled:
        print("EMAIL ALERTS ENABLED")
        print("-" * 40)

        email_min_level = level_map.get(email_level, AlertLevel.WARNING)

        if email_use_env:
            from src.alerts.notifiers import EmailNotifierFromEnv
            email_notifier = EmailNotifierFromEnv(min_level=email_min_level)
            manager.add_notifier(email_notifier)
            print("Using environment variables for email")
        elif email_smtp and email_to:
            from src.alerts.notifiers import EmailNotifier
            email_notifier = EmailNotifier(
                smtp_server=email_smtp,
                smtp_port=email_port,
                username=email_user,
                password=email_password,
                from_address=email_from or email_user,
                to_addresses=email_to,
                min_level=email_min_level
            )
            manager.add_notifier(email_notifier)
            print(f"SMTP Server: {email_smtp}:{email_port}")
            print(f"Sending to: {', '.join(email_to)}")

        print(f"Minimum email level: {email_level}")
        print("-" * 40 + "\n")

    # Add database storage if enabled
    database = None
    if database_enabled:
        print("DATABASE STORAGE ENABLED")
        print("-" * 40)
        try:
            from src.alerts.database import AlertDatabase, DatabaseNotifier
            database = AlertDatabase(database_url)
            manager.add_notifier(DatabaseNotifier(database))
            print(f"Database: {database_url}")
            print(f"Existing alerts: {database.get_count()}")
        except Exception as e:
            print(f"Database error: {e}")
        print("-" * 40 + "\n")

    # Demo alerts
    demo_alerts = [
        {
            'level': AlertLevel.INFO,
            'name': 'Minor Storm Activity',
            'location': (35.4676, -97.5164),
            'radar': 'KTLX',
            'hail': False,
            'prob': 25,
            'size': 0,
            'severity': 'none',
            'pdr': 15,
            'ref': 48,
            'mesh': 8,
            'posh': 20
        },
        {
            'level': AlertLevel.WATCH,
            'name': 'Developing Storm',
            'location': (32.7767, -96.7970),
            'radar': 'KFWS',
            'hail': True,
            'prob': 55,
            'size': 18,
            'severity': 'light',
            'pdr': 45,
            'ref': 58,
            'mesh': 22,
            'posh': 55
        },
        {
            'level': AlertLevel.WARNING,
            'name': 'Hail Storm - DFW Metro',
            'location': (32.8500, -96.8500),
            'radar': 'KFWS',
            'hail': True,
            'prob': 78,
            'size': 32,
            'severity': 'moderate',
            'pdr': 72,
            'ref': 65,
            'mesh': 35,
            'posh': 82
        },
        {
            'level': AlertLevel.CRITICAL,
            'name': 'SEVERE HAIL - Wichita Supercell',
            'location': (37.6872, -97.3301),
            'radar': 'KICT',
            'hail': True,
            'prob': 95,
            'size': 52,
            'severity': 'severe',
            'pdr': 88,
            'ref': 72,
            'mesh': 55,
            'posh': 98
        }
    ]

    # Show geo filter info if configured
    if geo_filter:
        print("GEOGRAPHIC FILTER ENABLED")
        print("-" * 40)
        print(f"Filter: {geo_filter.describe()}")
        bounds = geo_filter.get_bounds()
        if bounds:
            print(f"Bounds: {bounds['lat_min']:.2f} to {bounds['lat_max']:.2f}N, "
                  f"{bounds['lon_min']:.2f} to {bounds['lon_max']:.2f}W")
        print("-" * 40 + "\n")

    print("Generating demo alerts at increasing severity levels...\n")
    print("(In production, these would come from real NEXRAD analysis)\n")

    import time
    filtered_count = 0

    for i, demo in enumerate(demo_alerts, 1):
        # Apply geographic filter
        if geo_filter:
            lat, lon = demo['location']
            if not geo_filter.contains(lat, lon):
                print(f"\n[Demo {i}/4] FILTERED: {demo['name']} at ({lat:.2f}, {lon:.2f}) - outside coverage area")
                filtered_count += 1
                time.sleep(1)
                continue

        print(f"\n[Demo {i}/4] Generating {demo['level'].name} alert...")
        time.sleep(2)

        alert = Alert(
            id=f"DEMO-{i:04d}",
            timestamp=datetime.now(),
            level=demo['level'],
            event_name=demo['name'],
            location=demo['location'],
            radar_id=demo['radar'],
            hail_detected=demo['hail'],
            hail_probability=demo['prob'],
            hail_size_mm=demo['size'],
            severity=demo['severity'],
            pdr_score=demo['pdr'],
            max_reflectivity=demo['ref'],
            mesh_mm=demo['mesh'],
            posh=demo['posh'],
            message=f"Demo alert - {demo['level'].name} level",
            recommendations=[
                "This is a demonstration alert",
                "In production, real radar data would be analyzed",
                "Alerts would be dispatched to configured channels"
            ]
        )

        manager.dispatch_alert(alert)
        time.sleep(3)

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)

    # Show filtered count if geo filter was used
    if geo_filter and filtered_count > 0:
        print(f"\nGeographic Filter Results:")
        print(f"  Alerts filtered (outside coverage): {filtered_count}")
        print(f"  Alerts dispatched: {len(demo_alerts) - filtered_count}")

    # Show database statistics if enabled
    if database:
        print("\nDATABASE SUMMARY")
        print("-" * 40)
        stats = database.get_statistics(days=1)
        print(f"Total alerts stored: {database.get_count()}")
        print(f"Today's alerts: {stats['total_alerts']}")
        print(f"  - Critical: {stats['by_level']['critical']}")
        print(f"  - Warning: {stats['by_level']['warning']}")
        print(f"  - Watch: {stats['by_level']['watch']}")
        print(f"  - Info: {stats['by_level']['info']}")
        print(f"Average PDR Score: {stats['avg_pdr_score']}")
        print(f"Max Hail Size: {stats['max_hail_size_mm']}mm")
        print("-" * 40)

    print("\nTo start real monitoring, run:")
    print("  python run_realtime_alerts.py")
    print("\nOr with custom settings:")
    print("  python run_realtime_alerts.py --radars KFWS KTLX --interval 60")
    print()


if __name__ == '__main__':
    main()
