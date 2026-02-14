"""
Storm Monitor - Real-Time NEXRAD Monitoring System

Continuously monitors radar data and generates alerts for hail events.
"""

import os
import sys
import math
import time
from collections import deque
import tempfile
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
import numpy as np

# Check dependencies
try:
    import nexradaws
    NEXRAD_AVAILABLE = True
except ImportError:
    NEXRAD_AVAILABLE = False

try:
    import pyart
    PYART_AVAILABLE = True
except ImportError:
    PYART_AVAILABLE = False

from .alert_manager import AlertManager, Alert, AlertLevel
from .notifiers import ConsoleNotifier, SoundNotifier, FileNotifier
from .geo_filter import GeoFilter, get_suggested_radars, list_named_regions


@dataclass
class MonitorConfig:
    """Configuration for storm monitoring."""

    # Radars to monitor (if empty, will auto-select based on coverage area)
    radar_ids: List[str] = field(default_factory=lambda: [
        'KFWS', 'KDFW',  # Dallas-Fort Worth
        'KTLX', 'KVNX',  # Oklahoma
        'KICT', 'KDDC',  # Kansas
        'KOAX', 'KUEX',  # Nebraska
        'KAMA', 'KLBB',  # Texas Panhandle
    ])

    # Monitoring parameters
    scan_interval_seconds: int = 300  # 5 minutes
    lookback_minutes: int = 15        # How far back to search for scans

    # Alert thresholds
    min_reflectivity_dbz: float = 50.0
    min_mesh_mm: float = 15.0
    min_pdr_score: float = 40.0

    # Geographic coverage area (multiple options)
    # Option 1: Simple bounding box (legacy support)
    lat_min: Optional[float] = None
    lat_max: Optional[float] = None
    lon_min: Optional[float] = None
    lon_max: Optional[float] = None

    # Option 2: Named region (e.g., "texas", "dallas_fort_worth", "hail_alley_core")
    coverage_region: Optional[str] = None

    # Option 3: Radius from center point
    coverage_center_lat: Optional[float] = None
    coverage_center_lon: Optional[float] = None
    coverage_radius_miles: Optional[float] = None

    # Option 4: Multiple regions (comma-separated or list)
    coverage_regions: List[str] = field(default_factory=list)

    # Auto-select radars based on coverage area
    auto_select_radars: bool = False

    # Notification settings
    enable_sound: bool = True
    enable_console: bool = True
    enable_file_log: bool = True

    # Webhook (optional)
    webhook_url: Optional[str] = None
    webhook_platform: str = 'slack'

    # SMS/Twilio settings (optional)
    sms_enabled: bool = False
    sms_use_env: bool = False  # Use environment variables
    sms_account_sid: Optional[str] = None
    sms_auth_token: Optional[str] = None
    sms_from_number: Optional[str] = None
    sms_to_numbers: List[str] = field(default_factory=list)
    sms_min_level: str = 'WARNING'  # Minimum level to send SMS

    # Push notification settings (optional)
    ntfy_topic: Optional[str] = None
    ntfy_server: str = 'https://ntfy.sh'
    pushover_user: Optional[str] = None
    pushover_token: Optional[str] = None
    push_min_level: str = 'WARNING'

    # Email settings (optional)
    email_enabled: bool = False
    email_use_env: bool = False  # Use environment variables
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: List[str] = field(default_factory=list)
    email_min_level: str = 'WARNING'

    # Dual-pol hail gating thresholds
    max_rhohv_for_hail: float = 0.97   # RHOHV below this suggests hail (decorrelation)
    max_abs_zdr_for_hail: float = 1.2  # |ZDR| above this suggests hail (tumbling)

    # Database settings
    database_enabled: bool = True  # Enable by default
    database_url: str = 'sqlite:///data/alerts/alerts.db'


