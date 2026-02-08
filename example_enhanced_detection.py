"""
Example: Enhanced Dual-Pol Hail Detection Pipeline

Demonstrates the complete workflow:
1. Dual-pol radar data analysis
2. Hail probability scoring
3. Size estimation
4. Swath generation
5. GeoJSON export
"""

import os
from datetime import datetime, timedelta
from src.radar.enhanced_detection import EnhancedHailDetection, quick_analysis
from src.radar.dualpol_hail_detector import DualPolHailDetector


def example_enhanced_detection():
    print("\n" + "="*70)
    print("ENHANCED DUAL-POL HAIL DETECTION EXAMPLE")
    print("="*70 + "\n")

    # Initialize enhanced detection system
    enhanced = EnhancedHailDetection()

    # ====================================================================
    # EXAMPLE 1: ANALYZE SINGLE DUAL-POL SIGNATURE
    # ====================================================================

    print("[1/4] Analyzing single dual-pol signature...")
    print()

    sig = enhanced.analyze_dual_pol_signature(
        reflectivity=62.0,
        zdr=-0.3,
        cc=0.91,
        kdp=0.2,
        lat=32.77,
        lon=-96.80
    )

    print("   Input: Z=62 dBZ, ZDR=-0.3 dB, CC=0.91, KDP=0.2")
    print(f"   Results:")
    print(f"     Hail Probability: {sig.hail_probability:.1%}")
    print(f"     Estimated Size: {sig.estimated_size_inches:.2f}\"")
    print(f"     Size Category: {DualPolHailDetector.classify_hail_size(sig.estimated_size_inches)}")
    print(f"     Confidence: {sig.confidence.name}")
    print()
    print("   Component Scores:")
    print(f"     Z score:   {sig.z_score:.2f} (30% weight)")
    print(f"     ZDR score: {sig.zdr_score:.2f} (40% weight) <- Most important")
    print(f"     CC score:  {sig.cc_score:.2f} (20% weight)")
    print(f"     KDP score: {sig.kdp_score:.2f} (10% weight)")
    print()

    # ====================================================================
    # EXAMPLE 2: ANALYZE COMPLETE STORM WITH MULTIPLE DETECTIONS
    # ====================================================================

    print("[2/4] Analyzing complete storm track...")
    print()

    # Simulate storm track with dual-pol data
    # Storm moving NE, intensifying then weakening
    base_time = datetime(2024, 11, 15, 14, 30, 0)

    storm_data = [
        # Developing phase
        {
            'lat': 32.70, 'lon': -96.90,
            'reflectivity': 52.0, 'zdr': 0.8, 'cc': 0.94, 'kdp': 0.5,
            'timestamp': (base_time + timedelta(minutes=0)).isoformat()
        },
        {
            'lat': 32.72, 'lon': -96.87,
            'reflectivity': 55.0, 'zdr': 0.5, 'cc': 0.93, 'kdp': 0.4,
            'timestamp': (base_time + timedelta(minutes=5)).isoformat()
        },
        # Mature phase - peak intensity
        {
            'lat': 32.75, 'lon': -96.84,
            'reflectivity': 60.0, 'zdr': 0.0, 'cc': 0.91, 'kdp': 0.2,
            'timestamp': (base_time + timedelta(minutes=10)).isoformat()
        },
        {
            'lat': 32.78, 'lon': -96.81,
            'reflectivity': 65.0, 'zdr': -0.5, 'cc': 0.88, 'kdp': 0.0,
            'timestamp': (base_time + timedelta(minutes=15)).isoformat()
        },
        {
            'lat': 32.81, 'lon': -96.78,
            'reflectivity': 63.0, 'zdr': -0.3, 'cc': 0.90, 'kdp': 0.1,
            'timestamp': (base_time + timedelta(minutes=20)).isoformat()
        },
        # Weakening phase
        {
            'lat': 32.84, 'lon': -96.75,
            'reflectivity': 58.0, 'zdr': 0.3, 'cc': 0.92, 'kdp': 0.3,
            'timestamp': (base_time + timedelta(minutes=25)).isoformat()
        },
        {
            'lat': 32.87, 'lon': -96.72,
            'reflectivity': 53.0, 'zdr': 0.6, 'cc': 0.94, 'kdp': 0.5,
            'timestamp': (base_time + timedelta(minutes=30)).isoformat()
        },
        {
            'lat': 32.90, 'lon': -96.69,
            'reflectivity': 48.0, 'zdr': 1.0, 'cc': 0.96, 'kdp': 0.8,
            'timestamp': (base_time + timedelta(minutes=35)).isoformat()
        }
    ]

    print("   Storm track data (8 radar scans over 35 minutes):")
    print("   " + "-"*60)
    print(f"   {'Time':>8} | {'Z':>5} | {'ZDR':>5} | {'CC':>5} | {'Phase':>12}")
    print("   " + "-"*60)

    for i, data in enumerate(storm_data):
        if i < 2:
            phase = "Developing"
        elif i < 5:
            phase = "Mature"
        else:
            phase = "Weakening"
        print(f"   T+{i*5:02d} min | {data['reflectivity']:5.1f} | {data['zdr']:5.1f} | {data['cc']:5.2f} | {phase:>12}")
    print("   " + "-"*60)
    print()

    # Analyze the storm
    event = enhanced.analyze_storm(
        dual_pol_data=storm_data,
        event_name="DFW_Supercell_Nov15",
        event_date="2024-11-15"
    )

    print("   Analysis Results:")
    print(f"     Event: {event.event_name}")
    print(f"     Is Hail: {event.detection_result.is_hail}")
    print(f"     Max Probability: {event.max_probability:.1%}")
    print(f"     Max Hail Size: {event.max_hail_size:.2f}\" ({DualPolHailDetector.classify_hail_size(event.max_hail_size)})")
    print(f"     Confidence: {event.confidence.name}")
    print(f"     Detections above threshold: {len(event.detections)}/{len(storm_data)}")
    print()
    print("   Swath Information:")
    print(f"     Method: {event.swath_method}")
    print(f"     Area: {event.swath_area_sqmi:.1f} sq mi")
    print()
    print("   Radar Statistics:")
    print(f"     Max Reflectivity: {event.max_reflectivity:.1f} dBZ")
    print(f"     Min ZDR: {event.min_zdr:.2f} dB")
    print(f"     Min CC: {event.min_cc:.2f}")
    print()

    # Export to GeoJSON
    enhanced.export_event_geojson(
        event,
        'data/enhanced_storm_analysis.geojson',
        include_detections=True
    )
    print("   Exported: data/enhanced_storm_analysis.geojson")
    print()

    # ====================================================================
    # EXAMPLE 3: COMPARE DIFFERENT STORM TYPES
    # ====================================================================

    print("[3/4] Comparing different storm types...")
    print()

    storm_types = {
        'Severe Supercell': {
            'reflectivity': 68.0, 'zdr': -0.8, 'cc': 0.86, 'kdp': -0.2
        },
        'Moderate Supercell': {
            'reflectivity': 58.0, 'zdr': 0.2, 'cc': 0.92, 'kdp': 0.3
        },
        'Marginal Hail': {
            'reflectivity': 52.0, 'zdr': 0.8, 'cc': 0.95, 'kdp': 0.6
        },
        'Heavy Rain': {
            'reflectivity': 50.0, 'zdr': 2.0, 'cc': 0.98, 'kdp': 1.5
        },
        'Light Rain': {
            'reflectivity': 35.0, 'zdr': 1.5, 'cc': 0.99, 'kdp': 0.5
        }
    }

    print(f"   {'Storm Type':<20} | {'Prob':>6} | {'Size':>6} | {'Category':<15} | {'Verdict'}")
    print("   " + "-"*75)

    for name, data in storm_types.items():
        is_hail, prob, size, cat = quick_analysis(
            data['reflectivity'], data['zdr'], data['cc'], data['kdp']
        )
        verdict = "HAIL" if is_hail else "NO HAIL"
        print(f"   {name:<20} | {prob:5.1%} | {size:5.2f}\" | {cat:<15} | {verdict}")

    print()

    # ====================================================================
    # EXAMPLE 4: GENERATE ACCURACY REPORT
    # ====================================================================

    print("[4/4] Generating accuracy report...")
    print()

    # Analyze a few more events for statistics
    test_storms = [
        # Strong hail event
        [
            {'lat': 33.0, 'lon': -97.0, 'reflectivity': 62, 'zdr': -0.2, 'cc': 0.90, 'timestamp': '2024-11-10T15:00:00'},
            {'lat': 33.02, 'lon': -96.98, 'reflectivity': 65, 'zdr': -0.5, 'cc': 0.88, 'timestamp': '2024-11-10T15:05:00'},
            {'lat': 33.04, 'lon': -96.96, 'reflectivity': 60, 'zdr': 0.0, 'cc': 0.91, 'timestamp': '2024-11-10T15:10:00'},
        ],
        # Moderate hail event
        [
            {'lat': 32.5, 'lon': -97.5, 'reflectivity': 55, 'zdr': 0.5, 'cc': 0.93, 'timestamp': '2024-11-11T16:00:00'},
            {'lat': 32.52, 'lon': -97.48, 'reflectivity': 57, 'zdr': 0.3, 'cc': 0.92, 'timestamp': '2024-11-11T16:05:00'},
        ],
        # Rain event (no hail)
        [
            {'lat': 33.5, 'lon': -96.5, 'reflectivity': 45, 'zdr': 2.0, 'cc': 0.98, 'timestamp': '2024-11-12T14:00:00'},
            {'lat': 33.52, 'lon': -96.48, 'reflectivity': 42, 'zdr': 2.2, 'cc': 0.99, 'timestamp': '2024-11-12T14:05:00'},
        ]
    ]

    for i, storm in enumerate(test_storms):
        enhanced.analyze_storm(storm, f"Test_Storm_{i+1}", f"2024-11-{10+i}")

    report = enhanced.get_accuracy_report()

    print("   ACCURACY REPORT")
    print("   " + "="*50)
    print(f"   Method: {report['method']}")
    print(f"   Target Accuracy: {report['target_accuracy']:.0%}")
    print()
    print(f"   Events Analyzed: {report['total_events']}")
    print(f"   Hail Events Detected: {report['hail_events']}")
    print(f"   Total Detections: {report['total_detections']}")
    print()
    print("   Confidence Distribution:")
    for conf, count in report['confidence_distribution'].items():
        if count > 0:
            print(f"     {conf}: {count}")
    print()
    print("   Size Distribution:")
    for size_range, count in report['size_distribution'].items():
        if count > 0:
            print(f"     {size_range}: {count}")
    print()

    # ====================================================================
    # SUMMARY
    # ====================================================================

    print("="*70)
    print("ENHANCED DETECTION EXAMPLE COMPLETE")
    print("="*70)
    print()
    print("KEY FEATURES:")
    print("  -> Dual-pol weighted scoring (Z:30%, ZDR:40%, CC:20%, KDP:10%)")
    print("  -> Automatic size estimation from dual-pol signatures")
    print("  -> Integrated swath generation (circular/track/composite)")
    print("  -> GeoJSON export with color-coded severity")
    print("  -> Target accuracy: 75%")
    print()
    print("DETECTION THRESHOLDS:")
    print("  -> 60% probability required for hail detection")
    print("  -> Z > 50 dBZ for hail consideration")
    print("  -> ZDR < 0.5 dB indicates spherical hail")
    print("  -> CC < 0.95 confirms hail presence")
    print()
    print("OUTPUT FILES:")
    print("  -> data/enhanced_storm_analysis.geojson")
    print()
    print("VISUALIZATION:")
    print("  -> Open GeoJSON at geojson.io")
    print("  -> Shows swath polygon, detection points, and storm track")
    print("  -> Color-coded by hail severity")
    print()


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    example_enhanced_detection()
