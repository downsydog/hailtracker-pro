"""
Seed Database with Demo Data
============================
Populates the database with sample data for testing the app.

Run: python scripts/seed_data.py
"""

import os
import sys
import sqlite3
import bcrypt
from datetime import datetime, timedelta
import random

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = 'data/hailtracker_crm.db'


def get_connection():
    """Get database connection"""
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    """Hash a password with bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def seed_users():
    """Create test users with various roles"""
    print("\n[1/8] Creating users...")

    conn = get_connection()
    cursor = conn.cursor()

    # Check if users table exists, create if not
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'sales',
            phone TEXT,
            company_id INTEGER,
            active BOOLEAN DEFAULT 1,
            email_verified BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            login_count INTEGER DEFAULT 0
        )
    """)

    users = [
        ('admin@hailtracker.com', 'admin', 'admin123', 'Admin User', 'admin', '(405) 555-0001'),
        ('office@hailtracker.com', 'office', 'office123', 'Office Manager', 'office', '(405) 555-0002'),
        ('tech@hailtracker.com', 'tech', 'tech123', 'Mike Technician', 'tech', '(405) 555-0003'),
        ('sales@hailtracker.com', 'sales', 'sales123', 'Sarah Sales', 'sales', '(405) 555-0004'),
        ('estimator@hailtracker.com', 'estimator', 'est123', 'Eric Estimator', 'estimator', '(405) 555-0005'),
    ]

    user_ids = []
    for email, username, password, full_name, role, phone in users:
        try:
            cursor.execute("""
                INSERT INTO users (email, username, password_hash, full_name, role, phone, active, email_verified, company_id)
                VALUES (?, ?, ?, ?, ?, ?, 1, 1, 1)
            """, (email, username, hash_password(password), full_name, role, phone))
            user_ids.append(cursor.lastrowid)
            print(f"   Created: {full_name} ({role}) - {email}")
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            user_ids.append(row['id'] if row else 1)
            print(f"   Exists:  {full_name} ({role})")

    conn.commit()
    conn.close()
    return user_ids


