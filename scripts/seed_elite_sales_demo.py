"""
Seed Elite Sales Demo Data
Populates the database with realistic sample data for mobile app demo
Uses direct SQL to ensure all data is created
"""

import os
import sys
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def get_db_connection():
    """Get database connection"""
    db_path = PROJECT_ROOT / 'data' / 'hailtracker_crm.db'
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def generate_phone():
    """Generate random phone number"""
    return f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}"


def generate_address(city="Dallas", state="TX"):
    """Generate random address"""
    streets = [
        "Oak", "Maple", "Cedar", "Pine", "Elm", "Main", "Park", "Lake",
        "Hill", "River", "Spring", "Sunset", "Valley", "Forest", "Meadow"
    ]
    types = ["St", "Ave", "Blvd", "Dr", "Ln", "Way", "Ct", "Rd"]
    num = random.randint(100, 9999)
    street = random.choice(streets)
    stype = random.choice(types)
    zipcode = random.randint(75001, 75399)
    return f"{num} {street} {stype}, {city}, {state} {zipcode}"


def random_date_between(start_days_ago, end_days_ago=0):
    """Generate random date between two points"""
    start = datetime.now() - timedelta(days=start_days_ago)
    end = datetime.now() - timedelta(days=end_days_ago)
    delta = end - start
    random_days = random.randint(0, max(1, delta.days))
    return start + timedelta(days=random_days)


