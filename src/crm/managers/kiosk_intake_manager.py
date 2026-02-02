"""
Kiosk Intake Manager
Handles walk-in customer intake processing for tablet kiosk devices.

Features:
- Device token authentication
- Customer/vehicle/lead creation
- Office notifications
- Rate limiting
- Auto-reset after submission
"""

import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Any
import json
import re


class KioskIntakeManager:
    """
    Manages kiosk device operations and walk-in customer intake.

    Flow:
    1. Kiosk authenticates with device_token
    2. Customer fills intake form on tablet
    3. System creates customer + vehicle + lead
    4. Office gets notified
    5. Form resets for next walk-in
    """

    # Lead sources for kiosk intake
    LEAD_SOURCES = [
        {'value': 'WALK_IN', 'label': 'Walk-In'},
        {'value': 'REFERRAL', 'label': 'Referral'},
        {'value': 'WEBSITE', 'label': 'Website'},
        {'value': 'SOCIAL_MEDIA', 'label': 'Social Media'},
        {'value': 'GOOGLE', 'label': 'Google Search'},
        {'value': 'RADIO', 'label': 'Radio'},
        {'value': 'TV', 'label': 'Television'},
        {'value': 'NEWSPAPER', 'label': 'Newspaper'},
        {'value': 'DOOR_KNOCKER', 'label': 'Door Knocker'},
        {'value': 'HAIL_EVENT', 'label': 'Hail Storm'},
        {'value': 'OTHER', 'label': 'Other'},
    ]

    # Common vehicle makes
    VEHICLE_MAKES = [
        'Acura', 'Audi', 'BMW', 'Buick', 'Cadillac', 'Chevrolet', 'Chrysler',
        'Dodge', 'Ford', 'GMC', 'Honda', 'Hyundai', 'Infiniti', 'Jaguar',
        'Jeep', 'Kia', 'Land Rover', 'Lexus', 'Lincoln', 'Mazda',
        'Mercedes-Benz', 'Mini', 'Mitsubishi', 'Nissan', 'Porsche', 'Ram',
        'Subaru', 'Tesla', 'Toyota', 'Volkswagen', 'Volvo'
    ]

    # US States
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
        ('WI', 'Wisconsin'), ('WY', 'Wyoming')
    ]

    def __init__(self, db_path: str = "data/hailtracker_crm.db"):
        """Initialize with database path"""
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ========================================================================
    # DEVICE AUTHENTICATION
    # ========================================================================

    def validate_device(self, device_token: str) -> Optional[Dict]:
        """
        Validate kiosk device token.

        Returns device info if valid, None if invalid.
        """
        if not device_token:
            return None

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    k.id, k.organization_id, k.device_token, k.name,
                    k.auto_reset_seconds, k.welcome_message, k.is_active,
                    k.last_seen_at, k.last_ip,
                    o.account_id, o.name as organization_name,
                    a.name as account_name
                FROM kiosk_devices k
                JOIN organizations o ON k.organization_id = o.id
                JOIN accounts a ON o.account_id = a.id
                WHERE k.device_token = ? AND k.is_active = 1
            """, (device_token,))

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

        finally:
            conn.close()

    def update_device_activity(self, device_token: str, ip_address: str = None,
                               user_agent: str = None) -> bool:
        """Update kiosk last_seen_at and connection info"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE kiosk_devices
                SET last_seen_at = ?,
                    last_ip = COALESCE(?, last_ip),
                    user_agent = COALESCE(?, user_agent)
                WHERE device_token = ?
            """, (datetime.now().isoformat(), ip_address, user_agent, device_token))

            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()

    def get_kiosk_settings(self, organization_id: int) -> Dict:
        """Get organization settings relevant to kiosk"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT name, settings, logo_path
                FROM organizations
                WHERE id = ?
            """, (organization_id,))

            row = cursor.fetchone()
            if row:
                settings = json.loads(row['settings'] or '{}')
                return {
                    'organization_name': row['name'],
                    'logo_path': row['logo_path'],
                    'settings': settings
                }
            return {}

        finally:
            conn.close()

    # ========================================================================
    # FORM DATA
    # ========================================================================

    def get_lead_sources(self) -> List[Dict]:
        """Get lead sources for dropdown"""
        return self.LEAD_SOURCES

    def get_vehicle_makes(self) -> List[str]:
        """Get vehicle makes for dropdown"""
        return self.VEHICLE_MAKES

    def get_vehicle_years(self) -> List[int]:
        """Get vehicle years for dropdown (current year + 1 back to 1980)"""
        current_year = datetime.now().year
        return list(range(current_year + 1, 1979, -1))

    def get_us_states(self) -> List[tuple]:
        """Get US states for dropdown"""
        return self.US_STATES

    def get_insurance_companies(self, organization_id: int = None) -> List[Dict]:
        """Get insurance companies for dropdown"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, name, is_preferred
                FROM insurance_companies
                WHERE is_active = 1
                ORDER BY is_preferred DESC, name ASC
            """)

            rows = cursor.fetchall()
            return [dict(r) for r in rows]

        except sqlite3.OperationalError:
            # Table might not exist, return common insurers
            return [
                {'id': 0, 'name': 'State Farm', 'is_preferred': True},
                {'id': 0, 'name': 'Allstate', 'is_preferred': True},
                {'id': 0, 'name': 'Progressive', 'is_preferred': True},
                {'id': 0, 'name': 'GEICO', 'is_preferred': True},
                {'id': 0, 'name': 'USAA', 'is_preferred': True},
                {'id': 0, 'name': 'Farmers', 'is_preferred': False},
                {'id': 0, 'name': 'Liberty Mutual', 'is_preferred': False},
                {'id': 0, 'name': 'Nationwide', 'is_preferred': False},
                {'id': 0, 'name': 'American Family', 'is_preferred': False},
                {'id': 0, 'name': 'Travelers', 'is_preferred': False},
            ]
        finally:
            conn.close()

    # ========================================================================
    # INTAKE PROCESSING
    # ========================================================================

    def process_intake(self, device_token: str, form_data: Dict) -> Dict:
        """
        Process a kiosk intake submission.

        Creates:
        1. Customer record (or finds existing)
        2. Vehicle record
        3. Lead record (with WALK_IN source)

        Returns dict with success status and created IDs.
        """
        # Validate device
        device = self.validate_device(device_token)
        if not device:
            return {
                'success': False,
                'error': 'Invalid or inactive kiosk device',
                'error_code': 'INVALID_DEVICE'
            }

        organization_id = device['organization_id']
        account_id = device['account_id']

        # Validate required fields
        validation = self._validate_intake_data(form_data)
        if not validation['valid']:
            return {
                'success': False,
                'error': 'Validation failed',
                'errors': validation['errors'],
                'error_code': 'VALIDATION_FAILED'
            }

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Start transaction
            conn.execute('BEGIN')

            # 1. Find or create customer
            customer_id = self._find_or_create_customer(
                cursor, organization_id, form_data
            )

            # 2. Create vehicle
            vehicle_id = self._create_vehicle(
                cursor, organization_id, customer_id, form_data
            )

            # 3. Create lead
            lead_id = self._create_lead(
                cursor, organization_id, customer_id, vehicle_id, form_data, device
            )

            # 4. Log the intake
            self._log_intake(cursor, organization_id, device['id'],
                           customer_id, vehicle_id, lead_id, form_data)

            conn.commit()

            # 5. Notify office (non-blocking)
            self._notify_office(organization_id, customer_id, lead_id, form_data)

            # Build customer name for thank you screen
            customer_name = f"{form_data.get('first_name', '')} {form_data.get('last_name', '')}".strip()
            vehicle_desc = f"{form_data.get('vehicle_year', '')} {form_data.get('vehicle_make', '')} {form_data.get('vehicle_model', '')}".strip()

            return {
                'success': True,
                'customer_id': customer_id,
                'vehicle_id': vehicle_id,
                'lead_id': lead_id,
                'customer_name': customer_name,
                'vehicle_description': vehicle_desc,
                'message': 'Thank you for checking in!'
            }

        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e),
                'error_code': 'PROCESSING_ERROR'
            }

        finally:
            conn.close()

    def _validate_intake_data(self, data: Dict) -> Dict:
        """Validate intake form data"""
        errors = []

        # Required: first name
        if not data.get('first_name', '').strip():
            errors.append({'field': 'first_name', 'message': 'First name is required'})

        # Required: last name
        if not data.get('last_name', '').strip():
            errors.append({'field': 'last_name', 'message': 'Last name is required'})

        # Required: phone or email
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()

        if not phone and not email:
            errors.append({'field': 'phone', 'message': 'Phone or email is required'})

        # Validate email format if provided
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            errors.append({'field': 'email', 'message': 'Invalid email format'})

        # Validate phone format if provided
        if phone:
            clean_phone = re.sub(r'\D', '', phone)
            if len(clean_phone) < 10:
                errors.append({'field': 'phone', 'message': 'Phone must be at least 10 digits'})

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def _find_or_create_customer(self, cursor, organization_id: int,
                                  data: Dict) -> int:
        """Find existing customer or create new one"""
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        clean_phone = re.sub(r'\D', '', phone) if phone else ''

        # Try to find existing customer
        existing_id = None

        if email:
            cursor.execute("""
                SELECT id FROM customers
                WHERE organization_id = ? AND email = ? AND deleted_at IS NULL
            """, (organization_id, email))
            row = cursor.fetchone()
            if row:
                existing_id = row['id']

        if not existing_id and clean_phone:
            cursor.execute("""
                SELECT id FROM customers
                WHERE organization_id = ?
                  AND REPLACE(REPLACE(REPLACE(phone, '-', ''), '(', ''), ')', '') = ?
                  AND deleted_at IS NULL
            """, (organization_id, clean_phone))
            row = cursor.fetchone()
            if row:
                existing_id = row['id']

        if existing_id:
            # Update last contact
            cursor.execute("""
                UPDATE customers
                SET last_contact_date = ?, updated_at = ?
                WHERE id = ?
            """, (date.today().isoformat(), datetime.now().isoformat(), existing_id))
            return existing_id

        # Create new customer
        now = datetime.now().isoformat()

        # Build street address (combine line1 and line2 if provided)
        address_line1 = data.get('address_line1', '').strip()
        address_line2 = data.get('address_line2', '').strip()
        street_address = address_line1
        if address_line2:
            street_address = f"{address_line1}, {address_line2}" if address_line1 else address_line2

        cursor.execute("""
            INSERT INTO customers (
                organization_id, first_name, last_name, email, phone,
                street_address, city, state, zip_code,
                source, customer_type, status, customer_since,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            organization_id,
            data.get('first_name', '').strip(),
            data.get('last_name', '').strip(),
            email or None,
            phone or None,
            street_address or None,
            data.get('city', '').strip() or None,
            data.get('state', '').strip() or None,
            data.get('zip_code', '').strip() or None,
            data.get('source', 'WALK_IN'),
            'INDIVIDUAL',
            'ACTIVE',
            date.today().isoformat(),
            now,
            now
        ))

        return cursor.lastrowid

    def _create_vehicle(self, cursor, organization_id: int, customer_id: int,
                        data: Dict) -> Optional[int]:
        """Create vehicle record"""
        year = data.get('vehicle_year', '').strip()
        make = data.get('vehicle_make', '').strip()

        if not year and not make:
            return None

        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO vehicles (
                organization_id, customer_id, year, make, model, color,
                vin, license_plate, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            organization_id,
            customer_id,
            int(year) if year else None,
            make or None,
            data.get('vehicle_model', '').strip() or None,
            data.get('vehicle_color', '').strip() or None,
            data.get('vin', '').strip().upper() or None,
            data.get('license_plate', '').strip().upper() or None,
            now,
            now
        ))

        return cursor.lastrowid

    def _create_lead(self, cursor, organization_id: int, customer_id: int,
                     vehicle_id: Optional[int], data: Dict, device: Dict) -> int:
        """Create lead record"""
        now = datetime.now().isoformat()

        # Calculate lead score
        score = self._calculate_lead_score(data)
        temperature = 'HOT' if score >= 70 else ('WARM' if score >= 40 else 'COLD')

        # Source handling
        source = data.get('source', 'WALK_IN')

        # Build notes including referrer info if provided
        notes_parts = []
        if device:
            notes_parts.append(f"Kiosk check-in via {device['name']}")
        else:
            notes_parts.append("Kiosk check-in")
        if data.get('referrer_name', '').strip():
            notes_parts.append(f"Referred by: {data.get('referrer_name').strip()}")
        notes = ". ".join(notes_parts)

        cursor.execute("""
            INSERT INTO leads (
                organization_id, first_name, last_name,
                email, phone, source,
                vehicle_year, vehicle_make, vehicle_model,
                score, temperature, status,
                converted_to_customer_id, notes, next_follow_up_date,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            organization_id,
            data.get('first_name', '').strip(),
            data.get('last_name', '').strip(),
            data.get('email', '').strip() or None,
            data.get('phone', '').strip() or None,
            source,
            data.get('vehicle_year', '').strip() or None,
            data.get('vehicle_make', '').strip() or None,
            data.get('vehicle_model', '').strip() or None,
            score,
            temperature,
            'NEW',
            customer_id,  # Link to the customer we created/found
            notes,
            (date.today() + timedelta(days=1)).isoformat(),  # Follow up tomorrow
            now,
            now
        ))

        return cursor.lastrowid

    def _calculate_lead_score(self, data: Dict) -> int:
        """Calculate lead score based on provided information"""
        score = 0

        # Walk-in customer = high intent (+30)
        score += 30

        # Has vehicle info (+20)
        if data.get('vehicle_year') or data.get('vehicle_make'):
            score += 20

        # Has email (+10)
        if data.get('email'):
            score += 10

        # Has phone (+10)
        if data.get('phone'):
            score += 10

        # Has address (+10)
        if data.get('address_line1'):
            score += 10

        # Referral source (+10)
        if data.get('source') == 'REFERRAL':
            score += 10

        # Has insurance info (+10)
        if data.get('insurance_company'):
            score += 10

        return min(score, 100)

    def _log_intake(self, cursor, organization_id: int, kiosk_id: int,
                    customer_id: int, vehicle_id: Optional[int], lead_id: int,
                    data: Dict):
        """Log the intake in audit log"""
        cursor.execute("""
            INSERT INTO audit_log_new (
                organization_id, kiosk_id, action, resource_type, resource_id,
                details, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            organization_id,
            kiosk_id,
            'kiosk.intake_submitted',
            'lead',
            lead_id,
            json.dumps({
                'customer_id': customer_id,
                'vehicle_id': vehicle_id,
                'customer_name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
            }),
            datetime.now().isoformat()
        ))

    def _notify_office(self, organization_id: int, customer_id: int,
                       lead_id: int, data: Dict):
        """
        Notify office staff of new walk-in.

        This could be:
        - Email notification
        - Desktop notification via SSE
        - SMS to office phone

        For now, we just log it. Can be extended later.
        """
        # TODO: Implement actual notification
        # Options:
        # 1. Send email via email_manager
        # 2. Push SSE event for real-time dashboard update
        # 3. Send SMS via Twilio
        pass

    # ========================================================================
    # RATE LIMITING
    # ========================================================================

    def check_rate_limit(self, identifier: str, limit: int = 10,
                         window_minutes: int = 60) -> bool:
        """
        Check if submission is within rate limit.

        Args:
            identifier: IP address or device token
            limit: Max submissions per window
            window_minutes: Time window in minutes

        Returns True if within limit, False if exceeded.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Count recent submissions from this identifier
            cursor.execute("""
                SELECT COUNT(*) as cnt
                FROM audit_log_new
                WHERE action = 'kiosk.intake_submitted'
                  AND created_at > datetime('now', ?)
                  AND (ip_address = ? OR details LIKE ?)
            """, (f'-{window_minutes} minutes', identifier, f'%{identifier}%'))

            row = cursor.fetchone()
            count = row['cnt'] if row else 0

            return count < limit

        except sqlite3.OperationalError:
            # Table might not exist, allow submission
            return True

        finally:
            conn.close()

    # ========================================================================
    # RECENT SUBMISSIONS
    # ========================================================================

    def get_recent_submissions(self, organization_id: int, limit: int = 20) -> List[Dict]:
        """Get recent kiosk submissions for office view"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT
                    l.id as lead_id,
                    l.first_name, l.last_name, l.phone, l.email,
                    l.vehicle_year, l.vehicle_make, l.vehicle_model,
                    l.temperature, l.status, l.created_at,
                    l.converted_to_customer_id as customer_id,
                    k.name as kiosk_name
                FROM leads l
                LEFT JOIN audit_log_new a ON a.resource_id = l.id
                    AND a.resource_type = 'lead'
                    AND a.action = 'kiosk.intake_submitted'
                LEFT JOIN kiosk_devices k ON a.kiosk_id = k.id
                WHERE l.organization_id = ?
                  AND l.source = 'WALK_IN'
                  AND l.deleted_at IS NULL
                ORDER BY l.created_at DESC
                LIMIT ?
            """, (organization_id, limit))

            return [dict(r) for r in cursor.fetchall()]

        finally:
            conn.close()