def seed_customers():
    """Create sample customers"""
    print("\n[2/8] Creating customers...")

    conn = get_connection()
    cursor = conn.cursor()

    customers = [
        ('John', 'Smith', 'john.smith@email.com', '(405) 555-1001', '123 Main St', 'Oklahoma City', 'OK', '73102'),
        ('Jane', 'Doe', 'jane.doe@email.com', '(405) 555-1002', '456 Oak Ave', 'Norman', 'OK', '73019'),
        ('Bob', 'Wilson', 'bob.wilson@email.com', '(405) 555-1003', '789 Elm Dr', 'Edmond', 'OK', '73034'),
        ('Alice', 'Johnson', 'alice.j@email.com', '(405) 555-1004', '321 Pine Rd', 'Moore', 'OK', '73160'),
        ('Charlie', 'Brown', 'charlie.b@email.com', '(405) 555-1005', '654 Maple Ln', 'Midwest City', 'OK', '73110'),
        ('Diana', 'Martinez', 'diana.m@email.com', '(405) 555-1006', '987 Cedar Ct', 'Yukon', 'OK', '73099'),
        ('Edward', 'Garcia', 'edward.g@email.com', '(405) 555-1007', '147 Birch Way', 'Mustang', 'OK', '73064'),
        ('Fiona', 'Lee', 'fiona.lee@email.com', '(405) 555-1008', '258 Walnut Blvd', 'Bethany', 'OK', '73008'),
        ('George', 'Taylor', 'george.t@email.com', '(405) 555-1009', '369 Spruce St', 'Del City', 'OK', '73115'),
        ('Helen', 'Anderson', 'helen.a@email.com', '(405) 555-1010', '741 Ash Ave', 'Choctaw', 'OK', '73020'),
    ]

    sources = ['WALK_IN', 'REFERRAL', 'ONLINE', 'PHONE', 'INSURANCE']
    customer_ids = []

    for first, last, email, phone, addr, city, state, zip_code in customers:
        try:
            cursor.execute("""
                INSERT INTO customers (first_name, last_name, email, phone, street_address, city, state, zip_code, source, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (first, last, email, phone, addr, city, state, zip_code, random.choice(sources)))
            customer_ids.append(cursor.lastrowid)
            print(f"   Created: {first} {last}")
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM customers WHERE email = ?", (email,))
            row = cursor.fetchone()
            customer_ids.append(row['id'] if row else 1)
            print(f"   Exists:  {first} {last}")

    conn.commit()
    conn.close()
    return customer_ids


def seed_vehicles(customer_ids):
    """Create sample vehicles"""
    print("\n[3/8] Creating vehicles...")

    conn = get_connection()
    cursor = conn.cursor()

    vehicles = [
        (2023, 'Toyota', 'Camry', 'Silver', '1HGBH41JXMN109186'),
        (2022, 'Honda', 'Accord', 'White', '2HGFC2F59NH500001'),
        (2023, 'Ford', 'F-150', 'Blue', '1FTFW1E85NFA00001'),
        (2021, 'Chevrolet', 'Silverado', 'Black', '3GCUYDED5MG100001'),
        (2022, 'BMW', 'X5', 'Gray', 'WBAPL5C57BA000001'),
        (2023, 'Tesla', 'Model 3', 'Red', '5YJ3E1EA5NF000001'),
        (2022, 'Nissan', 'Altima', 'White', '1N4BL4BV8NN000001'),
        (2021, 'Jeep', 'Grand Cherokee', 'Green', '1C4RJFBG5MC000001'),
        (2023, 'Hyundai', 'Sonata', 'Blue', '5NPE34AF2NH000001'),
        (2022, 'Kia', 'Telluride', 'Black', '5XYP3DHC5NG000001'),
        (2023, 'Mazda', 'CX-5', 'Red', 'JM3KFBDM5N1000001'),
        (2021, 'Subaru', 'Outback', 'Silver', '4S4BTAPC5M3000001'),
        (2022, 'Volkswagen', 'Jetta', 'White', '3VWC57BU9NM000001'),
        (2023, 'Audi', 'Q7', 'Gray', 'WA1LAAF77ND000001'),
        (2022, 'Lexus', 'RX 350', 'Black', '2T2HZMDA5NC000001'),
    ]

    vehicle_ids = []

    for i, (year, make, model, color, vin) in enumerate(vehicles):
        customer_id = customer_ids[i % len(customer_ids)]
        try:
            cursor.execute("""
                INSERT INTO vehicles (customer_id, year, make, model, color, vin, status)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (customer_id, year, make, model, color, vin))
            vehicle_ids.append(cursor.lastrowid)
            print(f"   Created: {year} {make} {model} ({color})")
        except sqlite3.IntegrityError:
            vehicle_ids.append(i + 1)
            print(f"   Exists:  {year} {make} {model}")

    conn.commit()
    conn.close()
    return vehicle_ids