def ensure_tables_exist(conn):
    """Create all necessary tables"""
    cursor = conn.cursor()

    # Salespeople table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS salespeople (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            employee_id TEXT UNIQUE,
            points INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            leads_today INTEGER DEFAULT 0,
            leads_this_week INTEGER DEFAULT 0,
            total_leads INTEGER DEFAULT 0,
            knocks_today INTEGER DEFAULT 0,
            conversions INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # Field leads table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS field_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salesperson_id INTEGER,
            latitude REAL,
            longitude REAL,
            address TEXT,
            customer_name TEXT,
            phone TEXT,
            email TEXT,
            lead_quality TEXT DEFAULT 'WARM',
            status TEXT DEFAULT 'NEW',
            damage_description TEXT,
            vehicle_info TEXT,
            photos TEXT,
            notes TEXT,
            synced INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    # Competitor activity table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS competitor_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salesperson_id INTEGER,
            competitor_name TEXT,
            location_lat REAL,
            location_lon REAL,
            activity_type TEXT,
            vehicle_count INTEGER DEFAULT 1,
            notes TEXT,
            spotted_at TEXT
        )
    """)

    # Do-not-knock table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS do_not_knock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT,
            latitude REAL,
            longitude REAL,
            reason TEXT,
            notes TEXT,
            added_by INTEGER,
            created_at TEXT
        )
    """)

    # Objection log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS objection_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salesperson_id INTEGER,
            objection_type TEXT,
            response_used TEXT,
            outcome TEXT,
            logged_at TEXT
        )
    """)

    # Achievements table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salesperson_id INTEGER,
            achievement_type TEXT,
            achievement_name TEXT,
            points INTEGER DEFAULT 0,
            achievement_data TEXT,
            awarded_at TEXT
        )
    """)

    # Mobile check-ins table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mobile_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salesperson_id INTEGER,
            latitude REAL,
            longitude REAL,
            battery_level INTEGER,
            app_version TEXT,
            checkin_time TEXT
        )
    """)

    conn.commit()
    print("Tables verified/created")


def seed_demo_data():
    """Seed all demo data for Elite Sales mobile app"""
    print("=" * 60)
    print("SEEDING ELITE SALES DEMO DATA")
    print("=" * 60)
    print()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure tables exist
    ensure_tables_exist(conn)

    # =========================================================================
    # 1. SALESPEOPLE
    # =========================================================================
    print("Creating salespeople...")

    salespeople_data = [
        ("Mike", "Johnson", "mike.johnson@hailtracker.com", "(214) 555-0101", "EMP001"),
        ("Sarah", "Williams", "sarah.williams@hailtracker.com", "(214) 555-0102", "EMP002"),
        ("James", "Rodriguez", "james.rodriguez@hailtracker.com", "(214) 555-0103", "EMP003"),
        ("Emily", "Chen", "emily.chen@hailtracker.com", "(214) 555-0104", "EMP004"),
        ("David", "Thompson", "david.thompson@hailtracker.com", "(214) 555-0105", "EMP005"),
    ]

    salesperson_ids = []
    for first, last, email, phone, emp_id in salespeople_data:
        # Check if exists
        cursor.execute("SELECT id FROM salespeople WHERE email = ?", (email,))
        existing = cursor.fetchone()

        if existing:
            salesperson_ids.append(existing['id'])
            print(f"  Exists: {first} {last} (ID: {existing['id']})")
        else:
            leads_today = random.randint(3, 12)
            leads_week = leads_today + random.randint(20, 50)
            points = random.randint(2000, 9000)

            cursor.execute("""
                INSERT INTO salespeople (
                    first_name, last_name, email, phone, employee_id,
                    points, level, leads_today, leads_this_week, total_leads,
                    knocks_today, conversions, active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                first, last, email, phone, emp_id,
                points, points // 1000 + 1, leads_today, leads_week,
                leads_week + random.randint(100, 300),
                leads_today + random.randint(15, 40),
                int(leads_week * random.uniform(0.2, 0.4)),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            salesperson_ids.append(cursor.lastrowid)
            print(f"  Created: {first} {last} (ID: {cursor.lastrowid}, {points} pts)")

    conn.commit()
    print(f"  Total: {len(salesperson_ids)} salespeople")
    print()

    # =========================================================================
    # 2. FIELD LEADS
    # =========================================================================
    print("Creating field leads...")

    # Dallas area coordinates
    dallas_lat = 32.7767
    dallas_lon = -96.7970

    first_names = ["John", "Mary", "Robert", "Patricia", "Michael", "Jennifer",
                   "William", "Linda", "David", "Elizabeth", "Richard", "Barbara",
                   "Joseph", "Susan", "Thomas", "Jessica", "Charles", "Sarah"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
                  "Miller", "Davis", "Rodriguez", "Martinez", "Anderson", "Taylor"]

    lead_qualities = ["HOT", "HOT", "WARM", "WARM", "WARM", "COLD"]
    lead_statuses = ["NEW", "NEW", "CONTACTED", "APPOINTMENT_SET", "ESTIMATE_GIVEN", "SOLD"]
    damage_descriptions = [
        "Multiple dents on hood and roof, customer very interested",
        "Hail damage visible on all panels, insurance claim filed",
        "Light damage on hood, customer wants estimate",
        "Significant roof damage, needs immediate attention",
        "Damage on trunk and rear quarter panels",
        "Customer noticed dents after last week's hailstorm",
    ]

    # Clear existing leads for fresh demo
    cursor.execute("DELETE FROM field_leads")

    leads_created = 0
    for i in range(60):
        sp_id = random.choice(salesperson_ids)
        lat = dallas_lat + random.uniform(-0.12, 0.12)
        lon = dallas_lon + random.uniform(-0.12, 0.12)
        created = random_date_between(14)

        cursor.execute("""
            INSERT INTO field_leads (
                salesperson_id, latitude, longitude, address,
                customer_name, phone, email, lead_quality, status,
                damage_description, vehicle_info, synced, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sp_id, lat, lon, generate_address(),
            f"{random.choice(first_names)} {random.choice(last_names)}",
            generate_phone(),
            f"customer{i+1}@email.com" if random.random() > 0.4 else None,
            random.choice(lead_qualities),
            random.choice(lead_statuses),
            random.choice(damage_descriptions),
            f'{{"year": {random.randint(2019, 2024)}, "make": "{random.choice(["Toyota", "Honda", "Ford", "Chevy"])}", "model": "{random.choice(["Camry", "Accord", "F-150", "Silverado"])}"}}',
            1 if random.random() > 0.3 else 0,
            created.isoformat(),
            created.isoformat()
        ))
        leads_created += 1

    conn.commit()
    print(f"  Created {leads_created} field leads")
    print()

    # =========================================================================
    # 3. COMPETITOR SIGHTINGS
    # =========================================================================
    print("Creating competitor sightings...")

    competitors = [
        "Dent Wizard", "Paintless Pro", "Hail Masters", "Storm Chasers PDR",
        "Auto Dent Removal", "Precision PDR", "Elite Hail Repair"
    ]
    activity_types = ["CANVASSING", "SETUP", "WORKING", "ADVERTISING"]
    comp_notes = [
        "Spotted truck with signage",
        "Team of 3 canvassing neighborhood",
        "Setting up tent at dealership",
        "Door hangers being distributed",
        "Speaking with homeowner"
    ]

    # Clear existing
    cursor.execute("DELETE FROM competitor_activity")

    sightings_created = 0
    for i in range(35):
        sp_id = random.choice(salesperson_ids)
        lat = dallas_lat + random.uniform(-0.1, 0.1)
        lon = dallas_lon + random.uniform(-0.1, 0.1)
        spotted = random_date_between(10)

        cursor.execute("""
            INSERT INTO competitor_activity (
                salesperson_id, competitor_name, location_lat, location_lon,
                activity_type, vehicle_count, notes, spotted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sp_id,
            random.choice(competitors),
            lat, lon,
            random.choice(activity_types),
            random.randint(1, 4),
            random.choice(comp_notes),
            spotted.isoformat()
        ))
        sightings_created += 1

    conn.commit()
    print(f"  Created {sightings_created} competitor sightings")
    print()

    # =========================================================================
    # 4. DO-NOT-KNOCK LIST
    # =========================================================================
    print("Creating do-not-knock entries...")

    dnk_reasons = ["NO_SOLICITING", "HOSTILE", "PREVIOUS_CUSTOMER", "COMPETITOR_EMPLOYEE"]
    dnk_notes = [
        "No soliciting sign on door",
        "Homeowner was aggressive",
        "Already a customer from 2023",
        "Works for competing company",
        "Requested not to be contacted"
    ]

    # Clear existing
    cursor.execute("DELETE FROM do_not_knock")

    dnk_created = 0
    for i in range(20):
        lat = dallas_lat + random.uniform(-0.1, 0.1)
        lon = dallas_lon + random.uniform(-0.1, 0.1)

        cursor.execute("""
            INSERT INTO do_not_knock (
                address, latitude, longitude, reason, notes, added_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            generate_address(),
            lat, lon,
            random.choice(dnk_reasons),
            random.choice(dnk_notes),
            random.choice(salesperson_ids),
            random_date_between(30).isoformat()
        ))
        dnk_created += 1

    conn.commit()
    print(f"  Created {dnk_created} DNK entries")
    print()

    # =========================================================================
    # 5. OBJECTION LOG
    # =========================================================================
    print("Creating objection log entries...")

    objection_types = [
        "PRICE_TOO_HIGH", "NEED_TO_THINK", "INSURANCE_CONCERN",
        "ALREADY_HAVE_SOMEONE", "NOT_INTERESTED", "BAD_TIMING"
    ]
    responses = [
        "Explained insurance covers most repairs",
        "Offered free inspection and estimate",
        "Provided references from neighbors",
        "Explained PDR process benefits",
        "Demonstrated before/after photos"
    ]
    outcomes = ["CONVERTED", "CONVERTED", "FOLLOW_UP", "FOLLOW_UP", "LOST"]

    # Clear existing
    cursor.execute("DELETE FROM objection_log")

    objections_created = 0
    for i in range(50):
        sp_id = random.choice(salesperson_ids)

        cursor.execute("""
            INSERT INTO objection_log (
                salesperson_id, objection_type, response_used, outcome, logged_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            sp_id,
            random.choice(objection_types),
            random.choice(responses),
            random.choice(outcomes),
            random_date_between(14).isoformat()
        ))
        objections_created += 1

    conn.commit()
    print(f"  Created {objections_created} objection entries")
    print()

    # =========================================================================
    # 6. ACHIEVEMENTS
    # =========================================================================
    print("Awarding achievements...")

    achievement_types = [
        ("FIRST_LEAD", "First Lead Captured", 100),
        ("TEN_LEADS", "10 Leads in a Day", 500),
        ("FIRST_SALE", "First Sale Closed", 250),
        ("HOT_STREAK", "3 Hot Leads in a Row", 300),
        ("EARLY_BIRD", "First Check-in Before 8 AM", 150),
        ("ROAD_WARRIOR", "50 Miles Covered", 200),
        ("COMPETITOR_SPOTTER", "5 Competitor Sightings", 175),
        ("OBJECTION_MASTER", "10 Objections Overcome", 400),
        ("WEEKLY_CHAMPION", "Top Performer This Week", 1000),
        ("CONVERSION_KING", "5 Sales in One Day", 750),
    ]

    # Clear existing
    cursor.execute("DELETE FROM achievements")

    achievements_awarded = 0
    for sp_id in salesperson_ids:
        # Award 3-6 random achievements to each salesperson
        num_achievements = random.randint(3, 6)
        awarded = random.sample(achievement_types, num_achievements)

        for ach_type, name, points in awarded:
            cursor.execute("""
                INSERT INTO achievements (
                    salesperson_id, achievement_type, achievement_name,
                    points, achievement_data, awarded_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                sp_id, ach_type, name, points,
                f'{{"earned_on": "{random_date_between(30).strftime("%Y-%m-%d")}"}}',
                random_date_between(30).isoformat()
            ))
            achievements_awarded += 1

    conn.commit()
    print(f"  Awarded {achievements_awarded} achievements")
    print()

    # =========================================================================
    # 7. MOBILE CHECK-INS
    # =========================================================================
    print("Creating mobile check-ins...")

    # Clear existing
    cursor.execute("DELETE FROM mobile_checkins")

    checkins_created = 0
    for sp_id in salesperson_ids:
        # Create 8-15 check-ins per salesperson over the past week
        num_checkins = random.randint(8, 15)
        for _ in range(num_checkins):
            lat = dallas_lat + random.uniform(-0.08, 0.08)
            lon = dallas_lon + random.uniform(-0.08, 0.08)
            checkin_time = random_date_between(7)

            cursor.execute("""
                INSERT INTO mobile_checkins (
                    salesperson_id, latitude, longitude,
                    battery_level, app_version, checkin_time
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                sp_id, lat, lon,
                random.randint(15, 100),
                "1.0.0",
                checkin_time.isoformat()
            ))
            checkins_created += 1

    conn.commit()
    print(f"  Created {checkins_created} check-ins")
    print()

    # =========================================================================
    # SUMMARY
    # =========================================================================
    conn.close()

    print("=" * 60)
    print("DEMO DATA SEEDING COMPLETE")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  - Salespeople: {len(salesperson_ids)}")
    print(f"  - Field Leads: {leads_created}")
    print(f"  - Competitor Sightings: {sightings_created}")
    print(f"  - DNK Entries: {dnk_created}")
    print(f"  - Objection Logs: {objections_created}")
    print(f"  - Achievements: {achievements_awarded}")
    print(f"  - Mobile Check-ins: {checkins_created}")
    print()
    print("Demo Salespeople:")
    print("  1. Mike Johnson     - mike.johnson@hailtracker.com")
    print("  2. Sarah Williams   - sarah.williams@hailtracker.com")
    print("  3. James Rodriguez  - james.rodriguez@hailtracker.com")
    print("  4. Emily Chen       - emily.chen@hailtracker.com")
    print("  5. David Thompson   - david.thompson@hailtracker.com")
    print()
    print("Access the mobile app at:")
    print("  http://127.0.0.1:8765/mobile/app")
    print()

    return True


if __name__ == "__main__":
    seed_demo_data()
