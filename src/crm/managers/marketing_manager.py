"""
PDR CRM Part 28 - Marketing Automation Manager
Automated marketing campaigns and follow-ups

FEATURES:
- Email campaigns
- SMS marketing
- Customer segmentation
- Automated sequences
- Drip campaigns
- Referral program
- Seasonal promotions
- Campaign analytics
- A/B testing
- Multi-channel coordination
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta


class MarketingManager:
    """
    Manage marketing campaigns and automation

    Multi-channel marketing automation
    """

    # Campaign types
    CAMPAIGN_TYPES = [
        'EMAIL',
        'SMS',
        'MULTI_CHANNEL',
        'AUTOMATED_SEQUENCE',
        'DRIP_CAMPAIGN'
    ]

    # Campaign statuses
    CAMPAIGN_STATUSES = [
        'DRAFT',
        'SCHEDULED',
        'ACTIVE',
        'PAUSED',
        'COMPLETED',
        'CANCELLED'
    ]

    # Trigger types
    TRIGGER_TYPES = [
        'JOB_COMPLETED',
        'DAYS_SINCE_SERVICE',
        'LEAD_CREATED',
        'BIRTHDAY',
        'ANNIVERSARY',
        'INACTIVE_CUSTOMER'
    ]

    def __init__(self, db):
        """Initialize marketing manager with database instance"""
        if isinstance(db, str):
            from ..models.database import Database
            self.db = Database(db)
        else:
            self.db = db
        self._ensure_marketing_tables()

    def _ensure_marketing_tables(self):
        """Ensure marketing-related tables exist"""
        # Customer segments
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS customer_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                segment_name TEXT NOT NULL,
                criteria TEXT,
                description TEXT,
                customer_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)

        # Email campaigns
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS email_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                email_content TEXT,
                segment_id INTEGER,
                send_date TIMESTAMP,
                from_name TEXT,
                from_email TEXT,
                campaign_type TEXT DEFAULT 'ONE_TIME',
                template_id INTEGER,
                sent_at TIMESTAMP,
                sent_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'DRAFT',
                FOREIGN KEY (segment_id) REFERENCES customer_segments(id)
            )
        """)

        # Campaign sends (tracking individual sends)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS campaign_sends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                sent_at TIMESTAMP,
                opened_at TIMESTAMP,
                clicked_at TIMESTAMP,
                bounced INTEGER DEFAULT 0,
                unsubscribed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'PENDING',
                FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # SMS campaigns
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sms_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_name TEXT NOT NULL,
                sms_content TEXT NOT NULL,
                segment_id INTEGER,
                send_date TIMESTAMP,
                sent_at TIMESTAMP,
                sent_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'DRAFT',
                FOREIGN KEY (segment_id) REFERENCES customer_segments(id)
            )
        """)

        # Automated sequences
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS automated_sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence_name TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_criteria TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)

        # Sequence steps
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sequence_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence_id INTEGER NOT NULL,
                step_number INTEGER NOT NULL,
                delay_days INTEGER DEFAULT 0,
                action_type TEXT NOT NULL,
                subject TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sequence_id) REFERENCES automated_sequences(id)
            )
        """)

        # Sequence instances (active sequences for customers)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sequence_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                triggered_at TIMESTAMP,
                trigger_data TEXT,
                current_step INTEGER DEFAULT 0,
                last_sent_at TIMESTAMP,
                completed_at TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (sequence_id) REFERENCES automated_sequences(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Promotions
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promotion_name TEXT NOT NULL,
                promotion_type TEXT NOT NULL,
                discount_type TEXT NOT NULL,
                discount_value REAL NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                promo_code TEXT,
                min_purchase REAL,
                max_uses INTEGER,
                uses_count INTEGER DEFAULT 0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)

        # Promotion uses
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS promotion_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promotion_id INTEGER NOT NULL,
                customer_id INTEGER,
                invoice_id INTEGER,
                discount_amount REAL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (promotion_id) REFERENCES promotions(id)
            )
        """)

        # Referrals
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_customer_id INTEGER NOT NULL,
                referred_customer_id INTEGER NOT NULL,
                referral_source TEXT DEFAULT 'DIRECT',
                referrer_reward_type TEXT,
                referrer_reward_value REAL,
                referred_reward_type TEXT,
                referred_reward_value REAL,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'PENDING',
                FOREIGN KEY (referrer_customer_id) REFERENCES customers(id),
                FOREIGN KEY (referred_customer_id) REFERENCES customers(id)
            )
        """)

        # A/B test variants
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS ab_test_variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                variant_name TEXT NOT NULL,
                subject TEXT,
                content TEXT,
                sent_count INTEGER DEFAULT 0,
                open_count INTEGER DEFAULT 0,
                click_count INTEGER DEFAULT 0,
                conversion_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id)
            )
        """)

    # ========================================================================
    # CUSTOMER SEGMENTATION
    # ========================================================================

    def create_customer_segment(
        self,
        segment_name: str,
        criteria: Dict,
        description: Optional[str] = None
    ) -> int:
        """
        Create customer segment for targeted marketing

        Args:
            segment_name: Segment name
            criteria: Segmentation criteria
            description: Segment description

        Returns:
            Segment ID
        """
        result = self.db.execute("""
            INSERT INTO customer_segments (
                segment_name, criteria, description,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            segment_name,
            json.dumps(criteria),
            description,
            datetime.now().isoformat(),
            'ACTIVE'
        ))

        segment_id = result[0]['id']

        # Calculate segment size
        customer_count = self._calculate_segment_size(criteria)

        self.db.execute("""
            UPDATE customer_segments
            SET customer_count = ?
            WHERE id = ?
        """, (customer_count, segment_id))

        print(f"[OK] Created customer segment: {segment_name}")
        print(f"     Customers in segment: {customer_count}")

        return segment_id

    def _calculate_segment_size(self, criteria: Dict) -> int:
        """Calculate number of customers matching criteria"""
        query = "SELECT COUNT(*) as count FROM customers WHERE 1=1"

        # Build dynamic query based on criteria
        # Simplified - real implementation would handle all criteria types
        # For now, just count all customers

        result = self.db.execute(query)
        return result[0]['count'] if result else 0

    def get_segment(self, segment_id: int) -> Optional[Dict]:
        """Get segment details"""
        result = self.db.execute(
            "SELECT * FROM customer_segments WHERE id = ?",
            (segment_id,)
        )

        if not result:
            return None

        segment = dict(result[0])
        if segment.get('criteria'):
            segment['criteria'] = json.loads(segment['criteria'])

        return segment

    def get_segment_customers(
        self,
        segment_id: int,
        limit: int = 100
    ) -> List[Dict]:
        """Get all customers in segment"""
        segment = self.get_segment(segment_id)

        if not segment:
            return []

        # Simplified - real implementation would filter by criteria
        customers = self.db.execute(
            "SELECT * FROM customers LIMIT ?",
            (limit,)
        )

        return [dict(c) for c in customers]

    def update_segment_count(self, segment_id: int) -> int:
        """Recalculate and update segment customer count"""
        segment = self.get_segment(segment_id)

        if not segment:
            return 0

        count = self._calculate_segment_size(segment['criteria'])

        self.db.execute("""
            UPDATE customer_segments
            SET customer_count = ?,
                updated_at = ?
            WHERE id = ?
        """, (count, datetime.now().isoformat(), segment_id))

        return count

    # ========================================================================
    # EMAIL CAMPAIGNS
    # ========================================================================

    def create_email_campaign(
        self,
        campaign_name: str,
        subject: str,
        email_content: str,
        segment_id: Optional[int] = None,
        send_date: Optional[datetime] = None,
        from_name: str = 'PDR Excellence',
        from_email: str = 'info@pdrexcellence.com',
        campaign_type: str = 'ONE_TIME',
        template_id: Optional[int] = None
    ) -> int:
        """
        Create email campaign

        Args:
            campaign_name: Campaign name
            subject: Email subject line
            email_content: Email body (HTML)
            segment_id: Target customer segment
            send_date: When to send (immediate if None)
            from_name: Sender name
            from_email: Sender email
            campaign_type: ONE_TIME, RECURRING, AUTOMATED
            template_id: Email template ID

        Returns:
            Campaign ID
        """
        status = 'SCHEDULED' if send_date else 'DRAFT'

        result = self.db.execute("""
            INSERT INTO email_campaigns (
                campaign_name, subject, email_content,
                segment_id, send_date, from_name, from_email,
                campaign_type, template_id,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            campaign_name,
            subject,
            email_content,
            segment_id,
            send_date.isoformat() if send_date else None,
            from_name,
            from_email,
            campaign_type,
            template_id,
            datetime.now().isoformat(),
            status
        ))

        campaign_id = result[0]['id']

        # Calculate recipient count
        recipient_count = 0
        if segment_id:
            segment = self.get_segment(segment_id)
            if segment:
                recipient_count = segment['customer_count']

        print(f"[OK] Created email campaign: {campaign_name}")
        print(f"     Subject: {subject}")
        print(f"     Recipients: {recipient_count}")
        if send_date:
            print(f"     Send date: {send_date.strftime('%B %d, %Y at %I:%M %p')}")

        return campaign_id

    def get_campaign(self, campaign_id: int) -> Optional[Dict]:
        """Get campaign details"""
        result = self.db.execute(
            "SELECT * FROM email_campaigns WHERE id = ?",
            (campaign_id,)
        )

        if not result:
            return None

        return dict(result[0])

    def send_campaign(
        self,
        campaign_id: int
    ) -> Dict:
        """
        Send email campaign

        Returns send results
        """
        campaign = self.get_campaign(campaign_id)

        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Get recipients
        customers = []
        if campaign['segment_id']:
            customers = self.get_segment_customers(campaign['segment_id'])

        # Send to each customer
        sent_count = 0
        failed_count = 0

        for customer in customers:
            try:
                # In production, actually send email via email service
                self.db.execute("""
                    INSERT INTO campaign_sends (
                        campaign_id, customer_id,
                        sent_at, status
                    ) VALUES (?, ?, ?, ?)
                """, (
                    campaign_id,
                    customer['id'],
                    datetime.now().isoformat(),
                    'SENT'
                ))
                sent_count += 1
            except Exception:
                failed_count += 1

        # Update campaign status
        self.db.execute("""
            UPDATE email_campaigns
            SET status = 'ACTIVE',
                sent_at = ?,
                sent_count = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            sent_count,
            datetime.now().isoformat(),
            campaign_id
        ))

        results = {
            'campaign_id': campaign_id,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_recipients': len(customers)
        }

        print(f"[OK] Campaign sent!")
        print(f"     Sent: {sent_count}")
        print(f"     Failed: {failed_count}")

        return results

    def record_email_open(
        self,
        campaign_id: int,
        customer_id: int
    ) -> bool:
        """Record email open event"""
        self.db.execute("""
            UPDATE campaign_sends
            SET opened_at = ?
            WHERE campaign_id = ? AND customer_id = ?
              AND opened_at IS NULL
        """, (datetime.now().isoformat(), campaign_id, customer_id))

        return True

    def record_email_click(
        self,
        campaign_id: int,
        customer_id: int
    ) -> bool:
        """Record email click event"""
        self.db.execute("""
            UPDATE campaign_sends
            SET clicked_at = ?
            WHERE campaign_id = ? AND customer_id = ?
        """, (datetime.now().isoformat(), campaign_id, customer_id))

        return True

    # ========================================================================
    # SMS CAMPAIGNS
    # ========================================================================

    def create_sms_campaign(
        self,
        campaign_name: str,
        sms_content: str,
        segment_id: Optional[int] = None,
        send_date: Optional[datetime] = None,
        include_opt_out: bool = True
    ) -> int:
        """
        Create SMS campaign

        Args:
            campaign_name: Campaign name
            sms_content: SMS message (160 chars recommended)
            segment_id: Target customer segment
            send_date: When to send
            include_opt_out: Include opt-out instructions

        Returns:
            Campaign ID
        """
        original_length = len(sms_content)

        if include_opt_out:
            sms_content += " Reply STOP to opt out."

        result = self.db.execute("""
            INSERT INTO sms_campaigns (
                campaign_name, sms_content, segment_id,
                send_date, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            campaign_name,
            sms_content,
            segment_id,
            send_date.isoformat() if send_date else None,
            datetime.now().isoformat(),
            'SCHEDULED' if send_date else 'DRAFT'
        ))

        campaign_id = result[0]['id']

        print(f"[OK] Created SMS campaign: {campaign_name}")
        print(f"     Message length: {len(sms_content)} chars")
        if original_length > 160:
            print(f"     Warning: Message exceeds 160 chars (may be split)")

        return campaign_id

    def get_sms_campaign(self, campaign_id: int) -> Optional[Dict]:
        """Get SMS campaign details"""
        result = self.db.execute(
            "SELECT * FROM sms_campaigns WHERE id = ?",
            (campaign_id,)
        )

        return dict(result[0]) if result else None

    def send_sms_campaign(self, campaign_id: int) -> Dict:
        """Send SMS campaign"""
        campaign = self.get_sms_campaign(campaign_id)

        if not campaign:
            raise ValueError(f"SMS Campaign {campaign_id} not found")

        # Get recipients
        customers = []
        if campaign['segment_id']:
            customers = self.get_segment_customers(campaign['segment_id'])

        sent_count = 0

        for customer in customers:
            # In production, send via SMS service (Twilio, etc.)
            sent_count += 1

        # Update campaign
        self.db.execute("""
            UPDATE sms_campaigns
            SET status = 'ACTIVE',
                sent_at = ?,
                sent_count = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            sent_count,
            datetime.now().isoformat(),
            campaign_id
        ))

        print(f"[OK] SMS campaign sent to {sent_count} recipients")

        return {
            'campaign_id': campaign_id,
            'sent_count': sent_count
        }

    # ========================================================================
    # AUTOMATED SEQUENCES (DRIP CAMPAIGNS)
    # ========================================================================

    def create_automated_sequence(
        self,
        sequence_name: str,
        trigger_type: str,
        trigger_criteria: Dict,
        sequence_steps: List[Dict],
        description: Optional[str] = None
    ) -> int:
        """
        Create automated marketing sequence

        Args:
            sequence_name: Sequence name
            trigger_type: When to trigger (JOB_COMPLETED, DAYS_SINCE_SERVICE, etc.)
            trigger_criteria: Trigger conditions
            sequence_steps: List of automated steps
            description: Sequence description

        Returns:
            Sequence ID
        """
        result = self.db.execute("""
            INSERT INTO automated_sequences (
                sequence_name, trigger_type, trigger_criteria,
                description, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            sequence_name,
            trigger_type,
            json.dumps(trigger_criteria),
            description,
            datetime.now().isoformat(),
            'ACTIVE'
        ))

        sequence_id = result[0]['id']

        # Create sequence steps
        for step in sequence_steps:
            self.db.execute("""
                INSERT INTO sequence_steps (
                    sequence_id, step_number, delay_days,
                    action_type, subject, content,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                sequence_id,
                step['step_number'],
                step['delay_days'],
                step['action_type'],
                step.get('subject'),
                step.get('content'),
                datetime.now().isoformat()
            ))

        print(f"[OK] Created automated sequence: {sequence_name}")
        print(f"     Trigger: {trigger_type}")
        print(f"     Steps: {len(sequence_steps)}")

        return sequence_id

    def get_sequence(self, sequence_id: int) -> Optional[Dict]:
        """Get sequence with steps"""
        result = self.db.execute(
            "SELECT * FROM automated_sequences WHERE id = ?",
            (sequence_id,)
        )

        if not result:
            return None

        sequence = dict(result[0])
        if sequence.get('trigger_criteria'):
            sequence['trigger_criteria'] = json.loads(sequence['trigger_criteria'])

        # Get steps
        steps = self.db.execute("""
            SELECT * FROM sequence_steps
            WHERE sequence_id = ?
            ORDER BY step_number
        """, (sequence_id,))

        sequence['steps'] = [dict(s) for s in steps]

        return sequence

    def trigger_sequence(
        self,
        sequence_id: int,
        customer_id: int,
        trigger_data: Optional[Dict] = None
    ) -> int:
        """
        Trigger automated sequence for customer

        Args:
            sequence_id: Sequence ID
            customer_id: Customer ID
            trigger_data: Additional trigger data

        Returns:
            Sequence instance ID
        """
        result = self.db.execute("""
            INSERT INTO sequence_instances (
                sequence_id, customer_id,
                triggered_at, trigger_data,
                current_step, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            sequence_id,
            customer_id,
            datetime.now().isoformat(),
            json.dumps(trigger_data) if trigger_data else None,
            0,
            'ACTIVE'
        ))

        instance_id = result[0]['id']

        print(f"[OK] Triggered sequence for customer {customer_id}")
        print(f"     Sequence ID: {sequence_id}")

        return instance_id

    def get_sequence_instance(self, instance_id: int) -> Optional[Dict]:
        """Get sequence instance details"""
        result = self.db.execute(
            "SELECT * FROM sequence_instances WHERE id = ?",
            (instance_id,)
        )

        if not result:
            return None

        instance = dict(result[0])
        if instance.get('trigger_data'):
            instance['trigger_data'] = json.loads(instance['trigger_data'])

        return instance

    def process_sequence_steps(self) -> Dict:
        """
        Process pending sequence steps

        Called by scheduled task to send pending messages

        Returns:
            Processing results
        """
        # Get active sequence instances
        instances = self.db.execute("""
            SELECT * FROM sequence_instances
            WHERE status = 'ACTIVE'
        """)

        processed = 0
        sent = 0
        completed = 0

        for instance in instances:
            instance = dict(instance)

            # Get next step
            next_step = self.db.execute("""
                SELECT * FROM sequence_steps
                WHERE sequence_id = ?
                  AND step_number > ?
                ORDER BY step_number
                LIMIT 1
            """, (instance['sequence_id'], instance['current_step']))

            if not next_step:
                # Sequence complete
                self.db.execute("""
                    UPDATE sequence_instances
                    SET status = 'COMPLETED',
                        completed_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), instance['id']))
                completed += 1
                continue

            next_step = dict(next_step[0])

            # Check if it's time to send
            triggered_at = datetime.fromisoformat(instance['triggered_at'])
            days_since_trigger = (datetime.now() - triggered_at).days

            if days_since_trigger >= next_step['delay_days']:
                # Send message (in production, actually send)
                self.db.execute("""
                    UPDATE sequence_instances
                    SET current_step = ?,
                        last_sent_at = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (
                    next_step['step_number'],
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    instance['id']
                ))

                sent += 1

            processed += 1

        return {
            'instances_processed': processed,
            'messages_sent': sent,
            'sequences_completed': completed
        }

    # ========================================================================
    # SEASONAL PROMOTIONS
    # ========================================================================

    def create_promotion(
        self,
        promotion_name: str,
        promotion_type: str,
        discount_type: str,
        discount_value: float,
        start_date: date,
        end_date: date,
        promo_code: Optional[str] = None,
        min_purchase: Optional[float] = None,
        max_uses: Optional[int] = None,
        description: Optional[str] = None
    ) -> int:
        """
        Create seasonal promotion

        Args:
            promotion_name: Promotion name
            promotion_type: SEASONAL, FLASH_SALE, REFERRAL, etc.
            discount_type: PERCENTAGE, FIXED_AMOUNT, FREE_SERVICE
            discount_value: Discount value
            start_date: Promotion start date
            end_date: Promotion end date
            promo_code: Promo code (optional)
            min_purchase: Minimum purchase required
            max_uses: Maximum number of uses
            description: Promotion description

        Returns:
            Promotion ID
        """
        result = self.db.execute("""
            INSERT INTO promotions (
                promotion_name, promotion_type,
                discount_type, discount_value,
                start_date, end_date,
                promo_code, min_purchase, max_uses,
                description, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            promotion_name,
            promotion_type,
            discount_type,
            discount_value,
            start_date.isoformat(),
            end_date.isoformat(),
            promo_code,
            min_purchase,
            max_uses,
            description,
            datetime.now().isoformat(),
            'ACTIVE'
        ))

        promo_id = result[0]['id']

        print(f"[OK] Created promotion: {promotion_name}")
        if discount_type == 'PERCENTAGE':
            print(f"     Discount: {discount_value}% off")
        else:
            print(f"     Discount: ${discount_value:.2f} off")
        print(f"     Valid: {start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}")
        if promo_code:
            print(f"     Code: {promo_code}")

        return promo_id

    def get_promotion(self, promo_id: int) -> Optional[Dict]:
        """Get promotion details"""
        result = self.db.execute(
            "SELECT * FROM promotions WHERE id = ?",
            (promo_id,)
        )

        return dict(result[0]) if result else None

    def get_promotion_by_code(self, promo_code: str) -> Optional[Dict]:
        """Get promotion by promo code"""
        result = self.db.execute(
            "SELECT * FROM promotions WHERE promo_code = ?",
            (promo_code,)
        )

        return dict(result[0]) if result else None

    def apply_promotion(
        self,
        promo_code: str,
        invoice_total: float,
        customer_id: Optional[int] = None,
        invoice_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Apply promotion to invoice

        Returns discount details if valid
        """
        promotion = self.db.execute("""
            SELECT * FROM promotions
            WHERE promo_code = ?
              AND status = 'ACTIVE'
              AND DATE('now') BETWEEN start_date AND end_date
        """, (promo_code,))

        if not promotion:
            return None

        promotion = dict(promotion[0])

        # Check minimum purchase
        if promotion['min_purchase'] and invoice_total < promotion['min_purchase']:
            return None

        # Check usage limit
        if promotion['max_uses']:
            if promotion['uses_count'] >= promotion['max_uses']:
                return None

        # Calculate discount
        if promotion['discount_type'] == 'PERCENTAGE':
            discount_amount = invoice_total * (promotion['discount_value'] / 100)
        else:
            discount_amount = min(promotion['discount_value'], invoice_total)

        # Record the use
        if customer_id or invoice_id:
            self.db.execute("""
                INSERT INTO promotion_uses (
                    promotion_id, customer_id, invoice_id,
                    discount_amount, used_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                promotion['id'],
                customer_id,
                invoice_id,
                discount_amount,
                datetime.now().isoformat()
            ))

            # Update uses count
            self.db.execute("""
                UPDATE promotions
                SET uses_count = uses_count + 1
                WHERE id = ?
            """, (promotion['id'],))

        return {
            'promotion_id': promotion['id'],
            'promotion_name': promotion['promotion_name'],
            'promo_code': promo_code,
            'discount_type': promotion['discount_type'],
            'discount_value': promotion['discount_value'],
            'discount_amount': discount_amount,
            'final_total': invoice_total - discount_amount
        }

    def get_active_promotions(self) -> List[Dict]:
        """Get all active promotions"""
        results = self.db.execute("""
            SELECT * FROM promotions
            WHERE status = 'ACTIVE'
              AND DATE('now') BETWEEN start_date AND end_date
            ORDER BY end_date
        """)

        return [dict(r) for r in results]

    # ========================================================================
    # REFERRAL PROGRAM
    # ========================================================================

    def create_referral(
        self,
        referrer_customer_id: int,
        referred_customer_id: int,
        referral_source: str = 'DIRECT'
    ) -> int:
        """
        Track customer referral

        Args:
            referrer_customer_id: Customer who made referral
            referred_customer_id: New customer
            referral_source: How referral was made

        Returns:
            Referral ID
        """
        result = self.db.execute("""
            INSERT INTO referrals (
                referrer_customer_id, referred_customer_id,
                referral_source, created_at, status
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            referrer_customer_id,
            referred_customer_id,
            referral_source,
            datetime.now().isoformat(),
            'PENDING'
        ))

        referral_id = result[0]['id']

        print(f"[OK] Referral created")
        print(f"     Referrer: Customer #{referrer_customer_id}")
        print(f"     Referred: Customer #{referred_customer_id}")

        return referral_id

    def get_referral(self, referral_id: int) -> Optional[Dict]:
        """Get referral details"""
        result = self.db.execute(
            "SELECT * FROM referrals WHERE id = ?",
            (referral_id,)
        )

        return dict(result[0]) if result else None

    def complete_referral(
        self,
        referral_id: int,
        referrer_reward_type: str = 'CREDIT',
        referrer_reward_value: float = 50.00,
        referred_reward_type: str = 'DISCOUNT',
        referred_reward_value: float = 25.00
    ) -> bool:
        """
        Complete referral and issue rewards

        Called when referred customer completes first job
        """
        self.db.execute("""
            UPDATE referrals
            SET status = 'COMPLETED',
                completed_at = ?,
                referrer_reward_type = ?,
                referrer_reward_value = ?,
                referred_reward_type = ?,
                referred_reward_value = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            referrer_reward_type,
            referrer_reward_value,
            referred_reward_type,
            referred_reward_value,
            referral_id
        ))

        print(f"[OK] Referral completed!")
        print(f"     Referrer reward: ${referrer_reward_value:.2f} {referrer_reward_type}")
        print(f"     Referred reward: ${referred_reward_value:.2f} {referred_reward_type}")

        return True

    def get_customer_referrals(
        self,
        customer_id: int
    ) -> Dict:
        """Get customer's referral summary"""
        # Get referrals made
        referrals_made = self.db.execute("""
            SELECT * FROM referrals
            WHERE referrer_customer_id = ?
        """, (customer_id,))

        # Calculate totals
        total_referrals = len(referrals_made)
        completed_referrals = sum(
            1 for r in referrals_made if r['status'] == 'COMPLETED'
        )
        total_rewards = sum(
            r['referrer_reward_value'] or 0
            for r in referrals_made
            if r['status'] == 'COMPLETED'
        )

        return {
            'customer_id': customer_id,
            'total_referrals': total_referrals,
            'completed_referrals': completed_referrals,
            'pending_referrals': total_referrals - completed_referrals,
            'total_rewards_earned': total_rewards,
            'referrals': [dict(r) for r in referrals_made]
        }

    # ========================================================================
    # A/B TESTING
    # ========================================================================

    def create_ab_test(
        self,
        campaign_id: int,
        variants: List[Dict]
    ) -> List[int]:
        """
        Create A/B test variants for campaign

        Args:
            campaign_id: Campaign to test
            variants: List of variant configurations

        Returns:
            List of variant IDs
        """
        variant_ids = []

        for variant in variants:
            result = self.db.execute("""
                INSERT INTO ab_test_variants (
                    campaign_id, variant_name,
                    subject, content,
                    created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                campaign_id,
                variant['variant_name'],
                variant.get('subject'),
                variant.get('content'),
                datetime.now().isoformat()
            ))

            variant_ids.append(result[0]['id'])

        print(f"[OK] Created {len(variants)} A/B test variants")
        for v in variants:
            print(f"     - {v['variant_name']}")

        return variant_ids

    def get_ab_test_results(self, campaign_id: int) -> Dict:
        """Get A/B test results for campaign"""
        variants = self.db.execute("""
            SELECT * FROM ab_test_variants
            WHERE campaign_id = ?
        """, (campaign_id,))

        results = []
        winner = None
        best_rate = 0

        for variant in variants:
            variant = dict(variant)

            # Calculate rates
            sent = variant['sent_count'] or 1
            open_rate = (variant['open_count'] / sent) * 100 if sent > 0 else 0
            click_rate = (variant['click_count'] / sent) * 100 if sent > 0 else 0

            result = {
                'variant_id': variant['id'],
                'variant_name': variant['variant_name'],
                'sent_count': variant['sent_count'],
                'open_count': variant['open_count'],
                'click_count': variant['click_count'],
                'open_rate': round(open_rate, 2),
                'click_rate': round(click_rate, 2)
            }

            results.append(result)

            # Determine winner
            if open_rate > best_rate:
                best_rate = open_rate
                winner = variant['variant_name']

        return {
            'campaign_id': campaign_id,
            'variants': results,
            'winner': winner,
            'winning_metric': 'open_rate',
            'best_rate': round(best_rate, 2)
        }

    # ========================================================================
    # CAMPAIGN ANALYTICS
    # ========================================================================

    def get_campaign_analytics(
        self,
        campaign_id: int,
        campaign_type: str = 'EMAIL'
    ) -> Dict:
        """
        Get campaign performance analytics

        Returns comprehensive metrics
        """
        if campaign_type == 'EMAIL':
            campaign = self.get_campaign(campaign_id)

            if not campaign:
                return {}

            # Get send stats
            sends = self.db.execute("""
                SELECT
                    COUNT(*) as total_sent,
                    SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                    SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) as clicked,
                    SUM(bounced) as bounced,
                    SUM(unsubscribed) as unsubscribed
                FROM campaign_sends
                WHERE campaign_id = ?
            """, (campaign_id,))

            stats = dict(sends[0]) if sends else {
                'total_sent': 0,
                'opened': 0,
                'clicked': 0,
                'bounced': 0,
                'unsubscribed': 0
            }

            total_sent = stats['total_sent'] or 0
            opened = stats['opened'] or 0
            clicked = stats['clicked'] or 0
            bounced = stats['bounced'] or 0
            unsubscribed = stats['unsubscribed'] or 0

            analytics = {
                'campaign_id': campaign_id,
                'campaign_name': campaign['campaign_name'],
                'campaign_type': 'EMAIL',
                'status': campaign['status'],
                'sent_at': campaign.get('sent_at'),
                'metrics': {
                    'sent': total_sent,
                    'delivered': total_sent - bounced,
                    'opened': opened,
                    'clicked': clicked,
                    'bounced': bounced,
                    'unsubscribed': unsubscribed
                },
                'rates': {
                    'delivery_rate': round(((total_sent - bounced) / total_sent * 100), 2) if total_sent > 0 else 0,
                    'open_rate': round((opened / total_sent * 100), 2) if total_sent > 0 else 0,
                    'click_rate': round((clicked / total_sent * 100), 2) if total_sent > 0 else 0,
                    'click_to_open_rate': round((clicked / opened * 100), 2) if opened > 0 else 0,
                    'bounce_rate': round((bounced / total_sent * 100), 2) if total_sent > 0 else 0,
                    'unsubscribe_rate': round((unsubscribed / total_sent * 100), 2) if total_sent > 0 else 0
                }
            }

            return analytics

        return {}

    def get_marketing_roi(
        self,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        Calculate marketing ROI for period

        Returns ROI metrics
        """
        # Get campaigns in period
        campaigns = self.db.execute("""
            SELECT * FROM email_campaigns
            WHERE created_at BETWEEN ? AND ?
        """, (start_date.isoformat(), end_date.isoformat()))

        # Calculate costs (simplified - would include actual costs)
        campaign_cost = len(campaigns) * 50.00  # Example fixed cost per campaign

        # Get conversions/revenue attributed to campaigns
        # In production, would track actual conversions
        total_sent = sum(c['sent_count'] or 0 for c in campaigns)
        estimated_conversions = int(total_sent * 0.02)  # 2% conversion rate
        avg_order_value = 500.00
        attributed_revenue = estimated_conversions * avg_order_value

        roi = ((attributed_revenue - campaign_cost) / campaign_cost * 100) if campaign_cost > 0 else 0

        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'campaigns': {
                'total_campaigns': len(campaigns),
                'total_sent': total_sent
            },
            'costs': {
                'campaign_costs': campaign_cost,
                'total_marketing_cost': campaign_cost
            },
            'revenue': {
                'attributed_revenue': attributed_revenue,
                'conversion_count': estimated_conversions,
                'avg_order_value': avg_order_value
            },
            'roi': {
                'roi_percent': round(roi, 2),
                'revenue_per_dollar': round(attributed_revenue / campaign_cost, 2) if campaign_cost > 0 else 0
            }
        }

    def get_marketing_dashboard(self) -> Dict:
        """Get marketing dashboard overview"""
        # Active campaigns
        active_campaigns = self.db.execute("""
            SELECT COUNT(*) as count FROM email_campaigns
            WHERE status = 'ACTIVE'
        """)[0]['count']

        # Active sequences
        active_sequences = self.db.execute("""
            SELECT COUNT(*) as count FROM sequence_instances
            WHERE status = 'ACTIVE'
        """)[0]['count']

        # Active promotions
        active_promos = self.db.execute("""
            SELECT COUNT(*) as count FROM promotions
            WHERE status = 'ACTIVE'
              AND DATE('now') BETWEEN start_date AND end_date
        """)[0]['count']

        # Pending referrals
        pending_referrals = self.db.execute("""
            SELECT COUNT(*) as count FROM referrals
            WHERE status = 'PENDING'
        """)[0]['count']

        # Total segments
        segments = self.db.execute("""
            SELECT COUNT(*) as count FROM customer_segments
            WHERE status = 'ACTIVE'
        """)[0]['count']

        return {
            'active_email_campaigns': active_campaigns,
            'active_sequences': active_sequences,
            'active_promotions': active_promos,
            'pending_referrals': pending_referrals,
            'customer_segments': segments
        }
