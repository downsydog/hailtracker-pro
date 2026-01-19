"""
SMS Manager for Customer Notifications
Twilio-based SMS messaging for job status updates and customer communications.

USAGE:
    from src.crm.managers.sms_manager import SmsManager

    sms = SmsManager(db_path)
    sms.send_sms(customer_id, "Your vehicle is ready for pickup!")

SETUP:
    Set environment variables:
        TWILIO_ACCOUNT_SID=ACxxxxx
        TWILIO_AUTH_TOKEN=xxxxx
        TWILIO_FROM_NUMBER=+15551234567
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

# Try to import Twilio - optional dependency
try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    TwilioClient = None
    TwilioRestException = Exception


class SmsManager:
    """
    Manage SMS notifications for customers using Twilio.

    Features:
    - Send SMS to individual customers
    - Rate limiting to prevent spam
    - Message logging and tracking
    - Delivery status tracking
    """

    def __init__(self, db_path: str):
        """
        Initialize SMS manager.

        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self._ensure_tables()

        # Load Twilio credentials from environment
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.from_number = os.environ.get('TWILIO_FROM_NUMBER')

        # Initialize Twilio client
        self.client = None
        self._init_client()

        # Rate limiting settings
        self.max_messages_per_hour = int(os.environ.get('SMS_MAX_PER_HOUR', '5'))
        self.max_messages_per_day = int(os.environ.get('SMS_MAX_PER_DAY', '20'))

    def _get_db(self):
        """Get database connection."""
        from src.crm.models.database import Database
        return Database(self.db_path)

    def _ensure_tables(self):
        """Ensure SMS tracking tables exist."""
        db = self._get_db()

        # SMS log table
        db.execute("""
            CREATE TABLE IF NOT EXISTS sms_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                to_number TEXT NOT NULL,
                from_number TEXT,
                message TEXT NOT NULL,
                message_type TEXT DEFAULT 'NOTIFICATION',
                twilio_sid TEXT,
                status TEXT DEFAULT 'QUEUED',
                error_message TEXT,
                segments INTEGER DEFAULT 1,
                cost REAL,
                job_id INTEGER,
                sent_at TEXT,
                delivered_at TEXT,
                created_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)

        # Index for faster lookups
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sms_log_customer
            ON sms_log(customer_id)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sms_log_sent_at
            ON sms_log(sent_at)
        """)

    def _init_client(self):
        """Initialize Twilio client."""
        if not TWILIO_AVAILABLE:
            print("[INFO] Twilio not installed. Run: pip install twilio")
            return

        if not all([self.account_sid, self.auth_token, self.from_number]):
            print("[INFO] Twilio credentials not configured")
            print("       Set: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER")
            return

        try:
            self.client = TwilioClient(self.account_sid, self.auth_token)
            # Verify credentials by fetching account info
            account = self.client.api.accounts(self.account_sid).fetch()
            print(f"[OK] Twilio SMS initialized (Account: {account.friendly_name})")
        except Exception as e:
            print(f"[ERROR] Twilio initialization failed: {e}")
            self.client = None

    def is_configured(self) -> bool:
        """Check if SMS is properly configured."""
        return self.client is not None

    # ========================================================================
    # SENDING SMS
    # ========================================================================

    def send_sms(
        self,
        to_number: str,
        message: str,
        customer_id: Optional[int] = None,
        job_id: Optional[int] = None,
        message_type: str = 'NOTIFICATION',
        bypass_rate_limit: bool = False
    ) -> Dict[str, Any]:
        """
        Send an SMS message.

        Args:
            to_number: Phone number to send to (E.164 format preferred)
            message: Message content (max 1600 chars, will be split into segments)
            customer_id: Optional customer ID for tracking
            job_id: Optional job ID for tracking
            message_type: Type of message (NOTIFICATION, REMINDER, MARKETING, etc.)
            bypass_rate_limit: Skip rate limiting checks

        Returns:
            Dict with success status and details
        """
        if not self.client:
            return {
                'success': False,
                'error': 'Twilio not configured',
                'sent': False
            }

        # Normalize phone number
        to_number = self._normalize_phone(to_number)
        if not to_number:
            return {
                'success': False,
                'error': 'Invalid phone number',
                'sent': False
            }

        # Check rate limits
        if not bypass_rate_limit and not self._check_rate_limit(to_number):
            return {
                'success': False,
                'error': 'Rate limit exceeded',
                'sent': False
            }

        # Truncate message if too long
        if len(message) > 1600:
            message = message[:1597] + '...'

        db = self._get_db()

        try:
            # Send via Twilio
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )

            # Log the message
            log_id = db.insert('sms_log', {
                'customer_id': customer_id,
                'to_number': to_number,
                'from_number': self.from_number,
                'message': message,
                'message_type': message_type,
                'twilio_sid': twilio_message.sid,
                'status': twilio_message.status.upper() if twilio_message.status else 'SENT',
                'segments': twilio_message.num_segments or 1,
                'job_id': job_id,
                'sent_at': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            })

            print(f"[OK] SMS sent to ...{to_number[-4:]} (SID: {twilio_message.sid[:12]}...)")

            return {
                'success': True,
                'sent': True,
                'message_sid': twilio_message.sid,
                'status': twilio_message.status,
                'segments': twilio_message.num_segments or 1,
                'log_id': log_id
            }

        except TwilioRestException as e:
            error_msg = str(e)
            print(f"[ERROR] Twilio error: {error_msg}")

            # Log failed attempt
            db.insert('sms_log', {
                'customer_id': customer_id,
                'to_number': to_number,
                'from_number': self.from_number,
                'message': message,
                'message_type': message_type,
                'status': 'FAILED',
                'error_message': error_msg,
                'job_id': job_id,
                'sent_at': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            })

            return {
                'success': False,
                'error': error_msg,
                'sent': False
            }

        except Exception as e:
            print(f"[ERROR] SMS send failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'sent': False
            }

    def send_to_customer(
        self,
        customer_id: int,
        message: str,
        job_id: Optional[int] = None,
        message_type: str = 'NOTIFICATION'
    ) -> Dict[str, Any]:
        """
        Send SMS to a customer by their ID.

        Args:
            customer_id: Customer ID
            message: Message content
            job_id: Optional job ID for tracking
            message_type: Type of message

        Returns:
            Dict with success status and details
        """
        db = self._get_db()

        # Get customer phone number
        customer = db.execute("""
            SELECT phone, first_name, last_name FROM customers WHERE id = ?
        """, (customer_id,))

        if not customer:
            return {
                'success': False,
                'error': 'Customer not found',
                'sent': False
            }

        phone = customer[0].get('phone')
        if not phone:
            return {
                'success': False,
                'error': 'Customer has no phone number',
                'sent': False
            }

        return self.send_sms(
            to_number=phone,
            message=message,
            customer_id=customer_id,
            job_id=job_id,
            message_type=message_type
        )

    # ========================================================================
    # JOB STATUS NOTIFICATIONS
    # ========================================================================

    def send_job_notification(
        self,
        customer_id: int,
        job_id: int,
        title: str,
        message: str,
        job_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send job status notification via SMS.

        Args:
            customer_id: Customer ID
            job_id: Job ID
            title: Notification title
            message: Notification message
            job_number: Optional job number for reference

        Returns:
            Dict with success status
        """
        # Format SMS message (keep it concise)
        sms_text = f"PDR Update: {title}\n\n{message}"

        if job_number:
            sms_text += f"\n\nJob: {job_number}"

        # Add opt-out message (required for compliance)
        sms_text += "\n\nReply STOP to unsubscribe"

        return self.send_to_customer(
            customer_id=customer_id,
            message=sms_text,
            job_id=job_id,
            message_type='JOB_UPDATE'
        )

    # ========================================================================
    # RATE LIMITING
    # ========================================================================

    def _check_rate_limit(self, to_number: str) -> bool:
        """Check if we can send to this number (rate limiting)."""
        db = self._get_db()
        now = datetime.now()

        # Check hourly limit
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        hourly_count = db.execute("""
            SELECT COUNT(*) as count FROM sms_log
            WHERE to_number = ? AND sent_at > ? AND status != 'FAILED'
        """, (to_number, one_hour_ago))

        if hourly_count and hourly_count[0]['count'] >= self.max_messages_per_hour:
            print(f"[WARN] SMS hourly rate limit reached for ...{to_number[-4:]}")
            return False

        # Check daily limit
        one_day_ago = (now - timedelta(days=1)).isoformat()
        daily_count = db.execute("""
            SELECT COUNT(*) as count FROM sms_log
            WHERE to_number = ? AND sent_at > ? AND status != 'FAILED'
        """, (to_number, one_day_ago))

        if daily_count and daily_count[0]['count'] >= self.max_messages_per_day:
            print(f"[WARN] SMS daily rate limit reached for ...{to_number[-4:]}")
            return False

        return True

    # ========================================================================
    # PHONE NUMBER HANDLING
    # ========================================================================

    def _normalize_phone(self, phone: str) -> Optional[str]:
        """
        Normalize phone number to E.164 format.

        Args:
            phone: Phone number in various formats

        Returns:
            E.164 formatted number or None if invalid
        """
        if not phone:
            return None

        # Remove all non-digit characters except leading +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')

        # Handle different formats
        if cleaned.startswith('+'):
            # Already has country code
            return cleaned
        elif cleaned.startswith('1') and len(cleaned) == 11:
            # US/Canada number with country code
            return f'+{cleaned}'
        elif len(cleaned) == 10:
            # US/Canada number without country code
            return f'+1{cleaned}'
        elif len(cleaned) > 10:
            # Assume international with country code
            return f'+{cleaned}'

        # Invalid
        return None

    # ========================================================================
    # MESSAGE HISTORY & STATISTICS
    # ========================================================================

    def get_message_history(
        self,
        customer_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get SMS message history."""
        db = self._get_db()

        if customer_id:
            return db.execute("""
                SELECT * FROM sms_log
                WHERE customer_id = ?
                ORDER BY sent_at DESC
                LIMIT ? OFFSET ?
            """, (customer_id, limit, offset))
        else:
            return db.execute("""
                SELECT * FROM sms_log
                ORDER BY sent_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

    def get_statistics(self, days: int = 30) -> Dict:
        """Get SMS sending statistics."""
        db = self._get_db()
        since = (datetime.now() - timedelta(days=days)).isoformat()

        stats = db.execute("""
            SELECT
                COUNT(*) as total_sent,
                SUM(CASE WHEN status = 'DELIVERED' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                SUM(segments) as total_segments,
                COUNT(DISTINCT customer_id) as unique_customers
            FROM sms_log
            WHERE sent_at > ?
        """, (since,))

        return {
            'total_sent': stats[0]['total_sent'] if stats else 0,
            'delivered': stats[0]['delivered'] if stats else 0,
            'failed': stats[0]['failed'] if stats else 0,
            'total_segments': stats[0]['total_segments'] if stats else 0,
            'unique_customers': stats[0]['unique_customers'] if stats else 0,
            'period_days': days
        }

    def update_delivery_status(self, message_sid: str, status: str):
        """
        Update message delivery status (called by Twilio webhook).

        Args:
            message_sid: Twilio message SID
            status: New status (delivered, failed, etc.)
        """
        db = self._get_db()

        db.execute("""
            UPDATE sms_log
            SET status = ?,
                delivered_at = CASE WHEN ? = 'DELIVERED' THEN ? ELSE delivered_at END
            WHERE twilio_sid = ?
        """, (
            status.upper(),
            status.upper(),
            datetime.now().isoformat(),
            message_sid
        ))
