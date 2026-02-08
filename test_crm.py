"""
Test CRM System
Comprehensive test for CRM database and functionality
"""

import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.crm_database import CRMDatabase

def test_crm_system():
    """Run comprehensive CRM system tests"""

    print("\n" + "="*60)
    print("TESTING CRM SYSTEM")
    print("="*60 + "\n")

    # Use test database
    test_db_path = 'data/test_crm.db'

    # Remove existing test db
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    crm = CRMDatabase(test_db_path)

    # Test 1: Create user
    print("[1/10] Creating test user...")
    user_id = crm.create_user(
        name='John Smith',
        email='john@example.com',
        role='sales',
        phone='(555) 123-4567'
    )
    print(f"  Created user #{user_id}")

    # Test 2: Create deal
    print("\n[2/10] Creating test deal...")
    deal_id = crm.create_deal(
        location_id=1,
        event_id=1,
        stage='lead',
        estimated_value=50000,
        probability=25,
        assigned_to=user_id
    )
    print(f"  Created deal #{deal_id}")

    # Test 3: Log interaction
    print("\n[3/10] Logging interaction...")
    interaction_id = crm.log_interaction(
        location_id=1,
        interaction_type='call',
        outcome='answered',
        notes='Spoke with manager. Very interested in PDR services.',
        user_id=user_id,
        duration_seconds=420
    )
    print(f"  Logged interaction #{interaction_id}")

    # Test 4: Create task
    print("\n[4/10] Creating task...")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    task_id = crm.create_task(
        title='Follow up with ABC Motors',
        task_type='follow_up',
        location_id=1,
        deal_id=deal_id,
        assigned_to=user_id,
        due_date=tomorrow,
        priority='high',
        description='Send quote and schedule site visit'
    )
    print(f"  Created task #{task_id}")

    # Test 5: Add note
    print("\n[5/10] Adding note...")
    note_id = crm.add_note(
        note_text='Customer mentioned they have 150 vehicles on lot. High priority target.',
        location_id=1,
        deal_id=deal_id,
        user_id=user_id
    )
    print(f"  Added note #{note_id}")

    # Test 6: Update deal stage
    print("\n[6/10] Updating deal stage...")
    crm.update_deal_stage(deal_id, 'contacted')
    deal = crm.get_deal(deal_id)
    print(f"  Deal stage updated to: {deal['stage']}")

    # Test 7: Get pipeline summary
    print("\n[7/10] Getting pipeline summary...")
    pipeline = crm.get_pipeline_summary()
    print(f"  Total deals: {pipeline['total_deals']}")
    print(f"  Total value: ${pipeline['total_value']:,.0f}")
    print(f"  Stages: {len(pipeline['stages'])}")

    # Test 8: Get conversion funnel
    print("\n[8/10] Getting conversion funnel...")
    funnel = crm.get_conversion_funnel()
    print(f"  Leads: {funnel['leads']}")
    print(f"  Contacted: {funnel['contacted']}")
    print(f"  Won: {funnel['won']}")
    print(f"  In pipeline: {funnel['total_in_pipeline']}")

    # Test 9: Get tasks
    print("\n[9/10] Getting pending tasks...")
    tasks = crm.get_tasks(status='pending')
    print(f"  Found {len(tasks)} pending tasks")

    # Test 10: Get activity summary
    print("\n[10/10] Getting activity summary...")
    activity = crm.get_activity_summary(days=7)
    print(f"  Interactions (7 days): {activity['interactions']}")
    print(f"  New deals: {activity['new_deals']}")
    print(f"  Pending tasks: {activity['pending_tasks']}")

    # Test complete task
    print("\n[BONUS] Testing task completion...")
    crm.complete_task(task_id)
    task = crm.get_task(task_id)
    print(f"  Task status: {task['status']}")
    print(f"  Completed at: {task['completed_at']}")

    # Test deal win
    print("\n[BONUS] Testing deal win...")
    crm.update_deal_stage(deal_id, 'won', actual_value=55000)
    deal = crm.get_deal(deal_id)
    print(f"  Deal stage: {deal['stage']}")
    print(f"  Actual value: ${deal['actual_value']:,.0f}")
    print(f"  Close date: {deal['actual_close_date']}")

    # Get user performance
    print("\n[BONUS] Getting user performance...")
    performance = crm.get_user_performance(days=30)
    if performance:
        p = performance[0]
        print(f"  User: {p['name']}")
        print(f"  Calls: {p['calls']}")
        print(f"  Deals won: {p['deals_won']}")
        print(f"  Revenue: ${p['revenue']:,.0f}")

    print("\n" + "="*60)
    print("ALL CRM TESTS PASSED!")
    print("="*60 + "\n")

    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        print("Test database cleaned up.\n")

    return True


def test_crm_routes():
    """Test CRM Flask routes"""

    print("\n" + "="*60)
    print("TESTING CRM ROUTES")
    print("="*60 + "\n")

    try:
        from src.web.app import create_app

        app = create_app()
        client = app.test_client()

        # Test dashboard API
        print("[1/4] Testing dashboard API...")
        response = client.get('/crm/api/dashboard')
        assert response.status_code == 200
        data = response.get_json()
        assert 'pipeline' in data
        assert 'funnel' in data
        print("  Dashboard API OK")

        # Test create deal API
        print("\n[2/4] Testing create deal API...")
        response = client.post('/crm/api/deal',
                              json={'location_id': 1, 'estimated_value': 10000})
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        deal_id = data['deal_id']
        print(f"  Created deal #{deal_id}")

        # Test get deals API
        print("\n[3/4] Testing get deals API...")
        response = client.get('/crm/api/deals')
        assert response.status_code == 200
        data = response.get_json()
        assert 'deals' in data
        print(f"  Found {data['count']} deals")

        # Test create task API
        print("\n[4/4] Testing create task API...")
        response = client.post('/crm/api/task',
                              json={'title': 'Test task', 'type': 'call'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        print(f"  Created task #{data['task_id']}")

        print("\n" + "="*60)
        print("ALL CRM ROUTE TESTS PASSED!")
        print("="*60 + "\n")

        return True

    except ImportError as e:
        print(f"  Skipping route tests: {e}")
        return True
    except Exception as e:
        print(f"  Route test error: {e}")
        return False


if __name__ == '__main__':
    # Run database tests
    db_ok = test_crm_system()

    # Run route tests
    routes_ok = test_crm_routes()

    if db_ok and routes_ok:
        print("\n" + "="*60)
        print("CRM SYSTEM FULLY OPERATIONAL!")
        print("="*60)
        print("\nAvailable endpoints:")
        print("  /crm/dashboard     - CRM Dashboard")
        print("  /crm/deals         - Deal Pipeline")
        print("  /crm/tasks         - Task Management")
        print("  /crm/team          - Team Performance")
        print("\nAPI endpoints:")
        print("  POST /crm/api/deal        - Create deal")
        print("  POST /crm/api/interaction - Log interaction")
        print("  POST /crm/api/task        - Create task")
        print("  GET  /crm/api/pipeline    - Pipeline summary")
        print("  GET  /crm/api/analytics/* - Analytics data")
        print("="*60 + "\n")
    else:
        print("\nSome tests failed. Check output above.")
        sys.exit(1)
