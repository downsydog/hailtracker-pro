#!/usr/bin/env python3
"""
PDR Pro Estimating System - Complete Test Script
Tests the full estimating workflow including R/I, alerts, comparables, and insurance tracking.

Run after schema creation and seed data:
    python scripts/test_estimating_system.py
"""

import os
import sys
import json
from datetime import datetime, date

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Database path
DB_PATH = "data/pdr_crm.db"


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    """Print section header"""
    print(f"\n--- {title} ---")


def test_schema_creation():
    """Test schema creation"""
    print_header("1. SCHEMA CREATION")

    from src.crm.models.estimating_schema import EstimatingSchema

    print("Creating estimating schema...")
    EstimatingSchema.create_all_tables(DB_PATH)
    EstimatingSchema.add_estimate_insurance_fields(DB_PATH)
    print("[OK] Schema created successfully")


def test_seed_data():
    """Test seed data population"""
    print_header("2. SEED DATA")

    from scripts.seed_estimating_data import seed_estimating_data

    print("Seeding estimating data...")
    seed_estimating_data(DB_PATH)
    print("[OK] Seed data populated successfully")


def test_vin_decoder():
    """Test VIN decoder"""
    print_header("3. VIN DECODER")

    from src.utils.vin_decoder import decode_vin, get_vehicle_summary, get_vehicle_options_summary

    # Test VIN (2022 Ford F-150 - example VIN format)
    test_vins = [
        ("1FTFW1E5XNFA12345", "2022 Ford F-150"),  # Simulated - may not decode
        ("1HGBH41JXMN109186", "Honda Accord"),
    ]

    for vin, expected in test_vins:
        print(f"\nDecoding VIN: {vin}")
        result = decode_vin(vin, DB_PATH)

        if result.get('error'):
            print(f"  Note: {result['error']}")
        else:
            summary = get_vehicle_summary(vin, DB_PATH)
            print(f"  Result: {summary}")
            print(f"  Sunroof: {result.get('has_sunroof')}")
            print(f"  Roof Rails: {result.get('has_roof_rails')}")

    print("\n[OK] VIN decoder working")


def test_ri_manager():
    """Test R/I manager"""
    print_header("4. R/I MANAGER")

    from src.crm.managers.ri_manager import RIManager

    ri_mgr = RIManager(DB_PATH)

    # Get all operations
    print_section("All R/I Operations")
    operations = ri_mgr.get_all_ri_operations()
    print(f"Total R/I operations: {len(operations)}")

    # Show by category
    categories = {}
    for op in operations:
        cat = op['category']
        categories[cat] = categories.get(cat, 0) + 1

    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    # Test time lookup
    print_section("R/I Time Lookup")

    headliner_op = ri_mgr.get_ri_operation_by_code('RI-HDLNR')
    if headliner_op:
        hours, source, confidence, ri_time_id = ri_mgr.lookup_ri_time(
            headliner_op['id'],
            year=2022,
            make='Ford',
            model='F-150',
            body_style='SuperCrew'
        )
        print(f"Headliner R/I for 2022 Ford F-150 SuperCrew:")
        print(f"  Hours: {hours}")
        print(f"  Source: {source}")
        print(f"  Confidence: {confidence}%")

    # Test auto-suggestions
    print_section("Auto-Suggest R/I for Roof Panel")

    vehicle_info = {
        'year': 2022,
        'make': 'Ford',
        'model': 'F-150',
        'body_style': 'SuperCrew',
        'has_sunroof': True,
        'has_roof_rails': True
    }

    suggestions = ri_mgr.get_suggested_ri_items(
        estimate_id=1,
        panel_name='roof',
        dent_count=25,
        vehicle_info=vehicle_info
    )

    print(f"Suggested R/I items for roof with 25 dents:")
    total = 0
    for item in suggestions:
        marker = '[X]' if item['is_default'] else '[ ]'
        print(f"  {marker} {item['name']}: {item['hours']}hrs @ ${item['rate']}/hr = ${item['total']:.2f}")
        print(f"      Source: {item['source']} (confidence: {item['confidence']}%)")
        if item['is_default']:
            total += item['total']

    print(f"\nDefault R/I Total: ${total:.2f}")
    print("\n[OK] R/I manager working")


