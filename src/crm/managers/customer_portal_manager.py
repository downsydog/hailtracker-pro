"""
PDR CRM Part 27 - Customer Portal Manager
Self-service portal for customers

FEATURES:
- Portal access management
- Self-service appointment booking
- Real-time job tracking
- Online estimate requests
- Photo upload for quotes
- Service history
- Invoice viewing & payment
- Review & feedback system
- Loyalty program integration
"""

import json
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta


class CustomerPortalManager:
    """
    Manage customer portal access and self-service features

    Customer-facing functionality
    """

    # Loyalty tiers
    LOYALTY_TIERS = {
        'BRONZE': {'min_points': 0, 'points_per_dollar': 1.0},
        'SILVER': {'min_points': 1000, 'points_per_dollar': 1.5},
        'GOLD': {'min_points': 2500, 'points_per_dollar': 2.0},
        'PLATINUM': {'min_points': 5000, 'points_per_dollar': 2.5}
    }

    def __init__(self, db):
        """Initialize customer portal manager with database instance"""
        if isinstance(db, str):
            from ..models.database import Database
            self.db = Database(db)
        else:
            self.db = db
        self._ensure_portal_tables()

    def _ensure_portal_tables(self):
        """Ensure portal-related tables exist"""
        # Customer portal access
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS customer_portal_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                access_token TEXT UNIQUE NOT NULL,
                email TEXT,
                phone TEXT,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Portal appointments
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                service_date DATE NOT NULL,
                service_time TEXT NOT NULL,
                service_type TEXT,
                vehicle_info TEXT,
                damage_description TEXT,
                contact_preference TEXT DEFAULT 'EMAIL',
                notes TEXT,
                cancelled_at TIMESTAMP,
                cancellation_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'PENDING',
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Portal estimate requests
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_estimate_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                vehicle_info TEXT,
                damage_description TEXT,
                photo_urls TEXT,
                preferred_contact TEXT DEFAULT 'EMAIL',
                urgency TEXT DEFAULT 'NORMAL',
                estimated_amount REAL,
                responded_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'PENDING',
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Portal estimate photos
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_estimate_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                photo_url TEXT,
                photo_type TEXT,
                description TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (request_id) REFERENCES portal_estimate_requests(id)
            )
        """)

        # Payment links
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS payment_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                payment_token TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                used_at TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            )
        """)

        # Customer reviews
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS customer_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                review_text TEXT,
                would_recommend INTEGER DEFAULT 1,
                review_categories TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'PUBLISHED',
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)

        # Portal messages
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                related_job_id INTEGER,
                sender_type TEXT DEFAULT 'CUSTOMER',
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'UNREAD',
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Loyalty transactions
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS loyalty_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                points_earned INTEGER NOT NULL,
                description TEXT,
                related_invoice_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

    # ========================================================================
    # PORTAL ACCESS
    # ========================================================================

    def create_portal_access(
        self,
        customer_id: int,
        email: str,
        phone: Optional[str] = None
    ) -> Dict:
        """
        Create portal access for customer

        Args:
            customer_id: Customer ID
            email: Customer email
            phone: Customer phone

        Returns:
            Portal access credentials
        """
        # Generate access token
        access_token = secrets.token_urlsafe(32)

        # Check if access already exists
        existing = self.db.execute("""
            SELECT * FROM customer_portal_access
            WHERE customer_id = ?
        """, (customer_id,))

        if existing:
            # Update existing
            self.db.execute("""
                UPDATE customer_portal_access
                SET access_token = ?,
                    email = ?,
                    phone = ?,
                    updated_at = ?
                WHERE customer_id = ?
            """, (
                access_token,
                email,
                phone,
                datetime.now().isoformat(),
                customer_id
            ))
        else:
            # Create new
            self.db.execute("""
                INSERT INTO customer_portal_access (
                    customer_id, access_token, email, phone,
                    created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                customer_id,
                access_token,
                email,
                phone,
                datetime.now().isoformat(),
                'ACTIVE'
            ))

        portal_url = f"https://portal.yourshop.com/{access_token}"

        print(f"[OK] Created portal access for customer {customer_id}")
        print(f"     Email: {email}")
        print(f"     Portal URL: {portal_url}")

        return {
            'customer_id': customer_id,
            'access_token': access_token,
            'portal_url': portal_url,
            'email': email
        }

    def send_portal_invite(
        self,
        customer_id: int,
        email: str
    ) -> bool:
        """
        Send portal invitation email

        Args:
            customer_id: Customer ID
            email: Customer email
        """
        access = self.create_portal_access(customer_id, email)

        # In production, send actual email
        print(f"[OK] Portal invite sent to {email}")
        print(f"     Portal URL: {access['portal_url']}")

        return True

    def validate_portal_token(self, access_token: str) -> Optional[Dict]:
        """Validate portal access token"""
        result = self.db.execute("""
            SELECT * FROM customer_portal_access
            WHERE access_token = ? AND status = 'ACTIVE'
        """, (access_token,))

        if not result:
            return None

        # Update last login
        self.db.execute("""
            UPDATE customer_portal_access
            SET last_login = ?
            WHERE access_token = ?
        """, (datetime.now().isoformat(), access_token))

        return dict(result[0])

    def customer_login(
        self,
        username: str,
        password: str
    ) -> Optional[Dict]:
        """
        Authenticate customer login with username and password

        Args:
            username: Portal username
            password: Portal password

        Returns:
            Customer data if login successful, None otherwise
        """
        # Check portal_credentials table (created by CustomerOnboardingManager)
        try:
            result = self.db.execute("""
                SELECT pc.*, c.*
                FROM portal_credentials pc
                JOIN customers c ON c.id = pc.customer_id
                WHERE pc.username = ? AND pc.status = 'ACTIVE'
            """, (username,))

            if not result:
                return None

            credential = result[0]

            # Verify password (simple comparison for now)
            # In production, this would use bcrypt or similar
            if credential.get('password_hash') != password:
                return None

            # Update last login
            self.db.execute("""
                UPDATE portal_credentials
                SET last_login = ?
                WHERE username = ?
            """, (datetime.now().isoformat(), username))

            # Return customer data
            return {
                'customer_id': credential['customer_id'],
                'first_name': credential['first_name'],
                'last_name': credential['last_name'],
                'email': credential['email'],
                'phone': credential['phone'],
                'username': username,
                'last_login': datetime.now().isoformat()
            }

        except Exception:
            # If portal_credentials table doesn't exist, return None
            return None

    # ========================================================================
    # APPOINTMENT BOOKING
    # ========================================================================

    def get_available_slots(
        self,
        service_date: date,
        service_type: str = 'PDR'
    ) -> List[Dict]:
        """
        Get available appointment slots for date

        Args:
            service_date: Requested date
            service_type: Type of service

        Returns:
            List of available time slots
        """
        slots = []

        # Business hours: 8 AM - 5 PM
        for hour in range(8, 17):
            slot_time = f"{hour:02d}:00"

            # Check existing appointments
            existing = self.db.execute("""
                SELECT COUNT(*) as count FROM portal_appointments
                WHERE service_date = ? AND service_time = ?
                  AND status NOT IN ('CANCELLED')
            """, (service_date.isoformat(), slot_time))

            # Assume max 2 appointments per slot
            available = existing[0]['count'] < 2 if existing else True

            slots.append({
                'time': slot_time,
                'available': available,
                'duration_hours': 2.0,
                'service_type': service_type
            })

        return slots

    def book_appointment(
        self,
        customer_id: int,
        service_date: date,
        service_time: str,
        service_type: str,
        vehicle_info: Dict,
        damage_description: str,
        contact_preference: str = 'EMAIL',
        notes: Optional[str] = None
    ) -> int:
        """
        Book appointment through portal

        Args:
            customer_id: Customer ID
            service_date: Appointment date
            service_time: Appointment time
            service_type: Service type
            vehicle_info: Vehicle information
            damage_description: Description of damage
            contact_preference: EMAIL, PHONE, SMS
            notes: Additional notes

        Returns:
            Appointment ID
        """
        result = self.db.execute("""
            INSERT INTO portal_appointments (
                customer_id, service_date, service_time,
                service_type, vehicle_info, damage_description,
                contact_preference, notes,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            service_date.isoformat(),
            service_time,
            service_type,
            json.dumps(vehicle_info),
            damage_description,
            contact_preference,
            notes,
            datetime.now().isoformat(),
            'PENDING'
        ))

        appointment_id = result[0]['id']

        print(f"[OK] Appointment booked via portal")
        print(f"     Customer ID: {customer_id}")
        print(f"     Date: {service_date.strftime('%B %d, %Y')}")
        print(f"     Time: {service_time}")
        print(f"     Vehicle: {vehicle_info['year']} {vehicle_info['make']} {vehicle_info['model']}")

        return appointment_id

    def get_customer_appointments(
        self,
        customer_id: int,
        upcoming_only: bool = True
    ) -> List[Dict]:
        """Get customer appointments"""
        if upcoming_only:
            results = self.db.execute("""
                SELECT * FROM portal_appointments
                WHERE customer_id = ?
                  AND service_date >= ?
                  AND status != 'CANCELLED'
                ORDER BY service_date, service_time
            """, (customer_id, date.today().isoformat()))
        else:
            results = self.db.execute("""
                SELECT * FROM portal_appointments
                WHERE customer_id = ?
                ORDER BY service_date DESC, service_time
            """, (customer_id,))

        appointments = []
        for row in results:
            appt = dict(row)
            if appt.get('vehicle_info'):
                appt['vehicle_info'] = json.loads(appt['vehicle_info'])
            appointments.append(appt)

        return appointments

    def cancel_appointment(
        self,
        appointment_id: int,
        cancellation_reason: Optional[str] = None
    ) -> bool:
        """Cancel appointment through portal"""
        self.db.execute("""
            UPDATE portal_appointments
            SET status = 'CANCELLED',
                cancelled_at = ?,
                cancellation_reason = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            cancellation_reason,
            datetime.now().isoformat(),
            appointment_id
        ))

        print(f"[OK] Appointment {appointment_id} cancelled")

        return True

    # ========================================================================
    # ONLINE ESTIMATES
    # ========================================================================

    def request_estimate(
        self,
        customer_id: int,
        vehicle_info: Dict,
        damage_description: str,
        photo_urls: Optional[List[str]] = None,
        preferred_contact: str = 'EMAIL',
        urgency: str = 'NORMAL'
    ) -> int:
        """
        Request estimate through portal

        Args:
            customer_id: Customer ID
            vehicle_info: Vehicle information
            damage_description: Damage description
            photo_urls: List of uploaded photo URLs
            preferred_contact: Preferred contact method
            urgency: URGENT, NORMAL, FLEXIBLE

        Returns:
            Estimate request ID
        """
        result = self.db.execute("""
            INSERT INTO portal_estimate_requests (
                customer_id, vehicle_info, damage_description,
                photo_urls, preferred_contact, urgency,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            json.dumps(vehicle_info),
            damage_description,
            json.dumps(photo_urls) if photo_urls else None,
            preferred_contact,
            urgency,
            datetime.now().isoformat(),
            'PENDING'
        ))

        request_id = result[0]['id']

        print(f"[OK] Estimate request submitted")
        print(f"     Customer ID: {customer_id}")
        print(f"     Vehicle: {vehicle_info['year']} {vehicle_info['make']} {vehicle_info['model']}")
        print(f"     Photos: {len(photo_urls) if photo_urls else 0}")
        print(f"     Urgency: {urgency}")

        return request_id

    def upload_estimate_photos(
        self,
        request_id: int,
        photos: List[Dict]
    ) -> int:
        """
        Upload photos for estimate request

        Args:
            request_id: Estimate request ID
            photos: List of photo dictionaries

        Returns:
            Number of photos uploaded
        """
        for photo in photos:
            self.db.execute("""
                INSERT INTO portal_estimate_photos (
                    request_id, photo_url, photo_type,
                    description, uploaded_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                request_id,
                photo.get('url'),
                photo.get('type', 'damage'),
                photo.get('description'),
                datetime.now().isoformat()
            ))

        print(f"[OK] Uploaded {len(photos)} photos for estimate request {request_id}")

        return len(photos)

    def get_estimate_request(self, request_id: int) -> Optional[Dict]:
        """Get estimate request details"""
        result = self.db.execute("""
            SELECT * FROM portal_estimate_requests WHERE id = ?
        """, (request_id,))

        if not result:
            return None

        request = dict(result[0])
        if request.get('vehicle_info'):
            request['vehicle_info'] = json.loads(request['vehicle_info'])
        if request.get('photo_urls'):
            request['photo_urls'] = json.loads(request['photo_urls'])

        # Get photos
        photos = self.db.execute("""
            SELECT * FROM portal_estimate_photos WHERE request_id = ?
        """, (request_id,))

        request['photos'] = [dict(p) for p in photos]

        return request

    # ========================================================================
    # JOB TRACKING
    # ========================================================================

    def get_job_status(
        self,
        customer_id: int,
        job_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Get job status for customer

        Args:
            customer_id: Customer ID
            job_id: Specific job ID (optional)

        Returns:
            List of job statuses
        """
        if job_id:
            jobs = self.db.execute("""
                SELECT * FROM jobs
                WHERE id = ? AND customer_id = ?
            """, (job_id, customer_id))
        else:
            # Get all active jobs
            jobs = self.db.execute("""
                SELECT * FROM jobs
                WHERE customer_id = ?
                  AND status NOT IN ('COMPLETED', 'DELIVERED', 'CANCELLED')
                ORDER BY created_at DESC
            """, (customer_id,))

        job_statuses = []

        for job in jobs:
            job_dict = dict(job)

            # Get vehicle info
            vehicle = None
            if job_dict.get('vehicle_id'):
                vehicle_data = self.db.execute(
                    "SELECT * FROM vehicles WHERE id = ?",
                    (job_dict['vehicle_id'],)
                )
                vehicle = dict(vehicle_data[0]) if vehicle_data else None

            # Calculate progress
            progress_percent = self._calculate_job_progress(job_dict['status'])

            job_status = {
                'job_id': job_dict['id'],
                'status': job_dict['status'],
                'progress_percent': progress_percent,
                'estimated_completion': job_dict.get('estimated_completion_date'),
                'vehicle': vehicle,
                'description': job_dict.get('tech_notes'),
                'created_at': job_dict['created_at']
            }

            job_statuses.append(job_status)

        return job_statuses

    def _calculate_job_progress(self, status: str) -> int:
        """Calculate job progress percentage based on status"""
        progress_map = {
            'PENDING': 0,
            'SCHEDULED': 10,
            'CHECKED_IN': 20,
            'IN_PROGRESS': 50,
            'QUALITY_CHECK': 80,
            'READY_FOR_PICKUP': 95,
            'COMPLETED': 100,
            'DELIVERED': 100
        }

        return progress_map.get(status, 0)

    def get_status_timeline(self, job_id: int) -> List[Dict]:
        """
        Get complete status timeline for a job

        Shows all status changes in chronological order for customer portal

        Args:
            job_id: Job ID to get timeline for

        Returns:
            List of timeline entries with date, status, label, description
        """
        # Query job_status_history for all status changes
        history = self.db.execute("""
            SELECT * FROM job_status_history
            WHERE job_id = ?
            ORDER BY changed_at ASC
        """, (job_id,))

        timeline = []

        if history:
            # Build timeline from history
            for entry in history:
                status = entry['status']
                status_details = self._get_job_status_details(status)

                timeline.append({
                    'date': entry['changed_at'],
                    'status': status,
                    'label': status_details['label'],
                    'description': status_details['description'],
                    'notes': entry.get('notes'),
                    'progress': status_details['progress'],
                    'next_step': status_details['next_step']
                })
        else:
            # No history - get current job status
            job = self.db.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,)
            )

            if job:
                status = job[0]['status']
                status_details = self._get_job_status_details(status)

                timeline.append({
                    'date': job[0].get('created_at'),
                    'status': status,
                    'label': status_details['label'],
                    'description': status_details['description'],
                    'notes': None,
                    'progress': status_details['progress'],
                    'next_step': status_details['next_step']
                })

        return timeline

    def _get_job_status_details(self, status: str) -> Dict:
        """
        Get friendly details for a job status code

        Args:
            status: Status code (PENDING, IN_PROGRESS, etc.)

        Returns:
            Dictionary with label, description, progress, next_step, estimated_completion
        """
        status_map = {
            'PENDING': {
                'label': 'Pending',
                'description': 'Your repair request has been received and is awaiting review.',
                'progress': 5,
                'next_step': 'We will contact your insurance company to begin the claim process.',
                'estimated_completion': '1-2 business days'
            },
            'INSURANCE_CONTACTED': {
                'label': 'Insurance Contacted',
                'description': 'We have contacted your insurance company to file the claim.',
                'progress': 15,
                'next_step': 'Waiting for insurance approval and adjuster assignment.',
                'estimated_completion': '2-5 business days'
            },
            'INSURANCE_APPROVED': {
                'label': 'Insurance Approved',
                'description': 'Great news! Your insurance has approved the repair.',
                'progress': 25,
                'next_step': 'We will schedule your vehicle drop-off appointment.',
                'estimated_completion': '1-2 business days'
            },
            'SCHEDULED': {
                'label': 'Appointment Scheduled',
                'description': 'Your repair appointment has been scheduled.',
                'progress': 30,
                'next_step': 'Please bring your vehicle at the scheduled time.',
                'estimated_completion': 'See appointment date'
            },
            'CHECKED_IN': {
                'label': 'Vehicle Checked In',
                'description': 'Your vehicle has been received at our facility.',
                'progress': 35,
                'next_step': 'Our technicians will begin the repair process.',
                'estimated_completion': '3-5 business days'
            },
            'IN_PROGRESS': {
                'label': 'Repair In Progress',
                'description': 'Our skilled technicians are actively working on your vehicle.',
                'progress': 60,
                'next_step': 'Quality inspection will be performed once repairs are complete.',
                'estimated_completion': '1-3 business days'
            },
            'WAITING_PARTS': {
                'label': 'Waiting for Parts',
                'description': 'We are waiting for special parts needed for your repair.',
                'progress': 50,
                'next_step': 'Repairs will resume once parts arrive.',
                'estimated_completion': '2-7 business days'
            },
            'QUALITY_CHECK': {
                'label': 'Quality Inspection',
                'description': 'Your vehicle is undergoing final quality inspection.',
                'progress': 85,
                'next_step': 'Vehicle will be ready for pickup soon.',
                'estimated_completion': '1 business day'
            },
            'WAITING_PAYMENT': {
                'label': 'Awaiting Payment',
                'description': 'Repairs are complete. Awaiting final payment processing.',
                'progress': 90,
                'next_step': 'Complete payment to schedule pickup.',
                'estimated_completion': 'Upon payment'
            },
            'READY_FOR_PICKUP': {
                'label': 'Ready for Pickup',
                'description': 'Your vehicle is ready! Please schedule a pickup time.',
                'progress': 95,
                'next_step': 'Contact us to arrange pickup.',
                'estimated_completion': 'At your convenience'
            },
            'COMPLETED': {
                'label': 'Completed',
                'description': 'Your repair has been completed successfully.',
                'progress': 100,
                'next_step': 'Thank you for choosing us!',
                'estimated_completion': 'Complete'
            },
            'DELIVERED': {
                'label': 'Delivered',
                'description': 'Your vehicle has been delivered. Enjoy your like-new vehicle!',
                'progress': 100,
                'next_step': 'Please leave us a review!',
                'estimated_completion': 'Complete'
            },
            'CANCELLED': {
                'label': 'Cancelled',
                'description': 'This repair request has been cancelled.',
                'progress': 0,
                'next_step': 'Contact us if you have questions.',
                'estimated_completion': 'N/A'
            }
        }

        # Return default if status not found
        return status_map.get(status, {
            'label': status.replace('_', ' ').title(),
            'description': f'Current status: {status}',
            'progress': 50,
            'next_step': 'Contact us for more information.',
            'estimated_completion': 'Contact for estimate'
        })

    # ========================================================================
    # SERVICE HISTORY
    # ========================================================================

    def get_service_history(
        self,
        customer_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get customer service history

        Args:
            customer_id: Customer ID
            limit: Maximum number of records

        Returns:
            List of past services
        """
        jobs = self.db.execute("""
            SELECT * FROM jobs
            WHERE customer_id = ?
              AND status IN ('COMPLETED', 'DELIVERED')
            ORDER BY completed_at DESC
            LIMIT ?
        """, (customer_id, limit))

        history = []

        for job in jobs:
            job_dict = dict(job)

            # Get vehicle
            vehicle = None
            if job_dict.get('vehicle_id'):
                vehicle_data = self.db.execute(
                    "SELECT * FROM vehicles WHERE id = ?",
                    (job_dict['vehicle_id'],)
                )
                vehicle = dict(vehicle_data[0]) if vehicle_data else None

            # Get invoice
            invoice = self.db.execute(
                "SELECT * FROM invoices WHERE job_id = ?",
                (job_dict['id'],)
            )

            history_item = {
                'job_id': job_dict['id'],
                'service_date': job_dict.get('completed_at'),
                'vehicle': vehicle,
                'description': job_dict.get('tech_notes'),
                'total_cost': invoice[0]['total'] if invoice else None,
                'invoice_id': invoice[0]['id'] if invoice else None
            }

            history.append(history_item)

        return history

    # ========================================================================
    # INVOICE & PAYMENT
    # ========================================================================

    def get_customer_invoices(
        self,
        customer_id: int,
        unpaid_only: bool = False
    ) -> List[Dict]:
        """
        Get customer invoices

        Args:
            customer_id: Customer ID
            unpaid_only: Only return unpaid invoices

        Returns:
            List of invoices
        """
        query = """
            SELECT i.* FROM invoices i
            JOIN jobs j ON j.id = i.job_id
            WHERE j.customer_id = ?
        """

        if unpaid_only:
            query += " AND i.balance_due > 0"

        query += " ORDER BY i.invoice_date DESC"

        invoices = self.db.execute(query, (customer_id,))

        return [dict(inv) for inv in invoices]

    def create_payment_link(
        self,
        invoice_id: int,
        amount: float
    ) -> Dict:
        """
        Create payment link for invoice

        Args:
            invoice_id: Invoice ID
            amount: Amount to pay

        Returns:
            Payment link details
        """
        # Generate payment token
        payment_token = secrets.token_urlsafe(32)

        self.db.execute("""
            INSERT INTO payment_links (
                invoice_id, payment_token, amount,
                created_at, expires_at, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            invoice_id,
            payment_token,
            amount,
            datetime.now().isoformat(),
            (datetime.now() + timedelta(hours=24)).isoformat(),
            'ACTIVE'
        ))

        payment_url = f"https://pay.yourshop.com/{payment_token}"

        print(f"[OK] Payment link created")
        print(f"     Invoice: {invoice_id}")
        print(f"     Amount: ${amount:,.2f}")
        print(f"     URL: {payment_url}")

        return {
            'invoice_id': invoice_id,
            'payment_token': payment_token,
            'payment_url': payment_url,
            'amount': amount,
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
        }

    # ========================================================================
    # REVIEWS & FEEDBACK
    # ========================================================================

    def submit_review(
        self,
        customer_id: int,
        job_id: int,
        rating: int,
        review_text: Optional[str] = None,
        would_recommend: bool = True,
        review_categories: Optional[Dict] = None
    ) -> int:
        """
        Submit customer review

        Args:
            customer_id: Customer ID
            job_id: Job ID being reviewed
            rating: Overall rating (1-5)
            review_text: Review text
            would_recommend: Would recommend to others
            review_categories: Category ratings (quality, service, value, etc.)

        Returns:
            Review ID
        """
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        result = self.db.execute("""
            INSERT INTO customer_reviews (
                customer_id, job_id, rating, review_text,
                would_recommend, review_categories,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            job_id,
            rating,
            review_text,
            1 if would_recommend else 0,
            json.dumps(review_categories) if review_categories else None,
            datetime.now().isoformat(),
            'PUBLISHED'
        ))

        review_id = result[0]['id']

        stars = '*' * rating
        print(f"[OK] Review submitted")
        print(f"     Job ID: {job_id}")
        print(f"     Rating: {rating}/5 {stars}")
        print(f"     Would recommend: {would_recommend}")

        return review_id

    def get_customer_reviews(self, customer_id: int) -> List[Dict]:
        """Get all reviews by customer"""
        results = self.db.execute("""
            SELECT * FROM customer_reviews
            WHERE customer_id = ?
            ORDER BY created_at DESC
        """, (customer_id,))

        reviews = []
        for row in results:
            review = dict(row)
            if review.get('review_categories'):
                review['review_categories'] = json.loads(review['review_categories'])
            reviews.append(review)

        return reviews

    def get_review_request(self, job_id: int) -> Optional[Dict]:
        """
        Get review request for completed job

        Returns review request if job is eligible
        """
        job = self.db.execute(
            "SELECT * FROM jobs WHERE id = ?",
            (job_id,)
        )

        if not job:
            return None

        job = dict(job[0])

        if job['status'] not in ('COMPLETED', 'DELIVERED'):
            return None

        # Check if already reviewed
        existing_review = self.db.execute(
            "SELECT * FROM customer_reviews WHERE job_id = ?",
            (job_id,)
        )

        if existing_review:
            return None

        # Get customer
        customer = self.db.execute(
            "SELECT * FROM customers WHERE id = ?",
            (job['customer_id'],)
        )

        if not customer:
            return None

        customer = dict(customer[0])

        return {
            'job_id': job_id,
            'customer_name': f"{customer['first_name']} {customer['last_name']}",
            'completed_at': job.get('completed_at'),
            'eligible_for_review': True
        }

    # ========================================================================
    # COMMUNICATION CENTER
    # ========================================================================

    def send_message(
        self,
        customer_id: int,
        subject: str,
        message: str,
        related_job_id: Optional[int] = None
    ) -> int:
        """
        Send message through portal

        Args:
            customer_id: Customer ID
            subject: Message subject
            message: Message content
            related_job_id: Related job ID (optional)

        Returns:
            Message ID
        """
        result = self.db.execute("""
            INSERT INTO portal_messages (
                customer_id, subject, message,
                related_job_id, sender_type,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            subject,
            message,
            related_job_id,
            'CUSTOMER',
            datetime.now().isoformat(),
            'UNREAD'
        ))

        message_id = result[0]['id']

        print(f"[OK] Message sent from customer {customer_id}")
        print(f"     Subject: {subject}")

        return message_id

    def get_messages(
        self,
        customer_id: int,
        unread_only: bool = False
    ) -> List[Dict]:
        """Get customer messages"""
        query = """
            SELECT * FROM portal_messages
            WHERE customer_id = ?
        """

        if unread_only:
            query += " AND status = 'UNREAD'"

        query += " ORDER BY created_at DESC"

        messages = self.db.execute(query, (customer_id,))

        return [dict(m) for m in messages]

    def mark_message_read(self, message_id: int) -> bool:
        """Mark message as read"""
        self.db.execute("""
            UPDATE portal_messages
            SET status = 'READ',
                read_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), message_id))

        return True

    # ========================================================================
    # LOYALTY PROGRAM
    # ========================================================================

    def get_loyalty_points(self, customer_id: int) -> Dict:
        """
        Get customer loyalty points balance

        Returns points summary
        """
        # Get total points earned
        earned = self.db.execute("""
            SELECT COALESCE(SUM(points_earned), 0) as total
            FROM loyalty_transactions
            WHERE customer_id = ?
              AND transaction_type = 'EARNED'
        """, (customer_id,))

        total_earned = earned[0]['total'] if earned else 0

        # Get points redeemed
        redeemed = self.db.execute("""
            SELECT COALESCE(SUM(ABS(points_earned)), 0) as total
            FROM loyalty_transactions
            WHERE customer_id = ?
              AND transaction_type = 'REDEEMED'
        """, (customer_id,))

        total_redeemed = redeemed[0]['total'] if redeemed else 0

        # Calculate balance
        balance = total_earned - total_redeemed

        # Get tier
        tier = self._calculate_loyalty_tier(total_earned)

        return {
            'customer_id': customer_id,
            'points_balance': balance,
            'total_earned': total_earned,
            'total_redeemed': total_redeemed,
            'tier': tier,
            'tier_benefits': self._get_tier_benefits(tier)
        }

    def _calculate_loyalty_tier(self, total_points: int) -> str:
        """Calculate loyalty tier based on points"""
        if total_points >= 5000:
            return 'PLATINUM'
        elif total_points >= 2500:
            return 'GOLD'
        elif total_points >= 1000:
            return 'SILVER'
        else:
            return 'BRONZE'

    def _get_tier_benefits(self, tier: str) -> List[str]:
        """Get benefits for loyalty tier"""
        benefits = {
            'BRONZE': [
                '1 point per $1 spent',
                'Birthday discount'
            ],
            'SILVER': [
                '1.5 points per $1 spent',
                'Birthday discount',
                '5% off all services'
            ],
            'GOLD': [
                '2 points per $1 spent',
                'Birthday discount',
                '10% off all services',
                'Priority scheduling'
            ],
            'PLATINUM': [
                '2.5 points per $1 spent',
                'Birthday discount',
                '15% off all services',
                'Priority scheduling',
                'Free annual detail'
            ]
        }

        return benefits.get(tier, benefits['BRONZE'])

    def add_loyalty_points(
        self,
        customer_id: int,
        points: int,
        description: str,
        transaction_type: str = 'EARNED',
        related_invoice_id: Optional[int] = None
    ) -> int:
        """Add loyalty points for customer"""
        result = self.db.execute("""
            INSERT INTO loyalty_transactions (
                customer_id, transaction_type, points_earned,
                description, related_invoice_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            transaction_type,
            points,
            description,
            related_invoice_id,
            datetime.now().isoformat()
        ))

        return result[0]['id']

    def redeem_loyalty_points(
        self,
        customer_id: int,
        points: int,
        description: str
    ) -> bool:
        """Redeem loyalty points"""
        # Check balance
        loyalty = self.get_loyalty_points(customer_id)

        if loyalty['points_balance'] < points:
            raise ValueError("Insufficient points balance")

        self.add_loyalty_points(
            customer_id=customer_id,
            points=-points,
            description=description,
            transaction_type='REDEEMED'
        )

        print(f"[OK] Redeemed {points} points for customer {customer_id}")

        return True

    # ========================================================================
    # PORTAL DASHBOARD
    # ========================================================================

    def get_portal_dashboard(self, customer_id: int) -> Dict:
        """
        Get complete portal dashboard data

        Returns all portal data for customer
        """
        # Get customer info
        customer = self.db.execute(
            "SELECT * FROM customers WHERE id = ?",
            (customer_id,)
        )

        customer_info = dict(customer[0]) if customer else {}

        # Get active jobs
        active_jobs = self.get_job_status(customer_id)

        # Get upcoming appointments
        appointments = self.get_customer_appointments(customer_id, upcoming_only=True)

        # Get unpaid invoices
        unpaid_invoices = self.get_customer_invoices(customer_id, unpaid_only=True)

        # Get loyalty points
        loyalty = self.get_loyalty_points(customer_id)

        # Get unread messages
        unread_messages = self.get_messages(customer_id, unread_only=True)

        # Get referral summary
        referral_summary = self.get_referral_summary(customer_id)

        return {
            'customer': customer_info,
            'active_jobs': active_jobs,
            'upcoming_appointments': appointments,
            'unpaid_invoices': unpaid_invoices,
            'loyalty': loyalty,
            'unread_messages': len(unread_messages),
            'referrals': referral_summary
        }

    # ========================================================================
    # REFERRAL TRACKING & COMMISSIONS
    # ========================================================================

    def get_referral_dashboard(
        self,
        customer_id: int
    ) -> Dict:
        """
        Get customer's referral dashboard

        Shows referrals, commissions, and earnings
        """
        # Ensure referral tables exist
        self._ensure_referral_tables()

        # Get all referrals made by this customer
        referrals = self.db.execute("""
            SELECT
                cr.*,
                c.first_name, c.last_name, c.phone
            FROM customer_referrals cr
            JOIN customers c ON c.id = cr.referred_customer_id
            WHERE cr.referrer_customer_id = ?
            ORDER BY cr.created_at DESC
        """, (customer_id,))

        # Calculate statistics
        total_referrals = len(referrals)
        pending_referrals = sum(1 for r in referrals if r['status'] == 'PENDING')
        scheduled_referrals = sum(1 for r in referrals if r['status'] == 'SCHEDULED')
        completed_referrals = sum(1 for r in referrals if r['status'] == 'COMPLETED')

        # Commission structure: $50 per completed referral
        commission_per_referral = 50.00
        total_earned = completed_referrals * commission_per_referral
        pending_earnings = (scheduled_referrals + pending_referrals) * commission_per_referral

        # Get payment history
        payments = self.db.execute("""
            SELECT * FROM referral_commission_payments
            WHERE customer_id = ?
            ORDER BY paid_at DESC
        """, (customer_id,))

        total_paid = sum(p['amount'] for p in payments) if payments else 0
        balance_due = total_earned - total_paid

        # Get referral link clicks
        clicks = self.db.execute("""
            SELECT COUNT(*) as count FROM referral_link_clicks
            WHERE referrer_customer_id = ?
        """, (customer_id,))

        referral_link = f"https://portal.pdrcrm.com/refer/{customer_id}"

        return {
            'referral_link': referral_link,
            'summary': {
                'total_referrals': total_referrals,
                'pending': pending_referrals,
                'scheduled': scheduled_referrals,
                'completed': completed_referrals,
                'link_clicks': clicks[0]['count'] if clicks else 0
            },
            'earnings': {
                'total_earned': total_earned,
                'total_paid': total_paid,
                'balance_due': balance_due,
                'pending_earnings': pending_earnings,
                'commission_rate': commission_per_referral
            },
            'referrals': self._format_referrals(referrals),
            'payments': list(payments) if payments else []
        }

    def get_referral_summary(self, customer_id: int) -> Dict:
        """Get quick referral summary for dashboard"""
        try:
            dashboard = self.get_referral_dashboard(customer_id)
            return {
                'total': dashboard['summary']['total_referrals'],
                'completed': dashboard['summary']['completed'],
                'earnings': dashboard['earnings']['total_earned'],
                'balance': dashboard['earnings']['balance_due']
            }
        except Exception:
            return {'total': 0, 'completed': 0, 'earnings': 0, 'balance': 0}

    def _format_referrals(self, referrals: list) -> List[Dict]:
        """Format referral data for display"""
        formatted = []
        for ref in referrals:
            formatted.append({
                'id': ref['id'],
                'name': f"{ref['first_name']} {ref['last_name']}",
                'phone': ref.get('phone'),
                'referred_date': ref['created_at'],
                'status': ref['status'],
                'commission_amount': ref.get('commission_amount', 50.00),
                'commission_status': 'PAID' if ref['status'] == 'COMPLETED' and ref.get('commission_earned_at') else 'PENDING'
            })
        return formatted

    def _ensure_referral_tables(self):
        """Ensure referral-related tables exist"""
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

        # Referral commission payments table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS referral_commission_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                referral_id INTEGER,
                amount REAL,
                payment_method TEXT,
                paid_at TEXT,
                notes TEXT
            )
        """)

        # Referral link clicks table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS referral_link_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_customer_id INTEGER,
                click_source TEXT,
                clicked_at TEXT,
                ip_address TEXT,
                user_agent TEXT
            )
        """)

    def track_referral_click(
        self,
        referrer_customer_id: int,
        click_source: str = 'LINK',
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Track when someone clicks referral link"""
        self._ensure_referral_tables()

        self.db.execute("""
            INSERT INTO referral_link_clicks (
                referrer_customer_id, click_source, clicked_at,
                ip_address, user_agent
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            referrer_customer_id,
            click_source,
            datetime.now().isoformat(),
            ip_address,
            user_agent
        ))

    def create_referral(
        self,
        referrer_customer_id: int,
        referred_customer_id: int,
        enrollment_id: Optional[str] = None
    ) -> int:
        """Create a new referral record"""
        self._ensure_referral_tables()

        result = self.db.execute("""
            INSERT INTO customer_referrals (
                referrer_customer_id, referred_customer_id,
                enrollment_id, created_at, status
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            referrer_customer_id,
            referred_customer_id,
            enrollment_id,
            datetime.now().isoformat(),
            'PENDING'
        ))

        referral_id = result[0]['id']

        print(f"[OK] Referral created: Customer {referrer_customer_id} referred {referred_customer_id}")

        return referral_id

    def update_referral_status(
        self,
        referral_id: int,
        new_status: str,
        notes: Optional[str] = None
    ):
        """Update referral status when job progresses"""
        self.db.execute("""
            UPDATE customer_referrals
            SET status = ?,
                status_notes = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            new_status,
            notes,
            datetime.now().isoformat(),
            referral_id
        ))

        # If completed, calculate commission
        if new_status == 'COMPLETED':
            self._process_referral_commission(referral_id)

    def _process_referral_commission(self, referral_id: int):
        """Process commission payment for completed referral"""
        referral = self.db.execute(
            "SELECT * FROM customer_referrals WHERE id = ?",
            (referral_id,)
        )

        if not referral:
            return

        referral = referral[0]
        commission_amount = 50.00

        # Record commission earned
        self.db.execute("""
            UPDATE customer_referrals
            SET commission_amount = ?,
                commission_earned_at = ?
            WHERE id = ?
        """, (
            commission_amount,
            datetime.now().isoformat(),
            referral_id
        ))

        print(f"[OK] Commission of ${commission_amount:.2f} earned for referral {referral_id}")

    def pay_referral_commission(
        self,
        customer_id: int,
        amount: float,
        payment_method: str = 'CHECK',
        referral_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> int:
        """Record commission payment to customer"""
        self._ensure_referral_tables()

        result = self.db.execute("""
            INSERT INTO referral_commission_payments (
                customer_id, referral_id, amount, payment_method,
                paid_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            referral_id,
            amount,
            payment_method,
            datetime.now().isoformat(),
            notes
        ))

        payment_id = result[0]['id']

        print(f"[OK] Commission payment of ${amount:.2f} recorded for customer {customer_id}")

        return payment_id
