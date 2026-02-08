"""
Email Manager
PDR CRM Part 11 - Email Integration & Automation

FEATURES:
- Email templates with variables
- Automated sending (reminders, follow-ups)
- Email tracking
- Queue management
- Template library
- Scheduled sending
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import json
import re


class EmailManager:
    """
    Manage email automation and templates

    Handles all email communication with customers
    """

    # Email templates
    TEMPLATES = {
        'ESTIMATE_DELIVERY': {
            'subject': 'Estimate for {vehicle_description} - {estimate_number}',
            'body': """Hello {customer_name},

Thank you for choosing our PDR services. Please find your estimate details below.

Vehicle: {vehicle_description}
Estimate Number: {estimate_number}
Total: ${estimate_total}

This estimate is valid for {estimate_expires_days} days.

If you have any questions or would like to schedule your repair, please contact us:
Phone: {shop_phone}
Email: {shop_email}

We look forward to serving you!

Best regards,
{shop_name}
{shop_address}"""
        },

        'APPOINTMENT_REMINDER': {
            'subject': 'Reminder: Drop-off Appointment {drop_off_date}',
            'body': """Hello {customer_name},

This is a friendly reminder about your upcoming appointment:

Date: {drop_off_date}
Time: {drop_off_time}
Vehicle: {vehicle_description}

What to bring:
- Vehicle keys
- Insurance information (if applicable)
- Payment method

Our location:
{shop_name}
{shop_address}

If you need to reschedule, please contact us as soon as possible:
Phone: {shop_phone}

See you soon!

Best regards,
{shop_name}"""
        },

        'READY_FOR_PICKUP': {
            'subject': 'Your {vehicle_description} is Ready for Pickup!',
            'body': """Hello {customer_name},

Great news! Your {vehicle_description} is ready for pickup.

Job: {job_number}
Completed: {completion_date}

Pickup hours:
Monday-Friday: 8:00 AM - 5:00 PM
Saturday: 9:00 AM - 1:00 PM

Total due: ${balance_due}

Please bring:
- Photo ID
- Payment (we accept cash, check, and credit cards)

Our location:
{shop_name}
{shop_address}
Phone: {shop_phone}

We look forward to seeing you!

Best regards,
{shop_name}"""
        },

        'INSURANCE_CLAIM_UPDATE': {
            'subject': 'Insurance Claim Update - {claim_number}',
            'body': """Hello {customer_name},

We wanted to update you on your insurance claim:

Claim Number: {claim_number}
Insurance Company: {insurance_company}
Status: {claim_status}

{claim_notes}

If you have any questions, please don't hesitate to contact us:
Phone: {shop_phone}
Email: {shop_email}

Best regards,
{shop_name}"""
        },

        'FOLLOW_UP_LEAD': {
            'subject': 'Following up on your PDR inquiry',
            'body': """Hello {customer_name},

I wanted to follow up regarding your recent inquiry about PDR services for your {vehicle_description}.

We specialize in paintless dent repair and would love to help restore your vehicle to perfect condition.

Would you like to:
- Get a free estimate?
- Schedule an inspection?
- Ask questions about our process?

Simply reply to this email or call us at {shop_phone}.

We're here to help!

Best regards,
{salesperson_name}
{shop_name}
Phone: {shop_phone}"""
        },

        'THANK_YOU': {
            'subject': 'Thank you for choosing {shop_name}!',
            'body': """Hello {customer_name},

Thank you for trusting us with your {vehicle_description}!

We hope you're completely satisfied with our work. If you have any questions or concerns, please don't hesitate to reach out.

We'd also appreciate it if you could:
- Leave us a review on Google
- Refer friends and family who need PDR services
- Keep our number handy for future needs

Here's a special offer for your next visit:
10% off your next PDR service (mention this email)

Thank you again!

