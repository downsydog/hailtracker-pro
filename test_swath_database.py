"""
Test swath database storage and retrieval
"""

import os
import sys

sys.path.insert(0, '.')

from src.radar.swath_generator import HailDetection
from src.radar.swath_database import SwathDatabase


def test_swath_database():
    print("\n" + "="*70)
    print("TESTING SWATH DATABASE SYSTEM")
    print("="*70 + "\n")

    # Initialize database
    db = SwathDatabase()

    # ========================================================================
    # TEST 1: CREATE SIMPLE EVENT
    # ========================================================================

    print("[1/8] Creating simple hail event...")

    simple_detections = [
        HailDetection(32.7767, -96.7970, 1.75, '2024-11-15T14:00:00')
    ]

    event_id_1 = db.create_event_from_detections(
        simple_detections,
        event_name="Dallas Single Detection Test"
    )

    print()

    # ========================================================================
    # TEST 2: CREATE COMPOSITE EVENT
    # ========================================================================

    print("[2/8] Creating composite event (multiple detections)...")

    composite_detections = [
        HailDetection(32.70, -97.00, 1.50, '2024-11-15T14:00:00', reflectivity=55),
        HailDetection(32.75, -96.90, 1.75, '2024-11-15T14:05:00', reflectivity=62),
        HailDetection(32.80, -96.80, 2.00, '2024-11-15T14:10:00', reflectivity=68),
        HailDetection(32.85, -96.70, 1.75, '2024-11-15T14:15:00', reflectivity=60),
        HailDetection(32.90, -96.60, 1.50, '2024-11-15T14:20:00', reflectivity=56),
    ]

    event_id_2 = db.create_event_from_detections(composite_detections)

    print()

    # ========================================================================
    # TEST 3: CREATE SUPERCELL EVENT
    # ========================================================================

    print("[3/8] Creating supercell event (high reflectivity)...")

    supercell_detections = [
        HailDetection(32.50, -97.30, 1.00, '2024-05-28T15:00:00', reflectivity=52, storm_motion_dir=45, storm_motion_speed=50),
        HailDetection(32.60, -97.15, 1.50, '2024-05-28T15:10:00', reflectivity=58, storm_motion_dir=45, storm_motion_speed=50),
        HailDetection(32.70, -97.00, 2.00, '2024-05-28T15:20:00', reflectivity=65, storm_motion_dir=45, storm_motion_speed=50),
        HailDetection(32.80, -96.85, 2.75, '2024-05-28T15:30:00', reflectivity=72, storm_motion_dir=45, storm_motion_speed=50),
        HailDetection(32.90, -96.70, 2.50, '2024-05-28T15:40:00', reflectivity=70, storm_motion_dir=45, storm_motion_speed=50),
        HailDetection(33.00, -96.55, 2.00, '2024-05-28T15:50:00', reflectivity=63, storm_motion_dir=45, storm_motion_speed=50),
    ]

    event_id_3 = db.create_event_from_detections(supercell_detections)

    print()

    # ========================================================================
    # TEST 4: RETRIEVE EVENT BY ID
    # ========================================================================

    print("[4/8] Retrieving event by ID...")

    event = db.get_event_by_id(event_id_2)

    print(f"Retrieved event #{event['id']}:")
    print(f"   - Name: {event['event_name']}")
    print(f"   - Date: {event['event_date']}")
    print(f"   - Max hail: {event['max_hail_size']}\"")
    print(f"   - Area: {event['swath_area_sqmi']} sq mi")
    print(f"   - Method: {event['swath_method']}")
    print(f"   - Detections: {event['num_detections']}")
    print()

    # ========================================================================
    # TEST 5: GET ALL EVENTS
    # ========================================================================

    print("[5/8] Getting all events...")

    all_events = db.get_all_events()

    print(f"Found {len(all_events)} events:")
    for event in all_events:
        print(f"   - {event['event_name']} ({event['event_date']})")
        print(f"     Max hail: {event['max_hail_size']}\", Area: {event['swath_area_sqmi']} sq mi")

    print()

    # ========================================================================
    # TEST 6: GET EVENT DETECTIONS
    # ========================================================================

    print("[6/8] Getting detections for supercell event...")

    detections = db.get_event_detections(event_id_3)

    print(f"Found {len(detections)} detections:")
    for i, det in enumerate(detections, 1):
        print(f"   {i}. {det['detection_time'][:16]} - {det['hail_size']}\" @ {det['reflectivity']} dBZ")

    print()

    # ========================================================================
    # TEST 7: QUERY BY LOCATION
    # ========================================================================

    print("[7/8] Finding events near Dallas (50 mile radius)...")

    dallas_events = db.get_events_by_location(32.7767, -96.7970, radius_miles=50)

    print(f"Found {len(dallas_events)} events near Dallas:")
    for event in dallas_events:
        print(f"   - {event['event_name']}")

    print()

    # ========================================================================
    # TEST 8: STATISTICS
    # ========================================================================

    print("[8/8] Getting database statistics...")

    stats = db.get_event_statistics()

    print(f"Database Statistics:")
    print(f"   - Total events: {stats['total_events']}")
    print(f"   - Total detections: {stats['total_detections']}")
    print(f"   - Total area affected: {stats['total_area_sqmi']} sq mi")
    print()

    if stats['largest_event']:
        print(f"   Largest event: {stats['largest_event']['event_name']}")
        print(f"     - Area: {stats['largest_event']['swath_area_sqmi']} sq mi")
        print(f"     - Max hail: {stats['largest_event']['max_hail_size']}\"")
    print()

    if stats['most_intense_event']:
        print(f"   Most intense: {stats['most_intense_event']['event_name']}")
        print(f"     - Reflectivity: {stats['most_intense_event']['max_reflectivity']} dBZ")
        print(f"     - Max hail: {stats['most_intense_event']['max_hail_size']}\"")
    print()

    print(f"   Events by method:")
    for method, count in stats['events_by_method'].items():
        print(f"     - {method}: {count}")
    print()

    # ========================================================================
    # EXPORT TESTS
    # ========================================================================

    print("="*70)
    print("EXPORTING DATA")
    print("="*70 + "\n")

    # Export single event
    db.export_event_geojson(event_id_3, 'data/supercell_event.geojson')

    # Export all events
    db.export_all_events_geojson('data/all_hail_events.geojson')

    print()
    print("="*70)
    print("SWATH DATABASE TESTS COMPLETE")
    print("="*70)
    print()
    print("DATABASE FEATURES:")
    print("  - Store hail events with swaths")
    print("  - Store individual detections")
    print("  - Query by ID, date, location")
    print("  - Calculate statistics")
    print("  - Export to GeoJSON")
    print()
    print("FILES CREATED:")
    print("  - data/supercell_event.geojson (single event with detections)")
    print("  - data/all_hail_events.geojson (all events)")
    print()
    print("View these files at geojson.io to see your hail swaths on a map!")
    print()


