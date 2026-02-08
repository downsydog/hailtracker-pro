"""
Test edge cases and boundary conditions
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_edge_cases():
    print("\n" + "="*80)
    print("EDGE CASE TESTING")
    print("="*80 + "\n")

    print("Testing boundary conditions and edge cases...")
    print()

    from src.radar.swath_generator import SwathGenerator
    from src.radar.data_structures import HailDetection

    edge_cases = []
    passed = 0
    total = 0

    # ========================================================================
    # EDGE CASE 1: Zero hail size
    # ========================================================================

    total += 1
    print("[1/10] Testing zero hail size...")
    try:
        swath = SwathGenerator.create_circular_swath(32.7767, -96.7970, 0.0)
        if swath and swath['properties']['radius_miles'] >= 2.0:
            print("   [OK] Handled: Applied minimum radius")
            passed += 1
        else:
            edge_cases.append("Zero hail size not handled properly")
            print("   [WARN] Issue: No minimum radius enforcement")
    except Exception as e:
        edge_cases.append(f"Zero hail size crashed: {e}")
        print(f"   [FAIL] CRASHED: {e}")

    # ========================================================================
    # EDGE CASE 2: Negative hail size
    # ========================================================================

    total += 1
    print("[2/10] Testing negative hail size...")
    try:
        swath = SwathGenerator.create_circular_swath(32.7767, -96.7970, -1.5)
        # If we get here, it accepted negative (may or may not be ok depending on design)
        if swath and swath['properties']['radius_miles'] > 0:
            # It handled it by taking absolute or applying minimum
            print(f"   [OK] Handled: radius = {swath['properties']['radius_miles']:.1f} mi")
            passed += 1
        else:
            edge_cases.append("Negative hail size not handled")
            print("   [WARN] Issue: Accepted negative value without handling")
    except ValueError as e:
        print(f"   [OK] Correctly rejected: {e}")
        passed += 1
    except Exception as e:
        edge_cases.append(f"Negative hail crashed: {e}")
        print(f"   [FAIL] CRASHED: {e}")

    # ========================================================================
    # EDGE CASE 3: Extreme hail size
    # ========================================================================

    total += 1
    print("[3/10] Testing extreme hail size (10 inches)...")
    try:
        swath = SwathGenerator.create_circular_swath(32.7767, -96.7970, 10.0)
        if swath:
            radius = swath['properties']['radius_miles']
            if radius > 100:
                edge_cases.append("Extreme hail creates unrealistic swath")
                print(f"   [WARN] Issue: {radius} mile radius (too large)")
            else:
                print(f"   [OK] Handled: {radius:.1f} mile radius")
                passed += 1
    except Exception as e:
        edge_cases.append(f"Extreme hail crashed: {e}")
        print(f"   [FAIL] CRASHED: {e}")

    # ========================================================================
    # EDGE CASE 4: Invalid coordinates (North Pole)
    # ========================================================================

    total += 1
    print("[4/10] Testing extreme latitude (North Pole)...")
    try:
        swath = SwathGenerator.create_circular_swath(89.9, 0.0, 1.5)
        if swath:
            print("   [OK] Handled extreme latitude")
            passed += 1
        else:
            edge_cases.append("Null swath at North Pole")
    except Exception as e:
        edge_cases.append(f"Extreme latitude crashed: {e}")
        print(f"   [FAIL] CRASHED: {e}")

    # ========================================================================
    # EDGE CASE 5: Single detection for composite
    # ========================================================================

    total += 1
    print("[5/10] Testing composite swath with single detection...")
    try:
        detections = [HailDetection(32.7767, -96.7970, 1.5, "2024-11-15T14:30:00")]
        swath = SwathGenerator.create_composite_swath(detections)
        if swath:
            print("   [OK] Handled: Fell back to circular")
            passed += 1
        else:
            edge_cases.append("Single detection returns None")
    except Exception as e:
        edge_cases.append(f"Single detection crashed: {e}")
        print(f"   [FAIL] CRASHED: {e}")

    # ========================================================================
    # EDGE CASE 6: Empty detection list
    # ========================================================================

    total += 1
    print("[6/10] Testing composite swath with no detections...")
    try:
        swath = SwathGenerator.create_composite_swath([])
        if swath is None:
            print("   [OK] Correctly returns None for empty list")
            passed += 1
        else:
            edge_cases.append("Empty list creates swath (should be None)")
    except Exception as e:
        edge_cases.append(f"Empty list crashed: {e}")
        print(f"   [FAIL] CRASHED: {e}")

    # ========================================================================
    # EDGE CASE 7: Zero storm speed (stationary)
    # ========================================================================

    total += 1
    print("[7/10] Testing elliptical swath with zero speed...")
    try:
        swath = SwathGenerator.create_elliptical_swath(
            32.7767, -96.7970, 1.5, 45, 0, 30  # 0 mph
        )
        if swath:
            path_length = swath['properties']['path_length_miles']
            print(f"   [OK] Handled: {path_length:.1f} mile path")
            passed += 1
    except Exception as e:
        edge_cases.append(f"Zero speed crashed: {e}")
        print(f"   [FAIL] CRASHED: {e}")

    # ========================================================================
    # EDGE CASE 8: Very long duration
    # ========================================================================

    total += 1
    print("[8/10] Testing elliptical swath with 10 hour duration...")
    try:
        swath = SwathGenerator.create_elliptical_swath(
            32.7767, -96.7970, 1.5, 45, 50, 600  # 10 hours
        )
        if swath:
            path_length = swath['properties']['path_length_miles']
            if path_length > 1000:
                edge_cases.append(f"Unrealistic path length: {path_length} miles")
                print(f"   [WARN] Issue: {path_length:.0f} mile path (too long)")
            else:
                print(f"   [OK] Handled: {path_length:.1f} mile path")
                passed += 1
    except Exception as e:
        edge_cases.append(f"Long duration crashed: {e}")
        print(f"   [FAIL] CRASHED: {e}")

    # ========================================================================
    # EDGE CASE 9: Collinear detections
    # ========================================================================

    total += 1
    print("[9/10] Testing composite with collinear detections...")
    try:
        detections = [
            HailDetection(32.70, -96.80, 1.5, "2024-11-15T14:30:00"),
            HailDetection(32.75, -96.75, 1.5, "2024-11-15T14:35:00"),
            HailDetection(32.80, -96.70, 1.5, "2024-11-15T14:40:00")
        ]
        swath = SwathGenerator.create_composite_swath(detections)
        if swath:
            print("   [OK] Handled collinear points")
            passed += 1
        else:
            edge_cases.append("Collinear points failed")
    except Exception as e:
        edge_cases.append(f"Collinear crashed: {e}")
        print(f"   [FAIL] CRASHED: {e}")

    # ========================================================================
    # EDGE CASE 10: Duplicate detections (same location)
    # ========================================================================

    total += 1
    print("[10/10] Testing duplicate detections...")
    try:
        detections = [
            HailDetection(32.7767, -96.7970, 1.5, "2024-11-15T14:30:00"),
            HailDetection(32.7767, -96.7970, 1.5, "2024-11-15T14:30:00"),
            HailDetection(32.7767, -96.7970, 1.5, "2024-11-15T14:30:00")
        ]
        swath = SwathGenerator.create_composite_swath(detections)
        if swath:
            print("   [OK] Handled duplicates")
            passed += 1
        else:
            edge_cases.append("Duplicates failed")
    except Exception as e:
        edge_cases.append(f"Duplicates crashed: {e}")
        print(f"   [FAIL] CRASHED: {e}")

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("\n" + "="*80)
    print("EDGE CASE SUMMARY")
    print("="*80 + "\n")

    print(f"Passed: {passed}/{total} ({passed/total*100:.0f}%)")
    print()

    if edge_cases:
        print(f"Found {len(edge_cases)} edge case issues:\n")
        for i, issue in enumerate(edge_cases, 1):
            print(f"{i}. {issue}")
        print()
        print("RECOMMENDATIONS:")
        print("  -> Add input validation for hail size")
        print("  -> Add bounds checking for coordinates")
        print("  -> Add duration/speed limits for elliptical swaths")
        print("  -> Handle degenerate cases (collinear, duplicates)")
    else:
        print("[OK] All edge cases handled properly!")

    print()
    return len(edge_cases) == 0


if __name__ == '__main__':
    success = test_edge_cases()
    sys.exit(0 if success else 1)