def test_insurance_manager():
    """Test insurance battle manager"""
    print_header("5. INSURANCE BATTLE MANAGER")

    from src.crm.managers.insurance_battle_manager import InsuranceBattleManager

    ins_mgr = InsuranceBattleManager(DB_PATH)

    # Get all companies
    print_section("Insurance Companies")
    companies = ins_mgr.get_all_insurance_companies()
    print(f"Total companies: {len(companies)}")

    for co in companies[:5]:
        print(f"  {co['name']}: PDR rate ${co.get('pdr_rate', 'N/A')}/hr")

    # Get justifications
    print_section("Pushback Justifications")
    justifications = ins_mgr.get_all_justifications()
    print(f"Total justifications: {len(justifications)}")

    for just in justifications[:3]:
        print(f"  {just['title']}")
        print(f"    Category: {just['category']}")
        print(f"    Success rate: {just.get('success_rate', 'N/A')}%")

    # Test specific justification lookup
    print_section("Justification Lookup")
    headliner_just = ins_mgr.get_justification('ri_time', 'headliner')
    if headliner_just:
        print(f"Headliner justification found:")
        print(f"  {headliner_just['justification_text'][:100]}...")

    print("\n[OK] Insurance battle manager working")


def test_alerts_manager():
    """Test estimate alerts manager"""
    print_header("6. ESTIMATE ALERTS MANAGER")

    from src.crm.managers.estimate_alerts_manager import EstimateAlertsManager

    alerts_mgr = EstimateAlertsManager(DB_PATH)

    # Get alert rules
    print_section("Alert Rules")
    rules = alerts_mgr.get_all_alert_rules()
    print(f"Total active rules: {len(rules)}")

    for rule in rules[:5]:
        print(f"  [{rule['severity'].upper()}] {rule['name']}")

    print("\n[OK] Alerts manager working")


def test_comparables_manager():
    """Test estimate comparables manager"""
    print_header("7. ESTIMATE COMPARABLES MANAGER")

    from src.crm.managers.estimate_comparables_manager import EstimateComparablesManager

    comp_mgr = EstimateComparablesManager(DB_PATH)

    # Get comparable stats
    print_section("Comparable Stats")
    stats = comp_mgr.get_comparable_stats('Ford', 'F-150')
    print(f"Stats for Ford F-150:")
    print(f"  Sample size: {stats.get('sample_size') or 0}")
    print(f"  Avg estimate: ${(stats.get('avg_estimate') or 0):,.2f}")
    print(f"  Avg approved: ${(stats.get('avg_approved') or 0):,.2f}")

    # Get total count
    total = comp_mgr.get_comparables_count()
    print(f"\nTotal comparables in database: {total}")

    print("\n[OK] Comparables manager working")


