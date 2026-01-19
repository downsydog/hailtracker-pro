"""
Job Manager
Complete job workflow engine for PDR shops

WORKFLOW STAGES (25 total):
1. NEW -> Initial contact
2. WAITING_DROP_OFF -> Scheduled
3. DROPPED_OFF -> Car at shop
4. WAITING_WRITEUP -> Needs estimate
5. ESTIMATE_CREATED -> Estimate done
6. WAITING_INSURANCE -> Sent to insurance
7. WAITING_ADJUSTER -> Need adjuster response
8. ADJUSTER_SCHEDULED -> Adjuster appointment set
9. ADJUSTER_INSPECTED -> Adjuster came out
10. WAITING_APPROVAL -> Waiting approval
11. APPROVED -> Insurance approved!
12. WAITING_PARTS -> Need parts
13. PARTS_ORDERED -> Parts on order
14. PARTS_RECEIVED -> Parts arrived
15. ASSIGNED_TO_TECH -> Tech assigned
16. IN_PROGRESS -> Tech working
17. TECH_COMPLETE -> Tech finished
18. WAITING_QC -> Quality check needed
19. QC_COMPLETE -> QC passed
20. WAITING_DETAIL -> Needs detail
21. DETAIL_COMPLETE -> Detailed
22. READY_FOR_PICKUP -> Ready
23. COMPLETED -> Customer picked up
24. INVOICED -> Invoice created
25. PAID -> Payment received
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import json
import os


class JobManager:
    """
    Manage complete job lifecycle

    This is the heart of the PDR CRM system
    """

    # Valid status transitions (prevent invalid jumps)
    VALID_TRANSITIONS = {
        'NEW': ['WAITING_DROP_OFF', 'DROPPED_OFF', 'WAITING_WRITEUP'],
        'WAITING_DROP_OFF': ['DROPPED_OFF', 'NEW'],
        'DROPPED_OFF': ['WAITING_WRITEUP', 'ESTIMATE_CREATED'],
        'WAITING_WRITEUP': ['ESTIMATE_CREATED'],
        'ESTIMATE_CREATED': ['WAITING_INSURANCE', 'APPROVED', 'ASSIGNED_TO_TECH'],
        'WAITING_INSURANCE': ['WAITING_ADJUSTER', 'APPROVED'],
        'WAITING_ADJUSTER': ['ADJUSTER_SCHEDULED', 'WAITING_INSURANCE'],
        'ADJUSTER_SCHEDULED': ['ADJUSTER_INSPECTED', 'WAITING_ADJUSTER'],
        'ADJUSTER_INSPECTED': ['WAITING_APPROVAL', 'APPROVED'],
        'WAITING_APPROVAL': ['APPROVED', 'WAITING_ADJUSTER'],
        'APPROVED': ['WAITING_PARTS', 'ASSIGNED_TO_TECH'],
        'WAITING_PARTS': ['PARTS_ORDERED'],
        'PARTS_ORDERED': ['PARTS_RECEIVED', 'WAITING_PARTS'],
        'PARTS_RECEIVED': ['ASSIGNED_TO_TECH'],
        'ASSIGNED_TO_TECH': ['IN_PROGRESS'],
        'IN_PROGRESS': ['TECH_COMPLETE', 'WAITING_PARTS'],
        'TECH_COMPLETE': ['WAITING_QC'],
        'WAITING_QC': ['QC_COMPLETE', 'IN_PROGRESS'],
        'QC_COMPLETE': ['WAITING_DETAIL', 'READY_FOR_PICKUP'],
        'WAITING_DETAIL': ['DETAIL_COMPLETE'],
        'DETAIL_COMPLETE': ['READY_FOR_PICKUP'],
        'READY_FOR_PICKUP': ['COMPLETED'],
        'COMPLETED': ['INVOICED'],
        'INVOICED': ['PAID'],
        'PAID': []  # Terminal state
    }

    # Status categories for filtering
    STATUS_CATEGORIES = {
        'SCHEDULING': ['NEW', 'WAITING_DROP_OFF', 'DROPPED_OFF'],
        'ESTIMATING': ['WAITING_WRITEUP', 'ESTIMATE_CREATED'],
        'INSURANCE': ['WAITING_INSURANCE', 'WAITING_ADJUSTER', 'ADJUSTER_SCHEDULED',
                      'ADJUSTER_INSPECTED', 'WAITING_APPROVAL', 'APPROVED'],
        'PARTS': ['WAITING_PARTS', 'PARTS_ORDERED', 'PARTS_RECEIVED'],
        'PRODUCTION': ['ASSIGNED_TO_TECH', 'IN_PROGRESS', 'TECH_COMPLETE'],
        'QUALITY': ['WAITING_QC', 'QC_COMPLETE', 'WAITING_DETAIL', 'DETAIL_COMPLETE'],
        'PICKUP': ['READY_FOR_PICKUP', 'COMPLETED'],
        'BILLING': ['INVOICED', 'PAID']
    }

    def __init__(self, db, enable_notifications: bool = True):
        """
        Initialize job manager with database connection

        Args:
            db: Database connection
            enable_notifications: Whether to trigger notifications on status change
        """
        self.db = db
        self.enable_notifications = enable_notifications
        self._notification_manager = None

    def _get_notification_manager(self):
        """Get or create notification manager instance."""
        if self._notification_manager is None and self.enable_notifications:
            try:
                from src.crm.managers.job_notification_manager import JobNotificationManager
                # Get db_path from db connection
                db_path = getattr(self.db, 'db_path', None)
                if db_path:
                    self._notification_manager = JobNotificationManager(db_path)
            except ImportError:
                pass
        return self._notification_manager

    # ========================================================================
    # JOB CREATION
    # ========================================================================

    def create_job(
        self,
        customer_id: int,
        vehicle_id: int,
        job_type: str = "PDR",
        damage_type: Optional[str] = None,
        scheduled_drop_off: Optional[datetime] = None,
        location_id: Optional[int] = None,
        priority: str = "NORMAL",
        internal_notes: Optional[str] = None,
        customer_notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> int:
        """
        Create a new job

        Args:
            customer_id: Customer ID
            vehicle_id: Vehicle ID
            job_type: PDR, HAIL, CONVENTIONAL, DETAIL
            damage_type: HAIL, DOOR_DING, DENT, COLLISION
            scheduled_drop_off: When customer will drop off
            priority: URGENT, HIGH, NORMAL, LOW

        Returns:
            Job ID
        """
        # Generate job number
        job_number = self._generate_job_number()

        now = datetime.now().isoformat()

        job_data = {
            'job_number': job_number,
            'customer_id': customer_id,
            'vehicle_id': vehicle_id,
            'location_id': location_id,
            'job_type': job_type,
            'damage_type': damage_type,
            'status': 'NEW',
            'priority': priority,
            'scheduled_drop_off': scheduled_drop_off.isoformat() if scheduled_drop_off else None,
            'internal_notes': internal_notes,
            'customer_notes': customer_notes,
            'status_changed_at': now
        }

        job_id = self.db.insert('jobs', job_data)

        # Log status history
        self._log_status_change(
            job_id=job_id,
            from_status=None,
            to_status='NEW',
            changed_by=created_by,
            notes="Job created"
        )

        print(f"[OK] Created job #{job_number} (ID: {job_id})")

        return job_id

    def _generate_job_number(self) -> str:
        """Generate unique job number: JOB-2024-0001"""
        year = datetime.now().year

        # Get count of jobs this year
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM jobs
            WHERE job_number LIKE ?
        """, (f"JOB-{year}-%",))

        count = result[0]['count'] + 1

        return f"JOB-{year}-{count:04d}"

    # ========================================================================
    # STATUS MANAGEMENT (THE CORE!)
    # ========================================================================

    def update_status(
        self,
        job_id: int,
        new_status: str,
        changed_by: Optional[str] = None,
        notes: Optional[str] = None,
        validate: bool = True
    ) -> bool:
        """
        Update job status with validation

        Args:
            job_id: Job ID
            new_status: New status to set
            changed_by: Who made the change
            notes: Notes about the change
            validate: Validate status transition is allowed

        Returns:
            Success
        """
        # Get current status
        job = self.get_job(job_id)

        if not job:
            raise ValueError(f"Job {job_id} not found")

        current_status = job['status']

        # Validate transition
        if validate and current_status != new_status:
            valid_next_statuses = self.VALID_TRANSITIONS.get(current_status, [])

            if new_status not in valid_next_statuses:
                raise ValueError(
                    f"Invalid status transition: {current_status} -> {new_status}. "
                    f"Valid transitions: {', '.join(valid_next_statuses)}"
                )

        # Update status
        self.db.execute("""
            UPDATE jobs
            SET status = ?,
                status_changed_at = ?,
                status_changed_by = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            new_status,
            datetime.now().isoformat(),
            changed_by,
            datetime.now().isoformat(),
            job_id
        ))

        # Log to history
        self._log_status_change(
            job_id=job_id,
            from_status=current_status,
            to_status=new_status,
            changed_by=changed_by,
            notes=notes
        )

        # Auto-set timestamps based on status
        self._auto_set_timestamps(job_id, new_status)

        print(f"[OK] Updated job #{job['job_number']}: {current_status} -> {new_status}")

        # Trigger customer notifications
        self._trigger_status_notification(job_id, current_status, new_status, notes)

        return True

    def _trigger_status_notification(
        self,
        job_id: int,
        from_status: Optional[str],
        to_status: str,
        notes: Optional[str] = None
    ):
        """Trigger customer notifications for status change."""
        try:
            notification_manager = self._get_notification_manager()
            if notification_manager:
                notification_manager.notify_status_change(
                    job_id=job_id,
                    from_status=from_status,
                    to_status=to_status,
                    notes=notes
                )
        except Exception as e:
            # Don't let notification failures break status updates
            print(f"[WARN] Failed to send status notification: {e}")

    def _log_status_change(
        self,
        job_id: int,
        from_status: Optional[str],
        to_status: str,
        changed_by: Optional[str],
        notes: Optional[str]
    ):
        """Log status change to history"""
        self.db.execute("""
            INSERT INTO job_status_history (
                job_id, from_status, to_status,
                changed_by, changed_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            from_status,
            to_status,
            changed_by,
            datetime.now().isoformat(),
            notes
        ))

    def _auto_set_timestamps(self, job_id: int, status: str):
        """Auto-set timestamps when status changes"""
        updates = {}

        if status == 'DROPPED_OFF':
            updates['actual_drop_off'] = datetime.now().isoformat()
        elif status == 'COMPLETED':
            updates['actual_pickup'] = datetime.now().isoformat()
            updates['completed_at'] = datetime.now().isoformat()

        if updates:
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [job_id]

            self.db.execute(f"""
                UPDATE jobs SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, tuple(values))

    def get_status_history(self, job_id: int) -> List[Dict]:
        """Get complete status history for job"""
        return self.db.execute("""
            SELECT *
            FROM job_status_history
            WHERE job_id = ?
            ORDER BY changed_at ASC
        """, (job_id,))

    def get_valid_next_statuses(self, job_id: int) -> List[str]:
        """Get list of valid next statuses for a job"""
        job = self.get_job(job_id)
        if not job:
            return []
        return self.VALID_TRANSITIONS.get(job['status'], [])

    # ========================================================================
    # TECH ASSIGNMENT & UPDATES
    # ========================================================================

    def assign_tech(
        self,
        job_id: int,
        tech_id: int,
        estimated_hours: Optional[float] = None,
        assigned_by: Optional[str] = None
    ) -> bool:
        """
        Assign job to technician

        Args:
            job_id: Job ID
            tech_id: Technician ID
            estimated_hours: Estimated hours to complete
        """
        # Calculate estimated completion
        estimated_completion = None
        if estimated_hours:
            # Assume 8 hour work days
            days_needed = estimated_hours / 8
            estimated_completion = (date.today() + timedelta(days=max(1, int(days_needed)))).isoformat()

        self.db.execute("""
            UPDATE jobs
            SET assigned_tech_id = ?,
                assigned_at = ?,
                estimated_hours = ?,
                estimated_completion_date = ?,
                status = CASE
                    WHEN status IN ('APPROVED', 'PARTS_RECEIVED')
                    THEN 'ASSIGNED_TO_TECH'
                    ELSE status
                END,
                updated_at = ?
            WHERE id = ?
        """, (
            tech_id,
            datetime.now().isoformat(),
            estimated_hours,
            estimated_completion,
            datetime.now().isoformat(),
            job_id
        ))

        # Update tech job count
        self.db.execute("""
            UPDATE technicians SET
                current_job_count = (
                    SELECT COUNT(*) FROM jobs
                    WHERE assigned_tech_id = ?
                    AND status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
                    AND deleted_at IS NULL
                )
            WHERE id = ?
        """, (tech_id, tech_id))

        job = self.get_job(job_id)

        print(f"[OK] Assigned job #{job['job_number']} to tech #{tech_id}")
        if estimated_hours:
            print(f"     Estimated: {estimated_hours} hours, complete by {estimated_completion}")

        return True

    def unassign_tech(self, job_id: int) -> bool:
        """Remove tech assignment from job"""
        job = self.get_job(job_id)
        if not job:
            return False

        old_tech_id = job.get('assigned_tech_id')

        self.db.execute("""
            UPDATE jobs
            SET assigned_tech_id = NULL,
                assigned_at = NULL,
                updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), job_id))

        # Update old tech's job count
        if old_tech_id:
            self.db.execute("""
                UPDATE technicians SET
                    current_job_count = (
                        SELECT COUNT(*) FROM jobs
                        WHERE assigned_tech_id = ?
                        AND status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
                        AND deleted_at IS NULL
                    )
                WHERE id = ?
            """, (old_tech_id, old_tech_id))

        return True

    def tech_update_progress(
        self,
        job_id: int,
        update_text: str,
        estimated_hours_remaining: Optional[float] = None,
        updated_by: Optional[str] = None
    ) -> bool:
        """
        Tech provides daily update on progress

        Args:
            job_id: Job ID
            update_text: What tech did today / what's left
            estimated_hours_remaining: Hours remaining
        """
        # Get current tech notes
        job = self.get_job(job_id)
        if not job:
            return False

        # Append to tech notes with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_note = f"[{timestamp}] {update_text}"

        current_notes = job.get('tech_notes', '') or ''
        updated_notes = f"{current_notes}\n{new_note}".strip()

        # Update estimated completion if hours remaining provided
        estimated_completion = None
        if estimated_hours_remaining:
            days_needed = estimated_hours_remaining / 8
            estimated_completion = (date.today() + timedelta(days=max(1, int(days_needed)))).isoformat()

        self.db.execute("""
            UPDATE jobs
            SET tech_notes = ?,
                tech_daily_update = ?,
                last_tech_update = ?,
                estimated_hours = ?,
                estimated_completion_date = COALESCE(?, estimated_completion_date),
                updated_at = ?
            WHERE id = ?
        """, (
            updated_notes,
            update_text,
            datetime.now().isoformat(),
            estimated_hours_remaining,
            estimated_completion,
            datetime.now().isoformat(),
            job_id
        ))

        print(f"[OK] Tech update for job #{job['job_number']}:")
        print(f"     {update_text}")
        if estimated_hours_remaining:
            print(f"     Remaining: {estimated_hours_remaining} hours")

        return True

    def tech_mark_complete(
        self,
        job_id: int,
        completed_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Tech marks job as complete

        Auto-transitions to TECH_COMPLETE
        """
        return self.update_status(
            job_id=job_id,
            new_status='TECH_COMPLETE',
            changed_by=completed_by,
            notes=notes or "Tech marked job complete"
        )

    def tech_start_work(
        self,
        job_id: int,
        started_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Tech starts working on job

        Transitions from ASSIGNED_TO_TECH to IN_PROGRESS
        """
        return self.update_status(
            job_id=job_id,
            new_status='IN_PROGRESS',
            changed_by=started_by,
            notes=notes or "Tech started work"
        )

    # ========================================================================
    # PARTS MANAGEMENT
    # ========================================================================

    def update_parts_status(
        self,
        job_id: int,
        parts_status: str,
        parts_needed: Optional[List[str]] = None
    ) -> bool:
        """
        Update parts status for job

        Args:
            job_id: Job ID
            parts_status: NOT_NEEDED, NEEDED, ORDERED, PARTIAL, RECEIVED
            parts_needed: List of parts needed (if applicable)
        """
        self.db.execute("""
            UPDATE jobs
            SET parts_status = ?,
                parts_needed = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            parts_status,
            json.dumps(parts_needed) if parts_needed else None,
            datetime.now().isoformat(),
            job_id
        ))

        job = self.get_job(job_id)
        print(f"[OK] Updated parts status for job #{job['job_number']}: {parts_status}")

        return True

    def mark_parts_needed(self, job_id: int, parts_list: List[str]) -> bool:
        """Mark that parts are needed for a job"""
        self.update_parts_status(job_id, 'NEEDED', parts_list)
        return self.update_status(job_id, 'WAITING_PARTS', notes=f"Parts needed: {', '.join(parts_list)}")

    def mark_parts_ordered(self, job_id: int) -> bool:
        """Mark that parts have been ordered"""
        self.update_parts_status(job_id, 'ORDERED')
        return self.update_status(job_id, 'PARTS_ORDERED', notes="Parts ordered")

    def mark_parts_received(self, job_id: int) -> bool:
        """Mark that parts have been received"""
        self.update_parts_status(job_id, 'RECEIVED')
        return self.update_status(job_id, 'PARTS_RECEIVED', notes="Parts received")

    # ========================================================================
    # QUALITY CONTROL
    # ========================================================================

    def qc_pass(self, job_id: int, inspector: str = None, notes: str = None) -> bool:
        """Mark QC as passed"""
        return self.update_status(
            job_id=job_id,
            new_status='QC_COMPLETE',
            changed_by=inspector,
            notes=notes or "QC inspection passed"
        )

    def qc_fail(self, job_id: int, inspector: str = None, notes: str = None) -> bool:
        """Mark QC as failed - sends back to IN_PROGRESS"""
        return self.update_status(
            job_id=job_id,
            new_status='IN_PROGRESS',
            changed_by=inspector,
            notes=notes or "QC inspection failed - rework needed"
        )

    # ========================================================================
    # JOB RETRIEVAL & SEARCH
    # ========================================================================

    def get_job(self, job_id: int) -> Optional[Dict]:
        """
        Get complete job details

        Returns job with customer, vehicle, tech info
        """
        query = """
        SELECT
            j.*,
            c.first_name || ' ' || c.last_name as customer_name,
            c.email as customer_email,
            c.phone as customer_phone,
            v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
            v.vin,
            v.color as vehicle_color,
            t.first_name || ' ' || t.last_name as tech_name,
            ic.claim_number,
            ic.status as insurance_status
        FROM jobs j
        JOIN customers c ON c.id = j.customer_id
        JOIN vehicles v ON v.id = j.vehicle_id
        LEFT JOIN technicians t ON t.id = j.assigned_tech_id
        LEFT JOIN insurance_claims ic ON ic.id = j.insurance_claim_id
        WHERE j.id = ? AND j.deleted_at IS NULL
        """

        results = self.db.execute(query, (job_id,))

        return results[0] if results else None

    def get_job_by_number(self, job_number: str) -> Optional[Dict]:
        """Get job by job number"""
        results = self.db.execute("""
            SELECT id FROM jobs WHERE job_number = ? AND deleted_at IS NULL
        """, (job_number,))

        if results:
            return self.get_job(results[0]['id'])
        return None

    def search_jobs(
        self,
        status: Optional[str] = None,
        status_category: Optional[str] = None,
        assigned_tech_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        location_id: Optional[int] = None,
        priority: Optional[str] = None,
        search_term: Optional[str] = None,
        scheduled_date: Optional[date] = None,
        include_completed: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search jobs with filters

        Args:
            status: Specific status
            status_category: SCHEDULING, ESTIMATING, INSURANCE, PARTS,
                            PRODUCTION, QUALITY, PICKUP, BILLING
            assigned_tech_id: Jobs for specific tech
            search_term: Search job number, customer name, vehicle
        """
        query = """
        SELECT
            j.*,
            c.first_name || ' ' || c.last_name as customer_name,
            c.phone as customer_phone,
            v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
            t.first_name || ' ' || t.last_name as tech_name
        FROM jobs j
        JOIN customers c ON c.id = j.customer_id
        JOIN vehicles v ON v.id = j.vehicle_id
        LEFT JOIN technicians t ON t.id = j.assigned_tech_id
        WHERE j.deleted_at IS NULL
        """

        params = []

        if not include_completed:
            query += " AND j.status NOT IN ('COMPLETED', 'INVOICED', 'PAID')"

        if status:
            query += " AND j.status = ?"
            params.append(status)

        if status_category:
            statuses = self.STATUS_CATEGORIES.get(status_category, [])
            if statuses:
                placeholders = ','.join(['?'] * len(statuses))
                query += f" AND j.status IN ({placeholders})"
                params.extend(statuses)

        if assigned_tech_id:
            query += " AND j.assigned_tech_id = ?"
            params.append(assigned_tech_id)

        if customer_id:
            query += " AND j.customer_id = ?"
            params.append(customer_id)

        if vehicle_id:
            query += " AND j.vehicle_id = ?"
            params.append(vehicle_id)

        if location_id:
            query += " AND j.location_id = ?"
            params.append(location_id)

        if priority:
            query += " AND j.priority = ?"
            params.append(priority)

        if search_term:
            query += """ AND (
                j.job_number LIKE ? OR
                c.first_name LIKE ? OR
                c.last_name LIKE ? OR
                v.make LIKE ? OR
                v.model LIKE ?
            )"""
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern] * 5)

        if scheduled_date:
            query += " AND DATE(j.scheduled_drop_off) = ?"
            params.append(scheduled_date.isoformat())

        query += " ORDER BY j.priority DESC, j.created_at DESC LIMIT ?"
        params.append(limit)

        return self.db.execute(query, tuple(params))

    def get_jobs_by_status(self, status: str, limit: int = 100) -> List[Dict]:
        """Get all jobs with a specific status"""
        return self.search_jobs(status=status, include_completed=True, limit=limit)

    def get_jobs_by_status_board(self) -> Dict[str, List[Dict]]:
        """
        Get jobs organized by status category (for kanban board)

        Returns:
            Dict of {category: [jobs]}
        """
        board = {}

        for category, statuses in self.STATUS_CATEGORIES.items():
            board[category] = self.search_jobs(
                status_category=category,
                include_completed=(category == 'BILLING'),
                limit=50
            )

        return board

    def get_tech_jobs(self, tech_id: int, active_only: bool = True) -> List[Dict]:
        """Get all jobs assigned to a technician"""
        if active_only:
            return self.search_jobs(
                assigned_tech_id=tech_id,
                status_category='PRODUCTION'
            )
        return self.search_jobs(
            assigned_tech_id=tech_id,
            include_completed=True
        )

    def get_customer_jobs(self, customer_id: int) -> List[Dict]:
        """Get all jobs for a customer"""
        return self.search_jobs(
            customer_id=customer_id,
            include_completed=True
        )

    def get_todays_dropoffs(self) -> List[Dict]:
        """Get jobs scheduled for drop-off today"""
        return self.search_jobs(
            scheduled_date=date.today(),
            status='WAITING_DROP_OFF'
        )

    def get_ready_for_pickup(self) -> List[Dict]:
        """Get jobs ready for customer pickup"""
        return self.get_jobs_by_status('READY_FOR_PICKUP')

    # ========================================================================
    # JOB STATISTICS
    # ========================================================================

    def get_job_stats(self, location_id: int = None) -> Dict:
        """Get job statistics for dashboard"""
        stats = {}

        location_filter = "AND location_id = ?" if location_id else ""
        location_params = (location_id,) if location_id else ()

        # Total jobs
        result = self.db.execute(f"""
            SELECT COUNT(*) as count
            FROM jobs
            WHERE deleted_at IS NULL {location_filter}
        """, location_params)
        stats['total_jobs'] = result[0]['count']

        # By status category
        for category, statuses in self.STATUS_CATEGORIES.items():
            placeholders = ','.join(['?'] * len(statuses))
            result = self.db.execute(f"""
                SELECT COUNT(*) as count
                FROM jobs
                WHERE deleted_at IS NULL
                  AND status IN ({placeholders})
                  {location_filter}
            """, tuple(statuses) + location_params)
            stats[f'{category.lower()}_count'] = result[0]['count']

        # Jobs needing attention (overdue)
        result = self.db.execute(f"""
            SELECT COUNT(*) as count
            FROM jobs
            WHERE deleted_at IS NULL
              AND status NOT IN ('COMPLETED', 'INVOICED', 'PAID')
              AND (
                  (scheduled_drop_off < datetime('now') AND status = 'WAITING_DROP_OFF')
                  OR (estimated_completion_date < date('now') AND status = 'IN_PROGRESS')
              )
              {location_filter}
        """, location_params)
        stats['needs_attention'] = result[0]['count']

        # Average cycle time (days) - last 90 days
        result = self.db.execute(f"""
            SELECT AVG(
                JULIANDAY(completed_at) - JULIANDAY(created_at)
            ) as avg_days
            FROM jobs
            WHERE deleted_at IS NULL
              AND completed_at IS NOT NULL
              AND created_at >= date('now', '-90 days')
              {location_filter}
        """, location_params)
        stats['avg_cycle_time_days'] = round(result[0]['avg_days'] or 0, 1)

        # Today's stats
        result = self.db.execute(f"""
            SELECT
                SUM(CASE WHEN DATE(created_at) = DATE('now') THEN 1 ELSE 0 END) as created_today,
                SUM(CASE WHEN DATE(completed_at) = DATE('now') THEN 1 ELSE 0 END) as completed_today
            FROM jobs
            WHERE deleted_at IS NULL {location_filter}
        """, location_params)
        stats['created_today'] = result[0]['created_today'] or 0
        stats['completed_today'] = result[0]['completed_today'] or 0

        return stats

    def get_tech_workload(self, tech_id: Optional[int] = None) -> List[Dict]:
        """
        Get workload for tech(s)

        Returns list of techs with active job counts
        """
        query = """
        SELECT
            t.id,
            t.first_name || ' ' || t.last_name as tech_name,
            t.skill_level,
            COUNT(j.id) as active_jobs,
            SUM(j.estimated_hours) as total_hours,
            t.max_jobs_concurrent
        FROM technicians t
        LEFT JOIN jobs j ON j.assigned_tech_id = t.id
            AND j.status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
            AND j.deleted_at IS NULL
        WHERE t.deleted_at IS NULL AND t.status = 'ACTIVE'
        """

        params = []

        if tech_id:
            query += " AND t.id = ?"
            params.append(tech_id)

        query += " GROUP BY t.id ORDER BY active_jobs DESC"

        return self.db.execute(query, tuple(params))

    def get_priority_jobs(self, limit: int = 20) -> List[Dict]:
        """Get highest priority active jobs"""
        return self.db.execute("""
            SELECT
                j.*,
                c.first_name || ' ' || c.last_name as customer_name,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
                t.first_name || ' ' || t.last_name as tech_name
            FROM jobs j
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            LEFT JOIN technicians t ON t.id = j.assigned_tech_id
            WHERE j.deleted_at IS NULL
              AND j.status NOT IN ('COMPLETED', 'INVOICED', 'PAID')
            ORDER BY
                CASE j.priority
                    WHEN 'URGENT' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'NORMAL' THEN 3
                    WHEN 'LOW' THEN 4
                END,
                j.created_at ASC
            LIMIT ?
        """, (limit,))

    # ========================================================================
    # JOB UPDATES
    # ========================================================================

    def update_job(self, job_id: int, data: Dict) -> bool:
        """Update job fields"""
        return self.db.update('jobs', job_id, data)

    def set_priority(self, job_id: int, priority: str) -> bool:
        """Set job priority"""
        if priority not in ['URGENT', 'HIGH', 'NORMAL', 'LOW']:
            raise ValueError(f"Invalid priority: {priority}")
        return self.update_job(job_id, {'priority': priority})

    def add_internal_note(self, job_id: int, note: str) -> bool:
        """Add internal note to job"""
        job = self.get_job(job_id)
        if not job:
            return False

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_note = f"[{timestamp}] {note}"

        current_notes = job.get('internal_notes', '') or ''
        updated_notes = f"{current_notes}\n{new_note}".strip()

        return self.update_job(job_id, {'internal_notes': updated_notes})

    def link_insurance_claim(self, job_id: int, claim_id: int) -> bool:
        """Link insurance claim to job"""
        return self.update_job(job_id, {'insurance_claim_id': claim_id})

    def delete_job(self, job_id: int, hard: bool = False) -> bool:
        """Delete job (soft delete by default)"""
        return self.db.delete('jobs', job_id, soft=not hard)
