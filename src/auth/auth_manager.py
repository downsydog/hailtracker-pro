"""
Authentication Manager
Handles user authentication, sessions, and permissions
"""

import sqlite3
from src.db.engine import get_raw_connection, is_postgres
from src.db.compat import sql
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os


class AuthManager:
    """Manage user authentication and authorization"""

    def __init__(self, db_path='data/hailtracker_crm.db'):
        self.db_path = db_path
        if not is_postgres():
            self._ensure_auth_tables()

    def _ensure_auth_tables(self):
        """Create auth tables if they don't exist"""
        if is_postgres():
            return
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if users table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='users'
        """)
        table_exists = cursor.fetchone()
        conn.close()

        if not table_exists:
            # First time - run full schema
            schema_path = 'src/db/auth_schema.sql'
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    schema = f.read()

                conn = sqlite3.connect(self.db_path)
                conn.executescript(schema)
                conn.commit()
                conn.close()

                # Update admin password with proper bcrypt hash
                self._ensure_admin_user()

                print(f"Auth database initialized: {self.db_path}")

    def _ensure_admin_user(self):
        """Ensure admin user has correct password hash"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Generate proper bcrypt hash for admin123
        admin_password = 'admin123'
        password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())

        cursor.execute(sql.adapt("""
            UPDATE users
            SET password_hash = ?
            WHERE username = 'admin'
        """), (password_hash.decode('utf-8'),))

        conn.commit()
        conn.close()

    def get_connection(self):
        """Get database connection"""
        if is_postgres():
            return get_raw_connection()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ========================================================================
    # USER MANAGEMENT
    # ========================================================================

    def create_user(self, email: str, username: str, password: str,
                   full_name: str, role: str = 'sales',
                   company_id: int = None) -> Optional[int]:
        """Create a new user"""

        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            if is_postgres():
                cursor.execute(sql.adapt("""
                    INSERT INTO users (email, username, password_hash, full_name, role, company_id)
                    VALUES (?, ?, ?, ?, ?, ?) RETURNING id
                """), (email, username, password_hash.decode('utf-8'), full_name, role, company_id))
                user_id = cursor.fetchone()['id']
            else:
                cursor.execute(sql.adapt("""
                    INSERT INTO users (email, username, password_hash, full_name, role, company_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """), (email, username, password_hash.decode('utf-8'), full_name, role, company_id))
                user_id = cursor.lastrowid

            conn.commit()
            conn.close()

            self.log_audit(user_id, 'user_created', 'user', user_id, f'User {username} created')

            return user_id

        except Exception as e:
            print(f"User creation failed: {e}")
            return None

    def authenticate_user(self, username_or_email: str, password: str,
                         ip_address: str = None) -> Optional[Dict]:
        """Authenticate user with username/email and password"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(sql.adapt("""
            SELECT * FROM users
            WHERE (username = ? OR email = ?) AND active = TRUE
        """), (username_or_email, username_or_email))

        user = cursor.fetchone()

        if not user:
            conn.close()
            self.log_audit(None, 'login_failed', 'user', None,
                          f'Failed login: user not found {username_or_email}', ip_address)
            return None

        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # Update login stats
            cursor.execute(sql.adapt("""
                UPDATE users
                SET last_login = CURRENT_TIMESTAMP,
                    login_count = login_count + 1
                WHERE id = ?
            """), (user['id'],))

            conn.commit()
            conn.close()

            self.log_audit(user['id'], 'login_success', 'user', user['id'],
                          f'User {user["username"]} logged in', ip_address)

            return dict(user)
        else:
            conn.close()
            self.log_audit(None, 'login_failed', 'user', None,
                          f'Failed login: wrong password for {username_or_email}', ip_address)
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(sql.adapt("SELECT * FROM users WHERE id = ?"), (user_id,))
        user = cursor.fetchone()
        conn.close()

        return dict(user) if user else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(sql.adapt("SELECT * FROM users WHERE email = ?"), (email,))
        user = cursor.fetchone()
        conn.close()

        return dict(user) if user else None

    def update_user(self, user_id: int, **kwargs):
        """Update user fields"""

        allowed_fields = ['email', 'username', 'full_name', 'role', 'phone', 'active']

        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)

        if not updates:
            return

        values.append(user_id)

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(sql.adapt(f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE id = ?
        """), values)

        conn.commit()
        conn.close()

        self.log_audit(user_id, 'user_updated', 'user', user_id,
                      f'User updated: {", ".join(updates)}')

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Change user password"""

        user = self.get_user_by_id(user_id)
        if not user:
            return False

        # Verify old password
        if not bcrypt.checkpw(old_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return False

        # Hash new password
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(sql.adapt("""
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
        """), (new_hash.decode('utf-8'), user_id))

        conn.commit()
        conn.close()

        self.log_audit(user_id, 'password_changed', 'user', user_id, 'Password changed')

        return True

    def generate_reset_token(self, email: str) -> Optional[str]:
        """Generate password reset token"""

        user = self.get_user_by_email(email)
        if not user:
            return None

        token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(hours=24)

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(sql.adapt("""
            UPDATE users
            SET reset_token = ?,
                reset_token_expires = ?
            WHERE id = ?
        """), (token, expires.isoformat(), user['id']))

        conn.commit()
        conn.close()

        self.log_audit(user['id'], 'reset_token_generated', 'user', user['id'],
                      'Password reset token generated')

        return token

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using token"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(sql.adapt("""
            SELECT * FROM users
            WHERE reset_token = ?
            AND reset_token_expires > ?
        """), (token, datetime.now().isoformat()))

        user = cursor.fetchone()

        if not user:
            conn.close()
            return False

        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        cursor.execute(sql.adapt("""
            UPDATE users
            SET password_hash = ?,
                reset_token = NULL,
                reset_token_expires = NULL
            WHERE id = ?
        """), (new_hash.decode('utf-8'), user['id']))

        conn.commit()
        conn.close()

        self.log_audit(user['id'], 'password_reset', 'user', user['id'],
                      'Password reset via token')

        return True

    # ========================================================================
    # PERMISSIONS
    # ========================================================================

    def check_permission(self, user_id: int, resource: str, action: str) -> bool:
        """Check if user has permission"""

        user = self.get_user_by_id(user_id)
        if not user:
            return False

        # Admins have all permissions
        if user['role'] == 'admin':
            return True

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(sql.adapt("""
            SELECT allowed FROM permissions
            WHERE role = ? AND resource = ? AND action = ?
        """), (user['role'], resource, action))

        result = cursor.fetchone()
        conn.close()

        return result['allowed'] if result else False

    def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permissions for user as list of permission names"""

        user = self.get_user_by_id(user_id)
        if not user:
            return []

        conn = self.get_connection()
        cursor = conn.cursor()

        # Get permission names by joining through role_permissions
        # The user's role field contains the role name (e.g., 'admin')
        cursor.execute(sql.adapt("""
            SELECT p.name
            FROM permissions p
            JOIN role_permissions rp ON rp.permission_id = p.id
            JOIN roles r ON r.id = rp.role_id
            WHERE r.name = ?
        """), (user['role'],))

        permissions = cursor.fetchall()
        conn.close()

        # Return list of permission name strings
        return [p['name'] for p in permissions]

    # ========================================================================
    # AUDIT LOGGING
    # ========================================================================

    def log_audit(self, user_id: Optional[int], action: str,
                 resource_type: str = None, resource_id: int = None,
                 details: str = None, ip_address: str = None):
        """Log audit event"""

        conn = self.get_connection()
        cursor = conn.cursor()

        if is_postgres():
            # PG table is audit_logs with columns: description, metadata
            meta = f'{resource_type}:{resource_id}' if resource_type else None
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, description, metadata, ip_address)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, action, details, meta, ip_address))
        else:
            cursor.execute("""
                INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, action, resource_type, resource_id, details, ip_address))

        conn.commit()
        conn.close()

    def get_audit_log(self, user_id: int = None, limit: int = 100) -> List[Dict]:
        """Get audit log entries"""

        conn = self.get_connection()
        cursor = conn.cursor()

        if is_postgres():
            table = 'audit_logs'
            ts_col = 'created_at'
        else:
            table = 'audit_log'
            ts_col = 'timestamp'

        if user_id:
            cursor.execute(sql.adapt(f"""
                SELECT * FROM {table}
                WHERE user_id = ?
                ORDER BY {ts_col} DESC
                LIMIT ?
            """), (user_id, limit))
        else:
            cursor.execute(sql.adapt(f"""
                SELECT * FROM {table}
                ORDER BY {ts_col} DESC
                LIMIT ?
            """), (limit,))

        logs = cursor.fetchall()
        conn.close()

        return [dict(log) for log in logs]

    # ========================================================================
    # COMPANY MANAGEMENT
    # ========================================================================

    def get_company_users(self, company_id: int) -> List[Dict]:
        """Get all users in a company"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(sql.adapt("""
            SELECT id, email, username, full_name, role, active, created_at, last_login, login_count, company_id
            FROM users
            WHERE company_id = ?
            ORDER BY created_at DESC
        """), (company_id,))

        users = cursor.fetchall()
        conn.close()

        return [dict(u) for u in users]

    def get_all_users(self, active_only: bool = True) -> List[Dict]:
        """Get all users"""

        conn = self.get_connection()
        cursor = conn.cursor()

        if active_only:
            cursor.execute(sql.adapt("""
                SELECT id, email, username, full_name, role, active, created_at, last_login
                FROM users
                WHERE active = TRUE
                ORDER BY created_at DESC
            """))
        else:
            cursor.execute(sql.adapt("""
                SELECT id, email, username, full_name, role, active, created_at, last_login
                FROM users
                ORDER BY created_at DESC
            """))

        users = cursor.fetchall()
        conn.close()

        return [dict(u) for u in users]

    def deactivate_user(self, user_id: int, admin_id: int) -> bool:
        """Deactivate a user account"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(sql.adapt("""
            UPDATE users
            SET active = FALSE
            WHERE id = ?
        """), (user_id,))

        conn.commit()
        conn.close()

        self.log_audit(admin_id, 'user_deactivated', 'user', user_id,
                      f'User {user_id} deactivated by admin {admin_id}')

        return True

    def reactivate_user(self, user_id: int, admin_id: int) -> bool:
        """Reactivate a user account"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(sql.adapt("""
            UPDATE users
            SET active = TRUE
            WHERE id = ?
        """), (user_id,))

        conn.commit()
        conn.close()

        self.log_audit(admin_id, 'user_reactivated', 'user', user_id,
                      f'User {user_id} reactivated by admin {admin_id}')

        return True
