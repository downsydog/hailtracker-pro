"""
Database Manager
Handles connections and common operations for PDR CRM
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import contextmanager


class Database:
    """Database connection manager for PDR CRM"""

    def __init__(self, db_path: str = "data/pdr_crm.db"):
        """Initialize database connection"""
        self.db_path = db_path

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)

        # Create schema if needed
        if not os.path.exists(db_path):
            from .schema import DatabaseSchema
            DatabaseSchema.create_all_tables(db_path)

    @contextmanager
    def get_connection(self):
        """Get database connection as context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            # For SELECT queries
            if query.strip().upper().startswith('SELECT'):
                return [dict(row) for row in cursor.fetchall()]

            # For INSERT/UPDATE/DELETE
            return [{'id': cursor.lastrowid, 'rowcount': cursor.rowcount}]

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute same query with multiple parameter sets"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            return cursor.rowcount

    def get_by_id(self, table: str, id: int) -> Optional[Dict]:
        """Get single record by ID"""
        results = self.execute(f"SELECT * FROM {table} WHERE id = ?", (id,))
        return results[0] if results else None

    def insert(self, table: str, data: Dict) -> int:
        """Insert record and return ID"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        result = self.execute(query, tuple(data.values()))
        return result[0]['id']

    def update(self, table: str, id: int, data: Dict) -> bool:
        """Update record by ID"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"

        result = self.execute(query, tuple(data.values()) + (id,))
        return result[0]['rowcount'] > 0

    def delete(self, table: str, id: int, soft: bool = True) -> bool:
        """Delete record by ID (soft delete by default)"""
        if soft:
            query = f"UPDATE {table} SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?"
        else:
            query = f"DELETE FROM {table} WHERE id = ?"

        result = self.execute(query, (id,))
        return result[0]['rowcount'] > 0

    def search(self, table: str, conditions: Dict, limit: int = 100) -> List[Dict]:
        """Search records with conditions"""
        where_clauses = []
        params = []

        for key, value in conditions.items():
            if value is None:
                where_clauses.append(f"{key} IS NULL")
            elif isinstance(value, (list, tuple)):
                placeholders = ', '.join(['?' for _ in value])
                where_clauses.append(f"{key} IN ({placeholders})")
                params.extend(value)
            else:
                where_clauses.append(f"{key} = ?")
                params.append(value)

        where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
        query = f"SELECT * FROM {table} WHERE {where_sql} AND deleted_at IS NULL LIMIT ?"
        params.append(limit)

        return self.execute(query, tuple(params))

    def count(self, table: str, conditions: Dict = None) -> int:
        """Count records matching conditions"""
        if conditions:
            where_clauses = [f"{k} = ?" for k in conditions.keys()]
            where_sql = ' AND '.join(where_clauses)
            query = f"SELECT COUNT(*) as count FROM {table} WHERE {where_sql} AND deleted_at IS NULL"
            result = self.execute(query, tuple(conditions.values()))
        else:
            query = f"SELECT COUNT(*) as count FROM {table} WHERE deleted_at IS NULL"
            result = self.execute(query)

        return result[0]['count'] if result else 0

    # ========================================================================
    # JOB-SPECIFIC METHODS
    # ========================================================================

    def get_next_job_number(self) -> str:
        """Generate next job number (JOB-2024-0001 format)"""
        year = datetime.now().year
        prefix = f"JOB-{year}-"

        result = self.execute("""
            SELECT job_number FROM jobs
            WHERE job_number LIKE ?
            ORDER BY id DESC LIMIT 1
        """, (f"{prefix}%",))

        if result:
            last_num = int(result[0]['job_number'].split('-')[-1])
            return f"{prefix}{last_num + 1:04d}"
        else:
            return f"{prefix}0001"

    def get_jobs_by_status(self, status: str, location_id: int = None) -> List[Dict]:
        """Get all jobs with a specific status"""
        if location_id:
            return self.execute("""
                SELECT j.*, c.first_name, c.last_name, c.phone, c.email,
                       v.year, v.make, v.model, v.color
                FROM jobs j
                JOIN customers c ON j.customer_id = c.id
                JOIN vehicles v ON j.vehicle_id = v.id
                WHERE j.status = ? AND j.location_id = ? AND j.deleted_at IS NULL
                ORDER BY j.created_at DESC
            """, (status, location_id))
        else:
            return self.execute("""
                SELECT j.*, c.first_name, c.last_name, c.phone, c.email,
                       v.year, v.make, v.model, v.color
                FROM jobs j
                JOIN customers c ON j.customer_id = c.id
                JOIN vehicles v ON j.vehicle_id = v.id
                WHERE j.status = ? AND j.deleted_at IS NULL
                ORDER BY j.created_at DESC
            """, (status,))

    def update_job_status(self, job_id: int, new_status: str, changed_by: str = None, notes: str = None) -> bool:
        """Update job status and record history"""
        # Get current status
        job = self.get_by_id('jobs', job_id)
        if not job:
            return False

        old_status = job['status']

        # Update job
        self.execute("""
            UPDATE jobs SET
                status = ?,
                status_changed_at = CURRENT_TIMESTAMP,
                status_changed_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, changed_by, job_id))

        # Record history
        self.execute("""
            INSERT INTO job_status_history (job_id, from_status, to_status, changed_by, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (job_id, old_status, new_status, changed_by, notes))

        return True

    # ========================================================================
    # INSURANCE CLAIM METHODS
    # ========================================================================

    def get_claims_needing_followup(self, days_overdue: int = 3) -> List[Dict]:
        """Get insurance claims that need follow-up"""
        return self.execute("""
            SELECT ic.*, j.job_number, c.first_name, c.last_name
            FROM insurance_claims ic
            JOIN jobs j ON j.insurance_claim_id = ic.id
            JOIN customers c ON j.customer_id = c.id
            WHERE ic.status NOT IN ('PAID', 'CLOSED')
              AND ic.auto_follow_up_enabled = 1
              AND (
                  ic.next_follow_up_date <= date('now')
                  OR (ic.last_contact_date IS NOT NULL
                      AND julianday('now') - julianday(ic.last_contact_date) > ?)
              )
              AND ic.deleted_at IS NULL
            ORDER BY ic.next_follow_up_date ASC
        """, (days_overdue,))

    def record_adjuster_contact(self, claim_id: int, method: str, notes: str = None) -> bool:
        """Record contact with adjuster"""
        return self.execute("""
            UPDATE insurance_claims SET
                last_contact_date = date('now'),
                last_contact_method = ?,
                follow_up_count = follow_up_count + 1,
                next_follow_up_date = date('now', '+3 days'),
                adjuster_notes = CASE
                    WHEN adjuster_notes IS NULL THEN ?
                    ELSE adjuster_notes || char(10) || datetime('now') || ': ' || ?
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (method, notes or '', notes or '', claim_id))[0]['rowcount'] > 0

    # ========================================================================
    # TECH METHODS
    # ========================================================================

    def get_tech_workload(self, tech_id: int) -> Dict:
        """Get technician's current workload"""
        jobs = self.execute("""
            SELECT j.*, c.first_name, c.last_name,
                   v.year, v.make, v.model
            FROM jobs j
            JOIN customers c ON j.customer_id = c.id
            JOIN vehicles v ON j.vehicle_id = v.id
            WHERE j.assigned_tech_id = ?
              AND j.status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
              AND j.deleted_at IS NULL
            ORDER BY j.priority DESC, j.scheduled_pickup ASC
        """, (tech_id,))

        total_hours = sum(j['estimated_hours'] or 0 for j in jobs)

        return {
            'tech_id': tech_id,
            'active_jobs': len(jobs),
            'total_estimated_hours': total_hours,
            'jobs': jobs
        }

    def assign_job_to_tech(self, job_id: int, tech_id: int, estimated_hours: float = None) -> bool:
        """Assign a job to a technician"""
        # Update job
        self.execute("""
            UPDATE jobs SET
                assigned_tech_id = ?,
                assigned_at = CURRENT_TIMESTAMP,
                estimated_hours = COALESCE(?, estimated_hours),
                status = CASE WHEN status = 'PARTS_RECEIVED' OR status = 'APPROVED'
                             THEN 'ASSIGNED_TO_TECH' ELSE status END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (tech_id, estimated_hours, job_id))

        # Update tech job count
        self.execute("""
            UPDATE technicians SET
                current_job_count = (
                    SELECT COUNT(*) FROM jobs
                    WHERE assigned_tech_id = ?
                    AND status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
                    AND deleted_at IS NULL
                )
            WHERE id = ?
        """, (tech_id, tech_id))

        return True

    # ========================================================================
    # REPORTING METHODS
    # ========================================================================

    def get_job_summary(self, location_id: int = None, days: int = 30) -> Dict:
        """Get summary of jobs for reporting"""
        location_filter = "AND j.location_id = ?" if location_id else ""
        params = (days, location_id) if location_id else (days,)

        result = self.execute(f"""
            SELECT
                COUNT(*) as total_jobs,
                SUM(CASE WHEN status = 'COMPLETED' OR status = 'PAID' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status LIKE 'WAITING%' THEN 1 ELSE 0 END) as waiting,
                SUM(total_actual) as total_revenue,
                AVG(total_actual) as avg_job_value
            FROM jobs j
            WHERE j.created_at >= date('now', '-' || ? || ' days')
              AND j.deleted_at IS NULL
              {location_filter}
        """, params)

        return result[0] if result else {}

    def get_revenue_breakdown(self, start_date: str, end_date: str) -> List[Dict]:
        """Get revenue breakdown for a period"""
        return self.execute("""
            SELECT
                p.payment_date,
                SUM(p.total_amount) as total,
                SUM(p.insurance_portion) as insurance,
                SUM(p.parts_cost) as parts,
                SUM(p.sales_team_cut) as sales,
                SUM(p.tech_cut) as tech,
                SUM(p.office_cut) as office,
                SUM(p.shop_profit) as profit
            FROM payments p
            WHERE p.payment_date BETWEEN ? AND ?
            GROUP BY p.payment_date
            ORDER BY p.payment_date DESC
        """, (start_date, end_date))
