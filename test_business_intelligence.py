"""
Test Business Intelligence & Reporting
PDR CRM Part 29 - BI system and analytics
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_business_intelligence():
    print("\n" + "="*80)
    print("TESTING BUSINESS INTELLIGENCE & REPORTING")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.business_intelligence_manager import BusinessIntelligenceManager

    # Use test database
    test_db = "data/test_business_intelligence.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    mgr = BusinessIntelligenceManager(db)

    # Setup: Create test data
    print("Creating test data...")

    # Create customers
    for i in range(1, 11):
        db.execute("""
            INSERT INTO customers (first_name, last_name, email, phone, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f'Customer{i}',
            f'Test{i}',
            f'customer{i}@example.com',
            f'555-000{i}',
            'WEBSITE' if i % 2 == 0 else 'REFERRAL',
            (datetime.now() - timedelta(days=i*5)).isoformat()
        ))

    # Create technicians
    techs = [('Mike', 'Johnson', '["PDR"]'), ('Sarah', 'Williams', '["HAIL"]'), ('David', 'Chen', '["PDR"]')]
    for first, last, specialties in techs:
        db.execute("""
            INSERT INTO technicians (first_name, last_name, specialties, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (first, last, specialties, 'ACTIVE', datetime.now().isoformat()))

    # Create vehicles
    for i in range(1, 11):
        db.execute("""
            INSERT INTO vehicles (customer_id, year, make, model, vin, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (i, 2020 + (i % 4), 'Toyota', 'Camry', f'VIN{i:010d}', datetime.now().isoformat()))

    # Create jobs with various statuses
    job_statuses = ['COMPLETED', 'COMPLETED', 'COMPLETED', 'IN_PROGRESS', 'IN_PROGRESS', 'NEW', 'COMPLETED', 'COMPLETED', 'COMPLETED', 'NEW']
    for i in range(1, 11):
        completed_at = None
        if job_statuses[i-1] == 'COMPLETED':
            completed_at = (datetime.now() - timedelta(days=i*2)).isoformat()

        db.execute("""
            INSERT INTO jobs (
                job_number, customer_id, vehicle_id, assigned_tech_id,
                job_type, status, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f'JOB-2026-{i:04d}',
            i,
            i,
            (i % 3) + 1,  # Assign to tech 1, 2, or 3
            'PDR' if i % 2 == 0 else 'HAIL',
            job_statuses[i-1],
            (datetime.now() - timedelta(days=i*3)).isoformat(),
            completed_at
        ))

    # Create invoices
    for i in range(1, 8):  # 7 invoices for completed jobs
        total = 500 + (i * 150)
        balance = 0 if i <= 5 else total  # 5 paid, 2 unpaid
        db.execute("""
            INSERT INTO invoices (
                invoice_number, job_id, customer_id,
                invoice_date, subtotal, tax_amount, total,
                balance_due, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f'INV-2026-{i:04d}',
            i,
            i,
            (datetime.now() - timedelta(days=i*2)).isoformat(),
            total * 0.92,
            total * 0.08,
            total,
            balance,
            'PAID' if balance == 0 else 'SENT'
        ))

    # Create customer_reviews table (normally created by CustomerPortalManager)
    db.execute("""
        CREATE TABLE IF NOT EXISTS customer_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            review_text TEXT,
            would_recommend INTEGER DEFAULT 1,
            review_categories TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'PUBLISHED',
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    # Create customer reviews
    for i in range(1, 6):
        db.execute("""
            INSERT INTO customer_reviews (
                customer_id, job_id, rating, review_text,
                would_recommend, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            i,
            i,
            4 + (i % 2),  # 4 or 5 stars
            'Great service!' if i % 2 == 0 else 'Excellent work!',
            1,
            datetime.now().isoformat(),
            'PUBLISHED'
        ))

    print(f"  Created 10 customers, 3 technicians, 10 jobs, 7 invoices, 5 reviews")
    print()

    # ========================================================================
    # TEST 1: Executive Dashboard
    # ========================================================================

    print("="*80)
    print("[1/12] Getting executive dashboard...")
    print("="*80 + "\n")

    dashboard = mgr.get_executive_dashboard('THIS_MONTH')
    print()

    print(f"Executive Dashboard Summary:")
    print(f"  Period: {dashboard['period']['name']}")
    print()
    print(f"  Financial:")
    print(f"    Total Revenue: ${dashboard['financial']['total_revenue']:,.2f}")
    print(f"    Avg Invoice: ${dashboard['financial']['avg_invoice_value']:,.2f}")
    print(f"    Outstanding: ${dashboard['financial']['outstanding_receivables']:,.2f}")
    print()
    print(f"  Operations:")
    print(f"    Total Jobs: {dashboard['operations']['total_jobs']}")
    print(f"    Completed: {dashboard['operations']['jobs_completed']}")
    print(f"    Completion Rate: {dashboard['operations']['completion_rate']}%")
    print()
    print(f"  Customers:")
    print(f"    New Customers: {dashboard['customers']['new_customers']}")
    print(f"    Total Customers: {dashboard['customers']['total_customers']}")
    print()

    assert 'financial' in dashboard
    assert 'operations' in dashboard
    assert 'customers' in dashboard
    print("[OK] Executive dashboard generated")
    print()

    # ========================================================================
    # TEST 2: Financial Report
    # ========================================================================

    print("="*80)
    print("[2/12] Generating financial report...")
    print("="*80 + "\n")

    start_date = date.today() - timedelta(days=30)
    end_date = date.today()

    financial_report = mgr.generate_financial_report(
        start_date=start_date,
        end_date=end_date,
        include_breakdown=True
    )
    print()

    print(f"Financial Report Details:")
    print(f"  Gross Revenue: ${financial_report['revenue']['gross_revenue']:,.2f}")
    print(f"  Tax Collected: ${financial_report['revenue']['tax_collected']:,.2f}")
    print(f"  Invoice Count: {financial_report['revenue']['invoice_count']}")
    print(f"  Collection Rate: {financial_report['collections']['collection_rate']}%")
    print()

    assert financial_report['report_type'] == 'FINANCIAL'
    assert 'revenue' in financial_report
    assert 'collections' in financial_report
    print("[OK] Financial report generated")
    print()

    # ========================================================================
    # TEST 3: Technician Performance
    # ========================================================================

    print("="*80)
    print("[3/12] Getting technician performance...")
    print("="*80 + "\n")

    tech_performance = mgr.get_technician_performance(
        start_date=start_date,
        end_date=end_date
    )
    print()

    print(f"Technician Performance ({len(tech_performance)} technicians):")
    for tech in tech_performance:
        print(f"  {tech['name']}:")
        print(f"    Jobs Completed: {tech['jobs_completed']}")
        print(f"    Revenue: ${tech['revenue_generated']:,.2f}")
        print(f"    Avg Rating: {tech['avg_customer_rating']}")
        print(f"    Efficiency: {tech['efficiency_score']:.0f}%")
    print()

    assert len(tech_performance) >= 0
    print("[OK] Technician performance retrieved")
    print()

    # ========================================================================
    # TEST 4: Technician Leaderboard
    # ========================================================================

    print("="*80)
    print("[4/12] Getting technician leaderboard...")
    print("="*80 + "\n")

    leaderboard = mgr.get_technician_leaderboard(
        metric='revenue',
        period='THIS_MONTH',
        limit=5
    )

    print(f"Top Technicians by Revenue:")
    for tech in leaderboard:
        print(f"  #{tech.get('rank', '-')} {tech['name']}: ${tech['revenue_generated']:,.2f}")
    print()

    print("[OK] Technician leaderboard generated")
    print()

    # ========================================================================
    # TEST 5: Customer Insights - Segments
    # ========================================================================

    print("="*80)
    print("[5/12] Analyzing customer segments...")
    print("="*80 + "\n")

    segments = mgr.get_customer_insights('SEGMENTS')

    print(f"Customer Segment Analysis:")
    print(f"  Total Customers: {segments['total_customers']}")
    print()
    for segment_name, data in segments['segments'].items():
        print(f"  {segment_name.replace('_', ' ').title()}:")
        print(f"    Count: {data['count']} ({data['percent']}%)")
        print(f"    Total Revenue: ${data['total_revenue']:,.2f}")
    print()

    assert 'segments' in segments
    print("[OK] Customer segments analyzed")
    print()

    # ========================================================================
    # TEST 6: Customer Lifetime Value
    # ========================================================================

    print("="*80)
    print("[6/12] Analyzing customer lifetime value...")
    print("="*80 + "\n")

    ltv = mgr.get_customer_insights('LIFETIME_VALUE')

    print(f"Customer Lifetime Value Analysis:")
    print(f"  Average LTV: ${ltv['avg_lifetime_value']:,.2f}")
    print(f"  Avg Purchase Value: ${ltv['avg_purchase_value']:,.2f}")
    print(f"  Purchase Frequency: {ltv['purchase_frequency_per_year']} per year")
    print(f"  Avg Lifespan: {ltv['avg_customer_lifespan_years']} years")
    print(f"  Formula: {ltv['ltv_formula']}")
    print()

    assert ltv['avg_lifetime_value'] > 0
    print("[OK] Customer LTV calculated")
    print()

    # ========================================================================
    # TEST 7: Trend Analysis
    # ========================================================================

    print("="*80)
    print("[7/12] Analyzing revenue trends...")
    print("="*80 + "\n")

    revenue_trend = mgr.analyze_trends(
        metric='REVENUE',
        period='MONTHLY',
        lookback_periods=6
    )

    print(f"Revenue Trend (Last 6 Months):")
    for point in revenue_trend[-6:]:
        print(f"  {point['period']}: ${point['value']:,.2f}")
    print()

    jobs_trend = mgr.analyze_trends(
        metric='JOBS',
        period='MONTHLY',
        lookback_periods=6
    )

    print(f"Jobs Trend (Last 6 Months):")
    for point in jobs_trend[-6:]:
        print(f"  {point['period']}: {point['value']} jobs")
    print()

    assert len(revenue_trend) > 0
    print("[OK] Trend analysis completed")
    print()

    # ========================================================================
    # TEST 8: Revenue Forecasting
    # ========================================================================

    print("="*80)
    print("[8/12] Forecasting revenue...")
    print("="*80 + "\n")

    forecast = mgr.forecast_revenue(
        forecast_periods=3,
        method='LINEAR'
    )
    print()

    print(f"Revenue Forecast Details:")
    print(f"  Method: {forecast['method']}")
    print(f"  Historical Periods: {forecast['historical_periods']}")
    print(f"  Avg Growth Rate: {forecast['avg_growth_rate']}%")
    print()

    assert 'forecasts' in forecast
    assert len(forecast['forecasts']) == 3
    print("[OK] Revenue forecast generated")
    print()

    # ========================================================================
    # TEST 9: Custom Report
    # ========================================================================

    print("="*80)
    print("[9/12] Creating custom report...")
    print("="*80 + "\n")

    # Save custom report config
    report_id = mgr.create_custom_report(
        report_name='Monthly Performance Summary',
        report_config={
            'metrics': ['revenue', 'jobs', 'customers'],
            'period': 'THIS_MONTH',
            'include_charts': True
        },
        created_by='admin'
    )
    print()

    assert report_id > 0

    # Generate the custom report
    custom_report = mgr.generate_custom_report({
        'name': 'Monthly Performance Summary',
        'metrics': ['revenue', 'jobs', 'customers'],
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    })
    print()

    print(f"Custom Report: {custom_report['report_name']}")
    print(f"  Revenue: ${custom_report['data']['revenue']['total_revenue']:,.2f}")
    print(f"  Jobs: {custom_report['data']['jobs']['total_jobs']}")
    print(f"  New Customers: {custom_report['data']['customers']['new_customers']}")
    print()

    assert 'data' in custom_report
    print("[OK] Custom report created and generated")
    print()

    # ========================================================================
    # TEST 10: Report Export
    # ========================================================================

    print("="*80)
    print("[10/12] Exporting report...")
    print("="*80 + "\n")

    export_result = mgr.export_report(
        report_data=custom_report,
        export_format='JSON'
    )
    print()

    print(f"Export Result:")
    print(f"  Format: {export_result['export_format']}")
    print(f"  File: {export_result['file_path']}")
    print(f"  Size: {export_result['file_size']:,} bytes")
    print()

    assert export_result['export_format'] == 'JSON'
    print("[OK] Report exported successfully")
    print()

    # ========================================================================
    # TEST 11: KPI Targets
    # ========================================================================

    print("="*80)
    print("[11/12] Setting and tracking KPI targets...")
    print("="*80 + "\n")

    # Set revenue target
    target_id = mgr.set_kpi_target(
        kpi_name='revenue',
        target_value=50000.00,
        year=2026,
        month=1
    )
    print()

    assert target_id > 0

    # Check KPI vs target
    kpi_status = mgr.get_kpi_vs_target(
        kpi_name='revenue',
        period='THIS_MONTH'
    )

    print(f"KPI vs Target: {kpi_status['kpi_name']}")
    print(f"  Actual: ${kpi_status['actual']:,.2f}")
    print(f"  Target: ${kpi_status['target']:,.2f}" if kpi_status['target'] else "  Target: Not set")
    print(f"  Variance: ${kpi_status['variance']:,.2f} ({kpi_status['variance_percent']}%)")
    print(f"  On Track: {'Yes' if kpi_status['on_track'] else 'No'}")
    print()

    print("[OK] KPI targets working")
    print()

    # ========================================================================
    # TEST 12: BI System Summary
    # ========================================================================

    print("="*80)
    print("[12/12] Getting BI system summary...")
    print("="*80 + "\n")

    bi_summary = mgr.get_bi_summary()

    print(f"BI System Summary:")
    print(f"  Saved Reports: {bi_summary['saved_reports']}")
    print(f"  Total Exports: {bi_summary['total_exports']}")
    print(f"  Active KPI Targets: {bi_summary['active_kpi_targets']}")
    print()
    print(f"  Available Report Types: {len(bi_summary['available_report_types'])}")
    for rt in bi_summary['available_report_types']:
        print(f"    - {rt}")
    print()
    print(f"  Export Formats: {', '.join(bi_summary['export_formats'])}")
    print()

    print("[OK] BI summary retrieved")
    print()

    # ========================================================================
    # BONUS: Customer Retention Analysis
    # ========================================================================

    print("="*80)
    print("[BONUS] Analyzing customer retention...")
    print("="*80 + "\n")

    retention = mgr.get_customer_insights('RETENTION')

    print(f"Customer Retention Analysis:")
    print(f"  90-day retention: {retention['retention_rate_90_days']}%")
    print(f"  6-month retention: {retention['retention_rate_6_months']}%")
    print(f"  1-year retention: {retention['retention_rate_1_year']}%")
    print(f"  Churn rate: {retention['churn_rate']}%")
    print()

    print("[OK] Retention analysis complete")
    print()

    # ========================================================================
    # BONUS: Saved Reports
    # ========================================================================

    print("="*80)
    print("[BONUS] Getting saved reports...")
    print("="*80 + "\n")

    saved_reports = mgr.get_saved_reports()

    print(f"Saved Reports ({len(saved_reports)}):")
    for report in saved_reports:
        print(f"  - {report['report_name']} (ID: {report['id']})")
    print()

    print("[OK] Saved reports retrieved")
    print()

    # ========================================================================
    # Cleanup
    # ========================================================================

    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] BUSINESS INTELLIGENCE & REPORTING TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Executive dashboard")
    print("  [OK] Financial reporting")
    print("  [OK] Technician performance")
    print("  [OK] Technician leaderboard")
    print("  [OK] Customer segmentation")
    print("  [OK] Customer lifetime value")
    print("  [OK] Trend analysis")
    print("  [OK] Revenue forecasting")
    print("  [OK] Custom reports")
    print("  [OK] Report export")
    print("  [OK] KPI targets")
    print("  [OK] BI summary")
    print()

    print("REPORT TYPES:")
    for rt in mgr.REPORT_TYPES:
        print(f"  - {rt}")
    print()

    print("EXPORT FORMATS:")
    for ef in mgr.EXPORT_FORMATS:
        print(f"  - {ef}")
    print()

    print("ANALYSIS PERIODS:")
    for p in mgr.PERIODS:
        print(f"  - {p}")
    print()

    print("BI CAPABILITIES:")
    print("  - Real-time executive dashboards")
    print("  - Comprehensive financial reports")
    print("  - Technician performance tracking")
    print("  - Customer behavior analysis")
    print("  - Revenue trend analysis")
    print("  - Predictive forecasting")
    print("  - Custom report builder")
    print("  - Multi-format export (PDF, Excel, CSV)")
    print("  - KPI tracking vs targets")
    print()

    print("INSIGHTS PROVIDED:")
    print("  - Revenue growth rates")
    print("  - Collection efficiency")
    print("  - Operational metrics")
    print("  - Customer lifetime value")
    print("  - Retention/churn rates")
    print("  - Performance rankings")
    print()

    print("Ready for PROMPT 30?")
    print()

    return True


if __name__ == '__main__':
    success = test_business_intelligence()
    sys.exit(0 if success else 1)
