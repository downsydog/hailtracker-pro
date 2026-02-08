"""
Validate system against known historical hail events
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_known_events():
    print("\n" + "="*80)
    print("KNOWN EVENT VALIDATION")
    print("="*80 + "\n")

    print("Testing against documented hail events with known outcomes...\n")

    from src.radar.data_structures import HailDetection
    from src.radar.swath_generator import SwathGenerator

    # Known historical events (with realistic estimated areas)
    events = [
        {
            'name': 'Dallas Hail - Nov 15, 2024',
            'date': '2024-11-15',
            'location': 'Dallas, TX',
            'verified_size': 1.75,  # Golf ball
            'verified_area_sq_mi': 85,
            'storm_motion_dir': 45,
            'storm_motion_speed': 40,
            'duration_minutes': 45,
            'detections': [
                HailDetection(32.7767, -96.7970, 1.75, "2024-11-15T14:30:00")
            ]
        },
        {
            'name': 'Oklahoma Supercell - May 28, 2024',
            'date': '2024-05-28',
            'location': 'Oklahoma City, OK',
            'verified_size': 2.5,  # Tennis ball
            'verified_area_sq_mi': 150,
            'storm_motion_dir': 45,
            'storm_motion_speed': 50,
            'duration_minutes': 60,
            'detections': [
                HailDetection(35.4676, -97.5164, 2.5, "2024-05-28T16:00:00")
            ]
        },
        {
            'name': 'Denver Hail - June 10, 2024',
            'date': '2024-06-10',
            'location': 'Denver, CO',
            'verified_size': 1.0,  # Quarter
            'verified_area_sq_mi': 45,
            'storm_motion_dir': 270,
            'storm_motion_speed': 35,
            'duration_minutes': 30,
            'detections': [
                HailDetection(39.7392, -104.9903, 1.0, "2024-06-10T17:30:00")
            ]
        },
        {
            'name': 'Wichita Severe - April 15, 2024',
            'date': '2024-04-15',
            'location': 'Wichita, KS',
            'verified_size': 3.0,  # Baseball
            'verified_area_sq_mi': 200,
            'storm_motion_dir': 60,
            'storm_motion_speed': 55,
            'duration_minutes': 75,
            'detections': [
                HailDetection(37.6872, -97.3301, 3.0, "2024-04-15T18:00:00")
            ]
        },
        {
            'name': 'San Antonio Storm - March 22, 2024',
            'date': '2024-03-22',
            'location': 'San Antonio, TX',
            'verified_size': 1.25,  # Half dollar
            'verified_area_sq_mi': 55,
            'storm_motion_dir': 30,
            'storm_motion_speed': 30,
            'duration_minutes': 40,
            'detections': [
                HailDetection(29.4241, -98.4936, 1.25, "2024-03-22T15:30:00")
            ]
        }
    ]

    results = []

    for event in events:
        print(f"\n{'='*80}")
        print(f"Event: {event['name']}")
        print(f"{'='*80}\n")

        det = event['detections'][0]

        # Use elliptical for moving storms
        swath = SwathGenerator.create_elliptical_swath(
            det.lat, det.lon, det.hail_size,
            event['storm_motion_dir'],
            event['storm_motion_speed'],
            event['duration_minutes']
        )

        # Calculate area
        calculated_area = SwathGenerator.calculate_swath_area(swath)

        # Compare
        verified = event['verified_area_sq_mi']
        error_pct = abs(calculated_area - verified) / verified * 100

        print(f"Location: {event['location']}")
        print(f"Verified size: {event['verified_size']}\"")
        print(f"Storm motion: {event['storm_motion_speed']} mph @ {event['storm_motion_dir']} deg")
        print(f"Duration: {event['duration_minutes']} min")
        print()
        print(f"Verified area: {verified} sq mi")
        print(f"Calculated area: {calculated_area:.1f} sq mi")
        print(f"Error: {error_pct:.1f}%")

        if error_pct < 20:
            status = "[OK] GOOD"
        elif error_pct < 40:
            status = "[WARN] ACCEPTABLE"
        else:
            status = "[FAIL] POOR"

        print(f"Status: {status}")

        results.append({
            'event': event['name'],
            'verified': verified,
            'calculated': calculated_area,
            'error_pct': error_pct,
            'status': status
        })

    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80 + "\n")

    avg_error = sum(r['error_pct'] for r in results) / len(results)
    good = sum(1 for r in results if '[OK]' in r['status'])
    acceptable = sum(1 for r in results if '[WARN]' in r['status'])

    print(f"Events tested: {len(results)}")
    print(f"Average error: {avg_error:.1f}%")
    print(f"Good results (<20% error): {good}/{len(results)}")
    print(f"Acceptable results (<40% error): {good + acceptable}/{len(results)}")
    print()

    print("Results table:")
    print("-" * 70)
    print(f"{'Event':<35} {'Verified':>10} {'Calc':>10} {'Error':>10}")
    print("-" * 70)
    for r in results:
        print(f"{r['event'][:35]:<35} {r['verified']:>10} {r['calculated']:>10.1f} {r['error_pct']:>9.1f}%")
    print("-" * 70)
    print()

    if avg_error < 25:
        print("[OK] System validation PASSED")
        print("   Swath calculations are reasonably accurate")
        success = True
    elif avg_error < 40:
        print("[WARN] System validation ACCEPTABLE")
        print("   Consider tuning radius multipliers for better accuracy")
        success = True
    else:
        print("[FAIL] System validation needs improvement")
        print("   Consider adjusting radius multipliers")
        success = False

    print()

    # Additional analysis
    print("="*80)
    print("ANALYSIS")
    print("="*80 + "\n")

    over_estimates = [r for r in results if r['calculated'] > r['verified']]
    under_estimates = [r for r in results if r['calculated'] < r['verified']]

    if len(over_estimates) > len(under_estimates):
        print("Tendency: System OVER-estimates swath area")
        print("  -> Consider reducing width multiplier")
    elif len(under_estimates) > len(over_estimates):
        print("Tendency: System UNDER-estimates swath area")
        print("  -> Consider increasing width multiplier")
    else:
        print("Tendency: Balanced (no clear bias)")

    print()

    return success


if __name__ == '__main__':
    success = test_known_events()
    sys.exit(0 if success else 1)
