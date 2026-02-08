"""
Complete workflow example: From radar detection to database to export
"""

import os
import sys

sys.path.insert(0, '.')

from src.radar.swath_generator import HailDetection, SwathGenerator
from src.radar.swath_database import SwathDatabase


def complete_workflow_example():
    """
    Demonstrates complete workflow:
    1. Simulate radar detections
    2. Generate swath
    3. Store in database
    4. Query and export
    """

    print("\n" + "="*70)
    print("COMPLETE HAIL SWATH WORKFLOW")
    print("="*70 + "\n")

    # ========================================================================
    # STEP 1: SIMULATE REAL RADAR DETECTIONS
    # ========================================================================

    print("STEP 1: Simulating NEXRAD radar detections...")
    print("Scenario: May 15, 2024 tornado outbreak - Oklahoma City")
    print()

    # Realistic tornado-warned supercell
    radar_detections = [
        # Initial development southwest of OKC
        HailDetection(
            lat=35.20, lon=-97.70, hail_size=1.00,
            timestamp='2024-05-15T16:00:00',
            reflectivity=55, storm_motion_dir=50, storm_motion_speed=45
        ),

        # Intensification
        HailDetection(
            lat=35.30, lon=-97.60, hail_size=1.75,
            timestamp='2024-05-15T16:10:00',
            reflectivity=62, storm_motion_dir=50, storm_motion_speed=45
        ),

        # Hook echo forming - tornado warning
        HailDetection(
            lat=35.40, lon=-97.50, hail_size=2.50,
            timestamp='2024-05-15T16:20:00',
            reflectivity=70, storm_motion_dir=50, storm_motion_speed=45
        ),

        # Peak intensity - large hail core
        HailDetection(
            lat=35.50, lon=-97.40, hail_size=3.00,
            timestamp='2024-05-15T16:30:00',
            reflectivity=75, storm_motion_dir=50, storm_motion_speed=45
        ),

        # Continuing northeast
        HailDetection(
            lat=35.60, lon=-97.30, hail_size=2.75,
            timestamp='2024-05-15T16:40:00',
            reflectivity=72, storm_motion_dir=50, storm_motion_speed=45
        ),

        # Weakening
        HailDetection(
            lat=35.70, lon=-97.20, hail_size=2.00,
            timestamp='2024-05-15T16:50:00',
            reflectivity=65, storm_motion_dir=50, storm_motion_speed=45
        ),
    ]

    print(f"Simulated {len(radar_detections)} radar detections")
    print(f"   - Time span: 50 minutes")
    print(f"   - Max hail: 3.0 inches (baseball size)")
    print(f"   - Max reflectivity: 75 dBZ (extreme)")
    print()

    # ========================================================================
    # STEP 2: GENERATE SWATH
    # ========================================================================

    print("STEP 2: Generating hail swath polygon...")

    swath = SwathGenerator.auto_generate_swath(detections=radar_detections)

    print(f"Swath generated:")
    print(f"   - Method: {swath['properties']['method']}")
    print(f"   - Area: {swath['properties']['area_sq_miles']} square miles")
    print()

    # ========================================================================
    # STEP 3: STORE IN DATABASE
    # ========================================================================

    print("STEP 3: Storing event in database...")

    db = SwathDatabase()

    event_id = db.create_event_from_detections(
        radar_detections,
        event_name="May 15 2024 OKC Tornado Outbreak",
        data_source="NEXRAD KTLX"
    )

    print()

    # ========================================================================
    # STEP 4: RETRIEVE AND ANALYZE
    # ========================================================================

    print("STEP 4: Retrieving event from database...")

    event = db.get_event_by_id(event_id)
    detections = db.get_event_detections(event_id)

    print(f"Retrieved event #{event['id']}:")
    print(f"   - {event['event_name']}")
    print(f"   - Date: {event['event_date']}")
    print(f"   - Duration: {event['start_time']} to {event['end_time']}")
    print(f"   - Swath: {event['swath_area_sqmi']} sq mi")
    print(f"   - Max hail: {event['max_hail_size']}\"")
    print(f"   - Storm motion: {event['storm_motion_dir']}deg at {event['storm_motion_speed']} mph")
    print()

    print(f"Detection timeline:")
    for i, det in enumerate(detections, 1):
        time = det['detection_time'][11:16]  # Extract HH:MM
        print(f"   {i}. {time} - {det['hail_size']}\" hail @ {det['reflectivity']} dBZ")
    print()

    # ========================================================================
    # STEP 5: EXPORT FOR MAPPING
    # ========================================================================

    print("STEP 5: Exporting to GeoJSON for mapping...")

    db.export_event_geojson(event_id, 'data/okc_tornado_outbreak.geojson')

    print()

    # ========================================================================
    # STEP 6: QUERY AFFECTED AREA
    # ========================================================================

    print("STEP 6: Finding other events in Oklahoma...")

    okc_events = db.get_events_by_location(35.4676, -97.5164, radius_miles=100)

    print(f"Found {len(okc_events)} hail events within 100 miles of OKC:")
    for evt in okc_events:
        print(f"   - {evt['event_name']} ({evt['max_hail_size']}\")")
    print()

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("="*70)
    print("COMPLETE WORKFLOW FINISHED")
    print("="*70)
    print()
    print("WORKFLOW STEPS:")
    print("  1. Simulated NEXRAD radar detections")
    print("  2. Generated hail swath polygon (reflectivity method)")
    print("  3. Stored event + detections in database")
    print("  4. Retrieved and analyzed event data")
    print("  5. Exported to GeoJSON for mapping")
    print("  6. Queried events by location")
    print()
    print("NEXT STEPS:")
    print("  - Open data/okc_tornado_outbreak.geojson at geojson.io")
    print("  - See the complete swath with detection points")
    print("  - Integrate with fleet location database (Phase 1-9)")
    print("  - Identify affected dealerships for marketing")
    print()


