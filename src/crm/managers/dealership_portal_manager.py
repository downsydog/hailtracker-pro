"""
PDR CRM Part 25 - Dealership Portal Manager
Self-service portal for dealerships and fleet customers

FEATURES:
- Portal access management
- CSV/Excel batch upload
- API integration for DMS
- Real-time status tracking
- Invoice management
- Monthly reporting
"""

import json
import csv
import io
import secrets
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import calendar

from ..models.database import Database


class DealershipPortalManager:
    """
    Manage dealership self-service portal

    Provides batch submission, tracking, and reporting
    """

    # Access levels
    ACCESS_LEVELS = ['ADMIN', 'MANAGER', 'VIEWER', 'API_ONLY']

    # API permissions
    API_PERMISSIONS = [
        'batch.submit',
        'batch.view',
        'batch.cancel',
        'vehicle.view',
        'invoice.view',
        'invoice.pay',
        'report.view'
    ]

    def __init__(self, db_path_or_instance):
        """Initialize portal manager with database path or instance"""
        if isinstance(db_path_or_instance, str):
            self.db = Database(db_path_or_instance)
            self.db_path = db_path_or_instance
        else:
            self.db = db_path_or_instance
            self.db_path = None
        self._ensure_portal_tables()

    def _ensure_portal_tables(self):
        """Ensure portal-related tables exist"""
        # Portal users table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fleet_customer_id INTEGER NOT NULL,
                username TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT,
                access_level TEXT DEFAULT 'VIEWER',
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (fleet_customer_id) REFERENCES fleet_customers(id)
            )
        """)

        # API keys table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fleet_customer_id INTEGER NOT NULL,
                key_name TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                key_hash TEXT NOT NULL,
                permissions TEXT,
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (fleet_customer_id) REFERENCES fleet_customers(id)
            )
        """)

        # Portal activity log
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fleet_customer_id INTEGER NOT NULL,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fleet_customer_id) REFERENCES fleet_customers(id)
            )
        """)

    # ========================================================================
    # PORTAL ACCESS MANAGEMENT
    # ========================================================================

    def create_portal_access(
        self,
        fleet_id: int,
        username: str,
        email: str,
        access_level: str = 'VIEWER',
        password: Optional[str] = None
    ) -> int:
        """
        Create portal user account for fleet customer

        Args:
            fleet_id: Fleet customer ID
            username: Login username
            email: User email
            access_level: ADMIN, MANAGER, VIEWER, API_ONLY
            password: Optional password (will generate if not provided)

        Returns:
            User ID
        """
        if access_level not in self.ACCESS_LEVELS:
            raise ValueError(f"Invalid access_level. Must be: {self.ACCESS_LEVELS}")

        # Generate password if not provided
        if not password:
            password = secrets.token_urlsafe(12)

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        result = self.db.execute("""
            INSERT INTO portal_users (
                fleet_customer_id, username, email,
                password_hash, access_level,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            fleet_id,
            username,
            email,
            password_hash,
            access_level,
            datetime.now().isoformat(),
            'ACTIVE'
        ))

        user_id = result[0]['id']

        # Log activity
        self._log_activity(fleet_id, user_id, 'PORTAL_ACCESS_CREATED',
                          f'Username: {username}, Level: {access_level}')

        print(f"[OK] Created portal access for {username}")
        print(f"     Email: {email}")
        print(f"     Access level: {access_level}")

        return user_id

    def generate_api_key(
        self,
        fleet_id: int,
        key_name: str,
        permissions: List[str],
        expires_days: Optional[int] = None
    ) -> str:
        """
        Generate API key for fleet customer

        Args:
            fleet_id: Fleet customer ID
            key_name: Descriptive name for the key
            permissions: List of API permissions
            expires_days: Days until expiration (None = no expiration)

        Returns:
            API key string
        """
        # Validate permissions
        for perm in permissions:
            if perm not in self.API_PERMISSIONS:
                raise ValueError(f"Invalid permission: {perm}. Must be: {self.API_PERMISSIONS}")

        # Generate key
        api_key = f"fleet_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        expires_at = None
        if expires_days:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()

        self.db.execute("""
            INSERT INTO portal_api_keys (
                fleet_customer_id, key_name, api_key, key_hash,
                permissions, created_at, expires_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fleet_id,
            key_name,
            api_key,
            key_hash,
            json.dumps(permissions),
            datetime.now().isoformat(),
            expires_at,
            'ACTIVE'
        ))

        self._log_activity(fleet_id, None, 'API_KEY_GENERATED',
                          f'Key: {key_name}, Permissions: {permissions}')

        print(f"[OK] Generated API key: {key_name}")
        print(f"     Permissions: {', '.join(permissions)}")
        if expires_at:
            print(f"     Expires: {expires_at}")

        return api_key

    def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """Validate API key and return permissions"""
        result = self.db.execute("""
            SELECT * FROM portal_api_keys
            WHERE api_key = ? AND status = 'ACTIVE'
        """, (api_key,))

        if not result:
            return None

        key_data = dict(result[0])

        # Check expiration
        if key_data.get('expires_at'):
            if datetime.fromisoformat(key_data['expires_at']) < datetime.now():
                return None

        # Update last used
        self.db.execute("""
            UPDATE portal_api_keys SET last_used = ? WHERE id = ?
        """, (datetime.now().isoformat(), key_data['id']))

        return {
            'fleet_id': key_data['fleet_customer_id'],
            'key_name': key_data['key_name'],
            'permissions': json.loads(key_data['permissions']) if key_data['permissions'] else []
        }

    # ========================================================================
    # PORTAL DASHBOARD
    # ========================================================================

    def get_portal_dashboard(self, fleet_id: int) -> Dict:
        """
        Get dashboard data for fleet customer portal

        Returns aggregated data for dashboard display
        """
        from .fleet_manager import FleetManager

        # Get fleet manager instance
        fleet_mgr = FleetManager(self.db)

        # Get fleet info
        fleet = fleet_mgr.get_fleet_customer(fleet_id)

        if not fleet:
            return {}

        tier_info = fleet_mgr.PRICING_TIERS.get(fleet['pricing_tier'], {})

        # Get this month's activity
        first_of_month = date.today().replace(day=1)

        this_month = self.db.execute("""
            SELECT
                COUNT(DISTINCT bv.id) as vehicles,
                COALESCE(SUM(COALESCE(bv.actual_cost, bv.estimated_cost)), 0) as revenue
            FROM batch_vehicles bv
            JOIN batch_jobs bj ON bj.id = bv.batch_job_id
            WHERE bj.fleet_customer_id = ?
              AND DATE(bv.created_at) >= ?
        """, (fleet_id, first_of_month.isoformat()))

        vehicles_this_month = this_month[0]['vehicles'] if this_month else 0
        revenue_this_month = this_month[0]['revenue'] if this_month else 0

        # Get active batches
        active_batches = self.db.execute("""
            SELECT * FROM batch_jobs
            WHERE fleet_customer_id = ?
              AND status IN ('PENDING', 'IN_PROGRESS')
            ORDER BY created_at DESC
            LIMIT 10
        """, (fleet_id,))

        # Get recent invoices
        recent_invoices = self.db.execute("""
            SELECT * FROM fleet_invoices
            WHERE fleet_customer_id = ?
            ORDER BY invoice_date DESC
            LIMIT 5
        """, (fleet_id,))

        # Get unpaid balance
        unpaid = self.db.execute("""
            SELECT COALESCE(SUM(balance_due), 0) as balance
            FROM fleet_invoices
            WHERE fleet_customer_id = ?
              AND status IN ('PENDING', 'SENT', 'PARTIAL')
        """, (fleet_id,))

        unpaid_balance = unpaid[0]['balance'] if unpaid else 0

        return {
            'fleet_info': {
                'company_name': fleet['company_name'],
                'fleet_type': fleet['fleet_type'],
                'pricing_tier': fleet['pricing_tier'],
                'tier_name': tier_info.get('name', 'Standard'),
                'discount_percent': tier_info.get('discount_percent', 0),
                'payment_terms': fleet['payment_terms']
            },
            'this_month': {
                'vehicles_processed': vehicles_this_month,
                'revenue': revenue_this_month
            },
            'active_batches': [dict(b) for b in active_batches],
            'recent_invoices': [dict(i) for i in recent_invoices],
            'unpaid_balance': unpaid_balance
        }

    # ========================================================================
    # BATCH SUBMISSION
    # ========================================================================

    def submit_batch_via_csv(
        self,
        fleet_id: int,
        csv_data: str,
        batch_name: str,
        submitted_by: str
    ) -> Dict:
        """
        Submit batch of vehicles via CSV upload

        Args:
            fleet_id: Fleet customer ID
            csv_data: CSV string with vehicle data
            batch_name: Name for the batch
            submitted_by: Username who submitted

        Returns:
            Batch submission result
        """
        from .fleet_manager import FleetManager
        fleet_mgr = FleetManager(self.db)

        # Parse CSV
        vehicles = []
        reader = csv.DictReader(io.StringIO(csv_data.strip()))

        for row in reader:
            vehicle = {
                'stock_number': row.get('stock_number', '').strip(),
                'year': int(row.get('year', 0)) if row.get('year') else None,
                'make': row.get('make', '').strip(),
                'model': row.get('model', '').strip(),
                'vin': row.get('vin', '').strip(),
                'damage_type': row.get('damage_type', 'HAIL').strip().upper(),
                'estimated_cost': float(row.get('estimated_cost', 0)) if row.get('estimated_cost') else 0
            }
            vehicles.append(vehicle)

        if not vehicles:
            return {
                'success': False,
                'error': 'No vehicles found in CSV'
            }

        # Create batch
        batch_id = fleet_mgr.create_batch_job(
            fleet_id=fleet_id,
            batch_name=batch_name,
            vehicles=vehicles,
            created_by=submitted_by,
            notes=f'Submitted via CSV upload by {submitted_by}'
        )

        total_cost = sum(v.get('estimated_cost', 0) for v in vehicles)

        self._log_activity(fleet_id, None, 'BATCH_SUBMITTED_CSV',
                          f'Batch: {batch_name}, Vehicles: {len(vehicles)}')

        print(f"[OK] CSV batch uploaded successfully")
        print(f"     Batch: {batch_name}")
        print(f"     Vehicles: {len(vehicles)}")

        return {
            'success': True,
            'batch_id': batch_id,
            'batch_name': batch_name,
            'vehicles_uploaded': len(vehicles),
            'total_estimated_cost': total_cost
        }

    def submit_batch_via_api(
        self,
        fleet_id: int,
        api_key: str,
        vehicles: List[Dict],
        batch_name: Optional[str] = None
    ) -> Dict:
        """
        Submit batch of vehicles via API

        Args:
            fleet_id: Fleet customer ID
            api_key: API key for authentication
            vehicles: List of vehicle dictionaries
            batch_name: Optional batch name (auto-generated if not provided)

        Returns:
            Batch submission result
        """
        # Validate API key
        key_data = self.validate_api_key(api_key)

        if not key_data:
            return {
                'success': False,
                'error': 'Invalid or expired API key'
            }

        if key_data['fleet_id'] != fleet_id:
            return {
                'success': False,
                'error': 'API key not authorized for this fleet'
            }

        if 'batch.submit' not in key_data['permissions']:
            return {
                'success': False,
                'error': 'API key does not have batch.submit permission'
            }

        from .fleet_manager import FleetManager
        fleet_mgr = FleetManager(self.db)

        # Generate batch name if not provided
        if not batch_name:
            batch_name = f"API Batch - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Create batch
        batch_id = fleet_mgr.create_batch_job(
            fleet_id=fleet_id,
            batch_name=batch_name,
            vehicles=vehicles,
            created_by=f'API: {key_data["key_name"]}',
            notes='Submitted via API'
        )

        self._log_activity(fleet_id, None, 'BATCH_SUBMITTED_API',
                          f'Batch: {batch_name}, Vehicles: {len(vehicles)}, Key: {key_data["key_name"]}')

        print(f"[OK] API batch submitted successfully")
        print(f"     Batch ID: {batch_id}")
        print(f"     Vehicles: {len(vehicles)}")

        return {
            'success': True,
            'batch_id': batch_id,
            'batch_name': batch_name,
            'vehicles_submitted': len(vehicles)
        }

    # ========================================================================
    # STATUS TRACKING
    # ========================================================================

    def get_batch_status(self, fleet_id: int, batch_id: int) -> Dict:
        """
        Get detailed batch status for portal display

        Args:
            fleet_id: Fleet customer ID
            batch_id: Batch job ID

        Returns:
            Batch status with vehicle breakdown
        """
        # Get batch
        batch = self.db.execute("""
            SELECT * FROM batch_jobs
            WHERE id = ? AND fleet_customer_id = ?
        """, (batch_id, fleet_id))

        if not batch:
            return {}

        batch_data = dict(batch[0])

        # Get vehicles
        vehicles = self.db.execute("""
            SELECT * FROM batch_vehicles
            WHERE batch_job_id = ?
            ORDER BY stock_number
        """, (batch_id,))

        vehicle_list = [dict(v) for v in vehicles]

        # Calculate status breakdown
        status_breakdown = {
            'PENDING': 0,
            'IN_PROGRESS': 0,
            'COMPLETED': 0,
            'CANCELLED': 0
        }

        for v in vehicle_list:
            status = v.get('status', 'PENDING')
            if status in status_breakdown:
                status_breakdown[status] += 1

        total = len(vehicle_list)
        completed = status_breakdown['COMPLETED']
        progress = (completed / total * 100) if total > 0 else 0

        return {
            'batch_id': batch_id,
            'batch_name': batch_data['batch_name'],
            'created_at': batch_data['created_at'],
            'status': batch_data['status'],
            'total_vehicles': total,
            'completed_vehicles': completed,
            'progress_percent': progress,
            'status_breakdown': status_breakdown,
            'vehicles': vehicle_list,
            'total_estimated_cost': batch_data['total_estimated_cost'],
            'total_actual_cost': batch_data.get('total_actual_cost')
        }

    def get_vehicle_status(self, fleet_id: int, stock_number: str) -> Optional[Dict]:
        """
        Get individual vehicle status by stock number

        Args:
            fleet_id: Fleet customer ID
            stock_number: Vehicle stock number

        Returns:
            Vehicle status or None if not found
        """
        result = self.db.execute("""
            SELECT bv.*, bj.batch_name, bj.fleet_customer_id
            FROM batch_vehicles bv
            JOIN batch_jobs bj ON bj.id = bv.batch_job_id
            WHERE bv.stock_number = ? AND bj.fleet_customer_id = ?
            ORDER BY bv.created_at DESC
            LIMIT 1
        """, (stock_number, fleet_id))

        if not result:
            return None

        v = dict(result[0])

        return {
            'stock_number': v['stock_number'],
            'year': v['year'],
            'make': v['make'],
            'model': v['model'],
            'vin': v['vin'],
            'damage_type': v['damage_type'],
            'status': v['status'],
            'estimated_cost': v['estimated_cost'],
            'actual_cost': v.get('actual_cost'),
            'assigned_tech': v.get('assigned_tech'),
            'batch_id': v['batch_job_id'],
            'batch_name': v['batch_name'],
            'created_at': v['created_at'],
            'completed_at': v.get('completed_at')
        }

    # ========================================================================
    # INVOICE MANAGEMENT
    # ========================================================================

    def get_invoice_details(self, fleet_id: int, invoice_id: int) -> Optional[Dict]:
        """
        Get detailed invoice information for portal display

        Args:
            fleet_id: Fleet customer ID
            invoice_id: Invoice ID

        Returns:
            Invoice details with line items
        """
        # Get invoice
        invoice = self.db.execute("""
            SELECT * FROM fleet_invoices
            WHERE id = ? AND fleet_customer_id = ?
        """, (invoice_id, fleet_id))

        if not invoice:
            return None

        inv = dict(invoice[0])

        # Get line items (vehicles from batch)
        line_items = []
        if inv.get('batch_job_id'):
            vehicles = self.db.execute("""
                SELECT * FROM batch_vehicles
                WHERE batch_job_id = ?
                ORDER BY stock_number
            """, (inv['batch_job_id'],))

            line_items = [dict(v) for v in vehicles]

        return {
            'invoice': inv,
            'line_items': line_items,
            'line_item_count': len(line_items)
        }

    def get_invoice_history(
        self,
        fleet_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get invoice history for fleet customer"""
        if status:
            results = self.db.execute("""
                SELECT * FROM fleet_invoices
                WHERE fleet_customer_id = ? AND status = ?
                ORDER BY invoice_date DESC
                LIMIT ?
            """, (fleet_id, status, limit))
        else:
            results = self.db.execute("""
                SELECT * FROM fleet_invoices
                WHERE fleet_customer_id = ?
                ORDER BY invoice_date DESC
                LIMIT ?
            """, (fleet_id, limit))

        return [dict(row) for row in results]

    # ========================================================================
    # REPORTING
    # ========================================================================

    def generate_monthly_report(
        self,
        fleet_id: int,
        year: int,
        month: int
    ) -> Dict:
        """
        Generate monthly activity report for fleet customer

        Args:
            fleet_id: Fleet customer ID
            year: Report year
            month: Report month (1-12)

        Returns:
            Monthly report data
        """
        from .fleet_manager import FleetManager
        fleet_mgr = FleetManager(self.db)

        # Get fleet info
        fleet = fleet_mgr.get_fleet_customer(fleet_id)

        if not fleet:
            return {}

        # Calculate date range
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        # Get batches in period
        batches = self.db.execute("""
            SELECT * FROM batch_jobs
            WHERE fleet_customer_id = ?
              AND DATE(created_at) >= ?
              AND DATE(created_at) <= ?
        """, (fleet_id, first_day.isoformat(), last_day.isoformat()))

        batch_list = [dict(b) for b in batches]

        # Get vehicles in period
        vehicles = self.db.execute("""
            SELECT COUNT(*) as count
            FROM batch_vehicles bv
            JOIN batch_jobs bj ON bj.id = bv.batch_job_id
            WHERE bj.fleet_customer_id = ?
              AND DATE(bv.created_at) >= ?
              AND DATE(bv.created_at) <= ?
        """, (fleet_id, first_day.isoformat(), last_day.isoformat()))

        vehicle_count = vehicles[0]['count'] if vehicles else 0

        # Get revenue
        revenue = self.db.execute("""
            SELECT
                COALESCE(SUM(total), 0) as total_revenue,
                COALESCE(SUM(discount_amount), 0) as total_discounts
            FROM fleet_invoices
            WHERE fleet_customer_id = ?
              AND DATE(invoice_date) >= ?
              AND DATE(invoice_date) <= ?
        """, (fleet_id, first_day.isoformat(), last_day.isoformat()))

        total_revenue = revenue[0]['total_revenue'] if revenue else 0
        total_discounts = revenue[0]['total_discounts'] if revenue else 0

        tier_info = fleet_mgr.PRICING_TIERS.get(fleet['pricing_tier'], {})

        return {
            'report_period': {
                'year': year,
                'month': month,
                'month_name': calendar.month_name[month],
                'start_date': first_day.isoformat(),
                'end_date': last_day.isoformat()
            },
            'company_name': fleet['company_name'],
            'fleet_type': fleet['fleet_type'],
            'activity': {
                'batches_submitted': len(batch_list),
                'vehicles_processed': vehicle_count,
                'avg_vehicles_per_batch': round(vehicle_count / len(batch_list), 1) if batch_list else 0
            },
            'financial': {
                'total_revenue': total_revenue,
                'total_discounts': total_discounts,
                'avg_revenue_per_vehicle': round(total_revenue / vehicle_count, 2) if vehicle_count > 0 else 0
            },
            'pricing': {
                'current_tier': fleet['pricing_tier'],
                'tier_name': tier_info.get('name', 'Standard'),
                'discount_percent': tier_info.get('discount_percent', 0)
            }
        }

    # ========================================================================
    # ACTIVITY LOGGING
    # ========================================================================

    def _log_activity(
        self,
        fleet_id: int,
        user_id: Optional[int],
        action: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log portal activity"""
        self.db.execute("""
            INSERT INTO portal_activity_log (
                fleet_customer_id, user_id, action, details, ip_address, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            fleet_id,
            user_id,
            action,
            details,
            ip_address,
            datetime.now().isoformat()
        ))

    def get_activity_log(
        self,
        fleet_id: int,
        limit: int = 100
    ) -> List[Dict]:
        """Get activity log for fleet customer"""
        results = self.db.execute("""
            SELECT * FROM portal_activity_log
            WHERE fleet_customer_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (fleet_id, limit))

        return [dict(row) for row in results]
