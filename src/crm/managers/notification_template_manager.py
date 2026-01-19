"""
Notification Template Manager
Customizable templates for all notification channels (email, SMS, push, in-app).

USAGE:
    from src.crm.managers.notification_template_manager import NotificationTemplateManager

    templates = NotificationTemplateManager(db_path)
    message = templates.render('JOB_STATUS_UPDATE', {
        'customer_name': 'John',
        'vehicle': '2024 Tesla Model 3',
        'status': 'Ready for Pickup'
    })
"""

import os
import re
from typing import Optional, Dict, Any, List
from datetime import datetime


class NotificationTemplateManager:
    """
    Manage notification templates with variable substitution.

    Features:
    - Database-stored custom templates
    - Default templates for all notification types
    - Variable substitution with {{variable}} syntax
    - Channel-specific templates (email, SMS, push, in-app)
    - Template versioning and A/B testing support
    """

    # Default templates for job status notifications
    DEFAULT_TEMPLATES = {
        # ====================================================================
        # JOB STATUS TEMPLATES
        # ====================================================================
        'JOB_DROPPED_OFF': {
            'title': 'Vehicle Received',
            'email_subject': 'Vehicle Received - {{job_number}}',
            'email_body': """Hello {{customer_name}},

We've received your {{vehicle}} at our facility.

Our team will inspect your vehicle and prepare a detailed repair estimate. We'll notify you as soon as it's ready.

Job Number: {{job_number}}
Drop-off Date: {{date}}

Thank you for choosing PDR Excellence!

Best regards,
PDR Excellence Team""",
            'sms': "PDR Update: We've received your {{vehicle}}. Job #{{job_number}}. We'll contact you with an estimate soon.",
            'push_title': 'Vehicle Received',
            'push_body': "We've received your {{vehicle}}. Inspection in progress.",
            'in_app': "We've received your {{vehicle}}. Our team will inspect it and prepare a detailed repair estimate."
        },

        'JOB_ESTIMATE_CREATED': {
            'title': 'Estimate Ready',
            'email_subject': 'Estimate Ready - {{job_number}}',
            'email_body': """Hello {{customer_name}},

Your repair estimate for {{vehicle}} is ready for review.

Estimated Cost: {{estimate_amount}}
Estimated Duration: {{estimated_days}} days

Please log in to your customer portal to review the details and approve the repair.

Portal Link: {{portal_url}}

Best regards,
PDR Excellence Team""",
            'sms': "PDR: Your estimate for {{vehicle}} is ready! Amount: {{estimate_amount}}. Review at {{portal_url}}",
            'push_title': 'Estimate Ready',
            'push_body': "Your repair estimate for {{vehicle}} is ready. Tap to review.",
            'in_app': "Your repair estimate for {{vehicle}} is ready. Please review and approve to proceed with repairs."
        },

        'JOB_APPROVED': {
            'title': 'Great News - Approved!',
            'email_subject': 'Great News - Approved! - {{job_number}}',
            'email_body': """Hello {{customer_name}},

Great news! Your repair for {{vehicle}} has been approved.

We'll schedule your repair and assign a technician soon. You'll receive a notification when work begins.

Job Number: {{job_number}}
Approved Amount: {{approved_amount}}

Best regards,
PDR Excellence Team""",
            'sms': "PDR: Great news! Your {{vehicle}} repair is approved. We'll schedule it soon. Job #{{job_number}}",
            'push_title': 'Repair Approved!',
            'push_body': "Your {{vehicle}} repair has been approved! Scheduling soon.",
            'in_app': "Your claim for {{vehicle}} has been approved! We'll schedule your repair soon."
        },

        'JOB_SCHEDULED': {
            'title': 'Repair Scheduled',
            'email_subject': 'Repair Scheduled - {{job_number}}',
            'email_body': """Hello {{customer_name}},

Your {{vehicle}} repair has been scheduled!

Scheduled Date: {{scheduled_date}}
Estimated Completion: {{completion_date}}
Technician: {{technician_name}}

Please ensure your vehicle is available on the scheduled date.

Best regards,
PDR Excellence Team""",
            'sms': "PDR: Your {{vehicle}} repair is scheduled for {{scheduled_date}}. Job #{{job_number}}",
            'push_title': 'Repair Scheduled',
            'push_body': "Your {{vehicle}} repair is scheduled for {{scheduled_date}}.",
            'in_app': "Your repair is scheduled for {{scheduled_date}}. We'll send a reminder before your appointment."
        },

        'JOB_IN_PROGRESS': {
            'title': 'Repair Started',
            'email_subject': 'Repair Started - {{job_number}}',
            'email_body': """Hello {{customer_name}},

Good news! We've started working on your {{vehicle}}.

Technician: {{technician_name}}
Estimated Completion: {{completion_date}}

We'll keep you updated on the progress and notify you when it's ready for pickup.

Best regards,
PDR Excellence Team""",
            'sms': "PDR: Work has begun on your {{vehicle}}! We'll notify you when it's ready. Job #{{job_number}}",
            'push_title': 'Repair Started',
            'push_body': "Work has started on your {{vehicle}}!",
            'in_app': "Good news! We've started working on your {{vehicle}}."
        },

        'JOB_READY_FOR_PICKUP': {
            'title': 'Ready for Pickup!',
            'email_subject': 'Your Vehicle is Ready! - {{job_number}}',
            'email_body': """Hello {{customer_name}},

Your {{vehicle}} repair is complete and ready for pickup!

Pickup Location: {{location_address}}
Business Hours: {{business_hours}}

Please bring a valid ID and your job number: {{job_number}}

Final Amount: {{final_amount}}
Payment Methods: Cash, Credit Card, Check

Thank you for choosing PDR Excellence!

Best regards,
PDR Excellence Team""",
            'sms': "PDR: Your {{vehicle}} is READY! Pick up at {{location_name}}. Job #{{job_number}}. Amount due: {{final_amount}}",
            'push_title': 'Vehicle Ready!',
            'push_body': "Your {{vehicle}} is ready for pickup!",
            'in_app': "Your {{vehicle}} repair is complete and ready for pickup!"
        },

        'JOB_COMPLETED': {
            'title': 'Repair Completed',
            'email_subject': 'Thank You! - {{job_number}}',
            'email_body': """Hello {{customer_name}},

Thank you for choosing PDR Excellence for your {{vehicle}} repair!

We hope you're satisfied with our service. If you have a moment, we'd appreciate your feedback.

Review Us: {{review_url}}
Refer a Friend: {{referral_url}} (Earn $50!)

Job Number: {{job_number}}
Completed Date: {{completion_date}}

Best regards,
PDR Excellence Team""",
            'sms': "PDR: Thanks for choosing us! Rate your experience: {{review_url}} Refer friends & earn $50!",
            'push_title': 'Thank You!',
            'push_body': "Thanks for choosing PDR Excellence! Tap to leave a review.",
            'in_app': "Thank you for choosing PDR Excellence! We hope you're satisfied with our service."
        },

        # ====================================================================
        # APPOINTMENT REMINDERS
        # ====================================================================
        'APPOINTMENT_REMINDER_24H': {
            'title': 'Appointment Tomorrow',
            'email_subject': 'Reminder: Appointment Tomorrow',
            'email_body': """Hello {{customer_name}},

This is a reminder that your appointment is tomorrow.

Date: {{appointment_date}}
Time: {{appointment_time}}
Location: {{location_address}}

Please arrive 10 minutes early. If you need to reschedule, please call us at {{phone_number}}.

Best regards,
PDR Excellence Team""",
            'sms': "PDR Reminder: Your appointment is tomorrow at {{appointment_time}}. Location: {{location_name}}. Call {{phone_number}} to reschedule.",
            'push_title': 'Appointment Tomorrow',
            'push_body': "Reminder: Your appointment is tomorrow at {{appointment_time}}.",
            'in_app': "Reminder: Your appointment is scheduled for tomorrow at {{appointment_time}}."
        },

        'APPOINTMENT_REMINDER_2H': {
            'title': 'Appointment in 2 Hours',
            'email_subject': 'Reminder: Appointment in 2 Hours',
            'email_body': """Hello {{customer_name}},

Your appointment is in 2 hours.

Time: {{appointment_time}}
Location: {{location_address}}

See you soon!

Best regards,
PDR Excellence Team""",
            'sms': "PDR: Your appointment is in 2 hours at {{appointment_time}}. See you soon!",
            'push_title': 'Appointment Soon',
            'push_body': "Your appointment is in 2 hours!",
            'in_app': "Your appointment is in 2 hours. Please arrive 10 minutes early."
        },

        # ====================================================================
        # PAYMENT & INVOICE
        # ====================================================================
        'INVOICE_CREATED': {
            'title': 'Invoice Ready',
            'email_subject': 'Invoice #{{invoice_number}} - {{job_number}}',
            'email_body': """Hello {{customer_name}},

Your invoice is ready for review.

Invoice Number: {{invoice_number}}
Amount Due: {{amount_due}}
Due Date: {{due_date}}

Pay Online: {{payment_url}}

Best regards,
PDR Excellence Team""",
            'sms': "PDR: Invoice #{{invoice_number}} ready. Amount: {{amount_due}}. Pay at {{payment_url}}",
            'push_title': 'Invoice Ready',
            'push_body': "Your invoice for {{amount_due}} is ready.",
            'in_app': "Your invoice is ready. Amount due: {{amount_due}}."
        },

        'PAYMENT_RECEIVED': {
            'title': 'Payment Received',
            'email_subject': 'Payment Received - Thank You!',
            'email_body': """Hello {{customer_name}},

We've received your payment of {{payment_amount}}.

Invoice Number: {{invoice_number}}
Payment Date: {{payment_date}}
Payment Method: {{payment_method}}

Thank you for your payment!

Best regards,
PDR Excellence Team""",
            'sms': "PDR: Payment of {{payment_amount}} received. Thank you!",
            'push_title': 'Payment Received',
            'push_body': "We've received your payment of {{payment_amount}}.",
            'in_app': "Thank you! We've received your payment of {{payment_amount}}."
        },

        # ====================================================================
        # REFERRAL & REWARDS
        # ====================================================================
        'REFERRAL_BONUS': {
            'title': 'You Earned a Referral Bonus!',
            'email_subject': 'Congratulations! You Earned ${{bonus_amount}}!',
            'email_body': """Hello {{customer_name}},

Great news! {{referred_name}} used your referral link and completed their repair.

You've earned: ${{bonus_amount}}

Your total referral earnings: ${{total_earnings}}

Share your link for more rewards: {{referral_url}}

Best regards,
PDR Excellence Team""",
            'sms': "PDR: You earned ${{bonus_amount}} referral bonus! {{referred_name}} completed their repair. Total earned: ${{total_earnings}}",
            'push_title': 'Referral Bonus!',
            'push_body': "You earned ${{bonus_amount}}! {{referred_name}} completed their repair.",
            'in_app': "Congratulations! You earned ${{bonus_amount}} because {{referred_name}} completed their repair."
        },

        # ====================================================================
        # GENERAL
        # ====================================================================
        'WELCOME': {
            'title': 'Welcome to PDR Excellence!',
            'email_subject': 'Welcome to PDR Excellence!',
            'email_body': """Hello {{customer_name}},

Welcome to PDR Excellence! We're excited to have you as a customer.

Your customer portal is ready:
Portal: {{portal_url}}
Username: {{username}}

In your portal, you can:
- Track repair status
- View estimates and invoices
- Manage appointments
- Refer friends and earn rewards

If you have any questions, call us at {{phone_number}}.

Best regards,
PDR Excellence Team""",
            'sms': "Welcome to PDR Excellence! Your portal is ready: {{portal_url}}",
            'push_title': 'Welcome!',
            'push_body': "Welcome to PDR Excellence! Your portal is ready.",
            'in_app': "Welcome to PDR Excellence! Explore your portal to track repairs, manage appointments, and earn rewards."
        },

        'CUSTOM': {
            'title': '{{title}}',
            'email_subject': '{{subject}}',
            'email_body': '{{body}}',
            'sms': '{{message}}',
            'push_title': '{{title}}',
            'push_body': '{{message}}',
            'in_app': '{{message}}'
        }
    }

    def __init__(self, db_path: str):
        """
        Initialize template manager.

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
        """Ensure template tables exist."""
        db = self._get_db()

        # Custom templates table
        db.execute("""
            CREATE TABLE IF NOT EXISTS notification_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_key TEXT NOT NULL,
                channel TEXT NOT NULL,
                title TEXT,
                subject TEXT,
                body TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                version INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                created_by TEXT,
                UNIQUE(template_key, channel, version)
            )
        """)

        # Template usage log for A/B testing
        db.execute("""
            CREATE TABLE IF NOT EXISTS template_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_key TEXT NOT NULL,
                channel TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                customer_id INTEGER,
                sent_at TEXT,
                opened INTEGER DEFAULT 0,
                clicked INTEGER DEFAULT 0,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

    # ========================================================================
    # TEMPLATE RENDERING
    # ========================================================================

    def render(
        self,
        template_key: str,
        variables: Dict[str, Any],
        channel: str = 'all'
    ) -> Dict[str, str]:
        """
        Render a template with variable substitution.

        Args:
            template_key: Template identifier (e.g., 'JOB_READY_FOR_PICKUP')
            variables: Dict of variables to substitute
            channel: Specific channel or 'all' for all channels

        Returns:
            Dict with rendered templates for each channel
        """
        # Get template (custom or default)
        template = self._get_template(template_key)

        if not template:
            raise ValueError(f"Template not found: {template_key}")

        # Add default variables
        variables = self._add_default_variables(variables)

        result = {}

        if channel == 'all' or channel == 'title':
            result['title'] = self._substitute(template.get('title', ''), variables)

        if channel == 'all' or channel == 'email':
            result['email_subject'] = self._substitute(template.get('email_subject', ''), variables)
            result['email_body'] = self._substitute(template.get('email_body', ''), variables)

        if channel == 'all' or channel == 'sms':
            result['sms'] = self._substitute(template.get('sms', ''), variables)

        if channel == 'all' or channel == 'push':
            result['push_title'] = self._substitute(template.get('push_title', ''), variables)
            result['push_body'] = self._substitute(template.get('push_body', ''), variables)

        if channel == 'all' or channel == 'in_app':
            result['in_app'] = self._substitute(template.get('in_app', ''), variables)

        return result

    def render_email(self, template_key: str, variables: Dict[str, Any]) -> Dict[str, str]:
        """Render email template."""
        result = self.render(template_key, variables, channel='email')
        return {
            'subject': result.get('email_subject', ''),
            'body': result.get('email_body', '')
        }

    def render_sms(self, template_key: str, variables: Dict[str, Any]) -> str:
        """Render SMS template."""
        result = self.render(template_key, variables, channel='sms')
        return result.get('sms', '')

    def render_push(self, template_key: str, variables: Dict[str, Any]) -> Dict[str, str]:
        """Render push notification template."""
        result = self.render(template_key, variables, channel='push')
        return {
            'title': result.get('push_title', ''),
            'body': result.get('push_body', '')
        }

    def render_in_app(self, template_key: str, variables: Dict[str, Any]) -> Dict[str, str]:
        """Render in-app notification template."""
        result = self.render(template_key, variables, channel='in_app')
        title_result = self.render(template_key, variables, channel='title')
        return {
            'title': title_result.get('title', ''),
            'message': result.get('in_app', '')
        }

    def _substitute(self, text: str, variables: Dict[str, Any]) -> str:
        """Substitute {{variable}} placeholders with values."""
        if not text:
            return ''

        def replace(match):
            var_name = match.group(1).strip()
            value = variables.get(var_name, '')
            return str(value) if value is not None else ''

        # Replace {{variable}} patterns
        return re.sub(r'\{\{(\w+)\}\}', replace, text)

    def _add_default_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Add default variables if not provided."""
        defaults = {
            'company_name': 'PDR Excellence',
            'phone_number': '1-800-PDR-PROS',
            'portal_url': 'http://localhost:5000/portal/',
            'date': datetime.now().strftime('%B %d, %Y'),
            'time': datetime.now().strftime('%I:%M %p'),
            'year': datetime.now().strftime('%Y')
        }

        # Merge defaults with provided variables (provided takes precedence)
        return {**defaults, **variables}

    def _get_template(self, template_key: str) -> Optional[Dict]:
        """Get template from database or defaults."""
        db = self._get_db()

        # Check for custom template in database
        custom = db.execute("""
            SELECT * FROM notification_templates
            WHERE template_key = ? AND is_active = 1
            ORDER BY version DESC
            LIMIT 1
        """, (template_key,))

        if custom:
            # Build template from custom entries
            template = {}
            for row in db.execute("""
                SELECT channel, title, subject, body FROM notification_templates
                WHERE template_key = ? AND is_active = 1
                ORDER BY version DESC
            """, (template_key,)):
                channel = row['channel']
                if channel == 'email':
                    template['email_subject'] = row['subject']
                    template['email_body'] = row['body']
                    template['title'] = row['title']
                elif channel == 'sms':
                    template['sms'] = row['body']
                elif channel == 'push':
                    template['push_title'] = row['title']
                    template['push_body'] = row['body']
                elif channel == 'in_app':
                    template['title'] = row['title']
                    template['in_app'] = row['body']

            if template:
                return template

        # Fall back to default template
        return self.DEFAULT_TEMPLATES.get(template_key)

    # ========================================================================
    # TEMPLATE MANAGEMENT
    # ========================================================================

    def create_template(
        self,
        template_key: str,
        channel: str,
        body: str,
        title: Optional[str] = None,
        subject: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> int:
        """
        Create a custom template.

        Args:
            template_key: Template identifier
            channel: Channel (email, sms, push, in_app)
            body: Template body
            title: Optional title
            subject: Optional subject (for email)
            created_by: Who created this template

        Returns:
            Template ID
        """
        db = self._get_db()

        # Get next version
        existing = db.execute("""
            SELECT MAX(version) as max_version FROM notification_templates
            WHERE template_key = ? AND channel = ?
        """, (template_key, channel))

        version = (existing[0]['max_version'] or 0) + 1 if existing else 1

        return db.insert('notification_templates', {
            'template_key': template_key,
            'channel': channel,
            'title': title,
            'subject': subject,
            'body': body,
            'version': version,
            'is_active': 1,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'created_by': created_by
        })

    def update_template(
        self,
        template_id: int,
        body: Optional[str] = None,
        title: Optional[str] = None,
        subject: Optional[str] = None
    ) -> bool:
        """Update an existing template."""
        db = self._get_db()

        updates = {'updated_at': datetime.now().isoformat()}
        if body is not None:
            updates['body'] = body
        if title is not None:
            updates['title'] = title
        if subject is not None:
            updates['subject'] = subject

        db.execute("""
            UPDATE notification_templates
            SET body = COALESCE(?, body),
                title = COALESCE(?, title),
                subject = COALESCE(?, subject),
                updated_at = ?
            WHERE id = ?
        """, (body, title, subject, updates['updated_at'], template_id))

        return True

    def deactivate_template(self, template_id: int) -> bool:
        """Deactivate a template."""
        db = self._get_db()
        db.execute("""
            UPDATE notification_templates
            SET is_active = 0, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), template_id))
        return True

    def list_templates(self, template_key: Optional[str] = None) -> List[Dict]:
        """List all templates."""
        db = self._get_db()

        if template_key:
            return db.execute("""
                SELECT * FROM notification_templates
                WHERE template_key = ?
                ORDER BY channel, version DESC
            """, (template_key,))
        else:
            return db.execute("""
                SELECT * FROM notification_templates
                ORDER BY template_key, channel, version DESC
            """)

    def get_default_templates(self) -> Dict:
        """Get all default templates."""
        return self.DEFAULT_TEMPLATES.copy()

    def get_template_keys(self) -> List[str]:
        """Get list of all available template keys."""
        return list(self.DEFAULT_TEMPLATES.keys())

    # ========================================================================
    # USAGE TRACKING
    # ========================================================================

    def log_usage(
        self,
        template_key: str,
        channel: str,
        customer_id: Optional[int] = None,
        version: int = 1
    ) -> int:
        """Log template usage for analytics."""
        db = self._get_db()

        return db.insert('template_usage_log', {
            'template_key': template_key,
            'channel': channel,
            'version': version,
            'customer_id': customer_id,
            'sent_at': datetime.now().isoformat()
        })

    def log_open(self, usage_id: int):
        """Log that a notification was opened."""
        db = self._get_db()
        db.execute("""
            UPDATE template_usage_log SET opened = 1 WHERE id = ?
        """, (usage_id,))

    def log_click(self, usage_id: int):
        """Log that a notification link was clicked."""
        db = self._get_db()
        db.execute("""
            UPDATE template_usage_log SET clicked = 1 WHERE id = ?
        """, (usage_id,))

    def get_template_stats(self, template_key: str, days: int = 30) -> Dict:
        """Get usage statistics for a template."""
        db = self._get_db()
        from datetime import timedelta
        since = (datetime.now() - timedelta(days=days)).isoformat()

        stats = db.execute("""
            SELECT
                channel,
                COUNT(*) as sent,
                SUM(opened) as opened,
                SUM(clicked) as clicked
            FROM template_usage_log
            WHERE template_key = ? AND sent_at > ?
            GROUP BY channel
        """, (template_key, since))

        return {
            'template_key': template_key,
            'period_days': days,
            'by_channel': {row['channel']: {
                'sent': row['sent'],
                'opened': row['opened'] or 0,
                'clicked': row['clicked'] or 0,
                'open_rate': (row['opened'] or 0) / row['sent'] * 100 if row['sent'] > 0 else 0,
                'click_rate': (row['clicked'] or 0) / row['sent'] * 100 if row['sent'] > 0 else 0
            } for row in stats}
        }
