"""
CRM Database Manager
Handles all CRM-related database operations
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

class CRMDatabase:
    """Manage CRM database operations"""

    def __init__(self, db_path='data/hailtracker_crm.db'):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database and tables if they don't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Read schema file
        schema_path = os.path.join(os.path.dirname(__file__), 'crm_schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema = f.read()

            # Execute schema
            conn = sqlite3.connect(self.db_path)
            conn.executescript(schema)
            conn.commit()
            conn.close()

            print(f"CRM database initialized: {self.db_path}")

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ========================================================================
    # INTERACTIONS
    # ========================================================================

    def log_interaction(self, location_id: int, interaction_type: str,
                       outcome: str = None, notes: str = None,
                       user_id: int = None, duration_seconds: int = None,
                       next_followup_date: str = None) -> int:
        """Log a customer interaction"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO interactions (
                location_id, user_id, interaction_type, outcome,
                notes, duration_seconds, next_followup_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (location_id, user_id, interaction_type, outcome,
              notes, duration_seconds, next_followup_date))

        interaction_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return interaction_id

    def get_location_interactions(self, location_id: int, limit: int = 50) -> List[Dict]:
        """Get all interactions for a location"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM interactions
            WHERE location_id = ?
            ORDER BY interaction_date DESC
            LIMIT ?
        """, (location_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_recent_interactions(self, days: int = 7, limit: int = 100) -> List[Dict]:
        """Get recent interactions across all locations"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT i.*, u.full_name as user_name
            FROM interactions i
            LEFT JOIN users u ON i.user_id = u.id
            WHERE i.interaction_date >= datetime('now', ?)
            ORDER BY i.interaction_date DESC
            LIMIT ?
        """, (f'-{days} days', limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========================================================================
    # DEALS
    # ========================================================================

    def create_deal(self, location_id: int, event_id: int = None,
                   stage: str = 'lead', estimated_value: float = 0,
                   probability: int = 0, assigned_to: int = None,
                   expected_close_date: str = None) -> int:
        """Create a new deal"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO deals (
                location_id, event_id, stage, estimated_value,
                probability, assigned_to, expected_close_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (location_id, event_id, stage, estimated_value,
              probability, assigned_to, expected_close_date))

        deal_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return deal_id

    def update_deal_stage(self, deal_id: int, stage: str,
                         actual_value: float = None, lost_reason: str = None):
        """Update deal stage"""

        conn = self.get_connection()
        cursor = conn.cursor()

        # If moving to won/lost, set close date
        actual_close_date = None
        if stage in ['won', 'lost']:
            actual_close_date = datetime.now().strftime('%Y-%m-%d')

        cursor.execute("""
            UPDATE deals
            SET stage = ?,
                actual_value = COALESCE(?, actual_value),
                actual_close_date = COALESCE(?, actual_close_date),
                lost_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (stage, actual_value, actual_close_date, lost_reason, deal_id))

        conn.commit()
        conn.close()

    def get_deal(self, deal_id: int) -> Optional[Dict]:
        """Get a single deal by ID"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT d.*, u.full_name as assigned_name
            FROM deals d
            LEFT JOIN users u ON d.assigned_to = u.id
            WHERE d.id = ?
        """, (deal_id,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_deals_by_stage(self, stage: str = None) -> List[Dict]:
        """Get deals by stage (or all if None)"""

        conn = self.get_connection()
        cursor = conn.cursor()

        if stage:
            cursor.execute("""
                SELECT d.*, u.full_name as assigned_name
                FROM deals d
                LEFT JOIN users u ON d.assigned_to = u.id
                WHERE d.stage = ?
                ORDER BY d.updated_at DESC
            """, (stage,))
        else:
            cursor.execute("""
                SELECT d.*, u.full_name as assigned_name
                FROM deals d
                LEFT JOIN users u ON d.assigned_to = u.id
                ORDER BY d.updated_at DESC
            """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_deals_by_location(self, location_id: int) -> List[Dict]:
        """Get all deals for a location"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT d.*, u.full_name as assigned_name
            FROM deals d
            LEFT JOIN users u ON d.assigned_to = u.id
            WHERE d.location_id = ?
            ORDER BY d.created_at DESC
        """, (location_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_pipeline_summary(self) -> Dict:
        """Get deal pipeline summary"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                stage,
                COUNT(*) as count,
                COALESCE(SUM(estimated_value), 0) as total_value,
                COALESCE(AVG(probability), 0) as avg_probability
            FROM deals
            WHERE stage NOT IN ('won', 'lost')
            GROUP BY stage
        """)

        rows = cursor.fetchall()
        conn.close()

        stages = [dict(row) for row in rows]

        summary = {
            'stages': stages,
            'total_deals': sum(row['count'] for row in stages),
            'total_value': sum(row['total_value'] or 0 for row in stages)
        }

        return summary

    # ========================================================================
    # TASKS
    # ========================================================================

    def create_task(self, title: str, task_type: str,
                   location_id: int = None, deal_id: int = None,
                   assigned_to: int = None, due_date: str = None,
                   priority: str = 'medium', description: str = None) -> int:
        """Create a new task"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO tasks (
                location_id, deal_id, assigned_to, task_type,
                title, description, due_date, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (location_id, deal_id, assigned_to, task_type,
              title, description, due_date, priority))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return task_id

    def update_task_status(self, task_id: int, status: str):
        """Update task status"""

        conn = self.get_connection()
        cursor = conn.cursor()

        completed_at = None
        if status == 'completed':
            completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute("""
            UPDATE tasks
            SET status = ?,
                completed_at = COALESCE(?, completed_at)
            WHERE id = ?
        """, (status, completed_at, task_id))

        conn.commit()
        conn.close()

    def complete_task(self, task_id: int):
        """Mark task as completed"""
        self.update_task_status(task_id, 'completed')

    def get_task(self, task_id: int) -> Optional[Dict]:
        """Get a single task by ID"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.*, u.full_name as assigned_name
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            WHERE t.id = ?
        """, (task_id,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_tasks(self, assigned_to: int = None, status: str = 'pending',
                 due_soon: bool = False, limit: int = 100) -> List[Dict]:
        """Get tasks (optionally filtered)"""

        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT t.*, u.full_name as assigned_name
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            WHERE 1=1
        """
        params = []

        if assigned_to:
            query += " AND t.assigned_to = ?"
            params.append(assigned_to)

        if status:
            query += " AND t.status = ?"
            params.append(status)

        if due_soon:
            next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            query += " AND t.due_date <= ?"
            params.append(next_week)

        query += " ORDER BY t.due_date ASC, t.priority DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_overdue_tasks(self) -> List[Dict]:
        """Get all overdue tasks"""

        conn = self.get_connection()
        cursor = conn.cursor()

        today = datetime.now().strftime('%Y-%m-%d')

        cursor.execute("""
            SELECT t.*, u.full_name as assigned_name
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            WHERE t.status = 'pending'
              AND t.due_date < ?
            ORDER BY t.due_date ASC
        """, (today,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========================================================================
    # USERS
    # ========================================================================

    def create_user(self, name: str, email: str, role: str,
                   phone: str = None) -> int:
        """Create a new user"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (name, email, role, phone)
            VALUES (?, ?, ?, ?)
        """, (name, email, role, phone))

        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return user_id

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_users(self, active_only: bool = True) -> List[Dict]:
        """Get all users"""

        conn = self.get_connection()
        cursor = conn.cursor()

        if active_only:
            cursor.execute("SELECT * FROM users WHERE active = 1 ORDER BY name")
        else:
            cursor.execute("SELECT * FROM users ORDER BY name")

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========================================================================
    # NOTES
    # ========================================================================

    def add_note(self, note_text: str, location_id: int = None,
                deal_id: int = None, user_id: int = None,
                attachment_path: str = None) -> int:
        """Add a note"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO notes (location_id, deal_id, user_id, note_text, attachment_path)
            VALUES (?, ?, ?, ?, ?)
        """, (location_id, deal_id, user_id, note_text, attachment_path))

        note_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return note_id

    def get_notes(self, location_id: int = None, deal_id: int = None,
                 limit: int = 50) -> List[Dict]:
        """Get notes for a location or deal"""

        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT n.*, u.full_name as user_name
            FROM notes n
            LEFT JOIN users u ON n.user_id = u.id
            WHERE 1=1
        """
        params = []

        if location_id:
            query += " AND n.location_id = ?"
            params.append(location_id)

        if deal_id:
            query += " AND n.deal_id = ?"
            params.append(deal_id)

        query += " ORDER BY n.created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========================================================================
    # ANALYTICS
    # ========================================================================

    def get_conversion_funnel(self) -> Dict:
        """Get conversion funnel statistics"""

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(CASE WHEN stage = 'lead' THEN 1 END) as leads,
                COUNT(CASE WHEN stage = 'contacted' THEN 1 END) as contacted,
                COUNT(CASE WHEN stage = 'qualified' THEN 1 END) as qualified,
                COUNT(CASE WHEN stage = 'quoted' THEN 1 END) as quoted,
                COUNT(CASE WHEN stage = 'negotiating' THEN 1 END) as negotiating,
                COUNT(CASE WHEN stage = 'won' THEN 1 END) as won,
                COUNT(CASE WHEN stage = 'lost' THEN 1 END) as lost
            FROM deals
        """)

        row = cursor.fetchone()
        conn.close()

        stats = dict(row)

        # Calculate conversion rates
        total_leads = stats['leads'] + stats['contacted'] + stats['qualified'] + \
                     stats['quoted'] + stats['negotiating'] + stats['won'] + stats['lost']

        if total_leads > 0:
            stats['lead_to_contact_rate'] = round((stats['contacted'] + stats['qualified'] +
                stats['quoted'] + stats['negotiating'] + stats['won']) / total_leads * 100, 1)
            stats['lead_to_won_rate'] = round(stats['won'] / total_leads * 100, 1)
        else:
            stats['lead_to_contact_rate'] = 0
            stats['lead_to_won_rate'] = 0

        stats['total_in_pipeline'] = total_leads - stats['won'] - stats['lost']

        return stats

    def get_revenue_by_period(self, period: str = 'month', limit: int = 12) -> List[Dict]:
        """Get revenue by time period"""

        conn = self.get_connection()
        cursor = conn.cursor()

        if period == 'month':
            date_format = '%Y-%m'
        elif period == 'week':
            date_format = '%Y-W%W'
        else:  # day
            date_format = '%Y-%m-%d'

        cursor.execute(f"""
            SELECT
                strftime('{date_format}', actual_close_date) as period,
                COUNT(*) as deals_won,
                COALESCE(SUM(actual_value), 0) as revenue
            FROM deals
            WHERE stage = 'won' AND actual_close_date IS NOT NULL
            GROUP BY period
            ORDER BY period DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_user_performance(self, user_id: int = None, days: int = 30) -> List[Dict]:
        """Get user performance metrics"""

        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                u.id as user_id,
                u.full_name,
                COUNT(DISTINCT i.id) as interactions,
                COUNT(DISTINCT CASE WHEN i.interaction_type = 'call' THEN i.id END) as calls,
                COUNT(DISTINCT CASE WHEN i.interaction_type = 'email' THEN i.id END) as emails,
                COUNT(DISTINCT CASE WHEN i.interaction_type = 'visit' THEN i.id END) as visits,
                COUNT(DISTINCT d.id) as deals_created,
                COUNT(DISTINCT CASE WHEN d.stage = 'won' THEN d.id END) as deals_won,
                COALESCE(SUM(CASE WHEN d.stage = 'won' THEN d.actual_value END), 0) as revenue
            FROM users u
            LEFT JOIN interactions i ON u.id = i.user_id
                AND i.interaction_date >= datetime('now', ?)
            LEFT JOIN deals d ON u.id = d.assigned_to
                AND d.created_at >= datetime('now', ?)
            WHERE u.active = 1
        """
        params = [f'-{days} days', f'-{days} days']

        if user_id:
            query += " AND u.id = ?"
            params.append(user_id)

        query += " GROUP BY u.id, u.full_name ORDER BY revenue DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_activity_summary(self, days: int = 7) -> Dict:
        """Get activity summary for dashboard"""

        conn = self.get_connection()
        cursor = conn.cursor()

        date_filter = f'-{days} days'

        # Interactions count
        cursor.execute("""
            SELECT COUNT(*) as count FROM interactions
            WHERE interaction_date >= datetime('now', ?)
        """, (date_filter,))
        interactions = cursor.fetchone()['count']

        # New deals
        cursor.execute("""
            SELECT COUNT(*) as count FROM deals
            WHERE created_at >= datetime('now', ?)
        """, (date_filter,))
        new_deals = cursor.fetchone()['count']

        # Deals won
        cursor.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(actual_value), 0) as revenue
            FROM deals
            WHERE stage = 'won' AND actual_close_date >= date('now', ?)
        """, (date_filter,))
        won_row = cursor.fetchone()
        deals_won = won_row['count']
        revenue = won_row['revenue']

        # Tasks completed
        cursor.execute("""
            SELECT COUNT(*) as count FROM tasks
            WHERE status = 'completed' AND completed_at >= datetime('now', ?)
        """, (date_filter,))
        tasks_completed = cursor.fetchone()['count']

        # Pending tasks
        cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE status = 'pending'")
        pending_tasks = cursor.fetchone()['count']

        conn.close()

        return {
            'period_days': days,
            'interactions': interactions,
            'new_deals': new_deals,
            'deals_won': deals_won,
            'revenue': revenue,
            'tasks_completed': tasks_completed,
            'pending_tasks': pending_tasks
        }
