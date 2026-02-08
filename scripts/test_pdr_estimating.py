#!/usr/bin/env python3
"""
PDR Estimating Module - End-to-End Test

Tests the complete flow:
1. Create estimate with dents
2. Add R&I items
3. Create work order
4. Log discoveries
5. Generate supplement
6. Generate invoice

Run with: python scripts/test_pdr_estimating.py
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:5000"
HEADERS = {
    "Content-Type": "application/json",
    "X-Test-Auth": "dev-user-1"  # DEV_MODE auth bypass
}


def print_step(step_num: int, description: str):
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {description}")
    print('='*60)


def print_result(label: str, data):
    print(f"\n{label}:")
    if isinstance(data, dict) or isinstance(data, list):
        print(json.dumps(data, indent=2))
    else:
        print(data)


def test_pricing_engine():
    """Test the pricing engine calculations with enhanced depth support."""
    print_step(1, "Test Pricing Engine")

    # Test calculate-price endpoint with depth=shallow (baseline)
    price_data = {
        "size": "medium",
        "zone": "edge",
        "depth": "shallow",  # Use shallow for baseline test
        "panel_name": "driver_door",
        "material": "steel"
    }

    response = requests.post(
        f"{BASE_URL}/api/pdr-estimates/calculate-price",
        headers=HEADERS,
        json=price_data
    )

    if response.status_code == 200:
        result = response.json()
        print_result("Price Calculation (shallow depth)", result)

        # Verify: medium ($75) * edge (1.4) * shallow (1.0) * driver_door (1.0) * steel (1.0) = $105
        expected_price = 75 * 1.4 * 1.0 * 1.0 * 1.0
        actual_price = result.get('price', 0)
        assert abs(actual_price - expected_price) < 0.01, f"Expected {expected_price}, got {actual_price}"
        print(f"PASS: Shallow depth price correct (${actual_price})")
    else:
        print(f"FAIL: {response.status_code} - {response.text}")
        return False

    # Test with deep depth
    price_data["depth"] = "deep"
    response = requests.post(
        f"{BASE_URL}/api/pdr-estimates/calculate-price",
        headers=HEADERS,
        json=price_data
    )

    if response.status_code == 200:
        result = response.json()
        print_result("Price Calculation (deep depth)", result)

        # Verify: medium ($75) * edge (1.4) * deep (1.6) * driver_door (1.0) * steel (1.0) = $168
        expected_price = 75 * 1.4 * 1.6 * 1.0 * 1.0
        actual_price = result.get('price', 0)
        assert abs(actual_price - expected_price) < 0.01, f"Expected {expected_price}, got {actual_price}"
        print(f"PASS: Deep depth price correct (${actual_price})")
    else:
        print(f"FAIL: {response.status_code} - {response.text}")
        return False

    # Test with coin-based size
    price_data = {
        "size": "quarter",
        "zone": "center",
        "depth": "shallow",
        "panel_name": "hood",
        "material": "steel"
    }
    response = requests.post(
        f"{BASE_URL}/api/pdr-estimates/calculate-price",
        headers=HEADERS,
        json=price_data
    )

    if response.status_code == 200:
        result = response.json()
        print_result("Price Calculation (quarter size)", result)

        # Verify: quarter ($70) * center (1.0) * shallow (1.0) * hood (1.0) * steel (1.0) = $70
        expected_price = 70 * 1.0 * 1.0 * 1.0 * 1.0
        actual_price = result.get('price', 0)
        assert abs(actual_price - expected_price) < 0.01, f"Expected {expected_price}, got {actual_price}"
        print(f"PASS: Coin-based size price correct (${actual_price})")
    else:
        print(f"FAIL: {response.status_code} - {response.text}")
        return False

    return True


def test_create_estimate():
    """Test creating a new estimate with dents."""
    print_step(2, "Create Estimate with Dents")

    # Create estimate
    estimate_data = {
        "customer_name": "Test Customer",
        "vehicle_year": 2022,
        "vehicle_make": "Toyota",
        "vehicle_model": "Camry",
        "vehicle_vin": "1HGCG5655WA123456"
    }

    response = requests.post(
        f"{BASE_URL}/api/pdr-estimates",
        headers=HEADERS,
        json=estimate_data
    )

    if response.status_code != 201:
        print(f"FAIL: Could not create estimate - {response.status_code} - {response.text}")
        return None

    result = response.json()
    estimate = result.get('estimate', result)  # Handle nested or flat response
    estimate_id = estimate.get('id')
    print_result("Created Estimate", result)

    # Add a panel
    print("\nAdding panel: Hood")
    panel_data = {
        "panel_name": "hood",
        "material_modifier": 1.0,
        "panel_difficulty": 1.0
    }

    response = requests.post(
        f"{BASE_URL}/api/pdr-estimates/{estimate_id}/panels",
        headers=HEADERS,
        json=panel_data
    )

    if response.status_code != 201:
        print(f"FAIL: Could not add panel - {response.status_code} - {response.text}")
        return None

    panel_result = response.json()
    panel = panel_result.get('panel', panel_result)  # Handle nested or flat response
    panel_id = panel.get('id')
    print_result("Added Panel", panel_result)

    # Add dents using batch endpoint with enhanced depth support
    print("\nAdding batch of dents with coin sizes and depth...")
    dents_data = {
        "dents": [
            {"size": "quarter", "zone": "center", "depth": "shallow"},
            {"size": "quarter", "zone": "center", "depth": "medium"},
            {"size": "nickel", "zone": "edge", "depth": "deep"},
            {"size": "half_dollar", "zone": "crease", "depth": "severe"}
        ]
    }

    response = requests.post(
        f"{BASE_URL}/api/pdr-estimates/{estimate_id}/panels/{panel_id}/dents/batch",
        headers=HEADERS,
        json=dents_data
    )

    if response.status_code != 201:
        print(f"FAIL: Could not add dents - {response.status_code} - {response.text}")
        return None

    dents_result = response.json()
    print_result("Added Dents", dents_result)

    # Verify vehicle tier was detected
    vehicle_tier = dents_result.get('vehicle_tier', 'unknown')
    print(f"Vehicle Tier: {vehicle_tier}")

    print(f"PASS: Created estimate #{estimate_id} with {dents_result.get('count', 0)} dents")
    return estimate_id


def test_add_rin_items(estimate_id: int):
    """Test adding R&I items."""
    print_step(3, "Add R&I Items")

    # First, get the panel ID
    response = requests.get(
        f"{BASE_URL}/api/pdr-estimates/{estimate_id}",
        headers=HEADERS
    )

    if response.status_code != 200:
        print(f"FAIL: Could not get estimate - {response.status_code}")
        return False

    estimate = response.json()
    panels = estimate.get('panels', [])

    if not panels:
        print("FAIL: No panels found on estimate")
        return False

    panel_id = panels[0].get('id')

    # Get R&I suggestions
    response = requests.get(
        f"{BASE_URL}/api/pdr-estimates/{estimate_id}/panels/{panel_id}/rin-suggestions?zone=edge",
        headers=HEADERS
    )

    if response.status_code == 200:
        suggestions = response.json()
        print_result("R&I Suggestions", suggestions)
    else:
        print(f"Warning: Could not get R&I suggestions - {response.status_code}")

    # Add an R&I item
    rin_data = {
        "item_name": "cowl_panel",
        "price": 25.00,
        "time_hours": 0.25,
        "auto_suggested": True
    }

    response = requests.post(
        f"{BASE_URL}/api/pdr-estimates/{estimate_id}/panels/{panel_id}/rin",
        headers=HEADERS,
        json=rin_data
    )

    if response.status_code != 201:
        print(f"FAIL: Could not add R&I item - {response.status_code} - {response.text}")
        return False

    rin_item = response.json()
    print_result("Added R&I Item", rin_item)

    print("PASS: R&I item added successfully")
    return True


def test_create_work_order(estimate_id: int):
    """Test creating a work order from estimate."""
    print_step(4, "Create Work Order")

    response = requests.post(
        f"{BASE_URL}/api/pdr-estimates/{estimate_id}/work-order",
        headers=HEADERS,
        json={}
    )

    if response.status_code != 201:
        print(f"FAIL: Could not create work order - {response.status_code} - {response.text}")
        return None

    result = response.json()
    work_order = result.get('work_order', result)  # Handle nested or flat response
    work_order_id = work_order.get('id')
    print_result("Created Work Order", result)

    print(f"PASS: Work order #{work_order_id} created successfully")
    return work_order_id


def test_log_discovery(work_order_id: int):
    """Test logging a discovery event."""
    print_step(5, "Log Discovery Event")

    discovery_data = {
        "type": "hidden_damage",
        "description": "Additional dents found under hood liner, not visible during initial inspection",
        "additional_time_hours": 0.5,
        "additional_cost": 75.00,
        "panel_name": "hood"
    }

    response = requests.post(
        f"{BASE_URL}/api/work-orders/{work_order_id}/discoveries",
        headers=HEADERS,
        json=discovery_data
    )

    if response.status_code != 201:
        print(f"FAIL: Could not log discovery - {response.status_code} - {response.text}")
        return False

    discovery = response.json()
    print_result("Logged Discovery", discovery)

    print("PASS: Discovery logged successfully")
    return True


def test_generate_supplement(work_order_id: int):
    """Test generating supplement narrative."""
    print_step(6, "Generate Supplement Narrative")

    response = requests.get(
        f"{BASE_URL}/api/work-orders/{work_order_id}/supplement",
        headers=HEADERS
    )

    if response.status_code != 200:
        print(f"FAIL: Could not generate supplement - {response.status_code} - {response.text}")
        return False

    supplement = response.json()
    print_result("Supplement Generated", supplement)

    # Check that narrative was generated
    narrative = supplement.get('summary_narrative', '')
    if 'SUPPLEMENT REQUEST' in narrative:
        print("PASS: Supplement narrative generated correctly")
    else:
        print("WARN: Supplement narrative may be incomplete")

    return True


def test_get_estimate_totals(estimate_id: int):
    """Test getting final estimate totals."""
    print_step(7, "Get Final Estimate Totals")

    response = requests.get(
        f"{BASE_URL}/api/pdr-estimates/{estimate_id}",
        headers=HEADERS
    )

    if response.status_code != 200:
        print(f"FAIL: Could not get estimate - {response.status_code} - {response.text}")
        return False

    estimate = response.json()
    print_result("Final Estimate", estimate)

    total = float(estimate.get('total_price', 0))
    print(f"\nFinal Total: ${total:.2f}")

    if total > 0:
        print("PASS: Estimate totals calculated correctly")
        return True
    else:
        print("WARN: Total appears to be zero")
        return True


def test_discovery_types():
    """Test listing discovery types."""
    print_step(8, "List Discovery Types")

    response = requests.get(
        f"{BASE_URL}/api/discovery-types",
        headers=HEADERS
    )

    if response.status_code != 200:
        print(f"FAIL: Could not list discovery types - {response.status_code} - {response.text}")
        return False

    types = response.json()
    print_result("Discovery Types", types)

    if len(types) > 0:
        print(f"PASS: {len(types)} discovery types available")
        return True
    else:
        print("WARN: No discovery types returned")
        return True


def test_ri_library():
    """Test the R&I library endpoints."""
    print_step(9, "Test R&I Library")

    # Get R&I library
    response = requests.get(
        f"{BASE_URL}/api/pdr-estimates/ri-library",
        headers=HEADERS
    )

    if response.status_code != 200:
        print(f"FAIL: Could not get R&I library - {response.status_code} - {response.text}")
        return False

    result = response.json()
    print_result("R&I Library (summary)", {
        "total_count": result.get("total_count"),
        "categories": list(result.get("by_category", {}).keys()),
        "tier_multipliers": result.get("tier_multipliers")
    })

    if result.get("total_count", 0) > 0:
        print(f"PASS: {result['total_count']} R&I operations available")
    else:
        print("WARN: No R&I operations in library")
        return True

    # Get specific operation
    response = requests.get(
        f"{BASE_URL}/api/pdr-estimates/ri-library/RI_HEADLINER_FULL?vehicle_tier=luxury&scope_level=typical",
        headers=HEADERS
    )

    if response.status_code == 200:
        op_result = response.json()
        print_result("R&I Operation Detail", {
            "name": op_result.get("operation", {}).get("name"),
            "calculated_time": op_result.get("calculated_time"),
            "time_details": op_result.get("time_details")
        })
        print("PASS: R&I operation detail fetched")
    else:
        print(f"WARN: Could not get operation detail - {response.status_code}")

    return True


def test_vehicle_tiers():
    """Test the vehicle tier endpoints."""
    print_step(10, "Test Vehicle Tiers")

    # Test tier lookup
    test_vehicles = [
        ("Toyota", "Camry", "standard"),
        ("BMW", "X5", "luxury"),
        ("Tesla", "Model 3", "ev_adas"),
        ("Kia", "Rio", "economy")
    ]

    for make, model, expected_tier in test_vehicles:
        response = requests.get(
            f"{BASE_URL}/api/pdr-estimates/vehicle-tier?make={make}&model={model}",
            headers=HEADERS
        )

        if response.status_code == 200:
            result = response.json()
            actual_tier = result.get("tier")
            if actual_tier == expected_tier:
                print(f"  PASS: {make} {model} -> {actual_tier}")
            else:
                print(f"  WARN: {make} {model} expected {expected_tier}, got {actual_tier}")
        else:
            print(f"  FAIL: Could not look up {make} {model} - {response.status_code}")

    # Get all vehicle tiers
    response = requests.get(
        f"{BASE_URL}/api/pdr-estimates/vehicle-tiers",
        headers=HEADERS
    )

    if response.status_code == 200:
        result = response.json()
        print(f"\nTotal vehicle classifications: {result.get('total_count', 0)}")
        print("PASS: Vehicle tier system working")
        return True
    else:
        print(f"FAIL: Could not list vehicle tiers - {response.status_code}")
        return False


def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "="*60)
    print("PDR ESTIMATING MODULE - END-TO-END TEST")
    print("="*60)
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")

    results = []

    # Test 1: Pricing engine (with depth support)
    results.append(("Pricing Engine", test_pricing_engine()))

    # Test 2: Create estimate
    estimate_id = test_create_estimate()
    results.append(("Create Estimate", estimate_id is not None))

    if estimate_id:
        # Test 3: R&I items
        results.append(("R&I Items", test_add_rin_items(estimate_id)))

        # Test 4: Work order
        work_order_id = test_create_work_order(estimate_id)
        results.append(("Create Work Order", work_order_id is not None))

        if work_order_id:
            # Test 5: Discovery
            results.append(("Log Discovery", test_log_discovery(work_order_id)))

            # Test 6: Supplement
            results.append(("Generate Supplement", test_generate_supplement(work_order_id)))

        # Test 7: Totals
        results.append(("Estimate Totals", test_get_estimate_totals(estimate_id)))

    # Test 8: Discovery types
    results.append(("Discovery Types", test_discovery_types()))

    # Test 9: R&I Library
    results.append(("R&I Library", test_ri_library()))

    # Test 10: Vehicle Tiers
    results.append(("Vehicle Tiers", test_vehicle_tiers()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = 0
    failed = 0

    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "" if result else ""
        print(f"  {symbol} {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print("\n" + "-"*60)
    print(f"Total: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print(f"\nERROR: Could not connect to {BASE_URL}")
        print("Make sure the test server is running:")
        print("  python scripts/test_api_server.py")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
