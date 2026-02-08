"""
Seed CRM with Demo Data
Creates realistic sample data for testing the CRM dashboard
"""

import os
import sys
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.crm_database import CRMDatabase

def seed_demo_data():
    print("\n" + "="*60)
    print("SEEDING CRM DEMO DATA")
    print("="*60 + "\n")

    db_path = 'data/hailtracker_crm.db'
    crm = CRMDatabase(db_path)

    # ========================================
    # 1. CREATE USERS (Team Members)
    # ========================================
    print("[1/6] Creating team members...")

    users = [
        {'name': 'Kyle Thompson', 'email': 'kyle@hailtracker.pro', 'role': 'admin', 'phone': '(405) 555-0100'},
        {'name': 'Mike Rodriguez', 'email': 'mike@hailtracker.pro', 'role': 'sales', 'phone': '(405) 555-0101'},
        {'name': 'Sarah Johnson', 'email': 'sarah@hailtracker.pro', 'role': 'sales', 'phone': '(405) 555-0102'},
        {'name': 'David Chen', 'email': 'david@hailtracker.pro', 'role': 'technician', 'phone': '(405) 555-0103'},
        {'name': 'Jessica Williams', 'email': 'jessica@hailtracker.pro', 'role': 'manager', 'phone': '(405) 555-0104'},
    ]

    user_ids = []
    for user in users:
        try:
            user_id = crm.create_user(**user)
            user_ids.append(user_id)
            print(f"   Created: {user['name']} ({user['role']})")
        except Exception as e:
            # User might already exist
            print(f"   Skipped: {user['name']} (already exists)")
            user_ids.append(1)

    # ========================================
    # 2. CREATE DEALS (Pipeline)
    # ========================================
    print("\n[2/6] Creating deals...")

    # Sample dealership/fleet data
    deals_data = [
        # Leads
        {'location_id': 1, 'stage': 'lead', 'value': 45000, 'prob': 15, 'name': 'AutoNation Toyota'},
        {'location_id': 2, 'stage': 'lead', 'value': 32000, 'prob': 20, 'name': 'Budget Car Rental'},
        {'location_id': 3, 'stage': 'lead', 'value': 28000, 'prob': 10, 'name': 'Enterprise Fleet'},

        # Contacted
        {'location_id': 4, 'stage': 'contacted', 'value': 55000, 'prob': 35, 'name': 'John Smith Chevrolet'},
        {'location_id': 5, 'stage': 'contacted', 'value': 41000, 'prob': 30, 'name': 'Hertz Local'},
        {'location_id': 6, 'stage': 'contacted', 'value': 38000, 'prob': 25, 'name': 'City Fleet Services'},

        # Qualified
        {'location_id': 7, 'stage': 'qualified', 'value': 72000, 'prob': 50, 'name': 'Hendrick BMW'},
        {'location_id': 8, 'stage': 'qualified', 'value': 48000, 'prob': 55, 'name': 'Avis Premium'},
        {'location_id': 9, 'stage': 'qualified', 'value': 35000, 'prob': 45, 'name': 'Municipal Fleet'},

        # Quoted
        {'location_id': 10, 'stage': 'quoted', 'value': 85000, 'prob': 70, 'name': 'Sewell Lexus'},
        {'location_id': 11, 'stage': 'quoted', 'value': 62000, 'prob': 75, 'name': 'National Car Rental'},
        {'location_id': 12, 'stage': 'quoted', 'value': 44000, 'prob': 65, 'name': 'State Farm Fleet'},

        # Negotiating
        {'location_id': 13, 'stage': 'negotiating', 'value': 95000, 'prob': 85, 'name': 'Park Place Mercedes'},
        {'location_id': 14, 'stage': 'negotiating', 'value': 58000, 'prob': 80, 'name': 'Dollar Rent A Car'},

        # Won (Closed)
        {'location_id': 15, 'stage': 'won', 'value': 78000, 'prob': 100, 'name': 'AutoNation Honda', 'actual': 82000},
        {'location_id': 16, 'stage': 'won', 'value': 45000, 'prob': 100, 'name': 'Enterprise OKC', 'actual': 47500},
        {'location_id': 17, 'stage': 'won', 'value': 33000, 'prob': 100, 'name': 'Landers Toyota', 'actual': 35200},

        # Lost
        {'location_id': 18, 'stage': 'lost', 'value': 52000, 'prob': 0, 'name': 'Competitor Won'},
    ]

    deal_ids = []
    for deal in deals_data:
        days_ago = random.randint(3, 45)
        deal_id = crm.create_deal(
            location_id=deal['location_id'],
            event_id=random.randint(1, 5),
            stage=deal['stage'],
            estimated_value=deal['value'],
            probability=deal['prob'],
            assigned_to=random.choice(user_ids[:3])
        )
        deal_ids.append(deal_id)

        # Update won deals with actual values
        if deal['stage'] == 'won':
            crm.update_deal_stage(deal_id, 'won', actual_value=deal.get('actual', deal['value']))

        print(f"   Created: {deal['name']} - ${deal['value']:,} ({deal['stage']})")

    # ========================================
    # 3. CREATE INTERACTIONS
    # ========================================
    print("\n[3/6] Creating interactions...")

    interaction_types = ['call', 'email', 'visit', 'sms', 'note']
    outcomes = ['answered', 'voicemail', 'no_answer', 'meeting_scheduled', 'quoted', 'declined']

    interaction_count = 0
    for location_id in range(1, 19):
        # Create 2-8 interactions per location
        num_interactions = random.randint(2, 8)

        for i in range(num_interactions):
            days_ago = random.randint(1, 60)
            int_type = random.choice(interaction_types)

            crm.log_interaction(
                location_id=location_id,
                interaction_type=int_type,
                outcome=random.choice(outcomes) if int_type in ['call', 'email', 'visit'] else None,
                notes=random.choice([
                    'Discussed hail damage repair options',
                    'Scheduled site visit for assessment',
                    'Sent quote via email',
                    'Manager was interested, will follow up',
                    'Left voicemail with contact info',
                    'Met with fleet manager on-site',
                    'Reviewed damage photos together',
                    'Negotiating pricing terms',
                    'Customer requested references',
                    None
                ]),
                user_id=random.choice(user_ids),
                duration_seconds=random.randint(60, 900) if int_type == 'call' else None,
                next_followup_date=(datetime.now() + timedelta(days=random.randint(1, 14))).strftime('%Y-%m-%d') if random.random() > 0.5 else None
            )
            interaction_count += 1

    print(f"   Created {interaction_count} interactions")

    # ========================================
    # 4. CREATE TASKS
    # ========================================
    print("\n[4/6] Creating tasks...")

    tasks_data = [
        {'title': 'Follow up with John Smith Chevrolet', 'type': 'call', 'priority': 'high', 'days': 1},
        {'title': 'Send revised quote to Sewell Lexus', 'type': 'email', 'priority': 'urgent', 'days': 0},
        {'title': 'Site visit - Hendrick BMW', 'type': 'visit', 'priority': 'high', 'days': 2},
        {'title': 'Call Enterprise Fleet manager', 'type': 'call', 'priority': 'medium', 'days': 3},
        {'title': 'Prepare proposal for Park Place Mercedes', 'type': 'quote', 'priority': 'urgent', 'days': 1},
        {'title': 'Follow up on voicemail - Budget Rental', 'type': 'follow_up', 'priority': 'medium', 'days': 2},
        {'title': 'Email damage assessment report', 'type': 'email', 'priority': 'low', 'days': 5},
        {'title': 'Schedule technician for AutoNation Honda', 'type': 'follow_up', 'priority': 'high', 'days': 1},
        {'title': 'Confirm start date with National Car Rental', 'type': 'call', 'priority': 'urgent', 'days': 0},
        {'title': 'Send contract to Dollar Rent A Car', 'type': 'email', 'priority': 'high', 'days': 1},
        {'title': 'Research Municipal Fleet contact', 'type': 'follow_up', 'priority': 'low', 'days': 7},
        {'title': 'Quarterly review - City Fleet Services', 'type': 'visit', 'priority': 'medium', 'days': 14},
    ]

    for task in tasks_data:
        due_date = (datetime.now() + timedelta(days=task['days'])).strftime('%Y-%m-%d')
        task_id = crm.create_task(
            title=task['title'],
            task_type=task['type'],
            location_id=random.randint(1, 18),
            deal_id=random.choice(deal_ids[:14]) if random.random() > 0.3 else None,
            assigned_to=random.choice(user_ids[:3]),
            due_date=due_date,
            priority=task['priority'],
            description=f"Auto-generated task for {task['title']}"
        )
        print(f"   Created: {task['title']} ({task['priority']})")

    # Add some completed tasks
    for i in range(5):
        task_id = crm.create_task(
            title=f'Completed task #{i+1}',
            task_type='follow_up',
            assigned_to=random.choice(user_ids),
            priority='medium'
        )
        crm.complete_task(task_id)

    print("   + 5 completed tasks")

    # ========================================
    # 5. CREATE NOTES
    # ========================================
    print("\n[5/6] Creating notes...")

    notes_text = [
        'Large dealership with 200+ vehicles on lot. High priority target.',
        'Manager mentioned they use competitor currently but open to switching.',
        'Best time to call is Tuesday/Wednesday mornings.',
        'Previous hail damage claim in 2024, good relationship with insurance.',
        'Fleet manager is Bob Johnson - very responsive via email.',
        'Corporate approval needed for contracts over $50k.',
        'They prefer detailed photo documentation before signing.',
        'Referred by AutoNation Honda - mention the connection.',
    ]

    for i, note in enumerate(notes_text):
        crm.add_note(
            note_text=note,
            location_id=random.randint(1, 18),
            deal_id=random.choice(deal_ids[:14]) if random.random() > 0.5 else None,
            user_id=random.choice(user_ids)
        )

    print(f"   Created {len(notes_text)} notes")

    # ========================================
    # 6. SUMMARY
    # ========================================
    print("\n[6/6] Generating summary...")

    pipeline = crm.get_pipeline_summary()
    funnel = crm.get_conversion_funnel()
    activity = crm.get_activity_summary(days=30)

    print("\n" + "="*60)
    print("CRM DEMO DATA SEEDED SUCCESSFULLY!")
    print("="*60)
    print(f"""
Pipeline Summary:
  - Total Deals: {pipeline['total_deals']}
  - Pipeline Value: ${pipeline['total_value']:,.0f}

Conversion Funnel:
  - Leads: {funnel['leads']}
  - Contacted: {funnel['contacted']}
  - Qualified: {funnel['qualified']}
  - Quoted: {funnel['quoted']}
  - Won: {funnel['won']}
  - Lost: {funnel['lost']}

Activity (30 days):
  - Interactions: {activity['interactions']}
  - New Deals: {activity['new_deals']}
  - Pending Tasks: {activity['pending_tasks']}

View at: http://localhost:5000/crm/dashboard
""")
    print("="*60 + "\n")

if __name__ == '__main__':
    seed_demo_data()