def seed_jobs(customer_ids, vehicle_ids, user_ids):
    """Create sample jobs in various statuses"""
    print("\n[4/8] Creating jobs...")

    conn = get_connection()
    cursor = conn.cursor()

    statuses = ['NEW', 'SCHEDULED', 'CHECKED_IN', 'IN_PROGRESS', 'WAITING_PARTS',
                'QUALITY_CHECK', 'READY_FOR_PICKUP', 'COMPLETED', 'INVOICED']
    damage_types = ['HAIL', 'DOOR_DING', 'MINOR_DENT', 'CREASE', 'BODY_LINE']
    job_types = ['PDR', 'CONVENTIONAL', 'COMBO']

    job_ids = []
    job_num = 1000

    for i in range(20):
        job_num += 1
        customer_id = customer_ids[i % len(customer_ids)]
        vehicle_id = vehicle_ids[i % len(vehicle_ids)]
        status = statuses[i % len(statuses)]

        # Set dates based on status
        scheduled_drop_off = None
        completed_at = None

        if status in ['SCHEDULED', 'CHECKED_IN', 'IN_PROGRESS', 'WAITING_PARTS', 'QUALITY_CHECK']:
            scheduled_drop_off = (datetime.now() + timedelta(days=random.randint(-5, 10))).strftime('%Y-%m-%d %H:%M:%S')
        if status in ['COMPLETED', 'INVOICED']:
            completed_at = (datetime.now() - timedelta(days=random.randint(0, 3))).strftime('%Y-%m-%d %H:%M:%S')

        try:
            cursor.execute("""
                INSERT INTO jobs (job_number, customer_id, vehicle_id, status, damage_type,
                                  job_type, total_estimate, assigned_tech_id, scheduled_drop_off,
                                  completed_at, priority, internal_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f'JOB-{job_num}', customer_id, vehicle_id, status,
                random.choice(damage_types),
                random.choice(job_types),
                random.randint(500, 5000),
                user_ids[2] if status in ['IN_PROGRESS', 'QUALITY_CHECK'] else None,  # tech user
                scheduled_drop_off, completed_at,
                random.choice(['LOW', 'NORMAL', 'HIGH', 'URGENT']),
                'Hail damage across multiple panels' if random.random() > 0.3 else 'Minor door ding'
            ))
            job_ids.append(cursor.lastrowid)
            print(f"   Created: JOB-{job_num} ({status})")
        except sqlite3.IntegrityError:
            job_ids.append(i + 1)
            print(f"   Exists:  JOB-{job_num}")

    conn.commit()
    conn.close()
    return job_ids


def seed_leads(user_ids):
    """Create sample leads"""
    print("\n[5/8] Creating leads...")

    conn = get_connection()
    cursor = conn.cursor()

    # Actual leads table schema:
    # id, first_name, last_name, company_name, email, phone, source, hail_event_id, score, temperature,
    # status, converted_to_customer_id, lost_reason, assigned_to, assigned_at, next_follow_up_date,
    # follow_up_count, last_contact_date, vehicle_year, vehicle_make, vehicle_model, damage_type,
    # damage_description, estimated_repair_cost, notes, created_at, updated_at, deleted_at, organization_id

    leads = [
        ('Michael', 'Roberts', 'mike.r@email.com', '(405) 555-2001', 2022, 'Ford', 'Explorer'),
        ('Jennifer', 'Davis', 'jen.d@email.com', '(405) 555-2002', 2023, 'Toyota', 'RAV4'),
        ('David', 'Miller', 'david.m@email.com', '(405) 555-2003', 2021, 'Honda', 'CR-V'),
        ('Sarah', 'Wilson', 'sarah.w@email.com', '(405) 555-2004', 2022, 'Chevrolet', 'Equinox'),
        ('James', 'Moore', 'james.m@email.com', '(405) 555-2005', 2023, 'Hyundai', 'Tucson'),
        ('Emily', 'Taylor', 'emily.t@email.com', '(405) 555-2006', 2022, 'Nissan', 'Rogue'),
        ('Chris', 'Anderson', 'chris.a@email.com', '(405) 555-2007', 2021, 'Jeep', 'Wrangler'),
        ('Amanda', 'Thomas', 'amanda.t@email.com', '(405) 555-2008', 2023, 'Mazda', 'CX-9'),
        ('Ryan', 'Jackson', 'ryan.j@email.com', '(405) 555-2009', 2022, 'Subaru', 'Forester'),
        ('Nicole', 'White', 'nicole.w@email.com', '(405) 555-2010', 2023, 'Kia', 'Sportage'),
        ('Brandon', 'Harris', 'brandon.h@email.com', '(405) 555-2011', 2022, 'BMW', '3 Series'),
        ('Jessica', 'Martin', 'jessica.m@email.com', '(405) 555-2012', 2021, 'Audi', 'A4'),
        ('Kevin', 'Garcia', 'kevin.g@email.com', '(405) 555-2013', 2023, 'Mercedes', 'C-Class'),
        ('Lauren', 'Martinez', 'lauren.m@email.com', '(405) 555-2014', 2022, 'Lexus', 'NX'),
        ('Tyler', 'Robinson', 'tyler.r@email.com', '(405) 555-2015', 2023, 'Tesla', 'Model Y'),
    ]

    statuses = ['NEW', 'CONTACTED', 'QUALIFIED', 'CONVERTED', 'LOST']
    temperatures = ['HOT', 'WARM', 'COLD']
    sources = ['WEBSITE', 'REFERRAL', 'FACEBOOK', 'GOOGLE', 'STORM_CHASE', 'PHONE']

    lead_ids = []
    for i, (first, last, email, phone, year, make, model) in enumerate(leads):
        status = statuses[i % 4] if i < 12 else statuses[i % len(statuses)]  # Most not converted/lost
        temp = temperatures[i % len(temperatures)] if status not in ['CONVERTED', 'LOST'] else 'COLD'
        score = random.randint(30, 95)

        try:
            cursor.execute("""
                INSERT INTO leads (first_name, last_name, email, phone, vehicle_year, vehicle_make,
                                   vehicle_model, damage_type, damage_description, source, status,
                                   temperature, score, assigned_to, estimated_repair_cost, notes,
                                   follow_up_count, organization_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                first, last, email, phone, year, make, model,
                'HAIL', 'Storm damage - needs assessment',
                random.choice(sources), status, temp, score,
                user_ids[3] if len(user_ids) > 3 else user_ids[0],  # sales user
                random.randint(500, 4000),
                'Lead from recent storm event',
                random.randint(0, 3),
                1  # organization_id
            ))
            lead_ids.append(cursor.lastrowid)
            print(f"   Created: {first} {last} ({status}, {temp})")
        except sqlite3.IntegrityError:
            lead_ids.append(i + 1)
            print(f"   Exists:  {first} {last}")

    conn.commit()
    conn.close()
    return lead_ids


