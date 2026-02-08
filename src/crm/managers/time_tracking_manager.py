"""
Time Tracking Manager
PDR CRM - Technician time tracking and clock in/out.

FEATURES:
- Clock in/out tracking
- Break management
- Job time logging
- Daily/weekly summaries
- GPS location capture
"""

from typing import Optional, Dict, List
from datetime import datetime, date, timedelta


class TimeTrackingManager:
    """
    Manages technician time tracking - clock in/out, job time, summaries.

    Time entries are stored with types:
    - clock_in: Start of work day
    - clock_out: End of work day
    - break_start: Start of break
    - break_end: End of break
    - job_time: Time logged to specific job
    """

    def __init__(self, db):
        """Initialize with database connection"""
        self.db = db
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure time tracking tables exist"""
        # Time entries table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                technician_id INTEGER NOT NULL,

                entry_type TEXT NOT NULL,
                entry_time TIMESTAMP NOT NULL,

                job_id INTEGER,
                hours REAL,

                latitude REAL,
                longitude REAL,

                description TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (technician_id) REFERENCES technicians(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)

        # Daily summary table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS time_daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                technician_id INTEGER NOT NULL,

                work_date DATE NOT NULL,

                clock_in_time TIMESTAMP,
                clock_out_time TIMESTAMP,

                total_hours REAL DEFAULT 0,
                break_hours REAL DEFAULT 0,
                job_hours REAL DEFAULT 0,

                is_complete INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,

                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (technician_id) REFERENCES technicians(id),
                UNIQUE(technician_id, work_date)
            )
        """)

        # Daily updates table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS tech_daily_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                technician_id INTEGER NOT NULL,

                update_date DATE NOT NULL,
                jobs_summary TEXT,
                total_hours REAL,
                notes TEXT,
                issues TEXT,

                submitted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (technician_id) REFERENCES technicians(id)
            )
        """)

        # Create indexes
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_time_entries_tech_date
            ON time_entries(technician_id, entry_time)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_time_summary_tech_date
            ON time_daily_summary(technician_id, work_date)
        """)

    def _get_or_create_daily_summary(self, tech_id: int, work_date: date = None) -> Dict:
        """Get or create daily summary for a date"""
        work_date = work_date or date.today()
        date_str = work_date.isoformat()

        # Try to get existing
        results = self.db.execute("""
            SELECT * FROM time_daily_summary
            WHERE technician_id = ? AND work_date = ?
        """, (tech_id, date_str))

        if results:
            return dict(results[0])

        # Get org_id from technician
        tech = self.db.execute("SELECT organization_id FROM technicians WHERE id = ?", (tech_id,))
        org_id = tech[0]['organization_id'] if tech else 1

        # Create new
        summary_id = self.db.insert('time_daily_summary', {
            'organization_id': org_id,
            'technician_id': tech_id,
            'work_date': date_str
        })

        return {
            'id': summary_id,
            'organization_id': org_id,
            'technician_id': tech_id,
            'work_date': date_str,
            'clock_in_time': None,
            'clock_out_time': None,
            'total_hours': 0,
            'break_hours': 0,
            'job_hours': 0,
            'is_complete': 0
        }

    def clock_in(self, tech_id: int, location: Dict = None, notes: str = None) -> Dict:
        """
        Clock in for the day.

        Returns: {success, entry_id, clock_in_time, message}
        """
        # Check if already clocked in today
        status = self.get_current_status(tech_id)
        if status in ('clocked_in', 'on_break'):
            return {
                'success': False,
                'error': 'Already clocked in today',
                'status': status
            }

        now = datetime.now()
        today = date.today()

        # Get org_id from technician
        tech = self.db.execute("SELECT organization_id FROM technicians WHERE id = ?", (tech_id,))
        org_id = tech[0]['organization_id'] if tech else 1

        # Create time entry
        entry_id = self.db.insert('time_entries', {
            'organization_id': org_id,
            'technician_id': tech_id,
            'entry_type': 'clock_in',
            'entry_time': now.isoformat(),
            'latitude': location.get('lat') if location else None,
            'longitude': location.get('lng') if location else None,
            'description': notes
        })

        # Update daily summary
        summary = self._get_or_create_daily_summary(tech_id, today)
        self.db.execute("""
            UPDATE time_daily_summary
            SET clock_in_time = ?, updated_at = ?
            WHERE id = ?
        """, (now.isoformat(), now.isoformat(), summary['id']))

        print(f"[OK] Tech #{tech_id} clocked in at {now.strftime('%H:%M')}")

        return {
            'success': True,
            'entry_id': entry_id,
            'clock_in_time': now.isoformat(),
            'message': f'Clocked in at {now.strftime("%I:%M %p")}'
        }

    def clock_out(self, tech_id: int, location: Dict = None, notes: str = None) -> Dict:
        """
        Clock out for the day.

        Returns: {success, entry_id, total_hours_today, message}
        """
        status = self.get_current_status(tech_id)
        if status == 'clocked_out':
            return {
                'success': False,
                'error': 'Not clocked in',
                'status': status
            }

        # End break if on break
        if status == 'on_break':
            self.end_break(tech_id)

        now = datetime.now()
        today = date.today()

        # Get org_id
        tech = self.db.execute("SELECT organization_id FROM technicians WHERE id = ?", (tech_id,))
        org_id = tech[0]['organization_id'] if tech else 1

        # Create time entry
        entry_id = self.db.insert('time_entries', {
            'organization_id': org_id,
            'technician_id': tech_id,
            'entry_type': 'clock_out',
            'entry_time': now.isoformat(),
            'latitude': location.get('lat') if location else None,
            'longitude': location.get('lng') if location else None,
            'description': notes
        })

        # Calculate total hours
        summary = self._get_or_create_daily_summary(tech_id, today)
        total_hours = 0

        if summary.get('clock_in_time'):
            clock_in = datetime.fromisoformat(summary['clock_in_time'])
            total_minutes = (now - clock_in).total_seconds() / 60
            break_hours = summary.get('break_hours', 0) or 0
            total_hours = round((total_minutes / 60) - break_hours, 2)

        # Update daily summary
        self.db.execute("""
            UPDATE time_daily_summary
            SET clock_out_time = ?, total_hours = ?, updated_at = ?
            WHERE id = ?
        """, (now.isoformat(), total_hours, now.isoformat(), summary['id']))

        print(f"[OK] Tech #{tech_id} clocked out at {now.strftime('%H:%M')} ({total_hours}h)")

        return {
            'success': True,
            'entry_id': entry_id,
            'clock_out_time': now.isoformat(),
            'total_hours': total_hours,
            'message': f'Clocked out at {now.strftime("%I:%M %p")} - {total_hours} hours'
        }

    def start_break(self, tech_id: int) -> Dict:
        """Start a break"""
        status = self.get_current_status(tech_id)
        if status != 'clocked_in':
            return {
                'success': False,
                'error': f'Cannot start break - current status: {status}',
                'status': status
            }

        now = datetime.now()

        # Get org_id
        tech = self.db.execute("SELECT organization_id FROM technicians WHERE id = ?", (tech_id,))
        org_id = tech[0]['organization_id'] if tech else 1

        entry_id = self.db.insert('time_entries', {
            'organization_id': org_id,
            'technician_id': tech_id,
            'entry_type': 'break_start',
            'entry_time': now.isoformat()
        })

        return {
            'success': True,
            'entry_id': entry_id,
            'break_start_time': now.isoformat(),
            'message': f'Break started at {now.strftime("%I:%M %p")}'
        }

    def end_break(self, tech_id: int) -> Dict:
        """End a break"""
        status = self.get_current_status(tech_id)
        if status != 'on_break':
            return {
                'success': False,
                'error': f'Not on break - current status: {status}',
                'status': status
            }

        now = datetime.now()
        today = date.today()

        # Get org_id
        tech = self.db.execute("SELECT organization_id FROM technicians WHERE id = ?", (tech_id,))
        org_id = tech[0]['organization_id'] if tech else 1

        # Find break start
        break_start_entry = self.db.execute("""
            SELECT * FROM time_entries
            WHERE technician_id = ? AND entry_type = 'break_start'
              AND DATE(entry_time) = ?
            ORDER BY entry_time DESC LIMIT 1
        """, (tech_id, today.isoformat()))

        break_hours = 0
        if break_start_entry:
            break_start = datetime.fromisoformat(break_start_entry[0]['entry_time'])
            break_minutes = (now - break_start).total_seconds() / 60
            break_hours = round(break_minutes / 60, 2)

        entry_id = self.db.insert('time_entries', {
            'organization_id': org_id,
            'technician_id': tech_id,
            'entry_type': 'break_end',
            'entry_time': now.isoformat(),
            'hours': break_hours
        })

        # Update daily summary with total break time
        summary = self._get_or_create_daily_summary(tech_id, today)
        current_break_hours = summary.get('break_hours', 0) or 0
        total_break_hours = round(current_break_hours + break_hours, 2)

        self.db.execute("""
            UPDATE time_daily_summary
            SET break_hours = ?, updated_at = ?
            WHERE id = ?
        """, (total_break_hours, now.isoformat(), summary['id']))

        return {
            'success': True,
            'entry_id': entry_id,
            'break_end_time': now.isoformat(),
            'break_duration': break_hours,
            'message': f'Break ended ({int(break_hours * 60)} minutes)'
        }

    def log_job_time(self, tech_id: int, job_id: int, hours: float,
                     description: str = None) -> Dict:
        """Log time spent on a specific job"""
        now = datetime.now()
        today = date.today()

        # Get org_id
        tech = self.db.execute("SELECT organization_id FROM technicians WHERE id = ?", (tech_id,))
        org_id = tech[0]['organization_id'] if tech else 1

        entry_id = self.db.insert('time_entries', {
            'organization_id': org_id,
            'technician_id': tech_id,
            'entry_type': 'job_time',
            'entry_time': now.isoformat(),
            'job_id': job_id,
            'hours': hours,
            'description': description
        })

        # Update daily summary job hours
        summary = self._get_or_create_daily_summary(tech_id, today)
        current_job_hours = summary.get('job_hours', 0) or 0
        total_job_hours = round(current_job_hours + hours, 2)

        self.db.execute("""
            UPDATE time_daily_summary
            SET job_hours = ?, updated_at = ?
            WHERE id = ?
        """, (total_job_hours, now.isoformat(), summary['id']))

        print(f"[OK] Logged {hours}h to job #{job_id} for tech #{tech_id}")

        return {
            'success': True,
            'entry_id': entry_id,
            'hours_logged': hours,
            'message': f'{hours} hours logged to job'
        }

    def get_current_status(self, tech_id: int) -> str:
        """
        Get tech's current status: clocked_out, clocked_in, on_break
        """
        today = date.today().isoformat()

        # Get today's entries ordered by time
        entries = self.db.execute("""
            SELECT entry_type, entry_time FROM time_entries
            WHERE technician_id = ? AND DATE(entry_time) = ?
            ORDER BY entry_time DESC
        """, (tech_id, today))

        if not entries:
            return 'clocked_out'

        last_entry = entries[0]['entry_type']

        if last_entry == 'clock_out':
            return 'clocked_out'
        elif last_entry == 'break_start':
            return 'on_break'
        elif last_entry in ('clock_in', 'break_end', 'job_time'):
            return 'clocked_in'

        return 'clocked_out'

    def get_today(self, tech_id: int) -> Dict:
        """
        Get today's time data
        """
        today = date.today()
        summary = self._get_or_create_daily_summary(tech_id, today)

        # Get entries for today
        entries = self.db.execute("""
            SELECT * FROM time_entries
            WHERE technician_id = ? AND DATE(entry_time) = ?
            ORDER BY entry_time
        """, (tech_id, today.isoformat()))

        status = self.get_current_status(tech_id)

        # Calculate current hours if clocked in
        current_hours = summary.get('total_hours', 0) or 0
        if status in ('clocked_in', 'on_break') and summary.get('clock_in_time'):
            clock_in = datetime.fromisoformat(summary['clock_in_time'])
            minutes_worked = (datetime.now() - clock_in).total_seconds() / 60
            break_hours = summary.get('break_hours', 0) or 0
            current_hours = round((minutes_worked / 60) - break_hours, 2)

        return {
            'date': today.isoformat(),
            'status': status,
            'clock_in_time': summary.get('clock_in_time'),
            'clock_out_time': summary.get('clock_out_time'),
            'total_hours': current_hours,
            'break_hours': summary.get('break_hours', 0) or 0,
            'job_hours': summary.get('job_hours', 0) or 0,
            'is_complete': bool(summary.get('is_complete')),
            'entries': entries
        }

    def get_week_summary(self, tech_id: int, week_start: date = None) -> Dict:
        """
        Get week summary
        """
        if not week_start:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())  # Monday

        week_end = week_start + timedelta(days=6)

        # Get daily summaries for the week
        summaries = self.db.execute("""
            SELECT * FROM time_daily_summary
            WHERE technician_id = ?
              AND work_date >= ? AND work_date <= ?
            ORDER BY work_date
        """, (tech_id, week_start.isoformat(), week_end.isoformat()))

        daily_totals = []
        total_hours = 0
        total_break_hours = 0
        total_job_hours = 0

        # Build daily data
        current_date = week_start
        summary_map = {s['work_date']: s for s in summaries}

        while current_date <= week_end:
            date_str = current_date.isoformat()
            summary = summary_map.get(date_str, {})

            hours = summary.get('total_hours', 0) or 0
            daily_totals.append({
                'date': date_str,
                'day_name': current_date.strftime('%A'),
                'hours': hours,
                'is_complete': bool(summary.get('is_complete'))
            })

            total_hours += hours
            total_break_hours += summary.get('break_hours', 0) or 0
            total_job_hours += summary.get('job_hours', 0) or 0

            current_date += timedelta(days=1)

        # Get job breakdown for the week
        job_entries = self.db.execute("""
            SELECT te.job_id, j.job_number,
                   c.first_name || ' ' || c.last_name as customer_name,
                   v.year || ' ' || v.make || ' ' || v.model as vehicle,
                   SUM(te.hours) as total_hours
            FROM time_entries te
            JOIN jobs j ON j.id = te.job_id
            LEFT JOIN customers c ON c.id = j.customer_id
            LEFT JOIN vehicles v ON v.id = j.vehicle_id
            WHERE te.technician_id = ?
              AND DATE(te.entry_time) >= ? AND DATE(te.entry_time) <= ?
              AND te.entry_type = 'job_time'
            GROUP BY te.job_id
            ORDER BY total_hours DESC
        """, (tech_id, week_start.isoformat(), week_end.isoformat()))

        return {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'daily_totals': daily_totals,
            'total_hours': round(total_hours, 2),
            'total_break_hours': round(total_break_hours, 2),
            'total_job_hours': round(total_job_hours, 2),
            'job_breakdown': job_entries
        }

    def get_time_for_job(self, job_id: int) -> Dict:
        """Get all time logged to a specific job"""
        entries = self.db.execute("""
            SELECT te.*, t.first_name || ' ' || t.last_name as tech_name
            FROM time_entries te
            JOIN technicians t ON t.id = te.technician_id
            WHERE te.job_id = ? AND te.entry_type = 'job_time'
            ORDER BY te.entry_time
        """, (job_id,))

        total_hours = sum(e.get('hours', 0) or 0 for e in entries)

        return {
            'job_id': job_id,
            'entries': entries,
            'total_hours': round(total_hours, 2),
            'entry_count': len(entries)
        }

    def is_clocked_in(self, tech_id: int) -> bool:
        """Check if tech is currently clocked in"""
        status = self.get_current_status(tech_id)
        return status in ('clocked_in', 'on_break')

    def mark_day_complete(self, tech_id: int, work_date: date = None) -> bool:
        """Mark a day's time tracking as complete"""
        work_date = work_date or date.today()
        summary = self._get_or_create_daily_summary(tech_id, work_date)

        self.db.execute("""
            UPDATE time_daily_summary
            SET is_complete = 1, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), summary['id']))

        return True
