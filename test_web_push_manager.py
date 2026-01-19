"""
Tests for WebPushManager - Browser Push Notification Support
"""

import os
import tempfile
import pytest
from datetime import datetime


class TestWebPushManager:
    """Test suite for WebPushManager"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_push.db")

        # Create schema
        from src.crm.models.schema import DatabaseSchema
        DatabaseSchema.create_all_tables(self.db_path)

        # Create a test customer
        from src.crm.models.database import Database
        db = Database(self.db_path)
        self.customer_id = db.insert('customers', {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'phone': '555-1234',
            'created_at': datetime.now().isoformat()
        })

        yield

        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_web_push_manager_init(self):
        """Test WebPushManager initialization"""
        from src.crm.managers.web_push_manager import WebPushManager

        manager = WebPushManager(self.db_path)

        assert manager is not None
        assert manager.db_path == self.db_path

    def test_ensure_tables_created(self):
        """Test that push subscription tables are created"""
        from src.crm.managers.web_push_manager import WebPushManager
        from src.crm.models.database import Database

        manager = WebPushManager(self.db_path)
        db = Database(self.db_path)

        # Check tables exist
        tables = db.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('push_subscriptions', 'vapid_keys', 'push_notification_log')
        """)

        table_names = [t['name'] for t in tables]
        assert 'push_subscriptions' in table_names
        assert 'vapid_keys' in table_names
        assert 'push_notification_log' in table_names

    def test_save_subscription(self):
        """Test saving a push subscription"""
        from src.crm.managers.web_push_manager import WebPushManager

        manager = WebPushManager(self.db_path)

        subscription_info = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/test-endpoint-123',
            'keys': {
                'p256dh': 'BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM',
                'auth': 'tBHItJI5svbpez7KI4CCXg'
            }
        }

        sub_id = manager.save_subscription(
            customer_id=self.customer_id,
            subscription_info=subscription_info,
            user_agent='Mozilla/5.0 Test Browser'
        )

        assert sub_id is not None
        assert sub_id > 0

    def test_save_subscription_duplicate_updates(self):
        """Test that duplicate subscriptions are updated, not duplicated"""
        from src.crm.managers.web_push_manager import WebPushManager

        manager = WebPushManager(self.db_path)

        subscription_info = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/unique-endpoint-456',
            'keys': {
                'p256dh': 'BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM',
                'auth': 'tBHItJI5svbpez7KI4CCXg'
            }
        }

        # Save twice with same endpoint
        sub_id1 = manager.save_subscription(self.customer_id, subscription_info)
        sub_id2 = manager.save_subscription(self.customer_id, subscription_info)

        # Should return same ID (updated, not duplicated)
        assert sub_id1 == sub_id2

    def test_get_customer_subscriptions(self):
        """Test retrieving customer subscriptions"""
        from src.crm.managers.web_push_manager import WebPushManager

        manager = WebPushManager(self.db_path)

        # Save a subscription
        subscription_info = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/get-test-789',
            'keys': {
                'p256dh': 'test-p256dh-key',
                'auth': 'test-auth-key'
            }
        }
        manager.save_subscription(self.customer_id, subscription_info)

        # Get subscriptions
        subscriptions = manager.get_customer_subscriptions(self.customer_id)

        assert len(subscriptions) >= 1
        assert subscriptions[0]['endpoint'] == 'https://fcm.googleapis.com/fcm/send/get-test-789'
        assert subscriptions[0]['is_active'] == 1

    def test_remove_subscription(self):
        """Test removing/deactivating a subscription"""
        from src.crm.managers.web_push_manager import WebPushManager

        manager = WebPushManager(self.db_path)

        endpoint = 'https://fcm.googleapis.com/fcm/send/remove-test-111'
        subscription_info = {
            'endpoint': endpoint,
            'keys': {
                'p256dh': 'test-p256dh-key',
                'auth': 'test-auth-key'
            }
        }
        manager.save_subscription(self.customer_id, subscription_info)

        # Remove subscription
        result = manager.remove_subscription(endpoint)
        assert result is True

        # Verify it's deactivated
        subscriptions = manager.get_customer_subscriptions(self.customer_id)
        active_endpoints = [s['endpoint'] for s in subscriptions]
        assert endpoint not in active_endpoints

    def test_get_vapid_public_key(self):
        """Test getting VAPID public key"""
        from src.crm.managers.web_push_manager import WebPushManager

        manager = WebPushManager(self.db_path)

        # May be None if not configured, but method should work
        public_key = manager.get_vapid_public_key()

        # Just verify the method works (key may or may not exist)
        assert public_key is None or isinstance(public_key, str)

    def test_get_subscription_stats(self):
        """Test getting subscription statistics"""
        from src.crm.managers.web_push_manager import WebPushManager

        manager = WebPushManager(self.db_path)

        # Save a subscription
        subscription_info = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/stats-test-222',
            'keys': {
                'p256dh': 'test-key',
                'auth': 'test-auth'
            }
        }
        manager.save_subscription(self.customer_id, subscription_info)

        # Get stats for customer
        stats = manager.get_subscription_stats(self.customer_id)

        assert 'total_subscriptions' in stats
        assert 'active_subscriptions' in stats
        assert stats['active_subscriptions'] >= 1

    def test_get_subscription_stats_all(self):
        """Test getting global subscription statistics"""
        from src.crm.managers.web_push_manager import WebPushManager

        manager = WebPushManager(self.db_path)

        # Get global stats
        stats = manager.get_subscription_stats()

        assert 'total_subscriptions' in stats
        assert 'active_subscriptions' in stats

    def test_send_notification_no_subscriptions(self):
        """Test sending notification when no subscriptions exist"""
        from src.crm.managers.web_push_manager import WebPushManager
        from src.crm.models.database import Database

        manager = WebPushManager(self.db_path)

        # Create a customer with no subscriptions
        db = Database(self.db_path)
        new_customer_id = db.insert('customers', {
            'first_name': 'No',
            'last_name': 'Subscriptions',
            'email': 'nosub@example.com',
            'created_at': datetime.now().isoformat()
        })

        result = manager.send_notification(
            customer_id=new_customer_id,
            title='Test',
            body='Test message'
        )

        assert result['sent'] == 0
        assert 'No active subscriptions' in result.get('error', '')

    def test_send_notification_no_vapid_keys(self):
        """Test sending notification when VAPID keys not configured"""
        from src.crm.managers.web_push_manager import WebPushManager

        manager = WebPushManager(self.db_path)

        # Clear VAPID keys
        manager.vapid_private_key = None
        manager.vapid_public_key = None

        # Save a subscription first
        subscription_info = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/vapid-test',
            'keys': {
                'p256dh': 'test-key',
                'auth': 'test-auth'
            }
        }
        manager.save_subscription(self.customer_id, subscription_info)

        result = manager.send_notification(
            customer_id=self.customer_id,
            title='Test',
            body='Test message'
        )

        assert result['sent'] == 0
        assert 'VAPID keys not configured' in result.get('error', '')


def test_web_push_manager_basic():
    """Basic test that WebPushManager can be imported and instantiated"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_basic.db")

    try:
        from src.crm.models.schema import DatabaseSchema
        DatabaseSchema.create_all_tables(db_path)

        from src.crm.managers.web_push_manager import WebPushManager
        manager = WebPushManager(db_path)

        assert manager is not None
        print("[OK] WebPushManager instantiated successfully")

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
