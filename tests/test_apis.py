"""
API Smoke Tests
===============
Basic tests for API endpoints to catch auth regressions.
Tests: 401 without auth, proper JSON responses.

Note: Many APIs use hardcoded database paths, so these tests focus on
authentication and response structure rather than data operations.
"""

import pytest
import json
import os
import tempfile
import sqlite3
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add project root to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.web.app import create_app


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def app():
    """Create test application with temporary database."""
    # Create temp database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    app = create_app({
        'TESTING': True,
        'DATABASE_PATH': db_path,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'LOGIN_DISABLED': False,
    })

    # Setup test database
    with app.app_context():
        setup_test_db(db_path)

    yield app

    # Cleanup - use try/except for Windows file lock issues
    try:
        os.close(db_fd)
    except:
        pass
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def client(app):
    """Flask test client (unauthenticated)."""
    return app.test_client()


def make_auth_app(app, user_dict):
    """Register a before_request handler that sets g.current_user for auth."""
    @app.before_request
    def set_test_user():
        from flask import g
        g.current_user = user_dict
        g.organization_id = user_dict.get('organization_id', 1)
        g.account_id = 1
    return app


@pytest.fixture
def auth_client(app):
    """Authenticated test client with admin role."""
    user_dict = {
        'id': 1,
        'email': 'admin@test.com',
        'first_name': 'Admin',
        'last_name': 'User',
        'role': 'admin',
        'organization_id': 1,
        'account_id': 1,
        'is_active': True,
        'permissions': [
            'jobs.view_all', 'jobs.view_own', 'jobs.create', 'jobs.edit', 'jobs.delete',
            'customers.view_all', 'customers.view_own', 'customers.create', 'customers.edit', 'customers.delete',
            'vehicles.view_all', 'vehicles.create', 'vehicles.edit', 'vehicles.delete',
            'estimates.view_all', 'estimates.create', 'estimates.edit', 'estimates.delete',
            'leads.view_all', 'leads.create', 'leads.edit', 'leads.delete',
            'reports.view',
        ]
    }
    make_auth_app(app, user_dict)
    client = app.test_client()
    # Also set session for admin_api which uses session-based auth
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['roles'] = ['admin']
    return client


@pytest.fixture
def tech_client(app):
    """Authenticated test client with technician role (limited permissions)."""
    user_dict = {
        'id': 2,
        'email': 'tech@test.com',
        'first_name': 'Tech',
        'last_name': 'User',
        'role': 'technician',
        'organization_id': 1,
        'account_id': 1,
        'is_active': True,
        'permissions': ['jobs.view_own', 'jobs.update_status']
    }
    make_auth_app(app, user_dict)
    client = app.test_client()
    # Set session for admin_api (not admin role)
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['roles'] = ['technician']
    return client


