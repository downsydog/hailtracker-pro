"""
Unified Real-Time Severe Weather Monitor

Combines all FREE data sources:
- NWS Alerts (weather.gov)
- Iowa Environmental Mesonet (Local Storm Reports)
- Storm Prediction Center (watches, outlooks)

Provides:
- Real-time severe weather alerts
- Verified hail reports with sizes
- Convective outlooks and risk areas
- Push notification callbacks for new events
"""

import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Callable, Optional
import logging
from dataclasses import dataclass, field

from .nws_alerts import NWSAlerts
from .iowa_mesonet import IowaMesonet
from .spc import StormPredictionCenter

logger = logging.getLogger(__name__)


@dataclass
class MonitorState:
    """Current state of the monitor."""
    alerts: List[Dict] = field(default_factory=list)
    hail_reports: List[Dict] = field(default_factory=list)
    tornado_reports: List[Dict] = field(default_factory=list)
    wind_reports: List[Dict] = field(default_factory=list)
    watches: List[Dict] = field(default_factory=list)
    outlooks: Dict = field(default_factory=dict)
    last_update: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)


class RealtimeMonitor:
    """
    Unified real-time severe weather monitor.

    Combines NWS Alerts, Iowa Mesonet LSRs, and SPC data into
    a single monitoring service with background updates.

    Usage:
        monitor = RealtimeMonitor()
        monitor.on_new_hail_report = my_callback
        monitor.start(interval_seconds=60)
    """

    def __init__(self):
        self.nws = NWSAlerts()
        self.iem = IowaMesonet()
        self.spc = StormPredictionCenter()

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.state = MonitorState()

        # Callbacks for push notifications
        self.on_new_alert: Optional[Callable[[Dict], None]] = None
        self.on_new_hail_report: Optional[Callable[[Dict], None]] = None
        self.on_new_tornado_report: Optional[Callable[[Dict], None]] = None
        self.on_new_watch: Optional[Callable[[Dict], None]] = None
        self.on_update: Optional[Callable[[MonitorState], None]] = None

        # Tracking for change detection
        self._seen_alert_ids: set = set()
        self._seen_report_keys: set = set()
        self._seen_watch_ids: set = set()

    def fetch_alerts(self) -> List[Dict]:
        """Fetch current NWS hail alerts."""
        try:
            alerts = self.nws.get_hail_alerts()
            logger.debug(f"Fetched {len(alerts)} hail alerts")
            return alerts
        except Exception as e:
            logger.error(f"Error fetching NWS alerts: {e}")
            self.state.errors.append(f"NWS Alerts: {str(e)}")
            return []

    def fetch_hail_reports(self, hours: int = 6) -> List[Dict]:
        """Fetch recent hail reports from IEM."""
        try:
            reports = self.iem.get_hail_reports(hours=hours)
            logger.debug(f"Fetched {len(reports)} hail reports")
            return reports
        except Exception as e:
            logger.error(f"Error fetching hail reports: {e}")
            self.state.errors.append(f"IEM Hail Reports: {str(e)}")
            return []

    def fetch_tornado_reports(self, hours: int = 6) -> List[Dict]:
        """Fetch recent tornado reports from IEM."""
        try:
            reports = self.iem.get_tornado_reports(hours=hours)
            logger.debug(f"Fetched {len(reports)} tornado reports")
            return reports
        except Exception as e:
            logger.error(f"Error fetching tornado reports: {e}")
            self.state.errors.append(f"IEM Tornado Reports: {str(e)}")
            return []

    def fetch_wind_reports(self, hours: int = 6) -> List[Dict]:
        """Fetch recent damaging wind reports from IEM."""
        try:
            reports = self.iem.get_wind_reports(hours=hours)
            logger.debug(f"Fetched {len(reports)} wind reports")
            return reports
        except Exception as e:
            logger.error(f"Error fetching wind reports: {e}")
            self.state.errors.append(f"IEM Wind Reports: {str(e)}")
            return []

    def fetch_watches(self) -> List[Dict]:
        """Fetch current SPC watches."""
        try:
            watches = self.spc.get_current_watches()
            logger.debug(f"Fetched {len(watches)} watches")
            return watches
        except Exception as e:
            logger.error(f"Error fetching watches: {e}")
            self.state.errors.append(f"SPC Watches: {str(e)}")
            return []

    def fetch_outlooks(self) -> Dict:
        """Fetch current SPC outlooks."""
        try:
            outlooks = {
                'categorical': self.spc.get_convective_outlook_day1(),
                'hail': self.spc.get_hail_outlook_day1(),
                'tornado': self.spc.get_tornado_outlook_day1(),
                'wind': self.spc.get_wind_outlook_day1(),
            }
            return outlooks
        except Exception as e:
            logger.error(f"Error fetching outlooks: {e}")
            self.state.errors.append(f"SPC Outlooks: {str(e)}")
            return {}

    def fetch_all(self, report_hours: int = 6) -> Dict:
        """
        Fetch all real-time data from all sources.

        Args:
            report_hours: How many hours of reports to fetch

        Returns:
            Dictionary with all data and metadata
        """
        self.state.errors = []

        # Fetch all data
        alerts = self.fetch_alerts()
        hail_reports = self.fetch_hail_reports(report_hours)
        tornado_reports = self.fetch_tornado_reports(report_hours)
        wind_reports = self.fetch_wind_reports(report_hours)
        watches = self.fetch_watches()
        outlooks = self.fetch_outlooks()

        # Update state
        self.state.alerts = alerts
        self.state.hail_reports = hail_reports
        self.state.tornado_reports = tornado_reports
        self.state.wind_reports = wind_reports
        self.state.watches = watches
        self.state.outlooks = outlooks
        self.state.last_update = datetime.utcnow()

        # Call update callback
        if self.on_update:
            try:
                self.on_update(self.state)
            except Exception as e:
                logger.error(f"Error in on_update callback: {e}")

        return {
            'timestamp': self.state.last_update.isoformat(),
            'alerts': alerts,
            'hail_reports': hail_reports,
            'tornado_reports': tornado_reports,
            'wind_reports': wind_reports,
            'watches': watches,
            'outlooks': outlooks,
            'errors': self.state.errors,
            'summary': {
                'active_alerts': len(alerts),
                'hail_reports_count': len(hail_reports),
                'tornado_reports_count': len(tornado_reports),
                'wind_reports_count': len(wind_reports),
                'active_watches': len(watches),
            }
        }

    def _check_for_new_events(
        self,
        new_alerts: List[Dict],
        new_hail: List[Dict],
        new_tornado: List[Dict],
        new_watches: List[Dict]
    ):
        """Check for new events and trigger callbacks."""

        # Check for new alerts
        for alert in new_alerts:
            alert_id = alert.get('id') or alert.get('headline', '')
            if alert_id and alert_id not in self._seen_alert_ids:
                self._seen_alert_ids.add(alert_id)
                if self.on_new_alert:
                    try:
                        self.on_new_alert(alert)
                    except Exception as e:
                        logger.error(f"Error in on_new_alert callback: {e}")

        # Check for new hail reports
        for report in new_hail:
            key = f"{report.get('lat')},{report.get('lon')},{report.get('valid_time')}"
            if key not in self._seen_report_keys:
                self._seen_report_keys.add(key)
                if self.on_new_hail_report:
                    try:
                        self.on_new_hail_report(report)
                    except Exception as e:
                        logger.error(f"Error in on_new_hail_report callback: {e}")

        # Check for new tornado reports
        for report in new_tornado:
            key = f"tor_{report.get('lat')},{report.get('lon')},{report.get('valid_time')}"
            if key not in self._seen_report_keys:
                self._seen_report_keys.add(key)
                if self.on_new_tornado_report:
                    try:
                        self.on_new_tornado_report(report)
                    except Exception as e:
                        logger.error(f"Error in on_new_tornado_report callback: {e}")

        # Check for new watches
        for watch in new_watches:
            watch_id = watch.get('id', '')
            if watch_id and watch_id not in self._seen_watch_ids:
                self._seen_watch_ids.add(watch_id)
                if self.on_new_watch:
                    try:
                        self.on_new_watch(watch)
                    except Exception as e:
                        logger.error(f"Error in on_new_watch callback: {e}")

    def start(self, interval_seconds: int = 60, report_hours: int = 6):
        """
        Start the background monitoring thread.

        Args:
            interval_seconds: How often to fetch updates (default 60)
            report_hours: How many hours of reports to fetch
        """
        if self.running:
            logger.warning("Monitor already running")
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds, report_hours),
            daemon=True
        )
        self.thread.start()
        logger.info(f"Realtime monitor started (interval: {interval_seconds}s)")

    def stop(self):
        """Stop the monitoring thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None
        logger.info("Realtime monitor stopped")

    def _monitor_loop(self, interval: int, report_hours: int):
        """Background loop that fetches data periodically."""
        # Initial fetch
        self.fetch_all(report_hours)

        while self.running:
            try:
                time.sleep(interval)

                if not self.running:
                    break

                # Fetch new data
                new_alerts = self.fetch_alerts()
                new_hail = self.fetch_hail_reports(report_hours)
                new_tornado = self.fetch_tornado_reports(report_hours)
                new_wind = self.fetch_wind_reports(report_hours)
                new_watches = self.fetch_watches()

                # Check for new events (triggers callbacks)
                self._check_for_new_events(
                    new_alerts, new_hail, new_tornado, new_watches
                )

                # Update state
                self.state.alerts = new_alerts
                self.state.hail_reports = new_hail
                self.state.tornado_reports = new_tornado
                self.state.wind_reports = new_wind
                self.state.watches = new_watches
                self.state.last_update = datetime.utcnow()

                # Refresh outlooks less frequently (every 10 minutes)
                if not hasattr(self, '_last_outlook_fetch'):
                    self._last_outlook_fetch = datetime.min
                if datetime.utcnow() - self._last_outlook_fetch > timedelta(minutes=10):
                    self.state.outlooks = self.fetch_outlooks()
                    self._last_outlook_fetch = datetime.utcnow()

                # Call update callback
                if self.on_update:
                    try:
                        self.on_update(self.state)
                    except Exception as e:
                        logger.error(f"Error in on_update callback: {e}")

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

    def get_status(self) -> Dict:
        """Get current monitor status."""
        return {
            'running': self.running,
            'last_update': self.state.last_update.isoformat() if self.state.last_update else None,
            'active_alerts': len(self.state.alerts),
            'hail_reports': len(self.state.hail_reports),
            'tornado_reports': len(self.state.tornado_reports),
            'wind_reports': len(self.state.wind_reports),
            'active_watches': len(self.state.watches),
            'errors': self.state.errors,
        }

    def get_hail_summary(self) -> Dict:
        """Get summary of current hail activity."""
        reports = self.state.hail_reports
        alerts = self.state.alerts

        if not reports and not alerts:
            return {
                'status': 'quiet',
                'message': 'No significant hail activity',
                'hail_reports': 0,
                'hail_alerts': 0,
            }

        # Get max sizes
        report_sizes = [r.get('hail_size_inches', 0) for r in reports if r.get('hail_size_inches')]
        alert_sizes = [a.get('hail_size_inches', 0) for a in alerts if a.get('hail_size_inches')]

        max_report = max(report_sizes) if report_sizes else 0
        max_alert = max(alert_sizes) if alert_sizes else 0
        max_size = max(max_report, max_alert)

        # Determine activity level
        if max_size >= 2.0:
            status = 'severe'
            message = f'SEVERE hail up to {max_size}" reported'
        elif max_size >= 1.0:
            status = 'significant'
            message = f'Significant hail up to {max_size}" reported'
        else:
            status = 'minor'
            message = f'Minor hail activity up to {max_size}"'

        # Group by state
        states = {}
        for r in reports:
            state = r.get('state', 'Unknown')
            if state not in states:
                states[state] = {'count': 0, 'max_size': 0}
            states[state]['count'] += 1
            size = r.get('hail_size_inches', 0)
            if size > states[state]['max_size']:
                states[state]['max_size'] = size

        return {
            'status': status,
            'message': message,
            'hail_reports': len(reports),
            'hail_alerts': len(alerts),
            'max_size_inches': max_size,
            'by_state': states,
            'largest_reports': reports[:5] if reports else [],
        }


# Global monitor instance
_monitor: Optional[RealtimeMonitor] = None


def get_monitor() -> RealtimeMonitor:
    """Get or create the global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = RealtimeMonitor()
    return _monitor


