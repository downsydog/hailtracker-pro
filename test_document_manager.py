"""
Test Document Generation
PDR CRM Part 12 - Professional PDF Generation
"""

import sys
import os
import shutil

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_document_manager():
    print("\n" + "="*80)
    print("TESTING DOCUMENT GENERATION (PDF)")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.document_manager import DocumentManager
    from src.crm.managers.estimate_manager import EstimateManager
    from src.crm.managers.job_manager import JobManager
    from src.crm.managers.customer_manager import CustomerManager
    from src.crm.managers.vehicle_manager import VehicleManager
    from src.crm.managers.payment_manager import PaymentManager
    from datetime import datetime, date

    # Use test database and output directory
    test_db = "data/test_documents.db"
    test_output_dir = "data/test_documents"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)
    if os.path.exists(test_output_dir):
        shutil.rmtree(test_output_dir)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)

    # Custom company info for testing
    company_info = {
        'name': 'Premier PDR Solutions',
        'address': '456 Auto Repair Lane',
        'city': 'Dallas',
        'state': 'TX',
        'zip': '75201',
        'phone': '(214) 555-1234',
        'email': 'service@premierpdr.com',
        'website': 'www.premierpdr.com'
    }

    doc_mgr = DocumentManager(db, company_info=company_info, output_dir=test_output_dir)
    estimate_mgr = EstimateManager(db)
    job_mgr = JobManager(db)
    customer_mgr = CustomerManager(db)
    vehicle_mgr = VehicleManager(db)
    payment_mgr = PaymentManager(db)

    # Create test data
    print("\nSetting up test data...")

    customer_id = customer_mgr.create_customer({
        'first_name': 'Robert',
        'last_name': 'Anderson',
        'phone': '214-555-0200',
        'email': 'robert.anderson@example.com',
        'street_address': '789 Oak Street',
        'city': 'Dallas',
        'state': 'TX',
        'zip_code': '75202'
    })

    vehicle_id = vehicle_mgr.create_vehicle({
        'customer_id': customer_id,
        'year': 2023,
        'make': 'Honda',
        'model': 'Accord',
        'color': 'Midnight Blue',
        'vin': '1HGCV1F34NA012345',
        'license_plate': 'ABC-1234'
    })

    # Create a technician
    db.execute("""
        INSERT INTO technicians (
            first_name, last_name, employee_id, skill_level,
            status, max_jobs_concurrent, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ('Mike', 'Smith', 'TECH001', 'EXPERT', 'ACTIVE', 3, datetime.now().isoformat()))

    tech_result = db.execute("SELECT id FROM technicians WHERE employee_id = 'TECH001'")
    tech_id = tech_result[0]['id']

    job_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        job_type="HAIL",
        damage_type="HAIL"
    )

    # Assign tech
    db.execute("""
        UPDATE jobs SET status = 'APPROVED', assigned_tech_id = ?, estimated_hours = 6.0, updated_at = ?
        WHERE id = ?
    """, (tech_id, datetime.now().isoformat(), job_id))

    # Create estimate
    estimate_id = estimate_mgr.create_estimate(
        job_id=job_id,
        template='HAIL_SEVERE',
        labor_rate=85.00,
        tax_rate=0.0825,
        notes="Extensive hail damage on hood, roof, and trunk. Some dents require glue pull technique.",
        terms="Payment due upon completion. Warranty: 30 days on workmanship."
    )

    # Approve estimate (must go through SENT first per workflow)
    estimate_mgr.update_status(estimate_id, 'SENT')
    estimate_mgr.update_status(estimate_id, 'APPROVED')

    # Create invoice from estimate
    invoice_id = estimate_mgr.convert_to_invoice(estimate_id)

    # Record a partial payment
    payment_id = payment_mgr.record_payment(
        invoice_id=invoice_id,
        job_id=job_id,
        amount=2000.00,
        payment_method='CHECK',
        payment_date=date.today(),
        payer_type='INSURANCE',
        payment_reference='CHK-12345'
    )

    print()

    # ========================================================================
    # TEST 1: Company Info
    # ========================================================================

    print("="*80)
    print("[1/8] Testing company info configuration...")
    print("="*80 + "\n")

    info = doc_mgr.get_company_info()
    print(f"Company: {info['name']}")
    print(f"Address: {info['address']}, {info['city']}, {info['state']} {info['zip']}")
    print(f"Phone: {info['phone']}")
    print(f"Email: {info['email']}")
    print()

    assert info['name'] == 'Premier PDR Solutions'
    print("[OK] Company info configured correctly")
    print()

    # ========================================================================
    # TEST 2: Generate Estimate Document
    # ========================================================================

    print("="*80)
    print("[2/8] Generating estimate document...")
    print("="*80 + "\n")

    estimate_doc = doc_mgr.generate_estimate_pdf(estimate_id)

    print(f"Estimate Number: {estimate_doc['estimate_number']}")
    print(f"Document Type: {estimate_doc['document_type']}")
    print(f"File Path: {estimate_doc['file_path']}")
    print()

    # Verify file exists
    assert os.path.exists(estimate_doc['file_path'])
    assert 'EST-' in estimate_doc['estimate_number']

    # Check HTML content
    html = estimate_doc['html_content']
    assert 'Robert Anderson' in html
    assert '2023 Honda Accord' in html
    assert 'Premier PDR Solutions' in html
    assert 'ESTIMATE' in html

    print("[OK] Estimate document generated successfully")
    print()

    # ========================================================================
    # TEST 3: Generate Invoice Document
    # ========================================================================

    print("="*80)
    print("[3/8] Generating invoice document...")
    print("="*80 + "\n")

    invoice_doc = doc_mgr.generate_invoice_pdf(invoice_id)

    print(f"Invoice Number: {invoice_doc['invoice_number']}")
    print(f"Document Type: {invoice_doc['document_type']}")
    print(f"File Path: {invoice_doc['file_path']}")
    print()

    # Verify file exists
    assert os.path.exists(invoice_doc['file_path'])
    assert 'INV-' in invoice_doc['invoice_number']

    # Check HTML content
    html = invoice_doc['html_content']
    assert 'Robert Anderson' in html
    assert 'INVOICE' in html
    assert 'Balance Due' in html or 'Paid in Full' in html

    print("[OK] Invoice document generated successfully")
    print()

    # ========================================================================
    # TEST 4: Generate Work Order
    # ========================================================================

    print("="*80)
    print("[4/8] Generating work order...")
    print("="*80 + "\n")

    work_order_doc = doc_mgr.generate_work_order_pdf(job_id)

    print(f"Job Number: {work_order_doc['job_number']}")
    print(f"Document Type: {work_order_doc['document_type']}")
    print(f"File Path: {work_order_doc['file_path']}")
    print()

    # Verify file exists
    assert os.path.exists(work_order_doc['file_path'])

    # Check HTML content
    html = work_order_doc['html_content']
    assert 'WORK ORDER' in html
    assert 'Mike Smith' in html  # Technician name
    assert '2023 Honda Accord' in html
    assert 'Quality Checklist' in html

    print("[OK] Work order generated successfully")
    print()

    # ========================================================================
    # TEST 5: Generate Receipt
    # ========================================================================

    print("="*80)
    print("[5/8] Generating payment receipt...")
    print("="*80 + "\n")

    receipt_doc = doc_mgr.generate_receipt_pdf(payment_id)

    print(f"Receipt Number: {receipt_doc['receipt_number']}")
    print(f"Document Type: {receipt_doc['document_type']}")
    print(f"File Path: {receipt_doc['file_path']}")
    print()

    # Verify file exists
    assert os.path.exists(receipt_doc['file_path'])
    assert 'RCP-' in receipt_doc['receipt_number']

    # Check HTML content
    html = receipt_doc['html_content']
    assert 'RECEIPT' in html
    assert '$2,000.00' in html
    assert 'CHECK' in html

    print("[OK] Receipt generated successfully")
    print()

    # ========================================================================
    # TEST 6: Batch Generation
    # ========================================================================

    print("="*80)
    print("[6/8] Testing batch document generation...")
    print("="*80 + "\n")

    batch_results = doc_mgr.generate_job_documents(job_id)

    print(f"Job ID: {batch_results['job_id']}")
    print(f"Documents Generated: {len(batch_results['documents'])}")
    for doc in batch_results['documents']:
        print(f"  - {doc['document_type']}: {os.path.basename(doc['file_path'])}")
    print()

    assert len(batch_results['documents']) >= 2  # At least work order and one other
    print("[OK] Batch generation working")
    print()

    # ========================================================================
    # TEST 7: Document History
    # ========================================================================

    print("="*80)
    print("[7/8] Testing document history...")
    print("="*80 + "\n")

    history = doc_mgr.get_document_history(limit=10)

    print(f"Document History: {len(history)} records")
    for record in history:
        print(f"  [{record['document_type']}] ID:{record['reference_id']} - {os.path.basename(record['file_path'])}")
    print()

    assert len(history) >= 4  # We generated at least 4 documents
    print("[OK] Document history tracking working")
    print()

    # ========================================================================
    # TEST 8: Document Report
    # ========================================================================

    print("="*80)
    print("[8/8] Generating document report...")
    print("="*80 + "\n")

    report = doc_mgr.generate_document_report(days=30)
    print(report)

    assert 'DOCUMENT GENERATION REPORT' in report
    print("[OK] Document report generated")
    print()

    # ========================================================================
    # BONUS: View Generated HTML
    # ========================================================================

    print("="*80)
    print("[BONUS] Sample of generated estimate HTML...")
    print("="*80 + "\n")

    # Read and display a portion of the estimate HTML
    with open(estimate_doc['file_path'], 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Show just the header portion
    start = html_content.find('<div class="header">')
    end = html_content.find('</div>', start + 100) + 6
    print("HTML Header Preview:")
    print("-" * 60)
    print(html_content[start:end][:500] + "...")
    print("-" * 60)
    print()

    # ========================================================================
    # BONUS: List Generated Files
    # ========================================================================

    print("="*80)
    print("[BONUS] Generated files...")
    print("="*80 + "\n")

    for folder in ['estimates', 'invoices', 'work_orders', 'receipts']:
        folder_path = os.path.join(test_output_dir, folder)
        if os.path.exists(folder_path):
            files = os.listdir(folder_path)
            if files:
                print(f"{folder.upper()}:")
                for f in files:
                    file_path = os.path.join(folder_path, f)
                    size = os.path.getsize(file_path)
                    print(f"  - {f} ({size:,} bytes)")
    print()

    # Cleanup
    os.remove(test_db)
    shutil.rmtree(test_output_dir)

    print("="*80)
    print("[SUCCESS] DOCUMENT GENERATION TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Company info configuration")
    print("  [OK] Estimate PDF generation")
    print("  [OK] Invoice PDF generation")
    print("  [OK] Work order generation")
    print("  [OK] Payment receipt generation")
    print("  [OK] Batch document generation")
    print("  [OK] Document history tracking")
    print("  [OK] Document reporting")
    print()

    print("DOCUMENT TYPES:")
    print("  - ESTIMATE - Professional estimates for customers")
    print("  - INVOICE - Billing documents with payment tracking")
    print("  - WORK_ORDER - Internal tech work orders")
    print("  - RECEIPT - Payment confirmation receipts")
    print()

    print("FEATURES:")
    print("  - Professional HTML styling (print-ready)")
    print("  - Company branding customization")
    print("  - Vehicle and customer information")
    print("  - Line item details")
    print("  - Payment history on invoices")
    print("  - Quality checklists on work orders")
    print("  - Signature lines")
    print("  - Document storage and retrieval")
    print()

    print("PDF CONVERSION:")
    print("  The HTML files can be converted to PDF using:")
    print("  - weasyprint (Python library)")
    print("  - pdfkit (wkhtmltopdf wrapper)")
    print("  - Browser print-to-PDF")
    print("  - headless Chrome/Puppeteer")
    print()

    print("Ready for PROMPT 13: Multi-Location Support?")
    print()

    return True


if __name__ == '__main__':
    success = test_document_manager()
    sys.exit(0 if success else 1)