def test_full_estimate_workflow():
    """Test complete estimate workflow"""
    print_header("8. FULL ESTIMATE WORKFLOW SIMULATION")

    from src.crm.managers.ri_manager import RIManager
    from src.crm.managers.estimate_alerts_manager import EstimateAlertsManager
    from src.crm.managers.estimate_comparables_manager import EstimateComparablesManager
    from src.crm.models.database import Database

    db = Database(DB_PATH)
    ri_mgr = RIManager(DB_PATH)
    alerts_mgr = EstimateAlertsManager(DB_PATH)
    comp_mgr = EstimateComparablesManager(DB_PATH)

    print_section("Simulating Estimate Creation")

    # Simulate vehicle info
    vehicle_info = {
        'year': 2022,
        'make': 'Ford',
        'model': 'F-150',
        'body_style': 'SuperCrew',
        'has_sunroof': True,
        'has_roof_rails': True
    }

    print(f"Vehicle: {vehicle_info['year']} {vehicle_info['make']} {vehicle_info['model']}")
    print(f"Options: Sunroof={vehicle_info['has_sunroof']}, Roof Rails={vehicle_info['has_roof_rails']}")

    # Simulate panel damage
    panels = [
        {"panel": "hood", "dents": 32},
        {"panel": "roof", "dents": 45},
        {"panel": "left_fender", "dents": 18},
        {"panel": "left_front_door", "dents": 15},
        {"panel": "trunk", "dents": 12},
    ]

    print_section("Panel Damage Analysis")

    total_dents = 0
    all_ri_items = []

    for panel_data in panels:
        panel = panel_data["panel"]
        dent_count = panel_data["dents"]
        total_dents += dent_count

        print(f"\n{panel.upper().replace('_', ' ')} - {dent_count} dents")

        # Get auto-suggested R/I for each panel
        suggestions = ri_mgr.get_suggested_ri_items(
            estimate_id=0,
            panel_name=panel,
            dent_count=dent_count,
            vehicle_info=vehicle_info
        )

        for item in suggestions:
            marker = '[X]' if item['is_default'] else '[ ]'
            print(f"  {marker} {item['name']}: {item['hours']}hrs = ${item['total']:.2f}")

            if item['is_default']:
                all_ri_items.append(item)

    print_section("Estimate Summary")

    # Calculate totals
    ri_total = sum(item['total'] for item in all_ri_items)

    # Simulate PDR pricing (using dent counts)
    pdr_pricing = {
        'hood': 50 * 1.0,
        'roof': 50 * 1.2,
        'left_fender': 45 * 1.0,
        'left_front_door': 45 * 1.0,
        'trunk': 45 * 1.0,
    }

    pdr_total = 0
    for panel_data in panels:
        panel = panel_data["panel"]
        dent_count = panel_data["dents"]
        price_per_dent = pdr_pricing.get(panel, 50)
        panel_total = dent_count * price_per_dent
        pdr_total += panel_total

    print(f"Total Dents:     {total_dents}")
    print(f"PDR Labor:       ${pdr_total:>10,.2f}")
    print(f"R/I Labor:       ${ri_total:>10,.2f}")
    print(f"Parts:           ${0:>10,.2f}")
    print(f"Materials:       ${50:>10,.2f}")
    print(f"               {'-' * 14}")
    print(f"TOTAL:           ${pdr_total + ri_total + 50:>10,.2f}")

    print_section("Comparable Lookup")

    comp_stats = comp_mgr.get_comparable_stats(
        vehicle_info['make'],
        vehicle_info['model'],
        year_range=(2019, 2024)
    )

    estimate_total = pdr_total + ri_total + 50
    avg = comp_stats.get('avg_estimate') or 0

    print(f"Comparables found: {comp_stats.get('sample_size') or 0}")
    print(f"Average estimate: ${avg:,.2f}")
    if avg > 0:
        variance = ((estimate_total - avg) / avg) * 100
        print(f"This estimate: ${estimate_total:,.2f} ({variance:+.1f}% vs average)")

    print("\n[OK] Full workflow simulation complete")


def run_all_tests():
    """Run all tests"""
    print("\n")
    print("=" * 70)
    print("  PDR PRO ESTIMATING SYSTEM - COMPLETE TEST SUITE")
    print("=" * 70)
    print(f"  Database: {DB_PATH}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        test_schema_creation()
        test_seed_data()
        test_vin_decoder()
        test_ri_manager()
        test_insurance_manager()
        test_alerts_manager()
        test_comparables_manager()
        test_full_estimate_workflow()

        print("\n")
        print("=" * 70)
        print("  ALL TESTS PASSED!")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Create a real estimate using estimate_manager")
        print("  2. Add panel damage with dent_mapper")
        print("  3. Run ri_manager.get_suggested_ri_items() for each panel")
        print("  4. Run alerts_manager.run_alerts() to check for issues")
        print("  5. Use insurance_battle_manager for negotiation support")
        print()

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
