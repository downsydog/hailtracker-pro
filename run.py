#!/usr/bin/env python3
"""
HailTracker Pro - Main Entry Point

Starts the HailTracker Pro web application and optional live monitoring.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.web.app import create_app


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='HailTracker Pro - North America Hail Tracking Platform'
    )
    parser.add_argument(
        '--host', default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port', type=int, default=5000,
        help='Port to listen on (default: 5000)'
    )
    parser.add_argument(
        '--debug', action='store_true',
        help='Enable debug mode'
    )
    parser.add_argument(
        '--monitor', action='store_true',
        help='Start live monitoring'
    )
    parser.add_argument(
        '--monitor-interval', type=int, default=300,
        help='Monitor check interval in seconds (default: 300)'
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger('HailTrackerPro')

    # Display banner
    print("""
    ===========================================================
    |                                                         |
    |   HAILTRACKER PRO                                       |
    |   North America Edition v2.0.0                          |
    |                                                         |
    |   Coverage: USA (154) | Canada (31) | Mexico (16)       |
    |   Total: 201 Active Radar Sites                         |
    |                                                         |
    ===========================================================
    """)

    # Start live monitoring if requested
    monitor = None
    if args.monitor:
        logger.info("Starting live monitoring...")
        from src.monitoring.live import create_national_monitor
        monitor = create_national_monitor()
        monitor.check_interval = args.monitor_interval
        monitor.start()
        logger.info("Live monitoring active")

    # Create and run Flask app
    logger.info(f"Starting web server on {args.host}:{args.port}")

    app = create_app({
        'DEBUG': args.debug,
        'DATABASE_PATH': str(PROJECT_ROOT / 'database' / 'hailtracker_pro.db')
    })

    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=False if args.monitor else args.debug
        )
    finally:
        if monitor:
            logger.info("Stopping live monitoring...")
            monitor.stop()


if __name__ == '__main__':
    main()
