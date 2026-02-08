"""
Test Insurance Partner Management
PDR CRM Part 26 - Insurance partner integration and claims processing
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_insurance_partner():
    print("\n" + "="*80)
    print("TESTING INSURANCE PARTNER MANAGEMENT")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.insurance_partner_manager import InsurancePartnerManager

    # Use test database
    test_db = "data/test_insurance_partner.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    mgr = InsurancePartnerManager(db)

    print()

    # ========================================================================
    # TEST 1: Create Insurance Partner (DRP)
    # ========================================================================

    print("="*80)
    print("[1/12] Creating DRP insurance partner...")
    print("="*80 + "\n")

    partner_id = mgr.create_insurance_partner(
        carrier_name='State Farm Insurance',
        carrier_type='STATE_FARM',
        contact_name='Sarah Miller',
        contact_email='sarah.miller@statefarm.com',
        contact_phone='555-8000',
        claims_email='claims@statefarm.com',
        claims_phone='555-8001',
        drp_agreement=True,
        drp_discount_percent=10.0,
        requires_pre_auth=True,
        photo_requirements={
            'min_photos': 8,
            'required_angles': ['overview', 'damage_closeup', 'vin', 'odometer'],
            'max_file_size_mb': 10
        },
        payment_terms='NET_30',
        notes='Major DRP partner since 2020'
    )
    print()

    assert partner_id > 0
    print("[OK] DRP insurance partner created")
    print()

    # ========================================================================
    # TEST 2: Create Non-DRP Partner
    # ========================================================================

    print("="*80)
    print("[2/12] Creating non-DRP insurance partner...")
    print("="*80 + "\n")

    partner2_id = mgr.create_insurance_partner(
        carrier_name='GEICO Insurance',
        carrier_type='GEICO',
        contact_name='Mike Johnson',
        contact_email='mike.johnson@geico.com',
        contact_phone='555-9000',
        claims_email='claims@geico.com',
        drp_agreement=False,
        requires_pre_auth=True,
        photo_requirements={
            'min_photos': 6,
            'required_angles': ['overview', 'damage_closeup'],
            'max_file_size_mb': 5
        },
        payment_terms='NET_45'
    )
    print()

    assert partner2_id > 0
    print("[OK] Non-DRP partner created")
    print()

    # ========================================================================
    # TEST 3: Create Insurance Claim
    # ========================================================================

    print("="*80)
    print("[3/12] Creating insurance claim...")
    print("="*80 + "\n")

    claim_id = mgr.create_insurance_claim(
        insurance_partner_id=partner_id,
        claim_number='SF-2026-123456',
        policy_number='POL-789012345',
        policyholder_name='John Doe',
        deductible_amount=500.00,
        date_of_loss=date(2026, 1, 10),
        loss_type='HAIL',
        adjuster_name='Tom Wilson',
        adjuster_phone='555-8100',
        adjuster_email='tom.wilson@statefarm.com',
        requires_inspection=False,
        notes='Customer referred by dealership'
    )
    print()

    assert claim_id > 0
    claim = mgr.get_claim(claim_id)
    assert claim['status'] == 'PENDING_AUTH'
    print("[OK] Insurance claim created")
    print()

    # ========================================================================
    # TEST 4: Authorize Claim
    # ========================================================================

    print("="*80)
    print("[4/12] Authorizing claim...")
    print("="*80 + "\n")

    mgr.authorize_claim(
        claim_id=claim_id,
        authorization_number='AUTH-98765',
        authorized_amount=2500.00,
        authorized_by='Tom Wilson',
        authorization_notes='Approved per photo review'
    )
    print()

    claim = mgr.get_claim(claim_id)
    assert claim['status'] == 'AUTHORIZED'
    assert claim['authorization_number'] == 'AUTH-98765'
    assert claim['authorized_amount'] == 2500.00
    print("[OK] Claim authorized")
    print()

    # ========================================================================
    # TEST 5: Add Claim Photos
    # ========================================================================

    print("="*80)
    print("[5/12] Adding claim photos...")
    print("="*80 + "\n")

    photos = [
        {
            'photo_type': 'overview',
            'file_path': '/photos/claim_1_overview.jpg',
            'description': 'Vehicle overview - driver side',
            'taken_at': datetime.now()
        },
        {
            'photo_type': 'damage_closeup',
            'file_path': '/photos/claim_1_hood.jpg',
            'description': 'Hood damage closeup',
            'taken_at': datetime.now()
        },
        {
            'photo_type': 'damage_closeup',
            'file_path': '/photos/claim_1_roof.jpg',
            'description': 'Roof damage closeup',
            'taken_at': datetime.now()
        },
        {
            'photo_type': 'vin',
            'file_path': '/photos/claim_1_vin.jpg',
            'description': 'VIN plate',
            'taken_at': datetime.now()
        },
        {
            'photo_type': 'odometer',
            'file_path': '/photos/claim_1_odometer.jpg',
            'description': 'Odometer reading',
            'taken_at': datetime.now()
        },
        {
            'photo_type': 'overview',
            'file_path': '/photos/claim_1_overview2.jpg',
            'description': 'Vehicle overview - passenger side',
            'taken_at': datetime.now()
        },
        {
            'photo_type': 'damage_closeup',
            'file_path': '/photos/claim_1_trunk.jpg',
            'description': 'Trunk damage',
            'taken_at': datetime.now()
        },
        {
            'photo_type': 'damage_closeup',
            'file_path': '/photos/claim_1_fender.jpg',
            'description': 'Fender damage',
            'taken_at': datetime.now()
        }
    ]

    count = mgr.add_claim_photos(
        claim_id=claim_id,
        photos=photos,
        uploaded_by='tech_mike'
    )
    print()

    assert count == 8
    claim_photos = mgr.get_claim_photos(claim_id)
    assert len(claim_photos) == 8
    print("[OK] Photos added to claim")
    print()

    # ========================================================================
    # TEST 6: Verify Photo Requirements
    # ========================================================================

    print("="*80)
    print("[6/12] Verifying photo requirements...")
    print("="*80 + "\n")

    verification = mgr.verify_photo_requirements(claim_id)

    print(f"Photo Verification:")
    print(f"  Total photos: {verification['total_photos']}")
    print(f"  Required: {verification['required_photos']}")
    print(f"  Has minimum: {verification['has_minimum']}")
    print(f"  Required angles: {verification['required_angles']}")
    print(f"  Missing angles: {verification['missing_angles']}")
    print(f"  Meets requirements: {verification['meets_requirements']}")
    print()

    assert verification['meets_requirements'] == True
    assert verification['total_photos'] >= verification['required_photos']
    print("[OK] Photo requirements verified")
    print()

    # ========================================================================
    # TEST 7: Update Claim Status
    # ========================================================================

    print("="*80)
    print("[7/12] Updating claim status to IN_PROGRESS...")
    print("="*80 + "\n")

    mgr.update_claim_status(claim_id, 'IN_PROGRESS', notes='Work started')
    print()

    claim = mgr.get_claim(claim_id)
    assert claim['status'] == 'IN_PROGRESS'

    mgr.update_claim_status(claim_id, 'COMPLETED', notes='Work completed')
    print()

    claim = mgr.get_claim(claim_id)
    assert claim['status'] == 'COMPLETED'
    print("[OK] Claim status updated")
    print()

    # ========================================================================
    # TEST 8: Submit Claim
    # ========================================================================

    print("="*80)
    print("[8/12] Submitting claim...")
    print("="*80 + "\n")

    mgr.submit_claim(
        claim_id=claim_id,
        submission_method='ELECTRONIC',
        submitted_amount=2500.00,
        supporting_documents=[
            '/docs/invoice_123.pdf',
            '/docs/photos_123.zip'
        ]
    )
    print()

    claim = mgr.get_claim(claim_id)
    assert claim['status'] == 'SUBMITTED'
    print("[OK] Claim submitted")
    print()

    # ========================================================================
    # TEST 9: Create Supplement
    # ========================================================================

    print("="*80)
    print("[9/12] Creating supplement request...")
    print("="*80 + "\n")

    supplement_id = mgr.create_supplement(
        claim_id=claim_id,
        supplement_reason='Hidden damage discovered',
        additional_damage_found='Additional dents found on passenger side pillars after panel removal',
        original_estimate=2500.00,
        supplement_amount=450.00,
        supporting_photos=['/photos/supplement_pillar1.jpg', '/photos/supplement_pillar2.jpg'],
        notes='Discovered during repair process'
    )
    print()

    assert supplement_id > 0
    supplements = mgr.get_claim_supplements(claim_id)
    assert len(supplements) == 1
    assert supplements[0]['status'] == 'PENDING'
    print("[OK] Supplement request created")
    print()

    # ========================================================================
    # TEST 10: Approve Supplement
    # ========================================================================

    print("="*80)
    print("[10/12] Approving supplement...")
    print("="*80 + "\n")

    mgr.approve_supplement(
        supplement_id=supplement_id,
        approved_amount=400.00,
        approved_by='Tom Wilson',
        approval_notes='Approved $400 of $450 requested'
    )
    print()

    supplements = mgr.get_claim_supplements(claim_id)
    assert supplements[0]['status'] == 'APPROVED'
    assert supplements[0]['approved_amount'] == 400.00
    print("[OK] Supplement approved")
    print()

    # ========================================================================
    # TEST 11: Record Insurance Payment
    # ========================================================================

    print("="*80)
    print("[11/12] Recording insurance payment...")
    print("="*80 + "\n")

    payment_id = mgr.record_insurance_payment(
        claim_id=claim_id,
        payment_amount=2400.00,  # Authorized minus deductible plus approved supplement
        payment_method='ACH',
        reference_number='ACH-2026-001234',
        payment_date=date.today(),
        notes='Final payment including approved supplement'
    )
    print()

    assert payment_id > 0
    claim = mgr.get_claim(claim_id)
    assert claim['status'] == 'PAID'
    assert claim['paid_amount'] == 2400.00

    payments = mgr.get_claim_payments(claim_id)
    assert len(payments) == 1
    print("[OK] Insurance payment recorded")
    print()

    # ========================================================================
    # TEST 12: Partner Performance Report
    # ========================================================================

    print("="*80)
    print("[12/12] Getting partner performance report...")
    print("="*80 + "\n")

    performance = mgr.get_partner_performance(partner_id)

    print(f"Partner Performance Report:")
    print(f"  Carrier: {performance['carrier_name']}")
    print(f"  DRP Partner: {performance['drp_agreement']}")
    print(f"  Period: {performance['period']['start_date']} to {performance['period']['end_date']}")
    print()
    print(f"  Claims:")
    print(f"    Total: {performance['claims']['total_claims']}")
    print(f"    Authorization rate: {performance['claims']['authorization_rate']}%")
    print(f"    Status breakdown: {performance['claims']['status_breakdown']}")
    print()
    print(f"  Financial:")
    print(f"    Total authorized: ${performance['financial']['total_authorized']:,.2f}")
    print(f"    Total paid: ${performance['financial']['total_paid']:,.2f}")
    print(f"    Outstanding: ${performance['financial']['outstanding']:,.2f}")
    print(f"    Avg claim amount: ${performance['financial']['avg_claim_amount']:,.2f}")
    print()
    print(f"  Timing:")
    print(f"    Avg days to payment: {performance['timing']['avg_days_to_payment']}")
    print()

    assert performance['claims']['total_claims'] == 1
    print("[OK] Partner performance report generated")
    print()

    # ========================================================================
    # BONUS: Get Claim Details
    # ========================================================================

    print("="*80)
    print("[BONUS] Getting complete claim details...")
    print("="*80 + "\n")

    details = mgr.get_claim_details(claim_id)

    print(f"Claim Details:")
    print(f"  Claim #: {details['claim']['claim_number']}")
    print(f"  Policyholder: {details['claim']['policyholder_name']}")
    print(f"  Status: {details['claim']['status']}")
    print(f"  Insurance Partner: {details['partner']['carrier_name']}")
    print(f"  Photos: {len(details['photos'])}")
    print(f"  Supplements: {len(details['supplements'])}")
    print(f"  Payments: {len(details['payments'])}")
    print()

    assert details['claim']['claim_number'] == 'SF-2026-123456'
    print("[OK] Claim details retrieved")
    print()

    # ========================================================================
    # BONUS: DRP Discount Calculation
    # ========================================================================

    print("="*80)
    print("[BONUS] Calculating DRP discount...")
    print("="*80 + "\n")

    discount = mgr.calculate_drp_discount(partner_id, 1000.00)

    print(f"DRP Discount Calculation:")
    print(f"  Base amount: ${discount['base_amount']:,.2f}")
    print(f"  Discount: {discount['discount_percent']}%")
    print(f"  Discount amount: ${discount['discount_amount']:,.2f}")
    print(f"  Final amount: ${discount['final_amount']:,.2f}")
    print(f"  Is DRP: {discount['is_drp']}")
    print()

    assert discount['is_drp'] == True
    assert discount['discount_percent'] == 10.0
    assert discount['final_amount'] == 900.00
    print("[OK] DRP discount calculated")
    print()

    # ========================================================================
    # BONUS: Get DRP Partners
    # ========================================================================

    print("="*80)
    print("[BONUS] Getting all DRP partners...")
    print("="*80 + "\n")

    drp_partners = mgr.get_drp_partners()

    print(f"DRP Partners ({len(drp_partners)}):")
    for p in drp_partners:
        print(f"  - {p['carrier_name']} ({p['drp_discount_percent']}% discount)")
    print()

    assert len(drp_partners) == 1
    print("[OK] DRP partners retrieved")
    print()

    # ========================================================================
    # Cleanup
    # ========================================================================

    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] INSURANCE PARTNER MANAGEMENT TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Insurance partner creation (DRP & non-DRP)")
    print("  [OK] DRP agreement management")
    print("  [OK] Claims processing workflow")
    print("  [OK] Claim authorization")
    print("  [OK] Photo documentation")
    print("  [OK] Photo requirements verification")
    print("  [OK] Claim status tracking")
    print("  [OK] Claim submission")
    print("  [OK] Supplement requests")
    print("  [OK] Supplement approval")
    print("  [OK] Payment recording")
    print("  [OK] Partner performance reporting")
    print("  [OK] DRP discount calculation")
    print()

    print("SUPPORTED CARRIERS:")
    for carrier in mgr.MAJOR_CARRIERS:
        print(f"  - {carrier}")
    print()

    print("CLAIM WORKFLOW:")
    print("  1. PENDING_AUTH - Claim created, awaiting authorization")
    print("  2. AUTHORIZED - Insurance approved the repair")
    print("  3. IN_PROGRESS - Work has started")
    print("  4. COMPLETED - Work finished")
    print("  5. SUBMITTED - Claim submitted for payment")
    print("  6. PAID - Payment received")
    print()
    print("  Alternative paths:")
    print("  - DENIED - Claim was rejected")
    print("  - SUPPLEMENTED - Additional damage found")
    print()

    print("DRP (DIRECT REPAIR PROGRAM) BENEFITS:")
    print("  - Pre-negotiated labor rates")
    print("  - Streamlined authorization")
    print("  - Faster payments")
    print("  - Higher claim volume")
    print("  - Direct billing to insurance")
    print()

    print("PHOTO REQUIREMENTS (Typical):")
    print("  - Overview shots (all 4 sides)")
    print("  - Damage closeups")
    print("  - VIN plate")
    print("  - Odometer reading")
    print("  - Before/after comparison")
    print()

    print("Ready for PROMPT 27?")
    print()

    return True


if __name__ == '__main__':
    success = test_insurance_partner()
    sys.exit(0 if success else 1)
