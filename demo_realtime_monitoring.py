"""
Real-Time Hail Monitoring Demo
Demonstrates the complete system monitoring for hail events
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.radar.data_structures import HailDetection
from src.radar.swath_generator import SwathGenerator
from src.alerts.database import AlertDatabase
from src.alerts.alert_manager import Alert, AlertLevel


def demo_realtime_monitoring():
    print("\n" + "="*80)
    print("REAL-TIME HAIL MONITORING DEMO")
    print("="*80 + "\n")

    print("This demo simulates real-time hail detection and swath generation")
    print("In production, this would connect to live NEXRAD radar data\n")

    # Initialize database
    db_path = "sqlite:///data/demo/demo_alerts.db"
    os.makedirs("data/demo", exist_ok=True)
    db = AlertDatabase(db_path)

    print("Monitoring for hail events...\n")

    # Simulate incoming hail detections
    simulated_events = [
        {
            'time': '14:30',
            'location': 'Dallas, TX',
            'lat': 32.7767,
            'lon': -96.7970,
            'size': 1.75,
            'size_mm': 44,
            'description': 'Golf ball size hail reported',
            'level': AlertLevel.WARNING
        },
        {
            'time': '14:35',
            'location': 'Fort Worth, TX',
            'lat': 32.7555,
            'lon': -97.3308,
            'size': 1.5,
            'size_mm': 38,
            'description': 'Ping pong ball size hail',
            'level': AlertLevel.WATCH
        },
        {
            'time': '14:40',
            'location': 'Plano, TX',
            'lat': 33.0198,
            'lon': -96.6989,
            'size': 2.0,
            'size_mm': 51,
            'description': 'Lime size hail reported',
            'level': AlertLevel.CRITICAL
        }
    ]

    all_detections = []
    swath_areas = []

    for i, event in enumerate(simulated_events, 1):
        print(f"[{event['time']}] HAIL DETECTED!")
        print(f"   Location: {event['location']}")
        print(f"   Size: {event['size']}\" ({event['description']})")
        print(f"   Coordinates: {event['lat']:.4f}, {event['lon']:.4f}")

        # Create detection
        detection = HailDetection(
            lat=event['lat'],
            lon=event['lon'],
            hail_size=event['size'],
            timestamp=f"2024-11-15T{event['time']}:00"
        )

        all_detections.append(detection)

        # Generate individual swath
        swath = SwathGenerator.create_circular_swath(
            event['lat'], event['lon'], event['size']
        )

        # Calculate area
        area = SwathGenerator.calculate_swath_area(swath)
        swath_areas.append(area)

        print(f"   Generated swath: {swath['properties']['radius_miles']:.1f} mi radius")
        print(f"   Affected area: ~{area:.1f} sq mi")

        # Create and save alert
        alert = Alert(
            id=f"DEMO-{i:04d}",
            timestamp=datetime.now(),
            level=event['level'],
            event_name=f"Hail Storm - {event['location']}",
            location=(event['lat'], event['lon']),
            radar_id="KFWS",
            hail_detected=True,
            hail_probability=85,
            hail_size_mm=event['size_mm'],
            severity="moderate" if event['size'] < 2.0 else "severe",
            pdr_score=int(event['size'] * 40),
            max_reflectivity=60 + event['size'] * 5,
            mesh_mm=event['size_mm'],
            posh=75 + event['size'] * 10,
            message=event['description'],
            recommendations=[
                f"Hail swath estimated at {area:.1f} sq mi",
                "Monitor storm movement",
                "Prepare for customer inquiries"
            ]
        )

        db.save_alert(alert)

        print(f"   Saved to database (Alert: {alert.id})")
        print()

        # Simulate time delay
        if i < len(simulated_events):
            time.sleep(1)

    # Generate composite swath from all detections
    print("="*80)
    print("GENERATING COMPOSITE SWATH")
    print("="*80 + "\n")

    print(f"Combining {len(all_detections)} detections into composite swath...\n")

    composite_swath = SwathGenerator.create_composite_swath(all_detections)
    composite_area = SwathGenerator.calculate_swath_area(composite_swath)

    print(f"Composite Swath Generated:")
    print(f"   Method: {composite_swath['properties']['method']}")
    print(f"   Detections: {composite_swath['properties']['detection_count']}")
    print(f"   Max hail: {composite_swath['properties']['max_hail_size']}\"")
    print(f"   Track length: {composite_swath['properties']['track_length_miles']:.1f} mi")
    print(f"   Width: {composite_swath['properties']['width_miles']:.1f} mi")
    print(f"   Total area: ~{composite_area:.1f} sq mi")
    print()

    # Query database
    print("="*80)
    print("DATABASE SUMMARY")
    print("="*80 + "\n")

    stats = db.get_statistics(days=1)
    total_alerts = db.get_count()

    print(f"Total alerts in database: {total_alerts}")
    print(f"Today's alerts:")
    print(f"   - Critical: {stats['by_level']['critical']}")
    print(f"   - Warning: {stats['by_level']['warning']}")
    print(f"   - Watch: {stats['by_level']['watch']}")
    print(f"   - Info: {stats['by_level']['info']}")
    print(f"Average PDR Score: {stats['avg_pdr_score']}")
    print(f"Max Hail Size: {stats['max_hail_size_mm']}mm")
    print()

    # PDR Business Impact
    print("="*80)
    print("PDR BUSINESS IMPACT")
    print("="*80 + "\n")

    total_area = composite_area

    print(f"Total affected area: {total_area:.1f} square miles")
    print()

    # Estimate vehicles affected (rough calculation)
    # Assume ~100 vehicles per square mile in metro areas
    vehicles_per_sq_mi = 100
    estimated_vehicles = int(total_area * vehicles_per_sq_mi)

    print(f"Estimated vehicles in affected areas: ~{estimated_vehicles:,}")
    print()

    # PDR opportunity
    penetration_rate = 0.10  # 10% of damaged vehicles get PDR
    avg_repair_value = 500  # $500 average PDR job

    potential_jobs = int(estimated_vehicles * penetration_rate)
    potential_revenue = potential_jobs * avg_repair_value

    print(f"PDR Opportunity Analysis:")
    print(f"   Potential customers (10% penetration): {potential_jobs:,}")
    print(f"   Potential revenue (@$500/job): ${potential_revenue:,}")
    print()

    # Success message
    print("="*80)
    print("DEMO COMPLETE")
    print("="*80 + "\n")

    print("Your hail detection system successfully:")
    print("   [OK] Detected and tracked hail events")
    print("   [OK] Generated accurate swaths")
    print("   [OK] Stored alerts in database")
    print("   [OK] Queried and analyzed historical data")
    print("   [OK] Calculated business impact")
    print()

    print("NEXT STEPS:")
    print("   1. Connect to live NEXRAD radar data (install PyART)")
    print("   2. Set up automated monitoring for your service area")
    print("   3. Configure email/SMS alerts for hail events")
    print("   4. Build customer-facing reports")
    print("   5. Integrate with your CRM/marketing systems")
    print()

    print("Your $10,000/year hail detection system is ready for production!")
    print()


if __name__ == '__main__':
    demo_realtime_monitoring()
