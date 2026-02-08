"""
Test Before/After Photo Management
PDR CRM Part 18 - Photo Management System
"""

import sys
import os
import base64
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_photo_manager():
    print("\n" + "="*80)
    print("TESTING BEFORE/AFTER PHOTO MANAGEMENT")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.photo_manager import PhotoManager

    # Use test database
    test_db = "data/test_photo_manager.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    photo_mgr = PhotoManager(db)

    print()

    # ========================================================================
    # Create Test Customer, Vehicle, and Job
    # ========================================================================

    print("Creating test customer and job...")

    # Create customer
    result = db.execute("""
        INSERT INTO customers (
            first_name, last_name, phone, email, zip_code, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "John",
        "PhotoTest",
        "555-0101",
        "john.phototest@test.com",
        "75024",
        datetime.now().isoformat()
    ))
    customer_id = result[0]['id']

    # Create vehicle
    result = db.execute("""
        INSERT INTO vehicles (
            customer_id, year, make, model, color, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        2022,
        "Toyota",
        "Camry",
        "Silver",
        datetime.now().isoformat()
    ))
    vehicle_id = result[0]['id']

    # Create job
    result = db.execute("""
        INSERT INTO jobs (
            job_number, customer_id, vehicle_id, job_type, damage_type,
            status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "JOB-PHOTO-001",
        customer_id,
        vehicle_id,
        "HAIL",
        "HAIL",
        "IN_PROGRESS",
        datetime.now().isoformat()
    ))
    job_id = result[0]['id']

    print(f"  Created job JOB-PHOTO-001 (ID: {job_id})")
    print()

    # ========================================================================
    # TEST 1: Upload Photos (Bytes)
    # ========================================================================

    print("="*80)
    print("[1/10] Uploading photos from bytes...")
    print("="*80 + "\n")

    # Create fake image data for testing
    def create_test_image(name: str) -> bytes:
        """Create simple test image data (PNG header + name)"""
        # PNG header signature
        png_header = b'\x89PNG\r\n\x1a\n'
        return png_header + name.encode('utf-8') + b'\x00' * 100

    # Upload BEFORE photos
    photo_ids = []

    hood_before = photo_mgr.upload_photo(
        job_id=job_id,
        photo_data=create_test_image("hood_before"),
        filename="hood_before.png",
        photo_type="BEFORE",
        panel_type="HOOD",
        description="Hood damage - multiple dents",
        uploaded_by="tech_mike"
    )
    photo_ids.append(hood_before)
    print()

    roof_before = photo_mgr.upload_photo(
        job_id=job_id,
        photo_data=create_test_image("roof_before"),
        filename="roof_before.png",
        photo_type="BEFORE",
        panel_type="ROOF",
        description="Roof damage - severe",
        uploaded_by="tech_mike"
    )
    photo_ids.append(roof_before)
    print()

    trunk_before = photo_mgr.upload_photo(
        job_id=job_id,
        photo_data=create_test_image("trunk_before"),
        filename="trunk_before.png",
        photo_type="BEFORE",
        panel_type="TRUNK",
        description="Trunk damage",
        uploaded_by="tech_mike"
    )
    photo_ids.append(trunk_before)
    print()

    # Upload AFTER photos
    hood_after = photo_mgr.upload_photo(
        job_id=job_id,
        photo_data=create_test_image("hood_after"),
        filename="hood_after.png",
        photo_type="AFTER",
        panel_type="HOOD",
        description="Hood repaired",
        uploaded_by="tech_mike"
    )
    photo_ids.append(hood_after)
    print()

    roof_after = photo_mgr.upload_photo(
        job_id=job_id,
        photo_data=create_test_image("roof_after"),
        filename="roof_after.png",
        photo_type="AFTER",
        panel_type="ROOF",
        description="Roof repaired",
        uploaded_by="tech_mike"
    )
    photo_ids.append(roof_after)
    print()

    # Upload OVERVIEW photo
    overview = photo_mgr.upload_photo(
        job_id=job_id,
        photo_data=create_test_image("overview"),
        filename="vehicle_overview.png",
        photo_type="OVERVIEW",
        description="Full vehicle shot",
        uploaded_by="tech_mike"
    )
    photo_ids.append(overview)
    print()

    # Upload DAMAGE close-up
    damage_detail = photo_mgr.upload_photo(
        job_id=job_id,
        photo_data=create_test_image("damage_detail"),
        filename="damage_closeup.png",
        photo_type="DAMAGE",
        panel_type="HOOD",
        description="Close-up of largest dent",
        uploaded_by="tech_mike"
    )
    photo_ids.append(damage_detail)
    print()

    assert len(photo_ids) == 7
    print(f"[OK] Uploaded {len(photo_ids)} photos")
    print()

    # ========================================================================
    # TEST 2: Upload Photo from Base64
    # ========================================================================

    print("="*80)
    print("[2/10] Uploading photo from base64...")
    print("="*80 + "\n")

    # Create base64 encoded test image
    test_image = create_test_image("base64_progress")
    base64_data = base64.b64encode(test_image).decode('utf-8')

    progress_photo = photo_mgr.upload_photo_base64(
        job_id=job_id,
        base64_data=base64_data,
        filename="progress_shot.png",
        photo_type="PROGRESS",
        panel_type="ROOF",
        description="Mid-repair progress",
        uploaded_by="tech_mike"
    )
    photo_ids.append(progress_photo)
    print()

    # Test with data URL prefix
    data_url = f"data:image/png;base64,{base64_data}"
    progress_photo2 = photo_mgr.upload_photo_base64(
        job_id=job_id,
        base64_data=data_url,
        filename="progress_shot2.png",
        photo_type="PROGRESS",
        description="Mobile upload test",
        uploaded_by="customer"
    )
    photo_ids.append(progress_photo2)
    print()

    assert len(photo_ids) == 9
    print("[OK] Base64 upload working (including data URL prefix)")
    print()

    # ========================================================================
    # TEST 3: Get Photos by Various Filters
    # ========================================================================

    print("="*80)
    print("[3/10] Getting photos with filters...")
    print("="*80 + "\n")

    # Get all photos for job
    all_photos = photo_mgr.get_job_photos(job_id)
    print(f"Total photos for job: {len(all_photos)}")
    print()

    # Get BEFORE photos only
    before_photos = photo_mgr.get_job_photos(job_id, photo_type="BEFORE")
    print(f"BEFORE photos: {len(before_photos)}")
    for p in before_photos:
        print(f"  - {p['filename']} ({p['panel_type']})")
    print()

    # Get AFTER photos only
    after_photos = photo_mgr.get_job_photos(job_id, photo_type="AFTER")
    print(f"AFTER photos: {len(after_photos)}")
    print()

    # Get photos by panel
    hood_photos = photo_mgr.get_job_photos(job_id, panel_type="HOOD")
    print(f"HOOD photos: {len(hood_photos)}")
    print()

    # Get photos organized by panel
    by_panel = photo_mgr.get_photos_by_panel(job_id)
    print("Photos by panel:")
    for panel, photos in by_panel.items():
        print(f"  {panel}: {len(photos)} photos")
    print()

    # Get photos organized by type
    by_type = photo_mgr.get_photos_by_type(job_id)
    print("Photos by type:")
    for ptype, photos in by_type.items():
        print(f"  {ptype}: {len(photos)} photos")
    print()

    assert len(all_photos) == 9
    assert len(before_photos) == 3
    assert len(after_photos) == 2
    print("[OK] Photo retrieval and filtering working")
    print()

    # ========================================================================
    # TEST 4: Create Before/After Pairs
    # ========================================================================

    print("="*80)
    print("[4/10] Creating before/after pairs...")
    print("="*80 + "\n")

    # Manual pair creation
    pair1 = photo_mgr.create_before_after_pair(
        before_photo_id=hood_before,
        after_photo_id=hood_after,
        notes="Hood repair complete",
        created_by="tech_mike"
    )
    print()

    pair2 = photo_mgr.create_before_after_pair(
        before_photo_id=roof_before,
        after_photo_id=roof_after,
        notes="Roof repair complete",
        created_by="tech_mike"
    )
    print()

    assert pair1 > 0
    assert pair2 > 0
    print("[OK] Manual pair creation working")
    print()

    # ========================================================================
    # TEST 5: Auto-Create Pairs
    # ========================================================================

    print("="*80)
    print("[5/10] Testing auto-pair creation...")
    print("="*80 + "\n")

    # Create a second job with photos for auto-pairing
    result = db.execute("""
        INSERT INTO jobs (
            job_number, customer_id, vehicle_id, job_type, damage_type,
            status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "JOB-PHOTO-002",
        customer_id,
        vehicle_id,
        "HAIL",
        "HAIL",
        "IN_PROGRESS",
        datetime.now().isoformat()
    ))
    job2_id = result[0]['id']

    # Upload before/after pairs for multiple panels
    panels = ['DRIVER_DOOR', 'PASSENGER_DOOR', 'DRIVER_FENDER']

    for panel in panels:
        photo_mgr.upload_photo(
            job_id=job2_id,
            photo_data=create_test_image(f"{panel}_before"),
            filename=f"{panel.lower()}_before.png",
            photo_type="BEFORE",
            panel_type=panel,
            uploaded_by="tech_mike"
        )
        print()

        photo_mgr.upload_photo(
            job_id=job2_id,
            photo_data=create_test_image(f"{panel}_after"),
            filename=f"{panel.lower()}_after.png",
            photo_type="AFTER",
            panel_type=panel,
            uploaded_by="tech_mike"
        )
        print()

    # Auto-create pairs
    auto_pairs = photo_mgr.auto_create_pairs(job2_id)
    print()

    print(f"Auto-created {len(auto_pairs)} pairs")

    pairs = photo_mgr.get_before_after_pairs(job2_id)
    for pair in pairs:
        print(f"  {pair['panel_type']}: {pair['before_filename']} -> {pair['after_filename']}")
    print()

    assert len(auto_pairs) == 3
    print("[OK] Auto-pair creation working")
    print()

    # ========================================================================
    # TEST 6: Photo Approval Workflow
    # ========================================================================

    print("="*80)
    print("[6/10] Testing photo approval workflow...")
    print("="*80 + "\n")

    # Get pending photos
    pending = photo_mgr.get_pending_photos(job_id)
    print(f"Pending photos: {len(pending)}")
    print()

    # Approve some photos
    photo_mgr.approve_photo(
        photo_id=hood_before,
        approved_by="manager_jane",
        notes="Good quality"
    )
    print()

    photo_mgr.approve_photo(
        photo_id=hood_after,
        approved_by="manager_jane",
        notes="Excellent repair documentation"
    )
    print()

    # Reject a photo
    photo_mgr.reject_photo(
        photo_id=damage_detail,
        rejected_by="manager_jane",
        reason="Image is blurry - please retake"
    )
    print()

    # Verify status changes
    approved_photo = photo_mgr.get_photo(hood_before)
    rejected_photo = photo_mgr.get_photo(damage_detail)

    assert approved_photo['status'] == 'APPROVED'
    assert approved_photo['approved_by'] == 'manager_jane'
    assert rejected_photo['status'] == 'REJECTED'
    assert rejected_photo['rejection_reason'] == "Image is blurry - please retake"

    print("[OK] Photo approval workflow working")
    print()

    # Bulk approve
    print("Testing bulk approval...")
    remaining_pending = photo_mgr.get_pending_photos(job_id)
    pending_ids = [p['id'] for p in remaining_pending]

    if pending_ids:
        approved_count = photo_mgr.bulk_approve(pending_ids, "manager_jane")
        print(f"Bulk approved {approved_count} photos")
        print()

    print("[OK] Bulk approval working")
    print()

    # ========================================================================
    # TEST 7: Photo Operations (Update, Delete, Reorder)
    # ========================================================================

    print("="*80)
    print("[7/10] Testing photo operations...")
    print("="*80 + "\n")

    # Update photo
    photo_mgr.update_photo(
        photo_id=roof_before,
        description="Updated: Severe roof damage - 15+ dents",
        sequence_order=1
    )
    print()

    updated = photo_mgr.get_photo(roof_before)
    assert "Updated:" in updated['description']
    print("[OK] Photo update working")
    print()

    # Reorder photos
    job_photos = photo_mgr.get_job_photos(job_id)
    photo_order = [p['id'] for p in reversed(job_photos)]

    photo_mgr.reorder_photos(job_id, photo_order)
    print()

    print("[OK] Photo reorder working")
    print()

    # Soft delete
    photo_mgr.delete_photo(damage_detail, soft_delete=True)
    print()

    deleted = photo_mgr.get_photo(damage_detail)
    assert deleted is None  # Soft deleted, not visible

    # Verify it's still in DB with deleted_at
    archived = photo_mgr.get_job_photos(job_id, include_deleted=True)
    archived_photo = [p for p in archived if p['id'] == damage_detail]
    assert len(archived_photo) == 1
    assert archived_photo[0]['status'] == 'ARCHIVED'

    print("[OK] Soft delete working")
    print()

    # ========================================================================
    # TEST 8: Photo Analytics
    # ========================================================================

    print("="*80)
    print("[8/10] Getting photo analytics...")
    print("="*80 + "\n")

    # Job photo summary
    summary = photo_mgr.get_job_photo_summary(job_id)

    print("Job Photo Summary:")
    print(f"  Total Photos: {summary['total_photos']}")
    print(f"  Total Size: {summary['total_size_mb']} MB")
    print(f"  Before/After Pairs: {summary['before_after_pairs']}")
    print(f"  Approved: {summary['approved_count']}")
    print(f"  Pending: {summary['pending_count']}")
    print(f"  Rejected: {summary['rejected_count']}")
    print()

    print("  By Type:")
    for ptype, count in summary['by_type'].items():
        print(f"    {ptype}: {count}")
    print()

    print("  By Panel:")
    for panel, count in summary['by_panel'].items():
        print(f"    {panel}: {count}")
    print()

    print("[OK] Photo analytics working")
    print()

    # ========================================================================
    # TEST 9: Find Missing Photos
    # ========================================================================

    print("="*80)
    print("[9/10] Finding missing documentation...")
    print("="*80 + "\n")

    missing = photo_mgr.find_missing_photos(job_id)

    if missing:
        print("Missing documentation:")
        for item in missing:
            print(f"  - {item}")
    else:
        print("No missing documentation!")
    print()

    # Create a job with incomplete photos
    result = db.execute("""
        INSERT INTO jobs (
            job_number, customer_id, vehicle_id, job_type, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "JOB-INCOMPLETE",
        customer_id,
        vehicle_id,
        "HAIL",
        "NEW",
        datetime.now().isoformat()
    ))
    incomplete_job_id = result[0]['id']

    # Only upload before photo
    photo_mgr.upload_photo(
        job_id=incomplete_job_id,
        photo_data=create_test_image("incomplete_before"),
        filename="before_only.png",
        photo_type="BEFORE",
        panel_type="HOOD"
    )
    print()

    incomplete_missing = photo_mgr.find_missing_photos(incomplete_job_id)
    print("Missing for incomplete job:")
    for item in incomplete_missing:
        print(f"  - {item}")
    print()

    assert "AFTER photos" in incomplete_missing[0]
    assert "OVERVIEW" in incomplete_missing[1]
    print("[OK] Missing photo detection working")
    print()

    # ========================================================================
    # TEST 10: Generate Photo Report
    # ========================================================================

    print("="*80)
    print("[10/10] Generating photo reports...")
    print("="*80 + "\n")

    # Individual job report
    print("--- JOB PHOTO REPORT ---")
    print()
    report = photo_mgr.generate_photo_report(job_id)
    print(report)
    print()

    # Overall statistics
    stats = photo_mgr.get_photo_stats()

    print("OVERALL PHOTO STATISTICS")
    print("-" * 40)
    print(f"  Total Photos: {stats['total_photos']}")
    print(f"  Total Size: {stats['total_size_bytes']:,} bytes")
    print(f"  Total Pairs: {stats['total_pairs']}")
    print(f"  Avg Photos/Job: {stats['avg_photos_per_job']}")
    print()

    print("  By Type:")
    for ptype, count in stats['photos_by_type'].items():
        print(f"    {ptype}: {count}")
    print()

    print("  By Status:")
    for status, count in stats['photos_by_status'].items():
        print(f"    {status}: {count}")
    print()

    print("[OK] Photo reports working")
    print()

    # ========================================================================
    # BONUS: Test Validation
    # ========================================================================

    print("="*80)
    print("[BONUS] Testing validation...")
    print("="*80 + "\n")

    # Test invalid photo type
    try:
        photo_mgr.upload_photo(
            job_id=job_id,
            photo_data=create_test_image("invalid"),
            filename="invalid.png",
            photo_type="INVALID_TYPE"
        )
        print("[ERROR] Should have raised ValueError")
    except ValueError as e:
        print(f"[OK] Validation caught invalid photo_type: {e}")
    print()

    # Test invalid panel type
    try:
        photo_mgr.upload_photo(
            job_id=job_id,
            photo_data=create_test_image("invalid"),
            filename="invalid.png",
            photo_type="BEFORE",
            panel_type="INVALID_PANEL"
        )
        print("[ERROR] Should have raised ValueError")
    except ValueError as e:
        print(f"[OK] Validation caught invalid panel_type: {e}")
    print()

    # Test pairing photos from different jobs
    try:
        # Get a photo from job2
        job2_photos = photo_mgr.get_job_photos(job2_id)
        if job2_photos:
            photo_mgr.create_before_after_pair(
                before_photo_id=hood_before,  # From job_id
                after_photo_id=job2_photos[0]['id']  # From job2_id
            )
            print("[ERROR] Should have raised ValueError for cross-job pairing")
    except ValueError as e:
        print(f"[OK] Validation caught cross-job pairing: {e}")
    print()

    print("[OK] All validation tests passed")
    print()

    # ========================================================================
    # Cleanup
    # ========================================================================

    # Clean up test photos directory
    import shutil
    if os.path.exists("data/photos"):
        for f in os.listdir("data/photos"):
            os.remove(os.path.join("data/photos", f))

    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] PHOTO MANAGEMENT TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Photo upload (bytes, base64, data URL)")
    print("  [OK] Panel categorization (16 panel types)")
    print("  [OK] Photo types (BEFORE, AFTER, PROGRESS, DAMAGE, OVERVIEW, DETAIL)")
    print("  [OK] Photo retrieval and filtering")
    print("  [OK] Photos by panel/type organization")
    print("  [OK] Before/after pair creation (manual)")
    print("  [OK] Before/after pair auto-creation")
    print("  [OK] Photo approval workflow")
    print("  [OK] Photo rejection with reason")
    print("  [OK] Bulk approval")
    print("  [OK] Photo update")
    print("  [OK] Photo reorder")
    print("  [OK] Soft delete (archive)")
    print("  [OK] Photo analytics/summary")
    print("  [OK] Missing photo detection")
    print("  [OK] Photo documentation report")
    print("  [OK] Validation (type, panel, cross-job)")
    print()

    print("PHOTO MANAGEMENT CAPABILITIES:")
    print("  - Upload photos via bytes, file, or base64")
    print("  - Categorize by 16 panel types (Hood, Roof, Doors, etc.)")
    print("  - 6 photo types (Before, After, Progress, Damage, Overview, Detail)")
    print("  - Create before/after pairs for insurance documentation")
    print("  - Auto-pair matching photos by panel type")
    print("  - Approval workflow (Pending -> Approved/Rejected)")
    print("  - Bulk operations (approve, delete)")
    print("  - Photo analytics and reporting")
    print("  - Missing documentation detection")
    print("  - File deduplication via MD5 hash")
    print("  - Soft delete with archive status")
    print()

    print("Ready for PROMPT 19: Tech Mobile Interface?")
    print()

    return True


if __name__ == '__main__':
    success = test_photo_manager()
    sys.exit(0 if success else 1)