Best regards,
{shop_name}
{shop_phone}
{shop_email}"""
        }
    }

    # Default shop info (can be overridden)
    DEFAULT_SHOP_INFO = {
        'shop_name': 'PDR Excellence',
        'shop_phone': '(555) 123-4567',
        'shop_email': 'info@pdrexcellence.com',
        'shop_address': '123 Main Street, Dallas, TX 75201'
    }

    def __init__(self, db, smtp_config: Optional[Dict] = None, shop_info: Optional[Dict] = None):
        """
        Initialize email manager

        Args:
            db: Database connection
            smtp_config: SMTP configuration for sending emails
            shop_info: Shop information for templates
        """
        self.db = db
        self.smtp_config = smtp_config or {}
        self.shop_info = shop_info or self.DEFAULT_SHOP_INFO

        # Ensure emails table exists
        self._ensure_emails_table()

    def _ensure_emails_table(self):
        """Create emails table if it doesn't exist"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Recipient
                to_email TEXT NOT NULL,
                to_name TEXT,
                cc TEXT,
                bcc TEXT,

                -- Content
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                attachments TEXT,

                -- Relationships
                job_id INTEGER,
                customer_id INTEGER,
                estimate_id INTEGER,
                lead_id INTEGER,

                -- Status
                status TEXT DEFAULT 'QUEUED',  -- QUEUED, SCHEDULED, SENT, FAILED, OPENED, CLICKED
                scheduled_send_at TIMESTAMP,
                sent_at TIMESTAMP,
                opened_at TIMESTAMP,
                clicked_at TIMESTAMP,

                -- Error tracking
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,

                -- Template info
                template_name TEXT,
                template_variables TEXT,

                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,

                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (estimate_id) REFERENCES estimates(id),
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        """)

        # Create indexes
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_emails_status
            ON emails(status)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_emails_customer
            ON emails(customer_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_emails_job
            ON emails(job_id)
        """)

    # ========================================================================
    # TEMPLATE MANAGEMENT
    # ========================================================================

    def get_template(self, template_name: str) -> Optional[Dict]:
        """Get email template by name"""
        return self.TEMPLATES.get(template_name)

    def list_templates(self) -> List[str]:
        """List available template names"""
        return list(self.TEMPLATES.keys())

    def get_template_preview(self, template_name: str) -> Optional[Dict]:
        """Get template with description of required variables"""
        template = self.get_template(template_name)
        if not template:
            return None

        # Find all variables in template
        subject_vars = re.findall(r'\{(\w+)\}', template['subject'])
        body_vars = re.findall(r'\{(\w+)\}', template['body'])
        all_vars = list(set(subject_vars + body_vars))

        return {
            'name': template_name,
            'subject': template['subject'],
            'body': template['body'],
            'required_variables': sorted(all_vars)
        }

    def render_template(
        self,
        template_name: str,
        variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Render template with variables

        Args:
            template_name: Template name
            variables: Variables to substitute

        Returns:
            Dict with rendered subject and body
        """
        template = self.get_template(template_name)

        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        # Merge shop info with provided variables
        all_vars = {**self.shop_info, **variables}

        # Render subject and body
        subject = template['subject']
        body = template['body']

        for key, value in all_vars.items():
            placeholder = '{' + key + '}'
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))

        # Check for missing variables
        missing_subject = re.findall(r'\{(\w+)\}', subject)
        missing_body = re.findall(r'\{(\w+)\}', body)

        if missing_subject or missing_body:
            missing = set(missing_subject + missing_body)
            print(f"[WARN] Missing variables: {', '.join(missing)}")

        return {
            'subject': subject,
            'body': body
        }

    # ========================================================================
    # EMAIL SENDING
    # ========================================================================

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        to_name: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        job_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        estimate_id: Optional[int] = None,
        lead_id: Optional[int] = None,
        send_at: Optional[datetime] = None,
        template_name: Optional[str] = None,
        template_variables: Optional[Dict] = None
    ) -> int:
        """
        Send email (or queue for later)

        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            to_name: Recipient name
            cc: CC recipients
            bcc: BCC recipients
            attachments: File paths to attach
            job_id: Related job ID
            customer_id: Related customer ID
            send_at: When to send (None = now)

        Returns:
            Email ID
        """
        # Determine status
        if send_at and send_at > datetime.now():
            status = 'SCHEDULED'
        else:
            status = 'QUEUED'
            send_at = datetime.now()

        # Create email record
        email_id = self.db.insert('emails', {
            'to_email': to_email,
            'to_name': to_name,
            'subject': subject,
            'body': body,
            'cc': json.dumps(cc) if cc else None,
            'bcc': json.dumps(bcc) if bcc else None,
            'attachments': json.dumps(attachments) if attachments else None,
            'job_id': job_id,
            'customer_id': customer_id,
            'estimate_id': estimate_id,
            'lead_id': lead_id,
            'status': status,
            'scheduled_send_at': send_at.isoformat() if send_at else None,
            'template_name': template_name,
            'template_variables': json.dumps(template_variables) if template_variables else None
        })

        # If queued, try to send now
        if status == 'QUEUED':
            self._send_queued_email(email_id)
        else:
            print(f"[OK] Email scheduled for {send_at.strftime('%m/%d/%Y %I:%M %p')}")

        return email_id

    def _send_queued_email(self, email_id: int) -> bool:
        """
        Actually send a queued email

        In production, this would use SMTP to send
        For now, we just mark it as sent (demo mode)
        """
        # Get email
        results = self.db.execute(
            "SELECT * FROM emails WHERE id = ?",
            (email_id,)
        )

        if not results:
            return False

        email = results[0]

        # Check SMTP config
        if not self.smtp_config.get('host'):
            # Demo mode - just mark as sent
            status = 'SENT'
        else:
            # Production mode - send via SMTP
            try:
                self._send_via_smtp(email)
                status = 'SENT'
            except Exception as e:
                status = 'FAILED'
                self.db.execute("""
                    UPDATE emails
                    SET status = 'FAILED',
                        error_message = ?,
                        retry_count = retry_count + 1,
                        updated_at = ?
                    WHERE id = ?
                """, (str(e), datetime.now().isoformat(), email_id))
                print(f"[ERROR] Failed to send email: {e}")
                return False

        # Update status
        self.db.execute("""
            UPDATE emails
            SET status = ?,
                sent_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            status,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            email_id
        ))

        print(f"[OK] Email sent to {email['to_email']}")
        print(f"     Subject: {email['subject']}")

        return True

    def _send_via_smtp(self, email: Dict):
        """Send email via SMTP (production implementation)"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg['From'] = f"{self.smtp_config.get('from_name', '')} <{self.smtp_config.get('from_email', '')}>"
        msg['To'] = email['to_email']
        msg['Subject'] = email['subject']

        if email.get('cc'):
            msg['Cc'] = ', '.join(json.loads(email['cc']))

        msg.attach(MIMEText(email['body'], 'plain'))

        with smtplib.SMTP(self.smtp_config['host'], self.smtp_config.get('port', 587)) as server:
            server.starttls()
            server.login(self.smtp_config['username'], self.smtp_config['password'])
            server.send_message(msg)

    def send_from_template(
        self,
        template_name: str,
        to_email: str,
        variables: Dict[str, Any],
        to_name: Optional[str] = None,
        job_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        estimate_id: Optional[int] = None,
        lead_id: Optional[int] = None,
        send_at: Optional[datetime] = None
    ) -> int:
        """
        Send email from template

        Combines render_template() and send_email()
        """
        # Render template
        rendered = self.render_template(template_name, variables)

        # Send email
        return self.send_email(
            to_email=to_email,
            to_name=to_name,
            subject=rendered['subject'],
            body=rendered['body'],
            job_id=job_id,
            customer_id=customer_id,
            estimate_id=estimate_id,
            lead_id=lead_id,
            send_at=send_at,
            template_name=template_name,
            template_variables=variables
        )

    # ========================================================================
    # AUTOMATED EMAILS
    # ========================================================================

    def send_estimate_email(
        self,
        estimate_id: int,
        send_at: Optional[datetime] = None
    ) -> int:
        """
        Send estimate to customer

        Automatically gathers all variables from estimate
        """
        # Get estimate details
        estimate = self.db.execute("""
            SELECT
                e.*,
                j.job_number,
                j.customer_id,
                c.first_name, c.last_name, c.email,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description
            FROM estimates e
            JOIN jobs j ON j.id = e.job_id
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            WHERE e.id = ?
        """, (estimate_id,))

        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        est = estimate[0]

        if not est['email']:
            raise ValueError("Customer has no email address")

        # Build variables
        variables = {
            'customer_name': f"{est['first_name']} {est['last_name']}",
            'vehicle_description': est['vehicle_description'],
            'estimate_number': est['estimate_number'],
            'estimate_total': f"{est['total']:.2f}",
            'estimate_expires_days': '30'
        }

        # Send from template
        email_id = self.send_from_template(
            template_name='ESTIMATE_DELIVERY',
            to_email=est['email'],
            to_name=f"{est['first_name']} {est['last_name']}",
            variables=variables,
            job_id=est['job_id'],
            customer_id=est['customer_id'],
            estimate_id=estimate_id,
            send_at=send_at
        )

        # Update estimate status
        self.db.execute("""
            UPDATE estimates
            SET sent_date = ?,
                status = CASE WHEN status = 'DRAFT' THEN 'SENT' ELSE status END,
                updated_at = ?
            WHERE id = ?
        """, (date.today().isoformat(), datetime.now().isoformat(), estimate_id))

        return email_id

    def send_appointment_reminder(
        self,
        job_id: int,
        hours_before: int = 24
    ) -> int:
        """
        Send appointment reminder

        Args:
            job_id: Job ID
            hours_before: Send X hours before appointment
        """
        # Get job details
        job = self.db.execute("""
            SELECT
                j.*,
                c.first_name, c.last_name, c.email,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description
            FROM jobs j
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            WHERE j.id = ?
        """, (job_id,))

        if not job:
            raise ValueError(f"Job {job_id} not found")

        j = job[0]

        if not j['email']:
            raise ValueError("Customer has no email address")

        if not j['scheduled_drop_off']:
            raise ValueError("Job has no scheduled drop-off")

        # Parse drop-off time
        drop_off = datetime.fromisoformat(j['scheduled_drop_off'])

        # Schedule reminder
        send_at = drop_off - timedelta(hours=hours_before)

        # Don't schedule in the past
        if send_at < datetime.now():
            send_at = None  # Send immediately

        # Build variables
        variables = {
            'customer_name': f"{j['first_name']} {j['last_name']}",
            'vehicle_description': j['vehicle_description'],
            'drop_off_date': drop_off.strftime('%A, %B %d, %Y'),
            'drop_off_time': drop_off.strftime('%I:%M %p')
        }

        # Send from template
        return self.send_from_template(
            template_name='APPOINTMENT_REMINDER',
            to_email=j['email'],
            to_name=f"{j['first_name']} {j['last_name']}",
            variables=variables,
            job_id=job_id,
            customer_id=j['customer_id'],
            send_at=send_at
        )

    def send_ready_for_pickup(self, job_id: int) -> int:
        """Send ready for pickup notification"""
        # Get job details
        job = self.db.execute("""
            SELECT
                j.*,
                c.first_name, c.last_name, c.email,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
                i.balance_due
            FROM jobs j
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            LEFT JOIN invoices i ON i.job_id = j.id
            WHERE j.id = ?
        """, (job_id,))

        if not job:
            raise ValueError(f"Job {job_id} not found")

        j = job[0]

        if not j['email']:
            raise ValueError("Customer has no email address")

        # Build variables
        variables = {
            'customer_name': f"{j['first_name']} {j['last_name']}",
            'vehicle_description': j['vehicle_description'],
            'job_number': j['job_number'],
            'completion_date': date.today().strftime('%B %d, %Y'),
            'balance_due': f"{j['balance_due'] or 0:.2f}"
        }

        # Send immediately
        return self.send_from_template(
            template_name='READY_FOR_PICKUP',
            to_email=j['email'],
            to_name=f"{j['first_name']} {j['last_name']}",
            variables=variables,
            job_id=job_id,
            customer_id=j['customer_id']
        )

    def send_insurance_update(
        self,
        claim_id: int,
        notes: str = ""
    ) -> int:
        """Send insurance claim status update"""
        # Get claim details
        claim = self.db.execute("""
            SELECT
                ic.*,
                j.id as job_id,
                j.customer_id,
                c.first_name, c.last_name, c.email
            FROM insurance_claims ic
            JOIN jobs j ON j.insurance_claim_id = ic.id
            JOIN customers c ON c.id = j.customer_id
            WHERE ic.id = ?
        """, (claim_id,))

        if not claim:
            raise ValueError(f"Claim {claim_id} not found")

        cl = claim[0]

        if not cl['email']:
            raise ValueError("Customer has no email address")

        # Build variables
        variables = {
            'customer_name': f"{cl['first_name']} {cl['last_name']}",
            'claim_number': cl['claim_number'],
            'insurance_company': cl['insurance_company'],
            'claim_status': cl['status'],
            'claim_notes': notes or "No additional notes at this time."
        }

        return self.send_from_template(
            template_name='INSURANCE_CLAIM_UPDATE',
            to_email=cl['email'],
            to_name=f"{cl['first_name']} {cl['last_name']}",
            variables=variables,
            job_id=cl['job_id'],
            customer_id=cl['customer_id']
        )

    def send_lead_followup(
        self,
        lead_id: int,
        salesperson_name: str = "Sales Team"
    ) -> int:
        """Send follow-up email to lead"""
        # Get lead details
        lead = self.db.execute("""
            SELECT *
            FROM leads
            WHERE id = ?
        """, (lead_id,))

        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        l = lead[0]

        if not l['email']:
            raise ValueError("Lead has no email address")

        # Build vehicle description
        vehicle_desc = "vehicle"
        if l['vehicle_year'] and l['vehicle_make'] and l['vehicle_model']:
            vehicle_desc = f"{l['vehicle_year']} {l['vehicle_make']} {l['vehicle_model']}"

        # Build variables
        variables = {
            'customer_name': f"{l['first_name']} {l['last_name']}",
            'vehicle_description': vehicle_desc,
            'salesperson_name': salesperson_name
        }

        return self.send_from_template(
            template_name='FOLLOW_UP_LEAD',
            to_email=l['email'],
            to_name=f"{l['first_name']} {l['last_name']}",
            variables=variables,
            lead_id=lead_id
        )

    def send_thank_you(self, job_id: int) -> int:
        """Send thank you email after job completion"""
        # Get job details
        job = self.db.execute("""
            SELECT
                j.*,
                c.first_name, c.last_name, c.email,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description
            FROM jobs j
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            WHERE j.id = ?
        """, (job_id,))

        if not job:
            raise ValueError(f"Job {job_id} not found")

        j = job[0]

        if not j['email']:
            raise ValueError("Customer has no email address")

        # Build variables
        variables = {
            'customer_name': f"{j['first_name']} {j['last_name']}",
            'vehicle_description': j['vehicle_description']
        }

        return self.send_from_template(
            template_name='THANK_YOU',
            to_email=j['email'],
            to_name=f"{j['first_name']} {j['last_name']}",
            variables=variables,
            job_id=job_id,
            customer_id=j['customer_id']
        )

    # ========================================================================
    # EMAIL QUEUE PROCESSING
    # ========================================================================

    def process_email_queue(self, limit: int = 50) -> int:
        """
        Process queued and scheduled emails

        Send any emails that are ready to go

        Returns:
            Number of emails sent
        """
        # Get emails ready to send
        emails = self.db.execute("""
            SELECT id
            FROM emails
            WHERE status IN ('QUEUED', 'SCHEDULED')
              AND (scheduled_send_at IS NULL OR scheduled_send_at <= ?)
            ORDER BY scheduled_send_at
            LIMIT ?
        """, (datetime.now().isoformat(), limit))

        sent_count = 0

        for email in emails:
            try:
                if self._send_queued_email(email['id']):
                    sent_count += 1
            except Exception as e:
                print(f"[ERROR] Failed to send email {email['id']}: {e}")

                # Mark as failed
                self.db.execute("""
                    UPDATE emails
                    SET status = 'FAILED',
                        error_message = ?,
                        retry_count = retry_count + 1,
                        updated_at = ?
                    WHERE id = ?
                """, (str(e), datetime.now().isoformat(), email['id']))

        if sent_count > 0:
            print(f"\n[OK] Processed {sent_count} email(s) from queue")

        return sent_count

    def retry_failed_emails(self, max_retries: int = 3) -> int:
        """Retry failed emails that haven't exceeded max retries"""
        # Reset status for retryable emails
        result = self.db.execute("""
            UPDATE emails
            SET status = 'QUEUED',
                updated_at = ?
            WHERE status = 'FAILED'
              AND retry_count < ?
        """, (datetime.now().isoformat(), max_retries))

        # Process queue
        return self.process_email_queue()

    # ========================================================================
    # EMAIL HISTORY & TRACKING
    # ========================================================================

    def get_email(self, email_id: int) -> Optional[Dict]:
        """Get email by ID"""
        results = self.db.execute("""
            SELECT * FROM emails WHERE id = ?
        """, (email_id,))
        return results[0] if results else None

    def get_email_history(
        self,
        job_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        lead_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get email history with filters"""
        query = """
            SELECT *
            FROM emails
            WHERE 1=1
        """
        params = []

        if job_id:
            query += " AND job_id = ?"
            params.append(job_id)

        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id)

        if lead_id:
            query += " AND lead_id = ?"
            params.append(lead_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        return self.db.execute(query, tuple(params))

    def mark_opened(self, email_id: int) -> bool:
        """Mark email as opened (for tracking pixels)"""
        self.db.execute("""
            UPDATE emails
            SET status = CASE WHEN status = 'SENT' THEN 'OPENED' ELSE status END,
                opened_at = COALESCE(opened_at, ?),
                updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), datetime.now().isoformat(), email_id))
        return True

    def mark_clicked(self, email_id: int) -> bool:
        """Mark email as clicked (for link tracking)"""
        self.db.execute("""
            UPDATE emails
            SET status = 'CLICKED',
                clicked_at = COALESCE(clicked_at, ?),
                updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), datetime.now().isoformat(), email_id))
        return True

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_email_stats(self, days: int = 30) -> Dict:
        """Get email statistics"""
        start_date = date.today() - timedelta(days=days)

        stats = {}

        # Total sent
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM emails
            WHERE status IN ('SENT', 'OPENED', 'CLICKED')
              AND sent_at >= ?
        """, (start_date.isoformat(),))
        stats['sent'] = result[0]['count'] if result else 0

        # By status
        result = self.db.execute("""
            SELECT status, COUNT(*) as count
            FROM emails
            WHERE created_at >= ?
            GROUP BY status
        """, (start_date.isoformat(),))
        stats['by_status'] = {row['status']: row['count'] for row in result}

        # Pending (queued + scheduled)
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM emails
            WHERE status IN ('QUEUED', 'SCHEDULED')
        """)
        stats['pending'] = result[0]['count'] if result else 0

        # Failed
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM emails
            WHERE status = 'FAILED'
              AND created_at >= ?
        """, (start_date.isoformat(),))
        stats['failed'] = result[0]['count'] if result else 0

        # Open rate
        opened = stats['by_status'].get('OPENED', 0) + stats['by_status'].get('CLICKED', 0)
        if stats['sent'] > 0:
            stats['open_rate'] = round((opened / stats['sent']) * 100, 1)
        else:
            stats['open_rate'] = 0

        # By template
        result = self.db.execute("""
            SELECT template_name, COUNT(*) as count
            FROM emails
            WHERE template_name IS NOT NULL
              AND created_at >= ?
            GROUP BY template_name
        """, (start_date.isoformat(),))
        stats['by_template'] = {row['template_name']: row['count'] for row in result}

        return stats

    def generate_email_report(self, days: int = 30) -> str:
        """Generate formatted email report"""
        stats = self.get_email_stats(days)

        lines = []
        lines.append("=" * 60)
        lines.append(f"EMAIL REPORT (Last {days} Days)")
        lines.append("=" * 60)
        lines.append("")

        lines.append(f"Total Sent:     {stats['sent']:>10d}")
        lines.append(f"Pending:        {stats['pending']:>10d}")
        lines.append(f"Failed:         {stats['failed']:>10d}")
        lines.append(f"Open Rate:      {stats['open_rate']:>9.1f}%")
        lines.append("")

        lines.append("By Status:")
        for status, count in stats.get('by_status', {}).items():
            lines.append(f"  {status:15s}: {count:>5d}")
        lines.append("")

        if stats.get('by_template'):
            lines.append("By Template:")
            for template, count in stats['by_template'].items():
                lines.append(f"  {template:25s}: {count:>5d}")

        return "\n".join(lines)
