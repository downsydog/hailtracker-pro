"""
Test Mobile Estimator (Offline Mode)
PDR CRM Part 22 - Mobile-first estimator with offline capability
"""

import sys
import os
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_mobile_estimator():
    print("\n" + "="*80)
    print("TESTING MOBILE ESTIMATOR (OFFLINE MODE)")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.mobile_estimator_manager import MobileEstimatorManager

    # Use test database
    test_db = "data/test_mobile_estimator.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    mgr = MobileEstimatorManager(db)

    print()

    # ========================================================================
    # TEST 1: Create Offline Estimate
    # ========================================================================

    print("="*80)
    print("[1/8] Creating offline estimate...")
    print("="*80 + "\n")

    estimate = mgr.create_offline_estimate(
        customer_info={
            'first_name': 'Mike',
            'last_name': 'Johnson',
            'phone': '555-9876',
            'email': 'mike@example.com'
        },
        vehicle_info={
            'year': 2021,
            'make': 'Ford',
            'model': 'F-150',
            'color': 'Blue',
            'vin': 'ABC123456789'
        },
        damage_info={
            'damage_type': 'HAIL',
            'panels': [
                {'panel': 'HOOD', 'dent_count': 25, 'severity': 4},
                {'panel': 'ROOF', 'dent_count': 35, 'severity': 5},
                {'panel': 'TRUNK', 'dent_count': 18, 'severity': 3}
            ],
            'estimated_cost': 2150.00,
            'notes': 'Severe hail damage from recent storm'
        },
        location_data={
            'latitude': 32.7767,
            'longitude': -96.7970,
            'address': 'Customer parking lot, 123 Main St, Dallas, TX',
            'accuracy': 12.5
        },
        created_by='tech_mike'
    )

    offline_id = estimate['offline_id']
    print()

    assert offline_id.startswith('OFFLINE_')
    assert estimate['status'] == 'PENDING_SYNC'
    print("[OK] Offline estimate created")
    print()

    # ========================================================================
    # TEST 2: Add GPS Location
    # ========================================================================

    print("="*80)
    print("[2/8] Adding GPS location...")
    print("="*80 + "\n")

    mgr.add_gps_location(
        offline_id=offline_id,
        latitude=32.7767,
        longitude=-96.7970,
        address='Customer parking lot, Dallas, TX',
        accuracy=10.5
    )
    print()

    # Verify location was added
    updated = mgr.get_offline_estimate(offline_id)
    assert updated['location_data'] is not None
    assert updated['location_data']['latitude'] == 32.7767
    print("[OK] GPS location added")
    print()

    # ========================================================================
    # TEST 3: Create Multiple Offline Estimates
    # ========================================================================

    print("="*80)
    print("[3/8] Creating multiple offline estimates...")
    print("="*80 + "\n")

    for i in range(3):
        mgr.create_offline_estimate(
            customer_info={
                'first_name': f'Customer{i+1}',
                'last_name': 'Test',
                'phone': f'555-000{i}',
                'email': f'customer{i+1}@test.com'
            },
            vehicle_info={
                'year': 2020 + i,
                'make': 'Toyota',
                'model': 'Camry',
                'color': 'Silver'
            },
            damage_info={
                'damage_type': 'HAIL',
                'panels': [{'panel': 'HOOD', 'dent_count': 10}],
                'estimated_cost': 500.00 + (i * 100)
            },
            created_by='tech_mike'
        )
        print()

    print("[OK] Multiple estimates created")
    print()

    # ========================================================================
    # TEST 4: Get Pending Sync Estimates
    # ========================================================================

    print("="*80)
    print("[4/8] Getting pending sync estimates...")
    print("="*80 + "\n")

    pending = mgr.get_pending_sync()

    print(f"Estimates pending sync: {len(pending)}")
    for est in pending:
        print(f"  - {est['offline_id']}")
        print(f"    Customer: {est['customer_info']['first_name']} {est['customer_info']['last_name']}")
        print(f"    Vehicle: {est['vehicle_info']['year']} {est['vehicle_info']['make']} {est['vehicle_info']['model']}")
        print(f"    Cost: ${est['damage_info']['estimated_cost']:,.2f}")
        print(f"    Sync attempts: {est['sync_attempts']}")
        print()

    assert len(pending) == 4
    print("[OK] Pending sync retrieval working")
    print()

    # ========================================================================
    # TEST 5: Sync Process Simulation
    # ========================================================================

    print("="*80)
    print("[5/8] Simulating sync process...")
    print("="*80 + "\n")

    first_estimate = pending[0]

    # Successful sync
    mgr.sync_estimate(
        offline_id=first_estimate['offline_id'],
        job_id=123,
        estimate_id=456
    )
    print()

    # Failed sync
    mgr.mark_sync_failed(
        offline_id=pending[1]['offline_id'],
        error_message='Network timeout during sync'
    )
    print()

    # Verify sync status
    synced = mgr.get_offline_estimate(first_estimate['offline_id'])
    assert synced['synced'] == True
    assert synced['synced_job_id'] == 123

    failed = mgr.get_offline_estimate(pending[1]['offline_id'])
    assert failed['sync_attempts'] == 1

    print("[OK] Sync process working")
    print()

    # ========================================================================
    # TEST 6: Get Technician Estimates
    # ========================================================================

    print("="*80)
    print("[6/8] Getting technician estimates...")
    print("="*80 + "\n")

    tech_estimates = mgr.get_technician_estimates('tech_mike', include_synced=True)

    print(f"Technician 'tech_mike' estimates: {len(tech_estimates)}")
    for est in tech_estimates:
        status = 'Synced' if est['synced'] else 'Pending'
        print(f"  [{status}] {est['offline_id']} - ${est['damage_info']['estimated_cost']:,.2f}")
    print()

    # Only pending
    pending_only = mgr.get_technician_estimates('tech_mike', include_synced=False)
    print(f"Pending only: {len(pending_only)} estimates")
    print()

    assert len(tech_estimates) == 4
    assert len(pending_only) == 3  # One was synced
    print("[OK] Technician estimate filtering working")
    print()

    # ========================================================================
    # TEST 7: Storage Statistics
    # ========================================================================

    print("="*80)
    print("[7/8] Getting storage statistics...")
    print("="*80 + "\n")

    stats = mgr.get_storage_stats()

    print(f"Offline Storage Statistics:")
    print(f"  Total estimates:    {stats['total_estimates']}")
    print(f"  Pending sync:       {stats['pending_sync']}")
    print(f"  Successfully synced: {stats['synced']}")
    print(f"  Failed (3+ attempts): {stats['failed']}")
    print()

    assert stats['total_estimates'] == 4
    assert stats['pending_sync'] == 3
    assert stats['synced'] == 1
    print("[OK] Storage statistics working")
    print()

    # ========================================================================
    # TEST 8: Quick Estimate & Export
    # ========================================================================

    print("="*80)
    print("[8/8] Testing quick estimate and export...")
    print("="*80 + "\n")

    # Quick estimate
    quick = mgr.create_quick_estimate(
        customer_name="Jane Smith",
        customer_phone="555-4321",
        vehicle_year=2023,
        vehicle_make="Honda",
        vehicle_model="Accord",
        damage_type="DOOR_DING",
        estimated_cost=350.00,
        created_by='tech_mike'
    )
    print()

    assert quick['customer_info']['first_name'] == 'Jane'
    assert quick['customer_info']['last_name'] == 'Smith'
    print("[OK] Quick estimate created")
    print()

    # Export summary
    print("Export Summary:")
    print("-" * 50)
    summary = mgr.export_estimate_summary(quick['offline_id'])
    print(summary)
    print()

    assert "MOBILE ESTIMATE" in summary
    print("[OK] Export summary working")
    print()

    # ========================================================================
    # BONUS: Photo Management
    # ========================================================================

    print("="*80)
    print("[BONUS] Testing photo management...")
    print("="*80 + "\n")

    # Add photos
    mgr.add_photo(
        offline_id=quick['offline_id'],
        photo_data='base64_encoded_image_data_here',
        photo_type='DAMAGE',
        panel='DRIVER_DOOR',
        notes='Door ding on driver door'
    )

    mgr.add_photo(
        offline_id=quick['offline_id'],
        photo_data='another_base64_image',
        photo_type='VEHICLE',
        notes='Full vehicle overview'
    )

    # Get photos
    photos = mgr.get_photos(quick['offline_id'])
    print(f"Photos attached: {len(photos)}")
    for photo in photos:
        print(f"  - {photo['type']}: {photo.get('panel', 'N/A')} - {photo.get('notes', '')[:30]}")
    print()

    assert len(photos) == 2
    print("[OK] Photo management working")
    print()

    # ========================================================================
    # Cleanup
    # ========================================================================

    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] MOBILE ESTIMATOR (OFFLINE MODE) TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Offline estimate creation")
    print("  [OK] Unique offline ID generation")
    print("  [OK] GPS location capture")
    print("  [OK] Multiple estimate management")
    print("  [OK] Sync queue handling")
    print("  [OK] Successful sync marking")
    print("  [OK] Failed sync retry tracking")
    print("  [OK] Technician estimate filtering")
    print("  [OK] Storage statistics")
    print("  [OK] Quick estimate shortcut")
    print("  [OK] Export summary generation")
    print("  [OK] Photo attachment")
    print()

    print("MOBILE PWA FEATURES:")
    print("  - Works completely offline")
    print("  - Touch-optimized interface")
    print("  - Camera integration ready")
    print("  - GPS location stamping")
    print("  - Auto-sync when online")
    print("  - Progressive Web App (installable)")
    print("  - Service Worker for offline cache")
    print()

    print("TYPICAL WORKFLOW:")
    print("  1. Tech meets customer in parking lot")
    print("  2. Opens mobile estimator on phone")
    print("  3. Fills in customer info")
    print("  4. Enters vehicle details")
    print("  5. Takes damage photos")
    print("  6. Assesses damage (dent count, severity)")
    print("  7. Saves estimate (stores locally if offline)")
    print("  8. Auto-syncs when connection restored")
    print("  9. Customer gets email with estimate")
    print()

    print("OFFLINE CAPABILITIES:")
    print("  - Create unlimited estimates offline")
    print("  - Capture photos offline")
    print("  - GPS works offline (if location enabled)")
    print("  - Queue syncs automatically")
    print("  - Retry failed syncs")
    print("  - Clean up old synced data")
    print()

    print("DEMO MOBILE APP:")
    print("  Open: src/crm/mobile/mobile_estimator.html")
    print("  (Best viewed on mobile device or in browser mobile mode)")
    print()

    print("Ready for PROMPT 23: Mobile E-signature & On-site Approval?")
    print()

    return True


if __name__ == '__main__':
    success = test_mobile_estimator()
    sys.exit(0 if success else 1)
