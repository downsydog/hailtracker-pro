"""
Tests for NotificationTemplateManager - Custom Message Templates
"""

import os
import tempfile
import pytest
from datetime import datetime


class TestNotificationTemplateManager:
    """Test suite for NotificationTemplateManager"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_templates.db")

        # Create schema
        from src.crm.models.schema import DatabaseSchema
        DatabaseSchema.create_all_tables(self.db_path)

        yield

        # Cleanup
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_template_manager_init(self):
        """Test NotificationTemplateManager initialization"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        assert manager is not None
        assert manager.db_path == self.db_path

    def test_ensure_tables_created(self):
        """Test that template tables are created"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager
        from src.crm.models.database import Database

        manager = NotificationTemplateManager(self.db_path)
        db = Database(self.db_path)

        # Check tables exist
        tables = db.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('notification_templates', 'template_usage_log')
        """)

        table_names = [t['name'] for t in tables]
        assert 'notification_templates' in table_names
        assert 'template_usage_log' in table_names

    def test_get_default_templates(self):
        """Test getting default templates"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)
        templates = manager.get_default_templates()

        assert 'JOB_DROPPED_OFF' in templates
        assert 'JOB_APPROVED' in templates
        assert 'JOB_READY_FOR_PICKUP' in templates
        assert 'JOB_COMPLETED' in templates

    def test_get_template_keys(self):
        """Test getting list of template keys"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)
        keys = manager.get_template_keys()

        assert len(keys) > 0
        assert 'JOB_DROPPED_OFF' in keys
        assert 'WELCOME' in keys

    def test_render_simple_template(self):
        """Test rendering a template with variables"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        result = manager.render('JOB_DROPPED_OFF', {
            'customer_name': 'John Smith',
            'vehicle': '2024 Tesla Model 3',
            'job_number': 'JOB-2024-001'
        })

        assert 'John Smith' in result['email_body']
        assert '2024 Tesla Model 3' in result['email_body']
        assert 'JOB-2024-001' in result['email_body']
        assert 'Vehicle Received' in result['title']

    def test_render_email(self):
        """Test rendering email template"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        result = manager.render_email('JOB_APPROVED', {
            'customer_name': 'Jane Doe',
            'vehicle': '2023 BMW X5',
            'job_number': 'JOB-2024-002',
            'approved_amount': '$1,500'
        })

        assert 'subject' in result
        assert 'body' in result
        assert 'Jane Doe' in result['body']
        assert '$1,500' in result['body']

    def test_render_sms(self):
        """Test rendering SMS template"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        result = manager.render_sms('JOB_READY_FOR_PICKUP', {
            'customer_name': 'Bob Wilson',
            'vehicle': '2022 Ford F-150',
            'job_number': 'JOB-2024-003',
            'location_name': 'Downtown Shop',
            'final_amount': '$800'
        })

        assert '2022 Ford F-150' in result
        assert 'JOB-2024-003' in result
        assert '$800' in result

    def test_render_push(self):
        """Test rendering push notification template"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        result = manager.render_push('JOB_IN_PROGRESS', {
            'vehicle': '2024 Honda Civic'
        })

        assert 'title' in result
        assert 'body' in result
        assert '2024 Honda Civic' in result['body']

    def test_render_in_app(self):
        """Test rendering in-app notification template"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        result = manager.render_in_app('JOB_COMPLETED', {
            'customer_name': 'Alice Brown',
            'vehicle': '2023 Toyota Camry',
            'job_number': 'JOB-2024-004',
            'completion_date': 'January 15, 2024',
            'review_url': 'https://example.com/review',
            'referral_url': 'https://example.com/refer'
        })

        assert 'title' in result
        assert 'message' in result

    def test_render_with_missing_variables(self):
        """Test rendering with missing variables (should replace with empty)"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        result = manager.render('JOB_DROPPED_OFF', {
            'customer_name': 'Test User'
            # Missing: vehicle, job_number
        })

        assert 'Test User' in result['email_body']
        # Missing variables should be replaced with empty strings
        assert '{{vehicle}}' not in result['email_body']

    def test_render_nonexistent_template(self):
        """Test rendering a template that doesn't exist"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        with pytest.raises(ValueError, match="Template not found"):
            manager.render('NONEXISTENT_TEMPLATE', {})

    def test_create_custom_template(self):
        """Test creating a custom template"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        template_id = manager.create_template(
            template_key='CUSTOM_PROMO',
            channel='email',
            body='Hello {{customer_name}}, check out our special offer!',
            title='Special Offer',
            subject='Limited Time Offer!',
            created_by='admin'
        )

        assert template_id > 0

    def test_list_templates(self):
        """Test listing templates"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        # Create a custom template
        manager.create_template(
            template_key='TEST_TEMPLATE',
            channel='sms',
            body='Test message for {{customer_name}}'
        )

        templates = manager.list_templates('TEST_TEMPLATE')
        assert len(templates) >= 1

    def test_deactivate_template(self):
        """Test deactivating a template"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager
        from src.crm.models.database import Database

        manager = NotificationTemplateManager(self.db_path)

        # Create a template
        template_id = manager.create_template(
            template_key='TO_DEACTIVATE',
            channel='push',
            body='Test push message'
        )

        # Deactivate it
        result = manager.deactivate_template(template_id)
        assert result is True

        # Verify it's deactivated
        db = Database(self.db_path)
        template = db.execute("""
            SELECT is_active FROM notification_templates WHERE id = ?
        """, (template_id,))

        assert template[0]['is_active'] == 0

    def test_template_versioning(self):
        """Test that templates support versioning"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        # Create version 1
        manager.create_template(
            template_key='VERSIONED_TEMPLATE',
            channel='email',
            body='Version 1 content'
        )

        # Create version 2
        manager.create_template(
            template_key='VERSIONED_TEMPLATE',
            channel='email',
            body='Version 2 content'
        )

        templates = manager.list_templates('VERSIONED_TEMPLATE')
        versions = [t['version'] for t in templates]

        assert 1 in versions
        assert 2 in versions

    def test_log_usage(self):
        """Test logging template usage"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        usage_id = manager.log_usage(
            template_key='JOB_APPROVED',
            channel='email',
            customer_id=1
        )

        assert usage_id > 0

    def test_log_open_and_click(self):
        """Test logging opens and clicks"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager
        from src.crm.models.database import Database

        manager = NotificationTemplateManager(self.db_path)

        # Log usage
        usage_id = manager.log_usage(
            template_key='JOB_READY_FOR_PICKUP',
            channel='email'
        )

        # Log open
        manager.log_open(usage_id)

        # Log click
        manager.log_click(usage_id)

        # Verify
        db = Database(self.db_path)
        log = db.execute("""
            SELECT opened, clicked FROM template_usage_log WHERE id = ?
        """, (usage_id,))

        assert log[0]['opened'] == 1
        assert log[0]['clicked'] == 1

    def test_get_template_stats(self):
        """Test getting template statistics"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        # Log some usage
        for i in range(5):
            usage_id = manager.log_usage('JOB_COMPLETED', 'email')
            if i < 3:
                manager.log_open(usage_id)
            if i < 1:
                manager.log_click(usage_id)

        stats = manager.get_template_stats('JOB_COMPLETED')

        assert stats['template_key'] == 'JOB_COMPLETED'
        assert 'email' in stats['by_channel']
        assert stats['by_channel']['email']['sent'] == 5
        assert stats['by_channel']['email']['opened'] == 3
        assert stats['by_channel']['email']['clicked'] == 1

    def test_default_variables_added(self):
        """Test that default variables are added automatically"""
        from src.crm.managers.notification_template_manager import NotificationTemplateManager

        manager = NotificationTemplateManager(self.db_path)

        # Use CUSTOM template which uses raw variables
        result = manager.render('WELCOME', {
            'customer_name': 'Test User',
            'username': 'testuser'
        })

        # Default variables like company_name should be filled in
        assert 'PDR Excellence' in result['email_body']


def test_notification_template_basic():
    """Basic test that NotificationTemplateManager can be imported and instantiated"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_basic.db")

    try:
        from src.crm.models.schema import DatabaseSchema
        DatabaseSchema.create_all_tables(db_path)

        from src.crm.managers.notification_template_manager import NotificationTemplateManager
        manager = NotificationTemplateManager(db_path)

        assert manager is not None
        assert len(manager.get_template_keys()) > 10
        print("[OK] NotificationTemplateManager instantiated successfully")
        print(f"[OK] Found {len(manager.get_template_keys())} default templates")

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
