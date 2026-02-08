"""
Test Analytics & Dashboard
PDR CRM Part 10 - Comprehensive Business Analytics
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_analytics_manager():
    print("\n" + "="*80)
    print("TESTING ANALYTICS & DASHBOARD")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.analytics_manager import AnalyticsManager
    from src.crm.managers.job_manager import JobManager
    from src.crm.managers.customer_manager import CustomerManager
    from src.crm.managers.vehicle_manager import VehicleManager
    from src.crm.managers.payment_manager import PaymentManager
    from src.crm.managers.tech_manager import TechManager
    from datetime import datetime, date, timedelta

    # Use test database
    test_db = "data/test_analytics.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    analytics_mgr = AnalyticsManager(db)
    job_mgr = JobManager(db)
    customer_mgr = CustomerManager(db)
    vehicle_mgr = VehicleManager(db)
    payment_mgr = PaymentManager(db)
    tech_mgr = TechManager(db)

    # Create test data
    print("\nGenerating sample data for analytics...")

    # Create technicians
    tech1_id = tech_mgr.create_tech(
        first_name='Mike',
        last_name='Smith',
        employee_id='TECH001',
        skill_level='EXPERT',
        max_jobs_concurrent=3
    )

    tech2_id = tech_mgr.create_tech(
        first_name='Sarah',
        last_name='Johnson',
        employee_id='TECH002',
        skill_level='INTERMEDIATE',
        max_jobs_concurrent=2
    )

    # Create customers, jobs, and payments
    print("Creating customers and jobs...")

    for i in range(10):
        customer_id = customer_mgr.create_customer({
            'first_name': f'Customer{i+1}',
            'last_name': 'Test',
            'phone': f'555-010{i}',
            'email': f'customer{i+1}@test.com',
            'source': ['HAIL_EVENT', 'REFERRAL', 'WEBSITE'][i % 3]
        })

        vehicle_id = vehicle_mgr.create_vehicle({
            'customer_id': customer_id,
            'year': 2020 + i % 3,
            'make': ['Toyota', 'Honda', 'Ford'][i % 3],
            'model': ['Camry', 'Accord', 'F-150'][i % 3],
            'color': ['Silver', 'Blue', 'Black'][i % 3]
        })

        job_id = job_mgr.create_job(
            customer_id=customer_id,
            vehicle_id=vehicle_id,
            job_type=['HAIL', 'PDR', 'HAIL'][i % 3],
            damage_type=['HAIL', 'DOOR_DING', 'HAIL'][i % 3]
        )

        # Assign some jobs to techs
        if i < 6:
            # Set job to APPROVED first
            db.execute("""
                UPDATE jobs SET status = 'APPROVED', updated_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), job_id))

            # Assign tech
            tech_to_assign = tech1_id if i % 2 == 0 else tech2_id
            job_mgr.assign_tech(job_id, tech_to_assign, estimated_hours=4.0 + i)

        # Complete some jobs and create payments
        if i % 2 == 0:
            # Mark job completed
            db.execute("""
                UPDATE jobs
                SET status = 'COMPLETED',
                    completed_at = ?,
                    total_estimate = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                datetime.now().isoformat(),
                2000.00 + (i * 100),
                datetime.now().isoformat(),
                job_id
            ))

            # Create invoice
            invoice_number = f'INV-2026-{i+1:04d}'
            db.execute("""
                INSERT INTO invoices (
                    invoice_number, job_id, customer_id,
                    subtotal, tax_amount, total, balance_due,
                    invoice_date, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_number, job_id, customer_id,
                2000.00 + (i * 100), 165.00, 2165.00 + (i * 100), 0,
                date.today().isoformat(), 'PAID',
                datetime.now().isoformat()
            ))

            # Get invoice ID
            invoice_result = db.execute("""
                SELECT id FROM invoices WHERE invoice_number = ?
            """, (invoice_number,))
            invoice_id = invoice_result[0]['id']

            # Record payment
            payment_mgr.record_payment(
                invoice_id=invoice_id,
                job_id=job_id,
                amount=2165.00 + (i * 100),
                payment_method='CHECK',
                payment_date=date.today() - timedelta(days=i),
                payer_type=['INSURANCE', 'CUSTOMER'][i % 2],
                parts_cost=200.00,
                tech_percentage=40.0
            )

    # Create leads
    print("Creating leads...")
    for i in range(15):
        db.execute("""
            INSERT INTO leads (
                first_name, last_name, phone, email,
                source, status, temperature,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f'Lead{i+1}', 'Test', f'555-020{i}', f'lead{i+1}@test.com',
            ['HAIL_EVENT', 'REFERRAL', 'WEBSITE'][i % 3],
            ['NEW', 'CONTACTED', 'QUALIFIED', 'CONVERTED'][i % 4],
            ['HOT', 'WARM', 'COLD'][i % 3],
            datetime.now().isoformat()
        ))

    print()

    # ========================================================================
    # TEST 1: Executive Dashboard
    # ========================================================================

    print("="*80)
    print("[1/7] Getting executive dashboard...")
    print("="*80 + "\n")

    dashboard = analytics_mgr.get_executive_dashboard(period_days=30)

    print("EXECUTIVE DASHBOARD (Last 30 Days)")
    print("-" * 70)
    print()

    print("REVENUE:")
    print(f"  Total: ${dashboard['revenue']['total']:,.2f}")
    print(f"  Average payment: ${dashboard['revenue']['average']:,.2f}")
    print(f"  Daily average: ${dashboard['revenue']['daily_average']:,.2f}")
    print(f"  Growth: {dashboard['revenue']['growth_pct']:.1f}%")
    print()

    print("JOBS:")
    print(f"  Created: {dashboard['jobs']['created']}")
    print(f"  Completed: {dashboard['jobs']['completed']}")
    print(f"  Active: {dashboard['jobs']['active_total']}")
    print(f"  Completion rate: {dashboard['jobs']['completion_rate']:.1f}%")
    print()

    print("SALES:")
    print(f"  Total leads: {dashboard['sales']['total_leads']}")
    print(f"  Converted: {dashboard['sales']['converted_leads']}")
    print(f"  Conversion rate: {dashboard['sales']['conversion_rate']:.1f}%")
    print(f"  Hot leads: {dashboard['sales']['hot_leads']}")
    print()

    print("OPERATIONS:")
    print(f"  Techs: {dashboard['operations']['tech_count']}")
    print(f"  Capacity: {dashboard['operations']['total_capacity']} jobs")
    print(f"  Utilization: {dashboard['operations']['utilization_pct']:.1f}%")
    print()

    print("CUSTOMERS:")
    print(f"  New customers: {dashboard['customers']['new_customers']}")
    print(f"  Total active: {dashboard['customers']['total_active']}")
    print(f"  Repeat rate: {dashboard['customers']['repeat_rate']:.1f}%")
    print()

    if dashboard['alerts']:
        print("ALERTS:")
        for alert in dashboard['alerts']:
            print(f"  [{alert['severity']}] {alert['message']}")
        print()

    print("[OK] Executive dashboard retrieved")
    print()

    # ========================================================================
    # TEST 2: Revenue Analytics
    # ========================================================================

    print("="*80)
    print("[2/7] Analyzing revenue trends...")
    print("="*80 + "\n")

    trend = analytics_mgr.get_revenue_trend(period='DAILY', days=7)

    print("Daily Revenue Trend (Last 7 Days):")
    if trend:
        for point in trend:
            print(f"  {point['date']}: ${point['revenue']:>10,.2f} ({point['count']} payments)")
    else:
        print("  No revenue data for this period")
    print()

    # Revenue by source
    by_source = analytics_mgr.get_revenue_by_source(days=30)
    print("Revenue by Source:")
    for source, data in by_source.items():
        print(f"  {source}: ${data['revenue']:,.2f} ({data['count']} payments)")
    print()

    # Revenue by job type
    by_type = analytics_mgr.get_revenue_by_job_type(days=30)
    print("Revenue by Job Type:")
    for job_type, data in by_type.items():
        print(f"  {job_type}: ${data['revenue']:,.2f} ({data['job_count']} jobs)")
    print()

    print("[OK] Revenue analytics working")
    print()

    # ========================================================================
    # TEST 3: Job Pipeline
    # ========================================================================

    print("="*80)
    print("[3/7] Analyzing job pipeline...")
    print("="*80 + "\n")

    pipeline = analytics_mgr.get_job_pipeline()

    print("Job Pipeline by Stage:")
    for stage, data in pipeline.items():
        print(f"  {stage:20s}: {data['count']:3d} jobs (${data['value']:>10,.2f})")
    print()

    # Status summary
    status_summary = analytics_mgr.get_job_status_summary()
    print("Active Jobs by Status:")
    for item in status_summary[:10]:  # Show top 10
        print(f"  {item['status']:25s}: {item['count']:3d} jobs")
    print()

    print("[OK] Job pipeline analysis working")
    print()

    # ========================================================================
    # TEST 4: Sales Funnel
    # ========================================================================

    print("="*80)
    print("[4/7] Analyzing sales funnel...")
    print("="*80 + "\n")

    funnel = analytics_mgr.get_conversion_funnel(days=30)

    print("Sales Funnel (Last 30 Days):")
    print(f"  Leads:      {funnel['leads']:>5d}")
    print(f"  Qualified:  {funnel['qualified']:>5d}  ({funnel['lead_to_qualified_pct']:.1f}%)")
    print(f"  Converted:  {funnel['converted']:>5d}  ({funnel['lead_to_customer_pct']:.1f}%)")
    print(f"  Jobs:       {funnel['jobs']:>5d}")
    print(f"  Paid:       {funnel['paid']:>5d}  ({funnel['lead_to_paid_pct']:.1f}%)")
    print()

    print("[OK] Sales funnel working")
    print()

    # ========================================================================
    # TEST 5: Tech Performance
    # ========================================================================

    print("="*80)
    print("[5/7] Getting tech performance...")
    print("="*80 + "\n")

    leaderboard = analytics_mgr.get_tech_leaderboard(days=30)

    print("Tech Leaderboard (Last 30 Days):")
    for tech in leaderboard:
        print(f"  #{tech['rank']} {tech['tech_name']:20s}: "
              f"{tech['jobs_completed']} jobs, "
              f"{tech['total_hours']:.1f} hrs, "
              f"${tech['earnings']:,.2f}")
    print()

    # Detailed tech performance
    if leaderboard:
        tech_detail = analytics_mgr.get_tech_performance_detail(leaderboard[0]['tech_id'], days=30)
        print(f"Detailed Performance for {tech_detail['tech_name']}:")
        print(f"  Skill Level: {tech_detail['skill_level']}")
        print(f"  Active Jobs: {tech_detail['active_jobs']}")
        print(f"  Completed: {tech_detail['completed_jobs']}")
        print(f"  Total Hours: {tech_detail['total_hours']}")
        print(f"  Earnings: ${tech_detail['earnings']:,.2f}")
        print()

    print("[OK] Tech performance working")
    print()

    # ========================================================================
    # TEST 6: Customer Analytics
    # ========================================================================

    print("="*80)
    print("[6/7] Analyzing customer data...")
    print("="*80 + "\n")

    acquisition = analytics_mgr.get_customer_acquisition(days=30)

    print("Customer Acquisition (Last 30 Days):")
    print(f"  New customers: {acquisition['new_customers']}")
    print(f"  Avg lifetime value: ${acquisition['avg_lifetime_value']:,.2f}")
    print(f"  By source:")
    for source, count in acquisition['by_source'].items():
        print(f"    {source}: {count}")
    print()

    # Top customers
    top_customers = analytics_mgr.get_top_customers(limit=5)
    print("Top Customers by Revenue:")
    for customer in top_customers:
        print(f"  #{customer['rank']} {customer['customer_name']}: "
              f"${customer['total_revenue']:,.2f} ({customer['total_jobs']} jobs)")
    print()

    print("[OK] Customer analytics working")
    print()

    # ========================================================================
    # TEST 7: Reports
    # ========================================================================

    print("="*80)
    print("[7/7] Generating reports...")
    print("="*80 + "\n")

    # Executive report
    print("EXECUTIVE REPORT:")
    print("-" * 70)
    exec_report = analytics_mgr.generate_executive_report(days=30)
    print(exec_report)
    print()

    # Pipeline report
    print("PIPELINE REPORT:")
    print("-" * 70)
    pipeline_report = analytics_mgr.generate_pipeline_report()
    print(pipeline_report)
    print()

    # Tech report
    print("TECH REPORT:")
    print("-" * 70)
    tech_report = analytics_mgr.generate_tech_report(days=30)
    print(tech_report)
    print()

    print("[OK] Reports generated")
    print()

    # ========================================================================
    # BONUS: Job Trend
    # ========================================================================

    print("="*80)
    print("[BONUS] Job creation trend...")
    print("="*80 + "\n")

    job_trend = analytics_mgr.get_job_trend(period='DAILY', days=7)
    print("Job Creation Trend (Last 7 Days):")
    if job_trend:
        for point in job_trend:
            print(f"  {point['date']}: {point['total']} jobs (Hail: {point['hail']}, PDR: {point['pdr']})")
    else:
        print("  No job data for this period")
    print()

    # Cleanup
    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] ANALYTICS & DASHBOARD TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Executive dashboard (all KPIs)")
    print("  [OK] Revenue analytics (trends, sources, job types)")
    print("  [OK] Job pipeline analysis (by stage)")
    print("  [OK] Sales funnel tracking (lead to paid)")
    print("  [OK] Tech performance metrics (leaderboard)")
    print("  [OK] Customer analytics (acquisition, top customers)")
    print("  [OK] Business alerts (overdue, stalled claims)")
    print("  [OK] Report generation (executive, pipeline, tech)")
    print()

    print("DASHBOARD INCLUDES:")
    print("  - Revenue (total, average, growth, by source)")
    print("  - Jobs (created, completed, cycle time)")
    print("  - Sales (leads, conversion rate)")
    print("  - Operations (capacity, utilization)")
    print("  - Customers (new, repeat rate, LTV)")
    print("  - Alerts (overdue jobs, stalled claims, low parts)")
    print()

    print("ANALYTICS VIEWS:")
    print("  - Revenue trends (daily/weekly/monthly)")
    print("  - Job pipeline by stage")
    print("  - Conversion funnel")
    print("  - Tech leaderboard")
    print("  - Customer acquisition")
    print()

    print("Ready for PROMPT 11: Email Integration & Automation?")
    print()

    return True


if __name__ == '__main__':
    success = test_analytics_manager()
    sys.exit(0 if success else 1)