class StormMonitor:
    """
    Real-time storm monitoring system.

    Continuously monitors NEXRAD radar data and generates alerts
    when hail is detected.

    Example:
        >>> config = MonitorConfig(
        ...     radar_ids=['KFWS', 'KTLX'],
        ...     min_pdr_score=50.0
        ... )
        >>> monitor = StormMonitor(config)
        >>> monitor.start()  # Runs continuously
    """

    def __init__(self, config: Optional[MonitorConfig] = None):
        """
        Initialize storm monitor.

        Args:
            config: Monitoring configuration
        """
        self.config = config or MonitorConfig()
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Check dependencies
        if not NEXRAD_AVAILABLE or not PYART_AVAILABLE:
            print("WARNING: nexradaws or pyart not available")
            print("Install with: pip install nexradaws arm-pyart")

        # Initialize components
        self.conn = nexradaws.NexradAwsInterface() if NEXRAD_AVAILABLE else None
        self.temp_dir = tempfile.mkdtemp()

        # Set up geographic filter
        self.geo_filter = self._setup_geo_filter()

        # Auto-select radars if requested
        if self.config.auto_select_radars and self.geo_filter:
            suggested = get_suggested_radars(self.geo_filter)
            if suggested:
                self.config.radar_ids = suggested
                print(f"Auto-selected radars for coverage area: {', '.join(suggested)}")

        # Alert manager
        self.alert_manager = AlertManager(
            min_pdr_score=self.config.min_pdr_score
        )

        # Set up notifiers
        self._setup_notifiers()

        # Tracking
        self.last_scan_times: Dict[str, datetime] = {}
        self.processed_scans: set = set()
        self.stats = {
            'scans_processed': 0,
            'alerts_generated': 0,
            'alerts_filtered': 0,  # Track alerts filtered by geo
            'start_time': None,
            'last_scan_time': None
        }

        # Import classifier
        try:
            from src.ml.hail_classifier import HailClassifier
            self.classifier = HailClassifier(simulation_mode=True)
        except ImportError:
            print("WARNING: HailClassifier not available")
            self.classifier = None

    def _setup_geo_filter(self) -> Optional[GeoFilter]:
        """Configure geographic filter from config options."""
        filters = []

        # Option 1: Simple bounding box
        if any([self.config.lat_min, self.config.lat_max,
                self.config.lon_min, self.config.lon_max]):
            try:
                filters.append(GeoFilter.from_bounds(
                    lat_min=self.config.lat_min or -90,
                    lat_max=self.config.lat_max or 90,
                    lon_min=self.config.lon_min or -180,
                    lon_max=self.config.lon_max or 180,
                    name="Custom Bounds"
                ))
            except Exception as e:
                print(f"Warning: Invalid bounding box: {e}")

        # Option 2: Single named region
        if self.config.coverage_region:
            try:
                filters.append(GeoFilter.from_named_region(self.config.coverage_region))
            except ValueError as e:
                print(f"Warning: {e}")

        # Option 3: Radius from center point
        if (self.config.coverage_center_lat is not None and
            self.config.coverage_center_lon is not None and
            self.config.coverage_radius_miles is not None):
            filters.append(GeoFilter.from_radius(
                self.config.coverage_center_lat,
                self.config.coverage_center_lon,
                self.config.coverage_radius_miles
            ))

        # Option 4: Multiple regions
        if self.config.coverage_regions:
            for region in self.config.coverage_regions:
                try:
                    filters.append(GeoFilter.from_named_region(region.strip()))
                except ValueError as e:
                    print(f"Warning: {e}")

        # Combine filters
        if not filters:
            return None
        elif len(filters) == 1:
            return filters[0]
        else:
            return GeoFilter.composite(filters, operator='OR', name="Combined Coverage")

    def _setup_notifiers(self):
        """Configure notification channels."""
        if self.config.enable_console:
            self.alert_manager.add_notifier(ConsoleNotifier(use_colors=True))

        if self.config.enable_sound:
            self.alert_manager.add_notifier(SoundNotifier())

        if self.config.enable_file_log:
            self.alert_manager.add_notifier(FileNotifier())

        if self.config.webhook_url:
            from .notifiers import WebhookNotifier
            self.alert_manager.add_notifier(
                WebhookNotifier(
                    self.config.webhook_url,
                    self.config.webhook_platform
                )
            )

        # SMS/Twilio notifier
        if self.config.sms_enabled:
            self._setup_sms_notifier()

        # Push notifications
        self._setup_push_notifiers()

        # Email notifications
        if self.config.email_enabled:
            self._setup_email_notifier()

        # Database storage
        if self.config.database_enabled:
            self._setup_database()

    def _setup_sms_notifier(self):
        """Configure SMS notifications via Twilio."""
        # Map level string to AlertLevel
        level_map = {
            'INFO': AlertLevel.INFO,
            'WATCH': AlertLevel.WATCH,
            'WARNING': AlertLevel.WARNING,
            'CRITICAL': AlertLevel.CRITICAL
        }
        min_level = level_map.get(self.config.sms_min_level, AlertLevel.WARNING)

        if self.config.sms_use_env:
            # Use environment variables
            from .notifiers import TwilioNotifierFromEnv
            self.alert_manager.add_notifier(
                TwilioNotifierFromEnv(min_level=min_level)
            )
        elif self.config.sms_account_sid and self.config.sms_to_numbers:
            # Use explicit credentials
            from .notifiers import TwilioNotifier
            self.alert_manager.add_notifier(
                TwilioNotifier(
                    account_sid=self.config.sms_account_sid,
                    auth_token=self.config.sms_auth_token,
                    from_number=self.config.sms_from_number,
                    to_numbers=self.config.sms_to_numbers,
                    min_level=min_level
                )
            )

    def _setup_push_notifiers(self):
        """Configure push notifications."""
        # Map level string to AlertLevel
        level_map = {
            'INFO': AlertLevel.INFO,
            'WATCH': AlertLevel.WATCH,
            'WARNING': AlertLevel.WARNING,
            'CRITICAL': AlertLevel.CRITICAL
        }
        min_level = level_map.get(self.config.push_min_level, AlertLevel.WARNING)

        # ntfy notifications
        if self.config.ntfy_topic:
            from .notifiers import NtfyNotifier
            self.alert_manager.add_notifier(
                NtfyNotifier(
                    topic=self.config.ntfy_topic,
                    server=self.config.ntfy_server,
                    min_level=min_level
                )
            )

        # Pushover notifications
        if self.config.pushover_user and self.config.pushover_token:
            from .notifiers import PushoverNotifier
            self.alert_manager.add_notifier(
                PushoverNotifier(
                    user_key=self.config.pushover_user,
                    api_token=self.config.pushover_token,
                    min_level=min_level
                )
            )

    def _setup_email_notifier(self):
        """Configure email notifications."""
        # Map level string to AlertLevel
        level_map = {
            'INFO': AlertLevel.INFO,
            'WATCH': AlertLevel.WATCH,
            'WARNING': AlertLevel.WARNING,
            'CRITICAL': AlertLevel.CRITICAL
        }
        min_level = level_map.get(self.config.email_min_level, AlertLevel.WARNING)

        if self.config.email_use_env:
            # Use environment variables
            from .notifiers import EmailNotifierFromEnv
            self.alert_manager.add_notifier(
                EmailNotifierFromEnv(min_level=min_level)
            )
        elif self.config.email_smtp_server and self.config.email_to:
            # Use explicit configuration
            from .notifiers import EmailNotifier
            self.alert_manager.add_notifier(
                EmailNotifier(
                    smtp_server=self.config.email_smtp_server,
                    smtp_port=self.config.email_smtp_port,
                    username=self.config.email_username,
                    password=self.config.email_password,
                    from_address=self.config.email_from or self.config.email_username,
                    to_addresses=self.config.email_to,
                    min_level=min_level
                )
            )

    def _setup_database(self):
        """Configure database storage."""
        try:
            from .database import AlertDatabase, DatabaseNotifier
            self.database = AlertDatabase(self.config.database_url)
            self.alert_manager.add_notifier(DatabaseNotifier(self.database))
            print(f"Database storage enabled: {self.config.database_url}")
        except Exception as e:
            print(f"Database setup error: {e}")
            self.database = None

    def start(self, background: bool = False):
        """
        Start monitoring.

        Args:
            background: Run in background thread
        """
        if not NEXRAD_AVAILABLE:
            print("Cannot start: nexradaws not available")
            return

        self.running = True
        self.stats['start_time'] = datetime.now()

        print("\n" + "=" * 70)
        print("HAILTRACKER PRO - REAL-TIME STORM MONITOR")
        print("=" * 70)
        print(f"\nMonitoring {len(self.config.radar_ids)} radars:")
        print(f"  {', '.join(self.config.radar_ids)}")
        print(f"\nScan interval: {self.config.scan_interval_seconds} seconds")
        print(f"Alert threshold: PDR score >= {self.config.min_pdr_score}")

        # Show coverage area info
        if self.geo_filter:
            print(f"\nCoverage Area: {self.geo_filter.describe()}")
            bounds = self.geo_filter.get_bounds()
            if bounds:
                print(f"  Bounds: {bounds['lat_min']:.2f} to {bounds['lat_max']:.2f}N, "
                      f"{bounds['lon_min']:.2f} to {bounds['lon_max']:.2f}W")
        else:
            print("\nCoverage Area: No filter (all alerts)")

        print("\nPress Ctrl+C to stop\n")
        print("=" * 70 + "\n")

        if background:
            self.monitor_thread = threading.Thread(target=self._monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
        else:
            self._monitor_loop()

    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        print("\nMonitoring stopped.")
        self._print_stats()

    def _monitor_loop(self):
        """Main monitoring loop."""
        try:
            while self.running:
                cycle_start = datetime.now()

                print(f"[{cycle_start.strftime('%H:%M:%S')}] Scanning radars...")

                for radar_id in self.config.radar_ids:
                    try:
                        self._check_radar(radar_id)
                    except Exception as e:
                        print(f"  {radar_id}: Error - {e}")

                self.stats['last_scan_time'] = datetime.now()

                # Wait for next cycle
                elapsed = (datetime.now() - cycle_start).total_seconds()
                sleep_time = max(0, self.config.scan_interval_seconds - elapsed)

                if sleep_time > 0:
                    print(f"\nNext scan in {sleep_time:.0f} seconds...")
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            self.running = False
        finally:
            self._print_stats()

    def _check_radar(self, radar_id: str):
        """Check a single radar for new data."""
        try:
            # Find recent scans
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=self.config.lookback_minutes)

            scans = self.conn.get_avail_scans_in_range(start_time, end_time, radar_id)

            if not scans:
                return

            # Get most recent scan
            def get_scan_time(s):
                st = s.scan_time
                if st.tzinfo is not None:
                    st = st.replace(tzinfo=None)
                return st

            latest = max(scans, key=get_scan_time)
            scan_key = f"{radar_id}_{latest.filename}"

            # Skip if already processed
            if scan_key in self.processed_scans:
                return

            print(f"  {radar_id}: New scan {latest.filename}")

            # Download and analyze
            results = self.conn.download(latest, self.temp_dir)

            if not results.success:
                return

            filepath = results.success[0].filepath
            radar = pyart.io.read_nexrad_archive(filepath)

            # Analyze for hail
            analysis = self._analyze_radar(radar, radar_id)

            self.stats['scans_processed'] += 1
            self.processed_scans.add(scan_key)

            # Cap processed_scans to prevent unbounded memory growth
            if len(self.processed_scans) > 500:
                # Keep only the most recent entries (convert to sorted list, trim, back to set)
                sorted_keys = sorted(self.processed_scans)
                self.processed_scans = set(sorted_keys[-500:])

            # Generate alert if threshold met
            if analysis and analysis.get('should_alert'):
                self._generate_alert(radar_id, analysis)

            # Cleanup downloaded file
            try:
                os.remove(filepath)
            except:
                pass

        except Exception as e:
            print(f"  {radar_id}: Error - {e}")

    def _extract_storm_objects(
        self,
        radar,
        radar_id: str,
        top_n: int = 10,
        min_pixels: int = 40,
        dbz_threshold: float = None,
    ) -> List[Dict]:
        """
        Segment lowest-sweep reflectivity into storm objects via connected components.

        Optionally gates on dual-pol fields (ZDR, RHOHV) when available to
        sharpen hail signatures and computes a per-object hail_score (0-1).

        Returns list of detection dicts for StormCellTracker.process_radar_scan():
        [{lat, lon, reflectivity, mesh_mm, area_km2, radar_id, obj_pixels,
          hail_score, min_rhohv, mean_zdr}, ...]
        """
        radar_lat = float(radar.latitude['data'][0])
        radar_lon = float(radar.longitude['data'][0])

        threshold = float(dbz_threshold if dbz_threshold is not None else self.config.min_reflectivity_dbz)

        # --- Reflectivity field ---
        field_name = None
        for fn in ['reflectivity', 'REF', 'DBZ']:
            if fn in radar.fields:
                field_name = fn
                break
        if not field_name:
            return []

        sweep_idx = 0
        data = radar.get_field(sweep_idx, field_name)
        if data.count() == 0:
            return []

        sweep_slice = radar.get_slice(sweep_idx)
        azimuths = radar.azimuth['data'][sweep_slice]
        ranges_km = radar.range['data'] / 1000.0

        arr = np.ma.filled(data, fill_value=-9999.0).astype(float)
        mask = arr >= threshold

        # --- Dual-pol field extraction (optional) ---
        zdr_arr = None
        rhohv_arr = None

        for zdr_field in ['differential_reflectivity', 'ZDR']:
            if zdr_field in radar.fields:
                try:
                    zdr_data = radar.get_field(sweep_idx, zdr_field)
                    zdr_arr = np.ma.filled(zdr_data, fill_value=np.nan).astype(float)
                except Exception:
                    pass
                break

        for cc_field in ['cross_correlation_ratio', 'RHOHV']:
            if cc_field in radar.fields:
                try:
                    rhohv_data = radar.get_field(sweep_idx, cc_field)
                    rhohv_arr = np.ma.filled(rhohv_data, fill_value=np.nan).astype(float)
                except Exception:
                    pass
                break

        # --- Apply dual-pol mask gating ---
        if rhohv_arr is not None:
            valid_rhohv = ~np.isnan(rhohv_arr)
            mask = mask & (~valid_rhohv | (rhohv_arr <= self.config.max_rhohv_for_hail))

        if zdr_arr is not None:
            valid_zdr = ~np.isnan(zdr_arr)
            mask = mask & (~valid_zdr | (np.abs(zdr_arr) >= self.config.max_abs_zdr_for_hail))

        if not mask.any():
            return []

        # --- Connected-component BFS ---
        H, W = mask.shape
        visited = np.zeros((H, W), dtype=np.uint8)
        q = deque()
        comps = []

        for r in range(H):
            for c in range(W):
                if not mask[r, c] or visited[r, c]:
                    continue
                visited[r, c] = 1
                q.clear()
                q.append((r, c))
                pts = []
                while q:
                    rr, cc = q.popleft()
                    pts.append((rr, cc))
                    if rr > 0 and mask[rr - 1, cc] and not visited[rr - 1, cc]:
                        visited[rr - 1, cc] = 1; q.append((rr - 1, cc))
                    if rr < H - 1 and mask[rr + 1, cc] and not visited[rr + 1, cc]:
                        visited[rr + 1, cc] = 1; q.append((rr + 1, cc))
                    if cc > 0 and mask[rr, cc - 1] and not visited[rr, cc - 1]:
                        visited[rr, cc - 1] = 1; q.append((rr, cc - 1))
                    if cc < W - 1 and mask[rr, cc + 1] and not visited[rr, cc + 1]:
                        visited[rr, cc + 1] = 1; q.append((rr, cc + 1))
                if len(pts) >= min_pixels:
                    comps.append(pts)

        if not comps:
            return []

        # --- Per-object summary with dual-pol stats and hail scoring ---
        summaries = []
        for pts in comps:
            max_ref = -9999.0
            sr = 0.0
            sc = 0.0
            rhohv_vals = []
            zdr_vals = []

            for rr, cc in pts:
                sr += rr
                sc += cc
                v = float(arr[rr, cc])
                if v > max_ref:
                    max_ref = v
                if rhohv_arr is not None and not np.isnan(rhohv_arr[rr, cc]):
                    rhohv_vals.append(float(rhohv_arr[rr, cc]))
                if zdr_arr is not None and not np.isnan(zdr_arr[rr, cc]):
                    zdr_vals.append(float(zdr_arr[rr, cc]))

            cr = sr / len(pts)
            cc_avg = sc / len(pts)

            az = float(azimuths[int(round(cr))])
            rng = float(ranges_km[int(round(cc_avg))])
            lat, lon = self._az_range_to_latlon(radar_lat, radar_lon, az, rng)

            # Rough gate area estimate
            try:
                gate_km = float(radar.range['meters_between_gates']) / 1000.0
            except Exception:
                gate_km = 0.25
            dtheta = math.radians(1.0)
            gate_area_km2 = max(0.01, (max(rng, 1.0) * dtheta) * gate_km)
            area_km2 = gate_area_km2 * len(pts)

            # Approximate MESH from peak reflectivity
            ref = max_ref
            mesh_mm = max(0, 2.54 * np.exp(0.1 * (ref - 40))) if ref >= 40 else 0
            mesh_mm = min(mesh_mm, 120)

            # Dual-pol per-object stats
            min_rhohv = float(min(rhohv_vals)) if rhohv_vals else float('nan')
            mean_zdr = float(np.mean(zdr_vals)) if zdr_vals else float('nan')

            # --- Hail score (0-1) combining reflectivity + MESH + RHOHV + ZDR ---
            score = 0.0

            # Reflectivity contribution (0-0.30): ramps 50->65 dBZ
            ref_contrib = np.clip((max_ref - 50.0) / 15.0, 0.0, 1.0) * 0.30
            score += ref_contrib

            # MESH contribution (0-0.30): ramps 15->50 mm
            mesh_contrib = np.clip((mesh_mm - 15.0) / 35.0, 0.0, 1.0) * 0.30
            score += mesh_contrib

            # RHOHV contribution (0-0.20): low RHOHV = hail tumbling
            if rhohv_vals:
                rhohv_contrib = np.clip((0.97 - min_rhohv) / 0.12, 0.0, 1.0) * 0.20
                score += rhohv_contrib

            # ZDR contribution (0-0.20): near-zero ZDR = tumbling hail
            if zdr_vals:
                abs_zdr = abs(mean_zdr)
                zdr_contrib = np.clip((1.5 - abs_zdr) / 1.5, 0.0, 1.0) * 0.20
                score += zdr_contrib

            hail_score = float(np.clip(score, 0.0, 1.0))

            summaries.append({
                'lat': lat,
                'lon': lon,
                'reflectivity': float(max_ref),
                'mesh_mm': float(mesh_mm),
                'area_km2': float(area_km2),
                'radar_id': radar_id,
                'obj_pixels': len(pts),
                'hail_score': hail_score,
                'min_rhohv': min_rhohv,
                'mean_zdr': mean_zdr,
            })

        summaries.sort(key=lambda d: d['hail_score'], reverse=True)
        return summaries[:top_n]

    def _extract_top_peaks(self, radar, radar_id: str, top_n: int = 10,
                           min_separation_km: float = 10.0) -> List[Dict]:
        """
        Extract top-N reflectivity peaks from radar scan with minimum separation.

        Returns list of detection dicts suitable for StormCellTracker.process_radar_scan().
        """
        radar_lat = float(radar.latitude['data'][0])
        radar_lon = float(radar.longitude['data'][0])

        # Collect all high-reflectivity points across lowest sweeps
        candidates = []
        for sweep_idx in range(min(radar.nsweeps, 3)):
            for field_name in ['reflectivity', 'REF', 'DBZ']:
                if field_name not in radar.fields:
                    continue
                data = radar.get_field(sweep_idx, field_name)
                if data.count() == 0:
                    continue

                sweep_slice = radar.get_slice(sweep_idx)
                azimuths = radar.azimuth['data'][sweep_slice]
                ranges_km = radar.range['data'] / 1000.0

                # Flatten and find indices above threshold
                flat = np.ma.filled(data, fill_value=0)
                threshold = self.config.min_reflectivity_dbz
                above = np.argwhere(flat >= threshold)

                for az_idx, rng_idx in above:
                    ref_val = float(flat[az_idx, rng_idx])
                    az = float(azimuths[az_idx])
                    rng = float(ranges_km[rng_idx])
                    lat, lon = self._az_range_to_latlon(radar_lat, radar_lon, az, rng)
                    candidates.append({
                        'lat': lat, 'lon': lon,
                        'reflectivity': ref_val,
                        'range_km': rng,
                    })
                break  # use first matching field name

        if not candidates:
            return []

        # Sort by reflectivity descending and pick top-N with minimum separation
        candidates.sort(key=lambda c: c['reflectivity'], reverse=True)
        selected = []

        for c in candidates:
            if len(selected) >= top_n:
                break
            # Check minimum separation from already-selected peaks
            too_close = False
            for s in selected:
                dlat = c['lat'] - s['lat']
                dlon = c['lon'] - s['lon']
                # Quick distance approximation in km
                approx_km = ((dlat * 111) ** 2 + (dlon * 111 * math.cos(math.radians(c['lat']))) ** 2) ** 0.5
                if approx_km < min_separation_km:
                    too_close = True
                    break
            if not too_close:
                # Approximate MESH from reflectivity
                ref = c['reflectivity']
                mesh_mm = max(0, 2.54 * np.exp(0.1 * (ref - 40))) if ref >= 40 else 0
                mesh_mm = min(mesh_mm, 120)
                selected.append({
                    'lat': c['lat'],
                    'lon': c['lon'],
                    'reflectivity': c['reflectivity'],
                    'mesh_mm': mesh_mm,
                    'area_km2': 50,  # rough default
                    'radar_id': radar_id,
                })

        return selected

    def _feed_tracker(self, detections: List[Dict], scan_time: datetime):
        """Feed detections into the global StormCellTracker instance."""
        try:
            from src.web.routes.storm_tracking_api import get_tracker
            tracker = get_tracker()
            cells = tracker.process_radar_scan(detections, scan_time)
            if cells:
                print(f"    Tracker: {len(cells)} cells from {len(detections)} detections")
        except Exception as e:
            print(f"    Tracker feed error: {e}")

    def _analyze_radar(self, radar, radar_id: str) -> Optional[Dict]:
        """Analyze radar data for hail signatures."""
        try:
            # Get radar location
            radar_lat = float(radar.latitude['data'][0])
            radar_lon = float(radar.longitude['data'][0])

            # --- Multi-detection extraction: storm objects first, fallback to peaks ---
            peaks = self._extract_storm_objects(radar, radar_id, top_n=10, min_pixels=40)
            if not peaks:
                peaks = self._extract_top_peaks(radar, radar_id, top_n=10, min_separation_km=10.0)
            if peaks:
                scan_time = datetime.utcnow()
                self._feed_tracker(peaks, scan_time)

            # --- Original single-max analysis for alerting ---
            # Find max reflectivity
            max_ref = 0
            storm_lat, storm_lon = radar_lat, radar_lon

            for sweep_idx in [0, 1, 2]:
                for field_name in ['reflectivity', 'REF', 'DBZ']:
                    if field_name in radar.fields:
                        data = radar.get_field(sweep_idx, field_name)
                        if data.count() > 0:
                            current_max = float(np.max(data))
                            if current_max > max_ref:
                                max_ref = current_max

                                # Find storm location
                                max_idx = np.unravel_index(np.argmax(data), data.shape)
                                az_idx, rng_idx = max_idx

                                sweep_slice = radar.get_slice(sweep_idx)
                                azimuths = radar.azimuth['data'][sweep_slice]
                                ranges = radar.range['data'] / 1000.0

                                az = azimuths[az_idx]
                                rng = ranges[rng_idx]

                                storm_lat, storm_lon = self._az_range_to_latlon(
                                    radar_lat, radar_lon, az, rng
                                )
                        break

            # Check minimum reflectivity
            if max_ref < self.config.min_reflectivity_dbz:
                return None

            # Extract dual-pol (simplified)
            zdr_min = 0.5
            cc_min = 0.95

            for sweep_idx in [0, 1]:
                for zdr_field in ['differential_reflectivity', 'ZDR']:
                    if zdr_field in radar.fields:
                        data = radar.get_field(sweep_idx, zdr_field)
                        if data.count() > 0:
                            zdr_min = float(np.min(data))
                        break

                for cc_field in ['cross_correlation_ratio', 'RHOHV']:
                    if cc_field in radar.fields:
                        data = radar.get_field(sweep_idx, cc_field)
                        if data.count() > 0:
                            cc_min = float(np.min(data))
                        break

            # Calculate MESH
            mesh_mm = self._calculate_mesh(radar)

            # Check MESH threshold
            if mesh_mm < self.config.min_mesh_mm:
                return None

            # Run ML classification
            if self.classifier:
                event = self.classifier.classify(
                    lat=storm_lat,
                    lon=storm_lon,
                    timestamp=datetime.now(),
                    radar_data={
                        'max_reflectivity': max_ref,
                        'mesh': mesh_mm,
                        'posh': min(99, 50 + mesh_mm) if mesh_mm >= 25 else 30 + mesh_mm,
                        'zdr_min': zdr_min,
                        'cc_min': cc_min
                    }
                )

                classification = {
                    'hail_detected': event.hail_detected,
                    'probability': event.hail_probability,
                    'size_mm': event.estimated_size_mm,
                    'severity': event.severity,
                    'pdr_score': event.pdr_opportunity_score
                }
            else:
                # Fallback classification
                classification = {
                    'hail_detected': mesh_mm >= 25,
                    'probability': min(99, mesh_mm * 2),
                    'size_mm': mesh_mm * 0.9,
                    'severity': 'moderate' if mesh_mm >= 25 else 'light',
                    'pdr_score': min(100, mesh_mm * 2)
                }

            return {
                'radar_id': radar_id,
                'storm_lat': storm_lat,
                'storm_lon': storm_lon,
                'max_reflectivity': max_ref,
                'mesh_mm': mesh_mm,
                'zdr_min': zdr_min,
                'cc_min': cc_min,
                'classification': classification,
                'should_alert': classification['pdr_score'] >= self.config.min_pdr_score,
                'detections_fed': len(peaks),
            }

        except Exception as e:
            print(f"    Analysis error: {e}")
            return None

    def _calculate_mesh(self, radar) -> float:
        """Calculate MESH from vertical profile."""
        try:
            max_refs = []
            heights = []

            for sweep_idx in range(min(radar.nsweeps, 14)):
                for field_name in ['reflectivity', 'REF', 'DBZ']:
                    if field_name in radar.fields:
                        data = radar.get_field(sweep_idx, field_name)
                        if data.count() > 0:
                            max_ref = float(np.max(data))
                            sweep_slice = radar.get_slice(sweep_idx)
                            elev = np.mean(radar.elevation['data'][sweep_slice])
                            height = 50 * np.tan(np.radians(elev)) + (50**2) / (2 * 8500)
                            max_refs.append(max_ref)
                            heights.append(height)
                        break

            if not max_refs:
                return 0

            freezing_level = 3.5
            above_freezing = [(h, r) for h, r in zip(heights, max_refs) if h > freezing_level]

            if above_freezing:
                max_above = max(r for h, r in above_freezing)
                if max_above >= 40:
                    mesh_mm = 2.54 * np.exp(0.1 * (max_above - 40))
                    return min(mesh_mm, 120)

            return 0

        except:
            return 0

    def _az_range_to_latlon(self, radar_lat, radar_lon, azimuth, range_km):
        """Convert radar azimuth/range to lat/lon."""
        import math
        R = 6371.0
        bearing = math.radians(azimuth)
        lat1 = math.radians(radar_lat)
        lon1 = math.radians(radar_lon)

        lat2 = math.asin(
            math.sin(lat1) * math.cos(range_km / R) +
            math.cos(lat1) * math.sin(range_km / R) * math.cos(bearing)
        )
        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(range_km / R) * math.cos(lat1),
            math.cos(range_km / R) - math.sin(lat1) * math.sin(lat2)
        )

        return math.degrees(lat2), math.degrees(lon2)

    def _generate_alert(self, radar_id: str, analysis: Dict):
        """Generate and dispatch an alert."""
        storm_lat = analysis['storm_lat']
        storm_lon = analysis['storm_lon']

        # Apply geographic filter
        if self.geo_filter and not self.geo_filter.contains(storm_lat, storm_lon):
            self.stats['alerts_filtered'] += 1
            print(f"    Filtered: Storm at ({storm_lat:.2f}, {storm_lon:.2f}) outside coverage area")
            return

        classification = analysis['classification']

        event_data = {
            'name': f"Storm near {radar_id}",
            'location': (storm_lat, storm_lon),
            'radar_id': radar_id,
            'timestamp': datetime.now()
        }

        radar_data = {
            'max_reflectivity': analysis['max_reflectivity'],
            'mesh_mm': analysis['mesh_mm'],
            'posh': min(99, 50 + analysis['mesh_mm']) if analysis['mesh_mm'] >= 25 else 30 + analysis['mesh_mm']
        }

        alert = self.alert_manager.create_alert(event_data, classification, radar_data)

        if alert:
            self.alert_manager.dispatch_alert(alert)
            self.stats['alerts_generated'] += 1

    def _print_stats(self):
        """Print monitoring statistics."""
        print("\n" + "=" * 70)
        print("MONITORING STATISTICS")
        print("=" * 70)

        if self.stats['start_time']:
            duration = datetime.now() - self.stats['start_time']
            print(f"Duration: {duration}")

        print(f"Scans processed: {self.stats['scans_processed']}")
        print(f"Alerts generated: {self.stats['alerts_generated']}")
        if self.stats.get('alerts_filtered', 0) > 0:
            print(f"Alerts filtered (outside coverage): {self.stats['alerts_filtered']}")

        alert_stats = self.alert_manager.get_alert_stats()
        if alert_stats['total'] > 0:
            print(f"\nAlert breakdown:")
            print(f"  Critical: {alert_stats.get('critical', 0)}")
            print(f"  Warning: {alert_stats.get('warning', 0)}")
            print(f"  Watch: {alert_stats.get('watch', 0)}")
            print(f"  Info: {alert_stats.get('info', 0)}")

        print("=" * 70)

    def get_status(self) -> Dict:
        """Get current monitor status."""
        return {
            'running': self.running,
            'radars': self.config.radar_ids,
            'scans_processed': self.stats['scans_processed'],
            'alerts_generated': self.stats['alerts_generated'],
            'last_scan': self.stats['last_scan_time'].isoformat() if self.stats['last_scan_time'] else None,
            'active_alerts': len(self.alert_manager.get_active_alerts())
        }
