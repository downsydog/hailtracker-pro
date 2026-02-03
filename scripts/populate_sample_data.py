"""
Populate Sample Data for HailTracker Pro
=========================================
Creates realistic sample data for testing the React frontend.
"""

import sqlite3
import random
import json
from datetime import datetime, timedelta
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'hailtracker_pro.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Sample data pools
FIRST_NAMES = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
               'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
               'Thomas', 'Sarah', 'Charles', 'Karen', 'Christopher', 'Nancy', 'Daniel', 'Lisa']

LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
              'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
              'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson', 'White']

STREETS = ['Main St', 'Oak Ave', 'Maple Dr', 'Cedar Ln', 'Pine Rd', 'Elm St', 'Park Ave',
           'Lake Dr', 'River Rd', 'Hill St', 'Valley View', 'Sunset Blvd', 'Highland Ave']

CITIES = [('Dallas', 'TX', '75201'), ('Houston', 'TX', '77001'), ('Austin', 'TX', '78701'),
          ('San Antonio', 'TX', '78201'), ('Fort Worth', 'TX', '76101'), ('Plano', 'TX', '75023'),
          ('Arlington', 'TX', '76010'), ('Irving', 'TX', '75060'), ('Frisco', 'TX', '75034')]

CAR_MAKES = {
    'Honda': ['Accord', 'Civic', 'CR-V', 'Pilot', 'Odyssey'],
    'Toyota': ['Camry', 'Corolla', 'RAV4', 'Highlander', 'Tacoma'],
    'Ford': ['F-150', 'Mustang', 'Explorer', 'Escape', 'Edge'],
    'Chevrolet': ['Silverado', 'Malibu', 'Equinox', 'Tahoe', 'Traverse'],
    'BMW': ['3 Series', '5 Series', 'X3', 'X5', '7 Series'],
    'Mercedes-Benz': ['C-Class', 'E-Class', 'GLC', 'GLE', 'S-Class'],
    'Nissan': ['Altima', 'Sentra', 'Rogue', 'Pathfinder', 'Maxima'],
    'Hyundai': ['Elantra', 'Sonata', 'Tucson', 'Santa Fe', 'Palisade'],
    'Tesla': ['Model 3', 'Model Y', 'Model S', 'Model X'],
    'Audi': ['A4', 'A6', 'Q5', 'Q7', 'A3']
}

COLORS = ['White', 'Black', 'Silver', 'Gray', 'Red', 'Blue', 'Green', 'Brown', 'Beige', 'Navy']

INSURANCE_COMPANIES = ['State Farm', 'Allstate', 'GEICO', 'Progressive', 'USAA',
                       'Liberty Mutual', 'Farmers', 'Nationwide', 'Travelers', 'American Family']

LEAD_SOURCES = ['Website', 'Referral', 'Google Ads', 'Facebook', 'Walk-in', 'Insurance Partner', 'Yelp', 'Phone']

JOB_STATUSES = ['PENDING', 'SCHEDULED', 'IN_PROGRESS', 'WAITING_PARTS', 'COMPLETED', 'INVOICED']
LEAD_STATUSES = ['NEW', 'CONTACTED', 'QUALIFIED', 'CONVERTED', 'LOST']
ESTIMATE_STATUSES = ['DRAFT', 'SENT', 'APPROVED', 'DECLINED']


def random_phone():
    return f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}"

def random_email(first, last):
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com']
    return f"{first.lower()}.{last.lower()}{random.randint(1,99)}@{random.choice(domains)}"

def random_vin():
    chars = 'ABCDEFGHJKLMNPRSTUVWXYZ0123456789'
    return ''.join(random.choice(chars) for _ in range(17))

def random_plate():
    return f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}-{random.randint(1000,9999)}"

def random_date(days_ago_max=90):
    return (datetime.now() - timedelta(days=random.randint(0, days_ago_max))).strftime('%Y-%m-%d %H:%M:%S')

def random_future_date(days_ahead_max=30):
    return (datetime.now() + timedelta(days=random.randint(1, days_ahead_max))).strftime('%Y-%m-%d %H:%M:%S')