def test_additional_queries():
    """Test additional database query methods"""
    print("\n" + "="*70)
    print("TESTING ADDITIONAL QUERIES")
    print("="*70 + "\n")

    db = SwathDatabase()

    # Test query by hail size
    print("[1/4] Finding events with 2\"+ hail...")
    large_hail_events = db.get_events_by_hail_size(2.0)
    print(f"  Found {len(large_hail_events)} events with 2\"+ hail")
    for event in large_hail_events:
        print(f"    - {event['event_name']}: {event['max_hail_size']}\"")
    print()

    # Test query by date range
    print("[2/4] Finding events in November 2024...")
    nov_events = db.get_events_by_date_range('2024-11-01', '2024-11-30')
    print(f"  Found {len(nov_events)} events in November 2024")
    for event in nov_events:
        print(f"    - {event['event_name']} ({event['event_date']})")
    print()

    # Test point containment
    print("[3/4] Checking if a point is in an event's swath...")
    all_events = db.get_all_events(limit=1)
    if all_events:
        event = all_events[0]
        test_lat = event['center_lat']
        test_lon = event['center_lon']
        is_in_swath = db.check_point_in_event(event['id'], test_lat, test_lon)
        print(f"  Center point ({test_lat:.4f}, {test_lon:.4f}) in event {event['id']}: {is_in_swath}")
    print()

    # Test finding events affecting a point
    print("[4/4] Finding events affecting a specific point...")
    affecting = db.find_events_affecting_point(32.7767, -96.7970)
    print(f"  Found {len(affecting)} events affecting Dallas coordinates")
    for event in affecting:
        print(f"    - {event['event_name']}")
    print()

    print("="*70)
    print("ADDITIONAL QUERIES COMPLETE")
    print("="*70 + "\n")


def test_manual_event():
    """Test creating a manual event without radar detections"""
    print("\n" + "="*70)
    print("TESTING MANUAL EVENT CREATION")
    print("="*70 + "\n")

    db = SwathDatabase()

    print("Creating manual event (without radar detections)...")

    event_id = db.create_event_manual(
        event_name="Manual Test Event - Wichita",
        event_date="2024-06-15",
        center_lat=37.6872,
        center_lon=-97.3301,
        max_hail_size=2.5,
        storm_motion_dir=60,
        storm_motion_speed=35,
        duration_minutes=45,
        data_source="Social Media"
    )

    print(f"Created manual event #{event_id}")
    print()

    # Verify
    event = db.get_event_by_id(event_id)
    print(f"Retrieved manual event:")
    print(f"   - Name: {event['event_name']}")
    print(f"   - Date: {event['event_date']}")
    print(f"   - Max hail: {event['max_hail_size']}\"")
    print(f"   - Area: {event['swath_area_sqmi']} sq mi")
    print(f"   - Method: {event['swath_method']}")
    print(f"   - Data source: {event['data_source']}")
    print()

    print("="*70)
    print("MANUAL EVENT TEST COMPLETE")
    print("="*70 + "\n")


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    test_swath_database()
    test_additional_queries()
    test_manual_event()
