#!/usr/bin/env python3
"""
HailTracker Pro - Main Entry Point

Starts the HailTracker Pro web application and optional live monitoring.
"""

import os
import sys
import time
import argparse
import logging
import threading
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

    # Configure logging (HARDEN-3: structured logging support)
    from src.observability.logging_config import configure_logging
    log_level_str = 'DEBUG' if args.debug else 'INFO'
    configure_logging(log_level=log_level_str)

    logger = logging.getLogger('HailTrackerPro')

    # Install signal handlers for graceful shutdown (SIGTERM/SIGINT)
    from src.safety.shutdown import install_shutdown_handlers, is_shutting_down
    install_shutdown_handlers()

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

    # Create Flask app first (so blueprint globals are importable)
    logger.info(f"Starting web server on {args.host}:{args.port}")

    app = create_app({
        'DEBUG': args.debug,
        'DATABASE_PATH': str(PROJECT_ROOT / 'database' / 'hailtracker_pro.db')
    })

    # Apply PostGIS migrations (001-004) on startup if using PostgreSQL
    try:
        from src.db.engine import ensure_schema, get_engine_info
        ensure_schema()
        info = get_engine_info()
        logger.info("Database backend: %s  (%s)", info['backend'],
                     info.get('database', ''))
    except Exception as e:
        logger.warning("Schema migration on startup failed (non-fatal): %s", e)

    # Start StormMonitor (real radar engine) if requested — ONE engine only
    monitor = None
    if args.monitor:
        logger.info("Starting StormMonitor (radar engine)...")
        from src.alerts.storm_monitor import StormMonitor, MonitorConfig
        from src.alerts.monitor_defaults import national_monitor_defaults

        # National defaults from env (or sane built-ins), then CLI override
        config = MonitorConfig(
            **national_monitor_defaults(),
            scan_interval_seconds=args.monitor_interval,
        )
        monitor = StormMonitor(config)
        monitor.start(background=True)

        # Share instance with API layer so /api/storm-monitor/* works
        from src.web.routes.storm_monitor_api import set_monitor_instance
        set_monitor_instance(monitor, started_by='cli')

        mode = 'discovery_focus' if config.enable_discovery_focus else 'legacy'
        logger.info(f"[ENGINE] storm_monitor started_by=cli "
                    f"mode={mode} workers={config.max_workers}")

        print(f"""
    ===========================================================
    |   ENGINE: StormMonitor ({mode}){'  ' if mode == 'discovery_focus' else '               '}|
    |   Started by: cli                                       |
    |   Workers: {config.max_workers:<3} | Batch: {config.max_discovery_radars_per_tick:<3} | Timeout: {config.per_radar_timeout_seconds}s{' ' * (12 - len(str(config.per_radar_timeout_seconds)))}|
    |   Discovery: {config.discovery_interval_seconds}s | Focus: {config.focus_interval_seconds}s | Hot TTL: {config.hot_ttl_seconds}s    |
    ===========================================================
        """)

    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=False if args.monitor else args.debug
        )
        # If app.run() returns normally, log it — this should never happen
        logger.warning("[MAIN] app.run() returned normally (unexpected)")
        print("[MAIN] app.run() returned normally — this should not happen",
              flush=True)
    except SystemExit as e:
        logger.warning("[MAIN] app.run() raised SystemExit(%s)", e.code)
        print(f"[MAIN] app.run() raised SystemExit({e.code})", flush=True)
    except KeyboardInterrupt:
        logger.info("[MAIN] KeyboardInterrupt — shutting down")
        print("[MAIN] KeyboardInterrupt", flush=True)
    except Exception as e:
        logger.error("[MAIN] app.run() raised %s: %s", type(e).__name__, e)
        print(f"[MAIN] app.run() raised {type(e).__name__}: {e}", flush=True)
    finally:
        # If monitor is running, keep the main thread alive so the daemon
        # thread's finally block (persist + swath) can complete the current tick.
        if monitor and monitor.running and not is_shutting_down():
            logger.warning("[MAIN] Flask exited but monitor still running — "
                           "keeping process alive")
            print("[MAIN] Flask exited but monitor still running — "
                  "keeping process alive (Ctrl+C or SIGTERM to stop)",
                  flush=True)
            try:
                while monitor.running and not is_shutting_down():
                    time.sleep(5)
            except (KeyboardInterrupt, SystemExit):
                pass

        if monitor:
            logger.info("Stopping StormMonitor...")
            monitor.stop()
        # Close DB connection pool
        from src.db.engine import close_engine
        close_engine()
        logger.info("[MAIN] shutdown complete, pid=%d", os.getpid())
        print(f"[MAIN] shutdown complete, pid={os.getpid()}", flush=True)


if __name__ == '__main__':
    main()
