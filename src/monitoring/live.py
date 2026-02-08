"""
Live Hail Monitoring System

Real-time monitoring of radar data across North America for hail detection.
Supports all 201 radar sites (US, Canada, Mexico).
"""

import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.radar.coverage import get_all_radars, find_covering_radars, RadarSite

logger = logging.getLogger('LiveMonitor')


@dataclass
class LiveAlert:
    """Real-time hail alert."""
    alert_id: str
    timestamp: datetime
    radar_site: str
    lat: float
    lon: float
    mesh_inches: float
    alert_type: str  # 'new_detection', 'size_increase', 'approaching'
    severity: str    # 'watch', 'warning', 'emergency'
    message: str
    affected_area: Optional[str] = None


@dataclass
class MonitoredRegion:
    """A region being monitored for hail."""
    region_id: str
    name: str
    lat: float
    lon: float
    radius_km: float
    alert_threshold_inches: float
    radar_sites: List[str] = field(default_factory=list)
    callback: Optional[Callable] = None


class LiveMonitor:
    """
    Real-time hail monitoring across North America.

    Monitors radar sites for hail signatures and generates alerts.
    """

    def __init__(
        self,
        db_path: str = None,
        check_interval_seconds: int = 300
    ):
        """
        Initialize live monitor.

        Args:
            db_path: Database path
            check_interval_seconds: Interval between radar checks
        """
        self.db_path = db_path or str(PROJECT_ROOT / 'database' / 'hailtracker_pro.db')
        self.check_interval = check_interval_seconds

        # Monitoring state
        self.running = False
        self.monitored_regions: Dict[str, MonitoredRegion] = {}
        self.active_alerts: List[LiveAlert] = []
        self.alert_history: List[LiveAlert] = []

        # Statistics
        self.stats = {
            'start_time': None,
            'checks_performed': 0,
            'alerts_generated': 0,
            'last_check_time': None
        }

        # Threading
        self._stop_event = threading.Event()
        self._monitor_thread = None

        # Load radars
        self.radars = {r.site_code: r for r in get_all_radars()}
        logger.info(f"Loaded {len(self.radars)} radar sites")

    def add_region(
        self,
        region_id: str,
        name: str,
        lat: float,
        lon: float,
        radius_km: float = 100,
        alert_threshold_inches: float = 1.0,
        callback: Callable = None
    ) -> MonitoredRegion:
        """
        Add a region to monitor.

        Args:
            region_id: Unique identifier
            name: Display name
            lat: Center latitude
            lon: Center longitude
            radius_km: Monitoring radius
            alert_threshold_inches: Minimum hail size to alert
            callback: Function to call on alert

        Returns:
            MonitoredRegion object
        """
        # Find covering radars
        coverages = find_covering_radars(lat, lon, max_distance_km=radius_km + 50, max_radars=5)
        radar_sites = [c.radar.site_code for c in coverages]

        region = MonitoredRegion(
            region_id=region_id,
            name=name,
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            alert_threshold_inches=alert_threshold_inches,
            radar_sites=radar_sites,
            callback=callback
        )

        self.monitored_regions[region_id] = region
        logger.info(f"Added region '{name}' with {len(radar_sites)} covering radars")

        return region

    def remove_region(self, region_id: str):
        """Remove a monitored region."""
        if region_id in self.monitored_regions:
            del self.monitored_regions[region_id]
            logger.info(f"Removed region {region_id}")

    def start(self):
        """Start live monitoring."""
        if self.running:
            logger.warning("Monitor already running")
            return

        self.running = True
        self.stats['start_time'] = datetime.utcnow()
        self._stop_event.clear()

        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        logger.info("Live monitoring started")

    def stop(self):
        """Stop live monitoring."""
        if not self.running:
            return

        self._stop_event.set()
        self.running = False

        if self._monitor_thread:
            self._monitor_thread.join(timeout=30)

        logger.info("Live monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self._check_all_regions()
                self.stats['checks_performed'] += 1
                self.stats['last_check_time'] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")

            self._stop_event.wait(self.check_interval)

    def _check_all_regions(self):
        """Check all monitored regions for hail."""
        for region_id, region in self.monitored_regions.items():
            try:
                self._check_region(region)
            except Exception as e:
                logger.error(f"Error checking region {region_id}: {e}")

    def _check_region(self, region: MonitoredRegion):
        """Check a single region for hail activity."""
        logger.debug(f"Checking region: {region.name}")

        # Query recent detections near this region
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Look for recent events in the region
        lat_delta = region.radius_km / 111.0
        lon_delta = region.radius_km / 85.0

        cursor.execute("""
            SELECT id, event_date, latitude, longitude,
                   max_hail_size_inches, primary_radar, city
            FROM hail_events
            WHERE is_live = 1
              AND latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
              AND event_date >= date('now', '-1 day')
            ORDER BY event_date DESC
            LIMIT 10
        """, (
            region.lat - lat_delta, region.lat + lat_delta,
            region.lon - lon_delta, region.lon + lon_delta
        ))

        rows = cursor.fetchall()
        conn.close()

        # Check for alertable conditions
        for row in rows:
            if row['max_hail_size_inches'] >= region.alert_threshold_inches:
                self._generate_alert(region, row)

    def _generate_alert(self, region: MonitoredRegion, event: sqlite3.Row):
        """Generate an alert for a region."""
        # Check if we already alerted for this event
        event_key = f"{event['id']}_{region.region_id}"
        if any(a.alert_id == event_key for a in self.alert_history):
            return

        # Determine severity
        size = event['max_hail_size_inches']
        if size >= 2.5:
            severity = 'emergency'
        elif size >= 1.5:
            severity = 'warning'
        else:
            severity = 'watch'

        # Generate message
        location = event['city'] or f"({event['latitude']:.2f}, {event['longitude']:.2f})"
        message = f"{size}\" hail detected near {location}"

        alert = LiveAlert(
            alert_id=event_key,
            timestamp=datetime.utcnow(),
            radar_site=event['primary_radar'],
            lat=event['latitude'],
            lon=event['longitude'],
            mesh_inches=size,
            alert_type='new_detection',
            severity=severity,
            message=message,
            affected_area=region.name
        )

        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        self.stats['alerts_generated'] += 1

        logger.warning(f"ALERT [{severity.upper()}]: {message}")

        # Trigger callback
        if region.callback:
            try:
                region.callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        # Store alert in database
        self._store_alert(alert, region)

    def _store_alert(self, alert: LiveAlert, region: MonitoredRegion):
        """Store alert in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO alert_history (
                    alert_type, severity, title, message,
                    sent_at, delivery_method, delivery_status
                ) VALUES (?, ?, ?, ?, ?, 'system', 'delivered')
            """, (
                alert.alert_type,
                alert.severity,
                f"Hail Alert: {region.name}",
                alert.message,
                alert.timestamp.isoformat()
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error storing alert: {e}")

    def get_active_alerts(self, max_age_hours: int = 24) -> List[Dict]:
        """Get currently active alerts."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        return [
            {
                'alert_id': a.alert_id,
                'timestamp': a.timestamp.isoformat(),
                'radar_site': a.radar_site,
                'lat': a.lat,
                'lon': a.lon,
                'mesh_inches': a.mesh_inches,
                'alert_type': a.alert_type,
                'severity': a.severity,
                'message': a.message,
                'affected_area': a.affected_area
            }
            for a in self.active_alerts
            if a.timestamp > cutoff
        ]

    def get_status(self) -> Dict:
        """Get monitor status."""
        return {
            'running': self.running,
            'monitored_regions': len(self.monitored_regions),
            'active_alerts': len([a for a in self.active_alerts
                                if a.timestamp > datetime.utcnow() - timedelta(hours=24)]),
            'stats': {
                **self.stats,
                'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
                'last_check_time': self.stats['last_check_time'].isoformat() if self.stats['last_check_time'] else None,
                'uptime_hours': (datetime.utcnow() - self.stats['start_time']).total_seconds() / 3600
                               if self.stats['start_time'] else 0
            },
            'regions': [
                {
                    'id': r.region_id,
                    'name': r.name,
                    'lat': r.lat,
                    'lon': r.lon,
                    'radius_km': r.radius_km,
                    'threshold': r.alert_threshold_inches,
                    'radar_count': len(r.radar_sites)
                }
                for r in self.monitored_regions.values()
            ]
        }


# Predefined monitoring configurations
def create_tornado_alley_monitor() -> LiveMonitor:
    """Create a monitor configured for Tornado Alley."""
    monitor = LiveMonitor(check_interval_seconds=300)

    # Add major cities
    cities = [
        ('okc', 'Oklahoma City', 35.47, -97.52),
        ('dallas', 'Dallas', 32.78, -96.80),
        ('denver', 'Denver', 39.74, -105.0),
        ('wichita', 'Wichita', 37.69, -97.34),
        ('omaha', 'Omaha', 41.26, -95.94),
    ]

    for city_id, name, lat, lon in cities:
        monitor.add_region(
            city_id, name, lat, lon,
            radius_km=75,
            alert_threshold_inches=1.0
        )

    return monitor


def create_national_monitor() -> LiveMonitor:
    """Create a monitor for all major PDR markets."""
    monitor = LiveMonitor(check_interval_seconds=600)

    # US Tornado Alley
    monitor.add_region('tornado_alley', 'Tornado Alley', 35.5, -98.0, 300, 1.0)

    # Texas Triangle
    monitor.add_region('texas', 'Texas Triangle', 31.5, -97.5, 400, 1.0)

    # Midwest
    monitor.add_region('midwest', 'Midwest', 41.0, -90.0, 300, 1.0)

    # Canadian Prairies
    monitor.add_region('prairies', 'Canadian Prairies', 52.0, -110.0, 300, 1.0)

    # Mexico Central
    monitor.add_region('mexico', 'Central Mexico', 21.0, -102.0, 300, 1.0)

    return monitor


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("LIVE MONITOR TEST")
    print("=" * 60)

    # Create monitor
    monitor = create_tornado_alley_monitor()

    print("\nMonitor Status:")
    status = monitor.get_status()
    print(f"  Running: {status['running']}")
    print(f"  Monitored Regions: {status['monitored_regions']}")
    print("\nConfigured Regions:")
    for region in status['regions']:
        print(f"  - {region['name']}: ({region['lat']:.2f}, {region['lon']:.2f}), "
              f"r={region['radius_km']}km, {region['radar_count']} radars")

    # Start monitoring (would run in background)
    print("\nStarting monitor for 10 seconds...")
    monitor.start()

    time.sleep(10)

    monitor.stop()

    print("\nFinal Status:")
    status = monitor.get_status()
    print(f"  Checks performed: {status['stats']['checks_performed']}")
    print(f"  Alerts generated: {status['stats']['alerts_generated']}")

    print("\nLive monitor ready!")
