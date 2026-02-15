"""
Storm Monitor - Real-Time NEXRAD Monitoring System

Continuously monitors radar data and generates alerts for hail events.
"""

import os
import sys
import math
import time
import json
from collections import deque
import tempfile
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    # Dev diagnostics
    debug_object_extraction: bool = False

    # Database settings
    database_enabled: bool = True  # Enable by default
    database_url: str = 'sqlite:///data/alerts/alerts.db'

    # --- Scheduler knobs (Discovery -> Focus) ---
    enable_discovery_focus: bool = True
    max_workers: int = 12
    max_discovery_radars_per_tick: int = 40
    discovery_interval_seconds: int = 900       # 15 min
    focus_interval_seconds: int = 180           # 3 min
    hot_ttl_seconds: int = 2400                 # 40 min
    max_focus_radars: int = 80
    hot_promote_dbz: float = 55.0
    hot_promote_hail_score: float = 0.20
    per_radar_timeout_seconds: int = 45


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
            'last_scan_time': None,
        }

        # Auto-swath idempotency cache: event_id -> last_generated_ts
        self._swath_cache: Dict[str, float] = {}

        # --- MRMS MESH backbone (optional, env-gated) ---
        self._mrms_cache = None
        self._mrms_updater = None
        if os.environ.get('ENABLE_MRMS', '').lower() in ('true', '1', 'yes'):
            try:
                from src.radar.mrms import MRMSCache, MRMSUpdater
                self._mrms_cache = MRMSCache()
                self._mrms_updater = MRMSUpdater(cache=self._mrms_cache)
                self._mrms_updater.start()
                print("[MRMS] MESH backbone enabled — background updater started")
            except Exception as e:
                print(f"[MRMS] Failed to initialize: {e}")

        # Discovery/Focus scheduler state
        self._stop_event = threading.Event()
        self._scans_lock = threading.Lock()

        # --- Discovery/Focus scheduling state ---
        self._hot_radars = {}  # radar_id -> last_active_ts (epoch seconds)
        self._next_due = {}    # radar_id -> next_due_ts (epoch seconds)
        self._sched_lock = threading.Lock()

        # --- Health stats ---
        self._stats_lock = threading.Lock()
        self._stats = {
            "last_tick_utc": None,
            "active_hot_radars": 0,
            "scheduled_discovery": 0,
            "scheduled_focus": 0,
            "processed_ok": 0,
            "processed_err": 0,
            "processed_timeout": 0,
            "cancelled_futures": 0,
            "timed_out_futures": 0,
            "avg_check_seconds": 0.0,
            "last_errors": [],  # keep last ~20 strings
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

        if self.config.enable_discovery_focus:
            print(f"\nScheduler: DISCOVERY/FOCUS (two-tier)")
            print(f"  Discovery interval: {self.config.discovery_interval_seconds}s | "
                  f"Focus interval: {self.config.focus_interval_seconds}s")
            print(f"  Hot TTL: {self.config.hot_ttl_seconds}s | "
                  f"Workers: {self.config.max_workers}")
            print(f"  Promote thresholds: dBZ>={self.config.hot_promote_dbz}, "
                  f"hail_score>={self.config.hot_promote_hail_score}")
        else:
            print(f"\nScheduler: LEGACY (sequential)")

        print("\nPress Ctrl+C to stop\n")
        print("=" * 70 + "\n")

        if background:
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop, name='monitor', daemon=True)
            self.monitor_thread.start()
        else:
            self._monitor_loop()

    def stop(self):
        """Stop monitoring."""
        self.running = False
        self._stop_event.set()
        if self._mrms_updater:
            self._mrms_updater.stop()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        print("\nMonitoring stopped.")
        self._print_stats()

    def _monitor_loop(self):
        """
        Main monitor loop.
        Discovery -> Focus scheduler with concurrency.
        """
        self.running = True
        executor = ThreadPoolExecutor(max_workers=int(self.config.max_workers))

        try:
            while self.running:
                tick_start = time.time()
                now_ts = tick_start

                if not self.config.enable_discovery_focus:
                    # fallback: old behavior (sequential)
                    for rid in self.config.radar_ids:
                        if not self.running:
                            break
                        try:
                            self._check_radar(rid)
                        except Exception as e:
                            self._stats_add_error(f"{rid}: {e}")
                    self.stats['last_scan_time'] = datetime.now()
                    try:
                        self._auto_generate_swaths()
                    except Exception as e:
                        self._stats_add_error(f"auto_swath: {e}")
                    try:
                        self._persist_tracker_events()
                    except Exception as e:
                        self._stats_add_error(f"persist_events: {e}")
                    self._stop_event.wait(self.config.scan_interval_seconds)
                    continue

                discovery_radars, focus_radars = self._schedule_tick(now_ts)
                scheduled = focus_radars + discovery_radars

                with self._stats_lock:
                    self._stats["last_tick_utc"] = datetime.utcnow().isoformat() + "Z"
                    self._stats["scheduled_discovery"] = len(discovery_radars)
                    self._stats["scheduled_focus"] = len(focus_radars)
                    self._stats["active_hot_radars"] = len(self._get_hot_radars_sorted())

                futures = {}
                for rid in scheduled:
                    futures[executor.submit(self._check_radar_with_result, rid)] = rid

                processed = 0
                ok = 0
                err = 0
                elapsed_sum = 0.0

                # Per-tick timeout: allow enough time for all futures
                # Use per_radar_timeout * 3 to give slower radars headroom
                tick_timeout = float(self.config.per_radar_timeout_seconds) * 3.0

                try:
                    for fut in as_completed(futures, timeout=tick_timeout):
                        if not self.running:
                            break

                        rid = futures[fut]
                        processed += 1

                        try:
                            res = fut.result(timeout=0)  # already completed
                        except Exception as e:
                            err += 1
                            self._stats_add_error(f"{rid}: future error: {e}")
                            self._update_next_due(rid, time.time(), self._is_hot(rid))
                            continue

                        elapsed_sum += float(res.get("elapsed") or 0.0)
                        result_ts = time.time()

                        if not res.get("ok"):
                            err += 1
                            self._stats_add_error(f"{rid}: {res.get('error')}")
                            self._update_next_due(rid, result_ts, self._is_hot(rid))
                            continue

                        ok += 1

                        # Promote to HOT based on cheap evidence
                        max_ref = res.get("max_reflectivity")
                        hail_peak = res.get("hail_score_peak")

                        if (max_ref is not None and float(max_ref) >= float(self.config.hot_promote_dbz)) or \
                           (hail_peak is not None and float(hail_peak) >= float(self.config.hot_promote_hail_score)):
                            self._mark_radar_hot(rid, result_ts)

                        self._update_next_due(rid, result_ts, self._is_hot(rid))
                except TimeoutError:
                    # Some futures didn't finish in time — cancel and move on
                    timed_out = len(futures) - processed
                    cancelled = sum(1 for fut in futures if fut.cancel())
                    self._stats_add_error(
                        f"tick_timeout: {timed_out}/{len(futures)} futures unfinished "
                        f"after {tick_timeout:.0f}s, cancelled={cancelled}"
                    )
                    err += timed_out
                    with self._stats_lock:
                        self._stats["processed_timeout"] += 1
                        self._stats["cancelled_futures"] += cancelled
                        self._stats["timed_out_futures"] += timed_out

                # Update rolling stats
                with self._stats_lock:
                    self._stats["processed_ok"] += ok
                    self._stats["processed_err"] += err
                    if processed > 0:
                        avg = elapsed_sum / processed
                        prev = self._stats["avg_check_seconds"]
                        self._stats["avg_check_seconds"] = (
                            0.8 * prev + 0.2 * avg if prev > 0 else avg
                        )

                self.stats['last_scan_time'] = datetime.now()

                # Auto-generate swaths for active events (never crashes the loop)
                try:
                    self._auto_generate_swaths()
                except Exception as e:
                    self._stats_add_error(f"auto_swath: {e}")

                # Persist tracker events to CRM hail_events table
                try:
                    self._persist_tracker_events()
                except Exception as e:
                    self._stats_add_error(f"persist_events: {e}")

                # Sleep until next tick — use the shorter focus interval
                # so hot radars get re-scanned promptly
                tick_elapsed = time.time() - tick_start
                sleep_time = max(0, self.config.focus_interval_seconds - tick_elapsed)
                if sleep_time > 0:
                    self._stop_event.wait(sleep_time)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        finally:
            self.running = False
            executor.shutdown(wait=False)
            self._print_stats()

    def _check_radar(self, radar_id: str) -> Optional[Dict]:
        """Check a single radar for new data. Returns analysis dict or None."""
        try:
            # Find recent scans
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=self.config.lookback_minutes)

            scans = self.conn.get_avail_scans_in_range(start_time, end_time, radar_id)

            if not scans:
                return None

            # Get most recent scan
            def get_scan_time(s):
                st = s.scan_time
                if st.tzinfo is not None:
                    st = st.replace(tzinfo=None)
                return st

            latest = max(scans, key=get_scan_time)
            scan_key = f"{radar_id}_{latest.filename}"

            # Skip if already processed
            with self._scans_lock:
                if scan_key in self.processed_scans:
                    return None

            print(f"  {radar_id}: New scan {latest.filename}")

            # Download and analyze
            results = self.conn.download(latest, self.temp_dir)

            if not results.success:
                return None

            filepath = results.success[0].filepath
            radar = pyart.io.read_nexrad_archive(filepath)

            # Analyze for hail
            analysis = self._analyze_radar(radar, radar_id)

            self.stats['scans_processed'] += 1
            with self._scans_lock:
                self.processed_scans.add(scan_key)

                # Cap processed_scans to prevent unbounded memory growth
                if len(self.processed_scans) > 500:
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

            return analysis

        except Exception as e:
            print(f"  {radar_id}: Error - {e}")
            return None

    # ------------------------------------------------------------------
    # Discovery / Focus scheduler helpers
    # ------------------------------------------------------------------

    def _check_radar_with_result(self, radar_id: str) -> dict:
        """
        Runs one radar check and returns summary dict.
        Must NOT raise (catch inside).
        """
        start = time.time()
        try:
            analysis = self._check_radar(radar_id)
            max_ref = None
            hail_peak = None
            if isinstance(analysis, dict):
                max_ref = analysis.get("max_reflectivity")
                dets = analysis.get("detections") or []
                if dets:
                    hail_peak = max(d.get("hail_score", 0) for d in dets)
            return {
                "ok": True,
                "radar_id": radar_id,
                "elapsed": time.time() - start,
                "max_reflectivity": max_ref,
                "hail_score_peak": hail_peak,
            }
        except Exception as e:
            return {
                "ok": False,
                "radar_id": radar_id,
                "elapsed": time.time() - start,
                "error": str(e),
            }

    def _should_promote(self, radar_id: str, analysis: Optional[Dict]) -> Optional[str]:
        """Return a reason string if this radar should be promoted to hot, else None."""
        if analysis is None:
            return None
        max_ref = analysis.get('max_reflectivity', 0)
        if max_ref >= self.config.hot_promote_dbz:
            return f"ref={max_ref:.1f}dBZ"
        detections = analysis.get('detections') or []
        for det in detections:
            if det.get('hail_score', 0) >= self.config.hot_promote_hail_score:
                return f"hail_score={det['hail_score']:.2f}"
        return None

    def get_health(self) -> dict:
        """Return current scheduler health stats."""
        with self._stats_lock:
            return dict(self._stats)

    def _stats_add_error(self, msg: str):
        with self._stats_lock:
            self._stats["processed_err"] += 1
            self._stats["last_errors"].append(msg)
            if len(self._stats["last_errors"]) > 20:
                self._stats["last_errors"] = self._stats["last_errors"][-20:]

    def _mark_radar_hot(self, radar_id: str, now_ts: float):
        with self._sched_lock:
            self._hot_radars[radar_id] = now_ts

    def _prune_hot_radars(self, now_ts: float):
        ttl = float(self.config.hot_ttl_seconds)
        with self._sched_lock:
            stale = [rid for rid, ts in self._hot_radars.items() if (now_ts - ts) > ttl]
            for rid in stale:
                self._hot_radars.pop(rid, None)

    def _is_hot(self, radar_id: str) -> bool:
        with self._sched_lock:
            return radar_id in self._hot_radars

    def _get_hot_radars_sorted(self) -> List[str]:
        """Return hot radar IDs sorted by newest activity first."""
        with self._sched_lock:
            return [rid for rid, _ in sorted(
                self._hot_radars.items(), key=lambda kv: kv[1], reverse=True
            )]

    def _record_stat(self, key: str, inc: int = 1):
        """Thread-safe increment of a _stats counter."""
        with self._stats_lock:
            self._stats[key] = self._stats.get(key, 0) + inc

    def _get_all_radar_ids(self) -> List[str]:
        """Return the full list of radar IDs to discovery-scan.
        Uses coverage module if available, else config.radar_ids."""
        try:
            from src.radar.coverage import get_all_radars
            return [r.site_code for r in get_all_radars()]
        except ImportError:
            return list(self.config.radar_ids)

    def _schedule_tick(self, now_ts: float):
        """
        Decide which radars to check this tick.
        Returns two lists: discovery_radars, focus_radars

        In discovery/focus mode, sources from the full national DB inventory
        (206+ radars) via _get_all_radar_ids(), NOT the config.radar_ids default.
        """
        radar_ids = self._get_all_radar_ids()

        # Initialize next_due if missing
        with self._sched_lock:
            for rid in radar_ids:
                if rid not in self._next_due:
                    self._next_due[rid] = now_ts  # eligible immediately

        # prune hot list
        self._prune_hot_radars(now_ts)

        hot = set(self._get_hot_radars_sorted())

        due_focus = []
        due_discovery = []

        with self._sched_lock:
            for rid in radar_ids:
                if self._next_due.get(rid, 0) > now_ts:
                    continue

                if rid in hot:
                    due_focus.append(rid)
                else:
                    due_discovery.append(rid)

        # Throttle discovery per tick (amortize 206 radars)
        max_disc = int(self.config.max_discovery_radars_per_tick)
        if len(due_discovery) > max_disc:
            due_discovery = due_discovery[:max_disc]

        return due_discovery, due_focus

    def _update_next_due(self, radar_id: str, now_ts: float, is_hot: bool):
        """Set next eligible scan time for a radar after processing."""
        interval = (self.config.focus_interval_seconds if is_hot
                    else self.config.discovery_interval_seconds)
        with self._sched_lock:
            self._next_due[radar_id] = now_ts + interval

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

        # --- Connected-component BFS (8-connected) ---
        H, W = mask.shape
        visited = np.zeros((H, W), dtype=np.uint8)
        q = deque()
        comps = []

        _NEIGHBORS = ((-1, -1), (-1, 0), (-1, 1),
                       (0, -1),           (0, 1),
                       (1, -1),  (1, 0),  (1, 1))

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
                    for dr, dc in _NEIGHBORS:
                        nr, nc = rr + dr, cc + dc
                        if 0 <= nr < H and 0 <= nc < W and mask[nr, nc] and not visited[nr, nc]:
                            visited[nr, nc] = 1
                            q.append((nr, nc))
                if len(pts) >= min_pixels:
                    comps.append(pts)

        largest_comp_pixels = max((len(c) for c in comps), default=0)
        comps_count = len(comps)
        comps_passing = sum(1 for c in comps if len(c) >= int(min_pixels))

        if getattr(self.config, 'debug_object_extraction', False):
            try:
                print(f"[OBJDBG] {radar_id} thr={threshold:.1f} min_px={int(min_pixels)} "
                      f"comps={comps_count} pass={comps_passing} largest={largest_comp_pixels}")
            except Exception:
                pass

        if not comps:
            return []

        # --- Gate area estimation (computed once for the sweep) ---
        area_method = 'metadata'
        try:
            gate_spacing_km = float(radar.range['meters_between_gates']) / 1000.0
        except Exception:
            gate_spacing_km = 0.25
            area_method = 'fallback_gate'

        n_azimuths = max(len(azimuths), 1)
        az_spacing_rad = 2.0 * math.pi / n_azimuths  # actual azimuth spacing

        # Try pyart gate geometry for better accuracy
        try:
            x, y, _ = radar.get_gate_x_y_z(sweep_idx)  # metres
            x_km = x / 1000.0
            y_km = y / 1000.0
            # Sample gate area at mid-range using Jacobian of (az, range) grid
            mid_az = H // 2
            mid_rng = W // 2
            dx = float(x_km[min(mid_az + 1, H - 1), mid_rng] - x_km[max(mid_az - 1, 0), mid_rng])
            dy = float(y_km[mid_az, min(mid_rng + 1, W - 1)] - y_km[mid_az, max(mid_rng - 1, 0)])
            sample_gate_area = abs(dx * dy) / 4.0  # average of the 2x2 stencil
            if 0.001 < sample_gate_area < 5.0:
                area_method = 'pyart_gate_xy'
        except Exception:
            sample_gate_area = None

        # --- Per-object summary with dual-pol stats and hail scoring ---
        summaries = []
        for pts in comps:
            max_ref = -9999.0
            w_sum_r = 0.0
            w_sum_c = 0.0
            w_total = 0.0
            rhohv_vals = []
            zdr_vals = []

            for rr, cc in pts:
                v = float(arr[rr, cc])
                w = max(v - threshold, 0.0) + 1.0  # reflectivity weight (above threshold)
                w_sum_r += rr * w
                w_sum_c += cc * w
                w_total += w
                if v > max_ref:
                    max_ref = v
                if rhohv_arr is not None and not np.isnan(rhohv_arr[rr, cc]):
                    rhohv_vals.append(float(rhohv_arr[rr, cc]))
                if zdr_arr is not None and not np.isnan(zdr_arr[rr, cc]):
                    zdr_vals.append(float(zdr_arr[rr, cc]))

            # Reflectivity-weighted centroid
            cr = w_sum_r / w_total if w_total > 0 else sum(rr for rr, _ in pts) / len(pts)
            cc_avg = w_sum_c / w_total if w_total > 0 else sum(cc for _, cc in pts) / len(pts)

            az = float(azimuths[int(round(min(cr, H - 1)))])
            rng = float(ranges_km[int(round(min(cc_avg, W - 1)))])
            lat, lon = self._az_range_to_latlon(radar_lat, radar_lon, az, rng)

            # Gate area: prefer pyart gate_xy, else analytical
            if area_method == 'pyart_gate_xy' and sample_gate_area is not None:
                gate_area_km2 = sample_gate_area
            else:
                gate_area_km2 = max(0.01, (max(rng, 1.0) * az_spacing_rad) * gate_spacing_km)
            area_km2 = gate_area_km2 * len(pts)
            # Sanity clamp: single storm object shouldn't exceed ~5000 km²
            area_km2 = min(area_km2, 5000.0)

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
                'area_method': area_method,
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
                # Hail score from reflectivity + MESH only (no dual-pol)
                hs = 0.0
                hs += min(1.0, max(0.0, (ref - 50.0) / 15.0)) * 0.30
                hs += min(1.0, max(0.0, (mesh_mm - 15.0) / 35.0)) * 0.30
                hs = min(1.0, max(0.0, hs))

                selected.append({
                    'lat': c['lat'],
                    'lon': c['lon'],
                    'reflectivity': c['reflectivity'],
                    'mesh_mm': mesh_mm,
                    'area_km2': 50,  # rough default
                    'radar_id': radar_id,
                    'hail_score': hs,
                    'min_rhohv': None,
                    'mean_zdr': None,
                })

        return selected

    # ------------------------------------------------------------------
    # Auto-swath: generate/update swath polygons for active events
    # ------------------------------------------------------------------

    def _auto_generate_swaths(self):
        """
        Auto-generate merged swath polygons for ACTIVE events.

        Idempotency: skips events whose swath was generated in the last 30 min.
        Never raises — all exceptions caught and logged.
        """
        try:
            from src.web.routes.storm_tracking_api import get_tracker
            tracker = get_tracker()
        except Exception:
            return

        events = tracker.get_events(lookback_minutes=180, join_distance_km=25.0)
        if not events:
            return

        now_ts = time.time()
        ttl = 1800  # 30 minutes

        for ev in events:
            if ev.status == 'EXPIRED':
                continue

            # Idempotency check
            last_ts = self._swath_cache.get(ev.event_id, 0)
            if (now_ts - last_ts) < ttl:
                continue

            try:
                merged = tracker.create_event_merged_swath(
                    ev.event_id, buffer_km=3.0,
                    lookback_minutes=180, join_distance_km=25.0,
                )
                if merged and merged.get('coordinates'):
                    self._swath_cache[ev.event_id] = now_ts
            except Exception as e:
                self._stats_add_error(f"auto_swath({ev.event_id}): {e}")

        # Evict stale cache entries
        stale = [k for k, v in self._swath_cache.items() if (now_ts - v) > ttl * 2]
        for k in stale:
            del self._swath_cache[k]

    # ------------------------------------------------------------------
    # Persist tracker events to CRM hail_events table
    # ------------------------------------------------------------------

    def _persist_tracker_events(self):
        """
        Persist all tracker events (with swaths) into CRM hail_events table.
        Idempotent via event_name UPSERT for NEXRAD_REALTIME events.
        Applies quality gate: suppress low-confidence junk.
        """
        try:
            from src.web.routes.storm_tracking_api import get_tracker
            tracker = get_tracker()
        except Exception:
            return

        events = tracker.get_events(lookback_minutes=360, join_distance_km=25.0)
        if not events:
            return

        from src.db.engine import get_connection

        try:
            with get_connection('sqlite:///data/hailtracker_crm.db') as conn:
                # Ensure partial unique index for NEXRAD_REALTIME upsert
                conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_hail_events_rt_upsert
                    ON hail_events(event_name) WHERE data_source = 'NEXRAD_REALTIME'
                """)

                # Migrate: add columns if missing
                for col_def in [
                    ('evidence_mrms', 'INTEGER DEFAULT 0'),
                    ('evidence_dualpol', 'INTEGER DEFAULT 0'),
                    ('evidence_multi_radar', 'INTEGER DEFAULT 0'),
                    ('evidence_spc', 'INTEGER DEFAULT 0'),
                    ('evidence_lsr', 'INTEGER DEFAULT 0'),
                    ('evidence_persistence', 'INTEGER DEFAULT 0'),
                    ('bbox_min_lat', 'REAL'),
                    ('bbox_max_lat', 'REAL'),
                    ('bbox_min_lon', 'REAL'),
                    ('bbox_max_lon', 'REAL'),
                    ('severity', "TEXT DEFAULT 'MINOR'"),
                ]:
                    try:
                        conn.execute(f"ALTER TABLE hail_events ADD COLUMN {col_def[0]} {col_def[1]}")
                    except Exception:
                        pass  # column already exists

                persisted = 0
                suppressed = 0
                for ev in events:
                    try:
                        # --- Quality gate ---
                        if ev.commercial_confidence < 45:
                            suppressed += 1
                            continue
                        mrms_val = ev.mrms_mesh_peak if ev.mrms_mesh_peak is not None else 0
                        if mrms_val < 20 and not ev.evidence_dualpol and not ev.evidence_lsr:
                            suppressed += 1
                            continue

                        # Build swath polygon GeoJSON
                        swath_json = None
                        swath_method = 'tracker'
                        swath_area_sqmi = 0.0

                        try:
                            merged = tracker.create_event_merged_swath(
                                ev.event_id, buffer_km=3.0,
                                lookback_minutes=360, join_distance_km=25.0,
                            )
                            if merged and 'geometry' in merged:
                                swath_json = json.dumps(merged['geometry'])
                                props = merged.get('properties', {})
                                swath_method = props.get('swath_method', 'tracker')
                                swath_area_sqmi = props.get('swath_area_sqmi', 0.0) or 0.0
                        except Exception:
                            pass

                        # Fallback: individual cell swath
                        if not swath_json:
                            for cell_id in ev.cell_ids:
                                try:
                                    cell_swath = tracker.create_track_swath(cell_id, buffer_km=3.0)
                                    if cell_swath and 'geometry' in cell_swath:
                                        swath_json = json.dumps(cell_swath['geometry'])
                                        props = cell_swath.get('properties', {})
                                        swath_method = props.get('method', 'track_buffer')
                                        swath_area_sqmi = props.get('swath_area_sqmi', 0.0) or 0.0
                                        break
                                except Exception:
                                    pass

                        # Fallback: centroid point
                        if not swath_json:
                            swath_json = json.dumps({
                                'type': 'Point',
                                'coordinates': [ev.centroid_lon, ev.centroid_lat],
                            })
                            swath_method = 'centroid_point'

                        # Convert area
                        if swath_area_sqmi == 0.0 and ev.estimated_area_sq_km > 0:
                            swath_area_sqmi = round(ev.estimated_area_sq_km * 0.386102, 1)

                        # Use authoritative hail size (MRMS-preferred)
                        max_hail_size = ev.authoritative_hail_inches
                        avg_hail_size = round(max_hail_size * 0.65, 2) if max_hail_size > 0 else 0.0

                        # Compute bbox from swath GeoJSON (with fallback radius for points)
                        from src.radar.geo_utils import compute_bbox_from_geojson
                        try:
                            geoj = json.loads(swath_json)
                            bbox = compute_bbox_from_geojson(
                                geoj,
                                fallback_center=(ev.centroid_lat, ev.centroid_lon),
                                fallback_radius_miles=10.0,
                            )
                        except Exception:
                            bbox = compute_bbox_from_geojson(
                                {},
                                fallback_center=(ev.centroid_lat, ev.centroid_lon),
                                fallback_radius_miles=10.0,
                            )
                        bbox_min_lat = bbox['bbox_min_lat']
                        bbox_max_lat = bbox['bbox_max_lat']
                        bbox_min_lon = bbox['bbox_min_lon']
                        bbox_max_lon = bbox['bbox_max_lon']

                        # Severity classification from hail size
                        if max_hail_size >= 3.0:
                            severity = 'CATASTROPHIC'
                        elif max_hail_size >= 2.0:
                            severity = 'SEVERE'
                        elif max_hail_size >= 1.0:
                            severity = 'MODERATE'
                        else:
                            severity = 'MINOR'

                        conn.execute("""
                            INSERT INTO hail_events (
                                event_name, event_date, start_time, end_time,
                                center_lat, center_lon, swath_polygon, swath_area_sqmi,
                                max_hail_size, avg_hail_size, max_reflectivity, avg_reflectivity,
                                swath_method, num_detections, data_source, confidence_score,
                                evidence_mrms, evidence_dualpol, evidence_multi_radar,
                                evidence_spc, evidence_lsr, evidence_persistence,
                                bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon, severity
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEXRAD_REALTIME', ?,
                                      ?, ?, ?, ?, ?, ?,
                                      ?, ?, ?, ?, ?)
                            ON CONFLICT(event_name) WHERE data_source = 'NEXRAD_REALTIME'
                            DO UPDATE SET
                                end_time = excluded.end_time,
                                swath_polygon = excluded.swath_polygon,
                                swath_area_sqmi = excluded.swath_area_sqmi,
                                max_hail_size = excluded.max_hail_size,
                                avg_hail_size = excluded.avg_hail_size,
                                max_reflectivity = excluded.max_reflectivity,
                                avg_reflectivity = excluded.avg_reflectivity,
                                swath_method = excluded.swath_method,
                                num_detections = excluded.num_detections,
                                confidence_score = excluded.confidence_score,
                                evidence_mrms = excluded.evidence_mrms,
                                evidence_dualpol = excluded.evidence_dualpol,
                                evidence_multi_radar = excluded.evidence_multi_radar,
                                evidence_spc = excluded.evidence_spc,
                                evidence_lsr = excluded.evidence_lsr,
                                evidence_persistence = excluded.evidence_persistence,
                                bbox_min_lat = excluded.bbox_min_lat,
                                bbox_max_lat = excluded.bbox_max_lat,
                                bbox_min_lon = excluded.bbox_min_lon,
                                bbox_max_lon = excluded.bbox_max_lon,
                                severity = excluded.severity,
                                updated_at = CURRENT_TIMESTAMP
                        """, (
                            ev.event_id,
                            ev.start_time.strftime('%Y-%m-%d'),
                            ev.start_time.isoformat(),
                            ev.end_time.isoformat(),
                            ev.centroid_lat, ev.centroid_lon,
                            swath_json, swath_area_sqmi,
                            max_hail_size, avg_hail_size,
                            ev.max_reflectivity, round(ev.max_reflectivity * 0.85, 1),
                            swath_method, len(ev.cell_ids),
                            ev.commercial_confidence,
                            int(ev.evidence_mrms), int(ev.evidence_dualpol),
                            int(ev.evidence_multi_radar), int(ev.evidence_spc),
                            int(ev.evidence_lsr), int(ev.evidence_persistence),
                            bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon, severity,
                        ))
                        persisted += 1
                    except Exception as e:
                        print(f"[PERSIST-ERROR] event {ev.event_id}: {e}")

                if persisted > 0 or suppressed > 0:
                    print(f"    Persisted {persisted} events, suppressed {suppressed} (quality gate)")
        except Exception as e:
            print(f"[PERSIST-ERROR] {e}")

    def _enrich_detections_with_mrms(self, detections: List[Dict]) -> None:
        """
        Attach MRMS MESH values to detection dicts (in-place).

        Non-blocking: if MRMS cache is empty or disabled, detections
        are left unchanged (no mrms_mesh_mm key).
        """
        if not self._mrms_cache or not self._mrms_cache.is_loaded:
            return

        source_time = self._mrms_cache.source_time
        for det in detections:
            lat = det.get('lat')
            lon = det.get('lon')
            if lat is None or lon is None:
                continue
            val = self._mrms_cache.query_point(lat, lon)
            if val is not None:
                det['mrms_mesh_mm'] = val
                det['mrms_source_time'] = source_time

    def _feed_tracker(self, detections: List[Dict], scan_time: datetime):
        """Feed detections into the global StormCellTracker instance and persist events to DB."""
        try:
            from src.web.routes.storm_tracking_api import get_tracker
            tracker = get_tracker()
            cells = tracker.process_radar_scan(detections, scan_time)
            if cells:
                print(f"    Tracker: {len(cells)} cells from {len(detections)} detections")

                # Persist tracker events to hail_events DB for calendar/map
                try:
                    from src.radar.event_persister import persist_tracker_events
                    persisted = persist_tracker_events(tracker)
                    if persisted > 0:
                        print(f"    Persisted {persisted} events to hail_events DB")
                except Exception as pe:
                    print(f"    Event persist warning: {pe}")
        except Exception as e:
            print(f"    Tracker feed error: {e}")

    def _analyze_radar(self, radar, radar_id: str) -> Optional[Dict]:
        """Analyze radar data for hail signatures."""
        try:
            # Get radar location
            radar_lat = float(radar.latitude['data'][0])
            radar_lon = float(radar.longitude['data'][0])

            # DEV-only object extraction diagnostics (auto-enable in _analyze_radar)
            if hasattr(self.config, 'debug_object_extraction'):
                self.config.debug_object_extraction = True

            # --- Multi-detection extraction: storm objects first, fallback to peaks ---
            # In real radar, storm objects can be sparse unless min_pixels is low.
            # We try a ladder: strict -> relaxed -> peaks.
            peaks = self._extract_storm_objects(
                radar,
                radar_id,
                top_n=10,
                min_pixels=40,
                dbz_threshold=self.config.min_reflectivity_dbz,
            )

            if not peaks:
                # relaxed object extraction (lets us build swaths earlier)
                peaks = self._extract_storm_objects(
                    radar,
                    radar_id,
                    top_n=10,
                    min_pixels=15,
                    dbz_threshold=self.config.min_reflectivity_dbz - 5.0,
                )

            if not peaks:
                peaks = self._extract_top_peaks(radar, radar_id, top_n=10, min_separation_km=10.0)
            if peaks:
                # Enrich with MRMS MESH (non-blocking, no-op if disabled)
                self._enrich_detections_with_mrms(peaks)
                scan_time = datetime.utcnow()
                self._feed_tracker(peaks, scan_time)

            # Store diagnostics for debug endpoint
            try:
                from src.web.routes.storm_tracking_api import store_last_scan_diagnostics
                store_last_scan_diagnostics({
                    'scan_time': datetime.utcnow().isoformat() + 'Z',
                    'radar_id': radar_id,
                    'detections': peaks or [],
                })
            except Exception:
                pass

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
                'detections': peaks,
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

        if self.config.enable_discovery_focus:
            s = self.get_health()
            print(f"\nDiscovery/Focus scheduler:")
            print(f"  Scheduled discovery: {s['scheduled_discovery']}")
            print(f"  Scheduled focus:     {s['scheduled_focus']}")
            print(f"  Processed OK:        {s['processed_ok']}")
            print(f"  Processed errors:    {s['processed_err']}")
            print(f"  Processed timeouts:  {s['processed_timeout']}")
            print(f"  Active hot radars:   {s['active_hot_radars']}")
            print(f"  Last tick (UTC):     {s['last_tick_utc']}")
            if s['last_errors']:
                print(f"  Recent errors ({len(s['last_errors'])}):")
                for err in s['last_errors'][-5:]:
                    print(f"    - {err}")

        print("=" * 70)

    def get_status(self) -> Dict:
        """Get current monitor status."""
        hot_ids = self._get_hot_radars_sorted()
        scheduler_mode = 'discovery_focus' if self.config.enable_discovery_focus else 'legacy'

        all_radars = self._get_all_radar_ids() if self.config.enable_discovery_focus else list(self.config.radar_ids)
        result = {
            'running': self.running,
            'radars': all_radars,
            'radar_count': len(all_radars),
            'scans_processed': self.stats['scans_processed'],
            'alerts_generated': self.stats['alerts_generated'],
            'last_scan': self.stats['last_scan_time'].isoformat() if self.stats['last_scan_time'] else None,
            'active_alerts': len(self.alert_manager.get_active_alerts()),
            'scheduler_mode': scheduler_mode,
            'hot_radar_count': len(hot_ids),
            'hot_radars': hot_ids,
            'scheduler_health': self.get_health(),
        }
        return result
