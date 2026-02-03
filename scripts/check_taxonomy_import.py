#!/usr/bin/env python3
"""
Taxonomy Import Sanity Check
============================
Verifies that category_taxonomy.py exists and normalize_category_key works correctly.
Exit 0 on success, exit 1 on failure.
"""
import sys
import os

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

def main():
    print("=" * 60)
    print("CATEGORY TAXONOMY SANITY CHECK")
    print("=" * 60)

    # Test 1: Import the module
    print("\n1. Testing import...")
    try:
        from src.business.category_taxonomy import (
            normalize_category_key,
            CATEGORY_TAXONOMY,
            CATEGORY_ALIASES,
            detect_category_from_tags,
            estimate_vehicles,
            get_categories_by_tier,
        )
        print("   [OK] All imports successful")
    except ImportError as e:
        print(f"   [FAIL] Import failed: {e}")
        return 1

    # Test 2: Verify key normalization
    print("\n2. Testing normalize_category_key()...")
    test_cases = [
        ('rental_car', 'car_rental'),
        ('service_company', 'service_trades'),
        ('parking', 'parking_structure'),
        ('car_rental', 'car_rental'),           # Already canonical
        ('service_trades', 'service_trades'),   # Already canonical
        ('parking_structure', 'parking_structure'),  # Already canonical
        ('car_dealership', 'car_dealership'),   # No alias needed
    ]

    failures = []
    for input_key, expected in test_cases:
        result = normalize_category_key(input_key)
        status = "OK" if result == expected else "FAIL"
        print(f"   {input_key:20} -> {result:20} (expected: {expected}) [{status}]")
        if result != expected:
            failures.append((input_key, expected, result))

    if failures:
        print(f"\n   [FAIL] {len(failures)} normalization tests failed")
        return 1
    print("   [OK] All normalization tests passed")

    # Test 3: Verify taxonomy structure
    print("\n3. Verifying taxonomy structure...")
    required_fields = ['name', 'tier', 'est_vehicles']
    missing_fields = []

    for key, config in CATEGORY_TAXONOMY.items():
        for field in required_fields:
            if field not in config:
                missing_fields.append((key, field))

    if missing_fields:
        print(f"   [FAIL] Missing required fields:")
        for key, field in missing_fields[:5]:
            print(f"      {key} missing '{field}'")
        return 1

    print(f"   [OK] All {len(CATEGORY_TAXONOMY)} categories have required fields")

    # Test 4: Verify tier distribution
    print("\n4. Verifying tier distribution...")
    tier_counts = {}
    for key, config in CATEGORY_TAXONOMY.items():
        tier = config.get('tier', 0)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    for tier in sorted(tier_counts.keys()):
        cats = list(get_categories_by_tier(tier).keys())
        print(f"   Tier {tier}: {tier_counts[tier]} categories - {cats[:3]}...")

    if not all(t in [1, 2, 3] for t in tier_counts.keys()):
        print("   [WARN] Unexpected tier values found")

    print("   [OK] Tier distribution verified")

    # Test 5: Verify aliases are defined
    print("\n5. Verifying aliases...")
    required_aliases = ['rental_car', 'service_company', 'parking']
    missing_aliases = [a for a in required_aliases if a not in CATEGORY_ALIASES]

    if missing_aliases:
        print(f"   [FAIL] Missing required aliases: {missing_aliases}")
        return 1

    print(f"   [OK] All {len(CATEGORY_ALIASES)} aliases defined")

    print("\n" + "=" * 60)
    print("ALL CHECKS PASSED")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