def seed_estimates(job_ids, user_ids):
    """Create sample estimates"""
    print("\n[6/8] Creating estimates...")

    conn = get_connection()
    cursor = conn.cursor()

    # Actual estimates table schema:
    # id, estimate_number, job_id, status, labor_hours, labor_rate, labor_total, parts_total,
    # subtotal, tax_rate, tax_amount, total, line_items, created_date, sent_date, viewed_date,
    # approved_date, expires_date, notes, terms, created_at, updated_at, created_by, organization_id

    statuses = ['DRAFT', 'SENT', 'APPROVED', 'DECLINED', 'EXPIRED']
    estimate_ids = []
    est_num = 2000

    for i in range(5):
        est_num += 1
        job_id = job_ids[i] if i < len(job_ids) else None
        status = statuses[i]

        labor_hours = random.randint(2, 12)
        labor_rate = 75.00
        labor_total = labor_hours * labor_rate
        parts_total = random.randint(0, 500)
        subtotal = labor_total + parts_total
        tax_rate = 0.085
        tax_amount = round(subtotal * tax_rate, 2)
        total = subtotal + tax_amount

        sent_date = None
        approved_date = None
        created_date = (datetime.now() - timedelta(days=random.randint(5, 15))).strftime('%Y-%m-%d')
        expires_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        if status in ['SENT', 'APPROVED']:
            sent_date = (datetime.now() - timedelta(days=random.randint(1, 10))).strftime('%Y-%m-%d')
        if status == 'APPROVED':
            approved_date = (datetime.now() - timedelta(days=random.randint(0, 5))).strftime('%Y-%m-%d')

        # Sample line items as JSON
        line_items = '[{"description":"PDR Labor","quantity":' + str(labor_hours) + ',"rate":75,"amount":' + str(labor_total) + '}]'

        try:
            cursor.execute("""
                INSERT INTO estimates (estimate_number, job_id, status, labor_hours, labor_rate,
                                       labor_total, parts_total, subtotal, tax_rate, tax_amount,
                                       total, line_items, created_date, sent_date, approved_date,
                                       expires_date, notes, terms, created_by, organization_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f'EST-{est_num}', job_id, status, labor_hours, labor_rate, labor_total,
                parts_total, subtotal, tax_rate, tax_amount, total, line_items,
                created_date, sent_date, approved_date, expires_date,
                'Standard PDR repair estimate',
                'Payment due upon completion. All work guaranteed.',
                user_ids[4] if len(user_ids) > 4 else user_ids[0],  # estimator
                1  # organization_id
            ))
            estimate_ids.append(cursor.lastrowid)
            print(f"   Created: EST-{est_num} ({status}) - ${total:,.2f}")
        except sqlite3.IntegrityError:
            estimate_ids.append(i + 1)
            print(f"   Exists:  EST-{est_num}")

    conn.commit()
    conn.close()
    return estimate_ids


def seed_notifications(user_ids):
    """Create sample notifications"""
    print("\n[7/8] Creating notifications...")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT DEFAULT 'INFO',
            title TEXT NOT NULL,
            message TEXT,
            link TEXT,
            read BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    notifications = [
        ('INFO', 'Welcome to HailTracker Pro!', 'Your account has been set up successfully.', '/app/dashboard'),
        ('JOB', 'New job assigned', 'JOB-1005 has been assigned to you.', '/app/jobs/5'),
        ('LEAD', 'Hot lead requires attention', 'Michael Roberts is waiting for a callback.', '/app/leads/1'),
        ('ESTIMATE', 'Estimate approved', 'EST-2003 has been approved by the customer.', '/app/estimates/3'),
        ('ALERT', 'Storm Alert: OKC Metro', 'Hail storm reported in Oklahoma City area.', '/app/hail-map'),
        ('JOB', 'Job completed', 'JOB-1008 marked as completed.', '/app/jobs/8'),
        ('CUSTOMER', 'New customer registered', 'Jane Doe has created an account.', '/app/customers/2'),
        ('PAYMENT', 'Payment received', 'Invoice #INV-001 paid in full.', '/app/invoices'),
        ('SCHEDULE', 'Appointment reminder', 'JOB-1003 scheduled for tomorrow at 9 AM.', '/app/schedule'),
        ('SYSTEM', 'Database backup complete', 'Nightly backup completed successfully.', '/app/settings'),
    ]

    admin_id = user_ids[0]
    notification_ids = []

    for i, (notif_type, title, message, link) in enumerate(notifications):
        days_ago = random.randint(0, 7)
        is_read = 1 if i < 4 else 0  # First 4 are read

        try:
            cursor.execute("""
                INSERT INTO notifications (user_id, type, title, message, link, read, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                admin_id, notif_type, title, message, link, is_read,
                (datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 12))).strftime('%Y-%m-%d %H:%M:%S')
            ))
            notification_ids.append(cursor.lastrowid)
            status = 'read' if is_read else 'unread'
            print(f"   Created: {title[:40]}... ({status})")
        except Exception as e:
            print(f"   Error: {e}")

    conn.commit()
    conn.close()
    return notification_ids