def create_customers(conn, count=25):
    """Create sample customers."""
    cursor = conn.cursor()
    customers = []

    for i in range(count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        city, state, zip_code = random.choice(CITIES)

        customer = {
            'first_name': first,
            'last_name': last,
            'email': random_email(first, last),
            'phone': random_phone(),
            'street_address': f"{random.randint(100, 9999)} {random.choice(STREETS)}",
            'city': city,
            'state': state,
            'zip_code': zip_code,
            'customer_type': random.choice(['individual', 'business']),
            'status': 'active',
            'source': random.choice(LEAD_SOURCES),
            'notes': random.choice(['', '', '', 'VIP customer', 'Referred by friend', 'Insurance claim']),
            'created_at': random_date(180),
            'updated_at': random_date(30)
        }

        cursor.execute('''
            INSERT INTO customers (first_name, last_name, email, phone, street_address, city, state,
                                   zip_code, customer_type, status, source, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer['first_name'], customer['last_name'], customer['email'],
              customer['phone'], customer['street_address'], customer['city'], customer['state'],
              customer['zip_code'], customer['customer_type'], customer['status'],
              customer['source'], customer['notes'], customer['created_at'], customer['updated_at']))

        customer['id'] = cursor.lastrowid
        customers.append(customer)

    conn.commit()
    print(f"Created {len(customers)} customers")
    return customers


def create_vehicles(conn, customers):
    """Create sample vehicles for customers."""
    cursor = conn.cursor()
    vehicles = []

    for customer in customers:
        num_vehicles = random.randint(1, 3) if random.random() < 0.3 else 1

        for _ in range(num_vehicles):
            make = random.choice(list(CAR_MAKES.keys()))
            model = random.choice(CAR_MAKES[make])
            year = random.randint(2015, 2024)

            has_insurance = random.random() > 0.3
            insurance = random.choice(INSURANCE_COMPANIES) if has_insurance else None
            policy = f"POL-{random.randint(100000, 999999)}" if has_insurance else None

            vehicle = {
                'customer_id': customer['id'],
                'year': year,
                'make': make,
                'model': model,
                'color': random.choice(COLORS),
                'vin': random_vin(),
                'license_plate': random_plate(),
                'insurance_company': insurance,
                'policy_number': policy,
                'status': 'active',
                'created_at': customer['created_at'],
                'updated_at': random_date(30)
            }

            cursor.execute('''
                INSERT INTO vehicles (customer_id, year, make, model, color, vin, license_plate,
                                     insurance_company, policy_number, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (vehicle['customer_id'], vehicle['year'], vehicle['make'], vehicle['model'],
                  vehicle['color'], vehicle['vin'], vehicle['license_plate'], vehicle['insurance_company'],
                  vehicle['policy_number'], vehicle['status'], vehicle['created_at'], vehicle['updated_at']))

            vehicle['id'] = cursor.lastrowid
            vehicles.append(vehicle)

    conn.commit()
    print(f"Created {len(vehicles)} vehicles")
    return vehicles


def create_jobs(conn, customers, vehicles, count=40):
    """Create sample jobs."""
    cursor = conn.cursor()
    jobs = []

    for i in range(count):
        vehicle = random.choice(vehicles)
        customer = next(c for c in customers if c['id'] == vehicle['customer_id'])
        status = random.choice(JOB_STATUSES)

        # Generate job number
        job_number = f"JOB-{datetime.now().year}-{1000 + i}"

        # Estimate cost based on damage type
        damage_types = ['HAIL', 'DOOR_DING', 'CREASE', 'MINOR_DENT', 'MAJOR_HAIL']
        damage_type = random.choice(damage_types)
        job_type = 'PDR' if 'HAIL' in damage_type or damage_type in ['DOOR_DING', 'CREASE', 'MINOR_DENT'] else 'CONVENTIONAL'

        if 'HAIL' in damage_type:
            total_estimate = random.randint(1500, 8000)
            estimated_hours = random.randint(4, 16)
        elif damage_type == 'CREASE':
            total_estimate = random.randint(300, 800)
            estimated_hours = random.randint(1, 3)
        else:
            total_estimate = random.randint(150, 500)
            estimated_hours = random.randint(1, 2)

        created_at = random_date(60)
        scheduled_drop_off = None
        actual_drop_off = None
        completed_at = None
        total_actual = None

        if status in ['SCHEDULED']:
            scheduled_drop_off = random_future_date(14)
        elif status in ['IN_PROGRESS', 'WAITING_PARTS']:
            scheduled_drop_off = random_date(7)
            actual_drop_off = scheduled_drop_off
        elif status in ['COMPLETED', 'INVOICED']:
            scheduled_drop_off = random_date(30)
            actual_drop_off = scheduled_drop_off
            completed_at = random_date(15)
            total_actual = total_estimate + random.randint(-200, 500)

        job = {
            'job_number': job_number,
            'customer_id': customer['id'],
            'vehicle_id': vehicle['id'],
            'job_type': job_type,
            'damage_type': damage_type,
            'status': status,
            'total_estimate': total_estimate,
            'total_actual': total_actual,
            'estimated_hours': estimated_hours,
            'scheduled_drop_off': scheduled_drop_off,
            'actual_drop_off': actual_drop_off,
            'completed_at': completed_at,
            'priority': random.choice(['LOW', 'NORMAL', 'HIGH', 'URGENT']),
            'internal_notes': random.choice(['', 'Customer requested morning appointment', 'Insurance pre-approved', 'Rush job']),
            'created_at': created_at,
            'updated_at': random_date(7)
        }

        cursor.execute('''
            INSERT INTO jobs (job_number, customer_id, vehicle_id, job_type, damage_type, status,
                            total_estimate, total_actual, estimated_hours, scheduled_drop_off,
                            actual_drop_off, completed_at, priority, internal_notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (job['job_number'], job['customer_id'], job['vehicle_id'], job['job_type'],
              job['damage_type'], job['status'], job['total_estimate'], job['total_actual'],
              job['estimated_hours'], job['scheduled_drop_off'], job['actual_drop_off'],
              job['completed_at'], job['priority'], job['internal_notes'],
              job['created_at'], job['updated_at']))

        job['id'] = cursor.lastrowid
        jobs.append(job)

    conn.commit()
    print(f"Created {len(jobs)} jobs")
    return jobs


def create_leads(conn, count=20):
    """Create sample leads (potential customers not yet converted)."""
    cursor = conn.cursor()
    leads = []

    for i in range(count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        status = random.choice(['NEW', 'CONTACTED', 'QUALIFIED'])  # Don't create converted/lost leads

        make = random.choice(list(CAR_MAKES.keys()))
        model = random.choice(CAR_MAKES[make])

        lead = {
            'first_name': first,
            'last_name': last,
            'email': random_email(first, last),
            'phone': random_phone(),
            'source': random.choice(LEAD_SOURCES),
            'status': status,
            'temperature': random.choice(['HOT', 'WARM', 'COLD']),
            'score': random.randint(20, 100),
            'vehicle_year': random.randint(2018, 2024),
            'vehicle_make': make,
            'vehicle_model': model,
            'damage_type': random.choice(['HAIL', 'DOOR_DING', 'CREASE', 'MINOR_DENT']),
            'damage_description': random.choice(['Hail damage from recent storm', 'Door ding in parking lot',
                                                  'Multiple dents', 'Minor hail damage', 'Shopping cart dent']),
            'estimated_repair_cost': random.randint(200, 5000),
            'notes': random.choice(['', 'Called back, interested', 'Waiting for insurance approval',
                                   'Wants free estimate', 'Referred by existing customer']),
            'follow_up_count': random.randint(0, 5),
            'created_at': random_date(30),
            'updated_at': random_date(7),
            'last_contact_date': random_date(5) if status != 'NEW' else None,
            'next_follow_up_date': random_future_date(7) if status in ['CONTACTED', 'QUALIFIED'] else None
        }

        cursor.execute('''
            INSERT INTO leads (first_name, last_name, email, phone, source, status, temperature, score,
                             vehicle_year, vehicle_make, vehicle_model, damage_type, damage_description,
                             estimated_repair_cost, notes, follow_up_count, created_at, updated_at,
                             last_contact_date, next_follow_up_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (lead['first_name'], lead['last_name'], lead['email'], lead['phone'], lead['source'],
              lead['status'], lead['temperature'], lead['score'], lead['vehicle_year'], lead['vehicle_make'],
              lead['vehicle_model'], lead['damage_type'], lead['damage_description'],
              lead['estimated_repair_cost'], lead['notes'], lead['follow_up_count'],
              lead['created_at'], lead['updated_at'], lead['last_contact_date'], lead['next_follow_up_date']))

        lead['id'] = cursor.lastrowid
        leads.append(lead)

    conn.commit()
    print(f"Created {len(leads)} leads")
    return leads


def create_estimates(conn, jobs, count=15):
    """Create sample estimates linked to jobs."""
    cursor = conn.cursor()
    estimates = []

    # Get jobs without estimates
    available_jobs = [j for j in jobs if j['status'] in ['PENDING', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'INVOICED']]
    selected_jobs = random.sample(available_jobs, min(count, len(available_jobs)))

    for i, job in enumerate(selected_jobs):
        status = random.choice(ESTIMATE_STATUSES)
        estimate_number = f"EST-{datetime.now().year}-{1000 + i}"

        # Create line items
        line_items = []
        services = [
            ('PDR - Hail Damage Repair', 'PDR', 75, 150),
            ('PDR - Door Ding Removal', 'PDR', 50, 100),
            ('PDR - Crease Repair', 'PDR', 100, 200),
            ('Glue Pull Repair', 'PDR', 75, 125),
        ]

        num_items = random.randint(1, 4)
        for j in range(num_items):
            service_name, service_type, min_price, max_price = random.choice(services)
            qty = random.randint(1, 10) if 'Hail' in service_name else random.randint(1, 3)
            price = random.randint(min_price, max_price)
            line_items.append({
                'description': service_name,
                'service_type': service_type,
                'quantity': qty,
                'unit_price': price,
                'total': qty * price
            })

        # Calculate totals
        labor_hours = job['estimated_hours'] or random.randint(2, 8)
        labor_rate = random.choice([65, 75, 85, 95])
        labor_total = labor_hours * labor_rate
        parts_total = sum(item['total'] for item in line_items)
        subtotal = labor_total + parts_total
        tax_rate = 8.25
        tax_amount = round(subtotal * tax_rate / 100, 2)
        total = round(subtotal + tax_amount, 2)

        created_at = job['created_at']
        sent_date = random_date(30) if status != 'DRAFT' else None
        approved_date = random_date(20) if status == 'APPROVED' else None

        estimate = {
            'estimate_number': estimate_number,
            'job_id': job['id'],
            'status': status,
            'labor_hours': labor_hours,
            'labor_rate': labor_rate,
            'labor_total': labor_total,
            'parts_total': parts_total,
            'subtotal': subtotal,
            'tax_rate': tax_rate,
            'tax_amount': tax_amount,
            'total': total,
            'line_items': json.dumps(line_items),
            'notes': random.choice(['', 'Price valid for 30 days', 'Includes all labor and materials']),
            'created_date': created_at[:10],
            'sent_date': sent_date[:10] if sent_date else None,
            'approved_date': approved_date[:10] if approved_date else None,
            'expires_date': random_future_date(30)[:10],
            'created_at': created_at,
            'updated_at': random_date(7)
        }

        cursor.execute('''
            INSERT INTO estimates (estimate_number, job_id, status, labor_hours, labor_rate, labor_total,
                                 parts_total, subtotal, tax_rate, tax_amount, total, line_items, notes,
                                 created_date, sent_date, approved_date, expires_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (estimate['estimate_number'], estimate['job_id'], estimate['status'], estimate['labor_hours'],
              estimate['labor_rate'], estimate['labor_total'], estimate['parts_total'], estimate['subtotal'],
              estimate['tax_rate'], estimate['tax_amount'], estimate['total'], estimate['line_items'],
              estimate['notes'], estimate['created_date'], estimate['sent_date'], estimate['approved_date'],
              estimate['expires_date'], estimate['created_at'], estimate['updated_at']))

        estimate['id'] = cursor.lastrowid
        estimates.append(estimate)

    conn.commit()
    print(f"Created {len(estimates)} estimates")
    return estimates


def create_technicians(conn):
    """Create sample technicians."""
    cursor = conn.cursor()

    techs = [
        ('Mike', 'Johnson', 'mike@hailtracker.com', '(555) 123-4567', 'PDR', 'SENIOR'),
        ('Sarah', 'Williams', 'sarah@hailtracker.com', '(555) 234-5678', 'PDR', 'MID'),
        ('David', 'Chen', 'david@hailtracker.com', '(555) 345-6789', 'PDR', 'MID'),
        ('Emily', 'Brown', 'emily@hailtracker.com', '(555) 456-7890', 'CONVENTIONAL', 'SENIOR'),
        ('James', 'Wilson', 'james@hailtracker.com', '(555) 567-8901', 'PAINT', 'JUNIOR'),
    ]

    for first, last, email, phone, specialties, skill_level in techs:
        cursor.execute('''
            INSERT OR IGNORE INTO technicians (first_name, last_name, email, phone, specialties, skill_level, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
        ''', (first, last, email, phone, specialties, skill_level, random_date(365)))

    conn.commit()
    print(f"Created {len(techs)} technicians")


def main():
    print(f"Database path: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = get_db()

    try:
        # Clear existing sample data (optional - comment out to append)
        print("\n=== Clearing existing data ===")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM estimates")
        cursor.execute("DELETE FROM jobs")
        cursor.execute("DELETE FROM vehicles")
        cursor.execute("DELETE FROM leads")
        cursor.execute("DELETE FROM customers")
        conn.commit()

        # Create sample data
        print("\n=== Creating Sample Data ===\n")

        create_technicians(conn)
        customers = create_customers(conn, 25)
        vehicles = create_vehicles(conn, customers)
        jobs = create_jobs(conn, customers, vehicles, 40)
        leads = create_leads(conn, 20)
        estimates = create_estimates(conn, jobs, 15)

        print("\n=== Sample Data Created Successfully ===")
        print(f"- {len(customers)} customers")
        print(f"- {len(vehicles)} vehicles")
        print(f"- {len(jobs)} jobs")
        print(f"- {len(leads)} leads")
        print(f"- {len(estimates)} estimates")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == '__main__':
    main()