def demonstrate_all_methods():
    """
    Demonstrate all swath generation methods with database storage
    """

    print("\n" + "="*70)
    print("DEMONSTRATING ALL SWATH METHODS WITH DATABASE")
    print("="*70 + "\n")

    db = SwathDatabase()

    # Method 1: Circular (single point)
    print("Method 1: Circular swath (single detection)...")
    single_detection = [
        HailDetection(33.5779, -101.8552, 2.0, '2024-06-01T18:00:00')
    ]
    event_id_1 = db.create_event_from_detections(
        single_detection,
        event_name="Lubbock Isolated Storm"
    )
    print()

    # Method 2: Elliptical (single point with movement data)
    print("Method 2: Elliptical swath (manual with movement data)...")
    event_id_2 = db.create_event_manual(
        event_name="Amarillo Moving Storm",
        event_date="2024-06-02",
        center_lat=35.2220,
        center_lon=-101.8313,
        max_hail_size=1.75,
        storm_motion_dir=60,
        storm_motion_speed=40,
        duration_minutes=30,
        data_source="Manual"
    )
    print()

    # Method 3: Composite (multiple detections, no reflectivity)
    print("Method 3: Composite swath (multiple detections)...")
    composite_detections = [
        HailDetection(31.90, -102.10, 1.5, '2024-06-03T17:00:00'),
        HailDetection(32.00, -102.00, 1.75, '2024-06-03T17:15:00'),
        HailDetection(32.10, -101.90, 2.0, '2024-06-03T17:30:00'),
    ]
    event_id_3 = db.create_event_from_detections(
        composite_detections,
        event_name="Midland Storm Track"
    )
    print()

    # Method 4: Reflectivity (multiple detections with dBZ)
    print("Method 4: Reflectivity swath (with radar intensity)...")
    reflectivity_detections = [
        HailDetection(32.40, -99.80, 1.25, '2024-06-04T16:00:00', reflectivity=52),
        HailDetection(32.50, -99.70, 1.75, '2024-06-04T16:10:00', reflectivity=58),
        HailDetection(32.60, -99.60, 2.25, '2024-06-04T16:20:00', reflectivity=66),
        HailDetection(32.70, -99.50, 2.0, '2024-06-04T16:30:00', reflectivity=62),
    ]
    event_id_4 = db.create_event_from_detections(
        reflectivity_detections,
        event_name="Abilene Supercell"
    )
    print()

    # Summary
    print("="*70)
    print("ALL METHODS DEMONSTRATED")
    print("="*70)
    print()

    stats = db.get_event_statistics()
    print(f"Database now contains:")
    print(f"   - {stats['total_events']} total events")
    print(f"   - {stats['total_detections']} total detections")
    print(f"   - {stats['total_area_sqmi']} sq mi total affected area")
    print()
    print(f"Events by method:")
    for method, count in stats['events_by_method'].items():
        print(f"   - {method}: {count}")
    print()

    # Export all
    db.export_all_events_geojson('data/all_methods_demo.geojson')
    print("Exported all events to data/all_methods_demo.geojson")
    print()


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    complete_workflow_example()
    demonstrate_all_methods()