def seed_company_settings():
    """Create company settings"""
    print("\n[8/8] Creating company settings...")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            setting_type TEXT DEFAULT 'string',
            category TEXT DEFAULT 'general',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    settings = [
        ('company_name', 'HailTracker Demo PDR', 'string', 'general'),
        ('company_phone', '(405) 555-0000', 'string', 'general'),
        ('company_email', 'info@hailtracker.pro', 'string', 'general'),
        ('company_address', '123 Business Parkway', 'string', 'general'),
        ('company_city', 'Oklahoma City', 'string', 'general'),
        ('company_state', 'OK', 'string', 'general'),
        ('company_zip', '73102', 'string', 'general'),
        ('tax_rate', '0.085', 'number', 'billing'),
        ('default_labor_rate', '75', 'number', 'billing'),
        ('estimate_validity_days', '30', 'number', 'estimates'),
        ('enable_customer_portal', 'true', 'boolean', 'features'),
        ('enable_sms_notifications', 'true', 'boolean', 'notifications'),
    ]

    for key, value, stype, category in settings:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO company_settings (setting_key, setting_value, setting_type, category)
                VALUES (?, ?, ?, ?)
            """, (key, value, stype, category))
            print(f"   Set: {key} = {value}")
        except Exception as e:
            print(f"   Error setting {key}: {e}")

    conn.commit()
    conn.close()


def seed_billing():
    """Create billing record"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT DEFAULT 'professional',
            plan_name TEXT DEFAULT 'Professional',
            status TEXT DEFAULT 'active',
            seats_included INTEGER DEFAULT 10,
            seats_used INTEGER DEFAULT 5,
            monthly_price REAL DEFAULT 99,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    try:
        cursor.execute("""
            INSERT INTO billing (plan_id, plan_name, status, seats_included, seats_used, monthly_price)
            VALUES ('professional', 'Professional', 'active', 10, 5, 99.00)
        """)
    except:
        pass

    conn.commit()
    conn.close()


def main():
    print("\n" + "=" * 60)
    print("HAILTRACKER PRO - DATABASE SEEDER")
    print("=" * 60)

    # Seed in order (respecting foreign keys)
    user_ids = seed_users()
    customer_ids = seed_customers()
    vehicle_ids = seed_vehicles(customer_ids)
    job_ids = seed_jobs(customer_ids, vehicle_ids, user_ids)
    lead_ids = seed_leads(user_ids)
    estimate_ids = seed_estimates(job_ids, user_ids)
    notification_ids = seed_notifications(user_ids)
    seed_company_settings()
    seed_billing()

    print("\n" + "=" * 60)
    print("SEED COMPLETE!")
    print("=" * 60)
    print(f"""
Summary:
  - Users:         {len(user_ids)}
  - Customers:     {len(customer_ids)}
  - Vehicles:      {len(vehicle_ids)}
  - Jobs:          {len(job_ids)}
  - Leads:         {len(lead_ids)}
  - Estimates:     {len(estimate_ids)}
  - Notifications: {len(notification_ids)}

Login Credentials:
  Admin:     admin@hailtracker.com / admin123
  Office:    office@hailtracker.com / office123
  Tech:      tech@hailtracker.com / tech123
  Sales:     sales@hailtracker.com / sales123
  Estimator: estimator@hailtracker.com / est123

Start the app: python run.py --port 5000
Then visit:    http://localhost:5000/auth/login
""")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
