"""
Tests for SmsManager - Twilio SMS Notification Support
"""

import os
import tempfile
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


class TestSmsManager:
    """Test suite for SmsManager"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_sms.db")

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
            'phone': '555-123-4567',
            'created_at': datetime.now().isoformat()
        })

        yield

        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sms_manager_init(self):
        """Test SmsManager initialization"""
        from src.crm.managers.sms_manager import SmsManager

        manager = SmsManager(self.db_path)

        assert manager is not None
        assert manager.db_path == self.db_path

    def test_ensure_tables_created(self):
        """Test that SMS log table is created"""
        from src.crm.managers.sms_manager import SmsManager
        from src.crm.models.database import Database

        manager = SmsManager(self.db_path)
        db = Database(self.db_path)

        # Check table exists
        tables = db.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name = 'sms_log'
        """)

        assert len(tables) == 1
        assert tables[0]['name'] == 'sms_log'

    def test_is_configured_without_credentials(self):
        """Test is_configured returns False without Twilio credentials"""
        from src.crm.managers.sms_manager import SmsManager

        # Clear any existing env vars
        for var in ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER']:
            if var in os.environ:
                del os.environ[var]

        manager = SmsManager(self.db_path)
        assert manager.is_configured() is False

    def test_normalize_phone_us_10_digit(self):
        """Test phone normalization for US 10-digit numbers"""
        from src.crm.managers.sms_manager import SmsManager

        manager = SmsManager(self.db_path)

        # 10 digit US number
        assert manager._normalize_phone('5551234567') == '+15551234567'
        assert manager._normalize_phone('555-123-4567') == '+15551234567'
        assert manager._normalize_phone('(555) 123-4567') == '+15551234567'

    def test_normalize_phone_us_11_digit(self):
        """Test phone normalization for US 11-digit numbers"""
        from src.crm.managers.sms_manager import SmsManager

        manager = SmsManager(self.db_path)

        # 11 digit US number with country code
        assert manager._normalize_phone('15551234567') == '+15551234567'
        assert manager._normalize_phone('1-555-123-4567') == '+15551234567'

    def test_normalize_phone_with_plus(self):
        """Test phone normalization for numbers with + prefix"""
        from src.crm.managers.sms_manager import SmsManager

        manager = SmsManager(self.db_path)

        # Already has country code
        assert manager._normalize_phone('+15551234567') == '+15551234567'
        assert manager._normalize_phone('+44 20 7123 4567') == '+442071234567'

    def test_normalize_phone_invalid(self):
        """Test phone normalization for invalid numbers"""
        from src.crm.managers.sms_manager import SmsManager

        manager = SmsManager(self.db_path)

        # Invalid numbers
        assert manager._normalize_phone('') is None
        assert manager._normalize_phone(None) is None
        assert manager._normalize_phone('123') is None  # Too short

    def test_send_sms_not_configured(self):
        """Test send_sms when Twilio is not configured"""
        from src.crm.managers.sms_manager import SmsManager

        manager = SmsManager(self.db_path)
        manager.client = None  # Ensure not configured

        result = manager.send_sms('+15551234567', 'Test message')

        assert result['success'] is False
        assert 'not configured' in result['error'].lower()

    def test_send_sms_invalid_phone(self):
        """Test send_sms with invalid phone number"""
        from src.crm.managers.sms_manager import SmsManager

        manager = SmsManager(self.db_path)
        # Mock client as configured
        manager.client = Mock()

        result = manager.send_sms('123', 'Test message')  # Invalid number

        assert result['success'] is False
        assert 'invalid' in result['error'].lower()

    @patch('src.crm.managers.sms_manager.TwilioClient')
    def test_send_sms_success(self, mock_twilio_client):
        """Test successful SMS sending with mocked Twilio"""
        from src.crm.managers.sms_manager import SmsManager

        # Mock the Twilio response
        mock_message = Mock()
        mock_message.sid = 'SM123456789'
        mock_message.status = 'queued'
        mock_message.num_segments = 1

        mock_client_instance = Mock()
        mock_client_instance.messages.create.return_value = mock_message
        mock_twilio_client.return_value = mock_client_instance

        # Set environment variables
        os.environ['TWILIO_ACCOUNT_SID'] = 'test_sid'
        os.environ['TWILIO_AUTH_TOKEN'] = 'test_token'
        os.environ['TWILIO_FROM_NUMBER'] = '+15550001111'

        manager = SmsManager(self.db_path)
        manager.client = mock_client_instance

        result = manager.send_sms(
            to_number='+15551234567',
            message='Test message',
            customer_id=self.customer_id
        )

        assert result['success'] is True
        assert result['sent'] is True
        assert result['message_sid'] == 'SM123456789'

        # Cleanup
        del os.environ['TWILIO_ACCOUNT_SID']
        del os.environ['TWILIO_AUTH_TOKEN']
        del os.environ['TWILIO_FROM_NUMBER']

    def test_send_to_customer_not_found(self):
        """Test send_to_customer with non-existent customer"""
        from src.crm.managers.sms_manager import SmsManager

        manager = SmsManager(self.db_path)
        manager.client = Mock()

        result = manager.send_to_customer(
            customer_id=99999,  # Non-existent
            message='Test message'
        )

        assert result['success'] is False
        assert 'not found' in result['error'].lower()

    def test_send_to_customer_no_phone(self):
        """Test send_to_customer when customer has no phone"""
        from src.crm.managers.sms_manager import SmsManager
        from src.crm.models.database import Database

        db = Database(self.db_path)

        # Create customer without phone
        customer_id = db.insert('customers', {
            'first_name': 'No',
            'last_name': 'Phone',
            'email': 'nophone@example.com',
            'created_at': datetime.now().isoformat()
        })

        manager = SmsManager(self.db_path)
        manager.client = Mock()

        result = manager.send_to_customer(
            customer_id=customer_id,
            message='Test message'
        )

        assert result['success'] is False
        assert 'no phone' in result['error'].lower()

    def test_rate_limit_check(self):
        """Test rate limiting functionality"""
        from src.crm.managers.sms_manager import SmsManager
        from src.crm.models.database import Database

        manager = SmsManager(self.db_path)
        manager.max_messages_per_hour = 2

        db = Database(self.db_path)

        # Add some SMS log entries
        for i in range(3):
            db.insert('sms_log', {
                'to_number': '+15551234567',
                'message': f'Test message {i}',
                'status': 'SENT',
                'sent_at': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            })

        # Should be rate limited
        assert manager._check_rate_limit('+15551234567') is False

    def test_get_message_history(self):
        """Test retrieving message history"""
        from src.crm.managers.sms_manager import SmsManager
        from src.crm.models.database import Database

        manager = SmsManager(self.db_path)
        db = Database(self.db_path)

        # Add some SMS log entries
        db.insert('sms_log', {
            'customer_id': self.customer_id,
            'to_number': '+15551234567',
            'message': 'Test message 1',
            'status': 'SENT',
            'sent_at': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat()
        })

        history = manager.get_message_history(customer_id=self.customer_id)

        assert len(history) >= 1
        assert history[0]['message'] == 'Test message 1'

    def test_get_statistics(self):
        """Test getting SMS statistics"""
        from src.crm.managers.sms_manager import SmsManager
        from src.crm.models.database import Database

        manager = SmsManager(self.db_path)
        db = Database(self.db_path)

        # Add some SMS log entries
        db.insert('sms_log', {
            'customer_id': self.customer_id,
            'to_number': '+15551234567',
            'message': 'Test message',
            'status': 'DELIVERED',
            'segments': 1,
            'sent_at': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat()
        })

        stats = manager.get_statistics(days=30)

        assert 'total_sent' in stats
        assert 'delivered' in stats
        assert 'failed' in stats
        assert stats['total_sent'] >= 1


def test_sms_manager_basic():
    """Basic test that SmsManager can be imported and instantiated"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_basic.db")

    try:
        from src.crm.models.schema import DatabaseSchema
        DatabaseSchema.create_all_tables(db_path)

        from src.crm.managers.sms_manager import SmsManager
        manager = SmsManager(db_path)

        assert manager is not None
        print("[OK] SmsManager instantiated successfully")

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
