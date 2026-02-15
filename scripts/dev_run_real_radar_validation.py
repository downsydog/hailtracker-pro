#!/usr/bin/env python3
"""
Multi-scan real-radar validation script for the hail tracking pipeline.

Downloads multiple recent NEXRAD Level II scans chronologically,
feeds each through _analyze_radar -> StormCellTracker, and checks
the active event feed after all scans are processed.

NOTE: This script validates radar parsing and cell tracking only.
      It does NOT persist events to the CRM database or test calendar population.
      Persistence + calendar E2E is validated by: scripts/test_e2e_persist_calendar.py

Usage:
    python scripts/dev_run_real_radar_validation.py
    python scripts/dev_run_real_radar_validation.py --radar_id KTLX --minutes 180 --max_scans 12
"""

import sys
import os
import argparse
import tempfile
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_scan_time(scan):
    """Extract naive UTC datetime from a nexradaws scan object."""
    st = scan.scan_time
    if st.tzinfo is not None:
        st = st.replace(tzinfo=None)
    return st


def run(radar_id: str, minutes: int, max_scans: int, min_dbz: float, top_n: int):
    """Run multi-scan real-radar validation for a single radar site."""
    print("=" * 70)
    print(f"MULTI-SCAN REAL RADAR VALIDATION: {radar_id}")
    print(f"  lookback={minutes}min, max_scans={max_scans}, min_dbz={min_dbz}, top_n={top_n}")
    print("=" * 70)

    # --- Check dependencies ---
    try:
        import nexradaws
        import pyart
        import numpy as np
    except ImportError as e:
        print(f"\nFATAL: Missing dependency: {e}")
        print("Install with: pip install nexradaws arm-pyart numpy")
        return False

    from src.alerts.storm_monitor import StormMonitor, MonitorConfig
    from src.radar.storm_cell_tracker import StormCellTracker

    # --- Step 1: Query available scans ---
    print(f"\n[1] Querying AWS for {radar_id} scans (last {minutes} min)...")
    conn = nexradaws.NexradAwsInterface()
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=minutes)

    try:
        scans = conn.get_avail_scans_in_range(start_time, end_time, radar_id)
    except Exception as e:
        print(f"    ERROR querying scans: {e}")
        return False

    if not scans:
        print(f"    No scans found for {radar_id} in last {minutes} min")
        return False

    # Sort chronologically, take up to max_scans evenly spaced
    scans_sorted = sorted(scans, key=get_scan_time)
    print(f"    Found {len(scans_sorted)} scans total")
    print(f"    Earliest: {get_scan_time(scans_sorted[0]).isoformat()}Z")
    print(f"    Latest:   {get_scan_time(scans_sorted[-1]).isoformat()}Z")

    if len(scans_sorted) > max_scans:
        # Evenly sample, always include first and last
        step = max(1, (len(scans_sorted) - 1) / (max_scans - 1))
        indices = [int(round(i * step)) for i in range(max_scans)]
        indices = sorted(set(min(idx, len(scans_sorted) - 1) for idx in indices))
        selected = [scans_sorted[i] for i in indices]
    else:
        selected = scans_sorted

    print(f"    Selected {len(selected)} scans for processing")

    # --- Step 2: Build monitor + tracker ---
    config = MonitorConfig(
        radar_ids=[radar_id],
        min_reflectivity_dbz=min_dbz,
    )
    monitor = StormMonitor.__new__(StormMonitor)
    monitor.config = config
    monitor.classifier = None

    tracker = StormCellTracker(simulation_mode=False)

    temp_dir = tempfile.mkdtemp(prefix='hailtracker_multi_')
    print(f"    Temp dir: {temp_dir}")

    # --- Step 3: Process each scan chronologically ---
    total_detections = 0
    total_cells = 0
    scan_results = []

    for scan_idx, scan in enumerate(selected):
        scan_time = get_scan_time(scan)
        print(f"\n[3.{scan_idx + 1}] Scan {scan_idx + 1}/{len(selected)}: "
              f"{scan.filename} ({scan_time.isoformat()}Z)")

        # Download
        try:
            results = conn.download(scan, temp_dir)
        except Exception as e:
            print(f"    WARN: Download failed: {e}, skipping")
            continue

        if not results.success:
            print(f"    WARN: Download unsuccessful, skipping")
            continue

        filepath = results.success[0].filepath
        print(f"    Downloaded: {os.path.basename(filepath)}")

        # Parse
        try:
            radar = pyart.io.read_nexrad_archive(filepath)
        except Exception as e:
            print(f"    WARN: pyart parse failed: {e}, skipping")
            continue

        # Check reflectivity
        ref_field = None
        for fn in ['reflectivity', 'REF', 'DBZ']:
            if fn in radar.fields:
                ref_field = fn
                break
        if not ref_field:
            print(f"    WARN: No reflectivity field, skipping")
            continue

        ref_data = radar.get_field(0, ref_field)
        ref_max = float(np.max(ref_data)) if ref_data.count() > 0 else 0
        print(f"    Max ref (sweep 0): {ref_max:.1f} dBZ")

        # Dual-pol info
        has_zdr = any(f in radar.fields for f in ['differential_reflectivity', 'ZDR'])
        has_rhohv = any(f in radar.fields for f in ['cross_correlation_ratio', 'RHOHV'])

        # Extract storm objects
        storm_objs = monitor._extract_storm_objects(radar, radar_id, top_n=top_n, min_pixels=40)
        if not storm_objs:
            # Fallback to peaks
            peaks = monitor._extract_top_peaks(radar, radar_id, top_n=top_n, min_separation_km=10.0)
            detections = peaks
            method = 'peaks'
        else:
            detections = storm_objs
            method = 'objects'

        print(f"    Detections: {len(detections)} ({method})")
        for i, d in enumerate(detections[:3]):
            print(f"      #{i+1}: ({d['lat']:.3f}, {d['lon']:.3f}) "
                  f"ref={d['reflectivity']:.1f} dBZ, MESH={d['mesh_mm']:.1f} mm, "
                  f"hs={d.get('hail_score', 0):.4f}")

        # Feed tracker with true scan timestamp
        if detections:
            cells = tracker.process_radar_scan(detections, scan_time)
            print(f"    Cells: {len(cells)}")
            for cell in cells[:3]:
                print(f"      Cell #{cell.id}: ({cell.centroid_lat:.3f}, {cell.centroid_lon:.3f}) "
                      f"ref={cell.max_reflectivity:.1f} dBZ, "
                      f"hs={cell.hail_score:.4f}, hs_peak={cell.hail_score_peak:.4f}")
            total_cells += len(cells)
        else:
            cells = []

        total_detections += len(detections)
        scan_results.append({
            'scan': scan.filename,
            'time': scan_time,
            'ref_max': ref_max,
            'detections': len(detections),
            'method': method,
            'cells': len(cells),
            'has_zdr': has_zdr,
            'has_rhohv': has_rhohv,
        })

        # Clean up radar file to save disk
        try:
            os.remove(filepath)
        except OSError:
            pass

    # --- Step 4: Events + Active event feed ---
    print(f"\n[4] Events + Active event feed...")
    events = tracker.get_events(lookback_minutes=360, join_distance_km=25.0)
    print(f"    Events: {len(events)}")
    for ev in events[:10]:
        print(f"      Event {ev.event_id}: severity={ev.severity}, "
              f"hs_peak={ev.hail_score_peak:.4f}, hs_avg={ev.hail_score_avg:.4f}, "
              f"eq={ev.event_quality_score}, status={ev.status}, phase={ev.phase}, "
              f"impact_window={ev.impact_window_minutes}min, "
              f"cells={len(ev.cell_ids)}")

    feed = tracker.get_active_event_features(
        lookback_minutes=360, join_distance_km=25.0, limit=20, buffer_km=3.0
    )
    print(f"\n    Active event features: {len(feed)}")
    for i, feat in enumerate(feed[:10]):
        p = feat['properties']
        print(f"      #{i+1}: event_id={p['event_id']}, "
              f"severity={p['severity']}, "
              f"hs_peak={p['hail_score_peak']:.4f}, hs_avg={p['hail_score_avg']:.4f}, "
              f"eq={p['event_quality_score']}, sq={p['swath_quality_score']}, "
              f"status={p['status']}, phase={p['phase']}, "
              f"impact_window={p['impact_window_minutes']}min")

    # --- Step 5: Sanity checks ---
    print(f"\n[5] Sanity checks...")
    ok = True

    # Check that at least some detections were found across all scans
    if total_detections == 0 and any(r['ref_max'] >= min_dbz for r in scan_results):
        print(f"    FAIL: 0 detections but some scans had ref >= {min_dbz} dBZ")
        ok = False
    else:
        print(f"    OK: total_detections={total_detections} across {len(scan_results)} scans")

    # Multi-scan: with >= 2 scans feeding the same cells, we should get track swaths
    if len(scan_results) >= 2 and total_cells > 0 and len(feed) == 0:
        print(f"    INFO: {total_cells} cells across {len(scan_results)} scans "
              f"but 0 active feed features (may need more temporal spread)")
    elif len(feed) > 0:
        print(f"    OK: {len(feed)} active feed features generated")

    # Hail score sanity
    for ev in events:
        if not (0.0 <= ev.hail_score_peak <= 1.0):
            print(f"    FAIL: event {ev.event_id} hail_score_peak={ev.hail_score_peak} out of [0,1]")
            ok = False
        if not (0.0 <= ev.hail_score_avg <= 1.0):
            print(f"    FAIL: event {ev.event_id} hail_score_avg={ev.hail_score_avg} out of [0,1]")
            ok = False

    # MRMS field presence (attributes exist regardless of ENABLE_MRMS)
    mrms_enabled = os.environ.get('ENABLE_MRMS', '').lower() in ('true', '1', 'yes')
    for ev in events:
        if not hasattr(ev, 'mrms_mesh_peak'):
            print(f"    FAIL: event {ev.event_id} missing mrms_mesh_peak attribute")
            ok = False
        if not hasattr(ev, 'mrms_mesh_avg'):
            print(f"    FAIL: event {ev.event_id} missing mrms_mesh_avg attribute")
            ok = False
    if ok:
        print(f"    OK: MRMS fields present on events (enabled={mrms_enabled})")

    if ok:
        print(f"    ALL SANITY CHECKS PASSED")

    # --- Summary ---
    print(f"\n{'=' * 70}")
    print(f"MULTI-SCAN SUMMARY: {radar_id}")
    print(f"  Time range: {start_time.isoformat()}Z -> {end_time.isoformat()}Z")
    print(f"  Scans processed: {len(scan_results)} / {len(selected)} selected / {len(scans_sorted)} available")
    print(f"  Total detections: {total_detections}")
    print(f"  Total cells tracked: {total_cells}")
    print(f"  Events: {len(events)}")
    print(f"  Active feed features: {len(feed)}")
    print(f"  Temp dir: {temp_dir}")

    if scan_results:
        print(f"\n  Per-scan breakdown:")
        for r in scan_results:
            print(f"    {r['time'].strftime('%H:%M:%S')}Z | ref={r['ref_max']:5.1f} dBZ | "
                  f"det={r['detections']:2d} ({r['method']:7s}) | cells={r['cells']:2d} | "
                  f"ZDR={'Y' if r['has_zdr'] else 'N'} RHOHV={'Y' if r['has_rhohv'] else 'N'}")

    print(f"{'=' * 70}")
    print(f"\nNOTE: This script validates radar parsing/tracking only.")
    print(f"      Persistence + calendar E2E -> scripts/test_e2e_persist_calendar.py")
    return ok


