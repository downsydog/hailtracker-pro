"""
PDR CRM Part 14 - Customer Portal Manager
Self-service portal for customers to view jobs, estimates, payments, and communicate with shop
"""

import hashlib
import secrets
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any


class PortalManager:
    """Manages customer portal access and self-service features"""

    def __init__(self, db):
        """Initialize with database instance"""
        self.db = db
        self._ensure_portal_tables()

    def _ensure_portal_tables(self):
        """Create portal-specific tables if they don't exist"""
        # Portal access tokens
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_used TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Portal messages (customer <-> shop communication)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                sender_type TEXT NOT NULL,  -- 'CUSTOMER' or 'SHOP'
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Customer uploaded photos
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                description TEXT,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Estimate approvals
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estimate_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                status TEXT NOT NULL,  -- 'APPROVED', 'DECLINED', 'PENDING'
                signature_data TEXT,
                ip_address TEXT,
                approved_at TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (estimate_id) REFERENCES estimates(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Portal activity log
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

    # =========================================================================
    # AUTHENTICATION
    # =========================================================================

    def generate_portal_link(self, customer_id: int, expires_days: int = 30) -> Dict[str, Any]:
        """Generate a secure portal access link for customer"""
        # Generate secure token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        now = datetime.now()
        expires_at = now + timedelta(days=expires_days)

        # Deactivate existing tokens
        self.db.execute("""
            UPDATE portal_tokens SET is_active = 0
            WHERE customer_id = ?
        """, (customer_id,))

        # Store hashed token
        self.db.execute("""
            INSERT INTO portal_tokens (
                customer_id, token_hash, created_at, expires_at, is_active
            ) VALUES (?, ?, ?, ?, 1)
        """, (customer_id, token_hash, now.isoformat(), expires_at.isoformat()))

        # Get customer info
        customer = self.db.execute("""
            SELECT first_name, last_name, email FROM customers WHERE id = ?
        """, (customer_id,))

        if customer:
            customer = customer[0]
            return {
                'token': token,
                'customer_id': customer_id,
                'customer_name': f"{customer['first_name']} {customer['last_name']}",
                'email': customer['email'],
                'expires_at': expires_at.isoformat(),
                'portal_url': f"/portal?token={token}"
            }

        return {'error': 'Customer not found'}

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate portal access token and return customer info"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        result = self.db.execute("""
            SELECT pt.*, c.first_name, c.last_name, c.email, c.phone
            FROM portal_tokens pt
            JOIN customers c ON pt.customer_id = c.id
            WHERE pt.token_hash = ? AND pt.is_active = 1
        """, (token_hash,))

        if not result:
            return None

        token_data = result[0]

        # Check expiration
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            self.db.execute("""
                UPDATE portal_tokens SET is_active = 0 WHERE token_hash = ?
            """, (token_hash,))
            return None

        # Update last used
        self.db.execute("""
            UPDATE portal_tokens SET last_used = ? WHERE token_hash = ?
        """, (datetime.now().isoformat(), token_hash))

        return {
            'customer_id': token_data['customer_id'],
            'first_name': token_data['first_name'],
            'last_name': token_data['last_name'],
            'email': token_data['email'],
            'phone': token_data['phone'],
            'token_expires': token_data['expires_at']
        }

    def revoke_token(self, customer_id: int) -> bool:
        """Revoke all portal tokens for a customer"""
        self.db.execute("""
            UPDATE portal_tokens SET is_active = 0 WHERE customer_id = ?
        """, (customer_id,))
        return True

    def log_activity(self, customer_id: int, action: str, details: str = None, ip_address: str = None):
        """Log customer portal activity"""
        self.db.execute("""
            INSERT INTO portal_activity (customer_id, action, details, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (customer_id, action, details, ip_address, datetime.now().isoformat()))

    # =========================================================================
    # JOB STATUS & TRACKING
    # =========================================================================

    def get_customer_jobs(self, customer_id: int, include_completed: bool = True) -> List[Dict[str, Any]]:
        """Get all jobs for a customer with status tracking"""
        query = """
            SELECT j.*, v.year, v.make, v.model, v.color, v.license_plate,
                   t.first_name as tech_first, t.last_name as tech_last
            FROM jobs j
            JOIN vehicles v ON j.vehicle_id = v.id
            LEFT JOIN technicians t ON j.assigned_tech_id = t.id
            WHERE j.customer_id = ?
        """

        if not include_completed:
            query += " AND j.status NOT IN ('COMPLETED', 'CANCELLED')"

        query += " ORDER BY j.created_at DESC"

        jobs = self.db.execute(query, (customer_id,))

        result = []
        for job in jobs:
            # Get status history
            history = self.db.execute("""
                SELECT to_status as status, notes, changed_at as created_at FROM job_status_history
                WHERE job_id = ? ORDER BY changed_at DESC LIMIT 5
            """, (job['id'],))

            # Count messages
            messages = self.db.execute("""
                SELECT COUNT(*) as count FROM portal_messages
                WHERE job_id = ? AND sender_type = 'SHOP' AND is_read = 0
            """, (job['id'],))

            unread_count = messages[0]['count'] if messages else 0

            result.append({
                'id': job['id'],
                'job_number': job['job_number'],
                'status': job['status'],
                'status_display': self._format_status(job['status']),
                'vehicle': f"{job['year']} {job['make']} {job['model']}",
                'vehicle_color': job['color'],
                'license_plate': job['license_plate'],
                'job_type': job['job_type'],
                'damage_type': job['damage_type'],
                'technician': f"{job['tech_first']} {job['tech_last']}" if job['tech_first'] else 'Not Assigned',
                'scheduled_date': job.get('scheduled_date'),
                'estimated_completion': job.get('estimated_completion'),
                'created_at': job['created_at'],
                'status_history': [dict(h) for h in history] if history else [],
                'unread_messages': unread_count,
                'progress_percent': self._calculate_progress(job['status'])
            })

        return result

    def get_job_details(self, job_id: int, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed job information for portal display"""
        job = self.db.execute("""
            SELECT j.*, v.year, v.make, v.model, v.color, v.vin, v.license_plate,
                   t.first_name as tech_first, t.last_name as tech_last,
                   ic.claim_number, ic.insurance_company
            FROM jobs j
            JOIN vehicles v ON j.vehicle_id = v.id
            LEFT JOIN technicians t ON j.assigned_tech_id = t.id
            LEFT JOIN insurance_claims ic ON j.insurance_claim_id = ic.id
            WHERE j.id = ? AND j.customer_id = ?
        """, (job_id, customer_id))

        if not job:
            return None

        job = job[0]

        # Get estimates
        estimates = self.db.execute("""
            SELECT id, estimate_number, total, status, created_at
            FROM estimates WHERE job_id = ?
            ORDER BY created_at DESC
        """, (job_id,))

        # Get invoices
        invoices = self.db.execute("""
            SELECT id, invoice_number, total, balance_due, status, invoice_date
            FROM invoices WHERE job_id = ?
            ORDER BY invoice_date DESC
        """, (job_id,))

        # Get payments
        payments = self.db.execute("""
            SELECT id, amount, payment_method, payment_date, payer_type
            FROM payments WHERE job_id = ? AND status = 'COMPLETED'
            ORDER BY payment_date DESC
        """, (job_id,))

        # Get photos
        photos = self.db.execute("""
            SELECT id, file_name, description, uploaded_at
            FROM portal_photos WHERE job_id = ?
            ORDER BY uploaded_at DESC
        """, (job_id,))

        # Get status history
        history = self.db.execute("""
            SELECT to_status as status, notes, changed_at as created_at FROM job_status_history
            WHERE job_id = ? ORDER BY changed_at DESC
        """, (job_id,))

        return {
            'id': job['id'],
            'job_number': job['job_number'],
            'status': job['status'],
            'status_display': self._format_status(job['status']),
            'progress_percent': self._calculate_progress(job['status']),
            'vehicle': {
                'year': job['year'],
                'make': job['make'],
                'model': job['model'],
                'color': job['color'],
                'vin': job['vin'],
                'license_plate': job['license_plate']
            },
            'technician': f"{job['tech_first']} {job['tech_last']}" if job['tech_first'] else None,
            'insurance': {
                'claim_number': job['claim_number'],
                'company': job['insurance_company']
            } if job.get('claim_number') else None,
            'job_type': job['job_type'],
            'damage_type': job['damage_type'],
            'scheduled_date': job.get('scheduled_date'),
            'estimated_completion': job.get('estimated_completion'),
            'notes': job.get('customer_notes'),
            'created_at': job['created_at'],
            'estimates': [dict(e) for e in estimates] if estimates else [],
            'invoices': [dict(i) for i in invoices] if invoices else [],
            'payments': [dict(p) for p in payments] if payments else [],
            'photos': [dict(ph) for ph in photos] if photos else [],
            'status_history': [dict(h) for h in history] if history else []
        }

    def _format_status(self, status: str) -> str:
        """Convert status code to customer-friendly display"""
        status_map = {
            'PENDING': 'Pending Review',
            'SCHEDULED': 'Scheduled',
            'INSPECTED': 'Inspected',
            'ESTIMATE_SENT': 'Estimate Ready',
            'APPROVED': 'Approved',
            'IN_PROGRESS': 'Work In Progress',
            'QUALITY_CHECK': 'Final Inspection',
            'COMPLETED': 'Completed',
            'DELIVERED': 'Delivered',
            'CANCELLED': 'Cancelled'
        }
        return status_map.get(status, status)

    def _calculate_progress(self, status: str) -> int:
        """Calculate job progress percentage"""
        progress_map = {
            'PENDING': 5,
            'SCHEDULED': 15,
            'INSPECTED': 25,
            'ESTIMATE_SENT': 35,
            'APPROVED': 45,
            'IN_PROGRESS': 65,
            'QUALITY_CHECK': 85,
            'COMPLETED': 100,
            'DELIVERED': 100,
            'CANCELLED': 0
        }
        return progress_map.get(status, 0)

    # =========================================================================
    # ESTIMATES & APPROVALS
    # =========================================================================

    def get_pending_estimates(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get estimates awaiting customer approval"""
        estimates = self.db.execute("""
            SELECT e.*, j.job_number, v.year, v.make, v.model
            FROM estimates e
            JOIN jobs j ON e.job_id = j.id
            JOIN vehicles v ON j.vehicle_id = v.id
            WHERE j.customer_id = ? AND e.status = 'SENT'
            ORDER BY e.created_at DESC
        """, (customer_id,))

        result = []
        for est in estimates:
            result.append({
                'id': est['id'],
                'estimate_number': est['estimate_number'],
                'job_id': est['job_id'],
                'job_number': est['job_number'],
                'vehicle': f"{est['year']} {est['make']} {est['model']}",
                'subtotal': est['subtotal'],
                'tax': est['tax_amount'],
                'total': est['total'],
                'created_at': est.get('created_at') or est.get('created_date'),
                'expires_at': est.get('valid_until'),
                'needs_approval': True
            })

        return result

    def get_estimate_details(self, estimate_id: int, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed estimate for customer review"""
        est = self.db.execute("""
            SELECT e.*, j.job_number, j.damage_type,
                   v.year, v.make, v.model, v.color, v.vin
            FROM estimates e
            JOIN jobs j ON e.job_id = j.id
            JOIN vehicles v ON j.vehicle_id = v.id
            WHERE e.id = ? AND j.customer_id = ?
        """, (estimate_id, customer_id))

        if not est:
            return None

        est = est[0]

        # Get line items from JSON
        items = json.loads(est.get('line_items') or '[]')

        return {
            'id': est['id'],
            'estimate_number': est['estimate_number'],
            'job_number': est['job_number'],
            'status': est['status'],
            'vehicle': {
                'year': est['year'],
                'make': est['make'],
                'model': est['model'],
                'color': est['color'],
                'vin': est['vin']
            },
            'damage_type': est['damage_type'],
            'line_items': items,
            'subtotal': est['subtotal'],
            'tax_amount': est['tax_amount'],
            'total': est['total'],
            'notes': est.get('notes'),
            'terms': est.get('terms'),
            'created_at': est.get('created_at') or est.get('created_date'),
            'valid_until': est.get('valid_until'),
            'can_approve': est['status'] == 'SENT'
        }

    def approve_estimate(self, estimate_id: int, customer_id: int,
                        signature_data: str = None, ip_address: str = None,
                        notes: str = None) -> Dict[str, Any]:
        """Customer approval of estimate"""
        # Verify estimate belongs to customer and is pending
        est = self.db.execute("""
            SELECT e.*, j.id as job_id FROM estimates e
            JOIN jobs j ON e.job_id = j.id
            WHERE e.id = ? AND j.customer_id = ? AND e.status = 'SENT'
        """, (estimate_id, customer_id))

        if not est:
            return {'success': False, 'error': 'Estimate not found or already processed'}

        est = est[0]
        now = datetime.now()

        # Record approval
        self.db.execute("""
            INSERT INTO portal_approvals (
                estimate_id, customer_id, status, signature_data,
                ip_address, approved_at, notes, created_at
            ) VALUES (?, ?, 'APPROVED', ?, ?, ?, ?, ?)
        """, (estimate_id, customer_id, signature_data, ip_address,
              now.isoformat(), notes, now.isoformat()))

        # Update estimate status
        self.db.execute("""
            UPDATE estimates SET status = 'APPROVED'
            WHERE id = ?
        """, (estimate_id,))

        # Update job status
        self.db.execute("""
            UPDATE jobs SET status = 'APPROVED', updated_at = ?
            WHERE id = ?
        """, (now.isoformat(), est['job_id']))

        # Log activity
        self.log_activity(customer_id, 'ESTIMATE_APPROVED',
                         f"Approved estimate #{est['estimate_number']}", ip_address)

        return {
            'success': True,
            'estimate_id': estimate_id,
            'estimate_number': est['estimate_number'],
            'approved_at': now.isoformat()
        }

    def decline_estimate(self, estimate_id: int, customer_id: int,
                        reason: str = None, ip_address: str = None) -> Dict[str, Any]:
        """Customer decline of estimate"""
        est = self.db.execute("""
            SELECT e.*, j.id as job_id FROM estimates e
            JOIN jobs j ON e.job_id = j.id
            WHERE e.id = ? AND j.customer_id = ? AND e.status = 'SENT'
        """, (estimate_id, customer_id))

        if not est:
            return {'success': False, 'error': 'Estimate not found or already processed'}

        est = est[0]
        now = datetime.now()

        # Record decline
        self.db.execute("""
            INSERT INTO portal_approvals (
                estimate_id, customer_id, status, ip_address, notes, created_at
            ) VALUES (?, ?, 'DECLINED', ?, ?, ?)
        """, (estimate_id, customer_id, ip_address, reason, now.isoformat()))

        # Update estimate status
        self.db.execute("""
            UPDATE estimates SET status = 'DECLINED'
            WHERE id = ?
        """, (estimate_id,))

        # Log activity
        self.log_activity(customer_id, 'ESTIMATE_DECLINED',
                         f"Declined estimate #{est['estimate_number']}: {reason}", ip_address)

        return {
            'success': True,
            'estimate_id': estimate_id,
            'declined_at': now.isoformat()
        }

    # =========================================================================
    # PAYMENTS & INVOICES
    # =========================================================================

    def get_outstanding_invoices(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get invoices with balance due"""
        invoices = self.db.execute("""
            SELECT i.*, j.job_number, v.year, v.make, v.model
            FROM invoices i
            JOIN jobs j ON i.job_id = j.id
            JOIN vehicles v ON j.vehicle_id = v.id
            WHERE i.customer_id = ? AND i.balance_due > 0
            ORDER BY i.invoice_date DESC
        """, (customer_id,))

        result = []
        for inv in invoices:
            # Get payments
            payments = self.db.execute("""
                SELECT SUM(amount) as paid FROM payments
                WHERE invoice_id = ? AND status = 'COMPLETED'
            """, (inv['id'],))

            paid = payments[0]['paid'] if payments and payments[0]['paid'] else 0

            result.append({
                'id': inv['id'],
                'invoice_number': inv['invoice_number'],
                'job_number': inv['job_number'],
                'vehicle': f"{inv['year']} {inv['make']} {inv['model']}",
                'total': inv['total'],
                'paid': paid,
                'balance_due': inv['balance_due'],
                'invoice_date': inv['invoice_date'],
                'due_date': inv.get('due_date'),
                'status': inv['status']
            })

        return result

    def get_invoice_details(self, invoice_id: int, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed invoice for customer view"""
        inv = self.db.execute("""
            SELECT i.*, j.job_number, v.year, v.make, v.model, v.vin
            FROM invoices i
            JOIN jobs j ON i.job_id = j.id
            JOIN vehicles v ON j.vehicle_id = v.id
            WHERE i.id = ? AND i.customer_id = ?
        """, (invoice_id, customer_id))

        if not inv:
            return None

        inv = inv[0]

        # Get line items from JSON
        items = json.loads(inv.get('line_items') or '[]')

        # Get payments
        payments = self.db.execute("""
            SELECT amount, payment_method, payment_date, payer_type, payment_reference
            FROM payments WHERE invoice_id = ? AND status = 'COMPLETED'
            ORDER BY payment_date
        """, (invoice_id,))

        return {
            'id': inv['id'],
            'invoice_number': inv['invoice_number'],
            'job_number': inv['job_number'],
            'status': inv['status'],
            'vehicle': {
                'year': inv['year'],
                'make': inv['make'],
                'model': inv['model'],
                'vin': inv['vin']
            },
            'line_items': items,
            'subtotal': inv['subtotal'],
            'tax_amount': inv['tax_amount'],
            'total': inv['total'],
            'balance_due': inv['balance_due'],
            'invoice_date': inv['invoice_date'],
            'due_date': inv.get('due_date'),
            'payments': [dict(p) for p in payments] if payments else [],
            'can_pay': inv['balance_due'] > 0
        }

    def record_portal_payment(self, invoice_id: int, customer_id: int,
                             amount: float, payment_method: str,
                             payment_reference: str = None,
                             ip_address: str = None) -> Dict[str, Any]:
        """Record payment made through portal"""
        # Verify invoice belongs to customer
        inv = self.db.execute("""
            SELECT i.*, j.id as job_id FROM invoices i
            JOIN jobs j ON i.job_id = j.id
            WHERE i.id = ? AND i.customer_id = ?
        """, (invoice_id, customer_id))

        if not inv:
            return {'success': False, 'error': 'Invoice not found'}

        inv = inv[0]

        if amount > inv['balance_due']:
            return {'success': False, 'error': 'Payment exceeds balance due'}

        now = datetime.now()

        # Record payment
        self.db.execute("""
            INSERT INTO payments (
                invoice_id, job_id, amount, total_amount,
                payment_method, payment_date, payer_type,
                payment_reference, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'CUSTOMER', ?, 'COMPLETED', ?)
        """, (invoice_id, inv['job_id'], amount, amount,
              payment_method, date.today().isoformat(), payment_reference,
              now.isoformat()))

        payment_id = self.db.execute("SELECT last_insert_rowid() as id")[0]['id']

        # Update invoice balance
        new_balance = inv['balance_due'] - amount
        new_status = 'PAID' if new_balance <= 0 else inv['status']

        self.db.execute("""
            UPDATE invoices SET balance_due = ?, status = ?
            WHERE id = ?
        """, (new_balance, new_status, invoice_id))

        # Log activity
        self.log_activity(customer_id, 'PAYMENT_MADE',
                         f"Paid ${amount:.2f} on invoice #{inv['invoice_number']}", ip_address)

        return {
            'success': True,
            'payment_id': payment_id,
            'amount': amount,
            'new_balance': new_balance,
            'invoice_paid': new_balance <= 0
        }

    def get_payment_history(self, customer_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get customer payment history"""
        payments = self.db.execute("""
            SELECT p.*, i.invoice_number, j.job_number,
                   v.year, v.make, v.model
            FROM payments p
            JOIN invoices i ON p.invoice_id = i.id
            JOIN jobs j ON p.job_id = j.id
            JOIN vehicles v ON j.vehicle_id = v.id
            WHERE i.customer_id = ? AND p.status = 'COMPLETED'
            ORDER BY p.payment_date DESC
            LIMIT ?
        """, (customer_id, limit))

        return [dict(p) for p in payments] if payments else []

    # =========================================================================
    # MESSAGING
    # =========================================================================

    def send_message(self, job_id: int, customer_id: int, message: str,
                    ip_address: str = None) -> Dict[str, Any]:
        """Customer sends message to shop"""
        # Verify job belongs to customer
        job = self.db.execute("""
            SELECT id, job_number FROM jobs WHERE id = ? AND customer_id = ?
        """, (job_id, customer_id))

        if not job:
            return {'success': False, 'error': 'Job not found'}

        now = datetime.now()

        self.db.execute("""
            INSERT INTO portal_messages (
                job_id, customer_id, sender_type, message, created_at
            ) VALUES (?, ?, 'CUSTOMER', ?, ?)
        """, (job_id, customer_id, message, now.isoformat()))

        message_id = self.db.execute("SELECT last_insert_rowid() as id")[0]['id']

        # Log activity
        self.log_activity(customer_id, 'MESSAGE_SENT',
                         f"Sent message on job #{job[0]['job_number']}", ip_address)

        return {
            'success': True,
            'message_id': message_id,
            'sent_at': now.isoformat()
        }

    def get_messages(self, job_id: int, customer_id: int) -> List[Dict[str, Any]]:
        """Get all messages for a job"""
        # Verify job belongs to customer
        job = self.db.execute("""
            SELECT id FROM jobs WHERE id = ? AND customer_id = ?
        """, (job_id, customer_id))

        if not job:
            return []

        messages = self.db.execute("""
            SELECT * FROM portal_messages
            WHERE job_id = ?
            ORDER BY created_at ASC
        """, (job_id,))

        # Mark shop messages as read
        self.db.execute("""
            UPDATE portal_messages SET is_read = 1
            WHERE job_id = ? AND sender_type = 'SHOP' AND is_read = 0
        """, (job_id,))

        return [dict(m) for m in messages] if messages else []

    def get_unread_count(self, customer_id: int) -> int:
        """Get count of unread messages for customer"""
        result = self.db.execute("""
            SELECT COUNT(*) as count FROM portal_messages pm
            JOIN jobs j ON pm.job_id = j.id
            WHERE j.customer_id = ? AND pm.sender_type = 'SHOP' AND pm.is_read = 0
        """, (customer_id,))

        return result[0]['count'] if result else 0

    def shop_send_message(self, job_id: int, message: str, sender_name: str = None) -> Dict[str, Any]:
        """Shop sends message to customer (internal use)"""
        job = self.db.execute("""
            SELECT id, customer_id, job_number FROM jobs WHERE id = ?
        """, (job_id,))

        if not job:
            return {'success': False, 'error': 'Job not found'}

        job = job[0]
        now = datetime.now()

        full_message = f"[{sender_name}] {message}" if sender_name else message

        self.db.execute("""
            INSERT INTO portal_messages (
                job_id, customer_id, sender_type, message, created_at
            ) VALUES (?, ?, 'SHOP', ?, ?)
        """, (job_id, job['customer_id'], full_message, now.isoformat()))

        message_id = self.db.execute("SELECT last_insert_rowid() as id")[0]['id']

        return {
            'success': True,
            'message_id': message_id,
            'sent_at': now.isoformat()
        }

    # =========================================================================
    # PHOTO UPLOADS
    # =========================================================================

    def upload_photo(self, job_id: int, customer_id: int,
                    file_path: str, file_name: str,
                    description: str = None) -> Dict[str, Any]:
        """Record customer photo upload"""
        # Verify job belongs to customer
        job = self.db.execute("""
            SELECT id, job_number FROM jobs WHERE id = ? AND customer_id = ?
        """, (job_id, customer_id))

        if not job:
            return {'success': False, 'error': 'Job not found'}

        now = datetime.now()

        self.db.execute("""
            INSERT INTO portal_photos (
                job_id, customer_id, file_path, file_name, description, uploaded_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (job_id, customer_id, file_path, file_name, description, now.isoformat()))

        photo_id = self.db.execute("SELECT last_insert_rowid() as id")[0]['id']

        # Log activity
        self.log_activity(customer_id, 'PHOTO_UPLOADED',
                         f"Uploaded {file_name} for job #{job[0]['job_number']}")

        return {
            'success': True,
            'photo_id': photo_id,
            'uploaded_at': now.isoformat()
        }

    def get_job_photos(self, job_id: int, customer_id: int) -> List[Dict[str, Any]]:
        """Get all photos for a job"""
        photos = self.db.execute("""
            SELECT * FROM portal_photos
            WHERE job_id = ? AND customer_id = ?
            ORDER BY uploaded_at DESC
        """, (job_id, customer_id))

        return [dict(p) for p in photos] if photos else []

    # =========================================================================
    # CUSTOMER PROFILE
    # =========================================================================

    def get_profile(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get customer profile for portal"""
        customer = self.db.execute("""
            SELECT * FROM customers WHERE id = ?
        """, (customer_id,))

        if not customer:
            return None

        c = customer[0]

        # Get vehicles
        vehicles = self.db.execute("""
            SELECT id, year, make, model, color, license_plate
            FROM vehicles WHERE customer_id = ?
            ORDER BY year DESC
        """, (customer_id,))

        # Get job count
        job_count = self.db.execute("""
            SELECT COUNT(*) as count FROM jobs WHERE customer_id = ?
        """, (customer_id,))

        # Get total spent
        total_spent = self.db.execute("""
            SELECT SUM(p.amount) as total FROM payments p
            JOIN invoices i ON p.invoice_id = i.id
            WHERE i.customer_id = ? AND p.status = 'COMPLETED'
        """, (customer_id,))

        return {
            'id': c['id'],
            'first_name': c['first_name'],
            'last_name': c['last_name'],
            'email': c['email'],
            'phone': c['phone'],
            'address': {
                'street': c.get('street_address'),
                'city': c.get('city'),
                'state': c.get('state'),
                'zip': c.get('zip_code')
            },
            'vehicles': [dict(v) for v in vehicles] if vehicles else [],
            'total_jobs': job_count[0]['count'] if job_count else 0,
            'total_spent': total_spent[0]['total'] if total_spent and total_spent[0]['total'] else 0,
            'member_since': c.get('created_at')
        }

    def update_profile(self, customer_id: int, updates: Dict[str, Any],
                      ip_address: str = None) -> Dict[str, Any]:
        """Update customer profile from portal"""
        allowed_fields = ['phone', 'email', 'street_address', 'city', 'state', 'zip_code']

        update_data = {k: v for k, v in updates.items() if k in allowed_fields and v}

        if not update_data:
            return {'success': False, 'error': 'No valid fields to update'}

        # Build update query
        set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
        values = list(update_data.values())
        values.append(datetime.now().isoformat())
        values.append(customer_id)

        self.db.execute(f"""
            UPDATE customers SET {set_clause}, updated_at = ? WHERE id = ?
        """, tuple(values))

        # Log activity
        self.log_activity(customer_id, 'PROFILE_UPDATED',
                         f"Updated fields: {', '.join(update_data.keys())}", ip_address)

        return {'success': True, 'updated_fields': list(update_data.keys())}

    # =========================================================================
    # PORTAL DASHBOARD
    # =========================================================================

    def get_dashboard_data(self, customer_id: int) -> Dict[str, Any]:
        """Get all data needed for portal dashboard"""
        # Active jobs
        active_jobs = self.db.execute("""
            SELECT COUNT(*) as count FROM jobs
            WHERE customer_id = ? AND status NOT IN ('COMPLETED', 'CANCELLED', 'DELIVERED')
        """, (customer_id,))

        # Pending estimates
        pending_estimates = self.db.execute("""
            SELECT COUNT(*) as count FROM estimates e
            JOIN jobs j ON e.job_id = j.id
            WHERE j.customer_id = ? AND e.status = 'SENT'
        """, (customer_id,))

        # Outstanding balance
        outstanding = self.db.execute("""
            SELECT SUM(balance_due) as total FROM invoices
            WHERE customer_id = ? AND balance_due > 0
        """, (customer_id,))

        # Unread messages
        unread = self.get_unread_count(customer_id)

        # Recent jobs
        recent_jobs = self.get_customer_jobs(customer_id, include_completed=True)[:5]

        # Pending estimates list
        estimates = self.get_pending_estimates(customer_id)

        # Outstanding invoices
        invoices = self.get_outstanding_invoices(customer_id)

        return {
            'summary': {
                'active_jobs': active_jobs[0]['count'] if active_jobs else 0,
                'pending_estimates': pending_estimates[0]['count'] if pending_estimates else 0,
                'outstanding_balance': outstanding[0]['total'] if outstanding and outstanding[0]['total'] else 0,
                'unread_messages': unread
            },
            'recent_jobs': recent_jobs,
            'pending_estimates': estimates,
            'outstanding_invoices': invoices
        }

    # =========================================================================
    # ACTIVITY LOG
    # =========================================================================

    def get_activity_log(self, customer_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get customer portal activity log"""
        activity = self.db.execute("""
            SELECT * FROM portal_activity
            WHERE customer_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (customer_id, limit))

        return [dict(a) for a in activity] if activity else []

    # =========================================================================
    # ADMIN FUNCTIONS
    # =========================================================================

    def get_all_portal_activity(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all portal activity for admin review"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        activity = self.db.execute("""
            SELECT pa.*, c.first_name, c.last_name, c.email
            FROM portal_activity pa
            JOIN customers c ON pa.customer_id = c.id
            WHERE pa.created_at >= ?
            ORDER BY pa.created_at DESC
            LIMIT ?
        """, (cutoff, limit))

        result = []
        for a in activity:
            result.append({
                'id': a['id'],
                'customer_id': a['customer_id'],
                'customer_name': f"{a['first_name']} {a['last_name']}",
                'customer_email': a['email'],
                'action': a['action'],
                'details': a['details'],
                'ip_address': a['ip_address'],
                'created_at': a['created_at']
            })

        return result

    def get_portal_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get portal usage statistics"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # Active tokens
        active_tokens = self.db.execute("""
            SELECT COUNT(*) as count FROM portal_tokens
            WHERE is_active = 1 AND expires_at > ?
        """, (datetime.now().isoformat(),))

        # Total logins
        logins = self.db.execute("""
            SELECT COUNT(*) as count FROM portal_activity
            WHERE action = 'LOGIN' AND created_at >= ?
        """, (cutoff,))

        # Estimates approved via portal
        approvals = self.db.execute("""
            SELECT COUNT(*) as count FROM portal_approvals
            WHERE status = 'APPROVED' AND created_at >= ?
        """, (cutoff,))

        # Payments made via portal
        portal_payments = self.db.execute("""
            SELECT COUNT(*) as count, SUM(amount) as total FROM payments
            WHERE payer_type = 'CUSTOMER' AND created_at >= ?
        """, (cutoff,))

        # Messages sent
        messages = self.db.execute("""
            SELECT COUNT(*) as count FROM portal_messages
            WHERE sender_type = 'CUSTOMER' AND created_at >= ?
        """, (cutoff,))

        # Photos uploaded
        photos = self.db.execute("""
            SELECT COUNT(*) as count FROM portal_photos
            WHERE uploaded_at >= ?
        """, (cutoff,))

        return {
            'period_days': days,
            'active_portal_links': active_tokens[0]['count'] if active_tokens else 0,
            'total_logins': logins[0]['count'] if logins else 0,
            'estimates_approved': approvals[0]['count'] if approvals else 0,
            'payments_count': portal_payments[0]['count'] if portal_payments else 0,
            'payments_total': portal_payments[0]['total'] if portal_payments and portal_payments[0]['total'] else 0,
            'messages_sent': messages[0]['count'] if messages else 0,
            'photos_uploaded': photos[0]['count'] if photos else 0
        }

    def generate_portal_report(self, days: int = 30) -> str:
        """Generate portal usage report"""
        stats = self.get_portal_stats(days)
        activity = self.get_all_portal_activity(days, limit=20)

        report = []
        report.append("=" * 60)
        report.append("CUSTOMER PORTAL USAGE REPORT")
        report.append(f"Period: Last {days} Days")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("=" * 60)
        report.append("")

        report.append("SUMMARY STATISTICS")
        report.append("-" * 40)
        report.append(f"Active Portal Links:      {stats['active_portal_links']:>10}")
        report.append(f"Total Logins:             {stats['total_logins']:>10}")
        report.append(f"Estimates Approved:       {stats['estimates_approved']:>10}")
        report.append(f"Payments Made:            {stats['payments_count']:>10}")
        report.append(f"Payment Total:            ${stats['payments_total']:>9,.2f}")
        report.append(f"Messages Sent:            {stats['messages_sent']:>10}")
        report.append(f"Photos Uploaded:          {stats['photos_uploaded']:>10}")
        report.append("")

        report.append("RECENT ACTIVITY")
        report.append("-" * 40)
        for a in activity[:10]:
            report.append(f"  {a['created_at'][:16]} | {a['customer_name'][:20]:<20} | {a['action']}")
        report.append("")

        return "\n".join(report)
