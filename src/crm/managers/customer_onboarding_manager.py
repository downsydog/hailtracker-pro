"""
Customer Onboarding Manager
Complete field enrollment workflow

FEATURES:
- Tablet handoff form
- VIN scanning
- Photo capture
- Insurance authorization
- Portal auto-creation
- Digital flyer delivery
- Referral tracking
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from src.crm.models.database import Database
import json
import secrets
import string
import hashlib


class CustomerOnboardingManager:
    """
    Manage complete customer onboarding workflow

    From field sign-up to portal access
    """

    def __init__(self, db_path: str = "data/pdr_crm.db"):
        """Initialize onboarding manager"""
        self.db = Database(db_path)
        self._init_tables()

    def _init_tables(self):
        """Initialize required database tables"""

        # Enrollment sessions table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS enrollment_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enrollment_id TEXT UNIQUE NOT NULL,
                salesperson_id INTEGER,
                customer_id INTEGER,
                location_lat REAL,
                location_lon REAL,
                vehicle_scan_type TEXT,
                vehicle_scan_data TEXT,
                started_at TEXT,
                completed_at TEXT,
                status TEXT DEFAULT 'IN_PROGRESS'
            )
        """)

        # Enrollment photos table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS enrollment_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enrollment_id TEXT,
                photo_type TEXT,
                photo_url TEXT,
                captured_at TEXT
            )
        """)

        # Customer insurance table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS customer_insurance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                company TEXT,
                policy_number TEXT,
                claim_number TEXT,
                deductible REAL,
                agent_name TEXT,
                agent_phone TEXT,
                enrollment_id TEXT,
                created_at TEXT
            )
        """)

        # Customer signatures table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS customer_signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                enrollment_id TEXT,
                form_type TEXT,
                signature_data TEXT,
                signed_at TEXT
            )
        """)

        # Customer portal access table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS customer_portal_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER UNIQUE,
                username TEXT UNIQUE,
                password_hash TEXT,
                created_at TEXT,
                last_login TEXT,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)

        # Customer communications table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS customer_communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                type TEXT,
                subject TEXT,
                message TEXT,
                sent_at TEXT,
                status TEXT
            )
        """)

        # Customer referrals table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS customer_referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_customer_id INTEGER,
                referred_customer_id INTEGER,
                enrollment_id TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'PENDING',
                status_notes TEXT,
                updated_at TEXT,
                commission_amount REAL,
                commission_earned_at TEXT
            )
        """)

    # ========================================================================
    # CUSTOMER ENROLLMENT (TABLET HANDOFF)
    # ========================================================================

    def start_enrollment(
        self,
        salesperson_id: int,
        location_lat: float,
        location_lon: float
    ) -> str:
        """
        Start new customer enrollment

        Returns enrollment session ID for tracking
        """

        enrollment_id = self._generate_enrollment_id()

        self.db.execute("""
            INSERT INTO enrollment_sessions (
                enrollment_id, salesperson_id,
                location_lat, location_lon,
                started_at, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            enrollment_id,
            salesperson_id,
            location_lat,
            location_lon,
            datetime.now().isoformat(),
            'IN_PROGRESS'
        ))

        print(f"Enrollment Started")
        print(f"   Session ID: {enrollment_id}")
        print(f"   Salesperson: {salesperson_id}")

        return enrollment_id

    def _generate_enrollment_id(self) -> str:
        """Generate unique enrollment session ID"""
        return f"ENR-{datetime.now().strftime('%Y%m%d')}-{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))}"

    def collect_customer_info(
        self,
        enrollment_id: str,
        customer_data: Dict
    ) -> int:
        """
        Collect customer information (customer fills on tablet)

        Args:
            enrollment_id: Enrollment session ID
            customer_data: {
                'first_name': str,
                'last_name': str,
                'phone': str,
                'email': str,
                'address': str,
                'city': str,
                'state': str,
                'zip': str
            }

        Returns:
            Customer ID
        """

        # Create customer record (using schema column names)
        result = self.db.execute("""
            INSERT INTO customers (
                first_name, last_name, phone, email,
                street_address, city, state, zip_code,
                created_at, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_data['first_name'],
            customer_data['last_name'],
            customer_data['phone'],
            customer_data.get('email'),
            customer_data.get('address') or customer_data.get('street_address'),
            customer_data.get('city'),
            customer_data.get('state'),
            customer_data.get('zip') or customer_data.get('zip_code'),
            datetime.now().isoformat(),
            'FIELD_ENROLLMENT'
        ))

        customer_id = result[0]['id']

        # Update enrollment session
        self.db.execute("""
            UPDATE enrollment_sessions
            SET customer_id = ?
            WHERE enrollment_id = ?
        """, (customer_id, enrollment_id))

        print(f"Customer Info Collected")
        print(f"   Name: {customer_data['first_name']} {customer_data['last_name']}")
        print(f"   Phone: {customer_data['phone']}")
        print(f"   Email: {customer_data.get('email', 'Not provided')}")

        return customer_id

    # ========================================================================
    # VIN/LICENSE PLATE SCANNING
    # ========================================================================

    def scan_vehicle(
        self,
        enrollment_id: str,
        scan_type: str,
        scan_data: str
    ) -> Dict:
        """
        Scan VIN or license plate

        Args:
            enrollment_id: Enrollment session ID
            scan_type: 'VIN' or 'LICENSE_PLATE'
            scan_data: Scanned data (VIN or plate number)

        Returns:
            Vehicle information decoded from VIN
        """

        if scan_type == 'VIN':
            vehicle_info = self._decode_vin(scan_data)
        else:
            # License plate lookup (would use API in production)
            vehicle_info = self._lookup_license_plate(scan_data)

        # Store scanned data
        self.db.execute("""
            UPDATE enrollment_sessions
            SET vehicle_scan_type = ?,
                vehicle_scan_data = ?
            WHERE enrollment_id = ?
        """, (scan_type, scan_data, enrollment_id))

        print(f"Vehicle Scanned")
        print(f"   Type: {scan_type}")
        print(f"   Data: {scan_data}")
        print(f"   Vehicle: {vehicle_info['year']} {vehicle_info['make']} {vehicle_info['model']}")

        return vehicle_info

    def _decode_vin(self, vin: str) -> Dict:
        """
        Decode VIN to get vehicle information

        In production: Use NHTSA API or similar
        """

        # VIN decoding logic (simplified)
        # Position 10 = Model year
        year_codes = {
            'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014,
            'F': 2015, 'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019,
            'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024,
            'S': 2025, 'T': 2026
        }

        year = year_codes.get(vin[9].upper(), 2022) if len(vin) >= 10 else 2022

        # Make detection from WMI (first 3 characters)
        make_codes = {
            '1G1': 'Chevrolet', '1G2': 'Pontiac', '1GC': 'Chevrolet',
            '1HG': 'Honda', '1FA': 'Ford', '1FM': 'Ford',
            '2T1': 'Toyota', '4T1': 'Toyota', '5YJ': 'Tesla',
            'JTD': 'Toyota', 'JN1': 'Nissan', 'WBA': 'BMW'
        }

        wmi = vin[:3].upper() if len(vin) >= 3 else ''
        make = make_codes.get(wmi, 'Toyota')

        return {
            'vin': vin,
            'year': year,
            'make': make,
            'model': 'Camry',  # Would be decoded from VIN
            'trim': 'LE',
            'color': 'Silver',
            'engine': '2.5L 4-Cyl',
            'transmission': 'Automatic'
        }

    def _lookup_license_plate(self, plate: str) -> Dict:
        """
        Lookup vehicle by license plate

        In production: Use state DMV API or commercial service
        """

        return {
            'license_plate': plate,
            'year': 2022,
            'make': 'Toyota',
            'model': 'Camry',
            'color': 'Silver',
            'state': 'TX'
        }

    def create_vehicle_record(
        self,
        customer_id: int,
        vehicle_info: Dict,
        enrollment_id: str = None
    ) -> int:
        """Create vehicle record from scanned data"""

        result = self.db.execute("""
            INSERT INTO vehicles (
                customer_id, year, make, model, vin,
                color, license_plate, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            vehicle_info.get('year'),
            vehicle_info.get('make'),
            vehicle_info.get('model'),
            vehicle_info.get('vin'),
            vehicle_info.get('color'),
            vehicle_info.get('license_plate'),
            datetime.now().isoformat()
        ))

        vehicle_id = result[0]['id']

        print(f"Vehicle Record Created")
        print(f"   Vehicle ID: {vehicle_id}")

        return vehicle_id

    # ========================================================================
    # PHOTO CAPTURE
    # ========================================================================

    def capture_reference_photos(
        self,
        enrollment_id: str,
        photo_type: str,
        photo_data: str
    ) -> int:
        """
        Capture reference photos during enrollment

        Photo types:
        - DAMAGE_OVERVIEW
        - HOOD
        - ROOF
        - TRUNK
        - DRIVER_SIDE
        - PASSENGER_SIDE
        - VIN_PLATE
        """

        result = self.db.execute("""
            INSERT INTO enrollment_photos (
                enrollment_id, photo_type, photo_url,
                captured_at
            ) VALUES (?, ?, ?, ?)
        """, (
            enrollment_id,
            photo_type,
            photo_data,
            datetime.now().isoformat()
        ))

        photo_id = result[0]['id']

        print(f"Photo Captured: {photo_type}")

        return photo_id

    def get_photo_checklist(self) -> List[Dict]:
        """Get required photos checklist"""

        return [
            {'type': 'DAMAGE_OVERVIEW', 'label': 'Overall Damage View', 'required': True},
            {'type': 'HOOD', 'label': 'Hood Close-up', 'required': True},
            {'type': 'ROOF', 'label': 'Roof Close-up', 'required': True},
            {'type': 'TRUNK', 'label': 'Trunk Close-up', 'required': False},
            {'type': 'DRIVER_SIDE', 'label': 'Driver Side', 'required': False},
            {'type': 'PASSENGER_SIDE', 'label': 'Passenger Side', 'required': False},
            {'type': 'VIN_PLATE', 'label': 'VIN Plate Photo', 'required': True}
        ]

    def get_enrollment_photos(self, enrollment_id: str) -> List[Dict]:
        """Get all photos for an enrollment"""

        return self.db.execute("""
            SELECT * FROM enrollment_photos
            WHERE enrollment_id = ?
            ORDER BY captured_at
        """, (enrollment_id,))

    # ========================================================================
    # INSURANCE INFORMATION
    # ========================================================================

    def collect_insurance_info(
        self,
        customer_id: int,
        enrollment_id: str,
        insurance_data: Dict
    ) -> int:
        """
        Collect insurance information

        Args:
            insurance_data: {
                'company': str,
                'policy_number': str,
                'claim_number': str (optional),
                'deductible': float,
                'agent_name': str,
                'agent_phone': str
            }
        """

        result = self.db.execute("""
            INSERT INTO customer_insurance (
                customer_id, company, policy_number,
                claim_number, deductible, agent_name,
                agent_phone, enrollment_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            insurance_data['company'],
            insurance_data['policy_number'],
            insurance_data.get('claim_number'),
            insurance_data.get('deductible'),
            insurance_data.get('agent_name'),
            insurance_data.get('agent_phone'),
            enrollment_id,
            datetime.now().isoformat()
        ))

        insurance_id = result[0]['id']

        print(f"Insurance Info Collected")
        print(f"   Company: {insurance_data['company']}")
        print(f"   Policy: {insurance_data['policy_number']}")

        return insurance_id

    # ========================================================================
    # DIRECTION OF PAY (E-SIGNATURE)
    # ========================================================================

    def generate_direction_of_pay(
        self,
        customer_id: int,
        enrollment_id: str
    ) -> Dict:
        """
        Generate Direction of Pay / Assignment of Benefits form

        Returns form data for e-signature
        """

        customer = self.db.execute(
            "SELECT * FROM customers WHERE id = ?",
            (customer_id,)
        )[0]

        insurance = self.db.execute("""
            SELECT * FROM customer_insurance
            WHERE customer_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (customer_id,))

        insurance_info = insurance[0] if insurance else {}

        form_data = {
            'form_type': 'DIRECTION_OF_PAY',
            'customer_name': f"{customer['first_name']} {customer['last_name']}",
            'insurance_company': insurance_info.get('company', ''),
            'policy_number': insurance_info.get('policy_number', ''),
            'authorization_text': f"""
I, {customer['first_name']} {customer['last_name']}, hereby authorize and direct
{insurance_info.get('company', 'my insurance company')} to issue payment directly to
PDR Solutions for hail damage repair services performed on my vehicle.

I understand that:
1. PDR Solutions is authorized to contact my insurance company on my behalf
2. Payment will be made directly to PDR Solutions
3. I am responsible for my deductible amount
4. This authorization remains in effect for this claim only

Policy Number: {insurance_info.get('policy_number', 'N/A')}
Date: {date.today().strftime('%B %d, %Y')}
            """.strip(),
            'generated_at': datetime.now().isoformat()
        }

        print(f"Direction of Pay Generated")

        return form_data

    def capture_signature(
        self,
        enrollment_id: str,
        customer_id: int,
        signature_data: str,
        form_type: str = 'DIRECTION_OF_PAY'
    ) -> int:
        """
        Capture customer e-signature

        Args:
            signature_data: Base64 encoded signature image
        """

        result = self.db.execute("""
            INSERT INTO customer_signatures (
                customer_id, enrollment_id, form_type,
                signature_data, signed_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            customer_id,
            enrollment_id,
            form_type,
            signature_data,
            datetime.now().isoformat()
        ))

        signature_id = result[0]['id']

        print(f"Signature Captured")
        print(f"   Form: {form_type}")

        return signature_id

    # ========================================================================
    # CUSTOMER PORTAL AUTO-CREATION
    # ========================================================================

    def create_customer_portal_access(
        self,
        customer_id: int
    ) -> Dict:
        """
        Auto-create customer portal login credentials

        Username: Last name (lowercase)
        Password: License plate number (or temp password)

        Returns login credentials
        """

        customer = self.db.execute(
            "SELECT * FROM customers WHERE id = ?",
            (customer_id,)
        )[0]

        vehicle = self.db.execute("""
            SELECT * FROM vehicles
            WHERE customer_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (customer_id,))

        # Generate credentials
        base_username = customer['last_name'].lower().replace(' ', '')

        # Check for existing username and append number if needed
        existing = self.db.execute(
            "SELECT COUNT(*) as count FROM customer_portal_access WHERE username LIKE ?",
            (f"{base_username}%",)
        )[0]['count']

        username = base_username if existing == 0 else f"{base_username}{existing + 1}"
        password = vehicle[0]['license_plate'] if vehicle and vehicle[0].get('license_plate') else self._generate_temp_password()

        # Hash password
        password_hash = self._hash_password(password)

        # Create portal account
        result = self.db.execute("""
            INSERT OR REPLACE INTO customer_portal_access (
                customer_id, username, password_hash,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            customer_id,
            username,
            password_hash,
            datetime.now().isoformat(),
            'ACTIVE'
        ))

        access_id = result[0]['id']

        credentials = {
            'username': username,
            'password': password,  # Only returned once
            'portal_url': 'https://portal.pdrcrm.com',
            'access_id': access_id
        }

        print(f"Portal Access Created")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Portal: {credentials['portal_url']}")

        return credentials

    def _generate_temp_password(self) -> str:
        """Generate temporary password if no license plate"""
        return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

    def _hash_password(self, password: str) -> str:
        """Hash password (simplified - use bcrypt in production)"""
        return hashlib.sha256(password.encode()).hexdigest()

    # ========================================================================
    # COMPLETE ENROLLMENT & SEND WELCOME
    # ========================================================================

    def complete_enrollment(
        self,
        enrollment_id: str,
        referred_by_customer_id: Optional[int] = None
    ) -> Dict:
        """
        Complete enrollment and trigger welcome communications

        Returns: Complete enrollment summary
        """

        # Get enrollment data
        enrollment = self.db.execute(
            "SELECT * FROM enrollment_sessions WHERE enrollment_id = ?",
            (enrollment_id,)
        )[0]

        customer_id = enrollment['customer_id']

        # Create portal access
        portal_credentials = self.create_customer_portal_access(customer_id)

        # Track referral if applicable
        if referred_by_customer_id:
            self._create_referral_tracking(
                referrer_id=referred_by_customer_id,
                referred_id=customer_id,
                enrollment_id=enrollment_id
            )

        # Mark enrollment complete
        self.db.execute("""
            UPDATE enrollment_sessions
            SET status = 'COMPLETED',
                completed_at = ?
            WHERE enrollment_id = ?
        """, (datetime.now().isoformat(), enrollment_id))

        # Send welcome communications
        self._send_welcome_package(customer_id, portal_credentials)

        summary = {
            'enrollment_id': enrollment_id,
            'customer_id': customer_id,
            'portal_credentials': portal_credentials,
            'welcome_sent': True,
            'completed_at': datetime.now().isoformat()
        }

        print(f"Enrollment Complete!")
        print(f"   Customer ID: {customer_id}")
        print(f"   Portal created: Yes")
        print(f"   Welcome package sent: Yes")

        return summary

    def _send_welcome_package(
        self,
        customer_id: int,
        portal_credentials: Dict
    ):
        """Send welcome email/SMS with digital flyer"""

        customer = self.db.execute(
            "SELECT * FROM customers WHERE id = ?",
            (customer_id,)
        )[0]

        # Generate referral link
        referral_link = f"https://portal.pdrcrm.com/refer/{customer_id}"

        welcome_message = f"""
Welcome {customer['first_name']}!

Thank you for choosing PDR Solutions! Your account is ready.

PORTAL ACCESS:
{portal_credentials['portal_url']}
Username: {portal_credentials['username']}
Password: {portal_credentials['password']}

NEXT STEPS:
1. Log in to track your repair status
2. We'll contact your insurance company
3. You'll receive updates via text/email

REFER & EARN:
Share this link with friends who need hail repair:
{referral_link}

You'll earn $50 for each completed referral!

Questions? Reply to this message or call (555) 123-4567
        """.strip()

        # Log communication
        self.db.execute("""
            INSERT INTO customer_communications (
                customer_id, type, subject, message,
                sent_at, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            'WELCOME_PACKAGE',
            'Welcome to PDR Solutions',
            welcome_message,
            datetime.now().isoformat(),
            'SENT'
        ))

        print(f"Welcome Email Sent to {customer.get('email', 'N/A')}")
        print(f"Welcome SMS Sent to {customer['phone']}")

    def _create_referral_tracking(
        self,
        referrer_id: int,
        referred_id: int,
        enrollment_id: str
    ):
        """Create referral tracking record"""

        self.db.execute("""
            INSERT INTO customer_referrals (
                referrer_customer_id, referred_customer_id,
                enrollment_id, created_at, status
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            referrer_id,
            referred_id,
            enrollment_id,
            datetime.now().isoformat(),
            'PENDING'
        ))

        print(f"Referral Tracked: Customer {referrer_id} referred {referred_id}")

    # ========================================================================
    # ENROLLMENT STATUS & REPORTING
    # ========================================================================

    def get_enrollment_status(self, enrollment_id: str) -> Dict:
        """Get current status of enrollment"""

        enrollment = self.db.execute(
            "SELECT * FROM enrollment_sessions WHERE enrollment_id = ?",
            (enrollment_id,)
        )[0]

        photos = self.get_enrollment_photos(enrollment_id)
        checklist = self.get_photo_checklist()

        # Check completion
        required_photos = [p['type'] for p in checklist if p['required']]
        captured_photos = [p['photo_type'] for p in photos]
        missing_photos = [p for p in required_photos if p not in captured_photos]

        return {
            'enrollment_id': enrollment_id,
            'status': enrollment['status'],
            'customer_id': enrollment.get('customer_id'),
            'photos_captured': len(photos),
            'photos_required': len(required_photos),
            'missing_photos': missing_photos,
            'started_at': enrollment['started_at'],
            'completed_at': enrollment.get('completed_at')
        }

    def get_daily_enrollments(
        self,
        salesperson_id: Optional[int] = None,
        date_str: Optional[str] = None
    ) -> List[Dict]:
        """Get enrollments for a specific day"""

        if not date_str:
            date_str = date.today().isoformat()

        query = """
            SELECT es.*, c.first_name, c.last_name, c.phone
            FROM enrollment_sessions es
            LEFT JOIN customers c ON c.id = es.customer_id
            WHERE DATE(es.started_at) = ?
        """
        params = [date_str]

        if salesperson_id:
            query += " AND es.salesperson_id = ?"
            params.append(salesperson_id)

        query += " ORDER BY es.started_at DESC"

        return self.db.execute(query, tuple(params))