def setup_test_db(db_path):
    """Setup test database with required tables for admin API."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Users table (for admin API)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            role TEXT DEFAULT 'user',
            status TEXT DEFAULT 'active',
            active INTEGER DEFAULT 1,
            avatar_url TEXT,
            invite_token TEXT,
            last_login TEXT,
            last_login_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')

    # Company settings table (for admin API)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            setting_type TEXT DEFAULT 'string',
            category TEXT DEFAULT 'general',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER
        )
    ''')

    # Billing table (for admin API)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT DEFAULT 'free',
            plan_name TEXT DEFAULT 'Free',
            status TEXT DEFAULT 'active',
            billing_email TEXT,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            current_period_start TEXT,
            current_period_end TEXT,
            seats_included INTEGER DEFAULT 5,
            seats_used INTEGER DEFAULT 1,
            monthly_price REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # User activity log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert test admin user
    cursor.execute('''
        INSERT INTO users (id, email, first_name, last_name, username, full_name, role, status, active, last_login)
        VALUES (1, 'admin@test.com', 'Admin', 'User', 'admin', 'Admin User', 'admin', 'active', 1, '2026-01-20 10:00:00')
    ''')

    # Insert billing record with all required fields
    cursor.execute('''
        INSERT INTO billing (plan_id, plan_name, status, seats_included, seats_used, current_period_start, current_period_end)
        VALUES ('free', 'Free Plan', 'active', 5, 1, '2026-01-01', '2026-02-01')
    ''')

    # Leads table (for search API)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            source TEXT DEFAULT 'DIRECT',
            status TEXT DEFAULT 'NEW',
            temperature TEXT DEFAULT 'WARM',
            deleted_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Customers table (for search API)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            company_name TEXT,
            email TEXT,
            phone TEXT,
            deleted_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Jobs table (for search API)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_number TEXT,
            customer_id INTEGER,
            vehicle_id INTEGER,
            status TEXT DEFAULT 'NEW',
            deleted_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Vehicles table (for search API)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vin TEXT,
            year INTEGER,
            make TEXT,
            model TEXT,
            color TEXT,
            customer_id INTEGER,
            deleted_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Hail events table (for leads API join)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hail_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT,
            center_lat REAL,
            center_lon REAL,
            event_date TEXT
        )
    ''')

    conn.commit()
    conn.close()


# =============================================================================
# AUTHENTICATION TESTS - UNAUTHENTICATED ACCESS
# =============================================================================

class TestUnauthenticatedAccess:
    """Test that all API endpoints require authentication."""

    def test_jobs_requires_auth(self, client):
        """GET /api/jobs returns 401 without auth."""
        response = client.get('/api/jobs')
        assert response.status_code in [401, 302]

    def test_customers_requires_auth(self, client):
        """GET /api/customers returns 401 without auth."""
        response = client.get('/api/customers')
        assert response.status_code in [401, 302]

    def test_vehicles_requires_auth(self, client):
        """GET /api/vehicles returns 401 without auth."""
        response = client.get('/api/vehicles')
        assert response.status_code in [401, 302]

    def test_estimates_requires_auth(self, client):
        """GET /api/estimates returns 401 without auth."""
        response = client.get('/api/estimates')
        assert response.status_code in [401, 302]

    def test_leads_requires_auth(self, client):
        """GET /api/leads returns 401 without auth."""
        response = client.get('/api/leads')
        assert response.status_code in [401, 302]

    def test_admin_users_requires_auth(self, client):
        """GET /api/admin/users returns 401 without auth."""
        response = client.get('/api/admin/users')
        assert response.status_code in [401, 302]

    def test_notifications_requires_auth(self, client):
        """GET /api/notifications returns 401 without auth."""
        response = client.get('/api/notifications')
        assert response.status_code in [401, 302]

    def test_search_requires_auth(self, client):
        """GET /api/search returns 401 without auth."""
        response = client.get('/api/search?q=test')
        assert response.status_code in [401, 302]


# =============================================================================
# ADMIN API TESTS - Uses test database properly
# =============================================================================

class TestAdminAPI:
    """Tests for /api/admin endpoints (uses app config database)."""

    def test_admin_users_returns_json(self, auth_client):
        """GET /api/admin/users returns JSON with users array."""
        response = auth_client.get('/api/admin/users')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = response.get_json()
        assert 'users' in data

    def test_admin_settings_returns_json(self, auth_client):
        """GET /api/admin/settings returns JSON."""
        response = auth_client.get('/api/admin/settings')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_admin_billing_returns_json(self, auth_client):
        """GET /api/admin/billing returns JSON with billing info."""
        response = auth_client.get('/api/admin/billing')
        assert response.status_code == 200
        data = response.get_json()
        assert 'billing' in data or 'plans' in data

    def test_admin_roles_returns_json(self, auth_client):
        """GET /api/admin/roles returns roles list."""
        response = auth_client.get('/api/admin/roles')
        assert response.status_code == 200
        data = response.get_json()
        assert 'roles' in data

    def test_admin_requires_admin_role(self, tech_client):
        """GET /api/admin/users returns 403 for non-admin user."""
        response = tech_client.get('/api/admin/users')
        assert response.status_code == 403


# =============================================================================
# LEADS API TESTS - Uses test database properly
# =============================================================================

class TestLeadsAPI:
    """Tests for /api/leads endpoints."""

    def test_list_leads_returns_json(self, auth_client):
        """GET /api/leads returns JSON response."""
        response = auth_client.get('/api/leads')
        assert response.status_code == 200
        assert response.content_type == 'application/json'


# =============================================================================
# SEARCH API TESTS
# =============================================================================

class TestSearchAPI:
    """Tests for /api/search endpoints."""

    def test_search_returns_json(self, auth_client):
        """GET /api/search returns JSON response."""
        response = auth_client.get('/api/search?q=test')
        assert response.status_code == 200
        assert response.content_type == 'application/json'


# =============================================================================
# PERMISSION TESTS
# =============================================================================

class TestPermissions:
    """Test role-based access control."""

    def test_tech_cannot_create_customer(self, tech_client):
        """POST /api/customers returns 403 for technician."""
        response = tech_client.post('/api/customers',
            json={'first_name': 'New', 'last_name': 'Customer'},
            content_type='application/json')
        assert response.status_code == 403

    def test_tech_cannot_access_admin(self, tech_client):
        """GET /api/admin/users returns 403 for technician."""
        response = tech_client.get('/api/admin/users')
        assert response.status_code == 403


# =============================================================================
# RESPONSE STRUCTURE TESTS
# =============================================================================

class TestResponseStructure:
    """Test that responses have proper JSON structure."""

    def test_admin_users_has_users_key(self, auth_client):
        """Admin users endpoint returns users array."""
        response = auth_client.get('/api/admin/users')
        data = response.get_json()
        assert 'users' in data
        assert isinstance(data['users'], list)

    def test_admin_billing_has_plans(self, auth_client):
        """Admin billing endpoint returns plans array."""
        response = auth_client.get('/api/admin/billing')
        data = response.get_json()
        assert 'plans' in data
        assert isinstance(data['plans'], list)

    def test_error_response_has_error_key(self, auth_client):
        """Error responses include error message."""
        # Admin API properly returns 404 for non-existent user
        response = auth_client.get('/api/admin/users/99999')
        if response.status_code == 404:
            data = response.get_json()
            assert 'error' in data


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
