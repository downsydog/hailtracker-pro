"""
Tech Manager
Backend API for tech mobile app

PDR CRM Part 8 - Mobile Tech App!

FEATURES:
- View assigned jobs (current/upcoming/completed)
- Start jobs
- Log progress updates
- Mark jobs complete
- View schedule
- Performance statistics
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta


class TechManager:
    """
    Manage tech-specific operations

    Provides data for tech mobile app
    """

    def __init__(self, db):
        """Initialize tech manager with database connection"""
        self.db = db

    # ========================================================================
    # TECH INFO
    # ========================================================================

    def get_tech(self, tech_id: int) -> Optional[Dict]:
        """Get tech details with current workload"""
        query = """
            SELECT
                t.*,
                l.name as location_name,
                COUNT(DISTINCT j.id) as active_jobs,
                COALESCE(SUM(j.estimated_hours), 0) as total_hours
            FROM technicians t
            LEFT JOIN locations l ON l.id = t.location_id
            LEFT JOIN jobs j ON j.assigned_tech_id = t.id
                AND j.status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
                AND j.deleted_at IS NULL
            WHERE t.id = ? AND t.deleted_at IS NULL
            GROUP BY t.id
        """

        results = self.db.execute(query, (tech_id,))
        return results[0] if results else None

    def get_tech_by_employee_id(self, employee_id: str) -> Optional[Dict]:
        """Get tech by employee ID (for login)"""
        results = self.db.execute("""
            SELECT * FROM technicians
            WHERE employee_id = ? AND deleted_at IS NULL AND status = 'ACTIVE'
        """, (employee_id,))

        return results[0] if results else None

    def get_tech_by_user_id(self, user_id: int) -> Optional[Dict]:
        """Get technician record linked to a user account"""
        # First try by user_id column
        try:
            results = self.db.execute("""
                SELECT * FROM technicians
                WHERE user_id = ? AND deleted_at IS NULL AND status = 'ACTIVE'
            """, (user_id,))
            if results:
                return results[0]
        except:
            pass  # Column might not exist

        # Fallback: Look up by email
        user = self.db.execute("SELECT email FROM users_new WHERE id = ?", (user_id,))
        if user:
            email = user[0]['email']
            results = self.db.execute("""
                SELECT * FROM technicians
                WHERE email = ? AND deleted_at IS NULL AND status = 'ACTIVE'
            """, (email,))
            if results:
                return results[0]

        return None

    def get_tech_by_email(self, email: str) -> Optional[Dict]:
        """Get technician record by email"""
        results = self.db.execute("""
            SELECT * FROM technicians
            WHERE email = ? AND deleted_at IS NULL AND status = 'ACTIVE'
        """, (email,))
        return results[0] if results else None

    def link_user_to_technician(self, user_id: int, technician_id: int) -> bool:
        """Link a user account to a technician record"""
        # Add user_id column if it doesn't exist
        try:
            self.db.execute("""
                ALTER TABLE technicians ADD COLUMN user_id INTEGER
            """)
        except:
            pass  # Column already exists

        # Update the technician record
        self.db.execute("""
            UPDATE technicians SET user_id = ?, updated_at = ? WHERE id = ?
        """, (user_id, datetime.now().isoformat(), technician_id))

        print(f"[OK] Linked user #{user_id} to technician #{technician_id}")
        return True

    def get_all_techs(self, active_only: bool = True) -> List[Dict]:
        """Get all technicians"""
        query = """
            SELECT
                t.*,
                COUNT(DISTINCT j.id) as active_jobs
            FROM technicians t
            LEFT JOIN jobs j ON j.assigned_tech_id = t.id
                AND j.status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
                AND j.deleted_at IS NULL
            WHERE t.deleted_at IS NULL
        """

        if active_only:
            query += " AND t.status = 'ACTIVE'"

        query += " GROUP BY t.id ORDER BY t.first_name, t.last_name"

        return self.db.execute(query)

    # ========================================================================
    # TECH JOBS
    # ========================================================================

    def get_tech_jobs(
        self,
        tech_id: int,
        status_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Get jobs assigned to tech

        Args:
            tech_id: Technician ID
            status_filter: Filter by status category
                - CURRENT: IN_PROGRESS
                - UPCOMING: ASSIGNED_TO_TECH
                - COMPLETED: TECH_COMPLETE and beyond
                - None: All active (not completed/paid)

        Returns:
            List of jobs with customer and vehicle info
        """
        query = """
            SELECT
                j.*,
                c.first_name || ' ' || c.last_name as customer_name,
                c.phone as customer_phone,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
                v.color as vehicle_color,
                v.license_plate,
                ic.claim_number,
                ic.insurance_company
            FROM jobs j
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            LEFT JOIN insurance_claims ic ON ic.id = j.insurance_claim_id
            WHERE j.assigned_tech_id = ?
              AND j.deleted_at IS NULL
        """

        params = [tech_id]

        if status_filter == 'CURRENT':
            query += " AND j.status = 'IN_PROGRESS'"
        elif status_filter == 'UPCOMING':
            query += " AND j.status = 'ASSIGNED_TO_TECH'"
        elif status_filter == 'COMPLETED':
            query += """ AND j.status IN (
                'TECH_COMPLETE', 'WAITING_QC', 'QC_COMPLETE',
                'WAITING_DETAIL', 'DETAIL_COMPLETE', 'READY_FOR_PICKUP',
                'COMPLETED', 'INVOICED', 'PAID'
            )"""
        else:
            # All active (not fully completed)
            query += " AND j.status NOT IN ('COMPLETED', 'INVOICED', 'PAID')"

        query += " ORDER BY j.priority DESC, j.scheduled_drop_off ASC"

        return self.db.execute(query, tuple(params))

    def get_job_details(self, job_id: int, tech_id: int) -> Optional[Dict]:
        """
        Get detailed job info for tech

        Verifies job is assigned to this tech
        """
        query = """
            SELECT
                j.*,
                c.first_name || ' ' || c.last_name as customer_name,
                c.phone as customer_phone,
                c.email as customer_email,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
                v.color as vehicle_color,
                v.vin,
                v.license_plate,
                ic.claim_number,
                ic.insurance_company,
                ic.adjuster_name
            FROM jobs j
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            LEFT JOIN insurance_claims ic ON ic.id = j.insurance_claim_id
            WHERE j.id = ?
              AND j.assigned_tech_id = ?
              AND j.deleted_at IS NULL
        """

        results = self.db.execute(query, (job_id, tech_id))
        return results[0] if results else None

    # ========================================================================
    # TECH ACTIONS (MOBILE)
    # ========================================================================

    def start_job(self, job_id: int, tech_id: int) -> bool:
        """
        Tech starts working on job

        Changes status from ASSIGNED_TO_TECH to IN_PROGRESS
        """
        # Verify job is assigned to this tech
        job = self.get_job_details(job_id, tech_id)

        if not job:
            raise ValueError(f"Job {job_id} not found or not assigned to tech {tech_id}")

        if job['status'] != 'ASSIGNED_TO_TECH':
            raise ValueError(f"Job must be in ASSIGNED_TO_TECH status (current: {job['status']})")

        now = datetime.now().isoformat()

        # Update job status
        self.db.execute("""
            UPDATE jobs
            SET status = 'IN_PROGRESS',
                status_changed_at = ?,
                status_changed_by = ?,
                updated_at = ?
            WHERE id = ?
        """, (now, f'tech_{tech_id}', now, job_id))

        # Log status change
        self.db.execute("""
            INSERT INTO job_status_history (
                job_id, status,
                changed_by, changed_at, notes
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            job_id,
            'IN_PROGRESS',
            f'tech_{tech_id}',
            now,
            'Tech started work via mobile app'
        ))

        print(f"[OK] Tech started job #{job['job_number']}")

        return True

    def update_progress(
        self,
        job_id: int,
        tech_id: int,
        progress_note: str,
        hours_remaining: Optional[float] = None
    ) -> bool:
        """
        Tech logs progress update

        Args:
            job_id: Job ID
            tech_id: Tech ID
            progress_note: What was done / what's left
            hours_remaining: Estimated hours remaining
        """
        # Verify access
        job = self.get_job_details(job_id, tech_id)
        if not job:
            raise ValueError(f"Job {job_id} not found or not assigned to tech {tech_id}")

        if job['status'] not in ('IN_PROGRESS', 'ASSIGNED_TO_TECH'):
            raise ValueError(f"Cannot update progress on job in {job['status']} status")

        # Get current notes
        current_notes = job.get('tech_notes', '') or ''

        # Append new note with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_note = f"[{timestamp}] {progress_note}"

        updated_notes = f"{current_notes}\n{new_note}".strip()

        # Calculate estimated completion if hours provided
        estimated_completion = None
        if hours_remaining:
            days_needed = hours_remaining / 8  # 8 hour work days
            estimated_completion = (date.today() + timedelta(days=max(1, int(days_needed)))).isoformat()

        now = datetime.now().isoformat()

        self.db.execute("""
            UPDATE jobs
            SET tech_notes = ?,
                tech_daily_update = ?,
                last_tech_update = ?,
                estimated_hours = COALESCE(?, estimated_hours),
                estimated_completion_date = COALESCE(?, estimated_completion_date),
                updated_at = ?
            WHERE id = ?
        """, (
            updated_notes,
            progress_note,
            now,
            hours_remaining,
            estimated_completion,
            now,
            job_id
        ))

        print(f"[OK] Progress logged for job #{job['job_number']}")
        if hours_remaining:
            print(f"     Remaining: {hours_remaining} hours")

        return True

    def mark_complete(
        self,
        job_id: int,
        tech_id: int,
        completion_notes: Optional[str] = None
    ) -> bool:
        """
        Tech marks job complete

        Changes status from IN_PROGRESS to TECH_COMPLETE
        """
        # Verify access
        job = self.get_job_details(job_id, tech_id)
        if not job:
            raise ValueError(f"Job {job_id} not found or not assigned to tech {tech_id}")

        if job['status'] != 'IN_PROGRESS':
            raise ValueError(f"Job must be IN_PROGRESS to mark complete (current: {job['status']})")

        now = datetime.now().isoformat()

        # Update status
        self.db.execute("""
            UPDATE jobs
            SET status = 'TECH_COMPLETE',
                status_changed_at = ?,
                status_changed_by = ?,
                updated_at = ?
            WHERE id = ?
        """, (now, f'tech_{tech_id}', now, job_id))

        # Log status change
        self.db.execute("""
            INSERT INTO job_status_history (
                job_id, status,
                changed_by, changed_at, notes
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            job_id,
            'TECH_COMPLETE',
            f'tech_{tech_id}',
            now,
            completion_notes or 'Tech marked complete via mobile app'
        ))

        # Add completion note to tech notes
        if completion_notes:
            current_notes = job.get('tech_notes', '') or ''
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            final_note = f"\n[{timestamp}] COMPLETED: {completion_notes}"

            self.db.execute("""
                UPDATE jobs SET tech_notes = ? WHERE id = ?
            """, (current_notes + final_note, job_id))

        print(f"[OK] Job #{job['job_number']} marked complete")

        return True

    # ========================================================================
    # TECH SCHEDULE
    # ========================================================================

    def get_schedule(
        self,
        tech_id: int,
        days_ahead: int = 7
    ) -> List[Dict]:
        """
        Get tech's schedule for next X days

        Shows upcoming jobs and when they're scheduled
        """
        end_date = date.today() + timedelta(days=days_ahead)

        query = """
            SELECT
                j.id,
                j.job_number,
                j.status,
                j.priority,
                j.scheduled_drop_off,
                j.estimated_completion_date,
                j.estimated_hours,
                c.first_name || ' ' || c.last_name as customer_name,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
                v.color as vehicle_color
            FROM jobs j
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            WHERE j.assigned_tech_id = ?
              AND j.deleted_at IS NULL
              AND j.status NOT IN ('COMPLETED', 'INVOICED', 'PAID')
              AND (
                  DATE(j.scheduled_drop_off) <= ?
                  OR j.status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
              )
            ORDER BY
                CASE j.status
                    WHEN 'IN_PROGRESS' THEN 1
                    WHEN 'ASSIGNED_TO_TECH' THEN 2
                    ELSE 3
                END,
                j.priority DESC,
                j.scheduled_drop_off ASC
        """

        return self.db.execute(query, (tech_id, end_date.isoformat()))

    # ========================================================================
    # TECH STATS
    # ========================================================================

    def get_tech_stats(
        self,
        tech_id: int,
        period_days: int = 30
    ) -> Dict:
        """
        Get tech performance stats

        Shows jobs completed, hours worked, etc.
        """
        start_date = date.today() - timedelta(days=period_days)
        week_start = date.today() - timedelta(days=date.today().weekday())

        stats = {}

        # Jobs completed in period
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM job_status_history jsh
            JOIN jobs j ON j.id = jsh.job_id
            WHERE j.assigned_tech_id = ?
              AND jsh.status = 'TECH_COMPLETE'
              AND DATE(jsh.changed_at) >= ?
        """, (tech_id, start_date.isoformat()))
        stats['jobs_completed'] = result[0]['count']

        # Currently active
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM jobs
            WHERE assigned_tech_id = ?
              AND deleted_at IS NULL
              AND status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
        """, (tech_id,))
        stats['jobs_active'] = result[0]['count']

        # This week completed
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM job_status_history jsh
            JOIN jobs j ON j.id = jsh.job_id
            WHERE j.assigned_tech_id = ?
              AND jsh.status = 'TECH_COMPLETE'
              AND DATE(jsh.changed_at) >= ?
        """, (tech_id, week_start.isoformat()))
        stats['week_completed'] = result[0]['count']

        # Average hours per job (for completed jobs in period)
        result = self.db.execute("""
            SELECT AVG(j.estimated_hours) as avg_hours
            FROM job_status_history jsh
            JOIN jobs j ON j.id = jsh.job_id
            WHERE j.assigned_tech_id = ?
              AND jsh.status = 'TECH_COMPLETE'
              AND DATE(jsh.changed_at) >= ?
              AND j.estimated_hours IS NOT NULL
        """, (tech_id, start_date.isoformat()))
        stats['avg_hours_per_job'] = round(result[0]['avg_hours'] or 0, 1)

        # Total hours estimated in period
        result = self.db.execute("""
            SELECT SUM(j.estimated_hours) as total_hours
            FROM job_status_history jsh
            JOIN jobs j ON j.id = jsh.job_id
            WHERE j.assigned_tech_id = ?
              AND jsh.status = 'TECH_COMPLETE'
              AND DATE(jsh.changed_at) >= ?
        """, (tech_id, start_date.isoformat()))
        stats['total_hours'] = round(result[0]['total_hours'] or 0, 1)

        return stats

    def get_tech_dashboard(self, tech_id: int) -> Dict:
        """
        Get complete dashboard data for tech mobile app

        Returns all data needed for main screen
        """
        tech = self.get_tech(tech_id)
        if not tech:
            return None

        return {
            'tech': tech,
            'stats': self.get_tech_stats(tech_id),
            'current_jobs': self.get_tech_jobs(tech_id, 'CURRENT'),
            'upcoming_jobs': self.get_tech_jobs(tech_id, 'UPCOMING'),
            'schedule': self.get_schedule(tech_id, days_ahead=7)
        }

    # ========================================================================
    # TECH MANAGEMENT (ADMIN)
    # ========================================================================

    def create_tech(
        self,
        first_name: str,
        last_name: str,
        employee_id: str,
        skill_level: str = 'INTERMEDIATE',
        max_jobs_concurrent: int = 3,
        location_id: Optional[int] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> int:
        """Create a new technician"""
        tech_data = {
            'first_name': first_name,
            'last_name': last_name,
            'employee_id': employee_id,
            'skill_level': skill_level,
            'max_jobs_concurrent': max_jobs_concurrent,
            'location_id': location_id,
            'email': email,
            'phone': phone,
            'status': 'ACTIVE',
            'current_job_count': 0
        }

        tech_id = self.db.insert('technicians', tech_data)

        print(f"[OK] Created technician: {first_name} {last_name} ({employee_id})")

        return tech_id

    def update_tech(self, tech_id: int, data: Dict) -> bool:
        """Update technician info"""
        return self.db.update('technicians', tech_id, data)

    def get_workload_summary(self) -> List[Dict]:
        """Get workload summary for all techs"""
        query = """
            SELECT
                t.id,
                t.first_name || ' ' || t.last_name as tech_name,
                t.skill_level,
                t.max_jobs_concurrent,
                COUNT(CASE WHEN j.status = 'IN_PROGRESS' THEN 1 END) as in_progress,
                COUNT(CASE WHEN j.status = 'ASSIGNED_TO_TECH' THEN 1 END) as assigned,
                SUM(CASE WHEN j.status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
                    THEN j.estimated_hours ELSE 0 END) as total_hours
            FROM technicians t
            LEFT JOIN jobs j ON j.assigned_tech_id = t.id
                AND j.deleted_at IS NULL
            WHERE t.deleted_at IS NULL AND t.status = 'ACTIVE'
            GROUP BY t.id
            ORDER BY total_hours DESC
        """

        return self.db.execute(query)
