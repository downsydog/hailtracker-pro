"""
PDR CRM Part 15 - Admin Manager
System administration, settings, user management, backup/restore, monitoring

FEATURES:
- System settings
- User management
- Business configuration
- Backup/restore
- System monitoring
- Audit logs
"""

import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any


class AdminManager:
    """
    System administration and configuration
    Manages all system-wide settings and operations
    """

    def __init__(self, db, db_path: str = "data/pdr_crm.db"):
        """Initialize admin manager with database instance"""
        self.db = db
        self.db_path = db_path
        self._ensure_admin_tables()

    def _ensure_admin_tables(self):
        """Create admin-specific tables if they don't exist"""
        # Settings table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                value_type TEXT DEFAULT 'STRING',
                category TEXT,
                description TEXT,
                updated_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Users table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'USER',
                first_name TEXT,
                last_name TEXT,
                status TEXT DEFAULT 'ACTIVE',
                last_login TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # Backups table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                created_at TEXT,
                created_by TEXT,
                notes TEXT
            )
        """)

        # Audit logs table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                description TEXT,
                metadata TEXT,
                ip_address TEXT,
                created_at TEXT
            )
        """)

    # =========================================================================
    # SYSTEM SETTINGS
    # =========================================================================

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get system setting by key"""
        result = self.db.execute("""
            SELECT value, value_type FROM settings WHERE key = ?
        """, (key,))

        if not result:
            return default

        value = result[0]['value']
        value_type = result[0]['value_type']

        # Convert based on type
        if value_type == 'JSON':
            return json.loads(value)
        elif value_type == 'BOOLEAN':
            return value.lower() == 'true'
        elif value_type == 'INTEGER':
            return int(value)
        elif value_type == 'FLOAT':
            return float(value)
        else:  # STRING
            return value

    def set_setting(self, key: str, value: Any, description: str = None,
                   category: str = None) -> bool:
        """Set system setting (auto-detects type)"""
        # Determine type
        if isinstance(value, bool):
            value_type = 'BOOLEAN'
            value_str = 'true' if value else 'false'
        elif isinstance(value, int):
            value_type = 'INTEGER'
            value_str = str(value)
        elif isinstance(value, float):
            value_type = 'FLOAT'
            value_str = str(value)
        elif isinstance(value, (dict, list)):
            value_type = 'JSON'
            value_str = json.dumps(value)
        else:
            value_type = 'STRING'
            value_str = str(value)

        now = datetime.now().isoformat()

        # Check if exists
        existing = self.db.execute("SELECT id FROM settings WHERE key = ?", (key,))

        if existing:
            # Update
            self.db.execute("""
                UPDATE settings SET value = ?, value_type = ?, updated_at = ?,
                                   description = COALESCE(?, description),
                                   category = COALESCE(?, category)
                WHERE key = ?
            """, (value_str, value_type, now, description, category, key))
        else:
            # Insert
            self.db.execute("""
                INSERT INTO settings (key, value, value_type, description, category, updated_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (key, value_str, value_type, description, category, now, now))

        print(f"[OK] Updated setting: {key} = {value}")
        return True

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all system settings"""
        results = self.db.execute("SELECT * FROM settings ORDER BY category, key")

        settings = {}
        for row in results:
            value = row['value']
            value_type = row['value_type'] or 'STRING'

            # Convert value
            if value_type == 'JSON':
                settings[row['key']] = json.loads(value)
            elif value_type == 'BOOLEAN':
                settings[row['key']] = value.lower() == 'true'
            elif value_type == 'INTEGER':
                settings[row['key']] = int(value)
            elif value_type == 'FLOAT':
                settings[row['key']] = float(value)
            else:
                settings[row['key']] = value

        return settings

    def get_settings_by_category(self, category: str) -> Dict[str, Any]:
        """Get settings for a specific category"""
        results = self.db.execute("""
            SELECT * FROM settings WHERE category = ? ORDER BY key
        """, (category,))

        settings = {}
        for row in results:
            value = row['value']
            value_type = row['value_type'] or 'STRING'

            if value_type == 'JSON':
                settings[row['key']] = json.loads(value)
            elif value_type == 'BOOLEAN':
                settings[row['key']] = value.lower() == 'true'
            elif value_type == 'INTEGER':
                settings[row['key']] = int(value)
            elif value_type == 'FLOAT':
                settings[row['key']] = float(value)
            else:
                settings[row['key']] = value

        return settings

    def initialize_default_settings(self) -> int:
        """Initialize default system settings"""
        defaults = {
            # Company Info
            'shop_name': ('PDR Excellence', 'COMPANY', 'Shop name'),
            'shop_address': ('123 Main Street', 'COMPANY', 'Street address'),
            'shop_city': ('Dallas', 'COMPANY', 'City'),
            'shop_state': ('TX', 'COMPANY', 'State'),
            'shop_zip': ('75201', 'COMPANY', 'ZIP code'),
            'shop_phone': ('(555) 123-4567', 'COMPANY', 'Phone number'),
            'shop_email': ('info@pdrexcellence.com', 'COMPANY', 'Email address'),
            'shop_website': ('www.pdrexcellence.com', 'COMPANY', 'Website'),
            'tax_id': ('12-3456789', 'COMPANY', 'Tax ID / EIN'),

            # Business Settings
            'default_tax_rate': (0.0825, 'BUSINESS', 'Default sales tax rate'),
            'default_labor_rate': (75.00, 'BUSINESS', 'Default labor rate per hour'),
            'estimate_validity_days': (30, 'BUSINESS', 'Estimate validity in days'),
            'invoice_due_days': (30, 'BUSINESS', 'Invoice due days from issue'),

            # Scheduling
            'max_appointments_per_slot': (3, 'SCHEDULING', 'Max appointments per time slot'),
            'appointment_slot_duration': (30, 'SCHEDULING', 'Time slot duration in minutes'),
            'business_hours_start': ('08:00', 'SCHEDULING', 'Business hours start'),
            'business_hours_end': ('17:00', 'SCHEDULING', 'Business hours end'),

            # Notifications
            'send_estimate_emails': (True, 'NOTIFICATIONS', 'Auto-send estimate emails'),
            'send_appointment_reminders': (True, 'NOTIFICATIONS', 'Send appointment reminders'),
            'reminder_hours_before': (24, 'NOTIFICATIONS', 'Hours before appointment to remind'),
            'send_invoice_emails': (True, 'NOTIFICATIONS', 'Auto-send invoice emails'),

            # Portal
            'portal_enabled': (True, 'PORTAL', 'Customer portal enabled'),
            'portal_token_days': (30, 'PORTAL', 'Portal access token validity days'),
            'allow_portal_payments': (True, 'PORTAL', 'Allow payments through portal'),

            # Commission
            'junior_commission_rate': (0.40, 'COMMISSION', 'Junior tech commission rate'),
            'senior_commission_rate': (0.55, 'COMMISSION', 'Senior tech commission rate'),
            'master_commission_rate': (0.60, 'COMMISSION', 'Master tech commission rate'),
        }

        count = 0
        for key, (value, category, description) in defaults.items():
            # Check if exists
            existing = self.db.execute("SELECT key FROM settings WHERE key = ?", (key,))

            if not existing:
                self.set_setting(key, value, description, category)
                count += 1

        print(f"[OK] Initialized {count} default settings")
        return count

    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================

    def create_user(self, username: str, email: str, password: str,
                   role: str = 'USER', first_name: str = None,
                   last_name: str = None) -> int:
        """Create system user"""
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        now = datetime.now().isoformat()

        # Create user
        self.db.execute("""
            INSERT INTO users (
                username, email, password_hash,
                role, first_name, last_name,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, email, password_hash, role, first_name, last_name,
              'ACTIVE', now))

        user_id = self.db.execute("SELECT last_insert_rowid() as id")[0]['id']

        print(f"[OK] Created user: {username} ({role})")
        return user_id

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user login"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        result = self.db.execute("""
            SELECT * FROM users
            WHERE username = ? AND password_hash = ? AND status = 'ACTIVE'
        """, (username, password_hash))

        if not result:
            return None

        user = result[0]

        # Update last login
        self.db.execute("""
            UPDATE users SET last_login = ? WHERE id = ?
        """, (datetime.now().isoformat(), user['id']))

        return {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role'],
            'first_name': user['first_name'],
            'last_name': user['last_name']
        }

    def update_user(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user details"""
        allowed_fields = ['email', 'first_name', 'last_name', 'role', 'status']
        update_data = {k: v for k, v in updates.items() if k in allowed_fields}

        if not update_data:
            return False

        set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
        values = list(update_data.values())
        values.append(datetime.now().isoformat())
        values.append(user_id)

        self.db.execute(f"""
            UPDATE users SET {set_clause}, updated_at = ? WHERE id = ?
        """, tuple(values))

        print(f"[OK] Updated user {user_id}")
        return True

    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """Update user password"""
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()

        self.db.execute("""
            UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?
        """, (password_hash, datetime.now().isoformat(), user_id))

        print(f"[OK] Updated password for user {user_id}")
        return True

    def update_user_role(self, user_id: int, role: str) -> bool:
        """Update user role"""
        self.db.execute("""
            UPDATE users SET role = ?, updated_at = ? WHERE id = ?
        """, (role, datetime.now().isoformat(), user_id))

        print(f"[OK] Updated user {user_id} role to {role}")
        return True

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account"""
        self.db.execute("""
            UPDATE users SET status = 'INACTIVE', updated_at = ? WHERE id = ?
        """, (datetime.now().isoformat(), user_id))

        print(f"[OK] Deactivated user {user_id}")
        return True

    def reactivate_user(self, user_id: int) -> bool:
        """Reactivate user account"""
        self.db.execute("""
            UPDATE users SET status = 'ACTIVE', updated_at = ? WHERE id = ?
        """, (datetime.now().isoformat(), user_id))

        print(f"[OK] Reactivated user {user_id}")
        return True

    def list_users(self, active_only: bool = True) -> List[Dict]:
        """List all users"""
        query = "SELECT * FROM users"
        if active_only:
            query += " WHERE status = 'ACTIVE'"
        query += " ORDER BY username"

        results = self.db.execute(query)
        return [dict(r) for r in results] if results else []

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        result = self.db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return dict(result[0]) if result else None

    # =========================================================================
    # BACKUP & RESTORE
    # =========================================================================

    def create_backup(self, backup_name: str = None, notes: str = None,
                     created_by: str = 'system') -> str:
        """Create database backup"""
        # Create backups directory
        backup_dir = "data/backups"
        os.makedirs(backup_dir, exist_ok=True)

        # Generate backup name
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}.db"

        backup_path = os.path.join(backup_dir, backup_name)

        # Copy database file
        shutil.copy2(self.db_path, backup_path)

        file_size = os.path.getsize(backup_path)

        # Record backup
        self.db.execute("""
            INSERT INTO backups (filename, file_path, file_size, created_at, created_by, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (backup_name, backup_path, file_size, datetime.now().isoformat(),
              created_by, notes))

        print(f"[OK] Created backup: {backup_path}")
        print(f"     Size: {file_size:,} bytes")

        return backup_path

    def restore_backup(self, backup_path: str) -> bool:
        """Restore from backup (WARNING: replaces current database)"""
        if not os.path.exists(backup_path):
            raise ValueError(f"Backup file not found: {backup_path}")

        # Verify it's a valid SQLite database
        try:
            test_conn = sqlite3.connect(backup_path)
            test_conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
            test_conn.close()
        except Exception as e:
            raise ValueError(f"Invalid backup file: {e}")

        # Create safety backup of current DB
        safety_backup = self.create_backup(
            backup_name=f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
            notes='Auto-backup before restore'
        )

        print(f"[OK] Safety backup created: {safety_backup}")
        print(f"[OK] Restoring from: {backup_path}")

        # Replace database file
        shutil.copy2(backup_path, self.db_path)

        print(f"[OK] Database restored from backup")
        print(f"     Restart application to use restored database")

        return True

    def list_backups(self, limit: int = 20) -> List[Dict]:
        """List available backups"""
        results = self.db.execute("""
            SELECT * FROM backups ORDER BY created_at DESC LIMIT ?
        """, (limit,))

        return [dict(r) for r in results] if results else []

    def delete_backup(self, backup_id: int) -> bool:
        """Delete a specific backup"""
        backup = self.db.execute("SELECT * FROM backups WHERE id = ?", (backup_id,))

        if not backup:
            return False

        backup = backup[0]

        # Delete file
        if os.path.exists(backup['file_path']):
            os.remove(backup['file_path'])

        # Delete record
        self.db.execute("DELETE FROM backups WHERE id = ?", (backup_id,))

        print(f"[OK] Deleted backup: {backup['filename']}")
        return True

    def delete_old_backups(self, keep_days: int = 30) -> int:
        """Delete backups older than X days"""
        cutoff_date = (date.today() - timedelta(days=keep_days)).isoformat()

        old_backups = self.db.execute("""
            SELECT * FROM backups WHERE DATE(created_at) < ?
        """, (cutoff_date,))

        deleted = 0
        for backup in old_backups:
            # Delete file
            if os.path.exists(backup['file_path']):
                os.remove(backup['file_path'])
                deleted += 1

            # Delete record
            self.db.execute("DELETE FROM backups WHERE id = ?", (backup['id'],))

        if deleted > 0:
            print(f"[OK] Deleted {deleted} old backup(s)")

        return deleted

    # =========================================================================
    # SYSTEM MONITORING
    # =========================================================================

    def get_system_health(self) -> Dict:
        """Get system health metrics"""
        health = {
            'status': 'HEALTHY',
            'timestamp': datetime.now().isoformat(),
            'database': {},
            'jobs': {},
            'storage': {},
            'issues': []
        }

        # Database info
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        health['database']['size_bytes'] = db_size
        health['database']['size_mb'] = round(db_size / (1024 * 1024), 2)

        # Table counts
        health['database']['table_counts'] = {}

        try:
            customers = self.db.execute("SELECT COUNT(*) as c FROM customers WHERE deleted_at IS NULL")
            health['database']['table_counts']['customers'] = customers[0]['c'] if customers else 0
        except:
            health['database']['table_counts']['customers'] = 0

        try:
            jobs = self.db.execute("SELECT COUNT(*) as c FROM jobs WHERE deleted_at IS NULL")
            health['database']['table_counts']['jobs'] = jobs[0]['c'] if jobs else 0
        except:
            health['database']['table_counts']['jobs'] = 0

        try:
            estimates = self.db.execute("SELECT COUNT(*) as c FROM estimates")
            health['database']['table_counts']['estimates'] = estimates[0]['c'] if estimates else 0
        except:
            health['database']['table_counts']['estimates'] = 0

        try:
            invoices = self.db.execute("SELECT COUNT(*) as c FROM invoices")
            health['database']['table_counts']['invoices'] = invoices[0]['c'] if invoices else 0
        except:
            health['database']['table_counts']['invoices'] = 0

        try:
            payments = self.db.execute("SELECT COUNT(*) as c FROM payments")
            health['database']['table_counts']['payments'] = payments[0]['c'] if payments else 0
        except:
            health['database']['table_counts']['payments'] = 0

        # Job health
        health['jobs']['total'] = health['database']['table_counts']['jobs']

        try:
            statuses = self.db.execute("""
                SELECT status, COUNT(*) as count FROM jobs
                WHERE deleted_at IS NULL GROUP BY status
            """)
            health['jobs']['by_status'] = {row['status']: row['count'] for row in statuses}
        except:
            health['jobs']['by_status'] = {}

        # Active jobs (not completed/cancelled)
        try:
            active = self.db.execute("""
                SELECT COUNT(*) as count FROM jobs
                WHERE deleted_at IS NULL AND status NOT IN ('COMPLETED', 'CANCELLED', 'DELIVERED')
            """)
            health['jobs']['active'] = active[0]['count'] if active else 0
        except:
            health['jobs']['active'] = 0

        # Storage - backups
        try:
            backup_count = self.db.execute("SELECT COUNT(*) as c FROM backups")
            health['storage']['backup_count'] = backup_count[0]['c'] if backup_count else 0
        except:
            health['storage']['backup_count'] = 0

        if health['storage']['backup_count'] == 0:
            health['issues'].append("No backups found - create backup!")
            health['status'] = 'WARNING'

        # Recent backup
        try:
            recent_backup = self.db.execute("""
                SELECT created_at FROM backups ORDER BY created_at DESC LIMIT 1
            """)
            if recent_backup:
                last_backup = datetime.fromisoformat(recent_backup[0]['created_at'])
                days_since = (datetime.now() - last_backup).days
                health['storage']['days_since_backup'] = days_since

                if days_since > 7:
                    health['issues'].append(f"Last backup {days_since} days ago - create new backup!")
                    health['status'] = 'WARNING'
        except:
            pass

        return health

    def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'totals': {},
            'recent': {},
            'revenue': {}
        }

        # Total counts
        try:
            stats['totals']['customers'] = self.db.execute(
                "SELECT COUNT(*) as c FROM customers WHERE deleted_at IS NULL"
            )[0]['c']
        except:
            stats['totals']['customers'] = 0

        try:
            stats['totals']['jobs'] = self.db.execute(
                "SELECT COUNT(*) as c FROM jobs WHERE deleted_at IS NULL"
            )[0]['c']
        except:
            stats['totals']['jobs'] = 0

        try:
            stats['totals']['estimates'] = self.db.execute(
                "SELECT COUNT(*) as c FROM estimates"
            )[0]['c']
        except:
            stats['totals']['estimates'] = 0

        try:
            stats['totals']['invoices'] = self.db.execute(
                "SELECT COUNT(*) as c FROM invoices"
            )[0]['c']
        except:
            stats['totals']['invoices'] = 0

        try:
            stats['totals']['technicians'] = self.db.execute(
                "SELECT COUNT(*) as c FROM technicians WHERE status = 'ACTIVE'"
            )[0]['c']
        except:
            stats['totals']['technicians'] = 0

        # Recent activity (last 30 days)
        cutoff = (date.today() - timedelta(days=30)).isoformat()

        try:
            stats['recent']['new_customers'] = self.db.execute(
                "SELECT COUNT(*) as c FROM customers WHERE DATE(created_at) >= ?",
                (cutoff,)
            )[0]['c']
        except:
            stats['recent']['new_customers'] = 0

        try:
            stats['recent']['new_jobs'] = self.db.execute(
                "SELECT COUNT(*) as c FROM jobs WHERE DATE(created_at) >= ?",
                (cutoff,)
            )[0]['c']
        except:
            stats['recent']['new_jobs'] = 0

        try:
            stats['recent']['completed_jobs'] = self.db.execute(
                "SELECT COUNT(*) as c FROM jobs WHERE status = 'COMPLETED' AND DATE(completed_at) >= ?",
                (cutoff,)
            )[0]['c']
        except:
            stats['recent']['completed_jobs'] = 0

        # Revenue
        try:
            total_rev = self.db.execute(
                "SELECT SUM(amount) as total FROM payments WHERE status = 'COMPLETED'"
            )[0]['total']
            stats['revenue']['all_time'] = total_rev or 0
        except:
            stats['revenue']['all_time'] = 0

        try:
            monthly_rev = self.db.execute(
                "SELECT SUM(amount) as total FROM payments WHERE status = 'COMPLETED' AND DATE(payment_date) >= ?",
                (cutoff,)
            )[0]['total']
            stats['revenue']['last_30_days'] = monthly_rev or 0
        except:
            stats['revenue']['last_30_days'] = 0

        return stats

    # =========================================================================
    # AUDIT LOGS
    # =========================================================================

    def log_admin_action(self, user_id: int, action: str, description: str,
                        metadata: Dict = None, ip_address: str = None) -> None:
        """Log administrative action"""
        self.db.execute("""
            INSERT INTO audit_logs (user_id, action, description, metadata, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, action, description,
              json.dumps(metadata) if metadata else None,
              ip_address, datetime.now().isoformat()))

    def get_audit_logs(self, user_id: int = None, action: str = None,
                      days: int = 30, limit: int = 100) -> List[Dict]:
        """Get audit logs"""
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        query = """
            SELECT a.*, u.username
            FROM audit_logs a
            LEFT JOIN users u ON u.id = a.user_id
            WHERE DATE(a.created_at) >= ?
        """
        params = [cutoff]

        if user_id:
            query += " AND a.user_id = ?"
            params.append(user_id)

        if action:
            query += " AND a.action = ?"
            params.append(action)

        query += " ORDER BY a.created_at DESC LIMIT ?"
        params.append(limit)

        results = self.db.execute(query, tuple(params))
        return [dict(r) for r in results] if results else []

    def get_action_summary(self, days: int = 30) -> Dict[str, int]:
        """Get summary of actions by type"""
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        results = self.db.execute("""
            SELECT action, COUNT(*) as count
            FROM audit_logs
            WHERE DATE(created_at) >= ?
            GROUP BY action
            ORDER BY count DESC
        """, (cutoff,))

        return {r['action']: r['count'] for r in results} if results else {}

    # =========================================================================
    # DATABASE MAINTENANCE
    # =========================================================================

    def vacuum_database(self) -> bool:
        """Optimize database (VACUUM)"""
        print("[...] Running VACUUM on database...")

        conn = sqlite3.connect(self.db_path)
        conn.execute("VACUUM")
        conn.close()

        print("[OK] Database optimized")
        return True

    def analyze_database(self) -> bool:
        """Update database statistics (ANALYZE)"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("ANALYZE")
        conn.close()

        print("[OK] Database statistics updated")
        return True

    def get_database_stats(self) -> Dict:
        """Get detailed database statistics"""
        stats = {
            'file_size': 0,
            'file_size_mb': 0,
            'tables': {},
            'total_records': 0
        }

        # Database size
        if os.path.exists(self.db_path):
            stats['file_size'] = os.path.getsize(self.db_path)
            stats['file_size_mb'] = round(stats['file_size'] / (1024 * 1024), 2)

        # Table stats
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        tables = cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """).fetchall()

        for (table_name,) in tables:
            try:
                count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                stats['tables'][table_name] = count
                stats['total_records'] += count
            except:
                stats['tables'][table_name] = 0

        conn.close()

        return stats

    def export_table_csv(self, table_name: str, output_path: str = None) -> str:
        """Export table to CSV"""
        import csv

        if not output_path:
            output_dir = "data/exports"
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"{table_name}_{timestamp}.csv")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get data
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

        conn.close()

        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        print(f"[OK] Exported {len(rows)} rows to {output_path}")
        return output_path

    # =========================================================================
    # REPORTING
    # =========================================================================

    def generate_admin_report(self, days: int = 30) -> str:
        """Generate comprehensive admin report"""
        stats = self.get_system_stats()
        health = self.get_system_health()
        db_stats = self.get_database_stats()

        report = []
        report.append("=" * 60)
        report.append("SYSTEM ADMINISTRATION REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append(f"Period: Last {days} Days")
        report.append("=" * 60)
        report.append("")

        report.append("SYSTEM HEALTH")
        report.append("-" * 40)
        report.append(f"Status:                   {health['status']}")
        report.append(f"Database Size:            {health['database']['size_mb']} MB")
        report.append(f"Days Since Last Backup:   {health['storage'].get('days_since_backup', 'N/A')}")
        if health['issues']:
            report.append("Issues:")
            for issue in health['issues']:
                report.append(f"  - {issue}")
        report.append("")

        report.append("TOTALS")
        report.append("-" * 40)
        report.append(f"Total Customers:          {stats['totals']['customers']:,}")
        report.append(f"Total Jobs:               {stats['totals']['jobs']:,}")
        report.append(f"Total Estimates:          {stats['totals']['estimates']:,}")
        report.append(f"Total Invoices:           {stats['totals']['invoices']:,}")
        report.append(f"Active Technicians:       {stats['totals']['technicians']}")
        report.append("")

        report.append(f"RECENT ACTIVITY (Last {days} Days)")
        report.append("-" * 40)
        report.append(f"New Customers:            {stats['recent']['new_customers']}")
        report.append(f"New Jobs:                 {stats['recent']['new_jobs']}")
        report.append(f"Completed Jobs:           {stats['recent']['completed_jobs']}")
        report.append("")

        report.append("REVENUE")
        report.append("-" * 40)
        report.append(f"All Time:                 ${stats['revenue']['all_time']:,.2f}")
        report.append(f"Last 30 Days:             ${stats['revenue']['last_30_days']:,.2f}")
        report.append("")

        report.append("DATABASE TABLES")
        report.append("-" * 40)
        for table, count in sorted(db_stats['tables'].items()):
            if count > 0:
                report.append(f"  {table:25s} {count:>10,}")
        report.append(f"  {'TOTAL':25s} {db_stats['total_records']:>10,}")
        report.append("")

        return "\n".join(report)
