"""
Digital Flyer Manager
Create and send custom digital marketing flyers

FEATURES:
- Company flyer upload
- Personalized referral links
- Track flyer views/clicks
- A/B testing
- Campaign analytics
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from src.crm.models.database import Database
import json
import secrets
import string


class DigitalFlyerManager:
    """
    Manage digital marketing flyers

    Custom flyers with referral tracking
    """

    def __init__(self, db_path: str = "data/pdr_crm.db"):
        """Initialize flyer manager"""
        if isinstance(db_path, str):
            self.db = Database(db_path)
        else:
            self.db = db_path
        self._init_tables()

    def _init_tables(self):
        """Initialize required database tables"""

        # Digital flyers table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS digital_flyers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flyer_name TEXT NOT NULL,
                flyer_html TEXT,
                flyer_image_url TEXT,
                flyer_type TEXT DEFAULT 'STANDARD',
                campaign_id INTEGER,
                created_at TEXT,
                updated_at TEXT,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)

        # Personalized flyers table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS personalized_flyers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                flyer_id INTEGER,
                flyer_url TEXT UNIQUE,
                referral_link TEXT,
                generated_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (flyer_id) REFERENCES digital_flyers(id)
            )
        """)

        # Flyer views table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS flyer_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                flyer_id INTEGER,
                personalized_flyer_id INTEGER,
                viewer_ip TEXT,
                user_agent TEXT,
                viewed_at TEXT
            )
        """)

        # Flyer campaigns table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS flyer_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_name TEXT NOT NULL,
                campaign_type TEXT,
                start_date TEXT,
                end_date TEXT,
                target_audience TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'DRAFT'
            )
        """)

        # A/B test variants table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS flyer_ab_variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flyer_id INTEGER,
                variant_name TEXT,
                variant_html TEXT,
                variant_image_url TEXT,
                weight INTEGER DEFAULT 50,
                created_at TEXT,
                FOREIGN KEY (flyer_id) REFERENCES digital_flyers(id)
            )
        """)

    # ========================================================================
    # FLYER MANAGEMENT
    # ========================================================================

    def upload_company_flyer(
        self,
        flyer_name: str,
        flyer_html: str,
        flyer_image_url: Optional[str] = None,
        flyer_type: str = 'STANDARD',
        campaign_id: Optional[int] = None
    ) -> int:
        """
        Upload company digital flyer template

        Args:
            flyer_name: Flyer identifier
            flyer_html: HTML content of flyer
            flyer_image_url: URL to flyer image
            flyer_type: STANDARD, SEASONAL, PROMOTIONAL, EVENT

        Returns:
            Flyer ID
        """

        result = self.db.execute("""
            INSERT INTO digital_flyers (
                flyer_name, flyer_html, flyer_image_url,
                flyer_type, campaign_id, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            flyer_name,
            flyer_html,
            flyer_image_url,
            flyer_type,
            campaign_id,
            datetime.now().isoformat(),
            'ACTIVE'
        ))

        flyer_id = result[0]['id']

        print(f"Digital Flyer Uploaded")
        print(f"   ID: {flyer_id}")
        print(f"   Name: {flyer_name}")
        print(f"   Type: {flyer_type}")

        return flyer_id

    def get_flyer(self, flyer_id: int) -> Optional[Dict]:
        """Get flyer by ID"""

        result = self.db.execute(
            "SELECT * FROM digital_flyers WHERE id = ?",
            (flyer_id,)
        )

        return dict(result[0]) if result else None

    def get_active_flyers(
        self,
        flyer_type: Optional[str] = None
    ) -> List[Dict]:
        """Get all active flyers"""

        if flyer_type:
            results = self.db.execute("""
                SELECT * FROM digital_flyers
                WHERE status = 'ACTIVE' AND flyer_type = ?
                ORDER BY created_at DESC
            """, (flyer_type,))
        else:
            results = self.db.execute("""
                SELECT * FROM digital_flyers
                WHERE status = 'ACTIVE'
                ORDER BY created_at DESC
            """)

        return [dict(r) for r in results]

    def update_flyer(
        self,
        flyer_id: int,
        flyer_html: Optional[str] = None,
        flyer_image_url: Optional[str] = None,
        status: Optional[str] = None
    ):
        """Update flyer content"""

        updates = []
        params = []

        if flyer_html:
            updates.append("flyer_html = ?")
            params.append(flyer_html)

        if flyer_image_url:
            updates.append("flyer_image_url = ?")
            params.append(flyer_image_url)

        if status:
            updates.append("status = ?")
            params.append(status)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(flyer_id)

        self.db.execute(f"""
            UPDATE digital_flyers
            SET {', '.join(updates)}
            WHERE id = ?
        """, tuple(params))

    def delete_flyer(self, flyer_id: int):
        """Soft delete flyer"""

        self.db.execute("""
            UPDATE digital_flyers
            SET status = 'DELETED', updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), flyer_id))

    # ========================================================================
    # PERSONALIZED FLYERS
    # ========================================================================

    def generate_personalized_flyer(
        self,
        customer_id: int,
        flyer_id: int
    ) -> Dict:
        """
        Generate personalized flyer for customer

        Includes customer's unique referral link
        """

        customer = self.db.execute(
            "SELECT * FROM customers WHERE id = ?",
            (customer_id,)
        )

        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        customer = customer[0]

        flyer = self.db.execute(
            "SELECT * FROM digital_flyers WHERE id = ?",
            (flyer_id,)
        )

        if not flyer:
            raise ValueError(f"Flyer {flyer_id} not found")

        flyer = flyer[0]

        # Generate unique referral link
        referral_link = f"https://portal.pdrcrm.com/refer/{customer_id}"
        booking_link = f"https://portal.pdrcrm.com/book?ref={customer_id}"

        # Generate unique flyer URL
        flyer_token = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(12))
        flyer_url = f"https://flyers.pdrcrm.com/{flyer_token}"

        # Personalize flyer HTML
        personalized_html = flyer['flyer_html']
        if personalized_html:
            personalized_html = personalized_html.replace(
                '{CUSTOMER_NAME}', customer['first_name']
            ).replace(
                '{CUSTOMER_FULL_NAME}', f"{customer['first_name']} {customer['last_name']}"
            ).replace(
                '{REFERRAL_LINK}', referral_link
            ).replace(
                '{BOOKING_LINK}', booking_link
            ).replace(
                '{FLYER_URL}', flyer_url
            )

        # Track flyer generation
        self.db.execute("""
            INSERT INTO personalized_flyers (
                customer_id, flyer_id, flyer_url,
                referral_link, generated_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            customer_id,
            flyer_id,
            flyer_url,
            referral_link,
            datetime.now().isoformat()
        ))

        print(f"Personalized Flyer Generated")
        print(f"   Customer: {customer['first_name']} {customer['last_name']}")
        print(f"   Flyer URL: {flyer_url}")

        return {
            'flyer_url': flyer_url,
            'referral_link': referral_link,
            'booking_link': booking_link,
            'flyer_html': personalized_html,
            'flyer_image_url': flyer.get('flyer_image_url'),
            'customer_name': customer['first_name']
        }

    def get_personalized_flyer(
        self,
        flyer_url: str
    ) -> Optional[Dict]:
        """Get personalized flyer by URL"""

        result = self.db.execute("""
            SELECT pf.*, df.flyer_html, df.flyer_image_url, df.flyer_name,
                   c.first_name, c.last_name
            FROM personalized_flyers pf
            JOIN digital_flyers df ON df.id = pf.flyer_id
            JOIN customers c ON c.id = pf.customer_id
            WHERE pf.flyer_url = ?
        """, (flyer_url,))

        if not result:
            return None

        data = dict(result[0])

        # Personalize on retrieval
        if data.get('flyer_html'):
            data['flyer_html'] = data['flyer_html'].replace(
                '{CUSTOMER_NAME}', data['first_name']
            ).replace(
                '{REFERRAL_LINK}', data['referral_link']
            )

        return data

    def get_customer_flyers(
        self,
        customer_id: int
    ) -> List[Dict]:
        """Get all personalized flyers for customer"""

        results = self.db.execute("""
            SELECT pf.*, df.flyer_name, df.flyer_type
            FROM personalized_flyers pf
            JOIN digital_flyers df ON df.id = pf.flyer_id
            WHERE pf.customer_id = ?
            ORDER BY pf.generated_at DESC
        """, (customer_id,))

        return [dict(r) for r in results]

    # ========================================================================
    # VIEW TRACKING
    # ========================================================================

    def track_flyer_view(
        self,
        customer_id: int,
        flyer_id: int,
        viewer_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        personalized_flyer_id: Optional[int] = None
    ):
        """Track when someone views the flyer"""

        self.db.execute("""
            INSERT INTO flyer_views (
                customer_id, flyer_id, personalized_flyer_id,
                viewer_ip, user_agent, viewed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            flyer_id,
            personalized_flyer_id,
            viewer_ip,
            user_agent,
            datetime.now().isoformat()
        ))

    def get_flyer_analytics(
        self,
        customer_id: int
    ) -> Dict:
        """Get analytics for customer's shared flyers"""

        # Get total views
        views = self.db.execute("""
            SELECT COUNT(*) as view_count
            FROM flyer_views
            WHERE customer_id = ?
        """, (customer_id,))

        # Get referral link clicks (from portal manager tables)
        clicks = self.db.execute("""
            SELECT COUNT(*) as click_count
            FROM referral_link_clicks
            WHERE referrer_customer_id = ?
        """, (customer_id,))

        # Get referrals generated
        referrals = self.db.execute("""
            SELECT COUNT(*) as referral_count
            FROM customer_referrals
            WHERE referrer_customer_id = ?
        """, (customer_id,))

        total_views = views[0]['view_count'] if views else 0
        total_clicks = clicks[0]['click_count'] if clicks else 0
        total_referrals = referrals[0]['referral_count'] if referrals else 0

        # Calculate conversion rates
        click_rate = (total_clicks / total_views * 100) if total_views > 0 else 0
        conversion_rate = (total_referrals / total_clicks * 100) if total_clicks > 0 else 0

        return {
            'total_views': total_views,
            'total_clicks': total_clicks,
            'total_referrals': total_referrals,
            'click_rate': round(click_rate, 2),
            'conversion_rate': round(conversion_rate, 2)
        }

    def get_flyer_view_history(
        self,
        flyer_id: int,
        days: int = 30
    ) -> List[Dict]:
        """Get view history for a flyer"""

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        results = self.db.execute("""
            SELECT DATE(viewed_at) as view_date, COUNT(*) as views
            FROM flyer_views
            WHERE flyer_id = ? AND viewed_at >= ?
            GROUP BY DATE(viewed_at)
            ORDER BY view_date
        """, (flyer_id, cutoff_date))

        return [dict(r) for r in results]

    # ========================================================================
    # CAMPAIGNS
    # ========================================================================

    def create_campaign(
        self,
        campaign_name: str,
        campaign_type: str = 'GENERAL',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        target_audience: Optional[str] = None
    ) -> int:
        """Create a marketing campaign"""

        result = self.db.execute("""
            INSERT INTO flyer_campaigns (
                campaign_name, campaign_type, start_date,
                end_date, target_audience, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            campaign_name,
            campaign_type,
            start_date,
            end_date,
            target_audience,
            datetime.now().isoformat(),
            'DRAFT'
        ))

        campaign_id = result[0]['id']

        print(f"Campaign Created")
        print(f"   ID: {campaign_id}")
        print(f"   Name: {campaign_name}")

        return campaign_id

    def get_campaign_analytics(
        self,
        campaign_id: int
    ) -> Dict:
        """Get analytics for a campaign"""

        # Get all flyers in campaign
        flyers = self.db.execute("""
            SELECT * FROM digital_flyers
            WHERE campaign_id = ?
        """, (campaign_id,))

        flyer_ids = [f['id'] for f in flyers]

        if not flyer_ids:
            return {
                'campaign_id': campaign_id,
                'flyers': 0,
                'total_views': 0,
                'unique_viewers': 0
            }

        # Get view statistics
        placeholders = ','.join('?' * len(flyer_ids))

        views = self.db.execute(f"""
            SELECT COUNT(*) as total_views,
                   COUNT(DISTINCT viewer_ip) as unique_viewers
            FROM flyer_views
            WHERE flyer_id IN ({placeholders})
        """, tuple(flyer_ids))

        return {
            'campaign_id': campaign_id,
            'flyers': len(flyers),
            'total_views': views[0]['total_views'] if views else 0,
            'unique_viewers': views[0]['unique_viewers'] if views else 0
        }

    # ========================================================================
    # A/B TESTING
    # ========================================================================

    def create_ab_variant(
        self,
        flyer_id: int,
        variant_name: str,
        variant_html: str,
        variant_image_url: Optional[str] = None,
        weight: int = 50
    ) -> int:
        """Create an A/B test variant for a flyer"""

        result = self.db.execute("""
            INSERT INTO flyer_ab_variants (
                flyer_id, variant_name, variant_html,
                variant_image_url, weight, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            flyer_id,
            variant_name,
            variant_html,
            variant_image_url,
            weight,
            datetime.now().isoformat()
        ))

        variant_id = result[0]['id']

        print(f"A/B Variant Created")
        print(f"   Flyer ID: {flyer_id}")
        print(f"   Variant: {variant_name}")
        print(f"   Weight: {weight}%")

        return variant_id

    def get_ab_variant(self, flyer_id: int) -> Optional[Dict]:
        """Get a random A/B variant based on weights"""

        import random

        variants = self.db.execute("""
            SELECT * FROM flyer_ab_variants
            WHERE flyer_id = ?
        """, (flyer_id,))

        if not variants:
            return None

        # Weight-based selection
        total_weight = sum(v['weight'] for v in variants)
        random_value = random.randint(1, total_weight)

        cumulative = 0
        for variant in variants:
            cumulative += variant['weight']
            if random_value <= cumulative:
                return dict(variant)

        return dict(variants[0])

    def get_ab_test_results(
        self,
        flyer_id: int
    ) -> Dict:
        """Get A/B test results for a flyer"""

        variants = self.db.execute("""
            SELECT * FROM flyer_ab_variants
            WHERE flyer_id = ?
        """, (flyer_id,))

        results = {
            'flyer_id': flyer_id,
            'variants': []
        }

        for variant in variants:
            # Get views for this variant
            views = self.db.execute("""
                SELECT COUNT(*) as views
                FROM flyer_views fv
                JOIN personalized_flyers pf ON pf.id = fv.personalized_flyer_id
                WHERE pf.flyer_id = ?
            """, (flyer_id,))

            results['variants'].append({
                'variant_id': variant['id'],
                'variant_name': variant['variant_name'],
                'weight': variant['weight'],
                'views': views[0]['views'] if views else 0
            })

        return results

    # ========================================================================
    # FLYER TEMPLATES
    # ========================================================================

    def get_default_flyer_template(self) -> str:
        """Get default flyer HTML template"""

        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDR Solutions - Hail Damage Repair</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 40px 20px;
            text-align: center;
        }
        .logo {
            font-size: 32px;
            font-weight: bold;
            color: #00d4ff;
            margin-bottom: 20px;
        }
        h1 {
            font-size: 28px;
            margin-bottom: 15px;
        }
        .highlight {
            color: #00d4ff;
        }
        .offer-box {
            background: rgba(0, 212, 255, 0.1);
            border: 2px solid #00d4ff;
            border-radius: 12px;
            padding: 25px;
            margin: 30px 0;
        }
        .offer-amount {
            font-size: 48px;
            font-weight: bold;
            color: #00d4ff;
        }
        .btn {
            display: inline-block;
            background: linear-gradient(135deg, #00d4ff, #0099cc);
            color: white;
            text-decoration: none;
            padding: 15px 40px;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            margin: 10px;
        }
        .referral-section {
            margin-top: 40px;
            padding: 25px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
        }
        .referral-link {
            background: #1a1a2e;
            padding: 15px;
            border-radius: 8px;
            word-break: break-all;
            font-family: monospace;
            margin: 15px 0;
        }
        .features {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            margin: 30px 0;
        }
        .feature {
            flex: 1;
            min-width: 150px;
            padding: 15px;
        }
        .feature-icon {
            font-size: 36px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">PDR Solutions</div>

        <h1>Hey {CUSTOMER_NAME}!</h1>
        <p>Thanks for trusting us with your hail damage repair.</p>

        <div class="offer-box">
            <p>Share with friends & earn</p>
            <div class="offer-amount">$50</div>
            <p>for every completed referral!</p>
        </div>

        <div class="features">
            <div class="feature">
                <div class="feature-icon">🚗</div>
                <div>Free Estimates</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🛡️</div>
                <div>Insurance Approved</div>
            </div>
            <div class="feature">
                <div class="feature-icon">⭐</div>
                <div>5-Star Service</div>
            </div>
        </div>

        <a href="{BOOKING_LINK}" class="btn">Book Free Estimate</a>

        <div class="referral-section">
            <h3>Your Personal Referral Link</h3>
            <div class="referral-link">{REFERRAL_LINK}</div>
            <p>Share this link and earn $50 for each friend who completes their repair!</p>
        </div>

        <p style="margin-top: 40px; opacity: 0.7;">
            PDR Solutions | Professional Paintless Dent Repair<br>
            (555) 123-4567 | info@pdrsolutions.com
        </p>
    </div>
</body>
</html>
        """.strip()

    def create_default_flyer(self) -> int:
        """Create a default flyer using the template"""

        return self.upload_company_flyer(
            flyer_name='Default Referral Flyer',
            flyer_html=self.get_default_flyer_template(),
            flyer_type='STANDARD'
        )
