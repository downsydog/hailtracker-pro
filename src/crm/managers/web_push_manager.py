"""
Web Push Notification Manager
Browser push notifications using the Web Push API

Supports VAPID authentication for secure push notifications.

USAGE:
    from src.crm.managers.web_push_manager import WebPushManager

    push_manager = WebPushManager(db_path)
    push_manager.send_notification(subscription_info, title, body)
"""

import os
import json
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime

# Try to import pywebpush - optional dependency
try:
    from pywebpush import webpush, WebPushException
    WEBPUSH_AVAILABLE = True
except ImportError:
    WEBPUSH_AVAILABLE = False
    print("[INFO] pywebpush not installed. Run: pip install pywebpush")


class WebPushManager:
    """
    Manage browser push notifications using Web Push API.

    Uses VAPID (Voluntary Application Server Identification) for authentication.
    """

    def __init__(self, db_path: str):
        """
        Initialize web push manager.

        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self._ensure_tables()

        # Load or generate VAPID keys
        self.vapid_private_key = os.environ.get('VAPID_PRIVATE_KEY')
        self.vapid_public_key = os.environ.get('VAPID_PUBLIC_KEY')
        self.vapid_claims = {
            "sub": os.environ.get('VAPID_CLAIM_EMAIL', 'mailto:admin@pdrexcellence.com')
        }

        # If no keys in environment, try to load from database
        if not self.vapid_private_key or not self.vapid_public_key:
            self._load_or_generate_vapid_keys()

    def _get_db(self):
        """Get database connection."""
        from src.crm.models.database import Database
        return Database(self.db_path)

    def _ensure_tables(self):
        """Ensure push subscription tables exist."""
        db = self._get_db()

        # Push subscriptions table
        db.execute("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                endpoint TEXT NOT NULL UNIQUE,
                p256dh_key TEXT NOT NULL,
                auth_key TEXT NOT NULL,
                user_agent TEXT,
                created_at TEXT,
                last_used_at TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # VAPID keys storage
        db.execute("""
            CREATE TABLE IF NOT EXISTS vapid_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_key TEXT NOT NULL,
                private_key TEXT NOT NULL,
                created_at TEXT
            )
        """)

        # Push notification log
        db.execute("""
            CREATE TABLE IF NOT EXISTS push_notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER,
                customer_id INTEGER,
                title TEXT,
                body TEXT,
                status TEXT,
                error_message TEXT,
                sent_at TEXT,
                FOREIGN KEY (subscription_id) REFERENCES push_subscriptions(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Index for faster lookups
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_push_subscriptions_customer
            ON push_subscriptions(customer_id)
        """)

    def _load_or_generate_vapid_keys(self):
        """Load VAPID keys from database or generate new ones."""
        db = self._get_db()

        # Try to load existing keys
        result = db.execute("SELECT * FROM vapid_keys ORDER BY id DESC LIMIT 1")

        if result:
            self.vapid_public_key = result[0]['public_key']
            self.vapid_private_key = result[0]['private_key']
            print("[OK] Loaded existing VAPID keys")
        else:
            # Generate new keys
            self._generate_vapid_keys()

    def _generate_vapid_keys(self):
        """Generate new VAPID key pair."""
        if not WEBPUSH_AVAILABLE:
            print("[WARN] Cannot generate VAPID keys - pywebpush not installed")
            return

        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization

            # Generate EC key pair
            private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
            public_key = private_key.public_key()

            # Serialize keys
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint
            )

            # URL-safe base64 encode
            self.vapid_private_key = base64.urlsafe_b64encode(private_bytes).decode('utf-8')
            self.vapid_public_key = base64.urlsafe_b64encode(public_bytes).decode('utf-8')

            # Store in database
            db = self._get_db()
            db.insert('vapid_keys', {
                'public_key': self.vapid_public_key,
                'private_key': self.vapid_private_key,
                'created_at': datetime.now().isoformat()
            })

            print("[OK] Generated new VAPID keys")

        except Exception as e:
            print(f"[ERROR] Failed to generate VAPID keys: {e}")

    def get_vapid_public_key(self) -> Optional[str]:
        """Get the VAPID public key for client-side subscription."""
        return self.vapid_public_key

    # ========================================================================
    # SUBSCRIPTION MANAGEMENT
    # ========================================================================

    def save_subscription(
        self,
        customer_id: int,
        subscription_info: Dict,
        user_agent: Optional[str] = None
    ) -> int:
        """
        Save a push subscription for a customer.

        Args:
            customer_id: Customer ID
            subscription_info: Push subscription object from browser
            user_agent: Browser user agent string

        Returns:
            Subscription ID
        """
        db = self._get_db()

        endpoint = subscription_info.get('endpoint')
        keys = subscription_info.get('keys', {})

        # Check if subscription already exists
        existing = db.execute("""
            SELECT id FROM push_subscriptions WHERE endpoint = ?
        """, (endpoint,))

        if existing:
            # Update existing subscription
            db.execute("""
                UPDATE push_subscriptions
                SET customer_id = ?, p256dh_key = ?, auth_key = ?,
                    user_agent = ?, last_used_at = ?, is_active = 1
                WHERE endpoint = ?
            """, (
                customer_id,
                keys.get('p256dh'),
                keys.get('auth'),
                user_agent,
                datetime.now().isoformat(),
                endpoint
            ))
            return existing[0]['id']
        else:
            # Create new subscription
            return db.insert('push_subscriptions', {
                'customer_id': customer_id,
                'endpoint': endpoint,
                'p256dh_key': keys.get('p256dh'),
                'auth_key': keys.get('auth'),
                'user_agent': user_agent,
                'created_at': datetime.now().isoformat(),
                'last_used_at': datetime.now().isoformat(),
                'is_active': 1
            })

    def remove_subscription(self, endpoint: str) -> bool:
        """Remove a push subscription by endpoint."""
        db = self._get_db()

        db.execute("""
            UPDATE push_subscriptions
            SET is_active = 0
            WHERE endpoint = ?
        """, (endpoint,))

        return True

    def get_customer_subscriptions(self, customer_id: int) -> List[Dict]:
        """Get all active push subscriptions for a customer."""
        db = self._get_db()

        return db.execute("""
            SELECT * FROM push_subscriptions
            WHERE customer_id = ? AND is_active = 1
        """, (customer_id,))

    # ========================================================================
    # SENDING NOTIFICATIONS
    # ========================================================================

    def send_notification(
        self,
        customer_id: int,
        title: str,
        body: str,
        icon: Optional[str] = None,
        badge: Optional[str] = None,
        url: Optional[str] = None,
        tag: Optional[str] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Send push notification to all customer's subscribed devices.

        Args:
            customer_id: Customer ID
            title: Notification title
            body: Notification body
            icon: URL to notification icon
            badge: URL to badge icon
            url: URL to open when notification is clicked
            tag: Notification tag (for grouping)
            data: Additional data to include

        Returns:
            Dict with success/failure counts
        """
        if not WEBPUSH_AVAILABLE:
            return {'sent': 0, 'failed': 0, 'error': 'pywebpush not installed'}

        if not self.vapid_private_key or not self.vapid_public_key:
            return {'sent': 0, 'failed': 0, 'error': 'VAPID keys not configured'}

        subscriptions = self.get_customer_subscriptions(customer_id)

        if not subscriptions:
            return {'sent': 0, 'failed': 0, 'error': 'No active subscriptions'}

        # Build notification payload
        payload = {
            'title': title,
            'body': body,
            'icon': icon or '/static/icons/icon-192x192.png',
            'badge': badge or '/static/icons/badge-72x72.png',
            'tag': tag or 'pdr-notification',
            'data': {
                'url': url or '/portal/',
                **(data or {})
            }
        }

        results = {'sent': 0, 'failed': 0, 'errors': []}
        db = self._get_db()

        for sub in subscriptions:
            try:
                subscription_info = {
                    'endpoint': sub['endpoint'],
                    'keys': {
                        'p256dh': sub['p256dh_key'],
                        'auth': sub['auth_key']
                    }
                }

                webpush(
                    subscription_info=subscription_info,
                    data=json.dumps(payload),
                    vapid_private_key=self.vapid_private_key,
                    vapid_claims=self.vapid_claims
                )

                results['sent'] += 1

                # Log success
                db.insert('push_notification_log', {
                    'subscription_id': sub['id'],
                    'customer_id': customer_id,
                    'title': title,
                    'body': body,
                    'status': 'SENT',
                    'sent_at': datetime.now().isoformat()
                })

                # Update last used
                db.execute("""
                    UPDATE push_subscriptions
                    SET last_used_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), sub['id']))

            except WebPushException as e:
                results['failed'] += 1
                results['errors'].append(str(e))

                # Log failure
                db.insert('push_notification_log', {
                    'subscription_id': sub['id'],
                    'customer_id': customer_id,
                    'title': title,
                    'body': body,
                    'status': 'FAILED',
                    'error_message': str(e),
                    'sent_at': datetime.now().isoformat()
                })

                # If subscription is no longer valid, deactivate it
                if e.response and e.response.status_code in [404, 410]:
                    db.execute("""
                        UPDATE push_subscriptions
                        SET is_active = 0
                        WHERE id = ?
                    """, (sub['id'],))

            except Exception as e:
                results['failed'] += 1
                results['errors'].append(str(e))

        return results

    def send_to_subscription(
        self,
        subscription_info: Dict,
        title: str,
        body: str,
        **kwargs
    ) -> bool:
        """Send notification to a specific subscription."""
        if not WEBPUSH_AVAILABLE:
            return False

        payload = {
            'title': title,
            'body': body,
            'icon': kwargs.get('icon', '/static/icons/icon-192x192.png'),
            'badge': kwargs.get('badge', '/static/icons/badge-72x72.png'),
            'tag': kwargs.get('tag', 'pdr-notification'),
            'data': kwargs.get('data', {})
        }

        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims
            )
            return True
        except Exception as e:
            print(f"[ERROR] Web push failed: {e}")
            return False

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_subscription_stats(self, customer_id: Optional[int] = None) -> Dict:
        """Get push notification statistics."""
        db = self._get_db()

        if customer_id:
            subs = db.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active
                FROM push_subscriptions
                WHERE customer_id = ?
            """, (customer_id,))
        else:
            subs = db.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active
                FROM push_subscriptions
            """)

        return {
            'total_subscriptions': subs[0]['total'] if subs else 0,
            'active_subscriptions': subs[0]['active'] if subs else 0
        }
