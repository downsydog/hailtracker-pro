#!/usr/bin/env python3
"""
Test: StormMonitor timeout resilience.

Proves that when some radars take longer than per_radar_timeout_seconds,
the monitor thread does NOT crash. Instead it:
  1. Catches the TimeoutError
  2. Cancels stale futures
  3. Increments processed_timeout and cancelled_futures stats
  4. Continues to the next tick
"""
import os, sys, time, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.alerts.storm_monitor import StormMonitor, MonitorConfig


def test_timeout_resilience():
    print("=" * 60)
    print("TEST: Monitor timeout resilience")
    print("=" * 60)

    # Config with very short timeouts so the test runs fast
    # tick_timeout = per_radar_timeout * 3 = 2 * 3 = 6s
    # Slow radars sleep 10s > 6s, so TimeoutError fires
    config = MonitorConfig(
        radar_ids=['KFWS', 'KTLX', 'KDFW', 'KAMA', 'KLBB'],
        scan_interval_seconds=2,
        per_radar_timeout_seconds=2,   # tick_timeout = 6s
        max_workers=5,
        enable_discovery_focus=True,
        focus_interval_seconds=1,
        discovery_interval_seconds=1,
    )

    monitor = StormMonitor(config)

    # --- Monkeypatch: make _check_radar_with_result sleep too long for some radars ---
    original_check = monitor._check_radar_with_result
    slow_radars = {'KTLX', 'KAMA', 'KLBB'}

    def patched_check(radar_id):
        if radar_id in slow_radars:
            # Sleep longer than tick_timeout (per_radar_timeout * 3 = 6s)
            time.sleep(10.0)
            return {"ok": False, "error": "simulated_slow", "elapsed": 10.0}
        # Fast radars return immediately
        return {"ok": True, "elapsed": 0.01, "max_reflectivity": 40.0, "hail_score_peak": 0.05}

    monitor._check_radar_with_result = patched_check

    # --- Monkeypatch: override _get_all_radar_ids to use our small set ---
    monitor._get_all_radar_ids = lambda: list(config.radar_ids)

    # --- Monkeypatch: disable persistence and swath generation (no DB needed) ---
    monitor._auto_generate_swaths = lambda: None
    monitor._persist_tracker_events = lambda: None

    # Force running state so _monitor_loop can start
    monitor.running = True

    # Run monitor loop in a background thread, let it do 1 tick
    # tick_timeout=6s + buffer = ~10s total wait
    print("\n[1] Starting monitor thread (will run ~10s)...")
    loop_thread = threading.Thread(target=monitor._monitor_loop, daemon=True)
    loop_thread.start()

    # Let it run for enough time for at least 1 tick with timeout
    time.sleep(10.0)

    # Stop the monitor
    monitor.running = False
    monitor._stop_event.set()
    loop_thread.join(timeout=5.0)

    alive = loop_thread.is_alive()
    health = monitor.get_health()

    print(f"\n[2] Monitor thread alive after stop: {alive}")
    print(f"    Health stats:")
    for k, v in sorted(health.items()):
        if k != 'last_errors':
            print(f"      {k}: {v}")
    if health.get('last_errors'):
        print(f"      last_errors:")
        for e in health['last_errors']:
            print(f"        - {e}")

    # --- Assertions ---
    print(f"\n[3] Assertions:")

    # Thread should NOT have crashed (it should have been stopped cleanly)
    assert not alive, f"FAIL: monitor thread still alive after stop"
    print(f"  OK: thread stopped cleanly")

    # processed_timeout should be > 0 (at least 1 tick timed out)
    pt = health.get('processed_timeout', 0)
    assert pt > 0, f"FAIL: processed_timeout={pt}, expected > 0"
    print(f"  OK: processed_timeout={pt}")

    # timed_out_futures should be > 0 (slow radars were abandoned)
    tof = health.get('timed_out_futures', 0)
    assert tof > 0, f"FAIL: timed_out_futures={tof}, expected > 0"
    print(f"  OK: timed_out_futures={tof}")

    # processed_ok should be > 0 (fast radars succeeded)
    po = health.get('processed_ok', 0)
    assert po > 0, f"FAIL: processed_ok={po}, expected > 0"
    print(f"  OK: processed_ok={po}")

    # last_errors should contain the timeout message
    errors = health.get('last_errors', [])
    has_timeout_msg = any('tick_timeout' in e for e in errors)
    assert has_timeout_msg, f"FAIL: no tick_timeout in last_errors: {errors}"
    print(f"  OK: tick_timeout message in last_errors")

    # processed_err should be > 0 (timed-out futures count as errors)
    pe = health.get('processed_err', 0)
    assert pe > 0, f"FAIL: processed_err={pe}, expected > 0"
    print(f"  OK: processed_err={pe}")

    print(f"\n{'=' * 60}")
    print(f"ALL ASSERTIONS PASSED")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    test_timeout_resilience()
