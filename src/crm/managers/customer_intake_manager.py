"""
Customer Self-Intake Manager
Handles lobby tablet intake form processing

FEATURES:
- Process walk-in customer intake forms
- Create customer, vehicle, and lead records
- Link insurance information
- Handle referral tracking for commissions
- Send confirmation notifications
- Notify office of new walk-ins

FLOW:
1. Customer fills out tablet form
2. Form submits to /intake/customer
3. Create customer record (or find existing)
4. Create vehicle record (decode VIN if provided)
5. Link insurance info
6. Create lead with source tracking
7. If referral, link to referrer
8. Send confirmation to customer
9. Notify office staff
"""

import os
import re
from typing import Optional, Dict, List, Any
from datetime import datetime, date

from src.crm.models.database import Database
from src.utils.vin_decoder import decode_vin


class CustomerIntakeManager:
    """
    Manages customer self-intake from lobby tablets.

    Designed for walk-in customers filling out their info
    before meeting with an estimator.
    """

    # Lead sources from intake form
    LEAD_SOURCES = {
        'door_knocker': 'DOOR_KNOCKER',
        'referral': 'REFERRAL',
        'google': 'GOOGLE',
        'facebook': 'FACEBOOK',
        'drove_by': 'DROVE_BY',
        'insurance_referred': 'INSURANCE',
        'other': 'OTHER'
    }

    # US States for dropdown
    US_STATES = [
        ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'),
        ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'),
        ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'),
        ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'),
        ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'),
        ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'),
        ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'),
        ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'),
        ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'),
        ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'),
        ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'),
        ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'),
        ('WI', 'Wisconsin'), ('WY', 'Wyoming'), ('DC', 'Washington DC')
    ]

    def __init__(self, db_path: str = "data/pdr_crm.db"):
        """Initialize intake manager"""
        self.db = Database(db_path)
        self.db_path = db_path

    def process_intake(self, form_data: Dict) -> Dict:
        """
        Process complete intake form submission.

        Args:
            form_data: All form fields from the intake form

        Returns:
            Dict with:
                - success: bool
                - customer_id: int (if successful)
                - vehicle_id: int (if successful)
                - lead_id: int (if successful)
                - message: str
                - errors: list (if any)
        """
        errors = []

        # Validate required fields
        validation = self._validate_form(form_data)
        if not validation['valid']:
            return {
                'success': False,
                'errors': validation['errors'],
                'message': 'Please correct the highlighted fields.'
            }

        try:
            # 1. Find or create customer
            customer_result = self._process_customer(form_data)
            if not customer_result['success']:
                errors.append(customer_result['error'])
                raise ValueError("Customer creation failed")

            customer_id = customer_result['customer_id']
            is_new_customer = customer_result['is_new']

            # 2. Create vehicle record
            vehicle_result = self._process_vehicle(form_data, customer_id)
            if not vehicle_result['success']:
                errors.append(vehicle_result['error'])
                # Continue anyway - vehicle is optional
            vehicle_id = vehicle_result.get('vehicle_id')

            # 3. Create lead with source tracking
            lead_result = self._create_lead(
                form_data, customer_id, vehicle_id
            )
            lead_id = lead_result.get('lead_id')

            # 4. Handle referral tracking
            if form_data.get('source') == 'referral' and form_data.get('referrer_name'):
                self._track_referral(customer_id, form_data)

            # 5. Store consent preferences
            self._store_consent(customer_id, form_data)

            # 6. Store signature if provided
            if form_data.get('signature_data'):
                self._store_signature(customer_id, form_data['signature_data'])

            # 7. Send confirmation notification to customer
            self._send_customer_confirmation(customer_id, form_data)

            # 8. Notify office staff
            self._notify_office(customer_id, vehicle_id, form_data)

            # Build success response
            customer = self.db.get_by_id('customers', customer_id)
            customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()

            vehicle_desc = ""
            if vehicle_id:
                vehicle = self.db.get_by_id('vehicles', vehicle_id)
                if vehicle:
                    vehicle_desc = f"{vehicle.get('year', '')} {vehicle.get('make', '')} {vehicle.get('model', '')}".strip()

            return {
                'success': True,
                'customer_id': customer_id,
                'vehicle_id': vehicle_id,
                'lead_id': lead_id,
                'is_new_customer': is_new_customer,
                'customer_name': customer_name,
                'vehicle_description': vehicle_desc,
                'message': 'Thank you! Someone will be with you shortly.'
            }

        except Exception as e:
            return {
                'success': False,
                'errors': errors + [str(e)],
                'message': 'An error occurred. Please see the front desk for assistance.'
            }

    def _validate_form(self, data: Dict) -> Dict:
        """Validate required form fields"""
        errors = []

        # Required fields
        if not data.get('first_name', '').strip():
            errors.append({'field': 'first_name', 'message': 'First name is required'})

        if not data.get('last_name', '').strip():
            errors.append({'field': 'last_name', 'message': 'Last name is required'})

        if not data.get('phone', '').strip():
            errors.append({'field': 'phone', 'message': 'Phone number is required'})
        elif not self._validate_phone(data.get('phone', '')):
            errors.append({'field': 'phone', 'message': 'Please enter a valid phone number'})

        # Email validation if provided
        if data.get('email') and not self._validate_email(data.get('email', '')):
            errors.append({'field': 'email', 'message': 'Please enter a valid email address'})

        # VIN validation if provided
        if data.get('vin'):
            vin = data['vin'].upper().strip()
            if len(vin) != 17:
                errors.append({'field': 'vin', 'message': 'VIN must be 17 characters'})

        # Consent checkboxes
        if not data.get('consent_sms'):
            errors.append({'field': 'consent_sms', 'message': 'SMS consent is required'})

        if not data.get('consent_email'):
            errors.append({'field': 'consent_email', 'message': 'Email consent is required'})

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def _validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        clean = re.sub(r'[^\d]', '', phone)
        return len(clean) >= 10

    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _format_phone(self, phone: str) -> str:
        """Format phone number to (XXX) XXX-XXXX"""
        clean = re.sub(r'[^\d]', '', phone)
        if len(clean) == 10:
            return f"({clean[:3]}) {clean[3:6]}-{clean[6:]}"
        elif len(clean) == 11 and clean[0] == '1':
            return f"({clean[1:4]}) {clean[4:7]}-{clean[7:]}"
        return phone

    def _process_customer(self, data: Dict) -> Dict:
        """Create or find existing customer"""
        phone = self._format_phone(data.get('phone', ''))
        email = data.get('email', '').strip().lower() if data.get('email') else None

        # Check for existing customer by phone
        existing = self.db.execute("""
            SELECT id FROM customers
            WHERE REPLACE(REPLACE(REPLACE(phone, '-', ''), '(', ''), ')', '') = ?
              AND deleted_at IS NULL
        """, (re.sub(r'[^\d]', '', phone),))

        if existing:
            # Update existing customer
            customer_id = existing[0]['id']
            self.db.execute("""
                UPDATE customers SET
                    first_name = ?,
                    last_name = ?,
                    email = COALESCE(?, email),
                    address_line1 = COALESCE(?, address_line1),
                    address_line2 = COALESCE(?, address_line2),
                    city = COALESCE(?, city),
                    state = COALESCE(?, state),
                    zip_code = COALESCE(?, zip_code),
                    updated_at = ?
                WHERE id = ?
            """, (
                data.get('first_name', '').strip(),
                data.get('last_name', '').strip(),
                email,
                data.get('address_line1', '').strip() or None,
                data.get('address_line2', '').strip() or None,
                data.get('city', '').strip() or None,
                data.get('state', '').strip() or None,
                data.get('zip_code', '').strip() or None,
                datetime.now().isoformat(),
                customer_id
            ))

            return {'success': True, 'customer_id': customer_id, 'is_new': False}

        # Create new customer
        customer_data = {
            'first_name': data.get('first_name', '').strip(),
            'last_name': data.get('last_name', '').strip(),
            'phone': phone,
            'email': email,
            'address_line1': data.get('address_line1', '').strip() or None,
            'address_line2': data.get('address_line2', '').strip() or None,
            'city': data.get('city', '').strip() or None,
            'state': data.get('state', '').strip() or None,
            'zip_code': data.get('zip_code', '').strip() or None,
            'source': 'WALK_IN',
            'status': 'ACTIVE',
            'customer_since': date.today().isoformat(),
            'created_at': datetime.now().isoformat()
        }

        customer_id = self.db.insert('customers', customer_data)

        return {'success': True, 'customer_id': customer_id, 'is_new': True}

    def _process_vehicle(self, data: Dict, customer_id: int) -> Dict:
        """Create vehicle record, optionally decoding VIN"""
        vin = data.get('vin', '').upper().strip() if data.get('vin') else None

        # Get vehicle info from VIN or form fields
        vehicle_info = {}

        if vin and len(vin) == 17:
            # Decode VIN
            decoded = decode_vin(vin, self.db_path)
            if not decoded.get('error'):
                vehicle_info = {
                    'year': decoded.get('year'),
                    'make': decoded.get('make'),
                    'model': decoded.get('model'),
                    'trim': decoded.get('trim'),
                    'body_style': decoded.get('body_style'),
                }

        # Override with form fields if provided
        if data.get('vehicle_year'):
            vehicle_info['year'] = int(data['vehicle_year'])
        if data.get('vehicle_make'):
            vehicle_info['make'] = data['vehicle_make'].strip()
        if data.get('vehicle_model'):
            vehicle_info['model'] = data['vehicle_model'].strip()

        # Require at least year, make, model
        if not all([vehicle_info.get('year'), vehicle_info.get('make'), vehicle_info.get('model')]):
            if not vin:
                return {'success': False, 'error': 'Vehicle information required'}

        vehicle_data = {
            'customer_id': customer_id,
            'vin': vin,
            'year': vehicle_info.get('year'),
            'make': vehicle_info.get('make'),
            'model': vehicle_info.get('model'),
            'trim': vehicle_info.get('trim'),
            'body_style': vehicle_info.get('body_style'),
            'color': data.get('vehicle_color', '').strip() or None,
            'license_plate': data.get('license_plate', '').strip().upper() or None,
            'mileage': int(data['mileage']) if data.get('mileage') else None,
            'created_at': datetime.now().isoformat()
        }

        vehicle_id = self.db.insert('vehicles', vehicle_data)

        return {'success': True, 'vehicle_id': vehicle_id}

    def _create_lead(self, data: Dict, customer_id: int, vehicle_id: int = None) -> Dict:
        """Create lead record with source tracking"""
        source_key = data.get('source', 'walk_in')
        source = self.LEAD_SOURCES.get(source_key, 'WALK_IN')

        # Get vehicle info for lead
        vehicle_year = None
        vehicle_make = None
        vehicle_model = None

        if vehicle_id:
            vehicle = self.db.get_by_id('vehicles', vehicle_id)
            if vehicle:
                vehicle_year = vehicle.get('year')
                vehicle_make = vehicle.get('make')
                vehicle_model = vehicle.get('model')

        # Calculate lead score
        score = 40  # Base score for walk-in
        if vehicle_id:
            score += 20  # Has vehicle info
        if data.get('insurance_company'):
            score += 15  # Has insurance info
        if data.get('email'):
            score += 10  # Has email
        if data.get('phone'):
            score += 10  # Has phone

        temperature = 'HOT' if score >= 70 else ('WARM' if score >= 40 else 'COLD')

        lead_data = {
            'customer_id': customer_id,
            'source': source,
            'status': 'NEW',
            'score': score,
            'temperature': temperature,
            'first_name': data.get('first_name', '').strip(),
            'last_name': data.get('last_name', '').strip(),
            'phone': self._format_phone(data.get('phone', '')),
            'email': data.get('email', '').strip().lower() if data.get('email') else None,
            'vehicle_year': vehicle_year,
            'vehicle_make': vehicle_make,
            'vehicle_model': vehicle_model,
            'notes': self._build_lead_notes(data),
            'created_at': datetime.now().isoformat()
        }

        # Add salesman if door knocker
        if source_key == 'door_knocker' and data.get('salesman_id'):
            lead_data['assigned_to'] = data['salesman_id']
            lead_data['assigned_at'] = datetime.now().isoformat()

        lead_id = self.db.insert('leads', lead_data)

        return {'lead_id': lead_id}

    def _build_lead_notes(self, data: Dict) -> str:
        """Build lead notes from intake data"""
        notes = ["Walk-in intake form submission"]

        if data.get('source') == 'referral' and data.get('referrer_name'):
            notes.append(f"Referred by: {data['referrer_name']}")

        if data.get('source') == 'door_knocker' and data.get('salesman_name'):
            notes.append(f"Door knocker: {data['salesman_name']}")

        if data.get('insurance_company'):
            notes.append(f"Insurance: {data['insurance_company']}")
            if data.get('claim_number'):
                notes.append(f"Claim #: {data['claim_number']}")
            if data.get('has_deductible') and data.get('deductible_amount'):
                notes.append(f"Deductible: ${data['deductible_amount']}")

        return "\n".join(notes)

    def _track_referral(self, customer_id: int, data: Dict):
        """Track referral for commission purposes"""
        referrer_name = data.get('referrer_name', '').strip()
        if not referrer_name:
            return

        # Try to find referrer in customers
        referrer = self.db.execute("""
            SELECT id FROM customers
            WHERE (first_name || ' ' || last_name) LIKE ?
               OR (last_name || ', ' || first_name) LIKE ?
            LIMIT 1
        """, (f"%{referrer_name}%", f"%{referrer_name}%"))

        referrer_id = referrer[0]['id'] if referrer else None

        # Create referral tracking record
        self.db.execute("""
            INSERT INTO referral_tracking (
                referrer_customer_id, referred_customer_id,
                referrer_name, source, status, created_at
            ) VALUES (?, ?, ?, 'INTAKE_FORM', 'PENDING', ?)
        """, (
            referrer_id,
            customer_id,
            referrer_name,
            datetime.now().isoformat()
        ))

    def _store_consent(self, customer_id: int, data: Dict):
        """Store customer communication consent preferences"""
        consent_data = {
            'customer_id': customer_id,
            'sms_consent': 1 if data.get('consent_sms') else 0,
            'email_consent': 1 if data.get('consent_email') else 0,
            'consent_date': datetime.now().isoformat(),
            'consent_source': 'INTAKE_FORM',
            'ip_address': data.get('ip_address'),
            'user_agent': data.get('user_agent')
        }

        # Check if consent record exists
        existing = self.db.execute("""
            SELECT id FROM customer_consent WHERE customer_id = ?
        """, (customer_id,))

        if existing:
            self.db.execute("""
                UPDATE customer_consent SET
                    sms_consent = ?, email_consent = ?,
                    consent_date = ?, consent_source = ?,
                    updated_at = ?
                WHERE customer_id = ?
            """, (
                consent_data['sms_consent'],
                consent_data['email_consent'],
                consent_data['consent_date'],
                consent_data['consent_source'],
                datetime.now().isoformat(),
                customer_id
            ))
        else:
            # Create consent table if needed
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS customer_consent (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    sms_consent INTEGER DEFAULT 0,
                    email_consent INTEGER DEFAULT 0,
                    consent_date TEXT,
                    consent_source TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT
                )
            """)
            self.db.insert('customer_consent', consent_data)

    def _store_signature(self, customer_id: int, signature_data: str):
        """Store digital signature"""
        # Create signatures table if needed
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS customer_signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                signature_data TEXT NOT NULL,
                signature_type TEXT DEFAULT 'INTAKE_CONSENT',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.db.insert('customer_signatures', {
            'customer_id': customer_id,
            'signature_data': signature_data,
            'signature_type': 'INTAKE_CONSENT',
            'created_at': datetime.now().isoformat()
        })

    def _send_customer_confirmation(self, customer_id: int, data: Dict):
        """Send confirmation notification to customer"""
        try:
            # Try to use notification manager if available
            from src.crm.managers.job_notification_manager import JobNotificationManager
            notifier = JobNotificationManager(self.db_path)

            customer = self.db.get_by_id('customers', customer_id)
            if not customer:
                return

            # Send SMS if consented
            if data.get('consent_sms') and customer.get('phone'):
                notifier._send_sms(
                    customer['phone'],
                    f"Thanks for visiting PDR Pro! We've received your info and someone will be with you shortly. Questions? Reply to this text."
                )

            # Send email if consented
            if data.get('consent_email') and customer.get('email'):
                notifier._send_email(
                    customer['email'],
                    "Welcome to PDR Pro!",
                    f"Hi {customer.get('first_name', '')},\n\nThank you for visiting us! We've received your information and a team member will be with you shortly.\n\nPDR Pro Team"
                )

        except Exception as e:
            # Log but don't fail
            print(f"Warning: Could not send confirmation: {e}")

    def _notify_office(self, customer_id: int, vehicle_id: int, data: Dict):
        """Notify office staff of new walk-in"""
        try:
            customer = self.db.get_by_id('customers', customer_id)
            customer_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()

            vehicle_desc = "No vehicle info"
            if vehicle_id:
                vehicle = self.db.get_by_id('vehicles', vehicle_id)
                if vehicle:
                    vehicle_desc = f"{vehicle.get('year', '')} {vehicle.get('make', '')} {vehicle.get('model', '')}".strip()

            # Create in-app notification for office
            self.db.execute("""
                INSERT INTO office_notifications (
                    notification_type, title, message,
                    priority, status, created_at
                ) VALUES ('WALK_IN', ?, ?, 'HIGH', 'UNREAD', ?)
            """, (
                f"New Walk-in: {customer_name}",
                f"Vehicle: {vehicle_desc}\nSource: {data.get('source', 'walk_in').replace('_', ' ').title()}",
                datetime.now().isoformat()
            ))

        except Exception as e:
            # Create table if it doesn't exist
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS office_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notification_type TEXT,
                    title TEXT,
                    message TEXT,
                    priority TEXT DEFAULT 'NORMAL',
                    status TEXT DEFAULT 'UNREAD',
                    read_by TEXT,
                    read_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Retry
            try:
                self._notify_office(customer_id, vehicle_id, data)
            except:
                pass

    # =========================================================================
    # DATA HELPERS
    # =========================================================================

    def get_insurance_companies(self) -> List[Dict]:
        """Get list of insurance companies for dropdown"""
        companies = self.db.execute("""
            SELECT id, name FROM insurance_companies
            ORDER BY name
        """)
        return companies

    def get_salespeople(self) -> List[Dict]:
        """Get list of salespeople for door knocker dropdown"""
        users = self.db.execute("""
            SELECT id, first_name || ' ' || last_name as name
            FROM users
            WHERE role IN ('sales', 'manager', 'admin')
              AND is_active = 1
            ORDER BY last_name, first_name
        """)
        return users

    def get_vehicle_makes(self) -> List[str]:
        """Get common vehicle makes for dropdown"""
        return [
            'Acura', 'Audi', 'BMW', 'Buick', 'Cadillac', 'Chevrolet',
            'Chrysler', 'Dodge', 'Ford', 'GMC', 'Honda', 'Hyundai',
            'Infiniti', 'Jeep', 'Kia', 'Lexus', 'Lincoln', 'Mazda',
            'Mercedes-Benz', 'Mitsubishi', 'Nissan', 'Porsche', 'Ram',
            'Subaru', 'Tesla', 'Toyota', 'Volkswagen', 'Volvo', 'Other'
        ]

    def get_vehicle_years(self) -> List[int]:
        """Get vehicle years for dropdown (current year + 1 back to 1990)"""
        current_year = datetime.now().year
        return list(range(current_year + 1, 1989, -1))

    def get_us_states(self) -> List[tuple]:
        """Get US states for dropdown"""
        return self.US_STATES

    def get_lead_sources(self) -> List[Dict]:
        """Get lead sources for dropdown"""
        return [
            {'value': 'door_knocker', 'label': 'Door Knocker / Salesman'},
            {'value': 'referral', 'label': 'Referral from Friend/Family'},
            {'value': 'google', 'label': 'Google Search'},
            {'value': 'facebook', 'label': 'Facebook/Social Media'},
            {'value': 'drove_by', 'label': 'Drove By / Saw Your Sign'},
            {'value': 'insurance_referred', 'label': 'Insurance Company Referred'},
            {'value': 'other', 'label': 'Other'}
        ]

    # =========================================================================
    # RATE LIMITING
    # =========================================================================

    def check_rate_limit(self, ip_address: str, limit: int = 10, window_minutes: int = 60) -> bool:
        """
        Check if IP is rate limited.

        Returns True if allowed, False if rate limited.
        """
        # Create rate limit table if needed
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS intake_rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Clean old entries
        self.db.execute("""
            DELETE FROM intake_rate_limits
            WHERE created_at < datetime('now', '-' || ? || ' minutes')
        """, (window_minutes,))

        # Count recent submissions
        result = self.db.execute("""
            SELECT COUNT(*) as count FROM intake_rate_limits
            WHERE ip_address = ?
              AND created_at > datetime('now', '-' || ? || ' minutes')
        """, (ip_address, window_minutes))

        count = result[0]['count'] if result else 0

        if count >= limit:
            return False

        # Record this attempt
        self.db.insert('intake_rate_limits', {
            'ip_address': ip_address,
            'created_at': datetime.now().isoformat()
        })

        return True

    # =========================================================================
    # OFFLINE QUEUE PROCESSING
    # =========================================================================

    def process_queued_submission(self, queue_data: Dict) -> Dict:
        """
        Process a submission that was queued while offline.

        Queue data should include the original form data plus:
        - queued_at: timestamp when queued
        - device_id: identifier for the tablet
        """
        # Add metadata
        form_data = queue_data.get('form_data', queue_data)
        form_data['was_queued'] = True
        form_data['queued_at'] = queue_data.get('queued_at')
        form_data['device_id'] = queue_data.get('device_id')

        return self.process_intake(form_data)

    def get_recent_submissions(self, limit: int = 20) -> List[Dict]:
        """Get recent intake submissions for office view"""
        return self.db.execute("""
            SELECT
                c.id as customer_id,
                c.first_name || ' ' || c.last_name as customer_name,
                c.phone,
                v.year || ' ' || v.make || ' ' || v.model as vehicle,
                l.source,
                l.created_at as submitted_at
            FROM leads l
            JOIN customers c ON c.id = l.customer_id
            LEFT JOIN vehicles v ON v.customer_id = c.id
            WHERE l.source IN ('WALK_IN', 'DOOR_KNOCKER', 'REFERRAL')
              AND l.created_at > datetime('now', '-24 hours')
            ORDER BY l.created_at DESC
            LIMIT ?
        """, (limit,))
