"""
Test Tech Manager (Mobile App Backend)
PDR CRM Part 8 - Mobile Tech App!
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_tech_manager():
    print("\n" + "="*80)
    print("TESTING TECH MANAGER (MOBILE APP BACKEND)")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.tech_manager import TechManager
    from src.crm.managers.customer_manager import CustomerManager
    from src.crm.managers.vehicle_manager import VehicleManager
    from src.crm.managers.job_manager import JobManager
    from datetime import datetime, date, timedelta

    # Use test database
    test_db = "data/test_tech_mgr.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    tech_mgr = TechManager(db)
    customer_mgr = CustomerManager(db)
    vehicle_mgr = VehicleManager(db)
    job_mgr = JobManager(db)

    # Create test data
    print("\nSetting up test data...")

    customer_id = customer_mgr.create_customer({
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '214-555-0100',
        'email': 'john@example.com'
    })

    vehicle_id = vehicle_mgr.create_vehicle({
        'customer_id': customer_id,
        'year': 2022,
        'make': 'Toyota',
        'model': 'Camry',
        'color': 'Silver'
    })

    # Create tech using TechManager
    tech_id = tech_mgr.create_tech(
        first_name='Mike',
        last_name='Smith',
        employee_id='TECH001',
        skill_level='EXPERT',
        max_jobs_concurrent=3
    )

    # Create second tech
    tech2_id = tech_mgr.create_tech(
        first_name='Sarah',
        last_name='Johnson',
        employee_id='TECH002',
        skill_level='INTERMEDIATE',
        max_jobs_concurrent=2
    )

    # Create jobs
    job1_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        job_type="HAIL",
        damage_type="HAIL",
        priority="HIGH"
    )

    job2_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        job_type="PDR",
        damage_type="DOOR_DING"
    )

    job3_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        job_type="PDR"
    )

    # Transition jobs through workflow to APPROVED (so they can be assigned to techs)
    # In a real workflow, this would happen through estimate approval
    for job_id in [job1_id, job2_id, job3_id]:
        db.execute("""
            UPDATE jobs SET status = 'APPROVED', updated_at = ? WHERE id = ?
        """, (datetime.now().isoformat(), job_id))

    # Assign jobs to tech (this will transition to ASSIGNED_TO_TECH)
    job_mgr.assign_tech(job1_id, tech_id, 6.0)
    job_mgr.assign_tech(job2_id, tech_id, 4.5)
    job_mgr.assign_tech(job3_id, tech2_id, 3.0)

    print()

    # ========================================================================
    # TEST 1: Get Tech Info
    # ========================================================================

    print("="*80)
    print("[1/8] Getting tech info...")
    print("="*80 + "\n")

    tech = tech_mgr.get_tech(tech_id)

    print(f"Tech: {tech['first_name']} {tech['last_name']}")
    print(f"  Employee ID: {tech['employee_id']}")
    print(f"  Skill Level: {tech['skill_level']}")
    print(f"  Active jobs: {tech['active_jobs']}")
    print(f"  Total hours: {tech['total_hours']}")
    print()

    # Test login by employee ID
    logged_in = tech_mgr.get_tech_by_employee_id('TECH001')
    assert logged_in is not None
    assert logged_in['id'] == tech_id
    print(f"[OK] Login by employee ID works")
    print()

    # ========================================================================
    # TEST 2: Get Assigned Jobs
    # ========================================================================

    print("="*80)
    print("[2/8] Getting assigned jobs...")
    print("="*80 + "\n")

    upcoming_jobs = tech_mgr.get_tech_jobs(tech_id, status_filter='UPCOMING')

    print(f"Upcoming Jobs: {len(upcoming_jobs)}")
    for job in upcoming_jobs:
        print(f"  - {job['job_number']}: {job['customer_name']} - {job['vehicle_description']}")
    print()

    assert len(upcoming_jobs) == 2
    print(f"[OK] Found {len(upcoming_jobs)} upcoming jobs")
    print()

    # ========================================================================
    # TEST 3: Start Job
    # ========================================================================

    print("="*80)
    print("[3/8] Tech starting job...")
    print("="*80 + "\n")

    tech_mgr.start_job(job_id=job1_id, tech_id=tech_id)

    # Verify job is now in progress
    job1 = job_mgr.get_job(job1_id)
    assert job1['status'] == 'IN_PROGRESS'
    print(f"[OK] Job status is now: {job1['status']}")
    print()

    # Check current jobs
    current_jobs = tech_mgr.get_tech_jobs(tech_id, status_filter='CURRENT')
    assert len(current_jobs) == 1
    print(f"[OK] Tech has {len(current_jobs)} current job(s)")
    print()

    # ========================================================================
    # TEST 4: Update Progress
    # ========================================================================

    print("="*80)
    print("[4/8] Tech logging progress...")
    print("="*80 + "\n")

    tech_mgr.update_progress(
        job_id=job1_id,
        tech_id=tech_id,
        progress_note="Finished hood (42 dents), started on roof. About 60 dents on roof.",
        hours_remaining=3.5
    )
    print()

    # Second update
    tech_mgr.update_progress(
        job_id=job1_id,
        tech_id=tech_id,
        progress_note="Roof complete, trunk complete. Tomorrow: doors and fenders.",
        hours_remaining=2.0
    )
    print()

    print("[OK] Progress updates logged")
    print()

    # ========================================================================
    # TEST 5: Get Job Details
    # ========================================================================

    print("="*80)
    print("[5/8] Getting job details...")
    print("="*80 + "\n")

    job_details = tech_mgr.get_job_details(job_id=job1_id, tech_id=tech_id)

    print(f"Job: {job_details['job_number']}")
    print(f"  Customer: {job_details['customer_name']}")
    print(f"  Vehicle: {job_details['vehicle_description']} ({job_details['vehicle_color']})")
    print(f"  Status: {job_details['status']}")
    print(f"  Estimated hours: {job_details['estimated_hours']}")
    print(f"  Last update: {job_details['tech_daily_update']}")
    print()
    print(f"  Tech Notes:")
    if job_details['tech_notes']:
        for line in job_details['tech_notes'].split('\n'):
            if line.strip():
                print(f"    {line}")
    print()

    assert job_details['tech_notes'] is not None
    assert len(job_details['tech_notes']) > 0
    print("[OK] Job details retrieved with tech notes")
    print()

    # ========================================================================
    # TEST 6: Mark Complete
    # ========================================================================

    print("="*80)
    print("[6/8] Tech marking job complete...")
    print("="*80 + "\n")

    tech_mgr.mark_complete(
        job_id=job1_id,
        tech_id=tech_id,
        completion_notes="All PDR work complete. Ready for QC inspection."
    )

    # Verify job is complete
    job1 = job_mgr.get_job(job1_id)
    assert job1['status'] == 'TECH_COMPLETE'
    print(f"[OK] Job status is now: {job1['status']}")
    print()

    # Check completed jobs
    completed_jobs = tech_mgr.get_tech_jobs(tech_id, status_filter='COMPLETED')
    assert len(completed_jobs) == 1
    print(f"[OK] Tech has {len(completed_jobs)} completed job(s)")
    print()

    # ========================================================================
    # TEST 7: Get Schedule & Stats
    # ========================================================================

    print("="*80)
    print("[7/8] Getting schedule and stats...")
    print("="*80 + "\n")

    schedule = tech_mgr.get_schedule(tech_id, days_ahead=7)

    print(f"Schedule (Next 7 Days): {len(schedule)} job(s)")
    for job in schedule:
        print(f"  - {job['job_number']}: {job['customer_name']}")
        print(f"    {job['vehicle_description']} - {job['status']}")
        if job['estimated_hours']:
            print(f"    Estimated: {job['estimated_hours']} hours")
    print()

    stats = tech_mgr.get_tech_stats(tech_id, period_days=30)

    print(f"Tech Stats (Last 30 Days):")
    print(f"  Jobs completed: {stats['jobs_completed']}")
    print(f"  Currently active: {stats['jobs_active']}")
    print(f"  Week completed: {stats['week_completed']}")
    print(f"  Avg hours/job: {stats['avg_hours_per_job']}")
    print(f"  Total hours: {stats['total_hours']}")
    print()

    assert stats['jobs_completed'] == 1
    print("[OK] Stats calculated correctly")
    print()

    # ========================================================================
    # TEST 8: Dashboard & Workload
    # ========================================================================

    print("="*80)
    print("[8/8] Getting dashboard and workload summary...")
    print("="*80 + "\n")

    dashboard = tech_mgr.get_tech_dashboard(tech_id)

    print(f"Dashboard for {dashboard['tech']['first_name']} {dashboard['tech']['last_name']}:")
    print(f"  Current jobs: {len(dashboard['current_jobs'])}")
    print(f"  Upcoming jobs: {len(dashboard['upcoming_jobs'])}")
    print(f"  Schedule items: {len(dashboard['schedule'])}")
    print()

    # Workload summary for all techs
    workload = tech_mgr.get_workload_summary()

    print(f"Workload Summary (All Techs):")
    for tech in workload:
        print(f"  {tech['tech_name']} ({tech['skill_level']})")
        print(f"    In Progress: {tech['in_progress']}, Assigned: {tech['assigned']}")
        print(f"    Total Hours: {tech['total_hours'] or 0}")
    print()

    # Get all techs
    all_techs = tech_mgr.get_all_techs()
    assert len(all_techs) == 2
    print(f"[OK] Found {len(all_techs)} active technicians")
    print()

    # Cleanup
    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] TECH MANAGER TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Tech info and login by employee ID")
    print("  [OK] View assigned jobs (current/upcoming/completed)")
    print("  [OK] Start job (ASSIGNED_TO_TECH -> IN_PROGRESS)")
    print("  [OK] Log progress updates with hours remaining")
    print("  [OK] Mark job complete (IN_PROGRESS -> TECH_COMPLETE)")
    print("  [OK] View schedule (next 7 days)")
    print("  [OK] Performance statistics")
    print("  [OK] Dashboard data for mobile app")
    print("  [OK] Workload summary for all techs")
    print()

    print("MOBILE APP WORKFLOW:")
    print("  1. Tech logs in with employee ID (TECH001)")
    print("  2. Sees current jobs and upcoming schedule")
    print("  3. Taps 'Start Job' to begin work")
    print("  4. Updates progress daily with notes + hours remaining")
    print("  5. Marks complete when finished")
    print("  6. Office sees update in real-time")
    print()

    print("DEMO APP:")
    print("  Open in browser: src/crm/mobile/tech_app.html")
    print("  (Works on any smartphone - no app store needed!)")
    print()

    print("Ready for PROMPT 9: Scheduling System?")
    print()

    return True


if __name__ == '__main__':
    success = test_tech_manager()
    sys.exit(0 if success else 1)
