"""
Multi-Tenant Authentication Manager
Handles authentication, authorization, and tenant context for the RBAC system.

This replaces the simple auth system with a full multi-tenant implementation.
"""

import sqlite3
import bcrypt
import secrets
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import os


class SeatLimitExceeded(Exception):
    """Raised when trying to create a user but seat limit is reached"""
    pass


class AuthManager:
    """
    Handles authentication, authorization, and tenant context.

    Key features:
    - Account/Organization/User hierarchy
    - Role-based permissions
    - Session management
    - Seat limit enforcement
    - Kiosk device support
    - Audit logging
    """

    # Session duration
    SESSION_DURATION_HOURS = 24
    KIOSK_SESSION_DURATION_HOURS = 720  # 30 days

    # Lockout settings
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

    def __init__(self, db_path: str = 'data/hailtracker_crm.db'):
        self.db_path = db_path
        self._permission_cache = {}  # user_id -> [permissions]

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ========================================================================
    # ACCOUNT MANAGEMENT
    # ========================================================================

    def create_account(self, name: str, owner_email: str, owner_password: str,
                       plan: str = 'starter', **kwargs) -> Dict[str, int]:
        """
        Create a new account with default organization and owner user.

        Args:
            name: Company name (e.g., "ABC Dent Repair LLC")
            owner_email: Email for the owner user
            owner_password: Password for the owner user
            plan: Subscription plan (starter, professional, enterprise)
            **kwargs: Additional account fields (phone, address, city, state, zip)

        Returns:
            Dict with account_id, organization_id, user_id
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Generate slug from name
            slug = self._generate_slug(name)

            # Ensure slug is unique
            cursor.execute("SELECT COUNT(*) FROM accounts WHERE slug = ?", (slug,))
            if cursor.fetchone()[0] > 0:
                slug = f"{slug}-{secrets.token_hex(3)}"

            # Determine max seats based on plan
            seat_limits = {
                'starter': 5,
                'professional': 15,
                'enterprise': 50
            }
            max_seats = seat_limits.get(plan, 5)

            # Create account
            cursor.execute("""
                INSERT INTO accounts (name, slug, owner_email, phone, address, city, state, zip, plan, max_user_seats, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (
                name, slug, owner_email,
                kwargs.get('phone'), kwargs.get('address'), kwargs.get('city'),
                kwargs.get('state'), kwargs.get('zip'),
                plan, max_seats
            ))
            account_id = cursor.lastrowid

            # Create default organization
            cursor.execute("""
                INSERT INTO organizations (account_id, name, slug, address, city, state, zip, phone, email)
                VALUES (?, ?, 'main', ?, ?, ?, ?, ?, ?)
            """, (
                account_id, f"{name} - Main",
                kwargs.get('address'), kwargs.get('city'), kwargs.get('state'),
                kwargs.get('zip'), kwargs.get('phone'), owner_email
            ))
            organization_id = cursor.lastrowid

            # Get owner role ID
            cursor.execute("SELECT id FROM roles WHERE name = 'owner'")
            role_row = cursor.fetchone()
            if not role_row:
                raise ValueError("Owner role not found. Run seed_rbac.py first.")
            owner_role_id = role_row['id']

            # Hash password
            password_hash = bcrypt.hashpw(owner_password.encode('utf-8'), bcrypt.gensalt())

            # Create owner user
            cursor.execute("""
                INSERT INTO users_new (account_id, organization_id, role_id, email, password_hash, first_name, last_name, is_active, email_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1)
            """, (
                account_id, organization_id, owner_role_id, owner_email, password_hash.decode('utf-8'),
                kwargs.get('first_name', 'Account'), kwargs.get('last_name', 'Owner')
            ))
            user_id = cursor.lastrowid

            conn.commit()

            # Log the action
            self._log_audit(conn, organization_id, user_id, None, 'account.created', 'account', account_id,
                           {'name': name, 'plan': plan})

            return {
                'account_id': account_id,
                'organization_id': organization_id,
                'user_id': user_id
            }

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_account(self, account_id: int) -> Optional[Dict]:
        """Get account details"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_seat_usage(self, account_id: int) -> Dict[str, int]:
        """
        Get current seat usage for an account.

        Returns:
            Dict with max, used, available, at_limit
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                a.max_user_seats as max,
                COUNT(CASE WHEN r.counts_as_seat = 1 AND u.is_active = 1 THEN u.id END) as used
            FROM accounts a
            LEFT JOIN users_new u ON u.account_id = a.id
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE a.id = ?
            GROUP BY a.id
        """, (account_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            max_seats = row['max']
            used_seats = row['used']
            return {
                'max': max_seats,
                'used': used_seats,
                'available': max_seats - used_seats,
                'at_limit': used_seats >= max_seats
            }
        return {'max': 0, 'used': 0, 'available': 0, 'at_limit': True}

    def update_account(self, account_id: int, **updates) -> bool:
        """Update account fields"""
        allowed_fields = ['name', 'phone', 'address', 'city', 'state', 'zip', 'plan', 'max_user_seats', 'status']

        set_clauses = []
        values = []
        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                values.append(value)

        if not set_clauses:
            return False

        set_clauses.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(account_id)

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            UPDATE accounts SET {', '.join(set_clauses)}
            WHERE id = ?
        """, values)

        conn.commit()
        conn.close()
        return True

    # ========================================================================
    # USER MANAGEMENT
    # ========================================================================

    def create_user(self, account_id: int, organization_id: int, email: str,
                    password: str, role_name: str, **profile) -> int:
        """
        Create a user. Checks seat limits before creating.

        Args:
            account_id: Account the user belongs to
            organization_id: Organization (location) for the user
            email: User's email (unique)
            password: User's password (will be hashed)
            role_name: Role name (owner, admin, office, sales, tech, estimator, kiosk)
            **profile: Additional fields (first_name, last_name, phone, etc.)

        Returns:
            user_id

        Raises:
            SeatLimitExceeded: If account is at seat limit for this role type
            ValueError: If role not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Get role and check if it counts as a seat
            cursor.execute("SELECT id, counts_as_seat FROM roles WHERE name = ?", (role_name,))
            role_row = cursor.fetchone()
            if not role_row:
                raise ValueError(f"Role '{role_name}' not found")

            role_id = role_row['id']
            counts_as_seat = role_row['counts_as_seat']

            # Check seat limit if this role counts as a seat
            if counts_as_seat:
                seat_usage = self.get_seat_usage(account_id)
                if seat_usage['at_limit']:
                    raise SeatLimitExceeded(
                        f"Account has reached seat limit ({seat_usage['max']}). "
                        f"Upgrade plan or deactivate users to add more."
                    )

            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Create user
            cursor.execute("""
                INSERT INTO users_new (
                    account_id, organization_id, role_id, email, password_hash,
                    first_name, last_name, phone, job_title,
                    commission_rate, hourly_rate, hire_date,
                    is_active, email_verified, created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?)
            """, (
                account_id, organization_id, role_id, email, password_hash.decode('utf-8'),
                profile.get('first_name'), profile.get('last_name'),
                profile.get('phone'), profile.get('job_title'),
                profile.get('commission_rate', 0), profile.get('hourly_rate', 0),
                profile.get('hire_date'),
                profile.get('created_by')
            ))

            user_id = cursor.lastrowid
            conn.commit()

            # Log the action
            self._log_audit(conn, organization_id, profile.get('created_by'), None,
                           'user.created', 'user', user_id, {'email': email, 'role': role_name})

            # Clear permission cache
            self._permission_cache.pop(user_id, None)

            return user_id

        except sqlite3.IntegrityError as e:
            conn.rollback()
            if 'UNIQUE constraint failed' in str(e):
                raise ValueError(f"Email '{email}' is already in use")
            raise
        finally:
            conn.close()

    def authenticate(self, email: str, password: str,
                     ip_address: str = None, user_agent: str = None) -> Optional[Dict]:
        """
        Authenticate user, return user dict with role and permissions.

        Handles failed login tracking and lockout.

        Args:
            email: User's email
            password: User's password
            ip_address: Client IP (for logging)
            user_agent: Client user agent (for logging)

        Returns:
            User dict with role and permissions, or None if auth failed
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Get user
            cursor.execute("""
                SELECT u.*, r.name as role_name, r.display_name as role_display_name,
                       a.status as account_status, a.name as account_name,
                       o.name as organization_name
                FROM users_new u
                JOIN roles r ON u.role_id = r.id
                JOIN accounts a ON u.account_id = a.id
                JOIN organizations o ON u.organization_id = o.id
                WHERE u.email = ?
            """, (email,))

            user = cursor.fetchone()

            if not user:
                self._log_audit(conn, None, None, None, 'auth.failed',
                               details={'reason': 'user_not_found', 'email': email},
                               ip_address=ip_address)
                return None

            user_dict = dict(user)

            # Check if account is active
            if user_dict['account_status'] != 'active':
                self._log_audit(conn, user_dict['organization_id'], user_dict['id'], None,
                               'auth.failed', details={'reason': 'account_inactive'},
                               ip_address=ip_address)
                return None

            # Check if user is active
            if not user_dict['is_active']:
                self._log_audit(conn, user_dict['organization_id'], user_dict['id'], None,
                               'auth.failed', details={'reason': 'user_inactive'},
                               ip_address=ip_address)
                return None

            # Check if locked out
            if user_dict['locked_until']:
                locked_until = datetime.fromisoformat(user_dict['locked_until'])
                if datetime.now() < locked_until:
                    self._log_audit(conn, user_dict['organization_id'], user_dict['id'], None,
                                   'auth.failed', details={'reason': 'locked_out'},
                                   ip_address=ip_address)
                    return None
                # Lock expired, reset
                cursor.execute("""
                    UPDATE users_new SET locked_until = NULL, failed_login_attempts = 0
                    WHERE id = ?
                """, (user_dict['id'],))

            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user_dict['password_hash'].encode('utf-8')):
                # Increment failed attempts
                new_attempts = user_dict['failed_login_attempts'] + 1
                lock_time = None

                if new_attempts >= self.MAX_FAILED_ATTEMPTS:
                    lock_time = (datetime.now() + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)).isoformat()

                cursor.execute("""
                    UPDATE users_new SET failed_login_attempts = ?, locked_until = ?
                    WHERE id = ?
                """, (new_attempts, lock_time, user_dict['id']))
                conn.commit()

                self._log_audit(conn, user_dict['organization_id'], user_dict['id'], None,
                               'auth.failed', details={'reason': 'wrong_password', 'attempts': new_attempts},
                               ip_address=ip_address)
                return None

            # Successful login - update tracking
            cursor.execute("""
                UPDATE users_new SET
                    last_login_at = ?,
                    last_activity_at = ?,
                    failed_login_attempts = 0,
                    locked_until = NULL
                WHERE id = ?
            """, (datetime.now().isoformat(), datetime.now().isoformat(), user_dict['id']))
            conn.commit()

            # Load permissions
            permissions = self.get_user_permissions(user_dict['id'])

            # Log success
            self._log_audit(conn, user_dict['organization_id'], user_dict['id'], None,
                           'auth.success', ip_address=ip_address)

            # Remove sensitive data and add permissions
            del user_dict['password_hash']
            user_dict['permissions'] = permissions
            user_dict['role'] = user_dict['role_name']

            return user_dict

        finally:
            conn.close()

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user with role and org info"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT u.id, u.account_id, u.organization_id, u.role_id, u.email,
                   u.first_name, u.last_name, u.phone, u.avatar_path, u.job_title,
                   u.commission_rate, u.hourly_rate, u.hire_date,
                   u.is_active, u.email_verified, u.must_change_password,
                   u.last_login_at, u.last_activity_at, u.created_at,
                   r.name as role_name, r.display_name as role_display_name,
                   a.name as account_name, a.slug as account_slug,
                   o.name as organization_name
            FROM users_new u
            JOIN roles r ON u.role_id = r.id
            JOIN accounts a ON u.account_id = a.id
            JOIN organizations o ON u.organization_id = o.id
            WHERE u.id = ?
        """, (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            user_dict = dict(row)
            user_dict['role'] = user_dict['role_name']
            return user_dict
        return None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users_new WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self.get_user(row['id'])
        return None

    def get_user_permissions(self, user_id: int) -> List[str]:
        """Get list of permission names for user"""
        # Check cache first
        if user_id in self._permission_cache:
            return self._permission_cache[user_id]

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.name
            FROM users_new u
            JOIN role_permissions rp ON rp.role_id = u.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE u.id = ?
        """, (user_id,))

        permissions = [row['name'] for row in cursor.fetchall()]
        conn.close()

        # Cache the result
        self._permission_cache[user_id] = permissions
        return permissions

    def update_user(self, user_id: int, **updates) -> bool:
        """Update user profile"""
        allowed_fields = [
            'first_name', 'last_name', 'phone', 'avatar_path', 'job_title',
            'commission_rate', 'hourly_rate', 'hire_date', 'organization_id',
            'is_active', 'must_change_password'
        ]

        set_clauses = []
        values = []
        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                values.append(value)

        if not set_clauses:
            return False

        set_clauses.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(user_id)

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            UPDATE users_new SET {', '.join(set_clauses)}
            WHERE id = ?
        """, values)

        conn.commit()
        conn.close()

        # Clear permission cache
        self._permission_cache.pop(user_id, None)
        return True

    def change_password(self, user_id: int, new_password: str, old_password: str = None) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            new_password: New password
            old_password: Old password (required unless admin reset)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if old_password:
                # Verify old password
                cursor.execute("SELECT password_hash FROM users_new WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if not row:
                    return False
                if not bcrypt.checkpw(old_password.encode('utf-8'), row['password_hash'].encode('utf-8')):
                    return False

            # Hash new password
            new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

            cursor.execute("""
                UPDATE users_new SET password_hash = ?, must_change_password = 0, updated_at = ?
                WHERE id = ?
            """, (new_hash.decode('utf-8'), datetime.now().isoformat(), user_id))

            conn.commit()

            # Revoke all sessions (force re-login)
            self.revoke_all_sessions(user_id)

            return True
        finally:
            conn.close()

    def deactivate_user(self, user_id: int, admin_user_id: int = None) -> bool:
        """Soft delete - deactivate user, free up seat"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users_new SET is_active = 0, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), user_id))

        conn.commit()

        # Get user org for logging
        user = self.get_user(user_id)
        if user:
            self._log_audit(conn, user['organization_id'], admin_user_id, None,
                           'user.deactivated', 'user', user_id)

        # Revoke all sessions
        self.revoke_all_sessions(user_id)

        conn.close()

        # Clear permission cache
        self._permission_cache.pop(user_id, None)
        return True

    def reactivate_user(self, user_id: int, admin_user_id: int = None) -> bool:
        """Reactivate a deactivated user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check seat limit first
        user = self.get_user(user_id)
        if not user:
            conn.close()
            return False

        cursor.execute("SELECT counts_as_seat FROM roles WHERE id = ?", (user['role_id'],))
        role_row = cursor.fetchone()

        if role_row and role_row['counts_as_seat']:
            seat_usage = self.get_seat_usage(user['account_id'])
            if seat_usage['at_limit']:
                conn.close()
                raise SeatLimitExceeded("Cannot reactivate user - seat limit reached")

        cursor.execute("""
            UPDATE users_new SET is_active = 1, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), user_id))

        conn.commit()
        self._log_audit(conn, user['organization_id'], admin_user_id, None,
                       'user.reactivated', 'user', user_id)
        conn.close()
        return True

    def get_users_for_account(self, account_id: int, include_inactive: bool = False) -> List[Dict]:
        """Get all users in an account"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT u.id, u.email, u.first_name, u.last_name, u.phone,
                   u.is_active, u.last_login_at, u.created_at,
                   r.name as role_name, r.display_name as role_display_name,
                   o.name as organization_name
            FROM users_new u
            JOIN roles r ON u.role_id = r.id
            JOIN organizations o ON u.organization_id = o.id
            WHERE u.account_id = ?
        """

        if not include_inactive:
            query += " AND u.is_active = 1"

        query += " ORDER BY u.created_at DESC"

        cursor.execute(query, (account_id,))
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================

    def create_session(self, user_id: int = None, kiosk_id: int = None,
                       context: dict = None) -> str:
        """
        Create session, return session token.

        Args:
            user_id: User ID (mutually exclusive with kiosk_id)
            kiosk_id: Kiosk ID (mutually exclusive with user_id)
            context: Optional context (ip_address, user_agent, device_type)
        """
        if not user_id and not kiosk_id:
            raise ValueError("Either user_id or kiosk_id required")

        context = context or {}
        session_token = secrets.token_urlsafe(32)

        # Determine expiration
        if kiosk_id:
            duration = self.KIOSK_SESSION_DURATION_HOURS
        else:
            duration = self.SESSION_DURATION_HOURS

        expires_at = (datetime.now() + timedelta(hours=duration)).isoformat()

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO user_sessions (user_id, kiosk_id, session_token, ip_address, user_agent, device_type, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, kiosk_id, session_token,
            context.get('ip_address'), context.get('user_agent'), context.get('device_type'),
            expires_at
        ))

        conn.commit()
        conn.close()

        return session_token

    def validate_session(self, session_token: str) -> Optional[Dict]:
        """
        Validate token, return user/kiosk info or None.

        Returns:
            Dict with user_id OR kiosk_id, plus expires_at
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, kiosk_id, expires_at
            FROM user_sessions
            WHERE session_token = ?
              AND revoked_at IS NULL
              AND expires_at > ?
        """, (session_token, datetime.now().isoformat()))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'user_id': row['user_id'],
                'kiosk_id': row['kiosk_id'],
                'expires_at': row['expires_at']
            }
        return None

    def revoke_session(self, session_token: str) -> bool:
        """Logout - revoke session"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE user_sessions SET revoked_at = ?
            WHERE session_token = ?
        """, (datetime.now().isoformat(), session_token))

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected > 0

    def revoke_all_sessions(self, user_id: int) -> int:
        """Revoke all sessions for user (password change, etc.)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE user_sessions SET revoked_at = ?
            WHERE user_id = ? AND revoked_at IS NULL
        """, (datetime.now().isoformat(), user_id))

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from database"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM user_sessions
            WHERE expires_at < ? OR revoked_at IS NOT NULL
        """, (datetime.now().isoformat(),))

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected

    # ========================================================================
    # KIOSK MANAGEMENT
    # ========================================================================

    def create_kiosk_device(self, organization_id: int, name: str, **settings) -> Dict:
        """
        Create kiosk device, return {id, device_token}.

        Args:
            organization_id: Organization the kiosk belongs to
            name: Display name (e.g., "Lobby Tablet 1")
            **settings: Optional settings (auto_reset_seconds, welcome_message)
        """
        device_token = secrets.token_urlsafe(32)

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO kiosk_devices (organization_id, device_token, name, auto_reset_seconds, welcome_message)
            VALUES (?, ?, ?, ?, ?)
        """, (
            organization_id, device_token, name,
            settings.get('auto_reset_seconds', 30),
            settings.get('welcome_message')
        ))

        kiosk_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            'id': kiosk_id,
            'device_token': device_token,
            'name': name
        }

    def authenticate_kiosk(self, device_token: str, ip_address: str = None,
                           user_agent: str = None) -> Optional[Dict]:
        """Authenticate kiosk device"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT k.*, o.account_id, o.name as organization_name
            FROM kiosk_devices k
            JOIN organizations o ON k.organization_id = o.id
            WHERE k.device_token = ? AND k.is_active = 1
        """, (device_token,))

        row = cursor.fetchone()

        if row:
            # Update last seen
            cursor.execute("""
                UPDATE kiosk_devices SET last_seen_at = ?, last_ip = ?, user_agent = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), ip_address, user_agent, row['id']))
            conn.commit()
            conn.close()
            return dict(row)

        conn.close()
        return None

    def get_kiosk(self, kiosk_id: int) -> Optional[Dict]:
        """Get kiosk device details"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT k.*, o.account_id, o.name as organization_name
            FROM kiosk_devices k
            JOIN organizations o ON k.organization_id = o.id
            WHERE k.id = ?
        """, (kiosk_id,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def deactivate_kiosk(self, kiosk_id: int) -> bool:
        """Deactivate a kiosk (lost/stolen)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE kiosk_devices SET is_active = 0
            WHERE id = ?
        """, (kiosk_id,))

        # Revoke all sessions for this kiosk
        cursor.execute("""
            UPDATE user_sessions SET revoked_at = ?
            WHERE kiosk_id = ? AND revoked_at IS NULL
        """, (datetime.now().isoformat(), kiosk_id))

        conn.commit()
        conn.close()
        return True

    def get_kiosks_for_organization(self, organization_id: int) -> List[Dict]:
        """Get all kiosks for an organization"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM kiosk_devices
            WHERE organization_id = ?
            ORDER BY created_at DESC
        """, (organization_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========================================================================
    # PERMISSION CHECKING
    # ========================================================================

    def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if user has specific permission"""
        permissions = self.get_user_permissions(user_id)
        return permission in permissions

    def has_any_permission(self, user_id: int, permissions: List[str]) -> bool:
        """Check if user has any of the permissions"""
        user_perms = set(self.get_user_permissions(user_id))
        return bool(user_perms.intersection(set(permissions)))

    def has_all_permissions(self, user_id: int, permissions: List[str]) -> bool:
        """Check if user has all of the permissions"""
        user_perms = set(self.get_user_permissions(user_id))
        return set(permissions).issubset(user_perms)

    def get_role_by_name(self, role_name: str) -> Optional[Dict]:
        """Get role by name"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM roles WHERE name = ?", (role_name,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_all_roles(self) -> List[Dict]:
        """Get all roles"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM roles ORDER BY sort_order")
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_permissions_for_role(self, role_id: int) -> List[str]:
        """Get permission names for a role"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.name
            FROM role_permissions rp
            JOIN permissions p ON rp.permission_id = p.id
            WHERE rp.role_id = ?
            ORDER BY p.sort_order
        """, (role_id,))

        permissions = [row['name'] for row in cursor.fetchall()]
        conn.close()
        return permissions

    # ========================================================================
    # AUDIT LOGGING
    # ========================================================================

    def log_action(self, organization_id: int, user_id: int, action: str,
                   resource_type: str = None, resource_id: int = None,
                   details: dict = None, ip_address: str = None) -> int:
        """
        Log an auditable action.

        Args:
            organization_id: Org context
            user_id: User performing action
            action: Action name (e.g., 'user.created', 'job.status_changed')
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional context as dict
            ip_address: Client IP
        """
        conn = self.get_connection()
        log_id = self._log_audit(conn, organization_id, user_id, None, action,
                                resource_type, resource_id, details, ip_address)
        conn.close()
        return log_id

    def _log_audit(self, conn, organization_id: int, user_id: int, kiosk_id: int,
                   action: str, resource_type: str = None, resource_id: int = None,
                   details: Any = None, ip_address: str = None) -> int:
        """Internal audit logging (uses existing connection)"""
        cursor = conn.cursor()

        details_json = json.dumps(details) if details else None

        cursor.execute("""
            INSERT INTO audit_log_new (organization_id, user_id, kiosk_id, action, resource_type, resource_id, details, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (organization_id, user_id, kiosk_id, action, resource_type, resource_id, details_json, ip_address))

        log_id = cursor.lastrowid
        conn.commit()
        return log_id

    def get_audit_log(self, organization_id: int = None, user_id: int = None,
                      action: str = None, limit: int = 100) -> List[Dict]:
        """Get audit log entries with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM audit_log_new WHERE 1=1"
        params = []

        if organization_id:
            query += " AND organization_id = ?"
            params.append(organization_id)
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if action:
            query += " AND action = ?"
            params.append(action)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            entry = dict(row)
            if entry['details']:
                try:
                    entry['details'] = json.loads(entry['details'])
                except:
                    pass
            results.append(entry)

        return results

    # ========================================================================
    # ORGANIZATION MANAGEMENT
    # ========================================================================

    def create_organization(self, account_id: int, name: str, slug: str, **details) -> int:
        """Create a new organization (location) under an account"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO organizations (account_id, name, slug, address, city, state, zip, phone, email, timezone, settings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            account_id, name, slug,
            details.get('address'), details.get('city'), details.get('state'),
            details.get('zip'), details.get('phone'), details.get('email'),
            details.get('timezone', 'America/Chicago'),
            json.dumps(details.get('settings', {}))
        ))

        org_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return org_id

    def get_organization(self, organization_id: int) -> Optional[Dict]:
        """Get organization details"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT o.*, a.name as account_name
            FROM organizations o
            JOIN accounts a ON o.account_id = a.id
            WHERE o.id = ?
        """, (organization_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            org = dict(row)
            if org['settings']:
                try:
                    org['settings'] = json.loads(org['settings'])
                except:
                    org['settings'] = {}
            return org
        return None

    def get_organizations_for_account(self, account_id: int) -> List[Dict]:
        """Get all organizations for an account"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM organizations
            WHERE account_id = ? AND is_active = 1
            ORDER BY name
        """, (account_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _generate_slug(self, text: str) -> str:
        """Generate URL-safe slug from text"""
        # Convert to lowercase and replace spaces with hyphens
        slug = text.lower().strip()
        # Remove special characters
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        # Replace spaces with hyphens
        slug = re.sub(r'[\s_]+', '-', slug)
        # Remove multiple hyphens
        slug = re.sub(r'-+', '-', slug)
        # Trim hyphens from ends
        slug = slug.strip('-')
        return slug[:50]  # Limit length

    def clear_permission_cache(self, user_id: int = None):
        """Clear permission cache for a user or all users"""
        if user_id:
            self._permission_cache.pop(user_id, None)
        else:
            self._permission_cache.clear()