def reset_monitor():
    """Reset the global monitor instance."""
    global _monitor
    if _monitor:
        _monitor.stop()
    _monitor = None


# Test function
def test_realtime_monitor():
    """Test the real-time monitor."""
    print("Testing Real-Time Monitor...")

    def on_hail(report):
        size = report.get('hail_size_inches', 'Unknown')
        city = report.get('city', 'Unknown')
        state = report.get('state', '')
        print(f"  [NEW HAIL] {size}\" in {city}, {state}")

    def on_alert(alert):
        print(f"  [NEW ALERT] {alert.get('headline', 'Unknown')}")

    monitor = RealtimeMonitor()
    monitor.on_new_hail_report = on_hail
    monitor.on_new_alert = on_alert

    # Fetch all data
    print("\n[Fetching all data...]")
    data = monitor.fetch_all(report_hours=24)

    print(f"\nSummary:")
    print(f"  Active alerts: {data['summary']['active_alerts']}")
    print(f"  Hail reports (24h): {data['summary']['hail_reports_count']}")
    print(f"  Tornado reports: {data['summary']['tornado_reports_count']}")
    print(f"  Wind reports: {data['summary']['wind_reports_count']}")
    print(f"  Active watches: {data['summary']['active_watches']}")

    # Get hail summary
    print("\n[Hail Summary]")
    summary = monitor.get_hail_summary()
    print(f"  Status: {summary['status']}")
    print(f"  Message: {summary['message']}")

    if summary.get('by_state'):
        print("  By state:")
        for state, info in summary['by_state'].items():
            print(f"    {state}: {info['count']} reports, max {info['max_size']}\"")

    # Test status
    print("\n[Monitor Status]")
    status = monitor.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    print("\nReal-time monitor test complete!")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_realtime_monitor()