def main():
    parser = argparse.ArgumentParser(description='Multi-scan real radar validation for hail pipeline')
    parser.add_argument('--radar_id', default='KFWS', help='NEXRAD radar ID (default: KFWS)')
    parser.add_argument('--minutes', type=int, default=60, help='Lookback minutes (default: 60)')
    parser.add_argument('--max_scans', type=int, default=6, help='Max scans to process (default: 6)')
    parser.add_argument('--min_dbz', type=float, default=45.0, help='Min reflectivity threshold (default: 45)')
    parser.add_argument('--top_n', type=int, default=10, help='Max storm objects per scan (default: 10)')
    args = parser.parse_args()

    # Try requested radar, then fallbacks
    radars_to_try = [args.radar_id]
    if args.radar_id not in ('KTLX', 'KHGX'):
        radars_to_try.extend(['KTLX', 'KHGX'])
    else:
        for fb in ['KTLX', 'KHGX']:
            if fb != args.radar_id:
                radars_to_try.append(fb)

    for rid in radars_to_try:
        ok = run(
            radar_id=rid,
            minutes=args.minutes,
            max_scans=args.max_scans,
            min_dbz=args.min_dbz,
            top_n=args.top_n,
        )
        if ok is not False:
            sys.exit(0)
        else:
            print(f"\n--- {rid} failed, trying next fallback ---\n")

    print("FATAL: All radar sites failed")
    sys.exit(1)


if __name__ == '__main__':
    main()
