"""
Job Notification Manager
Real-time notifications for job status changes

Supports multiple channels:
- In-app notifications (customer portal)
- Email notifications
- SMS notifications (via Twilio)
- Push notifications (Pushover, ntfy, FCM)

USAGE:
    from src.crm.managers.job_notification_manager import JobNotificationManager

    notifier = JobNotificationManager(db_path)
    notifier.notify_status_change(job_id=123, from_status='IN_PROGRESS', to_status='READY_FOR_PICKUP')
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, time
import json
import os


class JobNotificationManager:
    """
    Manage real-time notifications for job status changes.

    Dispatches notifications to multiple channels based on customer preferences.
    """

    # Default statuses that trigger notifications
    DEFAULT_NOTIFY_STATUSES = [
        'APPROVED',
        'SCHEDULED',
        'IN_PROGRESS',
        'READY_FOR_PICKUP',
        'COMPLETED'
    ]

    # Status message templates
    STATUS_MESSAGES = {
        'NEW': {
            'title': 'Job Created',
            'message': 'Your repair job for {vehicle} has been created. We\'ll keep you updated on its progress.',
            'priority': 'NORMAL'
        },
        'WAITING_DROP_OFF': {
            'title': 'Drop-off Scheduled',
            'message': 'Your {vehicle} is scheduled for drop-off. We\'ll send a reminder before your appointment.',
            'priority': 'NORMAL'
        },
        'DROPPED_OFF': {
            'title': 'Vehicle Received',
            'message': 'We\'ve received your {vehicle}. Our team will inspect it and provide an update soon.',
            'priority': 'NORMAL'
        },
        'ESTIMATE_CREATED': {
            'title': 'Estimate Ready',
            'message': 'Your repair estimate for {vehicle} is ready. Please review it in your portal.',
            'priority': 'NORMAL'
        },
        'WAITING_INSURANCE': {
            'title': 'Submitted to Insurance',
            'message': 'Your claim for {vehicle} has been submitted to insurance. We\'ll update you once we hear back.',
            'priority': 'NORMAL'
        },
        'ADJUSTER_SCHEDULED': {
            'title': 'Adjuster Appointment Set',
            'message': 'An insurance adjuster appointment has been scheduled for your {vehicle}.',
            'priority': 'NORMAL'
        },
        'APPROVED': {
            'title': 'Great News - Approved!',
            'message': 'Your claim for {vehicle} has been approved! We\'ll schedule your repair soon.',
            'priority': 'HIGH'
        },
        'WAITING_PARTS': {
            'title': 'Waiting for Parts',
            'message': 'We\'re waiting on parts for your {vehicle}. We\'ll notify you when they arrive.',
            'priority': 'NORMAL'
        },
        'PARTS_RECEIVED': {
            'title': 'Parts Arrived',
            'message': 'All parts for your {vehicle} have arrived. Repair work will begin soon!',
            'priority': 'NORMAL'
        },
        'ASSIGNED_TO_TECH': {
            'title': 'Technician Assigned',
            'message': 'A skilled technician has been assigned to repair your {vehicle}.',
            'priority': 'NORMAL'
        },
        'IN_PROGRESS': {
            'title': 'Repair Started',
            'message': 'Good news! We\'ve started working on your {vehicle}. We\'ll keep you updated.',
            'priority': 'NORMAL'
        },
        'TECH_COMPLETE': {
            'title': 'Repair Work Complete',
            'message': 'Our technician has finished the repair work on your {vehicle}. Quality check is next!',
            'priority': 'NORMAL'
        },
        'QC_COMPLETE': {
            'title': 'Quality Check Passed',
            'message': 'Your {vehicle} has passed our quality inspection. Almost ready for pickup!',
            'priority': 'NORMAL'
        },
        'DETAIL_COMPLETE': {
            'title': 'Detailing Complete',
            'message': 'Your {vehicle} has been cleaned and detailed. Looking great!',
            'priority': 'NORMAL'
        },
        'READY_FOR_PICKUP': {
            'title': 'Ready for Pickup!',
            'message': 'Your {vehicle} is ready for pickup! Visit your portal to see the details.',
            'priority': 'HIGH'
        },
        'COMPLETED': {
            'title': 'Thank You!',
            'message': 'Thank you for choosing us! Your {vehicle} repair is complete. We appreciate your business.',
            'priority': 'NORMAL'
        },
        'INVOICED': {
            'title': 'Invoice Ready',
            'message': 'Your invoice for {vehicle} repair is ready. View it in your portal.',
            'priority': 'NORMAL'
        },
        'PAID': {
            'title': 'Payment Received',
            'message': 'Thank you! We\'ve received your payment for {vehicle} repair.',
            'priority': 'NORMAL'
        }
    }

    def __init__(self, db_path: str):
        """
        Initialize job notification manager.

        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self._ensure_tables()

    def _get_db(self):
        """Get database connection."""
        from src.crm.models.database import Database
        return Database(self.db_path)

    def _ensure_tables(self):
        """Ensure notification tables exist."""
        db = self._get_db()

        # Customer notification preferences
        db.execute("""
            CREATE TABLE IF NOT EXISTS customer_notification_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL UNIQUE,
                email_enabled INTEGER DEFAULT 1,
                sms_enabled INTEGER DEFAULT 0,
                push_enabled INTEGER DEFAULT 0,
                in_app_enabled INTEGER DEFAULT 1,
                notify_on_statuses TEXT,
                quiet_hours_start TEXT,
                quiet_hours_end TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # In-app notifications
        db.execute("""
            CREATE TABLE IF NOT EXISTS customer_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                job_id INTEGER,
                notification_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'UNREAD',
                priority TEXT DEFAULT 'NORMAL',
                created_at TEXT,
                read_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)

        # Create indexes
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_notifications_customer_id
            ON customer_notifications(customer_id)
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_notifications_status
            ON customer_notifications(status)
        """)

    # ========================================================================
    # MAIN NOTIFICATION TRIGGER
    # ========================================================================

    def notify_status_change(
        self,
        job_id: int,
        from_status: Optional[str],
        to_status: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trigger notifications when job status changes.

        Args:
            job_id: The job ID
            from_status: Previous status (None for new jobs)
            to_status: New status
            notes: Optional notes about the status change

        Returns:
            Dict with notification results for each channel
        """
        db = self._get_db()
        results = {
            'in_app': False,
            'email': False,
            'sms': False,
            'push': False
        }

        # Get job and customer info
        job_info = self._get_job_info(job_id)
        if not job_info:
            print(f"[WARN] Job {job_id} not found for notification")
            return results

        customer_id = job_info['customer_id']

        # Get customer preferences
        preferences = self.get_customer_preferences(customer_id)

        # Check if we should notify for this status
        if not self.should_notify_for_status(preferences, to_status):
            print(f"[INFO] Skipping notification for status {to_status} (not in customer preferences)")
            return results

        # Check quiet hours
        if self.is_within_quiet_hours(preferences):
            print(f"[INFO] Skipping notification - within quiet hours")
            # Still create in-app notification, just don't send push/SMS
            results['in_app'] = self._create_in_app_notification(
                customer_id=customer_id,
                job_id=job_id,
                to_status=to_status,
                job_info=job_info,
                notes=notes
            )
            return results

        # Get message template
        message_data = self._format_status_message(to_status, job_info, notes)

        # Send to each enabled channel
        if preferences.get('in_app_enabled', True):
            results['in_app'] = self._create_in_app_notification(
                customer_id=customer_id,
                job_id=job_id,
                to_status=to_status,
                job_info=job_info,
                notes=notes
            )

        if preferences.get('email_enabled', True) and job_info.get('customer_email'):
            results['email'] = self._send_email_notification(
                customer_id=customer_id,
                job_info=job_info,
                message_data=message_data
            )

        if preferences.get('sms_enabled', False) and job_info.get('customer_phone'):
            results['sms'] = self._send_sms_notification(
                job_info=job_info,
                message_data=message_data
            )

        if preferences.get('push_enabled', False):
            results['push'] = self._send_push_notification(
                customer_id=customer_id,
                message_data=message_data
            )

        print(f"[OK] Notifications sent for job #{job_info['job_number']}: {to_status}")
        return results

    # ========================================================================
    # IN-APP NOTIFICATIONS
    # ========================================================================

    def _create_in_app_notification(
        self,
        customer_id: int,
        job_id: int,
        to_status: str,
        job_info: Dict,
        notes: Optional[str] = None
    ) -> bool:
        """Create an in-app notification for the customer portal."""
        db = self._get_db()

        message_data = self._format_status_message(to_status, job_info, notes)

        try:
            db.execute("""
                INSERT INTO customer_notifications (
                    customer_id, job_id, notification_type,
                    title, message, status, priority, created_at
                ) VALUES (?, ?, ?, ?, ?, 'UNREAD', ?, ?)
            """, (
                customer_id,
                job_id,
                'STATUS_UPDATE',
                message_data['title'],
                message_data['message'],
                message_data['priority'],
                datetime.now().isoformat()
            ))
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create in-app notification: {e}")
            return False

    def create_notification(
        self,
        customer_id: int,
        notification_type: str,
        title: str,
        message: str,
        job_id: Optional[int] = None,
        priority: str = 'NORMAL'
    ) -> int:
        """
        Create a custom notification.

        Args:
            customer_id: Customer ID
            notification_type: Type (STATUS_UPDATE, MESSAGE, REMINDER, etc.)
            title: Notification title
            message: Notification message
            job_id: Optional related job ID
            priority: Priority (LOW, NORMAL, HIGH)

        Returns:
            Notification ID
        """
        db = self._get_db()

        notification_id = db.insert('customer_notifications', {
            'customer_id': customer_id,
            'job_id': job_id,
            'notification_type': notification_type,
            'title': title,
            'message': message,
            'status': 'UNREAD',
            'priority': priority,
            'created_at': datetime.now().isoformat()
        })

        return notification_id

    def get_notifications(
        self,
        customer_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict]:
        """Get notifications for a customer."""
        db = self._get_db()

        query = """
            SELECT
                n.*,
                j.job_number,
                j.status as job_status
            FROM customer_notifications n
            LEFT JOIN jobs j ON j.id = n.job_id
            WHERE n.customer_id = ?
        """
        params = [customer_id]

        if unread_only:
            query += " AND n.status = 'UNREAD'"

        query += " ORDER BY n.created_at DESC LIMIT ?"
        params.append(limit)

        return db.execute(query, tuple(params))

    def get_notifications_since(
        self,
        customer_id: int,
        since: datetime
    ) -> List[Dict]:
        """Get notifications created since a specific time (for SSE)."""
        db = self._get_db()

        return db.execute("""
            SELECT
                n.*,
                j.job_number,
                j.status as job_status
            FROM customer_notifications n
            LEFT JOIN jobs j ON j.id = n.job_id
            WHERE n.customer_id = ?
              AND n.created_at > ?
            ORDER BY n.created_at ASC
        """, (customer_id, since.isoformat()))

    def get_unread_count(self, customer_id: int) -> int:
        """Get count of unread notifications."""
        db = self._get_db()

        result = db.execute("""
            SELECT COUNT(*) as count
            FROM customer_notifications
            WHERE customer_id = ? AND status = 'UNREAD'
        """, (customer_id,))

        return result[0]['count'] if result else 0

    def mark_as_read(self, notification_id: int) -> bool:
        """Mark a notification as read."""
        db = self._get_db()

        db.execute("""
            UPDATE customer_notifications
            SET status = 'READ', read_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), notification_id))

        return True

    def mark_all_as_read(self, customer_id: int) -> int:
        """Mark all notifications as read for a customer."""
        db = self._get_db()

        result = db.execute("""
            UPDATE customer_notifications
            SET status = 'READ', read_at = ?
            WHERE customer_id = ? AND status = 'UNREAD'
        """, (datetime.now().isoformat(), customer_id))

        return result

    def dismiss_notification(self, notification_id: int) -> bool:
        """Dismiss (delete) a notification."""
        db = self._get_db()

        db.execute("""
            UPDATE customer_notifications
            SET status = 'DISMISSED'
            WHERE id = ?
        """, (notification_id,))

        return True

    # ========================================================================
    # EMAIL NOTIFICATIONS
    # ========================================================================

    def _send_email_notification(
        self,
        customer_id: int,
        job_info: Dict,
        message_data: Dict
    ) -> bool:
        """Send email notification for status change."""
        try:
            from src.crm.managers.email_manager import EmailManager

            db = self._get_db()
            email_manager = EmailManager(db)

            # Create email content
            subject = f"{message_data['title']} - {job_info['job_number']}"

            body = f"""Hello {job_info['customer_name']},

{message_data['message']}

Job Details:
- Job Number: {job_info['job_number']}
- Vehicle: {job_info['vehicle_description']}
- Current Status: {job_info['status']}

View your job status and updates in your customer portal:
[Login to Portal]

If you have any questions, please contact us:
Phone: (555) 123-4567
Email: support@pdrexcellence.com

Best regards,
PDR Excellence
"""

            email_manager.send_email(
                to_email=job_info['customer_email'],
                to_name=job_info['customer_name'],
                subject=subject,
                body=body,
                job_id=job_info['id'],
                customer_id=customer_id
            )

            return True
        except Exception as e:
            print(f"[ERROR] Failed to send email notification: {e}")
            return False

    # ========================================================================
    # SMS NOTIFICATIONS
    # ========================================================================

    def _send_sms_notification(
        self,
        job_info: Dict,
        message_data: Dict
    ) -> bool:
        """Send SMS notification for status change."""
        try:
            from src.alerts.notifiers import TwilioNotifierFromEnv

            # Create SMS message (keep it short)
            sms_message = f"""PDR Update: {message_data['title']}

{message_data['message'][:120]}...

Job: {job_info['job_number']}
"""

            # Try to use Twilio from environment
            notifier = TwilioNotifierFromEnv()
            if notifier.client:
                notifier._send_sms(job_info['customer_phone'], sms_message)
                return True
            else:
                print("[INFO] Twilio not configured - SMS notification skipped")
                return False

        except ImportError:
            print("[INFO] Twilio not available - SMS notification skipped")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to send SMS notification: {e}")
            return False

    # ========================================================================
    # PUSH NOTIFICATIONS
    # ========================================================================

    def _send_push_notification(
        self,
        customer_id: int,
        message_data: Dict
    ) -> bool:
        """Send push notification (Pushover, ntfy, etc.)."""
        try:
            from src.alerts.notifiers import PushoverNotifierFromEnv, NtfyNotifierFromEnv

            sent = False

            # Try Pushover
            try:
                pushover = PushoverNotifierFromEnv()
                if pushover.user_key and pushover.api_token:
                    # Send a simplified push notification
                    import urllib.request
                    import urllib.parse

                    payload = {
                        'token': pushover.api_token,
                        'user': pushover.user_key,
                        'title': message_data['title'],
                        'message': message_data['message'],
                        'priority': 1 if message_data['priority'] == 'HIGH' else 0
                    }

                    data = urllib.parse.urlencode(payload).encode('utf-8')
                    req = urllib.request.Request(pushover.api_url, data=data)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        if response.status == 200:
                            sent = True
            except Exception:
                pass

            # Try ntfy
            try:
                ntfy = NtfyNotifierFromEnv()
                if ntfy.topic:
                    import urllib.request

                    url = f"{ntfy.server}/{ntfy.topic}"
                    headers = {
                        'Content-Type': 'text/plain; charset=utf-8',
                        'Title': message_data['title'],
                        'Priority': 'high' if message_data['priority'] == 'HIGH' else 'default'
                    }

                    req = urllib.request.Request(
                        url,
                        data=message_data['message'].encode('utf-8'),
                        headers=headers,
                        method='POST'
                    )
                    with urllib.request.urlopen(req, timeout=10) as response:
                        if response.status == 200:
                            sent = True
            except Exception:
                pass

            return sent
        except Exception as e:
            print(f"[ERROR] Failed to send push notification: {e}")
            return False

    # ========================================================================
    # CUSTOMER PREFERENCES
    # ========================================================================

    def get_customer_preferences(self, customer_id: int) -> Dict:
        """Get notification preferences for a customer."""
        db = self._get_db()

        result = db.execute("""
            SELECT * FROM customer_notification_preferences
            WHERE customer_id = ?
        """, (customer_id,))

        if result:
            prefs = result[0]
            # Parse JSON statuses
            if prefs.get('notify_on_statuses'):
                try:
                    prefs['notify_on_statuses'] = json.loads(prefs['notify_on_statuses'])
                except:
                    prefs['notify_on_statuses'] = self.DEFAULT_NOTIFY_STATUSES
            else:
                prefs['notify_on_statuses'] = self.DEFAULT_NOTIFY_STATUSES
            return prefs
        else:
            # Return defaults
            return {
                'customer_id': customer_id,
                'email_enabled': True,
                'sms_enabled': False,
                'push_enabled': False,
                'in_app_enabled': True,
                'notify_on_statuses': self.DEFAULT_NOTIFY_STATUSES,
                'quiet_hours_start': None,
                'quiet_hours_end': None
            }

    def update_customer_preferences(
        self,
        customer_id: int,
        preferences: Dict
    ) -> bool:
        """Update notification preferences for a customer."""
        db = self._get_db()

        # Check if preferences exist
        existing = db.execute("""
            SELECT id FROM customer_notification_preferences
            WHERE customer_id = ?
        """, (customer_id,))

        # Serialize statuses
        if 'notify_on_statuses' in preferences:
            preferences['notify_on_statuses'] = json.dumps(preferences['notify_on_statuses'])

        now = datetime.now().isoformat()

        if existing:
            # Update
            preferences['updated_at'] = now
            db.update('customer_notification_preferences', existing[0]['id'], preferences)
        else:
            # Insert
            preferences['customer_id'] = customer_id
            preferences['created_at'] = now
            preferences['updated_at'] = now
            db.insert('customer_notification_preferences', preferences)

        return True

    def should_notify_for_status(self, preferences: Dict, status: str) -> bool:
        """Check if notification should be sent for this status."""
        notify_statuses = preferences.get('notify_on_statuses', self.DEFAULT_NOTIFY_STATUSES)
        return status in notify_statuses

    def is_within_quiet_hours(self, preferences: Dict) -> bool:
        """Check if current time is within quiet hours."""
        quiet_start = preferences.get('quiet_hours_start')
        quiet_end = preferences.get('quiet_hours_end')

        if not quiet_start or not quiet_end:
            return False

        try:
            now = datetime.now().time()
            start = time.fromisoformat(quiet_start)
            end = time.fromisoformat(quiet_end)

            # Handle overnight quiet hours (e.g., 22:00 to 08:00)
            if start > end:
                return now >= start or now <= end
            else:
                return start <= now <= end
        except ValueError:
            return False

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _get_job_info(self, job_id: int) -> Optional[Dict]:
        """Get job information for notifications."""
        db = self._get_db()

        result = db.execute("""
            SELECT
                j.id,
                j.job_number,
                j.status,
                j.customer_id,
                c.first_name || ' ' || c.last_name as customer_name,
                c.email as customer_email,
                c.phone as customer_phone,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description
            FROM jobs j
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            WHERE j.id = ?
        """, (job_id,))

        return result[0] if result else None

    def _format_status_message(
        self,
        status: str,
        job_info: Dict,
        notes: Optional[str] = None
    ) -> Dict:
        """Format status message with job details."""
        template = self.STATUS_MESSAGES.get(status, {
            'title': f'Status Update: {status}',
            'message': 'Your job status has been updated to {status}.',
            'priority': 'NORMAL'
        })

        # Format message with job info
        vehicle = job_info.get('vehicle_description', 'your vehicle')

        message = template['message'].format(
            vehicle=vehicle,
            status=status,
            job_number=job_info.get('job_number', ''),
            customer_name=job_info.get('customer_name', '')
        )

        # Add notes if provided
        if notes:
            message += f"\n\nNote: {notes}"

        return {
            'title': template['title'],
            'message': message,
            'priority': template.get('priority', 'NORMAL')
        }

    # ========================================================================
    # NOTIFICATION HISTORY
    # ========================================================================

    def get_notification_stats(self, customer_id: int, days: int = 30) -> Dict:
        """Get notification statistics for a customer."""
        db = self._get_db()
        from datetime import timedelta

        start_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Total notifications
        result = db.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'UNREAD' THEN 1 ELSE 0 END) as unread,
                SUM(CASE WHEN status = 'READ' THEN 1 ELSE 0 END) as read,
                SUM(CASE WHEN status = 'DISMISSED' THEN 1 ELSE 0 END) as dismissed
            FROM customer_notifications
            WHERE customer_id = ? AND created_at >= ?
        """, (customer_id, start_date))

        stats = result[0] if result else {}

        # By type
        by_type = db.execute("""
            SELECT notification_type, COUNT(*) as count
            FROM customer_notifications
            WHERE customer_id = ? AND created_at >= ?
            GROUP BY notification_type
        """, (customer_id, start_date))

        stats['by_type'] = {row['notification_type']: row['count'] for row in by_type}

        return stats
