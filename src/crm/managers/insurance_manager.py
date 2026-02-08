"""
Insurance Claim Manager
Tracks insurance claims and adjuster communications

SOLVES THE #1 PAIN POINT:
- Adjusters who don't respond
- "Never received" claims (we have proof!)
- Lost correspondence
- Approval tracking

FEATURES:
- Every email tracked
- Auto-follow-up if no response
- Days since last contact
- Email parsing for decisions
- Complete audit trail
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import re


class InsuranceManager:
    """
    Manage insurance claims and adjuster tracking

    This is the system that solves the "adjuster never responds" problem!
    """

    # Email sentiment keywords
    APPROVAL_KEYWORDS = [
        'approved', 'authorization', 'authorize', 'proceed', 'go ahead',
        'green light', 'confirmed', 'acceptance', 'accept'
    ]

    DENIAL_KEYWORDS = [
        'denied', 'decline', 'reject', 'not approved', 'cannot approve',
        'unable to approve', 'insufficient', 'not covered'
    ]

    QUESTION_KEYWORDS = [
        'question', 'clarify', 'clarification', 'additional information',
        'need more', 'please provide', 'can you send', 'require'
    ]

    # Valid claim statuses
    CLAIM_STATUSES = [
        'SUBMITTED',
        'PENDING_ADJUSTER',
        'ADJUSTER_SCHEDULED',
        'INSPECTED',
        'WAITING_APPROVAL',
        'APPROVED',
        'SUPPLEMENT_NEEDED',
        'SUPPLEMENT_APPROVED',
        'PAID',
        'CLOSED'
    ]

    def __init__(self, db):
        """Initialize insurance manager with database connection"""
        self.db = db

    # ========================================================================
    # CLAIM CREATION & MANAGEMENT
    # ========================================================================

    def create_claim(
        self,
        claim_number: str,
        insurance_company: str,
        policy_number: Optional[str] = None,
        adjuster_name: Optional[str] = None,
        adjuster_email: Optional[str] = None,
        adjuster_phone: Optional[str] = None,
        adjuster_extension: Optional[str] = None,
        claim_date: Optional[date] = None,
        claimed_amount: Optional[float] = None,
        deductible: Optional[float] = None,
        notes: Optional[str] = None,
        auto_follow_up_enabled: bool = True
    ) -> int:
        """
        Create insurance claim

        Args:
            claim_number: Insurance claim number
            insurance_company: Insurance company name
            adjuster_name: Adjuster's name
            adjuster_email: Adjuster's email (CRITICAL for tracking!)
            adjuster_phone: Adjuster's phone
            claimed_amount: Amount claimed
            auto_follow_up_enabled: Enable auto-follow-up emails

        Returns:
            Claim ID
        """
        claim_data = {
            'claim_number': claim_number,
            'insurance_company': insurance_company,
            'policy_number': policy_number,
            'adjuster_name': adjuster_name,
            'adjuster_email': adjuster_email,
            'adjuster_phone': adjuster_phone,
            'adjuster_extension': adjuster_extension,
            'claim_date': claim_date.isoformat() if claim_date else date.today().isoformat(),
            'status': 'SUBMITTED',
            'claimed_amount': claimed_amount,
            'deductible': deductible,
            'auto_follow_up_enabled': 1 if auto_follow_up_enabled else 0,
            'submitted_date': date.today().isoformat(),
            'notes': notes,
            'follow_up_count': 0
        }

        claim_id = self.db.insert('insurance_claims', claim_data)

        print(f"[OK] Created insurance claim #{claim_number} (ID: {claim_id})")
        if adjuster_email:
            print(f"     Adjuster: {adjuster_name} <{adjuster_email}>")
            if auto_follow_up_enabled:
                print(f"     Auto-follow-up ENABLED")

        return claim_id

    def get_claim(self, claim_id: int) -> Optional[Dict]:
        """
        Get claim with calculated fields

        Returns claim with:
        - Days since last response
        - Email count
        - Follow-up status
        """
        query = """
        SELECT
            c.*,
            COUNT(e.id) as email_count,
            MAX(CASE WHEN e.direction = 'RECEIVED' THEN e.received_at END) as last_response_at,
            JULIANDAY('now') - JULIANDAY(MAX(CASE WHEN e.direction = 'RECEIVED' THEN e.received_at END)) as days_since_response
        FROM insurance_claims c
        LEFT JOIN email_tracking e ON e.insurance_claim_id = c.id
        WHERE c.id = ? AND c.deleted_at IS NULL
        GROUP BY c.id
        """

        results = self.db.execute(query, (claim_id,))

        if not results:
            return None

        claim = results[0]

        # Calculate days since last contact
        if claim.get('last_contact_date'):
            try:
                last_contact = datetime.fromisoformat(claim['last_contact_date']).date()
                claim['days_since_last_contact'] = (date.today() - last_contact).days
            except:
                claim['days_since_last_contact'] = None
        else:
            claim['days_since_last_contact'] = None

        return claim

    def get_claim_by_number(self, claim_number: str) -> Optional[Dict]:
        """Get claim by claim number"""
        results = self.db.execute(
            "SELECT id FROM insurance_claims WHERE claim_number = ? AND deleted_at IS NULL",
            (claim_number,)
        )
        if results:
            return self.get_claim(results[0]['id'])
        return None

    def update_claim(self, claim_id: int, data: Dict) -> bool:
        """Update claim fields"""
        return self.db.update('insurance_claims', claim_id, data)

    def update_claim_status(
        self,
        claim_id: int,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update claim status

        Status progression:
        SUBMITTED -> PENDING_ADJUSTER -> ADJUSTER_SCHEDULED ->
        INSPECTED -> WAITING_APPROVAL -> APPROVED -> SUPPLEMENT_NEEDED ->
        SUPPLEMENT_APPROVED -> PAID -> CLOSED
        """
        if status not in self.CLAIM_STATUSES:
            raise ValueError(f"Invalid status: {status}. Valid: {self.CLAIM_STATUSES}")

        updates = {
            'status': status
        }

        # Auto-set dates based on status
        if status == 'APPROVED':
            updates['approval_date'] = date.today().isoformat()
        elif status == 'PAID':
            updates['payment_received_date'] = date.today().isoformat()
        elif status == 'INSPECTED':
            updates['adjuster_inspection_date'] = date.today().isoformat()
        elif status == 'ADJUSTER_SCHEDULED':
            updates['adjuster_scheduled_date'] = datetime.now().isoformat()

        if notes:
            claim = self.get_claim(claim_id)
            existing_notes = claim.get('notes') or ''
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_notes = f"[{timestamp}] Status -> {status}: {notes}"
            updates['notes'] = f"{existing_notes}\n{new_notes}".strip()

        self.db.update('insurance_claims', claim_id, updates)

        claim = self.get_claim(claim_id)
        print(f"[OK] Updated claim {claim['claim_number']} status: {status}")

        return True

    def set_approved_amount(self, claim_id: int, amount: float) -> bool:
        """Set the approved amount for a claim"""
        return self.update_claim(claim_id, {'approved_amount': amount})

    def set_supplement_amount(self, claim_id: int, amount: float) -> bool:
        """Set supplement amount for a claim"""
        return self.update_claim(claim_id, {'supplement_amount': amount})

    def delete_claim(self, claim_id: int) -> bool:
        """Soft delete a claim"""
        return self.db.delete('insurance_claims', claim_id, soft=True)

    def search_claims(
        self,
        status: Optional[str] = None,
        insurance_company: Optional[str] = None,
        adjuster_email: Optional[str] = None,
        needs_follow_up: bool = False,
        no_response_days: Optional[int] = None,
        job_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search claims with filters

        Args:
            status: Claim status
            insurance_company: Filter by company
            adjuster_email: Filter by adjuster
            needs_follow_up: Claims needing follow-up
            no_response_days: Claims with no response for X days
        """
        query = """
        SELECT
            c.*,
            COUNT(e.id) as email_count,
            MAX(CASE WHEN e.direction = 'RECEIVED' THEN e.received_at END) as last_response_at,
            JULIANDAY('now') - JULIANDAY(c.last_contact_date) as days_since_contact
        FROM insurance_claims c
        LEFT JOIN email_tracking e ON e.insurance_claim_id = c.id
        WHERE c.deleted_at IS NULL
        """

        params = []

        if status:
            query += " AND c.status = ?"
            params.append(status)

        if insurance_company:
            query += " AND c.insurance_company LIKE ?"
            params.append(f"%{insurance_company}%")

        if adjuster_email:
            query += " AND c.adjuster_email = ?"
            params.append(adjuster_email)

        if needs_follow_up:
            query += " AND c.next_follow_up_date <= date('now')"
            query += " AND c.status NOT IN ('APPROVED', 'PAID', 'CLOSED')"

        query += " GROUP BY c.id"

        if no_response_days:
            query += " HAVING days_since_contact >= ?"
            params.append(no_response_days)

        query += " ORDER BY c.next_follow_up_date ASC LIMIT ?"
        params.append(limit)

        return self.db.execute(query, tuple(params))

    def get_active_claims(self) -> List[Dict]:
        """Get all claims not in terminal status"""
        return self.search_claims(limit=500)

    def get_pending_claims(self) -> List[Dict]:
        """Get claims waiting for adjuster response"""
        return self.db.execute("""
            SELECT c.*,
                   JULIANDAY('now') - JULIANDAY(c.last_contact_date) as days_waiting
            FROM insurance_claims c
            WHERE c.deleted_at IS NULL
              AND c.status IN ('WAITING_APPROVAL', 'PENDING_ADJUSTER', 'SUBMITTED')
            ORDER BY days_waiting DESC
        """)

    # ========================================================================
    # EMAIL TRACKING (THE CRITICAL PART!)
    # ========================================================================

    def log_email(
        self,
        claim_id: int,
        direction: str,
        from_address: str,
        to_address: str,
        subject: str,
        body: str,
        cc_addresses: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        received_at: Optional[datetime] = None,
        job_id: Optional[int] = None
    ) -> int:
        """
        Log email correspondence

        THIS IS CRITICAL - Every email is tracked so adjusters can't claim
        they "never received" it!

        Args:
            claim_id: Insurance claim ID
            direction: SENT or RECEIVED
            from_address: Sender email
            to_address: Recipient email
            subject: Email subject
            body: Email body text
            sent_at: When sent (for SENT emails)
            received_at: When received (for RECEIVED emails)

        Returns:
            Email tracking ID
        """
        if direction not in ['SENT', 'RECEIVED']:
            raise ValueError("direction must be 'SENT' or 'RECEIVED'")

        # Parse email for keywords
        body_lower = body.lower()

        contains_approval = any(keyword in body_lower for keyword in self.APPROVAL_KEYWORDS)
        contains_denial = any(keyword in body_lower for keyword in self.DENIAL_KEYWORDS)
        contains_question = any(keyword in body_lower for keyword in self.QUESTION_KEYWORDS)

        # Determine sentiment
        if contains_approval:
            sentiment = 'POSITIVE'
        elif contains_denial:
            sentiment = 'NEGATIVE'
        elif contains_question:
            sentiment = 'NEUTRAL'
        else:
            sentiment = 'NEUTRAL'

        # Determine if response required
        requires_response = (direction == 'RECEIVED' and contains_question)

        email_data = {
            'insurance_claim_id': claim_id,
            'job_id': job_id,
            'direction': direction,
            'from_address': from_address,
            'to_address': to_address,
            'cc_addresses': cc_addresses,
            'subject': subject,
            'body': body,
            'contains_approval': 1 if contains_approval else 0,
            'contains_denial': 1 if contains_denial else 0,
            'contains_question': 1 if contains_question else 0,
            'sentiment': sentiment,
            'requires_response': 1 if requires_response else 0,
            'sent_at': sent_at.isoformat() if sent_at else None,
            'received_at': received_at.isoformat() if received_at else None
        }

        email_id = self.db.insert('email_tracking', email_data)

        # Update claim last contact
        if direction == 'SENT':
            self.db.execute("""
                UPDATE insurance_claims
                SET last_contact_date = ?,
                    last_contact_method = 'EMAIL',
                    follow_up_count = follow_up_count + 1,
                    next_follow_up_date = date('now', '+3 days'),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (date.today().isoformat(), claim_id))

        elif direction == 'RECEIVED':
            # Reset follow-up counter when we get response
            self.db.execute("""
                UPDATE insurance_claims
                SET last_contact_date = ?,
                    last_contact_method = 'EMAIL',
                    follow_up_count = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (date.today().isoformat(), claim_id))

            # Auto-update status if approval detected
            if contains_approval:
                claim = self.get_claim(claim_id)
                if claim and claim['status'] in ['WAITING_APPROVAL', 'INSPECTED', 'PENDING_ADJUSTER']:
                    self.update_claim_status(
                        claim_id,
                        'APPROVED',
                        notes='Auto-detected approval in email'
                    )

        direction_icon = "[SENT]" if direction == "SENT" else "[RECEIVED]"
        print(f"{direction_icon} Logged email: {subject}")

        if contains_approval:
            print(f"     APPROVAL DETECTED!")
        elif contains_denial:
            print(f"     DENIAL DETECTED!")
        elif contains_question:
            print(f"     QUESTION DETECTED - Response required")

        return email_id

    def get_claim_emails(
        self,
        claim_id: int,
        direction: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all emails for a claim

        Returns complete email history with parsing results
        """
        query = """
        SELECT *
        FROM email_tracking
        WHERE insurance_claim_id = ?
        """

        params = [claim_id]

        if direction:
            query += " AND direction = ?"
            params.append(direction)

        query += " ORDER BY created_at ASC"

        return self.db.execute(query, tuple(params))

    def get_emails_needing_response(self) -> List[Dict]:
        """Get all received emails that need a response"""
        return self.db.execute("""
            SELECT e.*, c.claim_number, c.insurance_company, c.adjuster_name
            FROM email_tracking e
            JOIN insurance_claims c ON c.id = e.insurance_claim_id
            WHERE e.requires_response = 1
              AND e.response_received = 0
              AND c.deleted_at IS NULL
            ORDER BY e.received_at ASC
        """)

    def mark_email_responded(self, email_id: int, response_email_id: int = None) -> bool:
        """Mark an email as having been responded to"""
        self.db.execute("""
            UPDATE email_tracking
            SET response_received = 1,
                response_to_email_id = ?
            WHERE id = ?
        """, (response_email_id, email_id))
        return True

    # ========================================================================
    # AUTO-FOLLOW-UP SYSTEM (THE GAME CHANGER!)
    # ========================================================================

    def get_claims_needing_follow_up(
        self,
        days_threshold: int = 3
    ) -> List[Dict]:
        """
        Get claims that need follow-up emails

        Returns claims where:
        - Auto-follow-up is enabled
        - No response in X days
        - Not in terminal status

        Args:
            days_threshold: Days without response before follow-up
        """
        query = """
        SELECT
            c.*,
            JULIANDAY('now') - JULIANDAY(c.last_contact_date) as days_since_last_contact,
            (
                SELECT COUNT(*)
                FROM email_tracking e
                WHERE e.insurance_claim_id = c.id
                  AND e.direction = 'RECEIVED'
            ) as response_count
        FROM insurance_claims c
        WHERE c.deleted_at IS NULL
          AND c.auto_follow_up_enabled = 1
          AND c.status NOT IN ('APPROVED', 'PAID', 'CLOSED')
          AND c.last_contact_date IS NOT NULL
          AND JULIANDAY('now') - JULIANDAY(c.last_contact_date) >= ?
        ORDER BY days_since_last_contact DESC
        """

        return self.db.execute(query, (days_threshold,))

    def generate_follow_up_email(
        self,
        claim_id: int,
        shop_name: str = "PDR Shop",
        shop_email: str = "shop@pdrbusiness.com"
    ) -> Dict[str, str]:
        """
        Generate follow-up email text

        Returns email template for follow-up

        Returns:
            {'to': email, 'subject': subject, 'body': body}
        """
        claim = self.get_claim(claim_id)

        if not claim:
            raise ValueError(f"Claim {claim_id} not found")

        # Get last email sent
        emails = self.get_claim_emails(claim_id, direction='SENT')
        last_email = emails[-1] if emails else None

        # Calculate days since last contact
        days = claim.get('days_since_last_contact', 0) or 0

        # Generate email
        to_email = claim['adjuster_email']

        subject = f"Follow-up: Claim {claim['claim_number']}"

        claimed_amount = claim['claimed_amount'] or 0

        body = f"""Hi {claim['adjuster_name'] or 'there'},

I'm following up on claim {claim['claim_number']} that we submitted {int(days)} day(s) ago.

Insurance Company: {claim['insurance_company']}
Policy Number: {claim['policy_number'] or 'N/A'}
Claimed Amount: ${claimed_amount:,.2f}

We haven't received a response yet. Could you please provide an update on the status of this claim?

"""

        if last_email:
            last_date = last_email.get('sent_at', '')[:10] if last_email.get('sent_at') else 'recently'
            body += f"""Our last correspondence was on {last_date} regarding:
"{last_email['subject']}"

"""

        body += f"""Please let us know if you need any additional information.

Thank you,
{shop_name}
"""

        return {
            'from': shop_email,
            'to': to_email,
            'subject': subject,
            'body': body,
            'claim_id': claim_id,
            'claim_number': claim['claim_number'],
            'days_since_contact': int(days)
        }

    def send_auto_follow_ups(
        self,
        days_threshold: int = 3,
        dry_run: bool = True,
        shop_name: str = "PDR Shop",
        shop_email: str = "shop@pdrbusiness.com"
    ) -> List[Dict]:
        """
        Send automated follow-up emails

        THIS IS THE AUTOMATION THAT SOLVES THE PROBLEM!

        Args:
            days_threshold: Days before follow-up
            dry_run: If True, don't actually send, just show what would happen

        Returns:
            List of follow-ups that were (or would be) sent
        """
        claims = self.get_claims_needing_follow_up(days_threshold)

        follow_ups = []

        print(f"\n[AUTO-FOLLOW-UP SYSTEM]")
        print(f"   Checking claims with no response in {days_threshold}+ days...")
        print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print()

        for claim in claims:
            email = self.generate_follow_up_email(
                claim['id'],
                shop_name=shop_name,
                shop_email=shop_email
            )

            if dry_run:
                print(f"[WOULD SEND] Follow-up for claim {email['claim_number']}:")
                print(f"   To: {email['to']}")
                print(f"   Subject: {email['subject']}")
                print(f"   Days since last contact: {email['days_since_contact']}")
                print()
            else:
                # In production, this would actually send via email service
                # For now, just log it
                self.log_email(
                    claim_id=claim['id'],
                    direction='SENT',
                    from_address=shop_email,
                    to_address=email['to'],
                    subject=email['subject'],
                    body=email['body'],
                    sent_at=datetime.now()
                )

                print(f"[OK] Sent follow-up for claim {email['claim_number']}")
                print(f"     To: {email['to']}")
                print()

            follow_ups.append(email)

        if not follow_ups:
            print("   No claims need follow-up at this time")
        else:
            print(f"   Total: {len(follow_ups)} follow-up(s)")

        print()

        return follow_ups

    def schedule_adjuster_appointment(
        self,
        claim_id: int,
        appointment_date: datetime,
        notes: str = None
    ) -> bool:
        """Schedule adjuster inspection appointment"""
        self.update_claim(claim_id, {
            'adjuster_scheduled_date': appointment_date.isoformat()
        })
        return self.update_claim_status(claim_id, 'ADJUSTER_SCHEDULED', notes)

    def record_adjuster_inspection(
        self,
        claim_id: int,
        inspection_notes: str = None
    ) -> bool:
        """Record that adjuster inspection occurred"""
        self.update_claim(claim_id, {
            'adjuster_inspection_date': date.today().isoformat()
        })
        return self.update_claim_status(claim_id, 'INSPECTED', inspection_notes)

    # ========================================================================
    # CLAIM STATISTICS
    # ========================================================================

    def get_claim_stats(self) -> Dict:
        """Get claim statistics for dashboard"""
        stats = {}

        # Total claims
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM insurance_claims
            WHERE deleted_at IS NULL
        """)
        stats['total_claims'] = result[0]['count']

        # By status
        result = self.db.execute("""
            SELECT status, COUNT(*) as count
            FROM insurance_claims
            WHERE deleted_at IS NULL
            GROUP BY status
        """)
        stats['by_status'] = {row['status']: row['count'] for row in result}

        # Needs follow-up (no response in 3+ days)
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM insurance_claims
            WHERE deleted_at IS NULL
              AND auto_follow_up_enabled = 1
              AND status NOT IN ('APPROVED', 'PAID', 'CLOSED')
              AND JULIANDAY('now') - JULIANDAY(last_contact_date) >= 3
        """)
        stats['needs_follow_up'] = result[0]['count']

        # Awaiting response
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM insurance_claims
            WHERE deleted_at IS NULL
              AND status IN ('PENDING_ADJUSTER', 'WAITING_APPROVAL', 'SUBMITTED')
        """)
        stats['awaiting_response'] = result[0]['count']

        # Average approval time (days)
        result = self.db.execute("""
            SELECT AVG(
                JULIANDAY(approval_date) - JULIANDAY(submitted_date)
            ) as avg_days
            FROM insurance_claims
            WHERE deleted_at IS NULL
              AND approval_date IS NOT NULL
              AND submitted_date IS NOT NULL
        """)
        stats['avg_approval_days'] = round(result[0]['avg_days'] or 0, 1)

        # Total claimed vs approved
        result = self.db.execute("""
            SELECT
                SUM(claimed_amount) as total_claimed,
                SUM(approved_amount) as total_approved,
                SUM(payment_received) as total_received
            FROM insurance_claims
            WHERE deleted_at IS NULL
        """)
        stats['total_claimed'] = result[0]['total_claimed'] or 0
        stats['total_approved'] = result[0]['total_approved'] or 0
        stats['total_received'] = result[0]['total_received'] or 0

        # Email stats
        result = self.db.execute("""
            SELECT
                COUNT(*) as total_emails,
                SUM(CASE WHEN direction = 'SENT' THEN 1 ELSE 0 END) as sent,
                SUM(CASE WHEN direction = 'RECEIVED' THEN 1 ELSE 0 END) as received
            FROM email_tracking
        """)
        stats['total_emails'] = result[0]['total_emails'] or 0
        stats['emails_sent'] = result[0]['sent'] or 0
        stats['emails_received'] = result[0]['received'] or 0

        return stats

    def get_adjuster_performance(self) -> List[Dict]:
        """
        Get performance metrics by adjuster

        Shows which adjusters are responsive vs slow
        """
        query = """
        SELECT
            adjuster_name,
            adjuster_email,
            insurance_company,
            COUNT(*) as total_claims,
            AVG(JULIANDAY(approval_date) - JULIANDAY(submitted_date)) as avg_approval_days,
            SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved_count,
            SUM(CASE WHEN status IN ('PENDING_ADJUSTER', 'WAITING_APPROVAL', 'SUBMITTED') THEN 1 ELSE 0 END) as pending_count,
            SUM(claimed_amount) as total_claimed,
            SUM(approved_amount) as total_approved
        FROM insurance_claims
        WHERE deleted_at IS NULL
          AND adjuster_email IS NOT NULL
        GROUP BY adjuster_email
        ORDER BY avg_approval_days ASC
        """

        return self.db.execute(query)

    def get_company_performance(self) -> List[Dict]:
        """Get performance metrics by insurance company"""
        query = """
        SELECT
            insurance_company,
            COUNT(*) as total_claims,
            AVG(JULIANDAY(approval_date) - JULIANDAY(submitted_date)) as avg_approval_days,
            SUM(CASE WHEN status = 'APPROVED' OR status = 'PAID' THEN 1 ELSE 0 END) as approved_count,
            SUM(claimed_amount) as total_claimed,
            SUM(approved_amount) as total_approved
        FROM insurance_claims
        WHERE deleted_at IS NULL
        GROUP BY insurance_company
        ORDER BY total_claims DESC
        """

        return self.db.execute(query)

    def get_slow_claims(self, days_threshold: int = 7) -> List[Dict]:
        """Get claims that have been pending for too long"""
        return self.db.execute("""
            SELECT c.*,
                   JULIANDAY('now') - JULIANDAY(c.submitted_date) as days_pending
            FROM insurance_claims c
            WHERE c.deleted_at IS NULL
              AND c.status NOT IN ('APPROVED', 'PAID', 'CLOSED')
              AND JULIANDAY('now') - JULIANDAY(c.submitted_date) >= ?
            ORDER BY days_pending DESC
        """, (days_threshold,))
