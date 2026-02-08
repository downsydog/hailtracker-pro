"""
HailTracker Pro - Web Dashboard

Run a web-based dashboard for monitoring storm alerts.

Usage:
    python run_dashboard.py                    # Start dashboard on localhost:5000
    python run_dashboard.py --port 8080        # Use different port
    python run_dashboard.py --host 0.0.0.0     # Allow external connections
    python run_dashboard.py --with-monitor     # Start with live radar monitoring
"""

import argparse
import sys
import os
import time
import threading

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.alerts.alert_manager import AlertManager, Alert, AlertLevel
from src.alerts.web_dashboard import WebDashboard


def main():
    parser = argparse.ArgumentParser(
        description='HailTracker Pro - Web Alert Dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_dashboard.py
  python run_dashboard.py --port 8080
  python run_dashboard.py --host 0.0.0.0 --port 80
  python run_dashboard.py --with-monitor --radars KFWS KTLX

The dashboard provides:
  - Real-time alert visualization
  - Interactive map with alert locations
  - Alert statistics and history
  - Test alert generation
        """
    )

    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1, use 0.0.0.0 for external access)'
    )

    parser.add_argument(
        '--port', '-p',
        type=int,
        default=5000,
        help='Port to listen on (default: 5000)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable Flask debug mode'
    )

    parser.add_argument(
        '--with-monitor',
        action='store_true',
        help='Start with live radar monitoring'
    )

    parser.add_argument(
        '--radars', '-r',
        nargs='+',
        default=None,
        help='Radar IDs to monitor (with --with-monitor)'
    )

    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=300,
        help='Scan interval in seconds (with --with-monitor, default: 300)'
    )

    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run demo mode with simulated alerts'
    )

    args = parser.parse_args()

    print_banner()

    # Create alert manager
    alert_manager = AlertManager()

    # Create dashboard
    dashboard = WebDashboard(
        alert_manager=alert_manager,
        host=args.host,
        port=args.port,
        debug=args.debug
    )

    # Start with live monitoring if requested
    if args.with_monitor:
        start_monitor(alert_manager, args.radars, args.interval)

    # Start demo mode if requested
    if args.demo:
        start_demo(dashboard)

    # Run dashboard
    try:
        print(f"\nStarting dashboard at http://{args.host}:{args.port}")
        print("Press Ctrl+C to stop\n")

        if args.host == '0.0.0.0':
            print("WARNING: Dashboard is accessible from external connections")
            print("         Make sure you have appropriate firewall rules\n")

        dashboard.run(threaded=False)

    except KeyboardInterrupt:
        print("\n\nShutting down dashboard...")


def print_banner():
    """Print startup banner."""
    banner = """
    +====================================================================+
    |                                                                    |
    |   ***  HAILTRACKER PRO - WEB DASHBOARD  ***                        |
    |                                                                    |
    |   Real-time storm alert visualization                              |
    |   Interactive map and alert history                                |
    |                                                                    |
    +====================================================================+
    """
    print(banner)


def start_monitor(alert_manager: AlertManager, radars: list, interval: int):
    """Start radar monitoring in background."""
    try:
        from src.alerts.storm_monitor import StormMonitor, MonitorConfig

        config = MonitorConfig(
            scan_interval_seconds=interval
        )
        if radars:
            config.radar_ids = radars

        monitor = StormMonitor(config)

        # Share alert manager
        monitor.alert_manager = alert_manager

        # Start in background
        print("\nStarting radar monitor in background...")
        print(f"Monitoring: {', '.join(config.radar_ids)}")
        monitor.start(background=True)

    except Exception as e:
        print(f"Could not start monitor: {e}")


def start_demo(dashboard: WebDashboard):
    """Start demo mode with periodic alerts."""
    from datetime import datetime
    import random

    def demo_loop():
        demo_events = [
            {
                'level': AlertLevel.INFO,
                'name': 'Minor Storm - Oklahoma City',
                'lat': 35.4676, 'lon': -97.5164,
                'radar': 'KTLX',
                'prob': 25, 'size': 8, 'severity': 'none', 'pdr': 15
            },
            {
                'level': AlertLevel.WATCH,
                'name': 'Developing Storm - Dallas',
                'lat': 32.7767, 'lon': -96.7970,
                'radar': 'KFWS',
                'prob': 55, 'size': 18, 'severity': 'light', 'pdr': 45
            },
            {
                'level': AlertLevel.WARNING,
                'name': 'Hail Storm - Fort Worth',
                'lat': 32.7555, 'lon': -97.3308,
                'radar': 'KFWS',
                'prob': 78, 'size': 32, 'severity': 'moderate', 'pdr': 72
            },
            {
                'level': AlertLevel.CRITICAL,
                'name': 'SEVERE HAIL - Wichita',
                'lat': 37.6872, 'lon': -97.3301,
                'radar': 'KICT',
                'prob': 95, 'size': 52, 'severity': 'severe', 'pdr': 88
            },
            {
                'level': AlertLevel.WARNING,
                'name': 'Hail Event - Amarillo',
                'lat': 35.2220, 'lon': -101.8313,
                'radar': 'KAMA',
                'prob': 70, 'size': 28, 'severity': 'moderate', 'pdr': 65
            },
            {
                'level': AlertLevel.WATCH,
                'name': 'Storm Cell - Tulsa',
                'lat': 36.1540, 'lon': -95.9928,
                'radar': 'KINX',
                'prob': 48, 'size': 15, 'severity': 'light', 'pdr': 38
            }
        ]

        print("\nDemo mode: Generating alerts every 15-30 seconds...")
        alert_count = 0

        while True:
            time.sleep(random.randint(15, 30))
            alert_count += 1

            event = random.choice(demo_events)

            # Add some randomness to location
            lat = event['lat'] + random.uniform(-0.5, 0.5)
            lon = event['lon'] + random.uniform(-0.5, 0.5)

            alert = Alert(
                id=f"DEMO-{datetime.now().strftime('%H%M%S')}-{alert_count:04d}",
                timestamp=datetime.now(),
                level=event['level'],
                event_name=event['name'],
                location=(lat, lon),
                radar_id=event['radar'],
                hail_detected=event['level'] in [AlertLevel.WARNING, AlertLevel.CRITICAL],
                hail_probability=event['prob'] + random.randint(-10, 10),
                hail_size_mm=event['size'] + random.randint(-5, 10),
                severity=event['severity'],
                pdr_score=event['pdr'] + random.randint(-10, 10),
                max_reflectivity=55 + random.randint(0, 20),
                mesh_mm=event['size'] * 1.1,
                posh=event['prob'] + 10,
                message=f"Demo alert - {event['level'].name} level storm activity",
                recommendations=[
                    "This is a demonstration alert",
                    "Real alerts would come from NEXRAD data"
                ]
            )

            dashboard.add_alert(alert)
            print(f"[Demo] Generated {event['level'].name} alert: {event['name']}")

    thread = threading.Thread(target=demo_loop, daemon=True)
    thread.start()


if __name__ == '__main__':
    main()
